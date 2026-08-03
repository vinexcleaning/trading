"""
test_engine.py - correctness checks that must pass before any result is trusted.

The one that matters most is the look-ahead test: a synthetic market whose
future is catastrophic but whose past is benign. A causal engine cannot know.
"""

import math

import numpy as np

import engine
from engine import MarketView, fee, _walk


def mk(mid, spread=2.0, settlement=100.0):
    mid = np.asarray(mid, float)
    bid = mid - spread / 2
    ask = mid + spread / 2
    return MarketView(
        ticker="T", event="E", tournament="ATP", settlement=settlement,
        ts=np.arange(len(mid), dtype=np.int64) * 60,
        mid=mid, bid_close=bid, ask_close=ask,
        bid_high=bid.copy(), bid_low=bid.copy(),   # must not alias
        spread=np.full(len(mid), spread), live=np.ones(len(mid), bool),
    )


def test_fee_matches_spec():
    # spec: peaks at 1.75c/contract at 50c, 0.63c at 90c or 10c
    assert math.isclose(fee(100, 50) / 100, 0.0175, abs_tol=1e-9)
    assert math.isclose(fee(100, 90) / 100, 0.0063, abs_tol=1e-9)
    assert math.isclose(fee(100, 10) / 100, 0.0063, abs_tol=1e-9)
    # rounds UP to the next cent: 1 contract at 50c costs 0.0175 -> 0.02
    assert fee(1, 50) == 0.02
    assert fee(10, 50) == 0.18          # 0.175 -> 0.18
    print("  fee formula ......... OK")


def test_stop_wins_ties():
    """One candle whose low hits the stop and whose high hits the target.
    The stop must win."""
    v = mk([60.0] * 5)
    i = 2
    v.bid_low[i] = 30.0        # blows through a -20c stop
    v.bid_high[i] = 90.0       # also blows through a +15c target
    t = _walk(v, 0, 60.0, 10.0, 75.0, 40.0, 1.0, None, None)
    assert t.reason == "stop", t.reason
    assert t.exit < t.entry
    print("  stop-wins-ties ...... OK")


def test_no_lookahead():
    """Two markets identical up to candle 20, then one collapses. A trade
    entered at candle 5 with no exit conditions must be identical in both
    until the paths diverge - and the engine must not 'see' the collapse
    when deciding at candle 5."""
    a = mk([60.0] * 40)
    b = mk([60.0] * 20 + [5.0] * 20)
    ta = _walk(a, 5, 60.0, 10.0, None, 40.0, 1.0, 10, None)
    tb = _walk(b, 5, 60.0, 10.0, None, 40.0, 1.0, 10, None)
    # both hit the 10-minute time stop at candle 15, before divergence matters
    assert ta.exit_ts == tb.exit_ts == 15 * 60
    assert math.isclose(ta.net, tb.net)
    print("  no look-ahead ....... OK")


def test_entry_candle_not_scanned():
    """The entry candle's own high/low happened before we bought; scanning
    them would be look-ahead."""
    v = mk([60.0] * 6)
    v.bid_low[0] = 1.0          # entry candle had a spike low
    t = _walk(v, 0, 60.0, 10.0, 75.0, 40.0, 1.0, 4, None)
    assert t.reason == "time", t.reason
    print("  entry candle skipped  OK")


def test_settlement_no_exit_fee():
    v = mk([60.0] * 5, settlement=100.0)
    t = _walk(v, 0, 60.0, 10.0, None, None, 1.0, None, None)
    assert t.reason == "settlement"
    assert math.isclose(t.fees, fee(10.0, 60.0))     # entry fee only
    assert math.isclose(t.gross, (100.0 - 60.0) / 100 * 10.0)
    print("  settlement accounting OK")


def test_scale_out_halves():
    """+15c target banks half; remainder rides to 95c."""
    v = mk([60.0] * 3 + [80.0] * 3 + [96.0] * 3)
    t = _walk(v, 0, 60.0, 10.0, 75.0, 36.0, 1.0, None, None, scale_out=True)
    assert t.reason == "target_final", t.reason
    assert t.contracts == 10.0          # records the FULL original position
    # half banked near 75, half near 95 -> comfortably profitable
    assert t.net > 0
    print("  scale-out ........... OK")


def test_structural_direction():
    v = mk([50, 50, 50, 65, 65, 65, 50, 50], spread=2.0)
    assert engine.structural(v, 3, 1, 12.0) == 1
    assert engine.structural(v, 6, 1, 12.0) == -1
    assert engine.structural(v, 4, 1, 12.0) == 0
    print("  structural events ... OK")


if __name__ == "__main__":
    print("engine validation:")
    test_fee_matches_spec()
    test_stop_wins_ties()
    test_no_lookahead()
    test_entry_candle_not_scanned()
    test_settlement_no_exit_fee()
    test_scale_out_halves()
    test_structural_direction()
    print("all passed")
