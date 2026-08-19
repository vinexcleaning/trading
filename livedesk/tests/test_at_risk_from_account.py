"""What is riding comes from HIS ACCOUNT, not from the ledger's own rows.

⚠ THIS FEEDS THE STOP, so it is a money defect and not a display one.
`worst_case_total_usd()` subtracts what is at risk, so an inflated figure walks
the tool toward its own cut-off.

On 2026-08-19 the ledger carried **$35.69 of positions against $12.34 actually
held** -- $23 of phantoms -- which put the tool $19 "under" a floor it was
really $4 above. That is the same shape as the stop that fired on 2026-08-17 and
cost a whole window: a cut-off tripped by bookkeeping rather than by losses.

It then drifted the OTHER way -- positions he holds marked as no longer open --
which is the same defect with the sign flipped. Both directions are fixed by the
same rule: **the account decides.**

    livedesk\test.bat
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from ledger import ACCOUNT_FLOOR_USD, Entry, Ledger       # noqa: E402


@pytest.fixture
def led(tmp_path):
    lg = Ledger(tmp_path / "ledger.json")
    lg.account_positions = []
    return lg


def _row(ticker, size, exposure):
    return {"ticker": ticker, "position_fp": f"{size:.2f}",
            "market_exposure_dollars": f"{exposure:.6f}",
            "fees_paid_dollars": "0.000000",
            "realized_pnl_dollars": "0.000000"}


def _entry(led, ticker, cost, status="open", team="A Team"):
    e = Entry(game_key=f"2026-08-19:{ticker}", ticker=ticker, event_ticker="E",
              team=team, matchup="a at b", side="YES", price_c=50,
              contracts=10, cost_usd=cost, fee_usd=0.05,
              win_profit_usd=10 - cost, lose_usd=cost,
              starts_utc=(datetime.now(timezone.utc)
                          + timedelta(hours=4)).isoformat(),
              confirmed_utc=datetime.now().astimezone().isoformat(
                  timespec="seconds"),
              signal=f"sig-{ticker}", status=status)
    led.entries.append(e)
    led.save()
    return e


# ---------------------------------------------------- the phantom problem

def test_a_phantom_entry_counts_for_NOTHING(led):
    """The ledger says open; the account has never heard of it."""
    _entry(led, "REAL", 3.00)
    _entry(led, "PHANTOM", 7.00)
    led.account_positions = [_row("REAL", 6, 3.00)]
    assert led.at_risk_usd() == pytest.approx(3.00), (
        "a position he does not hold was counted against his floor")


def test_the_exact_shape_that_would_have_stopped_him(led):
    """$35.69 believed against $12.34 held put the tool $19 'under' a floor it
    was really $4 above."""
    for i in range(5):
        _entry(led, f"PHANTOM{i}", 4.67)
    _entry(led, "REAL", 12.34)
    led.account_positions = [_row("REAL", 20, 12.34)]
    led.account_start_usd = 68.57
    led.set_account_balance(56.23)
    assert led.at_risk_usd() == pytest.approx(12.34)
    assert led.worst_case_total_usd() > ACCOUNT_FLOOR_USD
    assert led.paused()[0] is False, "a bookkeeping error paused a live bot"


# ------------------------------------------------- and the other direction

def test_a_held_position_is_counted_even_if_the_row_drifted(led):
    """The same defect with the sign flipped: he holds it, the ledger had
    written it off as awaiting-settlement."""
    _entry(led, "HELD", 4.05, status="awaiting-settlement")
    led.account_positions = [_row("HELD", 7, 3.84)]
    assert led.at_risk_usd() == pytest.approx(3.84)


def test_the_amount_is_the_ACCOUNTS_not_the_ledgers(led):
    """It filled cheaper than it asked. The account's number wins."""
    _entry(led, "OURS", 4.05)
    led.account_positions = [_row("OURS", 7, 3.84)]
    assert led.at_risk_usd() == pytest.approx(3.84)


# ------------------------------------------------------- and his own bets

def test_HIS_own_position_is_not_counted_as_riding(led):
    """Mailbox 016. A position with no entry of ours is his."""
    _entry(led, "OURS", 3.00)
    led.account_positions = [_row("OURS", 6, 3.00),
                             _row("HIS-OWN", 100, 60.00)]
    assert led.at_risk_usd() == pytest.approx(3.00)


def test_but_his_own_bets_are_SHOWN_separately(led):
    """He should be able to see them without them entering the record."""
    _entry(led, "OURS", 3.00)
    led.account_positions = [_row("OURS", 6, 3.00),
                             _row("HIS-OWN", 100, 60.00)]
    line = led.at_risk_line()
    assert "$3.00" in line and "60.00" in line
    assert "YOUR OWN" in line and "not counted" in line


# ------------------------------------------------------------ fail safe

def test_an_unread_account_falls_back_and_SAYS_SO(led):
    """No reading means no account-sourced figure. It must not silently
    report zero at risk, which would make the floor look far away."""
    _entry(led, "OURS", 3.00)
    led.account_positions = None
    assert led.at_risk_usd() == pytest.approx(3.00)
    assert "has not been read" in led.at_risk_source()
    assert "this tool's own record" in led.at_risk_line()


def test_settled_and_void_rows_never_count(led):
    for status in ("won", "lost", "void", "expired", "deferred"):
        _entry(led, f"T-{status}", 5.00, status=status)
    led.account_positions = []
    assert led.at_risk_usd() == pytest.approx(0.0)
