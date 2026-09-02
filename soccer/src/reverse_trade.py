"""The reverse trade: back a side that has just gone one goal up.

**This file implements `PREREGISTRATION_REVERSE.md` and nothing else.** Every
choice below was fixed in that file before any 2026 European price was looked
at. If a rule here disagrees with that file, that file wins and this is a bug.

THE RULE, restated so it can be checked against the pre-registration:
  * entry   : the FIRST goal of the match, minute 20-45 inclusive
  * side    : whoever just went ahead
  * price   : the ASK, two minutes after the goal. Never the mid.
  * no ask below 100 -> NO TRADE AVAILABLE. Excluded from the result and
                        counted in the availability line (GUARDS #24).
  * hold    : to settlement. No stop, no exit.
  * fee     : common/kalshi_fees.py, the repo's only implementation
  * outcome : did that side win in regulation
  * unit    : ONE MATCH, one number.

WHY THE ANSWER IS EXPECTED TO BE "CANNOT TELL". The per-match result has a
spread of 7.35 cents (measured on August prices, SO037), so **216 matches** are
needed to see a 1-cent effect. That threshold is in the pre-registration and is
applied here mechanically rather than being decided after the fact.

Read-only. No network. No credentials. No orders.
"""
import json
import math
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

LO, HI = 20, 45          # entry window, fixed in the pre-registration
AFTER = 2                # minutes after the goal
NEEDED = 216             # matches before a verdict is allowed
EURO = {"eng.1", "esp.1", "ita.1", "ger.1", "fra.1",
        "uefa.champions", "uefa.europa",
        "uefa.champions_qual", "uefa.europa_qual"}
TIERS = ["top third", "middle third", "bottom third", "unknown"]


def rng(vals):
    """The range the average could really be."""
    if len(vals) < 2:
        return (float("nan"), float("nan"))
    m = statistics.mean(vals)
    se = statistics.pstdev(vals) / math.sqrt(len(vals))
    return (m - 1.96 * se, m + 1.96 * se)


