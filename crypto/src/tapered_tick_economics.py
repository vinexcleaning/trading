"""TASK 4 (part) — recompute wing economics with the CORRECT tapered tick.

All 14 fifteen-minute crypto series are `tapered_deci_cent`. Verified from the
API's own `price_ranges`:

    0.0000 - 0.1000  step 0.0010   (0.1c tick)
    0.1000 - 0.9000  step 0.0100   (1.0c tick)
    0.9000 - 1.0000  step 0.0010   (0.1c tick)

The hourly ladders (KXBTCD etc.) are `linear_cent` — a flat 1c everywhere.

WHY THIS MATTERS AND WHERE IT DOES NOT:
  - The touch matrix ran on KXBTCD (linear_cent). Its 1c tick was CORRECT.
  - The fade runs at ~50c on KXBTC15M, where tapered still gives 1c. CORRECT.
  - The lead-lag tradeability test assumed a 1c tick. At the money that is
    right. IN THE WINGS IT IS WRONG BY 10x, and the wings are exactly where a
    0.1c tick could let a sub-tick signal through.

So the open question this closes: does the finer wing tick rescue any of the
sub-tick results? Compute edge/tick across the whole price range instead of
only at the money.
"""
import json
import math
import os
import sys

import numpy as np
from scipy import stats

sys.path.insert(0, os.path.dirname(__file__))
from fees import kalshi_fee_per_contract_unrounded  # noqa: E402

OUT = r"C:\Users\gianf\crypto\reports"
SEC_PER_YEAR = 365.25 * 86400.0


def tick_at(p, tapered=True):
    """Minimum price increment in DOLLARS at price p."""
    if not tapered:
        return 0.01
    return 0.001 if (p < 0.10 or p > 0.90) else 0.01


def dP_dS_at(S, sigma_ann, minutes, p_target):
    """Binary delta at the strike implied by a target price p_target.

    For an ATM-ish binary, P = Phi(d2) so d2 = Phi^-1(p). Delta wrt spot is
    phi(d2) / (S * sigma * sqrt(tau)).
    """
    tau = (minutes * 60.0) / SEC_PER_YEAR
    v = sigma_ann * math.sqrt(tau)
    d2 = stats.norm.ppf(min(max(p_target, 1e-4), 1 - 1e-4))
    return float(stats.norm.pdf(d2) / (S * v))


def main():
    print("=" * 104)
    print("TAPERED TICK — cost bar across the price range, 15-MINUTE series")
    print("=" * 104)
    print("  verified price_ranges: 0-10c step 0.1c | 10-90c step 1c | "
          "90-100c step 0.1c\n")
    print(f"  {'price':>6} {'tick':>7} {'fee':>7} {'1-tick spread':>14} "
          f"{'ROUND TRIP':>11} {'vs flat-1c RT':>14}")
    rows = []
    for pc in [1, 2, 3, 5, 7, 10, 15, 20, 30, 50, 70, 80, 85, 90, 93, 95, 97,
               99]:
        p = pc / 100.0
        tk = tick_at(p)
        fee = float(kalshi_fee_per_contract_unrounded(p))
        rt = 2 * tk + 2 * fee              # cross one tick each way, 2 fees
        rt_flat = 2 * 0.01 + 2 * fee
        rows.append((pc, tk, fee, rt, rt_flat))
        print(f"  {pc:>5}c {tk*100:>6.2f}c {fee*100:>6.3f}c "
              f"{tk*100:>13.2f}c {rt*100:>10.3f}c "
              f"{rt_flat*100:>13.3f}c")

    print("\n  In the wings the tapered tick makes a round trip "
          f"{(rows[3][4]/rows[3][3]):.2f}x cheaper at 5c "
          f"({rows[3][4]*100:.2f}c -> {rows[3][3]*100:.2f}c).")

    # ---------------------------------------------------------------
    print("\n" + "=" * 104)
    print("DOES THE FINER WING TICK RESCUE THE LEAD-LAG SIGNAL?")
    print("=" * 104)
    print("  Signal: ETH->XRP 1s cross-correlation 0.1544, XRP 1s return sd")
    print("  0.01017%. Edge scales with the binary's delta, which COLLAPSES in")
    print("  the wings — so a finer tick there is fighting a smaller signal.\n")
    S, sig, mins = 62900.0, 0.435, 7.5
    corr, sd1s = 0.1544, 0.0001017
    print(f"  {'price':>6} {'tick':>7} {'delta c/$':>11} {'edge c':>9} "
          f"{'edge/tick':>10} {'fee c':>8} {'edge-tick-fee':>14} "
          f"{'verdict':>12}")
    best = None
    for pc in [1, 2, 3, 5, 7, 10, 15, 20, 30, 50, 70, 80, 90, 93, 95, 97, 99]:
        p = pc / 100.0
        tk = tick_at(p)
        d = dP_dS_at(S, sig, mins, p) * 100.0        # cents per $1 spot
        edge = corr * sd1s * S * d                    # cents
        fee = float(kalshi_fee_per_contract_unrounded(p)) * 100
        net = edge - tk * 100 - fee
        ratio = edge / (tk * 100)
        vd = "TRADEABLE" if net > 0 else ("> tick" if ratio > 1 else "< tick")
        if best is None or ratio > best[1]:
            best = (pc, ratio, edge, net)
        print(f"  {pc:>5}c {tk*100:>6.2f}c {d:>11.5f} {edge:>9.4f} "
              f"{ratio:>10.3f} {fee:>8.4f} {net:>14.4f} {vd:>12}")

    print(f"\n  best edge/tick ratio: {best[1]:.3f} at {best[0]}c "
          f"(edge {best[2]:.4f}c, net {best[3]:+.4f}c)")
    if best[1] < 1:
        print("  -> the signal is BELOW one tick at EVERY price. The finer")
        print("     wing tick does not rescue it: the binary's delta falls")
        print("     faster than the tick does.")
    else:
        print("  -> the signal EXCEEDS one tick somewhere; re-examine.")

    json.dump({"tick_table": [{"price_c": r[0], "tick": r[1], "fee": r[2],
                               "rt_tapered": r[3], "rt_flat": r[4]}
                              for r in rows],
               "best_edge_over_tick": best[1]},
              open(os.path.join(OUT, "tapered_tick.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
