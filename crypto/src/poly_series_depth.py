"""Phase 1.3: how much HISTORY exists for the short-dated crypto series?

The orderbook subgraph stops at 2026-04-28 (~3 months stale), so it cannot serve
the current 5m/15m up-down series on its own. The alternative path:
  Gamma /markets (incl. closed) by slug pattern  ->  per-market trades from
  data-api, which is current.

Establish how far back the recurring series go and how many markets exist.
"""
import json
import time
from collections import Counter, defaultdict

import requests

UA = {"User-Agent": "research-readonly/0.1"}
GAMMA = "https://gamma-api.polymarket.com"
DATA = "https://data-api.polymarket.com"


def get(url, **params):
    for attempt in range(5):
        r = requests.get(url, params=params or None, headers=UA, timeout=40)
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
    section("1. Can Gamma page through CLOSED markets by slug prefix?")
    # Gamma supports slug= exact match; test whether a LIKE/prefix works, and
    # whether paging all markets ordered by endDate is feasible.
    for params in [dict(limit=5, closed="true", slug="btc-updown-5m-1785542400"),
                   dict(limit=5, slug_contains="btc-updown-5m"),
                   dict(limit=5, closed="true", tag_slug="crypto",
                        order="endDate", ascending="false")]:
        r = get(f"{GAMMA}/markets", **params)
        n = len(r) if isinstance(r, list) else "err"
        print(f"  {json.dumps(params)[:74]:<74} -> {n}")
        if isinstance(r, list) and r:
            print(f"      first slug: {r[0].get('slug')}")

    section("2. Page the EVENTS endpoint for the recurring series")
    # events group the per-window markets; series may be exposed there
    for slug in ["btc-updown-5m", "bitcoin-up-or-down"]:
        r = get(f"{GAMMA}/events", limit=10, slug=slug)
        print(f"  events?slug={slug}: {len(r) if isinstance(r,list) else 'err'}")

    section("3. /markets paged by descending id, filtered client-side")
    # brute force: walk recent markets and count the recurring crypto families
    fams = Counter()
    earliest = {}
    offset = 0
    pages = 0
    while pages < 30:
        r = get(f"{GAMMA}/markets", limit=500, offset=offset,
                order="id", ascending="false")
        if not r:
            break
        for m in r:
            s = str(m.get("slug") or "")
            parts = s.rsplit("-", 1)
            fam = parts[0] + "-<ts>" if parts[-1].isdigit() else s
            if any(k in s for k in ("updown", "up-or-down", "bitcoin-above",
                                    "ethereum-above", "bitcoin-price-on")):
                fams[fam] += 1
                ed = m.get("endDate") or ""
                if fam not in earliest or (ed and ed < earliest[fam]):
                    earliest[fam] = ed
        offset += 500
        pages += 1
        time.sleep(0.1)
    print(f"  walked {offset} markets over {pages} pages")
    print(f"  {len(fams)} recurring crypto families found:\n")
    for fam, n in fams.most_common(30):
        print(f"    {n:>5}  {fam[:56]:<56} earliest_end={earliest.get(fam,'')[:16]}")

    section("4. Trade depth on ONE historical short-dated market")
    r = get(f"{GAMMA}/markets", limit=200, offset=0, order="id",
            ascending="false")
    cands = [m for m in (r or []) if "updown" in str(m.get("slug", ""))]
    print(f"  {len(cands)} updown markets in the most recent 200")
    for m in cands[:6]:
        cid = m.get("conditionId")
        tr = get(f"{DATA}/trades", market=cid, limit=1000)
        n = len(tr) if isinstance(tr, list) else 0
        vol = m.get("volumeNum")
        print(f"    {str(m.get('slug'))[:40]:<40} end={str(m.get('endDate'))[:16]} "
              f"trades={n:<5} vol={vol}")
        time.sleep(0.15)


if __name__ == "__main__":
    main()
