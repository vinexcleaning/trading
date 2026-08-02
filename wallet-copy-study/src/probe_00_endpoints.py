"""Phase 0 probe: what is actually retrievable, and over what period.

Writes raw probe results to data/probe_00.json. No analysis here -- this only
establishes reachability, schema, and date coverage. Every claim in
docs/data_availability.md must trace back to a record in that file.
"""
import json
import time
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "probe_00.json"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})
TIMEOUT = 45

results = {}


def record(name, **kw):
    results[name] = kw
    status = kw.get("ok")
    print(f"[{'OK ' if status else 'FAIL'}] {name}: {kw.get('note', '')}", flush=True)


def get(url, **kw):
    t0 = time.time()
    r = SESSION.get(url, timeout=TIMEOUT, **kw)
    return r, round((time.time() - t0) * 1000)


def post(url, payload):
    t0 = time.time()
    r = SESSION.post(url, json=payload, timeout=TIMEOUT)
    return r, round((time.time() - t0) * 1000)


# ---------------------------------------------------------------- subgraph
SUBGRAPHS = {
    "goldsky_orderbook": "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/orderbook-subgraph/prod/gn",
    "goldsky_activity": "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/activity-subgraph/prod/gn",
    "goldsky_pnl": "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/pnl-subgraph/prod/gn",
    "goldsky_positions": "https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw/subgraphs/positions-subgraph/prod/gn",
}


def probe_subgraph(name, url):
    # 1. introspect available entities
    q = {"query": "{ __schema { queryType { fields { name } } } }"}
    try:
        r, ms = post(url, q)
    except Exception as e:  # noqa: BLE001
        record(f"subgraph.{name}", ok=False, url=url, error=repr(e))
        return
    if r.status_code != 200:
        record(f"subgraph.{name}", ok=False, url=url, http=r.status_code,
               body=r.text[:400])
        return
    body = r.json()
    if "errors" in body:
        record(f"subgraph.{name}", ok=False, url=url, errors=body["errors"][:2])
        return
    fields = sorted(f["name"] for f in body["data"]["__schema"]["queryType"]["fields"])
    record(f"subgraph.{name}", ok=True, url=url, ms=ms,
           n_entities=len(fields), entities=fields[:80],
           note=f"{len(fields)} query fields")


for n, u in SUBGRAPHS.items():
    probe_subgraph(n, u)

ORDERBOOK = SUBGRAPHS["goldsky_orderbook"]


# ------------------------------------------------- orderFilledEvent extremes
def gql(url, query):
    r, ms = post(url, {"query": query})
    if r.status_code != 200:
        return None, {"http": r.status_code, "body": r.text[:400], "ms": ms}
    b = r.json()
    if "errors" in b:
        return None, {"errors": b["errors"][:3], "ms": ms}
    return b["data"], {"ms": ms}


FILL_FIELDS = """
  id timestamp maker { id } taker { id }
  makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee
  orderHash transactionHash
"""

for direction, order in (("oldest", "asc"), ("newest", "desc")):
    q = f"""{{ orderFilledEvents(first: 3, orderBy: timestamp, orderDirection: {order}) {{ {FILL_FIELDS} }} }}"""
    data, meta = gql(ORDERBOOK, q)
    if data is None:
        record(f"orderFilledEvents.{direction}", ok=False, **meta)
    else:
        rows = data["orderFilledEvents"]
        ts = [int(x["timestamp"]) for x in rows]
        record(f"orderFilledEvents.{direction}", ok=True, n=len(rows), ts=ts,
               iso=[time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(t)) for t in ts],
               sample=rows[0] if rows else None, **meta,
               note=time.strftime("%Y-%m-%d", time.gmtime(ts[0])) if ts else "empty")

# fee field populated?
q = """{ orderFilledEvents(first: 1000, orderBy: timestamp, orderDirection: desc) { fee makerAmountFilled takerAmountFilled } }"""
data, meta = gql(ORDERBOOK, q)
if data:
    rows = data["orderFilledEvents"]
    nonzero = sum(1 for r_ in rows if int(r_["fee"]) != 0)
    record("orderFilledEvents.fee_populated", ok=True, n=len(rows),
           n_fee_nonzero=nonzero, frac=round(nonzero / max(len(rows), 1), 4),
           note=f"{nonzero}/{len(rows)} recent fills have fee != 0")
else:
    record("orderFilledEvents.fee_populated", ok=False, **meta)

