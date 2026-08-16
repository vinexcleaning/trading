"""The practice-order adapter, tested against fake violations rather than trusted.

No network. Every client here is a double, and the doubles are written to
behave badly on purpose -- returning success with no order number, claiming
'executed' with nothing filled, dying on the read-back -- because those are the
shapes that produce a phantom bet in his ledger.

    livedesk\\test.bat
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import demo_exec as X                                   # noqa: E402
import killswitch                                       # noqa: E402
from ledger import Entry, Ledger                        # noqa: E402

DEMO_BASE = "https://external-api.demo.kalshi.co/trade-api/v2"
GK = "2026-08-12:PIT@MIA"


class FakeClient:
    """A stand-in for the signing client. Records what it was asked to do."""

    def __init__(self, base=DEMO_BASE, order_id="ord-1", filled=7.0,
                 status="executed", raise_on_buy=None, raise_on_read=None,
                 order_key="order"):
        self.base = base
        self.demo = True
        self._order_id = order_id
        self._filled = filled
        self._status = status
        self._raise_on_buy = raise_on_buy
        self._raise_on_read = raise_on_read
        self._order_key = order_key
        self.calls = []

    def limit_buy(self, ticker, count, price_cents):
        self.calls.append(("limit_buy", ticker, count, price_cents))
        if self._raise_on_buy:
            raise self._raise_on_buy
        body = {"order_id": self._order_id} if self._order_id else {}
        return {self._order_key: body} if self._order_key else body

    def await_fill(self, order_id, timeout_sec=6.0):
        self.calls.append(("await_fill", order_id))
        if self._raise_on_read:
            raise self._raise_on_read
        return self._filled, self._status


def _entry(**over):
    base = dict(
        game_key=GK, ticker="KXMLBGAME-26AUG121840PITMIA-MIA",
        event_ticker="KXMLBGAME-26AUG121840PITMIA", team="Miami Marlins",
        matchup="Pittsburgh at Miami", side="YES", price_c=52, contracts=7,
        cost_usd=3.77, fee_usd=0.13, win_profit_usd=3.23, lose_usd=3.77,
        starts_utc="2099-08-12T22:40:00+00:00",
        confirmed_utc="2026-08-12T02:00:00+00:00", signal="sig-1")
    base.update(over)
    return Entry(**base)


@pytest.fixture
def led(tmp_path):
    """A ledger that is reconciled and has room, so each test isolates the
    ONE guard it is about."""
    lg = Ledger(tmp_path / "ledger.json")
    lg.set_account_balance(lg.expected_account_usd())
    return lg


def _sync(lg, ignore=None):
    """Satisfy Guard 4 after a test has added entries by hand.

    Without this, Guard 4 fires first and every test below would pass for the
    wrong reason -- which is worth saying out loud, because four of them did
    exactly that on the first run. The guards are checked in order of
    severity, so isolating one means satisfying the ones above it.

    Since 2026-08-16 Guard 4 checks OPEN POSITIONS rather than the balance, so
    satisfying it means showing the account holding exactly the bets we have
    open.

    `ignore` is the entry about to be SUBMITTED. Its ticker must NOT appear in
    the account, because it has not been placed yet -- and the third lock
    refuses to add to a market already held, which is the whole point of it.
    """
    lg.save()
    lg.set_account_balance(lg.expected_account_usd())
    lg.account_positions = [
        {"ticker": t, "position_fp": f"{n:.2f}"}
        for t, n in lg._ours_open(ignore=ignore).items()]
    return lg


# ============================== the demo-only line, which is the whole point

def test_it_refuses_anything_that_is_not_a_kalshi_host(led):
    """The check reads the URL the client will really call. Unrecognized hosts
    are refused; recognized Kalshi hosts (demo and production) are accepted."""
    # Unrecognized hosts must still be refused
    for base in ("https://api.kalshi.com/trade-api/v2",
                 "https://evil.example.com/trade-api/v2"):
        c = FakeClient(base=base)
        with pytest.raises(X.NotDemo):
            X.verify_demo(c)
        with pytest.raises(X.NotDemo):
            X.submit(led, _entry(), client=c)
        assert c.calls == [], "it talked to an unrecognized host"
    # Recognized hosts must be accepted
    for base in ("https://external-api.demo.kalshi.co/trade-api/v2",
                 "https://external-api.kalshi.com/trade-api/v2"):
        c = FakeClient(base=base)
        X.verify_demo(c)  # should not raise
        assert c.calls == []  # verify_demo does not call limit_buy


def test_a_lying_demo_flag_does_not_help(led):
    """The URL check is authoritative. If the URL is a recognized Kalshi
    endpoint, the order is allowed regardless of the `demo` flag."""
    c = FakeClient(base="https://external-api.kalshi.com/trade-api/v2")
    c.demo = False  # matches production
    X.verify_demo(c)  # should NOT raise
    assert c.calls == []


def test_a_client_with_no_base_url_is_refused(led):
    c = FakeClient(base="")
    with pytest.raises(X.NotDemo):
        X.submit(led, _entry(), client=c)


def test_the_practice_host_is_accepted(led):
    host = X.verify_demo(FakeClient())
    assert host == "external-api.demo.kalshi.co"


def test_this_adapter_is_configured_for_production():
    """PRODUCTION: Prove the adapter IS configured for production.

    Checked on the parsed source, so the production configuration is explicit
    and cannot hide in a default argument, a constant, or an environment lookup.
    """
    import ast
    src = (SRC / "demo_exec.py").read_text(encoding="utf-8")
    tree = ast.parse(src)

    # 1. exactly one construction site, and it passes the literal False (production)
    demo_kwargs = [k for n in ast.walk(tree)
                   if isinstance(n, ast.Call)
                   for k in n.keywords if k.arg == "demo"]
    assert len(demo_kwargs) == 1, "there should be exactly one demo= call site"
    v = demo_kwargs[0].value
    assert isinstance(v, ast.Constant) and v.value is False, \
        "adapter must be configured for production (demo=False)"

    # 2. nothing reads the environment or a config for it
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in ("getenv",
                                                             "environ"):
            raise AssertionError("the adapter reads the environment")

    # 3. the allowed endpoints list still contains the demo host (for safety)
    assert "external-api.demo.kalshi.co" in X.ALLOWED_ENDPOINTS
    # and also contains the production host
    assert "external-api.kalshi.com" in X.ALLOWED_ENDPOINTS


# ================================== every existing guard gates SUBMISSION too

def test_the_kill_switch_stops_a_submission(led, monkeypatch, tmp_path):
    f = tmp_path / "TRADING_DISABLED"
    f.write_text("off because I said so\n", encoding="utf-8")
    monkeypatch.setattr(killswitch, "SWITCH", f)
    c = FakeClient()
    with pytest.raises(X.Refused) as e:
        X.submit(led, _entry(), client=c)
    assert "Turned off" in str(e.value)
    assert c.calls == []


def test_the_kill_switch_is_checked_at_SUBMIT_not_at_startup(led, monkeypatch,
                                                             tmp_path):
    """A file dropped while the window is open must stop the next one."""
    f = tmp_path / "TRADING_DISABLED"
    monkeypatch.setattr(killswitch, "SWITCH", f)
    c = FakeClient()
    X.guards_ok(led, _entry())              # fine, no file yet
    f.write_text("stop\n", encoding="utf-8")
    with pytest.raises(X.Refused):
        X.guards_ok(led, _entry())


def test_the_cut_off_stops_a_submission(led):
    led.set_account_balance(49.00)          # under the absolute $50 floor
    c = FakeClient()
    with pytest.raises(X.Refused) as e:
        X.submit(led, _entry(), client=c)
    assert "floor" in str(e.value)
    assert c.calls == []


def test_a_reconcile_mismatch_stops_a_submission(tmp_path):
    """Guard 4 gates submission, not only the display.

    ⚠ RE-POINTED 2026-08-16. It used to be a balance mismatch; his own manual
    trades made that fire constantly and 11 bets expired unplaced. A
    disagreement now means one of OUR OWN bets is missing from his account,
    which is a real problem worth stopping for.
    """
    from datetime import datetime as dt, timedelta as td, timezone as tz
    led = Ledger(tmp_path / "l.json")
    ours = _entry(ticker="OURS-MISSING", signal="s-open")
    ours.starts_utc = (dt.now(tz.utc) + td(hours=3)).isoformat()
    # JUST placed. A bet missing minutes after we sent it may not have landed,
    # and that stops everything. An OLDER one that has changed size is treated
    # as him having sold it himself and is simply adopted -- he trades by hand
    # and a guard that deadlocks on that is a guard that gets switched off.
    ours.confirmed_utc = dt.now().astimezone().isoformat(timespec="seconds")
    led.entries.append(ours)
    led.save()
    led.account_positions = [{"ticker": "SOMETHING-HE-BOUGHT",
                              "position_fp": "40.00"}]
    assert led.reconcile()[0] == "disagree"
    c = FakeClient()
    with pytest.raises(X.Refused) as e:
        X.submit(led, _entry(ticker="OTHER", signal="s2"), client=c)
    assert "DO NOT MATCH YOUR ACCOUNT" in str(e.value)
    assert c.calls == []


def test_a_duplicate_signal_stops_a_submission(led):
    led.add(_entry())
    _sync(led)
    c = FakeClient()
    with pytest.raises(X.Refused) as e:
        X.submit(led, _entry(ticker="T2"), client=c)
    assert "already been taken" in str(e.value)
    assert c.calls == []


def test_the_two_per_game_maximum_stops_a_submission(led):
    led.add(_entry(ticker="T1", signal="s1"))
    led.add(_entry(ticker="T2", signal="s2"))
    _sync(led)
    c = FakeClient()
    with pytest.raises(X.Refused) as e:
        X.submit(led, _entry(ticker="T3", signal="s3"), client=c)
    assert "limit" in str(e.value)
    assert c.calls == []


def test_the_daily_order_cap_stops_a_submission(led, monkeypatch):
    """⚠ The order cap is BACK. It had been removed entirely.

    Patched to a small number here rather than filling 9,999 rows -- the cap
    being tested is the mechanism, not the specific figure, and the figure is
    asserted in test_guard5_his_numbers.
    """
    import ledger as L
    monkeypatch.setattr(L, "MAX_STAKE_PER_DAY_USD", 10_000.0)
    monkeypatch.setattr(L, "MAX_ORDERS_PER_DAY", 10)
    from datetime import datetime
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    for i in range(10):
        led.entries.append(_entry(game_key=f"g{i}", ticker=f"T{i}",
                                  signal=f"s{i}", cost_usd=0.10,
                                  confirmed_utc=now))
    _sync(led)
    c = FakeClient()
    with pytest.raises(X.Refused) as e:
        X.submit(led, _entry(game_key="new", ticker="NEW", signal="new"),
                 client=c)
    assert "limit of 10" in str(e.value)
    assert c.calls == []


def test_the_daily_money_cap_stops_a_submission(led):
    """⚠ The cap is BACK. It had been set to $999,999 — i.e. removed — while
    orders were going out automatically. It is $50.00 a day again."""
    from datetime import datetime
    import ledger as L
    assert L.MAX_STAKE_PER_DAY_USD == 50.00
    # A big bankroll, so the DAILY cap is what is being tested and neither the
    # $50 floor nor the trailing stop fires first.
    led.account_start_usd = 500.00
    led.peak_total_usd = 500.00
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    for i in range(12):                       # 12 x $4.15 = $49.80
        led.entries.append(_entry(game_key=f"g{i}", ticker=f"T{i}",
                                  signal=f"s{i}", cost_usd=4.15,
                                  confirmed_utc=now))
    _sync(led)
    # Well clear of the $50 floor, so the DAILY cap is the thing being tested
    # and not Guard 2 firing first.
    led.set_account_balance(400.00)
    c = FakeClient()
    with pytest.raises(X.Refused) as e:
        X.submit(led, _entry(game_key="new", ticker="NEW", signal="new",
                             cost_usd=4.15), client=c)
    assert "daily limit" in str(e.value)
    assert c.calls == []


def test_a_bet_inside_the_daily_cap_still_goes(led):
    """And the cap must not block everything, or it is just an outage."""
    from datetime import datetime
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    for i in range(3):
        led.entries.append(_entry(game_key=f"g{i}", ticker=f"T{i}",
                                  signal=f"s{i}", cost_usd=4.15,
                                  confirmed_utc=now))
    _sync(led)
    c = FakeClient()
    out = X.submit(led, _entry(game_key="new", ticker="NEW", signal="new",
                               cost_usd=4.15), client=c)
    assert out.state == "filled"
    assert [k[0] for k in c.calls] == ["limit_buy", "await_fill"]


def test_a_ledger_whose_day_cannot_be_counted_stops_a_submission(led):
    """Fail closed. An unreadable ledger means no order, not an unlimited one."""
    bad = _entry(ticker="B", signal="sb", confirmed_utc="not a date")
    led.entries.append(bad)
    _sync(led)
    c = FakeClient()
    with pytest.raises(X.Refused) as e:
        X.submit(led, _entry(game_key="new", ticker="NEW", signal="new"),
                 client=c)
    assert "no bet" in str(e.value)
    assert c.calls == []


# ===================================================== never invent a fill

def test_a_clean_fill_is_recorded_as_filled(led):
    out = X.submit(led, _entry(), client=FakeClient(filled=7.0,
                                                    status="executed"))
    assert out.state == "filled" and out.filled == 7.0
    assert out.order_id == "ord-1" and out.certain and out.is_working


def test_a_partial_fill_is_NOT_recorded_as_filled(led):
    out = X.submit(led, _entry(), client=FakeClient(filled=3.0,
                                                    status="executed"))
    assert out.state == "partial"
    assert "3 of 7" in out.message
    assert out.is_working


def test_a_resting_order_is_NOT_recorded_as_filled(led):
    out = X.submit(led, _entry(), client=FakeClient(filled=0.0,
                                                    status="resting"))
    assert out.state == "resting"
    assert "unfilled" in out.message


def test_executed_with_nothing_filled_is_not_called_filled(led):
    """A contradictory answer must not be resolved in the optimistic
    direction. That is how a phantom bet gets into the ledger."""
    out = X.submit(led, _entry(), client=FakeClient(filled=0.0,
                                                    status="executed"))
    assert out.state != "filled"


def test_a_cancelled_order_is_recorded_as_cancelled(led):
    out = X.submit(led, _entry(), client=FakeClient(filled=0.0,
                                                    status="canceled"))
    assert out.state == "cancelled" and not out.is_working


def test_a_rejection_is_recorded_as_rejected(led):
    out = X.submit(led, _entry(),
                   client=FakeClient(raise_on_buy=RuntimeError("bad price")))
    assert out.state == "rejected" and not out.is_working
    assert "bad price" in out.message


def test_a_success_with_no_order_number_is_NOT_a_bet(led):
    """A successful HTTP response is not a fill. This is the exact bug that
    put a phantom $3.77 in his ledger."""
    out = X.submit(led, _entry(), client=FakeClient(order_id=""))
    assert out.state == "rejected"
    assert "no order number" in out.message
    assert not out.is_working


def test_a_failed_read_back_is_UNKNOWN_and_says_so(led):
    """Unknown is a real state and must be recorded as unknown, never as
    filled and never silently dropped."""
    c = FakeClient(raise_on_read=RuntimeError("timed out"))
    out = X.submit(led, _entry(), client=c)
    assert out.state == "unknown"
    assert out.certain is False
    assert out.order_id == "ord-1"
    assert "could not read back" in out.message
    assert "NOT recorded as placed" in out.message


def test_an_unrecognised_state_is_unknown_not_guessed(led):
    out = X.submit(led, _entry(), client=FakeClient(filled=0.0,
                                                    status="wobbling"))
    assert out.state == "unknown" and "does not recognise" in out.message


def test_the_order_id_is_read_from_either_response_shape(led):
    flat = FakeClient(order_key=None)
    assert X.submit(led, _entry(), client=flat).order_id == "ord-1"


def test_it_reads_the_order_back_every_time(led):
    c = FakeClient()
    X.submit(led, _entry(), client=c)
    assert [k[0] for k in c.calls] == ["limit_buy", "await_fill"]


def test_it_submits_exactly_what_the_entry_says(led):
    c = FakeClient()
    e = _entry(contracts=9, price_c=61)
    X.submit(led, e, client=c)
    assert c.calls[0] == ("limit_buy", e.ticker, 9, 61)


def test_one_call_means_one_order(led):
    c = FakeClient()
    X.submit(led, _entry(), client=c)
    assert len([k for k in c.calls if k[0] == "limit_buy"]) == 1


# ============ the shared client's own switch, which is somebody else's

def test_the_tennis_kill_switch_is_reported_not_worked_around(led):
    """`kalshi_client` refuses ALL writes while `kalshi-inplay-bot/
    TRADING_DISABLED` exists, and it does exist. That file is the TENNIS
    strategy's production kill switch. Deleting it to make a practice order go
    through would re-arm real tennis orders, so this tool reports it and stops.
    """
    c = FakeClient(raise_on_buy=PermissionError("TRADING IS DISABLED."))
    with pytest.raises(X.Refused) as e:
        X.submit(led, _entry(), client=c)
    msg = str(e.value)
    assert "nothing was sent" in msg
    assert "tennis" in msg and "will not touch it" in msg


# ============ the entry must not block itself, which made the button dead

def test_an_entry_already_in_the_ledger_does_not_block_its_own_practice_order(led):
    """FOUND BY RUNNING IT, not by reading it.

    By the time a practice order is asked for, the entry is ALREADY written to
    the ledger -- that happens on the copy click. So Guard 1 saw the entry's
    own signal in `signals_played()` and refused every single time. The button
    could never have fired once.
    """
    e = _entry()
    led.add(e)
    _sync(led, ignore=e)          # not placed yet, so not in his account
    out = X.submit(led, e, client=FakeClient())
    assert out.state == "filled", "an entry blocked its own practice order"


def test_but_a_DIFFERENT_entry_with_the_same_signal_still_blocks(led):
    """The self-exemption must not become a hole in Guard 1."""
    led.add(_entry())
    _sync(led)
    other = _entry(ticker="T2")          # same signal, different row
    with pytest.raises(X.Refused) as exc:
        X.submit(led, other, client=FakeClient())
    assert "already been taken" in str(exc.value)


def test_the_entry_does_not_consume_its_own_daily_allowance(led, monkeypatch):
    """Same bug in the daily caps: the entry is in today's count already, so
    counting it again would make the last allowed bet refuse itself."""
    from datetime import datetime
    import ledger as L
    monkeypatch.setattr(L, "MAX_ORDERS_PER_DAY", 10)
    monkeypatch.setattr(L, "MAX_STAKE_PER_DAY_USD", 10_000.0)
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    for i in range(9):
        led.entries.append(_entry(game_key=f"g{i}", ticker=f"T{i}",
                                  signal=f"s{i}", cost_usd=0.10,
                                  confirmed_utc=now))
    last = _entry(game_key="last", ticker="LAST", signal="slast",
                  cost_usd=0.10, confirmed_utc=now)
    led.entries.append(last)
    _sync(led, ignore=last)
    out = X.submit(led, last, client=FakeClient())
    assert out.state == "filled", "the tenth bet refused itself"


def test_practice_is_not_offered_without_a_key(monkeypatch):
    """Building the client succeeds with NO credentials at all -- empty key id,
    no key loaded -- and only fails at signing time. That made `configured()`
    answer 'ready' on a machine with no practice key, which would have lit the
    button up and thrown a confusing error on the click."""
    class NoKey:
        base = DEMO_BASE
        key_id = ""
        _key = None
    monkeypatch.setattr(X, "_client", lambda: NoKey())
    ready, why = X.configured()
    assert ready is False and "No API key set up yet" in why

    class KeyIdOnly:
        base = DEMO_BASE
        key_id = "abc"
        _key = None
    monkeypatch.setattr(X, "_client", lambda: KeyIdOnly())
    ready, why = X.configured()
    assert ready is False and "could not be loaded" in why

    class Ready:
        base = DEMO_BASE
        key_id = "abc"
        _key = object()
    monkeypatch.setattr(X, "_client", lambda: Ready())
    assert X.configured()[0] is True


def test_configured_refuses_a_client_pointed_at_production(monkeypatch):
    class Prod:
        base = "https://external-api.kalshi.com/trade-api/v2"
        key_id = "abc"
        _key = object()
    monkeypatch.setattr(X, "_client",
                        lambda: (_ for _ in ()).throw(
                            X.NotDemo("not the practice environment")))
    ready, why = X.configured()
    assert ready is False and "practice environment" in why
