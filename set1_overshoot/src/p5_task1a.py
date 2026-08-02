"""Task 1a -- hold-to-settlement vs round trip, and an anatomy of the 3.6c bar.

The Phase 5 brief supposes the Phase 2 fade configurations may have been round
trips paying two fees, in which case switching to hold-to-settlement would be
worth ~1.5c against a ~1.1c shortfall and would flip the result on its own.

That is checked here rather than assumed, because if it is wrong the whole
priority ladder of this phase changes.

It also decomposes the cost bar into its three parts, because "3.6c of cost"
hides the fact that the fee is only a minority of it and the levers therefore
have very different ceilings.
"""
import pathlib

import numpy as np
import pandas as pd

import fees
import p2_calib as p2

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RULES = [("deep:12", 0), ("deep:30", 38), ("deep:20", 38), ("deep:25", 0),
         ("cp", 0), ("fixed", 45)]


def fade(e, slip=p2.SLIP, exit_leg=False):
    """Underdog bought by selling the favourite. One fee unless exit_leg."""
    fill = np.minimum(100.0 - e["entry_bid"].values + slip, 99.0)
    won = 1.0 - e["fav_won"].values
    fee = np.array([float(fees.fee_rate_cents(int(round(f)))) for f in fill])
    if exit_leg:
        # settle-equivalent exit: close the position at the terminal price,
        # which is 100 or 0, so the second fee is at the extreme and is small.
        exitpx = 100.0 * won
        fee = fee + np.array([float(fees.fee_rate_cents(int(round(x))))
                              for x in exitpx])
    return 100.0 * won - fill - fee, fill, fee


def drawdown(pnl, rng, n_perm=200):
    """Worst peak-to-trough in cents per contract, over the realised order and
    over shuffles of it -- the realised order is one draw, not the risk."""
    def mdd(x):
        c = np.cumsum(x)
        return float((np.maximum.accumulate(c) - c).max())
    real = mdd(pnl)
    perms = [mdd(rng.permutation(pnl)) for _ in range(n_perm)]
    return real, float(np.median(perms)), float(np.percentile(perms, 95))


