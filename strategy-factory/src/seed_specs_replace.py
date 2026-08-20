"""Replacements for the three specs that rules text killed on 2026-08-20.

SF011 (Entertainment), SF012 (Politics) and SF016 (Science and Technology) were
all VOIDED by the same discovery: **Kalshi's named-candidate sets are not
mutually exclusive.** A festival has several headliners, several people can be
pardoned, and a Nobel Prize can be shared by three. Each of those specs rested
on the set summing to a dollar. None of them does.

That emptied three categories, so `spec.py --coverage` refused. These are the
replacements, and **each one carries the lesson that killed its predecessor**:
they use NUMERIC ladders, which genuinely partition, and they say so.

    py -3 strategy-factory/src/seed_specs_replace.py
"""
from __future__ import annotations

import json
from pathlib import Path

S = Path(__file__).resolve().parent.parent / "specs"
HOLD = {"mode": "hold_to_settlement", "sell_at_c": None, "buy_more_at_c": None,
        "time_exit_utc_rule": None, "second_mentality": None,
        "on_disagreement": None}

LESSON = (
    " || WHY THIS IS NOT ITS PREDECESSOR. The spec it replaces was VOIDED on "
    "2026-08-20 by rules text already on tape: Kalshi's NAMED-CANDIDATE sets "
    "are not mutually exclusive. 'Will Tame Impala be a Headliner at Coachella' "
    "- a festival has several. 'Will Eric Trump receive a presidential pardon' "
    "- several people can be. 'Will Yves Meyer win the Nobel Physics' - it can "
    "be shared by three. Every one of those specs assumed the set summed to a "
    "dollar. This one uses a NUMERIC ladder on a single published number, where "
    "exactly one bracket can be true, so the partition is real. If a future "
    "version of this spec is ever extended to a named-candidate family, it has "
    "become the spec it replaced and must be dropped.")


def w(d):
    (S / (d["id"] + ".json")).write_text(json.dumps(d, indent=1),
                                         encoding="utf-8")
    print("wrote %s  [%s]" % (d["id"], d.pop("_cat", "")))


