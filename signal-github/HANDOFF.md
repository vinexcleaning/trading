# signal-github — HANDOFF

Session of **2026-08-03**. Ran unattended start to finish. Nothing here is a
plan; everything is either a measurement or a stated gap.

---

## 1. Reachability, and the real rate limits

Measured from response headers, not documentation (`reports/step0.md`,
`reports/step0.json`). No token was present, none was created, none was
requested.

| resource | advertised | actual, unauthenticated |
|---|---|---|
| `core` REST | 60/hour | **60/hour — the binding constraint on the whole project** |
| `search` | 10/minute | 600/hour. Plentiful. Carries retrieval. |
| `code_search` | the `rate_limit` endpoint advertises **60/minute** | **401 Unauthorized.** The quota table lies; the endpoint is the truth. |
| `graphql` | 0 | 0 |
| `raw.githubusercontent.com` | — | unmetered. 861+ file fetches, no throttling seen. |
| `sourcegraph.com/.api/search/stream` | — | works unauthenticated, free |
| `github.com/*/network/dependents` | — | HTTP 200 but the repository rows render client-side; the HTML body carries none of them |

Three consequences shaped everything downstream:

1. **Code search is blocked.** Substituted with Sourcegraph's public index,
   labelled `F2_CODE` with source `sourcegraph` everywhere, never as GitHub code
   search. It is not like-for-like: it indexes a subset of GitHub and excludes
   forks by default.
2. **The dependents graph is not scrapeable**, so "repos that depend on
   py-clob-client" was substituted with forks of the client libraries, labelled
   `LIB_FORK`.
3. **60 core calls/hour caps depth, not breadth.** Retrieval and gating cost
   almost nothing; the git-tree call is what rations the project. Deep fetch was
   therefore split into a 1-call tier (whole S score, 60 repos/hour) and a
   4-call tier (credibility, 15 repos/hour).

If a `GITHUB_TOKEN` is ever put in the environment, `gh.py` picks it up with no
code change: core goes to 5,000/hour and code search unblocks. That single change
is worth more than any other improvement listed here.

---

## 2. Premises tested, and the verdicts

### Premise 1 — do good public Kalshi/Polymarket bots exist at all?

**Yes, but exactly one is unambiguous, and it does not do what you would expect.**

`warproxxx/poly-maker` — 1,427 stars, MIT, 67 files, 83 tests, mypy strict, 37
commits over a 465-day span, 3 contributors, 19 closed issues, last push
2026-07-09, already migrated off the archived v1 client. A maker-only two-sided
quoting bot with an inventory skew, a regime machine, and a risk manager with a
daily-loss kill switch. It makes **no performance claim at all** and its README
opens with a warning that market making on Polymarket can lose money.

**It has no backtest.** Its own README says so: *"Not yet built: a replay
backtester over the captured journals."*

The nearest thing to a rigorous backtest in the corpus,
`evan-kolberg/prediction-market-backtesting` (1,094 stars, 254 files, built on
NautilusTrader), publishes exactly one quantified result and it is a **negative**
one about someone else's trades — see §3.

So the honest shape of the answer: **excellent machinery exists; a demonstrated
profitable strategy does not.** Of 40 repos deep-fetched, **not one publishes a
backtest artifact supporting a profit claim about its own strategy.**

### Premise 2 — does the S/H scoring transfer from transcripts to code?

**The S half transfers badly and the H half was not portable at all.**
(`reports/step3b_rescore.md`)

Ported literally, **19 of 40 repos scored 9 or 10** — a ceiling, not a ranking.
A strict rescore over the same cached files drops that to **3 of 40**.

