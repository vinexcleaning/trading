"""STEP 6 gates: G1 transcript, G2 age, G3 on-topic.

G3 HONESTY NOTE
---------------
The brief specifies "cheap LLM yes/no on title + first 500 transcript words".
There is no LLM API key on this machine (Phase 0 established there is no
YOUTUBE_API_KEY either; no Anthropic/OpenAI key is present in the environment).
Rather than silently skip the gate or silently substitute something and call it an
LLM, G3 is a deterministic lexicon classifier whose decisions are auditable --
every decision records exactly which terms fired.

Its agreement with an actual LLM judgment is MEASURED on a stratified sample in
src/validate_g3.py, and that agreement number is reported. A classifier whose
error rate is unknown is not a gate, it is a guess.
"""

import re

STALE_MONTHS = 18

# A caption track that is almost entirely [Music]/[Applause] is not a transcript.
# Measured: the four "Backtesting Walk Forward Optimization Global N Futures"
# uploads carry 13-92 real words; genuine videos in this set carry 2,786-7,517.
# 100 separates them with room to spare.
MIN_REAL_WORDS = 100
_TAG = re.compile(r"\[[^\]]*\]|\([^)]*\)")


def real_words(snippets):
    """Word count excluding bracketed sound tags."""
    full = " ".join(s["text"] for s in snippets or [])
    return len(_TAG.sub(" ", full).split())

# Terms that alone establish the topic.
CORE = [
    "prediction market", "predictions market", "kalshi", "polymarket", "manifold market",
    "betfair", "trading bot", "trading bots", "algorithmic trading", "algo trading",
    "quant trading", "market making", "market maker", "order book", "orderbook",
    "backtest", "back test", "limit order book", "adverse selection",
    "binary option", "event contract", "copy trading", "copytrading", "arbitrage bot",
    # Promoted from METHOD after validation: walk-forward analysis is a specific
    # practitioner technique, and 4 of 5 G3 false negatives were walk-forward
    # trading education that fired no core term.
    "walk forward", "walkforward",
    # Added Phase 2. The holdout dropped "How To Build A Self-Improving AI Trading
    # Agent" as off-topic because the vocabulary moved to "agent" and the lexicon
    # did not follow.
    "trading agent", "ai agent", "ai trading", "autonomous agent",
    "systematic trading", "quantitative trading", "statistical arbitrage",
    "paper trading", "order flow", "market microstructure", "clob",
]

# Trading/markets context -- necessary but not sufficient on its own.
CONTEXT = [
    "trading", "trader", "trade", "market", "markets", "exchange", "broker",
    "portfolio", "position", "hedge", "crypto", "bitcoin", "futures", "options",
    "stocks", "forex", "betting", "odds", "wager", "bankroll",
]

# Method/技術 terms -- necessary but not sufficient on its own.
METHOD = [
    "api", "python", "websocket", "bot", "script", "automate", "automated",
    "strategy", "signal", "indicator", "sharpe", "win rate", "edge", "expectancy",
    "slippage", "spread", "liquidity", "fee", "fees", "commission", "sample size",
    "confidence interval", "overfit", "walk forward", "sharpe ratio", "drawdown",
    "profit", "roi", "pnl", "p&l",
]

# Strong off-topic markers: different subjects that share vocabulary.
#
# "recipe" was REMOVED in Phase 2. It fired on the idiom "a recipe for disaster"
# in a quantitative-trading video and suppressed a correct classification. Any
# marker that is also a common English idiom is a liability here.
NEGATIVE = [
    "grocery", "cooking recipe", "workout", "makeup", "skincare",
    "minecraft", "fortnite", "roblox", "league of legends",
    "real estate agent", "dropshipping course", "affiliate marketing",
]

# ---------------------------------------------------------------------------
# PHASE 2 BOUNDARY (decided 2026-08-02)
#
# IN SCOPE : prediction markets, trading bots, algorithmic and systematic method,
#            and the tooling and data around them.
# OUT      : discretionary / manual trading education -- chart reading, technical
#            analysis instruction, trading psychology, "my setup" content.
#
# Rationale: the extraction target is tools, sites and procedures with verifiable
# artifacts. Discretionary content has none of those and carries the platform's
# highest marketing density.
#
# The exclusion is deliberately CONDITIONAL, not absolute. It only fires when
# discretionary markers are present AND no systematic/prediction-market core term
# is. A video can teach chart patterns and still be about building a bot.
# ---------------------------------------------------------------------------
DISCRETIONARY = [
    "candlestick", "candle stick", "chart pattern", "head and shoulders",
    "support and resistance", "supply and demand zone", "entry zone",
    "fibonacci", "elliott wave", "ict", "smart money concept", "order block",
    "fair value gap", "price action", "trading psychology", "discipline",
    "my setup", "trade with me", "day trading strategy", "scalping strategy",
    "swing trading strategy", "technical analysis", "rsi", "macd",
    "moving average crossover", "trendline",
]

