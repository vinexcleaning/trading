"""The guards, tested against real violations rather than trusted.

GUARDS #9: a guard nobody has tested against a real violation is a guard
nobody knows still works.

Rewritten 2026-08-12 for amendment 2 of mailbox 001, which changed two of the
three guards after the user corrected them:
  * the cut-off is RELATIVE (a $50 floor plus a 35% trailing drop), not a
    fixed -$33;
  * the block is one bet per SIGNAL, not per game, with a cap of two per game
    and never adding to a losing position;
  * and a fourth guard was added: reconcile or refuse.

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

import killswitch                                      # noqa: E402
from ledger import (ACCOUNT_FLOOR_USD, Entry, Ledger,  # noqa: E402
                    MAX_ORDERS_PER_DAY, MAX_POSITIONS_PER_GAME,
                    MAX_STAKE_PER_DAY_USD, MAX_VOIDS_BEFORE_CLOSED,
                    RECONCILE_TOLERANCE_USD, SETTLEMENT_LAG_HOURS,
                    TRAILING_DROP_FRAC, signal_key)
from money import BANKROLL_START, STAKE_USD, size_bet  # noqa: E402

GK = "2026-08-12:PIT@MIA"


def _entry(game_key=GK, ticker="T1", signal="sig-1", price_c=52, contracts=7,
           cost=3.77, win=3.23, lose=3.77, status="open", pnl=0.0,
           settled_utc=None, confirmed_utc="2026-08-12T02:00:00+00:00"):
    return Entry(game_key=game_key, ticker=ticker, event_ticker="E",
                 team="Miami Marlins", matchup="Pittsburgh at Miami",
                 side="YES", price_c=price_c, contracts=contracts,
                 cost_usd=cost, fee_usd=0.13, win_profit_usd=win,
                 lose_usd=lose, starts_utc="2026-08-12T22:40:00+00:00",
                 confirmed_utc=confirmed_utc, signal=signal,
                 status=status, pnl_usd=pnl, settled_utc=settled_utc)


@pytest.fixture
def led(tmp_path):
    return Ledger(tmp_path / "ledger.json")


def _lose(led, n, cost=3.77):
    for i in range(n):
        led.entries.append(_entry(game_key=f"g{i}", ticker=f"T{i}",
                                  signal=f"s{i}", status="lost", pnl=-cost,
                                  cost=cost, lose=cost))
    led.save()


# =================================================== Guard 1: one per SIGNAL

def test_guard1_the_same_signal_is_blocked_for_good(led):
    led.add(_entry(signal="starter|MIA|home:form_divergence"))
    ok, why = led.may_bet(GK, "starter|MIA|home:form_divergence")
    assert not ok and "already been taken" in why
    with pytest.raises(ValueError):
        led.add(_entry(ticker="T2", signal="starter|MIA|home:form_divergence"))


def test_guard1_a_DIFFERENT_signal_on_the_same_game_is_allowed(led):
    """His own correction, and he was right: 'We should be allowed to reenter
    the same game if it's a different scenario... It's a different bet but
    it's the same game.'"""
    led.add(_entry(signal="starter|MIA|home:form_divergence"))
    ok, why = led.may_bet(GK, "starter|MIA|away:short_rest")
    assert ok, why


def test_guard1_hard_cap_of_two_per_game_whatever_the_reason(led):
    led.add(_entry(ticker="T1", signal="s1"))
    led.add(_entry(ticker="T2", signal="s2"))
    assert MAX_POSITIONS_PER_GAME == 2
    ok, why = led.may_bet(GK, "s3-brand-new")
    assert not ok and "limit" in why


def test_guard1_never_adds_to_a_losing_position(led):
    led.add(_entry(ticker="T1", signal="s1", price_c=52))
    assert led.may_bet(GK, "s2", price_now_c=55)[0] is True
    ok, why = led.may_bet(GK, "s2", price_now_c=44)
    assert not ok and "losing" in why


def test_guard1_survives_a_restart(tmp_path):
    p = tmp_path / "ledger.json"
    Ledger(p).add(_entry(signal="s1"))
    assert "s1" in Ledger(p).signals_played()
    assert Ledger(p).may_bet(GK, "s1")[0] is False


def test_guard1_still_blocked_after_it_settles(led):
    """A signal that lost is not a signal to try again."""
    led.add(_entry(signal="s1"))
    led.settle("T1", won=False)
    assert led.may_bet(GK, "s1")[0] is False


def test_guard1_a_void_frees_the_per_game_count(led):
    """No money was placed, so it does not use up one of his two per game.

    ⚠ This test used to also assert the signal stayed BLOCKED after a void.
    That was changed on 2026-08-12 -- see
    test_a_void_offers_the_bet_once_more for why, and what it cost him."""
    led.add(_entry(signal="s1"))
    led.entries[0].status = "void"
    led.save()
    assert led.positions_on_game(GK) == 0


def test_guard1_a_corrupt_ledger_refuses_to_look_empty(tmp_path):
    """An empty ledger re-opens every signal Guard 1 has closed."""
    p = tmp_path / "ledger.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(RuntimeError):
        Ledger(p)


def test_signal_key_ignores_the_drifting_numbers_in_a_flag(led):
    """mlb's A3 records an unusable divergence as
    'form_divergence_IGNORED_only_1_starts_5.1ip'. The innings count moves
    between decision windows; the RULE that fired does not. If the numbers
    counted, the identical bet would look fresh three times a day."""
    a = signal_key(GK, "MIA", {"home": {"flags":
                   ["form_divergence_IGNORED_only_1_starts_5.1ip"]}})
    b = signal_key(GK, "MIA", {"home": {"flags":
                   ["form_divergence_IGNORED_only_2_starts_11.2ip"]}})
    assert a == b
    c = signal_key(GK, "MIA", {"home": {"flags": ["short_rest"]}})
    assert c != a


def test_signal_key_is_stable_and_order_independent(led):
    a = signal_key(GK, "MIA", {"home": {"flags": ["short_rest", "debut_or_near"]}})
    b = signal_key(GK, "MIA", {"home": {"flags": ["debut_or_near", "short_rest"]}})
    assert a == b


# ========================================== Guard 2: the RELATIVE cut-off

def test_guard2_the_absolute_floor_never_moves(led):
    assert ACCOUNT_FLOOR_USD == 50.00
    led.set_account_balance(49.99)
    stopped, why = led.stopped()
    assert stopped and "floor" in why
    led.set_account_balance(50.01)
    assert led.stopped()[0] is False


def test_guard2_the_trailing_stop_is_35_percent_off_the_peak(led):
    assert TRAILING_DROP_FRAC == 0.35
    assert led.peak_total_usd == pytest.approx(83.00)
    assert led.trailing_stop_usd() == pytest.approx(53.95, abs=0.01)


def test_guard2_a_bigger_bankroll_allows_a_bigger_drawdown(led):
    """His correction: 'let's say the bot keeps going and makes three hundred,
    and then we lose thirty. That's only ten percent.' At a peak of $300 a $30
    loss must NOT stop it; a $105 loss must."""
    led.entries.append(_entry(signal="w", status="won", pnl=+217.0))
    led.save()
    assert led.running_total_usd() == pytest.approx(300.0)
    assert led.peak_total_usd == pytest.approx(300.0)
    assert led.trailing_stop_usd() == pytest.approx(195.0)
    led.set_account_balance(270.0)          # clear of the $50 floor
    led.entries.append(_entry(signal="l1", ticker="L1", game_key="gx",
                              status="lost", pnl=-30.0, cost=30.0, lose=30.0))
    led.save()
    assert led.stopped()[0] is False, "a $30 loss from $300 must not stop it"
    led.entries.append(_entry(signal="l2", ticker="L2", game_key="gy",
                              status="lost", pnl=-80.0, cost=80.0, lose=80.0))
    led.save()
    assert led.stopped()[0] is True, "a $110 loss from $300 must stop it"


def test_guard2_the_peak_only_ever_goes_up_and_survives_a_restart(tmp_path):
    p = tmp_path / "ledger.json"
    a = Ledger(p)
    a.entries.append(_entry(signal="w", status="won", pnl=+40.0))
    a.save()
    assert a.peak_total_usd == pytest.approx(123.0)
    a.entries.append(_entry(signal="l", ticker="L", game_key="gx",
                            status="lost", pnl=-10.0, cost=10.0, lose=10.0))
    a.save()
    assert a.peak_total_usd == pytest.approx(123.0), "the peak fell"
    assert Ledger(p).peak_total_usd == pytest.approx(123.0)


def test_guard2_counts_money_still_riding_on_open_games(led):
    """The cut-off must not keep handing out bets while losers are in flight
    and notice only after they all settle."""
    led.set_account_balance(83.0)
    for i in range(9):
        led.entries.append(_entry(game_key=f"g{i}", ticker=f"T{i}",
                                  signal=f"s{i}", status="open"))
    led.save()
    assert led.realised_usd() == 0.0
    assert led.worst_case_total_usd() == pytest.approx(49.07, abs=0.01)
    assert led.worst_case_total_usd() < led.trailing_stop_usd()
    assert led.stopped()[0] is True


def test_guard2_says_when_the_floor_is_checked_against_a_made_up_number(led):
    value, real = led.account_for_floor_usd()
    assert real is False and "not your account" in led.room_line()
    led.set_account_balance(70.0)
    value, real = led.account_for_floor_usd()
    assert real is True and value == 70.0
    assert "not your account" not in led.room_line()


# =========================================== Guard 4: reconcile or refuse

def test_guard4_nothing_placed_cannot_be_wrong(led):
    assert led.reconcile()[0] == "nothing"
    assert led.profit_shown() is True


def test_guard4_a_settled_bet_with_no_balance_typed_refuses(led):
    led.entries.append(_entry(signal="s1", status="lost", pnl=-3.77))
    led.save()
    state, msg = led.reconcile()
    assert state == "unchecked"
    assert led.profit_shown() is False


def test_guard4_the_32_dollar_disagreement_is_caught(led):
    """THE case this guard exists for. His account went 130 -> 160 while the
    tennis app said it was down $2, with no trades of his own between: about
    $32 of disagreement, reported, 'fixed', and still wrong."""
    led.account_start_usd = 130.0
    led.entries.append(_entry(signal="s1", status="lost", pnl=-2.0,
                              cost=2.0, lose=2.0,
                              settled_utc="2026-08-01T00:00:00+00:00"))
    led.save()
    assert led.expected_account_usd() == pytest.approx(128.0)
    led.set_account_balance(160.0)
    state, msg = led.reconcile()
    assert state == "disagree"
    assert "+$32.00" in msg
    assert led.profit_shown() is False


def test_guard4_a_disagreement_stops_the_profit_figure_being_shown(led):
    led.entries.append(_entry(signal="s1", status="won", pnl=+3.23,
                              settled_utc="2026-08-01T00:00:00+00:00"))
    led.save()
    led.set_account_balance(200.0)
    assert led.reconcile()[0] == "disagree"
    assert "not checked" in led.summary_line()


def test_guard4_agreement_inside_a_dollar_is_fine(led):
    assert RECONCILE_TOLERANCE_USD == 1.00
    led.entries.append(_entry(signal="s1", status="won", pnl=+3.23,
                              settled_utc="2026-08-01T00:00:00+00:00"))
    led.save()
    # 83 out 3.77, back 7 contracts x $1 = 7.00 -> expect 86.23
    assert led.expected_account_usd() == pytest.approx(86.23, abs=0.01)
    led.set_account_balance(86.23)
    assert led.reconcile()[0] == "ok"
    led.set_account_balance(87.10)
    assert led.reconcile()[0] == "ok", "87c is inside the dollar"
    led.set_account_balance(87.50)
    assert led.reconcile()[0] == "disagree"


def test_guard4_a_win_that_just_settled_does_not_fire_a_false_alarm(led):
    """Kalshi pays out minutes after the result is final. A bet settled
    seconds ago is legitimately in the ledger and not yet in the balance, and
    a false alarm here would train him to ignore the real one."""
    just_now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    led.entries.append(_entry(signal="s1", status="won", pnl=+3.23,
                              settled_utc=just_now))
    led.save()
    assert led.pending_payout_usd() == pytest.approx(7.00)
    led.set_account_balance(79.23)          # paid out, cash not landed
    assert led.reconcile()[0] == "ok"
    old = (datetime.now(timezone.utc)
           - timedelta(hours=SETTLEMENT_LAG_HOURS + 1)).isoformat(timespec="seconds")
    led.entries[0].settled_utc = old
    led.save()
    assert led.reconcile()[0] == "disagree", "once the lag is past it must fire"


def test_guard4_a_void_never_counts_as_money_out(led):
    led.entries.append(_entry(signal="s1", status="void"))
    led.save()
    assert led.money_out_usd() == 0.0
    assert led.reconcile()[0] == "nothing"


def test_guard4_nothing_in_the_ledger_can_reach_an_account(led):
    """The balance is typed by him and by nothing else.

    Checked on the PARSED IMPORTS, not by grepping for words. The word-grep
    version of this test passed until a comment mentioned Kalshi's payout
    timing and then failed on prose, which is a test that measures writing
    rather than code. What is actually claimed is 'this module imports nothing
    that could reach a network or a broker', and that is a fact about the
    import list.
    """
    import ast
    src = (Path(__file__).resolve().parents[1] / "src" / "ledger.py").read_text(
        encoding="utf-8")
    roots = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            roots |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            roots.add((node.module or "").split(".")[0])
    allowed = {"json", "os", "re", "tempfile", "dataclasses", "datetime",
               "pathlib", "typing", "money", "__future__"}
    assert roots <= allowed, f"ledger.py imports {roots - allowed}"


# ================================================ Guard 3: flat 5%, no growth

def test_guard3_stake_is_five_percent_of_83():
    assert STAKE_USD == pytest.approx(4.15)
    assert BANKROLL_START == 83.00


def test_guard3_size_never_exceeds_the_flat_stake():
    for price in range(1, 100):
        bet = size_bet(price)
        assert bet.contracts * price / 100.0 <= STAKE_USD + 1e-9, price


def test_guard3_does_not_grow_with_a_winning_balance(led):
    base = size_bet(52).contracts
    for i in range(20):
        led.entries.append(_entry(game_key=f"g{i}", ticker=f"T{i}",
                                  signal=f"s{i}", status="won", pnl=+3.23))
    led.save()
    assert led.running_total_usd() > BANKROLL_START
    assert size_bet(52).contracts == base


def test_guard3_a_caller_cannot_ask_for_a_bigger_stake():
    base = size_bet(52)
    for attempt in (STAKE_USD * 2, 50.0, 1000.0, float("inf")):
        assert size_bet(52, attempt).contracts == base.contracts, attempt
    assert size_bet(52, 1.00).contracts < base.contracts


def test_guard3_the_fee_is_in_the_break_even():
    bet = size_bet(52)
    assert bet.breakeven_out_of_100 > 52.0
    assert bet.breakeven_out_of_100 == pytest.approx(53.9, abs=0.6)


def test_guard3_an_unaffordable_price_produces_no_bet():
    assert size_bet(99).contracts >= 1
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
    bet = size_bet(52)
    assert bet.contracts == 7
    assert bet.cost_usd == pytest.approx(7 * 0.52 + bet.fee_usd, abs=0.005)
    assert bet.win_profit_usd == pytest.approx(7 * 1.00 - bet.cost_usd, abs=0.005)
    assert bet.lose_usd == pytest.approx(bet.cost_usd, abs=0.005)


def test_the_ledger_file_is_readable_by_a_human(led):
    led.add(_entry(signal="s1"))
    raw = json.loads(led.path.read_text(encoding="utf-8"))
    assert raw["account_start_usd"] == 83.0
    assert raw["account_floor_usd"] == 50.0
    assert raw["entries"][0]["team"] == "Miami Marlins"


# ============================== a pick the strategy has changed its mind about

def _mkdb(tmp_path, rows):
    """A tiny stand-in for mlb-paper's paper.db with just the columns read."""
    import sqlite3
    db = tmp_path / "paper.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE decisions (id TEXT, ts_utc TEXT, bot TEXT, "
                "mentality TEXT, exit_mode TEXT, game_key TEXT, game_pk INT, "
                "starts_utc TEXT, window TEXT, kind TEXT, ticker TEXT, "
                "side TEXT, quoted_price_c INT, conviction REAL, "
                "stated_prob_c REAL, edge_c REAL, stake_usd REAL, "
                "reasoning_json TEXT, reasoning_sha1 TEXT, outcome_known INT)")
    con.execute("CREATE TABLE ticks (ts_utc TEXT)")
    for r in rows:
        con.execute(
            "INSERT INTO decisions (id,ts_utc,bot,mentality,exit_mode,game_key,"
            "starts_utc,window,kind,ticker,side,quoted_price_c,reasoning_json,"
            "reasoning_sha1,outcome_known) VALUES (?,?,?,'starter','hold',?,?,"
            "'T-24h',?,?,'YES',?,?,'x',0)",
            (r["ts"], r["ts"], r["bot"], r["gk"], r["starts"], r["kind"],
             "KXMLBGAME-26AUG121840PITMIA-MIA", 52, json.dumps(r["j"])))
    con.commit()
    con.close()
    return db


