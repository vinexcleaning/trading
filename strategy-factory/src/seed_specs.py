"""Write the first batch of strategy specs.

Kept as a script rather than eight hand-typed JSON files so that the batch is
reviewable as one diff and reproducible. Re-running it overwrites the batch; it
does not touch specs written later by hand or by another pass.

Four sources are named in `STRATEGY_FACTORY.md` stage 2 and all four are meant
to run. This batch covers three of them - my own reasoning about market
structure, the extractors, and the claims the `reopen` chat found were closed
for the wrong reason. **The fourth, his own domain knowledge, is the one this
repo cannot generate**, and it is the single item batched to him in HANDOFF.md
rather than guessed at here.

    py -3 strategy-factory/src/seed_specs.py
    py -3 strategy-factory/src/spec.py --validate
"""
from __future__ import annotations

import json
from pathlib import Path

S = Path(__file__).resolve().parent.parent / "specs"


def w(d):
    S.mkdir(parents=True, exist_ok=True)
    (S / (d["id"] + ".json")).write_text(json.dumps(d, indent=1),
                                         encoding="utf-8")
    print("wrote", d["id"])


NO_EXIT = {"sell_at_c": None, "buy_more_at_c": None, "time_exit_utc_rule": None,
           "second_mentality": None, "on_disagreement": None}


