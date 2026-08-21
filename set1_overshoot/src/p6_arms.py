"""Phase 6e -- the three registered arms, both representations, both queue
bounds, the taker benchmark, and the two placebos.

READ `PREREGISTRATION_MAKER_FADE.md` BEFORE READING ANY NUMBER OUT OF THIS.
Three arms only. Everything else printed here is a picture and is labelled one.

WHAT IS REPORTED FOR EVERY CELL, AND WHY EACH ONE IS THERE
----------------------------------------------------------
  fill rate        -- a maker strategy that cannot get filled is not a strategy.
                      Preregistration section 10 kills it below 1 match in 5.
  per FILL         -- what a contract made when we got one.
  per ATTEMPT      -- the same, with the matches we never got into counted as
                      zero. This is the honest strategy-level number, and it is
                      the one a maker backtest usually leaves out.
  the taker line   -- the same trade, crossing the spread. Without it "the
                      maker version made 0.4c" means nothing.
  doing nothing    -- zero. Named explicitly because a fraction of a cent on a
                      handful of fills is competing with leaving it alone.

Confidence intervals are bootstrapped over MATCHES, never over fills: a match
settles once, and hundreds of fills inside it share that one outcome.
"""
from __future__ import annotations

import argparse
import pathlib
import sqlite3
import sys
from decimal import Decimal

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent))

import p6_maker_fill as F                          # noqa: E402
from common import kalshi_fees as KF               # noqa: E402

DB = ROOT / "data" / "maker.db"
CUTOFF = "2026-08-02"

ARMS = {
    "M1 pooled":       None,
    "M2 maker-free":   ("itf", "challenger"),
    "M3 main tour":    ("main",),
}

#: The study entered at the ask plus one cent of slippage. Kept identical so
#: the benchmark is the same trade and not a different one.
TAKER_SLIPPAGE_C = 1


def taker_pnl_cents(price_c, dog_won, contracts=100):
    fee = KF.fee_order_cents(price_c, contracts)
    gross = (100 - price_c) if dog_won else (-price_c)
    return float(Decimal(gross) - fee / Decimal(contracts))


def boot_ci(x, n=4000, seed=7):
    """Bootstrap over MATCHES. Returns (mean, lo, hi)."""
    x = np.asarray(x, dtype=float)
    if len(x) == 0:
        return float("nan"), float("nan"), float("nan")
    if len(x) == 1:
        return float(x[0]), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n, len(x)))
    m = x[idx].mean(axis=1)
    return float(x.mean()), float(np.percentile(m, 2.5)), \
        float(np.percentile(m, 97.5))


def cell(rows, rep, bound, fee_types):
    """One representation at one queue bound.

    Only matches whose relevant tape is ON DISK are counted. A market we have
    not pulled trades for is not a market where nobody traded, and mixing them
    reports a data-coverage rate wearing a fill rate's clothes.
    """
    key = f"{rep}_{bound}"
    tape_key = "tape_d" if rep == "r1" else "tape_f"
    per_fill, per_attempt, filled = [], [], 0
    skipped = 0
    for r in rows:
        if not r.get(tape_key):
            skipped += 1
            continue
        got = r[key]
        # entry price expressed as the price paid for the UNDERDOG
        price = r["p_r1"] if rep == "r1" else 100 - r["p_r2"]
        if price <= 0 or price >= 100:
            continue
        ft = fee_types.get(r["series"], "quadratic")
        if got > 0:
            v = F.pnl_cents(price, r["dog_won"], ft, got)
            per_fill.append(v)
            per_attempt.append(v)
            filled += 1
        else:
            per_attempt.append(0.0)      # no trade is not a missing value
    n = len(per_attempt)
    return {
        "n": n, "filled": filled, "no_tape": skipped,
        "rate": filled / n if n else 0.0,
        "fill": boot_ci(per_fill),
        "attempt": boot_ci(per_attempt),
    }


def taker_cell(rows):
    """The study's own entry: at the ASK plus a cent of slippage.

    ⚠ Pricing this at the BID instead reads +8.79c where the study reports
    -1.10c, because it hands the taker the whole spread for free. The spread is
    the entire thing this study is about, so that error does not just shift the
    benchmark, it deletes the question.
    """
    v, px = [], []
    for r in rows:
        price = min(99, r["ask_dog"] + TAKER_SLIPPAGE_C)
        px.append(price)
        v.append(taker_pnl_cents(price, r["dog_won"]))
    return boot_ci(v), float(np.mean(px)) if px else float("nan")


def money(c, stake_usd=100.0):
    """Cents per contract -> dollars per $100 risked, which is the unit he
    reads. A contract at 66c risks 66c, so the scaling is by price."""
    return c / 66.0 * (stake_usd / 100.0) * 100.0