def _entry_json():
    return {"reasoning": {"backed": "Miami Marlins", "fair_c": 99.0,
                          "price_c": 67, "flags": {"home": {
                              "flags": ["form_divergence"], "divergence_er9": -2.5,
                              "recent_era": 2.1, "season_era": 4.6,
                              "career_starts_prior": 16}}}}


def _shadow_json(passes):
    return {"reason": "adjustment does not survive the cost bar",
            "detail": {"passes": passes, "backed": "Miami Marlins",
                       "fair_c": 71.3, "price_c": 68, "flags": {}}}


def test_a_pick_the_strategy_has_dropped_is_retired(tmp_path):
    """THE REAL CASE, 2026-08-12. `starter__hold` takes one entry per game and
    then never writes another row for it, so a superseded entry would sit on
    the card for ever. mlb's amendment A3 cut one game from 99 cents to 71 and
    below the cost bar, and the old entry was still being offered."""
    import picks as P
    far = "2099-08-12T22:40:00+00:00"
    db = _mkdb(tmp_path, [
        {"ts": "2026-08-12T00:54:00+00:00", "bot": "starter__hold",
         "kind": "entry", "gk": "g1", "starts": far, "j": _entry_json()},
        {"ts": "2026-08-12T04:22:00+00:00", "bot": "starter__shadow",
         "kind": "shadow", "gk": "g1", "starts": far, "j": _shadow_json(False)},
    ])
    out, retired = [], []
    out = P.pending_picks(db=db, retired=retired)
    assert out == [], "a pick the strategy has dropped was still offered"
    assert len(retired) == 1 and "cost bar" in retired[0][1]


