"""Build the tier2 watchlist: top-volume non-combo open markets, plus weather
nested-threshold families and bucket families that the arb scanner needs.

Cheap enough to re-run periodically; writes data/watchlist_tier2.json.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kalshi_research.api import KalshiPublicClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# Series with structural redundancy worth monitoring (nested thresholds / buckets)
STRUCTURAL_SERIES = [
    "KXTEMPDCH", "KXTEMPLAXH", "KXTEMPNYH", "KXTEMPCHIH", "KXTEMPMIAH",
    "KXTEMPAUSH", "KXTEMPDENH", "KXTEMPPHILH",
    "KXHIGHNY", "KXHIGHCHI", "KXHIGHMIA", "KXHIGHAUS", "KXHIGHLAX",
    "KXHIGHDEN", "KXHIGHPHIL",
    "KXBTC", "KXBTCD", "KXETH", "KXETHD", "KXSOLD", "KXXRPD",
    "KXINX", "KXINXU", "KXNASDAQ100", "KXNASDAQ100U", "KXDJI",
    "KXCPIYOY", "KXCPI", "KXFED", "KXJOBS", "KXCLAIMS", "KXGDP",
]


def main(cap: int = 400) -> None:
    c = KalshiPublicClient(rps=10.0)
    t0 = time.time()
    tickers: list[str] = []
    struct: dict[str, list[str]] = {}

    for s in STRUCTURAL_SERIES:
        try:
            d = c.get("/markets", {"series_ticker": s, "status": "open", "limit": 200})
        except Exception as e:  # noqa: BLE001
            print(f"  {s}: {type(e).__name__}")
            continue
        mk = [m["ticker"] for m in (d.get("markets") or [])]
        if mk:
            struct[s] = mk
            tickers += mk[:40]
        print(f"  {s}: {len(mk)} open")

    # top-volume singles from the last full enumeration, if present
    p = DATA / "markets_open.parquet"
    if p.exists():
        m = pd.read_parquet(p)
        singles = m[m.mve_collection_ticker.isna()].copy()
        singles["v"] = pd.to_numeric(singles.volume_24h_fp, errors="coerce").fillna(0)
        top = singles.nlargest(250, "v").ticker.tolist()
        tickers += top
        print(f"  top-volume singles from snapshot: {len(top)}")

    tickers = list(dict.fromkeys(tickers))[:cap]
    out = {
        "generated_ns": time.time_ns(),
        "tickers": tickers,
        "structural_families": struct,
    }
    (DATA / "watchlist_tier2.json").write_text(json.dumps(out, indent=1))
    print(f"\nwatchlist: {len(tickers)} tickers, {len(struct)} structural families")
    print(f"requests={c.n_req} 429={c.n_429} elapsed={time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
