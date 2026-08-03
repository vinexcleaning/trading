"""Resilient HTTP client for public market-data endpoints.

Polymarket exposes no rate-limit headers, so this client self-throttles rather
than probing for the ceiling. Retries use exponential backoff with jitter and
only cover transient failures -- a 404 or a schema problem fails fast so it
surfaces as a real error instead of being silently retried away.
"""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from ..config import get_settings
from ..logging_setup import get_logger

log = get_logger(__name__)

# Transient statuses worth retrying. 429 is included; 4xx otherwise is not.
RETRY_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504, 522, 524})


class ProviderError(RuntimeError):
    """Base class for data-source failures."""


class RateLimitedError(ProviderError):
    """Upstream asked us to slow down."""


class NotFoundError(ProviderError):
    """Resource does not exist; retrying will not help."""


class SchemaError(ProviderError):
    """Response did not have the shape we require."""


@dataclass
class RequestStats:
    """Per-job counters surfaced in the health panel and ingestion_jobs rows."""

    requests: int = 0
    retries: int = 0
    rate_limit_events: int = 0
    total_latency_ms: int = 0
    failures: int = 0

    def merge(self, other: RequestStats) -> None:
        self.requests += other.requests
        self.retries += other.retries
        self.rate_limit_events += other.rate_limit_events
        self.total_latency_ms += other.total_latency_ms
        self.failures += other.failures


class RateLimiter:
    """Thread-safe token-bucket-ish pacer.

    A simple minimum-interval gate is sufficient here and, unlike a token
    bucket, cannot emit a burst that trips an unknown upstream limit.
    """

    def __init__(self, requests_per_second: float) -> None:
        self._min_interval = 1.0 / requests_per_second if requests_per_second > 0 else 0.0
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def acquire(self) -> None:
        if self._min_interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            wait = self._next_allowed - now
            if wait > 0:
                time.sleep(wait)
                now = time.monotonic()
            self._next_allowed = now + self._min_interval


@dataclass
class HttpClient:
    """Thin wrapper over httpx adding pacing, retries and stats."""

    timeout: float = field(default_factory=lambda: get_settings().http_timeout_seconds)
    max_retries: int = field(default_factory=lambda: get_settings().http_max_retries)
    backoff_base: float = field(
        default_factory=lambda: get_settings().http_backoff_base_seconds
    )
    backoff_max: float = field(
        default_factory=lambda: get_settings().http_backoff_max_seconds
    )
    user_agent: str = field(default_factory=lambda: get_settings().http_user_agent)
    rate_limiter: RateLimiter | None = None
    stats: RequestStats = field(default_factory=RequestStats)
    _client: httpx.Client | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.rate_limiter is None:
            self.rate_limiter = RateLimiter(get_settings().http_requests_per_second)

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=httpx.Timeout(self.timeout),
                headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                follow_redirects=True,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        *,
        allow_404: bool = False,
    ) -> Any:
        """GET returning parsed JSON.

        ``allow_404`` turns a missing resource into ``None`` instead of raising,
        which some optional endpoints (e.g. a book for a market with no orders)
        legitimately need.
        """
        last_exc: Exception | None = None

        for attempt in range(self.max_retries + 1):
            assert self.rate_limiter is not None
            self.rate_limiter.acquire()
            started = time.monotonic()
            try:
                response = self.client.get(url, params=params)
                elapsed_ms = int((time.monotonic() - started) * 1000)
                self.stats.requests += 1
                self.stats.total_latency_ms += elapsed_ms

                if response.status_code == 404:
                    if allow_404:
                        return None
                    raise NotFoundError(f"404 for {url}")

                if response.status_code == 429:
                    self.stats.rate_limit_events += 1
                    retry_after = self._retry_after(response)
                    if attempt >= self.max_retries:
                        raise RateLimitedError(f"429 exhausted retries for {url}")
                    log.warning(
                        "http.rate_limited", url=url, attempt=attempt, sleep_s=retry_after
                    )
                    self.stats.retries += 1
                    time.sleep(retry_after)
                    continue

                if response.status_code in RETRY_STATUSES:
                    if attempt >= self.max_retries:
                        self.stats.failures += 1
                        raise ProviderError(
                            f"HTTP {response.status_code} for {url} after "
                            f"{attempt + 1} attempts"
                        )
                    delay = self._backoff(attempt)
                    log.warning(
                        "http.retrying",
                        url=url,
                        status=response.status_code,
                        attempt=attempt,
                        sleep_s=round(delay, 2),
                    )
                    self.stats.retries += 1
                    time.sleep(delay)
                    continue

                if response.status_code >= 400:
                    self.stats.failures += 1
                    raise ProviderError(
                        f"HTTP {response.status_code} for {url}: {response.text[:200]}"
                    )

                try:
                    return response.json()
                except ValueError as exc:
                    self.stats.failures += 1
                    raise SchemaError(
                        f"Non-JSON response from {url}: {response.text[:200]}"
                    ) from exc

            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                last_exc = exc
                self.stats.requests += 1
                if attempt >= self.max_retries:
                    self.stats.failures += 1
                    raise ProviderError(f"Network failure for {url}: {exc}") from exc
                delay = self._backoff(attempt)
                log.warning(
                    "http.network_retry",
                    url=url,
                    error=str(exc),
                    attempt=attempt,
                    sleep_s=round(delay, 2),
                )
                self.stats.retries += 1
                time.sleep(delay)

        # Only reachable if the loop exits without returning or raising.
        raise ProviderError(f"Exhausted retries for {url}: {last_exc}")

    def _backoff(self, attempt: int) -> float:
        """Exponential backoff with full jitter, capped."""
        raw = min(self.backoff_base * (2**attempt), self.backoff_max)
        return raw * (0.5 + random.random() * 0.5)

    @staticmethod
    def _retry_after(response: httpx.Response) -> float:
        header = response.headers.get("Retry-After")
        if header:
            try:
                return min(float(header), 60.0)
            except ValueError:
                pass
        return 5.0