def test_an_OLDER_change_of_mind_does_not_retire_a_newer_pick(tmp_path):
    """Ordering matters both ways. A refusal recorded BEFORE the entry is what
    the entry already overruled."""
    import picks as P
    far = "2099-08-12T22:40:00+00:00"
    db = _mkdb(tmp_path, [
        {"ts": "2026-08-12T00:10:00+00:00", "bot": "starter__shadow",
         "kind": "shadow", "gk": "g1", "starts": far, "j": _shadow_json(False)},
        {"ts": "2026-08-12T04:22:00+00:00", "bot": "starter__hold",
         "kind": "entry", "gk": "g1", "starts": far, "j": _entry_json()},
    ])
    retired = []
    assert len(P.pending_picks(db=db, retired=retired)) == 1
    assert retired == []


def test_a_shadow_that_PASSES_never_retires_anything(tmp_path):
    """Every one of the 1,063 shadow rows on 2026-08-12 said passes=False. If
    a future one ever says True it must not be read as a refusal."""
    import picks as P
    far = "2099-08-12T22:40:00+00:00"
    db = _mkdb(tmp_path, [
        {"ts": "2026-08-12T00:54:00+00:00", "bot": "starter__hold",
         "kind": "entry", "gk": "g1", "starts": far, "j": _entry_json()},
        {"ts": "2026-08-12T04:22:00+00:00", "bot": "starter__shadow",
         "kind": "shadow", "gk": "g1", "starts": far, "j": _shadow_json(True)},
    ])
    retired = []
    assert len(P.pending_picks(db=db, retired=retired)) == 1
    assert retired == []


