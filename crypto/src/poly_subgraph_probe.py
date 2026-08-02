"""Phase 1.2: how deep does the on-chain fill history go, and what is in it?

The orderbook subgraph has NO `orders` entity — only fills. So books are not
reconstructible; the tape is. Establish:
  - earliest indexed fill (how many years of history)
  - the `fee` field: does it let us verify the fee schedule empirically?
  - maker/taker addresses: counterparty fingerprinting + adverse selection
  - how to map assetId -> market
"""
import json
import time

import requests

UA = {"User-Agent": "research-readonly/0.1"}
GOLDSKY = ("https://api.goldsky.com/api/public/"
           "project_cl6mb8i9h0003e201j6li0diw/subgraphs/"
           "orderbook-subgraph/prod/gn")


def gql(query):
    for attempt in range(4):
        r = requests.post(GOLDSKY, json={"query": query}, headers=UA,
                          timeout=60)
        if r.status_code == 429:
            time.sleep(2 * (attempt + 1))
            continue
        j = r.json()
        if "errors" in j:
            return j
        return j
    return {"errors": "rate limited"}


def section(t):
    print("\n" + "=" * 100)
    print(t)
    print("=" * 100)


FILL_FIELDS = ("id timestamp maker taker makerAssetId takerAssetId "
               "makerAmountFilled takerAmountFilled fee orderHash "
               "transactionHash")


def main():
    section("1. FULL schema of orderFilledEvent")
    j = gql('{ __type(name:"OrderFilledEvent"){ fields{ name type{name kind '
            'ofType{name}} } } }')
    if "data" in j and j["data"].get("__type"):
        for f in j["data"]["__type"]["fields"]:
            t = f["type"]
            tn = t.get("name") or (t.get("ofType") or {}).get("name")
            print(f"    {f['name']:<24} {tn}")

    section("2. EARLIEST indexed fill")
    j = gql("{ orderFilledEvents(first:3, orderBy:timestamp, "
            "orderDirection:asc){ " + FILL_FIELDS + " } }")
    rows = j.get("data", {}).get("orderFilledEvents", [])
    for r in rows:
        ts = int(r["timestamp"])
        print(f"    ts={ts}  {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(ts))}"
              f"  fee={r['fee']}")

    section("3. LATEST indexed fill")
    j = gql("{ orderFilledEvents(first:3, orderBy:timestamp, "
            "orderDirection:desc){ " + FILL_FIELDS + " } }")
    rows = j.get("data", {}).get("orderFilledEvents", [])
    for r in rows:
        ts = int(r["timestamp"])
        print(f"    ts={ts}  {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(ts))}"
              f"  fee={r['fee']}")
    print("\n    --- full record ---")
    if rows:
        for k, v in rows[0].items():
            print(f"      {k:<20} {str(v)[:90]}")

    section("4. Is the `fee` field ever non-zero? (empirical fee verification)")
    j = gql("{ orderFilledEvents(first:200, orderBy:timestamp, "
            "orderDirection:desc){ fee makerAmountFilled takerAmountFilled "
            "makerAssetId takerAssetId timestamp } }")
    rows = j.get("data", {}).get("orderFilledEvents", [])
    nz = [r for r in rows if r["fee"] not in ("0", 0, None)]
    print(f"    {len(rows)} recent fills, {len(nz)} with non-zero fee")
    for r in nz[:10]:
        print(f"      fee={r['fee']:<14} makerAmt={r['makerAmountFilled']:<18} "
              f"takerAmt={r['takerAmountFilled']:<18}")

    section("5. ordersMatchedEvent schema (the taker side aggregate)")
    j = gql('{ __type(name:"OrdersMatchedEvent"){ fields{ name } } }')
    if "data" in j and j["data"].get("__type"):
        print("    " + ", ".join(f["name"]
                                 for f in j["data"]["__type"]["fields"]))

    section("6. marketData / orderbook entities — what do they hold?")
    for tn in ("MarketData", "Orderbook"):
        j = gql('{ __type(name:"%s"){ fields{ name } } }' % tn)
        if "data" in j and j["data"].get("__type"):
            print(f"    {tn}: " + ", ".join(
                f["name"] for f in j["data"]["__type"]["fields"]))

    j = gql("{ orderbooks(first:2){ id tradesQuantity buysQuantity "
            "sellsQuantity collateralVolume scaledCollateralVolume } }")
    print(f"\n    orderbooks sample: {json.dumps(j)[:400]}")

    section("7. Can we filter fills by assetId? (per-market pulls)")
    j = gql("{ orderFilledEvents(first:1, orderBy:timestamp, "
            "orderDirection:desc){ makerAssetId takerAssetId } }")
    r = j.get("data", {}).get("orderFilledEvents", [{}])[0]
    aid = r.get("takerAssetId") if r.get("takerAssetId") != "0" \
        else r.get("makerAssetId")
    print(f"    probing assetId={str(aid)[:40]}...")
    j = gql('{ orderFilledEvents(first:5, where:{makerAssetId:"%s"}, '
            'orderBy:timestamp, orderDirection:desc){ timestamp fee '
            'makerAmountFilled takerAmountFilled } }' % aid)
    print(f"    by makerAssetId: {json.dumps(j)[:300]}")
    j = gql('{ orderFilledEvents(first:5, where:{takerAssetId:"%s"}, '
            'orderBy:timestamp, orderDirection:desc){ timestamp fee '
            'makerAmountFilled takerAmountFilled } }' % aid)
    print(f"    by takerAssetId: {json.dumps(j)[:300]}")


if __name__ == "__main__":
    main()
