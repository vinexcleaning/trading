"""THE BREADTH PASS — one strategy for every category that had none.

Mailbox 001: *"A minimum number of strategy specs for EVERY category in the
census before a second one is written for any category. Breadth pass first,
depth pass second, and the breadth pass is not optional."*

`spec.py --coverage` said 8 specs across 4 of 13 testable categories, with nine
categories on zero. This file closes that. Every spec here is grounded in a
variable already written down in `reports/VARIABLES.md`, which was written
before any of them.

**These are deliberately NOT clever.** The first spec in a category exists to
put that category on the board and to start it accruing a sample. Depth comes
second, and only after every category has one.

    py -3 strategy-factory/src/seed_specs_breadth.py
    py -3 strategy-factory/src/spec.py --coverage
"""
from __future__ import annotations

import json
from pathlib import Path

S = Path(__file__).resolve().parent.parent / "specs"
NO_EXIT = {"sell_at_c": None, "buy_more_at_c": None, "time_exit_utc_rule": None,
           "second_mentality": None, "on_disagreement": None}
HOLD = dict(NO_EXIT, mode="hold_to_settlement")


def w(d):
    S.mkdir(parents=True, exist_ok=True)
    (S / (d["id"] + ".json")).write_text(json.dumps(d, indent=1),
                                         encoding="utf-8")
    print("wrote %s  [%s]" % (d["id"], d["_category"]))


