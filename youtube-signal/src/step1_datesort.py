"""STEP 1 (gating) -- can keyless yt-dlp return date-ordered or date-filtered search?

Tests three mechanisms against a relevance baseline, then VERIFIES by pulling real
upload dates and checking the ordering/filtering actually holds. A variant that
merely returns results is not a pass.

YouTube encodes search filters in the `sp=` query parameter (a base64 protobuf).
The tokens tested here:
    CAI=        sort by upload date
    EgIIBQ==    filter: this year (relevance order)
    CAISAggF    filter: this year AND sort by upload date

yt-dlp's YoutubeSearchURLIE handles /results?search_query=...&sp=..., so these ride
through with no API key and no quota.
"""

import datetime as dt
import json
import sys
import time
import urllib.parse
from pathlib import Path

from yt_dlp import YoutubeDL

ROOT = Path(__file__).resolve().parent.parent
TODAY = dt.date(2026, 8, 2)
QUERIES = ["kalshi api python", "polymarket clob api", "how to build a trading bot"]
TOP_N = 25
DATE_SAMPLE = 10  # how many of the top results to pull real upload dates for

VARIANTS = {
    "relevance_baseline": None,
    "sort_by_date": "CAI%3D",
    "filter_this_year": "EgIIBQ%3D%3D",
    "filter_year_sort_date": "CAISAggF",
}

_FLAT = {"quiet": True, "skip_download": True, "extract_flat": True, "no_warnings": True}


def search(query, sp=None, n=TOP_N):
    """Return flat entries. sp=None uses the plain ytsearch: form."""
    if sp is None:
        url = f"ytsearch{n}:{query}"
        opts = dict(_FLAT)
    else:
        q = urllib.parse.quote_plus(query)
        url = f"https://www.youtube.com/results?search_query={q}&sp={sp}"
        opts = dict(_FLAT, playlistend=n)
    t0 = time.time()
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    entries = [e for e in (info.get("entries") or []) if e and e.get("id")]
    return entries, round(time.time() - t0, 1)


def upload_dates(video_ids):
    """Real upload dates. extract_flat does not carry upload_date, so this needs a
    full extraction per video -- the only way to actually verify the claim."""
    out = {}
    opts = {"quiet": True, "skip_download": True, "no_warnings": True}
    with YoutubeDL(opts) as ydl:
        for vid in video_ids:
            try:
                info = ydl.extract_info(
                    f"https://www.youtube.com/watch?v={vid}", download=False
                )
                ud = info.get("upload_date")
                out[vid] = dt.datetime.strptime(ud, "%Y%m%d").date() if ud else None
            except Exception:  # noqa: BLE001
                out[vid] = None
            time.sleep(1.5)
    return out


def monotonic_report(dates):
    """How well is this ordered newest-first?"""
    seq = [d for d in dates if d]
    if len(seq) < 2:
        return None
    pairs = list(zip(seq, seq[1:]))
    ok = sum(1 for a, b in pairs if a >= b)
    return {
        "n_dated": len(seq),
        "adjacent_pairs": len(pairs),
        "non_increasing_pairs": ok,
        "frac_ordered": round(ok / len(pairs), 3),
        "strictly_ordered": ok == len(pairs),
        "newest": seq[0].isoformat(),
        "oldest": seq[-1].isoformat(),
    }


def main():
    findings = {}
    for query in QUERIES:
        print("\n" + "=" * 74)
        print(f"QUERY: {query!r}")
        print("=" * 74)
        findings[query] = {}
        for name, sp in VARIANTS.items():
            try:
                entries, secs = search(query, sp)
            except Exception as exc:  # noqa: BLE001
                print(f"\n  {name:<24} EXTRACTION FAILED {type(exc).__name__}: "
                      f"{str(exc).strip().splitlines()[0][:100]}")
                findings[query][name] = {"ok": False, "error": str(exc)[:200]}
                continue

            ids = [e["id"] for e in entries[:DATE_SAMPLE]]
            dates = upload_dates(ids)
            ordered = [dates[i] for i in ids]
            mono = monotonic_report(ordered)
            ages = [(TODAY - d).days / 30.44 for d in ordered if d]

            print(f"\n  {name:<24} {len(entries):>3} results in {secs}s")
            for i, vid in enumerate(ids):
                d = dates[vid]
                age = f"{(TODAY - d).days / 30.44:5.1f} mo" if d else "     ?  "
                title = (entries[i].get("title") or "")[:44]
                print(f"      {i:>2}. {d if d else '????-??-??'}  {age}  {title}")
            if mono:
                print(f"      -> newest-first in {mono['non_increasing_pairs']}/"
                      f"{mono['adjacent_pairs']} adjacent pairs "
                      f"(frac {mono['frac_ordered']}), "
                      f"strictly ordered: {mono['strictly_ordered']}")
            if ages:
                within12 = sum(1 for a in ages if a <= 12)
                print(f"      -> within 12 months: {within12}/{len(ages)}, "
                      f"max age {max(ages):.1f} mo")

            findings[query][name] = {
                "ok": True,
                "n_results": len(entries),
                "seconds": secs,
                "ordering": mono,
                "within_12mo": sum(1 for a in ages if a <= 12),
                "n_dated": len(ages),
                "max_age_months": round(max(ages), 1) if ages else None,
                "video_ids": [e["id"] for e in entries],
            }
            time.sleep(2)

    out = ROOT / "reports" / "step1_datesort.json"
    out.write_text(json.dumps(findings, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {out}")

    # ---- verdict ----
    print("\n" + "=" * 74)
    print("VERDICT")
    print("=" * 74)
    for name in VARIANTS:
        rows = [findings[q].get(name) for q in QUERIES]
        rows = [r for r in rows if r and r.get("ok")]
        if not rows:
            print(f"  {name:<24} ALL EXTRACTIONS FAILED")
            continue
        fracs = [r["ordering"]["frac_ordered"] for r in rows if r.get("ordering")]
        strict = sum(1 for r in rows if r.get("ordering", {}).get("strictly_ordered"))
        filt = [f"{r['within_12mo']}/{r['n_dated']}" for r in rows]
        avg = f"{sum(fracs)/len(fracs):.3f}" if fracs else "n/a"
        print(f"  {name:<24} mean frac newest-first {avg} | "
              f"strictly ordered {strict}/{len(rows)} queries | within-12mo {filt}")


if __name__ == "__main__":
    main()
