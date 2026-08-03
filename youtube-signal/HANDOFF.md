# HANDOFF — youtube-signal

Phase 1 (retrieval) complete. 2026-08-02. Laptop `gianf`, residential IP.
Repo `github.com/vinexcleaning/trading`, project `youtube-signal/`.
Numbers and evidence: `reports/phase1_2026-08-02.md`.
Phase 0's own handoff is preserved at `reports/phase0_2026-08-02.md`.
**YouTube Data API quota consumed to date: 0 units.**

---

## 1. Step 1 outcome: **B (partial)**. No API key needed.

Keyless yt-dlp **can** restrict search to the past 12 months and **cannot** sort by
upload date.

- **Date filter works.** `sp=EgIIBQ%3D%3D` via a `/results?search_query=…&sp=…`
  URL. Verified against real upload dates: 10/10, 9/9, 10/10 within 12 months
  versus 9/10, 7/10, 8/10 for the unfiltered baseline; max age drops from
  23–36 months to 6–10. Jaccard vs baseline 0.47–0.67, so it returns a different
  set rather than reordering one. The window is rolling, not calendar-year.
- **Date sort is ignored.** `sp=CAI%3D` gives fraction-newest-first **0.593**, and
  the relevance baseline gives **0.593** — identical, against 0.5 chance. Adding
  sortBy to the filter token changes nothing (same set, Jaccard 1.0).
- `yt-dlp daterange` is not an alternative: under `extract_flat`, 0/10 entries
  carry an `upload_date`.

**Consequence:** F3 is a date-*windowed* relevance family, not a date-*ordered*
one. **Is an API key now needed? No — and probably not worth buying.** True
`order=date` would cost 800 of 10,000 daily units, but 7c shows F3 is already the
weakest and most redundant family (only 20.4% exclusive). Fix or cut F3 before
paying for it.

## 2. Premises tested

| # | Premise | Verdict |
|---|---|---|
| 1 | Keyless date-sorted search works | **PARTIAL** — filter yes, sort no (§1) |
| 2 | yt-dlp survives 30+ searches | **PASS** — 72 searches, 0 failed, 0 empty, no degradation |
| 3 | **Insider vocabulary beats beginner vocabulary** | **SUPPORTED** — 2.25× on equal footing |
| 4 | 18 months is the right cutoff | **DEFENSIBLE, NOT SPECIAL** — insensitive across 12–24 mo |
| 5 | The four channel IDs are correct | **PASS** — 4/4 resolve, 0 drift flags |

**Premise 2.** Mean results 25.0 first half vs 25.0 second half; mean latency
2.09 s vs 2.17 s. No throttling at 72 searches plus 470 video fetches plus 43
channel enumerations in one session.

**Premise 3 — the central hypothesis. Supported, and by more than the headline.**
On the raw definition F2's low-view yield is 26.4% vs F1's 15.6% (1.69×). But F3
carries the date filter and therefore pre-satisfies gate G2, so the headline
compares families on a gate one of them got free. Removing G2: **F2 39.2% vs F1
17.4%, ratio 2.25×.** The mechanism is reach, not precision — F2's pass rate is
*lower* than F1's (47.2% vs 75.2%), but 55.8% of what F2 retrieves is under 5,000
views against 17.4% for F1, a 3.2× difference.

**Premise 4 corrects Phase 0.** Phase 0 measured one channel, found 40/40 inside
18 months, and called the cutoff non-binding. Across a real retrieval set it drops
**174 of 466** (37.3%). But the age distribution is bimodal — 56.4% under 12
months, 27.3% over 36 — so any cutoff in 12–24 months yields materially the same
corpus. 18 is fine; it is not load-bearing.

**A Phase 0 finding that did not survive.** Phase 0 reported retrieval as
nondeterministic (two `ytsearch3` calls returned different videos). At top-25,
run-to-run Jaccard is **F1 0.835, F2 0.801, F3 0.884**, and 75.1% of the union
appeared in all three runs. That was a small-N artifact. The union protocol is
kept anyway — the 12.6% single-run tail is real and cheap — but single-run metrics
are not worthless, which is what Phase 0 implied.

## 3. The Step 7 numbers

**7a — recall 2 of 4.** Nates Tokens **YES** (F2 rank 3, F3 rank 4, **not F1**);
Trading with DaviddTech **YES** (F1 rank 0, F2 rank 19, F3 rank 0); Mind Math
Money **NO**; Patrick Dang **NO**. Per-family recall@25: F1 1/4, F2 2/4, F3 2/4.
All retrieved seed videos had stability 3/3.

The critical case landed the right way: **F1 missed Nates Tokens and F2 caught
him**, which is precisely the insider-vocabulary hypothesis. Retrieval is not
broken, so 7b is readable.

The two misses are large channels missed by *every* family including F1. Either
they are not really on this topic (Patrick Dang is a B2B sales creator; Mind Math
Money is trading-education/TradingView) or the query set does not cover their
sub-topics. **This run cannot tell which, and it should not be reported as a 50%
retrieval failure until it is.**

**7b — low-view yield.** F1 15.6%, F2 26.4%, F3 42.9% (headline).
G2-neutral: F1 17.4%, **F2 39.2%**, F3 42.9%. F2/F1 = 2.25×.
F3's lead is not trustworthy: its videos are all under 12 months old by
construction, and young videos have had less time to accumulate views, so part of
its low-view yield is youth rather than obscurity. F2 vs F1 has no such confound.

**7c — overlap. The strongest number in the report.** F1–F2 Jaccard **0.037** —
16 shared videos out of 446. The beginner and insider vocabularies retrieve almost
entirely different corpora. Exclusive share: F1 40.4%, **F2 66.8%**, F3 20.4%.
F3 overlaps both at ~0.25 by construction and is the family to cut or redesign.

