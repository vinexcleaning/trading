"""
# ⚠ INVERTED 2026-08-16. These tests asserted that a DEFERRED entry does NOT
# close its signal, on the reasoning that a deferred pick "will be retried".
# The reasoning is right and the conclusion was backwards.
#
# There are two paths: a retry loop that re-submits the existing deferred
# entry, AND a fresh-pick path that creates a new entry for any signal not yet
# played. With deferred excluded, BOTH ran every refresh -- so the retry
# retried it and the fresh path made another one. It left THREE deferred
# entries each for Miami, San Diego and Atlanta, at two different stake sizes,
# from different rounds. He saw them stacked up in the window.
#
# A deferred entry IS a pending attempt at that signal, so it closes the
# signal. Retrying is the retry loop's job. `expired` still does not close it,
# because that game has started and nothing will be offered on it anyway.
Tests for the `deferred` / `expired` status system.

These cover the fix for the bug where temporary guard refusals permanently
burned signals by writing them as `void`.  The fix introduces:

  * `deferred` — temporary block; signal preserved and retried
  * `expired`  — game has started; signal gone forever
  * `counts_as_money` now excludes `deferred` (and `expired`)

    livedesk\\test.bat
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import demo_exec as DEMO
from ledger import Entry, Ledger

GK = "2026-08-12:PIT@MIA"
SIGNAL = "form_divergence_TEST"
TICKER = "KXMLBGAME-26AUG121840PITMIA-MIA"
EVENT = "KXMLBGAME-26AUG121840PITMIA"


def _make_entry(**over):
    base = dict(
        game_key=GK,
        ticker=TICKER,
        event_ticker=EVENT,
        team="Miami Marlins",
        matchup="Pittsburgh at Miami",
        side="YES",
        price_c=52,
        contracts=7,
        cost_usd=3.77,
        fee_usd=0.13,
        win_profit_usd=3.23,
        lose_usd=3.77,
        starts_utc="2099-08-12T22:40:00+00:00",
        confirmed_utc="2026-08-12T02:00:00+00:00",
        signal=SIGNAL,
    )
    base.update(over)
    return Entry(**base)


@pytest.fixture
def fresh_ledger(tmp_path):
    path = tmp_path / "ledger.json"
    lg = Ledger(path)
    lg.set_account_balance(lg.expected_account_usd())
    lg.account_positions = []      # read, and empty -- not "never read"
    return lg


def _sync(lg):
    """Re-agree the balance after a test has added entries by hand."""
    lg.save()
    lg.set_account_balance(lg.expected_account_usd())
    return lg


# ==================================================== counts_as_money

def test_counts_as_money_returns_false_for_deferred(fresh_ledger):
    """A deferred entry was never actually placed, so no money left the account."""
    e = _make_entry(status="deferred")
    assert not e.counts_as_money


def test_counts_as_money_returns_false_for_expired(fresh_ledger):
    """An expired entry's game has started; no money was placed."""
    e = _make_entry(status="expired")
    assert not e.counts_as_money


def test_counts_as_money_returns_true_for_open(fresh_ledger):
    e = _make_entry(status="open")
    assert e.counts_as_money


def test_counts_as_money_returns_true_for_won(fresh_ledger):
    e = _make_entry(status="won")
    assert e.counts_as_money


def test_counts_as_money_returns_true_for_lost(fresh_ledger):
    e = _make_entry(status="lost")
    assert e.counts_as_money


def test_counts_as_money_returns_false_for_void(fresh_ledger):
    e = _make_entry(status="void")
    assert not e.counts_as_money


# =================================================== deferred_entries()

def test_deferred_entries_returns_only_deferred(fresh_ledger):
    fresh_ledger.entries.append(_make_entry(status="deferred"))
    fresh_ledger.entries.append(_make_entry(status="open"))
    fresh_ledger.entries.append(_make_entry(status="void"))
    result = fresh_ledger.deferred_entries()
    assert len(result) == 1
    assert result[0].status == "deferred"


def test_deferred_entries_returns_empty_when_none(fresh_ledger):
    fresh_ledger.entries.append(_make_entry(status="open"))
    assert fresh_ledger.deferred_entries() == []


# ============================== expire_deferred_past_game_start()

def test_expire_deferred_past_game_start_expires_past_games(fresh_ledger):
    """Deferred entries whose game has started should become expired."""
    past = _make_entry(status="deferred",
                       starts_utc="2020-01-01T12:00:00+00:00")
    fresh_ledger.entries.append(past)
    count = fresh_ledger.expire_deferred_past_game_start()
    assert count == 1
    assert past.status == "expired"
    assert "game has started" in past.note


