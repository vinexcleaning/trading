"""Content-validate the completed trade backfill. Not a file count.

`days_complete=17` is a count of files on disk. Every incident in this project's
history had correct counts, so this checks what is actually inside: that each
day spans its full 24 hours, that no line is torn, that prices are inside
(0,1), that trade ids are unique within a day, and that the union of days
covers 2026-05-25 -> 2026-06-11 with no gap.
"""
import glob
import json
import os
from collections import Counter
from datetime import date, datetime, timedelta

DIR = os.path.join(os.path.dirname(__file__), "..", "data", "tape_pmxt_window")
REP = os.path.join(os.path.dirname(__file__), "..", "reports")

EXPECTED_FIELDS = {"count_fp", "created_time", "is_block_trade",
                   "no_price_dollars", "taker_book_side", "taker_outcome_side",
                   "taker_side", "ticker", "trade_id", "yes_price_dollars"}

files = sorted(glob.glob(os.path.join(DIR, "trades_*.jsonl")))
print(f"{len(files)} day files, "
      f"{sum(os.path.getsize(f) for f in files)/1e9:.1f} GB\n")
print(f"{'day':12s} {'trades':>10s} {'first':>9s} {'last':>9s} {'hrs':>4s} "
      f"{'series':>7s} {'torn':>5s} {'badpx':>6s} {'dupids':>7s}  verdict")

rows = []
all_days = set()
for path in files:
    day = os.path.basename(path)[7:17]
    n = torn = badpx = 0
    first = last = None
    hours = set()
    series = set()
    ids = set()
    dups = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                t = json.loads(line)
            except json.JSONDecodeError:
                torn += 1
                continue
            n += 1
            if not EXPECTED_FIELDS <= set(t):
                torn += 1
                continue
            ct = t.get("created_time") or ""
            if ct:
                if first is None or ct < first:
                    first = ct
                if last is None or ct > last:
                    last = ct
                hours.add(ct[11:13])
            tk = t.get("ticker")
            if tk:
                series.add(tk.split("-")[0])
            try:
                p = float(t["yes_price_dollars"])
                if not (0.0 < p < 1.0):
                    badpx += 1
            except (TypeError, ValueError, KeyError):
                badpx += 1
            tid = t.get("trade_id")
            if tid in ids:
                dups += 1
            else:
                ids.add(tid)
    # KALSHI HAS A WEEKLY MAINTENANCE WINDOW ON THURSDAYS, ~07:00-09:00 UTC.
    # Measured: 2026-05-28, 06-04 and 06-11 are all missing hour 08 entirely
    # and have only 6-21 trades in hour 07. All three are Thursdays -- three
    # for three. Re-querying those hours directly returns ZERO trades, so the
    # hour is genuinely empty at the source, not a pagination gap.
    #
    # An earlier version of this check labelled 06-11 "partial by design",
    # assuming it was truncated because the pmxt archive ends at 03:00. That
    # was wrong: the TAPE for 06-11 is a full 00:00-23:59 day with 5.25M
    # trades; it is missing hour 08 for the same Thursday reason.
    weekday = datetime.strptime(day, "%Y-%m-%d").weekday()  # 3 = Thursday
    maintenance = weekday == 3 and "08" not in hours and len(hours) == 23
    ok = (torn == 0 and badpx == 0 and dups == 0 and n > 0
          and (len(hours) >= 24 or maintenance))
    verdict = "OK" if ok else "CHECK"
    if maintenance:
        verdict += " (Thursday maintenance, hour 08 empty at source)"
    print(f"{day:12s} {n:10,d} {str(first)[11:19]:>9s} {str(last)[11:19]:>9s} "
          f"{len(hours):4d} {len(series):7d} {torn:5d} {badpx:6d} {dups:7d}  "
          f"{verdict}")
    rows.append({"day": day, "trades": n, "hours": len(hours),
                 "series": len(series), "torn": torn, "badpx": badpx,
                 "dup_ids": dups, "verdict": verdict})
    all_days.add(day)

print(f"\ntotal trades: {sum(r['trades'] for r in rows):,}")
print(f"days failing content checks: "
      f"{sum(1 for r in rows if not r['verdict'].startswith('OK'))}")

# contiguity against the pmxt archive window
d, missing = date(2026, 5, 25), []
while d <= date(2026, 6, 11):
    if d.isoformat() not in all_days:
        missing.append(d.isoformat())
    d += timedelta(days=1)
print(f"\ncoverage 2026-05-25 .. 2026-06-11: "
      f"{'CONTIGUOUS, no gaps' if not missing else 'MISSING ' + str(missing)}")
print("2026-05-14 .. 2026-05-24 remains unrecoverable "
      "(past the 69-day tape window).")

with open(os.path.join(REP, "backfill_verification.json"), "w",
          encoding="utf-8") as fh:
    json.dump({"days": rows, "missing": missing}, fh, indent=1)