def report(con, depth, min_minute, rest_min, pre_spread_max, period_label,
           before, since, arms=ARMS):
    fee_types = dict(con.execute("select series, fee_type from fees"))
    print("=" * 78)
    print(f"deep:{depth:.0f}@{min_minute}   rest {rest_min} min   "
          f"pre-match spread <= {pre_spread_max}c   [{period_label}]")
    print("=" * 78)

    for name, tiers in arms.items():
        rows = F.run(con, depth=depth, min_minute=min_minute,
                     rest_min=rest_min, tiers=tiers,
                     pre_spread_max=pre_spread_max,
                     before=before, since=since)
        if not rows:
            print(f"\n{name}: the rule fired on nothing")
            continue
        won = sum(r["dog_won"] for r in rows)
        (tk, tlo, thi), mean_px = taker_cell(rows)
        print(f"\n{name}   fired on {len(rows):,} matches   "
              f"underdog won {won / len(rows):.1%}")
        print(f"  {'':22}{'fill rate':>10} {'per FILL':>22} "
              f"{'per ATTEMPT':>22}")
        for rep in ("r1", "r2"):
            label = ("R1 bid on underdog" if rep == "r1"
                     else "R2 ask on favourite")
            for bound in ("front", "back"):
                c = cell(rows, rep, bound, fee_types)
                fm, flo, fhi = c["fill"]
                am, alo, ahi = c["attempt"]
                fs = ("     --" if np.isnan(fm)
                      else f"{fm:+6.2f} [{flo:+5.2f},{fhi:+5.2f}]")
                as_ = ("     --" if np.isnan(am)
                       else f"{am:+6.2f} [{alo:+5.2f},{ahi:+5.2f}]")
                print(f"  {label:<18} {bound:<5}{c['rate']:>9.1%} "
                      f"{fs:>22} {as_:>22}   n={c['n']:,}")
        print(f"  {'TAKER benchmark':<18} {'n/a':<5}{1.0:>9.1%} "
              f"{tk:+6.2f} [{tlo:+5.2f},{thi:+5.2f}]{'':>4} "
              f"{tk:+6.2f} [{tlo:+5.2f},{thi:+5.2f}]")
        print(f"  {'DOING NOTHING':<18} {'':<5}{'':>9} {0.0:+6.2f}"
              f"{'':>16} {0.0:+6.2f}")


def placebos(con, depth, min_minute, rest_min, pre_spread_max, before):
    print("\n" + "=" * 78)
    print("PLACEBOS -- a failure in either voids the run")
    print("=" * 78)
    real = F.run(con, depth=depth, min_minute=min_minute, rest_min=rest_min,
                 pre_spread_max=pre_spread_max, before=before)
    shuf = F.run(con, depth=depth, min_minute=min_minute, rest_min=rest_min,
                 pre_spread_max=pre_spread_max, before=before,
                 shuffle=True, seed=11)
    fee_types = dict(con.execute("select series, fee_type from fees"))
    print("\nP1 -- shuffle which side was the aggressor, keep prices and times.")
    print("     A real fill advantage MUST collapse.")
    print(f"  {'':10}{'real fill':>10}{'shuffled':>10}"
          f"{'real /attempt':>16}{'shuffled':>16}")
    for rep in ("r1", "r2"):
        a = cell(real, rep, "front", fee_types)
        b = cell(shuf, rep, "front", fee_types)
        print(f"  {rep.upper() + ' front':<10}{a['rate']:>10.1%}"
              f"{b['rate']:>10.1%}{a['attempt'][0]:>+15.2f}c"
              f"{b['attempt'][0]:>+15.2f}c")
    same = all(cell(real, r, "front", fee_types)["rate"]
               == cell(shuf, r, "front", fee_types)["rate"]
               for r in ("r1", "r2"))
    if same:
        print("  ⚠ THE SHUFFLE CHANGED NOTHING. That is a broken placebo, not "
              "a pass.\n    The repo's first placebo was algebraically a no-op "
              "and passed vacuously.")
    print("\nP2 -- rest at a random minute with no signal at all.")
    print("     Reported by --placebo-random, which is a separate run so that "
          "it cannot\n     quietly share this one's event list.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--depth", type=float, default=30.0)
    ap.add_argument("--min-minute", type=int, default=38)
    ap.add_argument("--rest-min", type=int, default=F.REST_MIN)
    ap.add_argument("--pre-spread-max", type=int, default=10)
    ap.add_argument("--grid", action="store_true",
                    help="the whole depth grid, as a PICTURE with no verdict")
    ap.add_argument("--open-the-check-period", action="store_true",
                    help="ONE evaluation, only after the arms are frozen")
    a = ap.parse_args()

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    have = con.execute(
        "select count(distinct ticker) from trades").fetchone()[0]
    print(f"markets with trades on disk: {have:,}\n")

    if a.open_the_check_period:
        print("⚠ OPENING THE UNTOUCHED CHECK PERIOD. Preregistration section 5: "
              "one\n  evaluation, no second pass. If the rule changes after "
              "this, the check\n  period is spent and must be declared spent.\n")
        report(con, a.depth, a.min_minute, a.rest_min, a.pre_spread_max,
               "CHECK PERIOD 2026-08-02 -> 08-20", None, CUTOFF)
        return

    report(con, a.depth, a.min_minute, a.rest_min, a.pre_spread_max,
           "selection 2026-06-14 -> 08-01", CUTOFF, None)
    placebos(con, a.depth, a.min_minute, a.rest_min, a.pre_spread_max, CUTOFF)

    if a.grid:
        print("\n" + "=" * 78)
        print("THE DEPTH GRID -- A PICTURE. No verdict, no p-value, no ledger "
              "row.")
        print("Preregistration: if a depth other than 30 looks better, that "
              "does NOT\npromote it -- it goes in the not-tested list for a "
              "future registration.")
        print("=" * 78)
        for d in (8, 12, 16, 20, 25, 30, 35, 40):
            rows = F.run(con, depth=float(d), min_minute=a.min_minute,
                         rest_min=a.rest_min,
                         pre_spread_max=a.pre_spread_max, before=CUTOFF)
            if not rows:
                continue
            ft = dict(con.execute("select series, fee_type from fees"))
            c = cell(rows, "r2", "front", ft)
            am = c["attempt"][0]
            mark = "  <- registered" if d == 30 else (
                "  <- the one he asked for" if d == 40 else "")
            print(f"  deep:{d:<3} fired {len(rows):>5,}  R2 front fill "
                  f"{c['rate']:>6.1%}  per attempt {am:+6.2f}c{mark}")


if __name__ == "__main__":
    sys.exit(main())
