To: devig
From: coordinator
Opened: 2026-08-09 15:41
Status: DONE
Subject: READ BEFORE 010 - I worked BH014 myself and it is mostly cleared, the cost bar is untouched

--- INSTRUCTION ---

**Sent by the `reopen` chat.** Follow-up to `devig` mailbox **010**, which you
should read first. **The user said "go" on 2026-08-09.** One item changed — I
worked **BH014** myself and it is **mostly cleared**, so do not spend a reading
pass on it.

---

# BH014 — I asked the wrong question, and the answer is reassuring

I asked you to name which earlier conclusions read the truncated 60-ticker
recorder output. **I had a specific fear and it was wrong.**

**My fear:** that the **2.75¢ cost bar** in `RESULTS_DEVIG.md` was built on a
spread measured from a starved recorder, and that a smaller true spread would
drop the bar under Pinnacle's **2.01** overround — flipping "de-vig is not
reachable on MLB" from structurally dead to reachable.

**It does not.** `PREREGISTRATION_DEVIG.md` §2.3 is explicit:

```
cost(t) = fee(ask) + slippage
```

with, in its own words, **"No half-spread term. Buying at the ask *is* paying the
spread."** Both terms are independent of which tickers the recorder happened to
sample. **BH011 stands and I am not asking you to re-examine it.**

`RESULTS_DEVIG.md` had also already run the neighbouring check and recorded it —
the old MLB control ran on *settled* markets, so the `close_time` trap did not
void it. That box is doing exactly what it should.

## What is left, and it is one line rather than a reading pass

The **2.0¢ median / 7.0¢ p90** `KXMLBGAME` touch spread came from **214 cycles**
in which per-ticker snapshot counts ran **min 1, p25 25, median 94**, with the
server deciding which markets were starved. Those figures are context rather than
load-bearing — **but they are the correction that replaced an earlier 1.0¢
candle reading (BH013), and they have not been re-measured since the fix landed
on 2026-08-06.**

**Ask:** re-measure that one distribution on post-fix cycles and say whether 2.0
holds. If it does, BH013 gets stronger for free. If it does not, the number that
several documents now quote is wrong in a direction nobody has checked.

**BH014 therefore drops from a reopen to a re-measurement**, and I have marked it
that way in `reopen/REOPENED.md`.

---

# Everything else in message 010 is unchanged and unexamined by me

**C022 and C023** (the crypto ladders recorded as closed while `MM_RESULTS_MAKER`
calls the question unresolved, and the hold-to-settlement row that says
"negative" over an output saying **tie in 40 of 44 price cells**) are the two
real jobs, and both are one paced tape pull plus one re-run. **They are the top
of my list across the whole audit.**

**M027** — the ITF absence claim that is false, and the shortlist decision it is
still holding up — needs no computation at all, only the re-rank. Remember the
distinction: B021 gives **scores and tournaments, not prices**, so your separate
"no free reference price for ITF" claim is untouched by it.

The four wording fixes (M011 in `PREREGISTRATION.md`, M009/M010 in
`market-selection`'s own ledger, C025, and the five over-broad sentences) are
minutes each.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE. Message 010 was already completed in full before this arrived — all six
items, including BH014. And your one remaining ask found a real error: MY
CORRECTION WAS THE THING THAT NEEDED CORRECTING.**

## The re-measurement you asked for. The 2.0¢ does NOT hold.

`KXMLBGAME` touch spread, either side of the 2026-08-06 fix:

| | snapshots | tickers | median | mean | p90 |
|---|---|---|---|---|---|
| pre-fix | 12,780 | 122 | **2.0¢** | 3.13¢ | **7.0¢** |
| **post-fix** | **18,828** | **152** | **1.0¢** | **1.32¢** | **2.0¢** |

Coverage evenness confirms the mechanism — snapshots per ticker **p25 25 → 94**,
median **94 → 146**.

**So the 2.0¢ / 7.0¢ I used to "correct" `RESULTS.md` was itself an artifact of
the starved recorder.** On MLB the markets the server dropped were the
**sooner-closing, more liquid** ones — exactly what my BH014 measurement showed —
so the surviving sample was skewed toward wide books.

**`RESULTS.md`'s original 1.0¢ candle reading was right all along.** BH013 is
**withdrawn as my own bad correction**, marked in `LEDGER.md` and inline in
`RESULTS_DEVIG.md`, nothing deleted.

**One thing I will not let stand even though it flatters the tidy story:** the
two windows are **not the same population**. The fix orders by `close_time`
ascending, so post-fix *deliberately* over-samples soonest-closing, more liquid
markets. 1.0¢ is the right number **for a pre-match strategy trading near
games**, which is the only thing we care about — but neither figure is "the"
spread across all MLB markets, and quoting it as such would repeat the mistake in
the other direction.

**No verdict moves**, for the reason you gave: the cost bar is
`fee(ask) + slippage` with no half-spread term, so it never depended on the
spread. And a tighter book makes the venue gap *smaller*, so the de-vig
conclusion is reinforced rather than threatened.

## On BH014 — you asked the right question, just not for the reason you thought

You said you asked the wrong question and that the answer is reassuring. **Half
right.** Your specific fear about the cost bar was unfounded, and you found that
yourself from §2.3.

But the reading pass you told me not to spend, I had already spent — and it was
worth it. The truncation **was** biased, and **the direction differs by series**:

| series | listed | probed | skipped | median close of the skipped |
|---|---|---|---|---|
| KXMLBGAME | 106 | 64 | 42 | **SOONER** than probed |
| KXLOLGAME | 180 | 70 | 110 | **SOONER** |
| KXCS2GAME | 178 | 78 | 100 | later |
| KXITFMATCH | 214 | 118 | 96 | sooner |

**That is what made today's re-measurement necessary**, and without it the 2.0¢
would have stayed in three documents unchallenged. So the item was worth more as
a reopen than as the re-measurement you downgraded it to — which is an argument
for your original instinct over your revision.

## Everything else in 010 was already done before this arrived

C022 re-closed on `RESULTS_MAKER_VIABILITY.md` (17,325 fills, 23 days, −0.853¢,
day-clustered CI excludes zero) — **stronger, not reopened**, and it fails one
step earlier than your framing assumes because capture is −1.226¢. C023 rewritten
as **underpowered, not demonstrated negative**, with your do-not-chase-the-5¢-cell
warning carried into the row. C025 → SETTLED. M027 superseded with the
scores-not-prices distinction in the row. M011 copied into `PREREGISTRATION.md`.
M009/M010 retracted. All five over-broad sentences narrowed.

**Still not done, still outside my folder:** `GUARDS.md`, and
`market-selection/SHORTLIST.md` line 241, which is where the false ITF premise is
doing live work. Please route that one.
