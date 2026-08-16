"""Guard 4, re-pointed: watch our own bets, not his whole account.

⚠ WHY THIS EXISTS. The old check compared this tool's ledger against his WHOLE
Kalshi balance, which silently assumed every trade in the account came from
this tool. **He trades manually and always will** -- he has said so twice. So
the sums could never agree, every signal deferred, and **11 bets expired
unplaced** while every entry's note recorded the same sentence:

    auto-exec deferred: THESE DO NOT AGREE by +$29.53...

The guard was not protecting him from anything. It was eating every signal the
tool produced. The question it asks now is narrower and answerable: **is each
bet I placed sitting in his account at the size I placed it?**

    livedesk\\test.bat
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from ledger import Entry, Ledger, POSITION_LIVE_HOURS      # noqa: E402


@pytest.fixture
def led(tmp_path):
    return Ledger(tmp_path / "ledger.json")


def _pos(ticker, size):
    """A row shaped like Kalshi's. Size is a decimal STRING -- `position_fp`,
    never `position`. Reading the wrong one is trap C024 and sums to zero."""
    return {"ticker": ticker, "position_fp": f"{size:.2f}"}


def _open(led, ticker="OURS", contracts=7, starts=None, team="Miami Marlins"):
    e = Entry(game_key="2026-08-16:PIT@MIA", ticker=ticker, event_ticker="E",
              team=team, matchup="Pittsburgh at Miami", side="YES",
              price_c=52, contracts=contracts, cost_usd=3.77, fee_usd=0.13,
              win_profit_usd=3.23, lose_usd=3.77,
              starts_utc=starts or (datetime.now(timezone.utc)
                                    + timedelta(hours=3)).isoformat(),
              confirmed_utc=datetime.now().astimezone().isoformat(
                  timespec="seconds"),
              signal=f"sig-{ticker}")
    led.entries.append(e)
    led.save()
    return e


# ------------------------------------------------- the whole point of the fix

def test_a_manual_trade_of_his_own_changes_nothing(led):
    """He trades manually and always will. His bets must be invisible to it."""
    _open(led, "OURS", 7)
    rows = [_pos("OURS", 7),
            _pos("HIS-OWN-BET", 40),
            _pos("ANOTHER-OF-HIS", 3)]
    state, msg = led.reconcile_positions(rows)
    assert state == "ok", msg


def test_a_whole_account_of_his_own_trades_and_none_of_ours(led):
    """No bets of ours open at all -> nothing to check, whatever he is doing."""
    rows = [_pos("HIS-A", 10), _pos("HIS-B", 25)]
    assert led.reconcile_positions(rows)[0] == "nothing"


# ------------------------------------------------------ what it DOES catch

def test_a_JUST_PLACED_bet_missing_is_a_disagreement(led):
    """A bet missing minutes after we sent it may not have landed. That stops
    everything. An OLDER one is treated as him having sold it -- see
    test_an_old_position_he_changed_himself_is_adopted_not_blocked."""
    _open(led, "OURS", 7)
    state, msg = led.reconcile_positions([_pos("HIS-OWN-BET", 40)])
    assert state == "disagree"
    assert "does not show it at all" in msg
    assert "Miami Marlins" in msg, "it must name the bet, not just complain"


def test_an_old_position_he_changed_himself_is_adopted_not_blocked(led):
    """⚠ THE DEADLOCK THIS PREVENTS. He sold a Baltimore position down from 64
    contracts to 11 by hand. The ledger said 10, the account said 11, and
    Guard 4 blocked EVERY new bet for ever on a difference he had created
    himself and was entitled to create.

    His account is the truth. Our record follows it, loudly, and does not stop
    the tool."""
    from datetime import datetime as dt, timedelta as td
    e = _open(led, "OURS", 10)
    e.confirmed_utc = (dt.now().astimezone() - td(hours=4)).isoformat()
    led.save()
    state, msg = led.reconcile_positions([_pos("OURS", 11)])
    assert state == "ok", msg
    assert "updated to match your account" in msg
    assert e.contracts == 11, "it must adopt the account's number"
    assert "resized" in e.note, "and say so in the record"


def test_an_old_position_he_sold_ENTIRELY_is_voided_not_blocked(led):
    from datetime import datetime as dt, timedelta as td
    e = _open(led, "OURS", 10)
    e.confirmed_utc = (dt.now().astimezone() - td(hours=4)).isoformat()
    led.save()
    state, msg = led.reconcile_positions([])
    assert state == "ok", msg
    assert e.status == "void"
    assert "gone from your account" in e.note


def test_one_of_OUR_bets_at_the_wrong_size_is_a_disagreement(led):
    _open(led, "OURS", 7)
    state, msg = led.reconcile_positions([_pos("OURS", 3)])
    assert state == "disagree"
    assert "3 contracts" in msg and "7" in msg


def test_it_names_the_specific_bet_which_the_old_one_could_not(led):
    """Before, the worst it could say was 'something does not add up
    somewhere'. That is not actionable and he ignored it."""
    _open(led, "CLE-TICKER", 7, team="Cleveland Guardians")
    msg = led.reconcile_positions([])[1]
    assert "Cleveland Guardians" in msg


def test_several_problems_are_all_reported_not_just_the_first(led):
    _open(led, "A", 7, team="Boston Red Sox")
    _open(led, "B", 5, team="New York Mets")
    msg = led.reconcile_positions([_pos("B", 2)])[1]
    assert "Boston Red Sox" in msg and "New York Mets" in msg


# --------------------------------------------------------- the awkward edges