**7d — census.** 72 searches / 198 s / 0 failures. 1,800 hits → **470 unique from
search** → 4,964 including expansion. Gates: PASS 263 (56.0%), STALE 117 (24.9%),
off-topic 52 (11.1%), no transcript 27 (5.7%), empty transcript 7 (1.5%),
unavailable 4 (0.9%). 43 channels expanded, 4,494 metadata-only rows added.

**Which components never fired: none of the gates.** Every gate rejected something.
Independently counted, 34 videos fail G1, 174 are over 18 months, 52 are off
topic. The one rule that has never fired is the **>5× channel drift guard** — 0
trips, which on this data is the correct answer rather than evidence it works.

## 4. Built vs. actually run on real data

| module | built | ran on real data |
|---|---|---|
| `retrieval.py` (paced/logged/throttle-instrumented search) | yes | **yes** — 72 searches, 470 video fetches, 43 channel enumerations |
| `queries.py` (F1/F2/F3) | yes | **yes** — 24 queries × 3 runs |
| `run_retrieval.py` (union protocol, Jaccard) | yes | **yes** |
| `gates.py` G1/G2/G3 | yes | **yes** — 470 videos, all gates fired |
| `run_gates.py` + channel expansion | yes | **yes** — 43 channels, 4,494 rows |
| `db.py` schema incl. transcript cache | yes | **yes** — 439 transcripts cached |
| `validate_g3.py` / `validate_g3b.py` | yes | **yes** — 64 videos judged by hand |
| `measure.py` / `measure_addendum.py` | yes | **yes** |
| `channels.py` drift guard | yes | **ran, never triggered** (0 trips) |
| `quota.py` | yes (Phase 0) | **NO — still has never guarded a real API call** |
| F4 tool-name family | **not built** | — (correctly deferred to Phase 3) |

Nothing for Phase 2 exists: no scoring, no S/H/C, no n-check, no extraction.

## 5. What is wrong, unfinished, or untrusted

1. **G3's shipped error rate is 79.2% agreement, precision 0.833, recall 0.769**
   (holdout, n=24, disjoint from the sample used to fix it). It is a lexicon
   classifier, not the LLM the brief specifies, because no LLM API key exists on
   this machine. **Roughly 1 in 5 gate decisions disagrees with a careful human.**
   Every 7b number inherits that error.
2. **Two G3 defects found by the holdout are NOT fixed**, deliberately — fixing
   them would leave a classifier with no clean holdout left to measure it on:
   - The off-topic marker `recipe` fires on the idiom **"a recipe for disaster"**,
     which suppressed a correctly-identified quantitative-trading video. The whole
     "a negative term overrides a core term" rule is fragile and should probably go.
   - `CORE` has `trading bot` but not **`trading agent` / `AI agent`**, so
     *How To Build A Self-Improving AI Trading Agent* was dropped as off-topic.
     The vocabulary has moved and the lexicon has not.
3. **The on-topic boundary is undefined in the brief, and that causes more
   disagreement than the bugs do.** Both holdout false positives were competent
   *discretionary* trading videos. I judged manual chart-reading education off
   topic because the topic is prediction markets / bots / algorithmic trading;
   the classifier counts them on topic because they say "backtest". Someone has to
   decide which it is — this is a specification gap, not a code defect.
4. **Channel expansion at ≥2 passing videos is too loose.** It admitted Bloomberg
   Television, OddsJam Sports Betting Picks and DGFantasy — Prizepicks, each
   contributing ~200 uploads. **Roughly 800 of the 4,494 expansion rows (18%) come
   from channels that are not about this topic**, and they go straight into Phase 2's
   input.
5. **The 2/4 recall is unexplained** (see §3). It is the difference between "the
   query set has a coverage hole" and "two of the four seeds never belonged".
6. **`quota.py` has still never guarded a real API call.** Its halt logic is proven
   against a scratch DB; the integration is unproven because there are no API calls.
   If Phase 2+ never needs a key, this module should be deleted rather than kept as
   reassuring dead code.
7. **Expansion rows have no `upload_date`** — flat enumeration does not carry it.
   4,494 of the 4,964 videos are therefore un-gateable until Phase 2 fetches them
   individually (~2.2 s each ⇒ **~2.7 hours** if all are fetched). Phase 2 needs a
   selection rule before it starts, not a full sweep.
8. **`is_generated` disagreement** between the two transcript paths (noted in
   Phase 0) is still unresolved. Cosmetic unless H-scoring weights manual captions.
9. F3's low-view advantage is confounded with video age (§3) and is not evidence
   for recency as a retrieval strategy.

## 6. The single next thing to do

**Decide the on-topic boundary, then re-validate G3 against it — before any Phase 2
scoring runs.**

It is first because every downstream number is conditioned on it. G3 currently
disagrees with a careful human on ~1 video in 5, and the largest single cause is
not a bug but an undecided question: *does discretionary, manual trading education
count as on topic for this project, or only prediction markets, bots and
systematic method?* The bugs in §5.2 are twenty minutes of work; the boundary
question is the one that changes what the corpus is.

Concretely: (a) write the boundary down as a one-paragraph rule, (b) fix the
`recipe` idiom and add the `trading agent` vocabulary, (c) draw a **third** sample
disjoint from both existing ones and re-measure, (d) only then re-run
`reclassify.py` — it works from cached transcripts and costs seconds, so this is
cheap to iterate.

The corpus is already in hand: 470 gated videos, 439 cached transcripts, 263
passing, 4,964 known videos across 43 expanded channels. Phase 2 is not blocked on
retrieval; it is blocked on knowing what counts.
