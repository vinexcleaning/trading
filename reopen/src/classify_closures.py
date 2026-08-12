"""The classification itself: every distinct claim, sorted by HOW it was closed.

This file is the audit. The screen (`screen_closures.py`) ordered the reading;
this records the reading. Every judgement here was made by opening the claim's
own row and, where the row summarises an artifact, the artifact.

CATEGORIES
----------
  NOT-A-CLOSURE  the row is a fact, a guard, a positive finding, a correction,
                 or an item that is still openly open. It never stopped a line
                 of work, so there is nothing to reopen.
  EVIDENCE       measured properly, at a sample that could have found the
                 effect being looked for, and it did not. Leave it alone.
  BUG            a script was wrong and the conclusion followed the bug.
  DATA           closed because a source was missing, paywalled or dead.
  NARROW         one arm was tested and the whole idea was declared dead.
  FLOOR          a null reported by a test too small to see the effect the
                 idea would need. "No effect" where the honest sentence is
                 "this test could not have seen it."

The build FAILS if any claim in any ledger is missing from the table below.
Silent omission is the exact failure this chat exists to catch, so it is a
hard error rather than a warning.

READ ONLY outside reopen/.

  py -3 reopen\\src\\classify_closures.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "coordinator"))

import ledger  # noqa: E402

OUT = HERE.parent / "reports"

N = "NOT-A-CLOSURE"
E = "EVIDENCE"

# id: (category, note). Note is required for anything that is not EVIDENCE or
# NOT-A-CLOSURE -- a reopen without a stated reason is not a finding.
C: dict[str, tuple[str, str]] = {

    # ---- set1_overshoot -----------------------------------------------------
    "S001": (N, "a positive finding, not a closure"),
    "S002": (E, ""),
    "S003": (N, "retraction"),
    "S004": (N, "cost arithmetic, recomputed every run"),
    "S005": ("FLOOR", "0 of 25 time/tier buckets clear the bar -- and the row's "
             "own median detectable effect is 3.7-9.0c against a ~2c target. "
             "The test could not have seen the thing it reports absent."),
    "S006": ("FLOOR", "0 of 10 margin buckets, own median detectable effect "
             "9.9c against a ~2c target. Five times too coarse."),
    "S007": (N, "SUGGESTIVE gradient, openly untested"),
    "S008": (E, ""),
    "S009": (E, ""),
    "S010": (N, "fee structure fact"),
    "S011": (N, "retraction"),
    "S012": (N, "retraction"),
    "S013": (N, "retraction"),
    "S014": (N, "detector accuracy, externally validated"),
    "S015": (N, "estimator tuning fact"),
    "S016": (N, "structural fact"),
    "S017": (N, "identity check / guard"),
    "S018": ("DATA", "'label coverage cannot be raised' rests on exactly two "
             "sources -- Apify's tier cap and Flashscore's +/-7 day window. No "
             "third source is named anywhere."),
    "S019": (N, "fill-assumption fact"),
    "S020": (N, "audit of 15 numbers"),
    "S021": ("FLOOR", "says so itself: needs ~3,970 events for a 2c edge and "
             "the recorder accrues ~1,900 matches a week. Written 2026-08-01. "
             "The sample it lacked is the cheapest thing in this whole audit."),
    "S022": ("BUG", "computed on the event set the dedupe bug voided, BROKEN, "
             "never re-run. Root audit D1, still open."),
    "S023": ("BUG", "the fade side -- half of 'no edge in either direction' -- "
             "computed on the void event set, BROKEN, never re-run."),
    "S024": (N, "SUGGESTIVE, re-test openly pending"),
    "S025": (N, "structural fact from the API"),

    # ---- crypto -------------------------------------------------------------
    "C001": ("NARROW", "'no arbitrage' from 10.5 minutes of scanning. K007 "
             "later found 52 real violations in 9 hours (none tradeable), so "
             "the conclusion holds and the stated count did not."),
    "C002": ("NARROW", "same 10.5-minute window"),
    "C003": (N, "retraction"),
    "C004": (N, "fee fact, reproduced twice"),
    "C005": (N, "descriptive fact about returns"),
    "C006": (N, "retraction"),
    "C007": (N, "control"),
    "C008": (N, "control"),
    "C009": (N, "control"),
    "C010": (E, "250 events, controls that prove the test can find a 5% bias"),
    "C011": (N, "model improvement finding"),
    "C012": (N, "model finding"),
    "C013": (N, "retraction"),
    "C014": (N, "retraction"),
    "C015": (N, "retraction"),
    "C016": ("NARROW", "'the cheap wings are not tradeable' is 61 minutes of "
             "one ladder on one day, 2026-08-01, 11 strikes."),
    "C017": (E, "structural: shortest usable Deribit expiry 54.2h against a "
             "1.0h ladder. Kills Deribit; no other venue was probed."),
    "C018": (N, "API fact"),
    "C019": (N, "guard"),
    "C020": (E, ""),
    "C021": (E, "path/streak: every CI that excludes zero is negative, 250 "
             "events, entry at ask and exit at bid"),
    # WITHDRAWN 2026-08-09. crypto/RESULTS_MAKER_VIABILITY.md (2026-08-08)
    # closed this on evidence a day before I called it a reopen, and I did not
    # open it -- 17,325 fills, 1,161 events, 23 days of replayed KXBTCD book,
    # net -0.853c/contract, CI [-1.632, -0.185] clustered on days, excludes
    # zero. Capture alone is -1.226c, so it fails one step earlier than my
    # "0.5c against 1.0c" framing assumed: there is no spread being captured.
    # Same error as M017 -- I stopped one document short.
    "C022": (E, "closed on evidence 2026-08-08: 17,325 fills, 1,161 events, "
             "23 days, net -0.853c/contract, interval excludes zero. My reopen "
             "read the 08-07 file and missed the 08-08 one. WITHDRAWN."),
    "C023": ("FLOOR", "LEDGER's effect column says 'negative'. The artifact "
             "says TIE in 40 of 44 price cells, with ranges +/-5 to 15c against "
             "a 1-2c cost bar, and BTC at 5c is +2.93c [-0.01, +6.13]."),
    "C024": (N, "recorder bug, openly recorded, fix status unverified"),
    "C025": ("NARROW", "'0 of 4 series profitable' when only one series was "
             "ever P&L-tested. Now largely filled by the 2026-08-07 four-series "
             "run, and the ledger row has not caught up."),
    "C026": (N, "guard -- effective independent series"),
    "C027": (E, "killed on economics: 0.38c of edge against a 1.00c tick"),

    # ---- wallet-copy-study --------------------------------------------------
    "W001": (N, "positive finding"), "W002": (N, "positive finding"),
    "W003": (E, ""), "W004": (E, "the closure: +0.937pp against a >=1.0pp spread"),
    "W005": (E, "monotone decline across three split points"),
    "W006": (N, "retraction"), "W007": (E, ""), "W008": (E, ""),
    "W009": (E, ""), "W010": (E, ""), "W011": (N, "retraction"),
    "W012": (N, "retraction"), "W013": (N, "SUGGESTIVE, caveated"),
    "W014": (E, "2.2M buy signals"), "W015": (N, "shrinkage mechanism"),
    "W016": (N, "an explicit power statement, correctly made"),
    "W017": (N, "regime fact"), "W018": (N, "composition finding"),
    "W019": (E, ""), "W020": (E, ""), "W021": (E, ""), "W022": (E, ""),
    "W023": (N, "canary"),
    "W024": (N, "a declared gate, not a measurement"),

    # ---- kalshi-tennis ------------------------------------------------------
    "T001": (N, "coverage fact"),
    "T002": ("DATA", "the binding constraint on the whole player model is one "
             "frozen source ending 2026-06-02. The root audit's D10 records "
             "that $9.99 buys 43 months of point-by-point history including "
             "ITF. Nobody has bought it."),
    "T003": ("DATA", "'Sackmann upstream is gone' -- B020 later found a live "
             "mirror and a live 399-star repo. Corrected in LEDGER, and the "
             "closure was made before the check."),
    "T004": (E, "3.4M player-match rows, split-half, positive control and null"),
    "T005": (N, "model quality finding"),
    "T006": (E, "the Stage 4 gate, on data containing no Kalshi prices, so the "
             "leak never touched it"),
    "T007": (N, "retraction"), "T008": (N, "retraction"),
    "T009": (E, "19 survive correction, every one negative"),
    "T010": (N, "retraction"), "T011": (N, "leak diagnostic"),
    "T012": (N, "positive finding -- Kalshi is the sharp line"),
    "T013": (E, ""), "T014": (N, "naming hazard"),
    "T015": (N, "spread distribution fact"), "T016": (N, "sanity check"),
    "T017": (N, "retraction"),
    "T018": ("NARROW", "'the ITF tier cannot be modelled' is true of Sackmann's "
             "futures files, which is one source. It is quoted as if it were "
             "about ITF."),
    "T019": (N, "guard"), "T020": (N, "guard"),
    "T021": (N, "reading hazard, severity corrected down"),
    "T022": (N, "fixed, unrun"),

    # ---- kalshi-market-scan -------------------------------------------------
    "K001": ("FLOOR", "'no model beats the mid on KXBTC15M' on 25 markets, "
             "every range spanning zero. The family is separately dead on "
             "structure (K013), which is what actually closes it."),
    "K002": (N, "positive finding"),
    "K003": (N, "retraction"), "K005": (N, "retraction"), "K006": (N, "retraction"),
    "K004": (E, "10 of 11 families fail the power or capacity bar. The "
             "survivor's deciding gate is openly unmeasured."),
    "K007": (E, "52 violations, 0 with tradeable size"),
    "K008": (N, "positive finding on Polymarket"),
    "K009": (E, "762 settled matches; the load-bearing kill for copy trading. "
             "Measured on tennis only."),
    "K010": (N, "already labelled OVERSTATED"),
    "K011": (E, "1,376 settled markets, 1.77M trades"),
    "K012": ("FLOOR", "'economics series are killed on recurrence' is a "
             "statement that they can never be MEASURED (22-48 settlements "
             "against 481 needed), not that they have no edge. The word "
             "'killed' reads as the second."),
    "K013": (E, "structural: minted at the money on 99.86% of 6,261 markets"),
    "K014": (N, "power arithmetic"),
    "K015": (N, "retraction"),
    "K016": (N, "a declared decision"),

    # ---- bot-forensics ------------------------------------------------------
    "B001": (E, ""), "B002": (E, ""), "B003": (E, "200,000 reorderings"),
    "B004": (N, "SUGGESTIVE at best, said so"),
    "B005": (E, ""), "B005a": (N, "propagation gap, the 0 is right"),
    "B006": (N, "confound measurement"), "B007": (E, ""), "B008": (E, ""),
    "B009": (E, "13,658 market views, train/holdout, t=-26"),
    "B010": (E, "0 of 481 configurations"),
    "B011": (N, "consistency check"), "B012": (E, "four files agree"),
    "B013": (N, "settlement fact"), "B014": (N, "observational"),
    "B015": ("NARROW", "'nobody documents the overnight pattern' from two "
             "video corpora and four GitHub queries. It gates nothing."),
    "B016": (N, "superseded by B021"), "B017": (N, "correction"),
    "B018": (N, "sizing fact"), "B019": (N, "classifier caught and replaced"),
    "B020": (N, "corrects T003 / M015"),
    "B021": (N, "THE worked reopen -- a thread closed on a false premise, "
             "reopened by checking the premise"),
    "B022": (N, "vendor rate-limit fact"),
    "B023": ("FLOOR", "LEDGER says SETTLED (null). The project itself writes "
             "'read as not demonstrated on 29 days of form data, not player "
             "features cannot work'. The median player appears ~3 times."),
    "B024": (E, "reports its own detection floor (5.15pp on tight books) and "
             "says a real effect is not excluded, only unevidenced. The model."),
    "B025": (N, "own bugs, caught pre-publication"),
    "B026": (N, "resolved by B027"),
    "B027": (E, "6,519 events, both arms pre-declared"),

    # ---- market-selection ---------------------------------------------------
    "M001": (N, "retraction -- and the worked example of a bug closure"),
    "M002": (N, "retraction"), "M003": (N, "retraction"), "M004": (N, "retraction"),
    "M005r": (N, "retraction"), "M006r": (N, "retraction"),
    "M005": (N, "API fact -- depth is public"),
    "M006": (N, "API fact"), "M007": (N, "API fact"), "M008": (N, "fee fact"),
    "M009": ("BUG", "still SETTLED in market-selection's own ledger. BH009 "
             "refuted it on 2026-08-06: the boundary is a fixed calendar date, "
             "not a 69-day rolling window. LEDGER.md carries the retraction; "
             "the sub-ledger does not."),
    "M010": ("BUG", "the arithmetic consequence of M009 -- the 2026-08-19 "
             "deadline that does not exist. Also still SETTLED in the "
             "sub-ledger."),
    "M011": ("FLOOR", "13 games, one snapshot, a retail book. Corrected in "
             "PREREGISTRATION_DEVIG but PREREGISTRATION.md still calls MLB "
             "'known efficient' on it with no caveat."),
    "M012": (E, "93 fully-quoted three-way events"),
    "M013": (E, "structural: 1.00c median gap against a 6.75c two-venue fee"),
    "M014": (N, "cost comparison fact"),
    "M015": ("DATA", "'deleted, not moved' -- B020 found a live mirror five "
             "days later."),
    "M016": (N, "correctly labelled not-found rather than absent; B020 "
             "answered it"),
    "M017": ("DATA", "football-data.co.uk serves Poland for the Colombian code. "
             "That kills that source for those leagues; it is quoted as though "
             "no closing line exists for them."),
    "M018": (N, "coverage fact"),
    "M019": (N, "SUGGESTIVE, 14 markets per family"),
    "M020": (N, "universe composition fact"), "M021": (N, "API fact"),
    "M022": (N, "SUGGESTIVE"), "M023": (N, "data fact"),
    "M024": (E, "0 of all scanned prop entries carry both sides"),
    "M025": ("DATA", "'unanswerable with free data' after probing one book's "
             "feed. CANCELLED on that basis."),
    "M026": (N, "SUGGESTIVE"),
    "M027": ("DATA", "'No free data source covering ITF tennis was found', "
             "SETTLED, six sources probed. B021 returned 7,786 ITF tournaments "
             "on a free key on 2026-08-06. The sub-ledger still says SETTLED "
             "and SHORTLIST.md still gives it as the reason the exchange's "
             "highest-volume tennis family has no entry."),

    # ---- soccer, merged into the root ledger 2026-08-11 ----------------------
    # The other 39 SO rows live in soccer/LEDGER_SOCCER.md and are deferred.
    "SO041": ("EVIDENCE-PENDING", "the market does not quote the thing the "
              "strategy wanted to buy: at the 89th minute a quote existed 16 "
              "times in 100 and at 97c or better, 1 in 100. Predicted in "
              "writing before it was run, and its own selection canary FAILS "
              "on the has-a-market mask, which is the honest way round. 699 "
              "matches, one reading each. THIS AUDIT HAS NOT VERIFIED IT -- it "
              "is four days old and the folder's other 39 rows are unread."),
    "SO037": (N, "labelled SUGGESTIVE and conditional by its own author -- two "
              "populations, and by SO041 the readings are conditioned on the "
              "match still being in doubt. Not a closure."),

    # ---- bot-hunt -----------------------------------------------------------
    "BH001": (N, "API fact"),
    "BH002": (E, "2,779 esports events, 0 cells above zero, 120 survive "
              "correction and every one is negative"),
    "BH003": (N, "the pre-registered gate firing"),
    "BH004": (N, "cost finding, corrected by BH013"),
    "BH005": (N, "fill-rate finding -- a falsification that failed"),
    "BH006": (N, "BROKEN as evidence; the thread has no verdict"),
    "BH007": (N, "SUGGESTIVE on 13 events, says so itself"),
    "BH008": (N, "market-composition fact"),
    "BH009": (N, "retention fact; refutes M009"),
    "BH010": ("NARROW", "kills the South American soccer families on "
              "RETRIEVABLE KALSHI EVENTS (152 against a 481 bar). That is a "
              "statement about Kalshi's tape, not about soccer, and free "
              "historical soccer data goes back a decade."),
    # CORRECTED 2026-08-09 by the devig chat. My original note repeated the
    # vig-bound argument -- "the cost bar is larger than the entire vig it
    # removes" -- which devig had RETRACTED on 2026-08-07, before I wrote it.
    # The overround is what you STRIP to estimate fair value; it does not bound
    # the edge. If Kalshi's ask sat 8c below de-vigged fair, the edge would be
    # 8c on a 2pp-overround market. An audit that hardens a retracted claim is
    # the one failure this exercise cannot afford, and I did it.
    # The CONCLUSION survives on a measurement, which is what to quote:
    # 1,460 paired observations on 30 games, largest venue disagreement
    # anywhere 2.77c against a 2.75c cost.
    "BH011": (E, "closed on a measurement -- 1,460 paired observations on 30 "
              "games, largest venue disagreement 2.77c against a 2.75c cost. "
              "NOT on the vig-bound argument, which devig retracted 2026-08-07 "
              "and which this audit wrongly repeated."),
    "BH012": (N, "time-field fact"), "BH013": (N, "correction"),
    "BH014": ("BUG", "the recorder probed the first 60 tickers in Kalshi's "
              "undocumented listing order while the family listed 85-104. "
              "Fixed 2026-08-06. Which earlier conclusions read that "
              "truncated output has not been stated anywhere."),

    # ---- chat archive -------------------------------------------------------
    **{f"CH{i:03d}": (N, "retraction") for i in range(1, 21)},
    "CH021": (N, "BROKEN, unresolved"), "CH022": (N, "BROKEN, unresolved"),
    "CH023": (N, "SUGGESTIVE"), "CH024": (N, "SUGGESTIVE"),
    "CH025": (N, "UNVERIFIED, n=4, self-flagged"),
    "CH026": (N, "UNVERIFIED, n=6"), "CH027": (N, "UNVERIFIED, eyeballed"),
    "CH028": (N, "BROKEN by construction, self-flagged"),
    "CH029": (N, "BROKEN, rests on CH022"),
    "CH030": (N, "structural fact"),
    "CH031": (E, "a bug that correctly voided results rather than manufacturing "
              "a null; B008 later measured it at 97.4%"),
    "CH032": (N, "root cause"), "CH033": (N, "reconciliation"),
    "CH034": (N, "fee fact"),
    "CH035": (N, "an open gap, correctly labelled -- and still only partly "
              "filled: tennis (S008) yes, esports BROKEN (BH006), crypto one "
              "week of tape"),
    "CH036": (N, "arithmetic on assumed inputs"),
    "CH037": (N, "UNVERIFIED, flagged twice"),
    "CH038": (N, "SUGGESTIVE, unit-of-observation caveat"),
    "CH039": (N, "SUGGESTIVE"), "CH040": (N, "UNVERIFIED"),
    "CH041": (N, "SUGGESTIVE, n=27"), "CH042": (E, "break-even arithmetic"),
    "CH043": (N, "SUGGESTIVE"), "CH044": (N, "bug, later diagnosed"),
    "CH045": (N, "SUGGESTIVE"), "CH046": (N, "UNVERIFIED assertion"),
    "CH047": (N, "API fact"), "CH048": (N, "API fact"),
    "CH049": (N, "dedupe fact"), "CH050": (N, "spread fact"),
    "CH051": (N, "settlement fact"), "CH052": (N, "fee bug, fixed"),
    "CH053": (N, "look-ahead bug caught during construction"),
    "CH054": (N, "SUGGESTIVE, n~100, caveated"),
    "CH055": (N, "structural confound"), "CH056": (N, "logical"),
    "CH057": (N, "was UNVERIFIED; B010 replayed it at 481 configurations. The "
              "ledger row is stale, not wrong."),
    "CH058": (N, "random-entry control"),
    "CH059": (N, "coverage fact"), "CH060": (N, "= T002"),
    "CH061": (N, "= T003"), "CH062": (N, "sanity check"),
    "CH063": (N, "= T004"), "CH064": (N, "= T005"), "CH065": (N, "= T006"),
    "CH066": (N, "= T007, retracted"), "CH067": (N, "= T015"),
    "CH068": (N, "= T009"), "CH069": (N, "= T014"), "CH070": (N, "= T011"),
    "CH071": (N, "= T012"), "CH072": (N, "= T013"),
    "CH073": (N, "= T018"),
    "CH074": ("NARROW", "set-score and parlay markets were closed by an "
              "arithmetic argument on one worked example. The residual test it "
              "proposed at executable prices was never run."),
    "CH075": (E, "benchmark inflation, demonstrated"),
    "CH076": (N, "SUGGESTIVE, test proposed and never run"),
    "CH077": (N, "UNVERIFIED, self-scored"),
    "CH078": (N, "API fact"), "CH079": (N, "universe fact"),
    "CH080": (N, "= K013"), "CH081": (N, "cost fact"),
    "CH082": (N, "= C020"), "CH083": (N, "= K012"),
    "CH084": (N, "screen finding"),
    "CH085": (N, "openly UNVERIFIED as an edge claim -- this is the weather "
              "gate that is still unmeasured"),
    "CH086": (N, "machinery built, never run at real n. Still true for weather."),
    "CH087": (N, "= C024"), "CH088": (N, "self-report"),
    "CH089": (N, "fee arithmetic"), "CH090": (E, "martingale killed by arithmetic"),
    "CH091": (N, "process incident"),
    "CH092": (N, "UNVERIFIED clustering concern; superseded by W011"),
    "CH093": (N, "definition error found"),
    "CH094": (E, "direction settled, magnitude correctly left SUGGESTIVE"),
    "CH095": (N, "UNVERIFIED vendor figure"),
    "CH096": (N, "sound argument; the test it proposed became W001-W005"),
    "CH097": (E, "follows from CH005 + CH094 and is corroborated by W003-W005"),
    "CH098": (N, "export fact"), "CH099": (N, "arithmetic"),
    "CH100": (N, "export fact"),
    "CH101": (E, "the width of the interval IS the finding -- structurally "
              "unauditable"),
    "CH102": (N, "UNVERIFIED, n=4"), "CH103": (N, "SUGGESTIVE, n=4"),
    "CH104": (N, "SUGGESTIVE mechanism"), "CH105": (N, "arithmetic"),
    "CH106": (N, "SUGGESTIVE, n=2"), "CH107": (N, "SUGGESTIVE"),
    "CH108": (N, "measured on real cards"), "CH109": (N, "SUGGESTIVE, n=10"),
    "CH110": (N, "content fact"),
    "CH111": (N, "never tested for edge at all -- the thread stopped without a "
              "verdict rather than with a wrong one"),
    "CH112": (N, "SUGGESTIVE"), "CH113": (N, "UNVERIFIED, n=3"),
    "CH114": (N, "trade fact"), "CH115": (N, "arithmetic"),
    "CH116": (E, "exit arithmetic"), "CH117": (N, "the tail is untested"),
    "CH118": (N, "platform fact"), "CH119": (N, "SUGGESTIVE, n=3"),
    "CH120": (N, "UNVERIFIED, self-reported one day"),
    "CH121": (N, "two live patterns that cannot both be an edge; the test was "
              "never run"),
    "CH122": (N, "the question was asked and the answer is literally missing "
              "from the export. Never opened rather than wrongly closed."),
    "CH123": (N, "caution, consistent with T004"),
    "CH124": (N, "process finding"), "CH125": (N, "process fact"),
    "CH126": (N, "process fact"), "CH127": (N, "power arithmetic"),
    "CH128": (N, "power arithmetic"),
}

INPLAY_FILE = "kalshi-inplay-bot/audit/LEDGER.md"

# The live-money bot's own audit, 122 claims, read 2026-08-11 on mailbox 002.
#
# It carries its OWN C001-C117 numbering, which collides with `crypto`'s: 34
# ids mean two different claims depending on which file you are in. `crypto`
# C010 is "no model beats the Kalshi mid" on 250 events; this C010 is "a player
# model lost to the bookmaker". Keyed separately for that reason -- and until
# today THIS TOOL had the bug, silently applying crypto's calls to 27 of these
# rows. `idea.py` searches the same merged view and has the same exposure.
C_INPLAY: dict[str, tuple[str, str]] = {

    # -- P1, the live tennis bot ---------------------------------------------
    "C001": (E, "14,162 settled markets = 7,081 matches, 60/40 holdout touched "
             "once, random-entry control, slippage sweep. -9c against a ~4c "
             "cost base, so the conclusion is arithmetic."),
    "C002": (N, "the only positive number in P1, openly a train-set point "
             "estimate with no interval"),
    "C003": (E, "within-sample paired, consistent on holdout"),
    "C004": (N, "cost arithmetic from 2.94M live candles"),
    "C005": (N, "UNVERIFIED prose, no fill model"),
    "C005b": (N, "UNVERIFIED, code corroborated -- R6 records it re-run "
              "2026-08-05 into bot-forensics/out/"),
    "C005c": (N, "same, re-run 2026-08-05"),
    "C005d": (N, "a look-ahead trap caught, not a closure"),
    "C006": (E, "the holdout was touched once and all three tuned configs "
             "degraded 3.5-4.3c"),
    "C007": (N, "sensitivity fact"),
    "C008": (N, "a statement about the backtest; whether the live bot honours "
             "it is openly not established"),
    "C009": ("DATA", "'Kalshi tracks Betfair at r=0.9878, MAD 1.95c' is marked "
             "UNVERIFIED -- 'no Betfair data, script or output anywhere on this "
             "machine'. THE ARTIFACT EXISTS: it is T012 in the root ledger, "
             "n=809, SETTLED, same numbers. Resolvable by cross-reference. And "
             "it is load-bearing -- the stated reason to expect no "
             "favourite-longshot bias on Kalshi."),
    "C010": ("DATA", "'a player model lost to the bookmaker, Brier 0.2249 vs "
             "0.2057, n=2,645', artifact NONE. It is T006, SETTLED, same "
             "numbers. Resolvable by cross-reference."),
    "C011": ("FLOOR", "THE LIVE BOT'S PRIMARY ENTRY GATE, fitted to 125 real "
             "settled markets split into 5 price buckets -- about 25 "
             "observations each. Already BROKEN, and the bot is configured for "
             "real money (C108)."),
    "C012": ("FLOOR", "the stop width, from a 'smooth optimum' across 137 "
             "matches where the whole range across all widths is 2.3c. The "
             "optimum is inside the noise band -- the same failure the "
             "backtest's own Step 6 identified."),
    "C013": (N, "UNVERIFIED, probably computable from views.pkl"),
    "C014": (N, "UNVERIFIED"),
    "C015": (N, "a safety fact, flagged as deserving a code read"),
    "C016": (N, "a single incident"),
    "C017": (N, "11 files of preserved input, method and conclusion lost"),

    # -- P2, the exchange-wide scan ------------------------------------------
    "C018": (N, "API fact"), "C019": (N, "fee correction"),
    "C020": (N, "structural fact"), "C021": (N, "arithmetic"),
    "C022": (N, "API fact"), "C023": (N, "flow composition fact"),
    "C024": (N, "exchange fact"), "C025": (N, "rate limit"),
    "C026": (N, "the power arithmetic that kills most of the exchange"),
    "C027": (E, "and it states its own floor correctly: 'a null at n=25 "
             "markets, i.e. very low power. It rules out a large edge, not an "
             "edge.' This is how a category-4 row should read."),
    "C028": (N, "retracted, and the file carries its own caveat field"),
    "C029": (N, "retracted -- and still live in GO_NO_GO.md"),
    "C030": (N, "the corrected version, small n, labelled SUGGESTIVE"),
    "C031": (E, "102,716 candles; statistically real, economically dead"),
    "C032": (E, "21 lags tested jointly"),
    "C033": (N, "descriptive, well powered"),
    "C034": (E, "a pre-specified prediction that failed and was reported as "
             "failing"),
    "C035": (N, "shape confirmation, not an edge"),
    "C036": (N, "count BROKEN, conclusion SETTLED -- 2 distinct violations "
             "counted 55 times, and the meta file said 17 while the prose said "
             "52. Self-caught by this audit."),
    "C037": (E, "phantom arb caught by a tiling check plus a regression test"),
    "C038": (E, "independent corroboration from a different codebase"),
    "C039": (N, "SUGGESTIVE, and the interval is openly called narrower than "
             "the data supports"),
    "C040": (N, "retracted, self-caught"),
    "C041": (N, "SUGGESTIVE and openly contradicted by C064/C077"),
    "C042": ("DATA", "the +7.05pp price-band claim whose location is recorded "
             "as literally 'inline'. THIS IS THE THIRD COPY of K015 = W011, "
             "which wallet-copy-study recomputed from scratch at +2.09pp and "
             "-0.29pp net. Two projects had already killed it; this one still "
             "carries it as the claim that reframes its whole copy-trading "
             "thread."),
    "C043": (N, "SUGGESTIVE, bucket ns are positions not settlements"),
    "C044": (N, "a definition error found"),
    "C045": (N, "a self-limiting caveat"),
    "C046": (N, "point estimate sound, interval must be match-clustered"),
    "C047": (N, "retracted, self-caught"),
    "C048": (N, "retracted, self-caught"),
    "C049": (N, "retracted -- and still live in GO_NO_GO.md:87-90"),
    "C050": (E, "an honest reversal of an over-promise, stating its own power: "
             "bucket ranges +/-11-29 out of 100, 0 of 7 Polymarket values "
             "excluded"),
    "C051": (N, "correctly worded as 'no positive evidence', not 'refuted'"),
    "C052": (E, "1,376 settled markets, residual against price, correct unit. "
             "The best-powered null in P2."),
    "C053": (E, "structural -- no account identifier, so identity-level copy "
             "trading on Kalshi is impossible. Closes a whole family."),
    "C054": (N, "descriptive corroboration"),
    "C055": (N, "a clever ground-truth fact"),
    "C056": (E, "strict time split, leak assertion, clustered bootstrap over "
             "settlement hours, after the 8,090 correction"),
    "C057": (N, "retracted -- and still live in shortlist.md:113"),
    "C058": (N, "the correction that reframes the weather thread"),
    "C059": (N, "retracted -- and still live in shortlist.md and GO_NO_GO.md"),
    "C060": (N, "SUGGESTIVE; the depth half rests on ~12 snapshots and the "
             "author says so"),
    "C061": ("NARROW", "'whether the weather model beats the mid is unmeasured "
             "and blocked' -- while C096, in another project a week earlier, "
             "measured a weather model against market ASKS and it LOST. "
             "Different family and benchmark, so not a refutation. But the "
             "root audit calls this the largest unexplored lead in the repo, "
             "and neither it nor P2 cites C096."),
    "C062": (N, "volume fact, self-corrected"),
    "C063": (N, "prose says 3 positive-control detections, the JSON says 2. "
             "PASS survives either way."),
    "C064": (E, "self-caught mis-specification; adding a positive control "
             "unprompted is the best methodological decision in the corpus"),
    "C065": (N, "unit error caught by an assertion"),
    "C066": ("BUG", "THE ORDERBOOK PARSER UNWRAPPED A NON-EXISTENT 'orderbook' "
             "KEY -- diagnosed, quarantined and regression-tested here on "
             "2026-07-30. THIS IS THE SAME BUG AS M001, which market-selection "
             "re-discovered on 2026-08-02 and 'independently reproduced on 85 "
             "markets', and which then blocked the crypto market-making thread "
             "for six days. The fix was already on disk with 9 tests."),
    "C067": (N, "internally inconsistent FDR claim, flagged"),
    "C068": (E, "116 hypotheses, zero tradeable edges -- the headline"),

    # -- P3, Polymarket tennis copy trading ----------------------------------
    "C069": (N, "retracted, self-caught"),
    "C070": (N, "an operational rule, not a measured relationship"),
    "C071": (E, "structural"),
    "C072": (E, "split-sample plus thousands of random re-deals -- it "
             "simulates the SCREEN, not the strategy. The best-designed test "
             "in the corpus."),
    "C073": (N, "a multiple-comparisons decision"),
    "C074": (E, "the luck bar depends on the pool it is computed over -- "
             "tightening a gate flipped a wallet from fail to pass with no "
             "record changing"),
    "C075": (E, "tripled the data and every candidate got worse"),
    "C076": (E, "volume and directionality are anti-correlated"),
    "C077": (E, "42,652 wallets, one match = one call, 0 BH discoveries at 5% "
             "and 10%, and FEWER p<0.05 wallets than chance predicts. The "
             "strongest negative result in the entire corpus."),
    "C078": (E, "the luck bar FELL as the sweep grew -- the signature of noise"),
    "C079": (E, "the edge is real and dies inside 15 seconds, with the null "
             "expectation computed per delay"),
    "C080": (N, "three sample-size errors found and fixed"),
    "C081": (N, "SUGGESTIVE and explicitly below its own pass mark"),
    "C082": ("BUG", "KNOWN AND UNFIXED: the follower model disagrees with the "
             "wallet's own outcome on 42.4% of traded-out positions, and one "
             "affected wallet (33.7%) is IN THE FROZEN FOLLOW LIST while the "
             "forward verdict is pooled. One contaminated wallet in four "
             "corrupts it. Must be fixed before the forward record is scored."),
    "C083": ("BUG", "KNOWN AND UNFIXED: holding_seconds measures entry to a "
             "metadata finalisation timestamp -- 160 hours on single matches. "
             "Contaminates 100% of the headline candidate's record."),
    "C084": (N, "UNVERIFIED, openly unaudited"),
    "C085": (N, "verified API constraints"),
    "C086": (E, "correctly refuses to over-read its own null -- 823 of 1,164 "
             "observations come from 1-minute bars that cannot resolve "
             "sub-minute differences"),
    "C109": (E, "removing the top 5% of trades collapses ROI to zero or "
             "negative for all six finalists"),
    "C110": (E, "the tail-risk trap: two losses in 181 trades, one loss "
             "erasing 13.9 wins, while looking excellent on three metrics"),
    "C111": (E, "convexity bias in mean-of-ROI, demonstrated by trimming"),
    "C112": (N, "three defects, all flattering results"),
    "C113": (E, "states its own limitation -- every historical copyable-ROI "
             "figure is unfillability-tested"),
    "C114": (N, "n=1 but structural"),
    "C115": (E, "survivorship is not corrected and cannot be, said plainly"),
    "C116": (N, "a design, with no drift event yet reviewed"),

    # -- P4, PTIS -------------------------------------------------------------
    "C087": (N, "the report labels itself 'insufficient evidence' and refuses "
             "the positive cells"),
    "C088": ("FLOOR", "'Broad leaderboard consensus copying is REJECTED' -- on "
             "0 accepted resolved entries in all five niches. The ledger says "
             "so itself: 'the main setting is a null-by-no-data.' A rejection "
             "with no measurement under it. The unfiltered crypto control "
             "losing $40.17 on $40 is real; the headline is not."),
    "C089": (N, "SUGGESTIVE at n=26, and it independently corroborates C079"),
    "C090": (E, "invalidated runs excluded and preserved -- the best "
             "experiment hygiene in the corpus"),
    "C091": (N, "nothing claimed"),
    "C092": (N, "data-quality checks"),

    # -- P5, weather ----------------------------------------------------------
    "C093": (E, "47,163 of 47,187 contracts resolve exactly as the official "
             "observation says"),
    "C094": (N, "a leak-resistant pipeline design"),
    "C095": (N, "engineering, explicitly not proof of tradeable profit"),
    "C096": (E, "THE GATE FAILED: model 0.204805 vs market-ask 0.168963 on 600 "
             "contracts, sealed test. The most consequential single result in "
             "the corpus for weather -- and no other project references it."),
    "C097": (E, "an event-clustered bootstrap, the correct unit, and the gate "
             "does not pass"),
    "C098": (N, "SUGGESTIVE and explicitly overridden by C096"),
    "C099": (E, "all five exit policies lost on 28 independent events; the "
             "7-event validation gain was rejected as a small-sample anomaly"),
    "C100": (E, "three structurally different methods, all negative, against a "
             "pre-declared gate"),
    "C101": (E, "the decision that follows"),
    "C102": (N, "a forward design with a stated promotion rule"),

    # -- P6 and cross-cutting -------------------------------------------------
    "C103": (N, "the export exists and what it contains"),
    "C104": (N, "NEVER ATTEMPTED -- 'the largest completely untested item in "
             "the corpus'. Not a wrong closure; a thread never opened, and it "
             "is the same one as CH111."),
    "C105": ("NARROW", "TWO DIFFERENT TENNIS COST BARS ARE IN CIRCULATION. P2 "
             "uses 2.4c throughout and reports intervals that 'exclude the "
             "2.4c bar'; P1 measured 4.14c on real books. Conclusions phrased "
             "as 'clears the 2.4c bar' do not clear 4.14c, and the "
             "price-matched copy-trading result clears 4.14 only marginally. "
             "A THIRD bar now exists: tennis measured 4.79c forward on "
             "2026-08-09."),
    "C106": (N, "SETTLED for momentum, UNVERIFIED for buy-high and maker"),
    "C106b": ("DATA", "'Kalshi tennis prices are calibrated to +/-2.1c in every "
              "5c bucket, and cheap underdogs are slightly OVERpriced' -- no "
              "artifact preserved. P2 spent a whole session on exactly this "
              "question (C049/C050) without knowing a prior tennis-specific "
              "measurement existed. B027 later answered it properly."),
    "C106c": ("NARROW", "THE BIGGEST LIVE THREAD HERE, AND THE LEDGER NAMES IT "
              "ITSELF: 'this reframes every negative result in P1. All of "
              "C001-C007 concern PRICE-VISIBLE information, which the market "
              "prices correctly. None of it tests whether the market prices "
              "the SCORE correctly.' The forward tape built to test it ran for "
              "two days and stopped."),
    "C107": (N, "the fee float-dust defect, since consolidated repo-wide"),
    "C117": ("DATA", "'whether the tennis series sit inside the 124 maker-fee "
             "series is unrecorded anywhere and is the cheapest open question "
             "in the corpus'. IT IS RECORDED: S010 (maker fee zero on "
             "Challenger/ITF, 91% of the book), M008 (78 of 3,074 series) and "
             "S025 (the two maker-fee tennis series hold 34.4% of volume on "
             "5.8% of markets). Answered three times over, in another folder."),
    "C108": (N, "a configuration fact -- and the reason C011 and C012 matter"),
}

ACTION_INPLAY: dict[str, tuple[str, str, str, str]] = {
    "C011": ("REOPEN", "nobody",
             "The live bot's entry gate is fitted to ~25 observations a bucket "
             "and the bot is configured for real money. Either re-derive it on "
             "the 14,162-market tape that already exists, or turn the gate "
             "off. Trading is currently OFF, so this is not urgent -- it is a "
             "trap laid for whoever turns it back on.",
             "one re-run against data on disk"),
    "C012": ("REOPEN", "nobody",
             "Same for the 38c stop width: 137 matches, 2.3c of range across "
             "every width tested. Re-derive or drop it.",
             "one re-run"),
    "C066": ("RELABEL", "coordinator",
             "Record in the root LEDGER.md that M001's bug was already "
             "diagnosed, quarantined and regression-tested here on 2026-07-30 "
             "-- three days before it was re-discovered, and six days before "
             "it stopped blocking crypto. The lesson is about discoverability, "
             "not about the bug.",
             "minutes"),
    "C082": ("REOPEN", "nobody",
             "The follower model disagrees with the wallet's own outcome on "
             "42.4% of traded-out positions, and a contaminated wallet sits in "
             "the frozen follow list feeding a POOLED forward verdict. Fix "
             "before that record is ever scored.",
             "a fix, then a rescore"),
    "C083": ("RELABEL", "nobody",
             "holding_seconds is entry-to-finalisation, not entry-to-match-end. "
             "Mark every hold-duration figure in P3 as contaminated.",
             "minutes"),
    "C088": ("RELABEL", "nobody",
             "Rewrite 'consensus copying is REJECTED' as 'produced no data' -- "
             "0 accepted resolved entries is not a rejection. The crypto "
             "control result stands on its own and should carry the sentence.",
             "minutes"),
    "C009": ("RELABEL", "coordinator",
             "Point the row at T012 in the root ledger, which is the artifact "
             "it says does not exist.",
             "minutes"),
    "C010": ("RELABEL", "coordinator",
             "Point the row at T006.",
             "minutes"),
    "C042": ("RELABEL", "coordinator",
             "Mark it RETRACTED and point at W011 / K015. Two projects had "
             "already killed this number before this row was written.",
             "minutes"),
    "C106b": ("RELABEL", "tennis",
              "Point at B027, which measured Kalshi tennis calibration "
              "properly on 6,519 events.",
              "minutes"),
    "C117": ("RELABEL", "devig",
             "Answer the 'cheapest open question in the corpus' by pointing at "
             "S010, S025 and M008.",
             "minutes"),
    "C061": ("REOPEN", "devig",
             "Before spending a recorder on weather-versus-the-mid -- the root "
             "audit's top-ranked item -- read C096. A different project scored "
             "a weather model against market asks on 600 sealed contracts and "
             "LOST (0.2048 vs 0.1690), and its blend gate failed an "
             "event-clustered bootstrap. Different family and benchmark, so it "
             "does not settle the question. It changes the prior.",
             "a reading pass before a recorder job"),
    "C105": ("RELABEL", "coordinator",
             "Three tennis cost bars are now in circulation -- 2.4c, 4.14c and "
             "4.79c. Say which applies where, once, somewhere central.",
             "minutes"),
    "C106c": ("REOPEN", "tennis",
              "The real thesis -- price diverges from score -- has never been "
              "tested, and the ledger says every negative result in P1 is "
              "about price-visible information only. The forward tape built "
              "for it ran two days. tennis-paper-forward is now recording live "
              "matches with a brief per match, which is the same shape.",
              "a design question, then forward time"),
}

REOPEN_CATS = {"BUG", "DATA", "NARROW", "FLOOR"}

# ---------------------------------------------------------------------------
# DEFERRED -- claims this audit has NOT read, named out loud.
#
# On 2026-08-09 the coordinator fixed `ledger.py` (commit aaf5e06) after this
# chat reported it was reading 3 of the 5 files it listed. It now reads SIX and
# returns 596 rows / 538 distinct claims, against the 342 / 313 the first pass
# audited. `idea.py` -- the tool that exists so nobody says "we tried that"
# from memory -- had been blind to 43% of the archive.
#
# That is good news, and it leaves 225 claims unaudited. They are listed here
# rather than quietly dropped: the coverage check still FAILS on a claim that
# is neither classified nor from a file named below, so the only way to leave
# something out is to write down that you did and why.
# Parser noise, not claims. The widened parse picks up the FIRST COLUMN of two
# prose tables in LEDGER.md as if it were a claim id -- the M011 "eight places"
# citation table at line 494, whose first column is a filename, and the grouped
# retraction row that carries CH001-CH020 by reference (all twenty of which are
# classified individually). Reported to `coordinator`: it means the new
# 596/538 headline is overstated by five.
NOISE: dict[str, str] = {
    "where": "header cell of the M011 citation table, LEDGER.md:494",
    "PREREGISTRATION.": "filename cell in that table",
    "PREREGISTRATION_": "filename cell in that table",
    "RESULTS_CROSSVEN": "filename cell in that table",
    "PRIOR_ART.md, SH": "filename cell in that table",
    "CH001–CH020": "a grouping row; all twenty are classified individually",
}

DEFERRED: dict[str, str] = {
    # kalshi-inplay-bot/audit/LEDGER.md was deferred on 2026-08-09 and is now
    # AUDITED -- see C_INPLAY above.
    "set1_overshoot/HYPOTHESIS_LEDGER.md":
        "the full 97-row set-1 hypothesis grid. Newly readable 2026-08-09. "
        "Expect heavy overlap with S001-S025, which are audited.",
    "soccer/LEDGER_SOCCER.md":
        "43 rows, and they appeared BETWEEN this pass and the last one. The "
        "soccer chat created this file on 2026-08-09 in answer to this audit, "
        "and the coordinator has since added it to SUB_LEDGERS -- so the "
        "prior-work check can finally see soccer. Unaudited, and it is the "
        "obvious next pass: it is the newest work in the repo and the one "
        "folder whose claims have never been cross-checked against anything.",
    "crypto/HYPOTHESIS_LEDGER.md":
        "27 rows. Expect heavy overlap with C001-C027, which are audited.",
}

# For every claim NOT closed on evidence: what to actually do about it.
#
#   RELABEL  the measurement is fine or unfixable; the ROW is wrong. No test is
#            re-run. Someone rewrites a sentence so the next reader is not
#            misled. Cheap, and it is most of them.
#   REOPEN   there is a real question here that the closure did not answer, and
#            a specific thing would answer it.
#
# owner is the chat that owns the folder, from coordinator/chats.json. This
# chat writes NOTHING in those folders -- it files mail.
ACTION: dict[str, tuple[str, str, str, str]] = {
    # id: (action, owner, what would settle it, how long)
    "M027": ("REOPEN", "devig",
             "Strike the SETTLED absence claim and re-rank the tennis families. "
             "B021 already made the call that refutes it -- nothing needs "
             "running, but the shortlist decision does need remaking.",
             "an afternoon"),
    "S023": ("REOPEN", "tennis",
             "Re-run p2_fade.py on the outcome-independent dedupe. Half of 'no "
             "edge in either direction' currently rests on a void event set.",
             "one re-run"),
    "S022": ("REOPEN", "tennis",
             "Re-run the retirement add-back on the clean universe.",
             "one re-run"),
    "S021": ("REOPEN", "tennis",
             "Count how many matches the forward recorder has accumulated since "
             "2026-08-01 and re-run the primary test if it clears ~3,970.",
             "one count, then one re-run"),
    "C023": ("REOPEN", "devig",
             "Same tape pull as C022. Then rewrite the row: 40 of 44 price "
             "cells are ties, not 'negative'.",
             "shares C022's pull"),
    "T002": ("REOPEN", "tennis",
             "The $9.99 point-by-point history covering 43 months including "
             "ITF. It replaces the frozen source that ends 2026-06-02 and it "
             "re-powers B023 at the same time.",
             "$9.99 and one rebuild"),
    "S018": ("REOPEN", "tennis",
             "✅ PAID 2026-08-09. tennis-data.co.uk publishes one workbook PER "
             "SEASON carrying games won by each player in every set -- free, "
             "reaching back years, so the +/-7-day objection that closed this "
             "never applied. 1,062 labels on S006's own window against the 479 "
             "it used. REFUTED, not resolved: main tour only against a 73-87% "
             "ITF pool, and it moves the smallest visible effect 9.9 -> 6.6 "
             "against a 3.61 bar.",
             "done -- the join and the ITF gap remain"),
    "M017": ("RELABEL", "soccer",
             "WITHDRAWN. soccer/data-sources.md had already probed thirteen "
             "sources with content hashes, and the comeback table does not use "
             "that website at all -- Colombia is one of its best-covered "
             "competitions, 4,808 fixtures. My reopen was wrong twice over.",
             "nothing"),
    "M025": ("REOPEN", "devig",
             "One book's free feed was one-sided, so props were CANCELLED as "
             "unanswerable. Check whether any other free feed publishes both "
             "sides.",
             "a few hours"),
    "C016": ("REOPEN", "devig",
             "Re-check two-sidedness of the far wings across many days rather "
             "than the 61 minutes of 2026-08-01 that closed it.",
             "one query over recorded books"),
    "CH074": ("REOPEN", "tennis",
              "⚠ MY 'blocked, zero markets' CALL WAS WRONG. I probed "
              "KXATPTOTALSETS (genuinely empty) and generalised to the whole "
              "idea -- an absence claim from one query, in an audit about "
              "absence claims from too few sources. KXATPSETWINNER has 112 "
              "open and 200+ settled; KXWTASETWINNER 104 and 200+. Runnable "
              "historically AND forward on tennis's live recorder.",
              "one analysis run; forward version needs the user's OK because "
              "it widens a running pre-registered test"),
    "BH014": ("REOPEN", "devig",
              "State which earlier bot-hunt conclusions read the truncated "
              "60-ticker recorder output before it was fixed on 2026-08-06.",
              "a reading pass"),

    "S005": ("RELABEL", "tennis",
             "The row already prints its own detectable-effect range. Move the "
             "status from 'SETTLED (null)' to 'unmeasured at this sample'.",
             "minutes"),
    "S006": ("RELABEL", "tennis", "Same as S005, and the gap is wider.", "minutes"),
    "B023": ("RELABEL", "tennis",
             "The project's own wording is right and the ledger's is not. Copy "
             "the project's sentence into the row.",
             "minutes"),
    "K001": ("RELABEL", "devig",
             "Say '25 markets could not resolve it' rather than 'no model "
             "beats the mid'. The family is dead on structure anyway (K013).",
             "minutes"),
    "K012": ("RELABEL", "devig",
             "'Killed on recurrence' means it can never be measured, not that "
             "there is no edge. Two different sentences.",
             "minutes"),
    "M011": ("RELABEL", "devig",
             "PREREGISTRATION.md still calls MLB 'known efficient' on 13 games "
             "against a retail book, with no caveat. Its sibling file was "
             "corrected on 2026-08-06; this one was not.",
             "minutes"),
    "M009": ("RELABEL", "devig",
             "BH009 refuted it. LEDGER.md carries the retraction; "
             "market-selection's own ledger still says SETTLED.",
             "minutes"),
    "M010": ("RELABEL", "devig", "Same as M009 -- and it removes a deadline "
             "that does not exist.", "minutes"),
    "M015": ("RELABEL", "devig", "B020 found a live mirror.", "minutes"),
    "C025": ("RELABEL", "devig",
             "The 2026-08-07 run covers all four series. The row still says "
             "only one was ever tested.",
             "minutes"),
    "T003": ("RELABEL", "tennis", "B020 already corrected it in LEDGER.md; the "
             "project's own docs still say gone.", "minutes"),
    "T018": ("RELABEL", "tennis",
             "Say 'cannot be modelled from Sackmann' -- which is what was "
             "measured -- not 'cannot be modelled'.",
             "minutes"),
    "C001": ("RELABEL", "devig", "Say '10.5 minutes'. K007's 9 hours is the "
             "sentence to quote.", "minutes"),
    "C002": ("RELABEL", "devig", "Same window.", "minutes"),
    "BH010": ("RELABEL", "devig",
              "Scope it to Kalshi's retrievable tape. Free historical soccer "
              "results go back a decade and the soccer chat is using them now.",
              "minutes"),
    "B015": ("RELABEL", "signal",
             "An absence from two corpora. It gates nothing, so the only cost "
             "is someone quoting it as a census.",
             "minutes"),
}


def main() -> int:
    rows, files, _ = ledger.all_rows()
    OUT.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    out = []
    missing = []
    deferred: list[tuple[str, str]] = []
    noise: list[str] = []
    for r in rows:
        rid = (r.get("_id") or "").strip()
        key = (r.get("_file", ""), rid)
        if key in seen:
            continue
        seen.add(key)
        src = r.get("_file", "")
        table = C_INPLAY if src == INPLAY_FILE else C
        if rid not in table:
            if rid in NOISE:
                noise.append(rid)
            elif src in DEFERRED:
                deferred.append((rid, src))
            else:
                missing.append(rid)
            continue
        cat, note = table[rid]
        acts = ACTION_INPLAY if src == INPLAY_FILE else ACTION
        act, owner, settle, cost = acts.get(rid, ("", "", "", ""))
        out.append({
            "id": rid,
            "category": cat,
            "action": act,
            "owner": owner,
            "ledger_status": ledger.status_of(r),
            "project": ledger.project_of(r),
            "file": r.get("_file", ""),
            "claim": ledger.claim_of(r)[:160],
            "note": note,
            "what_would_settle_it": settle,
            "how_long": cost,
        })

    seen_ids = {i for _, i in seen}
    extra = sorted(set(C) - seen_ids)
    unactioned = sorted(
        rid for tbl in (C, C_INPLAY) for rid, (cat, _) in tbl.items()
        if cat in REOPEN_CATS and rid not in ACTION
        and rid not in ACTION_INPLAY)
    orphan_actions = sorted((set(ACTION) - set(C))
                            | (set(ACTION_INPLAY) - set(C_INPLAY)))

    if missing or extra or unactioned or orphan_actions:
        print("COVERAGE FAILURE -- the audit does not cover every claim.")
        if missing:
            print(f"  claims with no classification ({len(missing)}): {missing}")
        if extra:
            print(f"  classifications with no claim ({len(extra)}): {extra}")
        if unactioned:
            print(f"  not closed on evidence and no action stated "
                  f"({len(unactioned)}): {unactioned}")
        if orphan_actions:
            print(f"  actions for unknown claims: {orphan_actions}")
        return 1

    path = OUT / "classification.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    counts: dict[str, int] = {}
    for r in out:
        counts[r["category"]] = counts.get(r["category"], 0) + 1

    print("files read:")
    for f in files:
        print("  ", f)
    print(f"\ndistinct claims in the ledgers: "
          f"{len(out) + len(deferred)}   (coverage check PASSED)")
    print(f"  audited                      {len(out)}")
    print(f"  DEFERRED, named not dropped  {len(deferred)}")
    for f in DEFERRED:
        n = sum(1 for _, s in deferred if s == f)
        print(f"     {n:4d}  {f}")
    print(f"  parser noise, not claims     {len(noise)}\n")
    order = [N, E, "EVIDENCE-PENDING", "FLOOR", "DATA", "NARROW", "BUG"]
    for k in order:
        print(f"  {counts.get(k, 0):4d}  {k}")
    closures = sum(counts.get(k, 0) for k in order if k != N)
    reopens = sum(counts.get(k, 0) for k in REOPEN_CATS)
    n_reopen = sum(1 for r in out if r["action"] == "REOPEN")
    n_relabel = sum(1 for r in out if r["action"] == "RELABEL")
    print(f"\n  closures examined          {closures}")
    print(f"  closed on evidence         {counts.get(E, 0)}"
          f"   ({100 * counts.get(E, 0) / closures:.0f}% of closures)")
    print(f"  closed on something else   {reopens}")
    print(f"     of which REOPEN         {n_reopen}   (a test to re-run)")
    print(f"     of which RELABEL        {n_relabel}   (a sentence to rewrite)")
    by_owner: dict[str, int] = {}
    for r in out:
        if r["action"] == "REOPEN":
            by_owner[r["owner"]] = by_owner.get(r["owner"], 0) + 1
    print("\n  reopens by owning chat: " +
          ", ".join(f"{k} {v}" for k, v in sorted(by_owner.items())))
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
