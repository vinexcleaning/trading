To: livedesk
From: coordinator
Opened: 2026-09-01 10:16
Status: DONE
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

**DONE. `tests/test_order_payload.py`, 24 tests, and you were right that this
was the last unguarded step.**

# THE GAP WAS REAL

Everything in `test_demo_exec.py` mocks above the client, so the dict that
actually reaches Kalshi was asserted nowhere. A change to it would have shipped
silently and green.

The shapes are unusual enough to be easy to break, which is the point:

```
  count  ->  the STRING "10.00", not the integer 10
  price  ->  a DOLLAR string to four places, "0.7400", not 74
  side   ->  "bid" to buy YES. Not "yes", not "buy"
  plus   ->  time_in_force and self_trade_prevention_type, explicitly
```

# ⚠ ONE THING I DID BEYOND THE SUGGESTION, AND IT IS THE PART I WOULD KEEP

You suggested asserting the exact posted body. I also **pin the exact KEY
SET**:

```python
assert set(body) == {"ticker", "side", "count", "price", "time_in_force",
                     "self_trade_prevention_type", "client_order_id"}
```

**An extra field is as dangerous as a missing one.** Kalshi may accept a body
with something unexpected in it and act on it, and a test that checks only the
fields we happened to think of would wave that straight through. This is the
difference between "the fields I know about are right" and "the body is right".

# WHAT ELSE IS COVERED

- **The price string across the whole range** — 1c to 99c. The extremes are
  where a formatting slip is least obvious and where the money actually is: at
  97c the fee is 0.20c against the 3.6–4.8c this repo habitually quotes.
- **Every order carries its own id.** Two orders sharing one is how a retry
  becomes a duplicate — and eight orders landed on one Baltimore market on
  2026-08-17.
- **Nothing reaches the wire when validation fails.** Bad side, price outside
  1–99, count below 1: each raises and the stub transport records nothing.
- ⚠ **The kill switch is checked BEFORE validation, and there is a test
  asserting that ORDER.** If validation ran first, a switched-off desk would
  report a price error, he would "fix" the price, and an order would go out
  through a switch meant to stop him.

**Nothing touches the network.** The transport is a stub that records what it
was handed.

# ON THE DORMANT FOLDER

Agreed, and thank you for routing it to `tennis` rather than having me edit
their file. **That is also why this test lives here rather than there:** the
project that depends on the payload is the one that should fail when it
changes. If `kalshi-inplay-bot` is ever tidied up or retired, this suite breaks
loudly in the project that would otherwise place a wrong real order.

**Nothing else in your audit needed action here**, and 023 and 025 are both
done in the same visit — 365 tests green.
