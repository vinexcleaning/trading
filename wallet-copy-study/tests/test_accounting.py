"""Tests for fee arithmetic and P&L decomposition.

Two kinds of test here:

  1. Closed-form checks with hand-computed answers -- these catch algebra and
     sign errors, which have already bitten once in this project (an inverted
     maker side produced a 0.96 median relative fee error).

  2. A check against REAL DATA: a random sample of (wallet, market, token)
     groups is recomputed from raw fills through `accounting.reconstruct` and
     asserted equal to the row the pipeline actually emitted. This is what makes
     these tests a check on the pipeline rather than on a parallel copy of it
     that could drift silently.

Run:  python -m pytest tests/ -q
"""
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from accounting import (  # noqa: E402
    POLY_FEE_RATE, decode_fill, poly_fee, poly_fee_per_share,
    poly_fee_raw_onchain, reconstruct,
)

DATA = ROOT / "data"
TOL = 1e-9


# ------------------------------------------------------------------ fees
@pytest.mark.parametrize("price,expected_cents", [
    (0.10, 1.00), (0.25, 2.50), (0.50, 5.00), (0.75, 2.50), (0.90, 1.00),
    (0.01, 0.10), (0.99, 0.10),
])
def test_fee_reference_points(price, expected_cents):
    """The economic bar quoted throughout the study, in cents per share."""
    assert poly_fee_per_share(price) * 100 == pytest.approx(expected_cents, abs=1e-9)


def test_fee_is_symmetric_about_50c():
    for p in (0.01, 0.1, 0.2, 0.35, 0.49):
        assert poly_fee_per_share(p) == pytest.approx(poly_fee_per_share(1 - p))


def test_fee_peaks_at_50c():
    grid = [i / 1000 for i in range(1, 1000)]
    assert max(grid, key=poly_fee_per_share) == pytest.approx(0.5, abs=1e-3)


def test_fee_scales_linearly_in_shares():
    assert poly_fee(0.5, 200) == pytest.approx(2 * poly_fee(0.5, 100))


def test_published_formula_is_not_the_observed_one():
    """0.07*p*(1-p) matched 0.0% of 5,362 on-chain fills; guard the distinction."""
    p = 0.5
    published = 0.07 * p * (1 - p)
    observed = poly_fee_per_share(p)
    assert observed == pytest.approx(0.05)
    assert published == pytest.approx(0.0175)
    assert not math.isclose(published, observed, rel_tol=0.01)


def test_fee_rejects_degenerate_prices():
    for bad in (0.0, 1.0, -0.1, 1.5):
        with pytest.raises(ValueError):
            poly_fee_per_share(bad)


def test_raw_onchain_fee_both_sides_reduce_to_same_economic_cost():
    """BUY fee is in tokens (worth p each); SELL fee is in USDC. Same cost."""
    for p in (0.011, 0.25, 0.5, 0.8, 0.97):
        shares = 1234.5
        buy_tokens = poly_fee_raw_onchain(p, shares, "BUY")
        sell_usdc = poly_fee_raw_onchain(p, shares, "SELL")
        assert buy_tokens * p == pytest.approx(sell_usdc, rel=1e-12)
        assert sell_usdc == pytest.approx(poly_fee(p, shares), rel=1e-12)


def test_raw_onchain_fee_matches_worked_example():
    """The probe_00 fill: maker paid 66066 USDC for 6006000 tokens, fee 600600.

    p = 0.011, so min(p,1-p) = p and the BUY fee collapses to rate*shares.
    """
    shares_raw, usdc_raw, fee_raw = 6_006_000, 66_066, 600_600
    p = usdc_raw / shares_raw
    assert p == pytest.approx(0.011, abs=1e-9)
    pred = poly_fee_raw_onchain(p, shares_raw, "BUY")
    assert pred == pytest.approx(fee_raw, rel=1e-9)


def test_inverting_the_side_is_detectably_wrong():
    """Guards the specific bug that produced median relative error 0.96."""
    p, shares = 0.5, 1000.0
    right = poly_fee_raw_onchain(p, shares, "BUY")
    wrong = poly_fee_raw_onchain(p, shares, "SELL")
    assert abs(right - wrong) / wrong == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------- decode
def test_decode_buy_and_sell():
    buy = decode_fill("0", "12345", 500_000, 1_000_000)
    assert buy[0] == "BUY" and buy[1] == "12345"
    assert buy[2] == pytest.approx(1.0) and buy[4] == pytest.approx(0.5)

    sell = decode_fill("12345", "0", 1_000_000, 500_000)
    assert sell[0] == "SELL" and sell[1] == "12345"
    assert sell[2] == pytest.approx(1.0) and sell[4] == pytest.approx(0.5)


