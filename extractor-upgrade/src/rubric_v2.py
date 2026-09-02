"""Rubric v2 - the fixes the test set actually justified, and nothing else.

Every change below names the defect it repairs and the measurement that found
it. Changes that would merely have improved the 24-case score are deliberately
absent: tuning patterns until they fire correctly on cases you happened to read
is the overfitting this programme exists to catch, and `rubric_audit.py` in
social-signal refused to do it for exactly that reason. What is different here
is that there is now a test set with ground truth fixed outside the rubric, so
a change can be shown to help rather than argued to.

The base is IMPORTED from `social-signal/src/rubric.py`. Only the deltas live
here, so the two cannot silently diverge.

=============================================================================
THE SIX DEFECTS AND WHAT WAS DONE
=============================================================================

D1  NO COMPONENT ANYWHERE ASKS WHETHER THE THING STILL EXISTS.
    Measured: 0 of 2 stale cases flagged, by construction rather than by
    failure. A tutorial teaching Polymarket's v1 CLOB client was the
    pipeline's BUILD_AND_RECOMMEND.
    FIX: a `T` currency axis. It is a GATE, not a score - currency is not a
    quantity you trade off against substance. `data/tech_currency.json` is
    rebuilt by `verify_tech.py` from the GitHub and PyPI APIs, so the list
    cannot go stale silently the way a hand-written one does.
    > The trap this catches: `pip install py-clob-client` STILL WORKS.
    > PyPI serves 0.34.6 while the GitHub repo is archived. Staleness is
    > invisible at install time, which is why a reader cannot self-correct.

D2  A COMPONENT FIRES ON A SPAN THAT SAYS THE OPPOSITE.
    Measured: S1 (+3, the top-weighted component) fires on "I haven't added
    fees or slippage yet" - the sentence stating the cost side is MISSING.
    FIX: negation guards on S1/S2/S3. Naming a cost is not accounting for one.

D3  H IS INVERTED ON A SOURCE THAT QUOTES IN ORDER TO CONDEMN.
    Measured: a post warning ABOUT strategy sellers scored H = -6 on the
    language it quotes to condemn, and was SKIPped.
    FIX: attribution guards on the negative components H6/H7/H8. A span inside
    a condemnation frame is evidence about the thing condemned, not about the
    speaker.

D4  TWO COMPONENTS ARE UNREACHABLE AND THREE ARE INTERCEPTS.
    Measured on both populations, and the two implementations disagree about
    WHICH:
      LLM read, n=38     H9 0/38, H10 0/38 dead;  S5 95%, S4 92%, H4 87%
      lexicon, n=4,432   H1b 0/4,432 dead (it has a weight and NO detector);
                         B5 0.1%, H9 0.05% effectively dead
    FIX: intercepts scored 0 and kept as evidence; the informative threshold
    lowered by the same amount so ranking is unchanged and only sources that
    LACKED the intercept stop being penalised for it. H1b given the detector
    it never had. S4's pattern loses the bare words "because" and "the reason",
    which fire on ordinary English prose rather than on a mechanism.

D5  A RESULTS CLAIM WITH NO DENOMINATOR CAN STILL BE RECOMMENDED.
    Measured: 4 of 5 MIDDLE cases were recommended by the lexicon.
    FIX: a hard gate. A source whose performance claim carries no denominator
    caps at DISCOUNT however high its substance. This is the standard
    CLAUDE.md section 6 already holds this repo's own work to; the instrument
    now obeys it too.

D6  THE PROMPT DOES NOT DECLARE 6 OF THE 21 COMPONENTS THE CODE SCORES.
    Measured mechanically: B1-B5 and H10 appear nowhere in the RUBRIC string,
    and the JSON schema it asks for has no `b_components` key at all - yet
    `validate_response` and `totals` both read one. The B axis was added to
    the code and never to the prompt.
    FIX: `PROMPT_V2` below, declaring every component the code scores. This is
    a bug, not a tuning choice.

=============================================================================
NOT FIXED, ON PURPOSE
=============================================================================

  * `verdict()` in read_video takes `teaching_quality`, a free-text model
    judgment that is NEVER PERSISTED. No verdict in `scores` can be recomputed
    from the database. v2's routing uses no unstored input, but the historical
    verdicts remain irreproducible and no amount of rubric work changes that.
  * S4 at 92% on the LLM read is left scored. Its lexicon pattern was the
    defect; whether the model is simply generous with "mechanism" needs a
    second reader, not a weight change.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import corpora

_BASE = corpora.lexicon()

HERE = Path(__file__).resolve().parent
TECH_PATH = HERE.parent / "data" / "tech_currency.json"

# ------------------------------------------------------------------ weights
# Deltas from the base, each with the measured base rate that justifies it.
S_WEIGHTS = dict(_BASE.S_WEIGHTS)
S_WEIGHTS["S5"] = 0          # 95% on the LLM read: an intercept, not a signal
B_WEIGHTS = dict(_BASE.B_WEIGHTS)
H_WEIGHTS = dict(_BASE.H_WEIGHTS)
H_WEIGHTS["H4"] = 0          # 87% on the LLM read: same
H_WEIGHTS["H10"] = -3        # -4 double-counted with H7 on promo text

INFORMATIVE_MIN = 3          # was 4; S lost exactly 1 intercept point
BUILD_ROUTE_MIN = 3          # was 4. NOT a knob: B's realistic ceiling on text
                             # is low because B2 (2.7%), B4 (4.3%) and B5
                             # (0.1%) almost never fire over 4,432 posts, so a
                             # threshold of 4 closed the build route that the
                             # B axis was added to open. B1 alone is worth 3.
BUILDABLE_MIN = 6

# --------------------------------------------------------------- D4 patterns
PATTERNS = dict(_BASE.PATTERNS)
# "because" and "the reason" fire on ordinary English, not on a mechanism.
PATTERNS["S4"] = (r"\b(who(?:'s| is) on the other side|counterparty|"
                  r"adverse selection|order flow|mispric(e|ed|ing)|"
                  r"the mechanism|market maker|inventory risk|"
                  r"the other side of (the|this) trade|why (this|it) works)\b")
# H1b had a weight and no detector: unreachable in 4,432 posts.
PATTERNS["H1b"] = (r"\b(i lost|it didn'?t work|blew up|i failed|my mistake)\b"
                   r"[^.]{0,200}?\b(so i built|that'?s why i (built|made|"
                   r"created)|which is why my|join (my|the)|dm me|link in "
                   r"(bio|description)|my (course|signals|picks|bot|tool))\b")
_COMPILED = {k: re.compile(v, re.I | re.M | re.S)
             for k, v in PATTERNS.items() if v}

# ------------------------------------------------------- D2 negation guards
# A cost named as ABSENT is not a cost accounted for. Checked in the window
# around the match, both sides, because English puts the negation either way.
NEGATE_COST = re.compile(
    r"(haven'?t|have not|hasn'?t|didn'?t|did not|don'?t|do not|not|no|"
    r"without|before|excluding|ignoring|minus|pre[- ])\s+"
    r"(yet\s+)?(added|include[d]?|including|account(ed|ing)?\s+for|"
    r"factor(ed|ing)?\s+in|net\s+of|model(l?ed|ling)?|subtract(ed|ing)?)?"
    r"[^.]{0,40}\b(fees?|slippage|spread|commission|costs?|gas|vig)\b"
    r"|\b(fees?|slippage|spread|commission|costs?|gas|vig)\b[^.]{0,40}"
    r"\b(not (yet )?(included|added|accounted|modelled|modeled)|"
    r"aren'?t included|isn'?t included|excluded|ignored|to be added)\b",
    re.I)
NEGATE_SAMPLE = re.compile(
    r"\b(only|just|merely|a mere|barely)\s+\d{1,3}\s+"
    r"(trades?|bets?|days?|samples?)\b", re.I)

# ---------------------------------------------------- D3 attribution guards
# A span the source quotes IN ORDER TO CONDEMN is evidence about the thing
# condemned, not about the speaker.
CONDEMN = re.compile(
    r"\b(scam(mers?|my)?|grift(ers?)?|snake ?oil|charlatan|fraud|"
    r"red flags?|beware|avoid|don'?t (fall|trust|buy)|steer clear|"
    r"they (say|claim|tell you|promise)|you'?ll see (people|them)|"
    r"gets? tricked|hate seeing|these (guys|people)|the (usual|classic) )"
    r"|\bnever (buy|trust|pay)\b|\bwarning\b|\bsatire\b|\bparody\b|/s\b",
    re.I)
QUOTED = re.compile(r"[\"“‘'].{0,200}?[\"”’']", re.S)

# Same defect class as CONDEMN, a different frame: a number the source states
# IN ORDER TO REFUTE IT. Found on the walk-forward video, whose entire argument
# is that its own in-sample 1,500% is fake - and which the guard-less rubric
# therefore penalised for saying so.
DEBUNK = re.compile(
    r"\b(in[- ]sample|illusion|curve[- ]?fit(ting|ted)?|overfit(ting|ted)?|"
    r"looked (like|real)|would have (been|turned)|turns? out|collapsed?|"
    r"evaporat|became \d|fell to|dropped to|out[- ]of[- ]sample|"
    r"walk[- ]forward|paper (trading|only)|not real|fake)\b", re.I)

# ---------------------------------------------------------- D5 denominator
RESULT_CLAIM = re.compile(
    r"(\bup \d+%|\b\d+(\.\d+)?%\s*(roi|returns?|gains?|win ?rate|profit)|"
    r"\bmade \$?\d[\d,]*(k|,000)?\b|\bturned \$?[\d,]+ into \$?[\d,]+|"
    r"\$[\d,]+\s*(->|to|→)\s*\$[\d,]+|\b\d+x(ed)? (my|the) (account|money))",
    re.I)
DENOMINATOR = re.compile(
    # `folds`, `windows` and `walk-forward` were missing and they are the
    # sample units of the one methodology this corpus most wants to reward.
    r"(\bn\s*=\s*\d+|\bover \d{2,}\s+(trades?|bets?|days?|markets?)|"
    r"\b\d{1,}\s+(folds?|walk[- ]forward (folds?|windows?))\b|"
    r"\b\d{2,}\s+(trades?|bets?|samples?|markets?|matches|games|periods?|"
    r"windows?|settlements?|events?)\b|"
    r"across \d{2,}|\bsample size\b)", re.I)

# D3b - THIRD-PARTY ATTRIBUTION, the same defect class as the condemnation
# guard and found the same way. A source REPORTING that Virtu made $1.597B, or
# that public wallet 88888 earned ~$2,000 in rebates, is not making a
# denominator-free performance claim about itself. Without this, a fee
# explainer and a market-structure lecture both score as boasting.
FIRST_OR_SECOND_PERSON = re.compile(
    r"\b(i|i'?ve|i'?m|my|mine|we|we'?ve|our|me|you|you'?re|your)\b", re.I)
THIRD_PARTY_SUBJECT = re.compile(
    r"\b(he|she|they|their|his|hers?|its|the (creator|author|trader|wallet|"
    r"account|firm|company|fund|study|paper|report|researchers?)|"
    r"virtu|citadel|knight|robinhood|wallet \d+|account \d+)\b", re.I)

WINDOW = 160


def _window(text, m):
    return text[max(0, m.start() - WINDOW): m.end() + WINDOW]


def _third_party(win: str) -> bool:
    """The span belongs to somebody else: a third-party subject is present and
    the source does not put itself in the sentence."""
    return bool(THIRD_PARTY_SUBJECT.search(win)
                and not FIRST_OR_SECOND_PERSON.search(win))


def _all_matches(pat, text, limit=25):
    out = []
    for i, m in enumerate(pat.finditer(text or "")):
        if i >= limit:
            break
        out.append(m)
    return out


# ---------------------------------------------------------------- T: currency

def _tech():
    if TECH_PATH.exists():
        return json.loads(TECH_PATH.read_text(encoding="utf-8")), True
    return TECH_FALLBACK, False


# Frozen snapshot, only used when data/tech_currency.json is absent. Dated so
# a reader can see how old it is instead of trusting it.
TECH_FALLBACK = {
    "checked_utc": "2026-08-04T00:00:00+00:00",
    "github": {
        "Polymarket/py-clob-client": {"dead": True,
                                      "aliases": ["py-clob-client",
                                                  "py clob client"]},
        "Polymarket/clob-client": {"dead": True,
                                   "aliases": ["@polymarket/clob-client",
                                               "clob-client"]},
        "Polymarket/agents": {"dead": True, "aliases": ["polymarket/agents"]},
    },
    "sites": {"api.pushshift.io": {"dead": True},
              "thebetterers.com": {"dead": True}},
}


_ENGLISH_WORD = re.compile(r"^[a-z]+$")


def _distinctive(alias: str) -> bool:
    """An identifier is usable only if it cannot be ordinary prose: it must
    carry a separator (`/`, `-`, `@`, `.`) or be long and compound."""
    return (len(alias) >= 6
            and (not _ENGLISH_WORD.match(alias) or len(alias) >= 12))


def currency(text: str, meta: dict | None = None, corpus: str = ""):
    """Returns (stale: bool, reasons: list[str], dated: bool).

    Two routes, both auditable:
      T1  the text names an identifier the currency table says is dead
      T2  the text teaches a venue client AND predates that client's death
    """
    tech, dated = _tech()
    t = (text or "").lower()
    reasons = []

    for repo, d in (tech.get("github") or {}).items():
        if not d.get("dead"):
            continue
        # Only DISTINCTIVE identifiers. The first version of this loop also
        # tried the repo basename, so `Polymarket/agents` contributed the
        # alias `agents` and flagged five sources stale for the word "agents".
        # An identifier that can appear in ordinary English is not an
        # identifier.
        for alias in (d.get("aliases") or []) + [repo.lower()]:
            a = alias.lower()
            if not _distinctive(a):
                continue
            if a in t:
                reasons.append(
                    f"T1 names `{alias}` - {repo} is archived on GitHub"
                    + (f" (last push {d['pushed_at'][:10]}, checked "
                       f"{tech.get('checked_utc','')[:10]})"
                       if d.get("pushed_at") else ""))
                break
    for site, d in (tech.get("sites") or {}).items():
        # `dead` is now three-valued: True (a real 4xx/5xx), False (alive), and
        # **None meaning we could not reach it** -- a timeout or DNS failure is
        # a fact about our network, not the site (verify_tech.py, corrected
        # 2026-09-01). `None` is falsy, so an unreachable site contributes NO
        # staleness reason, which is the conservative direction: it fails
        # toward not accusing a source of being dead. **Do not "simplify" this
        # to `is False`** -- that would resurrect the bug.
        if d.get("dead") and site.lower() in t:
            reasons.append(
                f"T1 names `{site}` - returns "
                f"{d.get('status') or 'no DNS'} as of "
                f"{tech.get('checked_utc','')[:10]}")

    # T2: build content that predates the venue's own breaking change.
    up = (meta or {}).get("upload_date") or ""
    if up and re.search(r"\bclob\b", t) and re.search(
            r"polymarket|poly ?market", t):
        if str(up)[:10] < "2026-04-28":
            reasons.append(
                "T2 teaches the Polymarket CLOB client and is dated "
                f"{str(up)[:10]}, before CLOB v2 went live 2026-04-28; both "
                "v1 clients are archived. `pip install py-clob-client` still "
                "succeeds, so this does not surface as an error.")
    return bool(reasons), reasons, dated


# -------------------------------------------------------------------- score

def score(text: str, meta: dict | None = None, corpus: str = "") -> dict:
    text = text or ""
    comps, fired, suppressed = [], set(), []

    for comp, pat in _COMPILED.items():
        ms = _all_matches(pat, text)
        if not ms:
            continue
        kept = None
        for m in ms:
            win = _window(text, m)
            # D2 - negation
            if comp == "S1" and NEGATE_COST.search(win):
                suppressed.append((comp, "negated cost side", _span(text, m)))
                continue
            if comp == "S3" and NEGATE_SAMPLE.search(win):
                suppressed.append((comp, "sample named as too small",
                                   _span(text, m)))
                continue
            # D3 - attribution
            if comp in ("H6", "H7", "H8") and CONDEMN.search(win):
                suppressed.append((comp, "quoted inside a condemnation",
                                   _span(text, m)))
                continue
            if comp == "H6" and _third_party(win):
                suppressed.append((comp, "someone else's result, reported",
                                   _span(text, m)))
                continue
            if comp == "H6" and DEBUNK.search(win):
                suppressed.append((comp, "a number stated in order to refute it",
                                   _span(text, m)))
                continue
            kept = m
            break
        if kept is None:
            continue
        fired.add(comp)
        axis = comp[0]
        w = (S_WEIGHTS if axis == "S" else
             B_WEIGHTS if axis == "B" else H_WEIGHTS)[comp]
        comps.append({"axis": axis, "component": comp, "weight": w,
                      "quote": _span(text, kept)})

    # H10 as in the base: promotes and discloses nothing.
    if _BASE.PROMO.search(text) and "H5" not in fired:
        m = _BASE.PROMO.search(text)
        if not CONDEMN.search(_window(text, m)):
            comps.append({"axis": "H", "component": "H10",
                          "weight": H_WEIGHTS["H10"], "quote": _span(text, m)})
            fired.add("H10")
        else:
            suppressed.append(("H10", "promo language quoted to condemn",
                               _span(text, m)))

    for strong, weak in _BASE.MUTEX:
        if strong in fired and weak in fired:
            comps = [c for c in comps if c["component"] != weak]
            fired.discard(weak)

    s = min(10, sum(c["weight"] for c in comps if c["axis"] == "S"))
    b = min(10, sum(c["weight"] for c in comps if c["axis"] == "B"))
    h = max(-10, min(11, sum(c["weight"] for c in comps if c["axis"] == "H")))

    stale, stale_why, dated = currency(text, meta, corpus)

    # D5 - the denominator gate. Only the source's OWN claims can be naked;
    # reporting a third party's published number is not boasting.
    naked = False
    for m in _all_matches(RESULT_CLAIM, text):
        if _third_party(_window(text, m)):
            continue
        if DENOMINATOR.search(text):
            break
        naked = True
        break

    v = verdict(s, b, h, stale=stale, naked_claim=naked)
    return {"s": s, "b": b, "h": h, "verdict": v, "components": comps,
            "suppressed": suppressed, "stale": stale, "stale_why": stale_why,
            "currency_dated": dated, "naked_claim": naked,
            "fired": sorted(fired)}


def _span(text, m):
    lo = max(0, m.start() - 60)
    hi = min(len(text), m.end() + 60)
    words = " ".join(text[lo:hi].split()).split()
    if len(words) >= _BASE.MAX_QUOTE_WORDS:
        c = len(words) // 2
        half = (_BASE.MAX_QUOTE_WORDS - 1) // 2
        words = words[max(0, c - half): c + half]
    return " ".join(words)


def verdict(s, b, h, stale=False, naked_claim=False) -> str:
    """Routing. Two gates sit ahead of the score, both one-directional: they
    can only lower a verdict, never raise one."""
    info = s >= INFORMATIVE_MIN or b >= BUILD_ROUTE_MIN
    buildable = b >= BUILDABLE_MIN

    if not info:
        return "SKIP"
    if naked_claim and h < 2:
        return "ABSORB_RESULTS_DISCOUNTED"
    if stale:
        return "BUILD_BUT_STALE" if buildable else "ABSORB_BUT_STALE"
    if naked_claim:
        # substance is real and honesty is positive, but the headline number
        # has no denominator: absorb it, never hand it on as a recommendation.
        return "BUILD" if buildable else "ABSORB"
    if buildable and h >= 0:
        return "BUILD_AND_RECOMMEND"
    if buildable:
        return "BUILD"
    if h >= 2:
        return "ABSORB_AND_RECOMMEND"
    if h < 0:
        return "ABSORB_RESULTS_DISCOUNTED"
    return "ABSORB"


# ---------------------------------------------------------------- D6 prompt
# The prompt the model read should use. Every component the code scores is
# declared here, including the six that were absent, and the JSON schema now
# has the `b_components` key `validate_response` has always read.
PROMPT_V2 = _BASE.__doc__ and None  # placeholder replaced below
PROMPT_V2 = """You are extracting substance from a transcript or post about
prediction markets, trading bots, and algorithmic trading. You are not
summarising. The reader wants the tools, sites, procedures and specific claims
so they never have to watch or read it.

