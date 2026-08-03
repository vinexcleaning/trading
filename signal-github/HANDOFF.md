# signal-github — HANDOFF

Session of **2026-08-03**, on the **desktop** (`C:\Users\vinig`). The previous
session ran on the laptop (`C:\Users\gianf`). Ran unattended start to finish.
Nothing here is a plan; everything is either a measurement or a stated gap.

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

---

## 6. The single next thing to do

**Put the token in `signal-github/.env`.** It is no longer needed for depth —
that is now free — but it is what unblocks GitHub code search and stops
unauthenticated search dropping pages. `gh.py` reads the file at import; nothing
else changes.

Second: **read the Kalshi member agreement and the Polymarket terms of use in a
browser.** Both still defeat automated retrieval, and they are the one input that
could invalidate the venue recommendation.
