"""INPUT OVERLAP - how different is the INFORMATION each candidate reads?

Mailbox 012: "rank your candidates by how DIFFERENT the information they use
is, not by how promising they look."

⚠ THIS IS NOT THE OVERLAP THEY WILL MEASURE, AND THE DIFFERENCE MATTERS.
`mlb-paper` will compute the share of games two bots enter on the SAME SIDE,
which is tennis's 0.149 median. That number cannot exist before the bots run.

What CAN be computed today is whether two strategies read the same inputs, and
that is a bound rather than an estimate: two strategies reading disjoint inputs
cannot be near-copies, while two reading identical inputs may or may not be,
depending on the instrument. So a 0 here is evidence and a 1 here is a warning,
and neither is the entry overlap.

Instrument tags ("instrument: first five innings") are EXCLUDED from the
comparison. The market traded is not information about the game, and counting
it would make two bots look different for reading the same facts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The five live mentalities, read off mlb-paper/src/mentalities.py on
# 2026-09-03 - the docstrings and the module constants, not a summary of them.
LIVE = {
    "starter":  {"starting pitcher recent form"},
    "park-air": {"wind and temperature", "park run factor"},
    "bullpen":  {"bullpen usage"},
    "early":    {"team season record", "home field",
                 "starting pitcher season line"},
    "lineup":   {"lineup absences"},
}


def axes(spec):
    return {a for a in spec.get("information_axes", [])
            if not a.startswith("instrument:")}


def jac(a, b):
    return len(a & b) / len(a | b) if (a | b) else 0.0


def main():
    specs = []
    for p in sorted((ROOT / "specs").glob("SF2*.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        specs.append(s)
    specs.sort(key=lambda s: s["mlb_rank"])
    names = list(LIVE)
    print("%-7s %-5s %s   %s" % ("spec", "rank",
                                 "  ".join("%-8s" % n[:8] for n in names),
                                 "worst"))
    for s in specs:
        a = axes(s)
        vals = [jac(a, LIVE[n]) for n in names]
        print("%-7s %-5d %s   %.2f  %s"
              % (s["id"], s["mlb_rank"],
                 "  ".join("%-8.2f" % v for v in vals), max(vals),
                 s.get("paired_with") or "-"))
    print()
    print("PAIRWISE, AMONG THE TEN RECOMMENDED - are they near-copies of each "
          "OTHER?")
    ten = [s for s in specs if s["mlb_rank"] <= 10]
    print("%-7s %s" % ("", " ".join("%-6s" % x["id"][-3:] for x in ten)))
    worst = (0.0, None)
    for a in ten:
        row = []
        for b in ten:
            v = 0.0 if a is b else jac(axes(a), axes(b))
            row.append(v)
            if a is not b and v > worst[0]:
                worst = (v, (a["id"], b["id"]))
        print("%-7s %s" % (a["id"], " ".join("%-6.2f" % v for v in row)))
    print("highest pair among the ten: %.2f  %s" % worst)
    print()
    print("WARNING - WHAT THIS TABLE CANNOT SEE. Two specs can read different FACTS "
          "off the SAME DOCUMENT at the same moment - SF203 and SF207 both "
          "wait for the posted batting order - and this measure scores them "
          "0.00 because the facts differ. They will still fire on the same "
          "games. Only the forward test settles that.")


    print("worst = the highest input overlap with any live bot. 0.00 means it "
          "reads nothing any live bot reads.")
    print("last column = the bot it is PAIRED-TESTABLE against, which is a "
          "deliberate high overlap, not an accident.")


if __name__ == "__main__":
    main()
