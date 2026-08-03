# STATUS.md

As of **2026-08-02** for the laptop, **2026-08-03** for the desktop. The laptop
inventory recomputed nothing and touched no process. The desktop pass moved
directories and patched the live bot — see the dated section at the end.
Claims: [LEDGER.md](LEDGER.md). Reusable checks: [GUARDS.md](GUARDS.md).
How the repos and sessions fit together: [HOW_THIS_WORKS.md](HOW_THIS_WORKS.md).
New ideas go in [INBOX.md](INBOX.md) first, before deciding where they belong.

---

## Threads — CLOSED

| Thread | Why it closed | Next action |
|---|---|---|
| **Tennis set-1 overshoot** | The undershoot is real (−2.42pp, p=0.0009, n=3,436) and **uncollectable** against a 3.61pp cost bar. 0 of 25 time/tier and 0 of 10 margin buckets clear. | **Stop.** n≈3,970 needed for a 2¢ edge; more slicing has negative EV. |
| **Crypto ladder modelling** | **No model beats the Kalshi mid** on 250 events. Two tie, two lose. The positive control proves the test would have found a 5% bias. | None. NO-GO fired; Task 5 was correctly never run. |
| **Polymarket copy trading** | Wallet skill is real and persists, but the copyable part (+0.937pp, falling to −0.135pp in the fee era) is **smaller than the spread** (≥1.0pp). | **Do not build the bot.** Phase 5 deliberately skipped. |
| **Stage 0–5 player model** | **The model loses to the bookmakers**: +0.01922 Brier [+0.01438,+0.02417], n=2,645. Stage 4 gate failed. | None. Sackmann features end 2026-06-02 and the upstream repos are 404. |
| **BTC 15-minute (KXBTC15M)** | Structurally dead — `floor_strike` equals the prior window's settlement in 99.86% of 6,261 markets, so every contract is minted at-the-money on the peak of the fee curve. | None. Structural kill, not statistical. |
| **Ladder arbitrage** | 0 monotonicity violations in 3,187 scans; 1 gross bucket-sum violation in 1,135, **unprofitable net**. The ladder is wide enough that legging it is self-defeating. | None (10.5 min of recording — a preliminary null, but with a structural mechanism). |

## Threads — ALIVE

| Thread | State | **Single next action** |
|---|---|---|
| **Depth recorder (tennis)** | Running since 08-01 06:58. 79–120 markets, 0.55 s pacing, content-checked ×5/day at 98.8% non-empty. | Leave it. It is accruing the only asset that cannot be re-pulled. |
| **15m opens recorder (crypto)** | Running since 08-01 13:42, `--hours 168`. | Leave it. |
| ~~v3 structural-event backtest~~ | **RESOLVED 08-03 — CLEAN, the result stands.** See "Desktop, 2026-08-03" below. | None. |
| ~~Desktop recorder integrity~~ | **RESOLVED 08-03 — no bug. The desktop already reads `*_dollars`/`*_fp`.** Tier B is unblocked. | None. |
| ~~Live bot position-sizing bug~~ | **DIAGNOSED AND FIXED 08-03.** Not a sizing bug — a martingale. See below. | Decide whether it trades at all: its own backtest says −9¢/trade. |
| **Score-staleness (already fixed)** | `fetched_at` was stamped at cache read, so the 30 s guard never rejected anything. | Nothing to fix — but **no live entry result predating the fix is a valid test of the entry logic.** Treat the 4-for-10 as void. |
| **Label coverage (tennis)** | Blocked. Apify at a monthly hard limit; Flashscore's `dayOffsets` is −7..+7 against a −68 need. | Restore quota, then label day-by-day via `crawlstone/tennis-scraper` or `tennisexplorer` (~$20, not $3.44). Only path above 13.9% coverage. |
| **youtube-signal** | **Phase 2 BLOCKED at Step 0: no `ANTHROPIC_API_KEY`, so the LLM read never ran and no S or H component has ever fired.** All LLM-free work done: corpus 718 gated / 369 passing / 683 transcripts cached, G3 retuned to recall 1.000, F3 cut, F2B's 12 new insider terms added (88.5% exclusive, Jaccard 0.041 vs F2), 60-video read set selected, Wilson n-check verified. Retrieval win (F1∩F2 Jaccard 0.037, 2.25× low-view yield) is **still not cashed out** — different videos, not yet demonstrably better ones. | **Buy $5 of Anthropic API credit, add the key, run the read on 2 videos.** Measured cost for all 60 is $3.64 on Sonnet. Everything else waits on this one input. |

