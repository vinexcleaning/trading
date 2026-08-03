# signal-github — HANDOFF

Session of **2026-08-03**, on the **desktop** (`C:\Users\vinig`). The previous
session ran on the laptop (`C:\Users\gianf`). Ran unattended start to finish.
Nothing here is a plan; everything is either a measurement or a stated gap.

---

## 0a. TWO SESSIONS, TWO DATABASES — read before trusting any count

Discovered 2026-08-03 while rebasing. **`signal-github` has been worked on by two
Claude sessions in parallel.** Code and markdown are shared through git; the
SQLite database is **not** — it is gitignored, so each machine has its own.

- The committed HANDOFF sections below describe a database with **862 repos
  scored**, plus `kalshi_fees_census.py` and `kalshi_liquidity_survey.py`.
- The database on **this laptop** (`C:\Users\gianf\trading\signal-github\data\github.db`) has **501**, and its `runlog`
  table contains **no entries** from the 862-repo run.

Neither number is wrong; they are different machines. **Do not read the counts in
this file as describing the database in front of you — re-query it.** The
`runlog` table is the authority for what actually ran locally.

What was merged in from the other session, and is now live here:

- `gh.archive()` — pulls a whole repo (every path *and* the text of every text
  file) from codeload in **one unmetered request**. It replaces the git-tree core
  call that rationed this project to 60 repos/hour. Verified working on this
  machine: `warproxxx/poly-maker` gave 67 paths, 66 file contents, **0 core calls**.
- Correction **C1** (`CORRECTIONS.md`): Kalshi does not charge makers and takers
  the same rate. This corrects a claim in `reports/step5_answers.md` that this
  session published; both that file and `PLAIN_ENGLISH.md` have been fixed.
- `commits_atom()` — free degradation for credibility when core is exhausted.

**Transient-failure note for whoever runs the archive pass next.** `_fetch_bytes`
has no retry, and a network blip makes `archive()` return zero paths, which looks
exactly like an empty repo. It is caught — `fetch_repo` writes `fetched=-2`
(retryable) rather than poisoning the row — but a run during a bad network
stretch will under-report and simply need re-running. Observed live: the same
repo returned 0 paths, then 67 a minute later.

---

## 0. Read this first — two things about the starting state

**1. There was no token.** The instruction was to set a GitHub personal access
token as `GITHUB_TOKEN`. **The token value did not arrive with the message**, and
there is none on this machine: no `GITHUB_TOKEN`/`GH_TOKEN` in the environment,
`gh auth status` reports not logged in, and a search of the whole user tree for
`ghp_*` / `github_pat_*` / `GITHUB_TOKEN=` returns four files, all of which are
**pattern lists in documentation**, not secrets (`DESKTOP_INVENTORY.md:182` is
the secret-scan pattern list from the desktop inventory; two are chat transcripts
quoting it; one is Cloudflare skill docs). An attempt to read the Windows
credential store was blocked by the permission classifier and was not worked
around.

So the session could not do what was asked literally. It did two things instead:

- **Made the token drop-in.** `gh.py` now loads `signal-github/.env` at import
  (`_load_dotenv()`), because shell environment variables do not survive between
  agent tool calls on Windows — a token exported in one call is gone by the next.
  Put the token in `signal-github/.env` as `GITHUB_TOKEN=...` and every script
  picks it up with no other change. That file is gitignored by rule
  `.gitignore:54 *.env`, verified with `git check-ignore`.
  `signal-github/.env.example` documents it.
- **Removed the constraint the token was for.** See below — depth no longer
  needs it.

**2. None of the previous session's data was on this machine.** `data/github.db`,
`cache/`, `reports/` and `GITHUB_KNOWLEDGE.md` are all gitignored, so the 3,133
retrieved repos, 2,562 gated and 146 scored existed only on the laptop. On the
desktop `signal-github/` contained `src/` and `HANDOFF.md` and nothing else. The
corpus had to be rebuilt from scratch before "go beyond 105 repos" could mean
anything. **This is a structural fact about the project worth planning around:
the code is shared through git and the corpus is not, so the two machines cannot
continue each other's work.**

(The brief said 105 deep-fetched at 4.1% coverage; the previous `HANDOFF.md`
ended at 146 at 6%, because a background pass was still running when the
`STATUS.md` figure was written. Both are superseded — this session reached
**862**.)

---

## 1. The finding that changes the project's economics

**The 60/hour core budget is no longer the binding constraint, and a token was
never the only way out of it.**

`codeload.github.com/<owner>/<repo>/tar.gz/<branch>` returns the complete file
tree **and the contents of every file** in one request. Measured today:

| | |
|---|---|
| `X-RateLimit-*` headers on the response | **none** |
| `/rate_limit` core reading before vs after a download | **identical — 0 spent** |
| `warproxxx/poly-maker` | 67 paths, 63 file texts, 225 KB, 5.6 s |
| `Polymarket/py-clob-client` | 111 paths, 106 file texts, 48 KB, 0.25 s |
| a nonexistent repo | clean 404 |
| second call | 0.002 s cache hit |

The old deep fetch spent **1 core call per repo** for a git tree that returned
**paths only**, which is what rationed the project to 60 repos/hour. The new one
spends **zero** and returns paths *and contents*.

Two consequences beyond speed, both of which touch conclusions the previous
handoff drew:

- **The source corpus was truncated and that was not stated anywhere.** Because
  each file used to be its own HTTP request, the scorer read the **30 largest
  files, capped at 400 KB**. S1 (a cost term inside arithmetic) and S2 (a
  backtest module *and* order submission in different files) were both decided on
  that window — and S2 is the component the previous handoff singled out as
  mattering most and transferring worst. It is now every text file in the repo.
  `MAX_SRC_FILES` 30 → 400, `MAX_SRC_BYTES` 400 KB → 4 MB.
- **`dump_repo.py` — the read step — had the same problem.** It read the per-file
  raw cache, which only ever held those 30 files. **Every repo "read in full"
  last session was read from a sample of itself**, and nothing said so. Fixed.

**Use the legacy URL form.** The documented `/tar.gz/refs/heads/<branch>` path
times out from this network (`WinError 10060`); the legacy `/tar.gz/<branch>`
form returns in 0.3 s. Do not "modernise" it.

**Where it does not work**, measured rather than assumed:
- Repos whose default branch is neither `main` nor `master`. The DB stores
  `default_branch` from search and it is tried first, so this is handled — but
  only because retrieval recorded it. `evan-kolberg/prediction-market-backtesting`
  has default branch **`v4.1-alpha`**, which is why a naive `main`/`master`
  attempt 404s on a live 1,098-star repo.
- Repos over the size cap. That same repo is **165 MB**, above `MAX_DOWNLOAD`
  (80 MB), so it still needs the core git-tree path. `fetch_one` falls back to
  `tree_of()` automatically and marks the row retryable rather than scoring it
  from nothing.

---

## 2. Correction C1 — Kalshi does not charge makers and takers the same rate

Carried in as a correction from the user's own measurement; **verified here two
independent ways, and it is right.** Full write-up in
[`CORRECTIONS.md`](CORRECTIONS.md); reproduce with `src/kalshi_fees_census.py`,
which exits non-zero if anything has moved.

**What this project published, and it was wrong:**

> Kalshi: `ceil_to_cent(0.07 × qty × p × (1−p))`, **same rate for makers and
> takers** — sourced from `evan-kolberg/prediction-market-backtesting`
> → `adapters/kalshi/fee_model.py:908`.

**Source 1 — Kalshi's own fee schedule**, effective 7 July 2026:

| side | formula | default multiplier `M` |
|---|---|---|
| taker | `roundup(M × 0.07 × C × P × (1−P))` | **1** |
| maker | `roundup(M × 0.0175 × C × P × (1−P))` | **0** |

The maker rate is **one quarter** of taker, and its multiplier defaults to
**zero**.

**Source 2 — the live API**, `/trade-api/v2/series` fully paginated, 12,396
series: `quadratic` (taker-only) **12,266** · `quadratic_with_maker_fees`
**130** · `fee_multiplier == 0` **14**. The **130 reproduces the user's count
exactly**.

**One refinement to the correction as given.** It came with "none of them
crypto". Two are: **`KXBTCMAX150`** and **`KXBTCMAX125`**, both long-dated "will
bitcoin reach $X" series rather than the 15-minute markets. 269 of 271 `Crypto`
series are taker-only, so the substantive point stands and the literal "zero"
does not.

### 2b. And the maker-fee series are where all the liquidity is

The 130 are 1.0% of series, which makes "Kalshi makers pay nothing" true on its
face. Whether it is true *where you would want to quote* was measured, not
inferred (`src/kalshi_liquidity_survey.py`, all 130 plus a random 300 taker-only,
seed 20260803):

| per series, open markets | maker-fee (n=130) | taker-only (n=300) |
|---|---|---|
| mean open volume | **1,812,418** | 16,627 |
| mean open interest | **1,399,160** | 8,919 |
| any open volume at all | 78 (60%) | 86 (29%) |

