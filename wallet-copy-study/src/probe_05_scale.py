"""Phase 1 prep: how big is the corpus, and how do we page it without `skip`?

Two things must be settled before any bulk pull:
  1. total fill volume, so the sampling frame is chosen deliberately rather than
     by whatever fits;
  2. a pagination method that does not rely on `skip`, which graph-node caps
     (usually at 5000) and which degrades badly at depth.

The cursor method used below is order-by-id-ascending with `id_gt`, which is
O(1) per page regardless of depth.
"""
import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "probe_05_scale.json"
S = requests.Session()
S.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})
ORDERBOOK = ("https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw"
             "/subgraphs/orderbook-subgraph/prod/gn")
res = {}


def rec(k, **kw):
    res[k] = kw
    print(f"  {k}: {kw.get('note', '')}", flush=True)


def gql(q, v=None):
    r = S.post(ORDERBOOK, json={"query": q, "variables": v or {}}, timeout=90)
    r.raise_for_status()
    b = r.json()
    if "errors" in b:
        raise RuntimeError(b["errors"])
    return b["data"]


def iso(ts, f="%Y-%m-%d"):
    return time.strftime(f, time.gmtime(int(ts)))


print("== aggregate entities: is there a global counter? ==")
for ent, fields in [
    ("ordersMatchedGlobals", "id tradesQuantity buysQuantity sellsQuantity "
                             "collateralVolume scaledCollateralVolume "
                             "collateralBuyVolume collateralSellVolume"),
    ("marketDatas", "id condition outcomeIndex priceOrderbook"),
    ("orderbooks", "id tradesQuantity buysQuantity sellsQuantity "
                   "collateralVolume scaledCollateralVolume lastActiveDay"),
]:
    try:
        d = gql(f"{{ {ent}(first: 3) {{ {fields} }} }}")
        rec(f"entity.{ent}", ok=True, sample=d[ent],
            note=f"{len(d[ent])} rows, fields resolve")
    except Exception as e:  # noqa: BLE001
        rec(f"entity.{ent}", ok=False, error=str(e)[:400], note="field mismatch")

print("\n== does `skip` cap out? ==")
for sk in (5000, 5001, 10000, 30000, 100000):
    try:
        d = gql(f"{{ orderFilledEvents(first:1, skip:{sk}) {{ id }} }}")
        rec(f"skip_{sk}", ok=True, n=len(d["orderFilledEvents"]),
            note=f"skip={sk} ok")
    except Exception as e:  # noqa: BLE001
        rec(f"skip_{sk}", ok=False, error=str(e)[:200], note=f"skip={sk} REJECTED")

print("\n== cursor paging by id (the method we will actually use) ==")
Q = """
query($lo:BigInt!,$hi:BigInt!,$cur:String!){
  orderFilledEvents(first:1000, orderBy:id, orderDirection:asc,
    where:{timestamp_gte:$lo, timestamp_lt:$hi, id_gt:$cur}){ id timestamp }
}"""
t0 = time.time()
lo = 1777248000                      # 2026-04-27
hi = lo + 86400
cur, n, pages = "", 0, 0
while True:
    rows = gql(Q, {"lo": str(lo), "hi": str(hi), "cur": cur})["orderFilledEvents"]
    if not rows:
        break
    n += len(rows)
    cur = rows[-1]["id"]
    pages += 1
    if pages > 200:
        break
el = time.time() - t0
rec("cursor_paging_one_day", date=iso(lo), n_fills=n, pages=pages,
    seconds=round(el, 1), fills_per_sec=round(n / el),
    note=f"{n} fills on {iso(lo)} in {pages} pages, {el:.1f}s "
         f"({round(n/el)} fills/s)")

print("\n== daily fill volume across the history (sizing the corpus) ==")
daily = {}
probe_days = []
for y, mo in [(2022, 12), (2023, 3), (2023, 6), (2023, 9), (2023, 12),
              (2024, 3), (2024, 6), (2024, 9), (2024, 12),
              (2025, 3), (2025, 6), (2025, 9), (2025, 12),
              (2026, 2), (2026, 4)]:
    probe_days.append(int(time.mktime(time.struct_time((y, mo, 15, 0, 0, 0, 0, 1, 0)))))

for d in probe_days:
    cur, n, pages = "", 0, 0
    while True:
        rows = gql(Q, {"lo": str(d), "hi": str(d + 86400), "cur": cur})["orderFilledEvents"]
        if not rows:
            break
        n += len(rows)
        cur = rows[-1]["id"]
        pages += 1
        if pages > 400:
            n = -n          # mark truncated
            break
    daily[iso(d)] = n
    print(f"    {iso(d)}  fills={n}", flush=True)

vals = [v for v in daily.values() if v > 0]
est_total = int(sum(vals) / len(vals) * ((1777374040 - 1669060209) / 86400)) if vals else None
rec("daily_volume", daily=daily,
    mean_daily=int(sum(vals) / len(vals)) if vals else None,
    est_total_fills=est_total,
    note=f"mean {int(sum(vals)/len(vals)) if vals else 0} fills/day -> "
         f"~{est_total:,} fills over the full history" if est_total else "n/a")

# how long would a full pull take at observed throughput?
if est_total and res.get("cursor_paging_one_day", {}).get("fills_per_sec"):
    fps = res["cursor_paging_one_day"]["fills_per_sec"]
    rec("full_pull_cost", est_total=est_total, fills_per_sec=fps,
        est_hours=round(est_total / fps / 3600, 1),
        note=f"a complete pull is ~{round(est_total/fps/3600,1)}h at {fps} fills/s")

OUT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {OUT}")
