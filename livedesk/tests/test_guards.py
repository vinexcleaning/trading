"""The three guards, tested against real violations rather than trusted.

GUARDS #9: a guard nobody has tested against a real violation is a guard
nobody knows still works.

    py -3 -m pytest livedesk/tests -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import killswitch                                      # noqa: E402
from ledger import Entry, Ledger                       # noqa: E402
from money import (BANKROLL_START, CUTOFF_LOSS_USD, STAKE_USD,   # noqa: E402
                   size_bet)


def _entry(game_key, ticker, price_c=52, contracts=7, cost=3.77,
           win=3.23, lose=3.77, status="open", pnl=0.0):
    return Entry(game_key=game_key, ticker=ticker, event_ticker=ticker[:-4],
                 team="Miami Marlins", matchup="Pittsburgh at Miami",
                 side="YES", price_c=price_c, contracts=contracts,
                 cost_usd=cost, fee_usd=0.13, win_profit_usd=win,
                 lose_usd=lose, starts_utc="2026-08-12T22:40:00+00:00",
                 confirmed_utc="2026-08-12T02:00:00+00:00",
                 status=status, pnl_usd=pnl)


@pytest.fixture
def led(tmp_path):
    return Ledger(tmp_path / "ledger.json")


# ------------------------------------------------------ Guard 1: one per game

def test_guard1_a_game_with_a_bet_is_closed_for_good(led):
    led.add(_entry("2026-08-12:PIT@MIA", "KXMLBGAME-A-MIA"))
    assert led.has_played("2026-08-12:PIT@MIA")
    with pytest.raises(ValueError):
        led.add(_entry("2026-08-12:PIT@MIA", "KXMLBGAME-A-PIT"))


def test_guard1_survives_a_restart(tmp_path):
    p = tmp_path / "ledger.json"
    Ledger(p).add(_entry("2026-08-12:PIT@MIA", "KXMLBGAME-A-MIA"))
    assert Ledger(p).has_played("2026-08-12:PIT@MIA")


def test_guard1_still_closed_after_it_settles(led):
    """A game that lost is not a game to try again. The tennis app repeating
    bets after a loss is the exact machine that blew up on him."""
    led.add(_entry("2026-08-12:PIT@MIA", "KXMLBGAME-A-MIA"))
    led.settle("KXMLBGAME-A-MIA", won=False)
    assert led.has_played("2026-08-12:PIT@MIA")
    with pytest.raises(ValueError):
        led.add(_entry("2026-08-12:PIT@MIA", "KXMLBGAME-A-MIA2"))


def test_guard1_still_closed_after_a_void(led):
    led.add(_entry("2026-08-12:PIT@MIA", "KXMLBGAME-A-MIA"))
    led.entries[0].status = "void"
    led.save()
    assert led.has_played("2026-08-12:PIT@MIA")


def test_guard1_a_corrupt_ledger_refuses_to_look_empty(tmp_path):
    """An empty ledger re-opens every game Guard 1 has closed. Unreadable
    must mean STOP, never mean zero."""
    p = tmp_path / "ledger.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(RuntimeError):
        Ledger(p)


# --------------------------------------------------- Guard 2: the $50 cut-off

def test_guard2_fires_on_the_tools_own_losses(led):
    """Eight losing bets is not enough; nine is. The line is -$33 from $83,
    which is the $50 he named."""
    for i in range(8):
        led.entries.append(_entry(f"g{i}", f"T{i}", status="lost", pnl=-3.77))
    assert led.realised_usd() == pytest.approx(-30.16, abs=0.01)
    assert led.cutoff_hit() is False
    assert led.bankroll_usd() == pytest.approx(52.84, abs=0.01)

    led.entries.append(_entry("g8", "T8", status="lost", pnl=-3.77))
    assert led.realised_usd() == pytest.approx(-33.93, abs=0.01)
    assert led.cutoff_hit() is True
    assert led.bankroll_usd() == pytest.approx(49.07, abs=0.01)


def test_guard2_does_not_fire_on_a_small_loss(led):
    led.entries.append(_entry("g", "T", status="lost", pnl=-10.0))
    assert not led.cutoff_hit()
    assert led.bankroll_usd() == pytest.approx(BANKROLL_START - 10.0)


def test_guard2_counts_money_still_in_open_games(led):
    """The cut-off must not keep handing out bets while $40 of losers are
    still in flight and only notice once they all settle."""
    for i in range(9):
        led.entries.append(_entry(f"g{i}", f"T{i}", status="open"))
    assert led.realised_usd() == 0.0
    assert led.worst_case_usd() == pytest.approx(-33.93, abs=0.01)
    assert led.cutoff_hit() is True


def test_guard2_ignores_money_he_moved_himself(led):
    """His own point: 'there might be a chance it dips to fifty because I'm
    the reason it dipped to fifty, and it had nothing to do with baseball.'
    Nothing in the ledger reads an account balance, so nothing he does to the
    account can trip this.

    Tested structurally, because the honest version of this test is "the
    cut-off has no way to learn the account balance": nothing in the module
    reaches the network or reads a broker, so there is no path by which his
    own withdrawal could reach it."""
    src = (Path(__file__).resolve().parents[1] / "src" / "ledger.py").read_text(
        encoding="utf-8")
    for banned in ("urllib", "requests", "import prices", "http", "kalshi"):
        assert banned not in src.lower(), banned
    # and the number itself is a pure function of the entries
    led.entries.append(_entry("g", "T", status="lost", pnl=-40.0))
    assert led.cutoff_hit() is True
    led.entries[0].pnl_usd = -1.0
    assert led.cutoff_hit() is False


def test_guard2_a_void_does_not_count_as_a_loss(led):
    led.entries.append(_entry("g", "T", status="void", pnl=0.0))
    assert led.realised_usd() == 0.0
    assert led.at_risk_usd() == 0.0


# ------------------------------------------------- Guard 3: flat 5%, no growth

def test_guard3_stake_is_five_percent_of_83():
    assert STAKE_USD == pytest.approx(4.15)
    assert BANKROLL_START == 83.00
    assert CUTOFF_LOSS_USD == 33.00


def test_guard3_size_never_exceeds_the_flat_stake():
    for price in range(1, 100):
        bet = size_bet(price)
        assert bet.contracts * price / 100.0 <= STAKE_USD + 1e-9, price


def test_guard3_does_not_grow_with_a_winning_balance(led):
    """The paper run drifted 3 contracts -> 25 on its own."""
    base = size_bet(52).contracts
    for i in range(20):
        led.entries.append(_entry(f"g{i}", f"T{i}", status="won", pnl=+3.23))
    assert led.bankroll_usd() > BANKROLL_START
    assert size_bet(52).contracts == base
    assert size_bet(52).cost_usd < STAKE_USD + 0.25


def test_guard3_a_caller_cannot_ask_for_a_bigger_stake():
    """The Critic caught this: saying "no parameter could carry a rising
    bankroll" about a function that has a stake parameter is a claim, not a
    guard. It is clamped, so passing a bigger number does nothing."""
    base = size_bet(52)
    for attempt in (STAKE_USD * 2, 50.0, 1000.0, float("inf")):
        assert size_bet(52, attempt).contracts == base.contracts, attempt
    # and it can still be driven DOWN, which is what the parameter is for
    assert size_bet(52, 1.00).contracts < base.contracts


def test_guard3_the_fee_is_in_the_break_even():
    """The correction the mlb chat made on 2026-08-08: quoting the price alone
    puts break-even at 52 out of 100 when it is really about 54."""
    bet = size_bet(52)
    assert bet.breakeven_out_of_100 > 52.0
    assert bet.breakeven_out_of_100 == pytest.approx(53.9, abs=0.6)


def test_guard3_an_unaffordable_price_produces_no_bet():
    assert size_bet(99).contracts >= 1        # 4 contracts at 99c is fine
    assert size_bet(0).contracts == 0
    assert size_bet(100).contracts == 0


# ------------------------------------------------------------- the kill switch

def test_killswitch_is_a_file_and_nothing_else():
    assert killswitch.SWITCH.name == "TRADING_DISABLED"
    assert killswitch.SWITCH.parent.name == "livedesk"


def test_killswitch_reports_when_the_file_is_there(tmp_path, monkeypatch):
    f = tmp_path / "TRADING_DISABLED"
    monkeypatch.setattr(killswitch, "SWITCH", f)
    assert not killswitch.disabled()
    f.write_text("off because X\nmore detail\n", encoding="utf-8")
    assert killswitch.disabled()
    assert "off because X" in killswitch.reason()


# ------------------------------------------------- the money, in plain numbers

def test_the_card_numbers_add_up():
    """What he reads has to be arithmetic he could check on a phone."""
    bet = size_bet(52)
    assert bet.contracts == 7
    assert bet.cost_usd == pytest.approx(7 * 0.52 + bet.fee_usd, abs=0.005)
    assert bet.win_profit_usd == pytest.approx(7 * 1.00 - bet.cost_usd, abs=0.005)
    assert bet.lose_usd == pytest.approx(bet.cost_usd, abs=0.005)


def test_the_ledger_file_is_readable_by_a_human(led, tmp_path):
    led.add(_entry("2026-08-12:PIT@MIA", "KXMLBGAME-A-MIA"))
    raw = json.loads(led.path.read_text(encoding="utf-8"))
    assert raw["bankroll_start_usd"] == 83.0
    assert raw["entries"][0]["team"] == "Miami Marlins"