Mann-Whitney on open volume **U = 28,065, z = 8.28, p ≈ 2e-16** (tie-corrected);
open interest agrees at U = 28,207, z = 8.42. Ratio of means 109× on volume,
157× on open interest. **Of the 430 surveyed series ranked by open volume, the top 25 are all
maker-fee** and 45 of the top 50 are — in a pool that is 30% maker-fee by
construction and 1.0% in the population. `KXSB` 53.0M, `KXMLB` 43.4M,
`KXNBA` 19.7M, **`KXATPMATCH` 13.4M**.

**107 of the 130 are Sports, including `KXATPMATCH` and `KXWTAMATCH` — the exact
series `kalshi-inplay-bot` and `set1_overshoot` trade.**

So: makers pay nothing on 98.9% of Kalshi series, and those are the series with
no book. The previous conclusion — quote where the maker fee is zero — survives
its own premise being wrong, but needs a second clause: **pick a series whose
maker multiplier is zero *and* which has a book.** On Kalshi those are close to
mutually exclusive.

Method note worth keeping: the obvious approach fails. Paginating
`/markets?status=open` spends its first 85,000 rows inside 32 of 12,396 series
because the cursor is ordered by series, so a capped scan of that endpoint
answers nothing. Query per series and compare with rank statistics instead —
that also avoids projecting a heavy-tailed 300-sample onto 12,266 series, whose
interval would be wider than the effect.

Caveats kept because they are what could overturn it: `volume` is cumulative
since a market opened, so long-dated season futures accumulate by age — but
`open_interest` is a stock, not a flow, and shows the same 157× gap.

### 2c. The Kalshi fee schedule is readable, and §5.1 was wrong about that

The previous handoff recorded `kalshi.com` as returning **HTTP 429 to every
request including its own fee-schedule PDF**, and concluded the fee schedule
"was never read". **The 429 is intermittent, not a block.** A browser
User-Agent plus a retry loop got the 382,507-byte PDF **on the first attempt**.
The schedule has now been read in full.

Still not read: the Kalshi **member agreement** and the Polymarket **terms of
use**. Every automation claim still rests on developer documentation.

**Also recovered from that document, new to this corpus:** Kalshi publishes a
**perpetual futures** fee schedule — taker 12.0 bps at tier 0 down to 2.6 bps at
≥$3,000M 30-day volume; maker 5.0 bps down to 0.6 bps. A separate product from
event contracts.

**The transferable lesson.** The wrong number came from a 1,094-star repo that
scores well on every computed component of this project's own rubric. It was a
*secondary* source for a fact the exchange publishes directly. Being rigorous
about your own strategy says nothing about whether you copied a venue constant
correctly.

---

## 2d. Reading the source of the wrong claim — it contradicts itself

`evan-kolberg/prediction-market-backtesting` (1,098★, 254 files, NautilusTrader)
is the most rigorous backtester in the corpus and was the source of C1's wrong
fee claim. Read in full this session, on its real default branch `v4.1-alpha`.
**The previous summary of it was accurate, and the repo is wrong in a more
interesting way than "it said the same rate".**

Three facts in one repository:

| where | what it says |
|---|---|
| `adapters/kalshi/fee_model.py`, `get_commission()` | *"liquidity side is ignored — Kalshi charges the same rate for makers and takers"*. Applies `fee_rate` (default `KALSHI_TAKER_FEE_RATE` = 0.07) to **every fill regardless of side**. |
| `adapters/kalshi/providers.py:49` | `KALSHI_MAKER_FEE_RATE = decimal.Decimal(0)`, with the comment *"Most markets have zero maker fees; markets that do charge a maker fee are noted in the fee schedule PDF."* |
| `adapters/kalshi/providers.py:124` | builds the instrument with `maker_fee=KALSHI_MAKER_FEE_RATE, taker_fee=KALSHI_TAKER_FEE_RATE` |

So **the instrument metadata says Kalshi makers pay 0 while the fee model
charges them 0.07**, in the same repository. Both cannot be right and neither
matches the published schedule (0.0175, on 130 series, zero on the other
12,266). The `providers.py` comment is *closer to correct than the fee model* —
it knows a maker-fee list exists.

Two consequences that a keyword scorer cannot see:

1. **`_fee_rate_for_fill()` only ever consults `instrument.taker_fee`.**
   `instrument.maker_fee` is never read by the fee model, so the `0` is dead
   code as far as backtest P&L goes: **every passive fill is charged the full
   taker rate.**
2. **`strategies/private/passive_pair_accumulation.py:179-181` *does* read
   `instrument.maker_fee`**, gated by `include_maker_fees_in_signal: bool = True`.
   That strategy is a passive/maker strategy. **Its entry signal believes maker
   fills are free while the backtest charges them 0.07** — the signal and the
   accounting disagree about the cost of the exact fills the strategy exists to
   capture, and they disagree in opposite directions (too eager to quote,
   too pessimistic on the resulting P&L).

