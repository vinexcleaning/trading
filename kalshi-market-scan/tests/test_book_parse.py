"""Regression tests for orderbook parsing.

The live response nests the book under `orderbook_fp` at the TOP level. An earlier
recorder unwrapped a non-existent `"orderbook"` key first, which returned {} for
every market and silently wrote empty marker rows for ~90 minutes. These tests pin
the real payload shape.
"""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rec", ROOT / "scripts" / "record_kalshi.py")
rec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rec)

# verbatim shape from GET /markets/{t}/orderbook on 2026-07-30
LIVE = {
    "orderbook_fp": {
        "no_dollars": [["0.0010", "28122.00"], ["0.0020", "2281.00"]],
        "yes_dollars": [["0.4500", "100.00"], ["0.4400", "250.50"]],
    }
}


def test_parses_the_actual_live_payload():
    rows = rec._ob_rows("KXBTC15M-x", LIVE, recv_ns=1, mono=2)
    assert len(rows) == 4, "must emit one row per (side, level)"
    assert {r["side"] for r in rows} == {"yes", "no"}


def test_prices_and_sizes_are_floats_not_strings():
    rows = rec._ob_rows("t", LIVE, 1, 2)
    for r in rows:
        assert isinstance(r["price"], float)
        assert isinstance(r["size"], float)


def test_depth_index_and_level_count_are_recorded():
    rows = rec._ob_rows("t", LIVE, 1, 2)
    yes = [r for r in rows if r["side"] == "yes"]
    assert [r["depth_i"] for r in yes] == [0, 1]
    assert all(r["n_levels"] == 2 for r in yes)


def test_values_match_the_payload():
    rows = rec._ob_rows("t", LIVE, 1, 2)
    yes0 = next(r for r in rows if r["side"] == "yes" and r["depth_i"] == 0)
    assert yes0["price"] == 0.45
    assert yes0["size"] == 100.0


def test_wrongly_unwrapped_response_yields_nothing():
    """The exact bug: .get("orderbook") on the live payload is None."""
    assert LIVE.get("orderbook") is None
    assert rec._ob_rows("t", {}, 1, 2) == []


def test_legacy_orderbook_key_still_supported():
    legacy = {"orderbook": {"yes_dollars": [["0.5000", "10.00"]]}}
    assert len(rec._ob_rows("t", legacy, 1, 2)) == 1


def test_genuinely_empty_book_is_distinguishable_from_a_parse_failure():
    """An empty book returns no rows; the caller writes a marker. Both look the
    same downstream, which is why the parse must be pinned by test."""
    assert rec._ob_rows("t", {"orderbook_fp": {"yes_dollars": [], "no_dollars": []}}, 1, 2) == []


def test_malformed_levels_are_skipped_not_fatal():
    bad = {"orderbook_fp": {"yes_dollars": [["0.50", "10"], ["oops"], None, ["x", "y"]]}}
    rows = rec._ob_rows("t", bad, 1, 2)
    assert len(rows) == 1
    assert rows[0]["price"] == 0.5


def test_three_timestamps_present_on_every_row():
    for r in rec._ob_rows("t", LIVE, recv_ns=111, mono=222):
        assert r["recv_ns"] == 111
        assert r["mono_ns"] == 222
        assert r["write_ns"] > 0
        assert r["event_ns"] is None  # REST snapshots expose no exchange event time
