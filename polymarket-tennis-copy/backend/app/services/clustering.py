"""Wallet relationship detection.

Purpose
-------
Three wallets controlled by one trader entering the same outcome is **one**
opinion, not three independent confirmations. Without this module the consensus
engine would treat a single trader splitting across addresses as its strongest
possible signal -- exactly backwards.

Evidence used (all lawful, from public on-chain activity we already ingest):

* overlap of traded (market, outcome) pairs -- Jaccard similarity
* how often shared entries land inside a tight time window
* similarity of position sizes on shared markets
* coordinated exits

What this module does not do
----------------------------
It never asserts common ownership. On-chain funding-graph analysis would be
required for that and is out of scope for v1. Labels are graded
(:class:`ClusterRelation`) and the strongest available is
``HIGHLY_CORRELATED`` -- a statement about behaviour, not identity.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from itertools import combinations

from ..config import Settings, get_settings
from ..enums import ClusterRelation
from ..logging_setup import get_logger

log = get_logger(__name__)

ZERO = Decimal("0")


@dataclass(slots=True)
class WalletActivitySignature:
    """Compact behavioural fingerprint for one wallet."""

    wallet_id: int
    address: str
    # (token_id) -> earliest entry timestamp for that outcome.
    entries: dict[str, int] = field(default_factory=dict)
    # (token_id) -> capital committed.
    sizes: dict[str, Decimal] = field(default_factory=dict)
    # (token_id) -> exit timestamp, when closed.
    exits: dict[str, int] = field(default_factory=dict)

    @property
    def traded_tokens(self) -> set[str]:
        return set(self.entries)


@dataclass
class PairSimilarity:
    """Pairwise evidence between two wallets."""

    wallet_a: int
    wallet_b: int
    shared_markets: int = 0
    jaccard: float = 0.0
    timing_correlation: float = 0.0
    size_correlation: float = 0.0
    coordinated_exits: int = 0
    relation: ClusterRelation = ClusterRelation.INSUFFICIENT_EVIDENCE
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)

    def evidence_json(self) -> str:
        return json.dumps(
            {
                "shared_markets": self.shared_markets,
                "jaccard": round(self.jaccard, 4),
                "timing_correlation": round(self.timing_correlation, 4),
                "size_correlation": round(self.size_correlation, 4),
                "coordinated_exits": self.coordinated_exits,
                "relation": self.relation.value,
                "confidence": round(self.confidence, 4),
                "notes": self.evidence,
            },
            sort_keys=True,
        )


@dataclass
class Cluster:
    """A group of behaviourally similar wallets."""

    label: str
    wallet_ids: set[int] = field(default_factory=set)
    relation: ClusterRelation = ClusterRelation.INSUFFICIENT_EVIDENCE
    confidence: float = 0.0
    pairs: list[PairSimilarity] = field(default_factory=list)

    @property
    def member_count(self) -> int:
        return len(self.wallet_ids)

    def evidence_summary(self) -> str:
        if not self.pairs:
            return "no pairwise evidence recorded"
        strongest = max(self.pairs, key=lambda p: p.confidence)
        return (
            f"{self.member_count} wallets; strongest pair shares "
            f"{strongest.shared_markets} markets "
            f"(Jaccard {strongest.jaccard:.2f}, timing "
            f"{strongest.timing_correlation:.2f}). "
            f"Label: {self.relation.value}. "
            "Behavioural similarity only -- not a claim of common ownership."
        )


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def _size_similarity(a: Decimal, b: Decimal) -> float:
    """1.0 for identical sizes, decaying toward 0 as they diverge."""
    if a <= ZERO or b <= ZERO:
        return 0.0
    ratio = float(min(a, b) / max(a, b))
    return ratio


class WalletClusterer:
    """Detects behavioural relationships between wallets."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    # ------------------------------------------------------------- pairwise
    def compare(
        self, a: WalletActivitySignature, b: WalletActivitySignature
    ) -> PairSimilarity:
        s = self.settings
        sim = PairSimilarity(wallet_a=a.wallet_id, wallet_b=b.wallet_id)

        shared = a.traded_tokens & b.traded_tokens
        sim.shared_markets = len(shared)
        sim.jaccard = _jaccard(a.traded_tokens, b.traded_tokens)

        if not shared:
            sim.relation = ClusterRelation.LIKELY_INDEPENDENT
            sim.evidence.append("no shared outcomes")
            return sim

        if sim.shared_markets < s.cluster_min_shared_markets:
            # Overlap happens by chance in a small market universe; a handful of
            # shared markets is not evidence of coordination.
            sim.relation = ClusterRelation.INSUFFICIENT_EVIDENCE
            sim.evidence.append(
                f"only {sim.shared_markets} shared outcomes "
                f"(need {s.cluster_min_shared_markets})"
            )
            return sim

        # --- timing: how many shared entries were near-simultaneous ---------
        close_entries = 0
        size_scores: list[float] = []
        for token in shared:
            delta = abs(a.entries[token] - b.entries[token])
            if delta <= s.cluster_timing_window_seconds:
                close_entries += 1
            size_scores.append(_size_similarity(a.sizes.get(token, ZERO), b.sizes.get(token, ZERO)))

        sim.timing_correlation = close_entries / len(shared)
        sim.size_correlation = sum(size_scores) / len(size_scores) if size_scores else 0.0

        # --- coordinated exits ----------------------------------------------
        for token in shared:
            if token in a.exits and token in b.exits:
                if abs(a.exits[token] - b.exits[token]) <= s.cluster_timing_window_seconds:
                    sim.coordinated_exits += 1

        # --- combine ---------------------------------------------------------
        # Timing dominates: trading the same markets is common, doing so within
        # two minutes repeatedly is not.
        sim.confidence = round(
            0.45 * sim.timing_correlation
            + 0.25 * min(1.0, sim.jaccard / max(s.cluster_jaccard_threshold, 1e-9))
            + 0.20 * sim.size_correlation
            + 0.10 * min(1.0, sim.coordinated_exits / max(len(shared), 1)),
            4,
        )

        strong_timing = sim.timing_correlation >= s.cluster_timing_ratio_threshold
        strong_overlap = sim.jaccard >= s.cluster_jaccard_threshold

        if strong_timing and strong_overlap and sim.confidence >= 0.7:
            sim.relation = ClusterRelation.HIGHLY_CORRELATED
            sim.evidence.append(
                f"{close_entries}/{len(shared)} shared entries within "
                f"{s.cluster_timing_window_seconds}s and Jaccard "
                f"{sim.jaccard:.2f}"
            )
        elif strong_timing or (strong_overlap and sim.timing_correlation >= 0.25):
            sim.relation = ClusterRelation.POSSIBLY_RELATED
            sim.evidence.append(
                f"timing correlation {sim.timing_correlation:.2f}, "
                f"Jaccard {sim.jaccard:.2f}"
            )
        else:
            sim.relation = ClusterRelation.LIKELY_INDEPENDENT
            sim.evidence.append(
                f"shared {sim.shared_markets} outcomes but timing correlation is "
                f"only {sim.timing_correlation:.2f}"
            )

        if sim.coordinated_exits:
            sim.evidence.append(
                f"{sim.coordinated_exits} coordinated exits"
            )
        return sim

    # -------------------------------------------------------------- clusters
    def build_clusters(
        self, signatures: list[WalletActivitySignature]
    ) -> tuple[list[Cluster], list[PairSimilarity]]:
        """Group wallets by transitive behavioural similarity.

        Only ``POSSIBLY_RELATED`` and stronger links join wallets, so an
        unrelated wallet cannot be pulled into a cluster by a single weak edge.
        """
        all_pairs: list[PairSimilarity] = []
        adjacency: dict[int, set[int]] = {sig.wallet_id: set() for sig in signatures}

        for a, b in combinations(signatures, 2):
            sim = self.compare(a, b)
            all_pairs.append(sim)
            if sim.relation in (
                ClusterRelation.POSSIBLY_RELATED,
                ClusterRelation.HIGHLY_CORRELATED,
            ):
                adjacency[a.wallet_id].add(b.wallet_id)
                adjacency[b.wallet_id].add(a.wallet_id)

        by_id = {sig.wallet_id: sig for sig in signatures}
        seen: set[int] = set()
        clusters: list[Cluster] = []

        for wallet_id in adjacency:
            if wallet_id in seen or not adjacency[wallet_id]:
                continue
            # Breadth-first over the similarity graph.
            group: set[int] = set()
            queue = [wallet_id]
            while queue:
                current = queue.pop()
                if current in group:
                    continue
                group.add(current)
                queue.extend(adjacency[current] - group)
            seen |= group

            if len(group) < 2:
                continue

            member_pairs = [
                p
                for p in all_pairs
                if p.wallet_a in group and p.wallet_b in group
                and p.relation
                in (ClusterRelation.POSSIBLY_RELATED, ClusterRelation.HIGHLY_CORRELATED)
            ]
            # The cluster is only as strong as its strongest evidence, and only
            # labelled HIGHLY_CORRELATED if a pair actually earned that label.
            relation = (
                ClusterRelation.HIGHLY_CORRELATED
                if any(p.relation is ClusterRelation.HIGHLY_CORRELATED for p in member_pairs)
                else ClusterRelation.POSSIBLY_RELATED
            )
            confidence = max((p.confidence for p in member_pairs), default=0.0)

            labels = sorted(by_id[w].address[:10] for w in group)
            clusters.append(
                Cluster(
                    label=f"cluster:{labels[0]}+{len(group) - 1}",
                    wallet_ids=group,
                    relation=relation,
                    confidence=confidence,
                    pairs=member_pairs,
                )
            )

        return clusters, all_pairs


