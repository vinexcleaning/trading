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
        # F1+F2 terms, restricted to the past 12 months. Deliberately a mix of
        # both vocabularies so the recency axis is not confounded with the
        # insider/beginner axis.
        "F3": [
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

# Which families carry the date filter.
FAMILY_SP = {"F1": None, "F2": None, "F3": SP_PAST_YEAR, "F4": None}


def families(topic="prediction_markets"):
    t = TOPICS[topic]
    return {k: v for k, v in t.items() if k != "F4" and v}
