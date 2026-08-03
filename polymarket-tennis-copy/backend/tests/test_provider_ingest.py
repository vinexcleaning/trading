"""Provider and ingestion tests against mocked HTTP.

No network access: every upstream call is served by respx from payloads shaped
like the real ones verified against the live endpoints. The point of these tests
is the boundary behaviour that silently corrupts data when it goes wrong --
pagination that stops early, retries that mask failures, and re-ingestion that
double-counts.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal

import httpx
import pytest
import respx

from app.providers.http import (
    HttpClient,
    NotFoundError,
    ProviderError,
    RateLimiter,
    RateLimitedError,
)
from app.providers.polymarket import PolymarketProvider

GAMMA = "https://gamma-api.polymarket.com"
DATA_API = "https://data-api.polymarket.com"
CLOB = "https://clob.polymarket.com"

ADDRESS = "0x" + "cd" * 20
TOKEN = "71321045679252212594626385532706912750332728571942532289631379312455583992563"


@pytest.fixture()
def provider():
    # No pacing delay in tests; the limiter is exercised in its own test.
    client = HttpClient(rate_limiter=RateLimiter(0), max_retries=2, backoff_base=0.0)
    p = PolymarketProvider(client=client)
    yield p
    p.close()


def _activity(ts: int, *, side: str = "BUY", tx: str | None = None) -> dict:
    return {
        "proxyWallet": ADDRESS,
        "timestamp": ts,
        "conditionId": "0xcondition",
        "type": "TRADE",
        "size": 100.0,
        "usdcSize": 65.0,
        "transactionHash": tx or f"0xhash{ts}",
        "price": 0.65,
        "asset": TOKEN,
        "side": side,
        "outcomeIndex": 0,
        "title": "Alcaraz vs Sinner",
        "slug": "alcaraz-vs-sinner",
        "outcome": "Alcaraz",
    }


# ------------------------------------------------------------------ HTTP layer


@respx.mock
def test_retries_then_succeeds_on_transient_error(provider):
    route = respx.get(f"{DATA_API}/activity").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(500),
            httpx.Response(200, json=[_activity(1_700_000_000)]),
        ]
    )
    rows = list(provider.iter_wallet_activity(ADDRESS, max_pages=1))
    assert len(rows) == 1
    assert route.call_count == 3
    assert provider.http.stats.retries == 2


@respx.mock
def test_gives_up_after_max_retries(provider):
    respx.get(f"{DATA_API}/activity").mock(return_value=httpx.Response(503))
    with pytest.raises(ProviderError):
        list(provider.iter_wallet_activity(ADDRESS, max_pages=1))


@respx.mock
def test_rate_limit_is_counted_and_retried(provider):
    respx.get(f"{DATA_API}/activity").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json=[_activity(1_700_000_000)]),
        ]
    )
    rows = list(provider.iter_wallet_activity(ADDRESS, max_pages=1))
    assert len(rows) == 1
    assert provider.http.stats.rate_limit_events == 1


@respx.mock
def test_404_raises_but_allow_404_returns_none(provider):
    respx.get(f"{CLOB}/book").mock(return_value=httpx.Response(404))
    # The book endpoint tolerates a missing book rather than failing the scan.
    assert provider.get_order_book(TOKEN) is None

    respx.get(f"{DATA_API}/activity").mock(return_value=httpx.Response(404))
    with pytest.raises(NotFoundError):
        list(provider.iter_wallet_activity(ADDRESS, max_pages=1))


@respx.mock
def test_non_json_response_is_a_schema_error(provider):
    respx.get(f"{CLOB}/book").mock(return_value=httpx.Response(200, text="<html>nope</html>"))
    with pytest.raises(Exception) as exc:
        provider.get_order_book(TOKEN)
    assert "Non-JSON" in str(exc.value) or "SchemaError" in type(exc.value).__name__


# ------------------------------------------------------------------ pagination


@respx.mock
def test_activity_pagination_walks_until_short_page(provider):
    """A full page means 'ask for more'; a short page means stop."""
    page_size = 500
    full_page = [_activity(1_700_000_000 + i, tx=f"0xa{i}") for i in range(page_size)]
    short_page = [_activity(1_700_100_000 + i, tx=f"0xb{i}") for i in range(3)]

    route = respx.get(f"{DATA_API}/activity").mock(
        side_effect=[
            httpx.Response(200, json=full_page),
            httpx.Response(200, json=short_page),
        ]
    )
    rows = list(provider.iter_wallet_activity(ADDRESS, max_pages=10))

    assert len(rows) == page_size + 3
    assert route.call_count == 2
    # The second request must advance the offset, or it would loop on page one.
    assert route.calls[1].request.url.params["offset"] == str(page_size)


@respx.mock
def test_activity_pagination_respects_max_pages(provider):
    """Stops at the cap even when the upstream still has more to give."""
    page_one = [_activity(1_700_000_000 + i, tx=f"0xa{i}") for i in range(500)]
    page_two = [_activity(1_700_500_000 + i, tx=f"0xb{i}") for i in range(500)]
    route = respx.get(f"{DATA_API}/activity").mock(
        side_effect=[
            httpx.Response(200, json=page_one),
            httpx.Response(200, json=page_two),
            httpx.Response(200, json=page_one),  # would be page 3; must not be fetched
        ]
    )
    rows = list(provider.iter_wallet_activity(ADDRESS, max_pages=2))
    assert route.call_count == 2
    assert len(rows) == 1000


@respx.mock
def test_repeated_page_is_not_double_counted(provider):
    """A server that ignores the offset must not inflate the history.

    Returning the same rows again is indistinguishable from real data unless the
    provider de-duplicates, and silent duplication would corrupt every metric
    downstream.
    """
    page = [_activity(1_700_000_000 + i, tx=f"0xa{i}") for i in range(500)]
    respx.get(f"{DATA_API}/activity").mock(return_value=httpx.Response(200, json=page))
    rows = list(provider.iter_wallet_activity(ADDRESS, max_pages=3))
    assert len(rows) == 500


@respx.mock
def test_empty_first_page_stops_immediately(provider):
    route = respx.get(f"{DATA_API}/activity").mock(
        return_value=httpx.Response(200, json=[])
    )
    assert list(provider.iter_wallet_activity(ADDRESS, max_pages=5)) == []
    assert route.call_count == 1


# ------------------------------------------------------------------ order book


@respx.mock
def test_order_book_depth_is_notional_within_band(provider):
    respx.get(f"{CLOB}/book").mock(
        return_value=httpx.Response(
            200,
            json={
                "market": "0xcondition",
                "asset_id": TOKEN,
                "timestamp": "1700000000000",
                "bids": [{"price": "0.64", "size": "100"}],
                "asks": [
                    {"price": "0.66", "size": "100"},
                    {"price": "0.67", "size": "200"},
                    {"price": "0.90", "size": "5000"},
                ],
                "tick_size": "0.01",
                "min_order_size": "5",
            },
        )
    )
    book = provider.get_order_book(TOKEN)
    assert book is not None
    assert book.best_ask == Decimal("0.66")
    assert book.spread == Decimal("0.02")

    # Total depth is dominated by a level 24c away from touch; the banded figure
    # is what a follower could realistically reach.
    near = book.ask_depth_usdc(within=Decimal("0.02"))
    total = book.ask_depth_usdc()
    assert near == Decimal("0.66") * 100 + Decimal("0.67") * 200
    assert total > near * 10


# ------------------------------------------------------------------- ingestion


def _seed_market(db_session):
    from app.models import Market, Outcome

    market = Market(
        condition_id="0xcondition",
        question="Alcaraz vs Sinner",
        is_tennis=True,
        classification_confidence=100.0,
        game_start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(market)
    db_session.flush()
    db_session.add(
        Outcome(market_id=market.id, token_id=TOKEN, outcome_index=0, label="Alcaraz")
    )
    db_session.flush()
    return market


@respx.mock
def test_reingesting_the_same_activity_does_not_duplicate(db_session, provider):
    """Idempotency: syncing twice must not double the wallet's history."""
    from app.models import NormalizedTransaction, RawActivity
    from app.services.ingest import WalletIngestor, WalletRegistry

    _seed_market(db_session)
    wallet, _ = WalletRegistry(db_session).add_wallet(ADDRESS)
    db_session.flush()

    payload = [_activity(1_700_000_000), _activity(1_700_000_060)]
    respx.get(f"{DATA_API}/activity").mock(return_value=httpx.Response(200, json=payload))
    respx.get(f"{DATA_API}/positions").mock(return_value=httpx.Response(200, json=[]))
    respx.get(f"{DATA_API}/value").mock(return_value=httpx.Response(200, json=[]))
    respx.get(f"{CLOB}/markets/0xcondition").mock(return_value=httpx.Response(404))

    ingestor = WalletIngestor(db_session, provider)
    first = ingestor.sync_wallet(wallet, max_pages=1)
    db_session.flush()
    assert first.inserted == 2

    second = ingestor.sync_wallet(wallet, full_backfill=True, max_pages=1)
    db_session.flush()

    assert second.inserted == 0
    assert second.duplicates == 2
    assert db_session.query(NormalizedTransaction).count() == 2
    assert db_session.query(RawActivity).count() == 2


