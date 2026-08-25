"""Finished games must not sit counted as live money. Mailbox 020.

    livedesk\\test.bat

⚠ WHAT WENT WRONG, AND IT IS THE CLEAREST HALF-FINISHED FIX IN THIS PROJECT.

`live_entries()` was widened to include `awaiting-settlement`, so the settle
sweep would stop losing bets that dropped off the positions list. **`settle()`
was not widened to match.** The sweep found each one, read a finalised result
from Kalshi, queued it, and `settle()` looked for `status == "open"`, did not
find it, and returned `None`.

The caller was `if e:`. **Nothing was logged when it failed.** So it ran every
sixty seconds and did nothing, silently, for 106 hours. Ten finished games were
carried at what they cost as though the outcome were unknown, his profit was
frozen at the moment of purchase, and a total about $20 wrong was repeated back
to him as though he were up money when he was down.

**He found it. By reading his own account. For the fifth time.**
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from ledger import Entry, Ledger, GAME_LENGTH_HOURS        # noqa: E402


@pytest.fixture
def led(tmp_path):
    lg = Ledger(tmp_path / "ledger.json")
    lg.account_positions = []
    return lg


def _bet(led, team="Miami Marlins", status="open", hours_ago=None, cost=5.0):
    """`hours_ago=None` means the game has not started yet."""
    start = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)
             if hours_ago is not None
             else datetime.now(timezone.utc) + timedelta(hours=3))
    e = Entry(game_key=f"k:{team}:{len(led.entries)}",
              ticker=f"T-{team}-{len(led.entries)}", event_ticker="E",
              team=team, matchup=f"{team} at Home", side="YES", price_c=50,
              contracts=10, cost_usd=cost, fee_usd=0.10,
              win_profit_usd=4.90, lose_usd=cost,
              starts_utc=start.isoformat(),
              confirmed_utc=datetime.now().astimezone().isoformat(),
              signal=f"sig-{team}-{len(led.entries)}")
    e.status = status
    led.entries.append(e)
    led.save()
    return e


# ------------------------------------------------------- THE ACTUAL DEFECT

def test_an_awaiting_settlement_bet_CAN_be_settled(led):
    """⚠ THE ONE-WORD BUG. `settle()` matched only `open`, so every row the
    sweep had parked as `awaiting-settlement` was unsettleable for ever."""
    e = _bet(led, status="awaiting-settlement", hours_ago=30)
    out = led.settle(e.ticker, won=True)
    assert out is not None, "this returned None for 106 hours"
    assert out.status == "won"
    assert out.pnl_usd == pytest.approx(4.90)
    assert out.settled_utc


def test_every_status_the_sweep_feeds_settle_can_actually_be_settled(led):
    """The sweep walks `live_entries()`. Anything it can hand to `settle()`
    must be something `settle()` accepts, or the two drift apart again -- which
    is exactly how this happened."""
    for status in Ledger.LIVE_STATUSES:
        e = _bet(led, team=f"Team {status}", status=status, hours_ago=30)
        assert led.settle(e.ticker, won=False) is not None, status


def test_an_already_settled_bet_is_not_settled_twice(led):
    e = _bet(led, status="open", hours_ago=30)
    led.settle(e.ticker, won=True)
    assert led.settle(e.ticker, won=False) is None, "it must not flip a result"
    assert e.status == "won"


def test_a_failed_settle_can_say_WHY(led):
    """⚠ THE SILENT `return None` IS WHAT HID THE BUG FOR FOUR DAYS. A sweep
    that cannot say why it did nothing is indistinguishable from a sweep that
    had nothing to do."""
    e = _bet(led, status="expired", hours_ago=30)
    assert led.settle(e.ticker, won=True) is None
    why = led.settle_reason(e.ticker)
    assert "expired" in why and e.team in why, why


def test_an_already_settled_ticker_reports_no_problem(led):
    """Settling twice is normal -- the sweep re-reads every minute. It must not
    cry wolf, or the real message gets ignored."""
    e = _bet(led, status="open", hours_ago=30)
    led.settle(e.ticker, won=True)
    assert led.settle_reason(e.ticker) == ""


def test_a_ticker_we_have_never_heard_of_says_so(led):
    assert "no entry at all" in led.settle_reason("NOT-A-TICKER")


# --------------------------------- started, finished, and merely unrecorded

def test_a_game_that_has_started_is_chased_not_ignored(led):
    e = _bet(led, status="open", hours_ago=GAME_LENGTH_HOURS + 1)
    assert led.has_started(e)
    assert e in led.waiting_on_result()
    assert e not in led.still_playing()


def test_a_game_in_progress_is_still_playing_not_stuck(led):
    """A bet on a game happening right now IS money at risk, and must not be
    reported as a stuck record. Getting this backwards would have the tool
    crying wolf every evening."""
    e = _bet(led, status="open", hours_ago=1)
    assert e in led.still_playing()
    assert e not in led.waiting_on_result()


def test_a_game_that_has_not_started_is_still_playing(led):
    e = _bet(led, status="open", hours_ago=None)
    assert not led.has_started(e)
    assert e in led.still_playing()


def test_an_unreadable_start_time_is_treated_as_STARTED(led):
    """⚠ THE CAUTIOUS DIRECTION. A row with a bad date gets chased for a
    result rather than assumed to be safely in the future and skipped -- being
    skipped is precisely how the ten of them sat unnoticed."""
    e = _bet(led, status="open", hours_ago=1)
    e.starts_utc = "not a date"
    led.save()
    assert led.has_started(e)
    assert e in led.waiting_on_result()


# --------------------------------------------- what he is actually told

def test_the_two_are_reported_SEPARATELY(led):
    """⚠ FOLDING THEM TOGETHER IS THE NUMBER THAT WAS ABOUT $20 WRONG.
    'Money riding on undecided games' and 'results the tool has not written
    down' are different things and only one of them is at risk."""
    _bet(led, team="Playing Now", status="open", hours_ago=1, cost=3.0)
    _bet(led, team="Finished Ages Ago", status="awaiting-settlement",
         hours_ago=100, cost=7.0)

    riding = led.riding_line()
    waiting = led.waiting_line()
    assert "$3.00" in riding and "$7.00" not in riding
    assert "$7.00" in waiting and "$3.00" not in waiting
    assert "NOT money at risk" in waiting


