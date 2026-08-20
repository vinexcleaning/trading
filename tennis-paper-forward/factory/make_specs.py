"""make_specs.py - the tennis strategy specs, for the strategy factory.

Emits one JSON file per spec into strategy-factory/specs/, in the format that
strategy-factory/src/spec.py validates.

ID RANGE: SF100-SF199 is tennis. Recorded in STATUS.md so two chats cannot
write the same id. The factory keeps SF001-SF099.

EVERY NUMBER HERE IS MEASURED, and each measurement is named where it is used.

  A. CAPACITY, from bot-hunt/data/record.db - 16 days, 2026-08-04 to 08-20,
     254,220 rows over 4,896 tennis tickers. Median dollars at the best ask and
     mean spread, bucketed by how long before that market stopped quoting:

        family        >12h out       2-12h          last 2h
        KXATPMATCH    3.8c / $1,002  1.4c / $6,642  1.2c / $9,599
        KXWTAMATCH    5.4c / $753    1.8c / $3,384  1.2c / $5,559
        KXITFWMATCH   16.9c / $18    7.9c / $63     3.9c / $163
        KXITFMATCH    19.9c / $13    9.7c / $46     5.6c / $124

     THAT IS THE HEADLINE AND IT SHAPES EVERY ITF SPEC BELOW. ITF is three to
     four times wider than ATP and carries roughly one per cent of the size. It
     is tradeable only in the last two hours, and even then a click is about
     $123 against ATP's $9,599.

  B. THE FORWARD TEST - tennis-paper-forward, 17 bots, 1,037 settled matches
     from 2026-08-06. Every bot carries a no-skill range from common/noskill.py
     and EVERY ONE SITS INSIDE ITS OWN RANGE. That is why most entries below
     are no_evidence rather than ruled_out: inside the range means the test
     could not tell, not that the idea is dead. GUARDS #21.

  C. THE ONE THING ACTUALLY RULED OUT: per-trade stops. The three exit arms
     differ ONLY in exit rule, on the same matches at the same prices, and not
     stopping won 5 families out of 5 by 9.3 points. Pre-registered before the
     run, and bot-forensics reached the same direction independently on the
     user's own live bot (-2.29c to -9.36c).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SPECS = ROOT / "strategy-factory" / "specs"

TODAY = "2026-08-20"
ME = "claude:tennis"

CAPACITY = ("Measured on 16 days of recorded book, 2026-08-04 to 08-20, with "
            "common/capacity.py. By hours before the market stopped quoting "
            "(>12h / 2-12h / last 2h): KXITFMATCH 19.9c-$13, 9.7c-$46, "
            "5.6c-$124. KXITFWMATCH 16.9c-$18, 7.9c-$63, 3.9c-$163. "
            "KXATPMATCH 3.8c-$1,002, 1.4c-$6,642, 1.2c-$9,599. KXWTAMATCH "
            "5.4c-$753, 1.8c-$3,384, 1.2c-$5,559. NOTE the two ITF families are NOT the same market: the women's book is about 30% tighter and 30% deeper than the men's in every bucket.")

FORWARD = ("tennis-paper-forward, 17 bots, 1,037 settled matches from "
           "2026-08-06, every bot inside its own no-skill range.")

HOLD = {"mode": "hold_to_settlement", "sell_at_c": None, "buy_more_at_c": None,
        "time_exit_utc_rule": None, "second_mentality": None,
        "on_disagreement": None}


def E(when, side="yes", lo=3, hi=97, spread=3):
    return {"when": when, "side": side, "min_price_c": lo,
            "max_price_c": hi, "max_spread_c": spread}


def S(usd, share=0.25):
    return {"rule": "depth_capped", "usd_per_bet": usd,
            "max_share_of_depth": share}


def spec(**kw):
    s = {"id": kw["id"], "created": TODAY, "author": ME,
         "source": kw.get("source", "reasoning"),
         "source_detail": kw["source_detail"], "families": kw["families"],
         "thesis": kw["thesis"], "unit": kw.get("unit", "one settled match"),
         "entry": kw["entry"], "exit": kw["exit"], "size": kw["size"],
         "wrong_if": kw["wrong_if"], "slow": kw.get("slow", False),
         "notes": kw["notes"]}
    # NON-STANDARD FIELD, flagged to the factory in STATUS.md rather than
    # invented silently. spec.py requires 13 fields and permits extras. It
    # exists because "tried, and the test could not tell" and "never tried" are
    # different things, and a factory that treats them alike will re-screen
    # dead ideas forever and inflate the screened total it judges everything by.
    if kw.get("prior"):
        s["prior_evidence"] = kw["prior"]
    return s


SPECS_OUT = [

    spec(id="SF100",
         families=["KXITFMATCH", "KXITFWMATCH"],
         source_detail=("Capacity measurement on this repo's own recorded "
                        "book, made 2026-08-20 by the tennis chat. " + CAPACITY),
         thesis=("ITF is only tradeable in the last two hours before a match, "
                 "when the quote tightens from about twenty cents to under six "
                 "and the money at the best price rises from thirteen dollars "
                 "to about a hundred and twenty. Any ITF strategy that ignores "
                 "the clock is priced against a book that does not exist."),
         entry=E("The market is inside its last two hours of quoting AND the "
                 "spread is 4 cents or less AND at least $100 is showing at the "
                 "best ask. This spec is the GATE, screened alone so the cost "
                 "of the restriction is known before any rule is layered on it.",
                 side="either", lo=10, hi=90, spread=4),
         exit=HOLD, size=S(25),
         wrong_if=["Fewer than 200 matches in 30 days pass the gate, which "
                   "would leave every ITF strategy underpowered however good "
                   "its rule is.",
                   "The gate is passed but the realised round trip still "
                   "exceeds 6 cents, which is larger than any edge this repo "
                   "has ever measured.",
                   "Capacity at the touch inside the gate is under $50, which "
                   "makes it a hobby rather than a market."],
         notes=("THE GATE, not a trade. " + CAPACITY +
                " || WHY THIS MATTERS TO THE FACTORY: KXITFMATCH and "
                "KXITFWMATCH carry about 3,500 of the 4,900 recorded tennis "
                "tickers, five times ATP and WTA combined, so a factory ranking "
                "families by ticker count will point straight at the least "
                "tradeable corner of the exchange. || PRIOR: no ledger row "
                "covers ITF capacity. LEDGER T018 said the ITF tier cannot be "
                "modelled, but that was measured as serve stats on 4.6% of one "
                "provider's rows - a statement about a data source, not about "
                "the book.")),

    spec(id="SF101",
         families=["KXITFMATCH", "KXITFWMATCH"],
         source="ledger",
         source_detail=("The soccer chat's finding that tennis is where a quote "
                        "survives furthest into a near-certainty, tested on the "
                        "family where the book is thinnest and a stale quote is "
                        "most likely to persist."),
         thesis=("In a thin ITF book a heavy favourite's price can lag the "
                 "state of the match, so a quote at 88 to 96 cents still "
                 "available late is either a genuine bargain or a stale screen. "
                 "This asks which, and the measurement is the same either way."),
         entry=E("Last two hours of quoting, spread 3 cents or less, best ask "
                 "between 88 and 96 cents, at least $100 showing. Buy YES.",
                 side="yes", lo=88, hi=96, spread=3),
         exit=HOLD, size=S(25),
         wrong_if=["The win rate comes in below the entry price - buying at 92c "
                   "wins under 92 times in 100 - which is the whole bet.",
                   "It fires under 100 times in 30 days.",
                   "The result sits inside its no-skill range once fees are "
                   "paid, which is what all 17 forward bots currently do."],
         notes=("AT 92 CENTS THE FEE IS ABOUT 0.52c, roughly a fifth of what it "
                "is at 50c, so this band is chosen partly because it is where "
                "the fee is cheapest. That is a real structural advantage and "
                "it is also exactly where a wrong-way loss costs 92 cents to "
                "win 8. || THE ARCHIVE IS AGAINST THIS. Buy-the-heavy-favourite "
                "measured +3.12c at the mid and +0.96c then -0.77c at real "
                "prices, and the apparent edge GREW with the spread: +1.18c "
                "where the quote was tight enough to trade, +7.92c where it was "
                "wider than 8c. That is the signature of the spread, not of an "
                "edge, which is why the spread is capped at 3c here rather than "
                "taking whatever is offered. || " + FORWARD)),

    spec(id="SF102",
         families=["KXITFMATCH", "KXITFWMATCH", "KXATPMATCH", "KXWTAMATCH"],
         source_detail=("Structural invariant on Kalshi's mirrored pair, "
                        "measured live by the tennis chat 2026-08-06 to 08-13."),
         thesis=("Kalshi lists one market per player, so the two YES asks are "
                 "complements and must cost at least a dollar together. When "
                 "they cost less, buying both is locked money - if the fees do "
                 "not eat it, which on this book they always have."),
         entry=E("Within one event, both sides quotable, ask(A) + ask(B) below "
                 "100 minus the two-leg fee. Buy both sides in equal size at "
                 "the recorded touch size.",
                 side="either", lo=1, hi=99, spread=99),
         exit=HOLD, size=S(25, 0.5),
         wrong_if=["It never fires net of the two-leg fee over 30 days, which "
                   "is what 16 days of live observation already suggests.",
                   "It fires but median locked profit is under 0.5 cents.",
                   "Capacity is under $25 per firing."],
         prior={"status": "expected null, but cheap and doubles as a canary",
                "measured_by": "tennis-paper-forward, live, 2026-08-06 to 08-13",
                "finding": ("13 to 16 of about 123 matches per tick showed both "
                            "asks summing under a dollar, median 1 cent gross, "
                            "and ZERO beat the two-leg fee of about 2.5 cents."),
                "why_still_worth_running": ("Free on tape already being "
                            "collected, and it is a data-quality canary: if it "
                            "starts firing constantly the likely cause is my "
                            "own event grouping, not the exchange.")},
         notes=("DOUBLES AS A CANARY, GUARDS #18. The correct stale-book "
                "invariant is the OTHER direction - bid(A) + bid(B) above 100 "
                "is impossible in a live book and fires on 1-2 matches a tick. "
                "The under-100 ask sum is common and is NOT a stale book; "
                "mislabelling it as one is a mistake this chat made and "
                "corrected. || Reproduces LEDGER K007 - 52 genuine violations, "
                "0 with tradeable size, 1,083 scans - on a family it was never "
                "measured on.")),

    spec(id="SF103",
         families=["KXATPMATCH", "KXWTAMATCH"],
         source_detail=("The one shape this repo has never tested on tennis and "
                        "the only shape currently winning anywhere in it: "
                        "pre-game. bot-forensics measured 97.4% of the price "
                        "move as already gone by the time a bot reacts in-play, "
                        "on 4,398 score-change events."),
         thesis=("Bet before the first ball on evidence that does not go stale "
                 "- career surface record, head-to-head, deciding-set record, "
                 "break points saved - because in-play is a race this repo has "
                 "already measured itself losing."),
         entry=E("Strictly before the scheduled start time. Spread 2 cents or "
                 "less. The brief's non-decaying evidence must favour the side "
                 "by more than that market's own round-trip cost.",
                 side="either", lo=15, hi=85, spread=2),
         exit=HOLD, size=S(25),
         wrong_if=["The result lands inside its no-skill range after 400 "
                   "settled matches, the point at which that range narrows "
                   "enough to be worth reading.",
                   "It fires under 150 times in 30 days.",
                   "Splitting by tier puts the whole effect in one tier, which "
                   "would make it a tier finding and not a rule."],
         notes=("ALREADY RUNNING as pre-game__hold in tennis-paper-forward "
                "since 2026-08-13, on its own arm, never pooled backwards. "
                "Deliberately EXCLUDES recent form: the free archive freezes at "
                "2026-06-01 and this project's own recorder holds 1.5 results "
                "per player with 66% of players appearing exactly once. One "
                "result is not form, and a bot leaning on it would measure "
                "staleness rather than the idea. || Written here so the factory "
                "does not generate it a second time. " + FORWARD)),

    spec(id="SF110",
         families=["KXITFMATCH", "KXITFWMATCH", "KXATPMATCH", "KXWTAMATCH"],
         source_detail=("tennis-paper-forward's own three-arm exit experiment, "
                        "pre-registered before the run."),
         thesis=("Selling a losing tennis position before settlement, on a stop "
                 "or a target, costs about nine points against simply holding - "
                 "because the downside is already capped at what you paid, so a "
                 "stop realises a loss that was going to recover and pays the "
                 "buy-sell gap twice."),
         entry=E("Any entry rule. This spec is about the EXIT, and exists so "
                 "the factory does not generate stop-loss variants of other "
                 "strategies without seeing this first.",
                 side="either", lo=3, hi=97, spread=4),
         exit={"mode": "sell_at_level", "sell_at_c": 12, "buy_more_at_c": None,
               "time_exit_utc_rule": None, "second_mentality": None,
               "on_disagreement": None},
         size=S(25),
         wrong_if=["A stop arm beats its own hold arm on the same matches at "
                   "the same prices over 400 or more settled matches, which "
                   "would overturn a pre-registered 5-of-5 result."],
         prior={"status": "RULED OUT",
                "measured_by": ("tennis-paper-forward, 545 settled matches, "
                                "2026-08-06 to 08-13"),
                "finding": ("Three arms differing ONLY in exit rule, on the "
                            "same matches at the same prices with the same "
                            "sizing. Not stopping won in 5 families out of 5, "
                            "by 9.3 points on average."),
                "independent_confirmation": ("bot-forensics, on the user's own "
                            "live tennis bot: stop-and-re-enter turned -2.29 "
                            "cents per contract into -9.36."),
                "caveat": ("The selling arms also differ in RE-ENTRY, not only "
                           "in stopping, so this is not a clean test of the "
                           "stop alone, and it is 5 matched pairs not 500."),
                "scope": ("Applies to a PER-TRADE stop on an instrument whose "
                          "downside is capped. It does NOT apply to a daily "
                          "stop-everything cut-off, which is a different animal "
                          "and should stay.")},
         notes=("WRITTEN AS A SPEC SO IT IS FINDABLE, not because it should be "
                "screened. The factory's rules say a variant counts against the "
                "screened total; the point of this entry is that stop-loss "
                "variants of tennis strategies should not be generated at all "
                "without a reason to overturn the result above.")),

    spec(id="SF111",
         families=["KXITFMATCH", "KXITFWMATCH", "KXATPMATCH", "KXWTAMATCH"],
         source_detail=("tennis-paper-forward's four in-play mentalities, "
                        "1,037 settled matches."),
         thesis=("Four different in-play dispositions - buy heavy favourites, "
                 "buy cheap underdogs, follow the price, trade the model's "
                 "disagreement with the price - all produced results a coin "
                 "could have produced."),
         entry=E("Various. Recorded as one entry because the finding is about "
                 "all four together: not one of them separated from chance.",
                 side="either", lo=3, hi=97, spread=4),
         exit=HOLD, size=S(25),
         wrong_if=["Any of the four lands outside its own no-skill range on the "
                   "winning side at 400 or more settled matches."],
         prior={"status": "NO EVIDENCE EITHER WAY - not ruled out",
                "measured_by": ("tennis-paper-forward, 1,037 settled matches "
                                "from 2026-08-06"),
                "finding": ("All 17 bots sit INSIDE their own no-skill range - "
                            "the spread a bot with no idea at all would land in "
                            "90 times in 100 while paying the same fees on the "
                            "same bets. The best, a heavy-favourite hold arm, "
                            "reads about +7.5% inside a range of -14.2% to "
                            "+10.9%."),
                "why_this_is_not_ruled_out": ("GUARDS #21. Inside the range "
                            "means the test could not tell, which is a verdict "
                            "about the TEST and not about the idea. Saying "
                            "otherwise is the mistake this repo has recorded "
                            "more than any other."),
                "what_would_settle_it": ("About 3,260 bets for the "
                            "heavy-favourite arm, which buys at 83c where the "
                            "fee is small and therefore needs the most data.")},
         notes=("RECORDED SO THE FACTORY DOES NOT COUNT THESE AS FRESH IDEAS. "
                "They have run forward on live markets for two weeks and the "
                "honest result is a shrug, not a kill. " + FORWARD)),
]


def main() -> int:
    SPECS.mkdir(parents=True, exist_ok=True)
    for s in SPECS_OUT:
        (SPECS / f"{s['id']}.json").write_text(
            json.dumps(s, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(SPECS_OUT)} tennis specs into {SPECS}")
    for s in SPECS_OUT:
        tag = (s.get("prior_evidence") or {}).get("status", "new")
        print(f"   {s['id']}  {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