def test_decode_rejects_token_for_token_and_degenerate():
    assert decode_fill("111", "222", 10, 10) is None      # no collateral leg
    assert decode_fill("0", "111", 0, 10) is None         # zero usdc
    assert decode_fill("0", "111", 10, 0) is None         # zero shares
    assert decode_fill("0", "111", 20, 10) is None        # price >= 1


# ----------------------------------------------------- P&L decomposition
def test_buy_and_hold_winner():
    r = reconstruct([(1, "BUY", 100.0, 0.40, 0.0)], is_winner=True)
    assert r["entry_px"] == pytest.approx(0.40)
    assert r["realised_per_share"] == pytest.approx(1.0)
    assert r["edge"] == pytest.approx(0.60)
    assert r["pnl"] == pytest.approx(60.0)
    assert r["held_to_settlement"] is True
    assert r["flags"] == []


def test_buy_and_hold_loser():
    r = reconstruct([(1, "BUY", 100.0, 0.40, 0.0)], is_winner=False)
    assert r["realised_per_share"] == pytest.approx(0.0)
    assert r["edge"] == pytest.approx(-0.40)
    assert r["pnl"] == pytest.approx(-40.0)


def test_favourite_that_wins_has_small_edge_not_large():
    """The whole point of the metric: 0.90 -> win is +10pp, not a 90% win rate."""
    r = reconstruct([(1, "BUY", 100.0, 0.90, 0.0)], is_winner=True)
    assert r["edge"] == pytest.approx(0.10)


def test_full_exit_before_settlement_scored_at_exit_price():
    """Market resolution must NOT drive P&L for a position already closed."""
    evs = [(1, "BUY", 100.0, 0.40, 0.0), (2, "SELL", 100.0, 0.55, 0.0)]
    win = reconstruct(evs, is_winner=True)
    lose = reconstruct(evs, is_winner=False)
    assert win["edge"] == pytest.approx(0.15)
    assert lose["edge"] == pytest.approx(0.15)      # identical: it was closed
    assert win["pnl"] == pytest.approx(15.0)
    assert win["held_to_settlement"] is False


def test_partial_exit_mixes_exit_and_settlement():
    evs = [(1, "BUY", 100.0, 0.40, 0.0), (2, "SELL", 40.0, 0.60, 0.0)]
    r = reconstruct(evs, is_winner=True)
    # 40 shares at 0.60 = 24 proceeds; 60 shares settle at 1.0 = 60
    assert r["realised_per_share"] == pytest.approx((24.0 + 60.0) / 100.0)
    assert r["edge"] == pytest.approx(0.84 - 0.40)
    assert r["final_balance"] == pytest.approx(60.0)


def test_adds_use_capital_weighted_entry_price():
    evs = [(1, "BUY", 100.0, 0.40, 0.0), (2, "BUY", 300.0, 0.60, 0.0)]
    r = reconstruct(evs, is_winner=True)
    assert r["entry_px"] == pytest.approx((40.0 + 180.0) / 400.0)   # 0.55
    assert r["edge"] == pytest.approx(0.45)


def test_fees_reduce_edge_net_but_not_edge():
    evs = [(1, "BUY", 100.0, 0.50, 5.0)]     # 5.00c/share at 50c on 100 shares
    r = reconstruct(evs, is_winner=True)
    assert r["edge"] == pytest.approx(0.50)
    assert r["edge_net"] == pytest.approx(0.45)
    assert r["pnl"] == pytest.approx(45.0)


def test_negative_balance_is_flagged_not_repaired():
    """Sell-then-buy: tokens came from a split we cannot see."""
    evs = [(1, "SELL", 50.0, 0.60, 0.0), (2, "BUY", 50.0, 0.40, 0.0)]
    r = reconstruct(evs, is_winner=True)
    assert "negative_balance_split_or_external" in r["flags"]
    assert r["min_balance"] < 0


def test_sell_only_has_no_entry_price():
    r = reconstruct([(1, "SELL", 50.0, 0.60, 0.0)], is_winner=True)
    assert "no_buys_sell_only" in r["flags"]
    assert r["entry_px"] is None
    assert r["edge"] is None


