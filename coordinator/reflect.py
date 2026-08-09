"""The mechanical half of the Critic. Scans a draft for the wording that has
actually preceded a wrong claim in this repo.

WHAT THIS CANNOT DO, and it is most of the job
----------------------------------------------
* **It cannot judge reasoning.** It matches phrasing. A perfectly-worded claim
  built on one bad source passes clean.
* **It cannot tell you what you failed to consider.** The narrowing failure --
  fixing on one price, one minute, one league -- leaves no trace in the text.
  That is what `REFLECT.md`'s checklist is for and it needs a mind.
* **A clean run is not a pass.** It means nothing matched a pattern that has
  burned this repo before.

What it IS good at: absence claims. Eight of the nine errors recorded in
`REFLECT.md` came from reading one source and concluding, and three of those
were sentences containing "no" or "only". Those have a shape.

No network. No credentials. Reads one file.

Usage
-----
  py -3 coordinator\\reflect.py --file draft.md
  py -3 coordinator\\reflect.py --checklist
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECKLIST = HERE / "REFLECT.md"

# Each rule: (name, regex, what went wrong last time, what to do about it)
RULES = [
    (
        "ABSENCE CLAIM",
        r"\b(there (?:is|are|was|were) no|has no|have no|no such|does not exist|"
        r"doesn't exist|never (?:been|had|has)|nothing (?:in|on|at)|not available|"
        r"cannot be found|none (?:of|exist))\b",
        "Three of the nine recorded errors were absence claims and all three "
        "were wrong. 'Kalshi has no Champions League' came from one 69-day "
        "window that landed in the European off-season.",
        "Name the source that WOULD have shown it if it existed, and say "
        "whether that source was actually consulted.",
    ),
    (
        "ONLY / EXCLUSIVE",
        r"\b(only|solely|exclusively|the sole|nothing but|purely)\b",
        "'Kalshi soccer is mostly friendlies' -- 139 of 210 -- was one tape "
        "covering the international break before the World Cup.",
        "Say what the sample was and over what dates, in the same sentence.",
    ),
    (
        "READ, NOT RUN",
        r"\b(the script (?:says|shows|contains)|reading (?:it|the code|the script)|"
        r"looking at the (?:code|script)|does not (?:contain|include|have) a? ?flag)\b",
        "install.ps1 was read for an elevation flag, none was found, and it was "
        "reported as needing no administrator. Registering the task was denied.",
        "Run it, or say plainly that it was not run.",
    ),
    (
        "NUMBER WITH NO DATE",
        r"(?<![\w.])\d[\d,]*(?:\.\d+)?\s?(?:%|c\b|¢|cents|dollars|\$)",
        "A number without the dates it covers reads as a fact about today. "
        "The 4.8c cost bar was true for tennis at middling prices and wrong by "
        "20x at 97c.",
        "Attach the dates measured over, and where the number came from.",
    ),
    (
        "CARRIED NUMBER",
        r"\b(the (?:usual|standard|normal|habitual) (?:cost|bar|fee|rate)|"
        r"as (?:always|usual)|the \d[\d.]* ?(?:c|¢|cent)? (?:cost )?bar)\b",
        "A threshold true in one project applied to another. The 481-settlement "
        "bar is a weather-market capacity number and was nearly applied to "
        "soccer as a statistical power number.",
        "Recompute it for THIS case, or say which project it came from.",
    ),
    (
        "JARGON",
        r"\b(pp\b|bps\b|CI\b|p-value|MDE\b|Brier|holdout|clustered|monotonic|"
        r"residual|sigma|variance|n\s?=\s?\d|t\s?=\s?[\d.-]|z\s?=\s?[\d.+-])",
        "He said directly that language he cannot follow stops him putting his "
        "own knowledge in -- and his knowledge is the one input we cannot "
        "generate.",
        "Say it in money, or say it out of 100. CLAUDE.md section 1.",
    ),
    (
        "SINGLE SOURCE",
        r"\b(according to|per the|the (?:file|document|note|report) says|"
        r"it says|as recorded in|the handoff (?:said|says))\b",
        "The 97-cents figure came from an illustration in a handoff note and "
        "silently became the definition of the strategy.",
        "Is this the only place it appears? If yes, say so in the report.",
    ),
    (
        "CERTAINTY",
        r"\b(obviously|clearly|of course|certainly|definitely|without doubt|"
        r"it is clear that|proves)\b",
        "Every one of the nine recorded errors was stated confidently. Not one "
        "was hedged and then wrong.",
        "Replace with what was measured and how much of it.",
    ),
]

REFEREE_FORM = """==========================================================================
THE REFEREE -- three lists, and the third one is not optional
==========================================================================

  The Critic attacked it. Now say what actually survives. Nothing else goes
  in here: no summary, no restatement, no "on balance". Three lists.