The docstring cites `https://kalshi.com/docs/kalshi-fee-schedule.pdf` — the
document retrieved in §2c, which has a section headed **"Maker Fees"**. The repo
cites the source that contradicts it.

**None of this is visible to any computed component.** The repo has a backtest
module, order submission in separate files, a test directory, pinned deps and a
mechanism-bearing README; it scores well. The defect is a disagreement between
two constants in different files, which is what reading is for.

## 2e. Second read — `aulekator/Polymarket-BTC-15-Minute-Trading-Bot`

557★, 164 forks, 4 commits over 13 days, no backtest. Flagged `trust_me_bro`
last session on the metrics alone; read this session. Directly adjacent to a
thread `STATUS.md` closed as **structurally dead** (BTC 15-minute), so it is
worth knowing whether it has something the structural argument missed. **It does
not.** Four defects, none visible to any computed component — it scores
**S_literal = 9**.

1. **The instrument's fees are invented, and in the wrong functional form.**
   `core/nautilus_core/instruments/btc_instruments.py:42-43` sets
   `maker_fee=0.001  # 0.1%` and `taker_fee=0.002  # 0.2%`. Those are ordinary
   crypto-exchange percentage-of-notional fees. Polymarket charges makers
   **zero** and takers a fee on **expected earnings**, which is a different
   formula, not a different constant. Two other instruments in the same file use
   0.005/0.005 and 0.001/0.001 — three different fee schedules for one venue.
2. **The live order path sends no fee at all.**
   `execution/polymarket_client.py:284` → `fee_rate_bps=0,  # Fee in basis points`.
3. **The README advertises a feature its own file tree calls a placeholder.**
   The feature table promises *"Self-Learning — Automatically optimizes signal
   weights based on performance"*; `README.md:211-212` describes the same
   component as *"Phase 7: Future learning / optimization"* and
   *"Placeholder for ML feedback loop"*. The README contradicts itself.
4. **An MIT badge with no licence.** The README carries
   `[![License: MIT]]`, there is **no `LICENSE` file** anywhere in the 104-file
   tree, and GitHub's own licence field is empty — so the repository is "all
   rights reserved" and the badge is the only permission anyone has.

Also worth noting as a hygiene signal the scorer counts as *content*: **42 of the
104 files are committed `__pycache__/*.pyc`**. `tree_files` counts them, and the
prescreen rewards size.

**Zero occurrences of `backtest` in the repository.** A "production-grade" bot
with 557 stars, no backtest, no results artifact, and a fee model that is wrong
three different ways in one file.

---

## 2f. The stars-vs-substance *correction* does not survive the larger sample

This is the most consequential number of the session, and it un-does something
the previous handoff had already corrected once.

The history: at **n=40** the correlation between stars and strict score was
−0.019 (p 0.91) and the project reported *"stars carry no information about
whether a repo has substance"*. At **n=105** it measured **+0.241 (p 0.013)**,
and the previous session **withdrew the strong claim**, writing that it "was
wrong and is withdrawn" and that stars are a *"weak but statistically
significant"* signal.

At **n=862** it is gone. Measured over nested prescreen-ordered subsamples of
the same corpus, so the trajectory is visible rather than asserted:

| n (top by prescreen) | rho(stars, S_strict) | p |
|---|---|---|
| 40 | −0.004 | 0.980 |
| **105** | **+0.189** | **0.051** |
| 200 | +0.036 | 0.611 |
| 400 | +0.034 | 0.496 |
| 600 | +0.017 | 0.677 |
| **862** | **−0.004** | **0.898** |

The n=105 bump reproduces (this session gets +0.189 where the last got +0.241,
both borderline) and then **decays monotonically to zero as n grows**. It was a
small-sample artifact. **The original claim is reinstated: stars carry no usable
information about substance, and the withdrawal of that claim was itself the
error.**

Concretely, in the 862: **58 repos with 50+ stars score ≤3 strict**, and **86
repos with ≤2 stars score ≥8 strict.**

### A scorer bias this exposed, which matters more than stars

| pair | rho | p |
|---|---|---|
| **`tree_files` vs S_strict** | **+0.593** | **<0.0001** |
| stars vs S_strict | −0.004 | 0.898 |
| forks vs S_strict | −0.009 | 0.790 |

**File count is by far the strongest predictor of the strict score** — and it is
largely mechanical, because more files means more chances for any component to
find its pattern. That is a property of the instrument, not of the repos. It is
also gameable and partly noise: §2e's repo has **42 of its 104 files as committed
`__pycache__/*.pyc`**, all of which `tree_files` counts. **Any future ranking
should normalise for repository size before anything else.**

