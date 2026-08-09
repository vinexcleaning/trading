"""Canaries for the dictator chat. In the style of GUARDS.md: they assert
nothing about intent, they just make a bad change loud.

The one that matters is the third: a prior-work report that omits what was
tested, on what data, over what dates, is exactly the "we tried that" answer
that killed a live idea once already. If someone simplifies idea.py and drops
one of those fields, this fails.

Run:  py -3 coordinator\\tests\\test_dictator.py
"""

from __future__ import annotations

import sys
from pathlib import Path

COORD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(COORD))

import chats as chatreg  # noqa: E402
import detail  # noqa: E402
import idea  # noqa: E402
import ledger  # noqa: E402


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    fail.count += 1  # type: ignore[attr-defined]


fail.count = 0  # type: ignore[attr-defined]


def check_ledger_parses() -> None:
    rows, read, missing = ledger.all_rows()
    if len(rows) < 500:
        fail(f"only {len(rows)} ledger claims parsed. There were 596 after the "
             f"parser was widened on 2026-08-09. A parser that silently "
             f"reads less makes every "
             f"'has this been tried' answer more confident and less correct.")
    if missing:
        fail(f"ledger file(s) listed but not found: {missing}. The search is "
             f"smaller than it claims to be.")
    # Only rows that HAVE a status column can fail to parse one. A table
    # without the column is not a parse failure, and counting it as one fired
    # this canary on 133 correctly-read rows.
    have = [r for r in rows if "status" in r]
    unknown = [r for r in have if ledger.status_of(r) == "?"]
    if have and len(unknown) > len(have) * 0.05:
        fail(f"{len(unknown)} of {len(have)} rows WITH a status column have no "
             f"readable status. "
             f"A column shift usually causes this -- check for an unescaped "
             f"pipe inside a cell.")


def check_report_says_what_was_tested() -> None:
    """The whole point. A report may never assert 'tried' without the detail."""
    text, _slug = idea.report(
        "test whether individual tennis players are systematically mispriced")
    required = [
        "WHAT WAS TESTED",
        "THE DATA",
        "MEASURED OVER",
        "WHAT CAME OUT",
        "NOT COVERED BY IT",
        "WORDS IT NEVER USES",
        "HOW YOUR IDEA DIFFERS",
        "GO AND READ IT",
    ]
    for key in required:
        if key not in text:
            fail(f"the prior-work report no longer prints '{key}'. Without it "
                 f"the report degrades into 'we tried that', which is the one "
                 f"thing this is built to prevent.")
    # The report NAMES the banned phrases in order to ban them, so they are
    # allowed where it is telling the reader not to use them. What must never
    # happen is one of them appearing as a VERDICT on a related claim -- that
    # is, anywhere in the list of hits.
    hits_part = text.split("HOW YOUR IDEA DIFFERS")[0].lower()
    for banned in ("we tried that", "already tested", "that's been done",
                   "already done"):
        if banned in hits_part:
            fail(f"the phrase '{banned}' appears in the list of related work, "
                 f"where it would read as a verdict. It is only allowed lower "
                 f"down, where the report is banning it.")


def check_report_surfaces_the_named_failure() -> None:
    """The concrete case this was built after: a player-features sweep was
    cited to close down a question about individual players. The report must
    surface that row, and must print words the row never uses."""
    text, _ = idea.report(
        "test whether individual tennis players are systematically mispriced, "
        "some players the market overrates")
    if "B023" not in text:
        fail("the report no longer surfaces B023, the pre-match player-feature "
             "sweep. That is the row someone must read before this idea is "
             "called settled -- and the row whose misuse this file exists for.")
    if "PART BY PART" not in text:
        fail("the per-word pass is gone. One ranked list always buries "
             "something, and what it buried last time was B023 itself.")


def check_routing_is_not_confidently_wrong() -> None:
    """Routing on prior work alone sent a baseball de-vig idea to the tennis
    chat, confidently, because de-vig ledger rows carry no project column and
    the tennis study's do. These four are the cases that caught it."""
    cases = [
        ("de-vig a retail bookmaker on baseball", {"devig", "mlb"}),
        ("record bitcoin order books every second", {"devig"}),
        ("scrape twitch streamers for trade calls", {"signal"}),
        ("individual tennis players mispriced on clay", {"tennis"}),
    ]
    for text, allowed in cases:
        _, slug = idea.report(text)
        if slug and slug not in allowed:
            fail(f"'{text}' routed to '{slug}'. Expected one of {sorted(allowed)} "
                 f"or an honest 'cannot tell'. A confidently wrong route is "
                 f"worse than no route -- it sends the work to a chat that "
                 f"does not own the folders.")


def check_every_chat_is_named() -> None:
    problems = chatreg.validate()
    for p in problems:
        fail(f"chats.json: {p}")
    for c in chatreg.chats():
        if not c.get("opening", "").strip():
            fail(f"'{c['slug']}' has no opening line, so nobody can be told "
                 f"what to type in that window.")


def check_detail_reads_brief_sections() -> None:
    """A regex that misses the timestamp in the section marker reports a chat
    that HAS written a brief as having written none. That reads as an
    accusation, so it is checked rather than assumed."""
    found = [c["slug"] for c in chatreg.chats()
             if detail.brief_section(c["slug"])]
    if len(found) < 2:
        fail(f"only {len(found)} chat(s) have a readable BRIEF.md section. "
             f"Either the markers changed shape or the regex broke -- and the "
             f"failure mode is telling a chat it wrote nothing when it did.")


def check_the_cannot_list_exists() -> None:
    doc = COORD.parent / "DICTATOR.md"
    if not doc.exists():
        fail("DICTATOR.md is missing. The limits are the honest half of this "
             "and they were written before the code on purpose.")
        return
    text = doc.read_text(encoding="utf-8", errors="replace")
    for phrase in ("CANNOT DO", "cannot place a trade", "one paste"):
        if phrase.lower() not in text.lower():
            fail(f"DICTATOR.md no longer says '{phrase}'.")
    if text.lower().index("cannot do") > text.lower().index("what it does"):
        fail("DICTATOR.md lists what it CAN do before what it cannot. The "
             "order is the point: a tool described by its best case gets "
             "trusted past its actual case.")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    check_ledger_parses()
    check_report_says_what_was_tested()
    check_report_surfaces_the_named_failure()
    check_routing_is_not_confidently_wrong()
    check_every_chat_is_named()
    check_detail_reads_brief_sections()
    check_the_cannot_list_exists()

    n = fail.count  # type: ignore[attr-defined]
    if n:
        print(f"\n{n} failure(s).")
        return 1
    print("OK: the prior-work report still says what was tested, on what data, "
          "over what dates; every chat is named; the limits are documented.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
