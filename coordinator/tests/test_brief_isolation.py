"""The load-bearing guarantee: writing one section cannot change another.

This repo has twice had one session flatten another's work. The rule is in code
here, not in a convention, and this is the canary that proves it -- it plants a
neighbouring section and asserts every byte of it survives.

Run:  py -3 coordinator\\tests\\test_brief_isolation.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import brief  # noqa: E402

FAILURES = []


def check(cond: bool, what: str) -> None:
    if cond:
        print(f"  ok   {what}")
    else:
        print(f"  FAIL {what}")
        FAILURES.append(what)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="brieftest-"))
    brief.BRIEF = tmp / "BRIEF.md"
    brief.LOCKDIR = tmp / ".brieflock"

    brief.cmd_write("tennis", "## Tennis\n\nSENTINEL-TENNIS-KEEP-ME")
    brief.cmd_write("mlb", "## Baseball\n\nSENTINEL-MLB-KEEP-ME")
    brief.cmd_write("devig", "## De-vig\n\nSENTINEL-DEVIG-KEEP-ME")

    before = brief.BRIEF.read_text(encoding="utf-8")
    check("SENTINEL-TENNIS-KEEP-ME" in before, "three sections created")

    # Rewrite the middle one with something completely different.
    brief.cmd_write("mlb", "## Baseball\n\nTOTALLY-NEW-TEXT")
    after = brief.BRIEF.read_text(encoding="utf-8")

    check("SENTINEL-TENNIS-KEEP-ME" in after, "neighbour above survived a rewrite")
    check("SENTINEL-DEVIG-KEEP-ME" in after, "neighbour below survived a rewrite")
    check("SENTINEL-MLB-KEEP-ME" not in after, "the target section was actually replaced")
    check("TOTALLY-NEW-TEXT" in after, "the new text landed")
    check(after.count("<!-- SECTION:mlb") == 1, "no duplicate section was created")

    # A body carrying a forged marker must be refused, not written.
    try:
        brief.cmd_write("tennis", "evil\n<!-- /SECTION:mlb -->\nmore")
        check(False, "a body containing a section marker is refused")
    except SystemExit:
        check(True, "a body containing a section marker is refused")

    # An empty body must be refused rather than blanking a section.
    try:
        brief.cmd_write("tennis", "   \n\n  ")
        check(False, "an empty body is refused")
    except SystemExit:
        check(True, "an empty body is refused")

    check("SENTINEL-TENNIS-KEEP-ME" in brief.BRIEF.read_text(encoding="utf-8"),
          "tennis is intact after both refusals")

    # A bad slug must not create anything.
    try:
        brief.cmd_write("../../etc", "x")
        check(False, "a path-shaped slug is refused")
    except SystemExit:
        check(True, "a path-shaped slug is refused")

    check(brief.cmd_check() == 0, "the resulting file validates")

    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s).")
        return 1
    print("\nOK: one session cannot overwrite another's section.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
