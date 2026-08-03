"""Out-of-sample validation of the wallet *selection procedure*.

Every other statistic in this codebase asks "does this wallet have an edge?".
This module asks the prior question: "does picking the best-looking wallet find
edge, or does it find noise?" Those are different, and only the second one
explains why a screened leaderboard can look excellent and still be worthless.

The mechanism: rank N wallets on a noisy statistic and report the winner's
number, and you have reported the *maximum* of N noisy draws. That maximum is
large even when every wallet is a coin-flipper -- roughly 2 standard errors
above the population mean at N=24, and 3.2 at N=1500. A headline figure produced
this way carries almost no evidence on its own, because the procedure that
produced it would have produced something similar from a population with no
skill in it at all.

Two tests separate the cases:

**Split-sample.** Rank on the first half of each wallet's record, measure on the
second. Real skill persists across the split; selection noise does not, because
the trades that won the ranking are not in the measurement set.

**Exchangeability permutation.** Pool every trade from every wallet, deal them
back out at random preserving each wallet's trade counts, and re-run the whole
selection. Repeating that builds the null distribution of "best wallet found by
this procedure when no wallet has skill". The observed winner is only evidence
if it beats that distribution -- comparing it against zero is the mistake.

The permutation deliberately does *not* recentre the pooled returns. The
question is whether wallets differ from each other, not whether the population
mean is positive; recentring would answer a different question and inflate
significance.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ..logging_setup import get_logger

log = get_logger(__name__)

# Fixed seed: a verdict that changes between identical runs is not a verdict.
PERMUTATION_SEED = 20260730


@dataclass(slots=True)
class TradeRecord:
    """One trade's per-trade return, with the timestamp used to order it."""

    wallet: str
    opened_ts: int
    roi: float


@dataclass(slots=True)
class WalletSplit:
    """A single wallet's record cut into selection and measurement halves.

    ``in_sample`` is what a screen run at the split date would have seen;
    ``out_sample`` is what following the wallet from that date would have paid.
    """

    wallet: str
    in_sample: list[float]
    out_sample: list[float]
    split_ts: int

    @property
    def n_in(self) -> int:
        return len(self.in_sample)

    @property
    def n_out(self) -> int:
        return len(self.out_sample)

    @property
    def in_mean(self) -> float:
        return float(np.mean(self.in_sample))

    @property
    def out_mean(self) -> float:
        return float(np.mean(self.out_sample))

    @property
    def in_median(self) -> float:
        return float(np.median(self.in_sample))

    @property
    def out_median(self) -> float:
        return float(np.median(self.out_sample))

    @property
    def decay(self) -> float:
        """How much of the in-sample figure failed to survive the split.

        Under pure selection this approaches the full in-sample edge; under real
        skill it stays near zero.
        """
        return self.in_mean - self.out_mean


def copier_edge(outcomes: list[bool], fills: list[float]) -> tuple[float, float, float]:
    """(implied breakeven, realised win rate, edge in points) for a follower.

    A market price *is* a probability: pay $0.40 and you must win 40% of the time
    to break even. The edge is the realised win rate minus the average price
    paid, so the same yardstick works at any price level.

    This is why raw win rate is never reported on its own. A wallet buying $0.95
    favourites wins 95% of the time and has no edge whatsoever; one buying $0.30
    longshots wins 35% and is printing money. ``fills`` must therefore be the
    price a *follower* pays after delay, not the wallet's own entry -- otherwise
    the edge belongs to the wallet and not to the person copying it.
    """
    n = len(outcomes)
    if n == 0 or n != len(fills):
        return 0.0, 0.0, 0.0
    implied = sum(fills) / n
    realised = sum(1 for w in outcomes if w) / n
    return implied, realised, realised - implied


