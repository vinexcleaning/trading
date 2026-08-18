"""noskill.py — what "no edge at all" looks like, for any set of bets.

THE ONE IMPLEMENTATION. Import it; do not write a third.

WHY THIS IS IN common/ AND NOT IN A PROJECT
    Two already exist. `tennis-paper-forward` simulates returns at each bet's
    own market-implied odds; `mlb-paper/src/examine_starter.py` takes a binomial
    tail of the win count against a break-even price. Both are right and they
    answer slightly different questions. The strategy factory
    (`coordinator/STRATEGY_FACTORY.md` stage 5) requires every strategy to carry
    its no-skill range, which would have made a third.

    The Kalshi fee formula went from 3 copies to 17 *after* an instruction to
    share it (GUARDS #6). A convention did not work; a shared module plus a
    failing test did. This is that, applied before the copies exist rather than
    after.

THE NULL, STATED PLAINLY
    **The market price is right.** A contract bought at 70c wins 70 times in 100.
    Each strategy keeps its REAL bets, REAL sizes, REAL prices and pays its REAL
    fees; only the outcome is redrawn. That is what a strategy with no idea at
    all, trading exactly what this one traded, would have earned.

    It is deliberately not a coin flip. A bot that only buys 85c favourites wins
    most of its bets whether or not it has any skill, and a 50/50 null would call
    that skill.

WHY THE FEES MATTER, AND THE MISTAKE THAT PROVES IT
    The first version of this in `tennis-paper-forward` had the real bots paying
    fees while the simulated no-skill bot paid none — gross against net. **Six of
    sixteen bots looked worse than luck when they were not.** Correcting it
    dropped that to two, which is what chance gives. An unfair comparison that
    happens to flatter your conclusion is the failure this repo has recorded most
    often; `fees` is not optional here for that reason.

WHAT A BAND MEANS
    `band()` returns the 5th and 95th percentile of that no-skill distribution.
    A result INSIDE the band means nothing yet. A result outside it is worth
    looking at — and if you are looking at many strategies, use `best_of()`,
    because the best of 2,000 no-skill strategies typically shows about +29.5%.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import comb
from typing import Iterable, Sequence

import numpy as np

DEFAULT_SIMS = 20_000
DEFAULT_SEED = 20260818


@dataclass(frozen=True)
class Bets:
    """One strategy's actual trades. Prices in integer cents, 1..99."""
    prices: Sequence[float]
    qtys: Sequence[float]
    fees: Sequence[float] = ()

    def __post_init__(self) -> None:
        if len(self.prices) != len(self.qtys):
            raise ValueError("prices and qtys must be the same length")
        if self.fees and len(self.fees) != len(self.prices):
            raise ValueError("fees must be empty or the same length as prices")
        if any(not (0 < p < 100) for p in self.prices):
            raise ValueError("prices must be strictly between 0 and 100 cents")

    @property
    def n(self) -> int:
        return len(self.prices)

    @property
    def staked_cents(self) -> float:
        return float(np.sum(np.asarray(self.prices, float) * np.asarray(self.qtys, float)))


def _draw(bets: Bets, rng: np.random.Generator, n_sims: int) -> np.ndarray:
    """n_sims no-skill returns, in percent of stake."""
    pr = np.asarray(bets.prices, dtype=float)
    qt = np.asarray(bets.qtys, dtype=float)
    fe = np.asarray(bets.fees, dtype=float) if len(bets.fees) else np.zeros_like(pr)
    staked = float(np.sum(pr * qt))
    if staked <= 0:
        return np.zeros(n_sims)
    wins = rng.random((n_sims, pr.size)) < (pr / 100.0)
    pnl = np.where(wins, (100.0 - pr) * qt, -pr * qt).sum(axis=1) - fe.sum()
    return 100.0 * pnl / staked


def band(bets: Bets, lo_pct: float = 5.0, hi_pct: float = 95.0,
         n_sims: int = DEFAULT_SIMS, seed: int = DEFAULT_SEED) -> tuple[float, float]:
    """Where a no-skill strategy making THESE bets lands, lo_pct..hi_pct."""
    draws = _draw(bets, np.random.default_rng(seed), n_sims)
    return float(np.percentile(draws, lo_pct)), float(np.percentile(draws, hi_pct))


def p_at_least(bets: Bets, observed_return_pct: float,
               n_sims: int = DEFAULT_SIMS, seed: int = DEFAULT_SEED) -> float:
    """Chance a no-skill version of this strategy does this well or better."""
    draws = _draw(bets, np.random.default_rng(seed), n_sims)
    return float(np.mean(draws >= observed_return_pct))


def best_of(all_bets: Iterable[Bets], observed_best_return_pct: float,
            n_sims: int = DEFAULT_SIMS, seed: int = DEFAULT_SEED) -> float:
    """Chance the BEST of these strategies looks this good with no skill at all.

    THE NUMBER THAT IS ALWAYS MISSING. Judging one strategy and judging the best
    of two thousand are different questions: the best of 2,000 no-skill
    strategies typically shows about +29.5%, and reaches +30% about 37 times in
    100. Report this, not `p_at_least`, whenever a winner was PICKED from a set.
    """
    packs = list(all_bets)
    if not packs:
        return float("nan")
    rng = np.random.default_rng(seed)
    best = np.full(n_sims, -np.inf)
    for b in packs:
        np.maximum(best, _draw(b, rng, n_sims), out=best)
    return float(np.mean(best >= observed_best_return_pct))


def binomial_tail(k: int, n: int, p: float) -> float:
    """P(at least k wins in n) when each wins with probability p. Exact.

    Cheaper and exact where every bet is the same price and size — the form
    `mlb-paper` uses. Prefer the simulation above when prices or stakes vary,
    because this cannot see either.
    """
    if n <= 0:
        return float("nan")
    if k > n:
        # asking for more wins than there were bets. Clamping k to n here would
        # return P(win them all) instead of zero, which is a small number that
        # looks like a plausible answer - the worst kind of wrong.
        return 0.0
    k = max(0, k)
    return float(sum(comb(n, i) * p**i * (1 - p)**(n - i) for i in range(k, n + 1)))


def verdict(observed_return_pct: float, lo: float, hi: float) -> str:
    """Three values, never two. GUARDS #21 — 'I could not tell' is a verdict."""
    if observed_return_pct > hi:
        return "OUTSIDE, better than no skill"
    if observed_return_pct < lo:
        return "OUTSIDE, worse than no skill"
    return "INSIDE the no-skill range — means nothing yet"
