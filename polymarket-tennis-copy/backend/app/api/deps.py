"""Shared API helpers: JSON coercion and common query params."""

from __future__ import annotations

import json
from typing import Any

DISCLAIMER = (
    "Analytical tool only -- not financial advice. Historical results do not "
    "guarantee future performance. Public wallet activity can be misleading. "
    "Paper-trading results may differ materially from real execution. Users must "
    "comply with all applicable laws, platform rules, age requirements and "
    "geographic restrictions."
)

LEADERBOARD_CAVEAT = (
    "Ranking is not a recommendation. A high position reflects past, "
    "delay-adjusted results over a limited sample and may not persist. Check "
    "sample size, coverage and risk flags before drawing conclusions."
)


def load_json(value: str | None, default: Any = None) -> Any:
    """Parse a JSON text column, tolerating nulls and malformed data."""
    if not value:
        return default if default is not None else None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else None


def load_json_list(value: str | None) -> list:
    parsed = load_json(value, [])
    return parsed if isinstance(parsed, list) else []


def load_json_dict(value: str | None) -> dict:
    parsed = load_json(value, {})
    return parsed if isinstance(parsed, dict) else {}
