# HANDOFF — youtube-signal

Phase 2 (extraction) **BLOCKED AT STEP 0**. 2026-08-02. Laptop `gianf`.
Repo `github.com/vinexcleaning/trading`, project `youtube-signal/`.
Numbers and evidence: `reports/phase2_2026-08-02.md` (gitignored, local only).

YouTube Data API quota consumed to date: **0 units.**
LLM cost incurred: **$0.00.** The read never ran.

---

## 1. Step 0 outcome: **FAIL. No LLM access. Cost incurred $0.**

`ANTHROPIC_API_KEY` is absent from the process environment, from user and machine
scope, and from every `.env` candidate.

What *is* present is `CLAUDE_CODE_OAUTH_SCOPES` and `ANTHROPIC_BASE_URL`: this
session authenticates through Claude Code's subscription OAuth. **That is exactly
the credential that does not carry API credit.** A Pro/Max subscription and
Anthropic API billing are separate products with separate balances. The
subscription grants no API key and no API credit, and the session's OAuth token is
not a substitute for one.

No lexicon was substituted for the read.

**Cost of the read that did not happen**, measured from the actual cached
transcripts of the actual 60 selected videos rather than an assumed average:
611,687 input + 120,000 output tokens → **$3.64 on Sonnet** (range $2.91–4.36),
$1.21 on Haiku 4.5, $18.18 on Opus. Mean 10,195 input tokens per video, which
matches the brief's ~10k guess almost exactly.

To unblock: `console.anthropic.com` → **Billing, add credit (this is separate from
any subscription; $5 covers it)** → **API keys → Create key** → paste into
`youtube-signal/.env` as `ANTHROPIC_API_KEY=sk-ant-...`. Then
`python src\read_video.py --dry-run` to inspect the assembled prompt for free,
then run two videos, check the JSON, then the rest.

## 2. Premises tested

| # | Premise | Verdict |
|---|---|---|
| 1 | An LLM is reachable from this machine | **FAIL** — no key. Everything below it is untested. |
| 2 | Substance can be scored from a transcript at all | **UNTESTED** |
| 3 | Extraction beats watching | **UNTESTED** |
| 4 | **S separates F2 content from F1 content** | **UNTESTED** |

**Premise 4 is the one that matters and it is untested.** Phase 1 proved F2
retrieves *different* videos from F1 (Jaccard 0.037) and more low-view ones
(2.25×). Whether they are *better* videos is exactly what S was supposed to
answer, and no S component has ever fired on real data. The retrieval win has not
been cashed out. Do not let the Phase 1 result stand in for it.

## 3. The Step 5 numbers

**5a, 5b, 5c: cannot be reported.** All three are computed from Step 2 scores.
No S or H component has fired even once. Component fire rates are unknown, S is
unmeasured against family, and compression is unmeasured.

**5d, the LLM-free parts:**

| | Phase 1 end | now |
|---|---|---|
| search-retrieved, gated | 470 | **718** |
| PASS | 263 | **369** |
| STALE_G2 | 117 | 184 |
| DROP_G3 off topic | 52 | 84 |
| DROP_G3 discretionary (new) | — | 19 |
| DROP_G1 no transcript / empty | 27 / 7 | 41 / 14 |
| cached transcripts | 439 | **683** |
| total known videos | 5,212 | 11,277 |

**G3 reclassification under the new boundary:** 3 previously-passing videos moved
out of scope as discretionary; the recall retune recovered 7 from off-topic. 13
more were reclassified from off-topic or stale into discretionary.

**G3 after the retune**, scored against all 64 hand-judged videos:

| classifier | sample | agreement | precision | recall |
|---|---|---|---|---|
| v2 (Phase 1) | holdout, n=24 | 79.2% | 0.833 | 0.769 |
| **v3 (Phase 2)** | holdout, n=24 | **83.3%** | 0.765 | **1.000** |
| v3 | combined, n=64 | 85.9% | 0.809 | **1.000** |

The retune bought what it was meant to: **zero false negatives across all 64**,
precision traded down as intended, agreement up anyway. Both samples have now
informed the lexicon's design, so these are **upper bounds, not a clean holdout**.

**F2B — 12 new insider terms:** 304 videos, 248 new to the corpus, **88.5%
exclusive**, Jaccard **0.041** vs F2 and 0.046 vs F1, run-to-run 0.803. A second
batch of insider terms is nearly as disjoint from the first batch as the first was
from beginner vocabulary. Corpus size scales with insider term count. Two terms
returned fewer than the 25 requested — `kalshi websocket feed` (11) and
`negative risk polymarket negrisk` (6) — meaning YouTube has almost no content
that insider. Whether that is the terms or the platform is a judgment for you.

**Read set:** 60 videos by a seeded, stored, re-runnable rule. 13 F1-only, 16
F2-only, 14 F2B-only, 17 multi; 14/15/17/14 across the four view bands; 48% under
5,000 views; 38.0 hours across 58 distinct channels.