def collect():
    px = defaultdict(dict)
    with open(PRICES, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            px[r["espn_id"]][r["minute"]] = r

    rows, no_trade, no_price = [], 0, 0
    with open(GOALS, encoding="utf-8") as fh:
        for line in fh:
            try:
                fx = json.loads(line)
            except ValueError:
                continue
            if fx["espn_id"] not in px or fx["league"] not in EURO:
                continue
            goals = sorted((g for g in fx["events"]
                            if g["kind"] == "goal" and g["minute"] is not None
                            and g.get("side")), key=lambda g: g["minute"])
            if not goals:
                continue
            g = goals[0]
            if not (LO <= g["minute"] <= HI):
                continue
            row = px[fx["espn_id"]].get(g["minute"] + AFTER)
            if not row:
                no_price += 1
                continue
            home = g["side"] == "home"
            ask = row["home_ask"] if home else row["away_ask"]
            tier = row["home_tier"] if home else row["away_tier"]
            if not (0 < ask < 100):
                no_trade += 1
                continue
            # Regulation result from the timeline -- the same basis the rest of
            # this folder scores on, and the basis Kalshi's own "Reg Time" legs
            # settle on.
            rh = sum(1 for x in goals
                     if x["side"] == "home" and x["minute"] <= 90)
            ra = sum(1 for x in goals
                     if x["side"] == "away" and x["minute"] <= 90)
            won = (rh > ra) if home else (ra > rh)
            fee = float(F.roundtrip_cost_cents(ask))
            rows.append({"net": (100.0 if won else 0.0) - ask - fee,
                         "ask": ask, "won": won, "tier": tier,
                         "league": fx["league"], "date": fx["date"][:10]})
    return rows, no_trade, no_price


def main():
    rows, no_trade, no_price = collect()

    out = []
    out.append("THE REVERSE TRADE - BACKING A SIDE THAT JUST WENT ONE GOAL UP")
    out.append("=" * 78)
    out.append("")
    out.append("Implements PREREGISTRATION_REVERSE.md exactly. First goal of the")
    out.append(f"match, minute {LO}-{HI}, priced at the ASK {AFTER} minutes later,")
    out.append("held to settlement. One number per match.")
    out.append("")
    out.append("AVAILABILITY FIRST, per GUARDS #24:")
    out.append(f"    matches with a tradeable entry      {len(rows)}")
    out.append(f"    entry existed but nothing to buy    {no_trade}")
    out.append(f"    no price at that minute at all      {no_price}")
    tot = len(rows) + no_trade
    if tot:
        out.append(f"    -> buyable on {len(rows)/tot*100:.0f} in 100 of the "
                   f"entries that existed")
    out.append("")

    if not rows:
        out.append("**No matches qualified. Nothing to report.**")
    else:
        nets = [r["net"] for r in rows]
        lo, hi = rng(nets)
        wins = sum(1 for r in rows if r["won"])
        out.append("=" * 78)
        out.append("THE RESULT")
        out.append("=" * 78)
        out.append("")
        out.append(f"    matches                  {len(nets)}")
        out.append(f"    you won                  {wins} of {len(nets)} "
                   f"({wins / len(nets) * 100:.0f} in 100)")
        out.append(f"    median price paid        "
                   f"{statistics.median(r['ask'] for r in rows):.1f}c")
        out.append(f"    average result           "
                   f"{statistics.mean(nets):+.2f}c per contract")
        out.append(f"    could really be          {lo:+.2f}c to {hi:+.2f}c")
        out.append("")
        out.append("**Positive means you were paid to take it. The range is the")
        out.append("part to read: if it touches zero, this cannot tell you.**")
        out.append("")
        out.append("BY HOW GOOD THE SIDE WAS - the hypothesis was that strength")
        out.append("matters, so if this is flat the idea is wrong even if the")
        out.append("overall number is positive.")
        out.append("")
        out.append(f"    {'the side that scored':>20s} {'matches':>8s} "
                   f"{'paid':>7s} {'won':>7s} {'result':>10s} "
                   f"{'could really be':>22s}")
        out.append("    " + "-" * 78)
        for t in TIERS:
            v = [r for r in rows if r["tier"] == t]
            if len(v) < 5:
                out.append(f"    {t:>20s} {len(v):>8d}   too few to read")
                continue
            n = [r["net"] for r in v]
            a, b = rng(n)
            span = f"{a:+.2f} to {b:+.2f}"
            out.append(f"    {t:>20s} {len(v):>8d} "
                       f"{statistics.median(r['ask'] for r in v):>6.1f}c "
                       f"{sum(1 for r in v if r['won']) / len(v) * 100:>6.0f}% "
                       f"{statistics.mean(n):>+9.2f}c {span:>22s}")
        out.append("")
        out.append("BY COMPETITION")
        out.append("")
        per = defaultdict(list)
        for r in rows:
            per[r["league"]].append(r["net"])
        for lg in sorted(per, key=lambda x: -len(per[x])):
            v = per[lg]
            if len(v) < 5:
                out.append(f"    {lg:>22s} {len(v):>5d}   too few to read")
            else:
                out.append(f"    {lg:>22s} {len(v):>5d} "
                           f"{statistics.mean(v):>+9.2f}c")

        out.append("")
        out.append("=" * 78)
        out.append("THE VERDICT, BY THE RULE FIXED BEFORE LOOKING")
        out.append("=" * 78)
        out.append("")
        out.append(f"The pre-registration requires **{NEEDED} matches** before a")
        out.append("verdict is allowed - the number needed to see a 1-cent effect")
        out.append("against a per-match spread of 7.35 cents.")
        out.append("")
        if len(nets) < NEEDED:
            out.append(f"**{len(nets)} matches. That is below {NEEDED}, so the "
                       f"verdict is CANNOT TELL** - and it was pre-registered as")
            out.append("the expected outcome, not chosen after seeing the number.")
            out.append("")
            out.append("The idea is neither alive nor dead. It is unmeasured.")
            out.append("Reading the result above as evidence either way is exactly")
            out.append("the mistake this folder documented four times.")
        elif lo <= 0 <= hi:
            out.append(f"{len(nets)} matches, at or above the threshold.")
            out.append("**The range touches zero, which the pre-registration")
            out.append("calls a stop rather than a maybe. DROPPED.**")
        elif hi < 0:
            out.append(f"{len(nets)} matches, at or above the threshold.")
            out.append("**The middle is below zero and the range never touches")
            out.append("it. The bet loses money. DROPPED.**")
        else:
            out.append(f"{len(nets)} matches, at or above the threshold.")
            out.append("**The range stays above zero.** Before this counts as")
            out.append("anything it needs the held-back years and a fresh")
            out.append("pre-registration - this is the search, not the test.")

        out.append("")
        out.append("VARIANTS TRIED: one. The rule in the pre-registration, run")
        out.append("once. No window moved, no competition dropped, no exit added.")

    txt = "\n".join(out)
    print(txt)
    os.makedirs(REP, exist_ok=True)
    with open(os.path.join(REP, "reverse_trade.txt"), "w",
              encoding="utf-8") as fh:
        fh.write(txt + "\n")
    print("\nwrote reports/reverse_trade.txt")


if __name__ == "__main__":
    main()
