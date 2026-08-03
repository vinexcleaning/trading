"""Confirm 'Nates Tokens' (plural) and pull its stats + upload-date distribution.

Also measures premise 5 (the 18-month staleness cutoff) against the one channel
we care most about, since that is the cheapest place to see whether the cutoff
would discard useful material.
"""

import datetime as dt
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import channels  # noqa: E402

hits = channels.search_videos("Nates Tokens polymarket", n=10)
cid = next((h["channel_id"] for h in hits if h["channel"] == "Nates Tokens"), None)
print("resolved channel_id:", cid)
if not cid:
    raise SystemExit("could not resolve Nates Tokens")

st = channels.channel_stats(cid, cap=200)
print(f"name        : {st['channel']!r}")
print(f"subscribers : {st['subscribers']}")
print(f"uploads     : {st['upload_count']}{'+' if st['upload_count_is_floor'] else ''}")
print(f"median views: {st['median_views']}  (min {st['min_views']} / max {st['max_views']})")

# Upload dates need a non-flat pull; sample rather than fetch all 200.
print("\n=== upload-date sample (premise 5: is 18 months the right cutoff?) ===")
url = f"https://www.youtube.com/channel/{cid}/videos"
with channels._ydl({"playlistend": 40, "extract_flat": False}) as ydl:
    info = ydl.extract_info(url, download=False)

today = dt.date(2026, 8, 2)
ages, rows = [], []
for e in info.get("entries") or []:
    if not e:
        continue
    ud = e.get("upload_date")
    if not ud:
        continue
    d = dt.datetime.strptime(ud, "%Y%m%d").date()
    months = (today - d).days / 30.44
    ages.append(months)
    rows.append((d.isoformat(), round(months, 1), e.get("view_count"), (e.get("title") or "")[:44]))

for r in rows[:12]:
    print(f"  {r[0]}  {r[1]:>5.1f} mo  views={r[2]}  {r[3]}")
if ages:
    within = sum(1 for a in ages if a <= 18)
    print(f"\n  n={len(ages)} newest uploads sampled")
    print(f"  age months: median {statistics.median(ages):.1f}, "
          f"min {min(ages):.1f}, max {max(ages):.1f}")
    print(f"  within 18-month cutoff: {within}/{len(ages)} "
          f"({100*within/len(ages):.0f}%)")