**n-check:** verified against the brief's worked example. 55% over n=33 →
`INDISTINGUISHABLE FROM NOISE`, normal SE 8.66 pp against the brief's ~8.7 pp.
Added `n_needed` beyond spec: that claim would need **n = 389** to clear 50%.

## 4. Built vs. actually run on real data

| module | built | ran on real data |
|---|---|---|
| `gates.py` v3 — boundary + recall retune | yes | **yes** — 718 videos |
| `reclassify.py` — re-gate from cache | yes | **yes** — 466 videos, seconds, no network |
| `run_f2b.py` — F2B retrieval | yes | **yes** — 36 searches, 304 videos |
| `score_g3_v3.py` — validation | yes | **yes** — 64 hand-judged videos |
| `select_read_set.py` — the 60 | yes | **yes** |
| `ncheck.py` — Wilson n-check | yes | **yes**, against the brief's example — but **never on a real extracted claim**, because there are none |
| `cost_estimate.py` | yes | **yes** — real transcripts |
| `make_worksheet.py` | yes | **yes** — 15 videos |
| `expansion_v2.py` | yes | **yes** — and it does not work, see §5 |
| `db_phase2.py` — scores/tools/claims/methods/watch_segments | yes | **schema only. Every one of those tables is EMPTY.** |
| `read_video.py` — the Step 2 read | yes | **NO. NEVER EXECUTED. Unvalidated below the API call.** |
| Step 4 artifact resolution | **not built** | — (nothing to resolve) |

## 5. What is wrong, unfinished or untrusted

1. **The whole point of Phase 2 did not happen.** No scores, no tools, no claims,
   no methods, no watch segments. Five tables exist and all are empty.
2. **`read_video.py` has never run.** The prompt, the JSON schema, the evidence
   validator, the totals and the verdict function are all written and none has
   ever seen a model response. Treat it as a draft. The first real run should be
   two videos, inspected by hand, before the other 58.
3. **The specified channel-expansion rule does not work, and I applied it anyway
   because it was a decision, not a suggestion.** The ≥50%-of-retrieved bar pruned
   **0** channels and admitted **46** more, taking the expansion corpus from 4,494
   to **10,559** rows — it added Fireship, freeCodeCamp.org, a16z crypto and
   Pinnacle. The denominator is wrong: it measures the on-topic share of the two
   videos we happened to retrieve, not of the 200-upload catalogue expansion pulls
   in. Bloomberg scores 100% because both its retrieved videos genuinely were
   about prediction markets.
   The obvious alternative is **worse**: catalogue specialisation prunes **Nates
   Tokens**, whose catalogue is 12% on topic and whose 12% is the entire reason he
   is the anchor case. A ratio cannot distinguish "narrow specialist" from "broad
   channel with a valuable seam". **Recommend reverting expansion to the Phase 1
   state and deferring the question until the LLM can score catalogue titles.**
   The rows are un-gated candidates and never enter the read set, so the noise
   costs nothing yet.
4. **The 22-hour video breaks the one-call-per-video design.** ~273,520 estimated
   tokens against a 200k context window. It is the only video over — next largest
   is 19,550 — and it is the video Step 5c was going to use for the compression
   test. Chunk it, or fall back to the 91-minute second-longest.
5. **G3's numbers are upper bounds.** Both hand-judged samples have now shaped the
   lexicon. A third disjoint sample is needed for an honest figure. Recall 1.000 on
   contaminated data is not recall 1.000.
6. **A concurrent session in this same clone committed and pushed my staged work.**
   All 28 Phase 2 files landed in `c3a0a21`, whose message describes an unrelated
   mlb latency study. Nothing was lost; `2ff63a2` records what happened. Two
   sessions in one clone will keep doing this to each other unless both stage
   explicit paths instead of `git add -A`.
7. **That push also published Phase 0 and Phase 1 commits I had deliberately held
   back**, and those commits contain `reports/` from before it was gitignored. The
   reports are gone from the tip but remain in public history. They hold topic
   classifications and mild channel characterisations only — **no honesty scores
   exist, because Step 2 never ran** — but the exact mechanism the gitignore
   decision was meant to prevent has already fired once. If that history matters,
   it needs a rewrite and force-push on a public repo, which is your call and not
   something I will do unasked.
8. **The n-check has never seen a real claim.** It is verified against the brief's
   example and synthetic cases only.
9. **13 F1-only videos is thin** for the 5b comparison. It will give a mean, not a
   confident one.

## 6. The single next thing to do

**Buy $5 of Anthropic API credit, add the key, and run the read on two videos.**

Everything else in this project is now waiting on that one input. The corpus is
built (718 gated, 369 passing, 683 transcripts cached locally), the read set is
selected and stored, the prompt is written, the n-check works, the cost is known
to be $3.64. Nothing further can be learned about premises 2, 3 or 4 — including
whether the entire Phase 1 retrieval win produces better videos and not merely
different ones — without a model reading a transcript.

Two videos first, not sixty: `read_video.py` has never executed, and the fastest
way to find out that the JSON schema or the evidence rule is wrong is to look at
two responses by hand before spending the other $3.50.
