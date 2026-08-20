"""The guard against the desk running on two computers at once.

    livedesk\\test.bat

⚠ NOTHING HERE TOUCHES THE NETWORK. Every test injects its own claims. A test
that really posted to ntfy would be slow, would fail on a train, and would
publish this machine's name to a public topic on every run.

The failure this guards is the only irreversible one in the move to the laptop:
two desks both placing the same bet on the same signal, and both acting on the
same position, with no way for either to see the other.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import onemachine                                          # noqa: E402
sys.path.insert(0, str(SRC.parent.parent / "kalshi-inplay-bot"))
import notify                                              # noqa: E402

_REAL_TOPIC = onemachine._topic


@pytest.fixture
def lock(tmp_path):
    return tmp_path / "desk.lock"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Default every test to 'no claim channel configured'. A test that wants
    the cross-machine path says so explicitly."""
    monkeypatch.setattr(onemachine, "_topic", lambda: "")


def _write(lock, machine="OTHER-PC", pid=999999, age_sec=0.0):
    lock.write_text(json.dumps({"machine": machine, "pid": pid,
                                "at": time.time() - age_sec}), encoding="utf-8")


# ------------------------------------------------------------ the lock file

def test_a_second_window_on_this_machine_is_refused(lock):
    _write(lock)
    ok, msg = onemachine.may_start(lock_path=lock)
    assert not ok
    assert "ALREADY OPEN on this computer" in msg


def test_our_own_lock_never_blocks_us(lock):
    """⚠ THE SHAPE OF BUG THAT MADE THE PRACTICE BUTTON UNCLICKABLE: a check
    that sees its own record and refuses. Guard 1 did it, Guard 4 did it the
    day it was re-pointed. Third time, so it gets a test."""
    _write(lock, pid=os.getpid())
    assert onemachine.may_start(lock_path=lock)[0] is True


def test_a_stale_lock_from_a_crash_does_not_block_him_for_ever(lock):
    """A desk that crashed leaves its lock behind. If that were permanent he
    would have to know to delete a file he has never heard of, at the moment
    he most wants the tool working."""
    _write(lock, age_sec=onemachine.STALE_SEC + 60)
    assert onemachine.may_start(lock_path=lock)[0] is True


def test_a_lock_four_beats_old_is_still_believed(lock):
    """The window refreshes every 60 seconds. A single slow refresh must not
    hand the desk to a second copy."""
    _write(lock, age_sec=120)
    assert onemachine.may_start(lock_path=lock)[0] is False


def test_no_lock_at_all_is_fine(lock):
    assert onemachine.may_start(lock_path=lock)[0] is True


def test_a_corrupt_lock_file_does_not_crash_the_desk(lock):
    lock.write_text("{{{ not json", encoding="utf-8")
    assert onemachine.may_start(lock_path=lock)[0] is True


def test_closing_the_window_frees_it_immediately(lock):
    """Otherwise he closes it on the desktop, walks to the laptop, and is told
    to close something he has already closed -- for five minutes."""
    onemachine.write_lock(lock)
    assert lock.exists()
    onemachine.clear_lock(lock)
    assert not lock.exists()


# -------------------------------------------------- the cross-machine claim

def _claims(monkeypatch, rows, ok=True):
    monkeypatch.setattr(onemachine, "_topic", lambda: "t")
    monkeypatch.setattr(onemachine, "read_claims", lambda *a, **k: (rows, ok))


def test_the_other_machine_running_it_blocks_us(monkeypatch, lock):
    _claims(monkeypatch, [{"machine": "LAPTOP-X", "at": time.time()}])
    ok, msg = onemachine.may_start(lock_path=lock)
    assert not ok
    assert "LAPTOP-X" in msg, "it must NAME the machine, or he cannot act on it"


def test_our_own_claim_from_the_last_cycle_does_not_block_us(monkeypatch, lock):
    """We post a claim every 60 seconds and then read the same topic. Reading
    our own beat as a rival is the identical self-blocking bug as above, over
    a different channel."""
    _claims(monkeypatch, [{"machine": onemachine._me(), "at": time.time()}])
    assert onemachine.may_start(lock_path=lock)[0] is True


def test_a_claim_from_a_machine_that_has_since_been_closed_expires(monkeypatch,
                                                                   lock):
    _claims(monkeypatch, [{"machine": "LAPTOP-X",
                           "at": time.time() - onemachine.STALE_SEC - 60}])
    assert onemachine.may_start(lock_path=lock)[0] is True


def test_it_STARTS_when_it_could_not_check(monkeypatch, lock):
    """⚠ THE DELIBERATE LENIENCY, AND THE REASON FOR IT. Failing shut would
    mean no internet equals no desk. He would work around that, and a guard he
    works around protects nothing. It blocks on EVIDENCE of a second desk, not
    on the absence of evidence -- and it says out loud that it could not
    check, because a guard that quietly did nothing reads exactly like a guard
    that passed."""
    _claims(monkeypatch, [], ok=False)
    ok, msg = onemachine.may_start(lock_path=lock)
    assert ok is True
    assert "COULD NOT CHECK" in msg
    assert "CLOSED on the other machine" in msg


