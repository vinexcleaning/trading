"""Stage 4, Kalshi benchmark, restricted to markets with a real quote.

40% of the joined markets quote 1c/99c. Their "mid" of 50c is not the market's
opinion -- it is the absence of one. Including them inflates the market's Brier
and flatters the model. This re-scores on markets where Kalshi actually has a
two-sided price.
"""
import pathlib
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "cache"
REPORT = ROOT / "reports"

j = pd.read_parquet(CACHE / "stage4_kalshi_join.parquet")
q = pd.read_parquet(ROOT / "data" / "kalshi" / "kalshi_prematch_prices.parquet",
                    columns=["event_ticker", "pre_bid", "pre_ask"])
j = j.merge(q, on="event_ticker", how="left", suffixes=("", "_q"))
j["spread"] = j["pre_ask"] - j["pre_bid"]

lines = []


def emit(s=""):
    print(s)
    lines.append(s)


def compare(d, label):
    d = d[d["p_model"].notna() & d["p_market"].notna()]
    if len(d) < 40:
        emit(f"{label:<26}{len(d):>6}   (too few)")
        return
    y = d["y"].to_numpy()
    pm = d["p_model"].to_numpy()
    pk = np.clip(d["p_market"].to_numpy(), 1e-6, 1 - 1e-6)
    bm, bk = brier_score_loss(y, pm), brier_score_loss(y, pk)
    rng = np.random.default_rng(3)
    n = len(d)
    boots = [brier_score_loss(y[s], pm[s]) - brier_score_loss(y[s], pk[s])
             for s in (rng.integers(0, n, n) for _ in range(2000))]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    verdict = ("MODEL beats market" if hi < 0
               else "market beats model" if lo > 0 else "indistinguishable")
    emit(f"{label:<26}{n:>6}{bm:>10.5f}{bk:>10.5f}"
         f"{bm - bk:>+10.5f}  [{lo:+.4f},{hi:+.4f}]  {verdict}")


emit("=" * 100)
emit("STAGE 4 (Kalshi) -- RE-SCORED BY QUOTE QUALITY")
emit("=" * 100)
emit(f"{'subset':<26}{'n':>6}{'model':>10}{'market':>10}"
     f"{'diff':>10}  {'95% CI':<20}  verdict")
compare(j, "all joined")
compare(j[j["spread"] <= 0.10], "spread <= 10c")
compare(j[j["spread"] <= 0.05], "spread <= 5c")
compare(j[j["spread"] <= 0.02], "spread <= 2c")
emit()
emit("By tier, restricted to a tradeable quote (spread <= 10c):")
liq = j[j["spread"] <= 0.10]
for tier, g in liq.groupby("k_tier", observed=True):
    compare(g, f"  {tier}")

emit()
emit("-" * 100)
emit("WHY THIS MATTERS")
emit("-" * 100)
emit("On the illiquid 40%, 'the market' is a 50c placeholder, so any model that")
emit("is better than a coin flip appears to beat it. Restricting to markets")
emit("with a real two-sided price is the only fair comparison -- and it is also")
emit("the only subset you could have traded.")

(REPORT / "stage4_kalshi_liquid.txt").write_text("\n".join(lines), encoding="utf-8")
print(f"\nreport -> {REPORT / 'stage4_kalshi_liquid.txt'}")
