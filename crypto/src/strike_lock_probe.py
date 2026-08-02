"""TASK A (part 1) — is the strike set BEFORE the window opens, or at open?

Instant probe. If markets in `unopened` status already carry a floor_strike,
the strike is locked ahead of time and the "TBD" seen in Phase 0 applies only
to a narrow pre-lock period. If unopened markets have floor_strike = null, the
strike locks at/near open and the lag question is live.

This distinguishes the two mechanisms without waiting for a boundary.
"""
import datetime as dt
import json
import time

import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "research-readonly/0.1"}


def get(path, **p):
    for a in range(5):
        try:
            r = requests.get(f"{BASE}{path}", params=p, headers=UA, timeout=40)
        except Exception:
            time.sleep(0.8 * (a + 1))
            continue
        if r.status_code == 429:
            time.sleep(1.5 * (a + 1))
            continue
        if r.status_code != 200:
            return None
        return r.json()
    return None


def iso(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def main():
    now = dt.datetime.now(dt.timezone.utc)
    print(f"probe at {now.isoformat()}\n")
    for status in ("open", "unopened"):
        j = get("/markets", series_ticker="KXBTC15M", status=status,
                limit=20)
        ms = (j or {}).get("markets", []) or []
        print("=" * 96)
        print(f"status={status}: {len(ms)} markets")
        print("=" * 96)
        if not ms:
            continue
        print(f"  {'ticker':<34} {'open_time':<21} {'strike':>12} "
              f"{'sub_title':<26} {'vol':>10}")
        for m in sorted(ms, key=lambda x: x.get("open_time") or "")[:12]:
            ot = m.get("open_time")
            fs = m.get("floor_strike")
            mins = ((iso(ot) - now).total_seconds() / 60.0) if ot else None
            print(f"  {str(m.get('ticker'))[:34]:<34} "
                  f"{str(ot)[:19]:<21} {str(fs):>12} "
                  f"{str(m.get('yes_sub_title'))[:26]:<26} "
                  f"{str(m.get('volume_fp')):>10}"
                  + (f"   (opens in {mins:+.1f} min)" if mins is not None
                     else ""))
        n_null = sum(1 for m in ms if m.get("floor_strike") is None)
        n_tbd = sum(1 for m in ms
                    if "TBD" in str(m.get("yes_sub_title", "")))
        print(f"\n  floor_strike NULL: {n_null}/{len(ms)}   "
              f"sub_title says TBD: {n_tbd}/{len(ms)}")

    # full field dump of the soonest unopened market
    j = get("/markets", series_ticker="KXBTC15M", status="unopened", limit=20)
    ms = (j or {}).get("markets", []) or []
    if ms:
        m = sorted(ms, key=lambda x: x.get("open_time") or "")[0]
        print("\n" + "=" * 96)
        print("SOONEST UNOPENED MARKET — full fields")
        print("=" * 96)
        for k in sorted(m):
            v = m[k]
            if isinstance(v, (dict, list)):
                v = json.dumps(v)[:110]
            print(f"  {k:<30} {str(v)[:110]}")


if __name__ == "__main__":
    main()
