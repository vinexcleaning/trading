"""A position in his account that this tool did not place is HIS. Full stop.

⚠ THIS ALREADY HAPPENED AND IT CORRUPTED THE RECORD, not just the display.

A restore loop keyed on the TICKER: if the account held a market and any old
entry mentioned it, the entry was restored and resized from the account.
**A ticker cannot tell whose bet it is.**

On 2026-08-17 he placed his own 64-contract Baltimore bet on a game the bot had
also looked at. The bot's own entry there had EXPIRED at 9 contracts, so the
loop found a matching ticker and wrote his $59.03 into the ledger as though the
bot had done it -- ten times its own sizing rule, with a profit figure that was
internally impossible.

He trades this account by hand and always will. Never adopted, never voided,
never counted.

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


def _row(ticker, size, exposure=25.0, fees=0.5, realized=0.0):
    return {"ticker": ticker, "position_fp": f"{size:.2f}",
            "market_exposure_dollars": f"{exposure:.6f}",
            "fees_paid_dollars": f"{fees:.6f}",
            "realized_pnl_dollars": f"{realized:.6f}",
            "total_traded_dollars": f"{exposure:.6f}"}


def _entry(led, ticker, status, contracts=9, price_c=42):
    e = Entry(game_key="2026-08-17:BAL@TB", ticker=ticker, event_ticker="E",
              team="Baltimore Orioles", matchup="Baltimore at Tampa Bay",
              side="YES", price_c=price_c, contracts=contracts, cost_usd=3.94,
              fee_usd=0.16, win_profit_usd=5.06, lose_usd=3.94,
              starts_utc=(datetime.now(timezone.utc)
                          + timedelta(hours=4)).isoformat(),
              confirmed_utc=datetime.now().astimezone().isoformat(
                  timespec="seconds"),
              signal="sig-bal", status=status)
    led.entries.append(e)
    led.save()
    return e


# ================= THE EXACT CASE: his bet on a game the bot also looked at

def test_an_EXPIRED_entry_is_never_restored_from_his_position(led):
    """⚠ THE $59.03 BUG, exactly. The bot's Baltimore bet expired at 9
    contracts; he then bet 64 of his own on the same market."""
    e = _entry(led, "BAL", "expired", contracts=9)
    led.adopt_fills([_row("BAL", 64, 26.24, 0.99)])
    assert e.status == "expired", "his bet resurrected the bot's dead entry"
    assert e.contracts == 9, "and resized it to his position"


def test_a_VOID_entry_is_never_restored_either(led):
    e = _entry(led, "BAL", "void", contracts=9)
    led.adopt_fills([_row("BAL", 64, 26.24, 0.99)])
    assert e.status == "void"
    assert e.contracts == 9


def test_his_position_never_creates_a_new_entry(led):
    n = len(led.entries)
    led.adopt_fills([_row("HIS-OWN-MARKET", 100, 60.0, 1.0)])
    led.reconcile_positions([_row("HIS-OWN-MARKET", 100, 60.0, 1.0)])
    assert len(led.entries) == n, "a bet was invented from his own trading"


def test_his_position_is_never_voided_by_this_tool(led):
    rows = [_row("HIS-OWN-MARKET", 100, 60.0, 1.0)]
    assert led.adopt_fills(rows) == []
    assert led.reconcile_positions(rows)[0] == "nothing"


def test_only_an_OPEN_entry_is_ever_touched(led):
    """The rule in one line. Anything not open is not ours to reconcile."""
    for status in ("expired", "void", "deferred", "lost", "won"):
        lg = Ledger(led.path.parent / f"{status}.json")
        lg.account_positions = []
        e = _entry(lg, "BAL", status, contracts=9)
        before = (e.status, e.contracts, e.cost_usd)
        lg.adopt_fills([_row("BAL", 64, 26.24, 0.99)])
        assert (e.status, e.contracts, e.cost_usd) == before, status


def test_an_open_entry_of_ours_IS_still_corrected(led):
    """No regression: the real job still works."""
    e = _entry(led, "OURS", "open", contracts=27, price_c=36)
    said = led.adopt_fills([_row("OURS", 27, 8.91, 0.209)])
    assert e.price_c == 33 and said


def test_the_restore_loop_is_gone_from_the_source():
    """Checked on the source so it cannot come back quietly. It looked like a
    helpful feature both times it was written."""
    src = (SRC / "ledger.py").read_text(encoding="utf-8")
    body = src[src.index("def adopt_fills"):]
    body = body[:body.index("\n    def ")]
    # The loop wrote a 'RESTORED from' note and set status to open. Both
    # markers, not the prose explaining why it is gone.
    assert 'RESTORED from' not in body, "the restore loop is back"
    assert 'back.status = "open"' not in body

