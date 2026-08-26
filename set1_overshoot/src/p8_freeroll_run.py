"""Phase 8 -- run the free-roll overlay over REAL trade lists.

`common/freeroll.py` is the overlay. This file is only the plumbing that turns
two existing pieces of work into position lists and feeds them through it.

WHY TWO LISTS, AND WHY THEY ARE THE RIGHT TWO
---------------------------------------------
His example buys at 10c and sells at 20c. **A doubling is arithmetically
impossible above 50c**, so the overlay's activation rate depends entirely on
where a strategy enters. The two real trade lists in this repo sit either side
of that line:

  FADE      the set-1 deep fade, `deep:30@38`. Buys the underdog at about 69c.
            A 2x rule can NEVER fire on it.
  REBOUND   the deep-dip cells from mailbox 019. Buys at about 30c, where a
            1.5x move to 45c is an ordinary afternoon.

**Reporting both is the point.** An overlay that only works on cheap entries is
a fact about which strategies can use it, and that is exactly what he asked to
be told.

Neither strategy makes money. That is deliberate and it is stated in every
table: **the overlay is being measured for what it does to the SHAPE of a
return, not for rescuing a bad edge.** Keeping the two apart is how an exit rule
is stopped from taking credit for a signal.
"""
from __future__ import annotations

import argparse
import pathlib
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent))

import p6_maker_fill as MF                        # noqa: E402
from common import freeroll as FR                 # noqa: E402

DB = ROOT / "data" / "maker.db"
CUTOFF = "2026-08-02"

#: How many contracts a position holds. His example is 10 for $1 at 10c; the
#: count matters because whole-contract rounding decides whether a scale-out is
#: possible at all, so it is a stated parameter and not a hidden one.
CONTRACTS = 10


def fade_positions(con, before=CUTOFF):
    """The set-1 deep fade: buy the underdog at the ask, hold to settlement."""
    out = []
    fee_type = dict(con.execute("select series, fee_type from fees"))
    for ev, fav, dog, e, p_r1, p_r2, ask_dog in MF.iter_events(
            con, depth=30.0, min_minute=38, pre_spread_max=10, before=before):
        pf = MF.load_paths(con, fav[0])
        if pf is None:
            continue
        fb, fa = pf
        # the underdog's book, mirrored off the favourite's -- one clock, the
        # same fix RESULTS_MAKER.md documents
        tape = [(100 - int(fa[i]), 100 - int(fb[i]))
                for i in range(e + 1, len(fb))
                if fb[i] >= 0 and fa[i] >= 0]
        if not tape or not (0 < ask_dog < 100):
            continue
        open_ts = fav[4] + (fav[5] + e + 1) * 60
        out.append(FR.Position(pid=ev, entry_ask_c=ask_dog,
                               contracts=CONTRACTS, tape=tape,
                               won=(dog[8] == "yes"),
                               fee_type=fee_type.get(fav[2], "quadratic"),
                               open_ts=open_ts,
                               settle_ts=open_ts + len(tape) * 60 + 60))
    return out


def rebound_positions(con, peak=80, dest=30, before=CUTOFF, tiers=("itf",)):
    """The deep-dip cells: a contract that peaked at `peak` and fell to `dest`.

    One event per ticker at its FIRST qualifying dip, exactly as 019 defines it,
    so an oscillating match cannot contribute ten correlated positions.
    """
    out = []
    fee_type = dict(con.execute("select series, fee_type from fees"))
    q = ("select m.ticker, m.series, m.tier, m.result, s.t_lo, s.t0 "
         "from markets m join state s on s.ticker = m.ticker "
         "where m.result in ('yes','no') and m.close_time < ? and s.ok = 1")
    rows = [r for r in con.execute(q, (before,)) if r[2] in tiers]
    for tk, series, _tier, result, t_lo, t0 in rows:
        p = MF.load_paths(con, tk)
        if p is None:
            continue
        bid, ask = p
        run_peak = -1.0
        for i in range(len(bid)):
            if bid[i] < 0 or ask[i] < 0:
                continue
            mid = (int(bid[i]) + int(ask[i])) / 2.0
            if mid > run_peak:
                run_peak = mid
            if run_peak < peak or mid > dest:
                continue
            # first qualifying dip; buy at the ask on the NEXT bar
            j = i + 1
            if j >= len(bid) or bid[j] < 0 or ask[j] < 0:
                break
            entry = int(ask[j])
            tape = [(int(bid[k]), int(ask[k])) for k in range(j + 1, len(bid))
                    if bid[k] >= 0 and ask[k] >= 0]
            if tape and 0 < entry < 100:
                open_ts = t_lo + (t0 + j) * 60
                out.append(FR.Position(pid=tk, entry_ask_c=entry,
                                       contracts=CONTRACTS, tape=tape,
                                       won=(result == "yes"),
                                       fee_type=fee_type.get(series,
                                                             "quadratic"),
                                       open_ts=open_ts,
                                       settle_ts=open_ts + len(tape) * 60 + 60))
            break
    return out


