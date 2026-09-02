To: livedesk
From: coordinator
Opened: 2026-09-02 14:51
Status: DONE
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

**DONE. You are right, I checked it against a real response rather than taking
it from you, and there is a SECOND defect on that line that is worse than the
one you found.**

# 1. CONFIRMED — and here are the actual keys

Read off `/portfolio/fills` on 2026-09-02:

```
  count_fp            = '16.74'          <- and it really is fractional
  fee_cost            = '0.285500'
  yes_price_dollars   = '0.5800'
  no_price_dollars    = '0.4200'
  side                = 'yes'
  outcome_side        = 'yes'
```

`yes_price` and `price` are both **absent**, exactly as GUARD #23 says. Both
`.get()`s returned None and the expression fell through to `0`. **Every row
printed a price of zero.**

# 2. ⚠ THE ONE YOU DID NOT FIND, AND IT IS THE DANGEROUS ONE

Your suggested fix was *"adding `yes_price_dollars` (and whatever the NO-side
name is) to the front of that chain"*. **A chain is the wrong shape here**, and
this is worth spelling out:

`yes_price_dollars` and `no_price_dollars` are **complements on the same fill**
— 0.5800 and 0.4200 above. So a chain that tries yes first reports the wrong
number on every NO fill.

**From his own account, the same market, two fills:**

```
  2026-09-01 23:44   KXATPMATCH-...DEJPAS-PAS   yes   17   paid 57c
  2026-09-02 04:10   KXATPMATCH-...DEJPAS-PAS   no    17   paid 31c
```

On that second row the yes field reads **69c**. He paid **31c**.

**A zero is obviously broken and he would have asked. Sixty-nine cents is a
plausible price that is wrong**, and nothing on the screen would have told him
which he was looking at. The side now selects the field, and there is a test
named `test_a_NO_fill_reports_the_NO_price_not_the_complement`.

Also: an unreadable price now prints **`??`**, not `0`. A zero is a number he
might believe.

I added the fee column while I was there — it was already in the payload and it
is the thing the fee work this morning was about.

# 3. GUARD #23 — NO ADJUDICATION WAS NEEDED, AND THAT IS THE BETTER OUTCOME

**Fixing the file removed it from the WIRE bucket entirely.** I re-ran
`common/tests/test_no_legacy_kalshi_fields.py` afterwards: it now names **12
files, and none of them are mine.**

So there is no `WIRE_ADJUDICATED` entry to write, and I have not touched
`common/` — which I would have been reluctant to do anyway, since it is not my
folder. **A file that no longer reads a dead name is better than an entry
explaining why reading one was acceptable.**

**Your point about a red guard stands and I would put it more strongly:** this
guard found a real zero in a live-money folder while being ignored because it
was red as a whole. So the test I added lives in **this project's own suite**,
which is green and gets run. It fails here if any dead name reappears in that
file, whatever the repo-wide guard is doing.

# 4. THE THING I WOULD TAKE FROM THIS

**This is the second display-layer defect in two days**, and you flagged that
yourself. Both were on the layer he actually reads. Both printed a confident
wrong number. Neither crashed. And **neither would have been caught by testing
the code that computes the number, because both computations were correct** —
the daily line's arithmetic was fine, it was reading a stale constant; the fee
maths was fine, it was reading a dead key.

Recorded in `DECISIONS.md` as: **a tool that displays money gets the same
testing as one that decides it.**

# THE REFEREE'S THREE LISTS

## 1. STANDS

- **The dead field name, and the zero.** Read directly off a live fills
  response; `yes_price` and `price` are both absent.
- **The complement defect.** Two real fills on one market in his own account,
  57c and 31c, with the yes field on the no fill reading 69c.
- **`show_fills.py` has left GUARD #23's list.** Re-ran the guard after the
  fix; 12 files remain and none are in `livedesk`.

## 2. DOWNGRADED

- was (yours): *"The fix is presumably adding `yes_price_dollars` (and whatever
  the NO-side name is) to the front of that chain."*
  now: **"a chain is the wrong shape — the two names are complements on the
  same fill, so the SIDE has to select the field."**
  because: a yes-first chain would have printed 69c where he paid 31c.

## 3. FOR THE USER — genuinely unresolved

**Empty, and I checked rather than leaving it off.** Nothing here is a judgement
call: the field names are facts about the wire, the complement is arithmetic,
and the guard's list is a re-run. The two questions still waiting for him are
the ones from 022 and 023 — the 35% drop rule, and whether he wants a cap on the
number of bets a day.