def test_a_short_position_counts_by_size_not_sign(led):
    """A NO position comes back negative. It is still the bet we placed."""
    _open(led, "OURS", 7)
    assert led.reconcile_positions([_pos("OURS", -7)])[0] == "ok"


def test_it_ignores_a_bet_whose_game_is_long_over(led):
    """Past the live window the position has settled and legitimately
    vanished, so its absence means nothing."""
    old = (datetime.now(timezone.utc)
           - timedelta(hours=POSITION_LIVE_HOURS + 2)).isoformat()
    _open(led, "OLD", 7, starts=old)
    assert led.reconcile_positions([])[0] == "nothing"


def test_it_still_watches_a_game_that_has_only_just_started(led):
    just = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    _open(led, "LIVE", 7, starts=just)
    assert led.reconcile_positions([])[0] == "disagree"


def test_it_reads_the_STRING_size_field_not_the_plain_one(led):
    """`position_fp` is a decimal string; `position` is the trap."""
    _open(led, "OURS", 7)
    assert led.reconcile_positions(
        [{"ticker": "OURS", "position_fp": "7.00"}])[0] == "ok"
    assert led.reconcile_positions(
        [{"ticker": "OURS", "position": 7}])[0] == "disagree"


def test_a_fully_closed_row_does_not_count_as_held(led):
    """Kalshi keeps returning markets you have closed, with size 0."""
    _open(led, "OURS", 7)
    assert led.reconcile_positions([_pos("OURS", 0)])[0] == "disagree"


def test_two_open_entries_on_one_ticker_are_summed(led):
    _open(led, "OURS", 4)
    _open(led, "OURS", 3)
    assert led.reconcile_positions([_pos("OURS", 7)])[0] == "ok"
    assert led.reconcile_positions([_pos("OURS", 4)])[0] == "disagree"


def test_a_voided_bet_is_not_expected_in_the_account(led):
    e = _open(led, "OURS", 7)
    e.status = "void"
    led.save()
    assert led.reconcile_positions([])[0] == "nothing"


# --------------------------------------------- it gates through the old name

def test_it_gates_the_button_through_the_normal_name(led):
    """Everything calls reconcile(); it must now be the positions check."""
    _open(led, "OURS", 7)
    led.account_positions = [_pos("OURS", 7)]
    assert led.reconcile()[0] == "ok"
    led.account_positions = []
    assert led.reconcile()[0] == "disagree"
    assert led.profit_shown() is False


def test_the_balance_line_is_now_a_DISPLAY_and_gates_nothing(led):
    """His own trading moves the balance and that is not a fault. It stays on
    screen because it is how a $32 error would show up, but it must never stop
    a bet again."""
    _open(led, "OURS", 7)
    led.account_positions = [_pos("OURS", 7)]
    led.set_account_balance(led.expected_account_usd() + 500.00)
    assert led.reconcile()[0] == "ok", "his own money stopped a bet again"
    assert "not from this tool" in led.balance_note()


def test_the_ledger_still_cannot_reach_a_network(led):
    """The positions are handed IN. This module must stay import-clean, or
    'nothing here can touch your account' stops being true."""
    import ast
    src = (SRC / "ledger.py").read_text(encoding="utf-8")
    roots = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            roots |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            roots.add((node.module or "").split(".")[0])
    allowed = {"json", "os", "re", "tempfile", "dataclasses", "datetime",
               "pathlib", "typing", "money", "__future__"}
    assert roots <= allowed, f"ledger.py imports {roots - allowed}"


# ===== the bug that refused every auto bet, 2026-08-16 evening =============

def test_a_brand_new_entry_does_not_refuse_its_own_submission(led):
    """⚠ THE SECOND TIME THIS SHAPE HAS APPEARED HERE, and it killed the bot.

    `_work()` writes the entry to the ledger and THEN submits it. So the bet
    about to be placed is an "open bet of ours", and it is of course not in his
    Kalshi account yet -- because it has not been placed. Guard 4 therefore
    said "the Baltimore Orioles bet is NOT in your account", and refused it.

    **Every auto bet, for ever.** He watched it happen on screen:

        17:56:18 AUTO refused Baltimore Orioles: THIS TOOL'S OWN BETS DO NOT
        MATCH YOUR ACCOUNT ... bet is NOT in your account at all.

    Guard 1 had the identical bug in August and made the practice button
    permanently dead. It was fixed there and reintroduced here the day Guard 4
    was re-pointed.
    """
    fresh = _open(led, "ABOUT-TO-BE-PLACED", 7)
    # His account holds nothing of ours yet.
    assert led.reconcile_positions([], ignore=fresh)[0] == "nothing"
    assert led.reconcile_positions([]) [0] == "disagree", (
        "without ignore it must still complain -- otherwise the guard is gone")


def test_the_ignored_entry_does_not_hide_a_REAL_missing_bet(led):
    """The exemption must be one entry wide, not a hole in the guard."""
    already = _open(led, "PLACED-EARLIER", 7)
    fresh = _open(led, "ABOUT-TO-BE-PLACED", 7)
    state, msg = led.reconcile_positions([], ignore=fresh)
    assert state == "disagree"
    assert "PLACED-EARLIER" in msg or "Miami Marlins" in msg


def test_guards_ok_passes_the_entry_through_to_guard_4(led):
    """Checked at the seam, because the unit was right and the wiring was not."""
    import demo_exec as X
    fresh = _open(led, "ABOUT-TO-BE-PLACED", 7)
    led.account_positions = []
    led.set_account_balance(500.00)
    X.guards_ok(led, fresh)          # must NOT raise
