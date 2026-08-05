"""The labelled test set: cases where the right answer is fixed by something
OUTSIDE the rubric.

The inclusion rule is deliberately strict, because the failure mode of a
"validated" rubric is that it was validated against its author's taste. A case
enters this file only if its label is decided by one of:

  ARITH   arithmetic on numbers the source itself states
  LIVE    an HTTP / API check runnable today (archive status, dead link)
  EXTERN  an external fact this repo has already primary-sourced
  SELFCON an internal contradiction inside the source

`why` names which one, and `evidence` states the fact. If neither can be
written down, the case does not belong here.

GROUND TRUTH, two axes:

  gt_action  what should happen to the source. Ordinal:
             REJECT(0) < DISCOUNT(1) < ABSORB(2) < RECOMMEND(3)
  gt_stale   True when the source teaches a path that no longer works.
             This is a SEPARATE axis on purpose: a stale tutorial is not
             dishonest and its concepts may still be worth absorbing. What it
             must never be is RECOMMENDED.

gt_class is the brief's four-way split and is reported, but the matrix is built
on gt_action because that is the decision the rubric actually drives.

> ONE OF THE BRIEF'S FIVE NAMED CASES IS NOT IN THIS REPO. The "33 trades /
> $23.53 total profit / summed winners +$127 / wallet cold for 2 months" case
> appears in no corpus here: no transcript in either youtube-signal database
> contains "23.53", no report or markdown file does either, and the nearest
> match (a fully-disclosed break-even stink-bid bot, 34 buys / 34 sells / net
> +8c, `rrLnJO5x_Po`) is a different video with a different shape. It is
> recorded as MISSING rather than reconstructed from memory, and two verifiable
> cases were substituted.
"""
from __future__ import annotations

from dataclasses import dataclass, field

ACTIONS = ["REJECT", "DISCOUNT", "ABSORB", "RECOMMEND"]
ACTION_RANK = {a: i for i, a in enumerate(ACTIONS)}

# How each rubric's verdict vocabulary maps onto the action axis. Both the
# youtube-signal LLM rubric and the social-signal lexicon emit these strings.
VERDICT_TO_ACTION = {
    "BUILD_AND_RECOMMEND": "RECOMMEND",
    "ABSORB_AND_RECOMMEND": "RECOMMEND",
    "RECOMMEND": "RECOMMEND",
    "BUILD": "ABSORB",
    "ABSORB": "ABSORB",
    "ABSORB_RESULTS_DISCOUNTED": "DISCOUNT",
    "RESULTS_DISCOUNTED": "DISCOUNT",
    "SKIP": "REJECT",
    # v2 additions
    "BUILD_BUT_STALE": "ABSORB",
    "ABSORB_BUT_STALE": "ABSORB",
}


@dataclass
class Case:
    cid: str
    corpus: str          # yt | yt_kalshi | reddit | github
    key: str             # video_id | post_id | full_name
    label: str           # human-readable name
    gt_class: str        # GENUINE | MIDDLE | MARKETING | STALE
    gt_action: str       # the centre of the acceptable band
    gt_stale: bool
    why: str             # ARITH | LIVE | EXTERN | SELFCON
    evidence: str
    note: str = ""
    tags: list = field(default_factory=list)
    band: tuple = ()     # (min, max) inclusive; empty means a point label

    def accepts(self, action: str) -> bool:
        if not self.band:
            return action == self.gt_action
        lo, hi = (ACTION_RANK[self.band[0]], ACTION_RANK[self.band[1]])
        return lo <= ACTION_RANK[action] <= hi

    def distance(self, action: str) -> int:
        r = ACTION_RANK[action]
        if not self.band:
            return abs(r - ACTION_RANK[self.gt_action])
        lo, hi = ACTION_RANK[self.band[0]], ACTION_RANK[self.band[1]]
        return 0 if lo <= r <= hi else min(abs(r - lo), abs(r - hi))

    @property
    def band_str(self) -> str:
        return (f"{self.band[0]}..{self.band[1]}" if self.band
                else self.gt_action)


# WHY BANDS EXIST, stated rather than buried: for some cases the outside
# evidence fixes a BOUND, not a point. A fully disclosed negative post-mortem
# must not be discounted and must not be rejected - whether it is also worth a
# human's own 19 minutes is taste, and encoding taste as ground truth would
# make this an opinion poll wearing a confusion matrix. Banded cases are marked
# in the report. The two metrics that decide anything - false RECOMMEND and
# false REJECT - are unaffected by the width of a band that excludes them.


