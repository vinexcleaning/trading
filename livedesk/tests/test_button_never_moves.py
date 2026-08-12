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
        fair_c=58.4, why=["a short reason."], warning="")
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
    _root.ledger.save()
    _root.picks = []
    _root.quotes = {}
    _root.skipped = set()
    _root._clear_alert()
    _root._render()
    return _root


def _button_xy(a):
    a.update()
    a.update_idletasks()
    found = []

    def walk(w):
        for c in w.winfo_children():
            if isinstance(c, tk.Button) and (
                    "KALSHI" in c.cget("text") or "TOO EXPENSIVE" in c.cget("text")):
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
    app.picks = [_fake_pick(game_key=f"g{i}", ticker=f"T{i}-MIA")
                 for i in range(40)]
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
            confirmed_utc="2026-08-12T02:00:00+00:00"))
    app._render()
    assert _button_xy(app) == home, "the placed-bets list moved the button"

    # 8. the kill switch
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
    for i in range(9):
        app.ledger.entries.append(Entry(
            game_key=f"g{i}", ticker=f"T{i}", event_ticker="E",
            team="X", matchup="a at b", side="YES", price_c=52, contracts=7,
            cost_usd=3.77, fee_usd=0.13, win_profit_usd=3.23, lose_usd=3.77,
            starts_utc="2026-08-12T22:40:00+00:00",
            confirmed_utc="2026-08-12T02:00:00+00:00",
            status="lost", pnl_usd=-3.77))
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


def test_a_game_already_bet_is_never_offered(app):
    from ledger import Entry
    app.ledger.entries.append(Entry(
        game_key="2026-08-12:PIT@MIA", ticker="X", event_ticker="E",
        team="Miami Marlins", matchup="a at b", side="YES", price_c=52,
        contracts=7, cost_usd=3.77, fee_usd=0.13, win_profit_usd=3.23,
        lose_usd=3.77, starts_utc="2026-08-12T22:40:00+00:00",
        confirmed_utc="2026-08-12T02:00:00+00:00", status="lost", pnl_usd=-3.77))
    app.picks = [_fake_pick()]
    assert app._available() == [], "a settled game came back around"
