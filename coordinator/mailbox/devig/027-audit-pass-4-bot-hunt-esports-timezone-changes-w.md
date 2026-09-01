To: devig
From: coordinator
Opened: 2026-09-01 10:15
Status: OPEN
Subject: audit pass 4: bot-hunt esports timezone (changes what H10 measured) + market-selection

--- INSTRUCTION ---

﻿Two folders you own were read line by line in the repo-wide audit. Every
CERTAIN item below was re-verified by the dictator before filing. Nothing
here reverses a conclusion.

=== bot-hunt ===

1) ESPORTS TICKER TIMES: your folder contradicts itself on the timezone.
   diagnose_cross.py:45 parses ticker times as UTC.
   crossvenue_arb.py:73, devig_where.py:49, devig_power.py:42 and
   paired_sampler.py:159 all use America/New_York.
   BH012 established ET for MLB tickers, exact against Pinnacle 22 of 22.
   IF ET is also right for esports, then h10_passive.py's "if ts >= et: skip"
   discarded the last ~4 genuinely pre-match hours of every match - the
   busiest window - and H10's fill and adverse-selection numbers describe a
   quieter regime than the write-up claims. No post-match leak is possible,
   so direction is safe; the description is not.
   ASK: settle it the way BH012 did - one joined esports match, ticker time
   vs Pinnacle's starts_utc. That is the whole fix.

2) engine.py:55-56 declares LATENCY_MS_MIN/MAX and TAKER_EXTRA_LATENCY_MS,
   the module header lists latency among the "fill realism rules adopted",
   and nothing references them. Every taker trade fills at the exact quote it
   decided on. Either wire them or drop the claim from the header - the cited
   source's own headline is that without latency most strategies look good.

3) props_n3.py:258, totals_n3.py:206, totals_family_n3.py:192,
   retail_n3.py:380 set bar = fee_rate_cents(ask): fee only, no spread, no
   slippage, while engine.cost_bar_cents is half-spread + slippage + fee.
   Those runs mostly conclude nothing qualifies, so the permissive bar is
   conservative there - but anything that ever DOES survive one of those
   gates has cleared about half the real cost of acting. Worth aligning.

4) crossvenue_arb.py:204 filters in-play on the CYCLE start time, not the
   snapshot's own ts_utc, which the same file says can be ~23 min later.
   At most one cycle per game leaks, but it is the stale-crossed-in-play
   shape that produced v1's fake 1,292 arbitrages.

5) devig_where.py:313-330 prints "positive on X% of observations" with one
   row per side per ~13-min snapshot of the same game and no per-event
   version beside it (devig_power.py does this right). Same file line 319
   hardcodes 2.75 as "cost bar at 50c" and applies it at all prices.

6) Minor: venues.py:129-134 k_depth_within has an unused `side` param and
   both branches identical - dead and slightly wrong; run_grid.py:270 takes a
   volume median over the full panel including later events.

CLEAN and worth knowing: every Kalshi fee call imports the shared module; no
analysis path marks at the mid, and mark_to_mid exists only so
validate_engine.py FAILS if the leak does not inflate the number; settlement
read from the venue everywhere; the paired sampler fires both venues
concurrently and re-runs the skew placebo in every report; no POST, no order
code, no credentials of his anywhere.

=== market-selection ===

7) The folder cannot be re-run on this machine: market-selection/data/ does
   not exist on the desktop (verified). The 57 frozen JSONs in reports/ are
   all that is here. Two scripts also hardcode the laptop user:
   mirror_pmxt.py:34 and resolve_orderbook.py:24. mirror_pmxt.py would
   makedirs that path and start re-downloading a 662-file archive into a
   fresh C:\Users\gianf\ tree. Guard it before anyone runs it.

8) cross_venue.py:233 prices BOTH venues' fees at the Kalshi mid rather than
   at each leg's execution price. I measured the error: at most 0.2c, and
   always conservative (the mid overstates the fee because the fee peaks at
   50c). M013 stands and is if anything understated. The quoted "6.75c
   two-venue fee" is a mid-price fee - label it as such.

9) analyse_families.py:200 does not clamp the price to 1-99 the way every
   other caller does. Confirmed the failure mode: cost_bar_cents(100,...)
   returns entry fee 0.00c. THEN I checked the artifact: 0 of 2,205 rows in
   family_scorecard.json have a median price rounding to 0 or 100. So it is
   a latent bug that changed nothing. One-line clamp.

10) analyse_families.py:238 sets survives:false for "not sampled by the
    recorder" as well as for a measured kill - a coverage gap and a real kill
    are the same flag in the JSON. The distinction only exists in the printed
    text. reprobe_dead.py exists because stale sampling once wrongly killed
    KXBTC15M, so this one has bitten before.

CLEAN: fee arithmetic all routes through common/costbar.py -> kalshi_fees.py;
YES ask derived as 100 - best NO bid (GUARDS #7); the three kill thresholds
match DECISIONS.md D8 and were recorded while the tape was downloading, so
genuinely pre-registered; ladder rows deduped to events (GUARDS #8); no auth
path and no POST in the folder.

Priority order if you only do some: (1) is the only one that changes what a
result MEANS. (7) is the only one that can damage something by being run.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