@respx.mock
def test_sync_records_success_time_and_job(db_session, provider):
    from app.models import IngestionJob
    from app.services.ingest import WalletIngestor, WalletRegistry

    _seed_market(db_session)
    wallet, _ = WalletRegistry(db_session).add_wallet(ADDRESS)
    db_session.flush()

    respx.get(f"{DATA_API}/activity").mock(
        return_value=httpx.Response(200, json=[_activity(1_700_000_000)])
    )
    respx.get(f"{DATA_API}/positions").mock(return_value=httpx.Response(200, json=[]))
    respx.get(f"{DATA_API}/value").mock(return_value=httpx.Response(200, json=[]))
    respx.get(f"{CLOB}/markets/0xcondition").mock(return_value=httpx.Response(404))

    WalletIngestor(db_session, provider).sync_wallet(wallet, max_pages=1)
    db_session.flush()

    assert wallet.last_sync_success_at is not None
    assert wallet.last_sync_error is None
    job = db_session.query(IngestionJob).order_by(IngestionJob.id.desc()).first()
    assert job is not None
    assert job.records_inserted == 1


def test_wallet_registry_rejects_malformed_addresses(db_session):
    from app.services.ingest import WalletRegistry

    registry = WalletRegistry(db_session)
    result = registry.import_csv(
        f"address\n{ADDRESS}\nnot-an-address\n0x123\n\n"
    )
    assert result["added"] == 1
    assert len(result["errors"]) == 2


