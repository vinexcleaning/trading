"""Mailbox 009 part 3: the match minute, via Pinnacle's live flag.

`close_time` on a live Kalshi soccer market is the match date plus ~72 hours --
the same placeholder trap as MLB (LEDGER BH012) -- and **soccer is worse than
MLB, because the ticker carries only a DATE and no kick-off time**. So the match
minute is not recoverable from anything Kalshi publishes.

The route, which the recorder already stores both halves of:

  * `pin_matchup.starts_utc` -- Pinnacle's scheduled kick-off, to the minute
  * `pin_matchup.live`       -- 1 while the match is actually in play

Join Kalshi's soccer markets to Pinnacle's matchups on team names + date, then
minute = (kalshi snapshot time - pinnacle kick-off).

WHY THIS IS THE WHOLE THING: without it, "buying NO at 97c in the last 20
minutes" cannot be distinguished from "buying NO at 97c three days before
kick-off on a market nobody has looked at yet". Those are completely different
trades and the second one is not the bet.

Read-only against the recorder. No API calls.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT.parent / "bot-hunt" / "data" / "record.db"
REP = ROOT / "reports"
TS = "%Y-%m-%dT%H:%M:%SZ"
SOCCER = ("KXLIGAMXGAME", "KXARGPREMDIVGAME", "KXDIMAYORGAME",
          "KXCOPADOBRASILGAME", "KXBRASILEIROGAME", "KXUCLGAME", "KXEPLGAME")
STOP = re.compile(r"\b(fc|cf|sc|ac|club|de|do|da|el|la|los|the|cd|ca|afc|"
                  r"united|city)\b")


def norm(s):
    if not s:
        return ""
    s = STOP.sub(" ", s.lower())
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", s).split())


def main() -> None:
    REP.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=300)

    # ---- Pinnacle soccer: kick-off and the live window, per matchup
    meta, live_span = {}, {}
    for mid, lg, h, a, st in con.execute(
            "select matchup_id, max(league), max(home), max(away), "
            "max(starts_utc) from pin_matchup where sport='soccer' "
            "group by matchup_id"):
        if h and a and st:
            meta[mid] = {"league": lg, "home": h, "away": a, "starts": st}
    for mid, lo, hi in con.execute(
            "select matchup_id, min(ts_utc), max(ts_utc) from pin_matchup "
            "where sport='soccer' and live=1 group by matchup_id"):
        live_span[mid] = (lo, hi)
    print(f"Pinnacle soccer matchups with names + kick-off : {len(meta):,}")
    print(f"   of which seen LIVE at least once            : {len(live_span):,}")

    # how long does Pinnacle keep a match flagged live? sanity on the clock
    durs = []
    for mid, (lo, hi) in live_span.items():
        if mid not in meta:
            continue
        try:
            d = (datetime.strptime(hi, TS) - datetime.strptime(lo, TS)).total_seconds() / 60
            if 0 < d < 400:
                durs.append(d)
        except ValueError:
            pass
    if durs:
        print(f"   live-flag duration: median {np.median(durs):.0f} min "
              f"(a real match is ~95-115 with stoppage and half time)")

    # ---- Kalshi soccer names
    kn = defaultdict(list)
    for tk, ev, sub, series in con.execute(
            f"select ticker, event_ticker, yes_sub_title, series from k_names "
            f"where series in ({','.join('?'*len(SOCCER))})", SOCCER):
        if sub:
            kn[ev].append((tk, sub, series))
    print(f"Kalshi soccer events with outcome names        : {len(kn):,}")

    # ---- join: both team names must appear among the event's outcomes
    pairs, drops = [], defaultdict(int)
    used = set()
    for ev, tks in kn.items():
        names = {norm(s) for _, s, _ in tks}
        hit = None
        for mid, m in meta.items():
            if mid in used:
                continue
            h, a = norm(m["home"]), norm(m["away"])
            if not h or not a:
                continue
            okh = any(n and (n == h or (len(n) >= 4 and (n in h or h in n)))
                      for n in names)
            oka = any(n and (n == a or (len(n) >= 4 and (n in a or a in n)))
                      for n in names)
            if okh and oka:
                hit = mid
                break
        if hit is None:
            drops["no_pinnacle_match"] += 1
            continue
        used.add(hit)
        pairs.append((ev, hit, tks))
    print(f"JOINED Kalshi event -> Pinnacle matchup        : {len(pairs):,}"
          f"   (unmatched {drops['no_pinnacle_match']:,})")
    if not pairs:
        print("\nnothing joined - the name join needs work before the minute "
              "question can be answered")
        return

    # ---- the book, bucketed by MATCH MINUTE
    buckets = defaultdict(list)
    for ev, mid, tks in pairs:
        try:
            ko = datetime.strptime(meta[mid]["starts"], TS).replace(
                tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        for tk, _s, _series in tks:
            for ts, yb, ya, bs in con.execute(
                    "select ts_utc, yes_bid_c, yes_ask_c, bid_size from k_book "
                    "where ticker=? and yes_bid_c is not null "
                    "and yes_ask_c is not null", (tk,)):
                t = datetime.strptime(ts, TS).replace(tzinfo=timezone.utc)
                mins = (t - ko).total_seconds() / 60.0
                if mins < -60 or mins > 130:
                    continue
                lab = ("before kick-off" if mins < 0 else
                       "0-45 first half" if mins < 45 else
                       "45-70" if mins < 70 else
                       "70-90 THE BET" if mins < 90 else "90+ stoppage")
                buckets[lab].append((yb, ya, bs or 0))
    con.close()

    order = ["before kick-off", "0-45 first half", "45-70", "70-90 THE BET",
             "90+ stoppage"]
    print(f"\n== THE BOOK BY MATCH MINUTE  (buying NO at 90c+ means yes_bid<=10)")
    print(f"   {'window':18} {'snapshots':>10} {'quoted 96-98c':>14} "
          f"{'spread med':>11} {'size med':>10}")
    out = {}
    for lab in order:
        v = buckets.get(lab) or []
        if not v:
            print(f"   {lab:18} {'0':>10}   nothing recorded")
            continue
        yb = np.array([x[0] for x in v], float)
        ya = np.array([x[1] for x in v], float)
        bs = np.array([x[2] for x in v], float)
        m = (100 - yb >= 96) & (100 - yb <= 98)
        print(f"   {lab:18} {len(v):>10,} {int(m.sum()):>14,} "
              f"{np.median(ya-yb):>10.1f}c "
              f"{(np.median(bs[m]) if m.any() else 0):>9,.0f}")
        out[lab] = {"snapshots": len(v), "quoted_96_98": int(m.sum()),
                    "spread_median_c": float(np.median(ya - yb)),
                    "size_median_at_97": float(np.median(bs[m])) if m.any() else 0.0}

    (REP / "soccer_match_minute.json").write_text(
        json.dumps({"joined": len(pairs), "buckets": out}, indent=1),
        encoding="utf-8")
    print("\nwrote reports/soccer_match_minute.json")


if __name__ == "__main__":
    main()
