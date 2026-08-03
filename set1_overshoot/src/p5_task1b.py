"""Task 1b -- maker versus taker, and the adverse selection that decides it.

Fading the favourite means selling the favourite (equivalently buying the
underdog). As a taker you hit the favourite's bid and pay half-spread +
slippage + full fee. As a maker you rest a sell above the bid and pay none of
the first two and a reduced fee -- if you fill.

The fill model is deliberately pessimistic, per the brief:

  * Last in queue. Touching my price is not enough; the book must trade
    STRICTLY THROUGH it. In favourite terms, some later minute's bid HIGH must
    exceed my resting level.
  * One contract, all-or-nothing. Kalshi's candlesticks carry no depth, so size
    cannot be modelled. At real size the fill rate would be lower, never higher,
    so the figures here are an upper bound on fill and therefore on P&L.
  * Unfilled opportunities are counted as zero P&L in the per-opportunity
    number. Reporting only the fills would be survivorship.

The structural worry, which is the point of the task: a resting sell of the
favourite can ONLY fill when the favourite ticks up, which is by construction
the direction that hurts a fade. Whether the price improvement survives that is
what decides the phase.
"""
import argparse
import pathlib

import numpy as np
import pandas as pd

import fees
import ledger
import p2_calib as p2

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# VERIFIED from GET /series/{ticker}.fee_type on 2026-08-01, not assumed:
#   KXATPMATCH, KXWTAMATCH            -> 'quadratic_with_maker_fees'
#   KXATPCHALLENGERMATCH, KXITF*      -> 'quadratic'  (taker-only, maker = 0)
# Challenger + ITF is ~91% of the tennis book, so the maker fee is ZERO for the
# overwhelming majority of the sample. The sibling crypto session verified the
# same field reads 'quadratic' on every crypto series; tennis is the first place
# in this project where maker fees exist at all.
#
# ⚠ THE RATE BELOW IS SUPERSEDED — corrected 2026-08-03, kept for reference.
#
# This read Kalshi's published schedule as a FLAT 0.25c/contract and said so
# honestly ("NOT verifiable from the read-only API, so it is flagged rather
# than trusted"). The schedule itself has now been retrieved (effective
# 7 Jul 2026, see common/kalshi_fees.py):
#
#     maker  roundup(M x 0.0175 x C x P x (1-P))     M defaults to 0
#
# It is the SAME QUADRATIC SHAPE as taker at a quarter of the rate — NOT a
# flat per-contract charge. The two cross: at 95c the true rate is
# 0.083c/contract against the 0.25c assumed here; at 50c it is 0.4375c.
# So this arm is wrong in a price-dependent direction, harsher at the tails
# and softer in the middle.
#
# S008's CONCLUSION IS UNAFFECTED: all 15 maker configurations were net
# negative under both this arm and the pessimistic quarter-of-taker arm, and
# the quarter-of-taker arm is the one that turned out to be correct. The
# tour mapping (who pays at all) was right and is confirmed by the API:
# KXATPMATCH/KXWTAMATCH are `quadratic_with_maker_fees`, Challenger and ITF
# are `quadratic`. Only the RATE was wrong.
#
# Prefer common.kalshi_fees.maker_fee_order_cents() for new work.
MAKER_FEE_BY_TOUR = {"ATP": 0.25, "WTA": 0.25,
                     "CHALL": 0.0, "ITF-M": 0.0, "ITF-W": 0.0}


def maker_fee_verified(tour_arr, px_arr):
    return np.array([MAKER_FEE_BY_TOUR.get(t, 0.25) for t in tour_arr])


def maker_fee_pessimistic(tour_arr, px_arr):
    """Alternative arm: pretend every series charges a quarter of taker.

    Named 'pessimistic' but it does NOT dominate the verified schedule
    everywhere -- the arms cross. On ITF/Challenger (verified fee zero) it is
    always harsher. On ATP/WTA it is harsher at mid prices but CHEAPER at the
    tails, because a quarter of the quadratic taker fee falls to 0.083c at 95c
    while the verified flat charge stays at 0.25c. Pinned in tests.
    """
    return np.array([0.25 * float(fees.fee_rate_cents(int(round(p))))
                     for p in px_arr])