def build():
    w({
        "id": "SF001",
        "created": "2026-08-18",
        "author": "claude:factory",
        "source": "reasoning",
        "source_detail":
            "Market structure. Kalshi lists threshold ladders where the YES "
            "side means 'above X'. P(above 92) can never exceed P(above 90). "
            "A crossing is an arithmetic impossibility, not a forecast.",
        "families": ["KXHIGHNY", "KXHIGHCHI", "KXBTCD", "KXETHD",
                     "KXNASDAQ100U", "KXINXU", "KXDJI"],
        "thesis":
            "On a ladder of 'above X' markets on the same underlying event, a "
            "higher strike must never be cheaper to buy than a lower strike is "
            "to sell. When it is, buying the high strike and selling the low "
            "one is locked money whatever the outcome, because the high strike "
            "winning implies the low strike winning.",
        "unit": "one event-day ladder",
        "entry": {
            "when":
                "Within one event (same underlying, same settlement time), "
                "find strikes A < B on the threshold ladder where ask(B) + fee "
                "< bid(A) - fee. Buy YES on B and sell YES on A (equivalently "
                "buy NO on A) in equal size. Both legs must be fillable at the "
                "recorded touch size.",
            "side": "either", "min_price_c": 1, "max_price_c": 99,
            "max_spread_c": 99},
        "exit": dict(NO_EXIT, mode="hold_to_settlement"),
        "size": {"rule": "depth_capped", "usd_per_bet": 25,
                 "max_share_of_depth": 0.5},
        "wrong_if": [
            "The rule fires fewer than 10 times in 30 days across all listed "
            "families.",
            "It fires but the locked profit after both fees, both sides, is "
            "under 0.5 cents per contract.",
            "Capacity at the recorded touch size is under $25 per opportunity.",
            "Every firing turns out to be two strikes with different "
            "settlement times or different underlyings, i.e. a bug in my own "
            "grouping rather than a crossing."],
        "slow": False,
        "notes":
            "This is a structural invariant, so it doubles as a data-quality "
            "canary (GUARDS #18: conservation can pass while the book rots). "
            "If it fires constantly, the far more likely explanation is that I "
            "have grouped the ladder wrongly, and the FIRST thing to check is "
            "my own grouping, not the exchange. Needs tier A depth to price "
            "the fill honestly. "
            "|| PRIOR WORK, AND IT IS STRONG. TWO ROWS, NOT ONE. "
            "(1) LEDGER C001, crypto: 'Kalshi greater ladders are monotone in "
            "strike - no arbitrage'. 3,187 scans across 26 events, on "
            "2026-08-01, zero violations. Its own wording was NARROWED on "
            "2026-08-09 because it rests on 10.5 MINUTES of scanning, and the "
            "row now says the sentence to quote is K007's instead. "
            "(2) LEDGER K007, kalshi-market-scan: 'No-arb violations are real "
            "but the size is dust'. 1,083 scans across 26 families over about "
            "9 hours, 2026-08-02 to 08-03. Result: 52 GENUINE VIOLATIONS, 0 "
            "WITH TRADEABLE SIZE. SETTLED as a null. One observation is one "
            "scan of one family's ladder. Note the correction attached to it: "
            "crypto cited this study twice as 'zero violations in 1,083 scans' "
            "when it found 52, corrected 2026-08-03. "
            "|| HOW THIS DIFFERS, and I am not claiming much. K007 is a "
            "LIVE SCAN: it asks whether a violation has tradeable size at the "
            "instant it looks. A recorded ladder asks a different question - "
            "how LONG a violation persists across cycles - and 'no tradeable "
            "size in this snapshot' and 'no tradeable size ever' are not the "
            "same sentence. It also runs continuously for the life of the "
            "recorder rather than for 9 hours, on weather and index families "
            "as well as crypto. "
            "|| WHAT I EXPECT: K007 to be confirmed. Its 52-violations-none-"
            "tradeable is the most likely outcome here and the honest prior. "
            "This spec is cheap because it runs on tape that is being "
            "collected anyway, and its real value is as the canary, not as "
            "the trade.",
    })

    w({
        "id": "SF002",
        "created": "2026-08-18",
        "author": "claude:factory",
        "source": "reasoning",
        "source_detail":
            "Market structure. Kalshi's 'between' brackets on one underlying "
            "partition the outcome space: exactly one of them must resolve "
            "YES. So the whole set is worth exactly 100 cents.",
        "families": ["KXHIGHNY", "KXHIGHCHI", "KXBTCD", "KXETHD"],
        "thesis":
            "Buying every bracket of a complete partition guarantees a payout "
            "of exactly one dollar, so if the asks across the whole set add up "
            "to less than a dollar plus fees, the difference is locked money "
            "that does not depend on the weather or the price of anything.",
        "unit": "one event-day ladder",
        "entry": {
            "when":
                "Group all 'between' brackets sharing an event and a "
                "settlement time. Require the set to be complete and "
                "non-overlapping by strike. Fire when the sum of asks plus the "
                "sum of per-leg fees is under 100 cents, buying one of each; "
                "or when the sum of bids minus fees is over 100 cents, selling "
                "one of each.",
            "side": "either", "min_price_c": 1, "max_price_c": 99,
            "max_spread_c": 99},
        "exit": dict(NO_EXIT, mode="hold_to_settlement"),
        "size": {"rule": "depth_capped", "usd_per_bet": 25,
                 "max_share_of_depth": 0.5},
        "wrong_if": [
            "The completeness check never passes, i.e. Kalshi's brackets do "
            "not actually partition and the whole idea rests on a misreading "
            "of the product.",
            "It fires fewer than 10 times in 30 days.",
            "Locked profit after all legs' fees is under 0.5 cents per set.",
            "The thinnest leg caps capacity below $25."],
        "slow": False,
        "notes":
            "Different rule from SF001 and therefore a different strategy, "
            "though the same underlying idea. SF001 needs two strikes; this "
            "needs the whole ladder and every leg's fee, which is a much "
            "higher bar. The fee is paid per leg and the legs are cheap, where "
            "the fee is small - that asymmetry is the reason this could "
            "survive where the two-leg version does not, and is exactly the "
            "arithmetic to check first. "
            "|| PRIOR WORK, AND IT IS A RETRACTION THIS SPEC IS BUILT TO "
            "AVOID REPEATING. LEDGER C014, crypto, RETRACTED: '464 profitable "
            "bucket-sum arbitrage violations at 96-97 cents'. Source "
            "reports/ladder_arb.json, 2026-08-01, 464 claimed violations. What "
            "happened: the ladder was FORWARD-FILLED and PARTIAL - 3 of 80 "
            "buckets. Buying 3 buckets pays a dollar only if the outcome lands "
            "in those 3, which is not an arbitrage, it is a bet. ALL 464 "
            "vanished on requiring a complete contiguous tiling. "
            "|| HOW THIS DIFFERS: it does not. The completeness and "
            "non-overlap requirement in this spec's entry rule IS C014's fix, "
            "written into the rule before any number exists rather than "
            "discovered after 464 of them did. If the completeness check is "
            "ever relaxed to get more firings, this spec has become C014 again "
            "and must be dropped. That sentence is the whole reason this note "
            "is here.",
    })

    w({
        "id": "SF003",
        "created": "2026-08-18",
        "author": "claude:factory",
        "source": "reasoning",
        "source_detail":
            "The census: 13,003 of Kalshi's 13,133 series have fee_type "
            "'quadratic', which charges takers only. 130 charge makers. So on "
            "99% of the exchange a resting order pays no fee at all.",
        "families": ["*tier_a_no_maker_fee"],
        "thesis":
            "On almost every Kalshi series a resting order costs nothing in "
            "fees, so quoting passively inside a wide spread earns the spread "
            "for free where crossing it would cost about two cents.",
        "unit": "one settled market",
        "entry": {
            "when":
                "Series charges no maker fee (fee_type == 'quadratic'). "
                "Recorded spread is 4 cents or wider and both sides have been "
                "continuously two-sided for the last hour of tape. Rest a bid "
                "one tick above the recorded best bid. Count a fill only when "
                "the recorded ask later trades down through the resting level, "
                "never when it merely touches it.",
            "side": "either", "min_price_c": 5, "max_price_c": 95,
            "max_spread_c": 99},
        "exit": {
            "mode": "sell_and_scale",
            "sell_at_c": 4,
            "buy_more_at_c": 4,
            "time_exit_utc_rule": None,
            "second_mentality":
                "A twin bot holds every fill to settlement instead of quoting "
                "out, so the spread-capture and the directional bet are "
                "separable.",
            "on_disagreement":
                "They are run as two separate bots with separate books and are "
                "never netted. The quoting bot is the one being tested; the "
                "holding twin is its control. Neither overrides the other."},
        "size": {"rule": "depth_capped", "usd_per_bet": 10,
                 "max_share_of_depth": 0.2},
        "wrong_if": [
            "Fills only arrive when the market then moves against the fill, "
            "i.e. the capture is smaller than the pick-off cost. This is the "
            "measured failure of crypto market making (reopen C022: 17,325 "
            "fills, 1,161 events, 23 days, net -0.853 cents per contract, "
            "range [-1.632, -0.185]). If this reproduces that shape on other "
            "categories it is dead.",
            "Under 100 fills in 30 days across all eligible families.",
            "Net capture after the pick-off cost is inside its no-skill range "
            "at 100 settled markets."],
        "slow": False,
        "notes":
            "sell_at_c and buy_more_at_c are OFFSETS in cents from the fill "
            "price, not absolute prices, because this quotes across the whole "
            "price range. C022 killed this on crypto specifically and on "
            "evidence. Crypto is therefore excluded from the family list, and "
            "this spec exists to ask the question C022 did not: whether the "
            "same is true in categories where the counterparty is not another "
            "bot.",
    })

    w({
        "id": "SF004",
        "created": "2026-08-18",
        "author": "claude:factory",
        "source": "github",
        "source_detail":
            "artyomderkach-bit/kalshi-15m-market-maker, read in full by "
            "signal-github (GITHUB_KNOWLEDGE.md, 'longshot-seller maker'); "
            "costs modelled YES, evidence backtest/longshot_maker.py:7 and "
            "backtest/maker_model.py:11. Independently described by Part Time "
            "Larry, 'the nothing ever happens strategy', youtube-signal "
            "KNOWLEDGE.md at timestamps 931-965s.",
        "families": ["*tier_a_no_maker_fee_non_financial"],
        "thesis":
            "Cheap long-shot contracts are priced above what they are worth "
            "because people enjoy buying them, so resting an offer against the "
            "long shot - which is the same as passively buying the favourite - "
            "earns that overpayment without ever crossing the spread.",
        "unit": "one settled market",
        "entry": {
            "when":
                "Long-shot side priced between 3 and 15 cents, and its ask "
                "exceeds the recorded touch by the margin. Rest a passive "
                "offer at the long-shot ask. At most one fill per market. "
                "Non-financial categories only.",
            "side": "no", "min_price_c": 3, "max_price_c": 15,
            "max_spread_c": 99},
        "exit": dict(NO_EXIT, mode="hold_to_settlement"),
        "size": {"rule": "flat", "usd_per_bet": 10, "max_share_of_depth": 0.2},
        "wrong_if": [
            "Forward result inside its no-skill range at 100 settled markets.",
            "Negative at 50 settled markets.",
            "The shape shows up as many small wins and rare large losses with "
            "a negative total, which is the failure this repo has already "
            "lived through."],
        "slow": False,
        "notes":
            "PRIOR WORK, and it is close. LEDGER B024: 'the one surviving "
            "signal - buy the heavy favourite - is a wide-book quoting "
            "artifact, not a mispricing'. bot-forensics, 952 settled events at "
            "80 cents or above, 2026-06-29 to 2026-07-27. Residual by opening "
            "spread was +7.92 out of 100 on books wider than 8 cents and +1.18 "
            "out of 100 on books tighter than 2 cents, which at t=0.64 is "
            "nothing; net at the ask it was -0.77 cents. SETTLED as an "
            "artifact, and its own row records the detectable-effect floor on "
            "tight books as 5.15 out of 100 - 'a real effect is not excluded, "
            "only unevidenced'. HOW THIS DIFFERS: B024 bought at the ASK as a "
            "taker and that is where the -0.77 cents came from. This never "
            "crosses the spread - it rests an order, on series that charge "
            "makers nothing, and is filled only if someone comes to it. The "
            "cost being tested differs by the spread plus the taker fee, which "
            "at these prices is the same size as the entire effect under "
            "discussion. This is a different test, not a re-run. It is also "
            "the shape of the $25 to $130 run (CLAUDE.md 9b item 3), so it "
            "gets watched for the one-loss-eats-thirty pattern specifically.",
    })

    w({
        "id": "SF005",
        "created": "2026-08-18",
        "author": "claude:factory",
        "source": "reopen",
        "source_detail":
            "reopen/REOPENED.md, claim C023. Recorded in the ledger with the "
            "single word 'negative'. The committed output "
            "crypto/reports/hold_settle.txt (25 May - 30 Jul 2026, four "
            "assets, 146-250 events each) says TIE in 40 of its 44 price "
            "cells, with ranges of plus or minus 5 to 15 cents against a cost "
            "of 1 to 2 cents. Bitcoin at 5 cents reads +2.9 cents with its "
            "bottom edge one hundredth of a cent below zero. Classified by the "
            "reopen audit as closed for the wrong reason - too small - not as "
            "a negative result.",
        "families": ["KXBTCD", "KXETHD", "KXSOLD", "KXBTCE", "KXETHE",
                     "KXSOLE"],
        "thesis":
            "Buying a crypto level contract and simply holding it to "
            "settlement was written down as a loser, but the measurement "
            "behind that word could not tell a five cent gain from a five cent "
            "loss, so the question is open rather than answered.",
        "unit": "one settled market",
        "entry": {
            "when":
                "Buy at the recorded ask at a fixed number of minutes before "
                "close, across the whole price range in 5-cent buckets, so the "
                "answer is a curve rather than one number. No selection on "
                "which bucket looks good.",
            "side": "either", "min_price_c": 2, "max_price_c": 98,
            "max_spread_c": 6},
        "exit": dict(NO_EXIT, mode="hold_to_settlement"),
        "size": {"rule": "flat", "usd_per_bet": 10, "max_share_of_depth": 0.25},
        "wrong_if": [
            "Every price bucket's range still contains zero at 100 settled "
            "markets per bucket - in which case the honest answer is still "
            "unmeasured, and it gets recorded as unmeasured rather than as "
            "negative for a second time.",
            "The whole curve sits below zero once the real ask and the real "
            "fee are used.",
            "The buckets that look good are the ones with the fewest markets "
            "in them."],
        "slow": False,
        "notes":
            "The reason this is worth re-running rather than re-reading: the "
            "original had 146-250 events per asset. Crypto level markets "
            "settle every hour, so the wide recorder accrues that many in "
            "days, not months. The number that killed it was a sample size, "
            "and a sample size is the one thing recording fixes. Reporting "
            "rule: the whole curve, every bucket, including the empty ones - "
            "picking the best bucket after the fact is exactly the best-of-N "
            "trap this project is built around.",
    })

    w({
        "id": "SF006",
        "created": "2026-08-18",
        "author": "claude:factory",
        "source": "reopen",
        "source_detail":
            "reopen/REOPENED.md, claim K012: 'economics markets are killed on "
            "recurrence' means we can never gather enough of them to measure "
            "anything. It reads as 'there is no edge there'. Those are "
            "opposite sentences.",
        "families": ["*tier_a_economics"],
        "thesis":
            "Economic release markets were never tested and were written off "
            "because they happen too rarely to gather - which is a reason to "
            "start recording them, not a reason to believe there is nothing "
            "there.",
        "unit": "one settled market",
        "entry": {
            "when":
                "Buy at the recorded ask at a fixed number of hours before "
                "close on every economics-category market the recorder covers, "
                "bucketed by price. Deliberately the dullest possible rule: "
                "the point of this spec is to accrue a sample in a category "
                "that has none, not to be clever.",
            "side": "either", "min_price_c": 5, "max_price_c": 95,
            "max_spread_c": 8},
        "exit": dict(NO_EXIT, mode="hold_to_settlement"),
        "size": {"rule": "flat", "usd_per_bet": 10, "max_share_of_depth": 0.25},
        "wrong_if": [
            "Fewer than 100 settled markets accrue by 2026-11-18, in which "
            "case the original 'killed on recurrence' judgment is confirmed on "
            "its own terms and this is dropped as unmeasurable rather than as "
            "unprofitable.",
            "Result inside its no-skill range at 100 settled markets."],
        "slow": True,
        "notes":
            "DECLARED SLOW IN ADVANCE, which is the point of the flag. "
            "Economics families settle monthly or quarterly. A month gives no "
            "answer here and saying so now is a prediction, not an excuse "
            "offered in September. What a month DOES give is tape that does "
            "not currently exist for a single economics family.",
    })

    w({
        "id": "SF007",
        "created": "2026-08-18",
        "author": "claude:factory",
        "source": "reasoning",
        "source_detail":
            "The market object carries settlement_timer_seconds (120 on the "
            "markets inspected) and the series object carries "
            "settlement_sources with names and URLs. So the exchange itself "
            "publishes who decides the outcome and how long it waits after "
            "deciding.",
        "families": ["*tier_a_scheduled_release"],
        "thesis":
            "Markets that settle on a number published at a scheduled instant "
            "stay open for a couple of minutes after that number exists, so "
            "the question worth measuring is how much of the price move "
            "happens before the number is public rather than after it.",
        "unit": "one settled market",
        "entry": {
            "when":
                "DIAGNOSTIC, not a trade. For every market whose series names "
                "a scheduled publisher, measure the recorded price path either "
                "side of the publication instant and report the share of the "
                "total move that had already happened one minute before "
                "publication.",
            "side": "either", "min_price_c": 1, "max_price_c": 99,
            "max_spread_c": 99},
        "exit": dict(NO_EXIT, mode="hold_to_settlement"),
        "size": {"rule": "flat", "usd_per_bet": 10, "max_share_of_depth": 0.25},
        "wrong_if": [
            "The share of the move already complete before publication is "
            "above 90 out of 100, which is the answer his own bot got on "
            "sports (97.4 out of 100 of the move already done, 4,398 "
            "score-change events). At that number this whole direction is dead "
            "for anything he could actually run, and it gets written down as "
            "dead.",
            "The recorder's cycle is too coarse to see the move at all, in "
            "which case the finding is about the recorder and is reported as "
            "such."],
        "slow": True,
        "notes":
            "This is a MEASUREMENT, not a strategy to run, and it is written "
            "as a spec so that it is screened and reported under the same "
            "rules as one. CLAUDE.md 9b item 2 holds absolutely: nothing here "
            "goes live and in-play, and this spec cannot become a live "
            "strategy no matter what it finds - it can only tell us whether "
            "that door is shut by a wall or a curtain. Doing it on tape costs "
            "nothing and answers it once for the whole exchange rather than "
            "family by family.",
    })

    w({
        "id": "SF008",
        "created": "2026-08-18",
        "author": "claude:factory",
        "source": "reasoning",
        "source_detail":
            "A crossed book - a bid above an ask - is impossible on a "
            "functioning exchange. On Kalshi both sides are quoted as bids and "
            "the YES ask is 100 minus the best NO bid, so a crossing means the "
            "two ladders have gone inconsistent.",
        "families": ["*all_tier_a"],
        "thesis":
            "If a bid is ever above an ask on the same market, either there is "
            "free money sitting on the screen or our reading of the book is "
            "wrong, and finding out which is worth doing before any strategy "
            "is priced off that book.",
        "unit": "one recorded snapshot",
        "entry": {
            "when":
                "yes_bid_c >= yes_ask_c on a recorded tier A snapshot with "
                "both sides sized above zero. Record it, its duration across "
                "cycles, and whether it persists into the next snapshot.",
            "side": "either", "min_price_c": 1, "max_price_c": 99,
            "max_spread_c": 99},
        "exit": {
            "mode": "time_exit", "sell_at_c": None, "buy_more_at_c": None,
            "time_exit_utc_rule": "the next recorded cycle, whatever it shows",
            "second_mentality": None, "on_disagreement": None},
        "size": {"rule": "flat", "usd_per_bet": 10, "max_share_of_depth": 0.5},
        "wrong_if": [
            "It never fires, which is the expected and desirable outcome and "
            "makes this a passed canary rather than a failed strategy.",
            "It fires often, in which case the overwhelmingly likely cause is "
            "our own reading of the two ladders and the first thing audited is "
            "our code, not the exchange."],
        "slow": False,
        "notes":
            "GUARDS #18, the structural-invariant canary: conservation can "
            "pass while the book rots. This runs continuously against tier A "
            "tape for the life of the project and costs nothing, and its value "
            "is almost entirely as a canary rather than as a trade.",
    })


if __name__ == "__main__":
    build()
