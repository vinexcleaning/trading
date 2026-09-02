"""What `show_fills.py` says he paid. Mailbox 026.

    livedesk\\test.bat

⚠ WHY A DISPLAY TOOL GETS A TEST. This is the second display-layer defect in
this folder in two days, after the "room for N more bets" line dividing by a
stake from the $83 era. **A tool that shows him numbers is not a lower tier
than one that computes them — it is the layer he actually reads**, and neither
of these crashed. Both printed a confident wrong number.

TWO SEPARATE DEFECTS LIVED ON ONE LINE:

    px = f.get("yes_price") or f.get("price") or 0

**1. Both names are dead.** Checked against a real fills response on
2026-09-02: the keys are `yes_price_dollars` and `no_price_dollars`. Both
`.get()`s returned None, so **every row printed a price of 0** — in a tool
whose only job is to show him what he paid. GUARD #23 exists because these
names moved once already.

**2. Even with the right name, the YES price is wrong on a NO fill.** They are
complements. A real pair from his account: the same market filled `yes` at 57c
and `no` at 31c. Printing the yes price on the no fill would have said 57 when
he paid 31 — **not a zero he would notice, but a plausible number that is
wrong**, which is worse.

NOTHING HERE TOUCHES THE NETWORK.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

LIVEDESK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LIVEDESK / "tools"))

import show_fills                                          # noqa: E402

#: Shape copied from a real `/portfolio/fills` row, 2026-09-02.
REAL_YES = {
    "ticker": "KXATPMATCH-26AUG30DEJPAS-PAS",
    "side": "yes", "outcome_side": "yes",
    "count_fp": "17.00", "fee_cost": "0.285500",
    "yes_price_dollars": "0.5700", "no_price_dollars": "0.4300",
    "created_time": "2026-09-01T23:44:01.000000Z",
}
REAL_NO = {
    "ticker": "KXATPMATCH-26AUG30DEJPAS-PAS",
    "side": "no", "outcome_side": "no",
    "count_fp": "17.00", "fee_cost": "0.264000",
    "yes_price_dollars": "0.6900", "no_price_dollars": "0.3100",
    "created_time": "2026-09-02T04:10:38.000000Z",
}


def test_a_yes_fill_reports_the_yes_price():
    assert show_fills._price_cents(REAL_YES) == pytest.approx(57.0)


def test_a_NO_fill_reports_the_NO_price_not_the_complement():
    """⚠ THE ONE THAT WOULD NOT HAVE BEEN NOTICED. Both numbers are plausible
    prices. He paid 31; the yes field on that same fill says 69."""
    assert show_fills._price_cents(REAL_NO) == pytest.approx(31.0)
    assert show_fills._price_cents(REAL_NO) != pytest.approx(69.0)


def test_the_dead_legacy_names_alone_do_NOT_produce_a_price():
    """⚠ THE ORIGINAL BUG. A fill carrying only the legacy names must read as
    UNKNOWN, never as zero. A zero is a number he might believe."""
    legacy_only = {"side": "yes", "yes_price": 58, "price": 58}
    assert show_fills._price_cents(legacy_only) is None


def test_an_unreadable_price_is_not_silently_zero():
    for bad in ({"side": "yes"},
                {"side": "yes", "yes_price_dollars": ""},
                {"side": "yes", "yes_price_dollars": "not a number"}):
        assert show_fills._price_cents(bad) is None


def test_a_missing_side_is_treated_as_yes_rather_than_crashing():
    """Kalshi has always sent one. If that ever changes, the tool should still
    print something rather than fall over mid-table."""
    assert show_fills._price_cents(
        {"yes_price_dollars": "0.4000"}) == pytest.approx(40.0)


def test_the_count_reads_the_LIVE_name_first():
    """`count_fp` is what the wire sends and it is a decimal STRING. The old
    line put the legacy `count` first and only worked by falling through."""
    assert show_fills._num(REAL_YES.get("count_fp"),
                           REAL_YES.get("count")) == pytest.approx(17.0)
    assert show_fills._num(None, None) == 0.0
    assert show_fills._num("", "3") == pytest.approx(3.0)


def test_fractional_contracts_survive():
    """A real fill carried `count_fp` of '16.74'. Kalshi does send fractions."""
    assert show_fills._num("16.74") == pytest.approx(16.74)


def test_this_tool_no_longer_names_any_dead_field():
    """⚠ GUARD #23, checked here so it is caught in this project's own suite
    rather than only in a repo-wide test that has been red for weeks. **A red
    guard nobody clears stops being a guard**, and this file was the only
    live-money entry on its list."""
    src = (LIVEDESK / "tools" / "show_fills.py").read_text(encoding="utf-8")
    import ast
    tree = ast.parse(src)
    dead = {"yes_price", "no_price", "yes_bid", "yes_ask", "last_price"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert node.value not in dead, (
                f"{node.value!r} is a legacy Kalshi name -- it reads None and "
                f"flows into the table as a silent zero")
