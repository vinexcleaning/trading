# HANDOFF — youtube-signal

**Updated 2026-08-03 ~16:10. Machine `vinig` (the DESKTOP), not `gianf` (the laptop).**
Working directory: `C:\Users\vinig\trading\youtube-signal` — inside the repo, tracked, pushed.
Repo `github.com/vinexcleaning/trading`.

**Cost this session: $0.00. YouTube Data API quota used: 0 units. No API key exists or is needed.**
`read_video.py` has still never executed. The read is done in-session by the model
reading the transcript directly. That remains correct.

---

## 0. READ THIS FIRST — this machine is not the machine the last handoff describes

The previous handoff was written on the laptop (`C:\Users\gianf\trading`). **That
profile does not exist on this machine.** `C:\Users\gianf` is absent; the only
user profiles here are `vinig`, `Public` and `WsiAccount`.

`data/`, `reports/` and `KNOWLEDGE.md` are **gitignored** — deliberately, because
they hold honesty judgments about named real people and the repo is public. So
they never travelled with the repo. On this machine, at session start:

| | laptop | this desktop, at start |
|---|---|---|
| `data/signal.db` | 11,277 known videos, 683 transcripts | **did not exist** |
| the 60-video read set | selected | **did not exist** |
| the 19 read extractions | present | **did not exist** |
| `.venv` | present | **did not exist** |
| `src/*.py` | present | present (all 46 files) |

**The instruction that started this session said "19 of the 60-video read set are
done". That is true of the laptop and was not true here.** Nothing was lost — the
laptop still has its 19 — but none of it was reachable from this machine, and the
work could not be "continued" in the literal sense. The corpus was rebuilt from
zero instead.

### The two corpora are NOT interchangeable

Retrieval was re-run, so this machine has **its own** union of videos and **its
own** seeded read set. Overlap with the laptop's set is partial and unmeasured.
**Do not pool the laptop's 19 extractions with this machine's 6 and call it 25.**
They are different samples from different retrieval runs, and the pre-registered
retrieval test depends on the read set's sampling design being intact.

If you want them merged, the honest route is to copy the laptop's
`reports/extractions/*.json` here and re-run `load_extraction.py` on any whose
`video_id` is also in this machine's `read_set`. Everything else is a different
population.

---

## 1. What was actually done this session

1. Built `.venv` (Python 3.13.14), installed `requirements.txt`.
2. **Found and fixed two schema bugs that made the pipeline non-reproducible on
   any second machine** (§2). One of them meant `run_gates.py` could not gate a
   single video on a fresh database.
3. Rebuilt the corpus end to end: retrieval → gates → ranking → read-set selection.
4. Read and extracted **6 videos**.
5. Pre-registered, then amended, the retrieval-payoff test (§4).
6. Regenerated `KNOWLEDGE.md` (32,147 chars).

### Corpus, rebuilt

| | this machine | laptop, for comparison |
|---|---|---|
| unique videos retrieved | **746** | ~718 gated |
| PASS | **370** | 369 |
| transcripts cached | **688** | 683 |
| searches, failures | 84, **0 failed** | — |
| throttle verdict | **no degradation detected** | — |

Gate census: PASS 370 · STALE_G2 190 · DROP_G3_OFF_TOPIC 98 ·
DROP_G1_NO_TRANSCRIPT 49 · DROP_G3_DISCRETIONARY 18 · DROP_G1_EMPTY_TRANSCRIPT 12
· DROP_META 9.

That the rebuild landed within ~1% of the laptop's PASS and transcript counts is
the strongest available evidence that retrieval is stable and the pipeline is
deterministic enough to trust.

Channel expansion was **skipped** (`--no-expansion`). Expanded videos carry no
query-family attribution, so they are unusable both for `select_read_set.py`
(which requires `source='search'`) and for the retrieval test. This also sidesteps
`expansion_v2.py`, which the previous handoff records as not working.

---

## 2. Two silent-schema bugs — the pipeline was not reproducible at all

Both are the same shape as the three already recorded, and both were invisible on
the machine where the code was written, because that machine's DB had been
patched by hand.

**Bug #4 — `scores.b_total`.** Written by `load_extraction.py:109`, read by
`build_knowledge.py` in three places, **created by no file**. It existed only as an
ad-hoc `ALTER` on the laptop's DB. Every extraction load on a fresh DB would have
raised `no such column: b_total`.

**Bug #5 — `videos.description`.** Written by `run_gates.py:96-103` on *every*
video it gates; created only by `backfill_descriptions.py`'s `ALTER`. Reproduced
against the committed pre-fix code before fixing:

```
PRE-FIX run_gates.py FAILS as predicted -> no such column: description
```

