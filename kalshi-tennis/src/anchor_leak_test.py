"""Which price anchor is actually pre-match?

Leakage signature: a price pinned at 0.995/0.005 that is always right. At a
genuinely pre-match anchor, extreme quotes should be rare and merely very
accurate, not perfect -- and Kalshi should NOT beat two independent books that
agree with each other at corr 0.9985.
"""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
REPORT = ROOT / "reports"

ANCHORS = ["h0", "h1", "h2", "h6", "h24"]

base = pd.read_parquet(CACHE / "pinnacle_vs_kalshi.parquet")
multi = pd.read_parquet(ROOT / "data" / "kalshi" /
                        "kalshi_prices_multianchor.parquet")

# `base` was built off the leaked anchor; keep only the join keys + truth
keep = base[["date", "player_a", "player_b", "y", "p_pinn", "p_avg",
             "surface", "tour"]].copy()
ev_map = pd.read_parquet(CACHE / "kalshi_events.parquet",
                         columns=["event_ticker", "player_a", "player_b"])
keep = keep.merge(ev_map, on=["player_a", "player_b"], how="left")
d = keep.merge(multi, on="event_ticker", how="inner")
d = d[d["p_pinn"].notna()].copy()

lines = []


def emit(s=""):
    print(s)
    lines.append(s)


def brier(p, y):
    return float(np.mean((np.clip(p, 1e-6, 1 - 1e-6) - y) ** 2))


emit("=" * 94)
emit("WHICH KALSHI ANCHOR IS ACTUALLY PRE-MATCH?")
emit("=" * 94)
emit("Two independent books agree with each other (corr 0.9985, MAD 0.015).")
emit("Any anchor where Kalshi 'beats' both by a wide margin is leaking.")
emit()
emit(f"{'anchor':<9}{'n':>6}{'extreme':>9}{'extr.acc':>10}"
     f"{'corr(bk)':>10}{'MAD':>8}{'Kalshi':>9}{'Betfair':>9}{'diff':>9}")

for a in ANCHORS:
    col = f"mid_{a}"
    if col not in d.columns:
        continue
    g = d[d[col].notna() & (d[f"ask_{a}"] - d[f"bid_{a}"] <= 0.10)].copy()
    if len(g) < 40:
        emit(f"{a:<9}{len(g):>6}  (too few)")
        continue
    y = g["y"].to_numpy()
    pk = g[col].to_numpy()
    pb = g["p_pinn"].to_numpy()

    extreme = (pk > 0.98) | (pk < 0.02)
    if extreme.sum() >= 5:
        # is the extreme quote always right?
        acc = np.mean((pk[extreme] > 0.5).astype(int) == y[extreme])
        acc_s = f"{acc * 100:.1f}%"
    else:
        acc_s = "n/a"
    corr = float(np.corrcoef(pk, pb)[0, 1])
    mad = float(np.mean(np.abs(pk - pb)))
    bk, bp = brier(pk, y), brier(pb, y)
    emit(f"{a:<9}{len(g):>6}{extreme.mean() * 100:>8.1f}%{acc_s:>10}"
         f"{corr:>10.4f}{mad:>8.4f}{bk:>9.5f}{bp:>9.5f}{bk - bp:>+9.5f}")

emit()
emit("Reading it: 'extreme' is the share of quotes outside 2c-98c and")
emit("'extr.acc' how often those were right. A pre-match market is rarely")
emit("that confident, and when it is it is ~95% right, not 100%.")

(REPORT / "anchor_leak_test.txt").write_text("\n".join(lines), encoding="utf-8")
print(f"\nreport -> {REPORT / 'anchor_leak_test.txt'}")
