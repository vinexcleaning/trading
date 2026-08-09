"""Screen every ledger row for the four ways a thread gets closed for the wrong
reason. This SORTS candidates for reading. It does not decide anything.

Why a screen and not just reading: 342 rows is readable, but "which nulls state
their own detection floor" is a question about the ABSENCE of a phrase, and
absence is the thing a human reader misses. GUARDS-style, the screen is the
canary and the reading is the verdict. Every flag it raises is read by hand
before it reaches REOPENED.md, and rows it does NOT flag are still read -- the
screen orders the reading, it does not replace it.

Four screens, matching the four categories in the tasking:

  BUG        the row's own text says a script was wrong, patched, or misparsed
  DATA       the closure rests on a source being missing, paywalled or dead
  NARROW     one arm/tier/venue/window tested, conclusion stated generally
  FLOOR      null language present, and NO statement of what the test could
             have detected. This is the one that cannot be spotted by reading
             for what is there, because the defect is what is not there.

READ ONLY. Writes nothing outside reopen/.

  py -3 reopen\\src\\screen_closures.py
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "coordinator"))

import ledger  # noqa: E402

OUT = HERE.parent / "reports"

# --- the screens ------------------------------------------------------------
# Written as word lists rather than one regex so that adding a word is a
# one-line diff a reader can check, which is the whole point of a canary.

NULL_WORDS = [
    r"\bnull\b", r"\bno edge\b", r"\bno effect\b", r"\bno signal\b",
    r"\bnothing\b", r"\bno model beats\b", r"\bdoes not exist\b",
    r"\bnot present\b", r"\bno .{0,20}bias\b", r"\b0 of \d", r"\bzero\b",
    r"\bnone\b", r"\bnot tradeable\b", r"\bcannot\b", r"\bno free\b",
    r"\bnot found\b", r"\bdead\b", r"\bkill", r"\bnot available\b",
    r"\bfails?\b", r"\bnegative\b", r"\bno-?go\b", r"\bdo not build\b",
]

# A row has stated its own floor if it says, in any wording, how big an effect
# the test could have seen. Missing this on a null is the D-category the
# tasking calls the largest and least visible.
FLOOR_WORDS = [
    r"\bMDE\b", r"minimum detectable", r"detection floor", r"\bpower\b",
    r"\bpowered\b", r"underpowered", r"could not have detected",
    r"\bn ?[≈~=] ?\d", r"needs? n", r"\bCI\b", r"\[.{0,12},", r"±",
    r"confidence", r"interval", r"\bse\b", r"standard error",
    r"too small", r"cannot resolve", r"not excluded", r"unevidenced",
]

BUG_WORDS = [
    r"\bbug\b", r"\bparse\b", r"\bmisparsed\b", r"\bkey that does not exist\b",
    r"\bfixed\b", r"\bpatched\b", r"\bregex\b", r"\bfield name\b",
    r"\bwrong column\b", r"\bread the wrong\b", r"\bdefect\b", r"\bbroken\b",
    r"\bfloating.point\b", r"\bmisclassif", r"\binverted\b", r"\bleak\b",
]

DATA_WORDS = [
    r"\b404\b", r"\b401\b", r"\b403\b", r"\bpaywall", r"\bfree tier\b",
    r"\bno free\b", r"\bnot found\b", r"\bdeleted\b", r"\bgone\b",
    r"\bunavailable\b", r"\bnot available\b", r"\bhard.cap", r"\brate limit\b",
    r"\bretention\b", r"\bcoverage\b", r"\bno data\b", r"\bno source\b",
    r"\bblocked\b", r"\bcredential", r"\bneeds a token\b", r"\bapify\b",
]

NARROW_WORDS = [
    r"\bone (market|series|day|snapshot|session|account|window|match|example)\b",
    r"\bsingle (market|series|day|snapshot|session|window|match|script)\b",
    r"\bonly .{0,12}(was|were) (ever )?(tested|run|checked|probed)\b",
    r"\b1 market\b", r"\b1 series\b", r"\bn ?= ?[1-9]\b", r"\bn ?= ?1[0-9]\b",
    r"\bsampled\b", r"\bbusiest\b", r"\bper tag\b", r"\bsuperset\b",
    r"\bnot exhaustive\b", r"\bwas never tested\b", r"\bnever run\b",
]

CLOSING_STATUS = {"SETTLED", "RETRACTED", "CANCELLED", "BROKEN"}


def hits(pattern_list: list[str], text: str) -> list[str]:
    found = []
    for p in pattern_list:
        if re.search(p, text, re.I):
            found.append(p)
    return found


def main() -> int:
    rows, files, _ = ledger.all_rows()
    OUT.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    out = []
    for r in rows:
        rid = (r.get("_id") or "").strip()
        if rid in seen:          # the retraction summary echoes project rows
            continue
        seen.add(rid)
        blob = " ".join(ledger.plain(str(v)) for k, v in r.items()
                        if not k.startswith("_"))
        status = ledger.status_of(r)
        null_h = hits(NULL_WORDS, blob)
        floor_h = hits(FLOOR_WORDS, blob)
        out.append({
            "id": rid,
            "status": status,
            "project": ledger.project_of(r),
            "file": r.get("_file", ""),
            "closing": "yes" if status in CLOSING_STATUS else "",
            "null_language": len(null_h),
            "states_floor": len(floor_h),
            # the screen that matters: a null with nothing said about how big
            # an effect the test could have seen
            "FLOOR_GAP": "yes" if (null_h and not floor_h) else "",
            "BUG": "yes" if hits(BUG_WORDS, blob) else "",
            "DATA": "yes" if hits(DATA_WORDS, blob) else "",
            "NARROW": "yes" if hits(NARROW_WORDS, blob) else "",
            "claim": ledger.claim_of(r)[:200],
        })

    path = OUT / "screen.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    def count(key):
        return sum(1 for r in out if r[key])

    print("files:", files)
    print(f"distinct claims        {len(out)}")
    print(f"  closing status       {count('closing')}")
    print(f"  FLOOR_GAP candidates {count('FLOOR_GAP')}")
    print(f"  BUG candidates       {count('BUG')}")
    print(f"  DATA candidates      {count('DATA')}")
    print(f"  NARROW candidates    {count('NARROW')}")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
