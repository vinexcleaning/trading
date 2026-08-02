"""Phase 1.5: do SETTLED short-dated markets stay visible, and how far back can
the public trade tape be paged?

This decides whether a Polymarket short-dated dataset is buildable at all on this
machine, and how large it can be.
"""
import json
import time
from collections import Counter

import requests

UA = {"User-Agent": "research-readonly/0.1"}
GAMMA = "https://gamma-api.polymarket.com"
DATA = "https://data-api.polymarket.com"
CLOB = "https://clob.polymarket.com"


def get(url, params=None):
    for attempt in range(5):
        r = requests.get(url, params=params, headers=UA, timeout=40)
        if r.status_code == 429:
            time.sleep(1.5 * (attempt + 1))
            continue
        if r.status_code >= 400:
            return None, r.status_code
        return r.json(), r.status_code
    return None, 0


def section(t):
    print("\n" + "=" * 100)
    print(t)
    print("=" * 100)


def main():
    section("1. Harvest slugs that DEFINITELY traded, from the tape")
    tape, _ = get(f"{DATA}/trades", {"limit": 500})
    seen = {}
    for t in tape or []:
        s = t.get("slug") or ""
        if "updown" in s:
            seen.setdefault(s, t)
    print(f"  {len(seen)} updown slugs in the last 500 trades")
    known = sorted(seen)[:6]
    for s in known:
        print(f"    {s}   ts={seen[s]['timestamp']}")

    section("2. Are those slugs resolvable on Gamma? (with/without filters)")
    for s in known[:4]:
        for extra in [{}, {"closed": "true"}, {"archived": "true"},
                      {"active": "false"}]:
            p = {"slug": s}
            p.update(extra)
            r, code = get(f"{GAMMA}/markets", p)
            n = len(r) if isinstance(r, list) else f"err{code}"
            print(f"    {s:<30} {json.dumps(extra):<22} -> {n}")
        time.sleep(0.1)

    section("3. Does the CLOB /markets/{condition_id} still resolve them?")
    for s in known[:4]:
        cid = seen[s].get("conditionId")
        r, code = get(f"{CLOB}/markets/{cid}")
        if isinstance(r, dict):
            print(f"    {s:<30} closed={r.get('closed')} "
                  f"accepting={r.get('accepting_orders')} "
                  f"tick={r.get('minimum_tick_size')} "
                  f"taker_fee={r.get('taker_base_fee')}")
        else:
            print(f"    {s:<30} err{code}")
        time.sleep(0.1)

    section("4. How far BACK can data-api /trades be paged?")
    # walk offsets and record the oldest timestamp reached
    for off in [0, 1000, 5000, 10000, 20000, 30000, 40000, 45000, 49000,
                49500, 50000]:
        r, code = get(f"{DATA}/trades", {"limit": 500, "offset": off})
        if not isinstance(r, list) or not r:
            print(f"    offset={off:<6} -> {code} / empty")
            continue
        ts = [int(x["timestamp"]) for x in r]
        oldest = min(ts)
        age_h = (1785542400 - oldest) / 3600.0
        print(f"    offset={off:<6} n={len(r):<4} oldest={oldest} "
              f"({time.strftime('%Y-%m-%d %H:%M', time.gmtime(oldest))}) "
              f"age={age_h:6.1f}h")
        time.sleep(0.2)

    section("5. Per-market trade pull for a SETTLED window (by conditionId)")
    # pick the oldest updown slug we saw and pull its whole tape
    s = known[0]
    cid = seen[s]["conditionId"]
    r, code = get(f"{DATA}/trades", {"market": cid, "limit": 1000})
    print(f"  {s}  conditionId={cid[:20]}...")
    print(f"  trades returned: {len(r) if isinstance(r,list) else code}")
    if isinstance(r, list) and r:
        rr = sorted(r, key=lambda x: int(x["timestamp"]))
        span = int(rr[-1]["timestamp"]) - int(rr[0]["timestamp"])
        sides = Counter(x["side"] for x in rr)
        outs = Counter(x["outcome"] for x in rr)
        szs = sorted(float(x["size"]) for x in rr)
        print(f"    span={span}s  sides={dict(sides)}  outcomes={dict(outs)}")
        print(f"    size: min={szs[0]} med={szs[len(szs)//2]} max={szs[-1]}")
        print(f"    distinct wallets: "
              f"{len({x['proxyWallet'] for x in rr})}")
        print(f"    price range: {min(float(x['price']) for x in rr)} .. "
              f"{max(float(x['price']) for x in rr)}")


if __name__ == "__main__":
    main()
