"""Write exactly one section of the repo-root BRIEF.md.

There is no mode that rewrites the whole file. A session can only ever replace
the bytes between its own two markers -- everything else is copied through
untouched. See coordinator/COORDINATOR.md section 5.

No network. No credentials. Local filesystem only.

Usage
-----
  py -3 coordinator\\brief.py write <slug> --file body.md
  py -3 coordinator\\brief.py write <slug> --stdin
  py -3 coordinator\\brief.py stamp                 # refresh the header + publish
  py -3 coordinator\\brief.py list                  # slugs + when each was written
  py -3 coordinator\\brief.py chain                 # entry URL and newest page
  py -3 coordinator\\brief.py check                 # validate, exit 1 if broken

Every write also publishes an immutable copy to briefs/BRIEF-<date>-<NN>.md.
Each page names the path of the next one, so a reader that caches by path can
walk forward on its own. Snapshots are never rewritten.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
BRIEF = REPO / "BRIEF.md"
BRIEFS = REPO / "briefs"
LOCKDIR = HERE / ".brieflock"

RAW = "https://raw.githubusercontent.com/vinexcleaning/trading/main"

LOCK_WAIT_SECONDS = 60
LOCK_STALE_SECONDS = 300

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,30}$")

HEADER = """# BRIEF.md — the whole picture, one page

One section per project. **Every session overwrites only its own section**, via
`py -3 coordinator\\brief.py write <slug> --file <body.md>`. Nothing else in this
file is touched by that command.

This is the file the coordinating chat reads. `STATUS.md` stays the detailed
channel between sessions; this is the short channel out. Plain English, no
acronyms, no jargon. If a number matters, say whether bigger is better.

Every version of this page is also kept forever at a dated path under
[briefs/](briefs/). Follow the chain in the box below to reach the newest.
"""

STAMP_OPEN = "<!-- STAMP -->"
STAMP_CLOSE = "<!-- /STAMP -->"


# --------------------------------------------------------------------------
# lock
# --------------------------------------------------------------------------
def acquire_lock() -> None:
    """mkdir is atomic on Windows and POSIX; use it as the lock primitive."""
    deadline = time.time() + LOCK_WAIT_SECONDS
    while True:
        try:
            LOCKDIR.mkdir()
            (LOCKDIR / "owner.txt").write_text(
                f"pid={os.getpid()} at={datetime.now():%Y-%m-%d %H:%M:%S}\n",
                encoding="utf-8",
            )
            return
        except FileExistsError:
            age = time.time() - LOCKDIR.stat().st_mtime
            if age > LOCK_STALE_SECONDS:
                # A crashed session left it behind. Take it.
                release_lock()
                continue
            if time.time() > deadline:
                sys.exit(
                    f"BRIEF.md is locked by another session and has been for "
                    f"{age:.0f}s. Nothing was written. Try again, or delete "
                    f"{LOCKDIR} if you are sure no session is running."
                )
            time.sleep(0.4)


def release_lock() -> None:
    try:
        for child in LOCKDIR.iterdir():
            child.unlink()
        LOCKDIR.rmdir()
    except FileNotFoundError:
        pass


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def git(*args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=REPO, capture_output=True, text=True, timeout=30
        )
        return out.stdout.strip()
    except Exception:
        return ""


def head_hash() -> str:
    return git("rev-parse", "--short", "HEAD") or "unknown"


def read_brief() -> str:
    if not BRIEF.exists():
        return HEADER + "\n" + stamp_block() + "\n"
    return BRIEF.read_text(encoding="utf-8")


def write_brief_atomic(text: str) -> None:
    tmp = BRIEF.with_suffix(".md.tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, BRIEF)


def next_generation_number(day: str) -> int:
    """The number the next snapshot of `day` would take. 1 if none yet."""
    return len(list(BRIEFS.glob(f"BRIEF-{day}-*.md"))) + 1


def core(text: str) -> str:
    """The page minus its stamp -- what 'has anything actually changed' means."""
    if STAMP_OPEN in text and STAMP_CLOSE in text:
        s = text.index(STAMP_OPEN)
        e = text.index(STAMP_CLOSE) + len(STAMP_CLOSE)
        text = text[:s] + text[e:]
    return text.strip()


def stamp_block() -> str:
    """The freshness header.

    A query string is NOT a cache key for at least one fetcher in use here: a
    request for `?v=A` came back with the body cached under `?v=B`. Measured,
    not assumed. So `?v=` is useless and no query-parameter scheme can work.
    Only a genuinely different PATH gets fetched fresh.

    Hence a chain of paths. Every page names the path of the next one. A reader
    follows next-links until one 404s; the last page that loaded is the newest.
    """
    h = head_hash()
    now = datetime.now()
    day = f"{now:%Y-%m-%d}"
    tomorrow = f"{now.date() + timedelta(days=1)}"
    nxt = next_generation_number(day) + 1
    return (
        f"{STAMP_OPEN}\n"
        f"> **Generated {now:%Y-%m-%d %H:%M}, on top of commit `{h}`.**\n"
        f">\n"
        f"> **Automated readers: follow the chain below. Do not re-fetch this\n"
        f"> page and do not add a query string.** Query strings are discarded by\n"
        f"> at least one fetcher in use here: two requests differing only in a `v=`\n"
        f"> parameter returned the same cached body. Only a different **path** is\n"
        f"> fetched fresh.\n"
        f">\n"
        f"> **Next page, if one exists:**\n"
        f"> `{RAW}/briefs/BRIEF-{day}-{nxt:02d}.md`\n"
        f"> Fetch it. If it loads, read it and follow *its* next link. Repeat\n"
        f"> until one returns 404 — the last page that loaded is the newest.\n"
        f">\n"
        f"> **To skip a whole day forward:**\n"
        f"> `{RAW}/briefs/BRIEF-{tomorrow}.md`\n"
        f"> One page exists per day the repo was worked on, holding that day's\n"
        f"> final state. A 404 means nothing was published that day — try the\n"
        f"> day after, and so on up to today's date.\n"
        f">\n"
        f"> **Cross-check:** commit `{h}` must appear in this repo's commit\n"
        f"> history. If it does not, this page predates it and is cached.\n"
        f"{STAMP_CLOSE}"
    )


def publish() -> str | None:
    """Copy the live BRIEF.md to an immutable dated path, if anything changed.

    Returns the snapshot's repo-relative path, or None if there was nothing new.
    Snapshots are NEVER rewritten once created -- that is what makes the chain
    walkable months later.
    """
    BRIEFS.mkdir(exist_ok=True)
    text = BRIEF.read_text(encoding="utf-8")
    day = f"{datetime.now():%Y-%m-%d}"

    previous = snapshots()
    result = None
    if not (previous and core(previous[-1].read_text(encoding="utf-8")) == core(text)):
        n = next_generation_number(day)
        snap = BRIEFS / f"BRIEF-{day}-{n:02d}.md"
        snap.write_text(text, encoding="utf-8", newline="\n")
        result = f"briefs/{snap.name}"

    # The day page always mirrors the newest snapshot of its own day. Rebuilt
    # every time rather than only on change, so a deleted or half-written one
    # heals itself instead of leaving a hole a reader would fall into.
    latest = snapshots()
    if latest:
        newest = latest[-1]
        body = newest.read_text(encoding="utf-8")
        day_page = BRIEFS / f"BRIEF-{newest.name[6:16]}.md"
        if not day_page.exists() or day_page.read_text(encoding="utf-8") != body:
            day_page.write_text(body, encoding="utf-8", newline="\n")
    return result


def open_marker(slug: str, when: str) -> str:
    return f"<!-- SECTION:{slug} updated={when} -->"


def close_marker(slug: str) -> str:
    return f"<!-- /SECTION:{slug} -->"


def section_span(text: str, slug: str):
    """Return (start, end, updated) byte span of a slug's section, or None."""
    om = re.search(
        r"<!--\s*SECTION:" + re.escape(slug) + r"(?:\s+updated=(\S+))?\s*-->", text
    )
    if not om:
        return None
    cm = re.search(r"<!--\s*/SECTION:" + re.escape(slug) + r"\s*-->", text[om.end():])
    if not cm:
        sys.exit(
            f"BRIEF.md has an opening marker for '{slug}' but no closing marker. "
            f"Refusing to guess where the section ends. Nothing was written."
        )
    return om.start(), om.end() + cm.end(), (om.group(1) or "?")


