"""Is there a BACKFILLABLE overlap between a sharp reference price and Kalshi?

Pinnacle's guest API is live-only, so a strategy built on it would have to wait
weeks for the recorder to accrue. But the reference price may already be
historical from a second direction:

  * football-data.co.uk's `PSCH` / `PSCD` / `PSCA` columns are **Pinnacle
    CLOSING** home/draw/away odds. If they are populated for 2026 matches in the
    South American leagues, the sharp side is backfilled for free.
  * Kalshi's public trade tape retains **~69 days** (bisected by a prior session:
    trades present at 2026-05-25, zero at 2026-05-24) and is free.

If both hold, Steps 4-6 can run on real history NOW instead of waiting.

This measures the overlap rather than assuming it: per league, how many matches
have a populated Pinnacle close, in what date range, and does that range reach
inside Kalshi's rolling window.

Read-only. Public endpoints only.
"""
from __future__ import annotations

import csv
import io
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import venues as V  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "reports"
UA = {"User-Agent": "bot-hunt-research/1.0"}

# code -> the Kalshi series that trades the same competition
LEAGUES = {
    "MEX": "KXLIGAMXGAME",
    "ARG": "KXARGPREMDIVGAME",
    "BRA": "KXCOPADOBRASILGAME",
    "USA": "KXMLSGAME",
    "JPN": None,
}


def parse_date(s):
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except (ValueError, AttributeError):
            continue
    return None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}

    print("=== Pinnacle CLOSING odds coverage in football-data.co.uk ===")
    print(f"{'code':5} {'rows':>6} {'PSC pop':>8} {'%':>6} {'first':>11} "
          f"{'last':>11} {'league column'}")
    for code in LEAGUES:
        r = requests.get(f"https://www.football-data.co.uk/new/{code}.csv",
                         headers=UA, timeout=60)
        if r.status_code != 200:
            print(f"{code:5} HTTP {r.status_code}")
            continue
        rows = list(csv.DictReader(io.StringIO(r.content.decode("utf-8",
                                                                "replace"))))
        n = len(rows)
        have, dates, leagues = 0, [], Counter()
        recent = []
        for row in rows:
            leagues[(row.get("League") or row.get("Div") or "?").strip()] += 1
            d = parse_date(row.get("Date", ""))
            if d:
                dates.append(d)
            psc = [row.get("PSCH"), row.get("PSCD"), row.get("PSCA")]
            ok = all(x not in (None, "", "0") for x in psc)
            if ok:
                have += 1
                if d and d >= datetime(2026, 1, 1).date():
                    recent.append((d, psc))
        lg = ", ".join(f"{k}({v})" for k, v in leagues.most_common(2))
        print(f"{code:5} {n:>6} {have:>8} {100*have/max(n,1):>5.1f}% "
              f"{str(min(dates) if dates else '-'):>11} "
              f"{str(max(dates) if dates else '-'):>11} {lg}")
        report[code] = {
            "rows": n, "psc_populated": have,
            "first": str(min(dates)) if dates else None,
            "last": str(max(dates)) if dates else None,
            "leagues": leagues.most_common(3),
            "rows_2026_with_psc": len(recent),
        }
        if recent:
            recent.sort()
            print(f"      2026 rows with a Pinnacle close: {len(recent)}; "
                  f"most recent {recent[-1][0]} odds={recent[-1][1]}")

    # --- how far back does Kalshi's trade tape actually reach today? ---
    print("\n=== Kalshi trade-tape retention, re-bisected today ===")
    today = datetime.now(timezone.utc).date()
    lo, hi = 0, 120  # days back
    found = {}

    def trades_on(days_back: int) -> int:
        d0 = datetime.combine(today - timedelta(days=days_back),
                              datetime.min.time(), timezone.utc)
        r = V.k_get("/markets/trades",
                    {"min_ts": int(d0.timestamp()),
                     "max_ts": int((d0 + timedelta(days=1)).timestamp()),
                     "limit": 10})
        if r is None or r.status_code != 200:
            return -1
        return len(((r.json() or {}).get("trades")) or [])

    while lo < hi - 1:
        mid = (lo + hi) // 2
        n = trades_on(mid)
        found[mid] = n
        print(f"   {today - timedelta(days=mid)} ({mid:>3}d back): "
              f"{'HTTP fail' if n < 0 else f'{n} trades'}")
        if n > 0:
            lo = mid
        else:
            hi = mid
    report["kalshi_tape_days"] = lo
    report["kalshi_tape_earliest"] = str(today - timedelta(days=lo))
    print(f"\n   tape reaches back {lo} days -> earliest "
          f"{today - timedelta(days=lo)}")

    # --- do the two windows overlap, per league? ---
    print("\n=== OVERLAP: usable matches with BOTH a Pinnacle close and a "
          "live Kalshi tape ===")
    earliest = today - timedelta(days=lo)
    for code, series in LEAGUES.items():
        info = report.get(code)
        if not info or not info.get("last"):
            continue
        last = datetime.strptime(info["last"], "%Y-%m-%d").date()
        print(f"   {code:5} Pinnacle closes to {last}  vs Kalshi tape from "
              f"{earliest}  -> "
              f"{'OVERLAP' if last >= earliest else 'NO OVERLAP'}"
              f"   series={series}")

    (OUT / "overlap_probe.json").write_text(json.dumps(report, indent=1,
                                                       default=str),
                                            encoding="utf-8")
    print("\nwrote reports/overlap_probe.json")


if __name__ == "__main__":
    main()
