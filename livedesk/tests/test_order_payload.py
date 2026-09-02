"""The exact body posted to Kalshi when a real order goes out. Mailbox 024.

    livedesk\\test.bat

⚠ THIS IS THE LAST UNGUARDED STEP BETWEEN A CODE CHANGE AND A WRONG REAL ORDER.

`test_demo_exec.py` covers everything ABOVE this layer -- read-back,
one-call-one-order, resting not recorded as filled, cancelled recorded as
cancelled -- by mocking the client. So the dict that actually reaches the
exchange was never asserted anywhere, and a change to it would ship silently
and green.

The comment above that dict in `kalshi_client.py` says getting any of these
wrong "places a wrong order". It is right, and the shapes are unusual enough to
be easy to break:

    count  ->  a STRING, "10.00", not the integer 10
    price  ->  a DOLLAR string to four places, "0.7400", not 74 cents
    side   ->  "bid" to buy YES. Not "yes", not "buy"
    plus   ->  time_in_force and self_trade_prevention_type, explicitly

⚠ AND THE FILE THIS TESTS IS NOT IN THIS FOLDER. `kalshi_client.py` lives in
`kalshi-inplay-bot/`, which has looked switched off since 3 August -- so
somebody tidying up a dormant tennis project is editing the code that places
his real baseball orders. That is exactly why this test lives here, in the
project that depends on it, rather than there.

NOTHING HERE TOUCHES THE NETWORK. The transport is replaced with a stub that
records what it was handed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

LIVEDESK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIVEDESK / "src"))
sys.path.insert(0, str(LIVEDESK.parent / "kalshi-inplay-bot"))

from kalshi_client import KalshiClient                      # noqa: E402


@pytest.fixture
def client(monkeypatch, tmp_path):
    """A production client whose transport is a stub. Never posts anywhere."""
    c = KalshiClient.__new__(KalshiClient)
    c.demo = False
    c.read_only = False
    c.kill_switch = str(tmp_path / "no-such-switch")
    sent = {}

    def fake_post(path, body):
        sent["path"] = path
        sent["body"] = body
        return {"order": {"order_id": "stub"}}

    c._post = fake_post
    c.sent = sent
    return c


# ------------------------------------------------------- the exact payload

def test_the_posted_body_is_exactly_what_kalshi_expects(client):
    client._order("KXMLBGAME-TEST-XYZ", "bid", 10, 74)
    body = client.sent["body"]

    assert client.sent["path"] == "/portfolio/events/orders"
    assert body["ticker"] == "KXMLBGAME-TEST-XYZ"
    assert body["side"] == "bid"
    assert body["count"] == "10.00", "count is a STRING, not the integer 10"
    assert body["price"] == "0.7400", \
        "price is a dollar string to four places, not 74 cents"
    assert body["time_in_force"] == "good_till_canceled"
    assert body["self_trade_prevention_type"] == "taker_at_cross"
    assert body["client_order_id"]


def test_no_field_appears_or_disappears_without_this_test_failing(client):
    """⚠ AN EXTRA FIELD IS AS DANGEROUS AS A MISSING ONE. Kalshi may accept a
    body with something unexpected in it and act on it. Pinning the exact key
    set is the point -- checking only the keys we happen to think of would let
    a new one through."""
    client._order("T", "bid", 1, 50)
    assert set(client.sent["body"]) == {
        "ticker", "side", "count", "price", "time_in_force",
        "self_trade_prevention_type", "client_order_id"}


def test_every_order_carries_its_own_id(client):
    """Two orders sharing an id is how a retry becomes a duplicate bet -- and
    eight orders landed on one Baltimore market on 2026-08-17."""
    client._order("T", "bid", 1, 50)
    first = client.sent["body"]["client_order_id"]
    client._order("T", "bid", 1, 50)
    assert client.sent["body"]["client_order_id"] != first


@pytest.mark.parametrize("cents,expect", [
    (1, "0.0100"), (7, "0.0700"), (50, "0.5000"),
    (74, "0.7400"), (97, "0.9700"), (99, "0.9900"),
])
def test_the_price_string_is_right_across_the_whole_range(client, cents,
                                                          expect):
    """Cheap and dear both matter. The fee at 97 cents is 0.20c against the
    3.6-4.8c this repo habitually quotes, so the extremes are where the money
    is and where a formatting slip would be least obvious."""
    client._order("T", "bid", 1, cents)
    assert client.sent["body"]["price"] == expect


def test_a_big_count_is_still_a_two_decimal_string(client):
    client._order("T", "bid", 250, 33)
    assert client.sent["body"]["count"] == "250.00"


# ------------------------------------------- what it refuses to send at all

@pytest.mark.parametrize("side", ["yes", "buy", "BID", "", "no"])
def test_a_side_that_is_not_bid_or_ask_never_reaches_the_wire(client, side):
    with pytest.raises(ValueError):
        client._order("T", side, 1, 50)
    assert not client.sent, "nothing may be posted when validation fails"


@pytest.mark.parametrize("cents", [0, -1, 100, 101, 1000])
def test_a_price_outside_1_to_99_never_reaches_the_wire(client, cents):
    with pytest.raises(ValueError):
        client._order("T", "bid", 1, cents)
    assert not client.sent


@pytest.mark.parametrize("count", [0, -5])
def test_a_count_below_one_never_reaches_the_wire(client, count):
    with pytest.raises(ValueError):
        client._order("T", "bid", count, 50)
    assert not client.sent


def test_the_kill_switch_is_checked_BEFORE_anything_else(client, tmp_path):
    """⚠ ORDER MATTERS. `_check_writable()` runs first, so a switched-off desk
    refuses even an order that is also malformed. If validation ran first, the
    error he saw would be about the price and he would 'fix' it and get an
    order out through a switch that was meant to stop him."""
    switch = tmp_path / "TRADING_DISABLED"
    switch.write_text("off", encoding="utf-8")
    client.kill_switch = str(switch)
    with pytest.raises(PermissionError):
        client._order("T", "not-a-side", 0, 999)
    assert not client.sent


def test_read_only_cannot_place(client):
    client.read_only = True
    with pytest.raises(PermissionError):
        client._order("T", "bid", 1, 50)
    assert not client.sent
