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
    },

    # -----------------------------------------------------------------------
    # TARGETED CAMPAIGN, added 2026-08-04 at the user's direction.
    #
    # The first corpus was built to answer a RETRIEVAL question -- do insider
    # queries find better videos than beginner ones -- so it was deliberately
    # broad and deliberately stratified. It is the wrong shape for the question
    # the user actually wants answered, which is narrow and practical:
    #
    #     on KALSHI and POLYMARKET specifically -- bots, strategies, data
    #     sources, and how to backtest any of it.
    #
    # RUN THIS IN ITS OWN CORPUS ($env:SIGNAL_DB = "kalshi_edge"). Adding these
    # families to the existing DB would rewrite the buckets that the
    # pre-registered retrieval test depends on.
    #
    # Four families, kept separate because they fail differently:
    #   V1 BUILD    -- venue + language + transport. Returns code, not opinion.
    #   V2 STRATEGY -- the claimed edge itself. Highest marketing density; this
    #                  is where H6 and the n-check earn their keep.
    #   V3 DATA     -- where the numbers come from. The most durable findings in
    #                  the whole project have come from this kind of query,
    #                  because a data source either exists or it does not.
    #   V4 VALIDATE -- backtesting and forward testing for event contracts,
    #                  which is where every strategy claim goes to die.
    # -----------------------------------------------------------------------
    "kalshi_polymarket_edge": {
        "V1": [
            "kalshi api python trading bot",
            "polymarket trading bot python tutorial",
            "polymarket clob client place order",
            "kalshi websocket order book python",
            "polymarket py-sdk order",
            "kalshi fix api trading",
            "polymarket agents framework llm",
            "prediction market bot automation tutorial",
        ],
        "V2": [
            "kalshi trading strategy that works",
            "polymarket arbitrage strategy",
            "kalshi sports trading edge",
            "polymarket market making strategy",
            "prediction market mispricing edge",
            "kalshi vs sportsbook arbitrage",
            "polymarket negative risk arbitrage",
            "event contract trading strategy profitable",
        ],
        "V3": [
            "kalshi historical data download",
            "polymarket historical data api",
            "polymarket subgraph query data",
            "prediction market data analysis python",
            "kalshi market data api tutorial",
            "sports odds api python historical",
        ],
        "V4": [
            "backtest prediction market strategy python",
            "kalshi backtest python",
            "polymarket backtesting framework",
            "event contract backtest walk forward",
            "prediction market paper trading test",
        ],
    },
}

# Which families carry the date filter. Nothing does, now that F3 is cut.
FAMILY_SP = {"F1": None, "F2": None, "F2B": None, "F3_RETIRED": SP_PAST_YEAR,
             "F4": None, "V1": None, "V2": None, "V3": None, "V4": None}

# Families that actually run, per topic.
ACTIVE_BY_TOPIC = {
    "prediction_markets": ("F1", "F2", "F2B"),
    "kalshi_polymarket_edge": ("V1", "V2", "V3", "V4"),
}
ACTIVE = ACTIVE_BY_TOPIC["prediction_markets"]   # back-compat for callers


def families(topic="prediction_markets"):
    t = TOPICS[topic]
    active = ACTIVE_BY_TOPIC.get(topic, ACTIVE)
    return {k: v for k, v in t.items() if k in active and v}