# ordersMatchedEvent
q = """{ ordersMatchedEvents(first: 2, orderBy: timestamp, orderDirection: desc) { id timestamp makerAssetID takerAssetID makerAmountFilled takerAmountFilled } }"""
data, meta = gql(ORDERBOOK, q)
record("ordersMatchedEvents", ok=data is not None,
       sample=(data or {}).get("ordersMatchedEvents"), **meta)

# pagination depth: can we skip deep?
for skip in (5000, 25000):
    q = f"""{{ orderFilledEvents(first: 1, skip: {skip}) {{ id timestamp }} }}"""
    data, meta = gql(ORDERBOOK, q)
    record(f"orderFilledEvents.skip_{skip}", ok=data is not None,
           got=(data or {}).get("orderFilledEvents"), **meta)


# ------------------------------------------------------------------- CLOB
CLOB = "https://clob.polymarket.com"
try:
    r, ms = get(f"{CLOB}/")
    record("clob.root", ok=r.ok, http=r.status_code, ms=ms, body=r.text[:200])
except Exception as e:  # noqa: BLE001
    record("clob.root", ok=False, error=repr(e))

for path, note in [("/markets", "paginated market list"),
                   ("/sampling-markets", "markets with rewards"),
                   ("/trades", "auth-required trade tape?")]:
    try:
        r, ms = get(f"{CLOB}{path}")
        j = None
        try:
            j = r.json()
        except Exception:  # noqa: BLE001
            pass
        keys = list(j.keys()) if isinstance(j, dict) else f"list[{len(j)}]" if isinstance(j, list) else None
        record(f"clob{path}", ok=r.ok, http=r.status_code, ms=ms, keys=keys,
               body=r.text[:300], note=note)
    except Exception as e:  # noqa: BLE001
        record(f"clob{path}", ok=False, error=repr(e))


# --------------------------------------------------------------- data-api
DATA = "https://data-api.polymarket.com"
for path, params, note in [
    ("/trades", {"limit": 5}, "public trade tape"),
    ("/trades", {"limit": 100, "offset": 10000}, "offset cap probe"),
    ("/activity", {"limit": 5}, "activity feed"),
    ("/holders", {"limit": 5}, "top holders"),
]:
    try:
        r, ms = get(f"{DATA}{path}", params=params)
        j = None
        try:
            j = r.json()
        except Exception:  # noqa: BLE001
            pass
        n = len(j) if isinstance(j, list) else None
        record(f"data-api{path}?{params}", ok=r.ok, http=r.status_code, ms=ms,
               n=n, sample=(j[0] if isinstance(j, list) and j else None),
               body=None if n else r.text[:300], note=note)
    except Exception as e:  # noqa: BLE001
        record(f"data-api{path}?{params}", ok=False, error=repr(e))


# ----------------------------------------------------------------- gamma
GAMMA = "https://gamma-api.polymarket.com"
try:
    r, ms = get(f"{GAMMA}/markets", params={"limit": 3})
    j = r.json()
    record("gamma.markets", ok=r.ok, http=r.status_code, ms=ms,
           n=len(j) if isinstance(j, list) else None,
           fields=sorted(j[0].keys()) if isinstance(j, list) and j else None,
           sample_ids=[m.get("id") for m in j] if isinstance(j, list) else None,
           note="default ordering -- check if oldest-first")
except Exception as e:  # noqa: BLE001
    record("gamma.markets", ok=False, error=repr(e))

# Does the documented filter actually filter? (prior probing says no)
try:
    r, ms = get(f"{GAMMA}/markets", params={"limit": 20, "tag_slug": "nba"})
    j = r.json()
    record("gamma.filter.tag_slug", ok=r.ok, ms=ms,
           n=len(j) if isinstance(j, list) else None,
           questions=[m.get("question", "")[:70] for m in j][:10] if isinstance(j, list) else None,
           note="VERIFY these are actually NBA")
except Exception as e:  # noqa: BLE001
    record("gamma.filter.tag_slug", ok=False, error=repr(e))

try:
    r, ms = get(f"{GAMMA}/markets", params={"limit": 20, "slug_contains": "bitcoin"})
    j = r.json()
    record("gamma.filter.slug_contains", ok=r.ok, ms=ms,
           n=len(j) if isinstance(j, list) else None,
           slugs=[m.get("slug", "")[:70] for m in j][:10] if isinstance(j, list) else None,
           note="VERIFY these actually contain 'bitcoin'")
except Exception as e:  # noqa: BLE001
    record("gamma.filter.slug_contains", ok=False, error=repr(e))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {OUT}  ({OUT.stat().st_size} bytes)", file=sys.stderr)
