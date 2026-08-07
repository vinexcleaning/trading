"""kalshi_read.py — read-only view of Kalshi's public tennis markets.

Every call goes through `safety.get`, which is GET-only and allowlisted. There
is no client object holding credentials because there are no credentials.

WHAT THIS MODULE KNOWS THAT THE ARCHIVE DID NOT
    SCOREBOARD.md says surface "cannot be done backwards - no way to link
    Kalshi's records to a tournament". That is true of settled markets. It is
    NOT true going forward: an open market's `rules_primary` reads

        "If Learner Tien wins the Tien vs Paul professional tennis match in
         the 2026 ATP Montreal Round Of 32 after a ball has been played..."

    so tournament, round and both surnames are all present while the market is
    live. Recording it forward is what makes surface, round and tier usable at
    all. That is the single cheapest thing this project does.

FIELD NAMES — the trap that has bitten this repo twice
    Kalshi's legacy fields (`yes_bid`, `yes_ask`, `last_price`, `volume`,
    `open_interest`) return **None**. The live values are `*_dollars` and
    `*_fp`. A recorder reading the old names writes nulls with correct row
    counts and looks perfectly healthy. GUARDS #12.

MIRRORED PAIRS — GUARDS #1
    Kalshi lists one market per player, so every event has two markets that
    are complements. Deduping on `volume_fp` is a coin weighted by the outcome
    (P(kept side wins) = 0.5356, z = +10.0). This module dedupes on
    **first ticker alphabetically**, the rule measured clean at 0.4969.
    `dedupe_event` is the only place that choice is made.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

from . import safety

BASE = "https://api.elections.kalshi.com/trade-api/v2"

# Singles head-to-head match-winner series only. Doubles, table tennis, aces,
# set/game winners, spreads and tournament-winner series are deliberately out:
# a "match" in this study is one two-player contest that settles once.
TENNIS_SERIES: tuple[str, ...] = (
    "KXATPMATCH",              # ATP main tour        - quadratic_with_maker_fees
    "KXWTAMATCH",              # WTA main tour        - quadratic_with_maker_fees
    "KXATPCHALLENGERMATCH",    # ATP Challenger       - quadratic
    "KXWTACHALLENGERMATCH",    # WTA Challenger       - quadratic
    "KXCHALLENGERMATCH",       # Challenger (legacy)  - quadratic
    "KXITFMATCH",              # ITF men              - quadratic
    "KXITFWMATCH",             # ITF women            - quadratic
)

TIER_OF_SERIES = {
    "KXATPMATCH": "ATP",
    "KXWTAMATCH": "WTA",
    "KXATPCHALLENGERMATCH": "CH",
    "KXWTACHALLENGERMATCH": "CH",
    "KXCHALLENGERMATCH": "CH",
    "KXITFMATCH": "ITF",
    "KXITFWMATCH": "ITF",
}

TOUR_OF_SERIES = {
    "KXATPMATCH": "atp",
    "KXATPCHALLENGERMATCH": "atp",
    "KXCHALLENGERMATCH": "atp",
    "KXITFMATCH": "atp",
    "KXWTAMATCH": "wta",
    "KXWTACHALLENGERMATCH": "wta",
    "KXITFWMATCH": "wta",
}

# Series whose fee_type is quadratic_with_maker_fees, verified against the live
# series index on 2026-08-06 (see common/kalshi_fees.py for the census). This
# study only ever crosses the spread, so it always pays taker; the field is
# recorded so the cost decomposition can say so rather than assume it.
MAKER_FEE_SERIES = frozenset({"KXATPMATCH", "KXWTAMATCH"})


def _f(v: Any) -> float | None:
    """Parse a Kalshi decimal-string field. None stays None — never 0."""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _cents(v: Any) -> int | None:
    d = _f(v)
    return None if d is None else int(round(d * 100))


# --------------------------------------------------------------------------
# Parsing the rules text
# --------------------------------------------------------------------------

# "... the Tien vs Paul professional tennis match in the 2026 ATP Montreal
#  Round Of 32 after a ball has been played"
_RULE = re.compile(
    r"the\s+(?P<a>.+?)\s+vs\.?\s+(?P<b>.+?)\s+"
    r"(?:professional\s+)?tennis\s+match\s+in\s+the\s+"
    r"(?P<year>\d{4})\s+(?P<rest>.+?)(?:\s+after\s+a\s+ball|\s*[.,]|$)",
    re.I,
)

_ROUND_WORDS = (
    ("Round Of 128", "R128"), ("Round Of 64", "R64"), ("Round Of 32", "R32"),
    ("Round Of 16", "R16"), ("Quarterfinal", "QF"), ("Quarter Final", "QF"),
    ("Semifinal", "SF"), ("Semi Final", "SF"), ("Final", "F"),
    ("Qualifying", "Q"), ("Qualifier", "Q"), ("Round Robin", "RR"),
)

# Surface by tournament name. Only entries we are confident about; anything
# unmatched stays None and the brief says so rather than guessing. Guessing a
# surface is exactly the kind of silent wrong answer GUARDS #13 is about.
_SURFACE_HINTS: tuple[tuple[str, str], ...] = (
    (r"wimbledon|queen|halle|eastbourne|newport|mallorca|s-hertogenbosch|stuttgart open|bad homburg|birmingham|nottingham", "Grass"),
    (r"roland garros|french open|monte.?carlo|madrid|rome|italian open|hamburg|barcelona|estoril|munich|umag|kitzbuhel|bastad|gstaad|santiago|buenos aires|rio de janeiro|cordoba|marrakech|houston", "Clay"),
    (r"australian open|us open|indian wells|miami|montreal|toronto|cincinnati|shanghai|paris masters|rolex paris|tokyo|beijing|basel|vienna|dubai|acapulco|doha|rotterdam|marseille|delray|los cabos|winston|atlanta|washington|chengdu|hangzhou|metz|antwerp|stockholm|almaty|adelaide|brisbane|auckland|hong kong|montpellier|dallas|memphis|san diego|guadalajara|monterrey|merida|austin|charleston|bogota|cluj|linz|ningbo|seoul|osaka|tokyo|zhengzhou|wuhan|guangzhou|nur.?sultan|astana", "Hard"),
)


def parse_rules(rules: str) -> dict[str, Any]:
    """Extract surnames, year, tournament, round and (best-effort) surface.

    Returns keys that are always present; unknown values are None. Nothing here
    guesses: an unrecognised tournament yields surface None, which the brief
    reports as missing so a bot can reason about the absence.
    """
    out: dict[str, Any] = {
        "surname_a": None, "surname_b": None, "year": None,
        "tournament": None, "round": None, "surface": None,
        "rules_parsed": False,
    }
    if not rules:
        return out
    m = _RULE.search(rules)
    if not m:
        return out
    rest = m.group("rest").strip()
    rnd = None
    for phrase, code in _ROUND_WORDS:
        if re.search(re.escape(phrase), rest, re.I):
            rnd = code
            rest = re.sub(re.escape(phrase), "", rest, flags=re.I).strip(" -,")
            break
    tour_prefix = re.match(r"^(ATP|WTA|ITF|Challenger)\s+", rest, re.I)
    tournament = rest[tour_prefix.end():].strip() if tour_prefix else rest
    surface = None
    for pat, surf in _SURFACE_HINTS:
        if re.search(pat, tournament, re.I):
            surface = surf
            break
    out.update(
        surname_a=m.group("a").strip(),
        surname_b=m.group("b").strip(),
        year=int(m.group("year")),
        tournament=tournament or None,
        round=rnd,
        surface=surface,
        rules_parsed=True,
    )
    return out


# --------------------------------------------------------------------------
# Market objects
# --------------------------------------------------------------------------

@dataclass
class Quote:
    """One side of one market at one instant. Prices in integer cents."""
    ticker: str
    event_ticker: str
    series: str
    player: str                 # the player this contract pays on
    yes_bid: int | None
    yes_ask: int | None
    yes_bid_size: float | None
    yes_ask_size: float | None
    last: int | None
    volume: float | None
    open_interest: float | None
    status: str
    open_time: str | None
    expected_expiration: str | None
    result: str
    fetched_at: str
    rules: dict[str, Any] = field(default_factory=dict)
    title: str = ""

    @property
    def spread(self) -> int | None:
        if self.yes_bid is None or self.yes_ask is None:
            return None
        return self.yes_ask - self.yes_bid

    @property
    def mid(self) -> float | None:
        """Present for DIAGNOSTICS ONLY. Never fill here — GUARDS #7."""
        if self.yes_bid is None or self.yes_ask is None:
            return None
        return (self.yes_bid + self.yes_ask) / 2.0

    def is_quotable(self) -> bool:
        return (
            self.yes_bid is not None and self.yes_ask is not None
            and 0 < self.yes_bid <= self.yes_ask < 100
        )