CASES = [
    # ---------------------------------------------------------------- GENUINE
    Case("C01", "yt", "Ib0BEFKAvn0",
         "Part Time Larry - Kalshi + Perplexity Sonar build",
         "GENUINE", "RECOMMEND", False, "LIVE",
         "Working code demonstrated on screen against a public repo; a real "
         "Kalshi account itemised on screen (~$100 in, +$68); nothing sold. "
         "The video also states the negative result that Sonar structured "
         "output is ~90% reliable and non-deterministic across two identical "
         "runs - a build blocker disclosed against its own tutorial.",
         note="THE BRIEF'S NAMED RUBRIC FAILURE. Scored S=3 H=9 -> SKIP before "
              "the B axis existed. Kept as a regression case.",
         tags=["brief", "anchor"]),

    Case("C02", "yt", "vT0qMNgOkxo",
         "Part Time Larry - Why Kalshi bettors lose (72M trades)",
         "GENUINE", "RECOMMEND", False, "EXTERN",
         "n = 72,000,000 trades, the full Kalshi tape to Jan 2026. Its "
         "headline finding - makers earn ~2.5% excess per trade, takers lose "
         "it - is the same direction this repo primary-sourced from Kalshi's "
         "own fee schedule (maker 0.0175 vs taker 0.07). Its long-shot number "
         "(5c contracts resolve YES 4.18%) is a calibration statement testable "
         "against the public tape."),

    Case("C03", "yt", "_BfpVLXB2Qw",
         "Mr. Finance Digital - The economics of becoming a market maker",
         "GENUINE", "RECOMMEND", False, "EXTERN",
         "Every load-bearing number is a public corporate fact: Virtu lost "
         "money on 1 of 1,238 trading days 2009-2014 (their own S-1/filings), "
         "Citadel Securities $12.2B 2025 trading revenue, Knight Capital's "
         "$440M/45min on 2012-08-01. 8 views, sells nothing."),

    Case("C04", "yt_kalshi", "7HXoCMMXr-8",
         "Emil Nielsen - Polymarket's new fees",
         "GENUINE", "RECOMMEND", False, "EXTERN",
         "Independently corroborated inside this repo: signal-github's "
         "CORRECTIONS.md C2 measured Polymarket's Gamma schedule over 2,100 "
         "markets and found makers pay zero on 100% of markets carrying a "
         "schedule, taker by category, rebate 15-25%. The video's claims "
         "(taker-only, fee peaks at 50c, rebate share cut to 20% in Jan 2026) "
         "match an instrument built without reference to it."),

    Case("C05", "yt_kalshi", "lIMu8ysJW68",
         "AI Pathways - walk-forward backtesting",
         "GENUINE", "RECOMMEND", False, "SELFCON",
         "The video argues against its own upgrade path and shows the numbers: "
         "a retail RSI backtest 199% -> 5% out of sample over 19 folds, then "
         "its own 'institutional' rewrite 1,500% -> 7%. A creator whose "
         "conclusion costs them their own pitch is the cheapest honesty test "
         "there is. Also names the scipy filtfilt zero-phase look-ahead trap, "
         "which is verifiable from scipy's own documentation."),

    Case("C06", "yt_kalshi", "Ea9BeOc_Yiw",
         "polyReplaydev - backtesting a Polymarket bot on historical data",
         "GENUINE", "RECOMMEND", False, "EXTERN",
         "Its 8 fill-realism rules (taker at ask, maker only when the ask "
         "crosses, fees in-engine, 50-150ms latency plus 200ms on taker fills, "
         "depth check before entry) are the same rules bot-hunt's own "
         "validate_engine.py independently arrived at, and its headline - "
         "'without latency, most strategies are profitable' - is reproduced by "
         "this repo's deliberate mid-price leak canary (+0.32c, half the "
         "quoted spread)."),

    Case("C07", "yt", "btG5YpvPkwE",
         "Sharbel A. - self-healing bot, $50 -> $500 -> $0",
         "GENUINE", "ABSORB", False, "SELFCON",
         "A complete negative post-mortem with the denominator attached: 814 "
         "trades, $50 start, ~$500 peak, ended at exactly $0, of which -$115 "
         "was fees. Then states that hand-tuning after the failure made it "
         "worse (win rate 19% -> 12%). Nothing here flatters the creator.",
         note="The brief's 'honest, absorb, negative result' case.",
         tags=["brief"]),

    Case("C08", "reddit", "1v56b7h",
         "r/algotrading - Hyperliquid copy bot, 10 lessons",
         "GENUINE", "RECOMMEND", False, "SELFCON",
         "Opens 'Do not ask for the bot. I am not selling anything.' Every "
         "lesson carries a number and most are failures. Reaches this repo's "
         "own closed copy-trading verdict from a different venue and then goes "
         "past it: the leak is exit fidelity, not entry latency - simulating "
         "zero lag barely moved the numbers."),

    Case("C09", "reddit", "1r0b2ni",
         "r/algotrading - PyKalshi open-source client announcement",
         "GENUINE", "RECOMMEND", False, "LIVE",
         "pip-installable package, public repo, demo notebook, author "
         "discloses authorship in the title. A library announcement makes no "
         "trading claim at all, which is precisely the shape S1/S2/S3 cannot "
         "score.",
         tags=["build_axis"]),

    Case("C10", "reddit", "1sj92sg",
         "r/algotrading - 'retail algo trading is gambling', 182 replies",
         "GENUINE", "ABSORB", False, "EXTERN",
         "Cites the multi-year Taiwanese day-trader study (Barber/Lee/Liu/"
         "Odean, a real and much-replicated result) and separates latency, "
         "friction and alpha decay as three distinct mechanisms. Text can cite "
         "external evidence; the rubric has no component that rewards it.",
         tags=["missing_component"]),

    Case("C11", "reddit", "1qx9xq2",
         "r/algotrading - 'nobody will ever sell you a real edge'",
         "GENUINE", "ABSORB", False, "SELFCON",
         "The post's whole argument is that anyone with an edge has no reason "
         "to sell it. The scam language it contains ('dm me', '200% return and "
         "no risk') is QUOTED IN ORDER TO CONDEMN IT. Whether a span is "
         "asserted or quoted is decidable from the surrounding sentence.",
         tags=["polarity"]),

    Case("C12", "github", "artyomderkach-bit/kalshi-15m-market-maker",
         "artyomderkach-bit - Kalshi 15m market maker",
         "GENUINE", "RECOMMEND", False, "LIVE",
         "0 stars, MIT licensed, ships in paper mode, makes no profit claim, "
         "states what it withholds, and imports one fair-value function into "
         "both engine and backtest 'so they can never drift apart'. Its own "
         "README says almost every edge that looked real in-sample decayed out "
         "of sample - a claim against its own product."),

    # ----------------------------------------------------------------- MIDDLE
    Case("C13", "yt", "YknxNkTgNWk",
         "Coin Bureau Trading - '+1,560% ROI With OpenClaw'",
         "MIDDLE", "DISCOUNT", False, "SELFCON",
         "The title number is PAPER: $260 simulated across six strategies, 500 "
         "trades in one week. The only real-money figure in the video is a "
         "live account going $100 -> ~$30 in one day. The same video reports a "
         "paper engine that compounded a $30 start into a claimed $6.2M "
         "through a bug. Headline and evidence point opposite ways.",
         note="THE BRIEF'S NAMED CASE. Current pipeline verdict: ABSORB, not "
              "discounted.",
         tags=["brief", "anchor"]),

    Case("C14", "yt_kalshi", "8u6jy8v56ww",
         "Amon - Polymarket BTC 5-minute, '96.83% win rate'",
         "MIDDLE", "DISCOUNT", False, "ARITH",
         "The 96.83% subset's own n is NEVER STATED - only the 12,272 total "
         "periods, of which the four-consecutive-up subset is a small "
         "fraction. And its 'conservative' projection of $2,500 -> $40,000 per "
         "month is a 1,500% MONTHLY return, which compounds to ~10^25 in a "
         "year. A stated projection that is arithmetically absurd is a "
         "denominator-free performance claim whatever else the video gets "
         "right."),

    Case("C15", "yt_kalshi", "ANGZMUercB4",
         "Matt Downs - Kalshi, the 3 numbers",
         "MIDDLE", "DISCOUNT", False, "SELFCON",
         "Claims to have proved the method 'over hundreds and thousands of "
         "tickets' and shows no count, no period, no capital and no record. "
         "Separately discloses that its own demonstrated mispriced prop had "
         "~$60 of liquidity - the method's own worked example does not size."),

    Case("C16", "yt", "sQZbxKXbk9g",
         "Prediction Quant - cross-venue arbitrage walkthrough",
         "MIDDLE", "DISCOUNT", False, "ARITH",
         "The worked 'guaranteed' arb is stated PRE-FEE: buy YES on Polymarket "
         "at 20c risking $10.80 and NO on Kalshi at 54c risking $29.06, "
         "$39.86 total for ~$14. Kalshi's own schedule bills the winning leg "
         "at 0.07*C*P*(1-P) rounded up, and the quoted edge is not net of it. "
         "An arbitrage claim quoted gross of the fee that decides it is a "
         "results claim without its cost side."),

    Case("C17", "yt", "rrLnJO5x_Po",
         "Moon Dev - AI bot trades Polymarket 24/7",
         "MIDDLE", "ABSORB", False, "SELFCON",
         "The live disclosed result is honest and NEGATIVE-to-flat: 34 buys, "
         "34 sells over one full day, net +8 cents, with the wallet shown. The "
         "same video asserts 'every time you trade by hand you're trading 3x "
         "less profitably' and an 8x figure attributed to a viewer comment, "
         "neither carrying any denominator. Absorb the tape, discard the "
         "multipliers."),

    Case("C18", "yt", "W722Ca8tS7g",
         "Unbiased Trading - 4 backtesting techniques",
         "MIDDLE", "DISCOUNT", False, "SELFCON",
         "Contains a genuinely useful execution-delay sweep, then states "
         "'these were the results the previous month where I did around 18%' "
         "on an automated portfolio with no trade count, no capital and no "
         "period beyond 'a month'. 122,687 views on the strength of it."),

    Case("C19", "github", "evan-kolberg/prediction-market-backtesting",
         "evan-kolberg - prediction market backtesting (1,098 stars)",
         "MIDDLE", "ABSORB", False, "SELFCON",
         "The most rigorous machinery in the GitHub corpus and its Kalshi "
         "taker-fee formula is correct - but the repo CONTRADICTS ITSELF on "
         "maker fees between its instrument metadata (makers pay 0) and its "
         "fee model (0.07), and a passive strategy inside it reads the one the "
         "backtest ignores. Absorb the engine, reject the maker numbers."),

    # -------------------------------------------------------------- MARKETING
    Case("C20", "yt", "PeutA_HKxew",
         "Rolink Craft - 'Poly Sniper AI', the best Polymarket bot",
         "MARKETING", "REJECT", False, "ARITH",
         "$300 becoming $15,000 'by the end of the week' is a 4,900% weekly "
         "return; compounded for one year that is ~10^70 dollars, more than "
         "the atoms in the observable universe. There is no artifact: the "
         "'bot' is a download behind a link in the description, the 70-80% win "
         "rate carries no n, and the single demonstrated trade is n=1. Nothing "
         "in it survives contact with arithmetic.",
         tags=["anchor"]),

    Case("C21", "reddit", "1skauaj",
         "r/algotrading - 'am i ready to go live?' (satire)",
         "MARKETING", "REJECT", False, "SELFCON",
         "A parody post enumerating every beginner error in sequence: two "
         "weeks of 5-minute candles, parameters tuned until the equity curve "
         "turns green, leverage to compensate, and the strategy withheld so JP "
         "Morgan cannot steal it. There is no method in it to absorb. It is "
         "here because the lexicon's top-weighted component fires on the "
         "sentence 'I haven't added fees or slippage yet' - the sentence that "
         "says the cost side is MISSING.",
         tags=["polarity", "anchor"]),

    Case("C22", "github", "aulekator/Polymarket-BTC-15-Minute-Trading-Bot",
         "aulekator - Polymarket BTC 15-minute bot (557 stars, 4 commits)",
         "MARKETING", "REJECT", False, "LIVE",
         "557 stars against 4 commits. Invents three mutually inconsistent fee "
         "schedules for one venue, ships fee_rate_bps=0 in the live path, "
         "advertises a 'self-learning' feature its own README calls a "
         "placeholder, and carries an MIT badge with no LICENSE file (the "
         "license field in the GitHub API is empty). Zero occurrences of "
         "'backtest' anywhere in the repository.",
         note="Included as a TRUE POSITIVE control: signal-github's own "
              "trust_me_bro flag fired on it from metrics alone."),

    # ------------------------------------------------------------------ STALE
    Case("C23", "yt", "lVqF8oLzVAU",
         "wangr - Setting up and interacting with the Polymarket CLOB API",
         "STALE", "ABSORB", True, "LIVE",
         "Published 2026-02-04 and teaches the v1 client path (get the client, "
         "supply the private key and chain id). Polymarket CLOB v2 went live "
         "2026-04-28 and BOTH v1 clients are archived - checked against the "
         "GitHub API on 2026-08-04: Polymarket/py-clob-client archived=True "
         "(1,235 stars, last push 2026-05-25), Polymarket/clob-client "
         "archived=True (514 stars). The live path is Polymarket/py-sdk, "
         "archived=False, pushed 2026-08-04. Concepts survive; the code does "
         "not, and it must not be handed to anyone as a build path.",
         note="THE BRIEF'S NAMED CASE. Current pipeline verdict: "
              "BUILD_AND_RECOMMEND.",
         tags=["brief", "anchor", "stale"]),

    Case("C24", "yt", "MyCjPs0pRy4",
         "JunkieAI - Pulling data from the Polymarket API using CLOB",
         "STALE", "ABSORB", True, "LIVE",
         "Published 2025-01-20, 18 months old, and works through the "
         "TypeScript @polymarket/clob-client with ethers - archived=True as of "
         "2026-08-04. Its own honest negative result (get_trades returned "
         "nothing usable on a two-day-old market) is still worth absorbing.",
         tags=["stale"]),
]