def build():
    w({
        "id": "SF023", "_cat": "Entertainment",
        "created": "2026-08-20", "author": "claude:factory",
        "source": "reasoning",
        "status": "LIVE",
        "source_detail":
            "Replaces the VOIDED SF011. KXRT is 180 two-sided markets on "
            "Rotten Tomatoes scores, and Entertainment mints about 509 new "
            "markets a day measured off the tape. Unlike an awards shortlist, "
            "a score ladder is a numeric partition: a film has exactly one "
            "score.",
        "families": ["KXRT"],
        "thesis":
            "A film's Rotten Tomatoes score is public and stops moving once "
            "enough reviews are in, so the question worth asking is whether "
            "Kalshi still quotes a market whose answer is already visible - and "
            "if it does not, that is the same wall that closed the soccer work.",
        "unit": "one film",
        "entry": {
            "when":
                "For each film, record whether a two-sided quote exists at each "
                "point in the run-up to settlement, and how far the current "
                "public score sits from the strike. Buy at the recorded ask "
                "only where the outcome is already effectively determined by "
                "the public score AND a quote exists. Availability is recorded "
                "first and separately from price.",
            "side": "either", "min_price_c": 3, "max_price_c": 97,
            "max_spread_c": 6},
        "exit": HOLD,
        "size": {"rule": "depth_capped", "usd_per_bet": 10,
                 "max_share_of_depth": 0.25},
        "wrong_if": [
            "No quote exists once the score is effectively settled - which is "
            "GUARDS #24 arriving in an eighth sport, and is the expected "
            "outcome. Reported as availability, not as price.",
            "Inside its no-skill range at 100 settled films.",
            "The public score is not obtainable free, in which case this is "
            "recorded as blocked on data and the availability half still "
            "stands on its own."],
        "slow": True,
        "notes":
            "THE AVAILABILITY HALF IS THE VALUABLE HALF AND IT COSTS NOTHING. "
            "GUARDS #24 says a market maker declines to quote when there is "
            "nothing left to be uncertain about, measured across seven sports. "
            "Rotten Tomatoes is the cleanest non-sport test of that guard "
            "available on this exchange, because the outcome becomes public "
            "BEFORE settlement in a way a match result does not. Whatever "
            "happens to the trade, the guard gets an eighth data point." + LESSON,
    })

    w({
        "id": "SF024", "_cat": "Politics",
        "created": "2026-08-20", "author": "claude:factory",
        "source": "reasoning",
        "status": "LIVE",
        "source_detail":
            "Replaces the VOIDED SF012. KXFUNDRAISING is 84 two-sided markets "
            "settling on FEC filings, and KXNYCSTAT 53 on published statistics "
            "- both NUMERIC ladders on a single published number, unlike the "
            "'who will be pardoned' sets that voided SF012.",
        "families": ["KXFUNDRAISING", "KXNYCSTAT"],
        "thesis":
            "Political money and city statistics settle on a number somebody "
            "publishes on a schedule, so the plain question - does buying and "
            "holding these ladders make or lose money - has never been asked "
            "and the answer costs nothing but the waiting.",
        "unit": "one published figure",
        "entry": {
            "when":
                "NUMERIC LADDERS ONLY. A family qualifies if its markets are "
                "brackets on one published number; any family whose markets "
                "name PEOPLE is excluded by rule, not by judgement. Buy at the "
                "recorded ask a fixed number of days before the scheduled "
                "publication, bucketed by price in 5-cent bands, and report the "
                "whole curve.",
            "side": "either", "min_price_c": 5, "max_price_c": 95,
            "max_spread_c": 8},
        "exit": HOLD,
        "size": {"rule": "flat", "usd_per_bet": 10, "max_share_of_depth": 0.25},
        "wrong_if": [
            "Fewer than 100 figures settle by 2027-02-20. Politics mints only "
            "about 10 new markets a day measured off the tape, so this is the "
            "likeliest outcome and it is reported as UNMEASURABLE, not as "
            "negative.",
            "Every price bucket's range contains zero at 100 settled figures.",
            "The whole curve sits below zero at the real ask and the real fee.",
            "A family in the list turns out to name people after all, which "
            "means the exclusion rule was applied by eye rather than by code."],
        "slow": True,
        "notes":
            "THE EXCLUSION IS A RULE, NOT A JUDGEMENT, and that is the whole "
            "point of the rewrite. SF012 died because somebody (me) looked at "
            "'who will Trump pardon' and assumed exactly one could happen. The "
            "replacement does not ask anyone to assess exclusivity by eye: a "
            "family is in only if its markets are brackets on a number." + LESSON,
    })

    w({
        "id": "SF025", "_cat": "Science and Technology",
        "created": "2026-08-20", "author": "claude:factory",
        "source": "reasoning",
        "status": "LIVE",
        "source_detail":
            "Replaces the VOIDED SF016, and rescues the half of it that was "
            "never affected. SF016 bundled Nobel prizes (named candidates, "
            "shareable, therefore void) with GPU PRICES (numeric, monthly). "
            "KXH200MON 28 two-sided, KXH100MON 20, KXB200MON 20 - the only "
            "recurring families in the category.",
        "families": ["KXH200MON", "KXH100MON", "KXB200MON", "KXB200MAX"],
        "thesis":
            "Graphics-card prices settle every month against a published "
            "figure, which makes them the only thing in this whole category "
            "that comes round often enough to ever be judged.",
        "unit": "one monthly settlement",
        "entry": {
            "when":
                "Buy at the recorded ask a fixed number of days before the "
                "monthly close, bucketed by price in 5-cent bands. The dullest "
                "possible rule on purpose - this exists to accrue a sample in "
                "the only corner of this category that recurs.",
            "side": "either", "min_price_c": 5, "max_price_c": 95,
            "max_spread_c": 8},
        "exit": HOLD,
        "size": {"rule": "flat", "usd_per_bet": 10, "max_share_of_depth": 0.25},
        "wrong_if": [
            "Fewer than 100 monthly settlements accrue by 2027-08-20 - four "
            "families settling monthly is 48 a year, so this is arithmetically "
            "the likely outcome and it is UNMEASURABLE, not negative.",
            "Every price bucket's range contains zero at whatever sample "
            "arrives.",
            "The settlement source ('Ornn') turns out not to be readable free, "
            "in which case this is blocked on data and says so."],
        "slow": True,
        "notes":
            "⚠ THE ARITHMETIC SAYS THIS WILL PROBABLY BE UNMEASURABLE AND THAT "
            "IS WRITTEN DOWN BEFORE IT RUNS. Four families times twelve months "
            "is 48 settlements a year against the 100 needed, so the honest "
            "expectation is a two-year wait. It is written anyway because the "
            "category has no other recurring family, and a category with no "
            "spec is a category that was skipped - but nobody should be "
            "surprised in a year, and 'unmeasurable' will not be dressed up as "
            "'no edge'." + LESSON,
    })


if __name__ == "__main__":
    build()