def binomial_tail(wins: int, n: int, p: float) -> float:
    """P(at least ``wins`` successes in ``n``) at implied probability ``p``.

    Small values mean the record is hard to explain by luck. One-sided and
    uncorrected for multiple wallets screened -- ``luck_bar`` is the tool for
    that, and the two should always be read together.
    """
    if n <= 0:
        return 1.0
    p = min(max(p, 1e-9), 1 - 1e-9)
    wins = max(0, min(wins, n))
    if n > 1000:
        # Exact form gets slow past here and the approximation is tight at this n.
        mu = n * p
        sd = math.sqrt(n * p * (1 - p))
        return float(0.5 * math.erfc((wins - 0.5 - mu) / (sd * math.sqrt(2))))
    return min(
        1.0,
        sum(math.comb(n, k) * p**k * (1 - p) ** (n - k) for k in range(wins, n + 1)),
    )


def luck_bar(
    sample_sizes: list[int],
    *,
    iterations: int = 4000,
    seed: int = PERMUTATION_SEED,
) -> float:
    """Edge the luckiest wallet shows when *nobody* has skill.

    Simulates a population with these exact trade counts, every wallet a
    coin-flipper priced at 50%, and returns the average of the best edge
    observed. That average is the bar a real wallet must clear -- comparing its
    edge against zero instead is what makes a screened leaderboard look like
    evidence when it is not.

    Sample size dominates the result, which is the useful part: on the live data
    this bar is +48 points across 25 wallets that include 1-trade records, and
    +6 points once a 50-trade minimum is applied. Demanding volume shrinks the
    bar far faster than any cleverness in the ranking formula.
    """
    sizes = [n for n in sample_sizes if n > 0]
    if not sizes:
        return 0.0
    rng = np.random.default_rng(seed)
    arr = np.asarray(sizes, dtype=np.int64)
    # One binomial draw per wallet per iteration, vectorised across wallets.
    draws = rng.binomial(arr[None, :], 0.5, size=(iterations, arr.size))
    edges = draws / arr[None, :] - 0.5
    return float(edges.max(axis=1).mean())


def winsorize(records: list[TradeRecord], *, pct: float = 95.0) -> list[TradeRecord]:
    """Cap returns at a pooled percentile, preserving sign and ordering.

    Tennis longshot returns are violently convex: in the live data 42% of trades
    lose everything and the best pays +937%. A mean over 12 such trades carries a
    standard error near 40 percentage points, so a screen ranking on it is
    ranking on which wallet happened to catch a tail -- the selection test says
    as much, with a null max above +50%.

    Capping keeps the direction of the convexity -- a capped winner is still a
    maximal observation, and a wallet that catches more of them still ranks
    higher -- while removing any single trade's power to decide a ranking on its
    own. Deleting the tail instead, as an earlier attempt did, destroys the very
    mechanism a longshot strategy trades on.

    Everything above the threshold is set *equal* to it, so the top trades tie:
    that is what winsorizing means, and it is only safe while the threshold sits
    above the bulk of the distribution. At p95 on the live data the cap lands at
    +213% against a +2% median, which is comfortably clear. Push ``pct`` low
    enough that the threshold falls inside the mass and the statistic stops
    discriminating between wallets at all.

    The threshold is computed over the *pooled* distribution, never per wallet:
    a 12-trade wallet has no percentile worth estimating from its own data.
    """
    if not records or pct >= 100.0:
        return records
    values = np.asarray([r.roi for r in records], dtype=np.float64)
    high = float(np.percentile(values, pct))
    low = float(np.percentile(values, 100.0 - pct))
    return [
        TradeRecord(r.wallet, r.opened_ts, min(max(r.roi, low), high)) for r in records
    ]


