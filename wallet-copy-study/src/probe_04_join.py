"""Phase 0 probe, part 5: does the subgraph address space join to the data API?

Everything in Phase 1 depends on this. The subgraph gives maker/taker EOA-ish
addresses on `orderFilledEvent`; the data API reports `proxyWallet`. Polymarket
routes user orders through proxy contracts, so these may be different address
spaces -- in which case wallet identity cannot be carried between the two
sources and the whole study has to run on one of them alone.

Test: take trades the data API attributes to a wallet, look their
transactionHash up in the subgraph, and see whether that wallet's address
appears as maker, as taker, or nowhere.
"""
import json
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "probe_04_join.json"
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


def iso(ts):
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(ts)))


# Pick active wallets off the live tape, then pull their history far enough
# back to land inside the subgraph's coverage (which ends 2026-04-28).
SUBGRAPH_END = 1777334400          # 2026-04-28

print("== collecting candidate wallets from the live tape ==")
tape = S.get(f"{DATA}/trades", params={"limit": 500}, timeout=45).json()
wallets = [w for w, _ in Counter(t["proxyWallet"] for t in tape).most_common(25)]
rec("tape_wallets", n_trades=len(tape), n_unique=len(set(t["proxyWallet"] for t in tape)),
    top=wallets[:10], note=f"{len(set(t['proxyWallet'] for t in tape))} unique wallets in 500 trades")

print("\n== finding wallet activity inside subgraph coverage ==")
pairs = []          # (wallet, txhash, timestamp) with ts < SUBGRAPH_END
for w in wallets:
    if len(pairs) >= 40:
        break
    for off in (0, 1000, 3000, 5000):
        try:
            r = S.get(f"{DATA}/activity",
                      params={"user": w, "limit": 100, "offset": off}, timeout=45)
            if not r.ok:
                break
            rows = r.json()
        except Exception:  # noqa: BLE001
            break
        if not rows:
            break
        old = [x for x in rows if x.get("timestamp", 0) < SUBGRAPH_END
               and x.get("type") == "TRADE"]
        for x in old[:4]:
            pairs.append({"wallet": w.lower(),
                          "tx": x["transactionHash"].lower(),
                          "ts": x["timestamp"], "price": x.get("price"),
                          "side": x.get("side"), "size": x.get("size")})
        if old:
            break
    if len(pairs) >= 40:
        break
rec("join_candidates", n=len(pairs),
    date_range=[iso(min(p["ts"] for p in pairs)), iso(max(p["ts"] for p in pairs))] if pairs else None,
    note=f"{len(pairs)} data-api trades inside subgraph coverage")

print("\n== looking those transactions up in the subgraph ==")
Q = """
query($tx:String!){
  orderFilledEvents(first:50, where:{transactionHash:$tx}){
    timestamp maker{id} taker{id}
    makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee
  }
}"""
outcome = Counter()
detail = []
for p in pairs[:40]:
    try:
        rows = gql(Q, {"tx": p["tx"]})["orderFilledEvents"]
    except Exception as e:  # noqa: BLE001
        outcome["query_error"] += 1
        continue
    if not rows:
        outcome["tx_not_in_subgraph"] += 1
        detail.append({**p, "verdict": "tx_not_in_subgraph"})
        continue
    makers = {r_["maker"]["id"].lower() for r_ in rows}
    takers = {r_["taker"]["id"].lower() for r_ in rows}
    w = p["wallet"]
    if w in makers and w in takers:
        v = "both"
    elif w in makers:
        v = "maker"
    elif w in takers:
        v = "taker"
    else:
        v = "ABSENT_different_address_space"
    outcome[v] += 1
    detail.append({**p, "verdict": v, "n_fills": len(rows),
                   "makers": sorted(makers)[:3], "takers": sorted(takers)[:3]})

rec("join_verdict", counts=dict(outcome), n_tested=len(detail),
    examples=detail[:6],
    note=f"{dict(outcome)}")

# If the wallet is absent, what addresses ARE there? Are takers a small set
# (i.e. an operator/relayer) while makers are the real users?
if detail:
    all_makers = Counter()
    all_takers = Counter()
    for d in detail:
        for m in d.get("makers", []):
            all_makers[m] += 1
        for t in d.get("takers", []):
            all_takers[t] += 1
    rec("address_concentration",
        top_makers=all_makers.most_common(5),
        top_takers=all_takers.most_common(5),
        n_distinct_makers=len(all_makers), n_distinct_takers=len(all_takers),
        note=f"{len(all_makers)} distinct makers vs {len(all_takers)} distinct takers "
             f"across {len(detail)} txs -- a tiny taker set means a relayer")

OUT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {OUT}")
