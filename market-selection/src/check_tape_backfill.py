"""Is the Kalshi trade tape re-pullable, or does it need a live recorder too?

This is a recording-priority decision, not a curiosity. Order-book depth has no
historical endpoint at all and must be recorded live. If the TRADE tape is also
live-only, a second recorder has to start tonight. If it is queryable
historically, recording it would waste the night's bandwidth on something that
can be fetched any time inside the ~69-day window.

STATUS.md says closed markets 404 on /markets/{ticker}. That is about the
market object. It does not follow that their TRADES are unreachable, because
/markets/trades is an exchange-wide endpoint with min_ts / max_ts.

Tested by asking for windows at increasing age and checking whether trades come
back AND whether they include tickers that no longer resolve as open markets.
"""
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
import kalshi_api as K  # noqa: E402

NOW = datetime.now(timezone.utc)


def window(days_ago, hours=1):
    end = NOW - timedelta(days=days_ago)
    start = end - timedelta(hours=hours)
    r = K.get("/markets/trades", {"limit": 1000,
                                  "min_ts": int(start.timestamp()),
                                  "max_ts": int(end.timestamp())})
    if r is None or r.status_code != 200:
        return days_ago, None, None, None if r is None else r.status_code
    tr = r.json().get("trades", [])
    if not tr:
        return days_ago, 0, None, 200
    ts = sorted(t["created_time"] for t in tr)
    return days_ago, len(tr), (ts[0], ts[-1]), 200


def main():
    print(f"now = {NOW:%Y-%m-%d %H:%M} UTC")
    print(f"\n{'days ago':>9s} {'http':>5s} {'trades':>7s}  span of returned trades")
    results = []
    for d in (0, 1, 3, 7, 14, 30, 45, 60, 68, 75, 90, 120, 365):
        dd, n, span, code = window(d)
        results.append({"days_ago": dd, "n": n, "span": span, "http": code})
        print(f"{dd:9d} {str(code):>5s} {str(n):>7s}  {span}")

    # do the OLD trades reference markets that are now gone?
    old = [r for r in results if r["days_ago"] >= 30 and (r["n"] or 0) > 0]
    if old:
        d = max(r["days_ago"] for r in old)
        end = NOW - timedelta(days=d)
        r = K.get("/markets/trades", {"limit": 200,
                                      "min_ts": int((end - timedelta(hours=1)).timestamp()),
                                      "max_ts": int(end.timestamp())})
        tks = list({t["ticker"] for t in r.json().get("trades", [])})[:8]
        print(f"\nspot-checking {len(tks)} tickers that traded {d} days ago:")
        gone = 0
        for t in tks:
            rr = K.get(f"/markets/{t}")
            status = "?"
            if rr is not None and rr.status_code == 200:
                status = (rr.json().get("market") or {}).get("status", "?")
            elif rr is not None:
                status = f"HTTP {rr.status_code}"
                gone += 1
            print(f"  {t[:52]:52s} -> {status}")
        print(f"\n{gone}/{len(tks)} of those markets no longer resolve, "
              f"yet their trades were returned by the tape.")

    ok = [r["days_ago"] for r in results if (r["n"] or 0) > 0]
    print(f"\nOldest window that returned trades: {max(ok) if ok else 'none'} days ago")
    print("VERDICT:", "tape is HISTORICALLY QUERYABLE -- no live trade recorder "
          "needed inside that horizon" if ok and max(ok) >= 30 else
          "tape looks LIVE-ONLY -- a trade recorder must start now")


if __name__ == "__main__":
    main()