def split_wallet(
    records: list[TradeRecord],
    *,
    mode: str = "count",
    min_half: int = 10,
) -> WalletSplit | None:
    """Cut one wallet's trades into two halves, or ``None`` if too thin.

    ``count`` splits at the median trade so both halves carry equal weight --
    the default, because it maximises the power of the out-of-sample half.
    ``time`` splits at the calendar midpoint, which is what a screen actually run
    on that date would have seen, but leaves the halves unbalanced whenever
    trading activity was not uniform.
    """
    if not records:
        return None
    ordered = sorted(records, key=lambda r: r.opened_ts)

    if mode == "count":
        mid = len(ordered) // 2
        first, second = ordered[:mid], ordered[mid:]
        split_ts = second[0].opened_ts if second else ordered[-1].opened_ts
    elif mode == "time":
        split_ts = (ordered[0].opened_ts + ordered[-1].opened_ts) // 2
        first = [r for r in ordered if r.opened_ts < split_ts]
        second = [r for r in ordered if r.opened_ts >= split_ts]
    else:
        raise ValueError(f"unknown split mode: {mode!r} (expected 'count' or 'time')")

    if len(first) < min_half or len(second) < min_half:
        return None
    return WalletSplit(
        wallet=ordered[0].wallet,
        in_sample=[r.roi for r in first],
        out_sample=[r.roi for r in second],
        split_ts=split_ts,
    )


def build_splits(
    records: list[TradeRecord],
    *,
    mode: str = "count",
    min_trades: int = 20,
    min_half: int = 10,
) -> list[WalletSplit]:
    """Group trades by wallet and split each one, dropping wallets that are
    too thin to say anything about."""
    by_wallet: dict[str, list[TradeRecord]] = {}
    for r in records:
        by_wallet.setdefault(r.wallet, []).append(r)

    splits: list[WalletSplit] = []
    for wallet, rows in by_wallet.items():
        if len(rows) < min_trades:
            continue
        split = split_wallet(rows, mode=mode, min_half=min_half)
        if split is not None:
            splits.append(split)
    splits.sort(key=lambda s: s.in_mean, reverse=True)
    return splits


