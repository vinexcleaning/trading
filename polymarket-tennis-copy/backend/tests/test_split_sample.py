"""Selection-validation tests.

These pin the property the whole module exists for: a population of pure
coin-flippers must not produce a significant result, no matter how good its best
member's record looks. A test suite that only checks the happy path would let a
sign error or a mis-indexed permutation silently bless noise as edge.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.services.split_sample import (
    TradeRecord,
    binomial_tail,
    build_splits,
    copier_edge,
    luck_bar,
    run_selection_test,
    spearman,
    split_wallet,
    winsorize,
)

DAY = 86_400
BASE_TS = 1_750_000_000


def _records(wallet: str, rois: list[float], *, start: int = BASE_TS) -> list[TradeRecord]:
    return [TradeRecord(wallet, start + i * DAY, roi) for i, roi in enumerate(rois)]


# --- splitting ---------------------------------------------------------------


def test_count_split_halves_the_record():
    split = split_wallet(_records("0xa", [1.0] * 10 + [2.0] * 10), min_half=5)
    assert split is not None
    assert split.n_in == 10 and split.n_out == 10
    assert split.in_mean == 1.0 and split.out_mean == 2.0


def test_split_orders_by_timestamp_not_input_order():
    """Trades arrive from the DB in arbitrary order; a split that trusted input
    order would leak later trades into the selection half."""
    shuffled = list(reversed(_records("0xa", [1.0] * 6 + [9.0] * 6)))
    split = split_wallet(shuffled, min_half=3)
    assert split is not None
    assert split.in_mean == 1.0 and split.out_mean == 9.0


def test_time_split_uses_calendar_midpoint():
    # Nine trades in the first week, one far later: a calendar split is lopsided
    # by design, which is what a screen run on that date would actually have had.
    rows = _records("0xa", [1.0] * 9)
    rows.append(TradeRecord("0xa", BASE_TS + 400 * DAY, 5.0))
    split = split_wallet(rows, mode="time", min_half=1)
    assert split is not None
    assert split.n_in == 9 and split.n_out == 1


def test_thin_halves_are_dropped():
    assert split_wallet(_records("0xa", [1.0] * 8), min_half=5) is None


def test_unknown_split_mode_is_rejected():
    with pytest.raises(ValueError, match="unknown split mode"):
        split_wallet(_records("0xa", [1.0] * 10), mode="sideways")


def test_build_splits_drops_thin_wallets_and_ranks_by_in_sample():
    records = _records("0xlow", [0.1] * 20) + _records("0xhigh", [0.9] * 20)
    records += _records("0xthin", [5.0] * 4)
    splits = build_splits(records, min_trades=20, min_half=5)
    assert [s.wallet for s in splits] == ["0xhigh", "0xlow"]


# --- copier edge vs the price paid -------------------------------------------


def test_favourite_trap_shows_no_edge_despite_a_huge_win_rate():
    """The trap this project exists to avoid: 95% winners at $0.95 is not skill.
    A screen ranking on raw win rate would put this wallet top."""
    implied, realised, edge = copier_edge([True] * 95 + [False] * 5, [0.95] * 100)
    assert realised == pytest.approx(0.95)
    assert implied == pytest.approx(0.95)
    assert edge == pytest.approx(0.0, abs=1e-9)


def test_longshot_with_a_low_win_rate_shows_real_edge():
    """The mirror case: 35% winners at $0.30 is printing money, and a raw
    win-rate screen would discard it."""
    _, realised, edge = copier_edge([True] * 35 + [False] * 65, [0.30] * 100)
    assert realised == pytest.approx(0.35)
    assert edge == pytest.approx(0.05)


def test_edge_uses_the_follower_fill_not_the_wallet_entry():
    """Delay moves the price against the copier; charging the wallet's own entry
    would hand the follower an edge that belongs to the wallet."""
    _, _, at_wallet_price = copier_edge([True] * 6 + [False] * 4, [0.50] * 10)
    _, _, at_follower_fill = copier_edge([True] * 6 + [False] * 4, [0.58] * 10)
    assert at_wallet_price == pytest.approx(0.10)
    assert at_follower_fill == pytest.approx(0.02)


def test_copier_edge_handles_empty_and_mismatched_input():
    assert copier_edge([], []) == (0.0, 0.0, 0.0)
    assert copier_edge([True, False], [0.5]) == (0.0, 0.0, 0.0)


# --- luck, and how sample size shrinks it ------------------------------------


def test_binomial_tail_flags_a_record_that_luck_struggles_to_explain():
    # 70 wins in 100 at a 50% implied price.
    assert binomial_tail(70, 100, 0.5) < 0.001
    # 52 in 100 is unremarkable.
    assert 0.3 < binomial_tail(52, 100, 0.5) < 0.7


def test_binomial_tail_edge_cases():
    assert binomial_tail(0, 0, 0.5) == 1.0
    assert binomial_tail(0, 10, 0.5) == pytest.approx(1.0)
    assert binomial_tail(10, 10, 0.5) == pytest.approx(0.5**10)
    # Past the exact/approximate switch the two must agree closely.
    assert binomial_tail(1200, 2000, 0.5) < 1e-6


def test_luck_bar_shrinks_as_trade_counts_rise():
    """The finding that trade count does the statistical heavy lifting: the
    luckiest of a skill-free population looks far less impressive at high n."""
    tiny = luck_bar([10] * 25, iterations=500)
    small = luck_bar([50] * 25, iterations=500)
    large = luck_bar([500] * 25, iterations=500)
    assert tiny > small > large
    # Standard error is 0.5/sqrt(n), so the bar must land in that ballpark.
    assert 0.05 < small < 0.20
    assert large < 0.06


def test_luck_bar_is_raised_by_a_single_tiny_wallet():
    """Why the earlier test was so conservative: one 1-trade wallet in the pool
    drags the whole bar up, because it can post a perfect record for free."""
    clean = luck_bar([200] * 10, iterations=500)
    polluted = luck_bar([200] * 10 + [1], iterations=500)
    assert polluted > clean + 0.15


def test_luck_bar_is_deterministic_and_ignores_empty_sizes():
    assert luck_bar([40] * 5, iterations=200) == luck_bar([40] * 5, iterations=200)
    assert luck_bar([]) == 0.0
    assert luck_bar([0, 0]) == 0.0


# --- winsorization -----------------------------------------------------------


def test_winsorize_caps_the_tail_without_deleting_it():
    """The +900% winner is capped, not removed: it still counts as a maximal
    observation, it just can no longer carry a wallet's mean by itself."""
    # Threshold lands above the bulk, as it does on the live distribution.
    rois = [-1.0] * 40 + [0.2] * 50 + [3.0] * 8 + [9.0, 8.0]
    capped = winsorize(_records("0xa", rois), pct=95.0)
    values = [r.roi for r in capped]

    assert len(values) == len(rois)
    assert max(values) < 8.0
    # The two big winners remain top-ranked, tied at the cap and clear of the bulk.
    assert values[-1] == values[-2] == max(values)
    assert max(values) > 0.2
    assert np.mean(values) < np.mean(rois)


