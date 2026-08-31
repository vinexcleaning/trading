To: devig
From: coordinator
Opened: 2026-08-31 16:02
Status: OPEN
Subject: GO on the paired sampler - and keep the skew placebo as a standing control

--- INSTRUCTION ---

**He has approved the paired sampler you asked for. Build it.**

> *"build the parlor sampler"* — voice dictation for the paired sampler in your
> `needs:` line. **Yes.**

# WHY IT IS WORTH BUILDING, IN YOUR OWN WORDS

BH024 could not answer the question because `record.py` walks Kalshi, then
Polymarket, then Pinnacle, leaving the venues a **median 6.5 minutes apart**
inside one cycle. Your own skew placebo settled it: **~14.7 extra crossings per
minute of skew, correlation 0.9975, extrapolating to 7 real against 125
observed — 94 in 100 were the clock.**

**That is an instrument limit, not a finding, and you said so rather than
reporting a null. This build removes the limit.**

# WHAT IT MUST DO

1. **Both venues within seconds, not minutes.** Concurrent requests, not
   sequential. **Record the actual per-venue timestamp on every row** and the
   measured gap — do not assume it worked.
2. **Store the skew as data.** Every future run must be able to re-run your own
   placebo. If the gap creeps back up, the numbers must show it rather than
   quietly degrading.
3. **Reuse the matching gate that already passed** — same clubs, same date, same
   numeric line, three independent agreements. 969 pairs over 202 games is a
   good result and should not be rebuilt.
4. **Exclude in-play by default**, for the reason you gave: the biggest fake
   crossings were stale limit orders on already-decided games, and `CLAUDE.md`
   §9b rules in-play out here anyway.
5. **Correct fees on both legs.** Kalshi from `common/kalshi_fees.py`.
   Polymarket from what you established in BH025 — **C x 0.05 x p x (1-p) taker,
   makers free** — and keep the citation and retrieval date next to it.
6. **Persistence is the headline number.** How many consecutive samples did a
   crossing survive? A 2-cent edge that lives for one sample is not tradeable
   and the current data cannot tell the difference.

# ⚠ WHAT NOT TO DO

- **No live connection to an execution path.** Recording only.
- **Do not re-run the skew placebo once and call it clean.** Run it on every
  report. It is now the standard control for this instrument.
- **Do not report an arbitrage count without the measured venue gap beside it.**
  That pairing is the whole lesson of BH024.

# THEN

The totals model against 854 settled games is still in your `left:` line and
`PREREGISTRATION_TOTALSMODEL.md` is written. **Sampler first — it is collecting
time-sensitive data and the totals model is not.**

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

