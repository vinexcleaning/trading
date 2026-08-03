"""The screen as actually specified: who could I copy, right now, today?

Gates, all overridable:

* not making the market       -- market-making / arbitrage / both-sides flags
* high win rate               -- measured against the price a COPIER pays
* high trade count            -- the thing that kills the lucky-streak problem
* trading for at least a week
* still trading now           -- silent for no more than N days
* recent form still good      -- the last 2 days, judged separately
* survives a realistic delay  -- default 15s, with the full curve shown

Win rate is deliberately never reported raw. A wallet buying $0.95 favourites
wins 90% of the time and loses money; the only number that means anything is the
win rate *minus the price paid*, in percentage points. At a 15s delay the price
paid is the follower's modelled fill, not the wallet's own entry, so the edge
reported here is the copier's edge rather than the wallet's.

Trade count does most of the statistical work. Win rate has a standard error of
roughly 0.5/sqrt(n): +-9 points at 30 trades, +-2 at 481. The screen therefore
prints, next to every wallet, the edge the LUCKIEST wallet in a skill-free
population of this size would show -- so a result can be read against the bar it
actually has to clear rather than against zero.

Usage:
    DATABASE_URL="sqlite:///./data/best.db" python scripts/live_candidates.py
    ... scripts/live_candidates.py --delay 60 --min-trades 100
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import func, select  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import session_scope  # noqa: E402
from app.models import (  # noqa: E402
    ReconstructedPosition as RP,
    TradeCopyability as TC,
    Wallet,
)
from app.services.split_sample import (  # noqa: E402
    TradeRecord,
    binomial_tail,
    build_splits,
    copier_edge,
    luck_bar,
    run_selection_test,
)
from app.services.statistics import active_periods  # noqa: E402

DAY = 86_400
COMPLETE = ("closed", "settled")

# Behaviours that mean the wallet is part of the price rather than taking it.
MARKET_SIDE = ("likely_market_making", "liquidity_provision", "possible_arbitrage")


@dataclass(slots=True)
class Trade:
    ts: int
    won: bool
    fill: float          # what a follower pays after the delay
    own_entry: float     # what the wallet itself paid


@dataclass(slots=True)
class Candidate:
    address: str
    trades: list[Trade]
    mm_share: float
    both_sides_share: float
    last_ts: int

    @property
    def n(self) -> int:
        return len(self.trades)

    @property
    def span_days(self) -> float:
        return (self.trades[-1].ts - self.trades[0].ts) / DAY

    def slice_since(self, ts: int) -> list[Trade]:
        return [t for t in self.trades if t.ts >= ts]


def edge_of(trades: list[Trade]) -> tuple[float, float, float]:
    return copier_edge([t.won for t in trades], [t.fill for t in trades])


def load(session, delay: int, confidence_floor: float) -> list[Candidate]:
    rows = session.execute(
        select(
            Wallet.address,
            RP.opened_ts,
            TC.follower_is_win,
            TC.estimated_fill_price,
            RP.avg_entry_price,
            RP.behaviour,
            RP.held_both_outcomes,
        )
        .join(RP, RP.wallet_id == Wallet.id)
        .join(TC, TC.position_id == RP.id)
        .where(
            TC.delay_seconds == delay,
            TC.follower_is_win.is_not(None),
            TC.estimated_fill_price.is_not(None),
            TC.data_confidence >= confidence_floor,
            RP.is_tennis.is_(True),
            RP.status.in_(COMPLETE),
        )
    ).all()

    grouped: dict[str, list] = {}
    for r in rows:
        grouped.setdefault(r[0], []).append(r)

    out: list[Candidate] = []
    for address, rs in grouped.items():
        rs.sort(key=lambda r: r[1])
        trades = [
            Trade(ts=r[1], won=bool(r[2]), fill=float(r[3]), own_entry=float(r[4]))
            for r in rs
        ]
        mm = sum(1 for r in rs if r[5] in MARKET_SIDE) / len(rs)
        both = sum(1 for r in rs if r[6]) / len(rs)
        out.append(Candidate(address, trades, mm, both, trades[-1].ts))
    return out


def main() -> int:
    settings = get_settings()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--delay", type=int, default=15, help="follower delay in seconds")
    p.add_argument("--min-trades", type=int, default=50)
    p.add_argument("--min-span-days", type=float, default=7.0)
    p.add_argument(
        "--min-active-weeks",
        type=int,
        default=4,
        help="weeks out of the last 8 that must contain at least one trade",
    )
    p.add_argument("--lookback-weeks", type=int, default=8)
    p.add_argument("--max-silence-days", type=float, default=2.0)
    p.add_argument("--recent-days", type=float, default=2.0)
    p.add_argument("--min-recent-trades", type=int, default=5)
    p.add_argument(
        "--min-edge",
        type=float,
        default=0.0,
        help="minimum edge in points; a follow list has no business containing losers",
    )
    p.add_argument("--max-market-making", type=float, default=0.20)
    p.add_argument("--max-both-sides", type=float, default=0.50)
    p.add_argument("--show-all", action="store_true", help="print wallets that fail gates too")
    p.add_argument(
        "--freeze",
        metavar="PATH",
        help="commit the passing list to a JSON pre-registration for forward testing",
    )
    args = p.parse_args()

    with session_scope() as session:
        candidates = load(session, args.delay, settings.min_copyable_data_confidence)
        latest = session.scalar(
            select(func.max(RP.opened_ts)).where(RP.is_tennis.is_(True))
        )

    if not candidates:
        print("No wallet has usable copyability data at this delay.")
        return 1

    now = int(latest)
    recent_cut = now - int(args.recent_days * DAY)

    print("=" * 118)
    print(f"LIVE COPY CANDIDATES  --  {args.delay}s follower delay, edge measured vs the price a COPIER pays")
    print("=" * 118)
    print(
        f"gates: >={args.min_trades} trades | >={args.min_span_days:g}d span | "
        f"active >={args.min_active_weeks}/{args.lookback_weeks} weeks | "
        f"silent <={args.max_silence_days:g}d | >={args.min_recent_trades} trades in last "
        f"{args.recent_days:g}d | market-making <{args.max_market_making:.0%} | "
        f"both-sides <{args.max_both_sides:.0%}"
    )
    print()

    rows = []
    for c in candidates:
        implied, realised, edge = edge_of(c.trades)
        wins = sum(1 for t in c.trades if t.won)
        pv = binomial_tail(wins, c.n, implied)
        silence = (now - c.last_ts) / DAY
        recent = c.slice_since(recent_cut)
        r_implied, r_realised, r_edge = edge_of(recent)

        active = active_periods(
            [t.ts for t in c.trades],
            now_ts=now,
            lookback_periods=args.lookback_weeks,
        )

        fails = []
        if c.n < args.min_trades:
            fails.append(f"only {c.n} trades")
        if c.span_days < args.min_span_days:
            fails.append(f"span {c.span_days:.1f}d")
        if active < args.min_active_weeks:
            fails.append(f"active {active}/{args.lookback_weeks}w")
        if silence > args.max_silence_days:
            fails.append(f"silent {silence:.1f}d")
        if len(recent) < args.min_recent_trades:
            fails.append(f"{len(recent)} recent trades")
        if edge * 100 < args.min_edge:
            fails.append(f"edge {edge*100:+.1f}p")
        if c.mm_share > args.max_market_making:
            fails.append(f"market-making {c.mm_share:.0%}")
        if c.both_sides_share > args.max_both_sides:
            fails.append(f"both-sides {c.both_sides_share:.0%}")

        rows.append({
            "c": c, "implied": implied, "realised": realised, "edge": edge,
            "p": pv, "silence": silence, "n_recent": len(recent),
            "r_edge": r_edge, "r_realised": r_realised, "fails": fails,
            "active": active,
        })

    passed = [r for r in rows if not r["fails"]]
    passed.sort(key=lambda r: r["edge"], reverse=True)
    failed = sorted((r for r in rows if r["fails"]), key=lambda r: r["edge"], reverse=True)

    header = (
        f"{'wallet':<16}{'n':>6}{'span':>7}{'act':>6}{'quiet':>7}{'pays':>8}{'wins':>8}"
        f"{'EDGE':>9}{'p(luck)':>10}{'last2d':>9}{'2d edge':>9}{'MM':>6}"
    )

    def show(r):
        c = r["c"]
        print(
            f"{c.address[:14]:<16}{c.n:>6}{c.span_days:>6.0f}d"
            f"{r['active']:>4}/{args.lookback_weeks}{r['silence']:>6.1f}d"
            f"{r['implied']*100:>7.1f}%{r['realised']*100:>7.1f}%"
            f"{r['edge']*100:>+8.1f}p{r['p']:>10.4f}"
            f"{r['n_recent']:>9}{r['r_edge']*100:>+8.1f}p{c.mm_share*100:>5.0f}%"
        )

    print("PASSED ALL GATES")
    print(header)
    print("-" * 118)
    if passed:
        for r in passed:
            show(r)
    else:
        print("(none)")

    if failed and (args.show_all or not passed):
        print()
        print("FAILED (closest first)")
        print(header)
        print("-" * 118)
        for r in failed[:12]:
            show(r)
            print(f"{'':<16}  -> {', '.join(r['fails'])}")

    # --- the luck bar, sized to every wallet that had a chance -------------
    # Computed over wallets meeting the VOLUME threshold, not over the ones that
    # survived every gate. The other gates are judgement calls made partly after
    # seeing the data; scoring against the survivors lets any tightening of a
    # gate lower the bar and flatter the winner. Measured live: gating harder cut
    # the pool from 6 to 3 and dropped the bar from +7.1 to +4.5 points, flipping
    # a fail into a pass without a single wallet's record changing.
    all_n = [r["c"].n for r in rows]
    eligible = [r for r in rows if r["c"].n >= args.min_trades]
    bar = luck_bar([r["c"].n for r in eligible]) if eligible else 0.0
    print()
    print("=" * 118)
    print("HOW BIG AN EDGE DOES LUCK ALONE PRODUCE HERE?")
    print("=" * 118)
    print(
        f"All {len(all_n)} measured wallets, no skill anywhere: luckiest shows "
        f"+{luck_bar(all_n)*100:.1f} points (inflated by 1-3 trade records)."
    )
    print(
        f"The {len(eligible)} with >={args.min_trades} trades -- everyone who had a real "
        f"chance -- gives a bar of +{bar*100:.1f} points."
    )
    print("That is the number to beat. It does not shrink when other gates tighten.")
    if passed:
        best = passed[0]
        clears = best["edge"] > bar
        print()
        print(
            f"Best wallet clearing all gates: {best['c'].address[:14]} at "
            f"{best['edge']*100:+.1f} points on {best['c'].n} trades -- "
            f"{'CLEARS' if clears else 'does NOT clear'} the +{bar*100:.1f} bar."
        )
        stake = 100
        print(
            f"In money: ${stake} on each of its {best['c'].n} trades at an average fill of "
            f"${best['implied']:.2f} returns "
            f"${(best['realised'] / best['implied'] - 1) * stake * best['c'].n:+,.0f} overall."
        )
        if not clears:
            print(
                "Positive and interesting, but not yet separable from the best that "
                "luck produces across this many candidates."
            )

    # --- does a first-half rank predict the second half, on WIN RATE? ------
    records = [
        TradeRecord(r["c"].address, t.ts, (1.0 if t.won else 0.0) - t.fill)
        for r in rows
        for t in r["c"].trades
        if r["c"].n >= args.min_trades
    ]
    splits = build_splits(records, min_trades=args.min_trades, min_half=args.min_trades // 2)
    result = run_selection_test(splits, iterations=2000)
    print()
    print("-" * 118)
    if result is None:
        print("Not enough high-volume wallets to validate the ranking out of sample.")
    else:
        print(
            f"OUT-OF-SAMPLE CHECK on win-rate edge, {result.n_wallets} wallets with "
            f">={args.min_trades} trades:"
        )
        print(
            f"  picked on 1st half: {result.winner[:14]} at {result.winner_in_mean*100:+.1f}p "
            f"-> 2nd half paid {result.winner_out_mean*100:+.1f}p  "
            f"(luck-only screen gives {result.null_winner_out_mean*100:+.1f}p, "
            f"p={result.p_value_out_sample:.4f})"
        )
        print(
            f"  {'SURVIVES' if result.survives else 'does not survive'} the out-of-sample null."
        )

    if args.freeze:
        freeze(Path(args.freeze), args, passed, now, bar)
    return 0 if passed else 2


def freeze(path: Path, args, passed: list[dict], now: int, bar: float) -> None:
    """Commit the follow list to disk, before any forward data exists.

    A forward record only means something if the wallet list and the pass mark
    are fixed in advance. Left unfrozen, the list drifts -- the scoring layer
    re-ranks wallets continuously -- and in a month it becomes impossible to tell
    a genuine forward result from a fresh backward-looking pick. Writing the
    prediction down first is the whole point, so this file must never be
    regenerated to 'update' it; start a new one instead.
    """
    if not passed:
        print("\nNothing passed the gates -- refusing to freeze an empty follow list.")
        return

    payload = {
        "frozen_at_ts": now,
        "frozen_at": dt.datetime.fromtimestamp(now, dt.timezone.utc).isoformat(),
        "delay_seconds": args.delay,
        "gates": {
            "min_trades": args.min_trades,
            "min_span_days": args.min_span_days,
            "min_active_weeks": args.min_active_weeks,
            "lookback_weeks": args.lookback_weeks,
            "max_silence_days": args.max_silence_days,
            "recent_days": args.recent_days,
            "min_recent_trades": args.min_recent_trades,
            "min_edge_points": args.min_edge,
            "max_market_making": args.max_market_making,
            "max_both_sides": args.max_both_sides,
        },
        "luck_bar_at_freeze": round(bar, 4),
        "criterion": (
            "PASS requires the pooled forward edge across these wallets to be "
            "positive AND to exceed the luck bar recomputed for the forward "
            "sample size. Per-wallet results are reported but the pooled figure "
            "is the verdict: judging the best wallet after the fact would "
            "reintroduce the selection problem this whole exercise exists to "
            "avoid."
        ),
        "wallets": [
            {
                "address": r["c"].address,
                "n_at_freeze": r["c"].n,
                "edge_at_freeze": round(r["edge"], 4),
                "implied_at_freeze": round(r["implied"], 4),
                "win_rate_at_freeze": round(r["realised"], 4),
                "recent_edge_at_freeze": round(r["r_edge"], 4),
            }
            for r in passed
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print()
    print("=" * 118)
    print(f"FROZEN: {len(passed)} wallets committed to {path}")
    print("=" * 118)
    print(f"Pass mark: pooled forward edge > +{bar * 100:.1f} points and > 0.")
    print("Score it later with: python scripts/forward_record.py " + str(path))
    print("Do not regenerate this file. If the list needs to change, freeze a new one.")


if __name__ == "__main__":
    raise SystemExit(main())
