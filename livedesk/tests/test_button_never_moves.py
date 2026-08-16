"""The button lands on the same pixel in every state the card can be in.

This is his one named complaint about the app this one is modelled on:
"sometimes bars will get added on, and then it would end up moving the button,
which would piss me off."

It is tested by MEASURING the button's screen position, not by asserting that
the layout code looks careful. Every state below has, at some point in the
tennis app's history, changed the height of something above the button.

ONE Tk root for the whole module, reused. Creating and destroying a root per
test made the SECOND one fail to re-source `tk.tcl` about half the time, and it
failed as a **skip** -- which is the worst outcome available, because a silently
skipped test reads as a green run (GUARDS #9). One root, reset between tests.

Set `LIVEDESK_REQUIRE_GUI=1` and a missing display is a FAILURE, not a skip.
`test.bat` sets it, so the command a human runs can never come back green with
the button untested.
"""
from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))


def _no_display(e):
    if os.environ.get("LIVEDESK_REQUIRE_GUI"):
        pytest.fail(f"LIVEDESK_REQUIRE_GUI is set and there is no usable "
                    f"display, so the button test cannot run: {e}")
    pytest.skip(f"no display: {e}")


def _fake_pick(**over):
    import picks as P
    base = dict(
        game_key="2026-08-12:PIT@MIA",
        ticker="KXMLBGAME-26AUG121840PITMIA-MIA",
        event_ticker="KXMLBGAME-26AUG121840PITMIA",
        team="Miami Marlins", matchup="Pittsburgh Pirates at Miami Marlins",
        side="YES", quoted_price_c=52,
        starts_utc="2099-08-12T22:40:00+00:00",
        decided_utc="2026-08-12T02:42:42+00:00", window="T-24h",
        fair_c=58.4, why=["a short reason."], warning="",
        signal="2026-08-12:PIT@MIA|Miami Marlins|home:form_divergence")
    base.update(over)
    return P.Pick(**base)


@pytest.fixture(scope="module")
def _root(tmp_path_factory):
    """One window for the whole module. Built once, never destroyed until the
    module ends."""
    import ledger as L
    import desk as D
    path = tmp_path_factory.mktemp("livedesk") / "ledger.json"
    L.LEDGER_PATH = path
    try:
        a = D.Desk()
    except tk.TclError as e:
        _no_display(e)
    a.stop_flag.set()
    a.paused = True
    yield a
    try:
        a.destroy()
    except tk.TclError:
        pass


@pytest.fixture
def app(_root, monkeypatch):
    """The same window, wound back to a clean state for each test."""
    _root.ledger.entries.clear()
    # The balance and the peak persist on disk by design, so a test that sets
    # one must not leak into the next.
    _root.ledger.account_balance_usd = None
    _root.ledger.account_checked_utc = None
    _root.ledger.peak_total_usd = _root.ledger.account_start_usd
    _root.ledger.save()
    _root.picks = []
    _root.quotes = {}
    _root.skipped = set()
    _root._announced = set()
    _root.pending = None
    _root._clear_alert()
    _root._render()
    return _root


def _button_xy(a):
    a.update()
    a.update_idletasks()
    found = []

    def walk(w):
        for c in w.winfo_children():
            # Every state's PRIMARY button, whatever it is called. The
            # hand-off card's button is "I PLACED IT" and it has to land on
            # the same pixel as "COPY & OPEN KALSHI".
            if isinstance(c, tk.Button) and any(
                    k in c.cget("text")
                    for k in ("KALSHI", "TOO EXPENSIVE", "I PLACED IT")):
                found.append((c.winfo_rootx(), c.winfo_rooty()))
            walk(c)
    walk(a.card)
    assert len(found) == 1, f"expected exactly one main button, got {len(found)}"
    return found[0]