1. STANDS
   Survived the attack. For each: the claim, and the ONE thing that makes it
   survive -- the sample, the second source, the arithmetic.

   -

2. DOWNGRADED
   Still true but weaker than it was written. For each: the old wording, the
   NEW wording, and what forced the change. Rewrite it here, do not just
   note that it needs rewriting.

   - was:
     now:
     because:

3. FOR THE USER -- genuinely unresolved
   Where the work and the attack disagree and neither wins on evidence.
   State BOTH positions fairly enough that he can pick without reading
   either in full.

   - the question:
     one side says:
     the other says:
     what would settle it:

--------------------------------------------------------------------------
  THE REFEREE NEVER RESOLVES A REAL DISAGREEMENT. That is his, and it is the
  reason he asked for this. An empty list 3 means you checked and found none
  -- say that out loud rather than leaving it blank.
"""

NEGATIVE_RESULT = re.compile(
    r"\b(no edge|does not work|doesn't work|found nothing|null result|"
    r"not profitable|fails to|no effect)\b", re.I)
DID_NOT_TEST = re.compile(
    r"\b(did not test|not tested|untested|what (?:was|we) did not|"
    r"versions not tried|out of scope)\b", re.I)


def scan(text: str) -> list[tuple[str, int, str, str, str]]:
    out = []
    lines = text.splitlines()
    for n, line in enumerate(lines, 1):
        if line.strip().startswith(("#", "|", ">", "-", "*")) and len(line) < 12:
            continue
        for name, pattern, why, fix in RULES:
            m = re.search(pattern, line, re.I)
            if m:
                out.append((name, n, m.group(0), why, fix))
    return out


def wrap(text: str, indent: str, width: int = 74) -> str:
    words, cur, rows = text.split(), "", []
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            rows.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        rows.append(cur)
    return ("\n" + indent).join(rows)


def _ascii_safe_console():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main() -> int:
    _ascii_safe_console()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", help="the draft to scan")
    ap.add_argument("--checklist", action="store_true",
                    help="print the part a script cannot do")
    ap.add_argument("--referee", action="store_true",
                    help="print the three lists the Referee owes, as a form")
    a = ap.parse_args()

    if a.referee:
        print(REFEREE_FORM)
        return 0
    if a.checklist or not a.file:
        if CHECKLIST.exists():
            print(CHECKLIST.read_text(encoding="utf-8"))
            return 0
        sys.exit("coordinator/REFLECT.md is missing -- it is the actual checklist.")

    text = Path(a.file).read_text(encoding="utf-8", errors="replace")
    hits = scan(text)

    print("=" * 74)
    print("THE MECHANICAL HALF OF THE CRITIC")
    print("=" * 74)
    print()
    print(wrap("This finds WORDING that has preceded a wrong claim in this repo "
               "before. It cannot judge reasoning and it cannot see what you "
               "failed to consider -- which is the failure that matters most. "
               "A clean run is not a pass.", "  "))
    print()

    by_rule: dict[str, list] = {}
    for name, n, hit, why, fix in hits:
        by_rule.setdefault(name, []).append((n, hit, why, fix))

    if not by_rule:
        print("  Nothing matched. Now do the part that needs a mind:")
        print("  py -3 coordinator\\reflect.py --checklist")
    for name in sorted(by_rule, key=lambda k: -len(by_rule[k])):
        rows = by_rule[name]
        _, _, why, fix = rows[0]
        print(f"  {name}  --  {len(rows)} place(s)")
        print("      " + wrap(f"Last time: {why}", "      "))
        print("      " + wrap(f"Do this:   {fix}", "      "))
        for n, hit, _, _ in rows[:6]:
            print(f"        line {n}: ...{hit}...")
        if len(rows) > 6:
            print(f"        ...and {len(rows) - 6} more")
        print()

    if NEGATIVE_RESULT.search(text) and not DID_NOT_TEST.search(text):
        print("  MISSING: this reads like a NEGATIVE RESULT and it does not say")
        print("      " + wrap("what was NOT tested. CLAUDE.md section 9c step 7 makes "
                              "that mandatory -- a dead idea with no such list looks "
                              "completely dead, and this repo has already killed a "
                              "live idea that way.", "      "))
        print()

    print("-" * 74)
    print(wrap("Now run the checklist, which is the half that matters: "
               "py -3 coordinator\\reflect.py --checklist", "  "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
