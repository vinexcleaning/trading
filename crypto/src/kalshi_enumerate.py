"""Phase 0.1: enumerate every Kalshi crypto series and inspect strike conventions.

Read-only, unauthenticated. Writes docs/kalshi_series.json.
"""
import json
import sys
import time

import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "research-readonly/0.1"}
OUT = r"C:\Users\gianf\crypto\docs\kalshi_series.json"


def get(path, **params):
    for attempt in range(6):
        r = requests.get(f"{BASE}{path}", params=params, headers=UA, timeout=30)
        if r.status_code == 429:
            time.sleep(1.0 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"rate limited on {path}")


def main():
    j = get("/series", category="Crypto")
    series = j.get("series", [])
    print(f"/series?category=Crypto returned {len(series)} series\n")
    print("--- raw shape of first series object ---")
    print(json.dumps(series[0], indent=2)[:2500])
    print("\n--- all tickers ---")
    for s in sorted(series, key=lambda x: x.get("ticker", "")):
        print(f"{s.get('ticker','?'):<22} {str(s.get('frequency')):<10} "
              f"{str(s.get('title'))[:70]}")
    with open(OUT, "w") as f:
        json.dump(j, f, indent=2)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
