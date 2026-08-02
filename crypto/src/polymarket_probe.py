"""Phase 0.3: THE decisive Phase 0 question for Polymarket — the fee structure.

If fees are genuinely zero/near-zero the cost bar is spread-only, roughly 3x lower
than Kalshi, and every prior Kalshi negative result must be re-evaluated.

Also enumerates crypto markets, tick size, min order size, oracle/resolution.
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
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"rate limited: {url}")


def section(t):
    print("\n" + "=" * 96)
    print(t)
    print("=" * 96)


def main():
    # ---------------------------------------------------------------- fees
    section("1. FEE STRUCTURE — raw fee fields on live CLOB markets")
    j = get(f"{CLOB}/markets")
    mkts = j.get("data", [])
    print(f"/markets returned {len(mkts)} (next_cursor={j.get('next_cursor')})")
    if mkts:
        print("\n--- full field dump of one CLOB market ---")
        for k in sorted(mkts[0].keys()):
            v = mkts[0][k]
            if isinstance(v, (dict, list)):
                v = json.dumps(v)[:200]
            print(f"  {k:<28} {str(v)[:200]}")

    fee_fields = [k for k in (mkts[0].keys() if mkts else [])
                  if "fee" in k.lower()]
    print(f"\nfee-bearing fields: {fee_fields}")
    ctr = defaultdict(Counter)
    for m in mkts:
        for k in fee_fields:
            ctr[k][str(m.get(k))] += 1
    for k, c in ctr.items():
        print(f"  {k}: {dict(c.most_common(8))}")

    # ---------------------------------------------------- tick / min size
    section("2. TICK SIZE + MIN ORDER SIZE distribution across CLOB markets")
    for k in ("minimum_tick_size", "minimum_order_size", "maker_base_fee",
              "taker_base_fee", "neg_risk", "accepting_orders"):
        c = Counter(str(m.get(k)) for m in mkts)
        print(f"  {k:<22} {dict(c.most_common(8))}")

    # ------------------------------------------------------ crypto markets
    section("3. CRYPTO MARKETS on Gamma (open)")
    found = {}
    for tag in ["crypto", "bitcoin", "ethereum", "solana", "xrp"]:
        try:
            rows = get(f"{GAMMA}/markets", limit=200, closed="false",
                       order="volumeNum", ascending="false", tag_slug=tag)
        except Exception as e:
            print(f"  tag={tag}: {type(e).__name__} {e}")
            continue
        print(f"\n  tag_slug={tag}: {len(rows)} markets")
        for m in rows[:12]:
            found[m.get("id")] = m
            print(f"    {str(m.get('slug'))[:64]:<64} "
                  f"end={str(m.get('endDate'))[:16]:<16} "
                  f"vol={str(m.get('volumeNum'))[:12]:>12} "
                  f"spread={str(m.get('spread')):>7} "
                  f"tick={str(m.get('orderPriceMinTickSize')):>7}")
        time.sleep(0.2)

    # look specifically for recurring short-dated crypto series
    section("4. SHORT-DATED / RECURRING crypto series on Gamma")
    for q in ["bitcoin-up-or-down", "ethereum-up-or-down", "bitcoin-price-on",
              "what-price-will-bitcoin"]:
        try:
            rows = get(f"{GAMMA}/markets", limit=40, closed="false", slug=q)
            print(f"  slug={q}: {len(rows)}")
        except Exception as e:
            print(f"  slug={q}: {type(e).__name__}")
    try:
        evs = get(f"{GAMMA}/events", limit=200, closed="false",
                  order="volume24hr", ascending="false", tag_slug="crypto")
        print(f"\n  crypto EVENTS (open, by 24h volume): {len(evs)}")
        for e in evs[:25]:
            print(f"    {str(e.get('slug'))[:62]:<62} "
                  f"n_mkts={len(e.get('markets') or []):>3} "
                  f"end={str(e.get('endDate'))[:16]:<16} "
                  f"vol24={str(e.get('volume24hr'))[:10]:>10}")
    except Exception as e:
        print(f"  events: {type(e).__name__} {e}")

    section("5. HISTORICAL TRADE ACCESS (data-api)")
    tr = get(f"{DATA}/trades", limit=5)
    print(f"  /trades returned {len(tr)}")
    if tr:
        print("  --- one trade record ---")
        for k, v in sorted(tr[0].items()):
            print(f"    {k:<20} {str(v)[:120]}")

    with open(r"C:\Users\gianf\crypto\docs\polymarket_probe.json", "w") as f:
        json.dump({"clob_markets_sample": mkts[:5],
                   "fee_fields": fee_fields}, f, indent=2, default=str)


if __name__ == "__main__":
    main()