### Score distribution at n=862

Literal ≥9 fires on **248 of 862 (28.8%)**; strict on **64 of 862 (7.4%)**. The
strict rate replicates the previous session's 3-of-40 (7.5%) almost exactly at
21× the sample, which is the best evidence so far that the strict scorer is
measuring something stable.

---

## 2g. The corpus-wide fee audit — and the sharpest result of the session

C1 gave a published ground truth for a constant that hundreds of repos hardcode.
`src/fee_audit.py` asks every deep-fetched repo what it believes, which is only
possible because whole-repo source is now free, and is a question no keyword
score can answer: **the answer depends on the value of a constant, not its
presence.**

Over the 862 scored repos:

| | repos |
|---|---|
| mentions a fee anywhere | 728 (84%) |
| **models no fee at all** | **132 (15%)** |
| sets some fee to zero | 309 (36%) |
| Kalshi taker rate = 0.07 (correct) | 70 |
| Kalshi taker rate = something else | 28 |
| **Kalshi maker rate = 0.0175 (correct)** | **19** |
| **Kalshi maker hardcoded to 0** | **15** |
| **Kalshi maker set equal to taker (the C1 error)** | **4** |

### The result

**The 19 repos that get Kalshi's maker fee right have 65 stars between them. The
15 that hardcode it to zero have 1,493 — 23× more.**

| | n | star counts | median | total |
|---|---|---|---|---|
| **correct (0.0175)** | 19 | 26, 20, 8, 6, 2, 1, 1, 1, then **eleven zeros** | **0** | **65** |
| **hardcoded zero** | 15 | **1098**, 225, 118, 11, 11, 9, 7, 6, 5, 2, 1, 0×4 | 6 | **1,493** |
| set equal to taker | 4 | 4, 1, 0, 0 | 0.5 | 5 |

16 repos name **both** Kalshi rates correctly. The most-starred has **26 stars**;
**nine of the sixteen have zero**. Several are better than correct — they know
the fee is *per series*:

- `hbere/kalshi-transport` (1★): `MAKER_FEE_RATE = 0.0175` … *"Returns 0.0 when
  the series carries no maker fee — pass `fee_type`"*
- `RohitDayanand/PolyKalshi_Client` (20★): *"Maker fees for specific tickers:
  0.0175 × C × P × (1−P) rounded up to next cent"*
- `utkarshp845/Kalshi-Trading-Bot` (1★): *"maker fee coefficient **where maker
  fees apply**"*

Meanwhile **`rodlaf/KalshiMarketMaker` (225★) — a Kalshi *market maker* —
hardcodes the maker fee to zero**, which is wrong on exactly the 130 liquid
series a market maker would want to quote.

This is the most concrete version of the stars finding the project has produced.
On an objectively checkable fact with a published ground truth, popularity is not
merely uninformative — **it points the wrong way.**

**The honest alternative explanation**, which this does not rule out: the
high-star repos here are general-purpose multi-venue frameworks (hummingbot,
`evan-kolberg`) that treat Kalshi as one venue among many and simplify, while the
zero-star repos are single-purpose Kalshi bots whose whole reason to exist is
that venue. That would produce the same pattern without popularity being
*anti*-informative. Either way the practical rule is the same: **for a venue
constant, do not take the popular repo's word for it — read the venue's
document.**

### Detector precision, stated because the last session's was not

The exact-value buckets (0.0175 / 0 / 0.07) were spot-checked by reading the
matched lines: **12 of 12 inspected are genuine**. The
`kalshi_*_other_value` buckets (28 and 40) are **not trustworthy** — they are
dominated by SQL column names like `maker_asset_id` and `taker_amount`
(`Jon-Becker/prediction-market-analysis` is matched this way). Only the
exact-value buckets are quoted above, and `reports/fee_audit.json` carries
`path:line` for every hit so any of it can be checked.

---

## 2h. The Kalshi member agreement — read, and it changes the venue answer

The previous handoff listed this as the one input that could invalidate the venue
recommendation, and as human-only work. **It is neither.** It is at
`kalshi.com/docs/kalshi-member-agreement.pdf` — same URL shape as the fee
schedule — and downloaded on the second attempt with a browser User-Agent.
9 pages, 34,214 characters, v1.6.

**What it does not say.** Term census over the full text:

| term | occurrences |
|---|---|
| bot, automated, automation, algorithmic, programmatic | **0** |
| API, script, scrape, scraping, robot | **0** |
| high-frequency, co-locate | **0** |
| manipulat*, spoof, wash trade, self-trade, disruptive | **0** |
| **Rulebook** | **19** |
| market maker | 11 |

