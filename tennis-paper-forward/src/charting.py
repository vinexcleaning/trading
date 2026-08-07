"""charting.py — real point-by-point, for the one brief field the match files
cannot answer honestly.

WHY THIS FILE EXISTS
    "Response after losing serve" is a claim about the sequence of games. A
    Sackmann match row gives you a set score ("6-4 3-6 7-5") and aggregate
    break points; neither tells you what happened in the game AFTER a break.
    The Match Charting Project's points files carry `Gm#`, `Svr` and
    `PtWinner`, so the game sequence reconstructs exactly.

    Source: JeffSackmann/tennis_MatchChartingProject (200, 399 stars,
    pushed 2026-05-25, no LICENSE file - see DECISIONS.md D4).

WHAT IS COMPUTED, AND AGAINST WHAT BENCHMARK
    Three numbers per player, each with its own denominator:

      hold_rate          P(holds a service game)                 - the baseline
      break_rate         P(breaks an opponent service game)      - the baseline
      breakback_rate     P(breaks the opponent's VERY NEXT service game
                           | was just broken)
      hold_after_broken  P(holds their next service game | was just broken)

    `breakback_rate` on its own means nothing: a player who breaks 30% of all
    games and 30% after being broken has no "response" at all. The brief always
    carries the delta against that player's own baseline, because the delta is
    the claim and the raw rate is an advertisement. CLAUDE.md §6.

COVERAGE IS THE LIMIT AND IT IS REPORTED, NOT ASSUMED
    Charting is volunteer work concentrated on main-tour matches. Challenger
    and ITF players will mostly be absent. `Brief` records `charting_matches`
    per player so a bot sees `None` and reasons about the gap instead of
    receiving a fabricated number. GUARDS #21: "I could not tell" is a verdict.
"""

from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from . import safety
from .sackmann import norm_name

DATA = Path(__file__).resolve().parent.parent / "data" / "charting"
MCP = "https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master"

# 2020s only by default: ~89 MB across both tours, and it is the window where
# the players Kalshi lists actually play. Add "2010s" for depth at the cost of
# another ~54 MB.
DEFAULT_ERAS = ("2020s",)


@dataclass
class ServeResponse:
    player: str
    matches: int = 0
    serve_games: int = 0
    holds: int = 0
    return_games: int = 0
    breaks: int = 0
    broken: int = 0                 # times broken (denominator for the below)
    breakback_next: int = 0         # broke opponent's very next service game
    breakback_chances: int = 0      # times a next return game actually existed
    held_after_broken: int = 0
    held_after_broken_chances: int = 0
    # THE MATCHED CONTROL - GUARDS #20, the placebo split.
    # "Broke back after being broken" compared against a player's ALL-GAMES
    # baseline is confounded: the games in which you get broken are the games
    # against opponents who are good enough to break you, and the all-games
    # baseline includes everyone else. So the same two quantities are also
    # measured after a HOLD - same match, same opponent, same day, differing
    # only in what just happened. The broken-vs-held difference is the claim.
    # The against-own-baseline difference is the advertisement.
    breakback_after_hold: int = 0
    breakback_after_hold_chances: int = 0
    held_after_hold: int = 0
    held_after_hold_chances: int = 0

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        hold = self.holds / self.serve_games if self.serve_games else None
        brk = self.breaks / self.return_games if self.return_games else None
        bb = (self.breakback_next / self.breakback_chances
              if self.breakback_chances else None)
        hab = (self.held_after_broken / self.held_after_broken_chances
               if self.held_after_broken_chances else None)
        bb_ctl = (self.breakback_after_hold / self.breakback_after_hold_chances
                  if self.breakback_after_hold_chances else None)
        hh_ctl = (self.held_after_hold / self.held_after_hold_chances
                  if self.held_after_hold_chances else None)
        d.update(
            hold_rate=hold,
            break_rate=brk,
            breakback_rate=bb,
            hold_after_broken=hab,
            break_after_hold=bb_ctl,
            hold_after_hold=hh_ctl,
            # the deltas are the claim; the raw rates are not
            breakback_delta=(bb - brk) if (bb is not None and brk is not None) else None,
            hold_after_broken_delta=(hab - hold) if (hab is not None and hold is not None) else None,
            # ...and these two are the CONTROLLED claim, which is the one to read
            breakback_vs_control=(bb - bb_ctl) if (bb is not None and bb_ctl is not None) else None,
            hold_after_broken_vs_control=(hab - hh_ctl) if (hab is not None and hh_ctl is not None) else None,
        )
        return d