def test_the_card_says_when_the_bot_ignored_a_rookies_form(tmp_path):
    """mlb's A3 records an unusable divergence instead of using it. 'The bot
    looked and could not tell' is a different thing from 'the bot found
    nothing', and only one of them is honest about a rookie."""
    import picks as P
    s = P._side_sentence("Kansas City Royals", {
        "flags": ["form_divergence_IGNORED_only_1_starts_1.7ip", "debut_or_near"],
        "divergence_er9": 13.75, "recent_era": 16.2, "season_era": 2.45,
        "career_starts_prior": 1, "recent_ip": 1.67, "form_usable": False})
    assert "IGNORED" in s
    assert "only 1 career start" in s
    assert "16.2 earned runs" not in s, "it quoted a number it did not use"


def test_a_thin_pitcher_warns_at_a_smaller_gap(tmp_path):
    """mlb asked for this second trigger and the numbers are theirs."""
    import picks as P
    thin = {"fair_c": 58.0, "price_c": 52, "flags": {"home": {
        "flags": ["debut_or_near"], "career_starts_prior": 2}}}
    assert "CAREFUL" in P._warning(thin)
    fat = {"fair_c": 58.0, "price_c": 52, "flags": {"home": {
        "flags": ["form_divergence"], "career_starts_prior": 20}}}
    assert P._warning(fat) == "", "a 6c gap on an established pitcher must stay quiet"


