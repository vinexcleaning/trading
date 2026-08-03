"""API endpoint tests.

These run against an in-memory schema with no network access. They check that
endpoints respond, that write paths persist, and -- most importantly -- that the
honesty guarantees the product depends on are actually enforced at the API
boundary: credentials are never returned, non-editable settings are refused, and
rejected signals stay visible.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.enums import (
    PaperTradeStatus,
    PriceSourceQuality,
    SignalStatus,
    SignalType,
    TennisMarketType,
)


ADDRESS = "0x" + "ab" * 20


# --------------------------------------------------------------- basic surface


@pytest.mark.parametrize(
    "path",
    [
        "/healthz",
        "/",
        "/api/health",
        "/api/overview",
        "/api/data-quality",
        "/api/settings",
        "/api/wallets",
        "/api/wallets/rankings",
        "/api/markets",
        "/api/markets/review-queue",
        "/api/signals",
        "/api/signals/alerts",
        "/api/paper/trades",
        "/api/paper/summary",
        "/api/paper/risk",
        "/api/paper/daily",
        "/api/backtests",
        "/api/errors",
        "/api/jobs",
        "/api/jobs/status",
        "/api/reports/daily",
        "/api/reports/weekly",
        "/api/alerts/count",
        "/api/db-info",
    ],
)
def test_get_endpoints_respond(client, path):
    response = client.get(path)
    assert response.status_code == 200, f"{path} -> {response.status_code} {response.text[:300]}"


def test_openapi_documents_every_route(client):
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "Tennis Copy-Trade Intelligence"
    # Spot-check that each functional area is documented.
    for path in (
        "/api/wallets",
        "/api/markets",
        "/api/signals",
        "/api/paper/trades",
        "/api/backtests",
        "/api/overview",
    ):
        assert path in spec["paths"], f"{path} missing from OpenAPI"


def test_root_and_overview_carry_the_disclaimer(client):
    for path in ("/", "/api/overview"):
        body = client.get(path).json()
        assert "not financial advice" in body["disclaimer"]


def test_request_id_is_echoed(client):
    response = client.get("/healthz", headers={"x-request-id": "trace-me"})
    assert response.headers["x-request-id"] == "trace-me"


# ------------------------------------------------------------------- wallets


def test_wallet_crud_roundtrip(client):
    created = client.post(
        "/api/wallets",
        json={"address": ADDRESS.upper(), "nickname": "test wallet", "tags": ["manual"]},
    )
    assert created.status_code == 201
    body = created.json()
    # Addresses are normalised so the same wallet cannot be registered twice.
    assert body["address"] == ADDRESS
    wallet_id = body["id"]

    assert client.get(f"/api/wallets/{wallet_id}").status_code == 200
    assert client.get(f"/api/wallets/{wallet_id}/activity").json() == []
    assert client.get(f"/api/wallets/{wallet_id}/positions").json() == []

    patched = client.patch(f"/api/wallets/{wallet_id}", json={"nickname": "renamed"})
    assert patched.json()["nickname"] == "renamed"

    assert client.delete(f"/api/wallets/{wallet_id}").status_code == 200
    assert client.get(f"/api/wallets/{wallet_id}").status_code == 404


def test_duplicate_wallet_is_not_created_twice(client):
    first = client.post("/api/wallets", json={"address": ADDRESS})
    second = client.post("/api/wallets", json={"address": ADDRESS})
    assert first.json()["id"] == second.json()["id"]
    assert len(client.get("/api/wallets").json()) == 1


def test_wallet_csv_import(client):
    csv_body = f"address,nickname\n{ADDRESS},imported\nnot-an-address,bad\n"
    response = client.post(
        "/api/wallets/import",
        files={"file": ("wallets.csv", csv_body, "text/csv")},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["added"] == 1
    # The malformed row is reported rather than silently dropped.
    assert result["errors"]


def test_metrics_404_before_any_sync(client):
    wallet_id = client.post("/api/wallets", json={"address": ADDRESS}).json()["id"]
    response = client.get(f"/api/wallets/{wallet_id}/metrics")
    assert response.status_code == 404
    assert "sync" in response.json()["detail"]


# ------------------------------------------------------------------ settings


def test_settings_never_expose_credentials(client, monkeypatch):
    from app.config import get_settings, reset_settings_cache

    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1/supersecret")
    reset_settings_cache()
    get_settings()

    payload = client.get("/api/settings").text
    assert "supersecret" not in payload
    # The channel is reported as configured without revealing the URL.
    assert "discord" in client.get("/api/settings").json()["notification_channels_configured"]

    reset_settings_cache()


def test_settings_reject_non_editable_keys(client):
    response = client.patch(
        "/api/settings", json={"key": "discord_webhook_url", "value": "https://x"}
    )
    assert response.status_code == 422
    assert "not runtime-editable" in response.json()["detail"]


def test_settings_reject_invalid_values(client):
    response = client.patch(
        "/api/settings", json={"key": "alert_min_skill_score", "value": "not-a-number"}
    )
    assert response.status_code == 422


def test_settings_accept_and_clear_a_valid_override(client):
    assert client.patch(
        "/api/settings", json={"key": "alert_min_skill_score", "value": "80"}
    ).status_code == 200
    assert client.get("/api/settings").json()["alert_thresholds"]["min_skill_score"] == "80"
    assert client.delete("/api/settings/alert_min_skill_score").status_code == 200


# ------------------------------------------------------------------- signals


def _make_market(db_session, *, resolved: bool = False):
    from app.models import Market, Outcome

    market = Market(
        condition_id="0xcond",
        question="Alcaraz vs Sinner",
        is_tennis=True,
        tennis_market_type=TennisMarketType.MATCH_WINNER,
        classification_confidence=100.0,
        resolved=resolved,
        closed=resolved,
        game_start_time=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db_session.add(market)
    db_session.flush()
    outcome = Outcome(
        market_id=market.id, token_id="tok-1", outcome_index=0, label="Alcaraz"
    )
    db_session.add(outcome)
    db_session.flush()
    return market, outcome


def _make_signal(db_session, *, qualified: bool, status: str, dedupe: str = "k1"):
    from app.models import Signal

    market, outcome = _make_market(db_session)
    now = datetime.now(timezone.utc)
    signal = Signal(
        signal_type=SignalType.SINGLE_WALLET,
        status=status,
        market_id=market.id,
        token_id=outcome.token_id,
        condition_id=market.condition_id,
        outcome_label=outcome.label,
        dedupe_key=dedupe,
        first_wallet_trade_at=now,
        last_wallet_trade_at=now,
        detected_at=now,
        qualified=qualified,
        rejection_reasons=None if qualified else '["price_moved_too_far"]',
        explanation="test signal",
        wallet_entry_price_median=Decimal("0.60"),
        current_price=Decimal("0.62"),
    )
    db_session.add(signal)
    db_session.commit()
    return signal


def test_rejected_signals_remain_visible(client, db_session):
    """The rejection log is a product surface, not debris."""
    _make_signal(db_session, qualified=False, status=SignalStatus.REJECTED)

    all_signals = client.get("/api/signals").json()
    assert len(all_signals) == 1
    assert all_signals[0]["rejection_reasons"] == ["price_moved_too_far"]

    assert client.get("/api/signals?qualified=false").json()
    assert client.get("/api/signals?qualified=true").json() == []


def test_market_detail_renders_with_signals_and_paper_trades(client, db_session):
    """Exercises the market detail composition end to end.

    This endpoint stitches together market, price, signal and paper-trade
    serialisers; a mismatch between those helpers only shows up here.
    """
    from app.models import PaperTrade

    signal = _make_signal(db_session, qualified=True, status=SignalStatus.QUALIFIED)
    db_session.add(
        PaperTrade(
            signal_id=signal.id,
            market_id=signal.market_id,
            token_id=signal.token_id,
            outcome_label=signal.outcome_label,
            status=PaperTradeStatus.OPEN,
            signal_detected_at=signal.detected_at,
            execution_delay_seconds=15,
            stake_usdc=Decimal("5"),
            fill_price=Decimal("0.62"),
            shares=Decimal("8.06"),
        )
    )
    db_session.commit()

    response = client.get(f"/api/markets/{signal.market_id}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["market"]["question"] == "Alcaraz vs Sinner"
    assert len(body["signals"]) == 1
    assert len(body["paper_trades"]) == 1
    assert body["signals"][0]["outcome_label"] == "Alcaraz"


def test_market_detail_404(client):
    assert client.get("/api/markets/999999").status_code == 404


def test_signal_detail_and_404(client, db_session):
    signal = _make_signal(db_session, qualified=True, status=SignalStatus.QUALIFIED)
    body = client.get(f"/api/signals/{signal.id}").json()
    assert body["outcome_label"] == "Alcaraz"
    assert body["market_question"] == "Alcaraz vs Sinner"
    assert client.get("/api/signals/999999").status_code == 404


def test_signal_expiry_moves_stale_signals(client, db_session):
    signal = _make_signal(db_session, qualified=True, status=SignalStatus.QUALIFIED)
    signal.expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()

    assert client.post("/api/signals/expire").json()["message"].startswith("expired 1")
    db_session.refresh(signal)
    assert signal.status == SignalStatus.EXPIRED


# -------------------------------------------------------------- paper trading


def test_paper_summary_is_labelled_as_simulation(client):
    body = client.get("/api/paper/summary").json()
    assert "Simulated" in body["disclaimer"]
    assert body["trades"] == 0


def test_paper_risk_reports_configured_limits(client):
    body = client.get("/api/paper/risk").json()
    assert body["max_open_positions"] == 10
    assert body["stake_per_signal"] == "5"
    assert Decimal(body["max_total_exposure"]) == Decimal("50")


def test_paper_trade_detail_includes_event_log(client, db_session):
    from app.models import PaperTrade, PaperTradeEvent

    market, outcome = _make_market(db_session)
    now = datetime.now(timezone.utc)
    trade = PaperTrade(
        market_id=market.id,
        token_id=outcome.token_id,
        outcome_label=outcome.label,
        status=PaperTradeStatus.OPEN,
        signal_detected_at=now,
        execution_delay_seconds=15,
        entered_at=now,
        fill_price=Decimal("0.61"),
        shares=Decimal("8.19"),
        stake_usdc=Decimal("5"),
        price_source_quality=PriceSourceQuality.OBSERVED_TRADE,
    )
    db_session.add(trade)
    db_session.flush()
    db_session.add(
        PaperTradeEvent(
            paper_trade_id=trade.id, event_type="filled", occurred_at=now,
            price=Decimal("0.61"),
        )
    )
    db_session.commit()

    body = client.get(f"/api/paper/trades/{trade.id}").json()
    assert body["trade"]["status"] == PaperTradeStatus.OPEN
    assert body["events"][0]["event_type"] == "filled"
    assert "Simulated" in body["disclaimer"]

    summary = client.get("/api/paper/summary").json()
    assert summary["open_trades"] == 1


# --------------------------------------------------------------- backtesting


def test_backtest_rejects_reversed_period(client):
    now = datetime.now(timezone.utc)
    response = client.post(
        "/api/backtests",
        json={
            "name": "bad period",
            "period_start": now.isoformat(),
            "period_end": (now - timedelta(days=1)).isoformat(),
        },
    )
    assert response.status_code == 422


def test_backtest_runs_synchronously_with_no_candidates(client):
    now = datetime.now(timezone.utc)
    response = client.post(
        "/api/backtests?run_async=false",
        json={
            "name": "empty run",
            "period_start": (now - timedelta(days=30)).isoformat(),
            "period_end": now.isoformat(),
            "delay_seconds": 15,
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["total_trades"] == 0
    assert body["lookahead_violations"] == 0
    # An empty run says so rather than reporting a flattering zero.
    assert any("no candidates" in w for w in body["warnings"])

    assert client.get(f"/api/backtests/{body['id']}").status_code == 200
    assert client.get(f"/api/backtests/{body['id']}/trades").json() == []
    assert client.delete(f"/api/backtests/{body['id']}").status_code == 200


def test_backtest_zero_delay_is_flagged_as_unachievable(client):
    now = datetime.now(timezone.utc)
    body = client.post(
        "/api/backtests?run_async=false",
        json={
            "name": "zero delay",
            "period_start": (now - timedelta(days=5)).isoformat(),
            "period_end": now.isoformat(),
            "delay_seconds": 0,
        },
    ).json()
    assert any("theoretical reference only" in w for w in body["warnings"])


def test_backtest_rejects_unknown_exit_strategy(client):
    now = datetime.now(timezone.utc)
    response = client.post(
        "/api/backtests?run_async=false",
        json={
            "name": "bad strategy",
            "period_start": (now - timedelta(days=5)).isoformat(),
            "period_end": now.isoformat(),
            "exit_strategy": "sell_when_vibes_are_off",
        },
    )
    assert response.status_code == 422
    assert "unknown exit_strategy" in response.json()["detail"]


# ------------------------------------------------------------------ reports


def test_report_export_formats(client):
    json_response = client.get("/api/reports/daily/export?fmt=json")
    assert json_response.status_code == 200
    assert "attachment" in json_response.headers["content-disposition"]

    csv_response = client.get("/api/reports/daily/export?fmt=csv")
    assert csv_response.status_code == 200
    assert csv_response.text.startswith("metric,value")


def test_report_rejects_unknown_period(client):
    assert client.get("/api/reports/monthly").status_code == 422


def test_unknown_job_is_404(client):
    assert client.post("/api/jobs/not-a-job/run").status_code == 404


# ------------------------------------------------------------------ rankings


def _seed_scored_wallet(
    db_session, *, address_suffix: str, nickname: str, trades: int, copyable_roi: float,
    skill: float,
):
    from app.models import Wallet, WalletMetrics, WalletScore

    wallet = Wallet(address=f"0x{address_suffix * 20}"[:42], nickname=nickname)
    db_session.add(wallet)
    db_session.flush()
    db_session.add(
        WalletMetrics(
            wallet_id=wallet.id,
            scope="tennis",
            completed_positions=trades,
            total_positions=trades,
            roi=copyable_roi,
            copyable_roi=copyable_roi,
            shrunk_copyable_roi=copyable_roi / 3,
            benchmark_delay_seconds=15,
            sample_confidence=100.0 if trades >= 100 else 20.0,
        )
    )
    db_session.add(
        WalletScore(
            wallet_id=wallet.id,
            scope="tennis",
            skill_score=skill,
            base_score=skill,
            total_penalty_multiplier=1.0,
            qualified=trades >= 30,
            confidence_level="high" if trades >= 100 else "insufficient",
            formula_version="v1",
        )
    )
    db_session.commit()
    return wallet


def test_undersampled_wallet_cannot_top_a_performance_ranking(client, db_session):
    """Eight lucky wins must not outrank a large, consistent sample.

    This is the spec's central ranking requirement. The lucky wallet still
    appears -- under "Emerging", labelled unproven -- but it cannot headline a
    list that reads as a recommendation.
    """
    _seed_scored_wallet(
        db_session, address_suffix="a", nickname="lucky", trades=8,
        copyable_roi=1.5, skill=51.0,
    )
    _seed_scored_wallet(
        db_session, address_suffix="b", nickname="grinder", trades=120,
        copyable_roi=0.19, skill=80.0,
    )

    rankings = client.get("/api/wallets/rankings?keys=best_copyable,emerging").json()
    best = next(r for r in rankings if r["key"] == "best_copyable")
    emerging = next(r for r in rankings if r["key"] == "emerging")

    assert [row["nickname"] for row in best["rows"]] == ["grinder"]
    # Not hidden -- relocated to the ranking that says it is unproven.
    assert [row["nickname"] for row in emerging["rows"]] == ["lucky"]
    assert "unproven" in emerging["caveat"]


def test_raw_profit_ranking_still_includes_small_samples(client, db_session):
    """The raw-profit list is explicitly not a copyability measure."""
    _seed_scored_wallet(
        db_session, address_suffix="c", nickname="lucky", trades=8,
        copyable_roi=1.5, skill=51.0,
    )
    ranking = client.get("/api/wallets/rankings?keys=highest_raw_profit").json()[0]
    assert "not a measure" in ranking["description"].lower() or "Raw profit" in ranking["caveat"]


def test_behavioural_profile_splits_hold_time_by_close_type(client, db_session):
    """Settlement closes must not be averaged into 'how long they held'.

    `resolved_at` is a settlement-bookkeeping timestamp that can land days after
    a match ends, so mixing redemption closes into hold time produces a figure
    that describes neither population.
    """
    from app.enums import PositionBehaviour, PositionStatus
    from app.models import ReconstructedPosition, Wallet

    wallet = Wallet(address=ADDRESS, nickname="mixed closer")
    db_session.add(wallet)
    db_session.flush()
    market, outcome = _make_market(db_session)

    def add(hold_seconds: int, redeemed: bool, token: str):
        db_session.add(
            ReconstructedPosition(
                wallet_id=wallet.id,
                market_id=market.id,
                token_id=token,
                condition_id=market.condition_id,
                outcome_index=0,
                status=PositionStatus.CLOSED,
                opened_at=datetime.now(timezone.utc) - timedelta(seconds=hold_seconds),
                opened_ts=1_700_000_000,
                closed_at=datetime.now(timezone.utc),
                closed_ts=1_700_000_000 + hold_seconds,
                first_entry_price=Decimal("0.5"),
                avg_entry_price=Decimal("0.5"),
                capital_committed=Decimal("100"),
                max_shares=Decimal("200"),
                realized_pnl=Decimal("10"),
                net_pnl=Decimal("10"),
                roi=0.1,
                is_win=True,
                holding_seconds=hold_seconds,
                settled_by_redemption=redeemed,
                behaviour=PositionBehaviour.DIRECTIONAL,
                is_tennis=True,
                reconstruction_confidence=100.0,
            )
        )

    # Two genuine sells at ~1h, two settlement closes at ~150h.
    add(3600, False, "tok-a")
    add(3600, False, "tok-b")
    add(540_000, True, "tok-c")
    add(540_000, True, "tok-d")
    db_session.commit()

    profile = client.get(f"/api/wallets/{wallet.id}").json()["behavioural_profile"]

    assert profile["positions_traded_out"] == 2
    assert profile["positions_held_to_settlement"] == 2
    assert profile["pct_held_to_settlement"] == 0.5
    # The traded-out median reflects real holding, not the 150h settlement lag.
    assert profile["median_hold_seconds_traded_out"] == 3600


def test_rotation_endpoint_reports_stances(client, db_session):
    """The rotation endpoint must be reachable and self-describing."""
    body = client.get("/api/wallets/rotation").json()
    for key in ("follow", "probation", "watch", "pause", "drop", "summary", "note"):
        assert key in body
    assert "not recommendations to bet" in body["note"]
