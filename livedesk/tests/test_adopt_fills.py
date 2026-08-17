"""What he actually GOT, not what the tool asked for.

⚠ HE FOUND THIS BY READING HIS OWN KALSHI ACCOUNT. Three of four positions
disagreed with the ledger. That is the tool's job, not his.

**The cause was not the arithmetic and not a partial fill.** Kalshi reports
`position_fp` exactly -- 18, 21, 27, 11 -- and every count matched the ledger.
What differed was:

  * **the PRICE.** Miami was asked at 36c and FILLED AT 33c -- a better price
    than requested. The ledger recorded the ask, so it carried $10.16 against a
    real $8.91.
  * **the FEE.** Every fill was charged about HALF the taker fee this tool
    computes: ATL $0.1565 vs $0.32, SD $0.1831 vs $0.37, MIA $0.2090 vs $0.42.

So the tool stops computing any of it. Kalshi returns the cost, the size and
the fee per position, and a number read from the account cannot be wrong about
the account.

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


def _row(ticker, size, exposure, fees):
    """A row shaped exactly like Kalshi's, decimal STRINGS and all."""
    return {"ticker": ticker,
            "position_fp": f"{size:.2f}",
            "market_exposure_dollars": f"{exposure:.6f}",
            "fees_paid_dollars": f"{fees:.6f}",
            "total_traded_dollars": f"{exposure:.6f}"}


def _open(led, ticker="MIA", contracts=27, price_c=36, cost=10.16, fee=0.42):
    e = Entry(game_key="2026-08-17:MIA@PHI", ticker=ticker, event_ticker="E",
              team="Miami Marlins", matchup="Miami at Philadelphia",
              side="YES", price_c=price_c, contracts=contracts,
              cost_usd=cost, fee_usd=fee,
              win_profit_usd=round(contracts - cost, 2), lose_usd=cost,
              starts_utc=(datetime.now(timezone.utc)
                          + timedelta(hours=3)).isoformat(),
              confirmed_utc=datetime.now().astimezone().isoformat(
                  timespec="seconds"),
              signal=f"sig-{ticker}")
    led.entries.append(e)
    led.save()
    return e


# ------------------------------------------------ the exact case he found

def test_a_better_fill_price_is_adopted(led):
    """Miami: asked 36c, filled 33c. The tool recorded the ask."""
    e = _open(led, "MIA", 27, 36, 10.16, 0.42)
    said = led.adopt_fills([_row("MIA", 27, 8.91, 0.2090)])
    assert e.contracts == 27, "the count was never wrong"
    assert e.price_c == 33, "it must take the price it GOT"
    assert e.cost_usd == pytest.approx(9.12, abs=0.01)
    assert said and "Miami Marlins" in said[0]
    assert "33 cents" in said[0]


def test_the_real_fee_is_taken_not_computed(led):
    """Every fill was charged about half the taker fee. The account reports
    the fee, so nothing here computes one."""
    e = _open(led, "ATL", 18, 54, 9.72 + 0.32, 0.32)
    led.adopt_fills([_row("ATL", 18, 9.72, 0.1565)])
    assert e.fee_usd == pytest.approx(0.16, abs=0.01)
    assert e.cost_usd == pytest.approx(9.88, abs=0.01)


def test_the_win_and_lose_figures_follow_the_real_cost(led):
    e = _open(led, "MIA", 27, 36, 10.16, 0.42)
    led.adopt_fills([_row("MIA", 27, 8.91, 0.2090)])
    assert e.lose_usd == pytest.approx(e.cost_usd)
    assert e.win_profit_usd == pytest.approx(27.0 - e.cost_usd, abs=0.01)


def test_an_agreeing_position_changes_nothing_and_says_nothing(led):
    """No noise when it is right. A correction message every minute is one he
    stops reading."""
    _open(led, "SD", 21, 47, 9.87 + 0.18, 0.18)
    assert led.adopt_fills([_row("SD", 21, 9.87, 0.1831)]) == []


def test_the_old_value_stays_visible_in_the_entry(led):
    """Never a silent correction -- that is how the phantom $3.77 survived."""
    e = _open(led, "MIA", 27, 36, 10.16, 0.42)
    led.adopt_fills([_row("MIA", 27, 8.91, 0.2090)])
    assert "was 27 at 36c costing $10.16" in e.note
    assert "really 27 at 33c" in e.note


def test_it_says_it_in_plain_words(led):
    e = _open(led, "MIA", 27, 36, 10.16, 0.42)
    said = led.adopt_fills([_row("MIA", 27, 8.91, 0.2090)])[0]
    for word in ("actually got", "the tool had recorded"):
        assert word in said
    for jargon in ("position_fp", "market_exposure", "reconcil"):
        assert jargon not in said.lower()


# ------------------------------------------------------------- the edges