MAKER_FEES = {
    "verified schedule": maker_fee_verified,
    "pessimistic (1/4 taker everywhere)": maker_fee_pessimistic,
}
WINDOWS = [5, 10, 20, 30, 10_000]


def taker(e):
    """Baseline: cross the spread now, pay slippage and the full fee."""
    fill = np.minimum(100.0 - e["entry_bid"].values + p2.SLIP, 99.0)
    fee = np.array([float(fees.fee_rate_cents(int(round(f)))) for f in fill])
    won = 1.0 - e["fav_won"].values
    return 100.0 * won - fill - fee, fill, fee


def rest_levels(e, style):
    """Resting price in FAVOURITE terms. Higher = better for a fade."""
    b = e["entry_bid"].values
    a = e["entry_ask"].values
    if style == "improve":                 # step inside the spread
        return np.where(a > b + 1, b + 1, a)
    if style == "join_ask":
        return a.copy()
    if style == "passive":                 # behind the ask, better price
        return np.minimum(a + 1, 99.0)
    raise ValueError(style)


def simulate(e, rows_idx, bid_h, style, window, dur):
    """Returns (filled, fill_minute, level). Fill needs a strict trade-through."""
    L = rest_levels(e, style)
    ei = e["entry_idx"].values.astype(int)
    n = len(e)
    filled = np.zeros(n, bool)
    at = np.full(n, -1)
    T = bid_h.shape[1]
    for k in range(n):
        r = rows_idx[k]
        lo = ei[k] + 1
        hi = int(min(dur[k], T, lo + window))
        if hi <= lo:
            continue
        seg = bid_h[r, lo:hi]
        hit = np.where(seg > L[k])[0]      # strictly through: last in queue
        if len(hit):
            filled[k] = True
            at[k] = lo + int(hit[0])
    return filled, at, L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="paths")
    ap.add_argument("--rule", default="deep:30")
    ap.add_argument("--floor", type=int, default=38)
    args = ap.parse_args()

    st, bid, ask, mid = p2.load(args.tag)
    bid_h, ask_l = p2.load_extremes(args.tag)
    rng = np.random.default_rng(1729)

    ev = p2.build_events(st, bid, ask, mid, args.rule, 0,
                         min_minute=args.floor)
    ev["row"] = np.arange(len(ev))
    e = ev[ev["is_event"]].copy()
    rows_idx = e["row"].values
    dur = e["dur_min"].values.astype(int)
    won = 1.0 - e["fav_won"].values
    out = []

    def w(s=""):
        print(s, flush=True)
        out.append(s)

    lbl = f"{args.rule}@{args.floor}" if args.floor else args.rule
    w("# Task 1b — maker versus taker")
    w("")
    w(f"Entry rule `{lbl}`, n = **{len(e):,}** opportunities. "
      f"Fade = sell the favourite.")
    w("")
    tk_net, tk_fill, tk_fee = taker(e)
    tlo, thi = p2.bootstrap_ci(tk_net, rng, n=8000)
    w(f"**Taker baseline**: fills 100% by assumption, mean fill "
      f"{tk_fill.mean():.2f}¢, fee {tk_fee.mean():.2f}¢, "
      f"net **{tk_net.mean():+.3f}¢** [{tlo:+.3f}, {thi:+.3f}].")
    w("")

    # ---------------- fill rates -----------------------------------------
    w("## Fill rates")
    w("")
    w("Fill requires the favourite's bid to trade **strictly above** the "
      "resting level in")
    w("some later minute — last in queue, no credit for merely being touched.")
    w("")
    w("| resting style | mean level ¢ | 5 min | 10 min | 20 min | 30 min | "
      "to end of match |")
    w("|---|---|---|---|---|---|---|")
    grids = {}
    for style in ("improve", "join_ask", "passive"):
        L = rest_levels(e, style)
        cells = []
        for win in WINDOWS:
            f, at, _ = simulate(e, rows_idx, bid_h, style, win, dur)
            grids[(style, win)] = (f, at, L)
            cells.append(f"{f.mean():.1%}")
        w(f"| {style} | {L.mean():.2f} | " + " | ".join(cells) + " |")
    w("")

    # ---------------- headline grid --------------------------------------
    w("## Net expectancy, maker vs taker")
    w("")
    w("`per fill` is the mean over filled trades only. **`per opportunity` is "
      "the number")
    w("that matters** — unfilled chances earn nothing, and a strategy is judged "
      "on the")
    w("signals it acts on, not the subset it happened to catch.")
    w("")
    w("| resting style | window | fill % | fill px ¢ | " +
      " | ".join(f"per fill, {k} ¢" for k in MAKER_FEES) +
      " | per opportunity (verified fee) ¢ |")
    w("|---|---|---|---|" + "---|" * (len(MAKER_FEES) + 1))
    best = None
    for style in ("improve", "join_ask", "passive"):
        for win in WINDOWS:
            f, at, L = grids[(style, win)]
            if f.sum() < 50:
                continue
            cost = 100.0 - L[f]
            gross = 100.0 * won[f] - cost
            tours = e["tour"].values[f]
            cells, per_opp = [], None
            for name, fn in MAKER_FEES.items():
                fee = fn(tours, cost)
                net = gross - fee
                cells.append(f"{net.mean():+.3f}")
                if name == "verified schedule":
                    full = np.zeros(len(e))
                    full[f] = net
                    per_opp = full
            wlab = "end" if win > 1000 else str(win)
            w(f"| {style} | {wlab} | {f.mean():.1%} | {cost.mean():.2f} | "
              + " | ".join(cells) + f" | **{per_opp.mean():+.3f}** |")
            ledger.add(phase="5-1b", factor="maker fill",
                       level=f"{style}/{wlab}min", n=int(f.sum()),
                       net_c=round(float(per_opp.mean()), 4),
                       note=f"fill {f.mean():.3f}; per-opportunity, 1/4 fee")
            if best is None or per_opp.mean() > best[0]:
                best = (per_opp.mean(), style, win, f, at, L, per_opp)
    w("")

    # ---------------- adverse selection ----------------------------------
    w("## Adverse selection — the pre-specified kill test")
    w("")
    w("A resting sell of the favourite fills only when the favourite ticks "
      "**up**. If the")
    w("fills are systematically the matches about to go wrong, the fee and "
      "spread saving")
    w("is illusory.")
    w("")
    w("| resting style | window | fill % | dog win, filled | dog win, all | "
      "shift pp | fav mid at signal | fav mid at fill | drift ¢ |")
    w("|---|---|---|---|---|---|---|---|---|")
    for style in ("improve", "join_ask", "passive"):
        for win in (10, 30, 10_000):
            f, at, L = grids[(style, win)]
            if f.sum() < 50:
                continue
            mf = mid[rows_idx[f], np.clip(at[f], 0, mid.shape[1] - 1)]
            ms = e["entry_mid"].values[f]
            wlab = "end" if win > 1000 else str(win)
            w(f"| {style} | {wlab} | {f.mean():.1%} | {won[f].mean():.4f} | "
              f"{won.mean():.4f} | {100 * (won[f].mean() - won.mean()):+.2f} | "
              f"{ms.mean():.2f} | {np.nanmean(mf):.2f} | "
              f"{np.nanmean(mf) - ms.mean():+.2f} |")
    w("")

    # decomposition on the best cell
    if best is not None:
        _, style, win, f, at, L, per_opp = best
        cost = 100.0 - L[f]
        fee_m = maker_fee_verified(e["tour"].values[f], cost)
        maker_net = 100.0 * won[f] - cost - fee_m
        tk_same = tk_net[f]
        w("### Decomposition on the best cell "
          f"(`{style}`, {'end' if win > 1000 else str(win) + ' min'})")
        w("")
        w("Same matches, both ways — this isolates the price improvement from "
          "the")
        w("selection effect.")
        w("")
        w(f"| quantity | value |")
        w("|---|---|")
        w(f"| opportunities | {len(e):,} |")
        w(f"| filled | {int(f.sum()):,} ({f.mean():.1%}) |")
        w(f"| price improvement vs taker, same matches | "
          f"{(tk_fill[f] - cost).mean():+.3f} ¢ |")
        w(f"| fee saving vs taker, same matches | "
          f"{(tk_fee[f] - fee_m).mean():+.3f} ¢ |")
        w(f"| **gross saving from being a maker** | "
          f"**{((tk_fill[f] + tk_fee[f]) - (cost + fee_m)).mean():+.3f} ¢** |")
        w(f"| underdog win rate, all opportunities | {won.mean():.4f} |")
        w(f"| underdog win rate, filled only | {won[f].mean():.4f} |")
        w(f"| **cost of adverse selection** | "
          f"**{100 * (won[f].mean() - won.mean()):+.3f} ¢** "
          f"(1 pp of win rate = 1 ¢) |")
        w("")
        # ---- four-way decomposition, per opportunity, exact identity -----
        fr = f.mean()
        mid_at_entry = e["entry_mid"].values
        fair_dog = 100.0 - mid_at_entry            # underdog fair value
        y_all, y_fil = won.mean(), won[f].mean()
        t_gross = fr * (100.0 * y_all - fair_dog[f].mean())
        t_adv = fr * 100.0 * (y_fil - y_all)
        t_impr = fr * (fair_dog[f].mean() - cost.mean())
        t_fee = -fr * fee_m.mean()
        total = t_gross + t_adv + t_impr + t_fee
        w("")
        w("### Four-way decomposition, per opportunity")
        w("")
        w("Reported in the same units as the sibling crypto market-making run "
          "so the two")
        w("are comparable, but **this is not two-sided market making** and the "
          "terms are")
        w("not the same objects. A passive directional entry quotes one side, "
          "so there is")
        w("no bid-ask capture; the analogue is price improvement against fair "
          "value. And")
        w("because the position is held to settlement, **the residual is "
          "marked at the")
        w("actual 0/100 outcome, never defaulted to 0.5** — the inventory-carry "
          "defect that")
        w("fabricated +2.96¢ in the crypto session cannot arise here.")
        w("")
        w("| term | ¢/opportunity |")
        w("|---|---|")
        w(f"| edge at fair value ({fr:.1%} × {100 * y_all:.2f}% vs "
          f"{fair_dog[f].mean():.2f}¢) | {t_gross:+.3f} |")
        w(f"| **adverse selection** ({100 * (y_fil - y_all):+.2f} pp on filled) "
          f"| **{t_adv:+.3f}** |")
        w(f"| price improvement vs fair value | {t_impr:+.3f} |")
        w(f"| maker fees (verified schedule) | {t_fee:+.3f} |")
        w(f"| **net per opportunity** | **{total:+.3f}** |")
        w(f"| identity check vs direct calculation | "
          f"{per_opp.mean():+.3f} (diff {total - per_opp.mean():+.4f}) |")
        w("")
        w(f"| bottom line | ¢/contract |")
        w("|---|---|")
        w(f"| taker, all {len(e):,} opportunities | {tk_net.mean():+.3f} |")
        w(f"| taker, the {int(f.sum()):,} that would have filled | "
          f"{tk_same.mean():+.3f} |")
        w(f"| maker, those same fills | {maker_net.mean():+.3f} |")
        w(f"| **maker, per opportunity** | **{per_opp.mean():+.3f}** |")
        lo, hi = p2.bootstrap_ci(per_opp, rng, n=10000)
        w(f"| 95% CI, match-clustered | [{lo:+.3f}, {hi:+.3f}] |")
        if "close_time" in e:
            day = pd.to_datetime(e["close_time"], utc=True).dt.strftime(
                "%Y-%m-%d").values
            keys = np.unique(day)
            gmap = {k: np.where(day == k)[0] for k in keys}
            bs = []
            for _ in range(6000):
                pick = rng.choice(len(keys), size=len(keys))
                idx = np.concatenate([gmap[keys[i]] for i in pick])
                bs.append(per_opp[idx].mean())
            w(f"| 95% CI, day-clustered | "
              f"[{np.percentile(bs, 2.5):+.3f}, "
              f"{np.percentile(bs, 97.5):+.3f}] |")

    (ROOT / "reports" / "p5_task1b.md").write_text("\n".join(out),
                                                   encoding="utf-8")
    print(f"\n-> {ROOT / 'reports' / 'p5_task1b.md'}")


if __name__ == "__main__":
    main()
