"""The gap: what really happens, what Kalshi charges, and the difference.

THE DELIVERABLE. For every state -- every minute, every scoreline -- three
numbers side by side:

    what the trailing team really does   (out of 100 matches)
    what Kalshi charged to bet against them
    the difference, in cents, after the fee

TWO POPULATIONS, AND THIS FILE REFUSES TO BLUR THEM. The rates come from ten
years of football. Every price comes from a 69-day window in 2026. A "fair
price" built from the rates is **a hypothesis about 2026, not a measurement of
it**, and every line that reports one says so.

`era_split.py` measured how bad that assumption is, and it is not free: at one
goal up, comebacks late in the match became MORE common after 2022 -- 1.3 per
100 at the 80th minute in 2015-2018 against 2.3 in 2022-2024, with ranges that
do not touch. Five substitutes became permanent in 2022. **So this file prices
against 2022-2024 only**, not the ten-year average, and pays for that with a
smaller sample.

LIQUIDITY IS REPORTED FIRST, BEFORE ANY EDGE. A price with nobody behind it is
not a trade, and in this market that is the usual case rather than the
exception. Any table that showed an edge without showing how often there was
anything to buy would be describing a bet that cannot be placed.

**No cell is nominated and nothing is ranked.** Same rule as the comeback table:
a grid this size always has a best-looking corner.

Read-only. No network. No credentials. No orders.
"""
import json
import os
import statistics
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "..", "common"))
import build_comeback_table as B   # noqa: E402
import kalshi_fees as F            # noqa: E402

PRICES = os.path.join(DATA, "price_by_minute.jsonl")
MODERN = ("2022", "2024")
MIN_PRICED = 8          # fewer priced minutes than this and a cell is not shown
SHOW = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 89]
TIERS = ["top third", "middle third", "bottom third", "unknown"]


def modern_rates():
    """Comeback rates from 2022-2024 only. Returns two lookups.

    Coarse: (minute, lead, trail) -> (per100, matches)
    Fine:   (minute, lead, trail, leader_tier, trailer_tier) -> (per100, matches)
    """
    matches, _ = B.load()
    coarse = defaultdict(lambda: [0, 0])
    fine = defaultdict(lambda: [0, 0])
    by_league = defaultdict(lambda: [0, 0])
    n = 0
    for m in matches:
        if not (MODERN[0] <= m["date"][:4] <= MODERN[1]):
            continue
        n += 1
        for o in B.observations(m):
            c = coarse[(o["minute"], o["lead"], o["trail"])]
            c[0] += o["trailer_won"]
            c[1] += 1
            f = fine[(o["minute"], o["lead"], o["trail"],
                      o["leader_tier"], o["trailer_tier"])]
            f[0] += o["trailer_won"]
            f[1] += 1
            g = by_league[(o["league"], o["minute"], o["lead"], o["trail"])]
            g[0] += o["trailer_won"]
            g[1] += 1
    return coarse, fine, by_league, n


