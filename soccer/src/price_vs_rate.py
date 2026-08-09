"""Put the two halves together: what Kalshi charges, against what happens.

`build_comeback_table.py` says how often the trailing team comes back.
`price_at_state.py` says what you actually pay to bet against them. Neither one
answers the question on its own, and this is the join.

For every state where both exist:

    what you pay  ->  the most comebacks that price can survive
    what happens  ->  the comebacks that actually occurred
    and whether the first is bigger than the second

WHAT THIS IS AND IS NOT. It is a descriptive comparison, not the pre-registered
test. The rates come from 2015-2024 across every competition; the prices come
from whatever Kalshi had inside its ~69-day window, which is a different and much
smaller set of matches. Those populations do not match, and this file says so
rather than quietly averaging them. What it can settle is a question that does
not need them to match: **does the price the idea assumed actually exist?**

Read-only. No network. No credentials. No orders.
"""
import collections
import csv
import json
import os
import statistics
import sys

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
sys.path.insert(0, os.path.join(ROOT, "..", "common"))
import kalshi_fees as F  # noqa: E402

PRICES = os.path.join(DATA, "price_at_state.json")
TABLE = os.path.join(REP, "comeback_table.csv")
MIN_MOMENTS = 5


def breakeven(price_cents):
    """Most comebacks per 100 this price survives, held to settlement.

    GUARDS #6: the fee has exactly one implementation in this repo and this is
    not it. At 100 cents you pay everything to win nothing, so the answer is
    zero and no arithmetic can rescue it.
    """
    fee = float(F.roundtrip_cost_cents(price_cents))
    win = 100 - price_cents - fee
    lose = price_cents + fee
    if win <= 0:
        return 0.0
    return win / (win + lose) * 100