def test_a_clean_check_says_nothing_at_all(monkeypatch, lock):
    """Silence when everything is fine. A reassuring message every startup is
    a message he stops reading."""
    _claims(monkeypatch, [])
    assert onemachine.may_start(lock_path=lock) == (True, "")


def test_a_stranger_posting_on_the_topic_is_ignored(monkeypatch, lock):
    """⚠ FOUND BY RUNNING IT, NOT BY A TEST. A debug probe reading
    'probe-from-livedesk' was read as a computer name and the desk refused to
    start. The ntfy topic is PUBLIC to anyone who knows it, so a claim must
    carry the exact tag or it is not a claim."""
    monkeypatch.setattr(onemachine, "_topic", lambda: "t")

    class R:
        text = "\n".join([
            json.dumps({"event": "message", "message": "hello there",
                        "time": time.time()}),
            json.dumps({"event": "message", "message": "probe-from-livedesk",
                        "time": time.time()}),
        ])

    monkeypatch.setattr(onemachine, "_HOST", "https://example.invalid")
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: R())
    rows, checked = onemachine.read_claims("t")
    assert checked is True
    assert rows == [], "untagged chatter is not a claim"


def test_a_properly_tagged_claim_is_read(monkeypatch):
    class R:
        text = json.dumps({"event": "message",
                           "message": onemachine._TAG + "LAPTOP-X",
                           "time": time.time()})

    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: R())
    rows, checked = onemachine.read_claims("t")
    assert checked is True
    assert rows and rows[0]["machine"] == "LAPTOP-X"


def test_no_topic_means_it_cannot_check_not_that_it_is_clear(monkeypatch, lock):
    """'Nobody else is running' and 'I could not find out' are different
    answers. Confusing an empty reading with a missing one is what voided a
    live $4.68 position on 2026-08-16."""
    rows, checked = onemachine.read_claims("")
    assert rows == [] and checked is False


# ------------------------------------------------------------- it is quiet

def test_the_claim_never_reaches_his_phone(monkeypatch):
    """It posts every 60 seconds. On his real topic that is 1,440 pushes a day
    and he would uninstall the app."""
    monkeypatch.setattr(onemachine, "_topic", _REAL_TOPIC)   # undo the autouse
    monkeypatch.setenv("KALSHI_NTFY_TOPIC", "his-real-topic")
    assert onemachine._topic() == "his-real-topic-deskclaim"

    seen = {}

    class FakeNotifier:
        def __init__(self, topic=None, **k):
            seen["topic"] = topic

        def send(self, message, **k):
            seen.update(message=message, **k)

    import notify
    monkeypatch.setattr(notify, "Notifier", FakeNotifier)
    onemachine.post_claim()
    assert seen["priority"] == "min", "a claim must never buzz his phone"
    assert seen["topic"].endswith("-deskclaim")
    assert seen["message"].startswith(onemachine._TAG)


def test_a_failed_claim_is_not_an_exception(monkeypatch, lock):
    """This runs inside the refresh loop, next to the code that places bets."""
    import requests

    def boom(*a, **k):
        raise RuntimeError("no network")

    monkeypatch.setattr(onemachine, "_topic", _REAL_TOPIC)   # undo the autouse
    monkeypatch.setenv("KALSHI_NTFY_TOPIC", "x")
    import notify
    monkeypatch.setattr(notify, "Notifier", boom)
    monkeypatch.setattr(requests, "get", boom)
    assert onemachine.post_claim() is False
    assert onemachine.read_claims() == ([], False)
    # ⚠ `lock`, NOT THE DEFAULT. The first version called heartbeat() with no
    # arguments and wrote HIS REAL data/desk.lock -- found by running the tool
    # afterwards and seeing a live lock held by a dead pytest process, which
    # would have refused to open his desk. Same shape as the default argument
    # that let a green test run delete his real ledger.
    onemachine.heartbeat(lock_path=lock)          # must not raise


def test_every_message_he_could_see_is_plain_ascii(monkeypatch, lock):
    """The Windows console is cp1252, and this one prints before any window
    exists -- so a fancy dash here means he sees a crash instead of the
    reason he is being stopped."""
    _claims(monkeypatch, [{"machine": "LAPTOP-X", "at": time.time()}])
    onemachine.may_start(lock_path=lock)[1].encode("cp1252")
    _claims(monkeypatch, [], ok=False)
    onemachine.may_start(lock_path=lock)[1].encode("cp1252")
    _write(lock)
    monkeypatch.setattr(onemachine, "_topic", lambda: "")
    onemachine.may_start(lock_path=lock)[1].encode("cp1252")
