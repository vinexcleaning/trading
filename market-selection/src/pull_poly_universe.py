"""TASK 1 (Polymarket half) — enumerate every tradable market, grouped by family.

Built around /events, not /markets, for two reasons found by probing:
  - gamma silently CAPS limit at 100 however large a value you send. A first
    version asked for 500, got 100, and its `len(batch) < LIM` stop condition
    ended the crawl after a single page. It reported "100 markets, 1 tag" and
    looked like a successful run.
  - tags are returned on /events but NOT on the events stub inside /markets, so
    market-first crawling has no family key at all.

Writes:
  data/poly_events.jsonl       one row per open event, markets inline
  reports/poly_universe.json   per-tag aggregates

Eligibility note (LEDGER W016): `enableOrderBook` / `active` / `closed`
describe CURRENT tradability and have already produced a 0-of-2,108,796 filter
in this project. Flags are recorded, not trusted; `acceptingOrders` plus a
future endDate is the working definition of live.

Read-only, paced, public endpoints.
"""
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

import requests

GAMMA = "https://gamma-api.polymarket.com"
UA = {"User-Agent": "market-selection-research/1.0"}
PACE = 0.25
LIM = 100                       # hard cap enforced server-side; do not raise
OUT = os.path.join(os.path.dirname(__file__), "..")
DATA, REP = os.path.join(OUT, "data"), os.path.join(OUT, "reports")
NOW = datetime.now(timezone.utc).isoformat()


def get(path, params, tries=5):
    for i in range(tries):
        try:
            r = requests.get(GAMMA + path, params=params, headers=UA, timeout=60)
        except requests.RequestException:
            time.sleep(1.5 * (i + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2.5 * (i + 1))
            continue
        time.sleep(PACE)
        return r
    return None


def fnum(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def main():
    t0 = time.time()
    path = os.path.join(DATA, "poly_events.jsonl")
    n_ev = n_mk = offset = 0
    with open(path, "w", encoding="utf-8") as fh:
        while True:
            r = get("/events", {"limit": LIM, "offset": offset, "closed": "false",
                                "order": "volume24hr", "ascending": "false"})
            if r is None or r.status_code != 200:
                print("stop: http", None if r is None else r.status_code)
                break
            batch = r.json()
            if not batch:
                break
            for e in batch:
                fh.write(json.dumps(e) + "\n")
                n_mk += len(e.get("markets") or [])
            n_ev += len(batch)
            offset += LIM
            if n_ev % 1000 == 0:
                print(f"  {n_ev} events, {n_mk} markets, {time.time()-t0:.0f}s",
                      flush=True)
            if len(batch) < LIM:
                break
    print(f"open events: {n_ev}  markets inside them: {n_mk}  "
          f"({time.time()-t0:.0f}s)")

    agg = defaultdict(lambda: {"n": 0, "ev": set(), "vol24": 0.0, "liq": 0.0,
                               "oi": 0.0, "spreads": [], "ticks": set(),
                               "live": 0, "two_sided": 0, "neg_risk": 0})
    tot_live = tot_two = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            e = json.loads(line)
            tags = [t.get("label") for t in (e.get("tags") or []) if t.get("label")]
            if not tags:
                tags = ["(untagged)"]
            for m in (e.get("markets") or []):
                end = m.get("endDate") or ""
                live = bool(m.get("acceptingOrders")) and bool(end) and end > NOW
                bb, ba = fnum(m.get("bestBid"), -1), fnum(m.get("bestAsk"), -1)
                two = bb > 0 and 0 < ba < 1
                tot_live += live
                tot_two += two
                for tag in tags:
                    a = agg[tag]
                    a["n"] += 1
                    a["ev"].add(e.get("ticker"))
                    a["vol24"] += fnum(m.get("volume24hr"))
                    a["liq"] += fnum(m.get("liquidityNum"))
                    a["neg_risk"] += bool(m.get("negRisk"))
                    a["live"] += live
                    if two:
                        a["two_sided"] += 1
                        a["spreads"].append((ba - bb) * 100.0)
                    ts = m.get("orderPriceMinTickSize")
                    if ts is not None:
                        a["ticks"].add(str(ts))
                a_oi = fnum(e.get("openInterest"))
            for tag in tags:
                agg[tag]["oi"] += a_oi if (e.get("markets")) else 0.0

    rows = []
    for tag, a in agg.items():
        sp = sorted(a["spreads"])
        rows.append({
            "tag": tag, "n_markets": a["n"], "n_events": len(a["ev"]),
            "n_live": a["live"], "volume_24h": round(a["vol24"], 0),
            "liquidity": round(a["liq"], 0), "open_interest": round(a["oi"], 0),
            "pct_two_sided": round(100.0 * a["two_sided"] / a["n"], 1) if a["n"] else 0,
            "median_spread_c": round(sp[len(sp) // 2], 2) if sp else None,
            "p75_spread_c": round(sp[int(len(sp) * .75)], 2) if sp else None,
            "p90_spread_c": round(sp[int(len(sp) * .9)], 2) if sp else None,
            "tick_sizes": sorted(a["ticks"]),
            "pct_neg_risk": round(100.0 * a["neg_risk"] / a["n"], 1) if a["n"] else 0,
        })
    rows.sort(key=lambda r: -r["volume_24h"])
    with open(os.path.join(REP, "poly_universe.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)

    print(f"\nlive (acceptingOrders AND endDate future): {tot_live} of {n_mk}")
    print(f"two-sided right now:                        {tot_two} of {n_mk}")
    print(f"\n{'tag':24s} {'mkts':>6s} {'evts':>5s} {'live':>6s} {'vol24h':>11s} "
          f"{'2sid%':>6s} {'med':>5s} {'p90':>6s} ticks")
    for r in rows[:40]:
        print(f"{str(r['tag'])[:24]:24s} {r['n_markets']:6d} {r['n_events']:5d} "
              f"{r['n_live']:6d} {r['volume_24h']:11.0f} {r['pct_two_sided']:6.1f} "
              f"{str(r['median_spread_c']):>5s} {str(r['p90_spread_c']):>6s} "
              f"{','.join(r['tick_sizes'])}")
    print(f"\ntotal tags {len(rows)}  elapsed {time.time()-t0:.0f}s")


if __name__ == "__main__":
    sys.exit(main())
