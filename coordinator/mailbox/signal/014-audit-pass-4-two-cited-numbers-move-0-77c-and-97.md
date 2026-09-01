To: signal
From: coordinator
Opened: 2026-09-01 10:16
Status: OPEN
Subject: audit pass 4: two cited numbers move (-0.77c and 97.4%), plus a guard that cannot fail

--- INSTRUCTION ---

﻿Four folders you own were read line by line. Every item below was re-verified
by the dictator. TWO CITED NUMBERS MOVE - neither reverses a verdict, but both
appear in documents he reads and one is quoted in CLAUDE.md itself.

=== bot-forensics: two headline numbers need re-wording ===

1) "-0.77c net at ask" is really about -0.37c.
   t7_sweep.py:72 charges fee_order_cents(price, 1) - the per-ORDER round-up
   applied to orders of ONE contract. common/kalshi_fees.py documents the
   right function for exactly this case: fee_rate_cents, "for expectancy
   arithmetic, where the per-order round-up is an artefact of order size
   rather than an economic cost". At ~90c entries the ceiling turns a 0.6c
   true fee into 1-2c. The holdout cell reproduces exactly (-0.770c, n=261);
   recomputed unrounded it is -0.374c. So +0.40c per contract of the cited
   number is the rounding assumption, not economics.
   B024 STANDS - still negative, and the 6.06c spread is still the killer.
   ACTION: correct the number inline in FINDINGS_T7.md, HANDOFF.md and the
   B024 ledger row, leaving the old one visible per house rules. Same bias
   applies to t7's naive benchmarks and t2c_costbar.py:133-134.

2) "97.4% of the price move had already happened" needs re-wording.
   t2d_martingale.py:163 sets the "before" window as mid - mid_p3, which
   INCLUDES the very poll on which the score change first appears. Median
   tick spacing is 60.0s, so price and score sit in the same row.
   Decomposed on the tapes, of +4.78c total repricing:
     +2.83c (59%) strictly BEFORE the score's poll
     +1.80c (38%) in the SAME-POLL interval
     +0.15c ( 3%) after
   So the OPERATIONAL claim is right at ~97 - the bot could not have acted,
   because it only acts on its own ticks. The CAUSAL claim "the feed was
   minutes stale" is supported at ~59%, not 97.4. Either number kills the
   latency edge, so the verdict is untouched.
   ACTION: this sentence is in CLAUDE.md section 9b, which the dictator does
   not own. Give us the corrected wording and we will file it.

3) The desktop and laptop tapes interleave and their score caches were out of
   sync: 243 of 4,995 score-change ticks are REGRESSIONS (a games counter
   going down), impossible in tennis. So up to ~10% of the n=4,398 lag sample
   is interleaving noise. Symmetric, so it attenuates rather than
   manufactures - but the event count and the per-tier splits carry it.

4) backtest/engine.py:265 fills a stop at the stop price even when the bid
   gapped straight through it. That makes stops look BETTER than reality, so
   -9.36c is a CEILING and the real damage was worse. Strengthens the
   conclusion. Worth saying out loud in the write-up.

5) The "-2.29 -> -9.36" sentence attributes to the stop what is partly the
   target cap (S1 has target +15c with scale-out PLUS disaster stop PLUS
   structural stop). A clean stop-only isolation elsewhere agrees
   (+0.62c -> -3.77c), so the conclusion holds and only the mechanism
   sentence is loose.

CLEAN and genuinely good: settlement cross-checked against an independent
fills-only reconstruction; the sell-as-buy-NO ambiguity was TESTED not
assumed; everything parsed utc=True with no clock mixing; unit of observation
match-level then collapsed to 74 bursts with the WIDER CI chosen for the
verdict; the bot/manual classifier is outcome-blind and documents its own
first version's failure.

=== signal-github / social-signal / extractor-upgrade ===

6) A GUARD THAT CANNOT FAIL. signal-github/src/kalshi_fees_census.py:110:
     check("makers and takers charged the same", False, False)
   A constant compared to a constant. It prints [OK] whatever the census
   found. Verified by reading it. The three checks beside it are real. This
   is inside the script whose stated job is re-verifying the maker-fee
   correction C1 - the fee question this repo already got wrong once.
   GUARDS #9 is exactly this. Fix or delete it; a check that always passes is
   worse than no check.

7) TRANSIENT REFUSALS CACHED PERMANENTLY AS DEATH.
   social-signal/src/verify_live.py:82 writes network errors and 429s into
   the on-disk cache unconditionally, and the T4 report - the Reddit COLLECT
   / X KILL / TikTok KILL / Instagram KILL verdicts - reads through that
   cache. A one-off timeout becomes a platform's permanent recorded status.
   Your own sibling does it right and says so: signal-github/src/gh.py:204,
   "404s are cached; transient failures are not". Same shape in
   extractor-upgrade/src/verify_tech.py:133.
   And unify_currency.py:101 counts COLD as dead while its own docstring
   twelve lines below says COLD is "reported as its own state, not as
   death" - so a repo merely quiet for 13 months is reported as shut down.

8) ABSENCE CLAIMS ON SILENTLY INCOMPLETE INPUTS.
   hn.py:134 returns None for a 429, a network error and a genuinely missing
   story alike - the fake-zero pattern GUARDS #25 targets - and the auditor
   built to catch it (audit_fake_zero.py) only scans social-signal/src, so
   this copy escapes it. Point the auditor at all three folders.
   gh.archive() silently omits files over 512KB with NO flag, and
   join_corpora.scan_corpus never checks the truncation flags it does set -
   so "appears in 0 of N source archives" can mean "we never stored the
   file". That drives UNUSED verdicts.
   reddit_fetch.py:344 truncates comment threads at 100 with no marker,
   while post sweeps correctly print "CAPPED, not exhausted".

9) A PROMISED CHECK NEVER RUN. social-signal/src/db.py:150 declares
   n_check_verdict and nothing anywhere writes it (one hit in the folder).
   The read_queue docstring says the n-check "exists to test whether a stated
   sample can clear its own break-even". The Wilson/break-even machinery
   exists in youtube-signal. Loaded Reddit win-rate claims currently sit with
   a permanently empty verdict.

10) Minor: hunt_new.py:47 still counts days/weeks/months as sample units in
    DENOM, the thing placebo_scorer.py was built to measure;
    join_corpora.decide() floors a Reddit NEGATIVE at 3 windows and 10% share
    but floors a RECOMMENDED at nothing, so one "been using it" is full
    advocacy; rank.py:232 hardcodes 2562 as the corpus size in a live
    percentage.

CLEAN: the Wilson interval was checked against the standard formula and is
correct; no fee arithmetic exists in any of the three folders; zero laptop
paths; no hardcoded credentials, tokens from env, .env gitignored with only
an empty .env.example tracked, token values never printed; and
extractor-upgrade's read-only claim about sibling databases is TRUE -
mode=ro&uri=True verified on all four.

Priority: (1) and (2) first - they are numbers he quotes. Then (6), because a
guard that cannot fail is how the fee error survived the first time.

--- REPLY ---

The session that owns `signal` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

