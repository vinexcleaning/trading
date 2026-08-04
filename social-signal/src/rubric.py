"""The credibility rubric, ported — not rewritten — from youtube-signal.

Weights, component meanings, the S/H separation and the verdict routing are
taken verbatim from `youtube-signal/src/read_video.py`. Two things are changed
and both are changes the sibling projects asked for in writing:

**1. The B axis is here from the start.** youtube-signal recorded the bug and
fixed it late: S1 (cost side), S2 (backtest vs live) and S3 (sample size) all
require a *trading claim*, so a pure API tutorial caps at S = 3 and auto-SKIPs
however good its code is. A Kalshi build with working code, a public repo and an
honest itemised account scored S=3 H=9 -> SKIP. B asks the different question:
does this teach you to build a thing that works?

**2. A negative component for undisclosed monetisation (H10).** youtube-signal
recorded this gap and deliberately did NOT patch it, because changing the rubric
mid-read would have invalidated comparisons between videos scored before and
after. This project has no such history, so it starts with the fix: a source
that promotes a product and discloses nothing scores below one with nothing to
disclose, instead of tying with it at zero.

S and H are never averaged. A high-S low-H source still has good tools —
discount its *results*, not its tooling.
"""
from __future__ import annotations

import re

S_WEIGHTS = {"S1": 3, "S2": 2, "S3": 2, "S4": 2, "S5": 1}
B_WEIGHTS = {"B1": 3, "B2": 2, "B3": 2, "B4": 2, "B5": 1}
H_WEIGHTS = {"H1": 3, "H1b": 1, "H2": 3, "H3": 2, "H4": 1, "H5": 2,
             "H6": -4, "H7": -2, "H8": -1, "H9": -2, "H10": -4}

MEANING = {
    "S1": "names the cost side: fees, spread, slippage, gas, vig",
    "S2": "distinguishes backtest/theory from live/actual",
    "S3": "states a sample size for a performance claim",
    "S4": "gives a mechanism: why it works, who is on the other side",
    "S5": "names specific tools, sites or steps",
    "B1": "shows working code or a runnable artifact",
    "B2": "a complete path from nothing to a running thing",
    "B3": "names versions, dependencies or exact endpoints",
    "B4": "names a gotcha, an error and how it was handled",
    "B5": "a command or config a reader can reproduce",
    "H1": "shows a failure AND does not pivot to selling a fix",
    "H1b": "shows a failure that sets up a sale",
    "H2": "points to a verifiable artifact: repo, wallet, public account",
    "H3": "a performance claim carrying n AND period AND capital",
    "H4": "names a weakness in their own method, unprompted",
    "H5": "discloses which promoted tools are their own",
    "H6": "performance claim with no denominator",
    "H7": "sells the method without disclosing the mechanism",
    "H8": "urgency or scarcity language",
    "H9": "promotes a strategy they have abandoned without saying so",
    "H10": "promotes a product and discloses no interest at all",
}

# Mechanical detectors. Every one produces a verbatim span, because the sibling
# rule is that a component you cannot quote did not happen.
PATTERNS = {
    "S1": r"\b(fees?|spread|slippage|commission|vig|juice|rake|gas fees?|"
          r"taker fee|maker fee|break ?even|transaction cost)\b",
    "S2": r"\b(back ?test(ed|ing)?|paper trad(e|ing)|out ?of ?sample|"
          r"in ?sample|forward test|live (trading|results|account)|walk ?forward)\b",
    "S3": r"(\bn\s*=\s*\d+|\b\d{2,}\s+(trades?|bets?|days?|samples?|markets?|"
          r"matches|games)\b|over \d{2,} (trades?|bets?|days?))",
    "S4": r"\b(because|the reason|who(?:'s| is) on the other side|counterparty|"
          r"adverse selection|order flow|mispric(e|ed|ing)|the mechanism|"
          r"market maker|inventory risk)\b",
    "S5": r"(https?://|`[^`]{3,}`|\bpip install\b|\bapi\b|\bendpoint\b|\bsdk\b)",
    "B1": r"(```|github\.com/|gitlab\.com/|\bdef \w+\(|\bimport \w+|"
          r"\bcurl \b|\bnpm i(nstall)?\b)",
    "B2": r"\b(step \d|first,|then,|finally,|clone the repo|set up|"
          r"from scratch|end ?to ?end)\b",
    "B3": r"(\bv?\d+\.\d+(\.\d+)?\b|requirements\.txt|package\.json|"
          r"\bpython 3\.\d+|\bnode \d+)",
    "B4": r"\b(gotcha|caveat|the trick is|i ran into|error|exception|"
          r"rate ?limit(ed)?|429|403|timed? ?out|watch out)\b",
    "B5": r"(```(bash|sh|shell|console)|^\s*\$ |\bpython \w+\.py\b)",
    "H1": r"\b(i lost|it didn'?t work|blew up|failed|my mistake|i was wrong|"
          r"doesn'?t work|gave up|stopped using|wasted)\b",
    "H2": r"(github\.com/|etherscan\.io/|polygonscan\.com/|0x[a-fA-F0-9]{20,}|"
          r"docs\.google\.com/spreadsheets)",
    "H3": r"(\b\d{2,}\s+(trades?|bets?)\b.{0,80}\b(over|across|in)\b.{0,40}"
          r"(month|week|year|day)|starting (bankroll|capital|with) \$?\d)",
    "H4": r"\b(the weakness|my (edge|method) (is|was) (thin|small|fragile)|"
          r"small sample|might be (luck|noise|variance)|could be overfit|"
          r"not enough data|take this with)\b",
    "H5": r"\b(disclosure|disclaimer|i built|my (product|tool|site|bot)|"
          r"full disclosure|i(?:'m| am) the (dev|developer|author|founder))\b",
    "H6": r"(\bup \d+%|\b\d+% (roi|returns?|gains?)|\bmade \$?\d[\d,]*(k|,000)?\b|"
          r"\bturned \$?\d+ into \$?\d+)",
    "H7": r"\b(dm me|join (my|the) (discord|group|channel)|link in bio|"
          r"my (course|signals|picks)|subscribe (to|for))\b",
    "H8": r"\b(limited (time|spots)|only \d+ (spots|left)|closing soon|"
          r"act (now|fast)|last chance|before it'?s too late)\b",
    "H9": r"\b(i don'?t (use|run) (it|this) any ?more|i stopped running|"
          r"used to run)\b",
    "H10": None,  # decided from context, not from a pattern; see score()
}
_COMPILED = {k: re.compile(v, re.I | re.M) for k, v in PATTERNS.items() if v}