def test_an_unread_account_changes_nothing(led):
    """None means never read. Adopting from a reading that does not exist is
    what voided a live position on 2026-08-16."""
    e = _open(led, "MIA", 27, 36, 10.16, 0.42)
    assert led.adopt_fills(None) == []
    assert e.contracts == 27 and e.price_c == 36


def test_a_ticker_the_account_does_not_mention_is_left_alone(led):
    """Absence is handled by reconcile_positions, not here. This must not
    quietly zero a bet just because the row was missing."""
    e = _open(led, "MIA", 27, 36, 10.16, 0.42)
    assert led.adopt_fills([_row("SOMETHING-ELSE", 5, 2.0, 0.02)]) == []
    assert e.contracts == 27


def test_a_zero_size_row_is_ignored(led):
    """Kalshi keeps returning closed markets at size 0. Adopting that would
    price the bet at zero."""
    e = _open(led, "MIA", 27, 36, 10.16, 0.42)
    assert led.adopt_fills([_row("MIA", 0, 0.0, 0.0)]) == []
    assert e.contracts == 27


def test_a_settled_bet_is_not_touched(led):
    e = _open(led, "MIA", 27, 36, 10.16, 0.42)
    e.status = "lost"
    led.save()
    assert led.adopt_fills([_row("MIA", 27, 8.91, 0.2090)]) == []
    assert e.price_c == 36


def test_the_entry_being_submitted_is_skipped(led):
    e = _open(led, "MIA", 27, 36, 10.16, 0.42)
    assert led.adopt_fills([_row("MIA", 27, 8.91, 0.2090)], ignore=e) == []


def test_nothing_here_computes_a_fee(led):
    """GUARDS #6 -- one fee implementation. This module must not grow a
    second one, and it no longer needs to: the account reports the fee."""
    src = (SRC / "ledger.py").read_text(encoding="utf-8")
    body = src[src.index("def adopt_fills"):]
    body = body[:body.index("\n    def ")]
    for banned in ("fee_order_cents", "0.07", "* 0.07", "fee_rate"):
        assert banned not in body, f"adopt_fills computes a fee: {banned}"


def test_a_churned_market_does_not_get_its_whole_fee_history(led):
    """⚠ MY OWN FIX WAS WRONG BY NINETY CENTS ON THE BET THAT STARTED THIS.

    `fees_paid_dollars` is cumulative FOR THE MARKET. Baltimore's is $0.99 --
    the fees from eight buys and the sell-down -- against 11 remaining
    contracts. Adding all of it reported $5.50 for a position he had read off
    his own account as $4.60.

    `realized_pnl_dollars` is non-zero once a market has been traded both ways.
    When it has, the fee belongs to the whole episode and the cost of what is
    LEFT is its exposure alone."""
    e = _open(led, "BAL", 11, 42, 4.78, 0.19)
    row = _row("BAL", 11, 4.51, 0.9872)
    row["realized_pnl_dollars"] = "-0.530000"        # it churned
    led.adopt_fills([row])
    assert e.cost_usd == pytest.approx(4.51, abs=0.01), (
        "the whole fee history was folded into 11 remaining contracts")
    assert e.price_c == 41


def test_a_clean_position_DOES_include_its_fee(led):
    """The other half. Nothing churned, so the fee is genuinely this bet's."""
    e = _open(led, "MIA", 27, 36, 10.16, 0.42)
    row = _row("MIA", 27, 8.91, 0.2090)
    row["realized_pnl_dollars"] = "0.000000"
    led.adopt_fills([row])
    assert e.cost_usd == pytest.approx(9.12, abs=0.01)


def test_a_position_the_ledger_lost_is_put_back(led):
    """⚠ HIS 11 BALTIMORE CONTRACTS, LOST THREE TIMES.

    Real money, from this tool, carried nowhere -- so every stake and every
    balance was computed around a hole. I repaired it from a command line three
    times and the running window's 60-second save wrote its own copy back over
    the top, every time.

    The repair has to live INSIDE the loop that saves, or it loses the race by
    design."""
    e = _open(led, "BAL", 11, 42, 4.78, 0.19)
    e.status = "void"
    e.note = "gone from your account"
    led.save()
    row = _row("BAL", 11, 4.51, 0.9872)
    row["realized_pnl_dollars"] = "-0.530000"
    said = led.adopt_fills([row])
    assert e.status == "open", "the account holds it and it was not restored"
    assert e.contracts == 11
    assert any("lost track" in s for s in said)
    assert "RESTORED" in e.note


def test_a_position_that_was_never_ours_is_left_alone(led):
    """His own trades must stay invisible. Restoring must not invent a bet."""
    before = len(led.entries)
    assert led.adopt_fills([_row("HIS-OWN-THING", 40, 20.0, 0.4)]) == []
    assert len(led.entries) == before


def test_an_already_tracked_position_is_not_restored_twice(led):
    _open(led, "BAL", 11, 41, 4.51, 0.0)
    row = _row("BAL", 11, 4.51, 0.0)
    said = led.adopt_fills([row])
    assert not any("lost track" in s for s in said)