def _to_quote(m: dict, now: str) -> Quote:
    return Quote(
        ticker=m.get("ticker", ""),
        event_ticker=m.get("event_ticker", ""),
        series=m.get("ticker", "").split("-")[0],
        player=(m.get("yes_sub_title") or "").strip(),
        yes_bid=_cents(m.get("yes_bid_dollars")),
        yes_ask=_cents(m.get("yes_ask_dollars")),
        yes_bid_size=_f(m.get("yes_bid_size_fp")),
        yes_ask_size=_f(m.get("yes_ask_size_fp")),
        last=_cents(m.get("last_price_dollars")),
        volume=_f(m.get("volume_fp")),
        open_interest=_f(m.get("open_interest_fp")),
        status=m.get("status", ""),
        open_time=m.get("open_time"),
        expected_expiration=m.get("expected_expiration_time"),
        result=m.get("result", "") or "",
        fetched_at=now,
        rules=parse_rules(m.get("rules_primary") or ""),
        title=m.get("title", ""),
    )


def fetch_series(series: str, status: str = "open", limit: int = 200,
                 max_pages: int = 25) -> list[Quote]:
    """All markets in one series. Paginates. Returns [] on a 404 (GUARDS #15)."""
    now = datetime.now(timezone.utc).isoformat()
    out: list[Quote] = []
    cursor = None
    for _ in range(max_pages):
        params = {"series_ticker": series, "status": status, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        body = safety.get(f"{BASE}/markets", params=params)
        if not body:
            break
        markets = body.get("markets") or []
        out.extend(_to_quote(m, now) for m in markets)
        cursor = body.get("cursor")
        if not cursor or not markets:
            break
    return out


def fetch_market(ticker: str) -> Quote | None:
    """One market by ticker. Returns None on 404 - GUARDS #15, a 404 is not death.

    This is how settlements are read. The alternative, sweeping
    `status=settled` across all seven series every tick, pulls Kalshi's whole
    ~69-day window of closed tennis markets to find at most a handful we care
    about; measured, it was the single most expensive thing in the loop.
    """
    body = safety.get(f"{BASE}/markets/{ticker}")
    if not body or "market" not in body:
        return None
    return _to_quote(body["market"], datetime.now(timezone.utc).isoformat())


def fetch_event(event_ticker: str) -> list[Quote]:
    """Both sides of one event by event ticker."""
    body = safety.get(f"{BASE}/events/{event_ticker}",
                      params={"with_nested_markets": "true"})
    if not body:
        return []
    ev = body.get("event") or {}
    now = datetime.now(timezone.utc).isoformat()
    return [_to_quote(m, now) for m in (ev.get("markets") or [])]


def fetch_tennis(status: str = "open") -> list[Quote]:
    quotes: list[Quote] = []
    for s in TENNIS_SERIES:
        try:
            quotes.extend(fetch_series(s, status=status))
        except RuntimeError:
            # One dead series must not take the whole tick down. The runner
            # records the miss; it is a health signal, not a crash.
            continue
    return quotes


# --------------------------------------------------------------------------
# Events: the unit of observation
# --------------------------------------------------------------------------

@dataclass
class MatchView:
    """One tennis MATCH — the unit of observation, not the market row.

    GUARDS #8: a match settles once. Two mirrored markets are one observation.
    `primary` is chosen by ticker order and nothing else.
    """
    event_ticker: str
    series: str
    tier: str
    tour: str
    primary: Quote
    mirror: Quote | None
    fetched_at: str

    @property
    def players(self) -> tuple[str, str]:
        a = self.primary.player
        b = self.mirror.player if self.mirror else _other_surname(self.primary)
        return a, (b or "?")

    @property
    def surface(self) -> str | None:
        return self.primary.rules.get("surface")

    @property
    def tournament(self) -> str | None:
        return self.primary.rules.get("tournament")

    @property
    def round(self) -> str | None:
        return self.primary.rules.get("round")

    def ask_sum(self) -> int | None:
        """Cost of owning both sides. Must be >= 100 or it is gross arbitrage."""
        if self.mirror is None:
            return None
        a, b = self.primary.yes_ask, self.mirror.yes_ask
        return None if (a is None or b is None) else a + b

    def bid_sum(self) -> int | None:
        """Proceeds from selling both sides. Must be <= 100."""
        if self.mirror is None:
            return None
        a, b = self.primary.yes_bid, self.mirror.yes_bid
        return None if (a is None or b is None) else a + b

    def crossed(self) -> bool:
        """GUARDS #18 - the invariant the REAL object must satisfy.

        Selling both complementary sides cannot raise more than the dollar they
        are jointly worth. `bid_sum > 100` is impossible in a live book and
        means one side is stale. This is the check that matters for health.

        Note what it is NOT. `ask_sum < 100` is gross arbitrage and it is
        COMMON here - 15 of 122 matches on the first live tick, all on ITF,
        median 1c. It is not a stale book and it is not free money: two legs of
        Kalshi fee at those prices cost about 2.5c against a 1c gross edge.
        That reproduces this repo's own arbitrage result ("52 real violations,
        0 with enough size to trade") on a market family it had not measured.
        Calling it a health alarm would have buried a corroboration inside a
        false alert.
        """
        s = self.bid_sum()
        return s is not None and s > 100

    def gross_arb_cents(self) -> int:
        """How far below a dollar both asks sit. Gross, before any fee."""
        s = self.ask_sum()
        return max(0, 100 - s) if s is not None else 0


def _other_surname(q: Quote) -> str | None:
    a, b = q.rules.get("surname_a"), q.rules.get("surname_b")
    if not a or not b:
        return None
    p = (q.player or "").lower()
    return b if a.lower() in p or p.endswith(a.lower()) else a


def dedupe_event(quotes: Iterable[Quote]) -> MatchView | None:
    """Fold an event's markets into one MatchView.

    THE ONLY SELECTION DECISION IN THIS PACKAGE. It is made on ticker order,
    the rule measured clean at P(kept wins) = 0.4969, z = -0.88. No field that
    could know the outcome (volume, open interest, last price, liquidity)
    participates. GUARDS #1.
    """
    qs = sorted(quotes, key=lambda q: q.ticker)
    if not qs:
        return None
    primary = qs[0]
    mirror = qs[1] if len(qs) > 1 else None
    series = primary.series
    return MatchView(
        event_ticker=primary.event_ticker,
        series=series,
        tier=TIER_OF_SERIES.get(series, "?"),
        tour=TOUR_OF_SERIES.get(series, "?"),
        primary=primary,
        mirror=mirror,
        fetched_at=primary.fetched_at,
    )


def build_match_pool(quotes: Iterable[Quote]) -> list[MatchView]:
    """The SHARED pool. Every bot sees exactly this list, in this order."""
    by_event: dict[str, list[Quote]] = {}
    for q in quotes:
        if not q.event_ticker:
            continue
        by_event.setdefault(q.event_ticker, []).append(q)
    pool = [dedupe_event(v) for v in by_event.values()]
    return sorted((m for m in pool if m is not None), key=lambda m: m.event_ticker)
