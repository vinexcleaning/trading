"""
report.py - turn the pickled step5/6/7 results into a markdown file.

Narrative text lives in RESULTS_NOTES at the bottom of the pipeline; this
module only handles the mechanical table formatting so the numbers in the
document are exactly the numbers the engine produced.
"""

from __future__ import annotations

import os
import pickle

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results")

ROUND = {
    "win_rate": 1, "avg_win_c": 1, "avg_loss_c": 1, "gross": 2, "fees": 2,
    "net": 2, "net_c_per_trade": 2, "net_$_per_trade": 3, "max_dd": 2,
    "train_net_c": 2, "hold_net_c": 2, "hold_net": 2, "hold_win": 1,
    "hold_gross": 2, "hold_fees": 2, "hold_dd": 2, "train_net": 2,
    "hold_avg_win_c": 1, "hold_avg_loss_c": 1, "delta": 2, "net_c": 2,
}


def md(df: pd.DataFrame, index: bool = False) -> str:
    """Minimal markdown table writer - no tabulate dependency."""
    if df is None or len(df) == 0:
        return "_(no rows)_\n"
    d = df.copy()
    if index:
        d = d.reset_index()
    for c in d.columns:
        if c in ROUND and pd.api.types.is_numeric_dtype(d[c]):
            d[c] = d[c].round(ROUND[c])
    cols = [str(c) for c in d.columns]
    lines = ["| " + " | ".join(cols) + " |",
             "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in d.iterrows():
        cells = []
        for c in d.columns:
            v = r[c]
            if isinstance(v, float) and np.isnan(v):
                cells.append("-")
            elif isinstance(v, float):
                cells.append(f"{v:,.2f}" if abs(v) >= 0.005 or v == 0 else f"{v:.3f}")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def load(name: str):
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        return None
    with open(p, "rb") as f:
        return pickle.load(f)


def funnel_table(funnels: dict) -> pd.DataFrame:
    rows = []
    for k, fn in funnels.items():
        rows.append({
            "strategy": k,
            "live candles": f"{fn['live']:,}",
            "structural events": f"{fn['event']:,}",
            "pass vol filter": f"{fn['act2']:,}",
            "pass hold": f"{fn['hold']:,}",
            "pass price band": f"{fn['band']:,}",
            "traded (after dedup)": f"{fn['taken']:,}",
        })
    return pd.DataFrame(rows)
