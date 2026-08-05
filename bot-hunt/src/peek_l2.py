"""What is actually in the L2 rows? Written before the replay, not after.

The sibling's own retraction is the lesson: they verified the FILES EXIST and
inferred the contents from the filename cadence. This opens the data, because
the fill model depends entirely on what `event_type`, `yes_bids`, `delta` and
`side` really mean — and on whether snapshots can be ordered against deltas at
all, which the first look says may not be true.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

D = Path(__file__).resolve().parent.parent / "data" / "l2"
files = sorted(D.glob("es_*.parquet"))
print(f"{len(files)} filtered hours on disk")
if not files:
    raise SystemExit("nothing pulled yet")

f = files[len(files) // 2]
t = pq.read_table(f)
d = t.to_pydict()
print(f"file {f.name}  rows={t.num_rows:,}")
print(f"event_type: {Counter(d['event_type']).most_common()}")

snap_idx = [i for i, e in enumerate(d["event_type"]) if e == "orderbook_snapshot"]
print(f"\n== SNAPSHOTS: {len(snap_idx)}")
null_ts = sum(1 for i in snap_idx if d["timestamp"][i] is None)
empty = sum(1 for i in snap_idx
            if not d["yes_bids"][i] and not d["no_bids"][i])
print(f"   with NULL timestamp : {null_ts}/{len(snap_idx)}")
print(f"   with EMPTY ladders  : {empty}/{len(snap_idx)}")

print("\n   first 3 snapshots WITH a populated ladder:")
shown = 0
for i in snap_idx:
    if d["yes_bids"][i] or d["no_bids"][i]:
        yb = [(float(x["1"]), float(x["2"])) for x in (d["yes_bids"][i] or [])]
        nb = [(float(x["1"]), float(x["2"])) for x in (d["no_bids"][i] or [])]
        print(f"     {d['market_ticker'][i]}  ts={d['timestamp'][i]}")
        print(f"       yes_bids ({len(yb)}): {yb[:6]}")
        print(f"       no_bids  ({len(nb)}): {nb[:6]}")
        shown += 1
        if shown >= 3:
            break
if shown == 0:
    print("     NONE — every snapshot in this hour has empty ladders")

# Per ticker: is there a usable snapshot to seed the book from?
per = defaultdict(lambda: {"snap": 0, "snap_full": 0, "delta": 0,
                           "first_delta": None, "last_delta": None})
for i, tk in enumerate(d["market_ticker"]):
    p = per[tk]
    if d["event_type"][i] == "orderbook_snapshot":
        p["snap"] += 1
        if d["yes_bids"][i] or d["no_bids"][i]:
            p["snap_full"] += 1
    else:
        p["delta"] += 1
        ts = d["timestamp"][i]
        if ts is not None:
            if p["first_delta"] is None:
                p["first_delta"] = ts
            p["last_delta"] = ts

seeded = sum(1 for v in per.values() if v["snap_full"] > 0)
print(f"\n== PER TICKER ({len(per)} tickers in this hour)")
print(f"   with >=1 POPULATED snapshot (book can be seeded): {seeded}")
print(f"   with only deltas (book must be inferred):         {len(per)-seeded}")
print(f"\n   {'ticker':44} {'snaps':>6} {'full':>5} {'deltas':>7}  span")
for tk, v in sorted(per.items(), key=lambda x: -x[1]["delta"])[:8]:
    span = ""
    if v["first_delta"] and v["last_delta"]:
        span = f"{v['first_delta']:%H:%M:%S} -> {v['last_delta']:%H:%M:%S}"
    print(f"   {tk[:44]:44} {v['snap']:>6} {v['snap_full']:>5} "
          f"{v['delta']:>7}  {span}")

print("\n== DELTA semantics")
sgn = Counter("neg" if float(x) < 0 else ("pos" if float(x) > 0 else "zero")
              for x in d["delta"] if x is not None)
print(f"   delta sign: {dict(sgn)}")
pr = [float(x) for x in d["price"] if x is not None]
if pr:
    print(f"   price range: {min(pr):.4f} .. {max(pr):.4f}  "
          f"(so prices are DOLLARS; 0.46 = 46c)")
print(f"   side: {Counter(d['side']).most_common()}")