Captions are auto-generated: punctuation is unreliable and homophones are
common ("Kashi" is Kalshi, "Poly Market" is Polymarket). Read through noise.

SCOPE: prediction markets, trading bots, algorithmic and systematic method, and
the tooling and data around them. Discretionary/manual trading education is OUT
OF SCOPE - if the source is entirely that, set on_topic=false and score nothing.

=== HARD RULE ===
Every component you award MUST carry a timestamp (seconds, a number; use 0 for
text sources) and a verbatim quote of FEWER THAN 15 WORDS copied exactly. If
you cannot cite it, do not award it. A component you cannot quote did not
happen. Do not paraphrase. Do not invent timestamps.

=== POLARITY RULE - read this before awarding anything ===
Award a component for what the source DOES, not for words it contains.
  * A cost side NAMED AS MISSING is not a cost side. "I haven't added fees or
    slippage yet" earns NOTHING on S1.
  * Language the source QUOTES IN ORDER TO CONDEMN is evidence about the thing
    condemned. A post warning about people who say "200% return, no risk" must
    not be penalised for containing that phrase.
  * Satire and parody score nothing at all. Set on_topic=false.

=== S - SUBSTANCE (0-10) ===
S1 (+3) ACCOUNTS FOR the cost side: fees, spread, slippage, gas - a number
        applied, not a word mentioned.
