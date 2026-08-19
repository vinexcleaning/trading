"""HIS SOCCER ANSWERS, TURNED INTO SPECS.

`coordinator` mailbox 004 carries his answers to all six questions in
`QUESTIONS_FOR_HIM.md`. They are recorded as variables in `DOMAIN_SOCCER.md`;
this file turns them into strategies.

**Three of his six answers say the same thing: the variable is the CLUB, not the
league table.** That rewrites SF018 (amendment A2 of
`PREREGISTRATION_HOLDON.md`, made before any result exists) and it is the reason
SF019 and SF020 look the way they do.

**Two of his answers were "I don't know", and one of those is now our work
rather than his** — which competitions behave differently. That is SF022's job.

    py -3 strategy-factory/src/seed_specs_soccer.py
    py -3 strategy-factory/src/spec.py --validate
"""
from __future__ import annotations

import json
from pathlib import Path

S = Path(__file__).resolve().parent.parent / "specs"
NO_EXIT = {"sell_at_c": None, "buy_more_at_c": None, "time_exit_utc_rule": None,
           "second_mentality": None, "on_disagreement": None}
HOLD = dict(NO_EXIT, mode="hold_to_settlement")

EURO_TOTALS = ["KXEPLTOTAL", "KXUCLTOTAL", "KXUELTOTAL", "KXUECLTOTAL",
               "KXLALIGATOTAL", "KXSERIEATOTAL", "KXLIGUE1TOTAL"]
EURO_GAMES = ["KXEPLGAME", "KXUCLGAME", "KXUELGAME", "KXUECLGAME",
              "KXLALIGAGAME", "KXSERIEAGAME", "KXLIGUE1GAME"]


def w(d):
    S.mkdir(parents=True, exist_ok=True)
    (S / (d["id"] + ".json")).write_text(json.dumps(d, indent=1),
                                         encoding="utf-8")
    print("wrote %s" % d["id"])