def main():
    st, bid, ask, mid = p2.load("paths")
    rng = np.random.default_rng(101)
    out = []

    def w(s=""):
        print(s, flush=True)
        out.append(s)

    w("# Task 1a — hold to settlement vs round trip")
    w("")
    w("## The premise is false, and it changes this phase's priorities")
    w("")
    w("The Phase 2 fade was **already hold-to-settlement**. From "
      "`src/p2_fade.py`:")
    w("")
    w("```python")
    w("fee = np.array([float(fees.fee_rate_cents(int(round(f)))) "
      "for f in fill])")
    w("net = 100.0 * dog_won - fill - fee      # one fee, no exit leg")
    w("```")
    w("")
    w("`net` pays the settlement value `100 * dog_won` against a single entry "
      "fill and a")
    w("single fee. There is no target, no stop and no exit trade anywhere in "
      "it. The")
    w("−1.10¢ headline already banks the whole hold-to-settlement saving.")
    w("")
    w("The round-trip figures the brief is thinking of are the **Phase 3 exit "
      "surface**,")
    w("which was a separate experiment on the *favourite* side, not the fade. "
      "There, all")
    w("25 target/stop cells lost more than hold-to-settlement, which is the "
      "same lesson")
    w("pointing the same way — but that saving is spent, not available.")
    w("")

    # Demonstrate the counterfactual: what a round trip WOULD have cost.
    w("### What a round trip would have cost, for completeness")
    w("")
    w("| entry rule | n | hold-to-settlement net ¢ | forced round-trip net ¢ | "
      "cost of the second leg |")
    w("|---|---|---|---|---|")
    for rule, floor in RULES:
        ev = p2.build_events(st, bid, ask, mid, rule,
                             0 if rule != "fixed" else floor,
                             min_minute=floor if rule != "fixed" else 0)
        e = ev[ev["is_event"]]
        if len(e) < 100:
            continue
        h, _, _ = fade(e)
        r, _, _ = fade(e, exit_leg=True)
        lbl = rule + (f"@{floor}" if floor and rule != "fixed" else "")
        w(f"| {lbl} | {len(e):,} | {h.mean():+.3f} | {r.mean():+.3f} | "
          f"{r.mean() - h.mean():+.3f} |")
    w("")
    w("The second leg is cheap here only because a settled position exits at "
      "0 or 100,")
    w("where the fee formula bottoms out. An early exit at a mid price would "
      "cost the")
    w("full ~1.7¢, which is what the Phase 3 surface measured.")
    w("")

    # ---------------- cost anatomy ---------------------------------------
    w("## Anatomy of the cost bar — where the 3.6¢ actually is")
    w("")
    w("Best-targeted rule `deep:30@38`, the one carrying the −2.53 pp "
      "undershoot.")
    w("")
    ev = p2.build_events(st, bid, ask, mid, "deep:30", 0, min_minute=38)
    e = ev[ev["is_event"]]
    fav_bid = e["entry_bid"].values
    fav_ask = e["entry_ask"].values
    fav_mid = e["entry_mid"].values
    dog_mid = 100.0 - fav_mid
    dog_taker = 100.0 - fav_bid
    half_spread = dog_taker - dog_mid
    fill = np.minimum(dog_taker + p2.SLIP, 99.0)
    fee = np.array([float(fees.fee_rate_cents(int(round(f)))) for f in fill])
    won = 1.0 - e["fav_won"].values

    rows = [
        ("fair value at entry (underdog mid)", dog_mid.mean(), ""),
        ("half-spread paid to cross", half_spread.mean(),
         "avoidable as a maker"),
        ("assumed slippage", float(p2.SLIP),
         "avoidable as a maker; an assumption, not measured"),
        ("exchange fee (taker)", fee.mean(),
         "up to 3/4 avoidable as a maker"),
    ]
    w("| component | ¢/contract | avoidable? |")
    w("|---|---|---|")
    for name, v, note in rows:
        w(f"| {name} | {v:.3f} | {note} |")
    total_cost = half_spread.mean() + p2.SLIP + fee.mean()
    w(f"| **total cost above fair value** | **{total_cost:.3f}** | |")
    w("")
    w(f"- observed underdog win rate: **{100 * won.mean():.2f}%**")
    w(f"- fair value implies: **{dog_mid.mean():.2f}%**")
    w(f"- **gross edge: {100 * won.mean() - dog_mid.mean():+.2f} pp**")
    w(f"- **net after cost: {100 * won.mean() - fill.mean() - fee.mean():+.3f} "
      f"¢/contract**")
    w("")
    w("So the fee is **"
      f"{100 * fee.mean() / total_cost:.0f}%** of the cost bar, not all of it. "
      "Spread and")
    w("slippage together are "
      f"**{100 * (half_spread.mean() + p2.SLIP) / total_cost:.0f}%**. "
      "That reorders the phase:")
    w("")
    w("| lever | ceiling ¢ | note |")
    w("|---|---|---|")
    w(f"| 1a hold to settlement | **0.000** | already banked |")
    w(f"| 1b maker, fee only (÷4) | {0.75 * fee.mean():.3f} | "
      f"if Kalshi charges 1/4 taker |")
    w(f"| 1b maker, fee to zero | {fee.mean():.3f} | "
      f"if tennis has no maker fee |")
    w(f"| 1b maker, no crossing + no slippage | "
      f"{half_spread.mean() + p2.SLIP:.3f} | the larger half of the prize |")
    w(f"| **1b maker, everything** | **"
      f"{half_spread.mean() + p2.SLIP + fee.mean():.3f}** | "
      f"vs a {-(100 * won.mean() - fill.mean() - fee.mean()):.3f}¢ gap "
      f"to close |")
    w(f"| 1c price geometry | ≤{fee.mean():.3f} | reallocates within the fee |")
    w(f"| 1d spread filter | ≤{half_spread.mean():.3f} | "
      f"reallocates within the spread |")
    w("")
    w("**1b is the whole phase.** 1c and 1d can only redistribute components "
      "1b already")
    w("targets, and 1a is spent. The maker line also has the one failure mode "
      "that could")
    w("kill it outright — a resting order that fades a favourite fills "
      "precisely when the")
    w("favourite is ticking up, which is adverse selection by construction. "
      "That is tested")
    w("next and is the pivot of this phase.")
    w("")

    # ---------------- distribution and drawdown ---------------------------
    w("## The distribution behind the mean, and drawdown")
    w("")
    w("Hold-to-settlement has no stop, so the mean hides a binary payoff. "
      "Per contract:")
    w("")
    net, _, _ = fade(e)
    real, med, p95 = drawdown(net, rng)
    w(f"- n = {len(net):,} positions, mean **{net.mean():+.3f}¢**, "
      f"sd {net.std():.1f}¢")
    w(f"- wins {100 * (net > 0).mean():.1f}% of the time, "
      f"averaging {net[net > 0].mean():+.1f}¢")
    w(f"- loses {100 * (net < 0).mean():.1f}% of the time, "
      f"averaging {net[net < 0].mean():+.1f}¢")
    w(f"- worst single position **{net.min():+.1f}¢**, "
      f"best **{net.max():+.1f}¢**")
    w("")
    w(f"Worst peak-to-trough, cumulative ¢ per 1 contract per match:")
    w(f"- in the realised chronological order: **{real:,.0f}¢**")
    w(f"- median over 200 shuffles: {med:,.0f}¢, 95th percentile "
      f"{p95:,.0f}¢")
    w("")
    w("At one contract per match that is a "
      f"**${real / 100:,.0f}** peak-to-trough on a strategy whose mean is "
      f"negative — the drawdown figure is included because it is the honest "
      f"companion to any expectancy number, not because this configuration is "
      f"worth trading.")

    (ROOT / "reports" / "p5_task1a.md").write_text("\n".join(out),
                                                   encoding="utf-8")
    print(f"\n-> {ROOT / 'reports' / 'p5_task1a.md'}")


if __name__ == "__main__":
    main()