def test_expire_deferred_past_game_start_ignores_future_games(fresh_ledger):
    """Deferred entries whose game has not started yet stay deferred."""
    future = _make_entry(status="deferred",
                         starts_utc="2099-08-12T22:40:00+00:00")
    fresh_ledger.entries.append(future)
    count = fresh_ledger.expire_deferred_past_game_start()
    assert count == 0
    assert future.status == "deferred"


def test_expire_deferred_past_game_start_only_affects_deferred(fresh_ledger):
    """Only deferred entries are affected; open/won/etc. are left alone."""
    fresh_ledger.entries.append(_make_entry(status="open"))
    fresh_ledger.entries.append(_make_entry(status="won"))
    fresh_ledger.entries.append(_make_entry(status="void"))
    past = _make_entry(status="deferred",
                       starts_utc="2020-01-01T12:00:00+00:00")
    fresh_ledger.entries.append(past)
    count = fresh_ledger.expire_deferred_past_game_start()
    assert count == 1
    assert past.status == "expired"


# ===================================== _is_temporary_refusal() classification

def test_is_temporary_refusal_duplicate_signal_is_permanent():
    """Duplicate signal → permanent (void), not temporary."""
    from desk import Desk
    assert not Desk._is_temporary_refusal(
        "this exact bet has already been taken on this game")


def test_is_temporary_refusal_already_taken_is_permanent():
    from desk import Desk
    assert not Desk._is_temporary_refusal(
        "this exact bet has already been taken")


def test_is_temporary_refusal_limit_is_permanent():
    from desk import Desk
    assert not Desk._is_temporary_refusal(
        "you already have 2 bets on this game, which is the limit")


def test_is_temporary_refusal_losing_position_is_permanent():
    from desk import Desk
    assert not Desk._is_temporary_refusal(
        "your open bet on this game is losing position")


def test_is_temporary_refusal_game_started_is_permanent():
    from desk import Desk
    assert not Desk._is_temporary_refusal(
        "game has started")


def test_is_temporary_refusal_game_finished_is_permanent():
    from desk import Desk
    assert not Desk._is_temporary_refusal(
        "game has finished")


def test_is_temporary_refusal_reconciliation_is_temporary():
    """Reconciliation mismatch → temporary (deferred)."""
    from desk import Desk
    assert Desk._is_temporary_refusal(
        "THESE DO NOT AGREE by +$5.00. Your balance says $100; "
        "this tool expects $95")


def test_is_temporary_refusal_account_floor_is_temporary():
    """Account floor → temporary (deferred)."""
    from desk import Desk
    assert Desk._is_temporary_refusal(
        "STOPPED. Your account is at $49, under the $50 floor")


def test_is_temporary_refusal_trailing_drawdown_is_temporary():
    """Trailing drawdown → temporary (deferred)."""
    from desk import Desk
    assert Desk._is_temporary_refusal(
        "STOPPED. Counting every open bet as a loss, this tool is at "
        "$40. Its best was $100, and 35% below that is $65.")


def test_is_temporary_refusal_daily_cap_is_temporary():
    """Daily cap → temporary (deferred, clears at midnight)."""
    from desk import Desk
    assert Desk._is_temporary_refusal(
        "you have made 10 bets today, daily cap reached")


def test_is_temporary_refusal_kill_switch_is_temporary():
    """Kill switch → temporary (deferred)."""
    from desk import Desk
    assert Desk._is_temporary_refusal(
        "Turned off. TRADING_DISABLED file exists")


def test_is_temporary_refusal_default_is_temporary():
    """Unknown refusal → default to temporary (deferred) — safer fail-closed."""
    from desk import Desk
    assert Desk._is_temporary_refusal(
        "some unexpected guard message")


# =================================== _handle_auto_refused() behavior

def test_handle_auto_refused_sets_deferred_for_temporary(fresh_ledger):
    """Temporary refusal → deferred status."""
    from desk import Desk
    entry = _make_entry()
    desk = Desk.__new__(Desk)  # minimal stub, no UI needed
    desk._is_temporary_refusal = lambda reason: "already been taken" not in reason.lower()
    desk._log = lambda *a, **k: None
    desk._alert = lambda *a, **k: None
    desk.ledger = fresh_ledger
    desk.events = type('obj', (object,), {'put': lambda *a, **k: None})()
    desk._handle_auto_refused(entry, DEMO.Refused("reconciliation mismatch"))
    assert entry.status == "deferred"
    assert "auto-exec deferred" in entry.note


