"""Phase 0.4: Polymarket crypto universe + fees on LIVE crypto markets.

Two corrections to the first probe:
  - Gamma's tag_slug filter is silently IGNORED (all tags returned identical
    rows). Discover markets by slug pattern and via the trade stream instead.
  - The first fee sample was 1000 mostly-CLOSED 2023 sports markets. The fee
    question must be answered on live, order-book-enabled CRYPTO markets.

Read-only, unauthenticated. No wallet.
"""
import json
import time
from collections import Counter, defaultdict

import requests

UA = {"User-Agent": "research-readonly/0.1"}
CLOB = "https://clob.polymarket.com"
GAMMA = "https://gamma-api.polymarket.com"
DATA = "https://data-api.polymarket.com"


def get(url, **params):
    for attempt in range(5):
        r = requests.get(url, params=params or None, headers=UA, timeout=30)
        if r.status_code == 429:
            time.sleep(1.0 * (attempt + 1))
            continue
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"rate limited: {url}")


def section(t):
    print("\n" + "=" * 100)
    print(t)
    print("=" * 100)


def main():
    # ------------------------------------------------------------------
    section("A. Discover recurring short-dated crypto series from the LIVE "
            "trade stream")
    # Walk the public trade stream and bucket by slug prefix.
    seen = {}
    slug_families = Counter()
    offset = 0
    for _ in range(12):
        tr = get(f"{DATA}/trades", limit=500, offset=offset)
        if not tr:
            break
        for t in tr:
            slug = t.get("slug") or ""
            # normalise a trailing unix stamp / date into <ts>
            parts = slug.rsplit("-", 1)
            fam = parts[0] + "-<ts>" if parts[-1].isdigit() else slug
            slug_families[fam] += 1
            seen.setdefault(slug, t)
        offset += 500
        time.sleep(0.15)
    print(f"scanned {sum(slug_families.values())} recent trades, "
          f"{len(seen)} distinct market slugs\n")
    print("  top slug families by recent trade count:")
    for fam, n in slug_families.most_common(30):
        print(f"    {n:>6}  {fam[:78]}")

    # ------------------------------------------------------------------
    section("B. FEES + TICK on LIVE, order-book-enabled CRYPTO markets")
    crypto_kw = ("btc", "bitcoin", "eth", "ethereum", "sol", "solana", "xrp",
                 "doge", "crypto")
    cand_slugs = [s for s in seen
                  if any(k in s.lower() for k in crypto_kw)]
    print(f"{len(cand_slugs)} crypto-looking slugs seen trading recently")

    rows = []
    for s in cand_slugs[:60]:
        g = get(f"{GAMMA}/markets", slug=s)
        if not g:
            continue
        gm = g[0] if isinstance(g, list) and g else None
        if not gm:
            continue
        cid = gm.get("conditionId")
        cm = get(f"{CLOB}/markets/{cid}") if cid else None
        if not cm:
            continue
        rows.append({
            "slug": s,
            "active": cm.get("active"),
            "closed": cm.get("closed"),
            "accepting_orders": cm.get("accepting_orders"),
            "enable_order_book": cm.get("enable_order_book"),
            "maker_base_fee": cm.get("maker_base_fee"),
            "taker_base_fee": cm.get("taker_base_fee"),
            "minimum_tick_size": cm.get("minimum_tick_size"),
            "minimum_order_size": cm.get("minimum_order_size"),
            "neg_risk": cm.get("neg_risk"),
            "rewards": cm.get("rewards"),
            "seconds_delay": cm.get("seconds_delay"),
            "end_date_iso": cm.get("end_date_iso"),
        })
        time.sleep(0.12)

    print(f"\nresolved {len(rows)} live crypto CLOB markets\n")
    for k in ("maker_base_fee", "taker_base_fee", "minimum_tick_size",
              "minimum_order_size", "neg_risk", "accepting_orders",
              "enable_order_book", "seconds_delay"):
        c = Counter(str(r.get(k)) for r in rows)
        print(f"  {k:<22} {dict(c.most_common(8))}")

    print("\n  --- per-market detail (first 25) ---")
    for r in rows[:25]:
        print(f"    {r['slug'][:46]:<46} maker={str(r['maker_base_fee']):>4} "
              f"taker={str(r['taker_base_fee']):>4} "
              f"tick={str(r['minimum_tick_size']):>6} "
              f"minsz={str(r['minimum_order_size']):>6} "
              f"ob={str(r['enable_order_book']):<5} "
              f"acc={str(r['accepting_orders']):<5} "
              f"rew={json.dumps(r['rewards'])[:44]}")

    # ------------------------------------------------------------------
    section("C. LIVE ORDER BOOK on one short-dated crypto market")
    live = [r for r in rows if r["accepting_orders"]]
    print(f"{len(live)} markets currently accepting orders")
    if live:
        s = live[0]["slug"]
        g = get(f"{GAMMA}/markets", slug=s)[0]
        toks = json.loads(g.get("clobTokenIds") or "[]")
        print(f"  market: {s}")
        print(f"  outcomes: {g.get('outcomes')}  tokens: {len(toks)}")
        for tid in toks[:2]:
            bk = get(f"{CLOB}/book", token_id=tid)
            if not bk:
                continue
            bids = bk.get("bids") or []
            asks = bk.get("asks") or []
            print(f"\n    token {str(tid)[:22]}...  "
                  f"{len(bids)} bid levels, {len(asks)} ask levels")
            print(f"      top asks: "
                  f"{[(a['price'], a['size']) for a in asks[-5:]]}")
            print(f"      top bids: "
                  f"{[(b['price'], b['size']) for b in bids[-5:]]}")

    with open(r"C:\Users\gianf\crypto\docs\polymarket_crypto.json", "w") as f:
        json.dump({"slug_families": slug_families.most_common(60),
                   "live_crypto_markets": rows}, f, indent=2, default=str)


if __name__ == "__main__":
    main()