def count_independent_groups(
    wallet_ids: list[int], cluster_membership: dict[int, int | None]
) -> int:
    """Number of distinct opinions among ``wallet_ids``.

    Wallets sharing a cluster collapse to one. Unclustered wallets each count
    separately. This is the value the consensus engine gates on -- not the raw
    wallet count.
    """
    groups: set[str] = set()
    for wallet_id in wallet_ids:
        cluster_id = cluster_membership.get(wallet_id)
        groups.add(f"c{cluster_id}" if cluster_id is not None else f"w{wallet_id}")
    return len(groups)


def deduplicate_by_cluster(
    wallet_ids: list[int], cluster_membership: dict[int, int | None]
) -> tuple[list[int], list[int]]:
    """Split wallets into (counted, suppressed).

    For each cluster only the first wallet (lowest id, for determinism) is
    counted; its peers are suppressed so they cannot inflate a consensus.
    """
    counted: list[int] = []
    suppressed: list[int] = []
    seen_clusters: set[int] = set()

    for wallet_id in sorted(wallet_ids):
        cluster_id = cluster_membership.get(wallet_id)
        if cluster_id is None:
            counted.append(wallet_id)
            continue
        if cluster_id in seen_clusters:
            suppressed.append(wallet_id)
        else:
            seen_clusters.add(cluster_id)
            counted.append(wallet_id)
    return counted, suppressed
