"""Database engine, session factory and the declarative base.

SQLite is the local default. Because SQLite has no native DECIMAL type we
register a Decimal-preserving adapter so monetary values never silently degrade
to binary floats.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Numeric, TypeDecorator, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import get_settings
from .logging_setup import get_logger

log = get_logger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class SqliteSafeNumeric(TypeDecorator):
    """Numeric that round-trips ``Decimal`` exactly on SQLite.

    SQLAlchemy warns (and loses precision) when Numeric is used on SQLite
    because values are stored as REAL. Storing the decimal as TEXT and parsing
    it back keeps money exact on both backends.
    """

    impl = Numeric
    cache_ok = True

    def __init__(self, precision: int = 28, scale: int = 10, **kw: Any) -> None:
        self.precision = precision
        self.scale = scale
        super().__init__(precision=precision, scale=scale, **kw)

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "sqlite":
            from sqlalchemy import String

            return dialect.type_descriptor(String(64))
        return dialect.type_descriptor(Numeric(self.precision, self.scale))

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "sqlite":
            return str(Decimal(str(value)))
        return Decimal(str(value))

    def process_result_value(self, value: Any, dialect: Any) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))


class UtcDateTime(TypeDecorator):
    """Timezone-aware datetime that stays aware on every backend.

    SQLite has no native timestamptz, so SQLAlchemy hands back *naive* datetimes
    even for ``DateTime(timezone=True)`` columns. Comparing one of those to an
    aware ``datetime.now(timezone.utc)`` raises
    ``can't subtract offset-naive and offset-aware datetimes`` -- a runtime error
    that only shows up on whichever code path happens to read the column.

    Normalising here means every datetime leaving the database is UTC-aware, so
    no call site has to remember. Values are converted to UTC on write, so a
    caller passing a non-UTC aware datetime is stored correctly rather than
    truncated.
    """

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        return dialect.type_descriptor(DateTime(timezone=True))

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None:
                # Naive input is assumed UTC: the application never produces
                # local-time datetimes.
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value: Any, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


# Money: up to 18 integer digits, 6 decimal places of USDC precision.
Money = SqliteSafeNumeric(28, 6)
# Prices: Polymarket ticks are 0.001 or 0.01; 6 dp is ample headroom.
Price = SqliteSafeNumeric(12, 6)
# Share quantities.
Qty = SqliteSafeNumeric(28, 6)


def _build_engine() -> Engine:
    settings = get_settings()
    url = settings.database_url
    kwargs: dict[str, Any] = {"echo": settings.db_echo, "future": True}

    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
        if ":memory:" in url:
            # Keep one connection so in-memory schemas survive across sessions.
            kwargs["poolclass"] = StaticPool
    else:
        kwargs["pool_pre_ping"] = True
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20

    engine = create_engine(url, **kwargs)

    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn: Any, _rec: Any) -> None:
            cur = dbapi_conn.cursor()
            # WAL keeps the scheduler writing while the API reads.
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA busy_timeout=30000")
            cur.close()

    return engine


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _build_engine()
        log.info("database.engine_created", dialect=_engine.dialect.name)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False
        )
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope for background jobs and services."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def reset_engine() -> None:
    """Test hook: drop cached engine/session factory."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
