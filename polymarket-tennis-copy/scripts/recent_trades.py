"""Show a wallet's most recent tennis trades, with money and timestamps.

Two P&L columns, because they answer different questions:

* **theirs** -- what the wallet actually made, at the price it actually got.
* **yours** -- what $100 flat on the same signal returns to a follower entering
  after the copy delay, at the modelled fill. This is the number that matters to
  someone copying, and it is always the worse of the two.

Open positions are listed separately. A position with no result yet has no P&L,
and showing a zero there would read as a breakeven trade rather than an
unfinished one.

Usage:
    DATABASE_URL="sqlite:///./data/best.db" python scripts/recent_trades.py
    ... scripts/recent_trades.py --wallet 0x37c1ff27d21b --limit 20
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import session_scope  # noqa: E402
from app.models import (  # noqa: E402
    Market,
    Outcome,
    ReconstructedPosition as RP,
    TradeCopyability as TC,
    Wallet,
)

FOLLOW_LIST = REPO_ROOT / "data" / "follow-list.json"
STAKE = 100.0


def fetch(session, address: str, delay: int, limit: int, closed_only: bool):
    stmt = (
        select(
            RP.opened_at, RP.closed_at, RP.status, Market.question,
            Market.tennis_market_type, Outcome.player_name, RP.avg_entry_price,
            RP.net_pnl, RP.is_win, RP.capital_committed,
            TC.estimated_fill_price, TC.follower_is_win, TC.data_confidence,
        )
        .join(Wallet, Wallet.id == RP.wallet_id)
        .outerjoin(Market, Market.id == RP.market_id)
        .outerjoin(Outcome, Outcome.id == RP.outcome_id)
        .outerjoin(TC, (TC.position_id == RP.id) & (TC.delay_seconds == delay))
        .where(Wallet.address == address, RP.is_tennis.is_(True))
        .order_by(RP.opened_ts.desc())
    )
    if closed_only:
        stmt = stmt.where(RP.status.in_(("closed", "settled")))
    return session.execute(stmt.limit(limit)).all()


def copier_pnl(fill, won) -> float | None:
    """Profit on a flat $100 stake for a follower entering at ``fill``."""
    if fill is None or won is None:
        return None
    f = float(fill)
    if not 0.0 < f < 1.0:
        return None
    return (STAKE / f) * (1.0 if won else 0.0) - STAKE


def main() -> int:
    settings = get_settings()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--wallet", action="append", help="repeatable; defaults to the frozen list")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--delay", type=int, default=15)
    p.add_argument("--include-open", action="store_true")
    args = p.parse_args()

    addresses = args.wallet
    if not addresses:
        if not FOLLOW_LIST.exists():
            print(f"No frozen list at {FOLLOW_LIST}; pass --wallet.")
            return 1
        spec = json.loads(FOLLOW_LIST.read_text(encoding="utf-8"))
        addresses = [w["address"] for w in spec["wallets"]]
        print(f"Frozen follow list, {spec['frozen_at']}\n")

    with session_scope() as session:
        resolved = []
        for a in addresses:
            full = session.scalar(
                select(Wallet.address).where(Wallet.address.like(f"{a.lower()}%"))
            )
            if full:
                resolved.append(full)
            else:
                print(f"! {a} not in this database")

        for address in resolved:
            rows = fetch(session, address, args.delay, args.limit, not args.include_open)
            print("=" * 112)
            print(f"{address}   last {len(rows)} tennis trades   ({args.delay}s follower delay)")
            print("=" * 112)
            if not rows:
                print("  no trades\n")
                continue
            print(
                f"{'opened (UTC)':<18}{'match':<38}{'backed':<14}"
                f"{'paid':>7}{'result':>8}{'theirs':>11}{'yours':>10}"
            )
            print("-" * 112)

            their_total = 0.0
            your_total = 0.0
            counted = 0
            for (
                opened, _closed, status, question, mtype, player, entry,
                pnl, is_win, _cap, fill, f_win, conf,
            ) in rows:
                match = (question or "?")[:36]
                backed = (player or "?")[:12]
                when = opened.strftime("%Y-%m-%d %H:%M") if opened else "?"

                if status not in ("closed", "settled") or is_win is None:
                    print(
                        f"{when:<18}{match:<38}{backed:<14}"
                        f"{float(entry or 0):>7.2f}{'OPEN':>8}{'--':>11}{'--':>10}"
                    )
                    continue

                theirs = float(pnl or 0)
                their_total += theirs
                counted += 1
                yours = copier_pnl(fill, f_win)
                # A fill without real price evidence is not a number to quote.
                if yours is not None and (conf or 0) >= settings.min_copyable_data_confidence:
                    your_total += yours
                    yours_txt = f"{yours:+,.0f}"
                else:
                    yours_txt = "n/a"
                print(
                    f"{when:<18}{match:<38}{backed:<14}"
                    f"{float(entry or 0):>7.2f}{'WON' if is_win else 'lost':>8}"
                    f"{theirs:>+11,.0f}{yours_txt:>10}"
                )

            print("-" * 112)
            print(
                f"{'over these ' + str(counted) + ' settled trades':<77}"
                f"{their_total:>+11,.0f}{your_total:>+10,.0f}"
            )
            print(
                f"{'':<77}{'their $':>11}{'$100/bet':>10}\n"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
