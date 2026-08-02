"""Are the four assets INDEPENDENT replications, or four views of one market?

This decides how to read "mean reversion appears in 3 of 4 assets". If the
15-minute up/down outcomes are highly correlated across assets, then seeing the
effect in BTC, ETH and SOL is closer to seeing it ONCE than three times, and the
replication argument collapses.

We already know 1-second spot returns are correlated 0.891 (BTC/ETH). The
question here is the SETTLEMENT SIGN of the actual contracts, matched by
window.
"""
import json
import os
from itertools import combinations

import numpy as np

SETTLED = r"C:\Users\gianf\crypto\data\kalshi_settled"
ASSETS = [("BTC", "KXBTC15M"), ("ETH", "KXETH15M"),
          ("SOL", "KXSOL15M"), ("XRP", "KXXRP15M")]


def load(series):
    ev = {}
    with open(os.path.join(SETTLED, f"{series}.jsonl"), encoding="utf-8") as f:
        for line in f:
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            ct, res = m.get("close_time"), str(m.get("result"))
            if ct and res in ("yes", "no"):
                ev[ct] = 1 if res == "yes" else 0
    return ev


def main():
    data = {n: load(s) for n, s in ASSETS}
    for n, d in data.items():
        print(f"  {n}: {len(d)} windows")
    common = sorted(set.intersection(*[set(d) for d in data.values()]))
    print(f"\n  windows common to ALL FOUR assets: {len(common)}")

    arr = {n: np.array([data[n][c] for c in common]) for n in data}

    print("\n" + "=" * 88)
    print("PAIRWISE AGREEMENT OF SETTLEMENT SIGN (matched by window)")
    print("=" * 88)
    print(f"  {'pair':<12} {'agree %':>9} {'phi corr':>10} "
          f"{'independent?':>14}")
    for a, b in combinations(arr, 2):
        agree = float((arr[a] == arr[b]).mean())
        phi = float(np.corrcoef(arr[a], arr[b])[0, 1])
        verdict = "NO" if phi > 0.3 else ("weak" if phi > 0.1 else "plausibly")
        print(f"  {a+'-'+b:<12} {agree*100:>8.2f}% {phi:>+10.4f} "
              f"{verdict:>14}")

    # how many effective independent series?
    M = np.corrcoef(np.vstack([arr[n] for n in arr]))
    ev = np.linalg.eigvalsh(M)
    n_eff = float((ev.sum() ** 2) / (ev ** 2).sum())
    print(f"\n  correlation matrix eigenvalues: "
          f"{', '.join(f'{e:.3f}' for e in sorted(ev, reverse=True))}")
    print(f"  EFFECTIVE number of independent series = {n_eff:.2f} "
          f"(out of 4)")
    print(f"\n  Reading: 4 assets behaving as ~{n_eff:.1f} independent series")
    print(f"  means 'replicates in 3 of 4' is worth far less than it sounds.")

    # do the assets agree on DIRECTION in the same windows?
    allup = np.vstack([arr[n] for n in arr]).sum(axis=0)
    print(f"\n  windows where all 4 agree: "
          f"{int(((allup == 0) | (allup == 4)).sum())} / {len(common)} "
          f"({100*((allup==0)|(allup==4)).mean():.1f}%)")
    print(f"  expected if independent: "
          f"{100*(0.5**4 + 0.5**4):.1f}%")


if __name__ == "__main__":
    main()
