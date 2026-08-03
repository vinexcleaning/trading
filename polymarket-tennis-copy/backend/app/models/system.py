"""Operational tables: ingestion jobs, errors, overrides, settings."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..db import UtcDateTime, Base
from ..enums import JobStatus


class IngestionJob(Base):
    """One execution of a sync task, with the counters the health panel shows."""

    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    # Correlates every log line emitted during the job.
    job_uid: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        String(20), default=JobStatus.RUNNING, nullable=False, index=True
    )

    target: Mapped[str | None] = mapped_column(String(120))
    wallet_id: Mapped[int | None] = mapped_column(
        ForeignKey("wallets.id", ondelete="SET NULL"), index=True
    )

    records_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_skipped_duplicate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pages_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    http_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    http_retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rate_limit_events: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False, index=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    error: Mapped[str | None] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("ix_jobs_type_started", "job_type", "started_at"),)


class SystemError(Base):
    """Recorded failure, surfaced in the frontend error dashboard."""

    __tablename__ = "system_errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    severity: Mapped[str] = mapped_column(String(15), default="error", nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    component: Mapped[str] = mapped_column(String(80), nullable=False)

    message: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(String(40))
    job_uid: Mapped[str | None] = mapped_column(String(40))

    # Repeated identical failures increment a counter instead of flooding.
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False, index=True
    )
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_system_error_fingerprint"),
        Index("ix_errors_recent", "resolved", "last_seen_at"),
    )


class ManualOverride(Base):
    """Human correction that outranks automated classification.

    Overrides are kept as data rather than applied destructively so the
    classifier's own output stays auditable and the override can be revoked.
    """

    __tablename__ = "manual_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entity_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    field: Mapped[str] = mapped_column(String(60), nullable=False)
    value: Mapped[str | None] = mapped_column(Text)

    reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(80), default="operator", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_key", "field", name="uq_override_target"),
    )


class ApplicationSetting(Base):
    """Runtime-editable setting overlaying the environment defaults.

    Only non-secret operational values live here; credentials stay in the
    environment so they can never be read back through the API.
    """

    __tablename__ = "application_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    value: Mapped[str | None] = mapped_column(Text)
    value_type: Mapped[str] = mapped_column(String(20), default="str", nullable=False)
    category: Mapped[str] = mapped_column(String(40), default="general", nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DataQualityReport(Base):
    """Periodic snapshot of pipeline completeness and confidence."""

    __tablename__ = "data_quality_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    generated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False, index=True
    )

    wallets_tracked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wallets_stale: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    markets_tracked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    markets_needing_review: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transactions_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transactions_unmatched_market: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    positions_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    positions_low_confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Distribution of price-source tiers behind copyability numbers.
    price_quality_breakdown_json: Mapped[str | None] = mapped_column(Text)
    avg_data_confidence: Mapped[float | None] = mapped_column(Float)
    # JSON list of human-readable warnings for the health panel.
    warnings_json: Mapped[str | None] = mapped_column(Text)


class SchemaDriftEvent(Base):
    """Recorded when an upstream payload gains or loses expected fields.

    Silent upstream schema changes are the most likely way this system starts
    producing quietly wrong numbers, so drift is a first-class alertable event.
    """

    __tablename__ = "schema_drift_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    endpoint: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    missing_fields: Mapped[str | None] = mapped_column(Text)
    new_fields: Mapped[str | None] = mapped_column(Text)
    sample_payload: Mapped[str | None] = mapped_column(Text)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        UtcDateTime, server_default=func.now(), nullable=False, index=True
    )
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __table_args__ = (
        UniqueConstraint("endpoint", "missing_fields", "new_fields", name="uq_drift"),
    )

