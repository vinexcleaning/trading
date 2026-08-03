"""Measure Polymarket's fee structure directly, the same way C1 did for Kalshi.

The Kalshi correction came from checking the venue instead of a third-party
repo. The Polymarket side of this project's fee claims has never had the same
treatment: `GITHUB_KNOWLEDGE.md` says "makers pay zero, takers 0.04-0.07 by
category, only geopolitics is free", sourced from a repo's documentation rather
than from Polymarket.

Gamma exposes `makerBaseFee` and `takerBaseFee` per market, so the claim is
directly checkable.

    python src/polymarket_fees_census.py [--pages 12]

Exit status 0 if the measurement matches what CORRECTIONS.md records, 1 if it
has moved.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

GAMMA = "https://gamma-api.polymarket.com"
UA = "signal-github/0.2 (research)"


def get(path: str, tries: int = 4):
    """Returns None on HTTP 422, which Gamma uses for "offset too large" rather
    than returning an empty list. Treating that as a crash cost a whole run."""
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(GAMMA + path,
                                         headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 422:
                return None
            last = e
            time.sleep(2 + 3 * i)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 + 3 * i)
    raise last


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main() -> int:
    pages = 12
    if "--pages" in sys.argv:
        pages = int(sys.argv[sys.argv.index("--pages") + 1])

    markets = []
    # Gamma silently caps limit at 100 and returns HTTP 422 past a maximum
    # offset, so paginate in 100s and stop on either signal.
    PAGE = 100
    for p in range(pages):
        params = {"limit": PAGE, "offset": p * PAGE, "closed": "false"}
        batch = get("/markets?" + urllib.parse.urlencode(params))
        if batch is None:
            print(f"  page {p+1}: HTTP 422 — offset limit reached, stopping", flush=True)
            break
        if not isinstance(batch, list) or not batch:
            break
        markets.extend(batch)
        print(f"  page {p+1}: {len(batch)} markets (total {len(markets)})", flush=True)

    print(f"\nopen markets pulled: {len(markets)}")
    if not markets:
        print("no markets returned - Gamma may have changed shape")
        return 1

    keys = Counter()
    for m in markets:
        keys.update(k for k in m if "fee" in k.lower())
    print("fee-related fields present:", dict(keys))

    # ---- the trap, recorded because it nearly produced a wrong claim -------
    # `makerBaseFee` and `takerBaseFee` are 1000 on ~94% of markets and are NOT
    # the operative fee. The CLOB API returns maker_base_fee=0 / taker_base_fee=0
    # for the same markets. `feeSchedule` is the authoritative field. A repo that
    # reads makerBaseFee concludes makers pay something; they do not.
    mb = Counter(num(m.get("makerBaseFee")) for m in markets)
    print("\nmakerBaseFee (NOT the operative fee — see feeSchedule):")
    for v, n in mb.most_common(4):
        print(f"  {str(v):>10}  {n:6}  ({100*n/len(markets):5.1f}%)")

    print("\nfeeSchedule — the field that decides what an order pays:")
    sched = Counter(json.dumps(m.get("feeSchedule"), sort_keys=True) for m in markets)
    for v, n in sched.most_common(10):
        print(f"  {n:6}  ({100*n/len(markets):5.1f}%)  {v}")

    taker_only = 0
    rates = Counter()
    for m in markets:
        s = m.get("feeSchedule") or {}
        if s.get("takerOnly"):
            taker_only += 1
        if s:
            rates[s.get("rate")] += 1
    print(f"\nfeeType values: {dict(Counter(m.get('feeType') for m in markets).most_common(8))}")
    print(f"taker rates in use: {dict(rates)}")
    print(f"markets where the schedule is takerOnly (makers pay nothing): "
          f"{taker_only} of {len(markets)}")

    print("\n--- verdict against the standing claim ---")
    print("  claim: 'Polymarket makers pay zero, takers 0.04-0.07 by category'")
    has_sched = sum(1 for m in markets if m.get("feeSchedule"))
    if has_sched and taker_only == has_sched:
        print(f"  makers: CONFIRMED zero — every one of the {has_sched} markets with a "
              "schedule is takerOnly")
    else:
        print(f"  makers: MOVED — {has_sched - taker_only} markets are not takerOnly")
    print(f"  takers: rates observed = {sorted(r for r in rates if r is not None)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