S2 (+2) Distinguishes backtest/theory from live/actual results.
S3 (+2) States a sample size for a performance claim.
S4 (+2) Gives a mechanism: why this works, who is on the other side.
S5 (+0) Names specific tools, sites or steps. RECORD IT, it scores nothing:
        it fires on 95% of sources, so it is an intercept, not a signal.

=== B - BUILD (0-10). A tutorial makes no trading claim, so S1/S2/S3 cannot
    fire and S caps at 4 however good the code is. B is the other route in. ===
B1 (+3) Shows working code or a runnable artifact.
B2 (+2) A complete path from nothing to a running thing.
B3 (+2) Names versions, dependencies or exact endpoints.
B4 (+2) Names a gotcha, an error, and how it was handled.
B5 (+1) A command or config a reader can reproduce.

=== H - HONESTY. Discounts results claims only; never blocks extraction. ===
H1  (+3) Shows a failure AND does not pivot to selling a fix.
H1b (+1) Shows a failure that sets up a sale. Award H1 or H1b, never both.
H2  (+3) Points to a verifiable artifact: repo, wallet, public account.
H3  (+2) A performance claim carrying n AND period AND starting capital.
H4  (+0) Names a weakness in their own method. RECORD IT, it scores nothing:
         87% base rate, an intercept.
