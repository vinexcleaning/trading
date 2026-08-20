"""The test suite must never write to his real ledger.

⚠ THIS EXISTS BECAUSE IT ALREADY HAPPENED. On 2026-08-16 a test run **deleted
every entry from `data/ledger.json`** -- his actual record of his actual money.

`test_button_never_moves.py` sets `ledger.LEDGER_PATH` to a temp file before
building the window. That never worked:

    def __init__(self, path: Path = LEDGER_PATH):   # <- bound at DEFINITION

A default argument is evaluated once, when the function is defined. Reassigning
the module global afterwards changes nothing, so `Desk()` opened the real file
and the per-test fixture's `entries.clear()` + `save()` wiped it.

**150 tests passed while that was happening**, because not one of them asked
where the tests were writing. That is the whole lesson: a suite can be green
and still be destroying the thing it is meant to protect.

    livedesk\\test.bat
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import ledger as L                                       # noqa: E402

REAL = Path(__file__).resolve().parents[1] / "data" / "ledger.json"
REAL_LOCK = Path(__file__).resolve().parents[1] / "data" / "desk.lock"


def test_the_path_is_resolved_when_called_not_when_defined(tmp_path,
                                                           monkeypatch):
    """The exact mechanism that failed. Monkeypatching the module global MUST
    redirect a Ledger built with no argument."""
    target = tmp_path / "redirected.json"
    monkeypatch.setattr(L, "LEDGER_PATH", target)
    assert L.Ledger().path == target, (
        "Ledger() ignored the patched LEDGER_PATH — this is exactly the bug "
        "that deleted his ledger on 2026-08-16")


def test_an_explicit_path_still_wins(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "LEDGER_PATH", tmp_path / "ignored.json")
    chosen = tmp_path / "chosen.json"
    assert L.Ledger(chosen).path == chosen


def test_saving_a_redirected_ledger_does_not_touch_the_real_file(tmp_path,
                                                                 monkeypatch):
    before = REAL.read_bytes() if REAL.exists() else None
    monkeypatch.setattr(L, "LEDGER_PATH", tmp_path / "safe.json")
    led = L.Ledger()
    led.entries.clear()
    led.save()
    after = REAL.read_bytes() if REAL.exists() else None
    assert after == before, "a test wrote to the real ledger"


def test_the_window_builds_its_ledger_with_no_hardcoded_path():
    """The GUI is what actually did the damage, so it is checked directly.

    ⚠ CHECKED ON THE SOURCE, NOT BY OPENING A WINDOW. The first version of this
    test built a second `Desk()`, which fails about half the time with
    `invalid command name "tcl_findLibrary"` -- a known flake already written up
    in `test_button_never_moves.py`. It therefore **SKIPPED**, with
    `LIVEDESK_REQUIRE_GUI=1` set, which is precisely the "a silently skipped
    test reads as a green run" failure this repo keeps recording. A test
    guarding against silent data loss must not itself be able to go quiet.

    So it asserts the property that matters -- the window asks for the ledger
    with no path, and therefore honours whatever `LEDGER_PATH` says at the
    moment it is called.
    """
    import ast
    src = (SRC / "desk.py").read_text(encoding="utf-8")
    calls = [n for n in ast.walk(ast.parse(src))
             if isinstance(n, ast.Call)
             and getattr(n.func, "id", "") == "Ledger"]
    assert calls, "desk.py never builds a Ledger — has it been renamed?"
    for c in calls:
        assert not c.args and not c.keywords, (
            "desk.py passes a path to Ledger(). It must pass nothing, so the "
            "path is resolved from LEDGER_PATH at call time and a test can "
            "redirect it. Hardcoding it here is how his ledger was deleted.")


# --------------------------------------------------------------------------
# ⚠ ADDED 2026-08-19, AFTER IT HAPPENED A SECOND TIME IN A DIFFERENT FILE.
#
# `test_one_machine.py` called `onemachine.heartbeat()` with no arguments. The
# default is his REAL `data/desk.lock`, so a test run left a live lock behind
# held by a pytest process that had already exited -- and the next time he
# opened the desk it would have refused to start and told him to close a window
# that was not open.
#
# Nobody noticed from the test output. It was found by RUNNING the tool
# afterwards and reading what it printed, which is the same way the ledger
# deletion was found. So the rule is generalised here rather than left as one
# more one-off fix: **every real path this project can write gets checked.**

import onemachine as OM                                   # noqa: E402


def test_every_real_path_this_project_writes_is_known():
    """If a new one appears it has to be added here deliberately, rather than
    being discovered by him when his desk refuses to open."""
    assert set(OM.real_paths()) == {OM.LOCK_PATH}


def test_the_lock_path_is_resolved_when_called_not_when_defined(tmp_path,
                                                                monkeypatch):
    """Same mechanism as the ledger bug. Reassigning the module global MUST
    redirect a call that passes no path -- if it does not, `conftest.py`'s
    protection is decorative and every test is writing his real file."""
    target = tmp_path / "redirected.lock"
    monkeypatch.setattr(OM, "LOCK_PATH", target)
    OM.write_lock()
    assert target.exists(), "the redirect did nothing -- this is the 2026-08-16 bug"
    assert OM.read_lock()["pid"] == os.getpid()


def test_a_full_test_run_leaves_no_lock_behind():
    """⚠ CHECKS THE LITERAL REAL PATH, not `OM.LOCK_PATH` -- conftest patches
    that global for every test, so reading it here would check the temp file
    and pass no matter what. The first version of this test did exactly that
    and would have been useless."""
    assert not REAL_LOCK.exists(), (
        f"a test wrote {REAL_LOCK} -- his desk would refuse to open, "
        f"blaming a window that is not there")
