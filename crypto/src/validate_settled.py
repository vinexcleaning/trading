"""Content-level validation of the Kalshi settled pull.

Row counts are NOT a data-quality check (failure mode #3). Two concurrent
writers were briefly running against these files, so every line is re-parsed and
every record is checked for the fields Tier A replay actually needs.

Checks:
  - every line parses as JSON (catches truncation from an interrupted write)
  - the LAST line parses (a truncated tail is the signature of a killed writer)
  - required fields present and non-empty on settled records
  - `result` is in {yes, no}
  - `expiration_value` parses as a number
  - strike present
  - duplicate tickers (the signature of two writers appending)
"""
import glob
import json
import os
from collections import Counter, defaultdict

ROOT = r"C:\Users\gianf\crypto\data\kalshi_settled"

REQUIRED = ["ticker", "event_ticker", "close_time", "result"]


def validate(path):
    rep = {"file": os.path.basename(path),
           "bytes": os.path.getsize(path),
           "lines": 0, "parse_errors": 0, "last_line_ok": False,
           "missing_field": Counter(), "bad_result": 0,
           "expiration_value_ok": 0, "expiration_value_missing": 0,
           "strike_ok": 0, "strike_missing": 0,
           "dup_tickers": 0, "n_events": 0,
           "first_close": None, "last_close": None}
    seen = Counter()
    events = set()
    closes = []
    last = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            rep["lines"] += 1
            last = line
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                rep["parse_errors"] += 1
                continue
            for k in REQUIRED:
                if m.get(k) in (None, ""):
                    rep["missing_field"][k] += 1
            if str(m.get("result")) not in ("yes", "no"):
                rep["bad_result"] += 1
            ev = m.get("expiration_value")
            if ev in (None, ""):
                rep["expiration_value_missing"] += 1
            else:
                try:
                    float(ev)
                    rep["expiration_value_ok"] += 1
                except (TypeError, ValueError):
                    rep["expiration_value_missing"] += 1
            if m.get("floor_strike") is None and m.get("cap_strike") is None:
                rep["strike_missing"] += 1
            else:
                rep["strike_ok"] += 1
            seen[m.get("ticker")] += 1
            if m.get("event_ticker"):
                events.add(m["event_ticker"])
            if m.get("close_time"):
                closes.append(m["close_time"])
    if last is not None:
        try:
            json.loads(last)
            rep["last_line_ok"] = True
        except json.JSONDecodeError:
            rep["last_line_ok"] = False
    rep["dup_tickers"] = sum(v - 1 for v in seen.values() if v > 1)
    rep["n_events"] = len(events)
    if closes:
        closes.sort()
        rep["first_close"] = closes[0]
        rep["last_close"] = closes[-1]
    return rep


def main():
    files = sorted(glob.glob(os.path.join(ROOT, "*.jsonl")))
    print(f"validating {len(files)} files\n")
    allrep = []
    for p in files:
        r = validate(p)
        allrep.append(r)
        ok = (r["parse_errors"] == 0 and r["last_line_ok"]
              and r["dup_tickers"] == 0 and not r["missing_field"])
        print(f"{'OK  ' if ok else 'FAIL'} {r['file']:<16} "
              f"lines={r['lines']:>7} events={r['n_events']:>6} "
              f"parse_err={r['parse_errors']:>4} "
              f"last_ok={str(r['last_line_ok']):<5} "
              f"dups={r['dup_tickers']:>7} "
              f"bad_result={r['bad_result']:>6} "
              f"exp_val={r['expiration_value_ok']:>7}/"
              f"{r['expiration_value_ok']+r['expiration_value_missing']}")
        if r["missing_field"]:
            print(f"       missing: {dict(r['missing_field'])}")
        print(f"       {str(r['first_close'])[:16]} -> "
              f"{str(r['last_close'])[:16]}")

    with open(os.path.join(ROOT, "validation.json"), "w") as f:
        json.dump(allrep, f, indent=2, default=str)


if __name__ == "__main__":
    main()
