To: livedesk
From: coordinator
Opened: 2026-09-02 14:51
Status: OPEN
Subject: show_fills.py prints every price as 0 - it reads a dead field name

--- INSTRUCTION ---

Found while extending the fee guard. Small, and it is a display tool rather
than the trading path - but it is a tool he might open to check his own real
fills, and it would lie to him silently.

## livedesk/tools/show_fills.py line 63 reads a DEAD field name

    px = f.get("yes_price") or f.get("price") or 0

`yes_price` is a legacy Kalshi field name. GUARD #23 records that the live
wire names end in `_dollars` or `_fp`, and that the legacy names are ABSENT -
so `.get()` returns None. Both alternatives here are legacy, so the whole
expression falls through to **0**.

**Consequence: every fill in that table prints a price of 0.** Not a crash, not
an error - a zero, in a tool whose job is to show him what he actually paid.

Line 58 immediately above gets this right:

    cnt = f.get("count") or f.get("count_fp") or 0

so the `_fp` convention was clearly known when the file was written; the price
line just did not get the same treatment. The fix is presumably adding
`yes_price_dollars` (and whatever the NO-side name is) to the front of that
chain - but **check the live field name against a real fills response rather
than taking mine**, since the whole point of GUARD #23 is that these names
moved once already.

**Worth a test**, because this is the second display-layer defect in this
folder in two days (after the "room for N more bets" line dividing by the dead
$4.15 stake). A tool that shows him numbers is not a lower tier than one that
computes them - it is the layer he actually reads.

## CONTEXT: this came from a guard that is currently RED repo-wide

`common/tests/test_no_legacy_kalshi_fields.py::test_no_new_WIRE_hit_appears`
is failing, and has been failing before anything I changed today (verified by
stashing my own edits and re-running). It names 13 files across five folders:

    bot-hunt/src/blind_spots.py, bot-hunt/src/pull_kalshi_soccer.py,
    crypto/src/deribit_chain.py, crypto/src/deribit_pricer.py,
    kalshi-market-scan/scripts/record_external.py, .../record_kalshi.py,
    .../score_vs_mid.py, .../soccer_census.py, .../vs_mid_clustered.py,
    livedesk/tools/show_fills.py,
    market-selection/src/check_fees_and_ticks.py,
    .../pull_kalshi_universe.py, .../pull_poly_universe.py

The test asks for each to be adjudicated into `WIRE_ADJUDICATED` with a
verdict. Yours is the only one in a live-money folder, which is why you are
getting told first. The rest are being routed to their owners.

**A red guard that nobody clears stops being a guard.** This one is doing its
job - it caught a real zero in your tool - and it is being ignored because it
is red as a whole.

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

