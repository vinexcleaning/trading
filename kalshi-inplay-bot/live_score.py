"""
live_score.py — pulls live tennis set scores from Apify (crawlstone/tennis-scraper)
so you don't have to eyeball SofaScore/Kalshi and type the score in by hand.

Setup:
    Free account at apify.com -> Settings -> Integrations -> copy your API token.
    set APIFY_TOKEN=your-token-here

Check it's working and see the real field names before trusting it:
    python live_score.py --debug

Find one player right now:
    python live_score.py --find "Alcaraz"

This module only READS scores. It never places orders and never decides
anything — scanner.py shows you what it found and you still confirm.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests

ACTOR = "crawlstone~tennis-scraper"
RUN_URL = f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items"

# Fallback. The primary reads SofaScore, which periodically blocks the
# scraper's proxies outright — when that happens the actor itself fails and
# no amount of retrying on our side helps. This one reads Flashscore.
FALLBACK_ACTOR = "extractify-labs~flashscore-tennis-matches"
FALLBACK_URL = f"https://api.apify.com/v2/acts/{FALLBACK_ACTOR}/run-sync-get-dataset-items"

# "Boyer T." (Flashscore) -> "T. Boyer", so the surname is the last token and
# the same matcher works for both feeds.
# non-greedy surname so multi-word ones ("Bittoun Kouzmine C.") flip too
_SURNAME_FIRST = re.compile(r"^(.+?)\s+([A-Z])\.$")


def _norm(s: str) -> str:
    return "".join(ch for ch in str(s).lower() if ch.isalnum())


@dataclass
class LiveScore:
    sets_won: int
    sets_lost: int
    status: str
    match_title: str
    fetched_at: float
    raw: dict
    was_favorite: Optional[bool] = None   # None = opening odds unavailable/unparseable

    @property
    def age_sec(self) -> int:
        return int(time.time() - self.fetched_at)


def _fractional_to_decimal(frac: Any) -> Optional[float]:
    """'2/11' -> 1.18. Returns None if it's missing or not a plain fraction."""
    try:
        a, b = str(frac).split("/")
        return 1 + float(a) / float(b)
    except (ValueError, ZeroDivisionError):
        return None


def _opening_favorite(m: dict) -> Optional[str]:
    """'home' or 'away' — whichever side opened at shorter (lower decimal)
    odds. None if odds are missing on either side or tied."""
    if m.get("_favorite_side"):          # fallback feed: inferred from ranking
        return m["_favorite_side"]
    odds = m.get("odds") or {}
    h = _fractional_to_decimal((odds.get("home") or {}).get("initialFractional"))
    a = _fractional_to_decimal((odds.get("away") or {}).get("initialFractional"))
    if h is None or a is None or h == a:
        return None
    return "home" if h < a else "away"


