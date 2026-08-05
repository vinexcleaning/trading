# TASK 1 — the rubric, measured against known answers

**The headline: the model read is the instrument, and the lexicon is a ranker
that should never have been allowed to emit a verdict.**

On 24 cases whose right answer is fixed by something outside the rubric:

| instrument | exact | mean ordinal error | false RECOMMEND | false REJECT | stale caught |
|---|---|---|---|---|---|
| **A — the pipeline as it actually ran** | **17/23 = 74%** | 0.39 | 2 | 1 | **0 of 2** |
| **B — the mechanical lexicon** | **10/24 = 42%** | 0.92 | 6 | 3 | **0 of 2** |
| **C — rubric v2 (the fix)** | **13/24 = 54%** | 0.71 | 5 | 1 | **2 of 2** |

Detail, matrices and the per-case components:
`reports/T1_rubric_validation.md` (gitignored — it names creators).
The overfitting check: `reports/T1_population_check.md`.

---

## How the test set was built, and why it is not an opinion poll

A rubric validated on cases its author picked is validating its author's taste.
The inclusion rule here is that **a case enters only if its label is decided by
something outside the rubric**, and the file records which:

| | what fixes the label | cases |
|---|---|---|
| **ARITH** | arithmetic on numbers the source itself states | 4 |
| **LIVE** | an HTTP or API check runnable today | 6 |
| **EXTERN** | a fact this repo has already primary-sourced | 6 |
| **SELFCON** | an internal contradiction inside the source | 8 |

Where the evidence fixes a **bound** rather than a point, the label is a band
and the reason is tabled. 17 of 24 are banded. **Widening a band can never
manufacture a pass on the two metrics that decide anything** — false RECOMMEND
and false REJECT are judged against the band's own edges.

Ground truth is two axes, not one. `gt_action` is ordinal —
`REJECT < DISCOUNT < ABSORB < RECOMMEND` — and `gt_stale` is separate, because
**a stale tutorial is not dishonest**. Its concepts may be worth absorbing.
What it must never be is recommended.

### ⚠ One of the brief's five named cases does not exist in this repo

> The brief describes "a creator showed a bot with day 1 and day 3 results and a
> public wallet: 33 trades, $23.53 total profit; summing the visible winners
> gave +$127, so ~$104 of losses sat below the fold, and the wallet's last trade
> was 2 months ago."
>
> **No transcript in either youtube-signal database contains `23.53`.** No
> tracked or untracked markdown in `youtube-signal`, `social-signal`,
> `signal-github` or `bot-hunt` contains it either. The nearest thing in any
> corpus is a **fully disclosed** break-even bot (34 buys, 34 sells over one
> day, net +8 cents, wallet shown) — the honest version of the same shape, not
> the incomplete-disclosure one.
>
> It is recorded as missing rather than reconstructed from memory. Two
> verifiable cases were substituted in its place.

The other four named cases are all present and all four were used.

---

## What the measurement found

### 1. The known rubric failure is already fixed — and the fix works

The brief names Part Time Larry's Kalshi + LLM build as scoring **S=3 H=9 →
auto-SKIP** with working code, a public repo and a real itemised account.

**That is no longer true.** The `B` (build) axis was added to
`youtube-signal/src/read_video.py` on 2026-08-03 and the video was rescored:
**S=3 B=10 H=9 → BUILD_AND_RECOMMEND.** Kept in the test set as a regression
case, not re-fixed. Across the whole 38-video read set there is now **not one
SKIP**, which is a different problem (see 4).

### 2. Staleness was invisible, and it was invisible by construction

**0 of 2 stale cases were flagged, and the reason is that no component in
either instrument asks whether the thing being taught still exists.** Both
instruments got a full mark for a tutorial teaching a dead library.

The clearest case: a Polymarket CLOB API tutorial published 2026-02-04, which
the pipeline recorded as **BUILD_AND_RECOMMEND**. Checked against the GitHub
API on 2026-08-04:

| | |
|---|---|
| `Polymarket/py-clob-client` | **archived**, 1,235 stars, last push 2026-05-25 |
| `Polymarket/clob-client` | **archived**, 514 stars |
| `Polymarket/py-sdk` | alive, pushed **2026-08-04** |
| `Polymarket/agents` (3,761 stars) | **archived**, cold since 2024-11-05 |

> **The trap that makes this undetectable by a reader: `pip install
> py-clob-client` STILL WORKS.** PyPI serves 0.34.6 (uploaded 2026-02-19) while
> the GitHub repository is archived. Nothing errors. Nothing warns. A learner
> following the tutorial gets a clean install of an unmaintained v1 client and
> finds out at the order endpoint.

v2 adds a `T` currency **gate** — not a score, because currency is not a
quantity you trade against substance. `src/verify_tech.py` rebuilds the
identifier table from the GitHub and PyPI APIs on every run, so the list cannot
rot the way a hand-written one does. **2 of 2 caught**, and across the whole
5,567-document population it flags **24 documents (0.43%)**, each naming the
identifier and the check that killed it.

### 3. Components fire on spans that say the opposite

Two distinct polarity bugs, both found by reading rather than by scoring:

- **Naming a cost is not accounting for one.** S1 (+3, the top-weighted
  component) fires on *"I haven't added fees or slippage yet"* — the sentence
  stating the cost side is **missing**.
- **A source that quotes in order to condemn is scored as the thing it
  condemns.** A post warning about strategy sellers scored **H = −6** on the
  language it quotes, and was SKIPped.

