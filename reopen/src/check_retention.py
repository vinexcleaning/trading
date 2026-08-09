"""Is the Kalshi trade tape still retrievable back to 2026-05-25?

WHY THIS CHAT IS RUNNING A NETWORK PROBE. It is not doing another chat's work.
The top reopen in this audit (C022/C023) asks `devig` to pull ~73 days of trade
tape against the 8 days already on disk. **Whether those 73 days still exist is
a fact about the closure, not a step in the fix**, and it decides whether that
reopen is safe to defer or has to happen now. Kalshi's window is the one thing
in this repo documented to vanish permanently.

BH009 measured the boundary on 2026-08-02, 08-04 and 08-06 and found it FIXED at
2026-05-25 while its apparent age grew 69 -> 71 -> 73 days. That refuted M009's
"exactly 69 days and rolls daily". **BH009's own caveat is the reason to
re-check: a fixed boundary is not a promise, the mechanism is unknown, and a
fixed boundary can vanish in one step rather than sliding.** This is the fourth
measurement.

Unauthenticated, read-only, GET only. Paced far under the 15 requests/second
ceiling C018 measured. Writes one file, inside reopen/.

  py -3 reopen\\src\\check_retention.py
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "reports"

KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
PACE_SEC = 1.0          # ~1 req/s against a measured ceiling of 15
TIMEOUT = 20

# The date BH009 pinned three times. If the boundary is still here, the C022
# pull is safe to defer; if it has moved forward, days are being lost.
PINNED = datetime(2026, 5, 25, tzinfo=timezone.utc)

# Ages in days to probe, chosen around the pinned boundary rather than by
# bisection -- three points either side answers "fixed or rolling" directly.
NOW = datetime.now(timezone.utc)


def get(path: str, params: dict):
    url = f"{KALSHI}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "trading-repo-audit"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:                                    # noqa: BLE001
        return None, {"error": repr(e)}


def trades_on(day: datetime) -> int | None:
    """How many trades does the tape return for a 24h window on `day`?

    No ticker filter: this asks about the tape as a whole, which is the claim
    being checked. A per-ticker probe can read zero because that market did not
    trade, which is how a retention question turns into a liquidity question.
    """
    start = int(day.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    status, body = get("/markets/trades",
                       {"min_ts": start, "max_ts": start + 86400, "limit": 100})
    if status != 200 or not isinstance(body, dict):
        return None
    return len(body.get("trades") or [])


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    probed = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
    pinned_age = (NOW - PINNED).days

    print(f"probed {probed}")
    print(f"BH009's pinned boundary 2026-05-25 is {pinned_age} days old today\n")

    days = [PINNED + timedelta(days=d) for d in (-3, -2, -1, 0, 1, 2, 3)]
    rows = []
    for day in days:
        n = trades_on(day)
        age = (NOW - day).days
        rows.append({"date": str(day.date()), "age_days": age, "trades": n})
        mark = ""
        if day.date() == PINNED.date():
            mark = "   <- BH009's boundary"
        print(f"  {day.date()}  age {age:>3}d  trades="
              f"{'ERR' if n is None else n:>4}{mark}")
        time.sleep(PACE_SEC)

    live = [r for r in rows if r["trades"]]
    dead = [r for r in rows if r["trades"] == 0]
    errs = [r for r in rows if r["trades"] is None]

    verdict = "UNDETERMINED"
    detail = ""
    if errs:
        verdict = "UNDETERMINED"
        detail = (f"{len(errs)} of {len(rows)} probes failed; a failed request "
                  f"is not an absence.")
    elif not live:
        verdict = "TAPE GONE OR MOVED"
        detail = ("Nothing returned at any probed date, including dates AFTER "
                  "the pinned boundary. Either retention moved a long way "
                  "forward or the endpoint changed shape. Do not read this as "
                  "'the data is gone' without a second check.")
    elif not dead:
        verdict = "BOUNDARY IS OLDER THAN PROBED"
        detail = ("Trades at every probed date including 3 days before the "
                  "pinned boundary, so the boundary sits further back than "
                  "2026-05-25 and BH009 understated the window.")
    else:
        oldest_live = min(r["date"] for r in live)
        verdict = f"BOUNDARY AT OR NEAR {oldest_live}"
        moved = oldest_live > str(PINNED.date())
        detail = ("MOVED FORWARD from 2026-05-25 -- the window is rolling "
                  "after all and days are being lost."
                  if moved else
                  "UNMOVED from 2026-05-25 across a fourth measurement.")

    print(f"\nVERDICT: {verdict}\n  {detail}")

    path = OUT / "retention_check.json"
    path.write_text(json.dumps({
        "probed_utc": probed,
        "pinned_boundary": str(PINNED.date()),
        "pinned_age_days_today": pinned_age,
        "prior_measurements": ["2026-08-02 (69d)", "2026-08-04 (71d)",
                               "2026-08-06 (73d)"],
        "rows": rows,
        "verdict": verdict,
        "detail": detail,
        "caveat": ("A fixed boundary is not a promise. Three -- now four -- "
                   "points establish it is not rolling NOW. The mechanism is "
                   "unknown and a fixed boundary can vanish in one step."),
    }, indent=2), encoding="utf-8")
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