def test_the_button_holds_still_through_every_card_state(app, monkeypatch):
    import killswitch

    # 1. nothing on offer
    app.picks = []
    app._render()
    home = _button_xy(app)

    # 2. an ordinary trade
    app.picks = [_fake_pick()]
    app._render()
    assert _button_xy(app) == home, "a trade appearing moved the button"

    # 3. a trade carrying the UNUSUAL warning -- an extra line above the body
    app.picks = [_fake_pick(warning="UNUSUAL — " + "very long warning. " * 6)]
    app._render()
    assert _button_xy(app) == home, "the warning line moved the button"

    # 4. a reason long enough to need truncating
    app.picks = [_fake_pick(why=["a very long reason. " * 40] * 6)]
    app._render()
    assert _button_xy(app) == home, "a long reason moved the button"

    # 5. an alert in the strip, which used to be packed only when it had
    #    something to say -- so every message shoved the window down
    app._alert("something happened that is quite long " * 3, "error")
    app._render()
    assert _button_xy(app) == home, "an alert moved the button"
    app._clear_alert()
    app._render()
    assert _button_xy(app) == home, "clearing the alert moved the button"

    # 6. a long queue of other games underneath
    app.picks = [_fake_pick(game_key=f"g{i}", ticker=f"T{i}-MIA",
                            signal=f"sig{i}") for i in range(40)]
    app._render()
    assert _button_xy(app) == home, "the waiting list moved the button"

    # 7. bets in the list on the right
    from ledger import Entry
    for i in range(12):
        app.ledger.entries.append(Entry(
            game_key=f"done{i}", ticker=f"D{i}", event_ticker="E",
            team="Miami Marlins", matchup="a at b", side="YES", price_c=52,
            contracts=7, cost_usd=3.77, fee_usd=0.13, win_profit_usd=3.23,
            lose_usd=3.77, starts_utc="2026-08-12T22:40:00+00:00",
            confirmed_utc="2026-08-12T02:00:00+00:00", signal=f"done{i}"))
    app._render()
    assert _button_xy(app) == home, "the placed-bets list moved the button"

    # 8. the reconcile bar disagreeing, which paints the header amber and puts
    #    a long red sentence in the strip above the card.
    #    RE-POINTED 2026-08-16: a disagreement is now one of OUR bets missing
    #    from his account, not a balance that does not add up.
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    app.ledger.entries.clear()
    app.ledger.entries.append(Entry(
        game_key="live", ticker="OURS-MISSING", event_ticker="E", team="X",
        matchup="a at b", side="YES", price_c=52, contracts=7, cost_usd=3.77,
        fee_usd=0.13, win_profit_usd=3.23, lose_usd=3.77,
        starts_utc=(_dt.now(_tz.utc) + _td(hours=3)).isoformat(),
        confirmed_utc="2026-08-12T02:00:00+00:00", signal="live"))
    app.ledger.account_positions = []
    assert app._blocked()[0] == "unreconciled"
    app._render()
    assert _button_xy(app) == home, "the reconcile warning moved the button"

    # 9. the kill switch
    monkeypatch.setattr(killswitch, "SWITCH", Path(__file__))   # always exists
    app._render()
    assert _button_xy(app) == home, "the kill switch moved the button"


def test_the_button_is_dead_when_the_kill_switch_is_on(app, monkeypatch):
    import killswitch
    app.picks = [_fake_pick()]
    app._render()
    assert app._blocked() is None
    monkeypatch.setattr(killswitch, "SWITCH", Path(__file__))
    assert app._blocked()[0] == "off"
    app._render()

    def walk(w, out):
        for c in w.winfo_children():
            if isinstance(c, tk.Button):
                out.append(c)
            walk(c, out)
        return out
    for b in walk(app.card, []):
        assert str(b.cget("state")) == "disabled"


def test_the_button_is_dead_once_the_cut_off_fires(app):
    from ledger import Entry
    app.ledger.set_account_balance(49.00)      # under the absolute $50 floor
    app.picks = [_fake_pick()]
    assert app._blocked()[0] == "stopped"
    app._render()

    def walk(w, out):
        for c in w.winfo_children():
            if isinstance(c, tk.Button):
                out.append(c)
            walk(c, out)
        return out
    for b in walk(app.card, []):
        assert str(b.cget("state")) == "disabled"


