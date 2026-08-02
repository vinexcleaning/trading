"""Are the SNAPSHOT rows carrying real multi-level books?

The delta rows have empty level arrays by construction -- that is the wire
format, not a defect. The question that decides whether this archive is usable
is whether the 0.27% snapshot rows carry populated ladders.
"""
import io
import sys

import pyarrow.parquet as pq
import pyarrow.compute as pc
import requests

URL = sys.argv[1] if len(sys.argv) > 1 else \
    "https://r2kalshi.pmxt.dev/kalshi_orderbook_2026-06-01T12.parquet"

r = requests.get(URL, timeout=300)
t = pq.read_table(io.BytesIO(r.content))
snap = t.filter(pc.equal(t["event_type"], "orderbook_snapshot"))
print("snapshot rows:", snap.num_rows, "of", t.num_rows)

yl = pc.list_value_length(snap["yes_bids"]).to_pandas()
nl = pc.list_value_length(snap["no_bids"]).to_pandas()
print("\nyes_bids levels per SNAPSHOT row:")
print(f"  frac_empty={(yl == 0).mean():.4f} median={yl.median()} "
      f"p75={yl.quantile(.75)} p90={yl.quantile(.9)} max={yl.max()}")
print("no_bids levels per SNAPSHOT row:")
print(f"  frac_empty={(nl == 0).mean():.4f} median={nl.median()} "
      f"p75={nl.quantile(.75)} p90={nl.quantile(.9)} max={nl.max()}")
print(f"\nsnapshots with depth on AT LEAST ONE side: "
      f"{((yl > 0) | (nl > 0)).mean()*100:.2f}%")
print(f"snapshots with depth on BOTH sides:          "
      f"{((yl > 0) & (nl > 0)).mean()*100:.2f}%")

df = snap.to_pandas()
df["yl"] = yl.values
df["nl"] = nl.values
rich = df[(df.yl > 0) & (df.nl > 0)]
print(f"\ntwo-sided snapshots: {len(rich)}  distinct tickers: "
      f"{rich.market_ticker.nunique()}")
def levels(arr):
    """The struct children are literally NAMED "1" (price) and "2" (size).
    Iterating the dict yields the KEYS -- that produced a fake (1.0, 2.0)
    ladder on the first pass. Read by key, explicitly."""
    return [(float(d["1"]), float(d["2"])) for d in arr]


print("\nsample two-sided snapshot ladders:")
for _, row in rich.head(4).iterrows():
    print(f"\n  {row.market_ticker}  recv={row.timestamp_received} exch={row.timestamp}")
    print(f"    yes_bids ({row.yl} lv): {levels(row.yes_bids)[:8]}")
    print(f"    no_bids  ({row.nl} lv): {levels(row.no_bids)[:8]}")

print("\n=== are the ladder prices/sizes plausible? ===")
allp, alls = [], []
for arr in list(rich.yes_bids) + list(rich.no_bids):
    for pr, sz in levels(arr):
        allp.append(pr)
        alls.append(sz)
import numpy as np  # noqa: E402
allp, alls = np.array(allp), np.array(alls)
print(f"  levels parsed: {len(allp)}")
print(f"  price  min={allp.min():.4f} max={allp.max():.4f} "
      f"frac_in_(0,1)={((allp > 0) & (allp < 1)).mean():.4f}")
print(f"  size   min={alls.min():.1f} median={np.median(alls):.1f} "
      f"p90={np.percentile(alls,90):.1f} max={alls.max():.1f} "
      f"frac_positive={(alls > 0).mean():.4f}")
print(f"  distinct prices: {len(np.unique(allp))}  distinct sizes: {len(np.unique(alls))}")

print("\n=== how many DISTINCT tickers ever get a snapshot this hour ===")
print("  snapshot tickers:", df.market_ticker.nunique())
print("  all tickers:     ", len(t.column("market_ticker").unique()))
print("  snapshot rows missing an exchange timestamp:",
      f"{df.timestamp.isna().mean()*100:.1f}%")

ser = df.market_ticker.astype(str).str.split("-").str[0]
print("\n  two-sided snapshot count by series (top 20):")
rser = rich.market_ticker.astype(str).str.split("-").str[0]
import pandas as pd  # noqa: E402
tab = pd.DataFrame({"snapshots": ser.value_counts(),
                    "two_sided": rser.value_counts()}).fillna(0).astype(int)
tab["pct_two_sided"] = (100 * tab.two_sided / tab.snapshots).round(1)
print(tab.sort_values("snapshots", ascending=False).head(20).to_string())
