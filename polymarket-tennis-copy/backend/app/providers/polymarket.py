"""Polymarket provider.

Every endpoint and field used here was verified against the live APIs on
2026-07-29; see ``docs/API_VERIFICATION.md`` for the captured responses.

Endpoints used (all public, read-only, documented):
  gamma-api.polymarket.com  /events, /markets, /tags/slug/{slug}
  data-api.polymarket.com   /activity, /positions, /trades, /value, /holders
  clob.polymarket.com       /book, /midpoint, /spread, /prices-history
  lb-api.polymarket.com     /volume, /profit

Quirks this module absorbs:
  * ``outcomes`` / ``outcomePrices`` / ``clobTokenIds`` arrive as JSON-encoded
    *strings*, not arrays.
  * ``/activity`` caps ``limit`` at 500 regardless of what you ask for.
  * ``gameStartTime`` uses a non-ISO ``"2026-07-29 19:40:00+00"`` format.
  * ``/prices-history`` cannot go finer than 1-minute fidelity.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from ..config import get_settings
from ..logging_setup import get_logger
from .base import (
    MarketDataProvider,
    ProviderActivity,
    ProviderBookLevel,
    ProviderEvent,
    ProviderLeaderboardEntry,
    ProviderMarket,
    ProviderOrderBook,
    ProviderOutcome,
    ProviderPosition,
    ProviderPricePoint,
    ProviderTrade,
)
from .http import HttpClient, NotFoundError, ProviderError

log = get_logger(__name__)

# Fields we depend on. Their disappearance is a schema-drift event, not a crash.
EXPECTED_MARKET_FIELDS = frozenset(
    {"conditionId", "question", "outcomes", "clobTokenIds", "closed", "active"}
)
EXPECTED_ACTIVITY_FIELDS = frozenset(
    {"proxyWallet", "timestamp", "type", "size", "asset", "conditionId"}
)
EXPECTED_TRADE_FIELDS = frozenset(
    {"proxyWallet", "side", "asset", "conditionId", "size", "price", "timestamp"}
)

# Verified against the live API: /activity rejects offsets beyond this with
# HTTP 400 "max historical activity offset of 5000 exceeded". Offset pagination
# alone therefore cannot reach the full history of an active wallet, so the
# iterator re-anchors on a timestamp and restarts the offset when it gets close.
MAX_ACTIVITY_OFFSET = 5000


def _to_decimal(value: Any) -> Decimal | None:
    """Parse a venue numeric into Decimal via ``str`` to avoid float artifacts."""
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes")
    return default


def _parse_json_list(value: Any) -> list[Any]:
    """Gamma returns arrays as JSON strings; tolerate both encodings."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            return []
    return []