**This one is the serious one: gating could not process a single video on a fresh
database.** The project was, in practice, un-runnable anywhere except the one
laptop.

The general rule, now written into both DB modules: `CREATE TABLE IF NOT EXISTS`
is a no-op against a table that already exists, so **a column added to `SCHEMA`
alone reaches new databases and never old ones, and a column added by `ALTER`
alone reaches old databases and never new ones. Both halves are always required.**
Both modules now carry a `MIGRATIONS` tuple applied idempotently at `connect()`.

That is five silent-default bugs in this project. The previous handoff's warning
stands and should be strengthened: **do not trust a green run on the machine where
the code was written.**

---

## 3. Issue 1 — the S1/S2/S3 rubric bug. ALREADY FIXED, and now demonstrated.

The instruction asked for a build axis to be added before scoring more
engineering videos. **It was already added on the laptop** (commits `d559fcb`,
`01825f2`, `1af7610`) and that code is in this repo: `read_video.py` carries
`B_WEIGHTS`, `validate_response` and `totals` handle `b_components`, and
`verdict()` routes on `b`. Nothing needed building.

What was missing was a demonstration on a video the axis had never seen. It now
has one:

> **`6MShnMgA9JY` — Jonjo Wadwa, "Alpaca Python Algorithmic Trading Tutorial"
> — S=3/10, B=9/10, H=0 → BUILD_AND_RECOMMEND.**

S=3 is the bug exactly as documented: S1 (cost side), S2 (backtest vs live) and
S3 (sample size) all require a *trading claim*, and a pure API tutorial makes
none, so it caps at 3 and would have been auto-`SKIP`. The video contains working
code, a complete key→client→order path, and a genuine gotcha — Alpaca returns
`equity` and `last_equity` as **strings**, so day return needs a `float()` cast.
None of that is visible to S. All of it is visible to B.

The rubric bug is closed. `SKIP` count across all 6 videos read here: **0**.

### One new judgment call, flagged because it extends the axis

`UQk6Mze5F3Q` fired **B1 (working code) on a prompt**, not on code — the video
drives Claude Code with verbatim, reproducible prompts, and in an agentic
workflow the prompt *is* the executable artifact. That is the first time B1 has
fired on something that is not source code. It is defensible and it is also a
widening of what B1 means. **Worth an explicit ruling before it becomes precedent
by accident.**

---

## 4. Issue 2 — the retrieval win. Part A replicates. Part B cannot be settled by this read set.

### Part A — the retrieval facts replicate, on a freshly retrieved corpus

| | Phase 1 (laptop) | this rebuild |
|---|---|---|
| F1 ∩ F2 Jaccard | 0.037 | **0.0463** |
| low-view yield ratio F2 / F1 | 2.25× | **2.21×** |

F1 vs F2B 0.0462, F2 vs F2B 0.0428. The families are near-disjoint and that is
now an **independent replication**, not a single measurement.

New numbers the laptop did not have:

| family | found | exclusive | PASS rate | <5k views, as % of PASS |
|---|---|---|---|---|
| F1 (beginner) | 123 | 74.8% | **77.2%** | 24.2% |
| F2 (insider) | 352 | 88.9% | 46.3% | 53.4% |
| F2B (insider, Phase 2) | 330 | 88.5% | 48.5% | **71.2%** |

Two things follow. **F2B is the best low-view finder in the project** — 2.94× F1,
better than the original F2, so the 12 added insider terms earned their place.
And **the insider families pay for it at the gate**: they pass at 46–48% against
F1's 77.2%. Insider vocabulary finds more obscure videos and more junk. That is
precisely the "different, not better" risk, and Part A cannot resolve it.

### Part B — pre-registered, amended, and currently unanswerable

`src/retrieval_payoff.py` fixes hypothesis, groups, primary outcome
(**max(S,B)**, because testing a retrieval family on an axis that cannot score
half its output would measure the rubric and not the retrieval), a two-sided
permutation test, and the decision rule — all written before any score existed.

**Amendment, committed after 4 videos and before any group was full:** the
read set clusters. `select_read_set.py`'s ANCHOR rule admits every passing video
from one channel (Nates Tokens); **all three landed in `F2_only`, entirely inside
the INSIDER arm**, placed there by a rule unrelated to retrieval family. Across
the whole read set: TC Trading 3, Nates Tokens 3, Unbiased Trading 2, Moon Dev 2,
IN THE MONEY 2. Two sensitivity analyses were declared — stratified-only, and one
row per channel — and the script downgrades its own verdict to
`CASHED_OUT_BUT_NOT_ROBUST` if they disagree with the primary.

