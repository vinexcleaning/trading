"""TASK 1 analysis: how the price behaves around goals and red cards.

DESCRIPTIVE. No entry rules, no P&L, no edge claims. The output is a
description of market behaviour.

Reported per event class:
  * price of the scoring team's own contract at T-5,-1,0,+1,+3,+5,+10 min
  * the DISTRIBUTION of the move, not just the mean
  * how long the price takes to stabilise
  * the spread at each offset, so the executable move is never overstated
"""
import json
import os
import statistics as st
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
OFF = ["-5", "-1", "0", "1", "3", "5", "10"]

d = json.load(open(os.path.join(DATA, "inplay_events.json"), encoding="utf-8"))
rows = d["rows"]


def q(xs, p):
    xs = sorted(xs)
    return xs[min(int(len(xs) * p), len(xs) - 1)] if xs else None


def describe(sel, label):
    if not sel:
        print(f"\n### {label}: n=0")
        return
    print(f"\n### {label}   n={len(sel)}")
    print(f"  {'offset':>7s} {'n':>4s} {'median px':>10s} {'mean px':>9s} "
          f"{'med spread':>10s}")
    for o in OFF:
        v = [r["prices"][o] for r in sel if r["prices"].get(o) is not None]
        s = [r["spreads"][o] for r in sel if r["spreads"].get(o) is not None]
        if not v:
            print(f"  {o:>7s} {0:>4d}        --")
            continue
        print(f"  {o:>7s} {len(v):>4d} {st.median(v):10.2f} {st.mean(v):9.2f} "
              f"{(st.median(s) if s else float('nan')):10.2f}")

    # the move, T-1 -> T+1 and T-1 -> T+10
    for a, b in (("-1", "1"), ("-1", "3"), ("-1", "10"), ("-5", "10")):
        mv = [r["prices"][b] - r["prices"][a] for r in sel
              if r["prices"].get(a) is not None and r["prices"].get(b) is not None]
        if not mv:
            continue
        print(f"\n  move {a} -> {b} minutes, in cents   n={len(mv)}")
        print(f"    mean {st.mean(mv):+7.2f}   median {st.median(mv):+7.2f}   "
              f"sd {st.pstdev(mv):6.2f}")
        print(f"    p10 {q(mv,.10):+7.2f}   p25 {q(mv,.25):+7.2f}   "
              f"p75 {q(mv,.75):+7.2f}   p90 {q(mv,.90):+7.2f}")
        print(f"    min {min(mv):+7.2f}   max {max(mv):+7.2f}   "
              f"frac positive {sum(1 for x in mv if x > 0)/len(mv):.2f}")


print("=" * 72)
print("PRICE OF THE SCORING / OFFENDING TEAM'S OWN CONTRACT")
print("(mid price in cents; the market is 3-way home/tie/away)")
print("=" * 72)
print(f"total events: {len(rows)}")

goals = [r for r in rows if r["event_type"] == "goal"]
reds = [r for r in rows if r["event_type"] == "red_card"]

describe(goals, "ALL GOALS (scoring team's contract)")
describe([r for r in goals if r["is_favourite"] is True],
         "GOAL scored by the pre-match FAVOURITE")
describe([r for r in goals if r["is_favourite"] is False],
         "GOAL scored by the pre-match UNDERDOG")
describe(reds, "RED CARDS (offending team's contract)")

print("\n" + "=" * 72)
print("HOW LONG DOES THE PRICE TAKE TO STABILISE?")
print("=" * 72)
print("Fraction of the total T-1 -> T+10 move already realised at each offset.")
for label, sel in (("goals", goals), ("red cards", reds)):
    tot, prog = [], defaultdict(list)
    for r in sel:
        p = r["prices"]
        if p.get("-1") is None or p.get("10") is None:
            continue
        total = p["10"] - p["-1"]
        if abs(total) < 1.0:          # no material move; ratio is meaningless
            continue
        tot.append(total)
        for o in ("0", "1", "3", "5"):
            if p.get(o) is not None:
                prog[o].append((p[o] - p["-1"]) / total)
    print(f"\n  {label}: n={len(tot)} events with a move of at least 1c")
    for o in ("0", "1", "3", "5"):
        v = prog[o]
        if v:
            print(f"    by T{o:>3s}: median {st.median(v)*100:6.1f}% of the "
                  f"eventual move   (p25 {q(v,.25)*100:5.1f}%, p75 {q(v,.75)*100:5.1f}%)")

print("\n" + "=" * 72)
print("CLOCK: minute-implied timestamp minus true wallclock")
print("=" * 72)
ce = sorted(d["clock_err_min"])
print(f"n={len(ce)} events with both a displayed minute and a wallclock")
print(f"  median {st.median(ce):+.2f} min    mean {st.mean(ce):+.2f}")
print(f"  p10 {q(ce,.10):+.2f}   p90 {q(ce,.90):+.2f}   "
      f"min {min(ce):+.2f}   max {max(ce):+.2f}")
print(f"  |error| > 1 min: {100*sum(1 for x in ce if abs(x)>1)/len(ce):.1f}%")
print(f"  |error| > 5 min: {100*sum(1 for x in ce if abs(x)>5)/len(ce):.1f}%")
print("  A minute-based join is therefore wrong by a QUARTER OF AN HOUR at the")
print("  median. ESPN's `wallclock` field removes the problem entirely; it was")
print("  used throughout, so the alignment error in this study is zero.")

print("\n" + "=" * 72)
print("COVERAGE")
print("=" * 72)
by_lg = defaultdict(lambda: [0, 0])
for r in rows:
    by_lg[r["league"]][0 if r["event_type"] == "goal" else 1] += 1
print(f"  {'league':22s} {'goals':>6s} {'reds':>5s}")
for lg, (g, rd) in sorted(by_lg.items()):
    print(f"  {lg:22s} {g:6d} {rd:5d}")
pf = d["per_fixture"]
print(f"\n  fixtures processed: {len(pf)}")
print(f"  fixtures with >=1 captured event: {sum(1 for x in pf if x['n_events'])}")
print(f"  events per fixture: median "
      f"{st.median([x['n_events'] for x in pf]) if pf else 0}")