RULES = [
    ("hold to settlement", FR.HOLD),
    ("1.25x entry, recover all", FR.Rule("multiple", 1.25)),
    ("1.5x entry, recover all", FR.Rule("multiple", 1.5)),
    ("2x entry, recover all", FR.Rule("multiple", 2.0)),
    ("3x entry, recover all", FR.Rule("multiple", 3.0)),
    ("+5c, recover all", FR.Rule("profit", 5)),
    ("+10c, recover all", FR.Rule("profit", 10)),
    ("+20c, recover all", FR.Rule("profit", 20)),
    ("2x entry, recover half", FR.Rule("multiple", 2.0, target=0.5)),
    ("2x entry, sell a third", FR.Rule("multiple", 2.0, sizing="third")),
    ("+10c, sell a half", FR.Rule("profit", 10, sizing="half")),
    ("price 50c, recover all", FR.Rule("price", 50)),
    ("price 70c, recover all", FR.Rule("price", 70)),
]


def show(name, ps, bankroll=None):
    print("=" * 84)
    tag = ("unlimited cash" if bankroll is None else
           f"bankroll ${bankroll/100:.0f}, positions OVERLAP in time")
    print(f"{name}   {len(ps):,} positions   {tag}")
    if ps:
        avg = sum(p.entry_ask_c for p in ps) / len(ps)
        wins = sum(1 for p in ps if p.won) / len(ps)
        print(f"  entered at {avg:.1f}c on average, won {wins:.1%} of the time")
    print("=" * 84)
    # ⚠ Under a bankroll, ROI-on-staked compares DIFFERENT position sets --
    # each rule takes a different subset, so the percentages are not
    # comparable. The honest metric on a fixed bankroll is dollars of profit
    # from the same starting cash, alongside how many bets were actually taken.
    if bankroll is None:
        print(f"  {'rule':<28}{'fires':>7}{'return':>9}{'worst run':>11}"
              f"{'vs hold':>9}")
    else:
        print(f"  {'rule':<28}{'fires':>7}{'bets':>7}{'profit $':>10}"
              f"{'vs hold $':>11}{'worst run':>11}")
    base = None
    for label, rule in RULES:
        r = (FR.simulate_concurrent(ps, rule, bankroll)
             if bankroll is not None else FR.simulate(ps, rule))
        if base is None:
            base = r
        if bankroll is None:
            d = (r.net_c - base.net_c) / base.staked_c * 100                 if base.staked_c else 0
            print(f"  {label:<28}{r.activation_rate:>6.1%}"
                  f"{r.roi * 100:>+8.1f}%{r.max_drawdown_c / 100:>10.2f}$"
                  f"{d:>+8.1f}%")
        else:
            print(f"  {label:<28}{r.activation_rate:>6.1%}{r.n:>7,}"
                  f"{r.net_c / 100:>+9.2f}${(r.net_c - base.net_c) / 100:>+10.2f}"
                  f"{r.max_drawdown_c / 100:>10.2f}$")
    # why the ones that did not fire, did not
    r = (FR.simulate_concurrent(ps, FR.Rule("multiple", 2.0), bankroll)
         if bankroll is not None else FR.simulate(ps, FR.Rule("multiple", 2.0)))
    print(f"\n  of {r.n:,} positions under the 2x rule: {r.activated:,} fired, "
          f"{r.unreachable:,} could never fire (2x is above 100c),")
    print(f"  {r.never_triggered:,} never reached the trigger, "
          f"{r.too_small:,} were too small to sell a whole contract")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bankroll", type=float, default=None,
                    help="dollars; omit for the unconstrained arm")
    a = ap.parse_args()
    bank = a.bankroll * 100 if a.bankroll else None

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    print("Both strategies below LOSE money. That is deliberate: the overlay is")
    print("measured for what it does to the SHAPE of a return, never for")
    print("rescuing a bad edge. Predictive edge is what the strategy picks;")
    print("exit management is what the overlay does to the same picks.\n")

    show("FADE -- buy the underdog after a 30c collapse (enters ~69c)",
         fade_positions(con), bank)
    print()
    show("REBOUND -- ITF contract that peaked at 80c and fell to 30c",
         rebound_positions(con, peak=80, dest=30), bank)


if __name__ == "__main__":
    sys.exit(main())