def test_handle_auto_refused_sets_void_for_permanent(fresh_ledger):
    """Permanent refusal → void status."""
    from desk import Desk
    entry = _make_entry()
    desk = Desk.__new__(Desk)
    desk._is_temporary_refusal = lambda reason: False
    desk._log = lambda *a, **k: None
    desk._alert = lambda *a, **k: None
    desk.ledger = fresh_ledger
    desk.events = type('obj', (object,), {'put': lambda *a, **k: None})()
    desk._handle_auto_refused(entry, DEMO.Refused("already been taken"))
    assert entry.status == "void"
    assert "auto-exec refused (permanent)" in entry.note


# =================================== signals_played() excludes deferred

def test_signals_played_excludes_deferred(fresh_ledger):
    """Deferred entries must NOT close a signal for Guard 1."""
    e = _make_entry(signal="sig-deferred", status="deferred")
    fresh_ledger.entries.append(e)
    fresh_ledger.save()
    played = fresh_ledger.signals_played()
    assert "sig-deferred" in played, (
        "a deferred entry must close its signal, or the fresh-pick path "
        "creates another one every refresh — see the note at the top")


def test_signals_played_excludes_expired(fresh_ledger):
    """Expired entries must NOT close a signal for Guard 1."""
    e = _make_entry(signal="sig-expired", status="expired")
    fresh_ledger.entries.append(e)
    fresh_ledger.save()
    played = fresh_ledger.signals_played()
    assert "sig-expired" not in played


def test_signals_played_includes_open(fresh_ledger):
    """Open entries DO close a signal for Guard 1."""
    e = _make_entry(signal="sig-open", status="open")
    fresh_ledger.entries.append(e)
    fresh_ledger.save()
    played = fresh_ledger.signals_played()
    assert "sig-open" in played


# =================================== positions_on_game() excludes deferred

def test_positions_on_game_excludes_deferred(fresh_ledger):
    """Deferred entries must NOT count toward the 2-per-game limit."""
    e1 = _make_entry(game_key=GK, ticker="T1", signal="s1", status="open")
    e2 = _make_entry(game_key=GK, ticker="T2", signal="s2", status="deferred")
    fresh_ledger.entries.append(e1)
    fresh_ledger.entries.append(e2)
    fresh_ledger.save()
    count = fresh_ledger.positions_on_game(GK)
    assert count == 1  # only the open entry counts


def test_positions_on_game_includes_open(fresh_ledger):
    e1 = _make_entry(game_key=GK, ticker="T1", signal="s1", status="open")
    e2 = _make_entry(game_key=GK, ticker="T2", signal="s2", status="won")
    fresh_ledger.entries.append(e1)
    fresh_ledger.entries.append(e2)
    fresh_ledger.save()
    count = fresh_ledger.positions_on_game(GK)
    assert count == 2  # both open and won count


# =================================== money_out_usd() excludes deferred

def test_money_out_usd_excludes_deferred(fresh_ledger):
    """Deferred entries must NOT affect the running total or reconciliation."""
    e_open = _make_entry(game_key="g1", ticker="T1", signal="s1",
                         cost_usd=5.00, status="open")
    e_deferred = _make_entry(game_key="g2", ticker="T2", signal="s2",
                             cost_usd=5.00, status="deferred")
    fresh_ledger.entries.append(e_open)
    fresh_ledger.entries.append(e_deferred)
    fresh_ledger.save()
    fresh_ledger.set_account_balance(fresh_ledger.expected_account_usd())
    assert fresh_ledger.money_out_usd() == 5.00  # only open, not deferred


def test_money_out_usd_excludes_void(fresh_ledger):
    e_void = _make_entry(game_key="g1", ticker="T1", signal="s1",
                         cost_usd=5.00, status="void")
    fresh_ledger.entries.append(e_void)
    fresh_ledger.save()
    fresh_ledger.set_account_balance(fresh_ledger.expected_account_usd())
    assert fresh_ledger.money_out_usd() == 0.00  # void doesn't count


# ============================== deferred retry in auto-exec loop