---

## What is running, where

| PID | Process | Machine | Writes to | Started |
|---|---|---|---|---|
| **17892** | `record_depth.py` | this laptop | `C:\Users\gianf\kalshi\set1_overshoot\data\depth\<date>\<hh>\depth.jsonl` | 08-01 02:58 |
| **24756** | `record_15m_opens_v2.py --hours 168` | this laptop | `C:\Users\gianf\crypto\data\btc15m_opens\opens_all_<date>.jsonl` | 08-01 13:42 |

Both were **alive and writing** at the time of this inventory. If the machine
sleeps, the gap is **irrecoverable** — Kalshi publishes no historical order-book
endpoint.

---

## Data on disk

| What | Where | Size | Re-pullable? |
|---|---|---|---|
| Polymarket fills / positions / books | `trading\wallet-copy-study\data\` | **12 GB** | Yes — permanently public on-chain |
| Stage 0–5 caches, Sackmann, tennis-data | `trading\kalshi-tennis\data\` | **1.6 GB** | **No.** Sackmann upstream is 404; this runs on a frozen mirror ending 2026-06-02. **Only copy.** |
| Crypto recordings, panel, spot, Deribit, Polymarket books | `C:\Users\gianf\crypto\data\` | **3.6 GB** | Partly. Recorded Kalshi books: **no**. |
| Tennis depth + candles | `C:\Users\gianf\kalshi\set1_overshoot\data\` | **384 MB** | Recorded depth: **no**. Candles: yes, for ~69 days. |
| Byte-identical backup of `kalshi-tennis/src` + `reports` | `trading\_archive\` | 296 KB | Redundant — safe to delete |
| youtube-signal DB: 718 gated videos, 683 cached transcripts, 11,277 known videos | `trading\youtube-signal\data\signal.db` | ~40 MB | **Yes**, but slowly — ~45 min of paced fetching to rebuild. Gitignored. |
| youtube-signal reports (gitignored from Phase 2 — they name real creators) | `trading\youtube-signal\reports\` | ~2 MB | Yes, regenerable from the DB. **Phase 0/1 copies remain in public git history**, see HANDOFF §5.7. |

**Kalshi's API is a ~69-day window.** Closed markets 404 and are gone. Never
re-pull to "replace" a local archive.

---

## MUST NOT BE TOUCHED

1. **PIDs 17892 and 24756.** Do not stop, restart, or move their working
   directories. This is why `C:\Users\gianf\kalshi\set1_overshoot\` and
   `C:\Users\gianf\crypto\` were **not** moved into `trading\` — only their code
   was copied. Moving a directory with an open file handle inside fails on
   Windows and would break the recorder.
2. **`trading\kalshi-tennis\data\`** — the only copy of the Stage 0–5 work,
   ~1 GB of derived artifacts that took a full session to compute, and its
   upstream source no longer exists.
3. **Recorded order books anywhere.** Not re-pullable at any price.
4. **Never copy folder-over-folder.** The laptop `kalshi` and the desktop
   `C:\Users\vinig\kalshi` share a name and have **zero files in common** — one
   is the Stage 0–5 research pipeline, the other is the live in-play bot. A
   folder-level copy in either direction destroys a project.
   *Update 08-03: the desktop projects are now renamed so this cannot recur —
   `kalshi-inplay-bot`, `kalshi-market-scan`, `polymarket-tennis-copy`,
   `ptis-polymarket`. The laptop's `kalshi-tennis` keeps its name. The one
   folder still called `kalshi` is the desktop live bot, which could not be
   moved — see below.*
5. **`C:\Users\vinig\OneDrive\Desktop\kalshi\kalshi_private_key.pem`** — the
   live order-signing key is sitting in a **OneDrive-synced folder**, byte
   identical to the one in the bot directory. Not deleted by any session; it
   is the user's call. Rotate on kalshi.com, then remove both old copies.

### ⚠️ Two source trees are temporarily duplicated

`set1_overshoot` and `crypto` now exist **both** at their original paths (live,
authoritative) and as code copies under `trading\`. Finish the move once the
recorders stop:

```bash
mv "C:/Users/gianf/kalshi/set1_overshoot" "C:/Users/gianf/trading/set1_overshoot_full" && mv "C:/Users/gianf/crypto" "C:/Users/gianf/trading/crypto_full"
```

Until then, **edit the originals, not the copies.**

---

## Repo

`C:\Users\gianf\trading` — 346 tracked files, **972 KiB** packed. Five projects
as siblings, no nested `.git`. Both inner repos' logs preserved to
`GIT_LOG_PRE_CONSOLIDATION.txt` (37 and 15 commits), author emails redacted.

`.gitignore` was written **before** the first commit: all `data/` directories,
`*.parquet` / `*.jsonl` / `*.db` / `*.sqlite` / `*.npz`, `.env`, keys and certs,
`__pycache__`, `.venv`, chat transcript exports, logs.

**Secret scan: clean.** No API keys, tokens, private keys, or credential-shaped
strings in any tracked file, and none in either inner repo's history. The code
reads **no** authentication environment variables at all — only analysis
parameters (`EXIT_CUT`, `COPY_MIN_MKTS`, …). Every venue call in this repo is a
public unauthenticated endpoint.

> **The signing credentials live on the desktop, not here** — `kalshi_client.py`
> and the live bot. Check that machine before pushing anything from it.

---

## The one number to carry forward

**Across all four projects, ~41 corrections. Every single one shrank the edge.
Not one ever revealed a larger effect.**

That asymmetry is what no edge looks like from the inside. A real edge survives
scrutiny and often grows under it. The durable output of this work is not a
strategy — it is [GUARDS.md](GUARDS.md).

---

## youtube-signal — Phase 2 read, batch 1 (2026-08-03)

**13 videos read in-session, 19 total. Cost $0.00. YouTube API quota 0 units.**
The previous handoff's blocker ("buy $5 of Anthropic API credit") was wrong: the
transcripts are read by the session model directly. `read_video.py` remains
unexecuted and unneeded.

| artifact | value |
|---|---|
| videos scored | 19 |
| claims | 205 (mechanism 67, procedure 40, result 39, spec 35, math 12, concept 11) |
| methods | 18 |
| tools | 58 — 30 URL-resolved, 1 dead, 27 reputation-judged, 31 unchecked |
| watch segments | 17 — **6.1 h runtime → 15 min to watch, 24×**; 4 videos needed zero |
| verdicts | ABSORB 8 · ABSORB_AND_RECOMMEND 7 · RESULTS_DISCOUNTED 2 · SKIP 2 |
| n-check on real claims | 4 SUPPORTED · 1 REFUTED · 1 INDISTINGUISHABLE FROM NOISE |
| S/H components that never fired | **none** (14 of 14 fired at least once) |
| `KNOWLEDGE.md` | 131,898 chars (gitignored) |

**Live prediction-market bot results found, all three negative or flat:**
$50 → $500 → **$0** over 814 trades with −$115 of that in fees; a Polymarket
stink-bid bot **break-even** over 34 trades; a "+1,560% ROI" headline that is
paper, against the same creator's one live account doing **−70% in a day**.

**The finding from `verify_tools.py`, not from the reading:** Polymarket CLOB
**V2 went live 28 Apr 2026** and both V1 clients are archived —
`py-clob-client` (1,234★, archived 11 May 2026) and `clob-client` (513★). V1
SDKs and V1-signed orders are unsupported on production. Two tutorials absorbed
this session teach V1; one is marked RECOMMEND. Current path is
`Polymarket/py-sdk` (alive, last push 31 Jul 2026).

**Rubric bug recorded, not patched:** S1/S2/S3 are trading-claim components, so a
pure API tutorial caps at S=3 and is auto-SKIP. Part Time Larry's Kalshi + LLM
build scored **S=3 H=9 → SKIP** with working code, a public repo and a real
itemised account. Claims still reach `KNOWLEDGE.md`; the verdict is unreliable.
Needs a build axis before more engineering videos are scored.

Code committed: `load_extraction.py` tools-upsert fix (`ON CONFLICT` targeted
`(name, url)` while the unique index is on `(name, COALESCE(url,''))` — trap #4
`NULL != NULL` surviving in a second place); `tool_reputation.py` +7 verdicts.
Judgments and transcripts stay local — `reports/` and `KNOWLEDGE.md` gitignored.

---

## signal-github — GitHub as a signal source (2026-08-03)

`signal-github/` · code committed · `data/`, `reports/`, `cache/`,
`GITHUB_KNOWLEDGE.md` gitignored · full write-up in `signal-github/HANDOFF.md`

**Rate limits, measured from headers, unauthenticated (`reports/step0.md`):**
core **60/hour** (the binding constraint) · search **600/hour** ·
raw.githubusercontent **unmetered** · **code search 401** although `/rate_limit`
advertises 60/min for it · dependents graph renders client-side, unscrapeable.
Substitutes: Sourcegraph public index for code search (labelled `F2_CODE`, never
as GitHub code search); forks of the client libraries for dependents.

| | |
|---|---|
| repos retrieved | 3,133 across 6 axes (laptop) · **2,806 rebuilt on the desktop 08-03** |
| gate PASS / STALE / DROP | 2,441 / 121 / 571 · **desktop: 2,221 / 126 / 459** |
| deep-fetched and scored | ~~105 (4.1%)~~ → **862 (36.7% of gated), 08-03, for ZERO core API calls** |
| how | `codeload` tarballs return the whole tree **and every file's contents**, unmetered. 1,197 archives in 266 s vs ~20 h at 60 tree-calls/hour. Depth no longer needs a token. |
| read in full | 12 (laptop) + **2 (desktop) → 5 more defects**, in repos scoring 10 and 9 |
| **fee audit, 862 repos** | 19 repos model Kalshi's maker fee correctly and have **65 stars between them**; 15 hardcode it to zero and have **1,493**. On a fact with published ground truth, popularity points the wrong way. |
| **F1 vs F2 Jaccard** | **0.033** (YouTube: 0.037 over 446 videos) |
| code-search hits found by neither family | 41 of 47 |
| **stars vs S_strict** | ~~rho +0.241, p 0.013 at n=105~~ — **RE-CORRECTED 08-03: −0.004, p 0.90 at n=862.** The n=105 bump decayed monotonically to zero (105 → 200 → 400 → 600 → 862). It was a small-sample artifact; **stars carry no usable information after all**, and the earlier withdrawal of that claim was itself the error. |
| forks vs S_strict / **tree_files vs S_strict** | −0.009 (p .79) / **+0.593 (p<0.0001)** — the ranking is substantially a *size* ranking; normalise for repo size before anything else |
| two repos both scoring 10/10 strict | one is 67 files/1 venue/no backtest and says so; the other 797 files/17 venues with a documented backtest API and no result. **The scorer cannot separate them; reading can.** |
| repos committing a backtest artifact behind their own strategy | **1 of 40** (`YichengYang-Ethan/oracle3`) |
| does that artifact support the strategy? | **no.** Headline reads +0.49%; the `performance` block in the same file reports total_pnl −8.80, Sharpe −1.5749, profit factor 0.9526, and the equity curve ends below its start. Zero mentions of fee, slippage or commission in 126 KB. |
| defects found only by reading | **5**, across 3 repos, all of which score well |
| S rubric ported literally | **19 of 40 scored 9–10** — saturated |
| same repos, strict rescore | **3 of 40** |
| S2 backtest-vs-live fire rate | 68% literal → **20% strict** |
| repos with a backtest module AND separate order-submission code | **8 of 40** |
| repos publishing a backtest artifact behind their own profit claim | **0 of 40** |
| "trust me bro" — results claim, <10 commits, no artifact | **3 of 40** |

**Toolchain finding — Polymarket's v1 client family is archived.**
`py-clob-client` 1,234★, `clob-client` 513★, `rs-clob-client` 691★,
`ctf-exchange` 356★, and `Polymarket/agents` 3,758★ (the org's most-starred repo,
last push 2024-11-05) are all archived. Live successors `py-clob-client-v2` 163★,
`py-sdk` 82★, `clob-client-v2` 76★. **The stars are on the dead libraries.**
9 repos in the corpus import v1, 3 import v2. Independently corroborated by the
parallel `youtube-signal` session, which dates CLOB V2 go-live to 28 Apr 2026.

**Venue asymmetry that decides the market-making question.** Both venues price
fees on expected earnings, `rate × qty × p × (1−p)`, peaking at p=0.50.

> **CORRECTED 2026-08-03.** This section previously read *"Kalshi:
> `ceil_to_cent(0.07 × qty × p × (1−p))`, same rate for makers and takers"*,
> sourced from a third-party repo's fee model. **That is wrong.** Kalshi's own
> fee schedule (effective 7 Jul 2026, now retrieved) charges takers
> `roundup(M × 0.07 × C × P × (1−P))` with `M` defaulting to **1**, and makers
> `roundup(M × 0.0175 × C × P × (1−P))` — a quarter of the rate — with `M`
> defaulting to **0**. Confirmed independently against the live API: of 12,396
> series, **12,266 are taker-only and exactly 130 charge makers**. So Kalshi
> makers pay nothing on 98.9% of series — but **107 of the 130 are Sports**,
> including `KXATPMATCH` and `KXWTAMATCH`, the tennis series this repo trades.
> Full write-up and reproduction: [signal-github/CORRECTIONS.md](signal-github/CORRECTIONS.md),
> `signal-github/src/kalshi_fees_census.py`. Canonical arithmetic:
> `common/kalshi_fees.py`.

Polymarket: **makers pay zero**, plus a 20–25% rebate share of taker fees, plus
a daily liquidity-rewards pool. Kalshi's only official client is 17 months
stale; Polymarket ships eight maintained repos. Kalshi's edge is the API docs —
published rate-limit tiers (Basic 200/100 tokens/s → Prestige 6,000/8,000) and
FIX.

**You cannot properly backtest Kalshi.** `evan-kolberg/prediction-market-
backtesting` (1,094★, 254 files, NautilusTrader-based, working Polymarket L2
replay) states Kalshi support depends on L2 historical book data it could not
get; Kalshi backtests there are trade-tick replay only. Free Polymarket L2:
**PMXT hourly archive** (`r2v2.pmxt.dev`) from 2026-02-21 onward.

**Copy trading, measured rather than argued.** The same repo replays a real
public wallet's filled-trade ledger against historical L2: **72 of 153 orders
filled (47%)**, ledger cash PnL **−223.88 USDC**. Four structural reasons, none
fixable by better wallet screening: the original trades are already inside the
replayed book; a public timestamp is a fill observation, not a decision time;
maker fills cannot be reconstructed from fill rows; thin books make IOC fills
contingent on queue position. **This contradicts the copy-trading method in
`youtube-signal/KNOWLEDGE.md`, which argues only about which wallet to pick.**

**The one strategy whose income is not required to overcome a fee first:**
maker-only two-sided quoting, in fee-free or low-fee categories. *(Corrected
2026-08-03: this read "on Polymarket", on the false premise that Kalshi charged
makers the full taker rate. Kalshi makers pay zero on 12,266 of 12,396 series,
so the venue is not excluded on fee grounds — but the 130 that do charge makers
are 107 Sports series, i.e. where Kalshi's liquidity is. The rule that survives
is **pick a series whose maker multiplier is zero**, on either venue.)*
Reference implementation `warproxxx/poly-maker` (1,427★, MIT, 83 tests, mypy
strict, 37 commits over 465 days, migrated to v2). Post BUY-YES at `r−δ` and
BUY-NO at `(1−r)−δ`; both legs are bids, so a filled pair merges to 1 USDC at
locked edge `1−p−q` — **the exit is also a maker action**. It makes no
performance claim and **has no backtest**; its own README says the replay
backtester is "not yet built". Maker realism needs L3/MBO data that does not
exist publicly, so the best strategy found and the best data found do not
compose.

**Wrong or untrusted (full list in HANDOFF §5):** the venue **legal terms were
never read** — `kalshi.com` returned HTTP 429 to every request including its own
fee-schedule PDF, and `polymarket.com/tos` renders client-side; every automation
statement rests on developer docs, not agreements. Coverage is 1.6%. Credibility
metrics are complete for all 40 — but 40 of 2,562. A rate-limiter bug in
`gh.core` slept on an already-expired reset timestamp and cost most of this
session's depth; fixed. The commits-vs-substance rho changed sign between n=30
and n=40, so at this sample size its sign is noise, not a weak signal. 77 repos were dropped
for having no fetchable README — a real false-negative channel. Both repos read
were selected by the strict score and were unusually honest; the corpus is
almost certainly less honest than they are.

**Next:** put a free `GITHUB_TOKEN` in the environment. Core goes 60/hour →
5,000/hour and code search unblocks, with no code change — `gh.py` already reads
it. Both constraints on this session are fixed by one environment variable.

---

## Desktop machine â€” inventory, consolidation, three blocked tasks (2026-08-03)

Machine `C:\Users\vinig`. Full write-up in [DESKTOP_INVENTORY.md](DESKTOP_INVENTORY.md).
This section is additive â€” nothing above it was rewritten except the three
thread rows that these tasks closed.

### What is running on the desktop: nothing

No `python`, `node`, or any other interpreter in the full process table. No
`.recorder.lock`. Empty Startup folder. No matching scheduled task. **The
desktop contributes zero running processes and zero open file handles**, so
none of its directories were frozen. It has also therefore **recorded nothing
since 17:32 UTC on 30 July** â€” the 8.5 h book recording in `kalshi-market-scan`
is a closed, finite asset, not a growing one.

### Consolidated into this repo

| Was | Now | Why renamed |
|---|---|---|
| `C:\Users\vinig\kalshi markets` | `kalshi-market-scan/` | space in path; `kalshi*` prefix collision |
| `C:\Users\vinig\tennis copy trade` | `polymarket-tennis-copy/` | space in path |
| `â€¦\Codex\2026-07-23\files-mentioned-by-the-user-master-2` | `ptis-polymarket/` | the old name carried no meaning |
| Discord export from `OneDrive\Desktop\kalshi` | `discord-trades-export/` | unique artifact, promoted out of a stale snapshot |

`kalshi-market-scan` had **21 commits and no remote** â€” that history existed
nowhere else and is preserved verbatim to
`kalshi-market-scan/GIT_LOG_PRE_CONSOLIDATION.txt`. Its inner `.git` and two
empty nested `.git` dirs were removed; **no nested `.git` remains**.

Archived, not deleted, under the gitignored `_archive/`: the stale 26 Jul
desktop snapshot of the bot (4 files, all superseded), `weather-market-bot-staging`
(redundant against the pushed `weather-market-bot`), `polymarket-shadow-copy`
(superseded by PTIS), and three byte-identical duplicate prompts.

`.gitignore` was extended **before** anything was staged: `node_modules/`,
sqlite `-wal`/`-shm` sidecars, `*.bak*`, `bot_state.json` (it carries live
Kalshi order ids), `*.lock`, and `discord-trades-export/` (it names real people
and this repo is public). **Secret scan on the staged set: clean** â€” 245 files,
no keys, no data blobs. The only `.env`-shaped hit is `.env.example`,
placeholders only.

### âš  One directory could NOT be moved

`C:\Users\vinig\kalshi` â€” **the live money bot** â€” is still outside the repo.
It is the working directory of the agent session doing the move, and Windows
refuses to rename a directory with an open handle. Per the standing rule the
move was **not forced**. It has **no version control of any kind**, which makes
it the single most exposed thing on either machine.

To finish, from a session whose cwd is *not* that folder:

```bash
mv "C:/Users/vinig/kalshi" "C:/Users/vinig/trading/kalshi-inplay-bot"
```

Nothing is running, so this will succeed. `bot_state.json` (5 open positions
with live order ids) and `kalshi_private_key.pem` travel with it; both are
gitignored.

### Task 1 â€” desktop recorder integrity: NO BUG. Tier B unblocked.

Verified three independent ways:

1. **Code.** `kalshi_client.py:232-237` already reads `yes_bid_dollars`,
   `yes_ask_dollars`, `last_price_dollars`, `volume_fp`, `open_interest_fp`.
   `record_data.py` reads the dataclass attributes, not raw API fields.
2. **The recorded tape.** `tennis_data.jsonl` (7,170 rows) and
   `tennis_data_laptop.jsonl` (27,083 rows) are **98.6â€“99.6% populated** â€”
   0.0% zero asks in both. A legacy read would have written 0 everywhere,
   because `_cents()` returns 0 on `TypeError`.
3. **The live API**, 100 open markets sampled today: every legacy field
   (`yes_bid`, `yes_ask`, `last_price`, `volume`, `open_interest`) is `None`
   on **100/100**; every `*_dollars`/`*_fp` replacement is present on 100/100.

**One thing worth noting for the laptop:** the running
`crypto/src/record_15m_opens_v2.py` also reads the new names (`:174-185`) and
stores them under local keys, so its `valid()` gate at `:56` is correct. The
`_v2` rewrite *is* this fix. No action.

Candlestick objects are a **different schema** â€” there `yes_bid` is still a
valid nested dict with `open_dollars`/`close_dollars`. `pull_data.py:132-133`,
`soccer/src/inplay.py`, `set1_overshoot/src/p0_candles.py` and the
`kalshi-tennis` downloaders all read candles and are all correct. Do not
"fix" them.

### Task 2 â€” v3 dedupe field: CLEAN. The 14,162-market result stands.

The mirrored-market dedupe is ordered by **signal timestamp**, with **ticker
order** as the stable tie-break. Neither `volume` nor `open_interest` nor
`last_price` participates.

The chain, end to end:

| Step | Where | What it does |
|---|---|---|
| 1 | `engine.py:56` | `df.sort_values(["ticker","ts"])` â€” the only sort in the file |
| 2 | `engine.py:157` | `groupby("ticker", sort=False)` â†’ first-appearance order = ticker order |
| 3 | `run_backtest.py:54` | `build_views(...)`, no re-sort |
| 4 | `strategies.py:147` | candidates appended in views order |
| 5 | `strategies.py:149` | `cand.sort(key=lambda x: x[0])` â€” **entry timestamp only**; Python sorts stably, so ties fall back to ticker order |
| 6 | `strategies.py:153-155` | chronological walk; `busy[v.event]` blocks the mirrored side |

Corroborating: **`strategies.py` contains zero occurrences of `volume`,
`open_interest`, `last_price` or `settlement`.** The dedupe is decidable at
decision time. No look-ahead. Per the pre-declared criterion, this is the
"ticker/API order â‡’ clean" branch.

That makes the ~100Ã— evidence base **usable**, and its verdict â€” 480 configs,
0 profitable, S1 âˆ’9.36Â¢ against random-entry S5 âˆ’8.28Â¢ â€” the best-supported
result in the programme.

### Task 3 â€” live bot "sizing bug": it is a martingale, not a sizing bug

Reconstructed from `_orders.json` / `_fills.json`, market
`KXITFWMATCH-26JUL28SAGLEV-LEV`, 28 Jul:

| Time | Action | Price | Qty | Sizing check |
|---|---|---|---|---|
| 14:17:24 | buy | 49Â¢ | 12 | $6.25 / 0.49 = 12 âœ” |
| 14:30:54 | stopped out | 29Â¢ | âˆ’12 | âˆ’$2.40 |
| 14:31:18 | **re-entry, +24 s** | 31Â¢ | 20 | $6.25 / 0.31 = 20 âœ” |
| 14:43:24 | stopped out | 18Â¢ | âˆ’20 | âˆ’$2.60 |
| 14:43:47 | **re-entry, +23 s** | 19Â¢ | 32 | $6.25 / 0.19 = 32 âœ” |
| 15:07:47 | stopped out | 11Â¢ | âˆ’32 | âˆ’$2.56 |

**64 = 12 + 20 + 32.** Every individual size is arithmetically correct.
`qty = int(stake / price)` did exactly what it says. **That is the bug**: a
*fixed-dollar* stake buys *more contracts as the price falls*, so re-entering a
collapsing market martingales automatically. Nobody designed it; it is an
emergent property of sizing by dollars. Total â‰ˆ **âˆ’$7.56 on one match in 50
minutes**, on a $125 book.

Three conditions had to hold at once, and all three did:

1. sizing by dollars â†’ each re-entry larger than the last;
2. `rearm_above = stop_price + 2` (`position_manager.py`) â†’ a **2Â¢ bounce off
   your own stop** re-arms entry, which in a falling market is ordinary
   bid/ask noise;
3. `max_daily_loss_pct = 0` â†’ nothing counted the damage across legs.

Fixed, with the sequence replayed against the patched engine as the test:

| Fix | Where |
|---|---|
| `max_contracts = 15` hard cap on any single entry | `tennis_engine.Config` |
| `reentry_cooldown_sec = 900` (was 24 s in practice) | `tennis_engine`, gated in `evaluate()` |
| `max_reentries_per_event = 1` | same |
| the `min_entry_price` floor now applies to **re-entries too** | same |
| `max_daily_loss_pct` **0 â†’ 15** | same |
| re-arm at `max(entry_price, stop+2)` instead of `stop+2` | `position_manager._fire_stop` |
| durable `stop_history` ledger, persisted across restarts | `position_manager` |
| `run_both.bat` / `autostart.bat` default **`--live` â†’ `--watch`** | both |

The ledger is deliberately **not** stored on `ManagedPosition`: `check()`
retires a stopped-out position two passes after it closes, so anything held
there is gone within about a minute â€” far short of a 15-minute cooldown. It
survives retirement *and* an app restart, so closing and reopening the app is
no longer a way to buy straight back in.

Replay result: all three SAGLEV legs are now refused (four independent ways
each); a legitimate 70Â¢ entry is **unchanged** at 8 contracts / $5.72.

`autostart.bat` was designed to be shortcut into Startup, so as written it would
resume **unattended live trading** after any reboot. It now comes back read-only.

**Still the user's call, and unchanged by any of this:** the bot's own
14,162-market backtest says this strategy loses ~9Â¢/trade against a ~4Â¢ cost
base, and the config it runs was tuned on 125â€“137 live observations and appears
nowhere in the sweep. These fixes stop it losing money *fast*. They do not make
it profitable.

> **These fixes live in `C:\Users\vinig\kalshi`, which is NOT in this repo**
> (see above). They are unversioned and exist on one machine only until that
> folder is moved.

---

## Two root files added (2026-08-03)

Both exist at the repo root and are tracked.

- **[INBOX.md](INBOX.md)** — idea capture. Every new idea goes here first: one
  line, dated, no thinking. Routing to a repo is a separate pass. It is a queue,
  not an archive — routed ideas are moved out or deleted.
- **[HOW_THIS_WORKS.md](HOW_THIS_WORKS.md)** — the operating manual. The four
  repos and what belongs in each (**trading** public, **nexus** private/
  ChatGPT-led, **Vinex-OS** private, **weather-market-bot** private — never
  mixed); STATUS.md as the shared brain, pulled at the start of every session
  and merged and pushed at the end; one session per folder; HANDOFF.md written
  and pushed at every session end; and why pushing is mandatory — the
  coordinating chat reads this repo over the public web and cannot see disk.

It also records the machine split: **the desktop `C:\Users\vinig` is now
primary; the laptop is a recording box only.** The "this laptop" rows in the
running-processes table above are that box.

---

## Fee consolidation + stale-claim sweep (2026-08-03)

Full write-up: [common/HANDOFF.md](common/HANDOFF.md). Commits `214ad96`,
`a92ef01`, `aeb26b9`.

**The Kalshi fee formula existed 15 times across five codebases, not the 9 the
desktop inventory recorded.** Nine of the fifteen carried the float-dust bug
(`0.07*100*0.5*0.5*100 == 175.00000000000003`, which `ceil()` bills as 176c);
each overcharged on **115 of 1,881 price/size cells, always by exactly 1c,
never under**. Two were in the live-money path.

`common/kalshi_fees.py` is now the single implementation — exact Decimal, 47
tests, self-verifying at import. All 14 other sites delegate to it. 210 tests
pass across common, kalshi-market-scan, crypto, set1_overshoot and
wallet-copy-study.

**Live bot: the fee call changed and nothing else.** Verified over 49,500
price/size cells (189 changed, all strictly cheaper by 1c, none dearer) and 760
`evaluate()` snapshots (entry, size, target, exit identical in every one).
Note the overcharged sizes cluster near the 50c fee peak — **the three legs of
the 28 Jul martingale do not hit the bug.** It was real, but it is not what
made that day expensive.

**`fee_type` re-verified against the live API** (full pagination, 12,396
series): 12,266 `quadratic`, **130** `quadratic_with_maker_fees`, 14 with
`fee_multiplier` 0. The 130 reproduces exactly; the total grew 12,368 → 12,396.

Three **hardcoded maker fees** found and fixed. The most consequential:
`crypto/src/fees.py` asserted "ZERO are crypto" and set the crypto maker rate
to 0 — **`KXBTCMAX150` and `KXBTCMAX125` are crypto and do charge makers.** The
ladder series this project trades are all `quadratic`, so the ladder results
stand; the generalisation was the defect.

**The maker RATE is now settled.** It was not API-verifiable (the series object
carries no maker-rate field) and two incompatible readings were live in the
repo. The sibling `signal-github` session then retrieved Kalshi's own schedule
(effective 7 Jul 2026): `maker = roundup(M × 0.0175 × C × P × (1−P))`, M
defaulting to 0. The quadratic quarter-of-taker reading is **correct**; the
flat 0.25c/contract reading in `set1_overshoot/src/p5_task1b.py` is
**superseded** and marked. S008's verdict survives either way.

> ⚠ **107 of the 130 maker-fee series are Sports, and `KXATPMATCH` /
> `KXWTAMATCH` are among them.** Kalshi charges makers precisely on the tennis
> series this repo trades. Whether they also hold most of the liquidity is
> **unmeasured**.

**Eight retracted claims were still stated as fact and are now marked inline**
— four in `kalshi-market-scan/docs/` (the 40× depth collapse, the 8,090-market
weather n, the "seven families clear the capacity bar" framing, and the
bucket-by-bucket calibration claim), and four found by sweeping the rest of the
repo against LEDGER.md (S013/S012 in `depth_analysis.md`, S012 doing
load-bearing work in `PREREGISTRATION_PARTB.md`, W006 in three unmarked places
in `COPY_TRADING_VERDICT.md`, C015 as a ticked item in `crypto/PROGRESS.md`).
Nothing was deleted — deleting is how a retracted number gets re-derived.

**No verdict anywhere changed.** Every affected conclusion was already NO-GO or
already negative, and each still is on evidence that holds.

> ⚠ **`kalshi-market-scan` has no rows in [LEDGER.md](LEDGER.md) at all.** Its
> claims were invisible to the ledger cross-check and were found only because
> the brief named them. It keeps a separate `docs/HYPOTHESIS_LEDGER.md` that
> nothing links to. **Ledger it, or link it.**

