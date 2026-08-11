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
    "set1_overshoot/HYPOTHESIS_LEDGER.md":
        "the full 97-row set-1 hypothesis grid. Newly readable 2026-08-09. "
        "Expect heavy overlap with S001-S025, which are audited.",
    "kalshi-inplay-bot/audit/LEDGER.md":
        "122 rows, and the highest-value of the three -- it is the live-money "
        "bot's own audit. The first pass named this file as one the parser did "
        "not read; it is now readable and still unaudited.",
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
        if rid in seen:
            continue
        seen.add(rid)
        if rid not in C:
            src = r.get("_file", "")
            if rid in NOISE:
                noise.append(rid)
            elif src in DEFERRED:
                deferred.append((rid, src))
            else:
                missing.append(rid)
            continue
        cat, note = C[rid]
        act, owner, settle, cost = ACTION.get(rid, ("", "", "", ""))
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

    extra = sorted(set(C) - seen)
    unactioned = sorted(rid for rid, (cat, _) in C.items()
                        if cat in REOPEN_CATS and rid not in ACTION)
    orphan_actions = sorted(set(ACTION) - set(C))

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
    order = [N, E, "FLOOR", "DATA", "NARROW", "BUG"]
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