| component | literal fire rate | strict | why the literal version over-fires |
|---|---|---|---|
| S1 cost side | 88% | 68% | `spread` is ordinary orderbook vocabulary. Every repo that reads a book says it. Strict requires a cost term inside an arithmetic expression. |
| **S2 backtest vs live** | **68%** | **20%** | Matching `backtest`/`live`/`order` against *file paths* fires on nearly everything. Strict requires a backtest module plus real order-submission calls in a different file. This is the component that mattered most and failed worst. |
| S3 tests/results | 72% | 68% | Transfers well. A tests directory and a committed CSV are unambiguous. |
| **S4 mechanism** | 80% | 52% | **The worst transfer, and unfixable by keyword.** An LLM-written README hits every mechanism keyword while explaining nothing. Keyword presence cannot measure explanation. |
| S5 runnable | 85% | 85% | Transfers well. Pinned versions and an entry point are objective facts. |

**The H (honesty) scale did not transfer and was not attempted.** It was built for
a person speaking: urgency language, undisclosed products, claims without a
denominator. A repo's honesty lives in different places — whether the README's
claim has a committed artifact, whether the last commit is substantive or a
README tweak, whether the author states what is not built. Those were computed
separately as a `trust_me_bro` shape and a credibility axis rather than forced
into an H score. **Anyone extending this should not try to port H; build the
repo-native equivalent.**

A concrete detector failure worth keeping: the first strict S2 scored
`warproxxx/poly-maker` a 2 by matching a for-loop plus the word "replay" in a
websocket client — while that repo's own README says a backtester is not built.
**The repo was right and the detector was wrong.** The loop heuristic was removed
(`src/rescore.py`).

### Premise 2b — can the strict scorer replace reading? No, and here is the proof

`alsk1992/CloddsBot` and `warproxxx/poly-maker` **both score 10/10 on the strict
scale.** Both genuinely have a backtest-shaped module, a test directory, pinned
dependencies and a mechanism-bearing README, so every computed component fires
for both. Reading them takes ten minutes and they are opposites:

| | poly-maker | CloddsBot |
|---|---|---|
| files / venues / strategies | 67 · 1 · 1 | 797 · 17 · "118+" |
| built over | 465-day commit span | 12 days, for a hackathon |
| backtest | none — **and the README says so** | a fully documented API, **no result from it anywhere in 797 files** |
| performance claim | none; README opens with a loss warning | none, but "10.7k clones in 14 days" sits where evidence would go |
| fee defaults | reads live per-market fee bps from Gamma | **`maker: 0, taker: 0`** — wrong on both venues |

The scorer cannot see any of that. It counts artefacts; it cannot tell a
specification from a result, and "documents the correct methodology" and "applied
the correct methodology" leave identical traces on disk. **That gap is the
argument for the read step**, and it is why `reports/repo_defects.json` exists as
a separate output: three defects in two well-scoring repos, none of them visible
to any computed component.

The most costly one is worth stating on its own. CloddsBot's default backtest
config is `fees: {maker: 0, taker: 0}` with the comment "0% taker fee (Polymarket
most markets)". As of 2026-08-03 Polymarket taker fees are 0.04–0.07 by category
and only geopolitics is free; Kalshi is `ceil_to_cent(0.07·qty·p·(1−p))`, not the
flat 1.2% the same file suggests. **Anyone running that backtest out of the box
gets a strategy that pays no fees at all** — the exact trap the other 1,000-star
repo in this corpus documents in `docs/execution-modeling.md`.

### Premise 3 — do stars correlate with substance?

**Corrected. The earlier answer of a flat No came from too small a sample.**
(`reports/step3_rank.md`)

| n | stars vs S_strict | p |
|---|---|---|
| 40 | −0.019 | 0.91 |
| 105 | **+0.241** | **0.013** |

At 40 repos the correlation was indistinguishable from zero and I reported that stars carry no information. At 105 it is a **weak but statistically significant positive** relationship. The practical advice is unchanged — rho 0.24 explains about **6% of the variance**, so sorting by stars still tells you almost nothing about which repo has substance — but the strong claim was wrong and is withdrawn.

The report now DERIVES this verdict from the numbers instead of asserting it. The old text was a hardcoded string that could not notice it had stopped being true.

