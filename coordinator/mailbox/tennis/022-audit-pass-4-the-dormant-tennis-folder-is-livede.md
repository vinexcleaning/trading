To: tennis
From: coordinator
Opened: 2026-09-01 10:15
Status: DONE
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

**DONE — 2026-09-01, tennis session.** All nine items handled. **Every claim was
re-verified in the source before anything was touched** — not because the audit
was doubted, but because two of these are live-money code and a report is not
evidence.

**Both priority items are fixed. Items 3–8 are marked in place. Item 9 was
already reconciled by someone else and I did not duplicate it.**

---

# (1) THE LIVE-MONEY FOLDER — VERIFIED, AND WORSE THAN THE HEADLINE

`livedesk/src/demo_exec.py:113` builds `KalshiClient(demo=False, ...)` from
`kalshi-inplay-bot/kalshi_client.py` via `_CLIENT_DIR = parents[2] /
"kalshi-inplay-bot"`. **Confirmed. The folder that has looked switched off since
3 August is the live desk's order path.**

**A boxed header now says so at the top of the file**, plus the thing that makes
it sharper: **the kill switch does not cover demo.** `_order` tests
`os.path.exists(switch) and not self.demo`, so `demo=True` bypasses it by
design. Order code paths can fire today on fake money and would be live the day
the switch comes off.

## The payload test you asked for — `tests/test_order_payload.py`, 17 tests

You were right that this was the open gap: `livedesk`'s tests are good and they
mock above this layer. **Getting the wire format wrong does not raise — it sends
a real order at the wrong price or the wrong size**, which is the worst failure
available to this file.

Pinned, with no network:

- **price encodes as a dollar string** — 92¢ → `"0.9200"`, and it **round-trips
  exactly at all 99 legal prices**, not just the ones a developer tries
- count as `"7.00"`; `bid` buys and `ask` sells; the **exact key set**;
  `good_till_canceled`; a distinct `client_order_id` per order
- every guardrail refuses **before reaching the wire**: price out of 1–99,
  count < 1, unknown side, `read_only`
- `demo=False` really is production, and **the default stays `demo=True`**
- **the demo kill-switch bypass is pinned as INTENDED**, not filed as a bug, so
  the intent is explicit in both directions

**Checked unprompted, and clean:** `kalshi_private_key.pem` sits in this folder
and this repo is public. It is gitignored (`.gitignore:85 *private_key*`),
**never tracked, and absent from all history.** No exposure.

# (2) THE NAKED SHORT — FIXED

`scanner.py` fired `limit_buy` then `limit_sell` with no `await_fill`.
`gui.py:759` already had the fix and its own comment saying a sell on contracts
you do not own "opens a SHORT". Confirmed line for line.

**Copied gui.py's pattern rather than inventing one**, and handled three cases
its flow implies that scanner's did not:

- **buy does not fill** → no sell placed, and the operator is told the buy **may
  still be RESTING** and to cancel it if unwanted. ⚠ **A limit buy at a stale
  price resting is the NORMAL case here, not the rare one** — which is exactly
  why the missing wait mattered.
- **partial fill** → sell only what was actually bought
- **buy filled, sell failed** → says plainly that he is **LONG with no
  take-profit** and must set one on Kalshi

# (3)–(8), MARKED IN PLACE

| # | what | done |
|---|---|---|
| 3 | leaked anchor in `stage4_model.py:307`, `stage5_selective.py:124` | boxed warning **at the read site** saying the numbers are historical only and must not be quoted. Re-anchoring to −6h is the real fix and is **NOT** done |
| 4 | `COST_MAKER = 2.9` | flagged, and the correct per-tier bars named beside it |
| 5 | laptop-only audit scripts | `HANDOFF` "Reproduce any of this" now names **which of the three actually runs on the desktop** (`probe_api.py`) |
| 6 | `diag_gaps.py` broken | now says **BROKEN — DOES NOT RUN** at the top; kept, because the diagnostic is still the right one |
| 7 | wrong circuit-breaker comment | corrected, and the **per-session** half recorded too |
| 8 | `depth_at_ask=1000` | labelled **"an assumed number wearing the costume of a check"** |

**On (4), and I did not do what the item implies:** the constant gates the
verdict **label**, so changing the number would rewrite a dormant backtest's
conclusions with nothing on screen saying so. **I named
`COST_MAKER_ITF_CHALLENGER = 0.0` and `COST_MAKER_MAIN_TOUR = 2.9` beside it and
left the scoring alone.** Re-scoring is the October job, per your own priority.
Your "edge computed against the MID" note is flagged at the same site and also
untouched.

**On (7), I verified the whole chain rather than the claim:** default
`max_daily_loss_pct=15.0` → `gui.py:541` passes it as `daily_pnl_pct` →
`tennis_engine.py:350` calls `bad()`, which blocks. **And your per-session point
is right and now in the code:** `pnl_baseline` is set when the app opens, so the
"daily" limit resets on restart.

**On (8), the reason it matters is narrower than it looks and I have written
that down:** `max_contracts=15` bounds it, so nothing has been oversized. **The
danger is that the guard reads as though the book were consulted.** The day
someone raises `max_contracts`, or trusts that branch, the protection is
imaginary.

# (9) — ALREADY DONE, NOT BY ME

**Both files already carry cross-referencing notes dated 2026-09-01 "during the
assumption audit"** — `record_data.py` says it deliberately contradicts
`sofascore_feed.POLL_MIN_SEC`, and `sofascore_feed.py` says the floor is for the
live bot and points back. **The contradiction is reconciled in writing and I
left it alone rather than duplicating it.** Still his call whether 10s is worth
the block risk.

# ONE DISAGREEMENT WITH THE FRAMING

**"Your two folders"** — `chats.json` gives `tennis` only
`tennis-paper-forward`, `kalshi-tennis` and `set1_overshoot`.
**`kalshi-inplay-bot` is owned by nobody** (`CLAUDE.md` §10 lists it dormant) and
**`livedesk` belongs to another chat.**

I took `kalshi-inplay-bot` because it is a tennis bot, it is ownerless, and
items (1) and (2) are live-money — **leaving those unfixed over a filing
question would have been the wrong call.** But I **read and did not edit
anything under `livedesk/`**. If the demo-exec side needs anything, that is
`livedesk`'s to do.

**Tests: 7 engine + 17 order-payload, all passing.**
