"""Shared test fixtures.

Tests run entirely against an in-memory database and recorded fixtures so the
suite never needs network access.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Must be set before app.config is first imported.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("NOTIFICATIONS_ENABLED", "false")


@pytest.fixture(scope="session", autouse=True)
def _configure_logging() -> None:
    from app.logging_setup import configure_logging

    configure_logging(level="WARNING", json_output=False)


@pytest.fixture()
def db_session() -> Iterator["Session"]:  # type: ignore[name-defined] # noqa: F821
    """A fresh in-memory schema per test."""
    # Import the models package first: ``Base.metadata`` only knows about tables
    # whose modules have been imported, so create_all would otherwise build a
    # partial schema depending on what the test module happened to import.
    import app.models  # noqa: F401
    from app.db import Base, get_engine, get_session_factory, reset_engine

    reset_engine()
    engine = get_engine()
    Base.metadata.create_all(engine)
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(engine)
        reset_engine()


@pytest.fixture()
def settings():
    from app.config import get_settings, reset_settings_cache

    reset_settings_cache()
    yield get_settings()
    reset_settings_cache()


@pytest.fixture()
def client(db_session) -> Iterator["TestClient"]:  # type: ignore[name-defined] # noqa: F821
    """API client bound to the per-test in-memory schema.

    ``get_db`` is overridden rather than left to open its own session so that
    writes made by a test are visible to the endpoint under test, and vice versa.
    The lifespan still runs, but ``APP_ENV=test`` keeps the scheduler from
    starting, so no background job or network call fires during tests.
    """
    from fastapi.testclient import TestClient

    from app.db import get_db
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