class LiveScoreClient:
    # Every scan that misses the cache costs an Apify actor run, so caching
    # saves real money. But it MUST stay under Config.max_score_age_sec (30s)
    # — past that the engine correctly refuses the trade for a stale score,
    # and you'd just be paying for scans that can never fire.
    def __init__(self, token: Optional[str] = None, cache_sec: int = 25):
        self.token = token or os.environ.get("APIFY_TOKEN", "")
        self.cache_sec = cache_sec
        self._cache: list[dict] = []
        self._cached_at = 0.0
        self.last_error: str = ""
        self.source: str = ""      # "sofascore" | "flashscore" | "" if both down
        # SofaScore stays the primary. But a dead primary costs ~50s per scan
        # to rediscover, which would quadruple the scan cycle during an
        # outage. So after it fails we stop asking for a few minutes, then
        # try again — it still returns to SofaScore on its own, just not on
        # every single tick.
        self._primary_down_until = 0.0
        self.primary_cooldown_sec = 300
        self.quota_exhausted = False

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    # ---- fetching -----------------------------------------------------
    def _fetch(self, max_matches: int = 50, force: bool = False) -> list[dict]:
        if not self.enabled:
            return []
        now = time.time()
        if not force and self._cache and now - self._cached_at < self.cache_sec:
            return self._cache
        # Fail FAST on the primary. When SofaScore blocks the scraper the actor
        # burns ~50s and dies; retrying it just multiplies the wait. One try,
        # then switch feeds.
        primary_err = ""
        if now < self._primary_down_until:
            secs = int(self._primary_down_until - now)
            primary_err = f"skipped, cooling down {secs}s after it failed"
        else:
            try:
                r = requests.post(
                    RUN_URL,
                    params={"token": self.token, "timeout": 50},
                    json={"mode": "liveMatches", "maxMatches": max_matches},
                    timeout=60,
                )
                r.raise_for_status()
                items = r.json()
                if items and not (len(items) == 1 and items[0].get("error")):
                    # back on the good feed — clear any cooldown
                    self._primary_down_until = 0.0
                    self._cache, self._cached_at = items, now
                    self.source, self.last_error = "sofascore", ""
                    return self._cache
                primary_err = "primary returned no usable data"
            except requests.RequestException as e:
                primary_err = str(e)[:120]
            self._primary_down_until = now + self.primary_cooldown_sec

        try:
            r = requests.post(
                FALLBACK_URL,
                params={"token": self.token, "timeout": 90},
                json={"dayOffsets": ["0"], "matchStatuses": ["live"],
                      "maxItems": max_matches},
                timeout=120,
            )
            r.raise_for_status()
            self._cache = _from_flashscore(r.json())
            self._cached_at = now
            self.source = "flashscore"
            self.last_error = f"primary feed down ({primary_err}); using Flashscore"
            return self._cache
        except requests.RequestException as e:
            self.source = ""
            body = ""
            resp = getattr(e, "response", None)
            if resp is not None:
                try:
                    body = resp.json().get("error", {}).get("message", "")
                except ValueError:
                    body = ""
                if resp.status_code == 403 and "usage" in body.lower():
                    self.quota_exhausted = True
                    self.last_error = (
                        "Apify monthly usage limit hit — the live score feed is OFF "
                        "until the billing cycle resets or you upgrade. No new trades "
                        "can be found. (Open positions are still watched: stops use "
                        "Kalshi prices, not this feed.)")
                    raise
            self.last_error = f"both feeds failed — primary: {primary_err}; fallback: {body or str(e)[:120]}"
            raise

    def raw(self, max_matches: int = 50, force: bool = True) -> list[dict]:
        """Unparsed dataset items — use --debug to inspect real field names."""
        return self._fetch(max_matches, force=force)

    # ---- lookup ---------------------------------------------------------
    def find(self, player_name: str, max_matches: int = 50) -> Optional[LiveScore]:
        """Fuzzy-match a player name against the live snapshot (home/away
        singles fields) and return their current set score, read straight
        off score.home / score.away — Apify already tallies sets there."""
        target = _norm(player_name)
        if not target:
            return None
        try:
            items = self._fetch(max_matches)
        except requests.RequestException as e:
            self.last_error = str(e)
            return None

        for m in items:
            if m.get("matchType") and m["matchType"] != "singles":
                continue
            home_name = _norm(m.get("homePlayerName", ""))
            away_name = _norm(m.get("awayPlayerName", ""))
            if home_name and (target in home_name or home_name in target):
                side = "home"
            elif away_name and (target in away_name or away_name in target):
                side = "away"
            else:
                continue

            result = self.score_from_item(m, side)
            if result is None:
                self.last_error = (
                    f"matched '{player_name}' but this match had no 'score' block — "
                    f"run --debug and check")
            return result
        return None

    def score_from_item(self, m: dict, side: str) -> Optional[LiveScore]:
        """Build a LiveScore for one side ('home'/'away') of a raw feed item.

        fetched_at is when the FEED was actually called, not now. It used to
        be time.time(), so cached data always looked 0 seconds old and the
        engine's max_score_age_sec guard could never fire — the whole point
        of that guard is to refuse a trade priced off a stale scoreline."""
        score = m.get("score") or {}
        if "home" not in score or "away" not in score:
            return None
        other = "away" if side == "home" else "home"
        won, lost = _num(score.get(side)), _num(score.get(other))
        title = f"{m.get('homePlayerName', '?')} vs {m.get('awayPlayerName', '?')}"
        fav_side = _opening_favorite(m)
        was_fav = None if fav_side is None else (fav_side == side)
        return LiveScore(sets_won=won, sets_lost=lost, status=str(m.get("status", "")),
                         match_title=title,
                         fetched_at=(self._cached_at or time.time()), raw=m,
                         was_favorite=was_fav)


