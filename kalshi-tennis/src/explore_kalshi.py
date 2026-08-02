"""Look at the shape of the Kalshi tennis markets before parsing them properly."""
import json
import pathlib
import re
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "data" / "kalshi" / "tennis_markets.json").read_text(encoding="utf-8"))

for series, rows in data.items():
    if not rows:
        continue
    print("=" * 78)
    print(f"{series}: {len(rows)} markets")
    print("=" * 78)

    events = Counter(m["event_ticker"] for m in rows)
    print(f"  events: {len(events)}   markets/event: {Counter(events.values())}")

    dates = sorted(m["open_time"][:10] for m in rows)
    print(f"  open_time range: {dates[0]} .. {dates[-1]}")

    subtitles = sum(1 for m in rows if m.get("yes_sub_title"))
    print(f"  with yes_sub_title: {subtitles}/{len(rows)}")

    # tournament phrasing in the rules
    pat = re.compile(r"the (\d{4} .+?) (?:Round|Quarter|Semi|Final|Match)", re.I)
    tours = Counter()
    for m in rows[:4000]:
        g = pat.search(m.get("rules_primary", "") or "")
        if g:
            tours[g.group(1)] += 1
    print(f"  sample tournament strings ({len(tours)} distinct):")
    for t, c in tours.most_common(8):
        print(f"     {c:5d}  {t}")

    print("  sample rules_primary:")
    print("     " + (rows[0].get("rules_primary", "")[:220]))
    print(f"  sample result values: {Counter(m.get('result','') for m in rows).most_common(6)}")
    print()
