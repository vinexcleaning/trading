"""Tennis market classification.

Several independent methods vote, and their agreement determines confidence.
The ordering matters: Polymarket publishes an explicit ``sportsMarketType`` for
sports markets (``moneyline``, ``tennis_set_winner``, ...), which is far stronger
evidence than parsing a title. Keyword rules exist only to catch what official
metadata misses -- chiefly tennis *futures* markets, which carry the tennis tag
but no sports metadata at all (verified: "Will Jannik Sinner win a calendar
Grand Slam in 2026?" has ``sportsMarketType=None``).

Confidence is deliberately conservative. A market classified only by keyword
match lands below the alerting threshold and is flagged for review rather than
traded on.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime

from ..enums import ClassificationMethod, SportCategory, TennisMarketType
from ..logging_setup import get_logger
from ..providers.base import ProviderMarket

log = get_logger(__name__)

# Markets at or above this confidence may generate alerts.
MIN_CONFIDENCE_FOR_ALERTING = 70.0
# Below this we ask a human to look.
REVIEW_THRESHOLD = 60.0
# Minimum evidence to call a market tennis at all. A single incidental keyword
# scores below this, which keeps non-market chatter out of the tennis universe.
MIN_TENNIS_EVIDENCE = 25.0

# ---------------------------------------------------------------- vocabularies

TENNIS_TAG_SLUGS = frozenset({"tennis", "atp", "wta", "itf", "challenger"})

# Official ``sportsMarketType`` values -> our taxonomy. Verified live.
SPORTS_MARKET_TYPE_MAP: dict[str, TennisMarketType] = {
    "moneyline": TennisMarketType.MATCH_WINNER,
    "tennis_completed_match": TennisMarketType.COMPLETED_MATCH,
    "tennis_set_winner": TennisMarketType.SET_WINNER,
    "tennis_first_set_winner": TennisMarketType.SET_WINNER,
    "tennis_game_winner": TennisMarketType.GAME_WINNER,
    "tennis_total_games": TennisMarketType.TOTAL_GAMES,
    "tennis_handicap": TennisMarketType.HANDICAP,
    "tennis_correct_score": TennisMarketType.CORRECT_SCORE,
    "spread": TennisMarketType.HANDICAP,
    "totals": TennisMarketType.TOTAL_GAMES,
}

# Strong tennis indicators: tournaments and tour vocabulary.
TENNIS_KEYWORDS = frozenset(
    {
        "tennis", "atp", "wta", "itf", "challenger",
        "wimbledon", "roland garros", "french open", "us open",
        "australian open", "aus open", "grand slam",
        "indian wells", "miami open", "monte carlo", "madrid open",
        "italian open", "rome masters", "canadian open", "cincinnati",
        "shanghai masters", "paris masters", "atp finals", "wta finals",
        "davis cup", "billie jean king cup", "united cup", "laver cup",
        "queen's club", "halle open", "eastbourne", "newport",
        "citi dc open", "dc open", "washington open",
        "deuce", "tiebreak", "tie-break", "straight sets",
        "aces", "double fault", "break point",
    }
)

# Words that indicate a *different* sport, used to veto weak tennis matches.
OTHER_SPORT_KEYWORDS = frozenset(
    {
        "nba", "nfl", "mlb", "nhl", "soccer", "football", "basketball",
        "baseball", "hockey", "cricket", "golf", "pga", "ufc", "mma", "boxing",
        "formula 1", "f1", "nascar", "olympics", "rugby", "volleyball",
        "table tennis", "ping pong", "badminton", "esports", "league of legends",
        "counter-strike", "dota", "valorant", "premier league", "la liga",
        "champions league", "world cup", "super bowl",
    }
)

# Market-shape patterns, applied to a normalised title.
SET_PATTERNS = (
    re.compile(r"\bset\s*(\d+)\s*winner\b", re.I),
    re.compile(r"\b(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th)\s+set\b", re.I),
    re.compile(r"\bwin\s+set\s*(\d+)\b", re.I),
)
GAME_PATTERNS = (
    re.compile(r"\bgame\s*(\d+)\s*winner\b", re.I),
    re.compile(r"\bwin\s+game\s*(\d+)\b", re.I),
)
HANDICAP_PATTERNS = (
    re.compile(r"\b(handicap|spread)\b", re.I),
    re.compile(r"[+-]\s*\d+\.?\d*\s*(games?|sets?)\b", re.I),
)
TOTAL_PATTERNS = (
    re.compile(r"\btotal\s+(games?|sets?)\b", re.I),
    re.compile(r"\b(over|under)\s+\d+\.?\d*\s*(games?|sets?)\b", re.I),
)
COMPLETED_PATTERNS = (re.compile(r"\bcompleted\s+match\b", re.I),)
FUTURES_PATTERNS = (
    re.compile(r"\bwin\s+(the\s+)?(\d{4}\s+)?(wimbledon|us open|french open|australian open|roland garros)\b", re.I),
    re.compile(r"\b(calendar\s+)?grand\s+slam\b", re.I),
    re.compile(r"\byear[- ]end\s+(no\.?\s*1|number\s+one|ranking)\b", re.I),
    re.compile(r"\bwin\s+a\s+\d{4}\b", re.I),
    re.compile(r"\bchampion\s+(in|of)\s+\d{4}\b", re.I),
)

ORDINAL_TO_INT = {
    "first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3,
    "fourth": 4, "4th": 4, "fifth": 5, "5th": 5,
}

# Match titles look like "Tournament: Player A vs Player B".
# Accepts "vs", "vs.", "v" and "v." as the separator: all four appear in the
# wild, and a title we fail to parse loses its player metadata silently.
VS_PATTERN = re.compile(
    r"^(?:(?P<tournament>[^:]{2,80}):\s*)?(?P<a>.{2,60}?)\s+vs?\.?\s+(?P<b>.{2,60})$", re.I
)
# Market-type labels can appear as a prefix *or* after the tournament, e.g.
# "US Open: Completed Match: Fritz vs Tiafoe" -- so this is stripped anywhere,
# not just at the start.
LABEL_SEGMENT = re.compile(
    r"\b(set\s*\d+\s*winner|first\s+set\s+winner|game\s*\d+\s*winner|completed\s+match|"
    r"match\s+winner|total\s+games?(\s+(over|under)\s+\d+\.?\d*)?|handicap|winner)"
    # Labels are separated by a colon or a dash depending on the market.
    r"\s*[:\-–—]\s*",
    re.I,
)
# Trailing line/handicap tokens attached to a competitor name, e.g.
# "Alcaraz -3.5 games" -> "Alcaraz".
NAME_LINE_SUFFIX = re.compile(r"\s*[+-]\s*\d+\.?\d*\s*(games?|sets?)?\s*$", re.I)

# Grand Slams are best-of-5 for men, best-of-3 for women.
GRAND_SLAMS = ("wimbledon", "us open", "french open", "roland garros", "australian open")
SURFACE_HINTS = {
    "wimbledon": "grass", "halle": "grass", "queen": "grass", "eastbourne": "grass",
    "newport": "grass", "s-hertogenbosch": "grass",
    "french open": "clay", "roland garros": "clay", "monte carlo": "clay",
    "madrid": "clay", "rome": "clay", "italian open": "clay", "hamburg": "clay",
    "barcelona": "clay", "estoril": "clay", "munich": "clay", "kitzbuhel": "clay",
    "us open": "hard", "australian open": "hard", "indian wells": "hard",
    "miami": "hard", "cincinnati": "hard", "shanghai": "hard", "dc open": "hard",
    "citi dc open": "hard", "canadian open": "hard", "toronto": "hard",
    "montreal": "hard", "paris masters": "hard", "atp finals": "hard",
}
TOUR_PATTERNS = (
    (re.compile(r"\bwta\b|\bwomen'?s\b", re.I), "WTA"),
    (re.compile(r"\bitf\b", re.I), "ITF"),
    (re.compile(r"\bchallenger\b|\bch\b", re.I), "CH"),
    (re.compile(r"\batp\b|\bmen'?s\b", re.I), "ATP"),
)


@dataclass(slots=True)
class ClassificationResult:
    """Outcome of classifying one market."""

    sport_category: SportCategory = SportCategory.UNKNOWN
    is_tennis: bool = False
    market_type: TennisMarketType = TennisMarketType.UNKNOWN
    confidence: float = 0.0
    methods: list[ClassificationMethod] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    period_number: int | None = None
    tournament: str | None = None
    player_a: str | None = None
    player_b: str | None = None
    best_of: int | None = None
    surface: str | None = None
    tour: str | None = None

    @property
    def needs_review(self) -> bool:
        """Ambiguous results are flagged rather than silently trusted."""
        if self.is_tennis and self.market_type == TennisMarketType.UNKNOWN:
            return True
        return self.is_tennis and self.confidence < REVIEW_THRESHOLD

    @property
    def alertable(self) -> bool:
        return (
            self.is_tennis
            and self.confidence >= MIN_CONFIDENCE_FOR_ALERTING
            and self.market_type != TennisMarketType.UNKNOWN
        )

    def methods_json(self) -> str:
        return json.dumps([m.value for m in self.methods])

    def notes_text(self) -> str | None:
        return "; ".join(self.notes) if self.notes else None


def _normalise(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip().lower()


def _contains_any(haystack: str, needles: frozenset[str]) -> list[str]:
    return sorted(n for n in needles if n in haystack)


def detect_market_type(title: str, sports_market_type: str | None) -> tuple[
    TennisMarketType, int | None, ClassificationMethod
]:
    """Resolve market shape, preferring official metadata over title parsing."""
    if sports_market_type:
        key = sports_market_type.strip().lower()
        mapped = SPORTS_MARKET_TYPE_MAP.get(key)
        if mapped is not None:
            period = None
            if key == "tennis_first_set_winner":
                period = 1
            elif mapped is TennisMarketType.SET_WINNER:
                # Which set is only in the title; official metadata omits it.
                period = _extract_period(title, SET_PATTERNS)
            return mapped, period, ClassificationMethod.OFFICIAL_SPORTS_METADATA

    lowered = _normalise(title)

    for pattern in COMPLETED_PATTERNS:
        if pattern.search(lowered):
            return TennisMarketType.COMPLETED_MATCH, None, ClassificationMethod.TITLE_PARSE
    for pattern in FUTURES_PATTERNS:
        if pattern.search(lowered):
            return TennisMarketType.TOURNAMENT_FUTURE, None, ClassificationMethod.TITLE_PARSE
    period = _extract_period(lowered, SET_PATTERNS)
    if period is not None or any(p.search(lowered) for p in SET_PATTERNS):
        return TennisMarketType.SET_WINNER, period, ClassificationMethod.TITLE_PARSE
    game_period = _extract_period(lowered, GAME_PATTERNS)
    if game_period is not None or any(p.search(lowered) for p in GAME_PATTERNS):
        return TennisMarketType.GAME_WINNER, game_period, ClassificationMethod.TITLE_PARSE
    for pattern in TOTAL_PATTERNS:
        if pattern.search(lowered):
            return TennisMarketType.TOTAL_GAMES, None, ClassificationMethod.TITLE_PARSE
    for pattern in HANDICAP_PATTERNS:
        if pattern.search(lowered):
            return TennisMarketType.HANDICAP, None, ClassificationMethod.TITLE_PARSE
    if " vs " in lowered or " vs. " in lowered:
        return TennisMarketType.MATCH_WINNER, None, ClassificationMethod.TITLE_PARSE

    return TennisMarketType.UNKNOWN, None, ClassificationMethod.KEYWORD


def _extract_period(text: str, patterns: tuple[re.Pattern[str], ...]) -> int | None:
    for pattern in patterns:
        match = pattern.search(text)
        if not match:
            continue
        for group in match.groups():
            if not group:
                continue
            if group.isdigit():
                return int(group)
            mapped = ORDINAL_TO_INT.get(group.lower())
            if mapped:
                return mapped
    return None


def _clean_player_name(name: str | None) -> str | None:
    """Strip market-type labels and handicap lines from a competitor name."""
    if not name:
        return None
    cleaned = LABEL_SEGMENT.sub("", name).strip()
    cleaned = NAME_LINE_SUFFIX.sub("", cleaned).strip()
    cleaned = cleaned.strip(" -–—:")
    return cleaned or None


def parse_players(title: str | None) -> tuple[str | None, str | None, str | None]:
    """Extract ``(tournament, player_a, player_b)`` from a match title."""
    if not title:
        return None, None, None
    cleaned = re.sub(r"\s+", " ", title).strip()

    # Remove market-type labels first so the tournament segment is not confused
    # with them, then keep whatever tournament remains.
    label_free = LABEL_SEGMENT.sub("", cleaned).strip()
    label_free = label_free.strip(" -–—:").strip()

    match = VS_PATTERN.match(label_free)
    if not match:
        return None, None, None

    tournament = _clean_player_name(match.group("tournament"))
    player_a = _clean_player_name(match.group("a"))
    player_b = _clean_player_name(match.group("b"))

    # Guard against a stray "vs" inside a non-match question.
    for name in (player_a, player_b):
        if name and len(name.split()) > 5:
            return tournament, None, None
    return tournament, player_a, player_b


def infer_best_of(tournament: str | None, tour: str | None, title: str | None) -> int | None:
    """Best-of-5 only for men's Grand Slam singles; otherwise best-of-3.

    Returns None when the tour is unknown, since guessing would put a wrong
    number in front of the user with no way to tell it apart from a known one.
    """
    haystack = _normalise(f"{tournament or ''} {title or ''}")
    is_slam = any(slam in haystack for slam in GRAND_SLAMS)
    if not is_slam:
        return 3 if tour else None
    if tour == "ATP":
        return 5
    if tour in ("WTA",):
        return 3
    return None


def infer_surface(tournament: str | None, title: str | None) -> str | None:
    """Surface from tournament name only. Never guessed from context."""
    haystack = _normalise(f"{tournament or ''} {title or ''}")
    for hint, surface in SURFACE_HINTS.items():
        if hint in haystack:
            return surface
    return None


def infer_tour(
    title: str | None,
    slug: str | None,
    event_title: str | None,
    tags: list[str] | None = None,
) -> str | None:
    """Identify the tour.

    Tags are checked first: Polymarket tags matches ``atp``/``wta`` explicitly,
    whereas a title like "Wimbledon: Sinner vs Zverev" names no tour at all. Tour
    matters because it decides best-of-3 vs best-of-5 at Grand Slams.
    """
    tag_set = {t.strip().lower() for t in (tags or [])}
    for slug_name, tour in (("wta", "WTA"), ("atp", "ATP"), ("itf", "ITF"), ("challenger", "CH")):
        if slug_name in tag_set:
            return tour

    haystack = _normalise(f"{slug or ''} {title or ''} {event_title or ''}")
    for pattern, tour in TOUR_PATTERNS:
        if pattern.search(haystack):
            return tour
    return None


class TennisClassifier:
    """Multi-method tennis classifier with explainable confidence.

    ``overrides`` maps ``condition_id -> {field: value}`` and wins over every
    automated method, which is how a human correction survives re-classification.
    """

    def __init__(self, overrides: dict[str, dict[str, str]] | None = None) -> None:
        self.overrides = overrides or {}

    def classify(self, market: ProviderMarket) -> ClassificationResult:
        result = ClassificationResult()
        title = market.question or ""
        event_title = market.event_title or ""
        slug = market.slug or ""
        haystack = _normalise(f"{title} {event_title} {slug} {market.description or ''}")

        # ---------------------------------------------------- manual override
        override = self.overrides.get(market.condition_id)
        if override:
            return self._apply_override(market, override)

        # ------------------------------------------------------ evidence pass
        tag_hits = sorted(TENNIS_TAG_SLUGS & {t.lower() for t in market.tags})
        sports_type = (market.sports_market_type or "").strip().lower()
        official_tennis = sports_type.startswith("tennis_")
        # "moneyline" is shared across sports, so it only counts as tennis
        # evidence when the tag or the text agrees.
        keyword_hits = _contains_any(haystack, TENNIS_KEYWORDS)
        other_sport_hits = _contains_any(haystack, OTHER_SPORT_KEYWORDS)

        confidence = 0.0
        methods: list[ClassificationMethod] = []

        if official_tennis:
            confidence += 70.0
            methods.append(ClassificationMethod.OFFICIAL_SPORTS_METADATA)
            result.notes.append(f"official sportsMarketType={market.sports_market_type!r}")

        if tag_hits:
            confidence += 45.0
            methods.append(ClassificationMethod.TAG)
            result.notes.append(f"tags={tag_hits}")

        if sports_type == "moneyline" and (tag_hits or keyword_hits):
            confidence += 20.0
            if ClassificationMethod.OFFICIAL_SPORTS_METADATA not in methods:
                methods.append(ClassificationMethod.OFFICIAL_SPORTS_METADATA)
            result.notes.append("moneyline corroborated by tag/keyword")

        if keyword_hits:
            # Keyword evidence alone is weak; it mostly serves to corroborate.
            confidence += min(25.0, 8.0 * len(keyword_hits))
            methods.append(ClassificationMethod.KEYWORD)
            result.notes.append(f"keywords={keyword_hits[:5]}")

        if market.event_title and " vs " in _normalise(market.event_title):
            confidence += 5.0
            if ClassificationMethod.EVENT_METADATA not in methods:
                methods.append(ClassificationMethod.EVENT_METADATA)

        # -------------------------------------------------- other-sport veto
        # Table tennis is the classic false positive: the name contains "tennis"
        # and the tag is hyphenated, so both spellings are checked.
        tag_set = {t.strip().lower() for t in market.tags}
        table_tennis = (
            "table tennis" in haystack
            or "ping pong" in haystack
            or bool(tag_set & {"table-tennis", "table_tennis", "tabletennis", "ping-pong"})
        )
        if table_tennis:
            result.sport_category = SportCategory.OTHER_SPORT
            result.notes.append("vetoed: table tennis / ping pong, not lawn tennis")
            result.confidence = 90.0
            result.methods = [ClassificationMethod.TAG if tag_set else ClassificationMethod.KEYWORD]
            return result

        if other_sport_hits and not official_tennis and not tag_hits:
            result.sport_category = SportCategory.OTHER_SPORT
            result.notes.append(f"vetoed by other-sport keywords={other_sport_hits[:5]}")
            result.confidence = 70.0
            result.methods = [ClassificationMethod.KEYWORD]
            return result

        # A bare keyword mention ("Will tennis be the most watched sport?") is not
        # a tennis market. Requiring more than incidental vocabulary keeps such
        # rows out of the tennis universe entirely rather than parking them in
        # the review queue forever.
        if confidence < MIN_TENNIS_EVIDENCE:
            result.sport_category = (
                SportCategory.OTHER_SPORT if other_sport_hits else SportCategory.NON_SPORT
            )
            result.confidence = 40.0
            result.notes.append(
                "insufficient tennis evidence"
                if confidence > 0
                else "no tennis evidence"
            )
            return result

        # --------------------------------------------------------- it's tennis
        result.is_tennis = True
        result.sport_category = SportCategory.TENNIS
        result.methods = methods

        market_type, period, type_method = detect_market_type(
            title or event_title, market.sports_market_type
        )
        result.market_type = market_type
        result.period_number = period
        if type_method not in result.methods:
            result.methods.append(type_method)

        # An unresolvable market shape caps confidence: we know it's tennis but
        # not what the bet actually is, which is not tradeable information.
        if market_type is TennisMarketType.UNKNOWN:
            confidence = min(confidence, 55.0)
            result.notes.append("market type unresolved")
        elif type_method is ClassificationMethod.OFFICIAL_SPORTS_METADATA:
            confidence += 10.0

        # ------------------------------------------------------- entity parse
        tournament, player_a, player_b = parse_players(title or event_title)
        if not player_a and event_title:
            tournament, player_a, player_b = parse_players(event_title)

        result.tournament = tournament
        result.player_a = player_a
        result.player_b = player_b
        result.tour = infer_tour(title, slug, event_title, market.tags)
        result.surface = infer_surface(tournament, title or event_title)
        result.best_of = infer_best_of(tournament, result.tour, title or event_title)

        if player_a and player_b:
            confidence += 5.0
        elif market_type is not TennisMarketType.TOURNAMENT_FUTURE:
            result.notes.append("players not parsed from title")

        result.confidence = round(min(confidence, 100.0), 1)
        return result

    # ------------------------------------------------------------- overrides
    def _apply_override(
        self, market: ProviderMarket, override: dict[str, str]
    ) -> ClassificationResult:
        """A human decision is authoritative and reported at full confidence."""
        result = ClassificationResult(
            methods=[ClassificationMethod.MANUAL_OVERRIDE],
            confidence=100.0,
            notes=[f"manual override: {sorted(override)}"],
        )

        is_tennis_raw = override.get("is_tennis")
        result.is_tennis = (
            str(is_tennis_raw).lower() in ("true", "1", "yes")
            if is_tennis_raw is not None
            else True
        )
        result.sport_category = (
            SportCategory.TENNIS if result.is_tennis else SportCategory.OTHER_SPORT
        )

        type_raw = override.get("tennis_market_type")
        if type_raw:
            try:
                result.market_type = TennisMarketType(type_raw)
            except ValueError:
                log.warning(
                    "classification.bad_override_type",
                    condition_id=market.condition_id,
                    value=type_raw,
                )
                result.market_type = TennisMarketType.UNKNOWN
        elif result.is_tennis:
            result.market_type, result.period_number, _ = detect_market_type(
                market.question or "", market.sports_market_type
            )

        tournament, player_a, player_b = parse_players(market.question or market.event_title)
        result.tournament = override.get("tournament") or tournament
        result.player_a = override.get("player_a") or player_a
        result.player_b = override.get("player_b") or player_b
        result.surface = override.get("surface") or infer_surface(
            result.tournament, market.question
        )
        result.tour = override.get("tour") or infer_tour(
            market.question, market.slug, market.event_title, market.tags
        )
        best_of_raw = override.get("best_of")
        if best_of_raw and str(best_of_raw).isdigit():
            result.best_of = int(best_of_raw)
        else:
            result.best_of = infer_best_of(result.tournament, result.tour, market.question)
        return result


def match_outcome_to_player(
    outcome_label: str, player_a: str | None, player_b: str | None
) -> str | None:
    """Map an outcome label onto a full player name.

    Set markets abbreviate ("Navarro" for "Emma Navarro"), so a surname match
    against the parsed full names is required to join set-level and match-level
    performance for the same player.
    """
    label = _normalise(outcome_label)
    if not label or label in ("yes", "no"):
        return None

    for candidate in (player_a, player_b):
        if not candidate:
            continue
        cand_norm = _normalise(candidate)
        if label == cand_norm:
            return candidate
        # Surname-only labels.
        surname = cand_norm.split()[-1] if cand_norm.split() else ""
        if surname and label == surname:
            return candidate
        if label in cand_norm or cand_norm in label:
            return candidate
    return None


def is_live_at(game_start_time: datetime | None, when: datetime) -> bool | None:
    """True if ``when`` is at/after the scheduled start. None when unknown."""
    if game_start_time is None:
        return None
    return when >= game_start_time
