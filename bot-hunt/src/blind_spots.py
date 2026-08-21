"""Mailbox 018, second job: WHERE is this repo flying blind on Kalshi baseball?

`RESEARCH` found that Pinnacle's free guest feed carries 79 two-sided baseball
props in three kinds only -- Exact Scores, Next Run, Futures -- while Kalshi
quotes far more per game. The useful question is not "which of those can we
trade". It is:

    for every kind of baseball market Kalshi quotes, is there ANY free sharp
    reference against which we could ever tell whether its price is wrong?

⚠ AND THE INFERENCE THAT MUST NOT BE DRAWN FROM THE ANSWER, STATED FIRST.
------------------------------------------------------------------------
"No free sharp reference exists for this market" is **NOT** evidence that the
market is mispriced. That is M024's retracted argument and `RESEARCH` refused it
explicitly. It is equally consistent with nobody trading the market at all --
and, worse, it **removes the cheap way of finding out you are wrong.** So a
market with no reference is not an opportunity. It is a place where a mistake
would be expensive to detect, which is the opposite.

What the output is for: knowing which parts of the board can be checked and
which cannot, before anyone builds anything on top of one of them.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT.parent))
import venues as V  # noqa: E402

# ⚠ ADDED 2026-08-21: launched by the watchdog these inherit the Windows cp1252
# console default, and a print containing a warning glyph then raises
# UnicodeEncodeError and kills the run. It cost one capture already.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

REP = ROOT / "reports"
PIN = "https://guest.api.arcadia.pinnacle.com/0.1/sports/3"


def kalshi_baseball_families():
    """Every open Kalshi baseball series, and how big each is.

    ⚠ v1 OF THIS FUNCTION RETURNED ZERO AND IT WAS A BUG, NOT AN ABSENCE --
    Guard #27 applied to my own output an hour after I wrote it. It paged the
    unfiltered `/markets` listing with a 40-page cap, saw 8,000 open markets,
    found no baseball among them, and printed a table of nothing. Baseball was
    simply past the cap: the same "a page cap silently decides what you see"
    failure that once starved 40 MLB markets a cycle in `record.py`.

    So the series list is enumerated FIRST and each one queried by name. The
    assert below is the control: if the exchange really carries no open
    baseball, that is a claim big enough to have to be stated deliberately.
    """
    ser = []
    r = V.k_get("/series", {"category": "Sports", "limit": 200})
    assert r is not None and r.status_code == 200, "series listing failed"
    allser = (r.json() or {}).get("series") or []
    assert allser, "series listing is EMPTY -- apparatus failure, not an absence"
    for s in allser:
        tk = (s.get("ticker") or "")
        title = (s.get("title") or "")
        if re.search(r"MLB|BASEBALL", tk.upper()) or "baseball" in title.lower():
            ser.append((tk, title))
    print(f"   baseball series listed by the exchange: {len(ser)}"
          f"  (of {len(allser):,} sports series)")

    fams = defaultdict(lambda: {"markets": 0, "events": set(), "titles": Counter(),
                                "two_sided": 0, "volume": 0, "name": ""})
    for tk, title in ser:
        got = list(V.k_paginate("/markets",
                                {"series_ticker": tk, "status": "open",
                                 "limit": 200}, "markets", max_pages=20))
        if not got:
            continue
        f = fams[tk]
        f["name"] = title
        for m in got:
            f["markets"] += 1
            f["events"].add(m.get("event_ticker"))
            f["titles"][(m.get("title") or "")[:70]] += 1
            # ⚠ *_dollars / *_fp, never the legacy integer fields (GUARDS #12/#23).
            yb = V.fnum(m.get("yes_bid_dollars"))
            ya = V.fnum(m.get("yes_ask_dollars"))
            if yb is not None and ya is not None and yb > 0 and ya < 1:
                f["two_sided"] += 1
            f["volume"] += int(V.fnum(m.get("volume")) or 0)
    return fams


def pinnacle_baseball_types():
    """What does the free sharp feed actually carry for baseball?"""
    mus = V.get(f"{PIN}/matchups", pace=0.3, tries=2, timeout=30)
    mk = V.get(f"{PIN}/markets/straight", pace=0.3, tries=2, timeout=30)
    assert mus is not None and mus.status_code == 200, "pinnacle matchups failed"
    assert mk is not None and mk.status_code == 200, "pinnacle markets failed"
    rows = mus.json()
    # a prop lives on a CHILD matchup: parentId set, and its own `special` block
    kinds = Counter()
    child_of = {}
    for m in rows:
        sp = m.get("special") or {}
        if m.get("parentId"):
            kinds[(sp.get("category") or "derivative/period").strip()] += 1
            child_of[m.get("id")] = m.get("parentId")
    two_sided = 0
    by_type = Counter()
    priced = defaultdict(set)
    for m in mk.json():
        mid = m.get("matchupId")
        prices = m.get("prices") or []
        by_type[f"{m.get('type')} p{m.get('period')}"] += 1
        if mid in child_of and len([p for p in prices
                                    if p.get("price") is not None]) >= 2:
            two_sided += 1
            priced[child_of[mid]].add(mid)
    return {"prop_kinds": kinds, "market_types": by_type,
            "two_sided_prop_markets": two_sided,
            "parents_with_props": len(priced), "total_matchups": len(rows)}


def main() -> None:
    REP.mkdir(parents=True, exist_ok=True)
    print("=" * 78)
    print("WHERE IS THIS REPO BLIND ON KALSHI BASEBALL?")
    print("=" * 78)
    print("⚠ 'No free sharp reference' is NOT evidence of mispricing. It is the")
    print("  absence of a cheap way to find out you are wrong. See the docstring.\n")

    fams = kalshi_baseball_families()
    print(f"{'Kalshi series':22} {'markets':>8} {'events':>7} {'2-sided':>8} "
          f"{'volume':>12}  most common title")
    print("-" * 108)
    tot = 0
    for ser, f in sorted(fams.items(), key=lambda x: -x[1]["markets"]):
        top = f["titles"].most_common(1)[0][0] if f["titles"] else ""
        tot += f["markets"]
        print(f"{ser:22} {f['markets']:>8,} {len(f['events']):>7,} "
              f"{f['two_sided']:>8,} {f['volume']:>12,}  {top[:40]}")
    print(f"{'TOTAL':22} {tot:>8,}")

    print("\n" + "=" * 78)
    print("WHAT THE FREE SHARP FEED CARRIES, SAME MOMENT")
    print("=" * 78)
    p = pinnacle_baseball_types()
    print(f"   matchups listed                    : {p['total_matchups']:,}")
    print(f"   parent games carrying any prop     : {p['parents_with_props']:,}")
    print(f"   two-sided prop markets             : {p['two_sided_prop_markets']:,}")
    print("\n   prop kinds it carries:")
    for k, n in p["prop_kinds"].most_common(12):
        print(f"      {k[:52]:52} {n:>6,}")
    print("\n   straight market types (type + period):")
    for k, n in p["market_types"].most_common(12):
        print(f"      {k[:52]:52} {n:>6,}")

    out = {"kalshi": {k: {"markets": v["markets"], "events": len(v["events"]),
                          "two_sided": v["two_sided"], "volume": v["volume"],
                          "top_titles": v["titles"].most_common(6)}
                      for k, v in fams.items()},
           "pinnacle": {"prop_kinds": dict(p["prop_kinds"]),
                        "market_types": dict(p["market_types"]),
                        "two_sided_prop_markets": p["two_sided_prop_markets"],
                        "parents_with_props": p["parents_with_props"]}}
    (REP / "baseball_blind_spots.json").write_text(json.dumps(out, indent=1),
                                                   encoding="utf-8")
    print("\n   wrote reports/baseball_blind_spots.json")


if __name__ == "__main__":
    main()
