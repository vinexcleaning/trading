"""What soccer trading is inside the 2026-05-25..06-11 tape window?

The in-play question needs three things to line up: an event with an exact
timestamp (ESPN wallclock), a market that was trading at that moment, and
trade prints fine-grained enough to see a reaction. The tape has millisecond
stamps and 73.5M trades; this checks how much of it is soccer and which
fixtures are usable.

Read-only, local files only.
"""
import glob
import json
import os
import re
from collections import Counter, defaultdict

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
TAPE = os.path.join(ROOT, "market-selection", "data", "tape_pmxt_window")
REP = os.path.join(os.path.dirname(__file__), "..", "reports")
SOCCER = ("KXLIGAMXGAME", "KXARGPREMDIVGAME", "KXCOPADOBRASILGAME",
          "KXDIMAYORGAME", "KXMLSGAME", "KXUSLGAME", "KXNWSLGAME",
          "KXCLUBFGAME", "KXINTLFRIENDLYGAME", "KXLEAGUESCUPGAME",
          "KXPERLIGA1GAME", "KXECULPGAME", "KXURYPDGAME", "KXCHLLDPGAME")

per_series = Counter()
per_ticker = Counter()
files = sorted(glob.glob(os.path.join(TAPE, "trades_*.jsonl")))
print(f"{len(files)} tape day-files")
for f in files:
    day = os.path.basename(f)[7:17]
    n = 0
    with open(f, encoding="utf-8") as fh:
        for line in fh:
            # cheap prefilter before json parsing -- these files are ~1.3 GB
            if "KX" not in line:
                continue
            hit = None
            for s in SOCCER:
                if s in line:
                    hit = s
                    break
            if hit is None:
                continue
            try:
                t = json.loads(line)
            except ValueError:
                continue
            tk = t.get("ticker") or ""
            if not tk.startswith(hit):
                continue
            per_series[hit] += 1
            per_ticker[tk] += 1
            n += 1
    print(f"  {day}: {n:>7,} soccer trades", flush=True)

print(f"\n=== soccer trades in the window: {sum(per_series.values()):,} ===")
for s, n in per_series.most_common():
    print(f"  {s:24s} {n:>9,}")

print(f"\ndistinct soccer markets traded: {len(per_ticker):,}")
top = per_ticker.most_common(15)
print("busiest markets:")
for t, n in top:
    print(f"  {t[:52]:52s} {n:>8,}")

# how many distinct FIXTURES (events), and on which dates
ev = defaultdict(int)
for t, n in per_ticker.items():
    ev[t.rsplit("-", 1)[0]] += n
print(f"\ndistinct fixtures (events): {len(ev):,}")
dates = Counter()
for e in ev:
    m = re.search(r"-(\d\d)([A-Z]{3})(\d\d)", e)
    if m:
        dates[f"{m.group(2)}{m.group(3)}"] += 1
print(f"fixtures per date: {dict(sorted(dates.items()))}")

# fixtures with enough prints to see a reaction
busy = {e: n for e, n in ev.items() if n >= 200}
print(f"\nfixtures with >=200 trades (usable for an event study): {len(busy)}")
json.dump({"per_series": dict(per_series), "n_fixtures": len(ev),
           "usable_fixtures": len(busy),
           "busy": dict(sorted(busy.items(), key=lambda x: -x[1])[:200])},
          open(os.path.join(REP, "tape_soccer_scan.json"), "w"), indent=1)
print("\nwrote reports/tape_soccer_scan.json")
