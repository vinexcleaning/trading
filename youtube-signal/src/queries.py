"""Query families for the v1 topic: prediction markets / trading bots / algo trading.

Topic is a parameter -- TOPICS maps a topic key to its four families. The families
exist because they fail differently and are never merged.

F3 note (Step 1, outcome B): keyless search CAN restrict to the past 12 months
(sp=EgIIBQ==, verified server-side) but CANNOT sort by upload date (sp=CAI= is
ignored). So F3 is a date-WINDOWED relevance family, not a date-ORDERED one.
"""

# Verified working: YouTube's "past 12 months" search filter, rolling window.
SP_PAST_YEAR = "EgIIBQ%3D%3D"

TOPICS = {
    "prediction_markets": {
        # What a newcomer would type.
        "F1": [
            "how to build a trading bot",
            "prediction markets explained",
            "algorithmic trading for beginners",
            "make money polymarket",
        ],
        # Vocabulary only a practitioner uses. This family is the point of the
        # project -- the hypothesis is that it surfaces low-view, high-specificity
        # videos that F1 never reaches.
        "F2": [
            "kalshi api python",
            "polymarket clob api",
            "adverse selection market making",
            "orderbook imbalance signal",
            "walk forward backtest overfitting",
            "prediction market fee formula",
            "polymarket copy trading wallet",
            "kalshi paper trading bot",
            "market maker inventory risk crypto",
            "win rate sample size confidence interval trading",
            "taker fee slippage binary options",
            "websocket order book recorder",
        ],
        # F2B -- 12 ADDITIONAL insider terms, added in Phase 2.
        #
        # Rationale: F1 and F2 came out nearly disjoint (Jaccard 0.037), so the
        # number of insider terms is the main lever on corpus size, and 12 was an
        # arbitrary starting number.
        #
        # These are deliberately more domain-anchored than the original F2. Phase 1
        # showed that the two loosest F2 terms -- "websocket order book recorder"
        # and "win rate sample size confidence interval trading" -- pulled in
        # generic software and university statistics teaching, and were the main
        # source of F2's low pass rate. Every term below names a venue, a specific
        # mechanism, or a named tool, so it cannot match a generic tutorial.
        #
        # THE USER SHOULD CORRECT THIS LIST. It is generated vocabulary, not
        # domain authority.
        "F2B": [
            "polymarket gamma api",              # Polymarket's actual API name
            "kalshi websocket feed",             # venue + transport
            "negative risk polymarket negrisk",  # Polymarket multi-outcome mechanism
            "uma oracle polymarket resolution",  # how Polymarket markets settle
            "brier score calibration forecasting",
            "kelly criterion position sizing",
            "closing line value sports betting",  # sharp-bettor term of art
            "implied probability vig removal",
            "prediction market arbitrage kalshi polymarket",
            "event contract settlement rules",
            "maker rebate taker fee exchange",
            "vectorbt backtesting python",       # named tool
        ],

        # F3 is CUT as of Phase 2.
        #
        # It was only 20.4% exclusive, it overlapped F1 and F2 at ~0.25 by
        # construction (it reused their terms), Step 1 had already cost it its
        # date-ORDERING, and its date filter pre-satisfied gate G2 -- which
        # inflated its apparent low-view yield in the Phase 1 measurement.
        # Recency is now handled per-claim via expires_after_months, not by
        # filtering whole videos.
        #
        # The queries are kept here, unused, so the decision is legible rather
        # than looking like they were forgotten.
        "F3_RETIRED": [
            "how to build a trading bot",
            "prediction markets explained",
            "make money polymarket",
            "kalshi api python",
            "polymarket clob api",
            "polymarket copy trading wallet",
            "kalshi paper trading bot",
            "adverse selection market making",
        ],
        # F4 is deferred to Phase 3, once tools have been extracted.
        "F4": [],
    }
}

# Which families carry the date filter. Nothing does, now that F3 is cut.
FAMILY_SP = {"F1": None, "F2": None, "F2B": None, "F3_RETIRED": SP_PAST_YEAR, "F4": None}

# Families that actually run.
ACTIVE = ("F1", "F2", "F2B")


def families(topic="prediction_markets"):
    t = TOPICS[topic]
    return {k: v for k, v in t.items() if k in ACTIVE and v}
