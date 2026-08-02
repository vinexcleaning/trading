"""Is 'Kalshi is sharper than Betfair' real, or is the tail bad joins?

mean |diff| 0.074 vs median 0.019 means a heavy tail. Either Kalshi and the
exchange genuinely disagree violently on a minority of matches, or those rows
are mispaired. Two independent books (Betfair and the book average) should
agree closely with EACH OTHER; where they don't, the row is suspect.
"""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

ROOT = pathlib.Path(__file__).resolve().parents[1]
d = pd.read_parquet(ROOT / "data" / "cache" / "pinnacle_vs_kalshi.parquet")
d = d[d["p_pinn"].notna() & d["p_avg"].notna()].copy()
d["diff_k_bf"] = (d["p_kalshi"] - d["p_pinn"]).abs()
d["diff_bf_avg"] = (d["p_pinn"] - d["p_avg"]).abs()
d["diff_k_avg"] = (d["p_kalshi"] - d["p_avg"]).abs()

print(f"n = {len(d):,}")
print("\n=== Do the two BOOKS agree with each other? ===")
print("If Betfair and the book average disagree, that row's odds are broken,")
print("not Kalshi's price.")
print(d[["diff_k_bf", "diff_bf_avg", "diff_k_avg"]].describe(
    percentiles=[.5, .75, .9, .95, .99]).round(4).to_string())

print("\n=== Rows where Kalshi and Betfair disagree hugely (>0.40) ===")
big = d[d["diff_k_bf"] > 0.40].copy()
print(f"{len(big)} rows ({len(big)/len(d)*100:.1f}%)")
if len(big):
    print("  of those, book-average also disagrees with Betfair by >0.40: "
          f"{(big['diff_bf_avg'] > 0.40).sum()}")
    print("  -> if that count is high, the ODDS row is bad, not the join\n")
    cols = ["date", "player_a", "player_b", "y", "p_kalshi", "p_pinn",
            "p_avg", "spread", "surface"]
    print(big[cols].head(15).to_string(index=False))

print("\n=== Which book agrees with Kalshi more? ===")
for col, lbl in (("p_pinn", "Betfair"), ("p_avg", "book average")):
    print(f"  corr(Kalshi, {lbl:<13}) = {d['p_kalshi'].corr(d[col]):.4f}  "
          f"MAD = {(d['p_kalshi']-d[col]).abs().mean():.4f}")
print(f"  corr(Betfair, book average) = {d['p_pinn'].corr(d['p_avg']):.4f}  "
      f"MAD = {(d['p_pinn']-d['p_avg']).abs().mean():.4f}")

print("\n=== Brier of each source, and after dropping suspect rows ===")
y = d["y"].to_numpy()


def brier(p):
    return float(np.mean((np.clip(p, 1e-6, 1 - 1e-6) - y) ** 2))


print(f"  ALL n={len(d)}   Kalshi {brier(d['p_kalshi']):.5f}   "
      f"Betfair {brier(d['p_pinn']):.5f}   avg {brier(d['p_avg']):.5f}")

clean = d[d["diff_bf_avg"] <= 0.05]
y = clean["y"].to_numpy()
print(f"  BOOKS AGREE (|Betfair-avg|<=0.05) n={len(clean)}   "
      f"Kalshi {brier(clean['p_kalshi']):.5f}   "
      f"Betfair {brier(clean['p_pinn']):.5f}   avg {brier(clean['p_avg']):.5f}")

print("\n=== The 90c+ favourite band, where the gap was largest ===")
d2 = d.copy()
fav = np.maximum(d2["p_kalshi"], 1 - d2["p_kalshi"])
band = d2[fav >= 0.90]
y = band["y"].to_numpy()
print(f"  n={len(band)}  Kalshi {brier(band['p_kalshi']):.5f}  "
      f"Betfair {brier(band['p_pinn']):.5f}  avg {brier(band['p_avg']):.5f}")
print(f"  mean Betfair prob on these: {band['p_pinn'].mean():.3f}, "
      f"mean Kalshi: {band['p_kalshi'].mean():.3f}, "
      f"actual hit rate: {band['y'].mean():.3f}")
print(f"  |Betfair - avg| > 0.40 on: {(band['diff_bf_avg'] > 0.40).sum()} rows")
print("\n  sample:")
print(band.sort_values("diff_k_bf", ascending=False)[
    ["date", "player_a", "player_b", "y", "p_kalshi", "p_pinn", "p_avg"]
].head(10).to_string(index=False))
