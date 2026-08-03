"""Download settled-market history for the families we intend to model.

This is the only source of out-of-sample outcome data that exists *tonight* —
order books are unrecoverable, but settled markets carry `expiration_value`
and `result`, which is everything Phase 4/5 scoring needs.

Idempotent: re-running merges on `ticker`.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kalshi_research.api import KalshiPublicClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "settled"
OUT.mkdir(parents=True, exist_ok=True)

KEEP = [
    "ticker", "event_ticker", "market_type", "status", "result",
    "expiration_value", "floor_strike", "cap_strike", "strike_type",
    "open_time", "close_time", "expiration_time", "settlement_timer_seconds",
    "volume_fp", "volume_24h_fp", "open_interest_fp", "liquidity_dollars",
    "last_price_dollars", "previous_price_dollars",
    "yes_bid_dollars", "yes_ask_dollars", "no_bid_dollars", "no_ask_dollars",
    "title", "yes_sub_title", "mve_collection_ticker",
]

# families worth history: BTC/ETH crypto ladders, weather ladders, index, econ
FAMILIES = [
    "KXBTC15M", "KXETH15M", "KXINX15M",
    "KXBTC", "KXETH", "KXBTCD", "KXETHD", "KXSOLD", "KXXRPD", "KXDOGED",
    "KXTEMPDCH", "KXTEMPLAXH", "KXTEMPCHIH", "KXTEMPAUSH",
    "KXTEMPNYH", "KXTEMPMIAH", "KXTEMPDENH", "KXTEMPPHILH",
    "KXHIGHNY", "KXHIGHCHI", "KXHIGHMIA", "KXHIGHAUS",
    "KXHIGHLAX", "KXHIGHDEN", "KXHIGHPHIL",
    "KXINX", "KXINXU", "KXNASDAQ100", "KXNASDAQ100U", "KXDJI",
    "KXCPIYOY", "KXCPI", "KXFED", "KXGDP",
]


def fetch(c: KalshiPublicClient, series: str, max_pages: int = 60) -> pd.DataFrame:
    rows: list[dict] = []
    cursor = None
    for _ in range(max_pages):
        p = {"series_ticker": series, "status": "settled", "limit": 1000}
        if cursor:
            p["cursor"] = cursor
        try:
            d = c.get("/markets", p)
        except Exception as e:  # noqa: BLE001
            print(f"    page error {type(e).__name__}: {str(e)[:60]}")
            break
        mk = d.get("markets") or []
        if not mk:
            break
        rows += mk
        cursor = d.get("cursor")
        if not cursor:
            break
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    for col in KEEP:
        if col not in df.columns:
            df[col] = None
    return df[KEEP]


def main() -> None:
    c = KalshiPublicClient(rps=8.0)
    t0 = time.time()
    summary = []
    for fam in FAMILIES:
        df = fetch(c, fam)
        if df.empty:
            print(f"  {fam:14s} 0 settled")
            summary.append({"series": fam, "n": 0})
            continue
        path = OUT / f"{fam}.parquet"
        if path.exists():
            old = pd.read_parquet(path)
            df = (
                pd.concat([old, df])
                .drop_duplicates(subset=["ticker"], keep="last")
                .reset_index(drop=True)
            )
        df.to_parquet(path, index=False)
        ct = pd.to_datetime(df.close_time, errors="coerce", utc=True)
        print(
            f"  {fam:14s} {len(df):6d} settled  "
            f"{ct.min():%Y-%m-%d} -> {ct.max():%Y-%m-%d}"
        )
        summary.append(
            {
                "series": fam,
                "n": len(df),
                "first": str(ct.min()),
                "last": str(ct.max()),
            }
        )
    pd.DataFrame(summary).to_csv(OUT / "_summary.csv", index=False)
    print(f"\nrequests={c.n_req} 429={c.n_429} elapsed={time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