v2 adds three guards — negation, condemnation, and third-party attribution
(*"Virtu made $1.597B"* is reporting, not boasting). A fourth, **debunk**
(a number stated in order to refute it), was added because the walk-forward
video's whole argument is that its own in-sample 1,500% is fake, and the
guard-less rubric penalised it for saying so.

> **Each guard trades one error for another and the net gain is small.** The
> debunk guard fixed one case and broke another (a video whose unsupported
> "around 18% last month" now escapes the discount). False RECOMMEND went 6 → 5,
> not 6 → 0.

### 4. Two components are unreachable, three are intercepts — and the two implementations disagree about which

Measured on the populations, not on the test cases:

| | LLM read, n = 38 | lexicon, n = 4,432 posts |
|---|---|---|
| **never fires** | **H9 (0), H10 (0)** | **H1b (0)** |
| effectively never | H7 5%, H8 11% | B5 0.1%, H9 0.05%, H3 0.5%, H4 0.9% |
| **near-universal** | **S5 95%, S4 92%, H4 87%** | — |

Three things fall out of that table:

- **`H1b` has a weight and no detector.** `H_WEIGHTS` assigns it +1 and
  `PATTERNS` has no `H1b` key, so it is unreachable in 4,432 posts — and the
  `MUTEX` rule that suppresses it when H1 fires can never trigger.
- **`H10` cannot be awarded by the model at all**, because it appears nowhere
  in the prompt (see 5).
- **S5 at 95% and H4 at 87% are intercepts, not signals.** They contribute a
  point to almost every score, which is most of why `S ≥ 4` ("informative") is
  nearly automatic and why **38 reads produced zero SKIPs**. v2 scores them 0,
  keeps them as required evidence, and lowers the threshold by the same amount
  so ranking is unchanged and only sources that *lacked* the intercept stop
  being penalised for it.

> **The same component name means different things in the two implementations.**
> H4 fires on 87% of videos and 0.9% of posts. A score is therefore **not
> comparable across corpora**, which matters directly for `social-signal`'s
> cross-platform reputation table, since it joins both.

Redundancy: the strongest pairs are `B1↔B3` (φ +0.65), `B2↔B3` (+0.64) and
**`S1↔S4` (+0.62, co-firing on 31 of 38)** — the cost-side and mechanism
components are largely measuring the same thing. n=38, so this is a redundancy
screen, not a hypothesis test.

### 5. The prompt does not declare 6 of the 21 components the code scores

Checked mechanically against the `RUBRIC` string:

> **`B1, B2, B3, B4, B5` and `H10` appear nowhere in the prompt**, and the JSON
> schema it asks the model to return has **no `b_components` key at all** — yet
> `validate_response()` and `totals()` both read one.

The B axis was added to the code and never to the prompt. Every B score in the
database was produced by a session that knew about B from somewhere other than
the prompt it was following. `rubric_v2.PROMPT_V2` declares all 21.

### 6. No verdict in the database can be recomputed from the database

`read_video.verdict()` takes `teaching_quality` — a free-text model judgment —
and the `scores` table has no column for it. Neither does it store duration.
**The RECOMMEND branch of the routing depends on an input that was never
persisted.** This is not fixed by any rubric change; it is fixed by storing the
field, which `PROMPT_V2` now marks as required.

### 7. The ceiling, stated plainly

v2 improves the lexicon from 42% to 54% and takes staleness from 0/2 to 2/2.
**It does not get past about half, and more pattern work will not.** The
remaining failures share one shape: *the source's own words are honest-looking,
and the dishonesty is in the relationship between two numbers.*

- A "+1,560% ROI" headline that is paper, sitting in the same video as a live
  account that lost 70% in a day. Both numbers are stated. The lexicon sees a
  sample size ("500 trades") and cannot see that it belongs to the paper run.
- A 96.83% win rate whose subset `n` is never stated, only the 12,272 total.
  **What is absent cannot be pattern-matched.**
- Satire. A parody post enumerating every beginner error scores ABSORB. **No
  satire detector was written**, because building one from a single example is
  the overfitting this programme exists to catch. It is recorded as a limit.

**Presence of a regex in a 20,000-character transcript is not evidence about a
document.** That is the structural ceiling, and it is why the lexicon's job is
to decide what gets read, not to decide what is true.

---

## Was v2 a fix or a memorisation of 24 cases?

Run over **5,567 documents** neither rubric was tuned on — every scored Reddit
post plus every transcript in both video corpora:

| action | v1 lexicon | v2 | change |
|---|---|---|---|
| REJECT | 3,944 (70.8%) | 3,968 (71.3%) | +24 |
| DISCOUNT | 301 (5.4%) | 305 (5.5%) | +4 |
| ABSORB | 905 (16.3%) | 859 (15.4%) | −46 |
| RECOMMEND | 417 (7.5%) | 435 (7.8%) | +18 |

**594 of 5,567 = 10.7% changed action.** A targeted fix moves a tenth of a
corpus; a rewrite moves half. The largest single transition is
`ABSORB → REJECT` (183), which is the intercept removal doing exactly what it
was supposed to do: sources that scored 4 on S5 + S4 alone no longer clear the
informative bar.

## What is NOT recommended on the strength of this

**Do not rescore the existing corpora with v2.** The 38 read videos were scored
by a model against the v1 prompt; rescoring their stored components under v2
weights would produce numbers that are neither v1 nor v2 reads. v2's prompt
applies from the next read forward, and the boundary should be recorded in the
database.
