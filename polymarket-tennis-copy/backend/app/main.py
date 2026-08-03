"""FastAPI application wiring.

Startup validates configuration and reports what it is actually connected to,
because the most expensive failure mode for this system is running happily
against the wrong database or with alerting silently disabled.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .api import (
    routes_backtest,
    routes_markets,
    routes_paper,
    routes_signals,
    routes_system,
    routes_wallets,
)
from .api.deps import DISCLAIMER
from .config import get_settings
from .logging_setup import bind_request_id, configure_logging, get_logger
from .scheduler import run_job_now, scheduler_status, shutdown_scheduler, start_scheduler

log = get_logger(__name__)

DESCRIPTION = f"""
Read-only analytics for Polymarket tennis wallets.

The question this API answers is **not** "did this wallet make money" but
"could a realistic follower have entered and exited these tennis trades in time
and still been profitable after delay, price deterioration, liquidity limits,
fees and slippage?"

**{DISCLAIMER}**

### Reading the numbers

* **Raw ROI** is what the wallet achieved. **Copyable ROI** is what a follower
  delayed by the benchmark delay would have achieved. Compare them.
* Copyable figures only count trades backed by real price evidence. Coverage is
  reported alongside every copyable number; a low coverage figure means the
  number rests on a subset of trades.
* Price evidence is tiered (`observed_trade` > `interpolated_trade` >
  `minute_bar` > `nearest_trade` > `modeled`). Polymarket's price history bottoms
  out at 1-minute fidelity, so sub-minute delays are answered from the trade tape
  where it exists and are labelled low-confidence where it does not.
* Rejected signals are kept and served. The rejection log is how alert
  thresholds get calibrated.

### Not implemented, by design

No real-money order placement. Paper trading is simulation only.
"""

TAGS_METADATA = [
    {"name": "wallets", "description": "Registry, sync, metrics, positions and rankings."},
    {"name": "markets", "description": "Tennis market search, detail and classification review."},
    {"name": "signals", "description": "Live signal feed, qualification detail and SSE stream."},
    {"name": "paper-trading", "description": "Simulated follower positions. No real orders."},
    {"name": "backtesting", "description": "Historical replay with look-ahead safeguards."},
    {"name": "system", "description": "Dashboard summaries, health, settings and reports."},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level, json_output=settings.log_json)

    from .db import get_engine

    engine = get_engine()
    log.info(
        "app.starting",
        environment=settings.app_env,
        database=engine.dialect.name,
        benchmark_delay_seconds=settings.benchmark_delay_seconds,
        notification_channels=settings.configured_notification_channels(),
        paper_trading=settings.paper_trading_enabled,
    )

    if settings.configured_notification_channels() == ["in_app"]:
        log.warning(
            "app.no_external_notifications",
            hint="Set DISCORD_WEBHOOK_URL or Telegram/SMTP variables to receive alerts",
        )

    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()
        log.info("app.stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, json_output=settings.log_json)

    app = FastAPI(
        title="Tennis Copy-Trade Intelligence",
        description=DESCRIPTION,
        version=routes_system.APP_VERSION,
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        bind_request_id(request_id)
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
        # Configuration and provider payload errors surface here; the message is
        # safe to return because settings never echo credential values.
        return JSONResponse(
            status_code=422,
            content={"detail": "validation error", "errors": exc.errors(include_url=False)},
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        log.exception("api.unhandled", path=str(request.url.path), request_id=request_id)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "internal server error",
                "request_id": request_id,
                "hint": "check server logs; the response omits internals on purpose",
            },
        )

    app.include_router(routes_wallets.router)
    app.include_router(routes_markets.router)
    app.include_router(routes_signals.router)
    app.include_router(routes_paper.router)
    app.include_router(routes_backtest.router)
    app.include_router(routes_system.router)

    jobs_router = APIRouter(prefix="/api/jobs", tags=["system"])

    @jobs_router.get("/status")
    def jobs_status() -> dict:
        """Scheduler inventory and last-run outcomes."""
        return scheduler_status()

    @jobs_router.post("/{job_id}/run")
    def trigger_job(job_id: str) -> dict:
        """Run one background job immediately."""
        try:
            return run_job_now(job_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc

    app.include_router(jobs_router)

    @app.get("/", tags=["system"])
    def root() -> dict:
        return {
            "name": "Tennis Copy-Trade Intelligence",
            "version": routes_system.APP_VERSION,
            "docs": "/docs",
            "openapi": "/openapi.json",
            "disclaimer": DISCLAIMER,
        }

    @app.get("/healthz", tags=["system"])
    def healthz() -> dict:
        """Container liveness probe. Does not touch the database."""
        return {"status": "ok"}

    return app


app = create_app()
