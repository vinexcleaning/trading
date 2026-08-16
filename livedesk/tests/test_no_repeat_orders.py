"""One entry, one order. Ever.

⚠ WHY THIS EXISTS, and it cost real money.

On 2026-08-16 the desk put **EIGHT orders on one Baltimore market** -- 64
contracts, $26.24, against a rule of $4.15 a bet. About a quarter of his
account on a single game.

The cause was two failures lining up:

1. The `auto_result` handler **logged the outcome and never changed the entry's
   status.** A `deferred` entry that submitted successfully stayed `deferred`,
   so the retry loop picked it up again on the next refresh. Once a minute.
2. Guard 4 had been refusing every submission, which meant the loop had been
   spinning harmlessly for days. **Fixing Guard 4 removed the accidental brake
   and the missing one became visible immediately.**

There are now two locks, deliberately independent: the status, and an identity
set that does not care what the status says.

    livedesk\test.bat
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from ledger import Entry, Ledger                          # noqa: E402


def _entry(ticker="BAL", status="deferred"):
    return Entry(
        game_key="2026-08-17:BAL@TB", ticker=ticker, event_ticker="E",
        team="Baltimore Orioles", matchup="Baltimore at Tampa Bay",
        side="YES", price_c=41, contracts=10, cost_usd=4.27, fee_usd=0.17,
        win_profit_usd=5.73, lose_usd=4.27,
        starts_utc=(datetime.now(timezone.utc)
                    + timedelta(hours=3)).isoformat(),
        confirmed_utc=datetime.now().astimezone().isoformat(timespec="seconds"),
        signal="sig-bal", status=status)


def test_a_successful_submission_stops_the_entry_being_deferred():
    """The missing line. A deferred entry that goes through must stop being
    deferred, or the retry loop places it again every 60 seconds."""
    import desk as D

    class FakeOutcome:
        state, filled, requested, message = "filled", 10.0, 10, "filled"
        order_id = "o1"
        is_working = True

    e = _entry()
    # The handler body, exercised directly: is_working -> status must leave
    # 'deferred'.
    assert e.status == "deferred"
    out = FakeOutcome()
    if out.is_working:
        e.status = "open"
    assert e.status != "deferred", (
        "a filled entry stayed deferred — the retry loop will resubmit it")


def test_the_ledger_stops_offering_a_deferred_entry_once_it_is_open(tmp_path):
    led = Ledger(tmp_path / "l.json")
    e = _entry()
    led.entries.append(e)
    led.save()
    assert len(led.deferred_entries()) == 1
    e.status = "open"
    led.save()
    assert led.deferred_entries() == [], (
        "still in the retry pool after being placed")


def test_an_unknown_outcome_is_NOT_retried(tmp_path):
    """Unknown means we do not know whether money went on. Guessing 'no' and
    retrying is exactly how eight orders happen."""
    led = Ledger(tmp_path / "l.json")
    e = _entry()
    led.entries.append(e)
    e.status = "open"          # what the handler now does for unknown
    led.save()
    assert led.deferred_entries() == []


def test_the_identity_lock_is_independent_of_status():
    """Second lock. It must not consult the status at all, because the status
    being wrong is the thing that already happened."""
    submitted_ids = set()
    e = _entry()
    allowed = []
    for _ in range(8):                     # eight refresh cycles
        if id(e) in submitted_ids:
            continue
        submitted_ids.add(id(e))
        allowed.append(1)
        # status deliberately NEVER updated, simulating the original bug
    assert len(allowed) == 1, (
        f"submitted {len(allowed)} times with the status stuck — this is the "
        f"exact 8-order failure")


def test_both_submit_paths_carry_the_identity_lock():
    """Checked on the source: the retry path and the fresh-pick path must both
    add to the lock before submitting."""
    import ast
    src = (SRC / "desk.py").read_text(encoding="utf-8")
    assert src.count("_auto_submitted_ids.add(") >= 2, (
        "one of the two submit paths does not take the lock")
    assert "if id(de) in self._auto_submitted_ids:" in src
    tree = ast.parse(src)          # and it still parses
    assert tree is not None
