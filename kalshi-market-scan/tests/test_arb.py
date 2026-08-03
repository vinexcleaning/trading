import pytest

from kalshi_research.arb import (
    Quote,
    check_bucket_sum,
    check_combo_vs_legs,
    check_monotone_ladder,
)


def q(t, bid, ask, bs=100.0, asz=100.0, floor=None):
    return Quote(t, bid, ask, bs, asz, floor_strike=floor)


class TestBucketSum:
    def test_fair_buckets_produce_nothing(self):
        qs = [q("A", 0.32, 0.34), q("B", 0.32, 0.34), q("C", 0.32, 0.34)]
        assert check_bucket_sum("F", qs) == []

    def test_tiny_violation_is_detected_but_not_an_arb_after_fees(self):
        """sum(asks)=99c -> 1c gross. Three legs cost ~3x2.6c, so net is negative."""
        qs = [q("A", 0.30, 0.33), q("B", 0.30, 0.33), q("C", 0.30, 0.33)]
        vs = check_bucket_sum("F", qs)
        assert len(vs) == 1
        v = vs[0]
        assert v.kind == "bucket_sum_low"
        assert v.gross_edge_cents == pytest.approx(1.0, abs=0.01)
        assert v.net_edge_cents < 0
        assert not v.is_arb

    def test_large_violation_survives_fees(self):
        qs = [q("A", 0.20, 0.25), q("B", 0.20, 0.25), q("C", 0.20, 0.25)]
        vs = check_bucket_sum("F", qs)
        v = next(x for x in vs if x.kind == "bucket_sum_low")
        assert v.gross_edge_cents == pytest.approx(25.0, abs=0.01)
        assert v.net_edge_cents > 0
        assert v.is_arb

    def test_bids_summing_over_100_is_a_sell_side_violation(self):
        qs = [q("A", 0.40, 0.45), q("B", 0.40, 0.45), q("C", 0.40, 0.45)]
        vs = check_bucket_sum("F", qs)
        v = next(x for x in vs if x.kind == "bucket_sum_high")
        assert v.gross_edge_cents == pytest.approx(20.0, abs=0.01)
        assert v.is_arb

    def test_size_available_is_the_binding_minimum(self):
        qs = [q("A", 0.20, 0.25, asz=500), q("B", 0.20, 0.25, asz=7), q("C", 0.20, 0.25, asz=99)]
        v = next(x for x in check_bucket_sum("F", qs) if x.kind == "bucket_sum_low")
        assert v.size_available == 7

    def test_zero_size_quote_disqualifies_the_family(self):
        """We cannot lock a basket we cannot fill."""
        qs = [q("A", 0.20, 0.25, asz=0), q("B", 0.20, 0.25), q("C", 0.20, 0.25)]
        assert [x for x in check_bucket_sum("F", qs) if x.kind == "bucket_sum_low"] == []

    def test_missing_quote_disqualifies_the_family(self):
        qs = [q("A", 0.20, None), q("B", 0.20, 0.25), q("C", 0.20, 0.25)]
        assert [x for x in check_bucket_sum("F", qs) if x.kind == "bucket_sum_low"] == []

    def test_single_bucket_is_not_a_family(self):
        assert check_bucket_sum("F", [q("A", 0.1, 0.2)]) == []

    def test_empty_input(self):
        assert check_bucket_sum("F", []) == []


class TestMonotoneLadder:
    def test_correctly_ordered_ladder_is_clean(self):
        qs = [
            q("k70", 0.78, 0.80, floor=70),
            q("k75", 0.48, 0.50, floor=75),
            q("k80", 0.18, 0.20, floor=80),
        ]
        assert check_monotone_ladder("T", qs) == []

    def test_inversion_is_detected(self):
        """ask(k=75)=0.30 < bid(k=80)=0.60: buy low strike, sell high strike."""
        qs = [q("k75", 0.28, 0.30, floor=75), q("k80", 0.60, 0.62, floor=80)]
        vs = check_monotone_ladder("T", qs)
        assert len(vs) == 1
        assert vs[0].gross_edge_cents == pytest.approx(30.0, abs=0.01)
        assert vs[0].is_arb
        assert vs[0].tickers == ("k75", "k80")

    def test_small_inversion_dies_after_fees(self):
        qs = [q("k75", 0.49, 0.50, floor=75), q("k80", 0.505, 0.515, floor=80)]
        vs = check_monotone_ladder("T", qs)
        assert len(vs) == 1
        assert vs[0].gross_edge_cents == pytest.approx(0.5, abs=0.01)
        assert not vs[0].is_arb

    def test_only_adjacent_strikes_compared(self):
        qs = [
            q("k70", 0.10, 0.12, floor=70),
            q("k75", 0.50, 0.52, floor=75),
            q("k80", 0.90, 0.92, floor=80),
        ]
        vs = check_monotone_ladder("T", qs)
        assert len(vs) == 2
        assert {v.tickers for v in vs} == {("k70", "k75"), ("k75", "k80")}

    def test_unsorted_input_is_sorted_by_strike(self):
        qs = [q("k80", 0.60, 0.62, floor=80), q("k75", 0.28, 0.30, floor=75)]
        vs = check_monotone_ladder("T", qs)
        assert vs[0].tickers == ("k75", "k80")

    def test_markets_without_strikes_are_ignored(self):
        assert check_monotone_ladder("T", [q("a", 0.1, 0.2), q("b", 0.8, 0.9)]) == []

    def test_duplicate_strikes_skipped(self):
        qs = [q("a", 0.1, 0.2, floor=75), q("b", 0.8, 0.9, floor=75)]
        assert check_monotone_ladder("T", qs) == []


