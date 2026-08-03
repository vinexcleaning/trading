"""
tennis_engine.py — decision engine for Kalshi live-tennis trades.

Takes a market snapshot, applies the rules, and returns a full trade
instruction: size, entry, target, exit, and the reasoning behind each.

This module decides. It does not place orders. Feed it a snapshot,
read the Decision, place the orders yourself.

    python tennis_engine.py --demo
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ----------------------------------------------------------------------
# configuration — every threshold lives here, nothing hardcoded below
# ----------------------------------------------------------------------

@dataclass
class Config:
    bankroll: float = 110.00
    stake_pct: float = 5.0           # same % on every qualifying trade

    # entry gates
    # Floor added 28 Jul. Across 125 real settled markets, net P&L by entry
    # price was the whole story:
    #     1-25c  -$31.66 (31% win) | 25-45c +$2.30 | 45-60c +$10.01
    #     60-75c +$83.12 (66% win) | 75c+   +$11.27
    # Everything below 60c together contributed -$19.35 while 60-75c carried
    # the account. This floor deletes that entire region, including the
    # "cheap underdog that might spike" trades, which were the worst bucket.
    min_entry_price: int = 60
    # 75c, not 85c. Two independent reasons: the 27 Jul 80c+ bucket went 1/4
    # for -$2.14, and the 4-week backtest's parameter sweep preferred a 65-70c
    # cap at every setting it tried. Above 75c the 99c ceiling leaves too
    # little upside to cover a stop that one break of serve can reach.
    max_favorite_price: int = 75
    thin_favorite_price: int = 70    # above this, warn
    max_divergence_price: int = 70   # above this, market already caught up

    # Who counts as the pre-match favourite. A market that opened 51c is a coin
    # flip, not a favourite, and routing it down the favourite path (looser
    # price cap) on a 1c difference is a knife edge. Anything in between is
    # treated as no clear favourite and takes the stricter divergence rules.
    favorite_threshold: int = 60
    underdog_threshold: int = 40

    # Set quality. "Won a set" is not one fact: 6-3 is a break of dominance,
    # 7-6 is a tiebreak coin flip, and the old rule counted them identically.
    # Margin 2 admits 6-4 and 7-5 but rejects 7-6 — which is exactly the
    # evidence a tiebreak actually provides.
    min_set_margin: int = 2

    # exits
    favorite_target_pct: float = 0.20    # +20% of capital risked
    divergence_target_pct: float = 0.50  # +50%
    # Resting target for the favourite setup. 95c, not the ~88c the percentage
    # rule produced: across 7,100 markets that touched 92c, 94.3% went on to
    # settle at 100, so taking 88c was leaving money behind. 95c keeps a real
    # exit while capturing most of that. (Riding all the way to settlement is
    # better still on paper, but it ties up a slot for hours and hands you a
    # 100%-loss tail on a small book.)
    favorite_target_price: int = 95
    # 38c, widened from 22c on 28 Jul after testing every width against 137
    # recorded matches. Per-trade result by stop width:
    #     none -3.84c | -15c -3.65c | -22c -3.81c | -30c -1.86c
    #     -40c -1.53c | -50c -1.65c | -60c -2.28c
    # A single break of serve moves these markets 15-30c, so 22c was still
    # inside the noise band: 47 of 137 stopped out, and of the trades we
    # actually stopped out of in live trading, 26% went on to WIN the match.
    # 30-50c all beat it and the curve is smooth, so this is a broad optimum
    # rather than a lucky point — 38c sits in the middle of it.
    # It is NOT a free win: a wider stop means a bigger loss on the ones that
    # really are breaking down. It trades a higher loss-per-stop for far
    # fewer stops.
    favorite_exit_drop: int = 38         # cents below entry
    divergence_exit_pct: float = 0.40    # fraction of entry price

    # Cancel an entry that hasn't filled in this many seconds (v3 spec §4).
    # A buy left resting is good-till-cancelled: it can fill long after the
    # score that justified it has changed. Set to 0 to disable.
    cancel_unfilled_after_sec: int = 60

    # Push a phone alert every time session P&L crosses this many dollars,
    # up or down. Entries are deliberately never notified - they happen
    # several times an hour and you'd stop reading the alerts.
    notify_pnl_every: float = 10.0

    # data freshness. Sofascore costs nothing per call, so the feed can be
    # polled every ~20s and this gate is finally meaningful rather than a
    # budget compromise.
    max_score_age_sec: int = 30

    # Spread ceiling. The backtest is unambiguous here: net P&L degrades
    # monotonically with spread (0-2c: -6.6c/trade, 3-5c: -11.1c, 6-10c:
    # -15.0c, 10c+: -20.3c). Anything above 3c was a guaranteed loser in
    # every strategy tested.
    max_spread: int = 3
    warn_spread: int = 2

    # portfolio guards
    # Staying at 5. Raising it was tempting after the Compagnucci re-entry got
    # blocked, but across 1,501 backtested trades these signals average -9c,
    # so a cap that blocks trades was protecting the account, not costing it.
    # The real fix for a slot held hostage by a loser is the time stop below.
    # 10, not 5. This is a runaway guard, not a strategy parameter — there are
    # rarely more than ten tennis matches live at once, so it caps a bug that
    # fires repeatedly rather than constraining real opportunities. At 5 the
    # bot was turning away genuine setups and re-entries with slots occupied.
    #
    # Cut 10 -> 4 on 28 Jul. Not because concurrency itself hurt — per-trade
    # P&L was flat across every book size (+0.05 / +0.53 / -0.08 / -0.09) —
    # but because 28 of 77 bot trades were opened with 7+ already running, and
    # each trade pays ~$0.46 in fees against a per-trade edge of roughly zero.
    # The cap is a fee brake, not a risk brake.
    #
    # Risk check at 4: entry ~70c, stop 38c below, ~9 contracts -> about $3.40
    # risked per position, so ~$14 across four. On a ~$130 book that is ~11%
    # if all four stop out together.
    max_open_positions: int = 4
    # Slots reserved for RE-ENTRIES only — a name you were stopped out of that
    # has since recovered and re-qualifies. On 27 Jul Compagnucci stopped out,
    # recovered to 100c, and every slot was occupied by a position that was
    # bleeding, so the bot watched the recovery it had already identified and
    # could do nothing. These are unreachable by a first-time entry, so they
    # cannot quietly inflate your general exposure.
    reentry_slots: int = 1

    # RE-ENABLED 3 Aug after the SAGLEV post-mortem below. It had been 0 (OFF)
    # since 28 Jul at the user's request. With it off, nothing whatsoever
    # stopped the three-leg sequence that lost $7.56 on one match in 50
    # minutes. At 15% of a $125 book the third leg would have been refused.
    max_daily_loss_pct: float = 15.0
    require_set_resolved: bool = True

    # ---- runaway guards, added 3 Aug -----------------------------------
    #
    # THE SAGLEV SEQUENCE, 28 Jul, KXITFWMATCH-26JUL28SAGLEV-LEV:
    #     14:17:24  buy  12 @ 49c   ($6.25 / 0.49 = 12)
    #     14:30:54  sell 12 @ 29c   stopped out, -$2.40
    #     14:31:18  buy  20 @ 31c   ($6.25 / 0.31 = 20)   <- 24s later
    #     14:43:24  sell 20 @ 18c   stopped out, -$2.60
    #     14:43:47  buy  32 @ 19c   ($6.25 / 0.19 = 32)   <- 23s later
    #     15:07:47  sell 32 @ 11c   stopped out, -$2.56
    #     total bought 12+20+32 = 64 contracts
    #
    # Every one of those three sizes is ARITHMETICALLY CORRECT. `stake /
    # price` is doing exactly what it says. That is the whole problem: a
    # FIXED-DOLLAR stake buys MORE contracts as the price FALLS, so re-
    # entering a collapsing market automatically martingales. Nobody designed
    # that; it is an emergent property of sizing by dollars.
    #
    # Three things had to be true at once, and all three were:
    #   1. sizing by dollars   -> each re-entry is bigger than the last
    #   2. rearm at stop + 2c  -> a 2c bounce off the stop re-arms entry, which
    #                             in a falling market is ordinary bid/ask noise
    #                             (position_manager.py, `rearm_above`)
    #   3. daily loss limit 0  -> nothing counted the damage across legs
    #
    # These caps fix 1 and 3. position_manager.py fixes 2.

    # Hard ceiling on contracts per entry, whatever the price says. At the
    # intended ~70c entry the stake buys ~9, so 15 leaves room for a genuine
    # cheaper entry without ever permitting 32.
    max_contracts: int = 15
    # A market below this price cannot support the configured stop distance
    # at all (a 38c stop under a 19c entry is not a stop, it is the whole
    # position), so the stake is risked in full. Entries there are refused.
    # This is the same floor as min_entry_price and is applied to RE-ENTRIES
    # too, which is where it was missing.
    reentry_respects_price_floor: bool = True
    # Minimum wall-clock gap before the same event may be re-entered after a
    # stop-out. The three SAGLEV legs were 24s and 23s apart.
    reentry_cooldown_sec: int = 900
    # Hard cap on how many times one event may be re-entered in a session.
    max_reentries_per_event: int = 1

    # Time stop — DISABLED (0). It was a mistake and the data says so.
    #
    # The original justification was Krivoshchekov sitting open 4h45m for
    # -$2.67. But that loss came from the APP BEING CLOSED for 4h13m, so
    # nothing was watching his stop. Long holds were the symptom; an unwatched
    # stop was the disease. A position with a live stop cannot bleed
    # indefinitely — it hits the stop or it doesn't.
    #
    # The backtest is unambiguous: of the five strategies tested, the one with
    # NO time limit (hold to settlement) was the best at -2.29c/trade, while
    # the two with 12-minute limits came in at -9.67c and -10.40c.
    #
    # It also contradicted the 95c target, which needs a match to run most of
    # its course. Evan Zhu was closed at 48c against a 41c stop that never
    # fired, and then recovered.
    #
    # Set to a positive number to re-enable if a future problem actually calls
    # for one. The stop loss is the real downside control.
    max_hold_minutes: int = 0

    # fee formula: ceil(rate * contracts * p * (1-p))
    fee_rate: float = 0.07


# ----------------------------------------------------------------------
# inputs
# ----------------------------------------------------------------------

class Setup(Enum):
    DIVERGENCE = "price overshot the score"
    FAVORITE = "favorite is winning"


@dataclass
class Snapshot:
    """Everything the engine needs to judge one trade."""
    player: str
    match: str

    # market
    ask: int                          # cents you'd pay
    bid: int                          # cents you'd receive
    depth_at_ask: int = 1000          # contracts available

    # match state
    sets_won: int = 0
    sets_lost: int = 0
    set_in_progress: bool = True
    was_prematch_favorite: bool = False
    # (my_games, their_games) for each COMPLETED set, in order. Lets the engine
    # tell a 6-3 apart from a 7-6 instead of counting both as "won a set".
    set_scores: list = field(default_factory=list)
    open_price: Optional[int] = None       # pre-match line, cents

    # hygiene
    score_age_sec: int = 0
    market_open: bool = True
    postponed: bool = False

    # portfolio
    open_positions: int = 0
    daily_pnl_pct: float = 0.0
    already_hold_other_side: bool = False
    # True when this is a name we were stopped out of that has recovered.
    # Re-entries may use the reserved slots; first entries may not.
    is_reentry: bool = False
    # Seconds since this event last stopped us out, and how many times it has
    # already been re-entered this session. Both feed the runaway guards added
    # 3 Aug. Defaults are the "never stopped out here" case, so a caller that
    # does not set them behaves exactly as before.
    stopped_out_ago_sec: Optional[int] = None
    reentries_so_far: int = 0

    @property
    def spread(self) -> int:
        return self.ask - self.bid

    @property
    def ahead_on_sets(self) -> bool:
        return self.sets_won > self.sets_lost


@dataclass
class Decision:
    take: bool
    setup: Optional[Setup] = None
    reasons: list[tuple[str, str]] = field(default_factory=list)

    contracts: int = 0
    cost: float = 0.0
    entry_price: int = 0
    resting_buy: int = 0
    target_price: int = 0
    exit_price: int = 0
    loss_if_exit: float = 0.0
    loss_if_held: float = 0.0
    breakeven_with_exit: float = 0.0
    breakeven_holding: float = 0.0


# ----------------------------------------------------------------------
# money
# ----------------------------------------------------------------------

def fee(cfg: Config, contracts: int, price_cents: int) -> float:
    p = price_cents / 100
    return math.ceil(cfg.fee_rate * contracts * p * (1 - p) * 100) / 100


def target_for_profit(cfg: Config, contracts: int, entry: int, goal: float) -> int:
    """Cheapest exit price (cents) netting `goal` dollars after both fees."""
    x = entry + goal / contracts * 100
    for _ in range(40):
        net = (contracts * x / 100 - fee(cfg, contracts, round(x))
               - contracts * entry / 100 - fee(cfg, contracts, entry))
        if abs(net - goal) < 0.005:
            break
        x += (goal - net) / contracts * 100
        if x > 99:
            return 99
    return min(99, math.ceil(x))


# ----------------------------------------------------------------------
# the rules
# ----------------------------------------------------------------------

def evaluate(cfg: Config, s: Snapshot) -> Decision:
    d = Decision(take=True)
    ok = lambda t: d.reasons.append(("ok", t))
    bad = lambda t: (d.reasons.append(("bad", t)), setattr(d, "take", False))
    warn = lambda t: d.reasons.append(("warn", t))

    # --- hygiene: things that kill a trade regardless of the setup -----
    if s.postponed:
        bad("Match postponed. Capital locks up and withdrawal resolves you to No.")
    if not s.market_open:
        bad("Market not open.")
    if s.score_age_sec > cfg.max_score_age_sec:
        bad(f"Score is {s.score_age_sec}s stale (limit {cfg.max_score_age_sec}s).")
    if s.already_hold_other_side:
        bad("You already hold the other side. Sell that instead of hedging it.")
    cap = cfg.max_open_positions + (cfg.reentry_slots if s.is_reentry else 0)
    if s.open_positions >= cap:
        if s.is_reentry:
            bad(f"{s.open_positions} positions open — even the re-entry "
                f"reserve is full (limit {cap}).")
        else:
            bad(f"{s.open_positions} positions already open "
                f"(limit {cfg.max_open_positions}; "
                f"{cfg.reentry_slots} more are reserved for re-entries).")
    elif s.is_reentry and s.open_positions >= cfg.max_open_positions:
        ok(f"Re-entry using a reserved slot ({s.open_positions}/{cap}).")
    if cfg.max_daily_loss_pct > 0 and s.daily_pnl_pct <= -cfg.max_daily_loss_pct:
        bad(f"Down {abs(s.daily_pnl_pct):.0f}% today. Daily limit hit — done trading.")

    # --- runaway guards (3 Aug, see Config for the SAGLEV post-mortem) ----
    if s.is_reentry:
        if s.reentries_so_far >= cfg.max_reentries_per_event:
            bad(f"Already re-entered this match {s.reentries_so_far}x "
                f"(limit {cfg.max_reentries_per_event}). Three legs into one "
                f"falling market is how 64 contracts happened.")
        if (s.stopped_out_ago_sec is not None
                and s.stopped_out_ago_sec < cfg.reentry_cooldown_sec):
            bad(f"Stopped out of this match {s.stopped_out_ago_sec}s ago — "
                f"cooling off for {cfg.reentry_cooldown_sec}s. A 2c bounce off "
                f"your own stop is noise, not a recovery.")
        else:
            ok("Re-entry cooldown satisfied.")
        if cfg.reentry_respects_price_floor and s.ask < cfg.min_entry_price:
            bad(f"Re-entry at {s.ask}c is below the {cfg.min_entry_price}c "
                f"entry floor. The floor applies to re-entries too.")

    # --- match stage ---------------------------------------------------
    if cfg.require_set_resolved and s.sets_won == 0 and s.sets_lost == 0:
        bad("No set resolved yet. Your rule: don't enter during set 1.")
    else:
        ok("A set has resolved.")

    # --- set quality: HOW they got ahead, not just that they did ---------
    # Applies to both setups. On the favourite side it stops us paying up for
    # a tiebreak. On the divergence side it stops us buying an underdog who
    # "broke through" by winning a 7-6 — the favourite losing a tiebreak is
    # not the same evidence as the favourite being outplayed 6-3.
    won_sets = [(a, b) for a, b in s.set_scores if a > b]
    if s.set_scores:
        if not won_sets:
            pass                       # handled by the ahead_on_sets checks
        else:
            best = max(a - b for a, b in won_sets)
            if best < cfg.min_set_margin:
                bad(f"Best set won by only {best} game(s) — a tiebreak is a "
                    f"coin flip, not evidence. Need a {cfg.min_set_margin}-game margin.")
            else:
                ok(f"Won a set by {best} games — decisive.")

    # --- which setup is this? -------------------------------------------
    # A market that opened between the two thresholds had no clear favourite,
    # so it takes the stricter divergence path rather than being waved through
    # on a 1c difference either side of 50.
    d.setup = Setup.FAVORITE if s.was_prematch_favorite else Setup.DIVERGENCE

    # Price floor applies to BOTH paths. Every band below it lost money live.
    if s.ask < cfg.min_entry_price:
        bad(f"{s.ask}c is below the {cfg.min_entry_price}c floor — everything "
            f"cheaper than this lost money over 125 settled markets.")

    if d.setup is Setup.FAVORITE:
        if s.ask >= cfg.max_favorite_price:
            bad(f"{s.ask}c favorite — too little room, fees eat the move.")
        elif s.ask >= cfg.thin_favorite_price:
            warn(f"{s.ask}c — thin upside. Only works if you take the exit.")
        else:
            ok(f"{s.ask}c favorite — room to run.")
        if not s.ahead_on_sets:
            bad("Favorite isn't ahead on sets. No reason to pay favorite prices.")
    else:
        if s.ask >= cfg.max_divergence_price:
            bad(f"{s.ask}c — market already repriced. Nothing left to capture.")
        elif not s.ahead_on_sets:
            bad("Not ahead on sets. The reversal hasn't happened yet — it's happening.")
        else:
            ok(f"{s.ask}c and ahead on sets — divergence intact.")

    # --- liquidity -------------------------------------------------------
    if s.spread > cfg.max_spread:
        bad(f"Spread is {s.spread}c. Round trip costs more than the edge.")
    elif s.spread > cfg.warn_spread:
        warn(f"Spread {s.spread}c — wide. Size down or skip.")
    else:
        ok(f"Spread {s.spread}c.")

    if not d.take:
        return d

    # --- sizing and orders ------------------------------------------------
    stake = cfg.bankroll * cfg.stake_pct / 100
    qty = max(1, int(stake / (s.ask / 100)))
    # A fixed-dollar stake buys more contracts the cheaper the market gets, so
    # this is the brake that stops a falling price inflating the position.
    # 3 Aug: without it, 49c -> 31c -> 19c produced 12 -> 20 -> 32 contracts.
    if qty > cfg.max_contracts:
        warn(f"Size capped at {cfg.max_contracts} (the stake would have "
             f"bought {qty} at {s.ask}c).")
        qty = cfg.max_contracts
    if qty > s.depth_at_ask:
        qty = s.depth_at_ask
        warn(f"Only {s.depth_at_ask} available — size capped by the book.")

    cost = qty * s.ask / 100 + fee(cfg, qty, s.ask)

    if d.setup is Setup.FAVORITE:
        # Rest at 95c rather than the ~88c the percentage rule gives. See the
        # note on favorite_target_price: 94.3% of markets that reached 92c
        # settled at 100, so the old target was selling too early.
        target = max(cfg.favorite_target_price,
                     target_for_profit(cfg, qty, s.ask, cost * cfg.favorite_target_pct))
        target = min(99, target)
        exit_px = max(1, s.ask - cfg.favorite_exit_drop)
    else:
        target = target_for_profit(cfg, qty, s.ask, cost * cfg.divergence_target_pct)
        exit_px = max(1, round(s.ask * (1 - cfg.divergence_exit_pct)))

    loss_if_exit = cost - (qty * exit_px / 100 - fee(cfg, qty, exit_px))
    gain = qty * target / 100 - fee(cfg, qty, target) - cost

    d.contracts, d.cost, d.entry_price = qty, cost, s.ask
    d.resting_buy = max(1, s.ask - 3)
    d.target_price, d.exit_price = target, exit_px
    d.loss_if_exit, d.loss_if_held = loss_if_exit, cost
    d.breakeven_with_exit = loss_if_exit / (loss_if_exit + gain) * 100
    d.breakeven_holding = cost / (cost + gain) * 100
    return d


# ----------------------------------------------------------------------
# output
# ----------------------------------------------------------------------

def render(d: Decision, s: Snapshot) -> str:
    mark = {"ok": "  [+]", "bad": "  [X]", "warn": "  [!]"}
    head = "TAKE IT" if d.take else "NO TRADE"
    out = [f"\n{s.player} — {s.match}", "=" * 58, head]
    if d.setup:
        out.append(f"setup: {d.setup.value}")
    out.append("")
    out += [f"{mark[k]} {t}" for k, t in d.reasons]

    if not d.take:
        out.append("\n  Passing is free.\n")
        return "\n".join(out)

    out += [
        "",
        "-" * 58,
        f"  buy               {d.contracts} @ {d.entry_price}c   (${d.cost:.2f})",
        f"  resting buy       {d.resting_buy}c   — better fill if it dips",
        f"  resting sell      {d.target_price}c   <- place this immediately",
        f"  exit if it hits   {d.exit_price}c   — manual, Kalshi has no stops",
        "-" * 58,
        f"  loss if you exit      ${d.loss_if_exit:.2f}",
        f"  loss if you hold      ${d.loss_if_held:.2f}",
        f"  win rate needed, exit  {d.breakeven_with_exit:.0f}%",
        f"  win rate needed, hold  {d.breakeven_holding:.0f}%",
        "",
        "  The exit is the strategy. Same trade either way.",
        "",
    ]
    return "\n".join(out)


DEMOS = [
    ("your Shibahara trade", Snapshot(
        player="Shibahara", match="vs Dong",
        ask=60, bid=58, sets_won=1, sets_lost=0,
        set_in_progress=True, was_prematch_favorite=False)),
    ("a 75c favorite, up a set", Snapshot(
        player="Svajda", match="vs Hewitt",
        ask=75, bid=73, sets_won=1, sets_lost=0,
        was_prematch_favorite=True)),
    ("Blockx, down a set", Snapshot(
        player="Blockx", match="vs Van Assche",
        ask=24, bid=22, sets_won=0, sets_lost=1,
        was_prematch_favorite=False)),
    ("an 88c favorite", Snapshot(
        player="McKennon", match="vs Filiz",
        ask=88, bid=85, sets_won=1, sets_lost=0,
        was_prematch_favorite=True)),
]


def main() -> None:
    ap = argparse.ArgumentParser(description="Kalshi tennis decision engine")
    ap.add_argument("--demo", action="store_true", help="run the example snapshots")
    ap.add_argument("--bankroll", type=float, default=110.0)
    ap.add_argument("--stake-pct", type=float, default=5.0)
    args = ap.parse_args()

    cfg = Config(bankroll=args.bankroll, stake_pct=args.stake_pct)

    if args.demo:
        for label, snap in DEMOS:
            print(f"\n### {label}")
            print(render(evaluate(cfg, snap), snap))
        return

    print(__doc__)
    print("Import Snapshot and evaluate(), or run with --demo.")


if __name__ == "__main__":
    main()