def all_sections(text: str):
    out = []
    for m in re.finditer(r"<!--\s*SECTION:([a-z0-9-]+)(?:\s+updated=(\S+))?\s*-->", text):
        out.append((m.group(1), m.group(2) or "?"))
    return out


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------
def cmd_write(slug: str, body: str) -> None:
    if not SLUG_RE.match(slug):
        sys.exit(
            f"'{slug}' is not a valid section name. Use lowercase letters, "
            f"digits and hyphens, e.g. 'tennis' or 'mlb-paper'."
        )
    if not body.strip():
        sys.exit("Refusing to write an empty section. Nothing was written.")
    body = body.strip("\n")
    if "<!-- SECTION:" in body or "<!-- /SECTION:" in body:
        sys.exit(
            "The body contains a section marker. That would corrupt the file "
            "and could swallow another project's section. Nothing was written."
        )

    when = f"{datetime.now():%Y-%m-%dT%H:%M}"
    block = (
        f"{open_marker(slug, when)}\n"
        f"{body}\n\n"
        f"_Section `{slug}` last written {when.replace('T', ' ')}._\n"
        f"{close_marker(slug)}"
    )

    acquire_lock()
    try:
        text = read_brief()          # re-read INSIDE the lock
        text = refresh_stamp(text)
        span = section_span(text, slug)
        if span:
            start, end, _ = span
            text = text[:start] + block + text[end:]
            verb = "updated"
        else:
            if not text.endswith("\n"):
                text += "\n"
            text += "\n---\n\n" + block + "\n"
            verb = "created"
        write_brief_atomic(text)
        snap = publish()
    finally:
        release_lock()

    print(f"BRIEF.md: section '{slug}' {verb} ({len(body.splitlines())} lines).")
    print(f"Sections now present: {', '.join(s for s, _ in all_sections(read_brief()))}")
    if snap:
        print(f"Published snapshot: {snap}  (commit it, or the chain breaks)")