def test_winsorize_uses_pooled_not_per_wallet_thresholds():
    """An 8-trade wallet has no percentile worth estimating from itself; the
    threshold must come from every wallet's trades together."""
    records = _records("0xbig", [0.0] * 200) + _records("0xsmall", [5.0] * 8)
    capped = winsorize(records, pct=95.0)
    small = [r.roi for r in capped if r.wallet == "0xsmall"]
    # The small wallet is under 5% of the pool, so pooled p95 sits in the big
    # wallet's mass and caps it. Per-wallet thresholds would leave it at 5.0.
    assert max(small) < 5.0


def test_winsorize_is_a_noop_at_100_pct():
    records = _records("0xa", [-1.0, 0.5, 9.0])
    assert [r.roi for r in winsorize(records, pct=100.0)] == [-1.0, 0.5, 9.0]


def test_winsorize_preserves_wallet_and_timestamp():
    records = _records("0xa", [-1.0] * 10 + [9.0])
    capped = winsorize(records, pct=90.0)
    assert [r.wallet for r in capped] == [r.wallet for r in records]
    assert [r.opened_ts for r in capped] == [r.opened_ts for r in records]


# --- rank correlation --------------------------------------------------------


def test_spearman_perfect_and_inverted():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)


def test_spearman_undefined_cases_return_none():
    assert spearman([1, 2], [1, 2]) is None          # too few points
    assert spearman([1, 1, 1, 1], [1, 2, 3, 4]) is None  # fully tied series