def _rankdata(arr: np.ndarray) -> np.ndarray:
    """Ranks with ties averaged, matching the usual Spearman convention."""
    order = np.argsort(arr, kind="mergesort")
    sorted_vals = arr[order]
    ranks = np.empty(arr.size, dtype=np.float64)
    i = 0
    n = arr.size
    while i < n:
        j = i
        while j + 1 < n and sorted_vals[j + 1] == sorted_vals[i]:
            j += 1
        ranks[order[i : j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def spearman(xs: list[float] | np.ndarray, ys: list[float] | np.ndarray) -> float | None:
    """Rank correlation between two equal-length series.

    ``None`` when it is undefined: fewer than three points, or one series
    entirely tied (every wallet identical), where no correlation exists to
    report and returning 0.0 would read as "measured, and it was nothing".
    """
    a = np.asarray(xs, dtype=np.float64)
    b = np.asarray(ys, dtype=np.float64)
    if a.size != b.size or a.size < 3:
        return None
    ra, rb = _rankdata(a), _rankdata(b)
    sa, sb = ra.std(), rb.std()
    if sa <= 1e-12 or sb <= 1e-12:
        return None
    return float(np.mean((ra - ra.mean()) * (rb - rb.mean())) / (sa * sb))


@dataclass(slots=True)
class SelectionTest:
    """Observed selection outcome, and the same procedure run under the null."""

    n_wallets: int
    n_trades: int
    pooled_mean: float

    # --- observed -------------------------------------------------------
    winner: str
    winner_in_mean: float
    winner_out_mean: float
    winner_n_in: int
    winner_n_out: int
    rank_correlation: float | None

    # --- null distribution (trades dealt at random) ---------------------
    iterations: int
    null_max_in_mean: float
    null_max_in_p95: float
    null_winner_out_mean: float
    null_rank_correlation: float
    # P(null procedure produces a winner at least this good in-sample).
    p_value_in_sample: float
    # P(null procedure's selected wallet does at least this well out-of-sample).
    p_value_out_sample: float
    p_value_rank_correlation: float | None

    splits: list[WalletSplit] = field(default_factory=list)

    @property
    def survives(self) -> bool:
        """The only result that justifies real money: the winner beats the
        selection null *out of sample*, where noise cannot follow it."""
        return self.p_value_out_sample < 0.05

    @property
    def selection_share(self) -> float | None:
        """Fraction of the winner's in-sample edge attributable to selection.

        1.0 means the entire headline number is the max-of-N artefact; 0.0 means
        it survived the split intact. Undefined when the in-sample edge is not
        positive, since there is then no edge to apportion.
        """
        edge = self.winner_in_mean - self.pooled_mean
        if edge <= 0:
            return None
        null_edge = self.null_max_in_mean - self.pooled_mean
        return round(min(1.0, max(0.0, null_edge / edge)), 4)


def run_selection_test(
    splits: list[WalletSplit],
    *,
    iterations: int = 2000,
    seed: int = PERMUTATION_SEED,
) -> SelectionTest | None:
    """Rank on the in-sample half, measure out of sample, and compare both
    against the same procedure applied to randomly dealt trades.

    Returns ``None`` with fewer than two wallets: selection is meaningless when
    there is nothing to select between, and reporting a p-value there would
    dress a single wallet's record up as a screening result.
    """
    if len(splits) < 2:
        return None

    # Interleave [in_0, out_0, in_1, out_1, ...] so one reduceat call recovers
    # every half-mean per iteration.
    pool_parts: list[np.ndarray] = []
    lengths: list[int] = []
    for s in splits:
        pool_parts.append(np.asarray(s.in_sample, dtype=np.float64))
        pool_parts.append(np.asarray(s.out_sample, dtype=np.float64))
        lengths.extend((s.n_in, s.n_out))

    pool = np.concatenate(pool_parts)
    seg_lengths = np.asarray(lengths, dtype=np.int64)
    starts = np.concatenate([[0], np.cumsum(seg_lengths)[:-1]]).astype(np.int64)

    obs_in = np.asarray([s.in_mean for s in splits], dtype=np.float64)
    obs_out = np.asarray([s.out_mean for s in splits], dtype=np.float64)
    winner_idx = int(np.argmax(obs_in))
    obs_rho = spearman(obs_in, obs_out)

    rng = np.random.default_rng(seed)
    null_max_in = np.empty(iterations, dtype=np.float64)
    null_winner_out = np.empty(iterations, dtype=np.float64)
    null_rhos: list[float] = []

    for i in range(iterations):
        dealt = rng.permutation(pool)
        means = np.add.reduceat(dealt, starts) / seg_lengths
        sim_in, sim_out = means[0::2], means[1::2]
        j = int(np.argmax(sim_in))
        null_max_in[i] = sim_in[j]
        null_winner_out[i] = sim_out[j]
        rho = spearman(sim_in, sim_out)
        if rho is not None:
            null_rhos.append(rho)

    winner = splits[winner_idx]
    # +1 in numerator and denominator: with B permutations the smallest
    # defensible p-value is 1/(B+1), not 0. Reporting p=0 from 2000 draws
    # overstates what the resampling can support.
    p_in = float((np.sum(null_max_in >= winner.in_mean) + 1) / (iterations + 1))
    p_out = float((np.sum(null_winner_out >= winner.out_mean) + 1) / (iterations + 1))

    p_rho = None
    if obs_rho is not None and null_rhos:
        arr = np.asarray(null_rhos, dtype=np.float64)
        p_rho = float((np.sum(arr >= obs_rho) + 1) / (arr.size + 1))

    return SelectionTest(
        n_wallets=len(splits),
        n_trades=int(pool.size),
        pooled_mean=float(pool.mean()),
        winner=winner.wallet,
        winner_in_mean=winner.in_mean,
        winner_out_mean=winner.out_mean,
        winner_n_in=winner.n_in,
        winner_n_out=winner.n_out,
        rank_correlation=obs_rho,
        iterations=iterations,
        null_max_in_mean=float(null_max_in.mean()),
        null_max_in_p95=float(np.quantile(null_max_in, 0.95)),
        null_winner_out_mean=float(null_winner_out.mean()),
        null_rank_correlation=float(np.mean(null_rhos)) if null_rhos else 0.0,
        p_value_in_sample=p_in,
        p_value_out_sample=p_out,
        p_value_rank_correlation=p_rho,
        splits=splits,
    )