**The member agreement is silent on automation.** It neither permits nor
prohibits bots. So it does not contradict the project's automation claims — but
it does not support them either, and the conduct rules are not in it. They are in
the **Rulebook**, which is incorporated by reference and, in the agreement's own
words, *"In the event of any conflict between this Agreement and the Kalshi
Rulebook, the Kalshi Rulebook will govern."* **The Rulebook is the operative
document for the automation question and is still unread** — `kalshi.com/regulatory/rulebook`
returns 145 KB of HTML that yields 581 characters of text, and renders an empty
body in a real browser too.

**What it does say, and this is the material part.** Clause T, quoted because
paraphrase would soften it:

> *"Under the rules, market makers will make markets on Kalshi in exchange for
> receiving benefits. The benefits can include monetary benefits, such as
> **discounts on fees, rebates on fees, revenue share from fees** … Market makers
> who receive these benefits **may be able to price their quotes in ways that are
> materially different** from other Kalshi members who are not eligible … Market
> makers may also be eligible for … **order protections whereby orders are
> canceled if the market maker's trading session disconnects** … and may be
> eligible to **greater throughput to the Exchange** … **These tools may give
> market makers a trading advantage over members who are not market makers**."*

And clause U: designated makers must hold a maximum spread and minimum depth only
*"during specific times"*; outside those, *"pricing and liquidity … may be
worse."*

**Consequence.** The project's single most promising strategy was maker-only
two-sided quoting. On Kalshi, the venue states in its own contract that a
non-designated participant running that strategy is competing against
counterparties who get fee discounts, rebates and revenue share on the very fees
the retail participant pays in full (and per §2 pays at all, on the 130 liquid
series), plus cancel-on-disconnect protection and higher throughput. **This is
the venue telling you, in the agreement you sign, that you are structurally
disadvantaged in exactly that strategy.** It is a stronger argument against
retail maker-only quoting on Kalshi than anything the project had derived.

**Polymarket's terms remain unread and are worse than "not tried".** `/tos`
returns HTTP 200, sets the page title to "Terms of Use | Polymarket", and renders
the **homepage body** — in a real browser, after client-side routing, with the
footer link clicked. There is no terms text. The previous handoff's advice to
"read it in a browser" does not work; that recommendation is withdrawn.

---

## 2i. Third read — the most honest repo in the corpus, and it understates itself

`artyomderkach-bit/kalshi-15m-market-maker` — **0 stars**, 10 commits over 8
days, 41 files, MIT, `s_strict` 10, and top of the combined shortlist (§3c). A
market maker for Kalshi's 15-minute crypto series.

It is the anti-pattern to everything else read this session:

- **It says what it is withholding.** *"This is the public version … the
  proprietary parts removed … the architecture, engine, backtest harness and
  tooling are the real thing; **the edge itself is not in this repo**."*
- **It makes no profit claim and pre-empts one:** *"This is not a promise of
  alpha."* It ships in **paper mode** running *"the one strategy that is roughly
  break-even under pessimistic fill assumptions"*.
- **It reports its own negative result:** *"Almost every edge that looked real
  in-sample decayed out-of-sample within a few weeks as the market makers on the
  other side sharpened up."* That is an independent corroboration of this
  programme's own central finding.
- **It is designed against the exact defect §2d found in `evan-kolberg`:** the
  fair-value function *"is imported by both the live engine and the backtests so
  they can never drift apart."*
- **Its paper fill detection is deliberately conservative** — a print must go
  *through* the resting level; *"it never lets a touch count as a fill."*
- Its fee helper is `math.ceil(raw * 100.0 - 1e-9) / 100.0` — independently the
  same float-dust guard that `common/kalshi_fees.py` exists to provide across
  this repo's own five codebases.

**And it has a real defect, in the opposite direction from every other one found
this session.** `backtest/pairdata.py:12` sets `MAKER_RATE = 0.0175` and
`backtest/maker_model.py:11` charges *"maker fee 0.0175"* on its own maker
strategy. Per §2, **the 15-minute crypto series do not charge makers at all**:

| series | fee_type | maker pays |
|---|---|---|
| `KXBTC15M` `KXETH15M` `KXSOL15M` `KXXRP15M` `KXDOGE15M` | `quadratic` | **zero** |

**Zero 15-minute series anywhere on Kalshi charge a maker fee.** At the repo's own
quoting range of $0.80–0.99 in 10-lots, it charges itself $0.01–0.03 per fill —
**0.1–0.3¢ per contract of phantom cost** — against a strategy it describes as
roughly break-even. That is the whole margin.

