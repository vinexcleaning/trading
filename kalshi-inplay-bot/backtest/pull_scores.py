"""
pull_scores.py — fetch historical Sofascore scores and align them to Kalshi.

This is what makes the real strategy testable. Kalshi candles have prices and
no score; Sofascore has the score and no prices. Joining them gives, for the
first time, "what was the set score when the price was X".

TIMING — the part that decides whether this is worth anything
    Sofascore does not publish when each set ENDED, but it publishes enough to
    reconstruct it closely:
        startTimestamp              when the match began
        time.period1, period2, ...  duration of each set, in seconds
        currentPeriodStartTimestamp when the LAST set began
        point-by-point              how many games were in each set
    Knowing the last set's start pins down the total of all earlier sets plus
    their breaks, so the accumulated gap can be distributed rather than
    guessed. That gets set boundaries to a couple of minutes instead of the
    ten-to-fifteen I first estimated.

    Anything finer than a set boundary is interpolation and is flagged as such.

BE POLITE
    One match needs 2-3 requests. There are thousands. This sleeps between
    calls, caches everything, and can be stopped and resumed at any time —
    delete nothing and just run it again.
"""

from __future__ import annotations

import json
import os
import pickle
import sys
import time
from typing import Optional

import pandas as pd
from curl_cffi import requests as cr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from autoscan import _name_matches, subject_player      # noqa: E402

B = "https://www.sofascore.com/api/v1"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data",
                   "sofascore_matches.jsonl")
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data",
                     "sofascore_cache.json")
PAUSE = 0.7          # seconds between requests


def get(path: str, tries: int = 3) -> Optional[dict]:
    for i in range(tries):
        try:
            r = cr.get(B + path, impersonate="chrome", timeout=25)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                time.sleep(20 * (i + 1))     # backed off, not hammering
                continue
        except Exception:
            pass
        time.sleep(2 * (i + 1))
    return None


def set_boundaries(ev: dict) -> list[dict]:
    """Reconstruct when each set started and ended, in unix seconds."""
    t = ev.get("time") or {}
    start = ev.get("startTimestamp")
    if not start:
        return []
    durs = [(i, t.get(f"period{i}")) for i in range(1, 6)]
    durs = [(i, d) for i, d in durs if d]
    if not durs:
        return []

    last_start = t.get("currentPeriodStartTimestamp") or ev.get(
        "currentPeriodStartTimestamp")
    # Total dead time (warm-up + changeovers) between the match start and the
    # final set, spread evenly across the gaps rather than assumed away.
    gap = 0.0
    if last_start and len(durs) > 1:
        played_before = sum(d for _, d in durs[:-1])
        slack = last_start - start - played_before
        if 0 <= slack < 3600:
            gap = slack / max(1, len(durs) - 1)

    out, clock = [], float(start)
    for n, (idx, d) in enumerate(durs):
        if n:
            clock += gap
        out.append({"set": idx, "start_ts": int(clock),
                    "end_ts": int(clock + d), "duration_s": int(d),
                    "gap_model_s": int(gap)})
        clock += d
    return out


def main() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    _, markets = pickle.load(open("data/views.pkl", "rb"))
    # One row per MATCH, not per market — the two sides are the same event.
    md = markets.drop_duplicates("event_ticker").copy()
    only = sys.argv[1] if len(sys.argv) > 1 else "ATP,WTA,Challenger"
    keep = [x.strip() for x in only.split(",")]
    md = md[md.tournament.isin(keep)]
    print(f"{len(md)} matches to look up ({', '.join(keep)})")

    cache = {}
    if os.path.exists(CACHE):
        cache = json.load(open(CACHE, encoding="utf-8"))
    done = set()
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["event"])
                except Exception:
                    pass
    print(f"{len(done)} already fetched, resuming\n")

    found = miss = 0
    for k, (_, m) in enumerate(md.iterrows(), 1):
        if m.event_ticker in done:
            continue
        player = subject_player(m.title) or m.player
        surname = player.split()[-1] if player else ""
        if not surname:
            continue

        # 1) find the player
        if surname not in cache:
            res = get(f"/search/all?q={surname}&page=0") or {}
            cache[surname] = [
                {"id": (r.get("entity") or {}).get("id"),
                 "name": (r.get("entity") or {}).get("name")}
                for r in (res.get("results") or [])
                if r.get("type") == "team"][:5]
            time.sleep(PAUSE)
        cands = [c for c in cache[surname]
                 if c.get("name") and _name_matches(player, c["name"])]

        # 2) find their match on the right day
        rec = None
        for c in cands[:2]:
            evs = get(f"/team/{c['id']}/events/last/0") or {}
            time.sleep(PAUSE)
            for e in (evs.get("events") or []):
                if abs(e.get("startTimestamp", 0) - m.open_ts) > 36 * 3600:
                    continue
                det = (get(f"/event/{e['id']}") or {}).get("event")
                time.sleep(PAUSE)
                if not det:
                    continue
                hs, as_ = det.get("homeScore") or {}, det.get("awayScore") or {}
                rec = {
                    "event": m.event_ticker, "ticker": m.ticker,
                    "kalshi_player": player, "tournament": m.tournament,
                    "sofa_event_id": e["id"],
                    "home": (det.get("homeTeam") or {}).get("name"),
                    "away": (det.get("awayTeam") or {}).get("name"),
                    "start_ts": det.get("startTimestamp"),
                    "winner_code": det.get("winnerCode"),
                    "first_to_serve": det.get("firstToServe"),
                    "sets": {f"set{i}": {"home": hs.get(f"period{i}"),
                                         "away": as_.get(f"period{i}")}
                             for i in range(1, 6)
                             if hs.get(f"period{i}") is not None},
                    "boundaries": set_boundaries(det),
                }
                break
            if rec:
                break

        if rec:
            with open(OUT, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            found += 1
        else:
            miss += 1

        if k % 25 == 0:
            json.dump(cache, open(CACHE, "w", encoding="utf-8"))
            print(f"  {k}/{len(md)}  found {found}  missed {miss}", flush=True)

    json.dump(cache, open(CACHE, "w", encoding="utf-8"))
    print(f"\nDONE. {found} matched, {miss} not found -> {OUT}")


if __name__ == "__main__":
    main()
