"""Dimension E (settlements per week) + the recorder content audit.

E matters because it bounds what can ever be validated. LEDGER S021: the tennis
line needs n approximately 3,970 events for a 2c edge and accrues ~1,900
matches/week, so it is resolvable. A family settling 20 times a year can never
be validated however attractive it looks on A-D.

Settlements per week is computed two ways and both are reported, because they
disagree in an informative direction:
  (a) declared    -- the series `frequency` field
  (b) observed    -- markets whose close_time falls in the next 7 days,
                     counted at the EVENT level, not the market level

(b) is the one that matters. A ladder event with 60 strikes is ONE settlement
of one underlying, not 60 independent draws (GUARDS #8). Counting markets
would inflate crypto ladders ~60x against a tennis match.

The audit half re-checks the live recorder on CONTENT, not row counts, which is
the failure that has twice hidden empty writes in this project.
"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
import kalshi_api as K  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
NOW = datetime.now(timezone.utc)
WEEK = NOW + timedelta(days=7)


def main():
    series = json.load(open(os.path.join(DATA, "kalshi_series.json"),
                            encoding="utf-8"))
    ev_close = defaultdict(dict)     # series -> event -> earliest close
    mkt_ct = Counter()
    with open(os.path.join(DATA, "kalshi_markets_open.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            m = json.loads(line)
            s = K.series_of(m["ticker"])
            ct = m.get("close_time")
            if not ct:
                continue
            ev = m.get("event_ticker") or m["ticker"]
            prev = ev_close[s].get(ev)
            if prev is None or ct < prev:
                ev_close[s][ev] = ct
            mkt_ct[s] += 1

    lo, hi = NOW.isoformat(), WEEK.isoformat()
    rows = []
    for s, evs in ev_close.items():
        in_week = sum(1 for c in evs.values() if lo <= c <= hi)
        rows.append({
            "series": s,
            "frequency_declared": (series.get(s) or {}).get("frequency"),
            "open_markets": mkt_ct[s],
            "open_events": len(evs),
            "events_settling_7d": in_week,
            "markets_settling_7d": sum(
                1 for _ev, c in evs.items() if lo <= c <= hi),
        })
    rows.sort(key=lambda r: -r["events_settling_7d"])
    with open(os.path.join(REP, "settlements_per_week.json"), "w",
              encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)

    print(f"settlements in the 7 days from {NOW:%Y-%m-%d %H:%M} UTC")
    print(f"{'series':30s} {'freq':10s} {'mkts':>7s} {'events':>7s} "
          f"{'ev/7d':>7s}")
    for r in rows[:40]:
        print(f"{r['series'][:30]:30s} {str(r['frequency_declared'])[:10]:10s} "
              f"{r['open_markets']:7d} {r['open_events']:7d} "
              f"{r['events_settling_7d']:7d}")

    print("\n=== RECORDER CONTENT AUDIT (not a row count) ===")
    files = sorted(glob.glob(os.path.join(DATA, "depth_broad", "*", "*",
                                          "depth.jsonl")))
    tot = Counter()
    per_series = defaultdict(Counter)
    bad_examples = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    tot["torn_line"] += 1
                    continue
                tot["rows"] += 1
                s = d.get("series", "?")
                per_series[s]["rows"] += 1
                yes, no = d.get("yes") or [], d.get("no") or []
                if yes or no:
                    tot["nonempty"] += 1
                    per_series[s]["nonempty"] += 1
                yb, ya = d.get("yes_bid_c"), d.get("yes_ask_c")
                if yb is not None and ya is not None:
                    tot["two_sided"] += 1
                    per_series[s]["two_sided"] += 1
                    if ya < yb:
                        tot["crossed_book"] += 1
                        bad_examples.append(("crossed", d.get("ticker"), yb, ya))
                # content assertions
                for p, sz in yes + no:
                    if not (0.0 < p < 100.0):
                        tot["price_out_of_range"] += 1
                        bad_examples.append(("price", d.get("ticker"), p, sz))
                    if sz < 0:
                        tot["negative_size"] += 1
                if not d.get("ts") or not d.get("ticker"):
                    tot["missing_key_field"] += 1

    r = tot["rows"] or 1
    print(f"  files                {len(files)}")
    print(f"  rows                 {tot['rows']:,}")
    print(f"  torn/unparseable     {tot['torn_line']}")
    print(f"  non-empty            {tot['nonempty']:,}  ({100*tot['nonempty']/r:.1f}%)")
    print(f"  two-sided            {tot['two_sided']:,}  ({100*tot['two_sided']/r:.1f}%)")
    print(f"  price out of (0,100) {tot['price_out_of_range']}")
    print(f"  negative size        {tot['negative_size']}")
    print(f"  crossed book (ask<bid) {tot['crossed_book']}")
    print(f"  missing ts/ticker    {tot['missing_key_field']}")
    print(f"  distinct series      {len(per_series)}")
    verdict = ("PASS" if tot["rows"] > 200 and tot["nonempty"] / r > 0.5
               and tot["price_out_of_range"] == 0 and tot["torn_line"] == 0
               else "INVESTIGATE")
    print(f"\n  VERDICT: {verdict}")
    if bad_examples:
        print(f"  examples: {bad_examples[:5]}")

    print(f"\n  {'series':30s} {'rows':>6s} {'nonempty%':>10s} {'2sided%':>8s}")
    for s, c in sorted(per_series.items(), key=lambda x: -x[1]["rows"])[:25]:
        n = c["rows"] or 1
        print(f"  {s[:30]:30s} {c['rows']:6d} {100*c['nonempty']/n:10.1f} "
              f"{100*c['two_sided']/n:8.1f}")


if __name__ == "__main__":
    main()