# ========================= the void that used to cost him the bet (mailbox 002)

def test_a_void_offers_the_bet_once_more(led):
    """2026-08-12: he copied Pittsburgh, Cleveland and Seattle, got lost on the
    Kalshi page, came back and pressed "I did NOT place this" on all three --
    and all three games were then closed for ever having never been bet.

    A void means NO MONEY WAS PLACED. Guard 1 exists to stop the same bet going
    on twice; re-offering something he never placed is not that."""
    led.add(_entry(signal="s1"))
    assert led.may_bet(GK, "s1")[0] is False, "not while it is open"
    led.entries[0].status = "void"
    led.save()
    ok, why = led.may_bet(GK, "s1")
    assert ok, f"a voided bet must come back once: {why}"


def test_the_SECOND_void_closes_it_for_good(led):
    """Otherwise he can copy, void, copy, void and eventually buy at a price
    the bot never saw."""
    assert MAX_VOIDS_BEFORE_CLOSED == 2
    for i in range(2):
        e = _entry(ticker=f"T{i}", signal="s1")
        e.status = "void"
        led.entries.append(e)
    led.save()
    ok, why = led.may_bet(GK, "s1")
    assert not ok and "already been taken" in why


def test_a_bet_really_placed_still_closes_it_immediately(led):
    """The reopen must not weaken the guard for money that actually went on."""
    led.add(_entry(signal="s1"))
    led.settle("T1", won=False)
    assert led.may_bet(GK, "s1")[0] is False


