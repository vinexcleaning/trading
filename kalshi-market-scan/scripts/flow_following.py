"""Phase 6 (Kalshi side): flow following on the anonymous trade feed.

Kalshi's public trade feed carries no account identifier, so identity-based copying
is impossible. What is available is aggregate one-sided flow. This builds it:

  - join recorded trades to the market universe on `ticker`
  - DROP combo/multivariate markets (87% of open markets) via `mve_collection_ticker`
  - aggregate per market per taker side into notional and VWAP
  - flag markets accumulating large one-sided flow

Reads whatever the recorder has written so far, so it is safe to run at any time
and gets more informative as the tape grows.
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

# a "whale print" is a single trade above this notional, in dollars
WHALE_NOTIONAL = 500.0


def load_trades() -> pd.DataFrame:
    fs = sorted(glob.glob(str(RAW / "source=kalshi_trades" / "**" / "*.parquet"),
                          recursive=True))
    if not fs:
        return pd.DataFrame()
    df = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    return df.drop_duplicates(subset=["trade_id"]).sort_values("event_ns")


def load_universe() -> pd.DataFrame:
    p = ROOT / "data" / "markets_open.parquet"
    if not p.exists():
        return pd.DataFrame()
    m = pd.read_parquet(p, columns=["ticker", "event_ticker", "mve_collection_ticker",
                                    "title", "yes_bid_dollars", "yes_ask_dollars"])
    m["is_combo"] = m.mve_collection_ticker.notna()
    return m


def main() -> None:
    tr = load_trades()
    if tr.empty:
        print("no recorded trades yet -- the recorder started during the daily "
              "trading halt (trading_active=false 07:00-09:00 UTC). Re-run after "
              "the exchange reopens.")
        (REPORTS / "flow_following.json").write_text(
            json.dumps({"status": "no trades recorded yet"}, indent=1)
        )
        return

    uni = load_universe()
    print(f"trades recorded: {len(tr):,}")
    if not uni.empty:
        tr = tr.merge(
            uni[["ticker", "is_combo", "title"]], on="ticker", how="left"
        )
        # must cast: fillna on an object column leaves object dtype, and `~` on
        # object does bitwise NOT on ints, silently producing -1 instead of False
        tr["is_combo"] = tr.is_combo.fillna(False).astype(bool)
        n_combo = int(tr.is_combo.sum())
        print(f"  combo-generated trades dropped: {n_combo:,} "
              f"({100*tr.is_combo.mean():.1f}%)")
        tr = tr[~tr.is_combo]
    print(f"  organic single-market trades: {len(tr):,}")
    if tr.empty:
        print("  nothing left after filtering")
        return

    tr["notional"] = tr["count"] * tr.yes_price
    # signed flow: taker buying YES is positive, taker buying NO is negative
    tr["signed"] = np.where(
        tr.taker_outcome_side.eq("yes"), tr.notional, -tr.notional
    )

    agg = tr.groupby("ticker").agg(
        n_trades=("trade_id", "size"),
        notional=("notional", "sum"),
        net_signed=("signed", "sum"),
        vwap_yes=("yes_price", lambda s: float(np.average(s))),
        first_ns=("event_ns", "min"),
        last_ns=("event_ns", "max"),
    )
    agg["one_sidedness"] = (agg.net_signed / agg.notional).abs()
    agg["side"] = np.where(agg.net_signed > 0, "yes", "no")
    agg = agg.sort_values("notional", ascending=False)
    agg.to_csv(REPORTS / "flow_by_market.csv")

    whales = tr[tr.notional >= WHALE_NOTIONAL].copy()
    print(f"  whale prints >= ${WHALE_NOTIONAL:.0f}: {len(whales):,}")

    print("\ntop 15 markets by traded notional:")
    cols = ["n_trades", "notional", "net_signed", "one_sidedness", "side", "vwap_yes"]
    print(agg.head(15)[cols].round(3).to_string())

    # accumulating one-sided flow is the signal the brief describes
    cand = agg[(agg.one_sidedness > 0.8) & (agg.notional > WHALE_NOTIONAL)]
    print(f"\nmarkets with >80% one-sided flow and >${WHALE_NOTIONAL:.0f} notional: "
          f"{len(cand)}")
    if len(cand):
        print(cand.head(10)[cols].round(3).to_string())

    summary = {
        "n_trades_recorded": int(len(tr)),
        "n_markets_traded": int(agg.shape[0]),
        "total_notional": float(agg.notional.sum()),
        "n_whale_prints": int(len(whales)),
        "n_one_sided_candidates": int(len(cand)),
        "note": (
            "Kalshi's trade feed is anonymous -- no account identifier exists in the "
            "schema -- so this is flow following, not copy trading. Combo markets are "
            "excluded via mve_collection_ticker."
        ),
    }
    (REPORTS / "flow_following.json").write_text(json.dumps(summary, indent=1))
    print(f"\nwrote {REPORTS/'flow_following.json'}")


if __name__ == "__main__":
    main()
