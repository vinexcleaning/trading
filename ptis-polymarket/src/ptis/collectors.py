from __future__ import annotations

import hashlib
import json
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .api import PublicApiClient
from .database import connect, initialize

DATA_API = "https://data-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


def _save_raw(raw_dir: Path, source: str, payload: Any, collected_at: datetime) -> Path:
    day_dir = raw_dir / source / collected_at.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]
    path = day_dir / f"{collected_at.strftime('%H%M%S_%f')}Z_{digest}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _unix_timestamp_to_utc(value: Any) -> str:
    timestamp = float(value)
    if timestamp > 10_000_000_000:
        timestamp /= 1000
    return _iso(datetime.fromtimestamp(timestamp, tz=timezone.utc))


def trade_key(row: dict[str, Any]) -> str:
    """Build a repeatable key from fields preserved by the public Trades API."""
    identity = {
        "transactionHash": row.get("transactionHash"),
        "proxyWallet": str(row.get("proxyWallet", "")).lower(),
        "asset": str(row.get("asset", "")),
        "conditionId": str(row.get("conditionId", "")),
        "side": str(row.get("side", "")).upper(),
        "size": str(row.get("size", "")),
        "price": str(row.get("price", "")),
        "timestamp": str(row.get("timestamp", "")),
    }
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_trade(row: dict[str, Any], expected_wallet: str) -> None:
    required = ("proxyWallet", "side", "asset", "conditionId", "size", "price", "timestamp")
    missing = [field for field in required if row.get(field) is None]
    if missing:
        raise ValueError(f"trade is missing required fields: {', '.join(missing)}")
    if str(row["proxyWallet"]).lower() != expected_wallet:
        raise ValueError("trade response contains an unexpected wallet")
    if str(row["side"]).upper() not in {"BUY", "SELL"}:
        raise ValueError(f"invalid trade side: {row['side']}")
    price = float(row["price"])
    size = float(row["size"])
    if not 0 <= price <= 1:
        raise ValueError(f"trade price outside [0, 1]: {price}")
    if size < 0:
        raise ValueError(f"negative trade size: {size}")
    _unix_timestamp_to_utc(row["timestamp"])