# Core terms that establish SYSTEMATIC intent specifically. A hit here overrides
# the discretionary exclusion.
SYSTEMATIC_CORE = [
    "prediction market", "kalshi", "polymarket", "manifold market", "betfair",
    "trading bot", "algorithmic trading", "algo trading", "quant trading",
    "market making", "market maker", "order book", "orderbook",
    "limit order book", "adverse selection", "event contract",
    "copy trading", "copytrading", "arbitrage bot", "api", "backtest",
    "back test", "walk forward", "trading agent", "ai agent",
]


def _hits(text, terms):
    """Match a term, allowing an optional trailing plural 's'.

    Without the 's?' the core term "prediction market" fails to match the phrase
    "prediction markets" -- which is how a video titled "Prediction Markets Are Now
    Live on tastytrade" was classified off-topic. That was a real false negative
    found in validation, not a hypothetical.
    """
    found = []
    for t in terms:
        if re.search(r"(?<![a-z])" + re.escape(t) + r"s?(?![a-z])", text):
            found.append(t)
    return found


def g3_on_topic(title, transcript_head):
    """Title + first 500 transcript words -> (bool, evidence dict).

    PHASE 2 RETUNE -- recall over precision, deliberately.

    The asymmetry was wrong before. A false positive costs one transcript read;
    a false negative loses a video permanently, because nothing downstream ever
    reconsiders a dropped video. So this gate is now permissive and the real topic
    call belongs to the LLM read in Step 2.

    Changes from Phase 1:
      * the context+method bar dropped from >=2 method terms to >=1
      * a negative marker no longer overrides a core term, it only blocks the
        weaker context+method route
      * the boundary exclusion (discretionary trading) fires only when NO
        systematic core term is present
    """
    text = f"{title or ''} \n {transcript_head or ''}".lower()
    core = _hits(text, CORE)
    ctx = _hits(text, CONTEXT)
    meth = _hits(text, METHOD)
    neg = _hits(text, NEGATIVE)
    disc = _hits(text, DISCRETIONARY)
    sysc = _hits(text, SYSTEMATIC_CORE)

    # Boundary: discretionary content with no systematic signal is out of scope.
    if disc and not sysc:
        decision, why = False, f"out of scope: discretionary ({len(disc)} markers), no systematic core"
    elif core:
        decision, why = True, "core term"
    elif ctx and meth and not neg:
        decision, why = True, "context + method term (recall-tuned)"
    else:
        decision, why = False, "no core term and insufficient context+method"

    return decision, {
        "decision": decision,
        "rule": why,
        "core": core[:6],
        "context": ctx[:6],
        "method": meth[:6],
        "negative": neg[:4],
        "discretionary": disc[:6],
        "systematic": sysc[:6],
        "n_core": len(core),
        "n_context": len(ctx),
        "n_method": len(meth),
        "n_discretionary": len(disc),
    }


def head_words(snippets, n=500):
    words = []
    for s in snippets or []:
        words.extend(s["text"].split())
        if len(words) >= n:
            break
    return " ".join(words[:n])


def classify(video, snippets):
    """Apply all three gates. Returns (gate_status, detail).

    Gates are evaluated independently so the census can say which gates a video
    would have failed, not just the first one it hit.
    """
    detail = {}

    # G1 -- transcript retrievable AND usable.
    detail["g1_transcript"] = bool(snippets)
    if not snippets:
        return "DROP_G1_NO_TRANSCRIPT", detail
    detail["real_words"] = real_words(snippets)
    if detail["real_words"] < MIN_REAL_WORDS:
        return "DROP_G1_EMPTY_TRANSCRIPT", detail

    # G2 -- within 18 months. STALE is set aside, not deleted.
    age = video.get("age_months")
    detail["age_months"] = age
    detail["g2_fresh"] = (age is not None and age <= STALE_MONTHS)

    # G3 -- genuinely on topic.
    head = head_words(snippets, 500)
    on_topic, ev = g3_on_topic(video.get("title"), head)
    detail["g3"] = ev

    if not on_topic:
        # Distinguish "different subject" from "in the trading world but out of
        # the Phase 2 scope boundary" -- they are different census lines.
        if ev.get("n_discretionary"):
            return "DROP_G3_DISCRETIONARY", detail
        return "DROP_G3_OFF_TOPIC", detail
    if age is None:
        return "DROP_G2_NO_DATE", detail
    if not detail["g2_fresh"]:
        return "STALE_G2", detail
    return "PASS", detail
