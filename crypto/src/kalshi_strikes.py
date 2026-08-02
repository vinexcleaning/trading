"""Phase 0.2: THE decisive Phase 0 question for Kalshi.

Is the hourly/daily crypto series struck at fixed round numbers (=> trades across
the full 1c-99c range, cheap tails, low fee) or at the previous window's
settlement (=> born at-the-money, quadratic fee peaks, the KXBTC15M problem)?

Read-only, unauthenticated.
"""
import json
import time
from collections import defaultdict

import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "research-readonly/0.1"}

# The recurring short-dated families that matter.
FOCUS = [
    ("KXBTC15M", "fifteen_min", "BTC 15m up/down  (prior work's series)"),
    ("KXETH15M", "fifteen_min", "ETH 15m up/down"),
    ("KXSOL15M", "fifteen_min", "SOL 15m"),
    ("KXXRP15M", "fifteen_min", "XRP 15m"),
    ("KXDOGE15M", "fifteen_min", "DOGE 15m"),
    ("KXBTC", "hourly", "BTC hourly RANGE"),
    ("KXBTCD", "hourly", "BTC hourly ABOVE/BELOW"),
    ("KXETH", "hourly", "ETH hourly RANGE"),
    ("KXETHD", "hourly", "ETH hourly ABOVE/BELOW"),
    ("KXSOL", "hourly", "SOL hourly RANGE"),
    ("KXSOLD", "hourly", "SOL hourly ABOVE/BELOW"),
    ("KXXRP", "hourly", "XRP hourly RANGE"),
    ("KXXRPD", "hourly", "XRP hourly ABOVE/BELOW"),
    ("BTC", "daily", "BTC daily RANGE"),
    ("BTCD", "daily", "BTC daily ABOVE/BELOW"),
    ("ETHD", "daily", "ETH daily ABOVE/BELOW"),
    ("KXBTCMAXD", "daily", "BTC max daily (one-touch)"),
]


def get(path, **params):
    for attempt in range(6):
        r = requests.get(f"{BASE}{path}", params=params, headers=UA, timeout=30)
        if r.status_code == 429:
            time.sleep(1.0 * (attempt + 1))
            continue
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"rate limited on {path}")


def markets(series_ticker, status, limit=500):
    j = get("/markets", series_ticker=series_ticker, status=status, limit=limit)
    if not j:
        return []
    return j.get("markets", []) or []


def main():
    report = {}
    for ticker, freq, label in FOCUS:
        print("=" * 100)
        print(f"{ticker}  [{freq}]  {label}")
        print("=" * 100)
        ms = markets(ticker, "open")
        if not ms:
            ms = markets(ticker, "unopened")
            if ms:
                print("  (no open markets; showing unopened)")
        if not ms:
            print("  no open/unopened markets returned\n")
            report[ticker] = {"n_open": 0}
            continue

        print(f"  {len(ms)} markets returned")
        m0 = ms[0]
        print("\n  --- full field dump of one market ---")
        for k in sorted(m0.keys()):
            v = m0[k]
            if isinstance(v, (dict, list)):
                v = json.dumps(v)[:160]
            print(f"    {k:<32} {str(v)[:160]}")

        # group by event to see the strike ladder within one expiry
        by_event = defaultdict(list)
        for m in ms:
            by_event[m.get("event_ticker")].append(m)
        ev = sorted(by_event.keys())[:3]
        print(f"\n  --- strike ladder, first {len(ev)} event(s) of "
              f"{len(by_event)} ---")
        for e in ev:
            rows = by_event[e]
            print(f"\n    event {e}   ({len(rows)} markets)  "
                  f"close={rows[0].get('close_time')}")
            def sk(m):
                return (m.get("floor_strike") if m.get("floor_strike") is not None
                        else (m.get("cap_strike") or 0))
            for m in sorted(rows, key=sk)[:40]:
                print(f"      {str(m.get('ticker')):<44} "
                      f"type={str(m.get('strike_type')):<16} "
                      f"floor={str(m.get('floor_strike')):>12} "
                      f"cap={str(m.get('cap_strike')):>12} "
                      f"bid={str(m.get('yes_bid_dollars')):>7} "
                      f"ask={str(m.get('yes_ask_dollars')):>7} "
                      f"vol={str(m.get('volume_fp')):>11} "
                      f"oi={str(m.get('open_interest_fp')):>11}")

        report[ticker] = {
            "n_markets": len(ms),
            "n_events": len(by_event),
            "strike_types": sorted({str(m.get("strike_type")) for m in ms}),
            "sample": m0,
        }
        print()
        time.sleep(0.25)

    with open(r"C:\Users\gianf\crypto\docs\kalshi_strikes.json", "w") as f:
        json.dump(report, f, indent=2, default=str)


if __name__ == "__main__":
    main()
