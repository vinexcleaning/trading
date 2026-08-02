"""Are the shortlist candidates actually being recorded?

Operating rule for this session: a family that reaches the shortlist starts
recording immediately, because depth accrues in wall-clock time and cannot be
backfilled. That rule is worthless if the recorder's top-85-by-trades ranking
happens to exclude a family the analysis later wants.
"""
import glob
import json
import os
from collections import Counter

ROOT = os.path.join(os.path.dirname(__file__), "..")
WANT = ["KXMLBGAME", "KXMLBTOTAL", "KXMLBSPREAD", "KXMLBRFI", "KXMLBF5",
        "KXMLBF5TOTAL", "KXMLBTEAMTOTAL", "KXMLBKS", "KXMLBHR", "KXMLBHIT",
        "KXMLBTB", "KXMLBHRR", "KXMLBEXTRAS",
        "KXITFMATCH", "KXITFWMATCH", "KXATPCHALLENGERMATCH",
        "KXWTACHALLENGERMATCH", "KXATPMATCH", "KXWTAMATCH",
        "KXLIGAMXGAME", "KXLIGAMXTOTAL", "KXARGPREMDIVGAME",
        "KXCOPADOBRASILGAME", "KXMLSGAME", "KXDIMAYORGAME",
        "KXNPBGAME", "KXNPBTOTAL", "KXKBOGAME", "KXBTCD"]

c = Counter()
for f in glob.glob(os.path.join(ROOT, "data", "depth_broad", "*", "*",
                                "depth.jsonl")):
    with open(f, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                c[json.loads(line).get("series")] += 1
            except json.JSONDecodeError:
                pass

print(f"recorder covers {len(c)} series, {sum(c.values()):,} rows\n")
print("series                       rows  covered?")
missing = []
for s in WANT:
    n = c.get(s, 0)
    if n == 0:
        missing.append(s)
    print(f"{s:26s} {n:6d}  " + ("YES" if n else "*** NOT RECORDED ***"))
print(f"\nMISSING ({len(missing)}): {missing}")