def refresh_stamp(text: str) -> str:
    new = stamp_block()
    if STAMP_OPEN in text and STAMP_CLOSE in text:
        s = text.index(STAMP_OPEN)
        e = text.index(STAMP_CLOSE) + len(STAMP_CLOSE)
        return text[:s] + new + text[e:]
    return text.rstrip("\n") + "\n\n" + new + "\n"


def cmd_stamp() -> None:
    acquire_lock()
    try:
        write_brief_atomic(refresh_stamp(read_brief()))
        snap = publish()
    finally:
        release_lock()
    print(f"BRIEF.md stamp refreshed to {head_hash()}.")
    print(
        f"Published snapshot: {snap}  (commit it, or the chain breaks)"
        if snap
        else "No new snapshot — the page has not changed since the last one."
    )


def cmd_list() -> None:
    text = read_brief()
    secs = all_sections(text)
    if not secs:
        print("BRIEF.md has no sections yet.")
        return
    width = max(len(s) for s, _ in secs)
    for slug, when in secs:
        print(f"  {slug.ljust(width)}  last written {when.replace('T', ' ')}")


def snapshots():
    return sorted(BRIEFS.glob("BRIEF-????-??-??-??.md")) if BRIEFS.is_dir() else []


def cmd_chain() -> None:
    """What to hand a reader that has never seen this repo, and the walk itself."""
    snaps = snapshots()
    if not snaps:
        print("No snapshots yet. Run:  py -3 coordinator\\brief.py stamp")
        return
    print("Entry point for a reader that has nothing (never changes):")
    print(f"  {RAW}/BRIEF.md")
    print("\nNewest page right now:")
    print(f"  {RAW}/briefs/{snaps[-1].name}")
    print(f"\n{len(snaps)} snapshot(s), {len(set(p.name[6:16] for p in snaps))} day(s).")
    print("A reader follows each page's next link until one 404s. It does not")
    print("need any of these URLs in advance except the entry point.")


def cmd_check() -> int:
    if not BRIEF.exists():
        print("FAIL: BRIEF.md does not exist.")
        return 1
    text = read_brief()
    problems = []
    if STAMP_OPEN not in text or STAMP_CLOSE not in text:
        problems.append("the freshness stamp block is missing")
    opens = [m.group(1) for m in re.finditer(r"<!--\s*SECTION:([a-z0-9-]+)", text)]
    closes = [m.group(1) for m in re.finditer(r"<!--\s*/SECTION:([a-z0-9-]+)", text)]
    for slug in opens:
        if opens.count(slug) > 1:
            problems.append(f"section '{slug}' is opened more than once")
        if slug not in closes:
            problems.append(f"section '{slug}' is never closed")
    for slug in closes:
        if slug not in opens:
            problems.append(f"section '{slug}' is closed but never opened")
    # The chain must have no gaps: a missing number 404s and stops a reader dead.
    by_day: dict[str, list[int]] = {}
    for p in snapshots():
        by_day.setdefault(p.name[6:16], []).append(int(p.name[17:19]))
    for day, nums in by_day.items():
        expected = list(range(1, max(nums) + 1))
        missing = sorted(set(expected) - set(nums))
        if missing:
            problems.append(
                f"the chain for {day} is missing generation(s) "
                f"{', '.join(f'{m:02d}' for m in missing)} — a reader following "
                f"next-links stops there and never sees anything later"
            )
        if not (BRIEFS / f"BRIEF-{day}.md").exists():
            problems.append(f"the day page BRIEF-{day}.md is missing")

    if problems:
        for p in sorted(set(problems)):
            print(f"FAIL: {p}")
        return 1
    print(f"OK: BRIEF.md is well formed, {len(set(opens))} section(s), "
          f"{len(snapshots())} snapshot(s), chain unbroken.")
    return 0


def _ascii_safe_console():
    """Old Windows consoles are cp1252 and choke on an em dash."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main() -> int:
    _ascii_safe_console()
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("write", help="replace one section")
    w.add_argument("slug")
    g = w.add_mutually_exclusive_group(required=True)
    g.add_argument("--file", help="path to a Markdown file holding the section body")
    g.add_argument("--stdin", action="store_true", help="read the body from stdin")

    sub.add_parser("stamp", help="refresh the freshness header and publish")
    sub.add_parser("list", help="show sections and when each was written")
    sub.add_parser("chain", help="the entry URL and the newest page")
    sub.add_parser("check", help="validate structure and the snapshot chain")

    a = ap.parse_args()
    if a.cmd == "write":
        body = (
            sys.stdin.read()
            if a.stdin
            else Path(a.file).read_text(encoding="utf-8")
        )
        cmd_write(a.slug, body)
        return 0
    if a.cmd == "stamp":
        cmd_stamp()
        return 0
    if a.cmd == "list":
        cmd_list()
        return 0
    if a.cmd == "chain":
        cmd_chain()
        return 0
    return cmd_check()


if __name__ == "__main__":
    raise SystemExit(main())
