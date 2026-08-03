"""Generate deterministic demo data and run the real analytics pipeline over it.

This is not a fixture dump: it writes markets, outcomes and wallet transactions,
then invokes the actual reconstruction, copyability, metrics, scoring, clustering
and signal code. That makes it both a populated demo and an end-to-end smoke test
of the whole chain.

The wallet archetypes are chosen to exercise the judgements the product exists to
make:

* ``grinder``      -- modest edge, hundreds of trades, price stays put. Copyable.
* ``front_runner`` -- strong raw ROI, but the price gaps away immediately after
                      it buys. Profitable, and *not* copyable.
* ``lucky``        -- eight big wins. Should not outrank the grinder.
* ``twin``         -- mirrors the grinder's trades minutes apart, to exercise
                      cluster detection and consensus de-duplication.
* ``maker``        -- buys and sells both outcomes; should be flagged, not ranked.
* ``loser``        -- negative edge.

Usage:
    python scripts/seed_demo.py [--reset]
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.db import Base, get_engine, session_scope  # noqa: E402
from app.enums import (  # noqa: E402
    ActivityType,
    ClassificationMethod,
    SportCategory,
    TennisMarketType,
    TradeSide,
    WalletSource,
)
from app.models import (  # noqa: E402
    Event,
    Market,
    MarketPrice,
    NormalizedTransaction,
    Outcome,
    PriceObservationKind,
    Wallet,
)

SEED = 20260729
NOW = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)

PLAYERS = [
    ("Carlos Alcaraz", "Jannik Sinner"),
    ("Iga Swiatek", "Aryna Sabalenka"),
    ("Novak Djokovic", "Daniil Medvedev"),
    ("Coco Gauff", "Elena Rybakina"),
    ("Alexander Zverev", "Casper Ruud"),
    ("Jessica Pegula", "Qinwen Zheng"),
    ("Taylor Fritz", "Frances Tiafoe"),
    ("Ons Jabeur", "Maria Sakkari"),
    ("Holger Rune", "Stefanos Tsitsipas"),
    ("Emma Raducanu", "Naomi Osaka"),
    ("Grigor Dimitrov", "Andrey Rublev"),
    ("Madison Keys", "Danielle Collins"),
]

TOURNAMENTS = ["Wimbledon", "US Open", "Miami Open", "Madrid Open", "Roland Garros"]

ARCHETYPES = {
    "grinder": {
        "nickname": "Steady grinder",
        "trades": 150,
        # A genuine, modest edge held over a large sample. This is the archetype
        # the scoring is meant to reward, so it is seeded to actually clear the
        # alert gates rather than having the thresholds relaxed to let it through.
        "win_rate": 0.67,
        "entry_range": (0.45, 0.58),
        # Price barely moves after entry: a follower gets nearly the same fill.
        "drift": (-0.004, 0.006),
        "hold_hours": (6, 40),
        # Consistent sizing keeps drawdown shallow, as a disciplined wallet's
        # would be.
        "size": (200, 300),
    },
    "front_runner": {
        "nickname": "Fast mover (uncopyable)",
        "trades": 70,
        "win_rate": 0.66,
        "entry_range": (0.40, 0.60),
        # Price gaps up right after entry, so the edge is gone by the time
        # anyone could follow.
        "drift": (0.055, 0.11),
        "hold_hours": (0.05, 0.4),
        "size": (400, 900),
    },
    "lucky": {
        "nickname": "Eight lucky wins",
        "trades": 8,
        "win_rate": 0.88,
        "entry_range": (0.25, 0.40),
        "drift": (-0.01, 0.02),
        "hold_hours": (10, 60),
        "size": (600, 1500),
    },
    "twin": {
        "nickname": "Grinder twin (related?)",
        "trades": 90,
        "win_rate": 0.57,
        "entry_range": (0.45, 0.62),
        "drift": (-0.004, 0.006),
        "hold_hours": (6, 40),
        "size": (140, 380),
    },
    "maker": {
        "nickname": "Two-sided quoter",
        "trades": 60,
        "win_rate": 0.50,
        "entry_range": (0.42, 0.58),
        "drift": (-0.01, 0.01),
        "hold_hours": (0.2, 3),
        "size": (80, 200),
        "both_sides": True,
    },
    "loser": {
        "nickname": "Negative edge",
        "trades": 55,
        "win_rate": 0.38,
        "entry_range": (0.50, 0.70),
        "drift": (-0.02, 0.01),
        "hold_hours": (5, 30),
        "size": (100, 300),
    },
}


def address_for(name: str) -> str:
    """Deterministic pseudo-address, clearly synthetic."""
    digest = abs(hash((name, SEED))) % (16**36)
    return "0xde" + f"{digest:036x}"[:38]


def build_markets(session, rng: random.Random) -> list[tuple[Market, list[Outcome]]]:
    made: list[tuple[Market, list[Outcome]]] = []

    for index, (player_a, player_b) in enumerate(PLAYERS):
        tournament = TOURNAMENTS[index % len(TOURNAMENTS)]
        # Spread from ~4 months ago to a few days ago, so recency weighting and
        # the 7/30/90-day period breakdowns all have data to work with.
        start = NOW - timedelta(days=120 - index * 10, hours=rng.randint(0, 20))
        resolved = start < NOW - timedelta(days=2)

        event = Event(
            gamma_event_id=f"demo-event-{index}",
            slug=f"demo-{player_a.split()[-1].lower()}-{player_b.split()[-1].lower()}",
            title=f"{player_a} vs {player_b}",
            sport_category=SportCategory.TENNIS,
            tournament=tournament,
            player_a=player_a,
            player_b=player_b,
            best_of=5 if tournament in ("Wimbledon", "US Open", "Roland Garros") else 3,
            tour="ATP" if index % 2 == 0 else "WTA",
            start_date=start,
            closed=resolved,
        )
        session.add(event)
        session.flush()

        winner_index = rng.randint(0, 1)
        market = Market(
            condition_id=f"0xdemo{index:04d}",
            gamma_market_id=f"demo-{index}",
            slug=event.slug,
            question=f"{player_a} vs {player_b}",
            event_id=event.id,
            sport_category=SportCategory.TENNIS,
            is_tennis=True,
            tennis_market_type=TennisMarketType.MATCH_WINNER,
            sports_market_type_raw="moneyline",
            classification_confidence=100.0,
            classification_methods=f'["{ClassificationMethod.OFFICIAL_SPORTS_METADATA}"]',
            needs_review=False,
            game_start_time=start,
            start_date=start,
            closed=resolved,
            resolved=resolved,
            winning_outcome_index=winner_index if resolved else None,
            resolved_at=start + timedelta(hours=3) if resolved else None,
            accepting_orders=not resolved,
            liquidity=Decimal(rng.randint(3_000, 45_000)),
            volume=Decimal(rng.randint(20_000, 400_000)),
            volume_24hr=Decimal(rng.randint(1_000, 40_000)),
            spread=Decimal(str(round(rng.uniform(0.005, 0.02), 3))),
            best_bid=Decimal("0.49"),
            best_ask=Decimal("0.51"),
            tick_size=Decimal("0.01"),
            min_order_size=Decimal("5"),
            synced_at=NOW,
        )
        session.add(market)
        session.flush()

        outcomes = []
        for outcome_index, label in enumerate((player_a, player_b)):
            outcome = Outcome(
                market_id=market.id,
                token_id=f"demo-token-{index}-{outcome_index}",
                outcome_index=outcome_index,
                label=label,
                player_name=label,
                is_winner=(outcome_index == winner_index) if resolved else None,
                last_price=Decimal("0.5"),
            )
            session.add(outcome)
            outcomes.append(outcome)
        session.flush()
        made.append((market, outcomes))

    return made


def build_live_markets(session, rng: random.Random) -> list[tuple[Market, list[Outcome]]]:
    """Open markets starting shortly, for the live-signal demo.

    These are anchored to the real clock rather than the fixed seed timestamp, so
    signals generated against them are genuinely fresh when the dashboard is
    opened straight after seeding. A stale signal is correctly rejected, which
    would leave the feed empty.
    """
    real_now = datetime.now(timezone.utc)
    made: list[tuple[Market, list[Outcome]]] = []

    upcoming = [
        ("Carlos Alcaraz", "Novak Djokovic", "Wimbledon"),
        ("Iga Swiatek", "Coco Gauff", "US Open"),
        ("Jannik Sinner", "Alexander Zverev", "Madrid Open"),
    ]

    for offset, (player_a, player_b, tournament) in enumerate(upcoming):
        start = real_now + timedelta(hours=2 + offset * 6)
        event = Event(
            gamma_event_id=f"demo-live-event-{offset}",
            slug=f"demo-live-{player_a.split()[-1].lower()}-{player_b.split()[-1].lower()}",
            title=f"{player_a} vs {player_b}",
            sport_category=SportCategory.TENNIS,
            tournament=tournament,
            player_a=player_a,
            player_b=player_b,
            best_of=5 if tournament in ("Wimbledon", "US Open") else 3,
            tour="ATP" if offset != 1 else "WTA",
            start_date=start,
            closed=False,
        )
        session.add(event)
        session.flush()

        market = Market(
            condition_id=f"0xdemolive{offset:02d}",
            gamma_market_id=f"demo-live-{offset}",
            slug=event.slug,
            question=f"{player_a} vs {player_b}",
            event_id=event.id,
            sport_category=SportCategory.TENNIS,
            is_tennis=True,
            tennis_market_type=TennisMarketType.MATCH_WINNER,
            sports_market_type_raw="moneyline",
            classification_confidence=100.0,
            classification_methods=f'["{ClassificationMethod.OFFICIAL_SPORTS_METADATA}"]',
            needs_review=False,
            game_start_time=start,
            start_date=start,
            closed=False,
            resolved=False,
            accepting_orders=True,
            liquidity=Decimal(rng.randint(12_000, 60_000)),
            volume=Decimal(rng.randint(40_000, 300_000)),
            volume_24hr=Decimal(rng.randint(8_000, 60_000)),
            spread=Decimal("0.01"),
            best_bid=Decimal("0.58"),
            best_ask=Decimal("0.59"),
            tick_size=Decimal("0.01"),
            min_order_size=Decimal("5"),
            synced_at=real_now,
        )
        session.add(market)
        session.flush()

        outcomes = []
        for outcome_index, label in enumerate((player_a, player_b)):
            outcome = Outcome(
                market_id=market.id,
                token_id=f"demo-live-token-{offset}-{outcome_index}",
                outcome_index=outcome_index,
                label=label,
                player_name=label,
                is_winner=None,
                last_price=Decimal("0.58") if outcome_index == 0 else Decimal("0.42"),
            )
            session.add(outcome)
            outcomes.append(outcome)
        session.flush()
        made.append((market, outcomes))

    return made


def seed_live_activity(
    session,
    wallets_by_key: dict[str, Wallet],
    live_markets: list[tuple[Market, list[Outcome]]],
    rng: random.Random,
) -> None:
    """Recent entries on open markets, so the live feed has real candidates.

    Three scenarios are staged deliberately:

    1. The grinder alone enters an open market -- a single-wallet candidate.
    2. The grinder and its twin both enter the same outcome. They are one
       behavioural cluster, so this must *fail* the independence requirement
       rather than read as two confirmations.
    3. The fast mover enters and the price immediately runs away, so the
       candidate is rejected on price deterioration.
    """
    real_now = datetime.now(timezone.utc)

    scenarios = [
        (["grinder"], 0, Decimal("0.58"), 0.002, 95),
        (["grinder", "twin"], 1, Decimal("0.61"), 0.004, 150),
        (["front_runner"], 2, Decimal("0.55"), 0.09, 70),
    ]

    for keys, market_slot, entry_price, drift, seconds_ago in scenarios:
        market, outcomes = live_markets[market_slot]
        outcome = outcomes[0]

        for index, key in enumerate(keys):
            wallet = wallets_by_key[key]
            entry_at = real_now - timedelta(seconds=seconds_ago - index * 30)
            entry_ts = int(entry_at.timestamp())
            size = Decimal(str(rng.randint(400, 900)))
            shares = (size / entry_price).quantize(Decimal("0.01"))

            session.add(
                NormalizedTransaction(
                    wallet_id=wallet.id,
                    market_id=market.id,
                    outcome_id=outcome.id,
                    condition_id=market.condition_id,
                    token_id=outcome.token_id,
                    outcome_index=outcome.outcome_index,
                    activity_type=ActivityType.TRADE,
                    side=TradeSide.BUY,
                    size=shares,
                    price=entry_price,
                    usdc_size=size,
                    timestamp=entry_ts,
                    occurred_at=entry_at,
                    transaction_hash=f"0xdemolive{wallet.id:03d}{market_slot}{index}",
                    market_phase="prematch",
                    is_tennis=True,
                    processed=True,
                )
            )

            add_price_evidence(
                session,
                outcome,
                market.id,
                entry_ts,
                entry_price,
                drift,
                int(real_now.timestamp()),
                entry_price + Decimal(str(round(drift, 4))),
            )

    session.flush()


def add_price_evidence(
    session,
    outcome: Outcome,
    market_id: int,
    entry_ts: int,
    entry_price: Decimal,
    drift: float,
    exit_ts: int,
    exit_price: Decimal,
) -> None:
    """Write trade prints around an entry, then bars through to the exit.

    Second-level prints near the entry are what make sub-minute delay analysis
    possible at all; without them the resolver correctly falls back to modelled
    prices and the copyable figures are withheld.
    """
    # Dense prints across the first two minutes, following the drift.
    #
    # The drift completes within ~10 seconds. That is the point of the
    # front-runner archetype: if the move took two minutes, a 15-second follower
    # would capture most of it and the wallet would look copyable when it is not.
    for offset in (-90, -45, -20, -8, -2, 0, 2, 5, 10, 15, 30, 45, 60, 90, 120):
        progress = 0.0 if offset <= 0 else min(1.0, offset / 10.0)
        price = float(entry_price) + drift * progress
        session.add(
            MarketPrice(
                token_id=outcome.token_id,
                market_id=market_id,
                timestamp=entry_ts + offset,
                observed_at=datetime.fromtimestamp(entry_ts + offset, tz=timezone.utc),
                kind=PriceObservationKind.TRADE_PRINT,
                price=Decimal(str(round(max(0.01, min(0.99, price)), 4))),
                size=Decimal("120"),
                source="demo_seed",
            )
        )

    # Minute bars from just after the entry to the exit, walking toward the exit
    # price so hold-to-resolution has something to resolve against.
    span = max(exit_ts - entry_ts, 120)
    steps = min(60, max(4, span // 900))
    start_price = float(entry_price) + drift
    for step in range(1, steps + 1):
        ts = entry_ts + int(span * step / steps)
        ratio = step / steps
        price = start_price + (float(exit_price) - start_price) * ratio
        session.add(
            MarketPrice(
                token_id=outcome.token_id,
                market_id=market_id,
                timestamp=ts,
                observed_at=datetime.fromtimestamp(ts, tz=timezone.utc),
                kind=PriceObservationKind.MINUTE_BAR,
                price=Decimal(str(round(max(0.01, min(0.99, price)), 4))),
                source="demo_seed",
            )
        )


def seed_wallet(
    session,
    key: str,
    spec: dict,
    markets: list[tuple[Market, list[Outcome]]],
    rng: random.Random,
    mirror_of: list[dict] | None = None,
) -> tuple[Wallet, list[dict]]:
    """Create a wallet and its activity.

    ``mirror_of`` replays another wallet's trades a few minutes later on the same
    outcomes. That is what makes the twin genuinely detectable as related: an
    independently-drawn wallet would share no pattern, and cluster detection would
    correctly find nothing.
    """
    wallet = Wallet(
        address=address_for(key),
        nickname=spec["nickname"],
        source=WalletSource.MANUAL,
        source_detail="demo seed",
        status="active",
        manually_approved=True,
        backfill_complete=True,
        sync_priority=5,
        last_sync_success_at=NOW,
        observed_portfolio_value=Decimal(rng.randint(5_000, 90_000)),
    )
    session.add(wallet)
    session.flush()

    first_ts: int | None = None
    last_ts = 0
    plans: list[dict] = []

    total = len(mirror_of) if mirror_of is not None else spec["trades"]

    for trade_index in range(total):
        if mirror_of is not None:
            source = mirror_of[trade_index]
            market, outcomes = markets[source["market_slot"]]
            # A few minutes behind, on the same outcome, at a similar size: the
            # pattern cluster detection is designed to notice.
            entry_ts = source["entry_ts"] + rng.randint(60, 300)
            entry_at = datetime.fromtimestamp(entry_ts, tz=timezone.utc)
            chosen_index = source["outcome_index"]
            outcome = outcomes[chosen_index]
            entry_price = source["entry_price"]
            drift = source["drift"]
            size = (source["size"] * Decimal(str(round(rng.uniform(0.9, 1.1), 2)))).quantize(
                Decimal("1")
            )
            wins = source["wins"]
            hold_hours = source["hold_hours"]
        else:
            market_slot = trade_index % len(markets)
            market, outcomes = markets[market_slot]
            if not market.resolved:
                continue

            # Spread entries across the market's life so recency and time-split
            # analysis have something to work with.
            base = market.game_start_time - timedelta(days=rng.randint(1, 25))
            entry_at = base + timedelta(minutes=rng.randint(0, 900))
            entry_ts = int(entry_at.timestamp())

            wins = rng.random() < spec["win_rate"]
            # Pick the side that produces the intended result.
            winning_index = market.winning_outcome_index or 0
            chosen_index = winning_index if wins else 1 - winning_index
            outcome = outcomes[chosen_index]

            entry_price = Decimal(str(round(rng.uniform(*spec["entry_range"]), 3)))
            drift = rng.uniform(*spec["drift"])
            size = Decimal(str(rng.randint(*spec["size"])))
            hold_hours = rng.uniform(*spec["hold_hours"])

            plans.append(
                {
                    "market_slot": market_slot,
                    "entry_ts": entry_ts,
                    "outcome_index": chosen_index,
                    "entry_price": entry_price,
                    "drift": drift,
                    "size": size,
                    "wins": wins,
                    "hold_hours": hold_hours,
                }
            )

        if not market.resolved:
            continue
        shares = (size / entry_price).quantize(Decimal("0.01"))

        session.add(
            NormalizedTransaction(
                wallet_id=wallet.id,
                market_id=market.id,
                outcome_id=outcome.id,
                condition_id=market.condition_id,
                token_id=outcome.token_id,
                outcome_index=outcome.outcome_index,
                activity_type=ActivityType.TRADE,
                side=TradeSide.BUY,
                size=shares,
                price=entry_price,
                usdc_size=size,
                timestamp=entry_ts,
                occurred_at=entry_at,
                transaction_hash=f"0xdemo{wallet.id:03d}{trade_index:04d}a",
                market_phase="prematch",
                is_tennis=True,
                processed=True,
            )
        )

        exit_at = entry_at + timedelta(hours=hold_hours)
        exit_ts = int(exit_at.timestamp())
        exit_price = Decimal("0.97") if wins else Decimal("0.04")

        session.add(
            NormalizedTransaction(
                wallet_id=wallet.id,
                market_id=market.id,
                outcome_id=outcome.id,
                condition_id=market.condition_id,
                token_id=outcome.token_id,
                outcome_index=outcome.outcome_index,
                activity_type=ActivityType.TRADE,
                side=TradeSide.SELL,
                size=shares,
                price=exit_price,
                usdc_size=(shares * exit_price).quantize(Decimal("0.01")),
                timestamp=exit_ts,
                occurred_at=exit_at,
                transaction_hash=f"0xdemo{wallet.id:03d}{trade_index:04d}b",
                market_phase="live",
                is_tennis=True,
                processed=True,
            )
        )

        # The two-sided quoter also takes the other side, which is what should
        # get it flagged rather than ranked.
        if spec.get("both_sides"):
            other = outcomes[1 - chosen_index]
            session.add(
                NormalizedTransaction(
                    wallet_id=wallet.id,
                    market_id=market.id,
                    outcome_id=other.id,
                    condition_id=market.condition_id,
                    token_id=other.token_id,
                    outcome_index=other.outcome_index,
                    activity_type=ActivityType.TRADE,
                    side=TradeSide.BUY,
                    size=shares,
                    price=Decimal("1") - entry_price,
                    usdc_size=size,
                    timestamp=entry_ts + 30,
                    occurred_at=entry_at + timedelta(seconds=30),
                    transaction_hash=f"0xdemo{wallet.id:03d}{trade_index:04d}c",
                    market_phase="prematch",
                    is_tennis=True,
                    processed=True,
                )
            )

        # Price evidence is written once per (token, entry) pair; the grinder and
        # its twin share markets, so guard against duplicate work.
        add_price_evidence(
            session, outcome, market.id, entry_ts, entry_price, drift, exit_ts, exit_price
        )

        first_ts = entry_ts if first_ts is None else min(first_ts, entry_ts)
        last_ts = max(last_ts, exit_ts)

    if first_ts:
        wallet.first_activity_at = datetime.fromtimestamp(first_ts, tz=timezone.utc)
        wallet.last_activity_at = datetime.fromtimestamp(last_ts, tz=timezone.utc)
        wallet.sync_cursor_ts = last_ts
    session.flush()
    return wallet, plans


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed demo data and run the pipeline.")
    parser.add_argument(
        "--reset", action="store_true", help="drop and recreate all tables first"
    )
    args = parser.parse_args()

    engine = get_engine()
    if args.reset:
        print("Dropping and recreating schema…")
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    rng = random.Random(SEED)

    with session_scope() as session:
        if session.query(Wallet).count() and not args.reset:
            print("Database already contains wallets. Re-run with --reset to rebuild.")
            return 1

        print("Creating demo markets…")
        markets = build_markets(session, rng)
        print(f"  {len(markets)} tennis markets")

        print("Creating wallets and activity…")
        grinder_plans: list[dict] = []
        wallets_by_key: dict[str, Wallet] = {}
        # The grinder is seeded first so the twin can replay its trades.
        for key in ("grinder", "front_runner", "lucky", "twin", "maker", "loser"):
            spec = ARCHETYPES[key]
            wallet, plans = seed_wallet(
                session,
                key,
                spec,
                markets,
                rng,
                mirror_of=grinder_plans if key == "twin" else None,
            )
            wallets_by_key[key] = wallet
            if key == "grinder":
                grinder_plans = plans
            note = " (mirrors the grinder)" if key == "twin" else ""
            print(f"  {wallet.nickname:<28} {spec['trades']:>4} intended trades{note}")

        print("Creating open markets and recent activity for the live feed…")
        live_markets = build_live_markets(session, rng)
        seed_live_activity(session, wallets_by_key, live_markets, rng)
        print(f"  {len(live_markets)} open markets with entries in the last few minutes")

        session.commit()

        print("\nRunning the analytics pipeline over the seeded data…")
        from app.services.pipeline import AnalyticsPipeline

        pipeline = AnalyticsPipeline(session)
        stats = pipeline.run_full()
        clusters = pipeline.compute_clusters(min_positions=3)
        session.commit()

        print(f"  positions reconstructed : {stats.positions_written}")
        print(f"  copyability rows        : {stats.copyability_rows}")
        print(f"  metrics written         : {stats.metrics_written}")
        print(f"  wallets scored          : {stats.scores_written}")
        print(f"  wallet clusters found   : {clusters}")
        if stats.errors:
            print(f"  errors                  : {len(stats.errors)}")
            for err in stats.errors[:5]:
                print(f"    - {err}")

        print("\nScanning for signals (no network; uses stored prices)…")
        from app.services.monitor import SignalMonitor

        # Scanned against the real clock so the recent entries are genuinely
        # fresh. The historical trades are swept up too and rejected as stale --
        # which is exactly what the rejection log is for.
        monitor = SignalMonitor(session, provider=None)
        scan = monitor.scan(lookback_seconds=200 * 86_400, dispatch=False, paper=True)
        session.commit()
        print(
            f"  evaluated {scan.tokens_evaluated} outcomes -> "
            f"{scan.qualified} qualified, {scan.rejected} rejected, "
            f"{scan.paper_entered} paper entries"
        )

        print("\nWallet scores:")
        from app.models import WalletMetrics, WalletScore
        from sqlalchemy import select

        rows = session.execute(
            select(Wallet.nickname, WalletScore.skill_score, WalletScore.qualified,
                   WalletMetrics.completed_positions, WalletMetrics.roi,
                   WalletMetrics.copyable_roi, WalletMetrics.copyable_coverage)
            .join(WalletScore, WalletScore.wallet_id == Wallet.id)
            .outerjoin(
                WalletMetrics,
                (WalletMetrics.wallet_id == Wallet.id) & (WalletMetrics.scope == "tennis"),
            )
            .where(WalletScore.scope == "tennis")
            .order_by(WalletScore.skill_score.desc())
        ).all()

        print(f"  {'wallet':<28} {'score':>6} {'qual':>5} {'n':>5} {'raw':>8} {'copy':>8} {'cov':>6}")
        for nickname, score, qualified, n, roi, copy_roi, coverage in rows:
            print(
                f"  {(nickname or '?'):<28} {score:>6.1f} {str(bool(qualified)):>5} "
                f"{(n or 0):>5} {_fmt(roi):>8} {_fmt(copy_roi):>8} {_fmt(coverage):>6}"
            )

    print("\nDone. Start the API with:  uvicorn app.main:app --app-dir backend --reload")
    return 0


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


if __name__ == "__main__":
    raise SystemExit(main())