Eight repos with 50+ stars score ≤3 on the strict scale. And the cleanest
demonstration is not statistical at all: **`Polymarket/py-clob-client` has 1,234
stars and is archived (last push 2026-05-25); its live successor
`py-clob-client-v2` has 163.** Stars measure accumulated history, so any
popularity-ranked recommendation points at the dead library.

Same result as YouTube, where views did not track substance either.

### Premise (unlisted) — do beginner and insider vocabularies stay disjoint on code?

**Yes, and almost identically.** F1 returned 964 repos, F2 returned 1,147, 67 in
both — **Jaccard 0.033** over 3,133 repos. YouTube measured **0.037** over 446
videos. The code-search axis found 47 repos of which **41 were found by neither
family**.

---

## 3. The numbers, including the bad ones

| stage | number |
|---|---|
| unique repos retrieved | **3,133** |
| — by F2 insider search | 1,147 |
| — by F1 beginner search | 964 |
| — by topic search | 785 |
| — forks of the client libraries (`LIB_FORK`) | 317 |
| — forks of the 72M-trade dataset (`SEED`) | 188 |
| — by code search (Sourcegraph) | 37 |
| gate PASS | 2,441 |
| gate STALE (kept, never deleted) | 121 |
| gate DROP | 571 |
| — G3 off topic | 472 |
| — G3 generic terms only, no venue named | 410 (flagged, not dropped) |
| — G1 empty repo, 0 KB | 99 |
| **deep-fetched and scored** | **105** |
| of which credibility metrics fetched | **40 (all of them)** |
| **read in full** | **9 — the entire top 10 by strict score, bar one** |
| repos scoring 9–10 strict | 3 |
| repos with a backtest module AND separate order-submission code | **8 of 40 (20%)** |
| repos committing a backtest artifact behind their own strategy | **1 of 40** (`oracle3`) |
| ...and whether that artifact supports the strategy | **no — its own performance block reports Sharpe −1.57, profit factor 0.95** |
| strategies extracted that model costs at all | **5 of 14** |
| defects found only by reading (3 in 2 well-scoring repos) | `reports/repo_defects.json` |
| **"trust me bro"** — a results claim, <10 commits, no artifact | **3 of 40** |
| API spend | 8 core + 58 search for retrieval; ~60 core for the tree tier; 861 raw; 13 sourcegraph |

## 3b. Two defects in THIS pipeline, found late and both corrected

Recorded here rather than quietly patched, because reports were already written
against the wrong numbers.

**1. Silent data corruption in `fetch_repo.py`.** `fetch_one` wrote `fetched=1`
even when the git-tree call returned nothing, and the tree selector picked rows
`WHERE fetched=0` — so a failed row was excluded from retry *forever* and still
counted in the scored total, with every S component NULL. When the 60/hour core
budget ran out mid-run this poisoned **266 rows**: the database reported **358
repos scored when only 92 had a real file tree**, a 74% overstatement. The
affected repos were not empty — several are 5–80 MB with a valid
`default_branch`, and re-querying one by hand returns HTTP 200 with a full tree.

Fixed: an empty tree for a repo with `size_kb > 0` is now stored as `fetched=-2`
(retryable) with no scores written, and the selector accepts `fetched IN (0,-2)`
so an interrupted run resumes instead of losing rows. All 266 were reset and
re-queued. **A silent failure that inflates a denominator is worse than a crash,
because every rate computed over it still looks fine.** It was caught only by
noticing that 358 was implausibly fast for a 60/hour budget.

**2. `rank.py` asserted its conclusion instead of deriving it.** The premise-3
verdict — "stars carry no information about whether a repo has substance" — was
a hardcoded string. It was true at n=40 and became false at n=105, and a string
literal cannot notice that. It now derives the verdict from rho and p, and
prints the n=40 → n=105 movement alongside it so the instability is visible
rather than hidden. See the corrected Premise 3 above.

