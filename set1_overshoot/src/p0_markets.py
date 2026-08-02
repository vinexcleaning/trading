"""Phase 0a -- pull the full market universe for the five tennis match series.

Every status is pulled so the settled/finalized set can be measured against the
whole book rather than assumed. Nothing is filtered here; filtering happens in
p0_universe.py where it can be counted.
"""
import json
import pathlib
import time

import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
OUT = pathlib.Path(__file__).resolve().parents[1] / "data"

SERIES = [
    "KXATPMATCH",
    "KXWTAMATCH",
    "KXATPCHALLENGERMATCH",
    "KXITFMATCH",
    "KXITFWMATCH",
]


def pull(series):
    out, cursor, pages = [], None, 0
    while True:
        params = {"series_ticker": series, "limit": 1000}
        if cursor:
            params["cursor"] = cursor
        for attempt in range(6):
            try:
                r = requests.get(f"{BASE}/markets", params=params, timeout=90)
                if r.status_code == 429:
                    time.sleep(2 * (attempt + 1))
                    continue
                r.raise_for_status()
                break
            except Exception:  # noqa: BLE001
                if attempt == 5:
                    raise
                time.sleep(2 * (attempt + 1))
        body = r.json()
        batch = body.get("markets", [])
        out.extend(batch)
        pages += 1
        cursor = body.get("cursor")
        if not cursor or not batch:
            return out
        time.sleep(0.12)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    everything = {}
    for s in SERIES:
        rows = pull(s)
        everything[s] = rows
        st = {}
        for m in rows:
            st[m.get("status", "?")] = st.get(m.get("status", "?"), 0) + 1
        print(f"{s:26s} {len(rows):6d} markets  {st}", flush=True)

    path = OUT / "markets_raw.json"
    path.write_text(json.dumps(everything), encoding="utf-8")
    total = sum(len(v) for v in everything.values())
    print(f"\n{total:,} markets -> {path} ({path.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
