"""Sanity-check Stage 1 before anything is built on top of it.

The failure mode that matters is leakage: a feature that quietly encodes the
result. These checks are cheap and would catch it.
"""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

ROOT = pathlib.Path(__file__).resolve().parents[1]
f = pd.read_parquet(ROOT / "data" / "cache" / "stage1_features.parquet")
f["date"] = pd.to_datetime(f["date"])
print(f"{len(f):,} rows x {len(f.columns)} cols\n")

print("=" * 74)
print("1. FIRST-EVER MATCH MUST HAVE EMPTY STATE")
print("=" * 74)
first_w = ~f["winner_name"].duplicated()
debut = f[first_w & (f["w_elo_n"] == 0)]
print(f"  debut rows (w_elo_n==0): {len(debut):,}")
print(f"  w_elo all exactly 1500?  {bool((debut['w_elo'] == 1500).all())}")
print(f"  w_all_n all zero?        {bool((debut['w_all_n'].fillna(0) == 0).all())}")
print(f"  w_matches_7d all zero?   {bool((debut['w_matches_7d'] == 0).all())}")
print(f"  h2h_played on debut>0:   {int((debut['h2h_played'] > 0).sum())} "
      f"(nonzero is fine: opponent may be known)")

print("\n" + "=" * 74)
print("2. ELO SANITY -- who ends up on top?")
print("=" * 74)
recent = f[f["date"] >= "2024-01-01"]
last = {}
for name_col, elo_col in (("winner_name", "w_elo"), ("loser_name", "l_elo")):
    for nm, e, t in zip(recent[name_col], recent[elo_col], recent["tour"]):
        if isinstance(nm, str) and e == e:
            last[nm] = (e, t)
top = sorted(last.items(), key=lambda kv: -kv[1][0])[:15]
for nm, (e, t) in top:
    print(f"  {e:7.0f}  {t}  {nm}")

print("\n" + "=" * 74)
print("3. ELO DISCRIMINATION (higher Elo should win more often)")
print("=" * 74)
sub = f[(f["date"] >= "2015-01-01") & f["w_elo"].notna() & f["l_elo"].notna()]
diff = sub["w_elo"].to_numpy() - sub["l_elo"].to_numpy()
print(f"  winner Elo > loser Elo in {np.mean(diff > 0) * 100:.1f}% of matches")
print(f"  mean Elo gap (winner - loser): {diff.mean():+.1f}")
for lo, hi in [(0, 25), (25, 50), (50, 100), (100, 200), (200, 400), (400, 2000)]:
    m = (np.abs(diff) >= lo) & (np.abs(diff) < hi)
    if m.sum() > 100:
        print(f"    |gap| {lo:>4}-{hi:<4} n={m.sum():>7,}  "
              f"favourite won {np.mean(diff[m] > 0) * 100:5.1f}%")

print("\n" + "=" * 74)
print("4. LEAKAGE PROBE -- correlation of each feature with the outcome")
print("=" * 74)
print("  Built symmetrically: for each match we compare the winner's feature")
print("  to the loser's. A pre-match feature can be predictive, but nothing")
print("  should be near-perfect, and nothing derived from THIS match's play")
print("  should appear at all.")
print("  Ties are EXCLUDED: for sparse or binary features (back_to_back,")
print("  qualifier) both players are usually identical, which would drag the")
print("  share away from 50% for reasons that have nothing to do with leakage.")
rows = []
for c in f.columns:
    if not c.startswith("w_"):
        continue
    lc = "l_" + c[2:]
    if lc not in f.columns or f[c].dtype.kind not in "fi":
        continue
    a = f[c].to_numpy(dtype=float)
    b = f[lc].to_numpy(dtype=float)
    ok = np.isfinite(a) & np.isfinite(b) & (a != b)
    if ok.sum() < 1000:
        continue
    share = float(np.mean(a[ok] > b[ok]))
    rows.append((c[2:], int(ok.sum()), share, float(np.mean(a == b))))
rows.sort(key=lambda r: -abs(r[2] - 0.5))
print(f"\n  {'feature':<24}{'n(non-tie)':>12}{'winner>loser':>14}{'tied':>8}")
for name, n, s, tie in rows[:20]:
    flag = "  <-- CHECK" if s > 0.90 or s < 0.10 else ""
    print(f"  {name:<24}{n:>12,}{s * 100:>13.1f}%{tie * 100:>7.0f}%{flag}")
print("\n  Anything above 90% would mean the feature knows the result.")

print("\n" + "=" * 74)
print("5. COVERAGE OF SERVE ACCUMULATORS BY ERA")
print("=" * 74)
for yr in (1995, 2005, 2015, 2024, 2026):
    s = f[f["date"].dt.year == yr]
    if len(s) == 0:
        continue
    print(f"  {yr}: n={len(s):>7,}  w_all_svpt>0 "
          f"{(s['w_all_svpt'].fillna(0) > 0).mean() * 100:5.1f}%   "
          f"w_surf_svpt>0 {(s['w_surf_svpt'].fillna(0) > 0).mean() * 100:5.1f}%")