def _store_trade_rows(
    database_path: Path,
    *,
    wallet: str | None,
    rows: list[dict[str, Any]],
    received_at: datetime,
    raw_path: Path,
) -> list[str]:
    inserted_keys: list[str] = []
    with closing(connect(database_path)) as connection:
        for row in rows:
            row_wallet = str(row.get("proxyWallet", "")).lower()
            if wallet is not None:
                _validate_trade(row, wallet)
                row_wallet = wallet
            else:
                if not row_wallet.startswith("0x") or len(row_wallet) != 42:
                    raise ValueError("market trade contains an invalid wallet")
                _validate_trade(row, row_wallet)
            connection.execute(
                """INSERT INTO traders
                   (proxy_wallet, username, first_observed_at_utc, last_observed_at_utc)
                   VALUES (?, NULL, ?, ?)
                   ON CONFLICT(proxy_wallet) DO UPDATE SET
                       last_observed_at_utc=excluded.last_observed_at_utc""",
                (row_wallet, _iso(received_at), _iso(received_at)),
            )
            key = trade_key(row)
            result = connection.execute(
                """INSERT OR IGNORE INTO public_trades
                   (trade_key, proxy_wallet, condition_id, token_id, side,
                    size_shares, price, executed_at_utc, transaction_hash,
                    source_name, ingested_at_utc, raw_file_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    key,
                    row_wallet,
                    str(row["conditionId"]),
                    str(row["asset"]),
                    str(row["side"]).upper(),
                    float(row["size"]),
                    float(row["price"]),
                    _unix_timestamp_to_utc(row["timestamp"]),
                    row.get("transactionHash"),
                    "Polymarket Data API",
                    _iso(received_at),
                    str(raw_path),
                ),
            )
            if result.rowcount:
                inserted_keys.append(key)
        connection.commit()
    return inserted_keys


def ingest_market_trade_tape(
    client: PublicApiClient,
    database_path: Path,
    raw_dir: Path,
    *,
    condition_id: str,
    page_size: int = 500,
    max_pages: int = 4,
) -> tuple[int, int]:
    """Archive a bounded public trade tape for one market."""
    initialize(database_path)
    downloaded = 0
    inserted = 0
    for page in range(max_pages):
        received_at = utc_now()
        payload = client.get_json(
            DATA_API,
            "/trades",
            {
                "market": condition_id,
                "limit": page_size,
                "offset": page * page_size,
                "takerOnly": "false",
            },
        )
        if not isinstance(payload, list):
            raise ValueError("market trade endpoint returned a non-list response")
        raw_path = _save_raw(raw_dir, "data_api_market_tape", payload, received_at)
        downloaded += len(payload)
        inserted += len(
            _store_trade_rows(
                database_path,
                wallet=None,
                rows=payload,
                received_at=received_at,
                raw_path=raw_path,
            )
        )
        if len(payload) < page_size:
            break
    return downloaded, inserted


def poll_wallet_trades(
    client: PublicApiClient,
    database_path: Path,
    raw_dir: Path,
    *,
    wallet: str,
    limit: int = 100,
) -> tuple[datetime, list[tuple[str, dict[str, Any]]]]:
    normalized_wallet = wallet.lower()
    if not normalized_wallet.startswith("0x") or len(normalized_wallet) != 42:
        raise ValueError("wallet must be a 0x-prefixed 40-byte address")
    received_at = utc_now()
    payload = client.get_json(
        DATA_API,
        "/trades",
        {
            "user": normalized_wallet,
            "limit": limit,
            "offset": 0,
            "takerOnly": "false",
        },
    )
    if not isinstance(payload, list):
        raise ValueError("trade endpoint returned a non-list response")
    raw_path = _save_raw(raw_dir, "data_api_live_poll", payload, received_at)
    _store_trade_rows(
        database_path,
        wallet=normalized_wallet,
        rows=payload,
        received_at=received_at,
        raw_path=raw_path,
    )
    return received_at, [(trade_key(row), row) for row in payload]


def _json_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        decoded = json.loads(value)
        if isinstance(decoded, list):
            return decoded
    raise ValueError("expected a JSON list")


def discover_candidates(
    client: PublicApiClient,
    database_path: Path,
    raw_dir: Path,
    *,
    limit: int,
    category: str = "OVERALL",
    time_period: str = "MONTH",
    order_by: str = "PNL",
) -> int:
    if not 1 <= limit <= 50:
        raise ValueError("leaderboard limit must be between 1 and 50")
    order_by = order_by.upper()
    if order_by not in {"PNL", "VOL"}:
        raise ValueError("leaderboard order must be PNL or VOL")
    collected_at = utc_now()
    payload = client.get_json(
        DATA_API,
        "/v1/leaderboard",
        {"category": category, "timePeriod": time_period, "orderBy": order_by, "limit": limit},
    )
    raw_path = _save_raw(raw_dir, "data_api_leaderboard", payload, collected_at)
    initialize(database_path)
    with closing(connect(database_path)) as connection:
        cursor = connection.execute(
            """INSERT INTO ingestion_runs
               (source_name, endpoint, started_at_utc, completed_at_utc, status, raw_file_path)
               VALUES (?, ?, ?, ?, 'completed', ?)""",
            ("Polymarket Data API", "/v1/leaderboard", _iso(collected_at), _iso(utc_now()), str(raw_path)),
        )
        run_id = cursor.lastrowid
        for row in payload:
            wallet = row["proxyWallet"].lower()
            connection.execute(
                """INSERT INTO traders
                   (proxy_wallet, username, first_observed_at_utc, last_observed_at_utc)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(proxy_wallet) DO UPDATE SET
                       username=excluded.username,
                       last_observed_at_utc=excluded.last_observed_at_utc""",
                (wallet, row.get("userName"), _iso(collected_at), _iso(collected_at)),
            )
            connection.execute(
                """INSERT INTO leaderboard_snapshots
                   (snapshot_at_utc, category, time_period, ranking_metric, rank, proxy_wallet,
                    reported_volume, reported_pnl, source_name, ingestion_run_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    _iso(collected_at), category, time_period, order_by, int(row["rank"]), wallet,
                    row.get("vol"), row.get("pnl"), "Polymarket Data API", run_id,
                ),
            )
        connection.commit()
    return len(payload)


