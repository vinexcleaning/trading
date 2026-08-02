"""Can we resolve a market from a token id / condition id on demand?

If yes, the sampling frame can be driven from FILLS rather than from a market
enumeration: draw random time windows, pull every fill, collect the distinct
asset ids, and look each one up. That sidesteps Gamma's offset ceiling
(~2500) entirely and guarantees the sampled markets are ones that actually
traded, which is what the study needs.

Tests targeted lookups on both APIs, and checks that the settlement they report
AGREES -- CLOB `tokens[].winner` versus Gamma `outcomePrices`. Two independent
sources agreeing is the only reason to trust either.
"""
import json
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "probe_07_lookup.json"
S = requests.Session()
S.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})
CLOB = "https://clob.polymarket.com"
GAMMA = "https://gamma-api.polymarket.com"
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
        raise RuntimeError(str(b["errors"])[:300])
    return b["data"]


# ---- grab real asset ids out of the subgraph, mid-history so they're settled
LO = 1740000000        # 2025-02-19
Q = """
query($lo:BigInt!,$hi:BigInt!){
  orderFilledEvents(first:400, orderBy:timestamp, orderDirection:asc,
    where:{timestamp_gte:$lo, timestamp_lt:$hi}){
    makerAssetId takerAssetId timestamp }
}"""
fills = gql(Q, {"lo": str(LO), "hi": str(LO + 3600)})["orderFilledEvents"]
assets = []
for f in fills:
    for k in ("makerAssetId", "takerAssetId"):
        a = f[k]
        if a and a != "0":
            assets.append(a)
uniq = list(dict.fromkeys(assets))
rec("assets_from_fills", n_fills=len(fills), n_distinct_assets=len(uniq),
    sample=uniq[:3],
    note=f"{len(fills)} fills -> {len(uniq)} distinct outcome tokens")

# ------------------------------------------------ CLOB single-market lookup
print("\n== CLOB /markets/{condition_id} and token lookup ==")
# first map a token -> condition via CLOB's book endpoint or market search
tok = uniq[0]
try:
    r = S.get(f"{CLOB}/book", params={"token_id": tok}, timeout=45)
    rec("clob_book_by_token", ok=r.ok, http=r.status_code,
        keys=list(r.json().keys()) if r.ok else None, body=r.text[:200],
        note="book lookup by token id")
except Exception as e:  # noqa: BLE001
    rec("clob_book_by_token", error=repr(e)[:160], note="error")

# ---------------------------------------------- Gamma targeted lookups
print("\n== Gamma targeted lookups (do these filters work?) ==")
base_ids = [x.get("id") for x in S.get(
    f"{GAMMA}/markets", params={"limit": 20, "order": "createdAt",
                                "ascending": "false"}, timeout=45).json()]

for name, params in [
    ("clob_token_ids", {"clob_token_ids": uniq[0]}),
    ("clob_token_ids x3", {"clob_token_ids": uniq[:3]}),
]:
    try:
        r = S.get(f"{GAMMA}/markets", params=params, timeout=45)
        j = r.json() if r.ok else None
        ids = [x.get("id") for x in j] if isinstance(j, list) else None
        ignored = ids == base_ids
        ok_semantics = None
        if isinstance(j, list) and j:
            want = set(params["clob_token_ids"]) if isinstance(
                params["clob_token_ids"], list) else {params["clob_token_ids"]}
            got = set()
            for m in j:
                try:
                    got |= set(json.loads(m.get("clobTokenIds") or "[]"))
                except Exception:  # noqa: BLE001
                    pass
            ok_semantics = bool(want & got)
        rec(f"gamma_lookup[{name}]", ok=r.ok, http=r.status_code,
            n=len(j) if isinstance(j, list) else None,
            identical_to_unfiltered=ignored, semantics_hold=ok_semantics,
            sample_q=(j[0].get("question", "")[:70] if isinstance(j, list) and j else None),
            note=("IGNORED" if ignored else
                  f"n={len(j) if isinstance(j,list) else '?'} semantics_hold={ok_semantics}"))
    except Exception as e:  # noqa: BLE001
        rec(f"gamma_lookup[{name}]", error=repr(e)[:160], note="error")

