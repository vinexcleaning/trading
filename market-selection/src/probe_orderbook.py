"""Resolve the LEDGER contradiction: does Kalshi's /orderbook return depth
unauthenticated, or empty?

One prior session concluded depth is not public. Another recorded 64,898
snapshots at 20 levels a side (S013). Both are in LEDGER.md. This settles it by
fetching, not by reading docs.

Read-only. Public unauthenticated endpoints only. Paced.
"""
import json
import sys
import time
from collections import Counter

import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "market-selection-research/1.0"}
PACE = 0.30


def get(path, params=None, tries=4):
    url = BASE + path
    for i in range(tries):
        r = requests.get(url, params=params, headers=UA, timeout=30)
        if r.status_code == 429:
            time.sleep(2.0 * (i + 1))
            continue
        time.sleep(PACE)
        return r
    return r


def main():
    out = {}

    # 1. Grab a spread of active markets across series, sorted by volume.
    r = get("/markets", {"limit": 1000, "status": "open"})
    print("GET /markets status", r.status_code)
    mkts = r.json().get("markets", [])
    print("open markets in first page:", len(mkts))

    # keep the busiest and a random-ish tail so we test both liquid and dead
    def vol(m):
        return m.get("volume") or m.get("volume_fp") or 0

    mkts_sorted = sorted(mkts, key=vol, reverse=True)
    sample = mkts_sorted[:15] + mkts_sorted[len(mkts_sorted) // 2:len(mkts_sorted) // 2 + 5] + mkts_sorted[-5:]

    print("\n=== field-name audit on /markets (the None-field bug) ===")
    keys = Counter()
    for m in mkts[:200]:
        for k, v in m.items():
            if v is not None:
                keys[k] += 1
    legacy = ["yes_bid", "yes_ask", "no_bid", "no_ask", "last_price", "volume",
              "open_interest", "liquidity"]
    newstyle = [k for k in keys if k.endswith("_dollars") or k.endswith("_fp")]
    print("legacy fields non-null count (of 200):",
          {k: keys.get(k, 0) for k in legacy})
    print("new-style fields present:", sorted(newstyle)[:20])
    out["legacy_nonnull_of_200"] = {k: keys.get(k, 0) for k in legacy}
    out["newstyle_fields"] = sorted(newstyle)

    print("\n=== /markets/{ticker}/orderbook ===")
    results = []
    for m in sample:
        t = m["ticker"]
        r = get(f"/markets/{t}/orderbook", {"depth": 100})
        rec = {"ticker": t, "series": m.get("event_ticker", ""), "volume": vol(m),
               "http": r.status_code}
        if r.status_code == 200:
            # ⚠ FIXED 2026-08-08 (mailbox 004). One top-level key exists,
            # `orderbook_fp`, holding `yes_dollars`/`no_dollars`. Reading
            # `orderbook` returned an empty dict from an HTTP 200 on every
            # market. Anything this script concluded about depth or liquidity
            # before today is void until re-run -- see LEDGER M001.
            ob = (r.json() or {}).get("orderbook_fp") or {}
            yes = ob.get("yes_dollars")
            no = ob.get("no_dollars")
            rec["yes_levels"] = len(yes) if yes else 0
            rec["no_levels"] = len(no) if no else 0
            rec["yes_sample"] = yes[:3] if yes else None
            rec["no_sample"] = no[:3] if no else None
            rec["keys"] = sorted(ob.keys())
        else:
            rec["body"] = r.text[:200]
        results.append(rec)
        print(f"  {t[:44]:44s} vol={rec['volume']:>8} http={rec['http']} "
              f"yes={rec.get('yes_levels')} no={rec.get('no_levels')}")
    out["orderbook_probe"] = results

    nonempty = [x for x in results if (x.get("yes_levels") or 0) + (x.get("no_levels") or 0) > 0]
    print(f"\nnon-empty orderbooks: {len(nonempty)}/{len(results)}")
    if nonempty:
        print("example:", json.dumps(nonempty[0], indent=2)[:800])

    print("\n=== /markets/trades (public tape) ===")
    r = get("/markets/trades", {"limit": 100})
    print("http", r.status_code)
    if r.status_code == 200:
        tr = r.json().get("trades", [])
        print("trades returned:", len(tr))
        if tr:
            print("keys:", sorted(tr[0].keys()))
            print("sample:", json.dumps(tr[0]))
        out["trades_keys"] = sorted(tr[0].keys()) if tr else []
        out["trades_n"] = len(tr)
    else:
        print(r.text[:300])

    print("\n=== /series/{s} fee_type ===")
    seen = set()
    for m in mkts[:400]:
        s = m["ticker"].split("-")[0]
        if s in seen:
            continue
        seen.add(s)
        if len(seen) > 8:
            break
        r = get(f"/series/{s}")
        if r.status_code == 200:
            d = r.json().get("series", {})
            print(f"  {s:12s} fee_type={d.get('fee_type')!r} "
                  f"fee_multiplier={d.get('fee_multiplier')!r} "
                  f"category={d.get('category')!r} freq={d.get('frequency')!r}")
        else:
            print(f"  {s:12s} http={r.status_code}")

    with open("market-selection/reports/probe_orderbook.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    print("\nwrote market-selection/reports/probe_orderbook.json")


if __name__ == "__main__":
    sys.exit(main())
