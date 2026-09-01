"""
sofascore_feed.py — free live tennis scores, no Apify, no monthly bill.

Standalone. Nothing else in the bot imports this yet; wire it in yourself
when you've seen it work.

WHY THIS EXISTS
    The Apify actors charge per row of data. At one check every 25 seconds
    that runs about $24/day, so the $29 Starter plan lasts roughly a day.
    Sofascore serves the same scores for free — it just blocks plain scripts
    with a 403. curl_cffi gets past that by impersonating a real Chrome TLS
    handshake, so no browser process is needed.

WHAT YOU GET THAT APIFY DIDN'T
    * sets, games-per-set, and the live point ("15", "40", "AD")
    * who is serving right now (derived — see _server_side)
    * ITF and Challenger coverage (ESPN has neither)
    * changeTimestamp, so score age is real rather than guessed

SETUP
    pip install curl_cffi

USE
    python sofascore_feed.py --debug              # show every live match
    python sofascore_feed.py --find "Khodorchenko"
    python sofascore_feed.py --poll 180 --out scores.jsonl   # log for research

BE POLITE
    Sofascore's terms don't invite automated collection. Keep it to personal
    use and leave POLL_MIN_SEC alone — every 2-3 minutes is plenty, since a
    tennis set takes half an hour.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Optional

from curl_cffi import requests as cr

BASE = "https://www.sofascore.com/api/v1"
LIVE = f"{BASE}/sport/tennis/events/live"
# Floor; do not lower FOR THE LIVE BOT — the bot needs this free endpoint to
# keep answering more than it needs another sample. ⚠ `record_data.py` polls
# the same endpoint every 10s on purpose (see the note at its MIN_INTERVAL):
# the recorder is measuring reaction speed and a 60s sample cannot see it.
# Both numbers are intentional. Noted 2026-09-01 in the assumption audit.
POLL_MIN_SEC = 60


# NFKD cannot decompose these — they are distinct letters, not accented bases.
_LETTER_FOLD = str.maketrans({
    "đ": "dj", "ð": "d", "ł": "l", "ø": "o", "ß": "ss",
    "æ": "ae", "œ": "oe", "þ": "th", "ħ": "h", "ı": "i",
})


def _norm(s: str) -> str:
    """Lowercase, strip punctuation AND strip accents.

    Sofascore writes "Aleksandar Vukić", Kalshi writes "Aleksandar Vukic".
    Without folding the accent away those never compare equal and the player
    is simply invisible. Tennis is full of them.
    """
    folded = unicodedata.normalize("NFKD", str(s).lower().translate(_LETTER_FOLD))
    return "".join(ch for ch in folded
                   if ch.isalnum() and not unicodedata.combining(ch))


def _num(v: Any) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


@dataclass
class LiveScore:
    """Field-compatible with live_score.LiveScore, plus the extras."""
    sets_won: int
    sets_lost: int
    status: str
    match_title: str
    fetched_at: float
    raw: dict
    was_favorite: Optional[bool] = None

    # new — none of this was available from the Apify feed
    serving: Optional[bool] = None      # True if THIS side is serving
    point: str = ""                     # "0" "15" "30" "40" "AD"
    opp_point: str = ""
    games_won: int = 0                  # games in the current set
    games_lost: int = 0
    set_number: int = 0
    finished: bool = False
    last_change_ts: Optional[float] = None   # when the scoreline last moved

    @property
    def age_sec(self) -> int:
        return int(time.time() - self.fetched_at)

    @property
    def since_change_sec(self) -> Optional[int]:
        """Seconds since the score itself last moved. Useful for research —
        not for the staleness guard, which cares about feed age."""
        if self.last_change_ts is None:
            return None
        return int(time.time() - self.last_change_ts)


def _sets_and_games(ev: dict, side: str) -> tuple[int, int, int, int, int]:
    """(sets_won, sets_lost, games_this_set, games_lost_this_set, set_no).

    Sofascore puts sets won in score.current and games per set in
    period1..period5. lastPeriod names the set in progress.
    """
    me = ev.get(f"{side}Score") or {}
    them = ev.get(f"{'away' if side == 'home' else 'home'}Score") or {}
    last = str(ev.get("lastPeriod") or "")
    m = re.match(r"period(\d+)", last)
    set_no = int(m.group(1)) if m else 0
    key = f"period{set_no}" if set_no else None
    return (_num(me.get("current")), _num(them.get("current")),
            _num(me.get(key)) if key else 0,
            _num(them.get(key)) if key else 0,
            set_no)


def _server_side(ev: dict) -> Optional[str]:
    """'home' or 'away' — who is serving this game.

    Serve alternates every game for the whole match, so the side that served
    first is serving again whenever an even number of games has been played.
    firstToServe is 1 for home, 2 for away.

    Caveat: inside a tiebreak the serve rotates 1-2-2, so this can be wrong
    for the duration of a tiebreak. Everywhere else it is exact.
    """
    first = ev.get("firstToServe")
    if first not in (1, 2):
        return None
    h, a = ev.get("homeScore") or {}, ev.get("awayScore") or {}
    games = 0
    for i in range(1, 6):
        games += _num(h.get(f"period{i}")) + _num(a.get(f"period{i}"))
    starter = "home" if first == 1 else "away"
    other = "away" if starter == "home" else "home"
    return starter if games % 2 == 0 else other


class SofaScoreClient:
    """Same surface as live_score.LiveScoreClient, so it can be swapped in."""

    def __init__(self, cache_sec: int = 25, timeout: int = 20):
        self.cache_sec = cache_sec
        self.timeout = timeout
        self._cache: list[dict] = []
        self._cached_at: float = 0.0
        self.last_error: str = ""

    @property
    def enabled(self) -> bool:
        return True                      # no token, no quota, always on

    @property
    def source(self) -> str:
        """The GUI logs this whenever the feed flips. There is only one
        source now, so it never flips — which is the point."""
        return "sofascore"

    # ---- fetching -------------------------------------------------------
    def _fetch(self, force: bool = False) -> list[dict]:
        now = time.time()
        if not force and self._cache and now - self._cached_at < self.cache_sec:
            return self._cache
        delay = 1.0
        for attempt in range(3):
            try:
                r = cr.get(LIVE, impersonate="chrome", timeout=self.timeout)
                if r.status_code == 200:
                    self._cache = [self._normalize(e)
                                   for e in (r.json().get("events") or [])]
                    self._cached_at = now
                    self.last_error = ""
                    return self._cache
                self.last_error = f"HTTP {r.status_code}"
            except Exception as e:                       # network, TLS, JSON
                self.last_error = f"{type(e).__name__}: {e}"
            if attempt < 2:
                time.sleep(delay)
                delay *= 2
        return self._cache                               # stale beats nothing

    def _normalize(self, ev: dict) -> dict:
        """Reshape into the field names the existing bot already reads, so
        score_from_item / find work without changes elsewhere."""
        t = (ev.get("tournament") or {}).get("name") or ""
        home = (ev.get("homeTeam") or {}).get("name") or "?"
        away = (ev.get("awayTeam") or {}).get("name") or "?"
        hs, as_ = ev.get("homeScore") or {}, ev.get("awayScore") or {}
        status = (ev.get("status") or {})
        ch = ev.get("changes") or {}
        server = _server_side(ev)
        return {
            # --- shape the existing code expects ---
            "matchType": "doubles" if "/" in home or "Doubles" in t else "singles",
            "homePlayerName": home,
            "awayPlayerName": away,
            "score": {"home": _num(hs.get("current")), "away": _num(as_.get("current"))},
            "status": status.get("description", ""),
            # --- extras ---
            "eventId": ev.get("id"),
            "tournament": t,
            "statusType": status.get("type", ""),
            "startTimestamp": ev.get("startTimestamp"),
            "changeTimestamp": ch.get("changeTimestamp"),
            "serving": server,
            "points": {"home": str(hs.get("point", "")), "away": str(as_.get("point", ""))},
            "games": {f"set{i}": {"home": _num(hs.get(f"period{i}")),
                                  "away": _num(as_.get(f"period{i}"))}
                      for i in range(1, 6)
                      if hs.get(f"period{i}") is not None},
            "lastPeriod": ev.get("lastPeriod"),
            "winnerCode": ev.get("winnerCode"),
            # --- strength of field ---
            # A #1200 vs #1000 match is close to a coin flip; #1 vs #200 is
            # not. Without these the bot treats both identically, so every
            # ranking-based idea is untestable. SofaScore supplies them and we
            # were simply dropping them on the floor.
            "homeRank": (ev.get("homeTeam") or {}).get("ranking"),
            "awayRank": (ev.get("awayTeam") or {}).get("ranking"),
            "gender": (ev.get("homeTeam") or {}).get("gender"),
            "category": ((ev.get("tournament") or {}).get("category") or {}).get("name"),
            "categorySlug": ((ev.get("tournament") or {}).get("category") or {}).get("slug"),
            "uniqueTournament": ((ev.get("tournament") or {})
                                 .get("uniqueTournament") or {}).get("name"),
        }

    def raw(self, max_matches: int = 50, force: bool = True) -> list[dict]:
        """max_matches is accepted for signature compatibility with the old
        Apify client (autoscan calls raw(max_matches=60)). The live endpoint
        returns every in-progress match in one response, so this only trims."""
        return self._fetch(force=force)[:max_matches]

    # ---- lookup ---------------------------------------------------------
    def find(self, player_name: str, max_matches: int = 50,
             singles_only: bool = True) -> Optional[LiveScore]:
        target = _norm(player_name)
        if not target:
            return None
        for m in self._fetch()[:max_matches]:
            if singles_only and m.get("matchType") != "singles":
                continue
            h, a = _norm(m["homePlayerName"]), _norm(m["awayPlayerName"])
            if h and (target in h or h in target):
                side = "home"
            elif a and (target in a or a in target):
                side = "away"
            else:
                continue
            return self.score_from_item(m, side)
        return None

    def score_from_item(self, m: dict, side: str) -> Optional[LiveScore]:
        other = "away" if side == "home" else "home"
        sc = m.get("score") or {}
        # Age = how old OUR INFORMATION is, i.e. when we last called the feed.
        # Deliberately not changeTimestamp: a score that hasn't changed in two
        # minutes isn't stale, it's just a long game, and using the change time
        # would make the engine reject every quiet moment in the match.
        # Never now() either — that makes cached data look permanently fresh
        # and defeats the staleness guard entirely.
        fetched = float(self._cached_at or time.time())
        games = m.get("games") or {}
        last = str(m.get("lastPeriod") or "")
        gm = games.get(last.replace("period", "set"), {}) if last else {}
        set_no = int(last.replace("period", "")) if last.startswith("period") else 0
        return LiveScore(
            sets_won=_num(sc.get(side)), sets_lost=_num(sc.get(other)),
            status=str(m.get("status", "")),
            match_title=f"{m['homePlayerName']} vs {m['awayPlayerName']}",
            fetched_at=fetched, raw=m, was_favorite=None,
            serving=(None if m.get("serving") is None else m["serving"] == side),
            point=str((m.get("points") or {}).get(side, "")),
            opp_point=str((m.get("points") or {}).get(other, "")),
            games_won=_num(gm.get(side)), games_lost=_num(gm.get(other)),
            set_number=set_no,
            finished=str(m.get("statusType", "")) == "finished",
            last_change_ts=(float(m["changeTimestamp"])
                            if m.get("changeTimestamp") else None),
        )


# ------------------------------------------------------------------ CLI
def _debug(c: SofaScoreClient) -> None:
    items = c.raw()
    if not items:
        print(f"no live matches (last_error: {c.last_error or 'none'})")
        return
    print(f"{len(items)} live match(es)\n")
    for m in items:
        if m["matchType"] != "singles":
            continue
        s = c.score_from_item(m, "home")
        srv = "?" if m.get("serving") is None else m["serving"]
        gs = " ".join(f"{v['home']}-{v['away']}" for v in (m.get("games") or {}).values())
        print(f"  {m['tournament'][:34]:34s} {m['homePlayerName'][:20]:20s} vs "
              f"{m['awayPlayerName'][:20]:20s} | sets {s.sets_won}-{s.sets_lost}"
              f" | games {gs} | pts {m['points']['home']}-{m['points']['away']}"
              f" | serving={srv} | {m['status']} | age {s.age_sec}s")


def _poll(c: SofaScoreClient, every: int, out: str) -> None:
    every = max(every, POLL_MIN_SEC)
    print(f"polling every {every}s -> {out}   (ctrl-c to stop)")
    n = 0
    try:
        while True:
            items = c.raw(force=True)
            stamp = time.time()
            with open(out, "a", encoding="utf-8") as f:
                for m in items:
                    f.write(json.dumps({"snapshot_ts": stamp, **m}) + "\n")
            n += len(items)
            print(f"  {time.strftime('%H:%M:%S')}  {len(items):3d} matches  "
                  f"{n} rows total" + (f"  [{c.last_error}]" if c.last_error else ""),
                  flush=True)
            time.sleep(every)
    except KeyboardInterrupt:
        print(f"\nstopped. {n} rows in {out}")


def main() -> None:
    p = argparse.ArgumentParser(description="Free Sofascore tennis feed")
    p.add_argument("--debug", action="store_true", help="print every live match")
    p.add_argument("--find", metavar="PLAYER", help="look up one player")
    p.add_argument("--poll", type=int, metavar="SECONDS",
                   help=f"log snapshots forever (min {POLL_MIN_SEC})")
    p.add_argument("--out", default="scores.jsonl", help="output file for --poll")
    a = p.parse_args()

    c = SofaScoreClient()
    if a.poll:
        _poll(c, a.poll, a.out)
    elif a.find:
        s = c.find(a.find)
        if not s:
            print(f"'{a.find}' not found in live matches "
                  f"({c.last_error or 'not playing right now'})")
            sys.exit(1)
        print(f"{s.match_title}\n  {s.status} | sets {s.sets_won}-{s.sets_lost} | "
              f"games {s.games_won}-{s.games_lost} | point {s.point}-{s.opp_point}\n"
              f"  serving={s.serving} | set {s.set_number} | age {s.age_sec}s")
    else:
        _debug(c)


if __name__ == "__main__":
    main()