class TestComboVsLegs:
    def test_combo_priced_below_upper_bound_is_clean(self):
        legs = [q("L1", 0.49, 0.51), q("L2", 0.49, 0.51)]
        combo = q("C", 0.24, 0.26)
        assert check_combo_vs_legs("F", combo, legs) == []

    def test_combo_above_comonotone_bound_is_flagged(self):
        """A parlay can never beat its weakest leg, whatever the correlation."""
        legs = [q("L1", 0.49, 0.51), q("L2", 0.29, 0.31)]
        combo = q("C", 0.60, 0.62)
        vs = check_combo_vs_legs("F", combo, legs)
        assert len(vs) == 1
        assert vs[0].gross_edge_cents == pytest.approx(30.0, abs=0.5)
        assert vs[0].is_arb

    def test_equal_to_bound_is_not_flagged(self):
        legs = [q("L1", 0.49, 0.51), q("L2", 0.29, 0.31)]
        combo = q("C", 0.30, 0.32)
        assert check_combo_vs_legs("F", combo, legs) == []

    def test_no_combo_bid_means_nothing_to_sell(self):
        legs = [q("L1", 0.49, 0.51)]
        assert check_combo_vs_legs("F", q("C", None, 0.9), legs) == []

    def test_zero_combo_size(self):
        legs = [q("L1", 0.20, 0.22)]
        assert check_combo_vs_legs("F", q("C", 0.9, 0.92, bs=0), legs) == []

    def test_no_legs(self):
        assert check_combo_vs_legs("F", q("C", 0.9, 0.92), []) == []


def test_violation_requires_both_positive_net_and_size():
    from kalshi_research.arb import Violation

    assert Violation("monotone_ladder", "f", ("a",), 10, 1, 9, 5).is_arb
    assert not Violation("monotone_ladder", "f", ("a",), 10, 1, 9, 0).is_arb
    assert not Violation("monotone_ladder", "f", ("a",), 10, 20, -10, 5).is_arb


def test_fee_charged_scales_with_number_of_legs():
    """A 5-bucket family must be charged more fee than a 2-bucket one."""
    two = check_bucket_sum("F", [q("A", 0.1, 0.2), q("B", 0.1, 0.2)])
    five = check_bucket_sum("F", [q(str(i), 0.05, 0.08) for i in range(5)])
    v2 = next(x for x in two if x.kind == "bucket_sum_low")
    v5 = next(x for x in five if x.kind == "bucket_sum_low")
    assert v5.fee_cents > v2.fee_cents


def qs_(t, bid, ask, stype, floor=None, cap=None, bs=100.0, asz=100.0):
    return Quote(t, bid, ask, bs, asz, floor_strike=floor, cap_strike=cap, strike_type=stype)


class TestClassifyFamily:
    def test_pure_greater_or_equal_ladder_is_a_ladder(self):
        """The KXDJI shape: 60 nested thresholds. Must never be summed."""
        from kalshi_research.arb import classify_family

        qs = [qs_(f"k{i}", 0.5, 0.6, "greater_or_equal", floor=i) for i in range(60)]
        assert classify_family(qs) == "ladder"

    def test_between_plus_tails_is_a_bucket_family(self):
        """The KXBTC shape: less + between... + greater tiles the line."""
        from kalshi_research.arb import classify_family

        qs = [
            qs_("lo", 0.0, 0.01, "less", cap=54250),
            qs_("b1", 0.0, 0.01, "between", floor=54250, cap=54499.99),
            qs_("hi", 0.0, 0.01, "greater", floor=54500),
        ]
        assert classify_family(qs) == "bucket"

    def test_no_strike_types_is_unknown(self):
        from kalshi_research.arb import classify_family

        assert classify_family([q("a", 0.1, 0.2)]) == "unknown"


class TestVerifyBucketCoverage:
    def _tiling(self):
        return [
            qs_("lo", 0.0, 0.01, "less", cap=100.0),
            qs_("b1", 0.0, 0.01, "between", floor=100.0, cap=199.99),
            qs_("b2", 0.0, 0.01, "between", floor=200.0, cap=299.99),
            qs_("hi", 0.0, 0.01, "greater", floor=300.0),
        ]

    def test_clean_tiling_verifies(self):
        from kalshi_research.arb import verify_bucket_coverage

        ok, why = verify_bucket_coverage(self._tiling())
        assert ok, why

    def test_gap_between_buckets_fails(self):
        from kalshi_research.arb import verify_bucket_coverage

        qs = self._tiling()
        qs[2] = qs_("b2", 0.0, 0.01, "between", floor=250.0, cap=299.99)
        ok, why = verify_bucket_coverage(qs)
        assert not ok and "gap" in why

    def test_missing_tail_fails(self):
        from kalshi_research.arb import verify_bucket_coverage

        ok, why = verify_bucket_coverage(self._tiling()[:-1])
        assert not ok and "tail" in why

    def test_ladder_family_never_verifies_as_buckets(self):
        """Regression guard for the 1,300c phantom arb."""
        from kalshi_research.arb import verify_bucket_coverage

        qs = [qs_(f"k{i}", 0.26, 0.95, "greater_or_equal", floor=51425 + 5 * i) for i in range(60)]
        ok, _ = verify_bucket_coverage(qs)
        assert not ok

    def test_bucket_sum_with_coverage_required_rejects_a_ladder(self):
        """The end-to-end guard: a nested ladder must yield zero violations."""
        qs = [qs_(f"k{i}", 0.26, 0.95, "greater_or_equal", floor=51425 + 5 * i) for i in range(60)]
        assert check_bucket_sum("KXDJI-x", qs, require_coverage=True) == []
        # and without the guard it produces the absurd result we are protecting against
        bad = check_bucket_sum("KXDJI-x", qs, require_coverage=False)
        assert any(v.gross_edge_cents > 500 for v in bad)
