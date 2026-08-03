"""Score a frozen follow list against what happened AFTER it was frozen.

This is the only test in the project that cannot be gamed. Every backward-looking
number can be improved by choosing the wallet, the window, the statistic or the
delay after seeing the data; `split_sample_test.py` exists because that is
exactly what had happened. A frozen list scored on later trades has none of those
degrees of freedom left -- the prediction is already on disk.

Deliberate design choices, each blocking a specific way of fooling ourselves:

* Only trades with ``opened_ts`` strictly after the freeze timestamp count. A
  trade already in the database at freeze time is not forward evidence.
* The verdict is the POOLED edge across all frozen wallets, not the best one.
  Reporting the best wallet after the fact re-runs the selection that the freeze
  was meant to prevent, and would make a failed list look like a hit.
* The pass mark is the luck bar recomputed at the FORWARD sample sizes, which
  will be small at first and therefore a high bar. That is correct: a handful of
  forward trades genuinely cannot demonstrate anything.
* Wallets that stop trading are reported with zero forward trades rather than
  dropped, so a list that quietly died does not read as a list that held up.

Usage:
    DATABASE_URL="sqlite:///./data/best.db" python scripts/forward_record.py data/follow-list.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import session_scope  # noqa: E402
from app.models import (  # noqa: E402
    ReconstructedPosition as RP,
    TradeCopyability as TC,
    Wallet,
)
from app.services.split_sample import (  # noqa: E402
    binomial_tail,
    copier_edge,
    luck_bar,
)

DAY = 86_400
COMPLETE = ("closed", "settled")


def load_forward(session, address: str, after_ts: int, delay: int, floor: float):
    """Completed tennis trades opened strictly after the freeze."""
    rows = session.execute(
        select(RP.opened_ts, TC.follower_is_win, TC.estimated_fill_price)
        .join(RP, RP.id == TC.position_id)
        .join(Wallet, Wallet.id == RP.wallet_id)
        .where(
            Wallet.address == address,
            RP.opened_ts > after_ts,
            RP.is_tennis.is_(True),
            RP.status.in_(COMPLETE),
            TC.delay_seconds == delay,
            TC.follower_is_win.is_not(None),
            TC.estimated_fill_price.is_not(None),
            TC.data_confidence >= floor,
        )
        .order_by(RP.opened_ts)
    ).all()
    return [(int(ts), bool(won), float(fill)) for ts, won, fill in rows]


def main() -> int:
    settings = get_settings()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("frozen", type=Path, help="path to the frozen follow list JSON")
    args = p.parse_args()

    if not args.frozen.exists():
        print(f"No frozen list at {args.frozen}.")
        print("Create one: python scripts/live_candidates.py --freeze " + str(args.frozen))
        return 1

    spec = json.loads(args.frozen.read_text(encoding="utf-8"))
    frozen_ts = int(spec["frozen_at_ts"])
    delay = int(spec["delay_seconds"])

    with session_scope() as session:
        results = []
        for entry in spec["wallets"]:
            trades = load_forward(
                session, entry["address"], frozen_ts, delay,
                settings.min_copyable_data_confidence,
            )
            results.append({"spec": entry, "trades": trades})

    now = dt.datetime.now(dt.timezone.utc)
    frozen_at = dt.datetime.fromisoformat(spec["frozen_at"])
    elapsed_days = (now - frozen_at).total_seconds() / DAY

    print("=" * 108)
    print("FORWARD RECORD  --  scored only on trades opened after the freeze")
    print("=" * 108)
    print(
        f"frozen {spec['frozen_at']}  ({elapsed_days:.1f} days ago)  |  "
        f"{delay}s delay  |  {len(results)} wallets committed"
    )
    print()

    print(
        f"{'wallet':<16}{'predicted':>11}{'fwd n':>8}{'pays':>8}{'wins':>8}"
        f"{'FWD EDGE':>11}{'vs pred':>10}"
    )
    print("-" * 108)
    pooled_outcomes: list[bool] = []
    pooled_fills: list[float] = []
    forward_sizes: list[int] = []

    for r in results:
        spec_e = r["spec"]
        trades = r["trades"]
        if not trades:
            print(
                f"{spec_e['address'][:14]:<16}{spec_e['edge_at_freeze']*100:>+10.1f}p"
                f"{0:>8}{'--':>8}{'--':>8}{'no trades':>11}{'--':>10}"
            )
            continue
        outcomes = [t[1] for t in trades]
        fills = [t[2] for t in trades]
        implied, realised, edge = copier_edge(outcomes, fills)
        pooled_outcomes += outcomes
        pooled_fills += fills
        forward_sizes.append(len(trades))
        drift = edge - spec_e["edge_at_freeze"]
        print(
            f"{spec_e['address'][:14]:<16}{spec_e['edge_at_freeze']*100:>+10.1f}p"
            f"{len(trades):>8}{implied*100:>7.1f}%{realised*100:>7.1f}%"
            f"{edge*100:>+10.1f}p{drift*100:>+9.1f}p"
        )

    silent = sum(1 for r in results if not r["trades"])
    print()
    if not pooled_outcomes:
        print(
            f"No forward trades yet from any of the {len(results)} wallets "
            f"after {elapsed_days:.1f} days."
        )
        if elapsed_days > 7:
            print("That is itself a finding: the follow list has gone quiet.")
        return 2

    implied, realised, edge = copier_edge(pooled_outcomes, pooled_fills)
    n = len(pooled_outcomes)
    wins = sum(1 for w in pooled_outcomes if w)
    pv = binomial_tail(wins, n, implied)
    # Pass mark recomputed at the sample sizes actually achieved, not the ones
    # available at freeze time -- a thin forward record must face a high bar.
    bar = luck_bar(forward_sizes) if len(forward_sizes) > 1 else luck_bar([n])

    print("=" * 108)
    print("VERDICT  (pooled across the frozen list -- not the best wallet)")
    print("=" * 108)
    print(f"forward trades          : {n} across {len(forward_sizes)} active wallets")
    if silent:
        print(f"wallets that went quiet : {silent} of {len(results)}")
    print(f"average fill paid       : ${implied:.3f}")
    print(f"realised win rate       : {realised*100:.1f}%  ({wins}/{n})")
    print(f"forward edge            : {edge*100:+.1f} points")
    print(f"p(luck)                 : {pv:.4f}")
    print(f"pass mark (luck bar)    : +{bar*100:.1f} points")
    print()

    passed = edge > bar and edge > 0
    stake = 100
    profit = (realised / implied - 1) * stake * n if implied > 0 else 0.0
    if passed:
        print(f"PASS -- the frozen list beat its pass mark on forward data.")
        print(
            f"${stake} on each of the {n} forward trades returns {profit:+,.0f} overall."
        )
        print("This is real evidence. It is the first this project has had.")
    else:
        print("NOT YET -- the frozen list has not beaten its pass mark.")
        print(
            f"${stake} on each of the {n} forward trades returns {profit:+,.0f} overall."
        )
        if edge > 0:
            print(
                f"The edge is positive but {abs(edge - bar)*100:.1f} points short of the "
                f"bar; at this sample size that gap is indistinguishable from luck."
            )
        print("Keep collecting. Do not re-freeze a new list to chase this one.")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