Result at n=3 per arm:

```
  outcome               insider  beginner    diff        p   effect
  max(S,B) [PRIMARY]       8.00      7.00   +1.00   0.7000    +0.33
  S                        8.00      5.00   +3.00   0.3000    +0.78
  B                        5.00      3.00   +2.00   0.6000    +0.33
  H                        2.67     -1.33   +4.00   0.2000    +0.89
  === NOT DEMONSTRATED. Minimum detectable effect exceeds the 10-point scale.
```

Every outcome points the same way and **not one of them means anything** at this
n. Both declared sensitivities refused to run — and sensitivity 2 refused
*because of the confound it exists to control*: INSIDER's 3 videos come from only
2 channels.

### The finding that actually matters: the read set may be structurally too small

`F1_only` contains **17** videos. That is a hard ceiling on the BEGINNER arm — so
**n=17 per arm is the most a complete read of all 60 can ever produce.** Power at
that ceiling, simulated by resampling the observed score pool:

| true effect | power at n=17/17 |
|---|---|
| +1.0 points | **0.34** |
| +1.5 points | 0.72 |
| +2.0 points | 0.94 |
| +2.5 points | ~1.00 |

**So: finishing the read set settles the question if the true effect is ≥1.5
points, and cannot settle it if the effect is around 1 point** — which is exactly
the size observed so far on the primary outcome. To resolve a +1.0 effect at 80%
power needs roughly **45 per arm**, which means enlarging the read set beyond 60.
The corpus can support it (95 F1 / 163 F2 / 160 F2B passing).

This is a real possibility that the question is not answerable at the planned
scale, and it is better known now than after 54 more reads.

---

## 5. What was read (6 of 60)

| video | channel | bucket | S | B | H | verdict |
|---|---|---|---|---|---|---|
| `UQk6Mze5F3Q` Use Claude to find Polymarket wallets | Nates Tokens | F2_only | 10 | 8 | 6 | BUILD_AND_RECOMMEND |
| `6MShnMgA9JY` Alpaca Python trading tutorial | Jonjo Wadwa | F1_only | 3 | 9 | 0 | BUILD_AND_RECOMMEND |
| `BbRop6eZHB4` How to copytrade on Polymarket | Nates Tokens | F2_only | 8 | 5 | 2 | ABSORB_AND_RECOMMEND |
| `7rfzAgvBHxU` BloFin trading fees explained | Crypto Trading Guides | F2B_only | 6 | 2 | 0 | ABSORB |
| `e0QRge6-bKU` Five things to know, Polymarket/Kalshi | WagerTalk TV | F1_only | 6 | 0 | −1 | ABSORB_RESULTS_DISCOUNTED |
| `PeutA_HKxew` "I found the best Polymarket bot" | Rolink Craft | F1_only | 6 | 0 | −3 | ABSORB_RESULTS_DISCOUNTED |

**79 claims** (spec 19, mechanism 18, result 12, procedure 11, concept 10, math 7,
tool_rec 2) · **17 tools**, 4 referral-flagged, 2 undisclosed ownership ·
**5 methods** · **3 watch segments**.

**40 minutes of runtime → 1.6 minutes that need eyes. 25× compression.** Three of
six needed zero watching.

**All 14 S/H components that have ever fired fired again, plus all 5 B components.**

### The n-check fired zero times, and that is itself the finding

Not one video stated a win rate *and* a sample size together. The closest:
`PeutA_HKxew` claims "a 70 to 80% win rate" with no n, no period and no capital —
which is why H6 (−4, performance claim with no denominator) fired on it. **The
arithmetic check cannot run because the denominator is exactly what this genre
omits.** That is not a gap in the tooling; it is the measurement.

### Substantive findings from the reading

- **`PeutA_HKxew` is a sales funnel and is scored as one** (H=−3). Its own numbers
  refute it, and the extraction records the arithmetic: $300 → $15,000 in a week
  is 50×, which at its claimed 75% win rate needs ~10 consecutive full-bankroll
  wins (log 50 / log 1.5 = 9.6), and 0.75¹⁰ = **5.6%**. It presents a 1-in-18
  outcome as the expected one.
- **`7rfzAgvBHxU` is a video entirely about fees that then tells you fees don't
  matter** — "these percentages don't really matter too much" because Bitcoin
  moves a few percent a day. That compares a deterministic cost with a stochastic
  move. Five taker round trips a day is 0.6% of notional *per day*, paid whatever
  the price does. Recorded as a correction, not as a claim.