# condition_ids lookup needs a real condition id: take it from the above
cond = None
try:
    j = S.get(f"{GAMMA}/markets", params={"clob_token_ids": uniq[0]}, timeout=45).json()
    if isinstance(j, list) and j:
        cond = j[0].get("conditionId")
except Exception:  # noqa: BLE001
    pass
if cond:
    for name, params in [("condition_ids", {"condition_ids": cond})]:
        try:
            r = S.get(f"{GAMMA}/markets", params=params, timeout=45)
            j = r.json() if r.ok else None
            ids = [x.get("id") for x in j] if isinstance(j, list) else None
            rec(f"gamma_lookup[{name}]", ok=r.ok, n=len(j) if isinstance(j, list) else None,
                identical_to_unfiltered=(ids == base_ids),
                semantics_hold=(isinstance(j, list) and bool(j)
                                and j[0].get("conditionId") == cond),
                note=f"cond={cond[:14]}… -> "
                     f"{'MATCH' if isinstance(j,list) and j and j[0].get('conditionId')==cond else 'MISMATCH'}")
        except Exception as e:  # noqa: BLE001
            rec(f"gamma_lookup[{name}]", error=repr(e)[:160], note="error")

    # CLOB by condition id
    try:
        r = S.get(f"{CLOB}/markets/{cond}", timeout=45)
        j = r.json() if r.ok else None
        rec("clob_market_by_condition", ok=r.ok, http=r.status_code,
            tokens=(j or {}).get("tokens"), closed=(j or {}).get("closed"),
            end_date=(j or {}).get("end_date_iso"),
            note=f"{'ok' if r.ok else r.status_code} -- winner flags present"
                 f"={bool((j or {}).get('tokens'))}")
    except Exception as e:  # noqa: BLE001
        rec("clob_market_by_condition", error=repr(e)[:160], note="error")

# --------------------------------- do CLOB winner and Gamma prices agree?
print("\n== settlement cross-check: CLOB winner vs Gamma outcomePrices ==")
agree = Counter()
detail = []
for tok in uniq[:25]:
    try:
        gj = S.get(f"{GAMMA}/markets", params={"clob_token_ids": tok}, timeout=45).json()
        if not (isinstance(gj, list) and gj):
            agree["gamma_miss"] += 1
            continue
        m = gj[0]
        c = m.get("conditionId")
        cj = S.get(f"{CLOB}/markets/{c}", timeout=45)
        if not cj.ok:
            agree["clob_miss"] += 1
            continue
        cm = cj.json()
        toks = cm.get("tokens") or []
        clob_winner = next((t["token_id"] for t in toks if t.get("winner")), None)
        try:
            gp = [float(x) for x in json.loads(m.get("outcomePrices") or "[]")]
            gt = json.loads(m.get("clobTokenIds") or "[]")
            gamma_winner = gt[gp.index(1.0)] if 1.0 in gp and len(gt) == len(gp) else None
        except Exception:  # noqa: BLE001
            gamma_winner = None
        if clob_winner is None and gamma_winner is None:
            agree["both_unresolved"] += 1
        elif clob_winner == gamma_winner:
            agree["AGREE"] += 1
        else:
            agree["DISAGREE"] += 1
            detail.append({"cond": c, "clob": clob_winner, "gamma": gamma_winner,
                           "closed": cm.get("closed"),
                           "q": (m.get("question") or "")[:60]})
    except Exception:  # noqa: BLE001
        agree["error"] += 1
rec("settlement_crosscheck", counts=dict(agree), disagreements=detail[:6],
    note=f"{dict(agree)}")

OUT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {OUT}")
