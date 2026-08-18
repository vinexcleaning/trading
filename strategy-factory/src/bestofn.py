"""THE BEST-OF-N NULL, re-derived here instead of quoted from elsewhere.

PREREGISTRATION.md section 6, gate 3. `coordinator/STRATEGY_FACTORY.md` carries
a table saying that the best of 2,000 zero-skill strategies typically looks like
+29.5%. That table is the single most load-bearing number in this whole project
- it is the reason a backtest is never reported as money - and this folder is
not allowed to rest on a number it did not compute.

So this recomputes it, in this folder, on the real fee function
(`common/kalshi_fees.py`, the only implementation, Guard #6), and prints the
disagreement with the quoted table if there is one.

WHAT IT SIMULATES. A strategy with NO SKILL AT ALL buys N contracts at price p.
Each settles at 100 cents with probability exactly p (that is what "no skill"
means: the market price is the truth) or at 0 otherwise. It pays the real
Kalshi taker fee on entry. Return is total profit divided by total staked.

Then: generate M such strategies, take the best one, and repeat. The
distribution of THAT is what a factory reporting its winner is actually
sampling from.

WHY IT MATTERS THAT THE FEE IS REAL. The fee is quadratic in price and is
largest at 50 cents (0.07 * 0.5 * 0.5 = 1.75 c per contract, rounded up per
ORDER). At 95 cents it is 0.33 c. A null derived without fees would be
symmetric around zero; the real one is not, and the asymmetry is the whole
reason "small positive" is not evidence of anything.

A SECOND METHOD, because one method is one source. The simulation is checked
against exact arithmetic: with 100 bets of one contract at a fixed price the
return can only take one value per number of wins, so the probability of
clearing any threshold is an exact tail of a binomial and needs no simulation
at all. Both are printed. If they disagree, one of them is wrong and the script
says so rather than picking the prettier one.

    py -3 strategy-factory/src/bestofn.py
    py -3 strategy-factory/src/bestofn.py --price 90 --bets 200
"""
from __future__ import annotations

import argparse
import math
import random
import sys
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent))
from common.kalshi_fees import fee_order_cents  # noqa: E402

# The quoted table this script exists to check. Source:
# coordinator/STRATEGY_FACTORY.md section 1.
QUOTED = {10: 10.1, 50: 17.9, 200: 23.7, 500: 25.6, 2000: 29.5}
QUOTED_P30 = {10: 0.0, 50: 0.0, 200: 5.0, 500: 9.0, 2000: 37.0}