H5  (+2) Discloses which promoted tools are their own.
H6  (-4) Performance claim with no denominator.
H7  (-2) Sells the method without disclosing the mechanism.
H8  (-1) Urgency or scarcity language.
H9  (-2) Promotes a strategy they have abandoned without saying so.
H10 (-3) Promotes a product and discloses no interest at all.

=== T - CURRENCY. A GATE, not a score. ===
T1 The source names a library, endpoint, SDK or site. LIST EVERY ONE with the
   exact identifier spoken or shown, so it can be checked against a live API.
   Do not judge whether it is current - you cannot know. Just name it.
T2 State the platform whose client is being taught, if any, and the date the
   source was published.

=== EXTRACTION ===
tools, claims, methods, watch_segments: unchanged from v1.
watch_segments: ONLY ranges that need eyes - code on screen, a live dashboard,
   a chart being read, an account balance. Be stingy.

Return ONE JSON object, no prose, no fence:
{
 "on_topic": true,
 "visual_dependent": false,
 "teaching_quality": "poor|fair|good|excellent",
 "s_components": [{"component":"S1","timestamp_s":123.4,"quote":"..."}],
 "b_components": [{"component":"B1","timestamp_s":200.0,"quote":"..."}],
 "h_components": [{"component":"H6","timestamp_s":45.0,"quote":"..."}],
 "tech_identifiers": [{"identifier":"py-clob-client","kind":"pypi",
                       "timestamp_s":300.0,"quote":"..."}],
 "platform_taught": "polymarket|kalshi|null",
 "tools": [...], "claims": [...], "methods": [...], "watch_segments": [...]
}

`teaching_quality` is REQUIRED and must be persisted alongside the score: v1's
verdict function consumed it and never stored it, so no v1 verdict can be
recomputed from the database."""
