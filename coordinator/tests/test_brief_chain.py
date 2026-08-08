"""The chain of dated pages must be walkable, and snapshots must be immutable.

Why this exists: a query string is NOT a cache key for the fetcher in use --
a request for `?v=A` came back with the body cached under `?v=B`. Measured on
2026-08-07. Only a different PATH is fetched fresh, so freshness now depends
entirely on each page naming the next page's path and that path existing.

Two things can break it, and both fail silently in the worst possible
direction -- the reader believes a stale page is current:

  1. a gap in the numbering, so following next-links dead-ends early;
  2. a snapshot rewritten after publication, so an already-fetched page's
     next-link no longer matches what is there.

Run:  py -3 coordinator\\tests\\test_brief_chain.py
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import brief  # noqa: E402

FAILURES = []


def check(cond: bool, what: str) -> None:
    print(f"  {'ok  ' if cond else 'FAIL'} {what}")
    if not cond:
        FAILURES.append(what)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="chaintest-"))
    brief.BRIEF = tmp / "BRIEF.md"
    brief.BRIEFS = tmp / "briefs"
    brief.LOCKDIR = tmp / ".brieflock"

    brief.cmd_write("tennis", "## Tennis\n\nfirst")
    snaps = brief.snapshots()
    check(len(snaps) == 1, "a write publishes a snapshot")

    first = snaps[0]
    first_body = first.read_text(encoding="utf-8")
    day = first.name[6:16]

    # The page must name the NEXT path, not its own, and no query string.
    nxt = re.search(r"briefs/BRIEF-\d{4}-\d\d-\d\d-(\d\d)\.md", first_body)
    check(nxt is not None, "the page names a next path")
    check(nxt and nxt.group(1) == "02", "the next path is the following generation")
    check("?v=" not in first_body, "no query-string cache trick anywhere on the page")
    check((brief.BRIEFS / f"BRIEF-{day}.md").exists(), "a day page is written too")

    # A second, different write must extend the chain by exactly one.
    brief.cmd_write("tennis", "## Tennis\n\nsecond")
    snaps = brief.snapshots()
    check(len(snaps) == 2, "a changed write extends the chain")
    check(snaps[1].name.endswith("-02.md"), "the new snapshot is numbered 02")
    check(
        first.read_text(encoding="utf-8") == first_body,
        "the earlier snapshot was NOT rewritten -- old pages stay walkable",
    )
    check(
        "second" in (brief.BRIEFS / f"BRIEF-{day}.md").read_text(encoding="utf-8"),
        "the day page tracks the latest",
    )

    # Re-stamping with no content change must NOT mint a new page.
    before = len(snaps)
    brief.cmd_stamp()
    after = len(brief.snapshots())
    check(after == before, "an unchanged page does not mint a new snapshot")

    check(brief.cmd_check() == 0, "check passes on an unbroken chain")

    # Plant a gap and prove check catches it.
    snaps[1].unlink()
    brief.cmd_write("mlb", "## Baseball\n\nx")   # becomes 02 again -- no gap
    (brief.BRIEFS / f"BRIEF-{day}-04.md").write_text("orphan", encoding="utf-8")
    check(brief.cmd_check() == 1, "check FAILS when the chain has a hole in it")

    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s).")
        return 1
    print("\nOK: the chain is walkable and old pages are immutable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
