"""Pull Kalshi tennis head-to-head match markets.

Each match is one event with two binary markets (one per player). The player
names come from yes_sub_title / no_sub_title; tournament and round come from
the rules text. Pulls every status so settled markets are available for the
Stage 4 market-vs-model comparison.
"""
import json
import pathlib
import time

import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
OUT = pathlib.Path(__file__).resolve().parents[1] / "data" / "kalshi"

# Head-to-head "who wins this match" series only. Excludes props (aces, games,
# spreads, set winners), tournament-outright and doubles series.
SERIES = [
    "KXATPMATCH",
    "KXWTAMATCH",
    "KXATPCHALLENGERMATCH",
    "KXCHALLENGERMATCH",
    "KXWTACHALLENGERMATCH",
    "KXITFMATCH",
    "KXITFWMATCH",
    "KXDAVISCUPMATCH",
    "KXUNITEDCUPMATCH",
    "KXATPGAME",
    "KXWTAGAME",
    "KXATPGWINNER",
    "KXEXHIBITIONMEN",
    "KXEXHIBITIONWOMEN",
    "KXTENNISEXHIBITION",
    "KXSIXKINGSMATCH",
    "KXBATTLEOFSEXES",
]


def pull(series):
    out, cursor = [], None
    while True:
        params = {"series_ticker": series, "limit": 1000}
        if cursor:
            params["cursor"] = cursor
        for attempt in range(5):
            try:
                r = requests.get(f"{BASE}/markets", params=params, timeout=90)
                r.raise_for_status()
                break
            except Exception:  # noqa: BLE001
                if attempt == 4:
                    raise
                time.sleep(2 * (attempt + 1))
        body = r.json()
        batch = body.get("markets", [])
        out.extend(batch)
        cursor = body.get("cursor")
        if not cursor or not batch:
            return out
        time.sleep(0.15)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    everything = {}
    for s in SERIES:
        try:
            rows = pull(s)
        except Exception as e:  # noqa: BLE001
            print(f"{s:24s} ERROR {e!r}", flush=True)
            continue
        everything[s] = rows
        statuses = {}
        for m in rows:
            statuses[m.get("status", "?")] = statuses.get(m.get("status", "?"), 0) + 1
        print(f"{s:24s} {len(rows):6d} markets  {statuses}", flush=True)

    path = OUT / "tennis_markets.json"
    path.write_text(json.dumps(everything), encoding="utf-8")
    total = sum(len(v) for v in everything.values())
    print(f"\nwrote {total} markets -> {path} ({path.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
