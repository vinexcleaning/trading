"""Mailbox 008, part 1: which soccer does Kalshi ACTUALLY run?

Two documents in this repo disagree and both are in my area:
  * soccer/dataset.md (2026-08-02): Liga MX, Argentina Primera, Copa do Brasil,
    Colombia, MLS.
  * soccer/reports/tape_soccer_scan.json: 210 tickers, 139 of them
    KXINTLFRIENDLYGAME, plus Uruguay, USL, Ecuador, Peru, NWSL, Chile, MLS,
    Colombia, Liga MX.

Neither shows a Premier League or Champions League market, and the user assumes
those exist. Answering from the API rather than from either document.

For every soccer series: how many markets it has ever listed, how much volume,
over what dates, and how much of it is settled. Then, explicitly, whether the
big European competitions are there at all.

Read-only. No keys, no orders.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "bot-hunt" / "src"))
import venues as V  # noqa: E402

REP = ROOT / "reports"

# Words that make a series title soccer. Deliberately broad -- it is easier to
# discard a false positive by eye than to notice a missing competition.
SOCCER = re.compile(
    r"soccer|football club|\bliga\b|premier league|serie a|bundesliga|la liga|"
    r"ligue 1|champions league|europa|eredivisie|mls\b|nwsl|copa|primera|"
    r"futbol|f[uú]tbol|世界杯|world cup|euro 20|fifa|uefa|concacaf|conmebol|"
    r"efl|championship|dimayor|brasileir|argentin|friendly", re.I)

# The competitions the user is assuming exist. Checked BY NAME, because "absent"
# is the answer that has to reach him and a silent omission is not an answer.
BIG_EURO = ["Premier League", "Champions League", "La Liga", "Bundesliga",
            "Serie A", "Ligue 1", "Europa League", "EFL", "Eredivisie",
            "World Cup", "Euro"]


def main() -> None:
    REP.mkdir(parents=True, exist_ok=True)
    r = V.k_get("/series", {"category": "Sports", "limit": 1000})
    ss = ((r.json() or {}).get("series") or []) if r and r.status_code == 200 else []
    print(f"Sports series on the exchange: {len(ss):,}")

    cand = [s for s in ss if SOCCER.search(
        f"{s.get('title','')} {s.get('ticker','')} {' '.join(s.get('tags') or [])}")]
    print(f"Series whose title/tags look like soccer: {len(cand)}\n")

    rows = []
    for i, s in enumerate(cand, 1):
        tk = s.get("ticker")
        n = nset = 0
        vol = 0.0
        lo = hi = None
        for m in V.k_paginate("/markets", {"series_ticker": tk, "limit": 200},
                              "markets", max_pages=25):
            n += 1
            if m.get("result") in ("yes", "no"):
                nset += 1
            try:
                vol += float(m.get("volume_fp") or 0)
            except (TypeError, ValueError):
                pass
            ct = m.get("close_time")
            if ct:
                lo = ct if lo is None or ct < lo else lo
                hi = ct if hi is None or ct > hi else hi
        rows.append({"ticker": tk, "title": s.get("title", ""),
                     "markets": n, "settled": nset, "volume": vol,
                     "first_close": lo, "last_close": hi,
                     "fee_type": s.get("fee_type")})
        if i % 10 == 0:
            print(f"   ...{i}/{len(cand)}", flush=True)

    rows.sort(key=lambda x: -x["volume"])
    print(f"\n{'series':26} {'markets':>8} {'settled':>8} {'volume':>14}  dates")
    print("-" * 96)
    for x in rows:
        if x["markets"] == 0:
            continue
        print(f"{x['ticker'][:26]:26} {x['markets']:>8,} {x['settled']:>8,} "
              f"{x['volume']:>14,.0f}  {str(x['first_close'])[:10]} .. "
              f"{str(x['last_close'])[:10]}   {x['title'][:34]}")

    dead = [x for x in rows if x["markets"] == 0]
    print(f"\nseries listed but with ZERO markets retrievable: {len(dead)}")

    tot_v = sum(x["volume"] for x in rows)
    tot_m = sum(x["markets"] for x in rows)
    print(f"\nALL SOCCER: {tot_m:,} markets, {tot_v:,.0f} contracts of volume")

    print("\n== THE COMPETITIONS THE USER IS ASSUMING EXIST")
    titles = " | ".join(f"{x['ticker']} {x['title']}" for x in rows)
    for name in BIG_EURO:
        hit = [x for x in rows if name.lower() in x["title"].lower()]
        if hit:
            print(f"   {name:20} PRESENT: " +
                  ", ".join(f"{h['ticker']} ({h['markets']:,} markets)"
                            for h in hit[:3]))
        else:
            print(f"   {name:20} ** ABSENT — no series on the exchange **")

    (REP / "soccer_census.json").write_text(
        json.dumps({"sports_series": len(ss), "soccer_series": len(cand),
                    "rows": rows}, indent=1, default=str), encoding="utf-8")
    print("\nwrote reports/soccer_census.json")


if __name__ == "__main__":
    main()