def ingest_wallet_trades(
    client: PublicApiClient,
    database_path: Path,
    raw_dir: Path,
    *,
    wallet: str,
    page_size: int = 500,
    max_pages: int = 20,
) -> tuple[int, int]:
    """Download a bounded wallet history and insert only previously unseen trades.

    Re-running the command intentionally overlaps prior downloads. Stable trade
    keys make that overlap safe and expose upstream revisions instead of relying
    on a fragile last-seen offset.
    """
    normalized_wallet = wallet.lower()
    if not normalized_wallet.startswith("0x") or len(normalized_wallet) != 42:
        raise ValueError("wallet must be a 0x-prefixed 40-byte address")
    if not 1 <= page_size <= 10000:
        raise ValueError("page size must be between 1 and 10000")
    if not 1 <= max_pages <= 100:
        raise ValueError("max pages must be between 1 and 100")

    initialize(database_path)
    started_at = utc_now()
    with closing(connect(database_path)) as connection:
        cursor = connection.execute(
            """INSERT INTO ingestion_runs
               (source_name, endpoint, started_at_utc, status)
               VALUES (?, ?, ?, 'running')""",
            ("Polymarket Data API", "/trades", _iso(started_at)),
        )
        run_id = int(cursor.lastrowid)
        connection.commit()

    downloaded = 0
    inserted = 0
    last_raw_path: Path | None = None
    try:
        for page_number in range(max_pages):
            offset = page_number * page_size
            if offset > 10000:
                break
            received_at = utc_now()
            payload = client.get_json(
                DATA_API,
                "/trades",
                {
                    "user": normalized_wallet,
                    "limit": page_size,
                    "offset": offset,
                    "takerOnly": "false",
                },
            )
            if not isinstance(payload, list):
                raise ValueError("trade endpoint returned a non-list response")
            last_raw_path = _save_raw(raw_dir, "data_api_trades", payload, received_at)
            downloaded += len(payload)

            inserted += len(
                _store_trade_rows(
                    database_path,
                    wallet=normalized_wallet,
                    rows=payload,
                    received_at=received_at,
                    raw_path=last_raw_path,
                )
            )

            if len(payload) < page_size:
                break

        with closing(connect(database_path)) as connection:
            connection.execute(
                """UPDATE ingestion_runs
                   SET completed_at_utc=?, status='completed', raw_file_path=?
                   WHERE id=?""",
                (_iso(utc_now()), str(last_raw_path) if last_raw_path else None, run_id),
            )
            connection.commit()
    except Exception as exc:
        with closing(connect(database_path)) as connection:
            connection.execute(
                """UPDATE ingestion_runs
                   SET completed_at_utc=?, status='failed', error_message=?
                   WHERE id=?""",
                (_iso(utc_now()), str(exc), run_id),
            )
            connection.commit()
        raise

    return downloaded, inserted


