"""Phase 0/1: enumerate all Kalshi series and open markets to parquet."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kalshi_research.api import CATEGORIES, KalshiPublicClient  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "data"
OUT.mkdir(exist_ok=True)


def main() -> None:
    c = KalshiPublicClient(rps=10.0)
    t0 = time.time()

    series_rows: list[dict] = []
    seen = set()
    for cat in CATEGORIES:
        try:
            rows = c.series_list(cat)
        except Exception as e:  # noqa: BLE001
            print(f"  {cat}: FAILED {e}")
            continue
        new = 0
        for s in rows:
            t = s.get("ticker")
            if t and t not in seen:
                seen.add(t)
                series_rows.append(
                    {
                        "ticker": t,
                        "title": s.get("title"),
                        "category": s.get("category"),
                        "frequency": s.get("frequency"),
                        "fee_type": s.get("fee_type"),
                        "fee_multiplier": s.get("fee_multiplier"),
                        "settlement_source": (s.get("settlement_sources") or [{}])[0].get("name"),
                        "contract_terms_url": s.get("contract_terms_url"),
                        "tags": ",".join(s.get("tags") or []),
                    }
                )
                new += 1
        print(f"  {cat}: {len(rows)} returned, {new} new  (total {len(series_rows)})")

    sdf = pd.DataFrame(series_rows)
    sdf.to_parquet(OUT / "series.parquet", index=False)
    print(f"\nseries: {len(sdf)} rows -> data/series.parquet  [{time.time()-t0:.0f}s]")

    print("\nenumerating open markets...")
    mrows = []
    for i, m in enumerate(c.markets(status="open")):
        mrows.append(m)
        if i and i % 5000 == 0:
            print(f"  {i} markets... [{time.time()-t0:.0f}s]")
    mdf = pd.json_normalize(mrows, max_level=0)
    for col in mdf.columns:
        if mdf[col].dtype == object:
            mdf[col] = mdf[col].apply(
                lambda v: str(v) if isinstance(v, (dict, list)) else v
            )
    mdf.to_parquet(OUT / "markets_open.parquet", index=False)
    print(f"open markets: {len(mdf)} rows -> data/markets_open.parquet")
    print(f"requests={c.n_req} 429s={c.n_429} elapsed={time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
