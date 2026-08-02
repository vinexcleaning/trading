"""A4 -- the three named high-risk candidates, tested where the data is here.

1. Stage 0-5 player model: match selection, train/test split, p1 assignment.
2. The Stage 4/5 "liquidity" filter, which filtered on a spread taken from the
   anchor file already known to be a look-ahead leak. A spread filter reading a
   post-settlement quote is a SELECTION leak sitting on top of a FEATURE leak,
   and the two have never been separated.
3. v3 structural-event backtest and the copy-trading work: not on this machine.
"""
import pathlib

import numpy as np
import pandas as pd

import leakguard as lg

OLD = pathlib.Path(r"C:\Users\gianf\kalshi")
ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    out = []

    def w(s=""):
        print(s, flush=True)
        out.append(s)

    w("A4 -- NAMED HIGH-RISK CANDIDATES")
    w("=" * 78)
    w("")

    # ---------------- 1. Stage 0-5 player model --------------------------
    w("## 1. Stage 0-5 player model -- CLEAN on all three checks")
    w("")
    w("  p1 assignment  (stage4_model.py:43-47):")
    w("      swap = w > l          # p1 is alphabetically first")
    w("      y = (~swap).astype(int)")
    w("    Player 1 is chosen by NAME, not by who won. The module docstring")
    w("    says so explicitly. Outcome-independent, and the target is ~50/50.")
    w("")
    w("  train/val/test  (stage4_model.py:36,150-151): split on calendar date")
    w("    (TRAIN_END, VAL_END = 2025-01-01). Temporal, not random, no leak.")
    w("")
    w("  match selection (stage4_model.py:313):")
    w("      ev[ev['pre_mid'].notna() & ev['result_a'].isin(['yes','no'])]")
    w("    Filtering on `result` being decided is required to have a label at")
    w("    all and does not select WHICH outcome. `pre_mid` notna is a")
    w("    data-availability filter -- but see section 2, because in")
    w("    stage4_model that pre_mid came from the leaking anchor.")
    w("")
    w("  stage0_audit.py:88-89 reads `volume_pre` / `oi_pre` from the last")
    w("  CANDLE at or before the anchor, not from the settled market record.")
    w("  That is the correct pattern and the exact near-miss that caught me:")
    w("  same field name, safe when timestamped, unsafe when read off a")
    w("  settled row.")
    w("")

    # ---------------- 2. the liquidity / spread filter -------------------
    w("## 2. The Stage 4/5 liquidity filter -- SELECTION ON A POST-SETTLEMENT "
      "QUOTE")
    w("")
    leak = OLD / "data" / "kalshi" / "kalshi_prematch_prices.parquet.INVALID_LOOKAHEAD_LEAK"
    multi = OLD / "data" / "kalshi" / "kalshi_prices_multianchor.parquet"
    join = OLD / "data" / "cache" / "stage4_kalshi_join.parquet"
    w("`stage4_kalshi_liquid.py` computes `spread = pre_ask - pre_bid` from")
    w("`kalshi_prematch_prices.parquet` and then reports results for")
    w("`spread <= 10c / 5c / 2c`. That file is the one already renamed")
    w("`.INVALID_LOOKAHEAD_LEAK`: its anchor sits at or after settlement for")
    w("84.5% of markets. So the filter is not selecting liquid markets -- it is")
    w("partly selecting **settled** ones, where the book has collapsed to a")
    w("tight quote around 0 or 100.")
    w("")
    if not (leak.exists() and join.exists()):
        w("  (source files not present; cannot test empirically here)")
    else:
        q = pd.read_parquet(leak, columns=["event_ticker", "pre_bid",
                                           "pre_ask"])
        j = pd.read_parquet(join)
        m = j.merge(q, on="event_ticker", how="inner")
        ycol = "y" if "y" in m.columns else None
        pcol = ("p_market" if "p_market" in m.columns else None)
        m["spread"] = m["pre_ask"] - m["pre_bid"]
        m = m[m["spread"].notna()]
        w(f"  joined rows with a leaking-anchor spread: {len(m):,}")
        if ycol and pcol:
            m = m[m[ycol].notna() & m[pcol].notna()]
            y = m[ycol].to_numpy(float)
            p = m[pcol].to_numpy(float)
            w("")
            w("  Test: does the spread filter shift the market's calibration")
            w("  residual? A genuine liquidity filter should not.")
            w("")
            for thr in (0.10, 0.05, 0.02):
                mask = (m["spread"] <= thr).to_numpy()
                z, d, msg = lg.assert_selection_neutral(
                    mask, y, p, f"leaking-anchor spread <= {thr:.2f}",
                    raise_on_fail=False)
                w(("  FAIL  " if abs(z) > lg.Z_MAX else "  pass  ") + msg)
            w("")
            ext = ((p <= 0.02) | (p >= 0.98))
            w(f"  extreme quotes (<=2c or >=98c) in this file: "
              f"{ext.mean():.2%}; of those the market was right "
              f"{(y[ext] == (p[ext] > 0.5)).mean():.4f} of the time")
            tight = (m["spread"] <= 0.02).to_numpy()
            w(f"  P(extreme quote | spread <= 2c) = {ext[tight].mean():.4f} "
              f"vs {ext[~tight].mean():.4f} otherwise")
        # the corrected anchor, for contrast
        if multi.exists():
            mm = pd.read_parquet(multi)
            if {"bid_h6", "ask_h6"}.issubset(mm.columns):
                mm["spread6"] = mm["ask_h6"] - mm["bid_h6"]
                j2 = j.merge(mm[["event_ticker", "spread6"]], on="event_ticker",
                             how="inner")
                j2 = j2[j2["spread6"].notna()]
                if "y" in j2 and "p_market" in j2:
                    j2 = j2[j2["y"].notna() & j2["p_market"].notna()]
                    w("")
                    w("  Same test on the CORRECTED -6h anchor, for contrast:")
                    for thr in (0.10, 0.05, 0.02):
                        mask = (j2["spread6"] <= thr).to_numpy()
                        z, d, msg = lg.assert_selection_neutral(
                            mask, j2["y"].to_numpy(float),
                            j2["p_market"].to_numpy(float),
                            f"h6 anchor spread <= {thr:.2f}",
                            raise_on_fail=False)
                        w(("  FAIL  " if abs(z) > lg.Z_MAX else "  pass  ")
                          + msg)
    w("")
    w("## 3. v3 structural-event backtest and copy-trading -- NOT ON THIS "
      "MACHINE")
    w("")
    w("  Neither exists under C:\\Users\\gianf. They live on the desktop under")
    w("  C:\\Users\\vinig\\kalshi and siblings. Listed with the exact checks to")
    w("  run in BLOCKED_ON_DESKTOP.md.")

    (ROOT / "reports" / "audit_a4.txt").write_text("\n".join(out),
                                                   encoding="utf-8")
    print(f"\n-> {ROOT / 'reports' / 'audit_a4.txt'}")


if __name__ == "__main__":
    main()