def ingest_market_metadata(
    client: PublicApiClient,
    database_path: Path,
    raw_dir: Path,
    *,
    condition_ids: list[str] | None = None,
    limit: int = 100,
) -> tuple[int, int]:
    """Resolve traded conditions into market, token, and observed fee metadata."""
    initialize(database_path)
    if condition_ids is None:
        with closing(connect(database_path)) as connection:
            condition_ids = [
                row[0]
                for row in connection.execute(
                    """SELECT DISTINCT condition_id FROM public_trades
                       WHERE condition_id NOT IN (SELECT condition_id FROM markets)
                       ORDER BY condition_id LIMIT ?""",
                    (limit,),
                )
            ]
    condition_ids = list(dict.fromkeys(condition_ids))[:limit]
    markets_saved = 0
    token_observations = 0

    for condition_id in condition_ids:
        observed_at = utc_now()
        markets = client.get_json(
            GAMMA_API,
            "/markets",
            {"condition_ids": condition_id, "limit": 1},
        )
        if not markets:
            markets = client.get_json(
                GAMMA_API,
                "/markets",
                {"condition_ids": condition_id, "closed": "true", "limit": 1},
            )
        if not isinstance(markets, list) or not markets:
            continue
        market = markets[0]
        tokens = [str(token) for token in _json_list(market.get("clobTokenIds"))]
        outcomes = [str(outcome) for outcome in _json_list(market.get("outcomes"))]
        prices = [float(price) for price in _json_list(market.get("outcomePrices"))]
        if tokens and len(tokens) != len(outcomes):
            raise ValueError(f"token/outcome count mismatch for {condition_id}")

        fee_rates: dict[str, int] = {}
        for token in tokens:
            fee_payload = client.get_json(CLOB_API, "/fee-rate", {"token_id": token})
            fee_rates[token] = int(fee_payload["base_fee"])
            token_observations += 1
        combined = {"market": market, "fee_rates": fee_rates}
        raw_path = _save_raw(raw_dir, "market_metadata", combined, observed_at)
        winning_token = None
        if market.get("closed") and prices:
            winning_indexes = [index for index, price in enumerate(prices) if price >= 0.999]
            if len(winning_indexes) == 1 and winning_indexes[0] < len(tokens):
                winning_token = tokens[winning_indexes[0]]
        nonzero_fee_rates = [rate for rate in fee_rates.values() if rate > 0]
        fee_schedule = market.get("feeSchedule") or {}
        fee_rate_decimal = fee_schedule.get("rate")
        if fee_rate_decimal is not None:
            fee_rate_decimal = float(fee_rate_decimal)
        elif not (market.get("feesEnabled") or nonzero_fee_rates):
            fee_rate_decimal = 0.0

        with closing(connect(database_path)) as connection:
            connection.execute(
                """INSERT INTO markets
                   (condition_id, gamma_market_id, event_id, slug, question, category,
                    resolution_source, end_at_utc, resolved_at_utc, winning_token_id,
                    fees_enabled, source_updated_at_utc, ingested_at_utc)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(condition_id) DO UPDATE SET
                       gamma_market_id=excluded.gamma_market_id,
                       slug=excluded.slug,
                       question=excluded.question,
                       category=excluded.category,
                       resolution_source=excluded.resolution_source,
                       end_at_utc=excluded.end_at_utc,
                       resolved_at_utc=excluded.resolved_at_utc,
                       winning_token_id=excluded.winning_token_id,
                       fees_enabled=excluded.fees_enabled,
                       source_updated_at_utc=excluded.source_updated_at_utc,
                       ingested_at_utc=excluded.ingested_at_utc""",
                (
                    condition_id,
                    market.get("id"),
                    None,
                    market.get("slug"),
                    market.get("question") or condition_id,
                    market.get("category"),
                    market.get("resolutionSource"),
                    market.get("endDate") or market.get("endDateIso"),
                    market.get("closedTime"),
                    winning_token,
                    int(bool(market.get("feesEnabled") or nonzero_fee_rates)),
                    market.get("updatedAt"),
                    _iso(observed_at),
                ),
            )
            for index, token in enumerate(tokens):
                connection.execute(
                    """INSERT INTO outcome_tokens
                       (token_id, condition_id, outcome_name, outcome_index)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(token_id) DO UPDATE SET
                           condition_id=excluded.condition_id,
                           outcome_name=excluded.outcome_name,
                           outcome_index=excluded.outcome_index""",
                    (token, condition_id, outcomes[index], index),
                )
            connection.execute(
                """INSERT INTO market_observations
                   (condition_id, observed_at_utc, active, closed, accepting_orders,
                    liquidity_usd, volume_usd, best_bid, best_ask, fees_enabled,
                    fee_rate_decimal, source_name, raw_file_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    condition_id,
                    _iso(observed_at),
                    int(bool(market.get("active"))),
                    int(bool(market.get("closed"))),
                    int(bool(market.get("acceptingOrders"))),
                    market.get("liquidityNum") or market.get("liquidity"),
                    market.get("volumeNum") or market.get("volume"),
                    market.get("bestBid"),
                    market.get("bestAsk"),
                    int(bool(market.get("feesEnabled") or nonzero_fee_rates)),
                    fee_rate_decimal,
                    "Polymarket Gamma and CLOB APIs",
                    str(raw_path),
                ),
            )
            connection.commit()
        markets_saved += 1

    return markets_saved, token_observations


def collect_orderbook(
    client: PublicApiClient,
    database_path: Path,
    raw_dir: Path,
    *,
    token_id: str,
) -> tuple[int, dict[str, Any]]:
    received_at = utc_now()
    payload = client.get_json(CLOB_API, "/book", {"token_id": token_id})
    raw_path = _save_raw(raw_dir, "clob_orderbook", payload, received_at)
    bids = payload.get("bids", [])
    asks = payload.get("asks", [])
    best_bid = max((float(level["price"]) for level in bids), default=None)
    best_ask = min((float(level["price"]) for level in asks), default=None)
    source_timestamp = payload.get("timestamp")
    source_timestamp_utc = None
    if source_timestamp is not None:
        source_timestamp_utc = _unix_timestamp_to_utc(source_timestamp)

    initialize(database_path)
    with closing(connect(database_path)) as connection:
        cursor = connection.execute(
            """INSERT INTO orderbook_snapshots
               (token_id, source_timestamp_utc, received_at_utc, best_bid, best_ask,
                spread, last_trade_price, book_hash, source_name, raw_file_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                token_id,
                source_timestamp_utc,
                _iso(received_at),
                best_bid,
                best_ask,
                None if best_bid is None or best_ask is None else best_ask - best_bid,
                payload.get("last_trade_price"),
                payload.get("hash"),
                "Polymarket CLOB API",
                str(raw_path),
            ),
        )
        snapshot_id = int(cursor.lastrowid)
        for side, levels in (("BID", bids), ("ASK", asks)):
            ordered = sorted(levels, key=lambda item: float(item["price"]), reverse=side == "BID")
            connection.executemany(
                """INSERT INTO orderbook_levels
                   (snapshot_id, side, level_index, price, size_shares)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    (snapshot_id, side, index, float(level["price"]), float(level["size"]))
                    for index, level in enumerate(ordered)
                ],
            )
        connection.commit()
    return snapshot_id, payload


def snapshot_orderbook(
    client: PublicApiClient,
    database_path: Path,
    raw_dir: Path,
    *,
    token_id: str,
) -> int:
    snapshot_id, _ = collect_orderbook(
        client, database_path, raw_dir, token_id=token_id
    )
    return snapshot_id
