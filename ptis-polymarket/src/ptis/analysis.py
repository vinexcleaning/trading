from __future__ import annotations

import math
from collections import defaultdict
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .collectors import _iso, utc_now
from .database import connect, initialize


@dataclass
class PositionState:
    shares: float = 0.0
    average_cost: float = 0.0
    realized_pnl: float = 0.0
    buys: int = 0
    sells: int = 0
    history_incomplete: bool = False


def rebuild_positions(database_path: Path, wallet: str) -> int:
    initialize(database_path)
    wallet = wallet.lower()
    states: dict[str, PositionState] = defaultdict(PositionState)
    with closing(connect(database_path)) as connection:
        rows = connection.execute(
            """SELECT token_id, side, size_shares, price, executed_at_utc
               FROM public_trades WHERE proxy_wallet=?
               ORDER BY executed_at_utc, trade_key""",
            (wallet,),
        ).fetchall()
        for token, side, size, price, _ in rows:
            state = states[token]
            if side == "BUY":
                new_shares = state.shares + size
                if new_shares > 0:
                    state.average_cost = (
                        state.shares * state.average_cost + size * price
                    ) / new_shares
                state.shares = new_shares
                state.buys += 1
            else:
                state.sells += 1
                matched = min(state.shares, size)
                state.realized_pnl += matched * (price - state.average_cost)
                state.shares -= matched
                if size > matched:
                    state.history_incomplete = True
                if state.shares <= 1e-12:
                    state.shares = 0.0
                    state.average_cost = 0.0

        as_of = _iso(utc_now())
        for token, state in states.items():
            connection.execute(
                """INSERT INTO reconstructed_positions
                   (proxy_wallet, token_id, as_of_utc, shares, average_cost,
                    realized_pnl_from_observed_trades, buys, sells, history_incomplete)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    wallet, token, as_of, state.shares, state.average_cost,
                    state.realized_pnl, state.buys, state.sells, int(state.history_incomplete),
                ),
            )
        connection.commit()
    return len(states)


def assess_trader(database_path: Path, wallet: str) -> dict[str, float | int | str | None]:
    initialize(database_path)
    wallet = wallet.lower()
    with closing(connect(database_path)) as connection:
        rows = connection.execute(
            """SELECT t.condition_id, t.token_id, t.side, t.executed_at_utc,
                      COALESCE(m.category, 'Unknown')
               FROM public_trades t
               LEFT JOIN markets m ON m.condition_id=t.condition_id
               WHERE t.proxy_wallet=?
               ORDER BY t.executed_at_utc, t.trade_key""",
            (wallet,),
        ).fetchall()
        if not rows:
            raise ValueError("no stored trades for wallet")
        buys = sum(row[2] == "BUY" for row in rows)
        markets = {row[0] for row in rows}
        condition_tokens: dict[str, set[str]] = defaultdict(set)
        category_counts: dict[str, int] = defaultdict(int)
        categorized_observations = 0
        previous_by_token: dict[str, tuple[str, datetime]] = {}
        reversals = 0
        for condition, token, side, timestamp, category in rows:
            if side == "BUY":
                condition_tokens[condition].add(token)
            if category != "Unknown":
                category_counts[category] += 1
                categorized_observations += 1
            moment = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            previous = previous_by_token.get(token)
            if previous and previous[0] != side:
                if (moment - previous[1]).total_seconds() <= 3600:
                    reversals += 1
            previous_by_token[token] = (side, moment)

        observation_count = len(rows)
        buy_share = buys / observation_count
        reversal_share = reversals / max(1, observation_count - 1)
        two_sided_share = (
            sum(len(tokens) > 1 for tokens in condition_tokens.values()) / len(markets)
        )
        top_category_share = (
            max(category_counts.values()) / categorized_observations
            if categorized_observations
            else None
        )

        if buy_share <= 0.05:
            classification = "sell-only-or-incomplete-history"
        elif reversal_share >= 0.25 and two_sided_share >= 0.25:
            classification = "market-making-or-arbitrage-like"
        elif two_sided_share >= 0.35:
            classification = "hedging-or-arbitrage-like"
        elif buy_share >= 0.75 and reversal_share <= 0.10:
            classification = "directional-candidate"
        elif reversal_share >= 0.25:
            classification = "rapid-trader"
        else:
            classification = "unknown"

        sample_points = min(20.0, 5.0 * math.log10(max(1, observation_count)))
        score = sample_points
        score += 15.0 * (1.0 - min(1.0, reversal_share / 0.30))
        score += 15.0 * (1.0 - min(1.0, two_sided_share / 0.50))
        score += 5.0 if 0.55 <= buy_share <= 1.0 else 0.0
        if top_category_share is not None and categorized_observations >= 30:
            score += 5.0 * top_category_share
        score = round(min(60.0, max(0.0, score)), 1)
        assessed_at = _iso(utc_now())
        limitations = (
            "Preliminary behavior-only score capped at 60; no delayed copy P&L, "
            "complete wallet history, hidden hedges, or out-of-sample evidence."
        )
        connection.execute(
            """INSERT INTO trader_assessments
               (proxy_wallet, assessed_at_utc, observation_count, market_count,
                buy_share, rapid_reversal_share, two_sided_market_share,
                top_category_share, classification,
                preliminary_copyability_score, limitations)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                wallet, assessed_at, observation_count, len(markets), buy_share,
                reversal_share, two_sided_share, top_category_share,
                classification, score, limitations,
            ),
        )
        connection.commit()
    return {
        "wallet": wallet,
        "observation_count": observation_count,
        "market_count": len(markets),
        "buy_share": round(buy_share, 4),
        "rapid_reversal_share": round(reversal_share, 4),
        "two_sided_market_share": round(two_sided_share, 4),
        "top_category_share": (
            round(top_category_share, 4) if top_category_share is not None else None
        ),
        "classification": classification,
        "preliminary_copyability_score": score,
    }