def _download(rel: str, *, refresh: bool = False) -> Path | None:
    p = DATA / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if refresh or not p.exists() or p.stat().st_size == 0:
        text = safety.get(f"{MCP}/{rel}", expect_json=False, timeout=600)
        if text is None:
            return None
        p.write_text(text, encoding="utf-8")
    return p


def _match_players(tour_letter: str, *, refresh: bool = False) -> dict[str, tuple[str, str]]:
    rel = f"charting-{tour_letter}-matches.csv"
    p = _download(rel, refresh=refresh)
    if p is None:
        return {}
    out: dict[str, tuple[str, str]] = {}
    with p.open(encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            mid = (r.get("match_id") or "").strip()
            p1, p2 = (r.get("Player 1") or "").strip(), (r.get("Player 2") or "").strip()
            if mid and p1 and p2:
                out[mid] = (p1, p2)
    if not out:
        raise ValueError(f"{rel} returned content but yielded no matches. GUARDS #13.")
    return out


def _game_sequence(rows: list[dict]) -> list[tuple[int, int]]:
    """Collapse a match's points into [(server, game_winner), ...] in order.

    The last point of a game decides it, and a game boundary is any change in
    (Set1, Set2, Gm#). Tiebreaks are dropped: 'held serve' is not defined in a
    tiebreak, and counting one as a hold or a break would quietly corrupt both
    baselines.
    """
    games: list[tuple[int, int]] = []
    cur_key = None
    cur_svr = None
    last_winner = None
    for r in rows:
        if str(r.get("TbSet", "")).strip().lower() == "true" and str(r.get("Gm#", "")).strip():
            # TbSet marks a set that *will* have a final tiebreak, not the
            # tiebreak itself; the tiebreak game is detected below by Pts.
            pass
        key = (r.get("Set1"), r.get("Set2"), r.get("Gm#"))
        try:
            svr = int(r.get("Svr") or 0)
            win = int(r.get("PtWinner") or 0)
        except (TypeError, ValueError):
            continue
        if svr not in (1, 2) or win not in (1, 2):
            continue
        if cur_key is not None and key != cur_key:
            if cur_svr in (1, 2) and last_winner in (1, 2):
                games.append((cur_svr, last_winner))
        cur_key, cur_svr, last_winner = key, svr, win
    if cur_key is not None and cur_svr in (1, 2) and last_winner in (1, 2):
        games.append((cur_svr, last_winner))
    return games


def _is_tiebreak_game(rows: list[dict]) -> bool:
    """A tiebreak has both players serving inside one Gm#."""
    svrs = {r.get("Svr") for r in rows}
    return len(svrs - {None, ""}) > 1


def build_index(eras: tuple[str, ...] = DEFAULT_ERAS, *, refresh: bool = False,
                verbose: bool = False) -> dict[str, dict[str, Any]]:
    """Build (and cache) the per-player serve/response index.

    The cache key includes the eras, so asking for a wider window rebuilds
    rather than silently returning the narrow one.
    """
    DATA.mkdir(parents=True, exist_ok=True)
    cache = DATA / f"serve_response__{'_'.join(eras)}.json"
    if cache.exists() and not refresh:
        return json.loads(cache.read_text(encoding="utf-8"))

    acc: dict[str, ServeResponse] = {}

    def rec(name: str) -> ServeResponse:
        k = norm_name(name)
        if k not in acc:
            acc[k] = ServeResponse(player=name)
        return acc[k]

    for letter in ("m", "w"):
        players = _match_players(letter, refresh=refresh)
        if not players:
            continue
        for era in eras:
            rel = f"charting-{letter}-points-{era}.csv"
            p = _download(rel, refresh=refresh)
            if p is None:
                continue
            if verbose:
                print(f"  indexing {rel} ({p.stat().st_size/1e6:.0f} MB)")
            with p.open(encoding="utf-8", errors="replace", newline="") as fh:
                cur_mid = None
                buf: list[dict] = []
                for r in csv.DictReader(fh):
                    mid = (r.get("match_id") or "").strip()
                    if mid != cur_mid:
                        if cur_mid and buf:
                            _absorb(cur_mid, buf, players, rec)
                        cur_mid, buf = mid, []
                    buf.append(r)
                if cur_mid and buf:
                    _absorb(cur_mid, buf, players, rec)

    out = {k: v.as_dict() for k, v in acc.items()}
    cache.write_text(json.dumps(out), encoding="utf-8")
    if verbose:
        print(f"  {len(out)} players indexed -> {cache.name}")
    return out


def _absorb(mid: str, rows: list[dict], players: dict[str, tuple[str, str]],
            rec) -> None:
    pair = players.get(mid)
    if not pair:
        return
    # drop tiebreak games before sequencing
    by_game: dict[tuple, list[dict]] = defaultdict(list)
    order: list[tuple] = []
    for r in rows:
        k = (r.get("Set1"), r.get("Set2"), r.get("Gm#"))
        if k not in by_game:
            order.append(k)
        by_game[k].append(r)
    clean: list[dict] = []
    for k in order:
        if not _is_tiebreak_game(by_game[k]):
            clean.extend(by_game[k])
    games = _game_sequence(clean)
    if len(games) < 6:
        return

    r1, r2 = rec(pair[0]), rec(pair[1])
    recs = {1: r1, 2: r2}
    for r in recs.values():
        r.matches += 1

    for i, (svr, win) in enumerate(games):
        ret = 2 if svr == 1 else 1
        recs[svr].serve_games += 1
        recs[ret].return_games += 1
        # The server's very next RETURN game and very next SERVICE game are
        # located identically whether the game was held or lost. Only the
        # counter they land in differs - that is what makes it a matched
        # control rather than two separate measurements.
        nxt_ret = next((j for j in range(i + 1, len(games))
                        if games[j][0] == ret), None)
        nxt_sv = next((j for j in range(i + 1, len(games))
                       if games[j][0] == svr), None)

        if win == svr:
            recs[svr].holds += 1
            if nxt_ret is not None:
                recs[svr].breakback_after_hold_chances += 1
                if games[nxt_ret][1] == svr:
                    recs[svr].breakback_after_hold += 1
            if nxt_sv is not None:
                recs[svr].held_after_hold_chances += 1
                if games[nxt_sv][1] == svr:
                    recs[svr].held_after_hold += 1
        else:
            recs[ret].breaks += 1
            recs[svr].broken += 1
            if nxt_ret is not None:
                recs[svr].breakback_chances += 1
                if games[nxt_ret][1] == svr:
                    recs[svr].breakback_next += 1
            if nxt_sv is not None:
                recs[svr].held_after_broken_chances += 1
                if games[nxt_sv][1] == svr:
                    recs[svr].held_after_broken += 1


_IDX: dict[str, dict[str, Any]] | None = None


def lookup(name: str, eras: tuple[str, ...] = DEFAULT_ERAS) -> dict[str, Any] | None:
    global _IDX
    if _IDX is None:
        _IDX = build_index(eras)
    return _IDX.get(norm_name(name))
