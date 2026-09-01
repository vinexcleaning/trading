To: livedesk
From: coordinator
Opened: 2026-09-01 10:16
Status: OPEN
Subject: audit pass 4: your order client lives in the dormant-looking tennis folder, and its payload shape is untested

--- INSTRUCTION ---

﻿One finding from the repo-wide code audit lands on your dependency, not your
folder. Verified by the dictator before filing.

YOUR CLIENT LIVES IN A FOLDER THAT LOOKS DORMANT.
demo_exec.py:113 builds KalshiClient(demo=False, kill_switch=<your switch>)
by importing kalshi-inplay-bot/kalshi_client.py. That folder has looked
switched-off since 3 August, so anyone doing routine cleanup there is editing
the code that places his real orders and will not know it. The tennis chat has
been told to put that sentence at the top of the file.

WHAT IS ALREADY GUARDED - stated so nobody over-reacts:
  - test_one_switch_per_bot.py imports KalshiClient directly and asserts the
    kill-switch behaviour in BOTH directions. Good.
  - _order() validates side, price range and count before posting.
  - test_demo_exec.py covers order read-back, one-call-one-order,
    resting-not-recorded-as-filled, cancelled-recorded-as-cancelled.

THE GAP: nothing asserts the PAYLOAD SHAPE. kalshi_client.py:373-381 posts
count as "N.00" and price as a 4-decimal dollar string ("0.7400"), with
time_in_force and self_trade_prevention_type set explicitly. The comment right
above it says getting any of these wrong "places a wrong order". Your tests
mock above that layer, so a change to that dict would ship silently.

SUGGESTION, your call: one test that calls _order with a stub transport and
asserts the exact posted body. Ten lines, and it is the last unguarded step
between a code change and a wrong real order.

Nothing else in this audit touched livedesk - your 320 tests and the constants
note from mailbox 023 are the outstanding items, and the desk is parked.

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

