"""Two ways the +51s window could still be my own artefact.

1. WRONG EVENT TIME. I used `about.startTime`, which is when the AT-BAT
   started, not when the run scored. An at-bat routinely lasts 30-60 seconds
   -- several pitches, then the hit. If the run actually crosses at `endTime`,
   most of the apparent lag is just the at-bat itself. This is the likely
   explanation and it is checked first.

2. WRONG THRESHOLD. "First trade at a clearly-moved price" used
   max(base+15, 80). If the price walks 50 -> 60 -> 70 -> 80, that measures
   time-to-fully-repriced, not time-to-first-reaction. The tradeable window is
   bounded by when the price STARTS moving, so several thresholds are measured.

Reports the lag from BOTH timestamps at SEVERAL thresholds. The honest number
is the one from `endTime` at the smallest threshold.
"""
import glob
import json
import os
import re
import statistics as st
from collections import defaultdict
from datetime import datetime, timedelta

ROOT = os.path.join(os.path.dirname(__file__), "..")
TAPE = os.path.join(ROOT, "..", "market-selection", "data", "tape_pmxt_window")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")

rows = json.load(open(os.path.join(REP, "inplay_rfi_latency.json"),
                      encoding="utf-8"))
want = {r["ticker"]: r for r in rows}

# recover start AND end for each event, keyed by game_pk
ends = {}
with open(os.path.join(DATA, "window_plays.jsonl"), encoding="utf-8") as fh:
    for line in fh:
        try:
            g = json.loads(line)
        except ValueError:
            continue
        first = sorted([p for p in g.get("scoring_plays", [])
                        if p.get("inning") == 1], key=lambda p: p["start"])
        if first:
            ends[g["pk"]] = (first[0]["start"], first[0].get("end"),
                             first[0].get("event"))

tr = defaultdict(list)
for f in sorted(glob.glob(os.path.join(TAPE, "trades_*.jsonl"))):
    with open(f, encoding="utf-8") as fh:
        for line in fh:
            if "KXMLBRFI" not in line:
                continue
            try:
                t = json.loads(line)
            except ValueError:
                continue
            tk = t.get("ticker")
            if tk not in want:
                continue
            try:
                ts = datetime.fromisoformat(
                    t["created_time"].replace("Z", "+00:00"))
                px = float(t["yes_price_dollars"]) * 100
                cnt = float(t.get("count_fp") or 0)
            except (KeyError, ValueError, TypeError):
                continue
            tr[tk].append((ts, px, cnt))
print(f"{sum(len(v) for v in tr.values()):,} trades, {len(tr)} markets")

THRESH = [3, 5, 10, 15, 25]
res = {("start", t): [] for t in THRESH}
res.update({("end", t): [] for t in THRESH})
atbat = []
usable = 0
for tk, xs in tr.items():
    r = want[tk]
    pk = r["game_pk"]
    if pk not in ends:
        continue
    s_, e_, ev = ends[pk]
    if not e_:
        continue
    ts_ = datetime.fromisoformat(s_.replace("Z", "+00:00"))
    te_ = datetime.fromisoformat(e_.replace("Z", "+00:00"))
    atbat.append((te_ - ts_).total_seconds())
    xs.sort()
    base = r["base_px"]
    if base is None or base > 85:
        continue
    usable += 1
    for label, t0 in (("start", ts_), ("end", te_)):
        post = [x for x in xs if x[0] >= t0]
        for th in THRESH:
            hit = next((x for x in post if x[1] >= base + th), None)
            if hit:
                lag = (hit[0] - t0).total_seconds()
                if -60 <= lag <= 900:
                    res[(label, th)].append(lag)

print(f"\nusable events: {usable}")
ab = sorted(atbat)
print(f"\n=== HOW LONG IS THE AT-BAT ITSELF? (endTime - startTime) ===")
print(f"  n={len(ab)}  median {st.median(ab):.1f}s  p25 {ab[int(len(ab)*.25)]:.1f}"
      f"  p75 {ab[int(len(ab)*.75)]:.1f}  max {ab[-1]:.1f}")
print("  ^ any lag measured from startTime includes this by construction")

print(f"\n=== LAG TO FIRST TRADE ABOVE base + N cents ===")
print(f"  {'thresh':>7s} | {'from startTime':>28s} | {'from endTime':>28s}")
print(f"  {'':>7s} | {'n':>4s} {'median':>8s} {'p25':>7s} {'p75':>7s} | "
      f"{'n':>4s} {'median':>8s} {'p25':>7s} {'p75':>7s}")
for th in THRESH:
    out = [f"  +{th:<6d} |"]
    for label in ("start", "end"):
        v = sorted(res[(label, th)])
        if v:
            out.append(f" {len(v):>4d} {st.median(v):>+8.1f} "
                       f"{v[int(len(v)*.25)]:>+7.1f} {v[int(len(v)*.75)]:>+7.1f} |")
        else:
            out.append(f" {0:>4d} {'--':>8s} {'--':>7s} {'--':>7s} |")
    print("".join(out))

v5 = sorted(res[("end", 5)])
if v5:
    neg = sum(1 for x in v5 if x < 0)
    print(f"\n=== THE HONEST NUMBER: +5c move, measured from endTime ===")
    print(f"  n={len(v5)}  median {st.median(v5):+.1f}s")
    print(f"  events where the market moved BEFORE the play ended: "
          f"{neg} of {len(v5)} ({100*neg/len(v5):.0f}%)")
    for s in (0, 1, 2, 5, 10, 30):
        print(f"    within {s:>2d}s: {sum(1 for x in v5 if x <= s)} of {len(v5)}")
    print("\n  A retail order needs seconds. If the median here is under ~5s,")
    print("  the window is not reachable and the idea is dead.")

json.dump({f"{k[0]}_{k[1]}": sorted(v) for k, v in res.items()},
          open(os.path.join(REP, "latency_refine.json"), "w"), indent=1)