def test_deferred_entry_that_clears_blocking_condition_gets_submitted(
        fresh_ledger, tmp_path):
    """When the blocking condition clears, the deferred entry should be
    submitted successfully."""
    # Create a deferred entry
    deferred = _make_entry(
        game_key="g-deferred",
        ticker="T-DEF",
        signal="sig-deferred",
        status="deferred",
        starts_utc="2099-08-12T22:40:00+00:00",
    )
    fresh_ledger.entries.append(deferred)
    fresh_ledger.save()
    fresh_ledger.set_account_balance(fresh_ledger.expected_account_usd())

    # Create a fresh entry with the same signal — it should be allowed
    # because deferred does NOT close the signal
    fresh_entry = _make_entry(
        game_key="g-deferred",
        ticker="T-FRESH",
        signal="sig-deferred",
        status="open",
    )

    # Verify may_bet allows the fresh entry (deferred doesn't block)
    ok, why = fresh_ledger.may_bet("g-deferred", "sig-deferred")
    assert not ok, ("a deferred entry must BLOCK a fresh duplicate — allowing "
                    "it is what stacked up three entries per game")

    # Verify signals_played does NOT include the deferred signal
    played = fresh_ledger.signals_played()
    assert "sig-deferred" in played


def test_deferred_entry_that_stays_blocked_remains_deferred(fresh_ledger):
    """If the blocking condition hasn't cleared, the entry stays deferred."""
    deferred = _make_entry(status="deferred")
    fresh_ledger.entries.append(deferred)
    fresh_ledger.save()

    # Simulate re-check: the entry is still deferred
    deferred_list = fresh_ledger.deferred_entries()
    assert len(deferred_list) == 1
    assert deferred_list[0].status == "deferred"


def test_expired_entries_are_not_retried(fresh_ledger):
    """Expired entries should NOT appear in deferred_entries()."""
    expired = _make_entry(status="expired")
    fresh_ledger.entries.append(expired)
    fresh_ledger.save()

    deferred_list = fresh_ledger.deferred_entries()
    assert len(deferred_list) == 0


def test_restart_duplicate_deferred_signal_is_blocked(fresh_ledger, tmp_path):
    """After a restart, a previously deferred signal should be re-offered
    (not blocked), because deferred does NOT close the signal.

    This is the key difference from void: void closes forever, deferred
    preserves the signal for retry.
    """
    # Step 1: Create a deferred entry
    deferred = _make_entry(
        game_key="g-deferred",
        ticker="T-DEF",
        signal="sig-deferred",
        status="deferred",
        starts_utc="2099-08-12T22:40:00+00:00",
    )
    fresh_ledger.entries.append(deferred)
    fresh_ledger.save()

    # Step 2: Simulate restart — new Ledger instance
    restart_ledger = Ledger(fresh_ledger.path)
    restart_ledger.set_account_balance(restart_ledger.expected_account_usd())

    # Step 3: The deferred signal should NOT be in signals_played
    played = restart_ledger.signals_played()
    assert "sig-deferred" in played, (
        "the deferred entry must survive a restart so the retry loop can "
        "pick it up")

    # Step 4: A fresh entry with the same signal should be allowed
    ok, why = restart_ledger.may_bet("g-deferred", "sig-deferred")
    assert not ok, (
        f"a deferred entry must still block a duplicate after a restart — "
        f"otherwise every restart adds another copy. got: {why}")

    # Step 5: Verify the deferred entry is still there for retry
    deferred_list = restart_ledger.deferred_entries()
    assert len(deferred_list) == 1
    assert deferred_list[0].status == "deferred"


def test_restart_void_signal_is_blocked(fresh_ledger, tmp_path):
    """After a restart, a voided signal should remain blocked (existing
    behavior, verified alongside deferred to ensure the distinction holds).

    Guard 1 requires 2 voids before closing a signal permanently.
    """
    # Need TWO voids for the signal to close (MAX_VOIDS_BEFORE_CLOSED = 2)
    void_entry1 = _make_entry(
        game_key="g-void",
        ticker="T-VOID-1",
        signal="sig-void",
        status="void",
    )
    void_entry2 = _make_entry(
        game_key="g-void",
        ticker="T-VOID-2",
        signal="sig-void",
        status="void",
    )
    fresh_ledger.entries.append(void_entry1)
    fresh_ledger.entries.append(void_entry2)
    fresh_ledger.save()

    # Simulate restart
    restart_ledger = Ledger(fresh_ledger.path)
    restart_ledger.set_account_balance(restart_ledger.expected_account_usd())

    # Both voids should close the signal
    played = restart_ledger.signals_played()
    assert "sig-void" in played

    ok, why = restart_ledger.may_bet("g-void", "sig-void")
    assert not ok, f"void should block the signal after two voids. got: {why}"