def test_one_void_and_one_real_bet_still_closes_it(led):
    led.entries.append(_entry(ticker="T0", signal="s1", status="void"))
    led.entries.append(_entry(ticker="T1", signal="s1", status="open"))
    led.save()
    assert led.may_bet(GK, "s1")[0] is False


# =================================================== Guard 5: the daily caps

def _today(n=0):
    from datetime import datetime as dt
    return dt.now().astimezone().replace(microsecond=0).isoformat()


def test_guard5_his_numbers(led):
    assert MAX_ORDERS_PER_DAY == 10
    assert MAX_STAKE_PER_DAY_USD == 25.00


def test_guard5_the_money_cap_stops_him_before_the_order_cap(led):
    """At $4.15 a bet, six bets is $24.90 and a seventh would be $29.05. So the
    limit of 10 orders can never be reached. He must not think he raised his
    ceiling from 6 to 10 when he did not."""
    for i in range(6):
        led.entries.append(_entry(game_key=f"g{i}", ticker=f"T{i}",
                                  signal=f"s{i}", cost=4.15,
                                  confirmed_utc=_today()))
    led.save()
    n, spent = led.daily_used()
    assert n == 6 and spent == pytest.approx(24.90)
    assert led.daily_block(4.15), "a seventh bet must be refused on money"
    assert "daily limit" in led.daily_block(4.15)


def test_guard5_says_WHICH_cap_will_actually_stop_him(led):
    line = led.daily_line()
    assert "0 of 10 bets" in line and "$0.00 of $25.00" in line
    assert "money runs out first, after 6 more" in line


def test_guard5_that_sentence_is_computed_not_hard_coded(led, monkeypatch):
    """It has to stay true if any of the three numbers change."""
    import ledger as L
    monkeypatch.setattr(L, "MAX_STAKE_PER_DAY_USD", 500.0)
    assert "order count runs out first, after 10 more" in led.daily_line()


def test_guard5_fails_CLOSED_when_today_cannot_be_counted(led):
    """An unreadable ledger means no bet, never an unlimited one."""
    led.entries.append(_entry(signal="s1"))
    led.entries[0].confirmed_utc = "not a date at all"
    led.save()
    with pytest.raises(ValueError):
        led.daily_used()
    msg = led.daily_block(4.15)
    assert msg and "no bet" in msg
    assert led.may_bet("other-game", "s-new")[0] is False


def test_guard5_a_void_does_not_use_up_the_day(led):
    """He never placed it, so it did not cost him a bet or a dollar."""
    led.entries.append(_entry(signal="s1", status="void", cost=4.15,
                              confirmed_utc=_today()))
    led.save()
    assert led.daily_used() == (0, 0.0)


def test_guard5_yesterdays_bets_do_not_count_against_today(led):
    led.entries.append(_entry(signal="s1", cost=4.15,
                              confirmed_utc="2026-08-01T12:00:00-04:00"))
    led.save()
    assert led.daily_used() == (0, 0.0)