def parse_datetime(value: Any) -> datetime | None:
    """Parse the several timestamp shapes Polymarket emits.

    Handles ISO-8601 with ``Z``, plain ISO, the ``gameStartTime`` variant
    ``"2026-07-29 19:40:00+00"``, and unix epochs. Always returns tz-aware UTC so
    downstream comparisons cannot silently mix naive and aware datetimes.
    """
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    # "+00" is a valid-but-unusual offset that fromisoformat rejects on some
    # versions; normalise it to "+00:00".
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    elif len(text) > 3 and text[-3] in "+-" and text[-2:].isdigit():
        text = text + ":00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class PolymarketProvider(MarketDataProvider):
    """Read-only Polymarket public-data provider."""

    name = "polymarket"

    # Optional fields vary legitimately between records (a market with no trades
    # omits volume fields entirely), so a field-set baseline is only meaningful
    # after enough records to see that variation. Below this count we accumulate
    # quietly; above it, genuinely new fields are reported.
    SCHEMA_BASELINE_RECORDS = 50

    def __init__(self, client: HttpClient | None = None) -> None:
        self.settings = get_settings()
        self.http = client or HttpClient()
        # endpoint -> union of field names seen, for drift detection.
        self._observed_fields: dict[str, set[str]] = {}
        self._records_seen: dict[str, int] = {}
        self.drift_warnings: list[dict[str, Any]] = []

    # ------------------------------------------------------------------ util
    def close(self) -> None:
        self.http.close()

    def _check_schema(self, endpoint: str, payload: dict[str, Any], expected: frozenset[str]) -> None:
        """Record missing/new fields without failing the ingest.

        A hard failure here would take the pipeline down on a cosmetic upstream
        change; a silent pass would let wrong numbers through. Recording drift
        gets both: data keeps flowing and the operator is told.
        """
        keys = set(payload.keys())

        # A field we actively depend on going missing is the case that can
        # silently corrupt analytics, so it is always reported.
        missing = expected - keys
        if missing:
            warning = {"endpoint": endpoint, "missing_fields": sorted(missing)}
            if warning not in self.drift_warnings:
                self.drift_warnings.append(warning)
                log.warning("provider.schema_drift", **warning)

        count = self._records_seen.get(endpoint, 0) + 1
        self._records_seen[endpoint] = count
        baseline = self._observed_fields.setdefault(endpoint, set())

        if count <= self.SCHEMA_BASELINE_RECORDS:
            baseline |= keys
            return

        new = keys - baseline
        if new:
            warning = {"endpoint": endpoint, "new_fields": sorted(new)}
            if warning not in self.drift_warnings:
                self.drift_warnings.append(warning)
                log.info("provider.new_fields", **warning)
            baseline |= new

    # --------------------------------------------------------------- markets
    def _parse_market(
        self, raw: dict[str, Any], event_ctx: dict[str, Any] | None = None
    ) -> ProviderMarket | None:
        self._check_schema("gamma/markets", raw, EXPECTED_MARKET_FIELDS)

        condition_id = raw.get("conditionId")
        if not condition_id:
            # Without a condition id the market cannot be joined to activity.
            return None

        labels = [str(x) for x in _parse_json_list(raw.get("outcomes"))]
        token_ids = [str(x) for x in _parse_json_list(raw.get("clobTokenIds"))]
        prices = [_to_decimal(x) for x in _parse_json_list(raw.get("outcomePrices"))]

        outcomes: list[ProviderOutcome] = []
        for idx, token_id in enumerate(token_ids):
            outcomes.append(
                ProviderOutcome(
                    token_id=token_id,
                    outcome_index=idx,
                    label=labels[idx] if idx < len(labels) else f"Outcome {idx}",
                    price=prices[idx] if idx < len(prices) else None,
                )
            )

        closed = _to_bool(raw.get("closed"))
        # A closed market resolves to whichever outcome price settled at 1.
        winning_index: int | None = None
        if closed and prices:
            for idx, price in enumerate(prices):
                if price is not None and price >= Decimal("0.99"):
                    winning_index = idx
                    break

        # Events may arrive nested on the market, or be supplied as context when
        # the market was reached via /events.
        event_id = None
        event_slug = None
        event_title = None
        tags: list[str] = []
        nested_events = raw.get("events")
        if isinstance(nested_events, list) and nested_events:
            ev = nested_events[0]
            if isinstance(ev, dict):
                event_id = str(ev.get("id")) if ev.get("id") is not None else None
                event_slug = ev.get("slug")
                event_title = ev.get("title")
                tags = [
                    str(t.get("slug"))
                    for t in ev.get("tags", []) or []
                    if isinstance(t, dict) and t.get("slug")
                ]
        if event_ctx:
            event_id = event_ctx.get("event_id") or event_id
            event_slug = event_ctx.get("event_slug") or event_slug
            event_title = event_ctx.get("event_title") or event_title
            tags = event_ctx.get("tags") or tags

        fee_schedule = raw.get("feeSchedule") or {}
        taker_bps: int | None = _to_int(raw.get("takerBaseFee"))
        if taker_bps is None and isinstance(fee_schedule, dict):
            rate = _to_decimal(fee_schedule.get("rate"))
            if rate is not None:
                taker_bps = int(rate * Decimal("10000"))

        return ProviderMarket(
            condition_id=str(condition_id),
            outcomes=outcomes,
            gamma_market_id=str(raw["id"]) if raw.get("id") is not None else None,
            question_id=raw.get("questionID"),
            slug=raw.get("slug"),
            question=raw.get("question"),
            description=raw.get("description"),
            event_id=event_id,
            event_slug=event_slug,
            event_title=event_title,
            tags=tags,
            sports_market_type=raw.get("sportsMarketType"),
            game_start_time=parse_datetime(raw.get("gameStartTime")),
            start_date=parse_datetime(raw.get("startDate") or raw.get("startDateIso")),
            end_date=parse_datetime(raw.get("endDate") or raw.get("endDateIso")),
            active=_to_bool(raw.get("active"), True),
            closed=closed,
            archived=_to_bool(raw.get("archived")),
            accepting_orders=_to_bool(raw.get("acceptingOrders"), True),
            enable_order_book=_to_bool(raw.get("enableOrderBook"), True),
            neg_risk=_to_bool(raw.get("negRisk")),
            resolved=closed and winning_index is not None,
            winning_outcome_index=winning_index,
            uma_resolution_statuses=(
                json.dumps(_parse_json_list(raw.get("umaResolutionStatuses")))
                if raw.get("umaResolutionStatuses")
                else None
            ),
            liquidity=_to_decimal(raw.get("liquidityNum") or raw.get("liquidity")),
            volume=_to_decimal(raw.get("volumeNum") or raw.get("volume")),
            volume_24hr=_to_decimal(raw.get("volume24hr")),
            spread=_to_decimal(raw.get("spread")),
            best_bid=_to_decimal(raw.get("bestBid")),
            best_ask=_to_decimal(raw.get("bestAsk")),
            last_trade_price=_to_decimal(raw.get("lastTradePrice")),
            tick_size=_to_decimal(raw.get("orderPriceMinTickSize")),
            min_order_size=_to_decimal(raw.get("orderMinSize")),
            maker_fee_bps=_to_int(raw.get("makerBaseFee")),
            taker_fee_bps=taker_bps,
            raw=raw,
        )

    def _parse_event(self, raw: dict[str, Any]) -> ProviderEvent:
        tags = [
            str(t.get("slug"))
            for t in raw.get("tags", []) or []
            if isinstance(t, dict) and t.get("slug")
        ]
        event_id = str(raw.get("id"))
        ctx = {
            "event_id": event_id,
            "event_slug": raw.get("slug"),
            "event_title": raw.get("title"),
            "tags": tags,
        }
        markets = []
        for m in raw.get("markets", []) or []:
            if isinstance(m, dict):
                parsed = self._parse_market(m, event_ctx=ctx)
                if parsed is not None:
                    markets.append(parsed)

        return ProviderEvent(
            event_id=event_id,
            slug=raw.get("slug"),
            ticker=raw.get("ticker"),
            title=raw.get("title"),
            description=raw.get("description"),
            tags=tags,
            start_date=parse_datetime(raw.get("startDate")),
            end_date=parse_datetime(raw.get("endDate")),
            active=_to_bool(raw.get("active"), True),
            closed=_to_bool(raw.get("closed")),
            liquidity=_to_decimal(raw.get("liquidity")),
            volume=_to_decimal(raw.get("volume")),
            volume_24hr=_to_decimal(raw.get("volume24hr")),
            markets=markets,
            raw=raw,
        )

    def iter_events(
        self,
        *,
        tag_id: int | None = None,
        closed: bool | None = None,
        limit: int = 100,
        max_pages: int | None = None,
        start_date_min: datetime | None = None,
    ) -> Iterator[ProviderEvent]:
        url = f"{self.settings.gamma_base_url}/events"
        offset = 0
        pages = 0

        while True:
            params: dict[str, Any] = {
                "limit": limit,
                "offset": offset,
                "order": "startDate",
                "ascending": "false",
            }
            if tag_id is not None:
                params["tag_id"] = tag_id
            if closed is not None:
                params["closed"] = str(closed).lower()
            if start_date_min is not None:
                params["start_date_min"] = start_date_min.strftime("%Y-%m-%dT%H:%M:%SZ")

            payload = self.http.get_json(url, params=params)
            if not isinstance(payload, list):
                raise ProviderError(f"Expected list from /events, got {type(payload).__name__}")
            if not payload:
                return

            for raw in payload:
                if isinstance(raw, dict):
                    yield self._parse_event(raw)

            pages += 1
            if len(payload) < limit:
                return
            if max_pages is not None and pages >= max_pages:
                return
            offset += limit

    def _parse_clob_market(self, raw: dict[str, Any]) -> ProviderMarket | None:
        """Parse the CLOB ``/markets/{condition_id}`` shape.

        A different payload from Gamma's: snake_case, ``tokens[]`` instead of
        parallel arrays, capitalised tag labels, and ``winner`` per token. It
        carries no liquidity/volume/spread -- those are Gamma-only and are left
        unset rather than guessed.
        """
        condition_id = raw.get("condition_id")
        if not condition_id:
            return None

        outcomes: list[ProviderOutcome] = []
        winning_index: int | None = None
        for index, token in enumerate(raw.get("tokens", []) or []):
            if not isinstance(token, dict):
                continue
            token_id = token.get("token_id")
            if not token_id:
                continue
            outcomes.append(
                ProviderOutcome(
                    token_id=str(token_id),
                    outcome_index=index,
                    label=str(token.get("outcome") or f"Outcome {index}"),
                    price=_to_decimal(token.get("price")),
                )
            )
            if _to_bool(token.get("winner")):
                winning_index = index

        closed = _to_bool(raw.get("closed"))
        fee_bps = _to_int(raw.get("taker_base_fee"))

        return ProviderMarket(
            condition_id=str(condition_id),
            outcomes=outcomes,
            question_id=raw.get("question_id"),
            slug=raw.get("market_slug"),
            question=raw.get("question"),
            description=raw.get("description"),
            # CLOB tags are display labels ("Tennis"); the classifier lowercases.
            tags=[str(t) for t in (raw.get("tags") or [])],
            game_start_time=parse_datetime(raw.get("game_start_time")),
            end_date=parse_datetime(raw.get("end_date_iso")),
            active=_to_bool(raw.get("active"), True),
            closed=closed,
            archived=_to_bool(raw.get("archived")),
            accepting_orders=_to_bool(raw.get("accepting_orders"), True),
            enable_order_book=_to_bool(raw.get("enable_order_book"), True),
            neg_risk=_to_bool(raw.get("neg_risk")),
            resolved=closed and winning_index is not None,
            winning_outcome_index=winning_index,
            tick_size=_to_decimal(raw.get("minimum_tick_size")),
            min_order_size=_to_decimal(raw.get("minimum_order_size")),
            maker_fee_bps=_to_int(raw.get("maker_base_fee")),
            taker_fee_bps=fee_bps,
            raw=raw,
        )

    def get_market(self, condition_id: str) -> ProviderMarket | None:
        """Look up a single market by condition id.

        Uses the CLOB endpoint, which is the only verified correct lookup.
        Gamma's ``/markets`` silently ignores every condition-id parameter
        spelling tried (``condition_ids``, ``conditionId``, ``condition_ids[]``,
        ...) and returns either an empty list or -- worse -- an unrelated default
        page of markets. Trusting that would attach wrong metadata to
        transactions, so it is deliberately not used here. CLOB returns a proper
        404 for an unknown condition instead of wrong data.
        """
        payload = self.http.get_json(
            f"{self.settings.clob_base_url}/markets/{condition_id}", allow_404=True
        )
        if not isinstance(payload, dict):
            return None

        parsed = self._parse_clob_market(payload)
        # Defensive: never accept a market that is not the one requested.
        if parsed is not None and parsed.condition_id != condition_id:
            log.warning(
                "provider.condition_id_mismatch",
                requested=condition_id,
                returned=parsed.condition_id,
            )
            return None
        return parsed

    def get_markets_by_condition_ids(self, condition_ids: list[str]) -> list[ProviderMarket]:
        """Look up several markets by condition id.

        No verified batch-by-id endpoint exists, so this issues one paced request
        per id. Callers should pass only the ids they are missing.
        """
        results: list[ProviderMarket] = []
        for condition_id in condition_ids:
            try:
                market = self.get_market(condition_id)
            except ProviderError as exc:
                log.warning(
                    "provider.market_lookup_failed",
                    condition_id=condition_id,
                    error=str(exc),
                )
                continue
            if market is not None:
                results.append(market)
        return results

    # ---------------------------------------------------------------- wallets
    def _parse_activity(self, raw: dict[str, Any]) -> ProviderActivity | None:
        self._check_schema("data/activity", raw, EXPECTED_ACTIVITY_FIELDS)

        wallet = raw.get("proxyWallet")
        ts = _to_int(raw.get("timestamp"))
        if not wallet or ts is None:
            return None

        size = _to_decimal(raw.get("size")) or Decimal("0")
        price = _to_decimal(raw.get("price"))
        tx_hash = raw.get("transactionHash")
        asset = raw.get("asset")
        side = raw.get("side")
        activity_type = str(raw.get("type") or "UNKNOWN").upper()

        # One tx hash may hold several fills, so the key spans the fields that
        # actually distinguish them.
        dedupe_key = "|".join(
            [
                str(tx_hash or ""),
                str(asset or ""),
                str(side or ""),
                activity_type,
                f"{size:f}",
                f"{price:f}" if price is not None else "",
                str(ts),
            ]
        )

        return ProviderActivity(
            wallet_address=str(wallet).lower(),
            activity_type=activity_type,
            timestamp=ts,
            dedupe_key=dedupe_key,
            size=size,
            condition_id=raw.get("conditionId"),
            token_id=str(asset) if asset else None,
            outcome_index=_to_int(raw.get("outcomeIndex")),
            outcome_label=raw.get("outcome"),
            side=str(side).upper() if side else None,
            price=price,
            usdc_size=_to_decimal(raw.get("usdcSize")),
            transaction_hash=str(tx_hash) if tx_hash else None,
            title=raw.get("title"),
            slug=raw.get("slug"),
            event_slug=raw.get("eventSlug"),
            raw=raw,
        )

    def iter_wallet_activity(
        self,
        wallet_address: str,
        *,
        start_ts: int | None = None,
        end_ts: int | None = None,
        max_pages: int | None = None,
    ) -> Iterator[ProviderActivity]:
        """Yield activity oldest-first.

        Ascending order matters: reconstruction consumes events chronologically,
        and an incremental sync that walks forward from a cursor cannot miss rows
        inserted mid-pagination the way a descending walk can.
        """
        url = f"{self.settings.data_api_base_url}/activity"
        page_size = self.settings.activity_page_size
        offset = 0
        pages = 0
        seen_keys: set[str] = set()
        cursor_ts = start_ts
        latest_ts: int | None = None

        while True:
            params: dict[str, Any] = {
                "user": wallet_address,
                "limit": page_size,
                "offset": offset,
                "sortBy": "TIMESTAMP",
                "sortDirection": "ASC",
            }
            if cursor_ts is not None:
                params["start"] = cursor_ts
            if end_ts is not None:
                params["end"] = end_ts

            payload = self.http.get_json(url, params=params)
            if not isinstance(payload, list):
                raise ProviderError(
                    f"Expected list from /activity, got {type(payload).__name__}"
                )
            if not payload:
                return

            fresh = 0
            for raw in payload:
                if not isinstance(raw, dict):
                    continue
                parsed = self._parse_activity(raw)
                # Guard against overlapping pages producing duplicates within a
                # single sync run.
                if parsed is not None and parsed.dedupe_key not in seen_keys:
                    seen_keys.add(parsed.dedupe_key)
                    fresh += 1
                    if latest_ts is None or parsed.timestamp > latest_ts:
                        latest_ts = parsed.timestamp
                    yield parsed

            pages += 1
            if len(payload) < page_size:
                return
            if max_pages is not None and pages >= max_pages:
                log.warning(
                    "provider.activity_page_cap",
                    wallet=wallet_address,
                    pages=pages,
                    note="stopped at max_pages; history may be incomplete",
                )
                return

            offset += page_size

            # Verified limit: the API rejects offsets past 5000 with HTTP 400
            # ("max historical activity offset exceeded"). Paging alone therefore
            # cannot reach the full history of an active wallet. Re-anchor on the
            # newest timestamp seen and restart the offset, which walks forward
            # through time in 5000-row windows instead.
            if offset + page_size > MAX_ACTIVITY_OFFSET:
                if latest_ts is None or fresh == 0:
                    # No forward progress -- either nothing new arrived or a
                    # single timestamp exceeds the window. Stop rather than loop.
                    log.warning(
                        "provider.activity_window_stalled",
                        wallet=wallet_address,
                        note="could not advance past the offset cap; history may be incomplete",
                    )
                    return
                log.info(
                    "provider.activity_rewindow",
                    wallet=wallet_address,
                    resume_from_ts=latest_ts,
                )
                cursor_ts = latest_ts
                offset = 0

    def get_wallet_positions(
        self, wallet_address: str, *, max_pages: int = 10
    ) -> list[ProviderPosition]:
        """All open positions, paginated.

        Active wallets exceed one page (500), and a truncated read would make a
        wallet look flat in markets it still holds -- which would corrupt the
        "has this wallet begun exiting?" check that alerting depends on.
        """
        url = f"{self.settings.data_api_base_url}/positions"
        page_size = 500
        offset = 0
        out: list[ProviderPosition] = []

        for _ in range(max_pages):
            payload = self.http.get_json(
                url,
                params={"user": wallet_address, "limit": page_size, "offset": offset},
                allow_404=True,
            )
            if not isinstance(payload, list) or not payload:
                break

            for raw in payload:
                if not isinstance(raw, dict):
                    continue
                token_id = raw.get("asset")
                condition_id = raw.get("conditionId")
                if not token_id or not condition_id:
                    continue
                out.append(
                    ProviderPosition(
                        wallet_address=str(wallet_address).lower(),
                        token_id=str(token_id),
                        condition_id=str(condition_id),
                        size=_to_decimal(raw.get("size")) or Decimal("0"),
                        avg_price=_to_decimal(raw.get("avgPrice")),
                        initial_value=_to_decimal(raw.get("initialValue")),
                        current_value=_to_decimal(raw.get("currentValue")),
                        cash_pnl=_to_decimal(raw.get("cashPnl")),
                        realized_pnl=_to_decimal(raw.get("realizedPnl")),
                        total_bought=_to_decimal(raw.get("totalBought")),
                        current_price=_to_decimal(raw.get("curPrice")),
                        outcome_index=_to_int(raw.get("outcomeIndex")),
                        outcome_label=raw.get("outcome"),
                        redeemable=_to_bool(raw.get("redeemable")),
                        title=raw.get("title"),
                        raw=raw,
                    )
                )

            if len(payload) < page_size:
                break
            offset += page_size

        return out

    def get_wallet_value(self, wallet_address: str) -> Decimal | None:
        payload = self.http.get_json(
            f"{self.settings.data_api_base_url}/value",
            params={"user": wallet_address},
            allow_404=True,
        )
        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
            return _to_decimal(payload[0].get("value"))
        if isinstance(payload, dict):
            return _to_decimal(payload.get("value"))
        return None

    # ----------------------------------------------------------------- prices
    def get_market_trades(
        self, condition_id: str, *, limit: int = 500, max_pages: int | None = None
    ) -> list[ProviderTrade]:
        url = f"{self.settings.data_api_base_url}/trades"
        out: list[ProviderTrade] = []
        offset = 0
        pages = 0
        page_size = min(limit, 1000)

        while True:
            payload = self.http.get_json(
                url,
                params={
                    "market": condition_id,
                    "limit": page_size,
                    "offset": offset,
                    "takerOnly": "false",
                },
                allow_404=True,
            )
            if not isinstance(payload, list) or not payload:
                break

            for raw in payload:
                if not isinstance(raw, dict):
                    continue
                self._check_schema("data/trades", raw, EXPECTED_TRADE_FIELDS)
                token_id = raw.get("asset")
                ts = _to_int(raw.get("timestamp"))
                price = _to_decimal(raw.get("price"))
                if not token_id or ts is None or price is None:
                    continue
                out.append(
                    ProviderTrade(
                        token_id=str(token_id),
                        condition_id=str(raw.get("conditionId") or condition_id),
                        timestamp=ts,
                        price=price,
                        size=_to_decimal(raw.get("size")) or Decimal("0"),
                        side=str(raw["side"]).upper() if raw.get("side") else None,
                        wallet_address=(
                            str(raw["proxyWallet"]).lower() if raw.get("proxyWallet") else None
                        ),
                        outcome_index=_to_int(raw.get("outcomeIndex")),
                        transaction_hash=raw.get("transactionHash"),
                        raw=raw,
                    )
                )

            pages += 1
            if len(payload) < page_size:
                break
            if max_pages is not None and pages >= max_pages:
                break
            offset += page_size

        return out

    # Verified 2026-07-29: /prices-history rejects fidelities finer than these for
    # each named interval with HTTP 400 ("minimum 'fidelity' for '1w' range is 5").
    # An explicit startTs/endTs window is NOT subject to these minimums and will
    # return 1-minute data over spans of a week or more, so windowed requests are
    # preferred whenever the caller knows the range it needs.
    INTERVAL_MIN_FIDELITY: dict[str, int] = {
        "1h": 1,
        "6h": 1,
        "1d": 1,
        "1w": 5,
        "1m": 10,
        "max": 1,
    }

    def get_price_history(
        self,
        token_id: str,
        *,
        interval: str = "1d",
        fidelity_minutes: int = 1,
        start_ts: int | None = None,
        end_ts: int | None = None,
    ) -> list[ProviderPricePoint]:
        """Historical series from CLOB.

        Fidelity is in minutes and **1 minute is the venue floor** -- no sub-minute
        history exists at any interval. That is precisely why the price resolver
        treats these points as weaker evidence than trade prints, and why
        sub-minute follower delays cannot be answered from this source.

        Pass ``start_ts``/``end_ts`` to get the finest available resolution over an
        arbitrary span; the named-interval form is clamped to the venue's minimum
        fidelity for that interval and the effective value is reported on each point.
        """
        requested = max(1, fidelity_minutes)
        params: dict[str, Any] = {"market": token_id}

        # ``interval`` and explicit start/end are mutually exclusive upstream.
        if start_ts is not None and end_ts is not None:
            effective = requested
            params["startTs"] = start_ts
            params["endTs"] = end_ts
        else:
            minimum = self.INTERVAL_MIN_FIDELITY.get(interval, 1)
            effective = max(requested, minimum)
            if effective != requested:
                log.debug(
                    "provider.fidelity_clamped",
                    interval=interval,
                    requested=requested,
                    effective=effective,
                    reason="venue minimum for this interval",
                )
            params["interval"] = interval

        params["fidelity"] = effective

        try:
            payload = self.http.get_json(
                f"{self.settings.clob_base_url}/prices-history", params=params, allow_404=True
            )
        except NotFoundError:
            return []
        if not isinstance(payload, dict):
            return []

        out: list[ProviderPricePoint] = []
        for point in payload.get("history", []) or []:
            if not isinstance(point, dict):
                continue
            ts = _to_int(point.get("t"))
            price = _to_decimal(point.get("p"))
            if ts is None or price is None:
                continue
            out.append(
                ProviderPricePoint(
                    token_id=token_id,
                    timestamp=ts,
                    price=price,
                    # The effective fidelity, not the requested one, so downstream
                    # confidence reflects what was actually returned.
                    fidelity_minutes=effective,
                )
            )
        out.sort(key=lambda p: p.timestamp)
        return out

    def get_order_book(self, token_id: str) -> ProviderOrderBook | None:
        payload = self.http.get_json(
            f"{self.settings.clob_base_url}/book",
            params={"token_id": token_id},
            allow_404=True,
        )
        if not isinstance(payload, dict):
            return None

        def levels(key: str) -> list[ProviderBookLevel]:
            out: list[ProviderBookLevel] = []
            for lvl in payload.get(key, []) or []:
                if not isinstance(lvl, dict):
                    continue
                price = _to_decimal(lvl.get("price"))
                size = _to_decimal(lvl.get("size"))
                if price is not None and size is not None and size > 0:
                    out.append(ProviderBookLevel(price=price, size=size))
            return out

        ts_raw = _to_int(payload.get("timestamp"))
        # CLOB book timestamps are milliseconds.
        ts = int(ts_raw / 1000) if ts_raw and ts_raw > 1_000_000_000_000 else (
            ts_raw or int(datetime.now(timezone.utc).timestamp())
        )

        return ProviderOrderBook(
            token_id=token_id,
            timestamp=ts,
            bids=levels("bids"),
            asks=levels("asks"),
            tick_size=_to_decimal(payload.get("tick_size")),
            min_order_size=_to_decimal(payload.get("min_order_size")),
            neg_risk=_to_bool(payload.get("neg_risk")),
            last_trade_price=_to_decimal(payload.get("last_trade_price")),
            raw=payload,
        )

    def get_midpoint(self, token_id: str) -> Decimal | None:
        payload = self.http.get_json(
            f"{self.settings.clob_base_url}/midpoint",
            params={"token_id": token_id},
            allow_404=True,
        )
        if isinstance(payload, dict):
            return _to_decimal(payload.get("mid"))
        return None

    # -------------------------------------------------------------- discovery
    def get_leaderboard(
        self, *, metric: str = "volume", window: str = "30d", limit: int = 50
    ) -> list[ProviderLeaderboardEntry]:
        """Public leaderboard.

        Verified: ``/volume`` and ``/profit`` respond; ``/leaderboard`` returns
        404. Entries are *candidates only* -- a leaderboard position says nothing
        about tennis skill or copyability.
        """
        path = "profit" if metric.lower().startswith("profit") else "volume"
        payload = self.http.get_json(
            f"{self.settings.leaderboard_base_url}/{path}",
            params={"window": window, "limit": limit},
            allow_404=True,
        )
        if not isinstance(payload, list):
            return []

        out: list[ProviderLeaderboardEntry] = []
        for raw in payload:
            if not isinstance(raw, dict):
                continue
            wallet = raw.get("proxyWallet")
            if not wallet:
                continue
            out.append(
                ProviderLeaderboardEntry(
                    wallet_address=str(wallet).lower(),
                    amount=_to_decimal(raw.get("amount")) or Decimal("0"),
                    metric=path,
                    window=window,
                    pseudonym=raw.get("pseudonym"),
                    name=raw.get("name"),
                )
            )
        return out

    def get_market_holders(self, condition_id: str, limit: int = 100) -> list[str]:
        """Wallet addresses currently holding a market's tokens (candidates)."""
        payload = self.http.get_json(
            f"{self.settings.data_api_base_url}/holders",
            params={"market": condition_id, "limit": limit},
            allow_404=True,
        )
        addresses: list[str] = []
        if isinstance(payload, list):
            for group in payload:
                if not isinstance(group, dict):
                    continue
                for holder in group.get("holders", []) or []:
                    if isinstance(holder, dict) and holder.get("proxyWallet"):
                        addresses.append(str(holder["proxyWallet"]).lower())
        # Preserve first-seen order while removing duplicates.
        return list(dict.fromkeys(addresses))