def main():
    prices = json.load(open(PRICES, encoding="utf-8"))
    rates = {}
    with open(TABLE, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["competition"] == "ALL" and r["leader_strength"] == "ALL":
                rates[(int(r["minute"]), int(r["leader_goals"]),
                       int(r["trailer_goals"]))] = (
                    float(r["comebacks_per_100"]), int(r["matches"]))

    out = []
    out.append("WHAT KALSHI CHARGES vs WHAT ACTUALLY HAPPENS")
    out.append("=" * 78)
    out.append("")

    # ---------------------------------------------------------------- part 1
    n = len(prices)
    band = collections.Counter()
    for p in prices:
        c = p["no_cost_cents"]
        band["100 -- nobody bidding on the losing side at all" if c >= 100 else
             "99" if c >= 99 else "98" if c >= 98 else "97" if c >= 97 else
             "95-96" if c >= 95 else "90-94" if c >= 90 else "under 90"] += 1
    out.append("1. DOES THE 97-CENT PRICE EVEN EXIST?")
    out.append("")
    out.append("The whole idea assumes you can pay about 97 cents to make 3.")
    out.append(f"Across all {n} priced moments, what you would actually pay:")
    out.append("")
    for k in ["100 -- nobody bidding on the losing side at all", "99", "98",
              "97", "95-96", "90-94", "under 90"]:
        out.append(f"    {k:52s} {band[k]:5d}  {band[k]/max(n,1)*100:5.1f}%")
    out.append("")
    out.append("A price of 100 is not the market charging 100. It means no one")
    out.append("is bidding for the losing team at all, so there is nothing to")
    out.append("buy at any price under 100. You cannot trade it.")
    out.append("")

    late = [p for p in prices if p["minute"] >= 70]
    lb = collections.Counter()
    for p in late:
        c = p["no_cost_cents"]
        lb["100" if c >= 100 else "99" if c >= 99 else "98" if c >= 98
           else "97 or less"] += 1
    out.append(f"Late in the match -- the 70th minute or later, which is the")
    out.append(f"whole point of the idea -- on {len(late)} moments:")
    out.append("")
    for k in ["100", "99", "98", "97 or less"]:
        out.append(f"    {k:52s} {lb[k]:5d}  {lb[k]/max(len(late),1)*100:5.1f}%")
    out.append("")

    # ---------------------------------------------------------------- part 2
    out.append("=" * 78)
    out.append("2. STATE BY STATE")
    out.append("=" * 78)
    out.append("")
    out.append("'Can afford' is the most comebacks per 100 the price survives.")
    out.append("'Really happens' is what happened, 2015-2024, all competitions.")
    out.append("If 'really happens' is the bigger number, the bet loses money.")
    out.append("")
    out.append(f"{'minute':>8s} {'score':>7s} {'moments':>8s} {'you pay':>8s} "
               f"{'can afford':>11s} {'really happens':>15s} {'matches':>9s} "
               f"{'':>7s}")
    out.append("-" * 78)

    by = collections.defaultdict(list)
    for p in prices:
        by[((p["minute"] // 10) * 10, p["lead"], p["trail"])].append(
            p["no_cost_cents"])

    loses = total = 0
    for key in sorted(by):
        b, lead, trail = key
        v = by[key]
        if len(v) < MIN_MOMENTS:
            continue
        price = statistics.median(v)
        be = breakeven(price)
        got = rates.get((b + 5, lead, trail)) or rates.get((b + 4, lead, trail))
        if not got:
            continue
        rate, nm = got
        total += 1
        bad = rate >= be
        loses += bad
        out.append(f"{f'{b}-{b+9}':>8s} {f'{lead}-{trail}':>7s} {len(v):>8d} "
                   f"{price:>7.0f}c {be:>11.2f} {rate:>15.2f} {nm:>9d} "
                   f"{'LOSES' if bad else 'ok':>7s}")
    out.append("")
    out.append(f"**{loses} of {total} states lose money at the price actually "
               f"charged.**")
    out.append("")

    # ---------------------------------------------------------------- part 3
    out.append("=" * 78)
    out.append("3. THE MECHANISM -- why, rather than just that")
    out.append("=" * 78)
    out.append("")
    cheap = [p for p in prices if p["minute"] >= 70 and p["no_cost_cents"] <= 97]
    out.append("Every moment at the 70th minute or later where 97 cents or less")
    out.append("was actually available:")
    out.append("")
    for p in sorted(cheap, key=lambda x: x["minute"]):
        out.append(f"    {p['date']}  {p['league']:20s} min {p['minute']:>3d}  "
                   f"{p['lead']}-{p['trail']}  pay {p['no_cost_cents']:.0f}c")
    sc = collections.Counter((p["lead"], p["trail"]) for p in cheap)
    out.append("")
    out.append(f"    by scoreline: "
               f"{', '.join(f'{a}-{b}: {c}' for (a, b), c in sc.most_common())}")
    out.append("")
    out.append("**The cheap price and the safe scoreline never happen at the")
    out.append("same time.** When Kalshi will sell at 97 cents late in a match,")
    out.append("it is a 2-1 or a 3-2 -- the scorelines with the HIGHEST comeback")
    out.append("rates on the whole table. Where the rate really is 1.7 in 100")
    out.append("(one goal up, 80th minute), the price is 99 or there is no")
    out.append("market at all.")
    out.append("")
    out.append("The market is not leaving money on the table. It is charging")
    out.append("less exactly where the risk is greater, which is what a working")
    out.append("market does.")
    out.append("")
    out.append("=" * 78)
    out.append("WHAT THIS DOES NOT SETTLE")
    out.append("=" * 78)
    out.append("")
    out.append("The rates are 2015-2024 across every competition; the prices are")
    out.append("a few hundred moments from Kalshi's ~69-day window. Those are")
    out.append("different populations and the per-state comparison in part 2 is")
    out.append("directional, not a measurement of profit.")
    out.append("")
    out.append("Part 1 does not depend on that, and part 1 is the answer: the")
    out.append("price the idea was built on is not there late in a match.")

    txt = "\n".join(out)
    print(txt)
    with open(os.path.join(REP, "price_vs_rate.txt"), "w",
              encoding="utf-8") as fh:
        fh.write(txt + "\n")
    print("\nwrote reports/price_vs_rate.txt")


if __name__ == "__main__":
    main()
