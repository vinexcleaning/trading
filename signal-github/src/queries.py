"""Search terms, in two families that are never merged.

The YouTube project measured Jaccard 0.037 between beginner and insider
phrasings over 446 videos. The families are reported separately here for the
same reason: if they overlap on GitHub the way they did not on YouTube, that
itself is the finding.

F1 is what someone types who wants a bot. F2 is what someone types who is
already writing one.
"""

F1_BEGINNER = [
    "kalshi bot",
    "polymarket bot",
    "prediction market trading bot",
    "sports betting bot",
    "prediction market bot",
    "polymarket trading",
    "kalshi trading",
    "betting arbitrage bot",
]

F2_INSIDER = [
    "kalshi api python",
    "polymarket clob client",
    "py-clob-client",
    "avellaneda stoikov",
    "market making inventory risk",
    "orderbook imbalance",
    "walk forward backtest",
    "negrisk polymarket",
    "kalshi websocket",
    "event contract arbitrage",
    "prediction market maker",
    "polymarket copy trading",
    "kalshi market maker",
    "gamma api polymarket",
    "conditional tokens framework",
    "polymarket websocket orderbook",
    "kalshi fills api",
    "clob orderbook market making",
]

# Code-search terms: the symbol a serious repo imports but a README never says.
# GitHub's own code search returns 401 unauthenticated, so these run against
# Sourcegraph's free public index instead. Recorded as a substitution, not a
# like-for-like.
F2_CODE = [
    "py_clob_client",
    "from py_clob_client.client import ClobClient",
    "clob.polymarket.com",
    "gamma-api.polymarket.com",
    "data-api.polymarket.com",
    "api.elections.kalshi.com",
    "trading-api.kalshi.com",
    "kalshi_python",
    "KalshiHttpClient",
    "negRisk",
    "createMarketBuyOrder polymarket",
    "avellaneda",
    "reservation_price inventory",
]

# The largest public Kalshi+Polymarket trade dataset. People building on it are
# the population most likely to have something real.
SEED_REPOS = [
    "Jon-Becker/prediction-market-analysis",
]

# Client libraries whose forks are a proxy for "repos that import this".
# GitHub's dependents graph renders client-side and is not scrapeable
# unauthenticated, so forks are the free substitute. Recorded as such.
CLIENT_LIBS = [
    "Polymarket/py-clob-client",
    "Polymarket/clob-client",
    "Polymarket/python-order-utils",
    "Kalshi/kalshi-python",
    "kalshi/kalshi-starter-code-python",
]

# Topic search is a third free axis: curated by repo owners, disjoint from text.
TOPICS = [
    "polymarket",
    "kalshi",
    "prediction-markets",
    "prediction-market",
    "market-making",
]

ON_TOPIC_TERMS = [
    "kalshi", "polymarket", "prediction market", "prediction-market",
    "clob", "event contract", "betfair", "manifold", "predictit",
    "market making", "market maker", "orderbook", "order book",
    "sportsbook", "betting odds", "arbitrage",
]
