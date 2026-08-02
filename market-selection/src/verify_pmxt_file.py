"""Verify one pmxt hourly file is REAL L2 depth, not a well-formed empty file.

GUARDS.md #12: content validation, not row counts. Row counts were right in both
prior incidents. So this checks:
  - schema has the depth-bearing columns
  - rows are non-zero AND the depth columns are non-null on a real fraction
  - prices are inside (0, 100) cents
  - both a snapshot and a delta event type are present
  - the book actually has multiple levels a side (that is what "L2" means)
"""
import io
import sys

import pyarrow.parquet as pq
import requests

URL = sys.argv[1] if len(sys.argv) > 1 else \
    "https://r2kalshi.pmxt.dev/kalshi_orderbook_2026-06-01T12.parquet"

print("fetching", URL)
r = requests.get(URL, timeout=300)
print("http", r.status_code, "bytes", len(r.content))
buf = io.BytesIO(r.content)
pf = pq.ParquetFile(buf)
print("\n=== schema ===")
print(pf.schema_arrow)
print("\nrow_groups", pf.num_row_groups, "rows", pf.metadata.num_rows)

t = pq.read_table(buf)
cols = t.column_names
print("\ncolumns:", cols)

import pandas as pd  # noqa: E402

df = t.to_pandas()
print("\nrows:", len(df))
print("\n=== non-null fraction per column ===")
for c in cols:
    nn = df[c].notna().mean()
    print(f"  {c:24s} {nn*100:6.2f}% non-null")

print("\n=== event_type distribution ===")
if "event_type" in cols:
    print(df["event_type"].value_counts().head(10))

print("\n=== breadth ===")
for c in ("market_ticker", "market_id"):
    if c in cols:
        print(f"  distinct {c}: {df[c].nunique()}")
if "market_ticker" in cols:
    ser = df["market_ticker"].astype(str).str.split("-").str[0]
    print("\n  top series by rows:")
    print(ser.value_counts().head(15))

print("\n=== depth reality check ===")
# a snapshot row should carry a list of levels; a delta carries one price
for c in ("yes_bids", "no_bids", "yes", "no", "bids", "asks"):
    if c in cols:
        s = df[c].dropna()
        print(f"  {c}: {len(s)} non-null rows")
        if len(s):
            v = s.iloc[0]
            print(f"    type={type(v).__name__} sample={str(v)[:220]}")
            try:
                lens = s.head(20000).map(lambda x: len(x) if hasattr(x, "__len__") else 0)
                print(f"    levels per row: median={lens.median()} p90={lens.quantile(.9)} "
                      f"max={lens.max()}  frac_empty={(lens == 0).mean():.4f}")
            except Exception as e:
                print("    len check failed:", e)

if "price" in cols:
    p = pd.to_numeric(df["price"], errors="coerce").dropna()
    print(f"\n  price: n={len(p)} min={p.min()} max={p.max()} "
          f"frac_in_(0,100)={((p > 0) & (p < 100)).mean():.4f}")
if "delta" in cols:
    d = pd.to_numeric(df["delta"], errors="coerce").dropna()
    print(f"  delta: n={len(d)} min={d.min()} max={d.max()} nonzero={(d != 0).mean():.4f}")

print("\n=== time span ===")
for c in ("timestamp", "timestamp_received"):
    if c in cols:
        s = df[c].dropna()
        if len(s):
            print(f"  {c}: {s.min()} .. {s.max()}")

print("\nHEAD:")
print(df.head(6).to_string()[:2000])