**So the most careful repo in the corpus is understating its own strategy.** Of
the six defects reading has found this session, five flatter the repo and this
one penalises it — and it is in the only repo that did everything else right.

**Why this matters for `STATUS.md`'s closed BTC-15-minute thread.** That thread
was killed structurally: *"every contract is minted at-the-money on the peak of
the fee curve."* This repo's answer is to quote the **wings** at $0.80–0.99,
where `p(1−p)` is small — sidestepping the fee peak rather than fighting it — and
it still only reaches break-even. That is independent support for the kill, from
someone who built the full apparatus and reached the same place. **It does not
reopen the thread.**

## 2j. Fourth read — the same defect again, which makes it a pattern

`hamad-khawaja/kalshi-trading-bot` — 2★, **104 commits over 13 days**, 103 files,
CI workflow, 15 test files, a `robustness_check.py`, six documented strategy
flows. `s_strict` 10, fee constants correct. It trades `KXBTC15M` and `KXETH15M`.

It makes **the same error as §2i, independently**, and deeper in the stack:

| site | what it does |
|---|---|
| `src/strategy/market_maker.py:213, 248` | charges a maker fee on **both quoting legs** |
| `src/strategy/edge_detector.py:151` | subtracts a maker fee **inside the edge calculation** |
| `src/bot.py` (6 sites), `position_tracker.py:533`, `fomo_detector.py:166`, `trend_continuation_detector.py:218` | `is_maker=True` throughout the decision path |
| `CLAUDE.md:69` | documents `maker rate=0.0175, taker rate=0.07` — **both correct** against the published schedule |

`KXBTC15M` and `KXETH15M` charge **no maker fee**. So the bot subtracts roughly
**0.44¢ per contract at the money** from an edge that does not have to cover it,
and declines trades that are actually profitable.

**Two independent repos, both among the most rigorous found, making the same
mistake, makes it a pattern worth naming.** It is recorded as correction **C1a**:

> The published maker rate is right. Applying it without checking the series'
> `fee_type` is wrong — and the repos careful enough to model maker fees at all
> are precisely the ones that get this wrong, because the careless ones use
> taker or zero everywhere.

The error is invisible to any check that compares a constant against the
schedule, **because the constant is correct**. Only the per-series `fee_type`
makes it wrong.

This is direct external validation of a design decision already made in this
repo: `common/kalshi_fees.py::maker_fee_order_cents()` takes no default for the
series and raises rather than guess. Two repos in the wild demonstrate exactly
the failure that refusal prevents.

---

## 3. The no-README false-negative channel is closed

77 repos were dropped last session purely for having no fetchable README, and it
was recorded as a real false-negative channel: a repo with an on-topic codebase
and no README was invisible to gate G3.

`run_gates.py` now has a third pass. When no README can be fetched it reads the
**code** — paths included, since a file named `kalshi_client.py` is itself a
venue term — and gates on that. A README is a convenience, not a requirement.
The report prints the outcome as a table: rescued / genuinely off topic / over
the size cap, so the residual leak is counted rather than hidden.

---

## 3b. The numbers, including the bad ones

Corpus rebuilt from zero on this machine, then taken further than the previous
session reached.

| stage | this session | previous |
|---|---|---|
| unique repos retrieved | **2,806** | 3,133 |
| — F1 beginner / F2 insider | 1,009 / 959 | 964 / 1,147 |
| — in both / **Jaccard** | 68 / **0.036** | 67 / 0.033 |
| — TOPIC / LIB_FORK / SEED | 390 / 317 / 187 | 785 / 317 / 188 |
| — F2_CODE (Sourcegraph) | **15** | 37 |
| gate PASS / STALE / DROP | 2,221 / 126 / 459 | 2,441 / 121 / 571 |
| **deep-fetched and scored** | **862** | 146 |
| **coverage of the gated set** | **36.7%** | 6.0% |
| repos read in full this session | 2 | 12 |
| literal S ≥ 9 | 248 of 862 (28.8%) | 19 of 40 (47.5%) |
| **strict S ≥ 9** | **64 of 862 (7.4%)** | 3 of 40 (7.5%) |
| core API calls spent on the deep fetch | **0** | ~146 |

Jaccard 0.036 against YouTube's 0.037 over 446 videos and the previous 0.033 —
the beginner/insider disjointness result now has three independent measurements
that agree.

**The corpus is smaller than last session's and that is a loss, not a
rounding.** Two causes, both external: the Sourcegraph code-search axis returned
15 repos where it returned 37, with several queries returning literally zero; and
unauthenticated search dropped whole pages to 403s, including both attempts at
`topic:kalshi`. See §5.1–5.2.