# H6 must not fire on a claim that also carries its denominator; H3 is the
# same sentence done honestly, and awarding both is double-counting a single
# fact in opposite directions.
MUTEX = [("H3", "H6"), ("H1", "H1b")]

MAX_QUOTE_WORDS = 15
PROMO = re.compile(r"(ref(erral)?[=/]|discord\.gg/|t\.me/|use my (link|code)|"
                   r"promo code|\bmy (site|product|tool|service)\b)", re.I)


def _quote(text: str, m: re.Match) -> str:
    """A verbatim span under 15 words, centred on the match. The hard rule from
    youtube-signal: a component that cannot be quoted did not happen."""
    lo = max(0, m.start() - 60)
    hi = min(len(text), m.end() + 60)
    span = " ".join(text[lo:hi].split())
    words = span.split()
    if len(words) >= MAX_QUOTE_WORDS:
        centre = len(words) // 2
        half = (MAX_QUOTE_WORDS - 1) // 2
        span = " ".join(words[max(0, centre - half): centre + half])
    return span


def score(text: str):
    """Mechanical component detection. Returns (s, b, h, components).

    **This is a proxy, and the report must say so.** It is a lexicon over text,
    not a read. Its purpose is to rank what a human or a model should read
    next; `reddit_score.py` measures its agreement against hand-read threads
    rather than assuming it.
    """
    comps = []
    fired = set()
    for comp, pat in _COMPILED.items():
        m = pat.search(text or "")
        if not m:
            continue
        fired.add(comp)
        axis = comp[0]
        weight = (S_WEIGHTS if axis == "S" else
                  B_WEIGHTS if axis == "B" else H_WEIGHTS)[comp]
        comps.append({"axis": axis, "component": comp, "weight": weight,
                      "quote": _quote(text, m)})

    # H10: promotes a product and discloses no interest. Fires only when a
    # promotional pattern is present AND H5 (disclosure) is not.
    if PROMO.search(text or "") and "H5" not in fired:
        m = PROMO.search(text)
        comps.append({"axis": "H", "component": "H10", "weight": H_WEIGHTS["H10"],
                      "quote": _quote(text, m)})
        fired.add("H10")

    for strong, weak in MUTEX:
        if strong in fired and weak in fired:
            comps = [c for c in comps if c["component"] != weak]
            fired.discard(weak)

    s = min(10, sum(c["weight"] for c in comps if c["axis"] == "S"))
    b = min(10, sum(c["weight"] for c in comps if c["axis"] == "B"))
    h = max(-10, min(11, sum(c["weight"] for c in comps if c["axis"] == "H")))
    return s, b, h, comps


def verdict(s: int, b: int, h: int) -> str:
    """Routing taken from `read_video.verdict`, minus the duration and
    teaching-quality terms, which have no analogue in text."""
    info = s >= 4 or b >= 4
    buildable = b >= 6
    if buildable and info and h >= 0:
        return "BUILD_AND_RECOMMEND"
    if buildable:
        return "BUILD"
    if info and h >= 2:
        return "ABSORB_AND_RECOMMEND"
    if info and h < 0:
        return "ABSORB_RESULTS_DISCOUNTED"
    if info:
        return "ABSORB"
    return "SKIP"
