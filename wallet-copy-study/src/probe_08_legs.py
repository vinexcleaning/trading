"""Is `taker` on orderFilledEvent a real wallet, or the exchange operator?

This is a fork in the road for Phase 1. If both legs are users, every fill is
two wallet-trades and a naive pass would double-count. If `taker` is the
matcher/operator, then each user order appears exactly once as `maker`, and the
taker field must be ignored entirely rather than treated as a counterparty.

Evidence so far points at the second reading: 513 makers vs 249 takers per 1000
fills, top taker 29.8% of flow, and the two heaviest takers have no data API
record at all. That is suggestive, not conclusive. Three tests here:

  1. Within one transaction, does the taker of event A appear as the maker of
     event B? If matching emits one OrderFilled per user order, it should.
  2. What share of distinct taker addresses have a data API record (i.e. are
     real user proxy wallets) versus none (contracts)?
  3. Do the maker legs within a transaction balance -- buys against sells on
     the same token -- which is what a match of two user orders looks like?
"""
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "probe_08_legs.json"
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
    r = S.post(ORDERBOOK, json={"query": q, "variables": v or {}}, timeout=90)
    r.raise_for_status()
    b = r.json()
    if "errors" in b:
        raise RuntimeError(str(b["errors"])[:300])
    return b["data"]


LO = 1777200000
Q = """
query($lo:BigInt!,$hi:BigInt!){
  orderFilledEvents(first:1000, orderBy:timestamp, orderDirection:asc,
    where:{timestamp_gte:$lo, timestamp_lt:$hi}){
    id timestamp transactionHash maker taker
    makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee }
}"""
fills = gql(Q, {"lo": str(LO), "hi": str(LO + 1800)})["orderFilledEvents"]
print(f"pulled {len(fills)} fills")

by_tx = defaultdict(list)
for f in fills:
    by_tx[f["transactionHash"]].append(f)

# ---- test 1: taker of one event == maker of another, same tx?
t1 = Counter()
multi = 0
for tx, evs in by_tx.items():
    makers = {str(e["maker"]).lower() for e in evs}
    takers = {str(e["taker"]).lower() for e in evs}
    if len(evs) > 1:
        multi += 1
    if takers & makers:
        t1["taker_also_a_maker_in_same_tx"] += 1
    else:
        t1["taker_never_a_maker_in_same_tx"] += 1
rec("test1_leg_structure", counts=dict(t1), n_tx=len(by_tx),
    n_tx_multi_event=multi,
    mean_events_per_tx=round(len(fills) / max(len(by_tx), 1), 2),
    note=f"{dict(t1)} over {len(by_tx)} txs "
         f"({round(len(fills)/max(len(by_tx),1),2)} events/tx)")

# ---- test 2: do taker addresses exist in the data API?
takers = Counter(str(f["taker"]).lower() for f in fills)
makers = Counter(str(f["maker"]).lower() for f in fills)
rec("cardinality", n_fills=len(fills),
    n_distinct_makers=len(makers), n_distinct_takers=len(takers),
    top_takers=takers.most_common(5),
    top_taker_share=round(takers.most_common(1)[0][1] / len(fills), 3),
    note=f"{len(makers)} makers vs {len(takers)} takers; "
         f"top taker {takers.most_common(1)[0][1]/len(fills):.1%} of flow")

print("\n== data API recognition of taker vs maker addresses ==")
def recognised(addr):
    try:
        r = S.get(f"{DATA}/activity", params={"user": addr, "limit": 5}, timeout=40)
        if not r.ok:
            return None
        j = r.json()
        return bool(isinstance(j, list) and j)
    except Exception:  # noqa: BLE001
        return None


tk_res, mk_res = Counter(), Counter()
for a, _ in takers.most_common(12):
    tk_res[str(recognised(a))] += 1
for a, _ in makers.most_common(12):
    mk_res[str(recognised(a))] += 1
rec("data_api_recognition",
    takers=dict(tk_res), makers=dict(mk_res),
    note=f"takers recognised={dict(tk_res)} | makers recognised={dict(mk_res)}")

# ---- test 3: do maker legs within a tx balance (buy vs sell, same token)?
def decode(x):
    ma, ta = x["makerAssetId"], x["takerAssetId"]
    mf, tf = int(x["makerAmountFilled"]), int(x["takerAmountFilled"])
    if ma == "0" and ta != "0":
        return "BUY", ta, tf, mf
    if ta == "0" and ma != "0":
        return "SELL", ma, mf, tf
    return None


t3 = Counter()
examples = []
for tx, evs in by_tx.items():
    if len(evs) < 2:
        t3["single_event_tx"] += 1
        continue
    net = defaultdict(float)
    sides = Counter()
    for e in evs:
        d = decode(e)
        if not d:
            t3["undecodable_leg"] += 1
            continue
        side, token, shares, _ = d
        sides[side] += 1
        net[token] += shares if side == "BUY" else -shares
    if sides["BUY"] and sides["SELL"]:
        t3["tx_has_both_buy_and_sell_makers"] += 1
        worst = max((abs(v) for v in net.values()), default=0)
        tot = sum(abs(v) for v in net.values()) or 1
        if worst / tot < 0.01:
            t3["net_share_flow_balances"] += 1
        else:
            t3["net_share_flow_does_not_balance"] += 1
            if len(examples) < 4:
                examples.append({"tx": tx[:20], "n": len(evs),
                                 "net": {k[:12]: round(v, 3) for k, v in net.items()}})
    else:
        t3["tx_makers_all_same_side"] += 1
rec("test3_balance", counts=dict(t3), examples=examples, note=f"{dict(t3)}")

# ---- test 4: does the same (wallet, tx) appear as maker AND taker anywhere?
pair = Counter()
for f in fills:
    if str(f["maker"]).lower() == str(f["taker"]).lower():
        pair["self_match"] += 1
rec("self_match", counts=dict(pair),
    note=f"{pair.get('self_match',0)} fills where maker == taker")

OUT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {OUT}")