**The fetch was stopped at 862 of a planned 1,200, deliberately.** The scoring
loop slows on very large repos (one monorepo in the queue has 13,526 files), and
finishing the remaining ~340 was worth less than running the strict rescore, the
ranking and the fee audit cleanly. The selector is `fetched IN (0,-2)`, so
re-running `python src/fetch_repo.py tree 1500` resumes exactly where it stopped;
every archive already pulled is a cache hit.

**Credibility metrics were not fetched for any repo this session.** `commits`,
`contributors` and `span_days` are all NULL, so `trust_me_bro` is undecided
corpus-wide and the commits-vs-substance correlation could not be computed at
all. That tier needs core calls (or the free atom feed, which gives recency but
no total count). It is the largest single gap in this session's output.

---

## 4. Pipeline defects found and fixed this session

1. **`run_retrieval.py` wrote to the database only after every axis**, including
   the two fork axes that spend core. With core exhausted that meant an hour of
   sleeping could discard an entire retrieval run's free work. It now writes
   after the free axes and again at the end, and `forks_of()` skips outright
   when there is no core budget and no token instead of sleeping an hour per
   page for a fork list.
2. **`rescore.py` read the cached git-tree**, which the archive transport no
   longer produces — the strict rescore would have silently found nothing and
   scored zero repos. Now reads the archive, with the old cache as fallback.
3. **`dump_repo.py` read a 30-file sample** and presented it as the repo. See §1.
4. Added `gh.core_budget()`, which asks `/rate_limit` for a live answer;
   that endpoint is documented as not counting against the limit.

---

## 5. What is wrong, unfinished or untrusted — read this section too

1. **Unauthenticated search silently loses pages.** Several queries returned
   `p2: 0 (total_count=None)` — a 403 secondary-rate-limit, about 300 repos
   across four queries on the first run. A re-run recovered most of them, but
   `topic:kalshi` was lost on both. **This is the one constraint a token still
   fixes**, along with real GitHub code search.
2. **The Sourcegraph code-search axis has degraded.** It returned 37 repos last
   session; this session several terms returned **0**, including
   `py_clob_client` and `api.elections.kalshi.com`. It was already the
   weakest-provenance axis; it may now be near-dead. A token replaces it with
   GitHub's own code search.
3. **The venue legal terms are still unread** — see §2c.
4. **The strict scorer is still a second draft, not a validated instrument.** It
   now sees every file rather than 30, which should help S1 and S2 specifically,
   but that is a reason to re-measure the literal-vs-strict gap, not to assume it
   improved. S4 cannot work by keyword and should still be treated as noise.
5. **Reading over-samples honesty.** Repos are selected for reading by the strict
   score, and rigorous repos score well *because* they are rigorous. The corpus
   as a whole is almost certainly less honest than the repos read.
6. **The strict score is 59% explained by file count** (rho +0.593). Until that
   is normalised, the ranking is substantially a size ranking. This is the
   highest-value single fix to the instrument and it is not done.
7. **Only 2 repos were read in full this session** against 12 last session. The
   session spent its time rebuilding a corpus that did not exist on this machine
   and on the fee work. The ratio the previous handoff flagged — defects come
   from reading, not scoring — held completely: **2 repos read produced 5
   defects** (1 in `evan-kolberg`, 4 in `aulekator`), none visible to any
   computed component, in repos scoring 10 and 9.
8. **No credibility metrics at all** — see §3b. `trust_me_bro` is undecided for
   all 862.

---

## 6. The next three things, in order

1. **Normalise the strict score for repository size.** `rho(tree_files,
   S_strict) = +0.593` against `rho(stars, S_strict) = −0.004`. The ranking is
   currently more a size ranking than a substance ranking, and everything built
   on top of it inherits that. This costs no API budget and is pure local work.

2. **Finish the fetch and add the credibility tier.**
   `python src/fetch_repo.py tree 1500` resumes at repo 863 with every existing
   archive a cache hit. Then `full` for the credibility axis — which is the one
   thing that still wants core budget, and therefore the token.

3. **Put the token in `signal-github/.env`.** No longer needed for depth, but it
   is what unblocks GitHub code search (replacing a Sourcegraph axis that has
   degraded from 37 repos to 15) and stops unauthenticated search silently
   dropping pages. `gh.py` reads the file at import; nothing else changes.

And still, unchanged from last session because no machine could do it: **read the
Kalshi member agreement and the Polymarket terms of use in a browser.** The fee
schedule turned out to be reachable after all (§2c) — the other two are not, and
they are the one input that could invalidate the venue recommendation.
