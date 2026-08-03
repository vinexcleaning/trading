"""Read-only Kalshi public API client.

HARD RULE: this module must never gain an order-placement method. Only GETs
against public market-data endpoints. No credentials are used or accepted.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Iterator

import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"

# Measured in Phase 0 on 2026-07-30 against uncacheable per-market orderbook URLs:
#   15 req/s sustained -> 0% 429   |   25 req/s -> 56% 429
# Budget well under the wall so recorders can run for hours unattended.
DEFAULT_RPS = 8.0


class RateLimiter:
    def __init__(self, rps: float) -> None:
        self._interval = 1.0 / rps
        self._lock = threading.Lock()
        self._next = time.monotonic()

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            if self._next < now:
                self._next = now
            wait = self._next - now
            self._next += self._interval
        if wait > 0:
            time.sleep(wait)


class KalshiPublicClient:
    """Read-only client. Every method is a GET."""

    def __init__(self, rps: float = DEFAULT_RPS, timeout: float = 20.0) -> None:
        self._s = requests.Session()
        self._s.headers.update({"User-Agent": "kalshi-research-readonly/0.1"})
        self._limiter = RateLimiter(rps)
        self._timeout = timeout
        self.n_429 = 0
        self.n_req = 0

    def get(self, path: str, params: dict[str, Any] | None = None, retries: int = 4) -> dict:
        url = f"{BASE}{path}"
        backoff = 0.5
        for attempt in range(retries + 1):
            self._limiter.acquire()
            self.n_req += 1
            try:
                r = self._s.get(url, params=params, timeout=self._timeout)
            except requests.RequestException:
                if attempt == retries:
                    raise
                time.sleep(backoff)
                backoff *= 2
                continue
            if r.status_code == 429:
                self.n_429 += 1
                if attempt == retries:
                    r.raise_for_status()
                time.sleep(backoff)
                backoff *= 2
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError("unreachable")

    def paginate(
        self, path: str, key: str, params: dict[str, Any] | None = None, max_pages: int = 10_000
    ) -> Iterator[dict]:
        params = dict(params or {})
        params.setdefault("limit", 200)
        cursor = None
        for _ in range(max_pages):
            if cursor:
                params["cursor"] = cursor
            d = self.get(path, params)
            rows = d.get(key) or []
            for row in rows:
                yield row
            cursor = d.get("cursor")
            if not cursor or not rows:
                return

    # --- market data ---------------------------------------------------
    def series_list(self, category: str | None = None) -> list[dict]:
        params = {"category": category} if category else None
        return self.get("/series", params).get("series") or []

    def series(self, ticker: str) -> dict:
        return self.get(f"/series/{ticker}").get("series") or {}

    def markets(self, **params: Any) -> Iterator[dict]:
        return self.paginate("/markets", "markets", params)

    def orderbook(self, ticker: str) -> dict:
        """Return the book side-map: {"yes_dollars": [[px, sz], ...], "no_dollars": ...}.

        The response nests this under `orderbook_fp` at the top level -- there is no
        `orderbook` key. Getting this wrong returns {} for every market silently.
        """
        d = self.get(f"/markets/{ticker}/orderbook")
        return d.get("orderbook_fp") or d.get("orderbook") or {}

    def trades(self, **params: Any) -> Iterator[dict]:
        return self.paginate("/markets/trades", "trades", params)

    def events(self, **params: Any) -> Iterator[dict]:
        return self.paginate("/events", "events", params)


CATEGORIES = [
    "Politics",
    "Sports",
    "Culture",
    "Crypto",
    "Climate",
    "Economics",
    "Companies",
    "Financials",
    "Health",
    "World",
    "Transportation",
    "Science and Technology",
]
