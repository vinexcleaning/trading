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
import os
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
From: {sender}
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


NUM_RE = re.compile(r"^(\d{3,})-")


def highest_number(slug: str) -> int:
    """The largest NNN already used in this box, or 0.

    Deliberately NOT a count. Counting reuses a number if a message is ever
    deleted or renamed, which would overwrite a live message. The highest
    number only ever goes up.
    """
    d = box(slug)
    if not d.is_dir():
        return 0
    n = 0
    # *.partial is a number that was claimed by a sender that then died. It
    # still counts: reusing it would hand out a number somebody already cited.
    for p in list(d.glob("*.md")) + list(d.glob("*.partial")):
        m = NUM_RE.match(p.name)
        if m:
            n = max(n, int(m.group(1)))
    return n


def _discard(claim) -> None:
    """Drop a claim we could not use. Never raises -- a stuck claim only
    costs one message number, and NNN.partial is visible on disk if it does."""
    try:
        claim.unlink()
    except (FileNotFoundError, PermissionError, OSError):
        pass


def create_exclusive(slug: str, subject: str, text: str, attempts: int = 200):
    """Claim the next free NNN and write it, atomically.

    ⚠ THE DEFECT THIS FIXES. `cmd_send` used to compute the number as
    `len(messages(slug)) + 1` and then write. Two senders running at the same
    moment both read the same count, both chose the same NNN, and the second
    write silently destroyed the first message. Nothing anywhere would have
    said so -- the loser simply never existed.

    `O_CREAT | O_EXCL` is atomic on Windows and POSIX: exactly one caller can
    create a given path, and every other caller gets FileExistsError. So the
    number is CLAIMED by the create, not chosen before it.

    ⚠ THE CLAIM PATH MUST DEPEND ON THE NUMBER ALONE. The first version of this
    fix claimed `NNN-<subject>.md` directly, which is not a mutex on the number:
    two senders with different subjects both succeed at the same NNN and you get
    two `016`s. Nothing is lost, but "mailbox 016" stops identifying a message,
    and that string is used by humans and quoted inside other messages. So the
    claim is `NNN.partial` -- subject-free -- and the real name is a rename
    afterwards.

    The rename is also why a reader never sees a half-written message.

    The final filename format is unchanged, so every existing message, every
    reader, and every human habit still works.
    """
    d = box(slug)
    d.mkdir(parents=True, exist_ok=True)
    n = highest_number(slug)
    for _ in range(attempts):
        n += 1
        claim = d / f"{n:03d}.partial"
        try:
            fd = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except (FileExistsError, PermissionError):
            # FileExistsError: somebody else owns this number.
            # ⚠ PermissionError: Windows only, and it means the same thing. A
            # file that has just been unlinked sits in a "delete pending" state
            # where CreateFile returns ACCESS_DENIED rather than ALREADY_EXISTS
            # until the last handle closes. Measured: this is what 40 concurrent
            # writers actually hit, roughly one run in three. Treating it as a
            # hard error would fail a send for a reason that resolves itself in
            # microseconds.
            continue
        # ⚠ Holding the claim is not enough on its own. A sender that finished
        # RENAMES its NNN.partial away, so the number stops being visible as a
        # partial the instant it becomes a real message -- and a sender whose
        # scan predated that rename would then claim the same NNN and be
        # allowed to. Measured: 2 duplicates in 40 concurrent writers. So once
        # the claim is held, look again for a real message at this number.
        #
        # ⚠ AND THE HANDLE MUST BE CLOSED BEFORE THE CLAIM IS UNLINKED. Windows
        # refuses to delete a file that anyone still has open -- including us --
        # and reports it as "used by another process", which reads like someone
        # else's fault and is not. That was the last flake here.
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                if list(d.glob(f"{n:03d}-*.md")):
                    taken = True
                else:
                    taken = False
                    fh.write(text)
        except BaseException:
            _discard(claim)
            raise
        if taken:
            _discard(claim)
            continue
        path = d / f"{n:03d}-{slugify(subject)}.md"
        try:
            os.replace(claim, path)
        except PermissionError:
            _discard(claim)
            continue          # transient on Windows; the next number is free
        return path
    raise RuntimeError(
        f"could not claim a free message number in {d} after {attempts} tries"
    )


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


def cmd_send(slug: str, subject: str, body: str,
             sender: str = "coordinator") -> None:
    if not SLUG_RE.match(slug):
        sys.exit(f"'{slug}' is not a valid mailbox name (lowercase, digits, hyphens).")
    body = body.strip()
    if not body:
        sys.exit("Refusing to send an empty instruction.")
    if not SLUG_RE.match(sender):
        sys.exit(f"'{sender}' is not a valid sender name (lowercase, digits, hyphens).")
    text = TEMPLATE.format(
        slug=slug,
        sender=sender,
        when=f"{datetime.now():%Y-%m-%d %H:%M}",
        subject=subject,
        body=body,
    )
    path = create_exclusive(slug, subject, text)
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
    s.add_argument("--from", dest="sender", default="coordinator",
                   help="who is sending. Defaults to coordinator, so every "
                        "existing Claude workflow is unchanged.")

    sub.add_parser("list")
    sub.add_parser("open")
    sh = sub.add_parser("show")
    sh.add_argument("slug")

    a = ap.parse_args()
    if a.cmd == "send":
        body = sys.stdin.read() if a.stdin else Path(a.file).read_text(encoding="utf-8")
        cmd_send(a.slug, a.subject, body, a.sender)
    elif a.cmd == "list":
        cmd_list(False)
    elif a.cmd == "open":
        cmd_list(True)
    else:
        cmd_show(a.slug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
