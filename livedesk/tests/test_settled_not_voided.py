"""A bet that SETTLED must never be recorded as one that never happened.

⚠ THREE OF HIS REAL, SETTLED, LOST BETS WERE RECORDED AS `void`, zero
contracts, zero loss. He had paid roughly $4.51 + $9.12 + $10.05 and lost all
three, and his own record said nothing had happened. His balance was correct
throughout -- which is the dangerous shape, because it looked reconciled.

**`position_fp = 0` means two different things**: "he never held this" and "he
held it and the market SETTLED". A settled market drops off the positions
endpoint entirely. Those two collapsed to the same row.

That is the same mechanism as the original $32 error in the tennis app.

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


@pytest.fixture
def led(tmp_path):
    lg = Ledger(tmp_path / "ledger.json")
    lg.account_positions = []
    return lg


def _placed(led, ticker="MIA", contracts=27, price_c=33, hours_ago=8):
    e = Entry(game_key="2026-08-17:MIA@PHI", ticker=ticker, event_ticker="E",
              team="Miami Marlins", matchup="Miami at Philadelphia",
              side="YES", price_c=price_c, contracts=contracts,
              cost_usd=9.12, fee_usd=0.21, win_profit_usd=17.88, lose_usd=9.12,
              starts_utc=(datetime.now(timezone.utc)
                          - timedelta(hours=hours_ago)).isoformat(),
              confirmed_utc=(datetime.now().astimezone()
                             - timedelta(hours=hours_ago + 1)).isoformat(),
              signal="sig-mia")
    led.entries.append(e)
    led.save()
    return e


def test_a_settled_bet_is_NEVER_voided(led):
    """THE BUG. The market settled, so it left the positions list, and the
    reconciliation wrote it down as a position that does not exist."""
    e = _placed(led, hours_ago=2)          # inside the live window
    led.reconcile_positions([])            # account shows nothing
    assert e.status != "void", (
        "a bet with a fill behind it was voided — his real loss was erased")
    assert e.contracts == 27, "and its size was zeroed too"


def test_it_keeps_the_money_it_really_had_on(led):
    e = _placed(led, hours_ago=2)
    led.reconcile_positions([])
    assert e.cost_usd > 0, "the cost was replaced by the fee"
    assert e.cost_usd == pytest.approx(9.12, abs=0.5)


def test_void_still_means_we_never_had_it(led):
    """The other half: a bet that never filled SHOULD still void."""
    e = _placed(led, contracts=0, hours_ago=2)
    e.contracts = 0
    led.save()
    led.reconcile_positions([])
    assert e.status in ("void", "open"), e.status
    assert e.status != "won" and e.status != "lost"


def test_a_bet_off_the_list_reads_as_waiting_not_gone(led):
    """What he sees must not say 'gone from your account' about a bet that
    finished. Those are different things and only one of them is alarming."""
    _placed(led, hours_ago=2)
    state, msg = led.reconcile_positions([])
    assert "gone from your account" not in msg
    assert "waiting for the result" in msg or state == "ok"


def test_a_still_live_position_is_untouched(led):
    """No regression: a bet the account still holds must stay open."""
    e = _placed(led, hours_ago=2)
    led.reconcile_positions([{"ticker": "MIA", "position_fp": "27.00"}])
    assert e.status == "open" and e.contracts == 27