def test_unsettled_market_yields_no_edge():
    r = reconstruct([(1, "BUY", 100.0, 0.40, 0.0)], is_winner=None)
    assert r["edge"] is None and r["pnl"] is None
    assert r["entry_px"] == pytest.approx(0.40)


def test_pnl_identity_holds():
    """pnl must equal edge_net * shares_in, exactly, by construction."""
    evs = [(1, "BUY", 250.0, 0.31, 3.1), (2, "BUY", 100.0, 0.44, 1.2),
           (3, "SELL", 120.0, 0.52, 1.9)]
    r = reconstruct(evs, is_winner=True)
    assert r["pnl"] == pytest.approx(r["edge_net"] * r["shares_in"], rel=1e-9)


def test_edge_equals_realised_minus_entry_identity():
    evs = [(1, "BUY", 77.0, 0.23, 0.5), (2, "SELL", 30.0, 0.41, 0.2)]
    r = reconstruct(evs, is_winner=False)
    assert r["edge"] == pytest.approx(
        r["realised_per_share"] - r["entry_px"], rel=1e-12)


# ------------------------------------------------- real-data agreement
def _load_sample_groups(n_groups=300, seed=20260801):
    """Recompute n random (wallet, market, token) groups from raw fills."""
    fills_p = DATA / "wallet_fills.jsonl"
    pos_p = DATA / "wallet_positions.jsonl"
    uni_p = DATA / "markets_clob.jsonl"
    if not (fills_p.exists() and pos_p.exists() and uni_p.exists()):
        pytest.skip("pipeline outputs not present yet")

    rng = random.Random(seed)
    emitted = {}
    with pos_p.open(encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            r = json.loads(line)
            if len(emitted) < n_groups:
                emitted[(r["wallet"], r["token"])] = r
            elif rng.random() < 0.001:
                emitted.pop(next(iter(emitted)))
                emitted[(r["wallet"], r["token"])] = r
            if i > 400_000:
                break
    if not emitted:
        pytest.skip("no positions emitted")

    wanted_w = {k[0] for k in emitted}
    groups = defaultdict(list)
    with fills_p.open(encoding="utf-8") as fh:
        for line in fh:
            f = json.loads(line)
            if f["wallet"] not in wanted_w:
                continue
            k = (f["wallet"], f["token"])
            if k in emitted:
                groups[k].append(
                    (f["ts"], f["side"], f["shares"], f["price"], f["fee_usd"]))
    return emitted, groups


def test_pipeline_matches_reference_implementation():
    """Recompute real positions from raw fills; assert the pipeline agrees."""
    emitted, groups = _load_sample_groups()
    checked = 0
    for k, evs in groups.items():
        row = emitted[k]
        evs.sort()
        ref = reconstruct(evs, row["is_winner"])
        assert ref["n_trades"] == row["n_trades"], k
        assert ref["shares_in"] == pytest.approx(row["shares_in"], abs=1e-4), k
        assert ref["cost"] == pytest.approx(row["cost"], abs=1e-4), k
        assert ref["proceeds"] == pytest.approx(row["proceeds"], abs=1e-4), k
        assert ref["final_balance"] == pytest.approx(
            row["final_balance"], abs=1e-4), k
        if row["edge"] is not None and ref["edge"] is not None:
            assert ref["edge"] == pytest.approx(row["edge"], abs=1e-5), k
            assert ref["edge_net"] == pytest.approx(row["edge_net"], abs=1e-5), k
        checked += 1
    assert checked >= 20, f"only {checked} groups cross-checked"


def test_no_position_claims_edge_without_settlement():
    """Guards the failure the brief names: resolution used as if it were P&L."""
    pos_p = DATA / "wallet_positions.jsonl"
    if not pos_p.exists():
        pytest.skip("positions not built yet")
    bad = 0
    with pos_p.open(encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            r = json.loads(line)
            if r["settle_state"] != "settled" and r["edge"] is not None:
                bad += 1
            if i > 500_000:
                break
    assert bad == 0, f"{bad} positions carry an edge without settlement"


def test_flagged_positions_are_excluded_from_edge_stats():
    """Split-derived positions must not silently carry a fabricated entry."""
    pos_p = DATA / "wallet_positions.jsonl"
    if not pos_p.exists():
        pytest.skip("positions not built yet")
    bad = 0
    with pos_p.open(encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            r = json.loads(line)
            if "no_buys_sell_only" in r["flags"] and r["entry_px"] is not None:
                bad += 1
            if i > 500_000:
                break
    assert bad == 0, f"{bad} sell-only positions carry an entry price"
