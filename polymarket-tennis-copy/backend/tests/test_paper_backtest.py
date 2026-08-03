"""Paper-trading and backtesting tests.

Two properties matter most here:
  * risk caps are enforced *before* an entry, never merely reported after;
  * a backtest decision cannot see data from after its own timestamp.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.enums import ExitStrategy, PaperTradeStatus, PositionStatus, PriceSourceQuality
from app.providers.base import ProviderBookLevel, ProviderOrderBook
from app.services.backtest import (
    BacktestCandidate,
    BacktestConfig,
    Backtester,
    PointInTimeView,
)
from app.services.metrics import PositionRecord
from app.services.paper import (
    PaperTradingEngine,
    RiskManager,
    RiskState,
    summarise_paper_trades,
)
from app.services.prices import PriceSeries

T0 = 1_785_000_000
NOW = datetime.fromtimestamp(T0, tz=timezone.utc)
ZERO = Decimal("0")


def series(points: list[tuple[int, str]]) -> PriceSeries:
    s = PriceSeries(token_id="tok")
    for offset, price in points:
        s.add_trade(T0 + offset, Decimal(price), Decimal("1000"))
    return s


def deep_book(price: str = "0.50", size: str = "100000") -> ProviderOrderBook:
    return ProviderOrderBook(
        token_id="tok", timestamp=T0,
        asks=[ProviderBookLevel(Decimal(price), Decimal(size))],
        bids=[ProviderBookLevel(Decimal("0.49"), Decimal(size))],
    )


class TestRiskManager:
    def test_default_stake_allowed_when_flat(self):
        d = RiskManager().evaluate(RiskState(), "m1")
        assert d.allowed is True
        assert d.stake == Decimal("5")

    def test_max_open_positions_blocks_entry(self):
        d = RiskManager().evaluate(RiskState(open_positions=10), "m1")
        assert d.allowed is False
        assert "max open positions" in d.reason

    def test_total_exposure_cap_blocks_entry(self):
        d = RiskManager().evaluate(RiskState(total_exposure=Decimal("50")), "m1")
        assert d.allowed is False
        assert "total exposure" in d.reason

    def test_per_market_cap_blocks_entry(self):
        state = RiskState(exposure_by_market={"m1": Decimal("20")})
        d = RiskManager().evaluate(state, "m1")
        assert d.allowed is False
        assert "per-market" in d.reason

    def test_daily_loss_cap_blocks_entry(self):
        d = RiskManager().evaluate(RiskState(realized_pnl_today=Decimal("-25")), "m1")
        assert d.allowed is False
        assert "daily loss cap" in d.reason

    def test_stake_reduced_to_remaining_allowance(self):
        state = RiskState(total_exposure=Decimal("47"))
        d = RiskManager().evaluate(state, "m1")
        assert d.allowed is True
        assert d.stake == Decimal("3")
        assert d.reduced is True

    def test_stake_capped_by_modeled_depth(self):
        """Never simulate more size than the book could absorb."""
        d = RiskManager().evaluate(
            RiskState(), "m1", requested_stake=Decimal("5"),
            modeled_fillable=Decimal("2"),
        )
        assert d.stake == Decimal("2")
        assert d.reduced is True

    def test_below_min_order_size_refused(self):
        state = RiskState(total_exposure=Decimal("49.5"))
        d = RiskManager().evaluate(state, "m1")
        assert d.allowed is False
        assert "minimum order size" in d.reason

    def test_no_martingale_stake_is_independent_of_losses(self):
        """Defaults must never scale size after losses."""
        flat = RiskManager().evaluate(RiskState(), "m1")
        after_losses = RiskManager().evaluate(
            RiskState(realized_pnl_today=Decimal("-10")), "m1"
        )
        assert flat.stake == after_losses.stake


class TestPaperEntry:
    def test_entry_uses_price_after_delay_not_signal_time(self):
        """The whole point: the follower pays the later price."""
        s = series([(0, "0.50"), (15, "0.58"), (60, "0.62")])
        entry = PaperTradingEngine().simulate_entry(
            signal_detected_at=NOW, series=s,
            wallet_entry_price=Decimal("0.50"),
            risk_state=RiskState(), market_key="m1",
            book=deep_book("0.58"), execution_delay_seconds=15,
        )
        assert entry.accepted is True
        # Filled around the 15s price, not the 0s price.
        assert entry.reference_price == Decimal("0.58")
        assert entry.fill_price >= Decimal("0.58")
        assert entry.entered_at == NOW + timedelta(seconds=15)

    def test_no_price_refuses_entry_rather_than_guessing(self):
        empty = PriceSeries(token_id="tok")
        entry = PaperTradingEngine().simulate_entry(
            signal_detected_at=NOW, series=empty, wallet_entry_price=None,
            risk_state=RiskState(), market_key="m1",
        )
        assert entry.accepted is False
        assert entry.rejection_reason == "no_price_available"
        assert "refused" in (entry.note or "")

    def test_risk_limit_refusal_is_recorded(self):
        entry = PaperTradingEngine().simulate_entry(
            signal_detected_at=NOW, series=series([(15, "0.50")]),
            wallet_entry_price=Decimal("0.50"),
            risk_state=RiskState(open_positions=99), market_key="m1",
        )
        assert entry.accepted is False
        assert entry.rejection_reason == "risk_limit"

    def test_thin_book_reduces_stake_and_flags_it(self):
        thin = ProviderOrderBook(
            token_id="tok", timestamp=T0,
            asks=[ProviderBookLevel(Decimal("0.50"), Decimal("4"))],  # $2 only
        )
        entry = PaperTradingEngine().simulate_entry(
            signal_detected_at=NOW, series=series([(15, "0.50")]),
            wallet_entry_price=Decimal("0.50"),
            risk_state=RiskState(), market_key="m1", book=thin,
        )
        assert entry.accepted is True
        assert entry.stake_reduced_for_liquidity is True
        assert entry.stake_usdc <= Decimal("2")

    def test_shares_and_stake_are_consistent(self):
        entry = PaperTradingEngine().simulate_entry(
            signal_detected_at=NOW, series=series([(15, "0.40")]),
            wallet_entry_price=Decimal("0.40"),
            risk_state=RiskState(), market_key="m1", book=deep_book("0.40"),
        )
        assert entry.shares * entry.fill_price == pytest.approx(
            entry.stake_usdc, abs=Decimal("0.0001")
        )

    def test_price_quality_is_propagated(self):
        s = PriceSeries(token_id="tok")
        s.add_bar(T0 + 15, Decimal("0.50"))
        entry = PaperTradingEngine().simulate_entry(
            signal_detected_at=NOW, series=s, wallet_entry_price=Decimal("0.50"),
            risk_state=RiskState(), market_key="m1",
        )
        assert entry.price_source_quality is PriceSourceQuality.MINUTE_BAR
        assert entry.data_confidence < 100.0


class TestPaperExit:
    def _open(self):
        return dict(
            entered_at=NOW, fill_price=Decimal("0.50"),
            shares=Decimal("100"), stake_usdc=Decimal("50"),
        )

    def test_resolution_overrides_every_strategy(self):
        for strategy in ExitStrategy:
            out = PaperTradingEngine().evaluate_exit(
                strategy=strategy, now=NOW + timedelta(hours=2),
                current_price=Decimal("0.60"), market_resolved=True, won=True,
                **self._open(),
            )
            assert out.exited is True
            assert out.exit_price == Decimal("1")
            assert out.settled_by_resolution is True
            # 100 shares * (1.00 - 0.50) = 50
            assert out.realized_pnl == Decimal("50.00")

    def test_hold_to_resolution_does_not_exit_early(self):
        out = PaperTradingEngine().evaluate_exit(
            strategy=ExitStrategy.HOLD_TO_RESOLUTION,
            now=NOW + timedelta(hours=1), current_price=Decimal("0.90"),
            **self._open(),
        )
        assert out.exited is False

    def test_follow_wallet_exit(self):
        out = PaperTradingEngine().evaluate_exit(
            strategy=ExitStrategy.FOLLOW_WALLET_EXIT,
            now=NOW + timedelta(minutes=5), current_price=Decimal("0.55"),
            wallet_has_exited=True, **self._open(),
        )
        assert out.exited is True
        assert out.realized_pnl == Decimal("5.00")
        assert out.reason == "wallet_exited"

    def test_profit_target(self):
        out = PaperTradingEngine().evaluate_exit(
            strategy=ExitStrategy.PROFIT_TARGET, now=NOW + timedelta(minutes=5),
            current_price=Decimal("0.65"), profit_target=Decimal("0.25"),
            **self._open(),
        )
        assert out.exited is True and out.reason == "profit_target"

    def test_stop_loss(self):
        out = PaperTradingEngine().evaluate_exit(
            strategy=ExitStrategy.STOP_LOSS, now=NOW + timedelta(minutes=5),
            current_price=Decimal("0.28"), stop_loss=Decimal("0.40"),
            **self._open(),
        )
        assert out.exited is True and out.reason == "stop_loss"
        assert out.realized_pnl < ZERO

    def test_fixed_hold(self):
        out = PaperTradingEngine().evaluate_exit(
            strategy=ExitStrategy.FIXED_HOLD, now=NOW + timedelta(seconds=400),
            current_price=Decimal("0.52"), max_hold_seconds=300, **self._open(),
        )
        assert out.exited is True and out.reason == "max_hold_reached"

    def test_consensus_gone(self):
        out = PaperTradingEngine().evaluate_exit(
            strategy=ExitStrategy.CONSENSUS_GONE, now=NOW + timedelta(minutes=5),
            current_price=Decimal("0.51"), consensus_still_present=False,
            **self._open(),
        )
        assert out.exited is True and out.reason == "consensus_gone"

    def test_trailing_stop(self):
        out = PaperTradingEngine().evaluate_exit(
            strategy=ExitStrategy.TRAILING_STOP, now=NOW + timedelta(minutes=5),
            current_price=Decimal("0.60"), peak_price=Decimal("0.80"),
            trailing_pct=Decimal("0.20"), **self._open(),
        )
        assert out.exited is True and out.reason == "trailing_stop"

    def test_no_current_price_means_no_exit(self):
        out = PaperTradingEngine().evaluate_exit(
            strategy=ExitStrategy.PROFIT_TARGET, now=NOW, current_price=None,
            **self._open(),
        )
        assert out.exited is False


class TestPaperSummary:
    def test_summary_separates_realized_open_and_rejected(self):
        rows = [
            {"status": PaperTradeStatus.SETTLED, "stake_usdc": "5",
             "realized_pnl": "2", "is_win": True, "roi_gap_vs_wallet": -0.05},
            {"status": PaperTradeStatus.SETTLED, "stake_usdc": "5",
             "realized_pnl": "-5", "is_win": False, "roi_gap_vs_wallet": -0.12},
            {"status": PaperTradeStatus.OPEN, "stake_usdc": "5", "unrealized_pnl": "1"},
            {"status": PaperTradeStatus.REJECTED, "rejection_reason": "risk_limit"},
        ]
        s = summarise_paper_trades(rows)
        assert s.trades == 4
        assert s.closed_trades == 2
        assert s.open_trades == 1
        assert s.rejected == 1
        assert s.realized_pnl == Decimal("-3")
        assert s.unrealized_pnl == Decimal("1")
        assert s.win_rate == 0.5
        assert s.rejection_reasons == {"risk_limit": 1}
        # Follower underperformed the wallet on both closed trades.
        assert s.avg_roi_gap_vs_wallet is not None and s.avg_roi_gap_vs_wallet < 0


def hist_position(pid: int, closed_ts: int, roi: float, copyable: float) -> PositionRecord:
    stake = Decimal("100")
    return PositionRecord(
        position_id=pid, opened_ts=closed_ts - 3600, closed_ts=closed_ts,
        status=PositionStatus.SETTLED, is_tennis=True,
        tennis_market_type="match_winner", entry_phase="prematch",
        avg_entry_price=Decimal("0.5"), capital_committed=stake,
        net_pnl=stake * Decimal(str(roi)), roi=roi, is_win=roi > 0,
        holding_seconds=3600, behaviour="directional",
        copyable={15: (copyable, stake * Decimal(str(copyable)), copyable > 0, 85.0, 95.0)},
    )


class TestPointInTimeView:
    def test_only_trades_closed_before_as_of_are_visible(self):
        """The load-bearing look-ahead guard."""
        history = {
            1: [
                hist_position(1, T0 - 10_000, 0.10, 0.08),
                hist_position(2, T0 - 5_000, 0.10, 0.08),
                # These close AFTER the decision point and must be invisible.
                hist_position(3, T0 + 5_000, 5.00, 5.00),
                hist_position(4, T0 + 9_000, 5.00, 5.00),
            ]
        }
        view = PointInTimeView(as_of=NOW, history=history, benchmark_delay=15)
        stats_now = view.wallet_stats(1)
        assert stats_now["trades"] == 2
        # The spectacular future trades must not inflate the known ROI.
        assert stats_now["copyable_roi"] == pytest.approx(0.08)

    def test_later_view_sees_more(self):
        history = {
            1: [
                hist_position(1, T0 - 1_000, 0.10, 0.08),
                hist_position(2, T0 + 1_000, 0.20, 0.15),
            ]
        }
        early = PointInTimeView(as_of=NOW, history=history, benchmark_delay=15)
        late = PointInTimeView(
            as_of=NOW + timedelta(seconds=5_000), history=history, benchmark_delay=15
        )
        assert early.wallet_stats(1)["trades"] == 1
        assert late.wallet_stats(1)["trades"] == 2

    def test_unknown_wallet_has_no_stats(self):
        view = PointInTimeView(as_of=NOW, history={}, benchmark_delay=15)
        s = view.wallet_stats(42)
        assert s["trades"] == 0
        assert s["copyable_roi"] is None
        assert s["score"] == 0.0

    def test_future_read_attempt_is_counted(self):
        view = PointInTimeView(as_of=NOW, history={}, benchmark_delay=15)
        assert view.assert_no_future_read(T0 - 100) is True
        assert view.violations == 0
        assert view.assert_no_future_read(T0 + 100) is False
        assert view.violations == 1


def candidate(
    pid: int, *, entry_offset: int, wallet_id: int = 1, entry: str = "0.50",
    won: bool = True, liquidity: str = "20000",
) -> BacktestCandidate:
    return BacktestCandidate(
        wallet_id=wallet_id, position_id=pid, token_id="tok",
        condition_id="0xc", market_id=1,
        entry_ts=T0 + entry_offset, entry_price=Decimal(entry),
        position_usdc=Decimal("1000"), holding_seconds=3600,
        market_phase="prematch", market_type="match_winner",
        liquidity=Decimal(liquidity), spread=Decimal("0.01"),
        resolved=True, won=won, wallet_exit_price=Decimal("0.70"),
        wallet_roi=0.4,
    )


class TestBacktester:
    def _history(self, n: int = 60, copyable: float = 0.10) -> dict:
        return {
            1: [
                hist_position(i, T0 - 100_000 + i * 100, 0.12, copyable)
                for i in range(n)
            ]
        }

    def _config(self, **kw) -> BacktestConfig:
        defaults = dict(
            name="test",
            period_start=NOW - timedelta(days=1),
            period_end=NOW + timedelta(days=30),
            delay_seconds=15,
            min_wallet_trades=30,
            min_wallet_score=40.0,
            min_copyability=30.0,
            stake_usdc=Decimal("10"),
        )
        defaults.update(kw)
        return BacktestConfig(**defaults)

    def test_run_produces_trades_and_no_violations(self):
        s = series([(0, "0.50"), (15, "0.51"), (3600, "0.70")])
        candidates = [candidate(i, entry_offset=i * 7200) for i in range(5)]
        result = Backtester().run(
            self._config(), candidates, lambda t: s, self._history()
        )
        assert result.lookahead_violations == 0
        assert result.is_valid is True
        assert len(result.trades) > 0
        assert result.total_return is not None

    def test_wallet_below_min_trades_is_skipped(self):
        s = series([(0, "0.50"), (15, "0.51")])
        result = Backtester().run(
            self._config(min_wallet_trades=500),
            [candidate(1, entry_offset=0)], lambda t: s, self._history(),
        )
        assert result.trades == []
        assert result.skip_reasons.get("wallet_below_min_trades") == 1

    def test_wallet_without_copyable_edge_is_skipped(self):
        """A negative copyable edge must never trade.

        ``min_wallet_score`` is relaxed to 0 so the copyable-edge gate is the one
        under test; at default settings the score gate would reject first, since a
        negative edge also drags the score proxy down.
        """
        s = series([(0, "0.50"), (15, "0.51")])
        result = Backtester().run(
            self._config(min_wallet_score=0.0),
            [candidate(1, entry_offset=0)], lambda t: s,
            self._history(copyable=-0.05),
        )
        assert result.trades == []
        assert result.skip_reasons.get("wallet_no_copyable_edge") == 1

    def test_missing_price_series_is_skipped_not_assumed(self):
        result = Backtester().run(
            self._config(), [candidate(1, entry_offset=0)],
            lambda t: None, self._history(),
        )
        assert result.trades == []
        assert result.skip_reasons.get("no_price_series") == 1

    def test_price_ran_away_is_skipped(self):
        s = series([(0, "0.50"), (15, "0.80")])
        result = Backtester().run(
            self._config(max_price_deterioration=Decimal("0.03")),
            [candidate(1, entry_offset=0)], lambda t: s, self._history(),
        )
        assert result.trades == []
        assert set(result.skip_reasons) & {"price_moved_too_far", "low_copyability"}

    def test_thin_liquidity_is_skipped(self):
        s = series([(0, "0.50"), (15, "0.51")])
        result = Backtester().run(
            self._config(min_liquidity_usdc=Decimal("100000")),
            [candidate(1, entry_offset=0)], lambda t: s, self._history(),
        )
        assert result.skip_reasons.get("insufficient_liquidity") == 1

    def test_splits_are_chronological(self):
        cfg = self._config(
            period_start=NOW, period_end=NOW + timedelta(days=100),
            train_fraction=0.5, validation_fraction=0.25,
        )
        assert cfg.split_for(NOW + timedelta(days=10)) == "train"
        assert cfg.split_for(NOW + timedelta(days=60)) == "validation"
        assert cfg.split_for(NOW + timedelta(days=90)) == "test"

    def test_delay_sensitivity_covers_all_delays(self):
        """Exposes wallets that only work at an unrealistic zero delay."""
        s = series(
            [(0, "0.50"), (2, "0.52"), (5, "0.55"), (15, "0.62"),
             (30, "0.70"), (60, "0.78"), (3600, "0.99")]
        )
        result = Backtester().run(
            self._config(max_price_deterioration=Decimal("1.0"), min_copyability=0.0),
            [candidate(i, entry_offset=i * 7200) for i in range(3)],
            lambda t: s, self._history(),
        )
        from app.config import get_settings

        assert set(result.delay_sensitivity) == set(get_settings().follower_delays_seconds)
        assert result.delay_sensitivity[0]["theoretical_only"] is True
        # Entering later on a rising market means a worse fill and lower return.
        r0 = result.delay_sensitivity[0]["return"]
        r60 = result.delay_sensitivity[60]["return"]
        if r0 is not None and r60 is not None:
            assert r0 > r60

    def test_decision_inputs_are_recorded_for_audit(self):
        s = series([(0, "0.50"), (15, "0.51"), (3600, "0.70")])
        result = Backtester().run(
            self._config(), [candidate(1, entry_offset=0)], lambda t: s, self._history()
        )
        assert result.trades
        inputs = result.trades[0].decision_inputs
        assert "as_of" in inputs
        assert "wallet_trades_known" in inputs
        assert "wallet_copyable_roi_known" in inputs

    def test_outlier_dependence_warning(self):
        s = series([(0, "0.10"), (15, "0.10"), (3600, "0.99")])
        candidates = [candidate(1, entry_offset=0, entry="0.10", won=True)] + [
            candidate(i, entry_offset=i * 7200, entry="0.10", won=False)
            for i in range(2, 6)
        ]
        result = Backtester().run(
            self._config(max_price_deterioration=Decimal("1.0"), min_copyability=0.0),
            candidates, lambda t: s, self._history(),
        )
        if result.trades and result.pct_pnl_from_top_trade:
            assert result.pct_pnl_from_top_trade > 0.5
            assert any("outlier-dependent" in w for w in result.warnings)

    def test_no_trades_warns_rather_than_reporting_zero_edge(self):
        result = Backtester().run(
            self._config(min_wallet_score=99.9),
            [candidate(1, entry_offset=0)], lambda t: series([(15, "0.5")]),
            self._history(),
        )
        assert result.trades == []
        assert result.total_return is None
        assert any("no trades" in w for w in result.warnings)

    def test_consensus_requirement_gates_single_wallet(self):
        s = series([(0, "0.50"), (15, "0.51"), (3600, "0.70")])
        result = Backtester().run(
            self._config(consensus_required=3),
            [candidate(1, entry_offset=0)], lambda t: s, self._history(),
        )
        assert result.skip_reasons.get("consensus_not_reached") == 1

    def test_config_roundtrips_to_json(self):
        import json

        cfg = self._config()
        payload = json.loads(cfg.to_json())
        assert payload["delay_seconds"] == 15
        assert payload["stake_usdc"] == "10"