def _num(v: Any) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _flip_surname_first(name: str) -> str:
    """'Boyer T.' -> 'T. Boyer'. Flashscore puts the surname first; every
    other part of this program assumes the surname is last."""
    m = _SURNAME_FIRST.match(str(name).strip())
    return f"{m.group(2)}. {m.group(1)}" if m else str(name)


def _from_flashscore(items: list[dict]) -> list[dict]:
    """Reshape Flashscore records into the same dict the primary feed
    returns, so nothing downstream needs to know which source was used.

    One real difference: Flashscore carries no odds, so the pre-match
    favourite is inferred from ATP/WTA ranking instead. That is a weaker
    signal than opening odds — it ignores form, surface and injuries."""
    out: list[dict] = []
    for it in items or []:
        if it.get("match_type") and it["match_type"] != "singles":
            continue
        home = (it.get("home_players") or [{}])[0]
        away = (it.get("away_players") or [{}])[0]
        hn, an = home.get("name"), away.get("name")
        if not hn or not an:
            continue
        hs, as_ = it.get("sets_won_home"), it.get("sets_won_away")
        if hs is None or as_ is None:
            continue

        rec = {
            "matchType": "singles",
            "homePlayerName": _flip_surname_first(hn),
            "awayPlayerName": _flip_surname_first(an),
            "score": {"home": _num(hs), "away": _num(as_)},
            "status": it.get("match_status") or "",
            "tournamentName": it.get("tournament_name", ""),
            "surface": it.get("surface", ""),
            "_source": "flashscore",
        }
        # ranking as a favourite proxy: lower number = stronger player
        hr, ar = home.get("ranking"), away.get("ranking")
        if isinstance(hr, int) and isinstance(ar, int) and hr != ar:
            rec["_favorite_side"] = "home" if hr < ar else "away"
        out.append(rec)
    return out


# ----------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--debug", action="store_true", help="dump raw live-match JSON (field names)")
    ap.add_argument("--find", metavar="NAME", help="look up one player's live score")
    ap.add_argument("--max", type=int, default=20, help="max matches to pull")
    args = ap.parse_args()

    client = LiveScoreClient()
    if not client.enabled:
        print("APIFY_TOKEN not set. Get a free token at apify.com and:")
        print("  set APIFY_TOKEN=your-token-here")
        return

    if args.find:
        score = client.find(args.find, max_matches=args.max)
        if score:
            fav = ("unknown" if score.was_favorite is None
                   else ("yes" if score.was_favorite else "no"))
            print(f"\n{score.match_title}")
            print(f"sets: {score.sets_won}-{score.sets_lost}   status: {score.status}   "
                  f"pre-match favorite: {fav}   fetched {score.age_sec}s ago\n")
        else:
            print(f"\nno match found for '{args.find}'"
                  + (f"\n  ({client.last_error})" if client.last_error else "") + "\n")
        return

    # default / --debug: show raw items so field names can be checked
    try:
        items = client.raw(max_matches=args.max)
    except requests.RequestException as e:
        print(f"request failed: {e}")
        return
    print(f"\n{len(items)} live matches returned\n")
    for i, m in enumerate(items[:5]):
        print(f"--- match {i} ---")
        print(json.dumps(m, indent=2, default=str)[:1500])
        print()


if __name__ == "__main__":
    main()
