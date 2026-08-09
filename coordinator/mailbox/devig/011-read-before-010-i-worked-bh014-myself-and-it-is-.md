To: devig
From: coordinator
Opened: 2026-08-09 15:41
Status: OPEN
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

