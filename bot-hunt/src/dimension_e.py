"""DIMENSION E for every candidate family: how many SETTLED EVENTS can actually
be retrieved today?

Not a rate from a 24h tape — the retrievable count, which is what a backtest
gets to use. The unit is the EVENT (one match), never the market: a 3-way
soccer ladder is three markets and one observation, and a Kalshi tennis match
is two markets and one observation. GUARDS #8.

The bar is LEDGER K014, measured on the real tape: **481 settled events** to
detect a 5pp edge at 80% power, **2,084** to clear a 2.4c cost bar.

Also records, per series, the earliest retrievable close_time — because this
turned out to be a fixed calendar boundary rather than a rolling window, and
that is a correction to `market-selection/WHAT_IS_LEFT.md`.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import venues as V  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "reports"

CANDIDATES = {
    # South American / Mexican soccer — market-selection's #1
    "KXLIGAMXGAME": "soccer LigaMX",
    "KXARGPREMDIVGAME": "soccer Argentina",
    "KXCOPADOBRASILGAME": "soccer Copa do Brasil",
    "KXDIMAYORGAME": "soccer Colombia (NO free line)",
    "KXMLSGAME": "soccer MLS",
    # tennis — biggest sports counterparty on the exchange
    "KXATPMATCH": "tennis ATP",
    "KXWTAMATCH": "tennis WTA",
    "KXITFMATCH": "tennis ITF men",
    "KXITFWMATCH": "tennis ITF women",
    # esports — the family with the only reconciled live P&L
    "KXCS2GAME": "esports CS2",
    "KXLOLGAME": "esports LoL",
    "KXVALORANTGAME": "esports Valorant",
    # MLB — market-selection's #2 and #3
    "KXMLBGAME": "MLB moneyline",
    "KXMLBRFI": "MLB 1st-inning run",
    "KXMLBTOTAL": "MLB total",
    "KXMLBHR": "MLB prop home run",
    "KXMLBKS": "MLB prop strikeouts",
    # negative control: known one-sided
    "KXHIGHNY": "weather NY (CONTROL: known dead)",
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    print(f"{'series':22} {'desc':30} {'mkts':>6} {'events':>7} {'mk/ev':>6} "
          f"{'earliest':>11} {'K014 5pp':>9}")
    for s, desc in CANDIDATES.items():
        mk = list(V.k_paginate("/markets",
                               {"series_ticker": s, "status": "settled",
                                "limit": 200}, "markets", max_pages=80))
        evs = Counter(m.get("event_ticker") for m in mk if m.get("event_ticker"))
        ct = [m.get("close_time") for m in mk if m.get("close_time")]
        n_ev = len(evs)
        per = (len(mk) / n_ev) if n_ev else 0
        earliest = min(ct)[:10] if ct else "-"
        ratio = n_ev / 481
        rows.append({"series": s, "desc": desc, "markets": len(mk),
                     "events": n_ev, "markets_per_event": round(per, 2),
                     "earliest_close": earliest,
                     "k014_5pp_ratio": round(ratio, 3),
                     "k014_cost_ratio": round(n_ev / 2084, 4)})
        print(f"{s:22} {desc:30} {len(mk):>6} {n_ev:>7} {per:>6.2f} "
              f"{earliest:>11} {ratio:>8.2f}x")

    (OUT / "dimension_e.json").write_text(json.dumps(rows, indent=1),
                                          encoding="utf-8")
    tot = sum(r["events"] for r in rows if "CONTROL" not in r["desc"])
    print(f"\n  total retrievable settled events across all candidates "
          f"(control excluded): {tot}")
    print(f"  K014 bar: 481 for a 5pp edge / 2,084 to clear a 2.4c cost bar")
    ea = Counter(r["earliest_close"] for r in rows)
    print(f"\n  earliest retrievable close_time, across families: "
          f"{dict(ea.most_common())}")
    print("  -> a single shared calendar boundary is a RETENTION CUTOFF, not "
          "a per-series season start")
    print("\nwrote reports/dimension_e.json")


if __name__ == "__main__":
    main()
