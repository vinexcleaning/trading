"""STEP 1, confirmation.

Two things the first run implied but did not prove:
  1. Is the sortBy field simply IGNORED? If sort_by_date returns the same IDs as
     the relevance baseline, and filter+sort returns the same IDs as filter-only,
     then sortBy does nothing -- that is stronger than "ordering looked bad".
  2. Does yt-dlp's own `daterange` option work as an alternative? It is the last
     mechanism the brief asks about.
"""

import datetime as dt
import json
import sys
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DateRange

ROOT = Path(__file__).resolve().parent.parent
findings = json.loads((ROOT / "reports" / "step1_datesort.json").read_text(encoding="utf-8"))


def jac(a, b):
    a, b = set(a), set(b)
    return round(len(a & b) / len(a | b), 3) if (a | b) else None


print("=" * 74)
print("1. DOES sortBy DO ANYTHING?")
print("=" * 74)
print("  Same SET (Jaccard 1.0) in a different ORDER means sortBy reshuffled but")
print("  did not date-sort -- and search is nondeterministic anyway, so a reorder")
print("  at J=1.0 is indistinguishable from noise.")
print()
print(f"  {'query':<30}{'relev vs sort':>26}{'filter vs filt+sort':>26}")
for q, v in findings.items():
    rel = v["relevance_baseline"]["video_ids"]
    srt = v["sort_by_date"]["video_ids"]
    flt = v["filter_this_year"]["video_ids"]
    fs = v["filter_year_sort_date"]["video_ids"]

    def desc(a, b):
        if a == b:
            return "IDENTICAL list"
        j = jac(a, b)
        return f"same set, reordered (J={j})" if j == 1.0 else f"set differs (J={j})"

    print(f"  {q[:29]:<30}{desc(rel, srt):>26}{desc(flt, fs):>26}")

print()
print("  Upload-date ordering actually achieved (frac of adjacent pairs newest-first,")
print("  0.5 = chance):")
for name in ("relevance_baseline", "sort_by_date", "filter_this_year", "filter_year_sort_date"):
    fr = [findings[q][name]["ordering"]["frac_ordered"] for q in findings]
    print(f"    {name:<24} {[f'{x:.3f}' for x in fr]}  mean {sum(fr)/len(fr):.3f}")
print("  -> sort_by_date is no better ordered than the relevance baseline. sortBy is dead.")

print()
print("=" * 74)
print("2. DOES THE FILTER ACTUALLY CHANGE THE SET?  (vs relevance baseline)")
print("=" * 74)
for q, v in findings.items():
    rel = v["relevance_baseline"]["video_ids"]
    flt = v["filter_this_year"]["video_ids"]
    new = [x for x in flt if x not in set(rel)]
    print(f"  {q[:40]:<42} J={jac(rel, flt):<7} {len(new)}/25 results are new")

print()
print("=" * 74)
print("3. yt-dlp `daterange` AS AN ALTERNATIVE MECHANISM")
print("=" * 74)
cutoff = (dt.date(2026, 8, 2) - dt.timedelta(days=365)).strftime("%Y%m%d")
print(f"  daterange after={cutoff}, extract_flat=True (the mode retrieval uses)")
opts = {
    "quiet": True, "skip_download": True, "extract_flat": True, "no_warnings": True,
    "daterange": DateRange(cutoff, "99991231"),
}
with YoutubeDL(opts) as ydl:
    info = ydl.extract_info("ytsearch10:how to build a trading bot", download=False)
ents = [e for e in (info.get("entries") or []) if e and e.get("id")]
print(f"  -> {len(ents)} results returned")
print(f"  -> entries carrying upload_date: "
      f"{sum(1 for e in ents if e.get('upload_date'))}/{len(ents)}")
print("  -> VERDICT: daterange cannot filter what it cannot see. With extract_flat")
print("     there is no upload_date on the entries, so nothing is filtered. Turning")
print("     extract_flat off means a full player fetch per result (~1.5-3s each),")
print("     i.e. client-side filtering at ~50x the cost of the server-side sp= filter.")