def build():
    # ---------------------------------------------------------- SPORTS ----
    w({
        "id": "SF009", "_category": "Sports",
        "created": "2026-08-18", "author": "claude:factory",
        "source": "reasoning",
        "source_detail":
            "VARIABLES.md, Sports: 'the relationship between the spread ladder "
            "and the plain who-wins market - a team favoured by 7 must win at "
            "least as often as it covers -7'. bot-hunt records no American "
            "football at all, and KXNFLSPREAD is 793 two-sided markets.",
        "families": ["KXNFLSPREAD", "KXNFLGAME", "KXNCAAFGAME"],
        "thesis":
            "A team cannot cover a seven-point handicap more often than it "
            "simply wins, so if the market ever prices covering above winning, "
            "one of those two prices is wrong and the pair can be bought and "
            "sold against each other without any opinion about the game.",
        "unit": "one settled game",
        "entry": {
            "when":
                "For one game, pair the who-wins market with each favourite-"
                "side spread market at a handicap of 1 point or more. Fire when "
                "ask(cover by H) + fee < bid(win) - fee for the same team, "
                "buying the cover and selling the win. Both legs must settle on "
                "the same game and both must be fillable at the recorded touch.",
            "side": "either", "min_price_c": 2, "max_price_c": 98,
            "max_spread_c": 99},
        "exit": HOLD,
        "size": {"rule": "depth_capped", "usd_per_bet": 25,
                 "max_share_of_depth": 0.5},
        "wrong_if": [
            "Fires fewer than 10 times in 30 days across all listed families.",
            "Locked profit after both legs' fees is under 0.5 cents.",
            "Every firing turns out to pair a spread with the wrong game or the "
            "wrong team, i.e. my join is the bug rather than the market.",
            "Kalshi's spread markets turn out to include a push outcome, which "
            "would break the implication and kill the whole idea."],
        "slow": False,
        "notes":
            "The push question is the real risk and it is checked FIRST, "
            "before any firing is counted: if a spread market can resolve NO "
            "for the favourite on an exact-number tie while the win market "
            "resolves YES, the inequality does not hold and this spec is void "
            "rather than weak. Whole-number handicaps are excluded until that "
            "is settled from the rules text stored in w_names.rules_primary. "
            "|| NOT the same as B024. B024 bought heavy favourites outright at "
            "the ask; this holds two legs on one game and has no directional "
            "opinion at all.",
    })

    # -------------------------------------------------------- ELECTIONS ----
    w({
        "id": "SF010", "_category": "Elections",
        "created": "2026-08-18", "author": "claude:factory",
        "source": "reasoning",
        "source_detail":
            "VARIABLES.md, Elections: 'the margin ladder against the winner "
            "market on the same race - P(margin above zero) and P(win) are the "
            "same event described twice'. KXMIDTERMMOV is the single largest "
            "two-sided family on the exchange at 3,687 markets.",
        "families": ["KXMIDTERMMOV", "KXHOUSERACE", "KXSENATERACE"],
        "thesis":
            "Winning a race and winning it by more than nothing are the same "
            "event, so the two markets must agree, and when they do not the "
            "difference is money that does not depend on who wins.",
        "unit": "one settled race",
        "entry": {
            "when":
                "For one race, take the winner market and the margin-of-victory "
                "ladder. The probability of a margin above zero for a candidate "
                "is the sum of that candidate's margin brackets. Fire when that "
                "sum, bought at ask plus fees, is below the winner market's bid "
                "minus fees, or the mirror.",
            "side": "either", "min_price_c": 1, "max_price_c": 99,
            "max_spread_c": 99},
        "exit": HOLD,
        "size": {"rule": "depth_capped", "usd_per_bet": 25,
                 "max_share_of_depth": 0.4},
        "wrong_if": [
            "The margin ladder is not complete for any race, so the sum is not "
            "the probability of winning and the whole comparison is invalid.",
            "It fires but the gap never exceeds the cost of the many legs "
            "involved - a margin ladder can be 20 markets and each pays a fee.",
            "Fewer than 10 races carry both a winner market and a complete "
            "margin ladder."],
        "slow": True,
        "notes":
            "DECLARED SLOW. These settle at an election, months away, so a "
            "month gives no settled units. What a month DOES give is the "
            "answer to whether the inconsistency exists at all, which is "
            "visible on tape long before anything settles - and that is worth "
            "having in September rather than never. || Same family of "
            "mechanism as SF001 and SF002 but a different rule and a different "
            "pairing: those compare strikes within one ladder, this compares a "
            "ladder against a separate market.",
    })

    # ----------------------------------------------------- ENTERTAINMENT ----
    w({
        "id": "SF011", "_category": "Entertainment",
        "created": "2026-08-18", "author": "claude:factory",
        "source": "reasoning",
        "source_detail":
            "VARIABLES.md, Entertainment: 'whether the candidate list is "
            "CLOSED - who headlines Coachella is a named short list, and a "
            "closed list of mutually exclusive outcomes must sum to a dollar'. "
            "KXROLEATEVENTCOACHELLA and KXPERFORMVS are named-candidate sets.",
        "families": ["KXROLEATEVENTCOACHELLA", "KXPERFORMVS", "KXRT"],
        "thesis":
            "When a market lists the named people who could take one slot and "
            "exactly one of them will, the whole set is worth a dollar, so a "
            "set that costs less than a dollar to buy outright is locked money "
            "whoever turns out to get it.",
        "unit": "one settled event",
        "entry": {
            "when":
                "Group every candidate market sharing one event. Require the "
                "set to be exhaustive - either the rules text names it as such "
                "or an 'anyone else' contract exists and is included. Fire when "
                "the sum of asks plus every leg's fee is under 100 cents.",
            "side": "yes", "min_price_c": 1, "max_price_c": 99,
            "max_spread_c": 99},
        "exit": HOLD,
        "size": {"rule": "depth_capped", "usd_per_bet": 25,
                 "max_share_of_depth": 0.4},
        "wrong_if": [
            "No candidate set is ever exhaustive - i.e. someone unlisted can "
            "always win - in which case this is not an arbitrage and is "
            "dropped rather than weakened.",
            "It fires fewer than 5 times in 60 days.",
            "The thinnest candidate caps capacity below $25."],
        "slow": True,
        "notes":
            "THE EXHAUSTIVENESS CHECK IS THE WHOLE SPEC and it is the same "
            "lesson as LEDGER C014, which claimed 464 bucket-sum arbitrages "
            "and retracted all 464 because the ladder was partial - 3 of 80 "
            "buckets. Buying 3 of 80 pays a dollar only if the outcome lands "
            "in those 3, which is a bet and not an arbitrage. Here the risk is "
            "worse than numeric ladders, because a named-candidate list is "
            "hand-curated and 'somebody nobody listed' is a real outcome. If "
            "the exhaustiveness requirement is ever relaxed to get more "
            "firings, this has become C014 and must be dropped.",
    })

    # ---------------------------------------------------------- POLITICS ----
    w({
        "id": "SF012", "_category": "Politics",
        "created": "2026-08-18", "author": "claude:factory",
        "source": "reasoning",
        "source_detail":
            "VARIABLES.md, Politics: 'whether the field is OPEN - who will "
            "Trump pardon has no closed list, so the candidates should sum to "
            "LESS than a dollar, and a sum above one is a lock'. "
            "KXTRUMPPARDONS and KXFEDERALCHARGE are open-field sets.",
        "families": ["KXTRUMPPARDONS", "KXFEDERALCHARGE", "KXFUNDRAISING"],
        "thesis":
            "When a market names some of the people something could happen to "
            "but anyone else could be the answer too, the listed names must "
            "add up to less than a dollar, so a set that can be SOLD for more "
            "than a dollar is locked money.",
        "unit": "one settled event",
        "entry": {
            "when":
                "Group every named-candidate market sharing one open-field "
                "event. Confirm from the rules text that an unlisted outcome is "
                "possible. Fire when the sum of BIDS minus every leg's fee "
                "exceeds 100 cents, selling one of each.",
            "side": "no", "min_price_c": 1, "max_price_c": 99,
            "max_spread_c": 99},
        "exit": HOLD,
        "size": {"rule": "depth_capped", "usd_per_bet": 25,
                 "max_share_of_depth": 0.4},
        "wrong_if": [
            "The events turn out not to be mutually exclusive - more than one "
            "person can be pardoned - in which case the sum is not bounded by "
            "a dollar at all and this spec is VOID, not weak.",
            "It fires fewer than 5 times in 60 days.",
            "Selling requires posting the full complement in margin, making "
            "the real capital cost far above the stated size."],
        "slow": True,
        "notes":
            "THE MUTUAL-EXCLUSIVITY QUESTION IS CHECKED FIRST AND IS LIKELY "
            "FATAL. 'Who will Trump pardon' plausibly allows several people to "
            "be pardoned, and if so nothing is bounded and there is no "
            "arbitrage - only a bet. This is written down now, before any "
            "firing is counted, so that a result cannot be read as evidence "
            "when the premise was never checked. The mirror of SF011 on "
            "purpose: closed field means BUY the set, open field means SELL "
            "it, and getting the direction backwards is the obvious way to "
            "lose money confidently.",
    })

    # ------------------------------------------------------- COMMODITIES ----
    w({
        "id": "SF013", "_category": "Commodities",
        "created": "2026-08-18", "author": "claude:factory",
        "source": "reasoning",
        "source_detail":
            "VARIABLES.md, Commodities: 'KXGOLDH and KXSILVERH settle HOURLY "
            "on Pyth - a free public price feed, and among the fastest-"
            "settling families outside crypto'. The category has zero tape in "
            "this repo.",
        "families": ["KXGOLDH", "KXSILVERH", "KXWTI", "KXWTIMAX"],
        "thesis":
            "Gold and silver settle every hour against a free public price, so "
            "a plain buy-and-hold at each price level accrues a real sample in "
            "days rather than months, in a category where this repo has never "
            "measured anything at all.",
        "unit": "one settled market",
        "entry": {
            "when":
                "Buy at the recorded ask at a fixed number of minutes before "
                "close, bucketed in 5-cent bands across the whole price range, "
                "so the answer is a curve. No selection on which band looks "
                "good.",
            "side": "either", "min_price_c": 2, "max_price_c": 98,
            "max_spread_c": 6},
        "exit": HOLD,
        "size": {"rule": "flat", "usd_per_bet": 10, "max_share_of_depth": 0.25},
        "wrong_if": [
            "Every price band's range still contains zero at 100 settled "
            "markets per band, in which case it is recorded as UNMEASURED and "
            "not as negative.",
            "The whole curve sits below zero at the real ask and the real fee.",
            "Fewer than 100 markets settle in 30 days, which would mean the "
            "hourly families are not as frequent as the listing suggests."],
        "slow": False,
        "notes":
            "Deliberately the same rule as SF005 on crypto, pointed at a "
            "different category - and therefore a DIFFERENT strategy with its "
            "own id and its own place in the screened count, not a re-run. "
            "The reason to expect a different answer is that the counterparty "
            "differs: crypto hourly markets are quoted heavily by bots, and "
            "LEDGER C022 measured market making there at -0.853 cents. Whether "
            "metals hourly are the same crowd is exactly the unknown.",
    })

    # ---------------------------------------------------------- MENTIONS ----
    w({
        "id": "SF014", "_category": "Mentions",
        "created": "2026-08-18", "author": "claude:factory",
        "source": "reasoning",
        "source_detail":
            "VARIABLES.md, Mentions: 'all of a family's risk resolves inside "
            "one short window - a speech, a press conference - and nothing "
            "should move before it', and 'the words are correlated: one speech "
            "drives every market in the family, so they are one observation "
            "and not thirty'.",
        "families": ["KXFEDMENTION", "KXSECPRESSMENTION", "KXTRUMPSAY",
                     "KXWARSHMENTION"],
        "thesis":
            "Markets on whether someone will say a particular word are decided "
            "entirely during one speech, so before the speech there is no news "
            "that can move them, and the question worth measuring is whether "
            "they drift anyway.",
        "unit": "one speech, NOT one word market",
        "entry": {
            "when":
                "For each speech event, record every word market's price at 24 "
                "hours, 6 hours and 1 hour before the scheduled start, and at "
                "settlement. Measure the drift over that window against the "
                "eventual outcome. Where drift is systematically toward zero "
                "beyond what the outcomes justify, buy the cheapest words at "
                "the 1-hour mark.",
            "side": "yes", "min_price_c": 2, "max_price_c": 30,
            "max_spread_c": 8},
        "exit": HOLD,
        "size": {"rule": "flat", "usd_per_bet": 5, "max_share_of_depth": 0.2},
        "wrong_if": [
            "Drift is inside its no-skill range at 100 SPEECHES - not 100 word "
            "markets, which would be pseudo-replication of exactly the kind "
            "that retracted LEDGER K003.",
            "Fewer than 100 speeches occur in 90 days, in which case this is "
            "dropped as unmeasurable rather than as unprofitable.",
            "The prices do not move before the speech at all, which makes this "
            "a null with nothing to trade and is the expected outcome."],
        "slow": True,
        "notes":
            "THE UNIT IS THE SPEECH AND THAT IS THE ENTIRE POINT. One speech "
            "drives every word market in the family simultaneously, so thirty "
            "word markets from one speech are ONE observation. LEDGER K003 was "
            "retracted for precisely this - a 10-strike ladder counted as 10 "
            "markets when it is one temperature reading, and the confidence "
            "ranges came out about three times too tight. Reporting effective "
            "sample size, not nominal, is not optional here. || Also a "
            "longshot family, so it overlaps SF004's price band; SF004 rests a "
            "passive offer against the longshot, this buys the longshot "
            "outright. Opposite directions, and that is deliberate.",
    })

    # --------------------------------------------------------- COMPANIES ----
    w({
        "id": "SF015", "_category": "Companies",
        "created": "2026-08-18", "author": "claude:factory",
        "source": "reasoning",
        "source_detail":
            "VARIABLES.md, Companies: 'these settle on a data vendor "
            "(Fiscal.ai), not on the filing' and 'the scheduled earnings "
            "date'. KXHOODA, KXTSLAA, KXSPOTA, KXSBUXA are company KPI "
            "ladders.",
        "families": ["KXHOODA", "KXTSLAA", "KXSPOTA", "KXSBUXA"],
        "thesis":
            "Company performance markets are ladders around a number reported "
            "on a date everyone knows in advance, so the plain question - does "
            "buying and holding them make or lose money - has never been asked "
            "here and costs nothing to ask.",
        "unit": "one settled market",
        "entry": {
            "when":
                "Buy at the recorded ask at a fixed number of days before the "
                "scheduled report, bucketed by price in 5-cent bands. The "
                "dullest possible rule, on purpose: this exists to accrue a "
                "sample in a category with none.",
            "side": "either", "min_price_c": 5, "max_price_c": 95,
            "max_spread_c": 8},
        "exit": HOLD,
        "size": {"rule": "flat", "usd_per_bet": 10, "max_share_of_depth": 0.25},
        "wrong_if": [
            "Fewer than 100 markets settle by 2026-11-18, which confirms the "
            "category is unmeasurable on this timescale and it is dropped as "
            "unmeasurable rather than unprofitable.",
            "Result inside its no-skill range at 100 settled markets.",
            "The ladders turn out to share one reported number, making the "
            "unit the EARNINGS REPORT rather than the market - in which case "
            "the sample is about 4 per company per year and the whole thing is "
            "underpowered by two orders of magnitude."],
        "slow": True,
        "notes":
            "The third kill condition is the one most likely to fire and it is "
            "written before any number exists. A 20-strike ladder on Tesla's "
            "quarterly revenue is ONE observation of one report, not 20 "
            "markets, and if that is how it turns out then 36 families times 4 "
            "quarters is 144 observations a year - which is the honest answer "
            "and is a finding about the category rather than about the "
            "strategy.",
    })

    # -------------------------------------------- SCIENCE AND TECHNOLOGY ----
    w({
        "id": "SF016", "_category": "Science and Technology",
        "created": "2026-08-18", "author": "claude:factory",
        "source": "reasoning",
        "source_detail":
            "VARIABLES.md, Science and Technology: 'award families are CLOSED "
            "candidate lists and should sum to a dollar' and 'KXH200MON and "
            "KXB200MAX are GPU prices, settling on a vendor'. KXNOBELPHYSICS "
            "is a named-candidate award set.",
        "families": ["KXNOBELPHYSICS", "KXH200MON", "KXB200MAX",
                     "KXEBOLACOUNTRY"],
        "thesis":
            "Award markets name the people who could win one prize and exactly "
            "one of them gets it, so the set is worth a dollar - and unlike "
            "entertainment awards, a scientific prize can go to somebody the "
            "market never listed, which is the thing to check before believing "
            "any of it.",
        "unit": "one settled award",
        "entry": {
            "when":
                "Group every candidate market for one prize in one year. "
                "Establish from the rules text whether an unlisted winner is "
                "possible. If the set is exhaustive, fire when the sum of asks "
                "plus fees is under 100 cents. If it is NOT exhaustive, fire "
                "only on the sell side when the sum of bids minus fees exceeds "
                "100 cents.",
            "side": "either", "min_price_c": 1, "max_price_c": 99,
            "max_spread_c": 99},
        "exit": HOLD,
        "size": {"rule": "depth_capped", "usd_per_bet": 25,
                 "max_share_of_depth": 0.4},
        "wrong_if": [
            "Neither side ever fires in 90 days.",
            "The prize is awarded to somebody unlisted while the set was "
            "treated as exhaustive, which is a direct loss and kills the "
            "exhaustive branch outright.",
            "Fewer than 5 award events settle in a year, making this "
            "unmeasurable by arithmetic."],
        "slow": True,
        "notes":
            "DECLARED SLOW and it is the slowest thing in the folder - a Nobel "
            "prize settles once a year. It is written anyway because the "
            "INCONSISTENCY is visible on tape immediately even though the "
            "settlement is not, and because a category with no spec is a "
            "category that was skipped. The GPU-price families in the same "
            "category settle monthly and are the faster half; they are listed "
            "so the family set is on the board, and a separate spec for them "
            "belongs in the depth pass.",
    })

    # ------------------------------------------------------ UNCLASSIFIED ----
    w({
        "id": "SF017", "_category": "?",
        "created": "2026-08-18", "author": "claude:factory",
        "source": "reasoning",
        "source_detail":
            "VARIABLES.md, Unclassified: 'wins across all teams are CONSERVED "
            "- every game produces exactly one win, so the expected wins "
            "implied by all thirty teams' ladders is pinned to a fixed total'. "
            "KXMLBWINS has 106 two-sided markets and no series row at all.",
        "families": ["KXMLBWINS"],
        "thesis":
            "Every baseball game produces exactly one win, so the wins the "
            "market expects from all thirty teams added together must equal "
            "the number of games left to play, and if it does not then some of "
            "those ladders are wrong by an amount that can be measured exactly.",
        "unit": "one league-season snapshot",
        "entry": {
            "when":
                "For each recorded snapshot, take every team's season win-total "
                "ladder and compute the implied expected wins for each team as "
                "the sum over strikes of the probability of exceeding that "
                "strike. Add across all teams. Compare against games already "
                "played plus games remaining. Where the total is above the "
                "conserved figure, sell the most overpriced ladders; below it, "
                "buy the most underpriced.",
            "side": "either", "min_price_c": 2, "max_price_c": 98,
            "max_spread_c": 10},
        "exit": HOLD,
        "size": {"rule": "depth_capped", "usd_per_bet": 25,
                 "max_share_of_depth": 0.3},
        "wrong_if": [
            "Fewer than 25 of the 30 teams carry a quoted ladder at the same "
            "moment, which makes the sum incomplete and the whole comparison "
            "invalid - the C014 failure again, in a new costume.",
            "The conservation gap is smaller than the cost of trading the "
            "ladders it would take to close it.",
            "The season ends before 100 snapshots with a complete set of teams "
            "accrue, in which case it is unmeasured, not negative."],
        "slow": True,
        "notes":
            "THE UNIT IS THE LEAGUE-SEASON SNAPSHOT, not the team and not the "
            "market. One conservation reading across thirty teams is ONE "
            "observation, however many contracts it involves - the same "
            "arithmetic that retracted LEDGER K003 and that this repo has now "
            "paid for twice. A season also gives very few independent "
            "readings, because consecutive days are almost the same reading; "
            "effective sample size is reported, not nominal. || This category "
            "exists in the census as '?' because KXMLBWINS has NO series row "
            "on the exchange at all - it is listed with open markets and no "
            "metadata, which is itself worth knowing.",
    })


if __name__ == "__main__":
    build()
