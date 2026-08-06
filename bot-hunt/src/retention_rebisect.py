"""Audit D8 -- re-bisect Kalshi's retention boundary, and settle M009 vs BH009.

TWO PROJECTS MEASURED THIS AND DISAGREE, and the disagreement gates a stated
deadline of 2026-08-19 in market-selection/WHAT_IS_LEFT.md ("THE DECAYING ITEM").

  M009 (market-selection, 2026-08-02): the Kalshi TRADE TAPE retains **exactly
       69 days and rolls daily**. Bisected at 13 ages; trades present at 69 d
       (2026-05-25), zero at 70 d.

  BH009 (bot-hunt, 2026-08-04):       the MARKET LISTING boundary is a **fixed
       calendar date**. Four independent query forms all return the same
       earliest close_time and 13 of 18 unrelated families share 2026-05-25.
       Bisected 08-02 and 08-04 -- the window GREW from 69 to 71 days.

THE HYPOTHESES MAKE DIFFERENT PREDICTIONS TODAY, which is what makes this cheap.
Today is 2026-08-06, i.e. 73 days after 2026-05-25.

  If retention ROLLS at 69 days      -> the boundary today is ~2026-05-29
  If the boundary is FIXED            -> it is still 2026-05-25, now 73 days old

They may also both be right about DIFFERENT OBJECTS -- the listing and the tape
are separate endpoints and nothing has ever tested them side by side on the same
day. So this probes BOTH, at the same minute, and reports them separately.

Read-only. A few dozen unauthenticated calls.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import venues as V  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REP = ROOT / "reports"

# Families deliberately unrelated to each other. If a boundary is a property of
# the EXCHANGE it is identical across all of them; if it is a property of a
# family's own history it is not.
FAMILIES = ["KXMLBGAME", "KXATPMATCH", "KXCS2GAME", "KXHIGHNY", "KXBTCD",
            "KXITFMATCH", "KXNBAGAME", "KXWTAMATCH"]

NOW = datetime.now(timezone.utc)


def earliest_listed(series: str):
    """The oldest settled market the LISTING endpoint will return."""
    best = None
    n = 0
    for m in V.k_paginate("/markets",
                          {"series_ticker": series, "status": "settled",
                           "limit": 200}, "markets", max_pages=40):
        ct = m.get("close_time")
        n += 1
        if ct and (best is None or ct < best):
            best = ct
    return best, n


def tape_at(series: str, ticker: str | None, day: datetime):
    """Does the TRADE TAPE return anything for a window on `day`?"""
    start = int(day.replace(hour=0, minute=0, second=0).timestamp())
    params = {"min_ts": start, "max_ts": start + 86400, "limit": 100}
    if ticker:
        params["ticker"] = ticker
    r = V.k_get("/markets/trades", params)
    if r is None or r.status_code != 200:
        return None
    try:
        return len((r.json() or {}).get("trades") or [])
    except ValueError:
        return None


def main() -> None:
    REP.mkdir(parents=True, exist_ok=True)
    out = {"probed_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ")}
    print(f"== RE-BISECT  {out['probed_utc']}")
    print(f"   2026-05-25 is {(NOW - datetime(2026,5,25,tzinfo=timezone.utc)).days} "
          f"days ago")
    print(f"   a 69-day rolling window would start "
          f"{(NOW - timedelta(days=69)).date()}\n")

    # ---------------------------------------------------- 1. the LISTING
    print("== 1. MARKET LISTING — earliest settled close_time per family")
    listing = {}
    for s in FAMILIES:
        try:
            ct, n = earliest_listed(s)
        except Exception as e:  # noqa: BLE001
            print(f"   {s:16} ERROR {type(e).__name__}")
            continue
        if ct is None:
            print(f"   {s:16} no settled markets returned")
            listing[s] = None
            continue
        age = (NOW - datetime.fromisoformat(ct.replace("Z", "+00:00"))).days
        listing[s] = {"earliest_close": ct, "age_days": age, "n_markets": n}
        print(f"   {s:16} {ct}   age {age:>3} d   ({n:,} settled markets)")
    out["listing"] = listing

    dates = sorted({v["earliest_close"][:10] for v in listing.values() if v})
    print(f"\n   distinct boundary dates across {len(FAMILIES)} families: {dates}")
    out["listing_distinct_dates"] = dates

    # ---------------------------------------------------- 2. the TRADE TAPE
    print("\n== 2. TRADE TAPE — is there a trade on each of these days?")
    tape = {}
    for age in (60, 66, 68, 69, 70, 71, 72, 73, 74, 76, 80):
        day = NOW - timedelta(days=age)
        n = tape_at("", None, day)
        tape[age] = {"date": str(day.date()), "trades": n}
        mark = "" if n else "   <-- empty"
        print(f"   age {age:>3} d  {day.date()}  trades={n}{mark}")
    out["tape"] = tape

    live = [a for a, v in sorted(tape.items()) if v["trades"]]
    dead = [a for a, v in sorted(tape.items()) if v["trades"] == 0]
    print(f"\n   tape has trades at ages: {live}")
    print(f"   tape EMPTY at ages:      {dead}")

    # ---------------------------------------------------- 3. the verdict
    print("\n== 3. VERDICT")
    roll_start = (NOW - timedelta(days=69)).date()
    if dates and dates[0] <= "2026-05-25":
        print(f"   LISTING boundary is {dates[0]}, which is "
              f"{(NOW - datetime.fromisoformat(dates[0] + 'T00:00:00+00:00')).days} "
              f"days old.")
        print(f"   A 69-day rolling window would put it at {roll_start}.")
        if dates[0] < str(roll_start):
            print("   => The LISTING boundary is OLDER than 69 days. "
                  "BH009 is supported: it is NOT a 69-day rolling window.")
            out["verdict_listing"] = "fixed_or_longer_than_69d"
        else:
            print("   => Consistent with a rolling window. M009 is supported.")
            out["verdict_listing"] = "rolling_69d"
    if dead and live:
        print(f"   TAPE goes empty between age {max(live)} d and {min(dead)} d.")
        out["verdict_tape"] = {"last_live_age_d": max(live),
                               "first_dead_age_d": min(dead)}
        if min(dead) > 71:
            print("   => The TAPE also extends past 69 days. M009's "
                  "'exactly 69 days' has moved.")
    elif live and not dead:
        print(f"   TAPE returned trades at EVERY age probed, out to "
              f"{max(live)} d. No boundary found in this range.")
        out["verdict_tape"] = {"no_boundary_within": max(live)}

    (REP / "retention_rebisect.json").write_text(
        json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("\nwrote reports/retention_rebisect.json")


if __name__ == "__main__":
    main()
