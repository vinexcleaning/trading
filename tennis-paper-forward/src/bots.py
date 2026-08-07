"""bots.py — sixteen dispositions, one shared match pool.

THE SPECIFICATION, RESTATED SO THE CODE CAN BE CHECKED AGAINST IT
    Five mentalities x three exit modes = fifteen bots, plus a no-trade
    control. All sixteen see the SAME pool on the same tick. None is forced
    to enter anything. A mentality is a disposition, not a rule: each one owns
    several tactics and decides for itself which apply to the match in front
    of it, including deciding that none do.

    That is implemented literally. A `Mentality` produces a `Deliberation`
    containing every consideration it weighed - the ones that argued for the
    trade AND the ones that argued against - a conviction score, and a plain
    English rationale. The rationale is written to disk before the match
    finishes. Nothing about the result is available to any of this code at
    decision time; the only outcome-bearing field on a Quote is `result`, and
    a market carrying a result is filtered out of the pool before the bots
    ever see it.

WHY THE TACTICS ARE THE ONES THEY ARE
    Each mentality is loaded with what this repo already measured about it,
    so the bots argue with the archive rather than rediscovering it:

      favourite   knows "buy the heavy favourite" was +3.12c at the mid and
                  +0.96c -> -0.77c at real prices, and that the apparent edge
                  GREW with the spread - +1.18c where the quote was tight
                  enough to trade and +7.92c where it was wider than 8c. So it
                  treats a wide quote as a reason to decline, not a bargain.

      underdog    knows a 2.18c loss on a 5c contract is 44% of the stake, and
                  that buying every longshot at the open lost 5.42c. So its
                  required edge scales up as the price falls.

      brief-led   uses the three-number check found in the video corpus:
                  edge = fair - price - cost, and "agreeing with the market is
                  a losing strategy because you pay the spread for fair odds".

      momentum    is the only one that needs a tape, so it cannot act on its
                  first sight of a market. It also knows the archive's
                  esports "follow the price move" result was +7.78c with a
                  lower bound of -2.02c on 83 matches - a shrug, not a signal.

      unconstrained  has no band and no house view. It runs the other four and
                  keeps every EVIDENTIAL consideration they produced while
                  discarding the DISPOSITIONAL ones - "this price is outside my
                  band" is a fact about a bot, not about a match. It is the
                  only one that can buy a 4c longshot and a 96c favourite on
                  the same tick, and the only one that compares the two sides
                  of a match against each other rather than each against a
                  band.

HOW MUCH, NOT JUST WHETHER
    Every bot also chooses its own stake from its own confidence, inside a
    fixed bankroll it never tops up, and the stake and its reasoning go into
    the same log as the decision. That is what lets selection and sizing be
    scored apart afterwards - mean profit per CONTRACT is selection, and
    whether stake-weighting beats equal-weighting is sizing. See sizing.py,
    which also explains why this is the most dangerous part of the design.

    None of that makes any of them right. It makes their reasoning auditable.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable

from .brief import Brief
from .engine import PaperEngine, Position, hold_cost_cents, round_trip_cost_cents
from .kalshi_read import MatchView
from .sizing import BANKROLL_CENTS, Stake, choose_stake

# The one shared fee implementation. GUARDS #6b - this file contains no fee
# arithmetic of its own, only calls into it.
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
from common.kalshi_fees import fee_rate_cents as _fee_rate_cents  # noqa: E402

# --------------------------------------------------------------------------
# The live tape each bot may consult
# --------------------------------------------------------------------------


@dataclass
class Tick:
    ts: str
    yes_ask: int | None
    yes_bid: int | None
    last: int | None
    volume: float | None


@dataclass
class LiveState:
    """Everything observable about one event, other than the brief."""
    event_ticker: str
    ticker: str
    ticks: list[Tick] = field(default_factory=list)
    first_seen: str = ""

    def push(self, mv: MatchView) -> None:
        q = mv.primary
        if not self.first_seen:
            self.first_seen = q.fetched_at
            self.ticker = q.ticker
        self.ticks.append(Tick(q.fetched_at, q.yes_ask, q.yes_bid, q.last, q.volume))
        if len(self.ticks) > 400:
            del self.ticks[:-400]

    def n(self) -> int:
        return len(self.ticks)

    def move(self, k: int = 5) -> int | None:
        """Change in the ask over the last k ticks, in cents."""
        pts = [t.yes_ask for t in self.ticks if t.yes_ask is not None]
        if len(pts) <= k:
            return None
        return pts[-1] - pts[-1 - k]

    def range(self, k: int = 20) -> int | None:
        pts = [t.yes_ask for t in self.ticks[-k:] if t.yes_ask is not None]
        if len(pts) < 3:
            return None
        return max(pts) - min(pts)

    def volume_delta(self, k: int = 5) -> float | None:
        vs = [t.volume for t in self.ticks if t.volume is not None]
        if len(vs) <= k:
            return None
        return vs[-1] - vs[-1 - k]

    def stale_ticks(self) -> int:
        """How many consecutive ticks the ask has not moved."""
        n = 0
        pts = [t.yes_ask for t in self.ticks if t.yes_ask is not None]
        for i in range(len(pts) - 1, 0, -1):
            if pts[i] == pts[i - 1]:
                n += 1
            else:
                break
        return n

    def open_ask(self) -> int | None:
        for t in self.ticks:
            if t.yes_ask is not None:
                return t.yes_ask
        return None


# --------------------------------------------------------------------------
# Deliberation — what a bot thought, written down before the result exists
# --------------------------------------------------------------------------


@dataclass
class Consideration:
    tactic: str
    reading: str          # plain English, no jargon
    direction: str        # "for" | "against" | "neutral"
    weight: float


@dataclass
class Deliberation:
    decision_id: str
    ts: str
    bot: str
    mentality: str
    exit_mode: str
    event_ticker: str
    brief_digest: str
    side_ticker: str | None
    side_player: str | None
    price_at_decision: int | None
    spread_at_decision: int | None
    cost_bar_cents: float | None
    considerations: list[Consideration]
    conviction: float
    action: str           # "enter" | "hold" | "exit" | "reenter" | "pass"
    rationale: str
    expectation: str      # what the bot expects to happen, in advance
    outcome_known: bool = False   # ALWAYS False when written
    repeated_unchanged: int = 0   # ticks this identical verdict was held
    # -- the sizing decision, logged on every trade so that sizing skill and
    #    selection skill can be measured apart afterwards
    contracts: int | None = None
    stake_cents: int | None = None
    stake_fraction: float | None = None
    sizing_basis: str | None = None
    kelly_full: float | None = None
    edge_cents: float | None = None
    sizing_rationale: str | None = None
    sizing_caps: list[str] = field(default_factory=list)
    p_size: float | None = None   # the probability the stake was actually sized on
    bankroll_cents: int | None = None
    open_exposure_cents: int | None = None

    def to_json(self) -> str:
        d = asdict(self)
        d["considerations"] = [asdict(c) if not isinstance(c, dict) else c
                               for c in self.considerations]
        return json.dumps(d, default=str)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _v(node: Any, default=None):
    """Pull `.value` out of a {value, n} block, tolerating None."""
    if isinstance(node, dict):
        return node.get("value", default)
    return default if node is None else node


def _n(node: Any) -> int:
    return int(node.get("n", 0)) if isinstance(node, dict) else 0


def _pct(x: float | None) -> str:
    return "unknown" if x is None else f"{100*x:.0f}%"


# --------------------------------------------------------------------------
# Mentalities
# --------------------------------------------------------------------------


class Mentality:
    name = "base"
    # Conviction a deliberation must reach before it is worth an entry at all.
    # Not a p-value and not calibrated - a disposition threshold, declared in
    # PREREGISTRATION.md before the run.
    enter_at = 1.0

    def sides(self, mv: MatchView, brief: Brief) -> list[tuple[str, str, int, int]]:
        """(ticker, player, ask, spread) for every quotable side of the event."""
        out = []
        for q in (mv.primary, mv.mirror):
            if q is not None and q.is_quotable():
                out.append((q.ticker, q.player, q.yes_ask, q.spread))
        return out

    def consider(self, mv: MatchView, brief: Brief, live: LiveState,
                 ticker: str, player: str, ask: int, spread: int
                 ) -> tuple[list[Consideration], str]:
        raise NotImplementedError

    # -- shared tactics ----------------------------------------------------

    def _side_block(self, brief: Brief, player: str) -> dict:
        from .sackmann import norm_name
        return brief.a if norm_name(player) == norm_name(brief.player_a) else brief.b

    def _opp_block(self, brief: Brief, player: str) -> dict:
        from .sackmann import norm_name
        return brief.b if norm_name(player) == norm_name(brief.player_a) else brief.a

    def _fair_for(self, brief: Brief, player: str) -> float | None:
        from .sackmann import norm_name
        p = brief.model.get("elo_prob_a_surface") or brief.model.get("elo_prob_a")
        if p is None:
            return None
        return p if norm_name(player) == norm_name(brief.player_a) else 1.0 - p

    def _data_penalty(self, brief: Brief, blk: dict, opp: dict) -> list[Consideration]:
        c: list[Consideration] = []
        if not blk.get("resolved") or not opp.get("resolved"):
            c.append(Consideration(
                "unresolved_player",
                "at least one player is not in the free archive, so every history "
                "figure below is missing rather than bad",
                "against", 2.0))
        if brief.staleness_days and brief.staleness_days > 21:
            c.append(Consideration(
                "stale_form",
                f"the free archive stops {brief.staleness_days} days ago, so 'recent "
                f"form' is form as of then, not as of this week",
                "against", 0.6 + min(1.4, brief.staleness_days / 60.0)))
        if brief.surface is None:
            c.append(Consideration(
                "surface_unknown",
                "the tournament is not in the surface lookup, so the surface record "
                "below is the all-surface record",
                "against", 0.5))
        if brief.market.get("stale_book"):
            c.append(Consideration(
                "stale_book",
                "the two bids on this match sum to more than a dollar, which cannot be "
                "true - one side of the book is stale, so neither price is trusted",
                "against", 3.0))
        return c


class FavouriteMentality(Mentality):
    name = "favourite"
    enter_at = 2.0
    FLOOR = 80

    def consider(self, mv, brief, live, ticker, player, ask, spread):
        c: list[Consideration] = []
        blk, opp = self._side_block(brief, player), self._opp_block(brief, player)
        c += self._data_penalty(brief, blk, opp)

        if ask < self.FLOOR:
            c.append(Consideration("price_band",
                f"{ask}c is below the 80c floor this disposition trades", "against", 5.0))
            return c, f"{player} is priced at {ask}c, under the 80c floor."
        c.append(Consideration("price_band",
            f"{ask}c is a heavy favourite, which is the only thing this disposition buys",
            "for", 1.5))

        # The archive's warning, applied by the bot to itself.
        bar = hold_cost_cents(ask, spread)
        if spread >= 4:
            c.append(Consideration("wide_quote",
                f"the quote is {spread}c wide. This repo measured the heavy-favourite "
                f"'edge' at +1.18c where the gap was 2c or less and +7.92c where it was "
                f"over 8c - it grows exactly where you cannot trade it, which means it "
                f"is the gap, not an edge. Declining.",
                "against", 4.0))
        elif spread <= 2:
            c.append(Consideration("tight_quote",
                f"the quote is {spread}c wide, tight enough that the price is a price. "
                f"Cost to break even holding to the end is {bar:.2f}c.",
                "for", 1.2))
        else:
            c.append(Consideration("quote_width",
                f"{spread}c wide - tradeable but not cheap; cost bar {bar:.2f}c.",
                "neutral", 0.0))

        fair = self._fair_for(brief, player)
        if fair is not None:
            edge = 100 * fair - ask - bar
            d = "for" if edge > 0 else "against"
            c.append(Consideration("evidence_vs_price",
                f"the archive's own rating makes {player} a {_pct(fair)} chance against "
                f"a {ask}c price and a {bar:.2f}c cost, so the edge as measured is "
                f"{edge:+.2f}c",
                d, min(3.0, abs(edge) / 3.0)))

        surf = blk.get("surface") or {}
        if _n(surf) >= 15:
            c.append(Consideration("surface_record",
                f"on {surf.get('which')} the record is {surf.get('w')}-{_n(surf)-surf.get('w',0)} "
                f"({_pct(_v(surf))}) over {_n(surf)} matches",
                "for" if (_v(surf) or 0) > 0.6 else "against", 0.8))
        else:
            c.append(Consideration("surface_record",
                f"only {_n(surf)} matches on this surface - too few to lean on", "neutral", 0.0))

        dec = blk.get("deciding_set") or {}
        if _n(dec) >= 20:
            c.append(Consideration("third_set",
                f"in matches that reached a deciding set the record is {dec.get('w')}-"
                f"{_n(dec)-dec.get('w',0)} ({_pct(_v(dec))}, n={_n(dec)}) - this matters "
                f"because a favourite's whole risk is the match going long",
                "for" if (_v(dec) or 0) >= 0.55 else "against", 0.9))

        ret = blk.get("retired_rate") or {}
        if _n(ret) >= 40 and (_v(ret) or 0) > 0.04:
            c.append(Consideration("attrition",
                f"retires from {_pct(_v(ret))} of matches (n={_n(ret)}) - at {ask}c "
                f"there is very little to win and a retirement loses all of it",
                "against", 1.5))

        rest = blk.get("days_since_last_match")
        load = blk.get("matches_last_28d")
        if rest is not None and rest > 45:
            c.append(Consideration("rust",
                f"has not played for {rest} days by the archive's reckoning", "against", 0.8))
        if load is not None and load >= 9:
            c.append(Consideration("workload",
                f"{load} matches in the last 28 days of the archive - heavy legs",
                "against", 0.6))

        rat = f"{player} at {ask}c, {spread}c wide, cost bar {bar:.2f}c."
        return c, rat


class UnderdogMentality(Mentality):
    name = "underdog"
    enter_at = 2.0
    LO, HI = 5, 35

    def consider(self, mv, brief, live, ticker, player, ask, spread):
        c: list[Consideration] = []
        blk, opp = self._side_block(brief, player), self._opp_block(brief, player)
        c += self._data_penalty(brief, blk, opp)

        if not (self.LO <= ask <= self.HI):
            c.append(Consideration("price_band",
                f"{ask}c is outside the {self.LO}-{self.HI}c band this disposition trades",
                "against", 5.0))
            return c, f"{player} at {ask}c is outside the underdog band."

        bar = hold_cost_cents(ask, spread)
        stake_frac = bar / max(1, ask)
        c.append(Consideration("cheap_ticket_tax",
            f"at {ask}c the {bar:.2f}c cost bar is {100*stake_frac:.1f}% of the ticket. "
            f"This repo measured the same shape on crypto: a 2.18c loss on a 5c contract "
            f"is 44% of the stake. Cheap is not the same as good value.",
            "against", min(3.0, 8.0 * stake_frac)))

        fair = self._fair_for(brief, player)
        if fair is None:
            c.append(Consideration("no_fair_value",
                "no rating is computable for this pair, so there is nothing to compare "
                "the price to and 'cheap' is the only argument left - which is not one",
                "against", 3.0))
        else:
            edge = 100 * fair - ask - bar
            c.append(Consideration("evidence_vs_price",
                f"the archive makes {player} a {_pct(fair)} chance; at {ask}c with a "
                f"{bar:.2f}c cost the edge is {edge:+.2f}c",
                "for" if edge > 0 else "against", min(3.5, abs(edge) / 2.5)))
            if 0 < edge < 3.0:
                c.append(Consideration("edge_smaller_than_the_error",
                    f"a {edge:.2f}c edge on a {ask}c contract is inside the noise of "
                    f"everything this brief is built from. Nine threads in this repo "
                    f"died as 'a real effect smaller than the cost of reaching it'.",
                    "against", 1.5))

        h = brief.h2h or {}
        if h.get("n", 0) >= 3:
            mine = h["a_wins"] if player == brief.player_a else h["b_wins"]
            c.append(Consideration("head_to_head",
                f"they have met {h['n']} times and {player} has won {mine}",
                "for" if mine * 2 > h["n"] else "against", 0.8))

        rls = blk.get("response_after_losing_serve") or {}
        d = rls.get("break_back_vs_control")
        if d is not None and rls.get("break_back_immediately", {}).get("n", 0) >= 40:
            # measured against the MATCHED control (what happens after a hold),
            # and then against the population mean of that controlled quantity,
            # which is -0.0333. A player who is merely at -0.03 is average.
            rel = d - (-0.0333)
            c.append(Consideration("response_after_losing_serve",
                f"after being broken, breaks straight back {_pct(rls['break_back_immediately']['value'])} "
                f"of the time against {_pct(rls.get('control_break_after_hold', {}).get('value'))} "
                f"after a hold in the same matches ({d:+.3f} over "
                f"{rls['break_back_immediately']['n']} occasions). Every charted player is "
                f"negative here on average ({-0.0333:+.4f}), so what matters is the "
                f"{rel:+.3f} departure from that, not the sign.",
                "for" if rel > 0.015 else "against", min(1.5, abs(rel) * 25)))

        form = blk.get("form_last10") or {}
        if _n(form) >= 8:
            c.append(Consideration("recent_form",
                f"won {form.get('w')} of the last {_n(form)} in the archive ({_pct(_v(form))})",
                "for" if (_v(form) or 0) >= 0.6 else "against", 0.7))

        dec = blk.get("deciding_set") or {}
        if _n(dec) >= 20 and (_v(dec) or 0) >= 0.55:
            c.append(Consideration("third_set",
                f"wins {_pct(_v(dec))} of deciding sets (n={_n(dec)}) - the way an "
                f"underdog actually wins is by surviving to one",
                "for", 1.0))

        return c, f"{player} at {ask}c, {spread}c wide, cost bar {bar:.2f}c."


class BriefLedMentality(Mentality):
    name = "brief-led"
    enter_at = 2.5

    def consider(self, mv, brief, live, ticker, player, ask, spread):
        c: list[Consideration] = []
        blk, opp = self._side_block(brief, player), self._opp_block(brief, player)
        c += self._data_penalty(brief, blk, opp)

        bar = hold_cost_cents(ask, spread)
        fair = self._fair_for(brief, player)
        if fair is None:
            c.append(Consideration("no_fair_value",
                "this disposition trades the gap between the brief and the price. "
                "There is no computable brief estimate here, so there is no gap to "
                "trade and it passes.", "against", 6.0))
            return c, "no fair value computable"

        edge = 100 * fair - ask - bar
        c.append(Consideration("three_number_check",
            f"edge = fair - price - cost = {100*fair:.1f} - {ask} - {bar:.2f} = {edge:+.2f}c. "
            f"Trade only on a clearly positive number; agreeing with the market is a "
            f"losing strategy because you pay the spread for fair odds.",
            "for" if edge > 0 else "against", min(4.0, abs(edge) / 2.0)))

        # Evidence weight: how much of the brief is actually there.
        support = 0.0
        surf = blk.get("surface") or {}
        osurf = opp.get("surface") or {}
        if _n(surf) >= 15 and _n(osurf) >= 15:
            gap = (_v(surf) or 0) - (_v(osurf) or 0)
            support += 1.0
            c.append(Consideration("surface_record",
                f"on {brief.surface}: {_pct(_v(surf))} (n={_n(surf)}) against "
                f"{_pct(_v(osurf))} (n={_n(osurf)}) - a {gap:+.3f} gap",
                "for" if gap * (1 if edge > 0 else -1) > 0 else "against",
                min(1.5, abs(gap) * 6)))

        f_me, f_op = blk.get("form_last20") or {}, opp.get("form_last20") or {}
        if _n(f_me) >= 12 and _n(f_op) >= 12:
            gap = (_v(f_me) or 0) - (_v(f_op) or 0)
            support += 1.0
            c.append(Consideration("recent_form",
                f"last {_n(f_me)}: {_pct(_v(f_me))} against {_pct(_v(f_op))} over "
                f"{_n(f_op)} - a {gap:+.3f} gap, as of {brief.staleness_days} days ago",
                "for" if gap > 0 else "against", min(1.2, abs(gap) * 4)))

        d_me, d_op = blk.get("deciding_set") or {}, opp.get("deciding_set") or {}
        if _n(d_me) >= 20 and _n(d_op) >= 20:
            gap = (_v(d_me) or 0) - (_v(d_op) or 0)
            support += 1.0
            c.append(Consideration("third_set",
                f"deciding sets: {_pct(_v(d_me))} (n={_n(d_me)}) against {_pct(_v(d_op))} "
                f"(n={_n(d_op)})", "for" if gap > 0 else "against", min(1.2, abs(gap) * 5)))

        r_me = blk.get("response_after_losing_serve") or {}
        r_op = opp.get("response_after_losing_serve") or {}
        n_me = (r_me.get("break_back_immediately") or {}).get("n", 0)
        n_op = (r_op.get("break_back_immediately") or {}).get("n", 0)
        if n_me >= 40 and n_op >= 40:
            support += 1.0
            me_d = r_me.get("break_back_vs_control") or 0.0
            op_d = r_op.get("break_back_vs_control") or 0.0
            gap = me_d - op_d
            c.append(Consideration("response_after_losing_serve",
                f"break-back rate against the matched after-a-hold control: {me_d:+.3f} "
                f"(n={n_me}) against {op_d:+.3f} (n={n_op}) - a {gap:+.3f} gap. Both are "
                f"normally negative; the population mean is -0.0333.",
                "for" if gap > 0 else "against", min(1.0, abs(gap) * 20)))
        else:
            c.append(Consideration("response_after_losing_serve",
                f"point-by-point coverage is {n_me} and {n_op} occasions - absent, not zero. "
                f"This field is unavailable for most Challenger and ITF players.",
                "neutral", 0.0))

        h = brief.h2h or {}
        if h.get("n", 0) >= 3:
            support += 0.5
            mine = h["a_wins"] if player == brief.player_a else h["b_wins"]
            c.append(Consideration("head_to_head",
                f"{mine} of {h['n']} previous meetings",
                "for" if mine * 2 > h["n"] else "against", 0.6))

        if support < 2.0:
            c.append(Consideration("thin_brief",
                f"only {support:.1f} of the brief's evidence blocks have enough matches "
                f"behind them to be worth reading. A gap computed from a thin brief is a "
                f"gap in the brief, not in the price.",
                "against", 2.0))

        return c, f"{player} at {ask}c; brief says {_pct(fair)}; edge {edge:+.2f}c."


class MomentumMentality(Mentality):
    name = "momentum"
    enter_at = 2.5
    MIN_TICKS = 6

    def consider(self, mv, brief, live, ticker, player, ask, spread):
        c: list[Consideration] = []
        blk, opp = self._side_block(brief, player), self._opp_block(brief, player)
        c += self._data_penalty(brief, blk, opp)

        if live.n() < self.MIN_TICKS:
            c.append(Consideration("no_tape",
                f"only {live.n()} observations of this market so far; this disposition "
                f"needs {self.MIN_TICKS} before it has anything to follow",
                "against", 6.0))
            return c, "not enough tape yet"

        mv5 = live.move(5)
        if mv5 is None:
            c.append(Consideration("no_tape", "the ask has not been quotable long enough",
                                   "against", 6.0))
            return c, "no usable tape"

        # The tape is for the PRIMARY ticker; the mirror moves the other way.
        signed = mv5 if ticker == live.ticker else -mv5
        bar = round_trip_cost_cents(ask, spread)
        c.append(Consideration("price_move",
            f"the price on this side has moved {signed:+d}c over the last 5 observations. "
            f"A round trip costs {bar:.2f}c, so the move has to be worth more than that "
            f"before following it is anything but paying the spread twice.",
            "for" if signed >= 3 else "against", min(3.0, abs(signed) / 2.0)))

        if 0 < signed < bar:
            c.append(Consideration("move_inside_the_cost",
                f"the whole move is {signed}c and the round trip is {bar:.2f}c - "
                f"following it cannot pay even if it continues",
                "against", 2.5))

        rng = live.range(20)
        if rng is not None and rng >= 6 and abs(signed) < rng / 3:
            c.append(Consideration("chop",
                f"the ask has ranged {rng}c over the last 20 observations and the current "
                f"move is only {abs(signed)}c of it - that is chop, not a trend",
                "against", 1.5))

        vd = live.volume_delta(5)
        if vd is not None:
            c.append(Consideration("volume_confirmation",
                f"volume has moved {vd:+.0f} contracts over the same window",
                "for" if vd > 0 else "neutral", 0.6 if vd > 0 else 0.0))

        stale = live.stale_ticks()
        if stale >= 8:
            c.append(Consideration("stale_price",
                f"the ask has not moved for {stale} consecutive observations. This repo's "
                f"esports work found 'buy the stalest price' at +7.96c with a lower bound "
                f"of -1.25c on 70 matches - a shrug, and the opposite of a momentum case.",
                "against", 1.2))

        op = live.open_ask()
        if op is not None:
            c.append(Consideration("move_from_open",
                f"this side has gone {ask - (op if ticker == live.ticker else 100 - op):+d}c "
                f"from where it was first seen",
                "neutral", 0.0))

        c.append(Consideration("archive_prior",
            "the archive's nearest measurement of this idea is 'follow the price move' at "
            "+7.78c with a lower bound of -2.02c over 83 esports matches - it could not "
            "tell. So could this.",
            "neutral", 0.0))

        return c, f"{player} at {ask}c, {signed:+d}c over 5 observations, cost bar {bar:.2f}c."


class UnconstrainedMentality(Mentality):
    """No fixed disposition. Reads everything and takes whatever it judges best.

    It is not a fifth set of tactics bolted on beside the other four - it is
    the other four with their DISPOSITIONS removed. Each of the constrained
    mentalities carries two different kinds of "against": evidence (this
    player's surface record is poor) and disposition (this price is outside my
    band). Only the first is a fact about the match. `_DISPOSITIONAL` names the
    second kind, and this mentality discards exactly those, keeping every
    evidential consideration the other four produced.

    So it can buy a 4c longshot and a 96c favourite on the same tick if that is
    what the evidence says, and it is the only one that can. It also compares
    the two sides of a match against each other, which none of the constrained
    four do - they each evaluate a side in isolation against their own band.
    """
    name = "unconstrained"
    enter_at = 3.5

    # Tactic names whose "against" verdict is a statement about the bot rather
    # than about the match. Dropped here; kept everywhere else.
    _DISPOSITIONAL = {"price_band", "no_tape"}
    # ...and tactics that ARE evidential but which a specialist over-weights
    # because its whole case rests on them. Capped, not dropped.
    _CAPPED = {"no_fair_value": 2.5, "cheap_ticket_tax": 1.5,
               "move_inside_the_cost": 1.5}

    def __init__(self):
        self._panel = (FavouriteMentality(), UnderdogMentality(),
                       BriefLedMentality(), MomentumMentality())

    def consider(self, mv, brief, live, ticker, player, ask, spread):
        merged: dict[str, Consideration] = {}
        for m in self._panel:
            cons, _ = m.consider(mv, brief, live, ticker, player, ask, spread)
            for c in cons:
                if c.tactic in self._DISPOSITIONAL and c.direction == "against":
                    continue
                w = c.weight
                cap = self._CAPPED.get(c.tactic)
                if cap is not None:
                    w = min(w, cap)
                cur = merged.get(c.tactic)
                # dedupe by tactic, keeping the strongest reading. Summing the
                # four panels' overlapping tactics would triple-count the same
                # fact - four bots reading the same surface record is one
                # surface record.
                if cur is None or w > cur.weight:
                    merged[c.tactic] = Consideration(c.tactic, c.reading, c.direction, w)
        c = list(merged.values())

        # its own tactics, which none of the four have
        bar = hold_cost_cents(ask, spread)
        fair = self._fair_for(brief, player)
        other = None
        for q in (mv.primary, mv.mirror):
            if q is not None and q.ticker != ticker and q.is_quotable():
                other = q
        if fair is not None and other is not None:
            mine = 100 * fair - ask - bar
            obar = hold_cost_cents(other.yes_ask, other.spread)
            theirs = 100 * (1 - fair) - other.yes_ask - obar
            better = mine >= theirs
            c.append(Consideration("side_comparison",
                f"this side prices at {ask}c for a {edge_str(mine)} edge; the other side "
                f"prices at {other.yes_ask}c for {edge_str(theirs)}. Taking the better of "
                f"the two is the whole advantage of not having a band - but note both can "
                f"be negative, and usually are, because the pair costs more than a dollar.",
                "for" if better and mine > 0 else "against",
                1.2 if (better and mine > 0) else 1.2))
        if fair is None:
            c.append(Consideration("no_estimate",
                "with no computable estimate there is no evidential case for either side, "
                "and 'no band' is not itself a reason to trade",
                "against", 3.0))

        # the discipline a band was providing, restated as a fact
        if ask <= 8 or ask >= 93:
            c.append(Consideration("extreme_price",
                f"at {ask}c the cost bar of {bar:.2f}c is {100*bar/max(1,min(ask,100-ask)):.0f}% "
                f"of the smaller side of the ticket. Freedom to trade any price is not a "
                f"reason to trade the prices where the fee is worst relative to what is "
                f"at stake.",
                "against", 1.5))
        return c, f"{player} at {ask}c, {spread}c wide, cost bar {bar:.2f}c (unconstrained)."


def edge_str(x: float) -> str:
    return f"{x:+.2f}c"


MENTALITIES: dict[str, Mentality] = {
    m.name: m for m in (FavouriteMentality(), UnderdogMentality(),
                        BriefLedMentality(), MomentumMentality(),
                        UnconstrainedMentality())
}

# --------------------------------------------------------------------------
# Exit modes
# --------------------------------------------------------------------------

EXIT_MODES = ("hold", "exit-once", "free")

# Re-entry protection. The live bot in this repo re-entered a falling market
# 24 seconds after being stopped out, three times, with dollar-based sizing.
# The cooldown and the cap are the two fixes that were verified to refuse all
# three legs. They are declared here and pre-registered.
REENTRY_COOLDOWN_SEC = 900
MAX_ENTRIES_PER_EVENT = 2       # i.e. one re-entry, for the "free" mode only

TAKE_PROFIT_CENTS = 12          # exit on a +12c move in your favour
STOP_CENTS = 12                 # exit on a -12c move against you


@dataclass
class Bot:
    name: str
    mentality: Mentality
    exit_mode: str
    is_control: bool = False

    @property
    def key(self) -> str:
        return self.name


def build_bots() -> list[Bot]:
    bots: list[Bot] = []
    for mname, m in MENTALITIES.items():
        for ex in EXIT_MODES:
            bots.append(Bot(name=f"{mname}__{ex}", mentality=m, exit_mode=ex))
    bots.append(Bot(name="control__no-trade", mentality=BriefLedMentality(),
                    exit_mode="hold", is_control=True))
    return bots


BOT_NAMES = [b.name for b in build_bots()]
assert len(BOT_NAMES) == 16, BOT_NAMES
assert len(MENTALITIES) == 5 and len(EXIT_MODES) == 3
# 5 mentalities x 3 exit modes + 1 control. All sixteen are in the
# multiple-testing denominator; see PREREGISTRATION.md.


# --------------------------------------------------------------------------
# The decision loop
# --------------------------------------------------------------------------


def _score(cons: list[Consideration]) -> float:
    s = 0.0
    for c in cons:
        if c.direction == "for":
            s += c.weight
        elif c.direction == "against":
            s -= c.weight
    return s


def _rationale(bot: Bot, cons: list[Consideration], conviction: float,
               head: str, action: str) -> str:
    fors = [c for c in cons if c.direction == "for"]
    againsts = [c for c in cons if c.direction == "against"]
    lines = [f"[{bot.name}] {head}"]
    lines.append(f"  For ({len(fors)}):")
    for c in sorted(fors, key=lambda x: -x.weight)[:6]:
        lines.append(f"    + ({c.weight:.1f}) {c.tactic}: {c.reading}")
    lines.append(f"  Against ({len(againsts)}):")
    for c in sorted(againsts, key=lambda x: -x.weight)[:6]:
        lines.append(f"    - ({c.weight:.1f}) {c.tactic}: {c.reading}")
    lines.append(f"  Net conviction {conviction:+.2f} against a bar of "
                 f"{bot.mentality.enter_at:.1f} -> {action.upper()}")
    return "\n".join(lines)


class BotRunner:
    """Runs all sixteen dispositions over one shared pool, every tick."""

    def __init__(self, engine: PaperEngine, log: Callable[[Deliberation], None]):
        self.engine = engine
        self.log = log
        self.bots = build_bots()
        self.control_intents: list[dict] = []
        self.last_exit_ts: dict[tuple[str, str], float] = {}

    # -- one tick ----------------------------------------------------------

    def tick(self, pool: list[MatchView], briefs: dict[str, Brief],
             live: dict[str, LiveState]) -> dict[str, int]:
        """Deliberate over everything, THEN commit in order of conviction.

        The first version committed in pool order, which is alphabetical by
        event ticker. With a bankroll that a busy bot exhausts inside one tick,
        that meant the cap fell on whatever happened to come last in the
        alphabet - so the bot's actual selection was partly `sorted()`. It
        looked like selection and was not.

        Two phases now. Everything is deliberated and logged first; then the
        entries are ranked by conviction and queued until the money runs out.
        The ones that miss out are logged as `deferred_no_bankroll`, so the
        record distinguishes "did not want it" from "wanted it and was full".
        """
        counts = {"deliberations": 0, "entries_queued": 0, "exits_queued": 0,
                  "deferred_no_bankroll": 0}
        for bot in self.bots:
            lg = self.engine.ledgers[bot.name]
            candidates: list[tuple[float, Any]] = []
            for mv in pool:
                br = briefs.get(mv.event_ticker)
                ls = live.get(mv.event_ticker)
                if br is None or ls is None:
                    continue
                counts["deliberations"] += 1
                pos = lg.open_position(mv.event_ticker)
                if pos is not None:
                    counts["exits_queued"] += int(self._manage(bot, mv, br, ls, pos))
                    continue
                cand = self._deliberate_entry(bot, mv, br, ls, lg)
                if cand is not None:
                    candidates.append(cand)

            # Commit best-first until the bankroll is committed. `queued` is
            # tracked separately because nothing fills until the next tick, so
            # `open_exposure_cents()` would still read the start-of-tick figure
            # and every candidate would think it had the whole bankroll.
            queued = 0
            for _conv, (d, mv, ticker, player, stake) in sorted(
                    candidates, key=lambda c: -c[0]):
                room = BANKROLL_CENTS - lg.open_exposure_cents() - queued
                need = stake.contracts * (d.price_at_decision or 0)
                if need > room:
                    d.action = "deferred_no_bankroll"
                    d.rationale += (
                        f"\n  DEFERRED: wanted {stake.contracts} contracts costing "
                        f"{need/100:.2f} dollars with only {room/100:.2f} of the "
                        f"bankroll uncommitted. Ranked below other candidates on "
                        f"this tick, not rejected on its merits.")
                    self.log(d)
                    counts["deferred_no_bankroll"] += 1
                    continue
                self.log(d)
                if bot.is_control:
                    self._record_control_intent(d, mv, ticker, player, stake)
                    continue
                self.engine.queue_buy(bot.name, mv, ticker, player, d.decision_id,
                                      qty=stake.contracts,
                                      max_price=min(99, (d.price_at_decision or 0) + 3))
                queued += need
                counts["entries_queued"] += 1
        return counts

    # -- entry -------------------------------------------------------------

    def _deliberate_entry(self, bot: Bot, mv: MatchView, br: Brief,
                          ls: LiveState, lg):
        """Reason about one match. Returns a ranked candidate, or None.

        Logs the PASS itself; only an entry is handed back for ranking, because
        only an entry competes for the bankroll.
        """
        entries = lg.entries_for(mv.event_ticker)
        if bot.exit_mode == "hold" and entries >= 1:
            return None
        if bot.exit_mode == "exit-once" and entries >= 1:
            return None
        if bot.exit_mode == "free" and entries >= MAX_ENTRIES_PER_EVENT:
            return None
        if entries >= 1:
            last = self.last_exit_ts.get((bot.name, mv.event_ticker))
            if last is not None and (datetime.now(timezone.utc).timestamp() - last) < REENTRY_COOLDOWN_SEC:
                return None

        best: tuple[float, Any] | None = None
        for ticker, player, ask, spread in bot.mentality.sides(mv, br):
            cons, head = bot.mentality.consider(mv, br, ls, ticker, player, ask, spread)
            conv = _score(cons)
            if best is None or conv > best[0]:
                best = (conv, (cons, head, ticker, player, ask, spread))
        if best is None:
            return None

        conv, (cons, head, ticker, player, ask, spread) = best
        act = "enter" if conv >= bot.mentality.enter_at else "pass"
        if act == "enter" and entries >= 1:
            act = "reenter"
        did = uuid.uuid4().hex[:12]
        bar = hold_cost_cents(ask, spread) if bot.exit_mode == "hold" \
            else round_trip_cost_cents(ask, spread)

        # -- how much, and why -------------------------------------------
        # Sized even on a PASS, so the log records what the bot would have
        # staked. Otherwise sizing can only ever be studied on trades the bot
        # chose to make, which is selection and sizing confounded again.
        q_side = mv.primary if mv.primary.ticker == ticker else mv.mirror
        depth_cap = None
        if q_side is not None and q_side.yes_ask_size is not None:
            depth_cap = int(q_side.yes_ask_size * 0.25)
        stake = choose_stake(
            conviction=conv, enter_at=bot.mentality.enter_at,
            fair=bot.mentality._fair_for(br, player),
            ask_cents=ask,
            open_exposure_cents=lg.open_exposure_cents(),
            first_entry_contracts=lg.first_entry_contracts(mv.event_ticker),
            depth_cap_contracts=depth_cap,
            market_prob=(ask / 100.0),
        )
        if act != "pass" and stake.contracts <= 0:
            act = "pass"
            cons = cons + [Consideration("no_stake_available",
                "the conviction cleared the bar but there is no room to stake - either "
                "the bankroll is fully committed or the book is not showing enough size",
                "against", 0.0)]

        expectation = (
            f"expects {player} to settle YES, and needs more than {bar:.2f}c of edge "
            f"over the {ask}c ask for that to have been worth doing. Staking "
            f"{stake.stake_cents/100:.2f} dollars on {stake.contracts} contracts, so a "
            f"loss costs {stake.stake_cents/100:.2f} and being right pays about "
            f"{stake.contracts*(100-ask)/100:.2f} before fees."
            if act != "pass" else
            f"expects to have avoided a trade whose cost bar was {bar:.2f}c at {ask}c; "
            f"had it entered it would have staked {stake.stake_cents/100:.2f} dollars"
        )
        d = Deliberation(
            decision_id=did, ts=_now(), bot=bot.name,
            mentality=bot.mentality.name, exit_mode=bot.exit_mode,
            event_ticker=mv.event_ticker, brief_digest=br.digest(),
            side_ticker=ticker if act != "pass" else None,
            side_player=player if act != "pass" else None,
            price_at_decision=ask, spread_at_decision=spread,
            cost_bar_cents=round(bar, 3), considerations=cons,
            conviction=round(conv, 3), action=act,
            rationale=_rationale(bot, cons, conv, head, act),
            expectation=expectation,
            contracts=stake.contracts, stake_cents=stake.stake_cents,
            stake_fraction=round(stake.fraction, 5), sizing_basis=stake.basis,
            kelly_full=(round(stake.kelly_full, 5) if stake.kelly_full is not None else None),
            edge_cents=(round(stake.edge_cents, 3) if stake.edge_cents is not None else None),
            sizing_rationale=stake.rationale, sizing_caps=stake.capped_by,
            p_size=(round(stake.p_size, 4) if stake.p_size is not None else None),
            bankroll_cents=BANKROLL_CENTS,
            open_exposure_cents=lg.open_exposure_cents(),
        )
        if act == "pass":
            self.log(d)
            return None
        return (conv, (d, mv, ticker, player, stake))

    def _record_control_intent(self, d: Deliberation, mv: MatchView,
                               ticker: str, player: str, stake) -> None:
        """The control logs what it would have done and does nothing.

        Marked at the MID with ZERO fees ON PURPOSE. The gap between this
        number and the traded bots' numbers IS the cost of execution, which is
        the one quantity fifty matches is actually enough to measure. It is a
        deliberately unattainable benchmark and is labelled as one wherever it
        appears - the same role the red FAKE rows play in SCOREBOARD.md.
        """
        q = mv.primary if mv.primary.ticker == ticker else mv.mirror
        self.control_intents.append({
            "decision_id": d.decision_id, "ts": d.ts,
            "event_ticker": mv.event_ticker, "ticker": ticker, "player": player,
            "intended_ask": d.price_at_decision,
            "intended_mid": q.mid if q else None,
            "spread": d.spread_at_decision, "conviction": d.conviction,
            "contracts": stake.contracts, "stake_cents": stake.stake_cents,
            "stake_fraction": stake.fraction, "sizing_basis": stake.basis,
            "basis": "UNATTAINABLE BENCHMARK: mid price, zero fees, hold to settle",
        })

    # -- management --------------------------------------------------------

    def _manage(self, bot: Bot, mv: MatchView, br: Brief, ls: LiveState,
                pos: Position) -> bool:
        if bot.exit_mode == "hold":
            return False
        q = mv.primary if mv.primary.ticker == pos.ticker else mv.mirror
        if q is None or not q.is_quotable():
            return False
        bid = q.yes_bid
        move = bid - pos.entry_price
        cons: list[Consideration] = []
        act = "hold"
        if move >= TAKE_PROFIT_CENTS:
            cons.append(Consideration("take_profit",
                f"the bid is {bid}c against a {pos.entry_price}c entry, {move:+d}c. "
                f"Selling now pays a second fee of "
                f"{float(_fee_rate_cents(bid)):.2f}c.",
                "for", 3.0))
            act = "exit"
        elif move <= -STOP_CENTS:
            cons.append(Consideration("stop_loss",
                f"the bid is {bid}c against a {pos.entry_price}c entry, {move:+d}c. "
                f"This repo measured the stop-loss as the single most expensive component "
                f"of its live strategy - the same trades went from +0.62c to -3.77c purely "
                f"by adding one. Firing it anyway is what this exit mode IS.",
                "for", 3.0))
            act = "exit"
        else:
            cons.append(Consideration("no_trigger",
                f"the bid is {bid}c against a {pos.entry_price}c entry ({move:+d}c), "
                f"inside the +/-{TAKE_PROFIT_CENTS}c band", "neutral", 0.0))

        if act == "exit":
            did = uuid.uuid4().hex[:12]
            d = Deliberation(
                decision_id=did, ts=_now(), bot=bot.name,
                mentality=bot.mentality.name, exit_mode=bot.exit_mode,
                event_ticker=mv.event_ticker, brief_digest=br.digest(),
                side_ticker=pos.ticker, side_player=pos.player,
                price_at_decision=bid, spread_at_decision=q.spread,
                cost_bar_cents=None, considerations=cons,
                conviction=_score(cons), action="exit",
                rationale=_rationale(bot, cons, _score(cons),
                                     f"holding {pos.qty} at {pos.entry_price}c", "exit"),
                expectation=(f"expects selling at {bid}c to beat holding to settlement; "
                             f"if the match settles YES this exit will have cost "
                             f"{100 - bid}c of upside plus a second fee"),
            )
            self.log(d)
            self.engine.queue_sell(bot.name, pos, mv, did,
                                   min_price=max(1, bid - 3))
            self.last_exit_ts[(bot.name, mv.event_ticker)] = \
                datetime.now(timezone.utc).timestamp()
            return True
        return False
