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

# Terms that alone establish the topic.
CORE = [
    "prediction market", "predictions market", "kalshi", "polymarket", "manifold market",
    "betfair", "trading bot", "trading bots", "algorithmic trading", "algo trading",
    "quant trading", "market making", "market maker", "order book", "orderbook",
    "backtest", "back test", "limit order book", "adverse selection",
    "binary option", "event contract", "copy trading", "copytrading", "arbitrage bot",
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

# Strong off-topic markers: these subjects share vocabulary but are not the topic.
NEGATIVE = [
    "grocery", "recipe", "cooking", "workout", "makeup", "skincare",
    "minecraft", "fortnite", "roblox", "gta ", "league of legends",
    "real estate agent", "dropshipping course", "affiliate marketing",
]


def _hits(text, terms):
    found = []
    for t in terms:
        if re.search(r"(?<![a-z])" + re.escape(t) + r"(?![a-z])", text):
            found.append(t)
    return found


def g3_on_topic(title, transcript_head):
    """Title + first 500 transcript words -> (bool, evidence dict)."""
    text = f"{title or ''} \n {transcript_head or ''}".lower()
    core = _hits(text, CORE)
    ctx = _hits(text, CONTEXT)
    meth = _hits(text, METHOD)
    neg = _hits(text, NEGATIVE)

    # A core term is decisive unless a strong off-topic marker also fires and no
    # second core term backs it up.
    if core and not (neg and len(core) < 2):
        decision, why = True, "core term"
    elif len(ctx) >= 1 and len(meth) >= 2 and not neg:
        decision, why = True, "context + >=2 method terms"
    else:
        decision, why = False, "no core term and insufficient context+method"

    return decision, {
        "decision": decision,
        "rule": why,
        "core": core[:6],
        "context": ctx[:6],
        "method": meth[:6],
        "negative": neg[:4],
        "n_core": len(core),
        "n_context": len(ctx),
        "n_method": len(meth),
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

    # G1 -- transcript retrievable.
    detail["g1_transcript"] = bool(snippets)
    if not snippets:
        return "DROP_G1_NO_TRANSCRIPT", detail

    # G2 -- within 18 months. STALE is set aside, not deleted.
    age = video.get("age_months")
    detail["age_months"] = age
    detail["g2_fresh"] = (age is not None and age <= STALE_MONTHS)

    # G3 -- genuinely on topic.
    head = head_words(snippets, 500)
    on_topic, ev = g3_on_topic(video.get("title"), head)
    detail["g3"] = ev

    if not on_topic:
        return "DROP_G3_OFF_TOPIC", detail
    if age is None:
        return "DROP_G2_NO_DATE", detail
    if not detail["g2_fresh"]:
        return "STALE_G2", detail
    return "PASS", detail
