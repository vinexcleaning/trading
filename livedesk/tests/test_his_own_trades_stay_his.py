"""He trades this same account by hand. His bets must stay invisible.

⚠ HIS WORDS, 2026-08-18: *"i will also be trading at the same time so it will
likely go below 40 on my balance for periods of times before the cash comes
back"*.

Since mailbox 011 the account is the source of truth on every refresh. He is
about to put his OWN positions in that account. If the reconciliation adopted
them, his personal wins and losses would land in the bot's record, its running
total, its peak and its profit figure.

**That corrupts the evidence, not just the display**, which makes it worse than
every ledger defect this week.

    livedesk\test.bat
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import ledger as L                                        # noqa: E402
from ledger import Entry, Ledger                          # noqa: E402


@pytest.fixture
def led(tmp_path):
    lg = Ledger(tmp_path / "ledger.json")
    lg.account_positions = []
    return lg


def _row(ticker, size, exposure=5.0, fees=0.1, realized=0.0):
    return {"ticker": ticker, "position_fp": f"{size:.2f}",
            "market_exposure_dollars": f"{exposure:.6f}",
            "fees_paid_dollars": f"{fees:.6f}",
            "realized_pnl_dollars": f"{realized:.6f}",
            "total_traded_dollars": f"{exposure:.6f}"}


def _ours(led, ticker="OURS", contracts=7):
    e = Entry(game_key="2026-08-18:A@B", ticker=ticker, event_ticker="E",
              team="Our Team", matchup="a at b", side="YES", price_c=50,
              contracts=contracts, cost_usd=3.55, fee_usd=0.05,
              win_profit_usd=3.45, lose_usd=3.55,
              starts_utc=(datetime.now(timezone.utc)
                          + timedelta(hours=5)).isoformat(),
              confirmed_utc=datetime.now().astimezone().isoformat(
                  timespec="seconds"),
              signal="sig-ours")
    led.entries.append(e)
    led.save()
    return e


# ------------------------------------------------------- never adopted

def test_his_own_position_is_never_written_into_the_ledger(led):
    before = [(e.ticker, e.contracts, e.cost_usd) for e in led.entries]
    led.adopt_fills([_row("HIS-OWN-TENNIS-BET", 40, 25.0, 0.5)])
    after = [(e.ticker, e.contracts, e.cost_usd) for e in led.entries]
    assert after == before, "one of his own trades was adopted"


def test_his_own_position_never_creates_an_entry(led):
    n = len(led.entries)
    led.adopt_fills([_row("HIS-OWN-THING", 100, 60.0, 1.0)])
    led.reconcile_positions([_row("HIS-OWN-THING", 100, 60.0, 1.0)])
    assert len(led.entries) == n, "a bet was invented from his own trading"


def test_his_own_position_is_never_voided_either(led):
    """Leave it completely alone -- not adopted, not voided, not counted."""
    rows = [_row("HIS-OWN-THING", 100, 60.0, 1.0)]
    assert led.adopt_fills(rows) == []
    assert led.reconcile_positions(rows)[0] == "nothing"


def test_a_huge_manual_position_does_not_disturb_our_own_check(led):
    _ours(led, "OURS", 7)
    rows = [_row("OURS", 7, 3.50, 0.05),
            _row("HIS-BIG-ONE", 500, 300.0, 5.0)]
    assert led.reconcile_positions(rows)[0] == "ok"


# ------------------------------------- his results must not move the peak

def test_the_peak_follows_the_BOTS_total_not_the_live_balance(led):
    """⚠ Checked because the coordinator asked for this exact line to be
    verified. If the peak read the live account, HIS winnings would raise the
    bot's high-water mark and HIS losses would trip its trailing stop."""
    import inspect
    src = inspect.getsource(L.Ledger._bump_peak)
    assert "running_total_usd" in src
    assert "account_balance_usd" not in src, (
        "the peak reads the live balance — his own trading would move it")


def test_his_winnings_do_not_raise_the_peak(led):
    led.account_start_usd = 62.61
    led.peak_total_usd = 62.61
    led.set_account_balance(500.00)          # he had a big day of his own
    led._bump_peak()
    assert led.peak_total_usd == pytest.approx(62.61)


def test_his_losses_do_not_trip_the_trailing_stop(led):
    led.peak_total_usd = 62.61
    led.set_account_balance(45.00)           # his own money, not the bot's
    paused, why = led.paused()
    assert not paused, why


# ------------------------------------------- the floor is a PAUSE now

def test_the_floor_is_forty_and_pausing_is_not_terminal():
    assert L.ACCOUNT_FLOOR_USD == 40.00


def test_below_the_floor_it_pauses_and_says_it_will_resume(led):
    led.set_account_balance(38.20)
    paused, why = led.paused()
    assert paused
    assert "PAUSED" in why and "40" in why
    assert "start again by itself" in why


def test_back_above_the_floor_it_resumes_with_no_restart(led):
    led.set_account_balance(38.20)
    assert led.paused()[0] is True
    led.set_account_balance(41.10)           # the cash came back
    assert led.paused()[0] is False, (
        "it did not resume on its own — he asked for no restart and no button")


def test_the_trailing_rule_also_pauses_rather_than_killing(led):
    """⚠ Resetting the peak to $62.61 puts the trailing stop at $40.70, right
    on top of the $40 floor. That is only safe because it pauses."""
    led.peak_total_usd = 62.61
    assert led.trailing_stop_usd() == pytest.approx(40.70, abs=0.01)
    led.set_account_balance(39.00)
    assert led.paused()[0] is True
    led.set_account_balance(45.00)
    assert led.paused()[0] is False
