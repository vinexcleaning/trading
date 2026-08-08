"""The mailbox: pass an instruction to a sibling session through a file.

A message is one Markdown file. The receiving session answers by editing that
same file -- changing `Status: OPEN` to `Status: DONE` (or `BLOCKED`) and typing
under the reply line. There is no tool for the receiving session to learn.

No network. No credentials. Local filesystem only.

Usage
-----
  py -3 coordinator\\mail.py send tennis --subject "..." --file body.md
  py -3 coordinator\\mail.py send tennis --subject "..." --stdin
  py -3 coordinator\\mail.py list                 # every message, newest last
  py -3 coordinator\\mail.py open                 # only what is still OPEN
  py -3 coordinator\\mail.py show tennis          # full text of that box
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAILBOX = HERE / "mailbox"

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,30}$")
STATUS_RE = re.compile(r"^Status:\s*(\S+)", re.MULTILINE)
SUBJECT_RE = re.compile(r"^Subject:\s*(.+)$", re.MULTILINE)
OPENED_RE = re.compile(r"^Opened:\s*(.+)$", re.MULTILINE)

TEMPLATE = """To: {slug}
From: coordinator
Opened: {when}
Status: OPEN
Subject: {subject}

--- INSTRUCTION ---

{body}

--- REPLY ---

The session that owns `{slug}` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

"""


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s or "message")[:48]


def box(slug: str) -> Path:
    return MAILBOX / slug


def messages(slug: str):
    d = box(slug)
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob("*.md") if p.name != "README.md")


def all_slugs():
    if not MAILBOX.is_dir():
        return []
    return sorted(p.name for p in MAILBOX.iterdir() if p.is_dir())


def status_of(path: Path) -> str:
    m = STATUS_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    return (m.group(1) if m else "?").upper()


def field(path: Path, rx) -> str:
    m = rx.search(path.read_text(encoding="utf-8", errors="replace"))
    return m.group(1).strip() if m else ""


def counts():
    """{slug: {'OPEN': n, 'DONE': n, ...}} -- used by scan.py too."""
    out = {}
    for slug in all_slugs():
        c = {}
        for p in messages(slug):
            st = status_of(p)
            c[st] = c.get(st, 0) + 1
        out[slug] = c
    return out


def cmd_send(slug: str, subject: str, body: str) -> None:
    if not SLUG_RE.match(slug):
        sys.exit(f"'{slug}' is not a valid mailbox name (lowercase, digits, hyphens).")
    body = body.strip()
    if not body:
        sys.exit("Refusing to send an empty instruction.")
    d = box(slug)
    d.mkdir(parents=True, exist_ok=True)
    n = len(messages(slug)) + 1
    path = d / f"{n:03d}-{slugify(subject)}.md"
    path.write_text(
        TEMPLATE.format(
            slug=slug,
            when=f"{datetime.now():%Y-%m-%d %H:%M}",
            subject=subject,
            body=body,
        ),
        encoding="utf-8",
        newline="\n",
    )
    try:
        shown = path.relative_to(HERE.parent)
    except ValueError:
        shown = path  # a test has redirected MAILBOX outside the repo
    print(f"Filed: {shown}")
    print(
        f"It is NOT delivered yet. The '{slug}' session sees it when it next "
        f"starts, or when you say 'check your mail' in that window."
    )


def cmd_list(only_open: bool) -> None:
    any_found = False
    for slug in all_slugs():
        rows = []
        for p in messages(slug):
            st = status_of(p)
            if only_open and st != "OPEN":
                continue
            rows.append((st, p.name, field(p, SUBJECT_RE), field(p, OPENED_RE)))
        if not rows:
            continue
        any_found = True
        print(f"\n{slug}")
        for st, name, subj, when in rows:
            mark = "[ ]" if st == "OPEN" else "[x]" if st == "DONE" else f"[{st[:1]}]"
            print(f"  {mark} {name}  {subj}   (opened {when}, {st})")
    if not any_found:
        print("No open messages." if only_open else "The mailbox is empty.")


def cmd_show(slug: str) -> None:
    ms = messages(slug)
    if not ms:
        print(f"No messages for '{slug}'.")
        return
    for p in ms:
        print(f"\n{'=' * 70}\n{p.name}\n{'=' * 70}")
        print(p.read_text(encoding="utf-8", errors="replace"))


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

    s = sub.add_parser("send")
    s.add_argument("slug")
    s.add_argument("--subject", required=True)
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--file")
    g.add_argument("--stdin", action="store_true")

    sub.add_parser("list")
    sub.add_parser("open")
    sh = sub.add_parser("show")
    sh.add_argument("slug")

    a = ap.parse_args()
    if a.cmd == "send":
        body = sys.stdin.read() if a.stdin else Path(a.file).read_text(encoding="utf-8")
        cmd_send(a.slug, a.subject, body)
    elif a.cmd == "list":
        cmd_list(False)
    elif a.cmd == "open":
        cmd_list(True)
    else:
        cmd_show(a.slug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
