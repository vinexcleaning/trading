# STATUS.md

As of **2026-08-02**. Inventory only — nothing was recomputed and no process was
touched. Claims: [LEDGER.md](LEDGER.md). Reusable checks: [GUARDS.md](GUARDS.md).

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
| **v3 structural-event backtest** | "14k markets, 480 configs, 0 profitable" — **~100× the evidence base of everything else and never verified.** Lives on the desktop. | **One grep**: which field orders its mirrored-market dedupe? `volume`/`open_interest`/`last_price` ⇒ void; ticker/API order ⇒ clean. ~10 minutes. |
| **Desktop recorder integrity** | Kalshi's legacy price fields now return `None`; values moved to `*_dollars`/`*_fp`. Never checked. | **One grep** of `kalshi_client.py` and `record_data.py`. If they write `None`, every recorded book on that machine is worthless. This gates all Tier B work. |
| **Live bot position-sizing bug** | 64 contracts placed against an intended 9, on a $125 bankroll, with `max_daily_loss_pct = 0 (OFF)`. Cause never identified. | Diagnose or disable the bot. **Top standing financial risk.** |
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
| repos retrieved | **3,133** across 6 axes |
| gate PASS / STALE / DROP | 2,441 / 121 / 571 |
| deep-fetched and scored | **105** (4.1% of gated); credibility for 40 |
| read in full | **9** — the top 10 by strict score bar one |
| **F1 vs F2 Jaccard** | **0.033** (YouTube: 0.037 over 446 videos) |
| code-search hits found by neither family | 41 of 47 |
| **stars vs S_strict** | **rho +0.241, p 0.013 at n=105** (was −0.019 at n=40 — corrected) |
| forks vs S_strict / commits vs S_strict | +0.126 (p .20) / +0.147 (p .36) |
| | **stars explain ~6% of rank variance — weak, real, still useless for sorting** |
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
fees on expected earnings, `rate × qty × p × (1−p)`, peaking at p=0.50. Kalshi:
`ceil_to_cent(0.07 × qty × p × (1−p))`, **same rate for makers and takers**
(source: `evan-kolberg/prediction-market-backtesting`
→ `adapters/kalshi/fee_model.py:908`, modified 2026-03-11). Polymarket: **makers
pay zero**, plus a 20–25% rebate share of taker fees, plus a daily liquidity-
rewards pool. Kalshi's only official client is 17 months stale; Polymarket ships
eight maintained repos. Kalshi's edge is the API docs — published rate-limit
tiers (Basic 200/100 tokens/s → Prestige 6,000/8,000) and FIX.

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
maker-only two-sided quoting on Polymarket, in fee-free or low-fee categories.
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
