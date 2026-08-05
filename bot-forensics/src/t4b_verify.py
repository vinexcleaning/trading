"""
t4b_verify.py - verify the two GitHub findings that would change a decision.

1. `livetennisapi/*` - eleven client libraries, all pushed in the last two
   days, every description claiming ATP + WTA + Challenger + **ITF**. If that
   is real and reachable it reopens the ITF thread, which this repo closed on
   data availability rather than on economics. Claimed coverage in a README is
   an ADVOCACY signal, not a corroboration - the vendor wrote it. So: read the
   README, find the base URL, and hit it.

2. `Aneeshers/tennis-sackmann-archive` - "Archival mirror of Jeff Sackmann's
   tennis datasets". STATUS.md states "Sackmann upstream is 404; this runs on a
   frozen mirror ending 2026-06-02" and treats kalshi-tennis/data as
   irreplaceable partly for that reason. Both halves are checkable.
"""
from __future__ import annotations
import sys, os, json, base64, re, time
SG = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "..", "..", "signal-github", "src"))
sys.path.insert(0, SG)
import gh
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")


def readme(fn):
    for path in ("README.md", "readme.md", "README.rst"):
        try:
            r = gh.raw(fn, path)
            if r:
                return r if isinstance(r, str) else r.decode("utf-8", "ignore")
        except Exception:
            pass
    return ""


def head(url, timeout=20):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(4000)
            return r.status, body.decode("utf-8", "ignore")[:1500]
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


print("=" * 78)
print("1. livetennisapi - is the ITF coverage real, and is it free?")
print("=" * 78)
for fn in ("livetennisapi/livetennisapi-go",
           "livetennisapi/livetennisapi-dify-plugin"):
    print(f"\n--- {fn}")
    md = readme(fn)
    print(f"README {len(md)} chars")
    urls = sorted(set(re.findall(r"https?://[a-zA-Z0-9._/\-]+", md)))
    base = [u for u in urls if "livetennis" in u.lower() or "api" in u.lower()]
    print("URLs mentioned:", base[:14])
    for kw in ("ITF", "free", "Free", "pricing", "Pricing", "API key",
               "api_key", "RapidAPI", "rate limit", "tier"):
        hits = [ln.strip() for ln in md.splitlines() if kw in ln][:3]
        for h in hits:
            print(f"    [{kw}] {h[:170]}")

for probe in ("https://api.livetennisapi.com/v1/matches/live",
              "https://livetennisapi.com/",
              "https://www.livetennisapi.com/pricing"):
    st, body = head(probe)
    print(f"\nGET {probe}\n  -> {st}  {body[:400]}")
    time.sleep(1)

print()
print("=" * 78)
print("2. Sackmann: is the upstream really 404, and is the mirror real?")
print("=" * 78)
for fn in ("JeffSackmann/tennis_atp", "JeffSackmann/tennis_wta",
           "JeffSackmann/tennis_MatchChartingProject",
           "JeffSackmann/tennis_slam_pointbypoint",
           "Aneeshers/tennis-sackmann-archive"):
    try:
        r = gh.core(f"/repos/{fn}")
    except Exception as e:
        r = None
        print(f"{fn:48s} ERROR {e}")
        continue
    if not r:
        print(f"{fn:48s} 404 / not returned")
    else:
        print(f"{fn:48s} OK  pushed {r.get('pushed_at')}  "
              f"stars {r.get('stargazers_count')}  "
              f"archived {r.get('archived')}  size {r.get('size')}kb")
    time.sleep(0.4)

print()
print("=" * 78)
print("3. The Kalshi-tennis crowd: how many others are building this bot?")
print("=" * 78)
raw = json.load(open(os.path.join(OUT, "t4_github_raw.json"), encoding="utf-8"))
seen = {}
for q in ("kalshi tennis", "polymarket tennis"):
    for r in raw["Q1_inplay_strategy"].get(q, []):
        if r.get("full_name"):
            seen[r["full_name"]] = r
import datetime as dt
now = dt.datetime(2026, 8, 5, tzinfo=dt.timezone.utc)
rows = []
for fn, r in seen.items():
    try:
        created = dt.datetime.fromisoformat(r["created"].replace("Z", "+00:00"))
        pushed = dt.datetime.fromisoformat(r["pushed"].replace("Z", "+00:00"))
    except Exception:
        continue
    rows.append((fn, (now - created).days, (now - pushed).days, r["stars"],
                 (r.get("desc") or "")[:90]))
rows.sort(key=lambda z: z[1])
print(f"{len(rows)} distinct Kalshi/Polymarket tennis repos")
print(f"{'repo':50s} {'age_d':>6s} {'stale_d':>8s} {'*':>4s}")
for fn, a, s, st_, d in rows:
    print(f"{fn[:50]:50s} {a:6d} {s:8d} {st_:4d}  {d}")
fresh = [r for r in rows if r[1] <= 180]
print(f"\ncreated within the last 180 days: {len(fresh)} of {len(rows)}")
print(f"total stars across all of them: {sum(r[3] for r in rows)}")
