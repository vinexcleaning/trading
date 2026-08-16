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

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import ledger as L                                       # noqa: E402

REAL = Path(__file__).resolve().parents[1] / "data" / "ledger.json"


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