- **`e0QRge6-bKU` contradicts itself across two of its own five points.** Point 2:
  fade the crowd, it is "a collated opinion from a bunch of people who regularly
  lose money". Point 5: the crowd is "a good sample size on what will happen".
  Its best claim is sound and worth keeping: break-even is 110/210 = **52.38%** at
  a sportsbook against ~51% on a prediction market, verified independently here.
- The BloFin fee numbers (0.02% maker / 0.06% taker) are from **April 2025** and
  `spec` claims expire in **3 months**. They are ~15 months stale. Do not repeat
  them without rechecking.

---

## 6. What is wrong, unfinished or untrusted

1. **A parallel session's `git add -A` swept this project's file into a
   `signal-github` commit** (`d0e10c0`). `retrieval_payoff.py`'s content is intact
   and verified in HEAD, but **the commit message documenting that the
   pre-registration amendment preceded the result was lost.** The file
   self-documents its own timing, so the audit trail survives in the source. This
   is the mechanism `CLAUDE.md` forbids `git add -A` for, firing for the **fifth**
   time — and the first time in this direction, with another project absorbing
   this one's work. Stage explicit paths.
2. **The 22-hour video (`b9EXshJM94g`, 1,323 min) is still unread.** It is the
   `longest` anchor and the deliberate compression test. It does not fit a context
   window and chunking is still not built. It sits at position 2 in the read order
   and was skipped, not forgotten.
3. **H can reward disclosure but cannot penalise concealment.** `7rfzAgvBHxU`
   promotes a referral link twice, never discloses any interest, and scores
   **H=0** — H5 (+2) simply fails to fire. A video that discloses nothing and a
   video with nothing to disclose are indistinguishable. Both score 0. **This is
   a genuine rubric gap and it is the same blind spot the laptop session found in
   descriptions.** A negative component for undisclosed monetisation is the
   obvious fix and was NOT added here, because changing the rubric mid-read would
   invalidate the comparison between videos scored before and after.
4. **H is meaningless for videos that make no claims.** `6MShnMgA9JY` scores H=0
   not because it is neutral but because there is nothing to be honest *about*.
   H=0 currently means three different things.
5. **B1 has now fired on a prompt** rather than on code (§3). Unruled precedent.
6. Both G3 validation samples still informed the lexicon's design, so its
   85.9% / precision 0.809 / recall 1.000 remain **upper bounds, not a holdout**.
   Unchanged this session.
7. `read_video.py` has still never run and is unvalidated below the API call.
8. The read set's ANCHOR rule injects a non-random single-channel block into one
   arm of the test (§4). Handled by declared sensitivity analyses, not fixed.

---

## 7. The single next thing to do

**Read `next_reads.py`'s order and keep going — but decide first whether the
retrieval test is worth finishing at all.**

```bash
C:\Users\vinig\trading\youtube-signal\.venv\Scripts\python.exe C:\Users\vinig\trading\youtube-signal\src\next_reads.py 10
```

The decision that governs everything else: at the read set's structural ceiling of
17 per arm, the test resolves a ≥1.5-point effect and cannot resolve a 1-point
one. Either accept that ceiling and read the remaining 54, or enlarge the read set
to ~45 per arm first — cheap, since selection is deterministic and seeded and the
corpus already holds 370 passing videos.

Reading is worth doing regardless for `KNOWLEDGE.md`. Only the *test* depends on
this choice.

Then re-run, in this order:

```bash
C:\Users\vinig\trading\youtube-signal\.venv\Scripts\python.exe C:\Users\vinig\trading\youtube-signal\src\retrieval_payoff.py
```

```bash
C:\Users\vinig\trading\youtube-signal\.venv\Scripts\python.exe C:\Users\vinig\trading\youtube-signal\src\build_knowledge.py
```

---

## 8. Checkpoint status

Working tree **clean**. All code committed and pushed; `origin/main` verified
**0 ahead, 0 behind** at the last push. Commits from this session:

| commit | what |
|---|---|
| `e4dff71` | schema bug #4 (`b_total`) + the pre-registered payoff test |
| `dc36ef2` | schema bug #5 (`videos.description`) — `run_gates` was dead on any fresh DB |
| `b256dcd` | bucket-balanced read order (`next_reads.py`) + `status.py` |
| `d0e10c0` | **not mine** — swept the payoff-test amendment in under a signal-github message |

One push failed with `Failed to connect to github.com port 443 after 21115 ms`
and succeeded on immediate retry. As the previous handoff says: **retry before
concluding anything.**

Gitignored and deliberately not committed — they hold judgments about named
creators and the repo is public: `KNOWLEDGE.md`, `reports/` (including
`reports/extractions/*.json`, the 6 extractions), `data/`, `.venv/`.

**Those 6 extractions exist on this machine only and are not backed up anywhere.**
