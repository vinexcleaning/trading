r"""Probe the CLOB for the cheapest way to record real bid/ask.

The one number the whole study now hangs on is the true effective spread. Every
"net" figure subtracts a 1.0pp floor derived from same-block trade-price
dispersion, which is a LOWER bound because the subgraph carries no book. If the
real spread is 1.5pp the politics edge is dead; if it is 0.5pp it is alive.

Before recording for hours, find out which endpoints exist and which are batched
-- polling one token at a time would cap how many markets can be watched.
"""
import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "rec_probe.json"
CLOB = "https://clob.polymarket.com"
S = requests.Session()
S.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})
res = {}


def rec(k, **kw):
    res[k] = kw
    print(f"[{'OK ' if kw.get('ok') else 'FAIL'}] {k}: {kw.get('note','')}",
          flush=True)


# ---- find some live, order-book-enabled tokens
print("finding live tokens...", flush=True)
live = []
cur = ""
for _ in range(6):
    r = S.get(f"{CLOB}/sampling-markets",
              params={"next_cursor": cur} if cur else {}, timeout=45)
    if not r.ok:
        break
    j = r.json()
    for m in j.get("data", []):
        if m.get("accepting_orders") and m.get("enable_order_book"):
            for t in (m.get("tokens") or []):
                if t.get("token_id"):
                    live.append({"token_id": t["token_id"],
                                 "condition_id": m.get("condition_id"),
                                 "slug": m.get("market_slug"),
                                 "outcome": t.get("outcome"),
                                 "tags": m.get("tags"),
                                 "min_tick": m.get("minimum_tick_size")})
    cur = j.get("next_cursor") or ""
    if not cur or cur == "LTE=":
        break
rec("live_tokens", ok=bool(live), n=len(live), sample=live[:2],
    note=f"{len(live)} order-book-enabled tokens on accepting markets")

if not live:
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    raise SystemExit("no live tokens found")

tid = live[0]["token_id"]
tids = [x["token_id"] for x in live[:20]]

# ---- single book
try:
    t0 = time.time()
    r = S.get(f"{CLOB}/book", params={"token_id": tid}, timeout=45)
    j = r.json() if r.ok else None
    bids = (j or {}).get("bids") or []
    asks = (j or {}).get("asks") or []
    rec("book_single", ok=r.ok, ms=round((time.time() - t0) * 1000),
        keys=sorted(j.keys()) if isinstance(j, dict) else None,
        n_bids=len(bids), n_asks=len(asks),
        best_bid=bids[-1] if bids else None, best_ask=asks[-1] if asks else None,
        note=f"{len(bids)} bids / {len(asks)} asks")
except Exception as e:  # noqa: BLE001
    rec("book_single", ok=False, error=repr(e)[:200])

# ---- batched books (POST)
for path in ("/books", "/prices", "/midpoints", "/spreads"):
    try:
        payload = [{"token_id": t, "side": "BUY"} for t in tids[:5]] \
            if path in ("/prices",) else [{"token_id": t} for t in tids[:5]]
        t0 = time.time()
        r = S.post(f"{CLOB}{path}", json=payload, timeout=45)
        j = r.json() if r.ok else None
        rec(f"POST{path}", ok=r.ok, http=r.status_code,
            ms=round((time.time() - t0) * 1000),
            type=type(j).__name__,
            n=len(j) if isinstance(j, (list, dict)) else None,
            sample=(j[:1] if isinstance(j, list) else
                    dict(list(j.items())[:2]) if isinstance(j, dict) else None),
            body=None if r.ok else r.text[:200],
            note=f"batched {len(payload)} tokens" if r.ok else "unavailable")
    except Exception as e:  # noqa: BLE001
        rec(f"POST{path}", ok=False, error=repr(e)[:200])

# ---- single-token GET variants
for path in ("/midpoint", "/spread"):
    try:
        t0 = time.time()
        r = S.get(f"{CLOB}{path}", params={"token_id": tid}, timeout=45)
        rec(f"GET{path}", ok=r.ok, http=r.status_code,
            ms=round((time.time() - t0) * 1000), body=r.text[:160],
            note="single token")
    except Exception as e:  # noqa: BLE001
        rec(f"GET{path}", ok=False, error=repr(e)[:200])

# ---- how big can a batch be?
for n in (50, 100, 200, 500):
    try:
        payload = [{"token_id": t} for t in
                   [x["token_id"] for x in live[:n]]]
        if len(payload) < n:
            break
        t0 = time.time()
        r = S.post(f"{CLOB}/books", json=payload, timeout=60)
        j = r.json() if r.ok else None
        rec(f"books_batch_{n}", ok=r.ok, http=r.status_code,
            ms=round((time.time() - t0) * 1000),
            returned=len(j) if isinstance(j, list) else None,
            note=f"asked {n}, got {len(j) if isinstance(j, list) else '?'}")
    except Exception as e:  # noqa: BLE001
        rec(f"books_batch_{n}", ok=False, error=repr(e)[:160])

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {OUT}")
