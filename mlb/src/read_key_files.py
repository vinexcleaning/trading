"""Read the specific files that carry honest validation, not marketing.

sharprfi's README has a "Variant | Brier | Calibration gap" table -- that is
the only number in any of these repos that could tell us whether a
first-inning model actually works.

phatcobra has guards.py, grade_nightly.py and audit_monthly.py, i.e. someone
who thought about validation rather than just fitting. Their feature list and
their grading approach are both worth having.
"""
import base64
import os
import re

import requests

UA = {"User-Agent": "Mozilla/5.0 (mlb-research/1.0)"}
REP = os.path.join(os.path.dirname(__file__), "..", "reports")


def raw(full, path):
    r = requests.get(f"https://raw.githubusercontent.com/{full}/HEAD/{path}",
                     headers=UA, timeout=45)
    return r.text if r.status_code == 200 else None


print("=" * 72)
print("sharprfi README -- the performance table and the model description")
print("=" * 72)
r = requests.get("https://api.github.com/repos/lucasreydman/sharprfi/readme",
                 headers=UA, timeout=45)
if r.status_code == 200:
    md = base64.b64decode(r.json()["content"]).decode("utf-8", "replace")
    lines = md.split("\n")
    # print any markdown table containing Brier, plus surrounding context
    for i, l in enumerate(lines):
        if re.search(r"brier|calibration|variant", l, re.I):
            for j in range(max(0, i - 4), min(len(lines), i + 12)):
                print("  " + lines[j][:130])
            print("  " + "-" * 60)
            break
    # the model section
    for i, l in enumerate(lines):
        if re.search(r"^#+\s*(model|method|how it works|approach)", l, re.I):
            for j in range(i, min(len(lines), i + 28)):
                print("  " + lines[j][:130])
            break

print("\n" + "=" * 72)
print("phatcobra/nrfi-predictor -- guards and grading")
print("=" * 72)
for f in ("nrfi/guards.py", "nrfi/grade_nightly.py", "nrfi/build_features.py"):
    t = raw("phatcobra/nrfi-predictor", f)
    if not t:
        print(f"\n  {f}: unavailable")
        continue
    print(f"\n--- {f} ({len(t)} chars) ---")
    # show the docstring and any function definitions
    head = t[:1400]
    print("\n".join("  " + x[:120] for x in head.split("\n")[:32]))
    defs = re.findall(r"^\s*def\s+(\w+)\s*\(", t, re.M)
    print(f"  functions: {defs[:20]}")

print("\n" + "=" * 72)
print("phatcobra feature list")
print("=" * 72)
t = raw("phatcobra/nrfi-predictor", "nrfi/build_features.py")
if t:
    cols = sorted(set(re.findall(r"[\"']([a-z0-9_]{3,40})[\"']", t)))
    interesting = [c for c in cols if any(
        s in c for s in ("era", "whip", "woba", "ops", "obp", "slg", "k_",
                         "bb_", "pitch", "bat", "run", "inning", "hard",
                         "barrel", "temp", "wind", "park", "rest", "lineup",
                         "hand", "split", "avg", "rate", "pct", "xwoba"))]
    print(f"  {len(interesting)} candidate feature names:")
    for i in range(0, len(interesting), 6):
        print("    " + ", ".join(interesting[i:i + 6]))

print("\n" + "=" * 72)
print("dbasley first-inning Statcast CSVs -- are they usable?")
print("=" * 72)
for f in ("statcast_2023_first_inning.csv", "statcast_2024_first_inning.csv"):
    r = requests.get(
        f"https://raw.githubusercontent.com/dbasley/NRFI_Project/HEAD/{f}",
        headers=UA, timeout=90)
    if r.status_code != 200:
        print(f"  {f}: http {r.status_code}")
        continue
    lines = r.text.split("\n")
    print(f"  {f}: {len(lines)-1} rows, {len(r.content):,} bytes")
    print(f"    header: {lines[0][:200]}")