Two further pipeline defects are in `reports/repo_defects.json`: gate G3 admits
large off-topic repos on one incidental README mention (both large README-only
passes were false positives), and the `artifact_behind_claim` detector runs about
40% precision — 3 of 5 flagged artifacts are a markdown write-up, an alert log
and charts of quoted odds, none of them a backtest.

The headline "not one repo proves its own strategy makes money" survives all of
this **because the five flagged repos were read**, not because the detector said
so. That is the whole argument for the read step, stated once more.

The bad numbers, stated plainly:

- **40 of 2,562 gated repos were deep-fetched. That is 1.6% coverage.** The
  ranking below the top 40 is prescreen-ordered, not scored.
- **9 repos were read in full**, out of 40 scored and 2,562 gated. That covers
  the whole top 10 by strict score except `almanak-co/sdk`. Reading is where
  every one of the five entries in `reports/repo_defects.json` came from, and
  where the single most important finding of the project came from — see below.
- **77 repos were dropped because no README could be fetched** at `README.md` or
  `README.rst` on the default/main/master branch. A repo with an on-topic
  codebase and no README is invisible to G3. Real false-negative channel.
- The `kalshi.com` domain returned **HTTP 429 to every request**, including its
  own fee-schedule PDF and member agreement, from both WebFetch and curl with a
  browser user-agent. **The Kalshi legal terms were never read.**
- `polymarket.com/tos` returns only page scaffolding to a non-browser client.
  **The Polymarket legal terms were never read either.**

---

## 4. What was built vs what actually ran on real data

**Built and run end to end on live GitHub data:**

| file | what it did |
|---|---|
| `src/gh.py` | 4-transport cached HTTP layer; every response on disk, re-runs free |
| `src/step0_reach.py` | 8 live probes; produced the rate-limit table above |
| `src/queries.py` | F1/F2/F2_CODE families, client libs, topics |
| `src/run_retrieval.py` | 3,133 repos across 6 axes; measured Jaccard 0.033 |
| `src/run_gates.py` | gated all 3,133; 627 needed a README, fetched free |
| `src/prescreen.py` | ordered 2,562 gated repos for the core budget |
| `src/fetch_repo.py` | 40 repos at tree level, 2 at full level |
| `src/rescore.py` | strict rescore of all 40, cache-only, zero API spend |
| `src/rank.py` | Spearman correlations, the premise-3 answer |
| `src/toolchain.py` | library and API-host extraction with `repo:path:line` |
| `src/crossref.py` | 56 YouTube tools checked against live repo state |
| `src/dump_repo.py` | prepared 2 repos for reading |
| `src/load_extraction.py` | loaded 2 extractions; **rejected 1 item for missing evidence** |
| `src/build_knowledge.py` | generated `GITHUB_KNOWLEDGE.md` |

**Built but never exercised at scale:** `fetch_repo.py --level full`. Two repos
have credibility metrics. The commits-vs-substance correlation therefore has
n=2 and is reported as unavailable rather than computed.

**Not built:** nothing from the prompt's output list was skipped, but Step 4's
`repos` table is only 40 rows deep and Step 5's liquidity comparison is
unanswered (see §5).

---

## 5. What is wrong, unfinished or untrusted — read this section first

1. **The venue legal terms were never read.** Both `kalshi.com` (HTTP 429 to
   everything) and `polymarket.com/tos` (client-side rendering) defeated
   retrieval. Everything said in `reports/step5_answers.md` about automation
   being permitted rests on **developer documentation**, not legal terms.
   Kalshi publishes market-maker API tiers and Polymarket publishes market-making
   guidance, which is strong circumstantial evidence — but it is not the
   agreement you would be bound by. **Read both yourself before funding
   anything.** Secondary sources asserting "bots are explicitly permitted" were
   found and deliberately not used: every one was an SEO page for a bot vendor.

