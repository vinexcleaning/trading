"""Phase 1.1: establish exactly WHAT Polymarket history is retrievable.

The prompt assumes "Polymarket's fill history is permanently public, so you can
backtest against real historical order books immediately". Fills and books are
different things. Polymarket matches orders OFF-chain in a centralised CLOB and
settles only FILLS on-chain, so resting-order lifecycle (place/cancel) may not be
public at all. Determine this before building anything on top of it.

Read-only, unauthenticated.
"""
import json
import time

import requests

UA = {"User-Agent": "research-readonly/0.1"}
CLOB = "https://clob.polymarket.com"
GAMMA = "https://gamma-api.polymarket.com"
DATA = "https://data-api.polymarket.com"
GOLDSKY = ("https://api.goldsky.com/api/public/"
           "project_cl6mb8i9h0003e201j6li0diw/subgraphs/"
           "orderbook-subgraph/prod/gn")


def get(url, **params):
    r = requests.get(url, params=params or None, headers=UA, timeout=30)
    return r


def gql(query, url=GOLDSKY):
    r = requests.post(url, json={"query": query}, headers=UA, timeout=40)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, r.text[:300]


def section(t):
    print("\n" + "=" * 100)
    print(t)
    print("=" * 100)


def main():
    # a recently-traded short-dated crypto market
    section("0. pick a live btc-updown-5m market")
    tr = get(f"{DATA}/trades", limit=500).json()
    cand = [t for t in tr if str(t.get("slug", "")).startswith("btc-updown-5m")]
    if not cand:
        cand = [t for t in tr if "updown" in str(t.get("slug", ""))]
    t0 = cand[0]
    slug = t0["slug"]
    print(f"  slug={slug}  title={t0.get('title')}")
    g = get(f"{GAMMA}/markets", slug=slug).json()[0]
    cid = g.get("conditionId")
    toks = json.loads(g.get("clobTokenIds") or "[]")
    print(f"  conditionId={cid}")
    print(f"  outcomes={g.get('outcomes')}  tokens={toks}")
    tid = toks[0]

    # ---------------------------------------------------------------- book
    section("1. LIVE book — /book")
    r = get(f"{CLOB}/book", token_id=tid)
    print(f"  status={r.status_code}")
    if r.status_code == 200:
        b = r.json()
        print(f"  keys={list(b.keys())}")
        print(f"  bids={len(b.get('bids') or [])} asks={len(b.get('asks') or [])}")
        print(f"  sample asks={(b.get('asks') or [])[-4:]}")
        print(f"  sample bids={(b.get('bids') or [])[-4:]}")
        print(f"  timestamp field: {b.get('timestamp')}  hash={b.get('hash')}")
    else:
        print(f"  body={r.text[:300]}")

    # -------------------------------------------------- historical prices
    section("2. HISTORICAL price series — /prices-history")
    for interval, fid in [("1m", 1), ("1h", 1), ("max", 1)]:
        r = get(f"{CLOB}/prices-history", market=tid, interval=interval,
                fidelity=fid)
        print(f"  interval={interval:<4} status={r.status_code} "
              f"len={len(r.text)}")
        if r.status_code == 200:
            h = r.json().get("history", [])
            print(f"    {len(h)} points; first={h[:2]}  last={h[-2:]}")
        else:
            print(f"    {r.text[:200]}")
        time.sleep(0.2)

    # ------------------------------------------------------------- trades
    section("3. TRADE TAPE — data-api /trades, pagination depth")
    r = get(f"{DATA}/trades", market=cid, limit=1000)
    print(f"  by conditionId: status={r.status_code} n={len(r.json()) if r.status_code==200 else '-'}")
    if r.status_code == 200 and r.json():
        rows = r.json()
        print(f"  fields: {sorted(rows[0].keys())}")
        print("  --- do trades carry a maker/taker flag? ---")
        for k in ("side", "outcome", "outcomeIndex", "size", "price",
                  "timestamp", "transactionHash", "proxyWallet"):
            print(f"    {k:<18} {rows[0].get(k)}")
    # how far back can we page?
    deep = get(f"{DATA}/trades", limit=1000, offset=50000)
    print(f"\n  offset=50000: status={deep.status_code} "
          f"n={len(deep.json()) if deep.status_code==200 else '-'}")

    # ------------------------------------------------------------ on-chain
    section("4. ON-CHAIN order lifecycle — Goldsky orderbook subgraph")
    st, j = gql("{ _meta { block { number timestamp } } }")
    print(f"  meta: {st} {json.dumps(j)[:200]}")

    # introspect what entities exist — this tells us if RESTING ORDERS are
    # indexed or only FILLS
    st, j = gql("{ __schema { queryType { fields { name } } } }")
    if st == 200 and "data" in j:
        names = [f["name"] for f in j["data"]["__schema"]["queryType"]["fields"]]
        print(f"\n  {len(names)} query entities:")
        for n in names:
            print(f"    {n}")
    else:
        print(f"  introspection: {st} {str(j)[:300]}")

    section("5. Does the subgraph expose ORDER PLACEMENT/CANCELLATION?")
    for probe in ["orderFilledEvents(first:2){id timestamp maker taker "
                  "makerAssetId takerAssetId makerAmountFilled "
                  "takerAmountFilled fee orderHash}",
                  "orders(first:2){id}",
                  "orderbooks(first:2){id}"]:
        st, j = gql("{ " + probe + " }")
        ok = st == 200 and "errors" not in j
        print(f"\n  {probe[:46]:<46} -> {'OK' if ok else 'NO'}")
        print(f"    {json.dumps(j)[:400]}")
        time.sleep(0.2)


if __name__ == "__main__":
    main()