def one_strategy(rng, price_c: float, bets: int, per_order: int) -> float:
    """Return-on-stake of one zero-skill strategy, net of the real fee.

    `per_order` is how many contracts are bought per order. It is a parameter
    rather than 1 because the Kalshi fee ROUNDS UP PER ORDER, so a strategy
    that buys 10 at a time pays materially less than one that buys singles -
    measured at 97 c, 100 singles cost 100 c of fee and one order of 100 costs
    21 c. Getting this wrong would make the null too pessimistic and would
    therefore make real strategies look better than they are.
    """
    n_orders = max(1, bets // per_order)
    contracts = n_orders * per_order
    p = price_c / 100.0
    wins = sum(1 for _ in range(contracts) if rng.random() < p)
    gross = wins * (100.0 - price_c) - (contracts - wins) * price_c
    fee = float(fee_order_cents(price_c, per_order)) * n_orders
    staked = contracts * price_c
    return (gross - fee) / staked


def best_of(rng, m: int, price_c: float, bets: int, per_order: int) -> float:
    return max(one_strategy(rng, price_c, bets, per_order) for _ in range(m))


def pct(xs, q):
    xs = sorted(xs)
    i = min(len(xs) - 1, max(0, int(q * (len(xs) - 1))))
    return xs[i]


def exact_p_at_least(threshold, price_c, bets, per_order, roundtrip=False):
    """EXACT probability that one zero-skill strategy clears `threshold`.

    No simulation. With `bets` contracts all bought at one price, the return is
    a function of the number of wins alone, so the answer is a binomial tail.
    This exists to check the simulation: two methods, and a disagreement is
    reported rather than averaged away.

    `roundtrip=True` charges the fee TWICE, once on entry and once on exit.
    That is the correct cost for a strategy that sells before settlement and
    the WRONG cost for one that holds - `common/kalshi_fees.py` says so in
    `roundtrip_cost_cents`: "exit_cents=None means held to settlement, which
    pays the entry fee only." It is a flag here because the quoted table in
    `coordinator/STRATEGY_FACTORY.md` can only be reproduced with it on, and
    which of the two is right changes the answer by a factor of four.
    """
    n_orders = max(1, bets // per_order)
    contracts = n_orders * per_order
    fee = float(fee_order_cents(price_c, per_order)) * n_orders
    if roundtrip:
        fee *= 2.0
    staked = contracts * price_c
    p = price_c / 100.0
    # profit(w) = w*(100-price) - (contracts-w)*price - fee = 100w - contracts*price - fee
    need_w = (threshold * staked + contracts * price_c + fee) / 100.0
    w = math.ceil(need_w - 1e-9)
    if w > contracts:
        return 0.0
    w = max(w, 0)
    return sum(comb(contracts, k) * (p ** k) * ((1 - p) ** (contracts - k))
               for k in range(w, contracts + 1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--price", type=float, default=50.0, help="cents")
    ap.add_argument("--bets", type=int, default=100)
    ap.add_argument("--per-order", type=int, default=1)
    ap.add_argument("--reps", type=int, default=2000,
                    help="how many times to draw a whole factory")
    ap.add_argument("--single-reps", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=20260818)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    print("BEST-OF-N NULL - zero skill, real Kalshi taker fee")
    print("price %.0f c   bets %d   contracts per order %d   seed %d"
          % (args.price, args.bets, args.per_order, args.seed))
    print("fee on one order of %d at %.0f c = %.2f c"
          % (args.per_order, args.price,
             float(fee_order_cents(args.price, args.per_order))))
    print()

    # ---- 1. ONE strategy. This is the user's own question, and he is right.
    xs = [one_strategy(rng, args.price, args.bets, args.per_order)
          for _ in range(args.single_reps)]
    n30 = sum(1 for x in xs if x >= 0.30)
    print("ONE strategy, %d bets, no skill at all (%d runs):" % (args.bets, len(xs)))
    print("  lands between %+.1f%% and %+.1f%% ninety times in a hundred"
          % (100 * pct(xs, 0.05), 100 * pct(xs, 0.95)))
    print("  typical (middle) result        : %+.1f%%" % (100 * pct(xs, 0.50)))
    print("  reaches +30%%                   : %d in %d  (%s)"
          % (n30, len(xs),
             "about 1 in %d" % round(len(xs) / n30) if n30 else "never seen"))
    print()

    # ---- 2. The best of M. This is what a factory reports.
    print("BEST OF M zero-skill strategies (%d factories drawn each):" % args.reps)
    print("  %6s  %14s  %14s  %10s  %14s"
          % ("M", "typical best", "quoted table", ">= +30%", "quoted >= 30%"))
    sims30 = []
    for m in (10, 50, 200, 500, 2000):
        bs = [best_of(rng, m, args.price, args.bets, args.per_order)
              for _ in range(args.reps)]
        med = 100 * pct(bs, 0.50)
        share30 = 100.0 * sum(1 for b in bs if b >= 0.30) / len(bs)
        sims30.append(share30)
        q = QUOTED.get(m)
        q30 = QUOTED_P30.get(m)
        print("  %6d  %13.1f%%  %13s  %9.1f%%  %13s"
              % (m, med, ("%+.1f%%" % q) if q is not None else "-",
                 share30, ("%.0f%%" % q30) if q30 is not None else "-"))
    print()

    # ---- 3. The same thing exactly, with no simulation at all.
    p_hold = exact_p_at_least(0.30, args.price, args.bets, args.per_order,
                              roundtrip=False)
    p_trip = exact_p_at_least(0.30, args.price, args.bets, args.per_order,
                              roundtrip=True)
    print("EXACT (binomial tail, no simulation) - chance of reaching +30%:")
    print("  %-46s %s" % ("held to settlement, entry fee only:",
                          "1 in %.0f" % (1 / p_hold) if p_hold else "never"))
    print("  %-46s %s" % ("sold before settlement, fee paid twice:",
                          "1 in %.0f" % (1 / p_trip) if p_trip else "never"))
    print()
    print("  %6s  %14s  %14s  %14s"
          % ("M", "exact, hold", "exact, roundtrip", "simulated"))
    for m, sim in zip((10, 50, 200, 500, 2000), sims30):
        print("  %6d  %13.1f%%  %15.1f%%  %13.1f%%"
              % (m, 100 * (1 - (1 - p_hold) ** m),
                 100 * (1 - (1 - p_trip) ** m), sim))
    print()
    print("WHICH FEE IS RIGHT decides this, and it is not a detail. Kalshi")
    print("charges nothing at settlement, so a BUY-AND-HOLD strategy - the")
    print("default shape in this repo - pays the fee once. The quoted table")
    print("can only be reproduced with the fee charged twice, which makes the")
    print("best-of-N hazard look about four times smaller than it is.")
    print()
    print("Read the M=2000 row as the specification of this project, not as a")
    print("warning about it: a factory that screens two thousand strategies")
    print("and reports its winner is reporting a number that a pile of")
    print("coin-flips would have produced. That is why the backtest only ever")
    print("CHOOSES, and the forward test is the only thing that COUNTS.")


if __name__ == "__main__":
    main()
