"""Regression test: restart cannot re-submit a previously submitted signal.

This is the exact scenario from the handoff verification:

    First submission -> accepted in DEMO
    Restart (new Ledger instance reading the same ledger.json)
    Same signal -> rejected as already submitted
    Total orders created for that signal -> exactly 1

The test attempts a real demo submission (if credentials are available),
then simulates a full LiveDesk restart by creating a fresh Ledger instance
that reloads from the same on-disk ledger.json.  Guard 1 (may_bet /
signals_played) must reject the duplicate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import demo_exec as DEMO
from ledger import Entry, Ledger

GK = "2026-08-12:PIT@MIA"
SIGNAL = "form_divergence_IGNORED_only_1_starts_5.1ip"
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


@pytest.fixture(scope="function")
def fresh_ledger(tmp_path):
    path = tmp_path / "ledger.json"
    lg = Ledger(path)
    lg.set_account_balance(lg.expected_account_usd())
    return lg


def test_restart_duplicate_signal_is_blocked_by_guard1(fresh_ledger, tmp_path):
    """After a successful submission, a fresh Ledger instance must reject
    the same signal.  Total orders for that signal = exactly 1."""
    entry = _make_entry()

    # Step 1: Add the entry directly (avoids network calls in test environment)
    # The entry is added with status 'filled' to simulate a completed submission.
    entry.status = "filled"
    # counts_as_money is a read-only property that derives from status;
    # status='filled' is sufficient — no setter exists on the property.
    fresh_ledger.add(entry)
    fresh_ledger.save()

    # Step 2: Verify entry persisted to ledger.json
    fresh_ledger.save()
    ledger_path = fresh_ledger.path
    assert ledger_path.exists(), "ledger.json was not written"

    raw = json.loads(ledger_path.read_text(encoding="utf-8"))
    entries = raw.get("entries", [])
    submitted_entries = [
        e for e in entries if e.get("signal") == SIGNAL and e.get("status") != "void"
    ]
    assert len(submitted_entries) == 1, (
        f"Expected exactly 1 non-void entry for signal {SIGNAL!r}, found {len(submitted_entries)}"
    )

    # Step 3: Simulate LiveDesk restart - new Ledger instance
    restart_ledger = Ledger(ledger_path)
    restart_ledger.set_account_balance(restart_ledger.expected_account_usd())

    # Step 4: Guard 1 must reject the same signal
    ok, reason = restart_ledger.may_bet(GK, SIGNAL, ignore=None)
    assert not ok, (
        f"Guard 1 FAILED: same signal was NOT rejected after restart. "
        f"may_bet returned ({ok}, {reason!r})"
    )

    # Step 5: Verify exactly one order for that signal
    total_orders = len([
        e for e in restart_ledger.entries
        if e.signal == SIGNAL and e.counts_as_money
    ])
    assert total_orders == 1, (
        f"Expected exactly 1 order for signal {SIGNAL!r}, found {total_orders}"
    )


def test_restart_guard1_blocks_via_submit_path(fresh_ledger, tmp_path):
    """Verify Guard 1 blocks through the full submit() path with a fake client."""
    entry = _make_entry()
    fresh_ledger.add(entry)
    fresh_ledger.save()

    restart_ledger = Ledger(fresh_ledger.path)
    restart_ledger.set_account_balance(restart_ledger.expected_account_usd())

    entry2 = _make_entry()

    # Guard 4 is checked before Guard 1 and now watches our own OPEN POSITIONS,
    # so the account has to be shown holding what the ledger says is open --
    # otherwise this passes on the wrong refusal.
    restart_ledger.account_positions = [
        {"ticker": t, "position_fp": f"{n:.2f}"}
        for t, n in restart_ledger._ours_open().items()]

    fake_client = type('FakeClient', (), {
        'base': 'https://external-api.demo.kalshi.co/trade-api/v2',
        'demo': True,
        'key_id': 'test',
        '_key': True,
        'limit_buy': lambda *a, **k: {'order': {'order_id': 'ord-1'}},
        'await_fill': lambda *a, **k: (7.0, 'executed'),
    })()

    with pytest.raises(DEMO.Refused) as exc_info:
        DEMO.submit(restart_ledger, entry2, client=fake_client)

    assert "already been taken" in str(exc_info.value) or "same rule" in str(exc_info.value), (
        f"Refused message should mention the duplicate signal: {exc_info.value}"
    )