# ---------------------------------------------------------------- the bands
# Where the outside evidence fixes a BOUND rather than a point. Each entry
# names what the bound is and why the rest is taste. Kept as one table rather
# than scattered through the cases so a reader can audit every soft label in
# one place - which is the only reason a banded label is honest at all.
_BANDS = {
    "C02": ("ABSORB", "RECOMMEND",
            "72M-trade analysis, nothing sold: must not be discounted. "
            "Whether it is also worth a human's own 17 minutes is taste."),
    "C03": ("ABSORB", "RECOMMEND",
            "public corporate facts, nothing sold: must not be discounted"),
    "C04": ("ABSORB", "RECOMMEND",
            "independently corroborated by this repo's own fee census: must "
            "not be discounted"),
    "C05": ("ABSORB", "RECOMMEND",
            "argues against its own upgrade path with numbers: must not be "
            "discounted"),
    "C06": ("ABSORB", "RECOMMEND",
            "its fill-realism rules were independently rederived here: must "
            "not be discounted"),
    "C07": ("ABSORB", "RECOMMEND",
            "a complete negative post-mortem with the denominator attached: "
            "must not be discounted and must not be rejected"),
    "C08": ("ABSORB", "RECOMMEND",
            "explicitly sells nothing, every lesson carries a number: must "
            "not be discounted or rejected"),
    "C09": ("ABSORB", "RECOMMEND",
            "a real installable library with a public repo: must not be "
            "rejected"),
    "C10": ("ABSORB", "RECOMMEND",
            "cites a real external study and separates three mechanisms: "
            "must not be rejected"),
    "C11": ("ABSORB", "RECOMMEND",
            "the scam language it contains is quoted in order to condemn it: "
            "must not be rejected or discounted"),
    "C12": ("ABSORB", "RECOMMEND",
            "makes no profit claim and states what it withholds: must not be "
            "discounted"),
    "C13": ("REJECT", "DISCOUNT",
            "headline is paper against the same creator's -70% live day: "
            "must be discounted at best"),
    "C17": ("DISCOUNT", "ABSORB",
            "an honest disclosed tape plus two unsupported multipliers: must "
            "not be recommended, must not be rejected"),
    "C19": ("DISCOUNT", "ABSORB",
            "rigorous engine, self-contradictory maker fees: must not be "
            "recommended"),
    "C22": ("REJECT", "DISCOUNT",
            "557 stars against 4 commits with no artifact behind the claim: "
            "must not be absorbed as a reference"),
    "C23": ("DISCOUNT", "ABSORB",
            "the concepts survive, the code path is archived: must never be "
            "recommended"),
    "C24": ("DISCOUNT", "ABSORB",
            "same, and its honest negative result is worth keeping: must "
            "never be recommended"),
}
BAND_REASON = {k: v[2] for k, v in _BANDS.items()}
for _c in CASES:
    if _c.cid in _BANDS:
        _c.band = (_BANDS[_c.cid][0], _BANDS[_c.cid][1])

BY_ID = {c.cid: c for c in CASES}

# Deliberately recorded, not silently dropped.
MISSING_FROM_BRIEF = [
    ("33 trades / $23.53 total profit / summed winners +$127 / wallet last "
     "traded 2 months ago",
     "No transcript in either youtube-signal database contains '23.53'; no "
     "tracked or untracked markdown file in youtube-signal, social-signal, "
     "signal-github or bot-hunt does either. Substituted: C17 (a fully "
     "disclosed break-even bot, which is the honest version of the same "
     "shape) and C22 (a 557-star repo whose claim has no artifact behind it)."),
]
