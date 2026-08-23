"""Canary: two senders filing at the same moment cannot destroy each other.

⚠ THE DEFECT THIS GUARDS. `mail.cmd_send` used to pick its message number with
`len(messages(slug)) + 1` and then write. Two senders running at the same
instant both read the same count, both chose the same NNN, and the second write
silently destroyed the first message. Nothing anywhere reported it -- the losing
instruction simply never existed, and the only way to notice would have been a
human remembering they had filed something.

That was harmless while exactly one Claude dictator wrote mail. It stops being
harmless the moment a second agent -- ChatGPT, an automation, a second window --
files anything.

`test_the_old_way_would_have_collided` is the important one: it reproduces the
old algorithm and asserts it loses messages. If someone ever "simplifies" the
numbering back to a count, that test still passes and the two above it fail,
which is the loud signal.

Run:  py -3 coordinator\\tests\\test_mail_collision.py
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

COORD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(COORD))

import mail  # noqa: E402

WRITERS = 40


def _isolate(tmp_path) -> None:
    """Point the mailbox at a temp dir so no real message is touched."""
    mail.MAILBOX = Path(tmp_path) / "mailbox"


def test_concurrent_senders_all_survive(tmp_path):
    """40 threads file at once. All 40 messages must exist, all distinct."""
    _isolate(tmp_path)
    start = threading.Barrier(WRITERS)
    errors = []

    def send(i: int) -> None:
        try:
            start.wait(timeout=30)          # maximum contention
            mail.cmd_send("target", f"subject {i}", f"BODY-{i}", sender="tester")
        except Exception as exc:            # noqa: BLE001
            errors.append(f"writer {i}: {exc!r}")

    threads = [threading.Thread(target=send, args=(i,)) for i in range(WRITERS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert not errors, f"senders raised: {errors[:5]}"

    files = mail.messages("target")
    assert len(files) == WRITERS, (
        f"{WRITERS} senders produced {len(files)} files -- "
        f"{WRITERS - len(files)} message(s) were silently overwritten"
    )

    # every body survived exactly once
    bodies = sorted(
        line
        for p in files
        for line in p.read_text(encoding="utf-8").splitlines()
        if line.startswith("BODY-")
    )
    assert bodies == sorted(f"BODY-{i}" for i in range(WRITERS)), (
        "a message was lost or duplicated: "
        f"{len(bodies)} bodies from {len(files)} files"
    )

    # and the numbers are unique
    nums = [p.name.split("-", 1)[0] for p in files]
    assert len(set(nums)) == len(nums), f"duplicate message numbers: {nums}"


def test_numbers_never_reused_after_a_deletion(tmp_path):
    """Deleting a message must not free its number for reuse.

    A count-based scheme would hand the next sender a number that is already
    referenced by every human and document that cited the deleted one.
    """
    _isolate(tmp_path)
    for i in range(3):
        mail.cmd_send("target", f"s{i}", f"BODY-{i}", sender="tester")
    files = mail.messages("target")
    assert len(files) == 3
    files[1].unlink()                        # delete 002

    mail.cmd_send("target", "after deletion", "BODY-new", sender="tester")
    names = sorted(p.name for p in mail.messages("target"))
    assert any(n.startswith("004-") for n in names), (
        f"expected the new message to be 004, got {names}"
    )
    assert not any(n.startswith("002-") for n in names), (
        f"002 was reused after being deleted: {names}"
    )


def test_the_old_way_would_have_collided(tmp_path):
    """Reproduce the old algorithm and prove it loses messages.

    This is the evidence that the fix is not decoration. It does not call
    mail.py -- it re-implements `len(messages) + 1` and shows the failure.
    """
    _isolate(tmp_path)
    d = mail.box("target")
    d.mkdir(parents=True, exist_ok=True)

    start = threading.Barrier(WRITERS)

    def old_send(i: int) -> None:
        start.wait(timeout=30)
        n = len(list(d.glob("*.md"))) + 1     # the old line, verbatim in spirit
        (d / f"{n:03d}-old.md").write_text(f"BODY-{i}", encoding="utf-8")

    threads = [threading.Thread(target=old_send, args=(i,)) for i in range(WRITERS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    survivors = list(d.glob("*.md"))
    assert len(survivors) < WRITERS, (
        "the old counting scheme did NOT collide in this run, so this canary "
        "proved nothing. It is timing-dependent; re-run or raise WRITERS. "
        "Do not delete this test on the strength of one clean run."
    )


def test_sender_defaults_to_coordinator(tmp_path):
    """Every existing Claude call omits --from. It must be unchanged."""
    _isolate(tmp_path)
    mail.cmd_send("target", "no sender given", "BODY")
    text = mail.messages("target")[0].read_text(encoding="utf-8")
    assert "From: coordinator" in text, text.splitlines()[:5]


def test_a_foreign_sender_is_recorded(tmp_path):
    """ChatGPT must be attributable in the file itself, not just by convention."""
    _isolate(tmp_path)
    mail.cmd_send("target", "from chatgpt", "BODY", sender="chatgpt")
    text = mail.messages("target")[0].read_text(encoding="utf-8")
    assert "From: chatgpt" in text, text.splitlines()[:5]


def test_the_format_is_unchanged(tmp_path):
    """Every reader greps these four headers. They must all still be there."""
    _isolate(tmp_path)
    mail.cmd_send("target", "shape check", "BODY", sender="chatgpt")
    p = mail.messages("target")[0]
    text = p.read_text(encoding="utf-8")
    for needed in ("To: target", "From: chatgpt", "Opened: ", "Status: OPEN",
                   "Subject: shape check", "--- INSTRUCTION ---", "--- REPLY ---"):
        assert needed in text, f"missing {needed!r} from the message"
    assert mail.status_of(p) == "OPEN"
    assert p.name.startswith("001-"), p.name


if __name__ == "__main__":
    import tempfile

    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        with tempfile.TemporaryDirectory() as td:
            try:
                fn(td)
                print(f"  ok    {name}")
            except AssertionError as exc:
                failures += 1
                print(f"  FAIL  {name}: {exc}")
    print("\nall good" if not failures else f"\n{failures} FAILED")
    raise SystemExit(1 if failures else 0)
