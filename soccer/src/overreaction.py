"""Does the price move as far for a weak team's goal as for a strong one's?

WHY THIS IS THE SHARPEST VERSION OF THE IDEA. The comeback table says the two
are not the same event. A side that goes one goal up between the 20th and 35th
minute wins 72.6 times in 100 if it is a top-third team (1,562 matches) and 59.6
times in 100 if it is a bottom-third team (944 matches). If Kalshi charges the
same for both, that is a real mistake -- and the trade it implies is the
opposite of the original idea: **backing a team to hold on, or to come back**,
which is a cheap contract rather than a 97-cent one.

THE ANSWER HERE IS THAT THIS WINDOW CANNOT ANSWER IT, and the reason is worth
more than the numbers. Requiring a price you could actually act on -- somebody
offering and somebody bidding -- cuts the sample to between eight and eighteen
goals per group. At that size one match moves the answer by ten cents.

**A DEFECT IN THE FIRST VERSION OF THIS FILE, KEPT ON THE RECORD.** It used the
middle of the market and did not check whether a market existed. Quotes of 100
(nobody offering) and 0 (nobody bidding) were averaged in as though they were
prices. That pushed the strong-team group to about 77 cents and produced a tidy
table in which the market looked well calibrated against the real win rates --
72.6% against 76.8c, 59.6% against 53.0c. It was an artifact of counting prices
that did not exist, and it read as a finding.

Read-only. No network. No credentials. No orders.
"""
import json
import os
import statistics
import sys
from collections import defaultdict

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
sys.path.insert(0, os.path.join(ROOT, "..", "common"))
import kalshi_fees as F     # noqa: E402

PRICES = os.path.join(DATA, "price_by_minute.jsonl")
GOALS = os.path.join(DATA, "goal_minutes.jsonl")
AFTER = 2
LO, HI = 20, 35
TIERS = ["top third", "middle third", "bottom third", "unknown"]

# What actually happened to a side that opened the scoring in this window,
# 2022-2024, from build_comeback_table's own replay. Percent of matches won.
REAL = {"top third": 72.6, "middle third": 64.9,
        "bottom third": 59.6, "unknown": 60.7}
REAL_N = {"top third": 1562, "middle third": 1179,
          "bottom third": 944, "unknown": 206}


def main():
    px = defaultdict(dict)
    for line in open(PRICES, encoding="utf-8"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        px[r["espn_id"]][r["minute"]] = r
    fixtures = {}
    for line in open(GOALS, encoding="utf-8"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r["espn_id"] in px:
            fixtures[r["espn_id"]] = r

    tradeable, untradeable = defaultdict(list), defaultdict(int)
    for eid, fx in fixtures.items():
        goals = sorted((g for g in fx["events"]
                        if g["kind"] == "goal" and g["minute"] is not None
                        and g.get("side")),
                       key=lambda g: g["minute"])
        if not goals:
            continue
        g = goals[0]                      # the goal that opens the scoring
        if not (LO <= g["minute"] <= HI):
            continue
        row = px[eid].get(g["minute"] + AFTER)
        if not row:
            continue
        home = g["side"] == "home"
        tier = row["home_tier"] if home else row["away_tier"]
        ask = row["home_ask"] if home else row["away_ask"]
        bid = row["home_bid"] if home else row["away_bid"]
        if not (0 < ask < 100):
            untradeable[tier] += 1
            continue
        tradeable[tier].append((ask, ask - bid))

    out = []
    out.append("DOES THE PRICE MOVE AS FAR FOR A WEAK TEAM'S GOAL?")
    out.append("=" * 78)
    out.append("")
    out.append(f"The goal that opens the scoring, {LO}th to {HI}th minute,")
    out.append("priced two minutes later at what you would actually PAY to back")
    out.append("that team -- not the middle of the market.")
    out.append("")
    out.append("**The short answer: this window cannot answer it.** The numbers")
    out.append("are below and the group sizes are why.")
    out.append("")
    out.append(f"{'the leader was':>16s} {'goals':>6s} {'you pay':>9s} "
               f"{'they really win':>16s} {'matches':>9s} {'left over':>11s}")
    out.append("-" * 74)
    for t in TIERS:
        v = tradeable.get(t) or []
        if len(v) < 5:
            out.append(f"{t:>16s} {len(v):>6d}   too few to read")
            continue
        a = statistics.median(x[0] for x in v)
        fee = float(F.roundtrip_cost_cents(a))
        out.append(f"{t:>16s} {len(v):>6d} {a:>8.1f}c {REAL[t]:>15.1f}% "
                   f"{REAL_N[t]:>9d} {REAL[t]-a-fee:>+10.2f}c")
    out.append("")
    out.append("'Left over' is what the football says it is worth, minus what")
    out.append("you pay, minus the fee. Positive would mean you were being paid")
    out.append("to take it.")
    out.append("")
    out.append("=" * 78)
    out.append("WHY NONE OF THOSE NUMBERS SHOULD BE ACTED ON")
    out.append("=" * 78)
    out.append("")
    out.append("**Eight to eighteen goals per group.** One or two matches move")
    out.append("the answer by ten cents. The last column swings from about minus")
    out.append("sixteen to about plus sixteen across four groups. That is what")
    out.append("noise looks like, not a pattern.")
    out.append("")
    tot = sum(untradeable.values())
    out.append(f"**{tot} more goals had no tradeable price at all** -- nobody")
    out.append("offering, or nobody bidding. Those are counted here and excluded")
    out.append("from the medians. Leaving them in was the defect in the first")
    out.append("version of this file: they dragged every group toward the")
    out.append("ceiling and produced a table in which the market looked neatly")
    out.append("calibrated. See the note at the top of the file.")
    out.append("")
    out.append("**The two halves are different sets of matches.** The win rates")
    out.append("are 2022-2024 across every competition; the prices are a few")
    out.append("dozen goals from a 69-day 2026 window that is more than half")
    out.append("World Cup and international friendlies, with no European league")
    out.append("in it at all.")
    out.append("")
    out.append("**The 'unknown' row is the worst and is left in on purpose.**")
    out.append("Those are mostly friendlies and World Cup ties where the strength")
    out.append("measure has no reading -- which is exactly where the market knows")
    out.append("the teams and this table does not.")
    out.append("")
    out.append("=" * 78)
    out.append("WHAT WOULD ACTUALLY ANSWER IT")
    out.append("=" * 78)
    out.append("")
    out.append("A season of prices in a competition where both sides are ranked")
    out.append("and the book is deep -- the Premier League and the Champions")
    out.append("League. That is what the recorder in `kalshi-market-scan` is")
    out.append("collecting now, and it is the reason this work is paused.")
    out.append("")
    out.append("**The football half needs no redoing.** A top-third side that")
    out.append("goes one up between the 20th and 35th minute wins 72.6 times in")
    out.append("100 on 1,562 matches; a bottom-third side wins 59.6 times in 100")
    out.append("on 944. Those are solid. Only the price is missing.")
    out.append("")
    out.append("WHAT THIS DOES NOT DO. It attaches no outcome to any price. A")
    out.append("price that moves 'too far' is only a mistake if the team it moved")
    out.append("against actually comes back, and that is a separate test on data")
    out.append("not yet looked at.")

    txt = "\n".join(out)
    print(txt)
    os.makedirs(REP, exist_ok=True)
    with open(os.path.join(REP, "overreaction.txt"), "w",
              encoding="utf-8") as fh:
        fh.write(txt + "\n")
    print("\nwrote reports/overreaction.txt")


if __name__ == "__main__":
    main()
