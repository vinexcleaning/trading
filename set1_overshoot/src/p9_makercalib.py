"""Phase 9 -- does MAKER execution turn the 90-95c prematch favourite positive?

Mailbox 021. Pre-registered in `PREREGISTRATION_MAKERCALIB.md`.

WHAT IS DIFFERENT FROM PHASE 6, AND WHY THE EARLIER NULL DOES NOT CARRY OVER
----------------------------------------------------------------------------
Phase 6 executed a SIGNAL -- the set-1 fade -- and came out UNDECIDABLE. This
executes WHOLE-MARKET CALIBRATION: every prematch favourite in a price band,
with no selection at all. **The edge is not a strategy's edge; it is the market
being wrong about a whole population.** So the method is reused and the verdict
is not.

The fill machinery is imported from `p6_maker_fill`, not re-implemented. A
second copy that was subtly different would look like a replication and would
not be one.

⚠ JOB 0 IS AVAILABILITY, NOT PROFIT. `GUARDS.md` #24: a quote is not a constant
of nature, and measuring only where a quote exists conditions the sample on the
event still being uncertain. Two numbers are printed before any money figure:
how often a resting bid could have filled at all, and whether the markets that
filled settled differently from the ones that did not. **The second is the most
likely way this produces a fake positive** -- if sellers only turn up when the
favourite is wobbling, the maker arm has quietly bought the riskier half.
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

import p6_maker_fill as MF                        # noqa: E402
from common import kalshi_fees as KF              # noqa: E402

DB = ROOT / "data" / "maker.db"
CUTOFF = "2026-08-02"

BANDS = [(75, 80), (80, 85), (85, 90), (90, 92.5), (92.5, 95), (95, 97.5)]
REST_MIN = 60                       # registered primary
REST_SENSITIVITY = (30, 240)

ARMS = {"C1 pooled": None,
        "C2 maker-free (ITF + Challenger)": ("itf", "challenger"),
        "C3 main tour (makers charged)": ("main",)}


def boot(x, n=4000, seed=11):
    x = np.asarray(x, float)
    if len(x) == 0:
        return float("nan"), float("nan"), float("nan")
    if len(x) == 1:
        return float(x[0]), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), (n, len(x)))].mean(axis=1)
    return float(x.mean()), float(np.percentile(m, 2.5)), \
        float(np.percentile(m, 97.5))


def rows(con, lo, hi, tiers=None, before=None, since=None):
    q = ("select s.ticker, s.event_ticker, s.series, s.tier, s.t_lo, s.t0, "
         "s.pre_bid, s.pre_ask, m.result, m.close_time "
         "from state s join markets m on m.ticker = s.ticker "
         "where s.ok = 1 and m.result in ('yes','no') "
         "and (s.pre_bid + s.pre_ask) / 2.0 >= ? "
         "and (s.pre_bid + s.pre_ask) / 2.0 < ?")
    args = [lo, hi]
    if tiers:
        q += " and s.tier in (%s)" % ",".join("?" * len(tiers))
        args += list(tiers)
    if before:
        q += " and m.close_time < ?"
        args.append(before)
    if since:
        q += " and m.close_time >= ?"
        args.append(since)
    out = list(con.execute(q, args))
    # ⚠ asserted, not assumed: at these prices only one side of a match can
    # qualify, so a match must never contribute two observations.
    evs = [r[1] for r in out]
    if len(set(evs)) != len(evs):
        raise SystemExit(
            f"band {lo}-{hi}: a match contributed two observations, so the "
            "unit is not one market and the intervals would be wrong")
    return out


def quote_at(con, ticker, ts):
    """The last quote at or before `ts`. Used so the DECISION price and the
    RESTING price are the same observation -- see the look-ahead note in
    `evaluate`."""
    r = con.execute(
        "select bid_c, ask_c from candles where ticker=? and ts<=? "
        "and bid_c is not null and ask_c is not null "
        "order by ts desc limit 1", (ticker, ts)).fetchone()
    return (int(r[0]), int(r[1])) if r else None


def evaluate(con, band, tiers=None, rest_min=REST_MIN, before=CUTOFF,
             since=None, wrong_side=False, contracts=100, mode="into_play"):
    """
    ⚠ A LOOK-AHEAD I HAD TO FIX, AND IT IS THE WHOLE DESIGN.

    The first version rested a bid at the quote observed at t0-1 (the last
    minute before play) for the HOUR BEFORE t0-1. That is a price you do not
    know yet while the order is resting. Two causal repairs, and both are run:

      mode="prematch"   decide AND rest at T = t0 - rest_min, using the quote
                        at T for the band, the price and the whole window.
                        Nothing after T is consulted. Honest, and it asks
                        whether anyone will sell you a favourite before play.

      mode="into_play"  decide at the prematch quote (t0-1, which is what the
                        coordinator's table uses), then rest that bid from the
                        first minute of play onward. Also causal -- the price
                        is known before the order exists.

    **`into_play` is the realistic one and it is where the trap lives.** A
    resting bid below the market only fills when the price comes DOWN to it,
    i.e. when the favourite is in trouble. That is adverse selection by
    construction, and drop criterion 3 exists to catch it.
    """
    lo, hi = band
    fee_types = dict(con.execute("select series, fee_type from fees"))
    taker, mk_front, mk_back = [], [], []
    filled_won, unfilled_won = [], []
    n_fill_front = n_fill_back = 0
    spreads = []

    for tk, _ev, series, tier, t_lo, t0, pre_bid, pre_ask, result, _ct in \
            rows(con, lo, hi, tiers, before, since):
        won = 1 if result == "yes" else 0
        ask, bid = int(pre_ask), int(pre_bid)
        if not (0 < bid <= ask < 100):
            continue
        spreads.append(ask - bid)

        # --- taker arm: cross the spread, hold to settlement, no exit fee
        tk_fee = float(KF.fee_order_cents(ask, contracts)) / contracts
        taker.append((100.0 - ask if won else -float(ask)) - tk_fee)

        # --- maker arm, causal in both modes (see the docstring)
        if mode == "prematch":
            t_start = t_lo + t0 * 60 - rest_min * 60
            t_end = t_lo + t0 * 60
            q = quote_at(con, tk, t_start)
            if q is None:
                continue
            dbid, dask = q
            if not (0 < dbid <= dask < 100):
                continue
            dmid = (dbid + dask) / 2.0
            if not (lo <= dmid < hi):
                continue          # band membership judged at the SAME moment
            price_bid = dbid
        else:
            t_start = t_lo + t0 * 60
            t_end = t_start + rest_min * 60
            price_bid = bid
        tape = MF.trades_for(con, tk)
        qa = MF.QUEUE_AHEAD.get(tier, 1500)
        # a resting YES bid is reached by a taker SELLING yes; the wrong-side
        # placebo rests an ASK at the same level, which a BUYER reaches
        want = "yes" if wrong_side else "no"
        price = price_bid
        front, back = MF.fill_from_tape(tape, t_start, t_end, price, want,
                                        contracts, qa)
        ft = fee_types.get(series, "quadratic")
        sf = KF.SeriesFees("<s>", ft, Decimal(1))

        def net(got):
            if got <= 0:
                return None
            f = float(KF.maker_fee_order_cents(price, int(got), sf)) / got
            return (100.0 - price if won else -float(price)) - f

        nf, nb = net(front), net(back)
        mk_front.append(nf if nf is not None else 0.0)
        mk_back.append(nb if nb is not None else 0.0)
        if front > 0:
            n_fill_front += 1
            filled_won.append(won)
        else:
            unfilled_won.append(won)
        if back > 0:
            n_fill_back += 1

    n = len(taker)
    return {
        "band": f"{lo}-{hi}", "n": n,
        "spread": float(np.mean(spreads)) if spreads else float("nan"),
        "won": (float(np.mean(filled_won + unfilled_won))
                if (filled_won or unfilled_won) else float("nan")),
        "taker": boot(taker),
        "front": boot(mk_front), "back": boot(mk_back),
        "fill_front": n_fill_front / n if n else 0.0,
        "fill_back": n_fill_back / n if n else 0.0,
        "won_filled": float(np.mean(filled_won)) if filled_won else float("nan"),
        "won_unfilled": (float(np.mean(unfilled_won)) if unfilled_won
                         else float("nan")),
        "n_filled": len(filled_won), "n_unfilled": len(unfilled_won),
    }


def pct(c, price=92.0):
    """cents per contract -> percent of stake, which is the unit 021 uses."""
    return c / price * 100.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rest-min", type=int, default=REST_MIN)
    ap.add_argument("--mode", choices=("into_play", "prematch"),
                    default="into_play")
    ap.add_argument("--wrong-side", action="store_true",
                    help="PLACEBO P1: rest an ASK instead of a bid")
    ap.add_argument("--open-the-check-period", action="store_true")
    a = ap.parse_args()
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

    before = None if a.open_the_check_period else CUTOFF
    since = CUTOFF if a.open_the_check_period else None
    label = ("CHECK PERIOD 2026-08-02 -> 08-20" if a.open_the_check_period
             else "selection 2026-06-14 -> 08-01")
    if a.wrong_side:
        label += "   [PLACEBO: quoting the WRONG side]"

    print(f"Maker execution on prematch favourites   mode={a.mode}   "
          f"rest {a.rest_min} min   [{label}]")
    print()
    print("⚠ JOB 0 FIRST -- availability, per GUARDS #24. An edge that cannot")
    print("   be filled is not an edge, and fills that only happen when the")
    print("   favourite wobbles are a selection effect, not an execution win.")
    print()
    print(f"  {'band':>10}{'n':>6}{'spread':>8}{'won':>7}"
          f"{'fill front':>12}{'fill back':>11}"
          f"{'won|filled':>12}{'won|unfilled':>14}")
    res = {}
    for b in BANDS:
        r = evaluate(con, b, rest_min=a.rest_min, before=before, since=since,
                     wrong_side=a.wrong_side, mode=a.mode)
        res[b] = r
        print(f"  {r['band']:>10}{r['n']:>6}{r['spread']:>7.1f}c"
              f"{r['won'] * 100:>6.1f}%{r['fill_front']:>11.1%}"
              f"{r['fill_back']:>11.1%}{r['won_filled'] * 100:>11.1f}%"
              f"{r['won_unfilled'] * 100:>13.1f}%")

    print()
    print("MONEY -- per 100 dollars staked, held to settlement, no exit fee")
    print(f"  {'band':>10}{'taker at the ask':>26}"
          f"{'maker, front of queue':>28}{'maker, back of queue':>28}")
    for b in BANDS:
        r = res[b]
        mid = (b[0] + b[1]) / 2
        f = lambda t: (f"{pct(t[0], mid):>+7.2f}% "                # noqa: E731
                       f"[{pct(t[1], mid):+6.2f},{pct(t[2], mid):+6.2f}]")
        print(f"  {r['band']:>10}{f(r['taker']):>26}"
              f"{f(r['front']):>28}{f(r['back']):>28}")

    print()
    print("THE REGISTERED ARMS -- 90 to 95c only")
    for name, tiers in ARMS.items():
        parts = [evaluate(con, b, tiers=tiers, rest_min=a.rest_min,
                          before=before, since=since,
                          wrong_side=a.wrong_side, mode=a.mode)
                 for b in ((90, 92.5), (92.5, 95))]
        n = sum(p["n"] for p in parts)
        if not n:
            print(f"  {name}: nothing in band")
            continue
        w = sum(p["fill_front"] * p["n"] for p in parts) / n
        tk = sum(p["taker"][0] * p["n"] for p in parts) / n
        fr = sum(p["front"][0] * p["n"] for p in parts) / n
        bk = sum(p["back"][0] * p["n"] for p in parts) / n
        print(f"  {name:<34} n={n:>4}  fills {w:>5.1%}   "
              f"taker {pct(tk, 92.5):>+6.2f}%   front {pct(fr, 92.5):>+6.2f}%"
              f"   back {pct(bk, 92.5):>+6.2f}%")


if __name__ == "__main__":
    sys.exit(main())