def test_discovered_wallets_are_never_auto_approved(db_session):
    from app.services.ingest import WalletRegistry

    wallet, created = WalletRegistry(db_session).add_wallet(ADDRESS, source="market_activity")
    assert created
    # Discovery is not evidence of skill; approval stays a human decision.
    assert wallet.manually_approved is False


# ------------------------------------------------------------------ migrations


def test_migrations_produce_the_model_schema(tmp_path):
    """The migration must build exactly what the models declare.

    Autogenerate is compared against a migrated database: if the two disagree,
    production would be running a schema nobody tested against.
    """
    from alembic import command
    from alembic.autogenerate import compare_metadata
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from sqlalchemy import create_engine

    import app.models  # noqa: F401
    from app.db import Base

    db_path = tmp_path / "migrated.db"
    url = f"sqlite:///{db_path.as_posix()}"

    config = Config("alembic.ini")
    config.set_main_option("script_location", "backend/migrations")
    config.set_main_option("sqlalchemy.url", url)
    # env.py reads the application settings, so point those at the temp file too.
    import os

    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    from app.config import reset_settings_cache

    reset_settings_cache()
    try:
        command.upgrade(config, "head")

        engine = create_engine(url)
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            diff = compare_metadata(context, Base.metadata)
        engine.dispose()
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        reset_settings_cache()

    assert diff == [], f"schema drift between models and migrations: {diff}"


# ------------------------------------------------- offset cap / re-windowing


@respx.mock
def test_activity_rewindows_past_the_offset_cap(provider):
    """The API rejects offsets past 5000, so paging alone truncates history.

    Verified live: HTTP 400 "max historical activity offset of 5000 exceeded".
    The iterator must re-anchor on the newest timestamp seen and restart the
    offset, otherwise an active wallet's older history is silently unreachable
    and every metric computed from it is quietly wrong.
    """
    from app.providers.polymarket import MAX_ACTIVITY_OFFSET

    page_size = 500
    pages_before_cap = MAX_ACTIVITY_OFFSET // page_size  # 10

    def handler(request):
        offset = int(request.url.params.get("offset", 0))
        start = int(request.url.params.get("start", 0) or 0)
        # A server honouring the documented cap would 400 here; assert we never
        # ask for it.
        assert offset + page_size <= MAX_ACTIVITY_OFFSET, (
            f"requested offset {offset} would exceed the API cap"
        )
        # First window: 10 full pages. Second window (start re-anchored): one
        # short page, ending the walk.
        if start == 0:
            base = 1_700_000_000 + offset
            return httpx.Response(
                200,
                json=[_activity(base + i, tx=f"0xw1-{offset + i}") for i in range(page_size)],
            )
        return httpx.Response(
            200, json=[_activity(start + 1 + i, tx=f"0xw2-{i}") for i in range(3)]
        )

    route = respx.get(f"{DATA_API}/activity").mock(side_effect=handler)
    rows = list(provider.iter_wallet_activity(ADDRESS, max_pages=40))

    # 10 pages of 500 in the first window, then 3 in the re-anchored window.
    assert len(rows) == pages_before_cap * page_size + 3
    assert route.call_count == pages_before_cap + 1
    # The re-anchored request carries a start timestamp instead of a big offset.
    assert int(route.calls[-1].request.url.params["start"]) > 0
    assert int(route.calls[-1].request.url.params["offset"]) == 0


@respx.mock
def test_rewindow_stops_when_no_progress_is_possible(provider):
    """A stalled window must terminate rather than loop forever."""
    page_size = 500
    # Every page returns the same rows, so re-anchoring yields nothing new.
    page = [_activity(1_700_000_000, tx=f"0xsame-{i}") for i in range(page_size)]
    respx.get(f"{DATA_API}/activity").mock(return_value=httpx.Response(200, json=page))

    rows = list(provider.iter_wallet_activity(ADDRESS, max_pages=100))
    # Deduplication means only the first page's rows are unique.
    assert len(rows) == page_size
