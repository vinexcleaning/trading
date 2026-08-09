# How an item gets graded

Plain English. The code is `src/rubric.py`; this explains what it is doing and,
more importantly, **what its score is and is not worth.**

## Three separate scores, never averaged

Every post gets three, and combining them into one number would destroy the
thing that makes them useful.

| axis | question | range |
|---|---|---|
| **S — Substance** | Does it contain real information about a *trading claim*? | 0–10 |
| **B — Build** | Does it teach you to build a thing that works? | 0–10 |
| **H — Honesty** | Can you trust the *results* it reports? | −10 to +11 |

**Why S and H are never averaged.** A post can be full of genuinely useful tools
and also lie about its returns. Averaging gives it a middling score and you
throw away both facts. Kept separate, the answer is: *use its tooling, ignore
its numbers.* That is inherited from `youtube-signal` and it is the single most
useful rule in the rubric.

**Why B exists.** S1, S2 and S3 all require a **trading claim** — a cost side, a
backtest-versus-live distinction, a sample size. A pure API tutorial makes no
trading claim, so it could score at most 3 out of 10 and be auto-rejected no
matter how good its code was. That happened: a Kalshi build with working code, a
public repo and an honest itemised account came out as SKIP. B asks the
different question.

## What earns points

**Substance** — names the cost side (fees, spread, slippage, vig); separates
backtest from live; states a sample size; explains *why* it works and who is on
the other side; names specific tools rather than gesturing.

**Build** — shows working code; a complete path from nothing to a running thing;
names versions and exact endpoints; names a gotcha and how it was handled; gives
a command you can reproduce.

**Honesty, positive** — shows a failure *and* does not pivot to selling a fix
(the strongest single signal); points to something verifiable — a repo, a
wallet, a public account; a performance claim carrying sample size **and** period
**and** starting capital; names a weakness in its own method unprompted;
discloses which promoted tools are its own.

**Honesty, negative — this is the marketing detector**

| | |
|---|---|
| **−4** | a performance claim with **no denominator** — "I made $5k" with no trade count, no period, no bankroll |
| **−2** | sells the method without disclosing the mechanism |
| **−2** | promotes a strategy they have abandoned without saying so |
| **−1** | urgency or scarcity language |
| **−4** | promotes a product and discloses no interest at all |

That last one is a fix this project shipped and `youtube-signal` did not: there,
a source that discloses nothing and a source with nothing to disclose both
scored zero and were indistinguishable.

## The verdicts

`BUILD_AND_RECOMMEND` · `BUILD` · `ABSORB_AND_RECOMMEND` · `ABSORB` ·
`ABSORB_RESULTS_DISCOUNTED` · `SKIP`

**`ABSORB_RESULTS_DISCOUNTED` is the interesting one.** It means: the method is
worth having, the numbers are not. Most useful people live there — they sell
something *and* show verifiable work.

## What this score is NOT

**It is a mechanical lexicon, not a reading.** It matches patterns and stores a
verbatim quote under 15 words for every component, which is the sibling rule —
*a component you cannot quote did not happen*. What it cannot do is understand.

**Its precision against a human read is UNKNOWN and no number is quoted for it
anywhere.** Six defects are documented in `reports/T2_rubric_audit.md`, every one
found by reading, and two of them found by reading the survivors of a previous
fix:

- A **satire post** enumerating every beginner error scores S=7, because "names
  the cost side" fires on *"I haven't added fees or slippage yet"*. **It cannot
  tell naming a cost from accounting for one** — and that is the top-weighted
  component.
- A post **warning about** scam sellers scores **H = −6**, because the negative
  components fire on language it quotes in order to condemn.
- On the best document in the whole corpus, **"shows a failure" does not fire on
  a post that is nothing but failures**, because its author writes "went from
  bleeding daily" rather than "I lost".

### The worst one, found by reading on 2026-08-05

A post claiming the favourite–longshot bias appears in prediction markets scored
**S=10 B=4 H=3 → ABSORB_AND_RECOMMEND**, the top of the whole queue. Its comment
section demolishes it — *"40-50% implied probability is neither a favourite or a
longshot… most likely an interpretation error, and if not then just spurious"*,
*"There's no universe where you're getting 20% edge per trade."*

Tracing every component back to the text that earned it:

| component | came from | the span |
|---|---|---|
| **S1 +3** names the cost side | **a COMMENT** | *"fees + slippage is like 5% at most?"* |
| **S4 +2** gives a mechanism | **a COMMENT** | *"you don't need to worry about adverse selection"* |
| **B4 +2** names a gotcha | **a COMMENT** | *"Most likely an interpretation error… just spurious"* |
| S2, S3, S5, B3, H1 | the post | — |

**Seven of its ten substance points came from the refutation.** The post scored
maximum substance *because* it was being demolished, and the better the
criticism the higher the claim scores.

This one is not a pattern quirk — it is a deliberate architectural choice doing
something unanticipated. Scoring the post *plus its comment thread* is right for
**finding** good threads, because on Reddit the substance is frequently in the
replies. But it means a single score cannot distinguish *"the post is good"*
from *"the post is wrong and the replies are excellent"* — and for a reputation
table those are opposite conclusions.

**Recorded, not patched.** The fix is architectural (store a post-only score
beside the thread score) rather than a pattern tweak, and it is untested.

### And one worse, where the mislabelling itself scored the points

A post titled **"90 days live trading & 800 trades"** whose body opens *"an
update on our live **paper** trading results"* — the 800 trades are paper and
live money had only just been set up. It scored **S=10 B=4 H=2 →
ABSORB_AND_RECOMMEND**.

| component | came from | the span |
|---|---|---|
| **S2 +2** *distinguishes backtest/theory from live/actual* | **the title** | *"days live trading & 800 trades"* |
| **S3 +2** *states a sample size* | **the title** | *"90 days live trading & 800 trades"* |
| **H3 +2** *a claim carrying n AND period AND capital* | **a COMMENT** | *"800 trades over 90 days is solid data"* |
| S1, S4, S5 | comments | — |

**The component that exists to reward separating paper from live fired on the
sentence that conflates them.** The sample-size component credited a paper
denominator presented as live. And an honesty credit came from a *reader
praising the author*.

Meanwhile the most damning fact in the thread scored nothing at all. Two
commenters independently asked whether the 15-percentage-point threshold was
fixed before the run, and the author replied: **"Nop no big testing upfront.
Gut feeling."** The single parameter selecting every trade was never
pre-registered — and it is an illiquidity filter (see
`FINDINGS_FROM_READING.md` §0d).

**Six of ten substance points and both honesty points came from either the
misleading title or from commenters.** This is the clearest evidence in the
project that the mechanical score cannot carry a verdict.

### Nothing was patched in response

Tuning patterns until they fire correctly on the handful you happened to read is
overfitting, and it would swap a *known-bad* instrument for an *unknown* one.

**So the score is used for one thing: ranking what to read next.** No verdict in
`reports/TOOL_REPUTATION.md` rests on it. Every finding this project has produced
came from reading the top of that queue — none came from the score itself.

## Read the per-platform split, never the aggregate

`reports/T2_reddit_scores.md` splits every rate by platform, because a rate
averaged across platforms is an average of two different objects:

| platform | items | PASS | recommend-grade | rate |
|---|---|---|---|---|
| reddit | 39,633 | 4,434 (11%) | 282 | **6.4% of PASS** |
| mastodon | 6,727 | 2,202 (33%) | 4 | **0.18% of PASS** |

Mastodon passes the on-topic gate three times as often and reaches
recommend-grade one thirty-fifth as often. Read either number alone and you get
the platform exactly backwards.
