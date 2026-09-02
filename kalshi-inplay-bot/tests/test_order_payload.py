"""The exact body this client posts to Kalshi when it places an order.

WHY THIS FILE EXISTS
--------------------
The repo-wide audit (2026-09-01, `tennis` mailbox 022) found that this folder,
which has looked dormant since 2026-08-03, is the path the live desk places
REAL ORDERS through: `livedesk/src/demo_exec.py:113` builds
`KalshiClient(demo=False, ...)` from here.

`livedesk`'s own tests are good but they **mock above this layer** — they assert
the kill-switch behaviour in both directions and never see the payload. So the
one thing nothing checked was the wire format itself: the price-as-dollar-string
and count-as-string encoding.

**Getting that encoding wrong does not raise. It sends a real order at the wrong
price or the wrong size**, which is the worst failure mode available to this
file. Every assertion below is about that.

Nothing here touches the network: `_post` is replaced with a recorder.
"""
from __future__ import annotations

import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kalshi_client import KalshiClient          # noqa: E402


class Recorder:
    """Stands in for `_post` and keeps what it was handed."""

    def __init__(self):
        self.calls = []

    def __call__(self, path, body):
        self.calls.append((path, body))
        return {"order": {"order_id": "test-order"}}

    @property
    def body(self):
        return self.calls[-1][1]


def client(**kw):
    """A client that cannot reach the network and cannot be blocked by a switch
    that happens to exist on this machine."""
    c = KalshiClient(demo=True, **kw)
    c._post = Recorder()
    return c


# ------------------------------------------------------------ the wire format
def test_price_is_sent_as_a_dollar_string_not_cents():
    """92 cents must go out as "0.9200". Sending "92" would be 92 DOLLARS."""
    c = client()
    c.limit_buy("KXATPMATCH-TEST", 10, 92)
    assert c._post.body["price"] == "0.9200"


def test_every_price_in_range_round_trips_to_the_same_cents():
    """The encoding must be exact at all 99 legal prices, not just the ones a
    developer happens to try. A rounding slip at one price is a real order at
    the wrong price."""
    c = client()
    for cents in range(1, 100):
        c.limit_buy("T", 1, cents)
        sent = c._post.body["price"]
        assert float(sent) * 100 == pytest.approx(cents, abs=1e-9), (
            f"{cents}c encoded as {sent!r}, which is {float(sent) * 100}c")


def test_count_is_sent_as_a_whole_number_string():
    c = client()
    c.limit_buy("T", 7, 50)
    assert c._post.body["count"] == "7.00"


def test_side_bid_is_buy_and_ask_is_sell():
    """`bid` buys YES and `ask` sells it. Swapping these two silently reverses
    every position the desk takes."""
    c = client()
    c.limit_buy("T", 1, 50)
    assert c._post.body["side"] == "bid"
    c.limit_sell("T", 1, 50)
    assert c._post.body["side"] == "ask"


def test_the_order_goes_to_the_orders_endpoint():
    c = client()
    c.limit_buy("T", 1, 50)
    assert c._post.calls[-1][0] == "/portfolio/events/orders"


def test_the_body_carries_exactly_the_expected_keys():
    """A key the exchange does not expect, or a missing one, is a rejected or
    misread order. Pinned so a well-meaning addition has to be deliberate."""
    c = client()
    c.limit_buy("T", 3, 41)
    assert set(c._post.body) == {
        "ticker", "side", "count", "price",
        "time_in_force", "self_trade_prevention_type", "client_order_id",
    }


def test_orders_rest_rather_than_being_cancelled():
    c = client()
    c.limit_buy("T", 1, 50)
    assert c._post.body["time_in_force"] == "good_till_canceled"


def test_each_order_carries_a_distinct_client_id():
    """A repeated id is how a retry becomes a duplicate position."""
    c = client()
    c.limit_buy("T", 1, 50)
    first = c._post.body["client_order_id"]
    c.limit_buy("T", 1, 50)
    assert c._post.body["client_order_id"] != first


# ------------------------------------------------------------- the guardrails
@pytest.mark.parametrize("bad", [0, 100, -1, 101])
def test_prices_outside_1_to_99_are_refused(bad):
    c = client()
    with pytest.raises(ValueError):
        c.limit_buy("T", 1, bad)
    assert not c._post.calls, "a bad price still reached the wire"


def test_a_zero_or_negative_count_is_refused():
    c = client()
    for bad in (0, -5):
        with pytest.raises(ValueError):
            c.limit_buy("T", bad, 50)
    assert not c._post.calls


def test_an_unknown_side_is_refused():
    c = client()
    with pytest.raises(ValueError):
        c._order("T", "buy", 1, 50)       # the word Kalshi does NOT use
    assert not c._post.calls


def test_a_read_only_client_cannot_place_an_order():
    c = client(read_only=True)
    with pytest.raises(PermissionError):
        c.limit_buy("T", 1, 50)
    assert not c._post.calls


# ------------------------------------------- the thing the audit actually found
def test_demo_false_is_production_and_says_so_in_the_url():
    """`livedesk` builds this client with demo=False. If PROD_BASE ever stops
    being the production host, or demo starts defaulting to False, this fails
    before anyone's money does."""
    prod = KalshiClient(demo=False)
    demo = KalshiClient(demo=True)
    assert prod.base != demo.base
    assert "demo" in demo.base.lower()
    assert "demo" not in prod.base.lower()
    # the default must stay the safe one
    assert KalshiClient().demo is True


def test_the_kill_switch_does_not_cover_demo_and_that_is_recorded(tmp_path):
    """NOT a bug report — this is deliberate, and the audit flagged that it is
    easy to miss. Pinned so the intent is explicit: a demo client keeps working
    with the switch on, and a production client does not."""
    sw = tmp_path / "TRADING_DISABLED"
    sw.write_text("off", encoding="utf-8")

    d = KalshiClient(demo=True, kill_switch=str(sw))
    d._post = Recorder()
    d.limit_buy("T", 1, 50)
    assert d._post.calls, "the demo client should still place fake orders"

    p = KalshiClient(demo=False, kill_switch=str(sw))
    p._post = Recorder()
    with pytest.raises(PermissionError):
        p.limit_buy("T", 1, 50)
    assert not p._post.calls, "a production order escaped the kill switch"