def build():
    # ---------------------------------------------------------- SF018 v2 ----
    w({
        "id": "SF018",
        "created": "2026-08-18",
        "author": "claude:factory",
        "source": "user",
        "source_detail":
            "coordinator mailbox 003 (which markets he knows) and 004 (what "
            "actually drives them). The trade is the one live descendant handed "
            "over by soccer/CLOSED.md. REWRITTEN 2026-08-19 on his answer to "
            "Q3: the variable is the club, not the table. Sealed in "
            "PREREGISTRATION_HOLDON.md, amendment A2, before any 2026/27 "
            "European price exists.",
        "families": ["KXUCLGAME", "KXEPLGAME"],
        "thesis":
            "A club that has shown all season that it sits back once it is one "
            "goal up is doing something different from a club that keeps "
            "attacking, so the price of the side that is ahead should depend on "
            "which kind of club it is - and the league table does not tell you "
            "which kind it is.",
        "unit": "one match",
        "entry": {
            "when":
                "A side goes one goal up between the 20th and 35th minute. "
                "Classify that club as PUSHES ON or SITS BACK from its own "
                "earlier matches this season only - never from the match being "
                "traded and never from the full season, which would be "
                "look-ahead. Buy the leading side at the recorded ask when the "
                "club is classified SITS BACK and the price implies it is more "
                "likely to be caught than its own record says. A club with too "
                "few earlier matches to classify is EXCLUDED and counted as "
                "excluded, never defaulted to the league average.",
            "side": "yes", "min_price_c": 35, "max_price_c": 80,
            "max_spread_c": 4},
        "exit": HOLD,
        "size": {"rule": "depth_capped", "usd_per_bet": 10,
                 "max_share_of_depth": 0.25},
        "wrong_if": [
            "Inside its no-skill range at 100 fired matches.",
            "Negative at 50 fired matches.",
            "Fewer than 10 firings in the first 30 days of the Champions "
            "League group stage - the availability failure that killed the "
            "parent idea, arriving on this one.",
            "Capacity below $25 per firing when priced by walking the recorded "
            "ladder.",
            "Clubs classified PUSHES ON and SITS BACK hold on equally often at "
            "these prices - the mechanism is then absent and the result is "
            "void rather than weak.",
            "The per-club label cannot be built for at least 60 of the 100 "
            "fired matches, in which case this is UNMEASURABLE and is reported "
            "as unmeasurable, not as negative."],
        "slow": True,
        "notes":
            "⚠ REWRITTEN 2026-08-19 AND THE OLD VERSION WAS WRONG IN A WAY "
            "THIS REPO HAS PAID FOR BEFORE. v1 identified a strong side as "
            "top-third of the domestic table. His own words kill that: 'Real "
            "Madrid's the type of team that if they score the first goal, "
            "they're gonna keep trying to score. But Manchester United, it's "
            "very likely that if they score the first goal, they're gonna park "
            "the bus no matter who they're playing against' - and 'a better "
            "team with better players will sometimes park the bus even playing "
            "against the worst team'. A league-wide average mixes clubs that do "
            "opposite things to the price and would report a null. That is the "
            "repo's most expensive recorded mistake - a sweep over price and "
            "market features used to close a question about individual players "
            "- arriving in a new sport, and it was caught BEFORE any number "
            "existed. || PRIOR WORK: soccer/CLOSED.md, 2026-08-11, closed the "
            "late-comeback idea on AVAILABILITY not price - at the 89th minute "
            "a tradeable quote existed 16 times in 100, and at 97 cents or "
            "better 1 time in 100, on 699 matches priced at every displayed "
            "minute. Now GUARDS #24, across seven sports. HOW THIS DIFFERS: it "
            "buys the UNCERTAIN side, where quotes were measured at 93 in 100 "
            "at the 15th minute, and the loss is capped at what was paid. "
            "CLOSED.md says in terms that 'nothing here supports the reverse "
            "trade and nothing here rules it out'. || THE FEE IS THE LIKELIEST "
            "KILLER: 1.74 cents at a price of 53 against 0.20 at 97, nine times "
            "bigger than the parent. Any version reporting a gross number is "
            "void.",
    })

    # ------------------------------------------------------------- SF019 ----
    w({
        "id": "SF019",
        "created": "2026-08-19",
        "author": "claude:factory",
        "source": "user",
        "source_detail":
            "His answer to Q1 and Q2, mailbox 004. Q1: rotation depends on the "
            "stakes in BOTH games, and 'at the beginning of the league, teams "
            "usually always come with their A game... towards the end, once the "
            "results are kind of defined, then it changes'. Q2, unprompted "
            "warning: 'Don't completely rely on this' - qualification status is "
            "NOT the driver; games played recently is.",
        "families": EURO_GAMES,
        "thesis":
            "A club with a pile of fixtures behind it is a weaker version of "
            "itself whether or not it changes the eleven, and that shows up "
            "late in a season once league places are settled rather than early "
            "when everyone is still trying.",
        "unit": "one match",
        "entry": {
            "when":
                "Buy against a side that has played 3 or more fixtures in the "
                "previous 10 days when its next fixture within 4 days is a "
                "European tie. Record matchday number and whether the club's "
                "league objective is still mathematically live. Fire only in "
                "the second half of the league season, because his rule is that "
                "the effect is absent early - and record the first-half matches "
                "anyway as the control that tests the rule.",
            "side": "no", "min_price_c": 20, "max_price_c": 85,
            "max_spread_c": 5},
        "exit": HOLD,
        "size": {"rule": "depth_capped", "usd_per_bet": 10,
                 "max_share_of_depth": 0.25},
        "wrong_if": [
            "No gradient across the season - if congested sides underperform "
            "equally in matchday 3 and matchday 33, his stated rule is wrong "
            "and it is reported as wrong.",
            "Inside its no-skill range at 100 fired matches.",
            "Fewer than 100 qualifying matches by the end of the season, which "
            "makes it unmeasurable rather than unprofitable.",
            "The effect vanishes once the leading-club identity from SF018 is "
            "controlled for, meaning this is SF018 wearing a different label."],
        "slow": True,
        "notes":
            "⚠ HIS WARNING IS BUILT INTO THE RULE AND IT IS THE MOST USEFUL "
            "PART: 'They might put the same team though. It might not put them "
            "at full effort.' So ROTATION IS NOT ONLY PERSONNEL - a club can "
            "field its first eleven and not try, and any line-up-based variable "
            "scores that match as full strength and is wrong. This spec "
            "therefore measures FIXTURE LOAD, which is observable, rather than "
            "line-up changes, which are observable and misleading. || He also "
            "told us the obvious version of Q2 is wrong before it was written: "
            "clubs that are already qualified often still field strong sides "
            "'because they wanna give their teams more practice'. Qualification "
            "status is recorded as a secondary flag and is NOT the driver. || "
            "The season gradient is a PREDICTION stated in advance, which makes "
            "it a test of his rule and not a parameter to tune.",
    })

    # ------------------------------------------------------------- SF020 ----
    w({
        "id": "SF020",
        "created": "2026-08-19",
        "author": "claude:factory",
        "source": "user",
        "source_detail":
            "His answer to Q5, mailbox 004: 'When they announce the line-up, "
            "the price might move... that news usually hits a few hours before "
            "the game.' ⚠ He marked this as a guess himself - 'I'm just giving "
            "you what I'm assuming would happen. That's all stuff you can check "
            "better than me' - so it is a hypothesis to verify, not a fact he "
            "supplied.",
        "families": ["KXUCLGAME", "KXEPLGAME"],
        "thesis":
            "If team news moves the price, it should show up as a step in the "
            "recorded book at a predictable time before kickoff, and if there "
            "is no step then there is nothing there to trade.",
        "unit": "one match",
        "entry": {
            "when":
                "DIAGNOSTIC FIRST, trade second. For every European match, "
                "measure the recorded price path from 8 hours before kickoff to "
                "kickoff and locate the largest step. Report the distribution "
                "of when those steps happen. Only if steps cluster at a "
                "repeatable time does a trade follow, and it is written as a "
                "separate spec with its own id rather than smuggled into this "
                "one.",
            "side": "either", "min_price_c": 5, "max_price_c": 95,
            "max_spread_c": 6},
        "exit": HOLD,
        "size": {"rule": "flat", "usd_per_bet": 10, "max_share_of_depth": 0.2},
        "wrong_if": [
            "The largest pre-kickoff step is uniformly distributed across the "
            "8 hours - no clustering means no announcement effect visible at "
            "this resolution, and it is reported as absent.",
            "The recorder's 10-minute cadence on the full-depth tier is too "
            "coarse to see the step, which is a finding about the recorder and "
            "is reported as such rather than as a finding about the market.",
            "Steps cluster but sit inside the spread, so there is nothing to "
            "capture after costs."],
        "slow": True,
        "notes":
            "THIS CANNOT BECOME A LIVE STRATEGY WHATEVER IT FINDS. CLAUDE.md "
            "9b item 2 holds absolutely: his own bot was reading scores after "
            "97.4 out of 100 of the price move had already happened, on 4,398 "
            "score-change events. A pre-kickoff announcement is a scheduled "
            "instant rather than an in-play event, which is why it is worth "
            "measuring at all - but the answer this produces is about whether "
            "the door is shut by a wall or a curtain, and paper stays paper. || "
            "He hedged this answer himself and that hedge is why it is written "
            "as a diagnostic rather than as a trade. An expert who marks their "
            "own uncertainty is worth more than one who does not, and the way "
            "to honour that is to test it rather than to build on it.",
    })

    # ------------------------------------------------------------- SF021 ----
    w({
        "id": "SF021",
        "created": "2026-08-19",
        "author": "claude:factory",
        "source": "user",
        "source_detail":
            "His answer to Q6, mailbox 004, and it is his own worked rule: "
            "'Arsenal has scored two goals in the last ten games, especially "
            "against teams below the top ten. Their next game against "
            "Nottingham Forest, twelfth place - it's more than likely they'll "
            "score more than two.' He also said a lot of people bet team totals "
            "and player statistics and that 'all that can be calculated with "
            "statistics'.",
        "families": EURO_TOTALS,
        "thesis":
            "How many goals a team has been scoring lately, against opponents "
            "of the same quality as the next one, is a plainer thing to "
            "forecast than who wins - and the goals markets are priced by "
            "people who are mostly thinking about who wins.",
        "unit": "one match",
        "entry": {
            "when":
                "For each match, compute the club's goals scored per game over "
                "its last 10 matches, restricted to opponents in the same third "
                "of the table as the coming opponent. Buy the OVER at the "
                "recorded ask when that rate exceeds the market's implied line "
                "by the margin; buy the UNDER on the mirror. Opponent quality "
                "is read from the table BEFORE the match.",
            "side": "either", "min_price_c": 10, "max_price_c": 90,
            "max_spread_c": 5},
        "exit": HOLD,
        "size": {"rule": "depth_capped", "usd_per_bet": 10,
                 "max_share_of_depth": 0.25},
        "wrong_if": [
            "Inside its no-skill range at 100 settled matches.",
            "Negative at 50 settled matches.",
            "It only fires on the over, or only on the under - a rule that can "
            "only bet one direction is a rule that has learned the season's "
            "scoring level rather than anything about the teams.",
            "The naive benchmark - buy the over in every match at the same "
            "prices - does as well, which would mean the conditioning on "
            "opponent quality is doing no work at all."],
        "slow": False,
        "notes":
            "THE NAIVE BENCHMARK IS THE WHOLE TEST HERE and it is named in the "
            "kill list rather than left to a footnote: goals markets can drift "
            "cheap or dear for a season, so a rule that always buys the over "
            "can look good for reasons that have nothing to do with his idea. "
            "The comparison that matters is against buying the over "
            "indiscriminately, not against zero. || Unit is the MATCH, not the "
            "strike. A totals ladder is roughly 11 strikes on one game, and "
            "counting strikes as observations is exactly what retracted LEDGER "
            "K003 - a 10-strike weather ladder counted as 10 markets when it is "
            "one temperature reading, with confidence ranges about three times "
            "too tight. || These families are currently TOP-OF-BOOK ONLY on the "
            "recorder. KXEPLTOTAL (60 two-sided) and KXUCLTOTAL (42) are his "
            "two competitions and are pinned to full depth from 2026-08-19; the "
            "rest of the list is breadth tier until a result justifies more.",
    })

    # ------------------------------------------------------------- SF022 ----
    w({
        "id": "SF022",
        "created": "2026-08-19",
        "author": "claude:factory",
        "source": "user",
        "source_detail":
            "Two of his answers converging with another chat. Q4: 'I have no "
            "idea how different these competitions work... that statistics, you "
            "can find for yourself' - recorded as answered-with-a-no, and "
            "therefore our work. Q6: he named player statistics as where he "
            "sees both a lot of fails and a lot of wins.",
        "families": ["KXEPLBTTS", "KXUCLBTTS", "KXLALIGABTTS", "KXSERIEABTTS",
                     "KXLIGUE1BTTS", "KXLALIGATEAMTOTAL", "KXMLSSCORE",
                     "KXLALIGASCORE"],
        "thesis":
            "Nobody here knows whether a Spanish league game behaves "
            "differently from a French one, and the exchange lists the same "
            "goal-shaped market in seven competitions at once - so the "
            "comparison is free and answers a question he explicitly said he "
            "cannot.",
        "unit": "one match",
        "entry": {
            "when":
                "The SAME rule applied unchanged across every competition that "
                "lists the family: buy at the recorded ask in fixed price "
                "buckets and hold. The output is a per-competition curve, not "
                "one number. No competition is selected before the curves "
                "exist, and the curves are reported in full including the "
                "empty ones.",
            "side": "either", "min_price_c": 10, "max_price_c": 90,
            "max_spread_c": 6},
        "exit": HOLD,
        "size": {"rule": "flat", "usd_per_bet": 10, "max_share_of_depth": 0.25},
        "wrong_if": [
            "Every competition's range contains zero at 100 settled matches "
            "each - reported as UNMEASURED, not as negative.",
            "The competitions that look best are the ones with the fewest "
            "matches, which is what a best-of-N artefact looks like from the "
            "inside.",
            "Fewer than 5 competitions accrue 100 settled matches by the end of "
            "the season, which makes the comparison unmeasurable."],
        "slow": True,
        "notes":
            "⚠ THIS SPEC IS A SEVEN-WAY COMPARISON AND IS THEREFORE A "
            "BEST-OF-N MACHINE BY CONSTRUCTION. Picking the best competition "
            "afterwards is precisely the trap this whole project is built "
            "around: the best of seven zero-skill arms looks good roughly 1 "
            "time in 3 at any single threshold. So the rule is fixed in "
            "advance, every curve is reported including the bad ones, and NO "
            "competition may be promoted on this screen alone - a winner here "
            "becomes a new spec with a new id and its own forward test, and it "
            "counts against the screened total. || He said he does not know the "
            "answer to this and that we should find it. That makes it the one "
            "place where a broad sweep is the right shape rather than a "
            "narrowing risk.",
    })


if __name__ == "__main__":
    build()