def test_a_signal_already_bet_is_never_offered(app):
    """And a DIFFERENT signal on the same game still is -- that is his own
    correction and the reason the guard moved from game to signal."""
    from ledger import Entry
    p = _fake_pick()
    app.ledger.entries.append(Entry(
        game_key=p.game_key, ticker="X", event_ticker="E",
        team="Miami Marlins", matchup="a at b", side="YES", price_c=52,
        contracts=7, cost_usd=3.77, fee_usd=0.13, win_profit_usd=3.23,
        lose_usd=3.77, starts_utc="2026-08-12T22:40:00+00:00",
        confirmed_utc="2026-08-12T02:00:00+00:00", signal=p.signal,
        status="lost", pnl_usd=-3.77))
    app.picks = [p]
    assert app._available() == [], "a settled signal came back around"
    app.picks = [_fake_pick(signal=p.signal + "|different-trigger")]
    assert len(app._available()) == 1, "a different trigger must still be offered"


def test_the_handoff_card_keeps_the_button_on_the_same_pixel(app):
    """The click-by-click card (mailbox 002) replaces the trade card and must
    not move the button -- he goes to Kalshi and back, and it is the same
    button in the same place both times."""
    from money import size_bet
    p = _fake_pick()
    app.picks = [p]
    app._render()
    home = _button_xy(app)

    bet = size_bet(52)
    from ledger import Entry
    app.ledger.entries.append(Entry(
        game_key=p.game_key, ticker=p.ticker, event_ticker=p.event_ticker,
        team=p.team, matchup=p.matchup, side="YES", price_c=bet.price_c,
        contracts=bet.contracts, cost_usd=bet.cost_usd, fee_usd=bet.fee_usd,
        win_profit_usd=bet.win_profit_usd, lose_usd=bet.lose_usd,
        starts_utc=p.starts_utc, signal=p.signal,
        confirmed_utc="2026-08-12T20:00:00-04:00", why=list(p.why)))
    app.pending = (app.ledger.entries[-1], p, bet)
    app._render()
    assert _button_xy(app) == home, "the hand-off card moved the button"

    # and a big price move puts a long warning above it, which is the state
    # that has broken this layout before
    import prices as PRICES
    app.quotes[p.ticker] = PRICES.Quote(
        ticker=p.ticker, status="active", bid_c=70, ask_c=71,
        ask_size=100.0, result="")
    app._render()
    assert _button_xy(app) == home, "the price-moved warning moved the button"
    app.pending = None


def test_guard6_a_second_click_while_one_is_pending_does_nothing(app):
    """One click, one order. A double-click, a repeated callback or a stray
    retry must not start a second."""
    from money import size_bet
    p = _fake_pick()
    bet = size_bet(52)
    from ledger import Entry
    app.ledger.entries.append(Entry(
        game_key=p.game_key, ticker=p.ticker, event_ticker=p.event_ticker,
        team=p.team, matchup=p.matchup, side="YES", price_c=bet.price_c,
        contracts=bet.contracts, cost_usd=bet.cost_usd, fee_usd=bet.fee_usd,
        win_profit_usd=bet.win_profit_usd, lose_usd=bet.lose_usd,
        starts_utc=p.starts_utc, signal=p.signal,
        confirmed_utc="2026-08-12T20:00:00-04:00", why=list(p.why)))
    app.pending = (app.ledger.entries[-1], p, bet)
    before = len(app.ledger.entries)
    app._confirm(_fake_pick(game_key="other", ticker="OTHER-X",
                            signal="brand-new"), bet)
    assert len(app.ledger.entries) == before, "a second bet was started"
    app.pending = None


def test_nothing_else_is_offered_while_one_is_out_being_placed(app):
    from money import size_bet
    p = _fake_pick()
    app.picks = [p, _fake_pick(game_key="g2", ticker="T2-MIA", signal="s2")]
    app._render()
    from ledger import Entry
    bet = size_bet(52)
    app.ledger.entries.append(Entry(
        game_key=p.game_key, ticker=p.ticker, event_ticker=p.event_ticker,
        team=p.team, matchup=p.matchup, side="YES", price_c=bet.price_c,
        contracts=bet.contracts, cost_usd=bet.cost_usd, fee_usd=bet.fee_usd,
        win_profit_usd=bet.win_profit_usd, lose_usd=bet.lose_usd,
        starts_utc=p.starts_utc, signal=p.signal,
        confirmed_utc="2026-08-12T20:00:00-04:00", why=list(p.why)))
    app.pending = (app.ledger.entries[-1], p, bet)
    app._render()
    titles = [c.cget("text") for c in app.card.winfo_children()]
    assert any("DO THIS ON THE PAGE" in t for t in titles)
    app.pending = None
