"""Phase 1.4: reach Polymarket's historical short-dated crypto markets.

Gamma's filters (tag_slug, slug_contains) are silently ignored, so filter-based
discovery is unusable. But the recurring series have DETERMINISTIC slugs:
    {asset}-updown-{5m|15m}-{unix_ts}     ts a multiple of 300 / 900
so the slug space can be generated and probed directly.

Establish: (a) does Gamma accept batched slugs, (b) how far back does the series
go, (c) how many trades per window.
"""
import json
import time

import requests

UA = {"User-Agent": "research-readonly/0.1"}
GAMMA = "https://gamma-api.polymarket.com"
DATA = "https://data-api.polymarket.com"

NOW = 1785542400  # 2026-07-31 20:00 ET, a known-good 5m boundary


def get(url, params=None):
    for attempt in range(5):
        r = requests.get(url, params=params, headers=UA, timeout=40)
        if r.status_code == 429:
            time.sleep(1.5 * (attempt + 1))
            continue
        if r.status_code >= 400:
            return None
        return r.json()
    return None


def section(t):
    print("\n" + "=" * 100)
    print(t)
    print("=" * 100)


def main():
    section("1. Does Gamma accept REPEATED slug params (batching)?")
    slugs = [f"btc-updown-5m-{NOW - 300 * i}" for i in range(5)]
    r = get(f"{GAMMA}/markets", [("slug", s) for s in slugs])
    print(f"  requested {len(slugs)} slugs -> got "
          f"{len(r) if isinstance(r, list) else 'err'}")
    if isinstance(r, list):
        for m in r:
            print(f"    {m.get('slug'):<32} closed={m.get('closed')} "
                  f"vol={m.get('volumeNum')} end={str(m.get('endDate'))[:16]}")

    section("2. How far BACK does btc-updown-5m go? (binary-ish probe)")
    # probe at increasing lookbacks
    for days in [0, 1, 2, 7, 14, 30, 60, 90, 180, 365]:
        ts = NOW - days * 86400
        ts -= ts % 300
        s = f"btc-updown-5m-{ts}"
        r = get(f"{GAMMA}/markets", [("slug", s)])
        hit = isinstance(r, list) and len(r) > 0
        info = ""
        if hit:
            m = r[0]
            info = (f"closed={m.get('closed')} vol={m.get('volumeNum')} "
                    f"end={str(m.get('endDate'))[:16]}")
        print(f"  -{days:>4}d  {s:<28} {'HIT ' if hit else 'miss'} {info}")
        time.sleep(0.15)

    section("3. Same for 15m and the older hourly 'up-or-down' family")
    for fam, step in [("btc-updown-15m", 900), ("eth-updown-5m", 300),
                      ("sol-updown-5m", 300), ("btc-updown-4h", 14400)]:
        for days in [1, 30, 90]:
            ts = NOW - days * 86400
            ts -= ts % step
            s = f"{fam}-{ts}"
            r = get(f"{GAMMA}/markets", [("slug", s)])
            hit = isinstance(r, list) and len(r) > 0
            v = r[0].get("volumeNum") if hit else ""
            print(f"  {fam:<18} -{days:>3}d  {'HIT' if hit else 'miss'}  vol={v}")
            time.sleep(0.15)

    section("4. Trades + book-ish data on a SETTLED short-dated market")
    ts = NOW - 3600  # an hour ago, definitely settled
    ts -= ts % 300
    s = f"btc-updown-5m-{ts}"
    r = get(f"{GAMMA}/markets", [("slug", s)])
    if not r:
        print(f"  {s}: no market")
        return
    m = r[0]
    print(f"  slug={s}")
    for k in ("conditionId", "closed", "volumeNum", "liquidityNum", "spread",
              "bestBid", "bestAsk", "lastTradePrice", "outcomePrices",
              "startDate", "endDate", "umaResolutionStatus",
              "orderPriceMinTickSize", "clobTokenIds"):
        print(f"    {k:<24} {str(m.get(k))[:110]}")

    cid = m.get("conditionId")
    tr = get(f"{DATA}/trades", {"market": cid, "limit": 1000})
    print(f"\n  trades: {len(tr) if isinstance(tr, list) else 'err'}")
    if isinstance(tr, list) and tr:
        tr = sorted(tr, key=lambda x: x["timestamp"])
        print(f"    first={tr[0]['timestamp']} last={tr[-1]['timestamp']} "
              f"span={tr[-1]['timestamp']-tr[0]['timestamp']}s")
        print("    sample:")
        for t in tr[:8]:
            print(f"      ts={t['timestamp']} {t['side']:<4} "
                  f"{t['outcome']:<5} p={t['price']:<7} sz={t['size']:<10} "
                  f"{t['proxyWallet'][:12]}")

    toks = json.loads(m.get("clobTokenIds") or "[]")
    if toks:
        h = get("https://clob.polymarket.com/prices-history",
                {"market": toks[0], "interval": "max", "fidelity": 1})
        pts = (h or {}).get("history", [])
        print(f"\n  prices-history points for settled market: {len(pts)}")
        if pts:
            print(f"    first={pts[0]}  last={pts[-1]}")


if __name__ == "__main__":
    main()