def test_it_says_how_old_the_worst_one_is(led):
    """A game that finished four days ago and is still counted has to be
    visible without him reading Kalshi."""
    _bet(led, status="awaiting-settlement", hours_ago=100)
    assert led.oldest_unsettled_hours() == pytest.approx(100, abs=1)
    assert "4 DAYS" in led.waiting_line()


def test_past_a_day_it_shouts(led):
    """Under a day is routine -- night games settle in the morning. Past a day
    something is wrong and the wording changes."""
    _bet(led, team="Recent", status="awaiting-settlement", hours_ago=8)
    assert led.waiting_line().startswith("WAITING ON RESULTS")
    _bet(led, team="Ancient", status="awaiting-settlement", hours_ago=100)
    assert led.waiting_line().startswith("!! STUCK")


def test_a_clean_ledger_says_nothing_is_waiting(led):
    _bet(led, status="open", hours_ago=1)
    assert led.waiting_line() == "nothing waiting on a result"


def test_both_lines_are_plain_ascii(led):
    """The console is cp1252 and a fancy dash has already crashed a tool in
    front of him, mid-way through setting up his API key."""
    _bet(led, status="awaiting-settlement", hours_ago=100)
    led.riding_line().encode("cp1252")
    led.waiting_line().encode("cp1252")


def test_settling_moves_a_bet_out_of_waiting(led):
    """The end-to-end point of the whole message: settle it, and it stops
    being counted."""
    e = _bet(led, status="awaiting-settlement", hours_ago=100, cost=7.0)
    assert led.waiting_on_result() == [e]
    led.settle(e.ticker, won=True)
    assert led.waiting_on_result() == []
    assert led.waiting_line() == "nothing waiting on a result"
