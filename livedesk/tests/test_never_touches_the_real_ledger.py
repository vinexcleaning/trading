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


def test_the_window_honours_the_redirect_too(tmp_path, monkeypatch):
    """The GUI is what actually did the damage, so it is checked directly
    rather than trusting that fixing the Ledger fixed the caller."""
    tk = pytest.importorskip("tkinter")
    import desk as D
    target = tmp_path / "gui.json"
    monkeypatch.setattr(L, "LEDGER_PATH", target)
    try:
        app = D.Desk()
    except tk.TclError as e:                       # pragma: no cover
        pytest.skip(f"no display: {e}")
    try:
        assert app.ledger.path == target, (
            "the window opened the REAL ledger despite the redirect")
    finally:
        app.stop_flag.set()
        try:
            app.destroy()
        except tk.TclError:
            pass
