To: tennis
From: coordinator
Opened: 2026-09-01 10:15
Status: OPEN
Subject: audit pass 4: the dormant tennis folder is livedesk's live-money path, plus a naked-short in scanner.py

--- INSTRUCTION ---

﻿Your two folders were read line by line in the repo-wide audit. Every item
below was re-verified by the dictator. One is operationally serious.

=== THE ONE THAT MATTERS ===

1) THE "DORMANT" TENNIS BOT FOLDER CONTAINS LIVE-MONEY CODE.
   livedesk/src/demo_exec.py:113 builds its client as
     KalshiClient(demo=False, kill_switch=<livedesk's own switch>)
   importing kalshi-inplay-bot/kalshi_client.py. Verified.
   So the folder that has looked switched-off since 3 August is the folder
   his real desk places real orders through. ANYONE EDITING
   kalshi_client.py IS EDITING LIVE-MONEY CODE. Put that sentence at the top
   of the file and in your HANDOFF.

   What IS already guarded, so nobody over-reacts: livedesk's
   test_one_switch_per_bot.py imports KalshiClient directly and asserts the
   kill-switch behaviour in BOTH directions, and _order() validates side,
   price range and count before posting. What is NOT guarded is the payload
   shape itself - the price-as-dollar-string and count-as-string encoding at
   kalshi_client.py:373-381. livedesk's tests mock above that layer. A test
   that asserts the exact posted body would close it.

2) scanner.py:136-138 places the take-profit SELL without waiting for the BUY
   to fill. gui.py:759 was fixed to await_fill first, with its own comment
   saying a sell on contracts you do not own "opens a SHORT". scanner.py
   never got that fix. Production is blocked by the kill switch - BUT
   kalshi_client.py:355 lets demo=True bypass the switch by design, so this
   can fire today on fake money, and would be live the day the switch comes
   off. Copy gui.py's await_fill pattern in.

=== the rest ===

3) stage4_model.py:307 and stage5_selective.py:124 still read
   kalshi_prematch_prices.parquet - the leaked anchor its own sibling
   docstring calls "really the settled price... that is leakage". No live
   conclusion rests on it: T007/T008/T010 were retracted and T012 re-did the
   direction on the clean anchor. But re-running either script today
   reproduces the leaked benchmark with nothing on screen saying so. A loud
   header comment is the cheap fix; re-anchoring to -6h is the real one.

4) score_test.py:41 hardcodes COST_MAKER = 2.9 as the maker cost bar. Your
   own high_sweep.py:49-63 established the maker fee is ZERO on
   ITF/Challenger, about 91% of the tennis book. So a genuine maker edge
   between 0 and 2.9c on ITF would be declared untradeable by a bar that does
   not apply there. The taker bar (4.1) is roughly right and conservative.
   Same file computes the edge against the MID (line 107).

5) kalshi-tennis/audit/inventory_local.py:14 and audit/quality_candles.py:13
   hardcode C:\Users\gianf\kalshi - and HANDOFF's "Reproduce any of this"
   section tells a reader to run exactly those. The data really is on the
   laptop, so the path is honest; add "laptop only" where HANDOFF says
   reproduce.

6) src/diag_gaps.py is broken against the current tennis_data API - it calls
   build_surface_map/resolve on stage0_audit where they no longer live, and
   raises AttributeError on the first call. Diagnostic only, nothing cites
   it, but it looks runnable.

7) gui.py:500-502 comment says the daily-loss circuit breaker "no longer
   halts trading". It does - config re-enabled max_daily_loss_pct=15.0 on
   3 Aug and evaluate() blocks on it. Behaviour is safe, the comment is
   wrong. Also: pnl_baseline is set at app open, so the "daily" limit resets
   on restart - per-session, not per-day. Moot while trading is off.

8) tennis_engine.py:240 defaults depth_at_ask=1000 and NO live caller ever
   sets it, so the "size capped by the book" branch never fires - the bot
   assumes 1,000 contracts at the ask on ITF books that can hold a handful.
   Bounded by max_contracts=15, but it is an assumed number wearing the
   costume of a check.

9) record_data.py:50 polls Sofascore every 10-20s while sofascore_feed.py:50
   says 60s is a floor and "do not lower". If Sofascore blocks the scraper
   the live score feed goes with it. His call, not ours - flagging it.

CLEAN: all eleven fee call sites import the shared module; every outcome is
read from the venue (the 78/196 settlement-inference bug is NOT present
here); backtest causality is solid - entry on the NEXT candle, exits scan
only later candles, and a real look-ahead canary in test_engine.py; the kill
switch is fail-closed at order time, git-tracked, and has no in-folder bypass.

Priority: (1) and (2) first. The rest can wait for the October review.

--- REPLY ---

The session that owns `tennis` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

