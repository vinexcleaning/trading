"""Phase 1 prep (retry): corpus size and a pagination method that survives.

probe_05 tried an id cursor with a timestamp filter. graph-node cannot serve
that -- ordering by id while filtering on timestamp scans the table and the
statement times out. But `skip` was accepted all the way to 100,000, so the
working method is: narrow time window + skip within it, with the window sized
so the fill count stays inside the skip ceiling.

Also reads ordersMatchedGlobals, which is a single-row global counter and gives
the corpus size for free.
"""
import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "probe_05b_scale.json"
S = requests.Session()
S.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})
ORDERBOOK = ("https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw"
             "/subgraphs/orderbook-subgraph/prod/gn")
res = {}


def rec(k, **kw):
    res[k] = kw
    print(f"  {k}: {kw.get('note', '')}", flush=True)


def gql(q, v=None, retries=3):
    for a in range(retries):
        try:
            r = S.post(ORDERBOOK, json={"query": q, "variables": v or {}}, timeout=120)
            r.raise_for_status()
            b = r.json()
            if "errors" in b:
                raise RuntimeError(str(b["errors"])[:300])
            return b["data"]
        except Exception:  # noqa: BLE001
            if a == retries - 1:
                raise
            time.sleep(2 * (a + 1))
    return None


def iso(ts, f="%Y-%m-%d"):
    return time.strftime(f, time.gmtime(int(ts)))


print("== global counter ==")
d = gql("""{ ordersMatchedGlobals(first:1){ id tradesQuantity buysQuantity
            sellsQuantity collateralVolume scaledCollateralVolume } }""")
g = d["ordersMatchedGlobals"][0] if d["ordersMatchedGlobals"] else {}
rec("global_counter", raw=g,
    note=f"tradesQuantity={g.get('tradesQuantity')} "
         f"scaledCollateralVolume={g.get('scaledCollateralVolume')}")

print("\n== counting a day with window+skip paging ==")
Q = """
query($lo:BigInt!,$hi:BigInt!,$skip:Int!){
  orderFilledEvents(first:1000, skip:$skip, orderBy:timestamp, orderDirection:asc,
    where:{timestamp_gte:$lo, timestamp_lt:$hi}){ id timestamp }
}"""


def count_window(lo, hi, cap_pages=120):
    """Count fills in [lo,hi) with skip paging. Returns (n, truncated, pages)."""
    n, pages = 0, 0
    ids = set()
    while pages < cap_pages:
        rows = gql(Q, {"lo": str(lo), "hi": str(hi), "skip": pages * 1000})["orderFilledEvents"]
        if not rows:
            return n, False, pages
        ids.update(r_["id"] for r_ in rows)
        n += len(rows)
        pages += 1
        if len(rows) < 1000:
            return len(ids), False, pages
    return len(ids), True, pages


t0 = time.time()
n, trunc, pages = count_window(1777248000, 1777248000 + 3600)
el = time.time() - t0
rec("hour_paging", date=iso(1777248000), n_fills=n, truncated=trunc, pages=pages,
    seconds=round(el, 1), fills_per_sec=round(n / el) if el else None,
    note=f"{n} fills in one hour, {pages} pages, {el:.1f}s "
         f"({round(n/el) if el else 0} fills/s)")

print("\n== daily fill volume across the history ==")
daily = {}
for y, mo in [(2022, 12), (2023, 3), (2023, 6), (2023, 9), (2023, 12),
              (2024, 3), (2024, 6), (2024, 9), (2024, 12),
              (2025, 3), (2025, 6), (2025, 9), (2025, 12),
              (2026, 2), (2026, 4)]:
    d0 = int(time.mktime(time.struct_time((y, mo, 15, 0, 0, 0, 0, 1, 0))))
    tot, tr = 0, False
    for h in range(0, 86400, 3600 * 6):        # 4 x 6h windows
        c, t, _ = count_window(d0 + h, d0 + h + 3600 * 6)
        tot += c
        tr = tr or t
    daily[iso(d0)] = {"n": tot, "truncated": tr}
    print(f"    {iso(d0)}  fills={tot:>7}{'  (TRUNCATED)' if tr else ''}", flush=True)

vals = [v["n"] for v in daily.values()]
span_days = (1777374040 - 1669060209) / 86400
mean = sum(vals) / len(vals)
rec("daily_volume", daily=daily, mean_daily=int(mean),
    span_days=round(span_days),
    est_total_fills=int(mean * span_days),
    note=f"mean {int(mean):,} fills/day over {round(span_days)} days "
         f"-> ~{int(mean*span_days):,} fills total")

fps = res["hour_paging"].get("fills_per_sec") or 1
rec("full_pull_cost", est_total=int(mean * span_days), fills_per_sec=fps,
    est_hours=round(mean * span_days / fps / 3600, 1),
    note=f"complete pull ~{round(mean*span_days/fps/3600,1)}h at {fps} fills/s "
         f"-- sampling frame must be chosen, not the whole corpus")

OUT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {OUT}")
