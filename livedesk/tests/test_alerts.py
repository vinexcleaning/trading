"""Phone alerts: the daily summary, and the promise that it cannot break the desk.

    livedesk\\test.bat

⚠ THE MOST IMPORTANT TEST IN THIS FILE IS `test_a_notifier_that_throws_on_every
_call_changes_nothing`. Everything else here is about a message being right.
That one is about a message failing being unable to stop a bet, and it is the
only reason it was safe to put a network call inside the refresh loop.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import alerts                                            # noqa: E402
from alerts import DeskAlerts, summary_text              # noqa: E402
from ledger import Entry, Ledger                         # noqa: E402


class FakeNotifier:
    """Records instead of sending. `enabled` mirrors the real one."""

    def __init__(self, healthcheck_url=""):
        self.sent = []
        self.beats = 0
        self.healthcheck_url = healthcheck_url

    @property
    def enabled(self):
        return True

    def send(self, message, title="", kind="info", priority="default", tags=""):
        self.sent.append({"message": message, "title": title, "kind": kind,
                          "priority": priority})

    def heartbeat(self):
        self.beats += 1


class ExplodingNotifier(FakeNotifier):
    def send(self, *a, **k):
        raise RuntimeError("ntfy is down")

    def heartbeat(self):
        raise RuntimeError("healthchecks is down")


@pytest.fixture
def led(tmp_path):
    lg = Ledger(tmp_path / "ledger.json")
    lg.account_positions = []
    return lg


def _bet(led, team="Miami Marlins", status="open", cost=5.0, pnl_when=None,
         placed=None, settled=None):
    now = datetime.now().astimezone()
    e = Entry(game_key=f"k:{team}", ticker=f"T-{team}-{len(led.entries)}",
              event_ticker="E", team=team, matchup=f"{team} at Home",
              side="YES", price_c=50, contracts=10, cost_usd=cost,
              fee_usd=0.10, win_profit_usd=4.9, lose_usd=cost,
              starts_utc=(datetime.now(timezone.utc)
                          + timedelta(hours=3)).isoformat(),
              confirmed_utc=(placed or now).isoformat(),
              signal=f"sig-{team}-{len(led.entries)}")
    e.status = status
    if status in ("won", "lost"):
        e.settled_utc = (settled or now).isoformat()
        # ⚠ `pnl_usd` IS A STORED FIELD, not computed from win_profit/lose. Only
        # `settle()` ever sets it, so a test that fakes a settled bet must set
        # it too -- the first version did not and every day read $0.00.
        e.pnl_usd = e.win_profit_usd if status == "won" else -e.lose_usd
    led.entries.append(e)
    led.save()
    return e


# --------------------------------------------------- the message he will read

def test_a_day_with_no_bets_still_produces_a_message(led):
    """⚠ THE WHOLE POINT OF THE DAILY SUMMARY. If it only sent on days with
    bets, silence would mean either 'nothing qualified' or 'the laptop is
    off', and he could not tell which -- which is exactly the failure he asked
    to be protected from."""
    text = summary_text(led)
    assert "no bets placed today" in text
    assert "Baseball desk" in text


def test_it_says_money_AND_the_percent_as_money(led):
    """CLAUDE.md: money, or out of 100. Never a bare percentage."""
    _bet(led, "Miami Marlins", "won", cost=10.0)
    led.entries[-1].status = "won"
    text = summary_text(led)
    assert "$" in text
    assert "for every $100 staked" in text, text
    assert "%" not in text, "a bare percentage is ambiguous and is banned here"


def test_the_percent_is_over_what_he_STAKED_not_his_balance(led):
    """He is shown $110 back per $100 when he staked $10 and made $1. If it
    divided by his bankroll instead, the same day would read $101 and mean
    something completely different."""
    e = _bet(led, "Miami Marlins", "won", cost=10.0)
    e.win_profit_usd = e.pnl_usd = 1.0
    led.account_balance_usd = 1000.00
    led.save()
    assert "$110 back for every $100 staked" in summary_text(led)


def test_a_losing_day_says_down_not_a_minus_sign(led):
    e = _bet(led, "Miami Marlins", "lost", cost=10.0)
    e.lose_usd = 10.0
    e.pnl_usd = -10.0
    led.save()
    text = summary_text(led)
    assert "down $10.00 for the day" in text, text


def test_bets_placed_today_and_bets_settled_today_are_different_questions(led):
    """A bet placed this evening on a game tomorrow is in one count and not
    the other. Folding them together would report tonight as flat."""
    yesterday = datetime.now().astimezone() - timedelta(days=1)
    _bet(led, "Old Bet", "won", cost=8.0, placed=yesterday, settled=yesterday)
    _bet(led, "New Bet", "open", cost=6.0)
    s = led.day_summary()
    assert s["placed"] == 1, "only today's placement counts"
    assert s["won"] + s["lost"] == 0, "yesterday's settlement is not today's"


def test_yesterdays_settled_bet_is_not_in_todays_money(led):
    yesterday = datetime.now().astimezone() - timedelta(days=1)
    _bet(led, "Old", "won", cost=8.0, placed=yesterday, settled=yesterday)
    assert led.day_summary()["money"] == 0.0


def test_an_unreadable_date_is_reported_and_does_not_stop_the_message(led):
    """⚠ `_today_entries` RAISES on a bad date, and that is correct for the
    daily CAP -- an unreadable ledger must mean no order, never an unlimited
    one. It is the wrong answer for a summary: silence is the thing this is
    built to prevent, so the gap is reported and the message still goes."""
    e = _bet(led, "Broken")
    e.confirmed_utc = "not a date at all"
    led.save()
    text = summary_text(led)
    assert "unreadable" in text
    assert "Baseball desk" in text


def test_it_says_how_much_is_still_riding(led):
    _bet(led, "Miami Marlins", "open", cost=5.0)
    led.account_positions = None      # never read -> falls back to our record
    assert "still running" in summary_text(led)


# -------------------------------------------- it cannot break the betting path

def test_a_notifier_that_throws_on_every_call_changes_nothing(led, tmp_path):
    """⚠ THE ONE THAT MATTERS. This is why a network call was allowed inside
    the refresh loop at all. If ntfy is down, or his internet is, or the topic
    is wrong, `tick` must return quietly and the desk must go on placing bets
    exactly as before."""
    a = DeskAlerts(notifier=ExplodingNotifier(),
                   state_path=tmp_path / "state.json")
    a.tick(led)                                  # must not raise
    assert a.last_error, "and it must not swallow the failure silently either"


def test_a_missing_notifier_is_not_an_error(led, tmp_path):
    a = DeskAlerts(notifier=None, state_path=tmp_path / "state.json")
    a.n = None
    assert a.tick(led) == ""
    assert not a.enabled


def test_it_never_writes_to_the_ledger(led, tmp_path):
    _bet(led, "Miami Marlins", "open", cost=5.0)
    before = (led.path.read_text(encoding="utf-8"))
    a = DeskAlerts(notifier=FakeNotifier(), state_path=tmp_path / "s.json")
    a.tick(led)
    summary_text(led)
    assert led.path.read_text(encoding="utf-8") == before


def test_its_state_file_is_not_the_real_one(tmp_path):
    """A test wrote over his real ledger once because a default argument was
    bound at definition. Same shape, so the same check."""
    a = DeskAlerts(notifier=FakeNotifier(), state_path=tmp_path / "s.json")
    assert a.state_path != alerts.STATE_PATH
    assert "livedesk" not in str(a.state_path).replace(str(tmp_path), "")


# ------------------------------------------------------------- the scheduling

def _at(hour):
    return datetime.now().astimezone().replace(hour=hour, minute=5)


def test_nothing_is_sent_before_the_hour(led, tmp_path):
    n = FakeNotifier()
    a = DeskAlerts(notifier=n, hour=22, state_path=tmp_path / "s.json")
    a.tick(led, now=_at(9))
    assert n.sent == []


def test_it_sends_once_after_the_hour_and_not_again(led, tmp_path):
    """The loop runs every 60 seconds. Without this he gets the same summary
    sixty times before midnight and turns the app off."""
    n = FakeNotifier()
    a = DeskAlerts(notifier=n, hour=22, state_path=tmp_path / "s.json")
    a.tick(led, now=_at(22))
    a.tick(led, now=_at(22))
    a.tick(led, now=_at(23))
    assert len(n.sent) == 1, [m["title"] for m in n.sent]


def test_the_once_a_day_lock_survives_the_window_being_reopened(led, tmp_path):
    """He closes and reopens the desk constantly. An in-memory flag would send
    the summary again every time."""
    sp = tmp_path / "s.json"
    n1 = FakeNotifier()
    DeskAlerts(notifier=n1, hour=22, state_path=sp).tick(led, now=_at(22))
    n2 = FakeNotifier()
    DeskAlerts(notifier=n2, hour=22, state_path=sp).tick(led, now=_at(23))
    assert len(n1.sent) == 1 and n2.sent == []


def test_the_heartbeat_goes_every_single_tick(led, tmp_path):
    """Not once a day. A dead-man switch that beats daily tells him the laptop
    died some time in the last 24 hours, which is useless."""
    n = FakeNotifier()
    a = DeskAlerts(notifier=n, hour=22, state_path=tmp_path / "s.json")
    for _ in range(5):
        a.tick(led, now=_at(9))
    assert n.beats == 5


# ------------------------------------- telling him when it is NOT protecting him

def test_it_says_so_when_nothing_watches_for_it_dying(led, tmp_path):
    """⚠ ntfy alone CANNOT report the laptop losing power, and a man who
    believes he is covered and is not is worse off than one who knows he is
    not. So the window says which of the two he has."""
    a = DeskAlerts(notifier=FakeNotifier(healthcheck_url=""),
                   state_path=tmp_path / "s.json")
    assert not a.watching
    assert "NOTHING WATCHES FOR THIS DYING" in a.status_line()

    b = DeskAlerts(notifier=FakeNotifier(healthcheck_url="https://hc-ping.com/x"),
                   state_path=tmp_path / "s2.json")
    assert b.watching
    assert "death-watch on" in b.status_line()


def test_alerts_off_says_silence_means_nothing(led, tmp_path):
    class Off(FakeNotifier):
        @property
        def enabled(self):
            return False
    a = DeskAlerts(notifier=Off(), state_path=tmp_path / "s.json")
    assert "silence tells you nothing" in a.status_line()


def test_every_line_it_prints_is_plain_ascii(led, tmp_path):
    """The Windows console is cp1252 and a dash killed `set_key.py` mid-run,
    in front of him, on the step that sets up his API key."""
    for line in (DeskAlerts(notifier=FakeNotifier(),
                            state_path=tmp_path / "s.json").status_line(),
                 summary_text(led)):
        line.encode("cp1252")


def test_no_statistics_words_reach_his_phone(led):
    """CLAUDE.md forbids these outright -- he cannot argue back with words he
    cannot follow, and that costs the project the one thing only he knows."""
    _bet(led, "Miami Marlins", "won", cost=10.0)
    text = summary_text(led).lower()
    for banned in ("p-value", "brier", "holdout", " ev ", "variance", "sigma",
                   "bps", " pp", "n=", "clustered", "residual"):
        assert banned not in text, f"{banned!r} reached his phone"
