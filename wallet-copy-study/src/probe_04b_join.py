"""Phase 0 probe 5b: address-space join, tested from the subgraph side.

probe_04 failed to find overlap because the live tape's active wallets have
>5000 activity rows newer than the subgraph cutoff, and the activity endpoint
caps at offset 5000. So go the other way: pull maker/taker addresses out of the
subgraph and ask the data API what it knows about them. If subgraph addresses
are proxy wallets, /activity?user=<addr> returns that wallet's trades and the
transactionHash values will match.
"""
import json
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "probe_04b_join.json"
S = requests.Session()
S.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})
ORDERBOOK = ("https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw"
             "/subgraphs/orderbook-subgraph/prod/gn")
DATA = "https://data-api.polymarket.com"
res = {}


def rec(k, **kw):
    res[k] = kw
    print(f"  {k}: {kw.get('note', '')}", flush=True)


def gql(q, v=None):
    r = S.post(ORDERBOOK, json={"query": q, "variables": v or {}}, timeout=60)
    r.raise_for_status()
    b = r.json()
    if "errors" in b:
        raise RuntimeError(b["errors"])
    return b["data"]


def _addr(v):
    """maker/taker come back as a bare address string, not an entity ref."""
    if isinstance(v, dict):
        v = v.get("id", "")
    return str(v).lower()


def iso(ts):
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ts)))


HI = 1777334400                # 2026-04-28
LO = HI - 86400 * 2

print("== pulling fills from the subgraph tail ==")
Q = """
query($lo:BigInt!,$hi:BigInt!){
  orderFilledEvents(first:1000, orderBy:timestamp, orderDirection:desc,
    where:{timestamp_gte:$lo, timestamp_lt:$hi}){
    timestamp transactionHash maker taker
    makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee
  }
}"""
fills = gql(Q, {"lo": str(LO), "hi": str(HI)})["orderFilledEvents"]
makers = Counter(_addr(f["maker"]) for f in fills)
takers = Counter(_addr(f["taker"]) for f in fills)
rec("subgraph_tail", n_fills=len(fills), window=[iso(LO), iso(HI)],
    n_distinct_makers=len(makers), n_distinct_takers=len(takers),
    top_makers=makers.most_common(5), top_takers=takers.most_common(5),
    note=f"{len(fills)} fills | {len(makers)} makers, {len(takers)} takers -- "
         f"a tiny taker set would mean the taker leg is a relayer")

print("\n== asking the data API about subgraph addresses ==")
tx_by_addr = {}
for f in fills:
    for role in ("maker", "taker"):
        a = _addr(f[role])
        tx_by_addr.setdefault(a, set()).add(f["transactionHash"].lower())

# test a spread of makers (heavy and light) plus the top takers
cands = [a for a, _ in makers.most_common(8)] + \
        [a for a, _ in makers.most_common()[-8:]] + \
        [a for a, _ in takers.most_common(4)]
seen, verdicts, detail = set(), Counter(), []
for a in cands:
    if a in seen:
        continue
    seen.add(a)
    try:
        r = S.get(f"{DATA}/activity", params={"user": a, "limit": 200}, timeout=45)
        rows = r.json() if r.ok else []
    except Exception as e:  # noqa: BLE001
        verdicts["error"] += 1
        continue
    if not isinstance(rows, list) or not rows:
        verdicts["no_data_api_record"] += 1
        detail.append({"addr": a, "role": "maker" if a in makers else "taker",
                       "subgraph_fills": makers.get(a, 0) + takers.get(a, 0),
                       "verdict": "no_data_api_record", "n_rows": 0})
        continue
    api_tx = {x.get("transactionHash", "").lower() for x in rows}
    hit = len(api_tx & tx_by_addr[a])
    pw = {x.get("proxyWallet", "").lower() for x in rows}
    v = "tx_overlap" if hit else "record_but_no_tx_overlap"
    verdicts[v] += 1
    detail.append({"addr": a, "role": "maker" if a in makers else "taker",
                   "subgraph_fills": makers.get(a, 0) + takers.get(a, 0),
                   "verdict": v, "n_rows": len(rows), "tx_overlap": hit,
                   "proxyWallet_matches_query": (pw == {a}),
                   "api_range": [iso(min(x["timestamp"] for x in rows)),
                                 iso(max(x["timestamp"] for x in rows))]})

rec("join_verdict", counts=dict(verdicts), n_tested=len(detail),
    detail=detail[:20],
    note=f"{dict(verdicts)}")

# Is the taker leg a relayer/operator? Check how concentrated it is over a
# wider window, and whether those addresses are contracts with huge fill counts.
print("\n== taker-leg concentration over a wider window ==")
Q2 = """
query($lo:BigInt!,$hi:BigInt!,$skip:Int!){
  orderFilledEvents(first:1000, skip:$skip, orderBy:timestamp, orderDirection:desc,
    where:{timestamp_gte:$lo, timestamp_lt:$hi}){ maker taker }
}"""
mk, tk = Counter(), Counter()
for i in range(5):
    rows = gql(Q2, {"lo": str(HI - 86400 * 7), "hi": str(HI), "skip": i * 1000})["orderFilledEvents"]
    for f in rows:
        mk[_addr(f["maker"])] += 1
        tk[_addr(f["taker"])] += 1
    if len(rows) < 1000:
        break
tot = sum(tk.values())
rec("taker_concentration", n_fills=tot,
    n_distinct_makers=len(mk), n_distinct_takers=len(tk),
    top_takers=[(a, c, round(c / tot, 3)) for a, c in tk.most_common(6)],
    top_makers=[(a, c, round(c / tot, 3)) for a, c in mk.most_common(6)],
    note=f"{tot} fills: {len(mk)} makers vs {len(tk)} takers; "
         f"top taker share {tk.most_common(1)[0][1]/tot:.1%}")

OUT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {OUT}")