def load_prices():
    rows = []
    with open(PRICES, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            h, a = r["h"], r["a"]
            if h == a:
                continue
            if h > a:
                lead, trail = h, a
                t_bid, t_ask = r["away_bid"], r["away_ask"]
                lt, tt = r["home_tier"], r["away_tier"]
            else:
                lead, trail = a, h
                t_bid, t_ask = r["home_bid"], r["home_ask"]
                lt, tt = r["away_tier"], r["home_tier"]
            rows.append({
                "minute": r["minute"], "lead": lead, "trail": trail,
                "league": r["league"], "date": r["date"], "event": r["event"],
                # Buying NO on the trailing side means crossing to the NO ask,
                # which is 100 minus their YES bid. A bid of zero means there is
                # no NO to buy below 100 at all -- that is no market, not a
                # price of 100, and it is counted separately everywhere below.
                "no_cost": 100.0 - t_bid,
                "has_market": t_bid > 0,
                "spread": t_ask - t_bid,
                "leader_tier": lt, "trailer_tier": tt,
            })
    return rows


def fee_at(price):
    return float(F.roundtrip_cost_cents(price))


def main():
    if not os.path.exists(PRICES):
        sys.exit("no per-minute prices yet -- run price_by_minute.py first")
    prices = load_prices()
    coarse, fine, by_league, n_modern = modern_rates()

    out = []
    out.append("THE GAP: WHAT HAPPENS, WHAT KALSHI CHARGES, AND THE DIFFERENCE")
    out.append("=" * 78)
    out.append("")
    out.append(f"Prices: {len(prices)} minute-readings from "
               f"{len({p['event'] for p in prices})} matches inside Kalshi's")
    out.append("69-day window, read at every displayed minute whether or not")
    out.append("anything had just happened.")
    out.append("")
    out.append(f"Rates: {n_modern} matches, 2022-2024 only. Not the ten-year")
    out.append("average -- comebacks late in a one-goal game became more common")
    out.append("after 2022 and the ten-year number would understate them.")
    out.append("")
    out.append("**These are two different sets of matches.** A fair price built")
    out.append("from the rates is a hypothesis about 2026, not a measurement.")

    # ------------------------------------------------------------ liquidity
    out.append("")
    out.append("=" * 78)
    out.append("1. IS THERE ANYTHING TO BUY AT ALL?")
    out.append("=" * 78)
    out.append("")
    out.append("Before any edge: how often was anyone bidding on the losing")
    out.append("team, so that a bet against them could actually be placed?")
    out.append("")
    out.append("Bigger is better. Zero means the trade does not exist.")
    out.append("")
    out.append(f"{'minute':>7s} {'readings':>9s} {'a market existed':>18s} "
               f"{'you could pay 97 or less':>26s}")
    out.append("-" * 64)
    for minute in SHOW:
        v = [p for p in prices if p["minute"] == minute]
        if not v:
            continue
        m = [p for p in v if p["has_market"]]
        cheap = [p for p in m if p["no_cost"] <= 97]
        out.append(f"{minute:>7d} {len(v):>9d} "
                   f"{f'{len(m)/len(v)*100:.0f} in 100':>18s} "
                   f"{f'{len(cheap)/len(v)*100:.0f} in 100':>26s}")

    # ------------------------------------------------------- the gap, 1 goal
    for lead, trail in [(1, 0), (2, 1), (2, 0)]:
        out.append("")
        out.append("=" * 78)
        out.append(f"2. THE GAP AT {lead}-{trail}")
        out.append("=" * 78)
        out.append("")
        out.append("'Really happens' is out of 100 matches, 2022-2024.")
        out.append("'Worth' is what betting against them is worth, in cents.")
        out.append("'Charged' is the middle of what Kalshi actually wanted.")
        out.append("'After fee' is worth minus charged minus the fee.")
        out.append("Positive means you were being paid to take it.")
        out.append("")
        out.append(f"{'minute':>7s} {'really happens':>15s} {'matches':>9s} "
                   f"{'worth':>7s} {'charged':>9s} {'readings':>9s} "
                   f"{'after fee':>11s}")
        out.append("-" * 74)
        for minute in SHOW:
            k, n = coarse.get((minute, lead, trail), [0, 0])
            v = [p for p in prices
                 if p["minute"] == minute and p["lead"] == lead
                 and p["trail"] == trail and p["has_market"]]
            if n < 100 or len(v) < MIN_PRICED:
                continue
            rate = k / n * 100
            worth = 100 - rate
            charged = statistics.median(p["no_cost"] for p in v)
            net = worth - charged - fee_at(charged)
            out.append(f"{minute:>7d} {rate:>14.2f} {n:>9d} "
                       f"{worth:>6.1f}c {charged:>8.1f}c {len(v):>9d} "
                       f"{net:>10.2f}c")
        out.append("")
        out.append("Readings are minutes, not matches -- one match contributes")
        out.append("a reading at every minute it sat in this state, so these")
        out.append("are the same matches seen repeatedly. Never add them up.")

    # ------------------------------------------------------------- strength
    out.append("")
    out.append("=" * 78)
    out.append("3. THE STRENGTH SPLIT, WHERE IT IS BIGGEST")
    out.append("=" * 78)
    out.append("")
    out.append("One goal up, the 25th minute. The user's own hypothesis, and")
    out.append("it is larger here than late in the match.")
    out.append("")
    out.append(f"{'leader':>14s} {'trailer':>14s} {'really happens':>15s} "
               f"{'matches':>9s} {'worth':>7s} {'charged':>9s} {'readings':>9s}")
    out.append("-" * 82)
    for lt in TIERS:
        for tt in TIERS:
            k, n = fine.get((25, 1, 0, lt, tt), [0, 0])
            if n < 100:
                continue
            v = [p for p in prices
                 if p["minute"] == 25 and p["lead"] == 1 and p["trail"] == 0
                 and p["leader_tier"] == lt and p["trailer_tier"] == tt
                 and p["has_market"]]
            rate = k / n * 100
            charged = (f"{statistics.median(p['no_cost'] for p in v):.1f}c"
                       if len(v) >= MIN_PRICED else "-")
            out.append(f"{lt:>14s} {tt:>14s} {rate:>14.2f} {n:>9d} "
                       f"{100-rate:>6.1f}c {charged:>9s} {len(v):>9d}")
    out.append("")
    out.append("A blank price means fewer than "
               f"{MIN_PRICED} readings existed in that box.")

    # ------------------------------------------- the attack on my own number
    out.append("")
    out.append("=" * 78)
    out.append("4. THE OBJECTION THAT COULD HAVE FAKED ALL OF THIS")
    out.append("=" * 78)
    out.append("")
    mix = Counter(p["league"] for p in prices)
    tot = sum(mix.values())
    out.append("Sections 2 and 3 compare a rate averaged over 23 competitions")
    out.append("against prices that came from whichever were in season. They")
    out.append("are not the same competitions:")
    out.append("")
    for lg, c in mix.most_common():
        out.append(f"    {lg:24s} {c:6d} readings  {c/tot*100:5.1f}%")
    out.append("")
    out.append("**More than half is the World Cup and international friendlies,")
    out.append("and there is no European league in it at all.** A friendly is")
    out.append("barely the same sport -- six substitutions and nobody trying --")
    out.append("so an average that includes ordinary league football could be")
    out.append("flattering or damning here purely by mixture.")
    out.append("")
    out.append("So: every reading is re-compared against ITS OWN competition's")
    out.append("rate at that exact minute and scoreline, 2022-2024. No averaging")
    out.append("across competitions happens at all.")
    out.append("")
    nets, thin = [], 0
    for p in prices:
        if not p["has_market"]:
            continue
        k, n = by_league.get(
            (p["league"], p["minute"], p["lead"], p["trail"]), [0, 0])
        if n < 100:
            thin += 1
            continue
        worth = 100 - k / n * 100
        nets.append((worth - p["no_cost"] - fee_at(p["no_cost"]), p))
    out.append(f"{'':>4s}readings compared        {len(nets)}")
    out.append(f"{'':>4s}dropped, own competition thin  {thin}")
    if nets:
        vals = sorted(v for v, _ in nets)
        pos = sum(1 for v in vals if v > 0)
        out.append(f"{'':>4s}middle result           {statistics.median(vals):+.2f}c "
                   f"per contract")
        out.append(f"{'':>4s}average result          "
                   f"{sum(vals)/len(vals):+.2f}c per contract")
        out.append(f"{'':>4s}readings that made money {pos} of {len(vals)} "
                   f"({pos/len(vals)*100:.0f} in 100)")
        out.append("")
        out.append(f"{'minute':>7s} {'readings':>9s} {'middle result':>15s}")
        out.append("-" * 34)
        for minute in SHOW:
            v = sorted(x for x, p in nets if p["minute"] == minute)
            if len(v) < MIN_PRICED:
                continue
            out.append(f"{minute:>7d} {len(v):>9d} "
                       f"{statistics.median(v):>+14.2f}c")
    out.append("")
    out.append("This is the number to believe over sections 2 and 3, because it")
    out.append("is the only one where the football and the price come from the")
    out.append("same competition.")

    txt = "\n".join(out)
    print(txt)
    os.makedirs(REP, exist_ok=True)
    with open(os.path.join(REP, "gap_table.txt"), "w", encoding="utf-8") as fh:
        fh.write(txt + "\n")
    print("\nwrote reports/gap_table.txt")


if __name__ == "__main__":
    main()
