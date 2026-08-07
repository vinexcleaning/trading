"""Write exactly one section of the repo-root BRIEF.md.

There is no mode that rewrites the whole file. A session can only ever replace
the bytes between its own two markers -- everything else is copied through
untouched. See coordinator/COORDINATOR.md section 5.

No network. No credentials. Local filesystem only.

Usage
-----
  py -3 coordinator\\brief.py write <slug> --file body.md
  py -3 coordinator\\brief.py write <slug> --stdin
  py -3 coordinator\\brief.py stamp                 # refresh the freshness header
  py -3 coordinator\\brief.py list                  # slugs + when each was written
  py -3 coordinator\\brief.py check                 # validate structure, exit 1 if broken
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
BRIEF = REPO / "BRIEF.md"
LOCKDIR = HERE / ".brieflock"

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


def stamp_block() -> str:
    h = head_hash()
    now = f"{datetime.now():%Y-%m-%d %H:%M}"
    # The stamp can never name the commit that contains it -- it is written
    # before that commit exists. So the freshness test is one-directional:
    # commit `h` must be FINDABLE in the repo history. If it is not, the page
    # predates it and is cached. Being one or two commits behind is normal.
    return (
        f"{STAMP_OPEN}\n"
        f"> **Generated {now}, on top of commit `{h}`.**\n"
        f"> **Freshness check:** if `{h}` does not appear in this repo's commit\n"
        f"> history on GitHub, you are reading a cached copy — stop and refetch.\n"
        f"> Being one or two commits behind the newest is normal and expected:\n"
        f"> this page is always written just before the commit that carries it.\n"
        f"> Cache-busting URL, always safe to use:\n"
        f"> `https://raw.githubusercontent.com/vinexcleaning/trading/main/BRIEF.md?v={h}`\n"
        f"{STAMP_CLOSE}"
    )


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
    finally:
        release_lock()

    print(f"BRIEF.md: section '{slug}' {verb} ({len(body.splitlines())} lines).")
    print(f"Sections now present: {', '.join(s for s, _ in all_sections(read_brief()))}")


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
    finally:
        release_lock()
    print(f"BRIEF.md stamp refreshed to {head_hash()}.")


def cmd_list() -> None:
    text = read_brief()
    secs = all_sections(text)
    if not secs:
        print("BRIEF.md has no sections yet.")
        return
    width = max(len(s) for s, _ in secs)
    for slug, when in secs:
        print(f"  {slug.ljust(width)}  last written {when.replace('T', ' ')}")


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
    if problems:
        for p in sorted(set(problems)):
            print(f"FAIL: {p}")
        return 1
    print(f"OK: BRIEF.md is well formed, {len(set(opens))} section(s).")
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

    sub.add_parser("stamp", help="refresh the freshness header only")
    sub.add_parser("list", help="show sections and when each was written")
    sub.add_parser("check", help="validate structure")

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
    return cmd_check()


if __name__ == "__main__":
    raise SystemExit(main())