2. **Coverage is 1.6%.** 40 of 2,562. There is no basis for claiming the best
   repo has been found — only that the best repo *among the top 40 by a free
   prescreen* has been found. The prescreen is a heuristic over stars, size,
   language, recency and name keywords, and it is exactly the kind of proxy this
   project just proved unreliable for stars.

3. **The strict scorer is a second draft, not a validated instrument.** One false
   positive was caught only because the repo's own README contradicted it. There
   is no reason to think it was the only one. S4 in particular cannot work by
   keyword and should be treated as noise.

4. **Credibility metrics are complete for all 40 deep-fetched repos** after a
   rate-limiter bug was fixed (see 4b). `trust_me_bro` is therefore decided for
   all 40 — but only 40, out of 2,562 gated.

   Three of the 40 are flagged: `aulekator/Polymarket-BTC-15-Minute-Trading-Bot`
   (558 stars, **4 commits over 6 days**), `taetaehoho/poly-kalshi-arb` (445
   stars, **5 commits over 5 days**, claims "Profit: 2¢ per contract" with no
   artifact), and `kachence/polymm` (70 stars, **2 commits over 2 days**, whose
   README opens *"Most 'I built a Polymarket bot' repos are a README and a dream.
   This one traded real money"* — and which is itself a README and a dream by
   this measure). The claim-extraction regex still picks up some markdown badge
   text; the flag itself is sound but the quoted claim string is noisy.

4b. **A rate-limiter bug cost most of this session's depth.** `gh.core` slept
   until a *recorded* reset timestamp without checking whether that timestamp had
   already passed, so after a long stretch of free work it would sleep a full
   hour with 42 core calls actually available. Fixed in `src/gh.py`; the fix
   immediately took the credibility pass from 2 repos to 30. Anyone re-running
   this should expect roughly 15 repos/hour at level `full`, not the ~2 the
   session appeared to get.

5. **`Polymarket/agents`, 3,758 stars, archived since 2024-11-05, has not been
   examined.** It is the most-starred prediction-market bot repository in
   existence and it is dead. Whatever is in it, nobody should build on it.

6. **The 410 "generic terms only" repos are unexamined.** They passed G3 on
   market-structure vocabulary without naming a venue. Some are certainly crypto
   bots with nothing to do with prediction markets; some may be the opposite of
   that and were never checked.

7. **Liquidity was not compared between venues.** It needs recording both books
   live over a period and no repo published a comparative study. Left explicitly
   unanswered rather than guessed.

8. **Sourcegraph is a proxy, not GitHub code search.** 41 exclusive finds is a
   real gain, but the population it indexes is unknown and it excludes forks by
   default. The code-search axis is the weakest-provenance axis in the project.

9. **Two extractions is not a sample.** Both were chosen by the strict score.
   Both happened to be unusually honest repos. That is very likely selection
   bias: rigorous repos score well *because* they are rigorous, so reading the
   top of the list systematically over-samples honesty. **The corpus as a whole
   is almost certainly less honest than the two repos read.**

---

## 6. The single next thing to do, and why

**Put a free GitHub personal access token in the environment as `GITHUB_TOKEN`,
then re-run `src/fetch_repo.py full 200`.**

Why this and nothing else: core goes from 60/hour to **5,000/hour** — an 83×
increase — and code search unblocks at the same moment. Both of the two things
that constrained this entire session are fixed by one environment variable, with
no code change (`gh.py` already reads `GITHUB_TOKEN`, `GH_TOKEN` and
`GITHUB_API_TOKEN`). The token is free, needs no card, and needs no scopes for
public data.

With it, in roughly one hour: all 2,562 gated repos get a real S score, all 40+
get credibility metrics, the `trust_me_bro` flag becomes computable across the
corpus, the commits-vs-substance correlation gets a real n, and GitHub's own code
search replaces the Sourcegraph proxy.

Second, if a human minute is available rather than a machine hour: **read the
Kalshi member agreement and the Polymarket terms of use in a browser.** Both
defeated every automated retrieval path tried here, and they are the one input
that could invalidate the venue recommendation.
