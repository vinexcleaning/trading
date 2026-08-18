"""Four staking tiers on the SAME picks. Mailbox 016 job 4.

His proposal, in his words:

    "if that strat continues to prove itself we can put like 10% stake on that
     and like only 5% of the others"

Two tiers, not a filter. Measured, not argued.

    python src/tiers.py [--usable 56] [--floor 50]

⚠ Tiers 3 and 4 are chosen by looking at which bucket won. That is selection on
the past. It is reported IN-SAMPLE and OUT-OF-SAMPLE separately for exactly
that reason, and the out-of-sample column is the only one that is evidence.
"""
from __future__ import annotations

import argparse
import collections
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import capital as C                    # noqa: E402
import engine as E                     # noqa: E402
from common.kalshi_fees import fee_order_cents   # noqa: E402

FOUND_ON = C.FOUND_ON

TIERS = {
    "flat 10% everything":       {"agreed": .10, "opp": .10, "alone": .10},
    "flat 5% everything":        {"agreed": .05, "opp": .05, "alone": .05},
    "10 agreed / 5 opp / 5 alone": {"agreed": .10, "opp": .05, "alone": .05},
    "10 agreed / 5 opp / SKIP alone": {"agreed": .10, "opp": .05, "alone": 0.0},
}


def run(con, tier, usable, floor, since=None, until=None):
    ag, op, al = C.buckets(con, since=since, until=until)
    tagged = ([(g, r, "agreed") for g, r in ag.items()]
              + [(g, r, "opp") for g, r in op.items()]
              + [(g, r, "alone") for g, r in al.items()])
    tagged.sort(key=lambda x: x[1]["opened_utc"])

    bal = usable
    cash = collections.defaultdict(float)
    nopen = collections.defaultdict(int)
    taken = skipped_cash = skipped_rule = 0
    pnl = staked = 0.0
    hit_floor = False
    for g, r, bucket in tagged:
        frac = tier[bucket]
        if frac <= 0:
            skipped_rule += 1
            continue
        stake = usable * frac
        price = r["entry_price_c"] / 100.0
        n = int(stake / price)
        if n < 1:
            skipped_cash += 1
            continue
        cost = n * price + float(fee_order_cents(r["entry_price_c"], n)) / 100.0
        # can we afford it without breaching the floor?
        a = datetime.fromisoformat(r["opened_utc"]).date()
        b = datetime.fromisoformat(r["closed_utc"]).date() if r["closed_utc"] else a
        cur = max((cash[d] for d in _span(a, b)), default=0.0)
        if cur + cost > usable:
            skipped_cash += 1
            continue
        for d in _span(a, b):
            cash[d] += cost
            nopen[d] += 1
        taken += 1
        staked += cost
        # scale the recorded P&L to this stake size
        pnl += (r["pnl_c"] or 0) / 100.0 * (n / max(1, r["contracts"]))
    peak = max(cash.values()) if cash else 0.0
    return {"taken": taken, "skipped_cash": skipped_cash,
            "skipped_rule": skipped_rule, "profit": round(pnl, 2),
            "staked": round(staked, 2),
            "return_pct": round(100 * pnl / staked, 1) if staked else None,
            "peak_cash": round(peak, 2),
            "peak_bets": max(nopen.values()) if nopen else 0,
            "hits_floor": peak > usable}


def _span(a, b):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--usable", type=float, default=56.0)
    ap.add_argument("--floor", type=float, default=50.0)
    a = ap.parse_args()
    con = E.connect()
    print(f"usable balance ${a.usable:.0f} (live balance minus a ${a.floor:.0f} "
          f"floor). Picks and prices identical across tiers.\n")
    for label, when in (("ALL settled games (in-sample, do not act on it)",
                         {}),
                        (f"OUT OF SAMPLE only (settled after {FOUND_ON})",
                         {"since": FOUND_ON})):
        print(f"## {label}\n")
        print(f"{'tier':<32} {'taken':>6} {'skipped':>8} {'profit$':>9} "
              f"{'return':>8} {'peak$':>8} {'at once':>8}")
        for nm, t in TIERS.items():
            r = run(con, t, a.usable, a.floor, **when)
            sk = f"{r['skipped_cash']}+{r['skipped_rule']}"
            print(f"{nm:<32} {r['taken']:>6} {sk:>8} {r['profit']:>9.2f} "
                  f"{str(r['return_pct'])+'%':>8} {r['peak_cash']:>8.2f} "
                  f"{r['peak_bets']:>8}")
        print()
    print("skipped column is 'ran out of money' + 'rule said no'.")
    print("** Tiers 3 and 4 were chosen by looking at which bucket won.")
    print("   Only the out-of-sample table is evidence.")
    con.close()