def test_spearman_averages_ties():
    # Ties at the top: ranks 3.5/3.5 rather than 3/4, so this stays below 1.0
    # without collapsing to zero.
    rho = spearman([1, 2, 3, 3], [1, 2, 3, 4])
    assert rho is not None and 0.8 < rho < 1.0


# --- the selection test ------------------------------------------------------


def _coinflip_population(n_wallets: int, n_trades: int, seed: int) -> list[TradeRecord]:
    """Wallets with no skill whatsoever: every trade drawn from one distribution."""
    rng = np.random.default_rng(seed)
    records: list[TradeRecord] = []
    for w in range(n_wallets):
        rois = rng.normal(0.0, 0.6, n_trades)
        records.extend(_records(f"0x{w:02x}", [float(r) for r in rois]))
    return records


def test_pure_noise_population_is_not_significant():
    """The headline guarantee. Screening 24 coin-flippers always yields a
    best-looking wallet; it must not clear the out-of-sample null."""
    splits = build_splits(_coinflip_population(24, 40, seed=7), min_trades=20, min_half=10)
    result = run_selection_test(splits, iterations=400)

    assert result is not None
    assert result.n_wallets == 24
    # The winner's in-sample record looks good in isolation: a clear margin over
    # the population it was drawn from, manufactured purely by taking the max.
    assert result.winner_in_mean - result.pooled_mean > 0.10
    # ...and is entirely unremarkable against the max-of-N null.
    assert result.p_value_in_sample > 0.05
    assert not result.survives
    assert result.selection_share == pytest.approx(1.0, abs=0.35)


def test_real_edge_survives_the_split():
    """One wallet with a genuine, persistent edge among coin-flippers must be
    detected -- otherwise the test is merely conservative, not informative."""
    records = _coinflip_population(15, 40, seed=11)
    rng = np.random.default_rng(3)
    skilled = [float(r) for r in rng.normal(0.9, 0.4, 40)]
    records.extend(_records("0xskill", skilled))

    splits = build_splits(records, min_trades=20, min_half=10)
    result = run_selection_test(splits, iterations=400)

    assert result is not None
    assert result.winner == "0xskill"
    assert result.survives
    assert result.p_value_out_sample < 0.05
    assert result.selection_share is not None and result.selection_share < 0.5


def test_permutation_is_deterministic():
    splits = build_splits(_coinflip_population(8, 30, seed=5), min_trades=20, min_half=10)
    a = run_selection_test(splits, iterations=200)
    b = run_selection_test(splits, iterations=200)
    assert a is not None and b is not None
    assert a.p_value_out_sample == b.p_value_out_sample
    assert a.null_max_in_mean == b.null_max_in_mean


def test_p_values_never_report_zero():
    """1/(B+1) is the floor: 2000 permutations cannot evidence p=0."""
    records = _coinflip_population(6, 30, seed=2)
    records.extend(_records("0xmassive", [50.0] * 30))
    splits = build_splits(records, min_trades=20, min_half=10)
    result = run_selection_test(splits, iterations=100)
    assert result is not None
    assert result.p_value_in_sample == pytest.approx(1 / 101)
    assert result.p_value_out_sample == pytest.approx(1 / 101)


def test_single_wallet_yields_no_selection_result():
    splits = build_splits(_records("0xa", [0.5] * 30), min_trades=20, min_half=10)
    assert len(splits) == 1
    assert run_selection_test(splits) is None


def test_uses_every_trade_in_the_pool():
    """Guards the reduceat offsets: a mis-computed segment boundary would drop
    or double-count trades and quietly bias every null draw."""
    splits = build_splits(_coinflip_population(5, 22, seed=1), min_trades=20, min_half=10)
    result = run_selection_test(splits, iterations=50)
    assert result is not None
    assert result.n_trades == sum(s.n_in + s.n_out for s in splits) == 5 * 22
    pooled = np.mean([roi for s in splits for roi in s.in_sample + s.out_sample])
    assert result.pooled_mean == pytest.approx(float(pooled))
