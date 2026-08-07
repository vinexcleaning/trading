# STATUS.md

As of **2026-08-02** for the laptop, **2026-08-03** for the desktop. The laptop
inventory recomputed nothing and touched no process. The desktop pass moved
directories and patched the live bot â€” see the dated section at the end.
Claims: [LEDGER.md](LEDGER.md). Reusable checks: [GUARDS.md](GUARDS.md).
How the repos and sessions fit together: [HOW_THIS_WORKS.md](HOW_THIS_WORKS.md).
New ideas go in [INBOX.md](INBOX.md) first, before deciding where they belong.

---

## Threads â€” CLOSED

| Thread | Why it closed | Next action |
|---|---|---|
| **Tennis set-1 overshoot** | The undershoot is real (âˆ’2.42pp, p=0.0009, n=3,436) and **uncollectable** against a 3.61pp cost bar. 0 of 25 time/tier and 0 of 10 margin buckets clear. | **Stop.** nâ‰ˆ3,970 needed for a 2Â¢ edge; more slicing has negative EV. |
| **Crypto ladder modelling** | **No model beats the Kalshi mid** on 250 events. Two tie, two lose. The positive control proves the test would have found a 5% bias. | None. NO-GO fired; Task 5 was correctly never run. |
| **Polymarket copy trading** | Wallet skill is real and persists, but the copyable part (+0.937pp, falling to âˆ’0.135pp in the fee era) is **smaller than the spread** (â‰¥1.0pp). | **Do not build the bot.** Phase 5 deliberately skipped. |
| **Stage 0â€“5 player model** | **The model loses to the bookmakers**: +0.01922 Brier [+0.01438,+0.02417], n=2,645. Stage 4 gate failed. | None. Sackmann features end 2026-06-02 and the upstream repos are 404. **⚠ "the upstream repos are 404" is too strong — corrected 2026-08-05, see the bot-forensics section and ledger row B020.** Three are 404; `tennis_MatchChartingProject` is live at 399★ and a third-party point-by-point mirror was pushed 2026-06-25. Does not change the verdict (the model lost to the bookmakers), only the recoverability. |
| **BTC 15-minute (KXBTC15M)** | Structurally dead â€” `floor_strike` equals the prior window's settlement in 99.86% of 6,261 markets, so every contract is minted at-the-money on the peak of the fee curve. | None. Structural kill, not statistical. |
| **Ladder arbitrage** | 0 monotonicity violations in 3,187 scans; 1 gross bucket-sum violation in 1,135, **unprofitable net**. The ladder is wide enough that legging it is self-defeating. | None (10.5 min of recording â€” a preliminary null, but with a structural mechanism). |

## Threads â€” ALIVE

| Thread | State | **Single next action** |
|---|---|---|
| **Depth recorder (tennis)** | Running since 08-01 06:58. 79â€“120 markets, 0.55 s pacing, content-checked Ã—5/day at 98.8% non-empty. | Leave it. It is accruing the only asset that cannot be re-pulled. |
| **15m opens recorder (crypto)** | Running since 08-01 13:42, `--hours 168`. | Leave it. |
| ~~v3 structural-event backtest~~ | **RESOLVED 08-03 â€” CLEAN, the result stands.** See "Desktop, 2026-08-03" below. | None. |
| ~~Desktop recorder integrity~~ | **RESOLVED 08-03 â€” no bug. The desktop already reads `*_dollars`/`*_fp`.** Tier B is unblocked. | None. |
| ~~Live bot position-sizing bug~~ | **DIAGNOSED AND FIXED 08-03.** Not a sizing bug â€” a martingale. See below. | ~~Decide whether it trades at all~~ **DECIDED 08-03: it does not. Trading is OFF** â€” see "Live bot turned off" below. |
| **Score-staleness (already fixed)** | `fetched_at` was stamped at cache read, so the 30 s guard never rejected anything. | Nothing to fix â€” but **no live entry result predating the fix is a valid test of the entry logic.** Treat the 4-for-10 as void. |
| **Label coverage (tennis)** | Blocked. Apify at a monthly hard limit; Flashscore's `dayOffsets` is âˆ’7..+7 against a âˆ’68 need. | Restore quota, then label day-by-day via `crawlstone/tennis-scraper` or `tennisexplorer` (~$20, not $3.44). Only path above 13.9% coverage. |
| **youtube-signal** | **UNBLOCKED and productive. 38 videos read, $0.00 spent, 0 API units.** The old "buy $5 of API credit" blocker was wrong â€” transcripts are read in-session. Two corpora: broad (746 videos, 370 PASS, 29 read) and a **targeted Kalshi/Polymarket one** (470 videos, 328 PASS, **9 read, 134 claims, 25 tools**). **Nine actionable findings** incl. the three-number check, itemised fees on both venues, 8 backtest-realism rules, the `filtfilt` look-ahead trap, and an adverse-selection result that **contradicts our own maker thesis**. See the dated section below. | **Read more of the targeted corpus.** `$env:SIGNAL_DB="kalshi_edge"` then `src/target_rank.py`. The broad corpus's retrieval test is still NOT DEMONSTRATED and is secondary to the practical hunt. |
| **tennis-paper-forward** | **NEW 2026-08-06. Built, tested, running.** A **PAPER-ONLY** forward test: 16 bots (5 mentalities x 3 exit modes + a no-trade control) over the SAME pool of ~123 live Kalshi singles tennis matches. No credentials, no order endpoint, GET-only allowlist - enforced by a test that plants a violation and asserts the detector bites. Every decision, and its stake, logged with full reasoning BEFORE the result exists. 49 tests pass here, 52 across `common/`. **Pre-registered as UNTESTABLE on P&L at n=50** (MDE 22.8c under BH across 16, against a 3.6c cost bar; ~2,000 matches/bot needed). What IS measurable at 50: execution cost, brief coverage, mentality divergence, and machine survival. | **Move it to the laptop** - `tennis-paper-forward/deploy/LAPTOP_SETUP.md`, ~15 min, and leave it a week. |
| **signal-github** | **Working, not blocked.** 4,017 retrieved / 3,252 gated / **3,165 scored (97.3%) for ZERO core API calls** via codeload tarballs; **credibility for 3,146**; 4 read. 283 repos then retroactively DROPPED for having <=1 commit (gate G1's second half, applied at last), so the live scored set is **2,882**. Token in signal-github/.env -> 5,000/hr + code search (916 repos no other axis found). Callable as **/github-signal**. Stars settled: rho -0.008 p 0.65 at n=3,165 - the earlier +0.241 correction was itself the error. `trust_me_bro` 19.1% of 2,717 and **weakly POSITIVELY correlated with substance** (+0.064, p 0.0009) - the earlier 'uncorrelated' reading was n=822. Fees now primary-sourced on both venues (C1/C1a/C2). | **Read the KalshiEX Rulebook** - the member agreement is silent on automation and says the Rulebook governs, so it is the only open item that could change the venue answer. It defeats HTTP and a real browser. |

---

## What is running, where

| PID | Process | Machine | Writes to | Started |
|---|---|---|---|---|
| **17892** | `record_depth.py` | this laptop | `C:\Users\gianf\kalshi\set1_overshoot\data\depth\<date>\<hh>\depth.jsonl` | 08-01 02:58 |
| **24756** | `record_15m_opens_v2.py --hours 168` | this laptop | `C:\Users\gianf\crypto\data\btc15m_opens\opens_all_<date>.jsonl` | 08-01 13:42 |

Both were **alive and writing** at the time of this inventory. If the machine
sleeps, the gap is **irrecoverable** â€” Kalshi publishes no historical order-book
endpoint.

---

## Data on disk

| What | Where | Size | Re-pullable? |
|---|---|---|---|
| Polymarket fills / positions / books | `trading\wallet-copy-study\data\` | **12 GB** | Yes â€” permanently public on-chain |
| Stage 0â€“5 caches, Sackmann, tennis-data | `trading\kalshi-tennis\data\` | **1.6 GB** | **No** for the derived Stage 0–5 caches — those are still the **only copy** and took a full session to compute. ~~Sackmann upstream is 404~~ **⚠ corrected 2026-08-05 (ledger B020): partly recoverable.** `tennis_atp`/`tennis_wta`/`tennis_slam_pointbypoint` are 404, but `JeffSackmann/tennis_MatchChartingProject` is live (399★) and `Aneeshers/tennis-sackmann-archive` mirrors the point-by-point data. Frozen mirror still ends 2026-06-02. |
| Crypto recordings, panel, spot, Deribit, Polymarket books | `C:\Users\gianf\crypto\data\` | **3.6 GB** | Partly. Recorded Kalshi books: **no**. |
| Tennis depth + candles | `C:\Users\gianf\kalshi\set1_overshoot\data\` | **384 MB** | Recorded depth: **no**. Candles: yes, for ~69 days. |
| Byte-identical backup of `kalshi-tennis/src` + `reports` | `trading\_archive\` | 296 KB | Redundant â€” safe to delete |
| youtube-signal DB: 718 gated videos, 683 cached transcripts, 11,277 known videos | `trading\youtube-signal\data\signal.db` | ~40 MB | **Yes**, but slowly â€” ~45 min of paced fetching to rebuild. Gitignored. |
| youtube-signal reports (gitignored from Phase 2 â€” they name real creators) | `trading\youtube-signal\reports\` | ~2 MB | Yes, regenerable from the DB. **Phase 0/1 copies remain in public git history**, see HANDOFF Â§5.7. |

**Kalshi's API is a ~69-day window.** Closed markets 404 and are gone. Never
re-pull to "replace" a local archive.

---

## MUST NOT BE TOUCHED

1. **PIDs 17892 and 24756.** Do not stop, restart, or move their working
   directories. This is why `C:\Users\gianf\kalshi\set1_overshoot\` and
   `C:\Users\gianf\crypto\` were **not** moved into `trading\` â€” only their code
   was copied. Moving a directory with an open file handle inside fails on
   Windows and would break the recorder.
2. **`trading\kalshi-tennis\data\`** â€” the only copy of the Stage 0â€“5 work,
   ~1 GB of derived artifacts that took a full session to compute, and its
   upstream source no longer exists.
3. **Recorded order books anywhere.** Not re-pullable at any price.
4. **Never copy folder-over-folder.** The laptop `kalshi` and the desktop
   `C:\Users\vinig\kalshi` share a name and have **zero files in common** â€” one
   is the Stage 0â€“5 research pipeline, the other is the live in-play bot. A
   folder-level copy in either direction destroys a project.
   *Update 08-03: the desktop projects are now renamed so this cannot recur â€”
   `kalshi-inplay-bot`, `kalshi-market-scan`, `polymarket-tennis-copy`,
   `ptis-polymarket`. The laptop's `kalshi-tennis` keeps its name. The one
   folder still called `kalshi` is the desktop live bot, which could not be
   moved â€” see below.*
5. **`C:\Users\vinig\OneDrive\Desktop\kalshi\kalshi_private_key.pem`** â€” the
   live order-signing key is sitting in a **OneDrive-synced folder**, byte
   identical to the one in the bot directory. Not deleted by any session; it
   is the user's call. Rotate on kalshi.com, then remove both old copies.

### âš ï¸ Two source trees are temporarily duplicated

`set1_overshoot` and `crypto` now exist **both** at their original paths (live,
authoritative) and as code copies under `trading\`. Finish the move once the
recorders stop:

```bash
mv "C:/Users/gianf/kalshi/set1_overshoot" "C:/Users/gianf/trading/set1_overshoot_full" && mv "C:/Users/gianf/crypto" "C:/Users/gianf/trading/crypto_full"
```

Until then, **edit the originals, not the copies.**

---

## Repo

`C:\Users\gianf\trading` â€” 346 tracked files, **972 KiB** packed. Five projects
as siblings, no nested `.git`. Both inner repos' logs preserved to
`GIT_LOG_PRE_CONSOLIDATION.txt` (37 and 15 commits), author emails redacted.

`.gitignore` was written **before** the first commit: all `data/` directories,
`*.parquet` / `*.jsonl` / `*.db` / `*.sqlite` / `*.npz`, `.env`, keys and certs,
`__pycache__`, `.venv`, chat transcript exports, logs.

**Secret scan: clean.** No API keys, tokens, private keys, or credential-shaped
strings in any tracked file, and none in either inner repo's history. The code
reads **no** authentication environment variables at all â€” only analysis
parameters (`EXIT_CUT`, `COPY_MIN_MKTS`, â€¦). Every venue call in this repo is a
public unauthenticated endpoint.

> **The signing credentials live on the desktop, not here** â€” `kalshi_client.py`
> and the live bot. Check that machine before pushing anything from it.

---

## The one number to carry forward

**Across all four projects, ~41 corrections. Every single one shrank the edge.
Not one ever revealed a larger effect.**

That asymmetry is what no edge looks like from the inside. A real edge survives
scrutiny and often grows under it. The durable output of this work is not a
strategy â€” it is [GUARDS.md](GUARDS.md).

---

## youtube-signal â€” Phase 2 read, batch 1 (2026-08-03)

**13 videos read in-session, 19 total. Cost $0.00. YouTube API quota 0 units.**
The previous handoff's blocker ("buy $5 of Anthropic API credit") was wrong: the
transcripts are read by the session model directly. `read_video.py` remains
unexecuted and unneeded.

| artifact | value |
|---|---|
| videos scored | 19 |
| claims | 205 (mechanism 67, procedure 40, result 39, spec 35, math 12, concept 11) |
| methods | 18 |
| tools | 58 â€” 30 URL-resolved, 1 dead, 27 reputation-judged, 31 unchecked |
| watch segments | 17 â€” **6.1 h runtime â†’ 15 min to watch, 24Ã—**; 4 videos needed zero |
| verdicts | ABSORB 8 Â· ABSORB_AND_RECOMMEND 7 Â· RESULTS_DISCOUNTED 2 Â· SKIP 2 |
| n-check on real claims | 4 SUPPORTED Â· 1 REFUTED Â· 1 INDISTINGUISHABLE FROM NOISE |
| S/H components that never fired | **none** (14 of 14 fired at least once) |
| `KNOWLEDGE.md` | 131,898 chars (gitignored) |

**Live prediction-market bot results found, all three negative or flat:**
$50 â†’ $500 â†’ **$0** over 814 trades with âˆ’$115 of that in fees; a Polymarket
stink-bid bot **break-even** over 34 trades; a "+1,560% ROI" headline that is
paper, against the same creator's one live account doing **âˆ’70% in a day**.

**The finding from `verify_tools.py`, not from the reading:** Polymarket CLOB
**V2 went live 28 Apr 2026** and both V1 clients are archived â€”
`py-clob-client` (1,234â˜…, archived 11 May 2026) and `clob-client` (513â˜…). V1
SDKs and V1-signed orders are unsupported on production. Two tutorials absorbed
this session teach V1; one is marked RECOMMEND. Current path is
`Polymarket/py-sdk` (alive, last push 31 Jul 2026).

**Rubric bug recorded, not patched:** S1/S2/S3 are trading-claim components, so a
pure API tutorial caps at S=3 and is auto-SKIP. Part Time Larry's Kalshi + LLM
build scored **S=3 H=9 â†’ SKIP** with working code, a public repo and a real
itemised account. Claims still reach `KNOWLEDGE.md`; the verdict is unreliable.
Needs a build axis before more engineering videos are scored.

Code committed: `load_extraction.py` tools-upsert fix (`ON CONFLICT` targeted
`(name, url)` while the unique index is on `(name, COALESCE(url,''))` â€” trap #4
`NULL != NULL` surviving in a second place); `tool_reputation.py` +7 verdicts.
Judgments and transcripts stay local â€” `reports/` and `KNOWLEDGE.md` gitignored.

---

## youtube-signal â€” targeted Kalshi/Polymarket hunt (2026-08-04)

**38 videos read total. Cost $0.00. YouTube API quota 0 units.** Full detail in
[youtube-signal/HANDOFF.md](youtube-signal/HANDOFF.md).

Two corpora, deliberately separate (`$env:SIGNAL_DB` selects one):

| | broad | **targeted (`kalshi_edge`)** |
|---|---|---|
| queries | 28 | **27**, in build / strategy / data / validate |
| videos â†’ PASS | 746 â†’ 370 (50%) | **470 â†’ 328 (70%)** |
| within-family Jaccard | 0.69â€“0.76 | **0.86â€“0.92** |
| read | 29 | 9 |

**Narrow venue-specific queries are both more on-topic and more reproducible.**
Worth reusing for any future topic.

### The four things worth acting on

**1. The three-number check** (`ANGZMUercB4`, 343 views). `edge = fair
probability âˆ’ price âˆ’ cost`, where fair probability is the **de-vigged sharp
sportsbook consensus**, not your own model. Trade only on clearly positive edge.
Corollary: *agreeing with the market is a losing strategy* â€” you pay the spread
for fair odds.

**2. The fee schedule, itemised** (`eVJHCsZIGg0`, 43 views). Kalshi â‰ˆ **7% of net
winnings** on resolution, tier dependent. Polymarket **taker fee by category:
sports 0.75%, politics 1%, crypto 1.8%, geopolitics 0%** â€” on winnings, not
stake. Plus Polygon gas, plus the spread. Prediction-market YES+NO sums to 100
(no vig) against a sportsbook's ~104.7%.

**3. Backtest realism, 8 rules** (`Ea9BeOc_Yiw`, 144 views) â€” the single most
useful build finding. Fill model (taker at ask, maker only when ask crosses),
fees in-engine, **no forward-looking**, **latency 50â€“150 ms random plus 200 ms on
taker fills**, book-depth check before entry, plot every fill to verify visually.
Its headline: **"without latency, most strategies are profitable."** Data source
named: tick-by-tick Polymarket 5m/15m BTC/ETH â€” top-of-book ~5 GB per 3â€“4 months,
full book ~150 GB.

**4. A validation framework** (`Jd0BHJflnw0`, 53 views). Research ledger written
*before* any price; three trials (timestamp / common-cause / executability);
**monotonicity constraint** â€” P(touch 120k) â‰¤ P(touch 110k), a violation is an
inconsistency but not automatically profit. Stress test by **deleting the top
five trades**. Multi-leg partial fills turn a risk-neutral position directional.

**5. Walk-forward, with the collapse measured twice** (`lIMu8ysJW68`, S=10). Train
12 months, LOCK parameters, test 3 months blind, roll. 19 folds on SPY 2018â€“2024.
A retail RSI backtest showing **199% became 5%** out-of-sample â€” the engine
reports **75% of the return as curve fitting**. Then he swaps in "institutional"
maths (ATR, volatility-scaled momentum, Butterworth filter): **1,500% became
7%.** Conclusion, stated against his own upgrade: *adding complex maths does not
create an edge.*

> **The single most important line for anyone having Claude build a backtester:**
> coding agents default to scipy's **`filtfilt`**, which is zero-phase â€” it runs
> the filter forwards *and backwards*, so today's indicator uses **future
> prices**. Silent look-ahead bias that fabricates returns. **Demand `lfilter`.**

**6. A 96.83% win rate that is real and not yours** (`8u6jy8v56ww`, S=10).
Polymarket 5-min BTC up/down: four consecutive up-minutes then betting up is
claimed to win **96.83%** over 12,272 periods, with the market provably flat
(49.99/50.01) so it is not a bull artifact. Break-even is 51.02% after
Polymarket's 2% winner fee. **Why it is still not tradeable, and the video says
most of it itself:** 95% of profits go to bots; you get a 60-second window; the
**Chainlink oracle lags Binance**, so bots front-run the settlement print.

> Reasoned here, not in the video: **if the settlement oracle lags spot, then
> "four green minutes" is partly stale news about a move that already happened.**
> The win rate is high *because* the signal is late â€” and lateness is exactly
> what makes it uncapturable by anyone slower than a bot reading Binance direct.
> One mechanism explains the 96.83%, the 95%-to-bots, and the slippage at once.

Also flagged: its "conservative" projection of $2,500 â†’ $40,000/month is a
**1,500% monthly return**, and the 96.83% subset's own n is never stated (only
the 12,272 total; the qualifying subset is plausibly ~1,500).

**7. Polymarket's fee curve and maker rebates, at API level** (`7HXoCMMXr-8`).
Fees exist **only on 15-minute crypto markets**; everything else is free. The
taker fee runs 0 → **1.56% and PEAKS AT 50¢** — the same expected-earnings shape
as Kalshi, independently confirmed. Taker fees fund a **daily USDC maker rebate**
paid pro-rata on executed maker liquidity. The maker share **fell from 100% to
20%** in January 2026, so Polymarket keeps 80%. A public wallet (88888) earned
~$2,000 in rebates and **stopped trading the week fees landed**.

> **API gotcha:** calling the REST endpoint directly requires the **fee rate
> inside the signed order** (official clients handle it). Per-market rates arrive
> in the market JSON. Undocumented: how long an order must rest to count as
> maker, and what the fee curve's `C` parameter is.

**8. Why informed retail still loses** (`LQ3-k8gKw74`, 24 views). Three traps —
confidence (you were right, but the price moved 68→76 before you entered),
urgency (**up to 25% of volume is wash trading**, per Columbia), belonging
(copying a wallet inherits the position but not the entry, context or exit plan).
Cited: LBS study of 1.72M accounts finding **only 3% drive price discovery**;
$40M in *guaranteed* arbitrage extracted across 86M transactions 2023–25.
Its one-sentence test: *does the current price reflect a genuine inefficiency,
and do I have a specific falsifiable reason to think the true probability differs?*

**9. ⚠ A 20-year professional contradicts our own maker thesis** (`rrKRhjye1sw`).
**"If you're new, be a market TAKER, not a market maker."** Adverse selection:
your resting offer is taken *only* when it's good for the other side. Worked
example — post 40¢ into a 50/50 game; if your team makes a big play nobody takes
it, if they concede you **get filled at a now-terrible price**. You are filled
only in the states where you were wrong.

> **This is the most important tension found so far.** `signal-github` concluded
> maker-only quoting is "the one strategy whose income is not required to
> overcome a fee first" — reasoning purely from **fee schedules**. Both are right:
> **maker economics win on fees and lose on adverse selection, a cost that
> appears nowhere in a fee model.** That is the missing term, and it is exactly
> why `poly-maker` ships no backtest — maker realism needs L3/MBO data that
> doesn't exist publicly.

Also note #9 disagrees with #1 on *where* the edge is: #1 hunts low-liquidity
niche props (nobody watching), #9 says the better prices are on **high-liquidity
marquee events** where recreational flow dilutes the institutional makers. Two
different edges — and the liquidity ceiling that kills the first doesn't bind the
second.

### Two independent corroborations of this repo's own results

- The monotonicity check is **exactly** the ladder-arbitrage test already run
  here (0 violations in 3,187 scans; 1 gross bucket-sum violation, unprofitable
  net). An unrelated source reaches the same caveat: inconsistency â‰  profit,
  because of spread and depth.
- Fees hurt **cheap** contracts disproportionately â€” the bar moved ~2% on a 69Â¢
  contract and **~6% on an 18Â¢** one. Same structure as the KXBTC15M fee-curve
  finding and the tennis 3.61pp cost bar, reached from the ticket side.

### The recurring shape, again

The Kalshi strategy video's own author discloses that his demonstrated mispriced
prop had **~$60 of liquidity**. The edge is real *because* nobody is looking,
which is precisely why nobody can size into it. Same shape as the copy-trading
and tennis threads: **a real effect smaller than the cost of reaching it.**

---

## signal-github â€” GitHub as a signal source (2026-08-03 â†’ 08-04)

`signal-github/` Â· code + `CORRECTIONS.md` committed Â· `data/`, `reports/`,
`cache/`, `GITHUB_KNOWLEDGE.md` gitignored Â· full write-up in
`signal-github/HANDOFF.md` Â· **callable as `/github-signal`**
(`.claude/skills/github-signal/SKILL.md`).

**The 60/hour core budget stopped being the constraint.**
`codeload.github.com/<repo>/tar.gz/<branch>` returns the whole file tree **and
every file's contents** in one request, carries no `X-RateLimit-*` headers, and
`/rate_limit` reads identically either side of a download. 1,397 archives in
**367 seconds** against ~23 hours at 60 tree-calls/hour. Use the legacy URL form;
the documented `/refs/heads/` form times out. A token is still worth having â€” it
is what unblocks code search â€” but depth no longer waits on it.

| | |
|---|---|
| repos retrieved | **4,017** (laptop corpus separately at 2,562 gated â€” see the warning below) |
| gate PASS / STALE / DROP | **3,091 / 161 / 765** |
| **deep-fetched and scored** | ~~105 (4.1%)~~ â†’ **3,165 = 97.3% of gated, for ZERO core API calls** |
| credibility metrics | **3,146** (was 40) - complete |
| retroactively dropped, <=1 commit | **283** - gate G1's second half needs a commit count, so it only fired once credibility was complete. Live scored set is **2,882**. |
| repos read in full | **4 this session**, loaded via `load_extraction.py` with zero rejections |
| **code search** | GitHub's own index: **1,141 hits, 916 found by no other axis** (Sourcegraph managed 15) |
| **F1âˆ©F2 Jaccard** | **0.032** â€” fourth measurement, with 0.033, 0.036 and YouTube's 0.037 |
| strict S â‰¥ 9 | 154 of 3,165 (**4.9%**) â€” 7.5% at n=40, 7.4% at n=862, 6.7% at n=2,260, and 4.9% at full coverage. It DRIFTS DOWN as the tail is reached, which is what a prescreen that front-loads the best repos should produce - not instability, but not the flat line an earlier reading of 79Ã— change in sample. |

### âš  Two coverage numbers exist in this repo and both are correct

`3a2f36a` says "2472 scored (96%)"; `19d5dba` says 2,260 at 69.5%. They measure
**two different databases on two machines** â€” `data/github.db` is gitignored, so
laptop and desktop each built their own corpus from shared code. Denominators
differ too: 2,472/2,562 there, 2,260/**3,252** here, because this machine's
retrieval included the code-search axis that added 916 repos the other corpus
does not have. **The machine with the lower percentage has the larger corpus.**
Always state which machine a coverage figure came from.

### Stars: settled, and the previous correction was the error

`rho(stars, S_strict) = âˆ’0.008, p = 0.65` **at n = 3,165** (full coverage). The n=105 sample gave
+0.241 (p 0.013) and the project withdrew its "stars carry no information" claim
on it; the bump decays monotonically 105 â†’ 200 â†’ 400 â†’ 600 â†’ 862 â†’ 2,260 and finally 3,165. It was
a small-sample artifact. **The original claim stands; the withdrawal was wrong.**

What replaced it: `rho(tree_files, S_strict) = +0.593` â€” the score was 59%
explained by **file count**. `src/size_adjust.py` fits it out (rho â†’ 0.12).
Validated against an external fact — of the **49** repos that provably model
Kalshi's maker fee correctly, the raw score puts **0** in its top 25 and the
adjusted one **4**; top 50, **0 → 5**; top 100, **4 → 6**. **But at top 200 it is
now WORSE, 11 → 9.** The adjustment helps where it matters (deciding what to
read) and slightly hurts in the long tail. Reported because it is a limitation of
an instrument built this session, found by re-running it at full coverage.

### Three axes, and none of them works alone

`trust_me_bro` fires on **519 of 2,717 (19.1%)** against 3 of 40 (7.5%) last
session - the sampling-bias warning, quantified.

**Overturned by full coverage, and worth stating plainly:** at n=822 this file
recorded the flag as **uncorrelated** with substance (rho +0.029, p 0.41). At
n=2,717 it is **weakly POSITIVE and significant: rho +0.064, p 0.0009** - flagged
repos score slightly HIGHER on substance (median s_adj +0.19 against -0.20).
That direction makes sense on reflection: making a results claim at all requires
having built something. The practical conclusion is unchanged - the two axes
measure different things and `shortlist.py` must combine them - but *orthogonal*
was measured at too small an n and is withdrawn.

`stars` vs `s_adj` also weakened, from -0.094 (p 0.007) to **-0.037 (p 0.052),
no longer significant** - consistent with stars carrying nothing at all.
`s_adj`'s own top pick had **1 commit** and claimed "Guaranteed profit".
`src/shortlist.py` combines substance, credibility and fee-correctness.

### What the corpus actually contains (`src/classify.py`, venue from imports)

| | |
|---|---|
| venue | polymarket 1,194 Â· **none 1,013** Â· kalshi 472 Â· both 458 |
| kind | live_trader 883 Â· market_maker 670 Â· data_collector 642 Â· backtester 245 Â· arbitrage 181 Â· copy_trader 113 |
| places real orders | 1,328 of 3,137 |
| Polymarket client | **v1-ARCHIVED 749 vs v2 121** â€” **6.2:1** toward the dead library |

**1,013 repos (32%) import neither venue.** They passed the README topic gate and
never touch Kalshi or Polymarket â€” invisible to the gate, obvious to the
classifier. Query it: `python src/classify.py --venue kalshi --kind market_maker --alive`.

### Fees â€” both venues now on primary evidence (`signal-github/CORRECTIONS.md`)

**C1.** Kalshi does **not** charge makers and takers the same rate â€” see the
corrected block above. Taker `0.07`, maker `0.0175` with multiplier defaulting to
**0**; **130 of 12,396 series charge makers and they are the liquid ones**
(107 Sports, incl. `KXATPMATCH`/`KXWTAMATCH`).

**C1a.** The published maker rate is right; **applying it without checking the
series' `fee_type` is wrong** â€” and only repos careful enough to model maker fees
at all can make this error. Two independent, rigorous repos do
(`artyomderkach-bit`, `hamad-khawaja`), on 15-minute crypto series where **zero**
maker fee applies. Both penalise themselves. Invisible to any constant-vs-schedule
check *because the constant is correct*. This is exactly what
`common/kalshi_fees.py` refuses to guess.

**C2.** Polymarket measured from Gamma, 2,100 markets: **makers pay zero on 100%**
of markets with a schedule (`takerOnly: true`); taker 0.04 / 0.05 / 0.07 by
category; rebate **15â€“25%** (a refinement â€” the old claim said 20â€“25%). Trap:
`makerBaseFee` reads `1000` on 94% of markets and is **not** the fee â€” the CLOB
API returns 0 for the same markets; `feeSchedule` is authoritative.

**Venue verdict, corrected twice and now settled: Polymarket for maker-only
quoting.** Not because Kalshi charges makers everywhere â€” it does not â€” but
because Kalshi charges them *precisely where the liquidity is*, offers no rebate,
and its member agreement (clause T) states designated market makers get *"discounts
on fees, rebates on fees, revenue share from fees"*, cancel-on-disconnect and
*"greater throughput"*, and that these *"may give market makers a trading
advantage over members who are not market makers."*

### Legal terms â€” one closed, one open, one impossible

- **Kalshi fee schedule: READ.** `kalshi.com/docs/kalshi-fee-schedule.pdf`. The
  429 is intermittent, not a block â€” browser UA plus a retry.
- **Kalshi member agreement: READ.** `kalshi.com/docs/kalshi-member-agreement.pdf`.
  **Silent on automation** â€” zero occurrences of bot, automated, algorithmic, API,
  scrape, manipulat*, spoof, wash trade.
- **KalshiEX Rulebook: NOT READ, and it now matters most.** The agreement says
  *"the Kalshi Rulebook will govern"* in any conflict, so it is the operative text
  for whether bots are permitted. `kalshi.com/regulatory/rulebook` yields 581
  characters from 145 KB of HTML and an empty body in a real browser.
- **Polymarket terms: NOT RETRIEVABLE.** `/tos` returns 200, sets the correct page
  title, and renders the **homepage body** â€” in a real browser, after client-side
  routing, with the footer link clicked. *"Read it in a browser" is withdrawn.*

### Reading still finds what scoring cannot â€” 4 repos, 6 defects

All six invisible to every computed component, in repos scoring 9 and 10.
`evan-kolberg` contradicts itself on maker fees between its instrument and its fee
model, and a passive strategy reads the one the backtest ignores. `aulekator`
(557â˜…, 4 commits) invents three fee schedules for one venue, ships `fee_rate_bps=0`
live, advertises a "self-learning" feature its own README calls a placeholder, and
carries an MIT badge with no LICENSE. Best repo found: **`artyomderkach-bit/kalshi-15m-market-maker`**
(0â˜…) â€” states what it withholds, makes no profit claim, ships in paper mode, and
imports one fair-value function into both engine and backtest *"so they can never
drift apart"*. Its README independently corroborates this programme's own finding:
*"almost every edge that looked real in-sample decayed out-of-sample."*

**Next:** (1) read the KalshiEX Rulebook â€” the only open item that could change
the venue answer; (2) **credibility is now complete** (3,146) - the remaining gap is `closed_issues`,
left NULL because its search call was 3x the cost of everything else combined and
no reported result uses it; (3) read further down
`reports/shortlist.md` - 4 repos read produced 6 defects, every one invisible to
all computed components.

---

## Desktop machine Ã¢â‚¬â€ inventory, consolidation, three blocked tasks (2026-08-03)

Machine `C:\Users\vinig`. Full write-up in [DESKTOP_INVENTORY.md](DESKTOP_INVENTORY.md).
This section is additive Ã¢â‚¬â€ nothing above it was rewritten except the three
thread rows that these tasks closed.

### What is running on the desktop: nothing

No `python`, `node`, or any other interpreter in the full process table. No
`.recorder.lock`. Empty Startup folder. No matching scheduled task. **The
desktop contributes zero running processes and zero open file handles**, so
none of its directories were frozen. It has also therefore **recorded nothing
since 17:32 UTC on 30 July** Ã¢â‚¬â€ the 8.5 h book recording in `kalshi-market-scan`
is a closed, finite asset, not a growing one.

### Consolidated into this repo

| Was | Now | Why renamed |
|---|---|---|
| `C:\Users\vinig\kalshi markets` | `kalshi-market-scan/` | space in path; `kalshi*` prefix collision |
| `C:\Users\vinig\tennis copy trade` | `polymarket-tennis-copy/` | space in path |
| `Ã¢â‚¬Â¦\Codex\2026-07-23\files-mentioned-by-the-user-master-2` | `ptis-polymarket/` | the old name carried no meaning |
| Discord export from `OneDrive\Desktop\kalshi` | `discord-trades-export/` | unique artifact, promoted out of a stale snapshot |

`kalshi-market-scan` had **21 commits and no remote** Ã¢â‚¬â€ that history existed
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
and this repo is public). **Secret scan on the staged set: clean** Ã¢â‚¬â€ 245 files,
no keys, no data blobs. The only `.env`-shaped hit is `.env.example`,
placeholders only.

### Ã¢Å¡Â  One directory could NOT be moved

`C:\Users\vinig\kalshi` Ã¢â‚¬â€ **the live money bot** Ã¢â‚¬â€ is still outside the repo.
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

### Task 1 Ã¢â‚¬â€ desktop recorder integrity: NO BUG. Tier B unblocked.

Verified three independent ways:

1. **Code.** `kalshi_client.py:232-237` already reads `yes_bid_dollars`,
   `yes_ask_dollars`, `last_price_dollars`, `volume_fp`, `open_interest_fp`.
   `record_data.py` reads the dataclass attributes, not raw API fields.
2. **The recorded tape.** `tennis_data.jsonl` (7,170 rows) and
   `tennis_data_laptop.jsonl` (27,083 rows) are **98.6Ã¢â‚¬â€œ99.6% populated** Ã¢â‚¬â€
   0.0% zero asks in both. A legacy read would have written 0 everywhere,
   because `_cents()` returns 0 on `TypeError`.
3. **The live API**, 100 open markets sampled today: every legacy field
   (`yes_bid`, `yes_ask`, `last_price`, `volume`, `open_interest`) is `None`
   on **100/100**; every `*_dollars`/`*_fp` replacement is present on 100/100.

**One thing worth noting for the laptop:** the running
`crypto/src/record_15m_opens_v2.py` also reads the new names (`:174-185`) and
stores them under local keys, so its `valid()` gate at `:56` is correct. The
`_v2` rewrite *is* this fix. No action.

Candlestick objects are a **different schema** Ã¢â‚¬â€ there `yes_bid` is still a
valid nested dict with `open_dollars`/`close_dollars`. `pull_data.py:132-133`,
`soccer/src/inplay.py`, `set1_overshoot/src/p0_candles.py` and the
`kalshi-tennis` downloaders all read candles and are all correct. Do not
"fix" them.

### Task 2 Ã¢â‚¬â€ v3 dedupe field: CLEAN. The 14,162-market result stands.

The mirrored-market dedupe is ordered by **signal timestamp**, with **ticker
order** as the stable tie-break. Neither `volume` nor `open_interest` nor
`last_price` participates.

The chain, end to end:

| Step | Where | What it does |
|---|---|---|
| 1 | `engine.py:56` | `df.sort_values(["ticker","ts"])` Ã¢â‚¬â€ the only sort in the file |
| 2 | `engine.py:157` | `groupby("ticker", sort=False)` Ã¢â€ â€™ first-appearance order = ticker order |
| 3 | `run_backtest.py:54` | `build_views(...)`, no re-sort |
| 4 | `strategies.py:147` | candidates appended in views order |
| 5 | `strategies.py:149` | `cand.sort(key=lambda x: x[0])` Ã¢â‚¬â€ **entry timestamp only**; Python sorts stably, so ties fall back to ticker order |
| 6 | `strategies.py:153-155` | chronological walk; `busy[v.event]` blocks the mirrored side |

Corroborating: **`strategies.py` contains zero occurrences of `volume`,
`open_interest`, `last_price` or `settlement`.** The dedupe is decidable at
decision time. No look-ahead. Per the pre-declared criterion, this is the
"ticker/API order Ã¢â€¡â€™ clean" branch.

That makes the ~100Ãƒâ€” evidence base **usable**, and its verdict Ã¢â‚¬â€ 480 configs,
0 profitable, S1 Ã¢Ë†â€™9.36Ã‚Â¢ against random-entry S5 Ã¢Ë†â€™8.28Ã‚Â¢ Ã¢â‚¬â€ the best-supported
result in the programme.

### Task 3 Ã¢â‚¬â€ live bot "sizing bug": it is a martingale, not a sizing bug

Reconstructed from `_orders.json` / `_fills.json`, market
`KXITFWMATCH-26JUL28SAGLEV-LEV`, 28 Jul:

| Time | Action | Price | Qty | Sizing check |
|---|---|---|---|---|
| 14:17:24 | buy | 49Ã‚Â¢ | 12 | $6.25 / 0.49 = 12 Ã¢Å“â€ |
| 14:30:54 | stopped out | 29Ã‚Â¢ | Ã¢Ë†â€™12 | Ã¢Ë†â€™$2.40 |
| 14:31:18 | **re-entry, +24 s** | 31Ã‚Â¢ | 20 | $6.25 / 0.31 = 20 Ã¢Å“â€ |
| 14:43:24 | stopped out | 18Ã‚Â¢ | Ã¢Ë†â€™20 | Ã¢Ë†â€™$2.60 |
| 14:43:47 | **re-entry, +23 s** | 19Ã‚Â¢ | 32 | $6.25 / 0.19 = 32 Ã¢Å“â€ |
| 15:07:47 | stopped out | 11Ã‚Â¢ | Ã¢Ë†â€™32 | Ã¢Ë†â€™$2.56 |

**64 = 12 + 20 + 32.** Every individual size is arithmetically correct.
`qty = int(stake / price)` did exactly what it says. **That is the bug**: a
*fixed-dollar* stake buys *more contracts as the price falls*, so re-entering a
collapsing market martingales automatically. Nobody designed it; it is an
emergent property of sizing by dollars. Total Ã¢â€°Ë† **Ã¢Ë†â€™$7.56 on one match in 50
minutes**, on a $125 book.

Three conditions had to hold at once, and all three did:

1. sizing by dollars Ã¢â€ â€™ each re-entry larger than the last;
2. `rearm_above = stop_price + 2` (`position_manager.py`) Ã¢â€ â€™ a **2Ã‚Â¢ bounce off
   your own stop** re-arms entry, which in a falling market is ordinary
   bid/ask noise;
3. `max_daily_loss_pct = 0` Ã¢â€ â€™ nothing counted the damage across legs.

Fixed, with the sequence replayed against the patched engine as the test:

| Fix | Where |
|---|---|
| `max_contracts = 15` hard cap on any single entry | `tennis_engine.Config` |
| `reentry_cooldown_sec = 900` (was 24 s in practice) | `tennis_engine`, gated in `evaluate()` |
| `max_reentries_per_event = 1` | same |
| the `min_entry_price` floor now applies to **re-entries too** | same |
| `max_daily_loss_pct` **0 Ã¢â€ â€™ 15** | same |
| re-arm at `max(entry_price, stop+2)` instead of `stop+2` | `position_manager._fire_stop` |
| durable `stop_history` ledger, persisted across restarts | `position_manager` |
| `run_both.bat` / `autostart.bat` default **`--live` Ã¢â€ â€™ `--watch`** | both |

The ledger is deliberately **not** stored on `ManagedPosition`: `check()`
retires a stopped-out position two passes after it closes, so anything held
there is gone within about a minute Ã¢â‚¬â€ far short of a 15-minute cooldown. It
survives retirement *and* an app restart, so closing and reopening the app is
no longer a way to buy straight back in.

Replay result: all three SAGLEV legs are now refused (four independent ways
each); a legitimate 70Ã‚Â¢ entry is **unchanged** at 8 contracts / $5.72.

`autostart.bat` was designed to be shortcut into Startup, so as written it would
resume **unattended live trading** after any reboot. It now comes back read-only.

**Still the user's call, and unchanged by any of this:** the bot's own
14,162-market backtest says this strategy loses ~9Ã‚Â¢/trade against a ~4Ã‚Â¢ cost
base, and the config it runs was tuned on 125Ã¢â‚¬â€œ137 live observations and appears
nowhere in the sweep. These fixes stop it losing money *fast*. They do not make
it profitable.

> **These fixes live in `C:\Users\vinig\kalshi`, which is NOT in this repo**
> (see above). They are unversioned and exist on one machine only until that
> folder is moved.

---

## Two root files added (2026-08-03)

Both exist at the repo root and are tracked.

- **[INBOX.md](INBOX.md)** â€” idea capture. Every new idea goes here first: one
  line, dated, no thinking. Routing to a repo is a separate pass. It is a queue,
  not an archive â€” routed ideas are moved out or deleted.
- **[HOW_THIS_WORKS.md](HOW_THIS_WORKS.md)** â€” the operating manual. The four
  repos and what belongs in each (**trading** public, **nexus** private/
  ChatGPT-led, **Vinex-OS** private, **weather-market-bot** private â€” never
  mixed); STATUS.md as the shared brain, pulled at the start of every session
  and merged and pushed at the end; one session per folder; HANDOFF.md written
  and pushed at every session end; and why pushing is mandatory â€” the
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

`common/kalshi_fees.py` is now the single implementation â€” exact Decimal, 47
tests, self-verifying at import. All 14 other sites delegate to it. 210 tests
pass across common, kalshi-market-scan, crypto, set1_overshoot and
wallet-copy-study.

**Live bot: the fee call changed and nothing else.** Verified over 49,500
price/size cells (189 changed, all strictly cheaper by 1c, none dearer) and 760
`evaluate()` snapshots (entry, size, target, exit identical in every one).
Note the overcharged sizes cluster near the 50c fee peak â€” **the three legs of
the 28 Jul martingale do not hit the bug.** It was real, but it is not what
made that day expensive.

**`fee_type` re-verified against the live API** (full pagination, 12,396
series): 12,266 `quadratic`, **130** `quadratic_with_maker_fees`, 14 with
`fee_multiplier` 0. The 130 reproduces exactly; the total grew 12,368 â†’ 12,396.

Three **hardcoded maker fees** found and fixed. The most consequential:
`crypto/src/fees.py` asserted "ZERO are crypto" and set the crypto maker rate
to 0 â€” **`KXBTCMAX150` and `KXBTCMAX125` are crypto and do charge makers.** The
ladder series this project trades are all `quadratic`, so the ladder results
stand; the generalisation was the defect.

**The maker RATE is now settled.** It was not API-verifiable (the series object
carries no maker-rate field) and two incompatible readings were live in the
repo. The sibling `signal-github` session then retrieved Kalshi's own schedule
(effective 7 Jul 2026): `maker = roundup(M Ã— 0.0175 Ã— C Ã— P Ã— (1âˆ’P))`, M
defaulting to 0. The quadratic quarter-of-taker reading is **correct**; the
flat 0.25c/contract reading in `set1_overshoot/src/p5_task1b.py` is
**superseded** and marked. S008's verdict survives either way.

> âš  **107 of the 130 maker-fee series are Sports, and `KXATPMATCH` /
> `KXWTAMATCH` are among them.** Kalshi charges makers precisely on the tennis
> series this repo trades. Whether they also hold most of the liquidity is
> **unmeasured**.

**Eight retracted claims were still stated as fact and are now marked inline**
â€” four in `kalshi-market-scan/docs/` (the 40Ã— depth collapse, the 8,090-market
weather n, the "seven families clear the capacity bar" framing, and the
bucket-by-bucket calibration claim), and four found by sweeping the rest of the
repo against LEDGER.md (S013/S012 in `depth_analysis.md`, S012 doing
load-bearing work in `PREREGISTRATION_PARTB.md`, W006 in three unmarked places
in `COPY_TRADING_VERDICT.md`, C015 as a ticked item in `crypto/PROGRESS.md`).
Nothing was deleted â€” deleting is how a retracted number gets re-derived.

**No verdict anywhere changed.** Every affected conclusion was already NO-GO or
already negative, and each still is on evidence that holds.

> âš  **`kalshi-market-scan` has no rows in [LEDGER.md](LEDGER.md) at all.** Its
> claims were invisible to the ledger cross-check and were found only because
> the brief named them. It keeps a separate `docs/HYPOTHESIS_LEDGER.md` that
> nothing links to. **Ledger it, or link it.**

### `high_sweep.py` re-run after the maker fix

Full table: [kalshi-inplay-bot/backtest/HIGH_SWEEP_RERUN.md](kalshi-inplay-bot/backtest/HIGH_SWEEP_RERUN.md).
All 8 maker rows improved (mean **+0.13Â¢/contract**), all 4 taker rows came
back **byte-identical** as the control. **No configuration flipped sign** â€” 2 of
12 rows positive before, 2 after. The two positive rows are both the
*optimistic* fill model this file's own header calls "the single easiest way to
fake a profitable backtest"; the honest `maker-strict` arm is still **âˆ’1.30 to
âˆ’2.42Â¢/contract** in every band. Consistent with S008/S009.

## â›” Live bot turned OFF (2026-08-03) â€” user decision

**The tennis in-play bot will not place orders.** A kill switch is now in
`kalshi-inplay-bot/kalshi_client.py`: while the file
`kalshi-inplay-bot/TRADING_DISABLED` exists, `_check_writable()` raises before
anything reaches the order endpoint. It **fails closed** and is checked *before*
the `read_only` flag, so it cannot be bypassed by constructing the client
differently. Verified: buy and sell both blocked with `read_only=False`, and
the guard releases cleanly when the file is removed.

**To trade again: delete `TRADING_DISABLED`. Nothing else needs changing.**

**Why:** the strategy's own 13,658-market backtest returns **â‰ˆ âˆ’9Â¢/trade**, and
the maker variants clear their cost bar only under an unrealistic fill model.
This is a decision about whether the edge exists, not a bug.

**State at shutdown, verified three ways:** no bot process was running (the only
Python process on the machine belonged to the concurrent `signal-github`
session); **no autostart shortcut was installed** and no scheduled task existed,
so it was not going to restart on its own; `bot_state.json` was last written
**2026-07-28 13:59** and lists 5 positions, all on matches dated 27â€“28 July,
which settled automatically ~6 days earlier. **No open exposure.**

> âš  **Still open and unrelated:** `kalshi_private_key.pem`, the live
> order-signing key, exists both in the bot folder **and** in a OneDrive-synced
> Desktop folder. Turning trading off does not address that. Rotating it on
> kalshi.com and deleting both old copies remains worth doing, and is the
> user's call.

## Repo integrity work (2026-08-03, autonomous continuation)

Commits `69a52de`, `f49aa0a`, `4710163`. Detail in
[common/HANDOFF.md](common/HANDOFF.md) Part 2.

**A guard now stops the fee formula being reimplemented again.**
[`common/tests/test_no_fee_reimplementation.py`](common/tests/test_no_fee_reimplementation.py)
walks every `.py` in the repo; anything with a fee fingerprint must import the
shared module or sit in an allowlist **with a written reason**. GUARDS #6
already said "one shared, tested `fees.py`" â€” and the count went from 3 to
**17 after that instruction**. A convention did not work; a failing test does.
It immediately found two more copies the manual sweep missed (`probe_01_depth`,
`probe_02_fees`), both now repointed. **True count was 17, not 15.**

**`kalshi-market-scan` is ledgered** â€” 16 rows, K001â€“K016, `LEDGER.md`
Section 6. Tally 216 â†’ 233 rows, RETRACTED 41 â†’ 45.

> ### âš  It paid immediately: **K015 is W011**
> The same claim â€” **+7.05pp on n=98,766** â€” had a row in *two* projects with
> *two different statuses*. `wallet-copy-study` had **already recomputed and
> retracted it** (+2.09pp [âˆ’1.37,+5.35] gross, **âˆ’0.29pp net**), while
> `kalshi-market-scan` still called it the finding that reframes its whole
> copy-trading block and the bot audit called it the corpus's least-supported
> claim. None of them knew the answer sat one section away.
>
> **A claim that travels between projects gets a fresh row and a fresh status
> each time, and the weakest status is the one a reader happens to find.**
> Cross-reference by number and n, not by project. Worth sweeping the other
> three projects the same way.

**Maker-fee tennis series hold 34.4% of volume on 5.8% of markets** â€” 5.9Ã—
concentration, `KXATPMATCH` alone 21.9%. Answers the question `signal-github`
`e3b87d7` left open. S010's "91% of the book" is a *count* and is correct
(94.2%); by *volume* the taker-only series are 65.6%. Does **not** revive the
maker case. See [common/TENNIS_MAKER_LIQUIDITY.md](common/TENNIS_MAKER_LIQUIDITY.md)
and LEDGER S025.

> Two traps hit and fixed while measuring it, both already in this repo's
> record: volume is **`volume_fp`** (the old name returns `None` and sums
> silently to **zero** â€” C024's renamed-field trap, and the first run reported
> a clean fake result), and tennis series must be matched by **prefix, not
> substring** (`WTAX` "Wealth tax" and `KXLOWTAUS` "Lowest temperature in
> Austin" both contain `WTA` â€” T017 is a retraction caused by exactly that).





---

## social-signal — the cross-platform join, Reddit, the Discord calls (2026-08-04)

`social-signal/` · code, `HANDOFF.md`, `FINDINGS_FROM_READING.md` and
`PAID_OPTIONS.md` committed · `data/`, `reports/`, `cache/` gitignored ·
full write-up in [social-signal/HANDOFF.md](social-signal/HANDOFF.md) · the
readable payoff is
[social-signal/FINDINGS_FROM_READING.md](social-signal/FINDINGS_FROM_READING.md).

**Cost $0.00. No API key for any platform exists or was needed.** Two sibling
sessions ran in this same working tree throughout; their databases were read and
never written, and every commit staged explicit paths.

### Three premises in the brief were wrong, one of them the top-priority platform

| the brief said | measured 2026-08-04 |
|---|---|
| Reddit: *"free JSON API, add `.json` to any URL, ~60/min"* | `reddit.com`, `old.reddit.com` and `oauth.reddit.com` **all** return `User-agent: *` / `Disallow: /`; `.json` returns **403** to a bot UA and a browser UA alike |
| *"Pushshift-style archives for history"* | `api.pushshift.io` → **403 "Not authenticated"**, moderators only |
| Discord: *"174 owner trade calls"* | 174 owner **messages**; 47 carry a call verb; **folded to one per (date, player) it is 34** |

Collection runs instead against **`arctic-shift.photon-reddit.com`**, the public
Reddit research archive that replaced Pushshift for non-moderators — `robots.txt`
`Disallow:` (empty, everything permitted), a documented JSON API, and
`X-RateLimit-Reset` headers that `src/reddit.py` obeys.

> **The uncomfortable half, stated rather than buried.** With a browser
> User-Agent, `reddit.com/r/algotrading/.rss` returns **200 and 54 KB** and
> `x.com/kalshi` returns **200 and 200 KB**. **The constraint is not technical.**
> The content is one GET away and is not taken, because a site's
> machine-readable statement of who may crawl it says nobody may, and a
> User-Agent string is not consent.

### What was built

**240 entities · 946 observations · 39,629 Reddit posts · 12,846 comments
across 538 threads ·
3,165 whole-repo source archives scanned in 50 s · 176 URLs fetched · 13 threads
read in full.**

Verdicts: **12 CONTRADICTION · 11 AGREE_NEGATIVE · 12 advocated-with-an-
incentive-and-corroborated-by-nobody** · 15 single-source · 170 agree-positive.
`ADVOCACY` is kept separate from `CORROBORATION`, so a stale repo somebody
mentioned in passing is a stale repo, not a contradiction.

> **The needle `clob-client` appears in 1,009 of 3,165 whole-repo source
> archives — 32% — and `Polymarket/clob-client` was archived by Polymarket
> itself.** `signal-github` measured v1:v2 = 578:121 from the classifier side;
> this is a direct count over source text. Two instruments, one conclusion.

> **`polymarket/agents` — Polymarket's own framework, 3,760★ — is ARCHIVED and
> 636 days cold, while 693 archived repos still reference it.** It sits in
> `signal-github`'s corpus as a PASS. No computed component in either sibling
> asks "is this archived?", and neither had joined it to anything.

**Every URL was fetched** — two prior sessions here listed dead links.
`thebetterers.com`, promoted with a *disclosed* referral link by a video scoring
**S=10**, no longer resolves. **`api.binance.com` returns HTTP 451, geo-blocked
from this machine** — `crypto/` treats it as a data source and will fail here for
a reason that looks like a network error and is not one. And **64 of 240
entities carry no URL at all**, which is a gap in `youtube-signal`'s extraction,
not a judgement about the tools.

> ### ⚠ Eight hand-researched verdicts existed in a file nobody imports
> `youtube-signal/src/tool_reputation.py` holds eight tool verdicts with their
> sources. **`signal.db`'s `tools` table has no `reputation` column**, so it has
> never run on this machine. Same shape as **K015 = W011**. It also carried a
> correction this table needed: the transcript said *"Creo"*, the product is
> *"Kreo"*, and a search under the wrong name returns `NO_FOOTPRINT`.

### T3 — the paid Discord server, read for the first time

**0 of 174 owner messages state a side and a price**; only 4 state a price at
all. The calls are prose ("I like *surname*", median 40 characters) and the
prices are in 83 screenshots whose **85 CDN URLs all carry an `ex=` signature
that expired 2026-07-31**. Folded n = **34** against ~481 — **14.1× short**.

**UNDERPOWERED is the finding, and it is decidable without ever seeing a price.**
The seller does post losses (6 to 34, plus 22 hedged calls), so H1 fires — and a
5.7:1 self-reported ratio is not a track record. **Do not re-export**; only a
forward record with prices against a pre-declared cost bar changes anything.

*`discord_measure.py` salts pseudonyms per run and does not store the salt. No
handle, id, server name or message text reaches any report.*

### T4 — X, TikTok and Instagram killed, and the expectation TESTED

X: robots `Disallow: /`, API v2 **401** without a paid key, mirrors are the same
act with an extra hop. TikTok: the keyless oEmbed endpoint **returns 200** — and
returns a title, an author and a thumbnail. Instagram: **400** without a Meta
token.

Short-form was **tested on 1,220 videos `youtube-signal` had already gated**:
sub-minute clears the substance gate at **31.6% [19.1, 47.5]** against
**66.3% [61.9, 70.3]** at 10–30 minutes. Non-overlapping — **and non-monotonic**,
30+ minutes falls back to 43.4%. Both ends are junk for different reasons.

---

## Reddit findings that land on threads this repo has already closed (2026-08-04)

All are other people's claims, verified only where stated. Detail and permalinks
in [social-signal/FINDINGS_FROM_READING.md](social-signal/FINDINGS_FROM_READING.md).

**1. A 4,604-window Polymarket 5-minute study reaches two of this repo's own
results independently.** Every price band loses against price+fee (−1.6 to
−6.5pp); momentum continuation inverts monotonically across 346,094 windows; the
Chainlink–Binance lag is **−0.4pp on 5,826 entries** and the profitable version
of that signal was **a measurement artifact**. Two things land here: it
independently names **break-even arming as "the single biggest source of loss"**
— the same mechanism as the 28 July martingale diagnosis, `rearm_above = stop+2`
— and its adverse-selection section supplies **the mechanism the ladder-arbitrage
null lacked**: rest both legs of a split and the leg in demand fills while the
worthless one hangs, so rescuing it means crossing as a taker and paying the fee
you were trying to earn.

**2. Copy trading: the leak may be exit fidelity, not entry latency.**
*"simulating zero lag barely moved the numbers. all the leak was on the exit
side."* **`wallet-copy-study` and `polymarket-tennis-copy` both model the
follower's loss as an entry delay** — `delay_seconds`, follower ROI at
+1s/+10s/+60s, and `follow_through.py`'s entire design. Does not reopen the
NO-GO — it means the verdict may be right for a reason the instrument does not
contain. The same post carries **e-values (always-valid sequential tests)** for
the repeated-peeking problem Holm-Bonferroni does not fix, and every recorder
here is watched daily. **Worth a [GUARDS.md](GUARDS.md) row.**

**3. Kalshi tennis series settle on who ADVANCES** — a walkover pays out with
zero play, from a poster tracking 750+ settlements. `kalshi-inplay-bot` and
`set1_overshoot` trade `KXATPMATCH`/`KXWTAMATCH` and have no model for that
settlement path. Same source: *"closed" is not "settled"* — count only
`finalized`.

**4. A free hourly order-book archive, enumerated rather than trusted.**
`archive.pmxt.dev`, Parquet, CC BY 4.0. **Polymarket v2: 21 Apr – 4 Aug 2026**,
~105 days at 412–534 MB/hour — **"recorded order books are not re-pullable at any
price" is false for that venue.** **Kalshi: 15 May – 11 June 2026 only**, ~~hourly~~,
feed dead — but Kalshi's own ~69-day window reaches back to about 27 May, so
**roughly twelve days of Kalshi books sit there that Kalshi no longer serves**,
and that shrinks daily.

> ⛔ **RETRACTED 2026-08-04 — "hourly" is wrong and it was load-bearing.** A file was
> finally downloaded and opened instead of judged from its filename: **128.7 MB /
> 20,723,041 rows for ONE hour**, 18.9 M of them `orderbook_delta`, microsecond
> stamps, full `yes_bids`/`no_bids` ladders, **642,054 tickers** — including **97
> `KXATPMATCH`/`KXWTAMATCH` tickers and 126,704 tennis rows in that hour alone**.
> Hourly is the **batching**, not the resolution: this is finer than this repo's
> own 0.55 s depth recorder, on the exact series `kalshi-inplay-bot` trades. The
> ~12 unrecoverable days are ~288 files ≈ **37 GB** from a volunteer archive, and
> tennis is 0.6%% of rows — filtering while streaming makes it ~230 MB on disk.
> Not pulled unilaterally; see `social-signal/DECISIONS.md` **D14**. **The window
> shrinks by a day every day.**

**5. "No edge" and "negative edge" are different objects.** Someone rebuilt a
400,000-view YouTube strategy over 16 years and 1,700 trades — **−23% against the
video's +40% on 100 trades** — and *"the exact 100 trades shown in the video do
appear in the backtest… a short lucky stretch inside a much longer downtrend."*
Reversing every signal raised the win rate to 61% and left expectancy at −0.01,
*"because when you reverse a strategy, you aren't reversing the costs."* This
repo's best-supported result is 480 configs, 0 profitable, **S1 −9.36¢ against
random-entry S5 −8.28¢** — and whether that 1.08¢ gap is the cost term decides
which of the two objects it is. The data to check is already here.

**One claim deliberately left unverified:** an r/quant post citing SSRN 6325658
argues Kalshi's passive LPs are **underwriting, not market making** — a claim
about the *return profile*, where every argument this programme has made about
maker-only quoting has been about *costs and privileges*. `papers.ssrn.com`
returns **403 behind a Cloudflare interstitial** and this project does not solve
bot challenges.

### Reading found what scoring could not, again — five read, five defects

The proxy rubric scores a **satire post** S=7 ABSORB, because S1 (+3, "names the
cost side") fires on *"I haven't added fees or slippage yet"* — **it cannot tell
naming a cost from accounting for one**. A post **warning about** strategy
sellers scores **H = −6** on the language it quotes in order to condemn. And on
the best document in the corpus, **H1 — show a failure without pivoting to a
sale — does not fire on a post that is nothing but failures.**

**Nothing was patched.** Tuning patterns until they fire on five examples you
happened to read is the overfitting this programme exists to catch, and it would
swap a known-bad instrument for an unknown one. **No verdict in the reputation
table rests on the proxy.**

> **One self-inflicted failure, recorded because it cost real work.** An analysis
> pass of mine held a write lock on `social.db` while the Reddit collector was
> running; SQLite's default busy timeout is **5 seconds** and the collector died
> with `database is locked` after 45 minutes. The 39,629 posts already written
> survived; the tool probe did not. Fixed at the root — 120-second busy timeout,
> WAL, and phase flags so a resume does not re-pull what is already there.

---

## CLAUDE.md now holds the standing rules (2026-08-04)

**`CLAUDE.md` is auto-loaded into every Claude Code session in this repo.** The
rules that previously had to be pasted by hand at the start of each session now
live there permanently. If you are a session reading this: you have already been
given them.

Nine sections: how to talk to the user (the mandatory end-of-message block),
autonomous work mode as the default, doing it yourself vs asking him, how he
communicates, coordination between parallel sessions, evidence standards, the
four repos, machines, and repo mechanics.

The three that change session behaviour most:

- **Every message ends with a plain-English block** — what I did / what it means
  / what I need / next. Under 150 words, no jargon, no acronyms undefined.
- **Autonomy is the default.** Never ask whether to inspect a file, run tests,
  fix a clear bug, update docs, commit, or push. Take the conservative option,
  log it in your folder's `DECISIONS.md`, and keep going. **Do not ask
  permission to update this file — just update it.**
- **Verify third-party web UIs before writing click-by-click instructions.**
  Training data carries outdated Google Cloud / GitHub / Supabase screenshots
  and has already sent the user to menus that no longer exist.

### Two stale facts fixed while writing it

- **`CLAUDE.md` gave a `C:\Users\gianf\` path** for the youtube-signal knowledge
  rebuild. That is the **laptop**. Verified: the path does not exist on the
  desktop, so the documented command has been broken since the machine became
  primary. Corrected to the desktop venv and both halves confirmed to resolve.
- **`LEDGER.md`'s "~41 corrections"** prose was stale by four against its own
  Tally table (**45**). Corrected, and `CLAUDE.md` §6 now points at the Tally as
  the source of truth rather than freezing a number that goes stale — which it
  has now done twice.

> The brief for this task said "~47 corrections". The measured figure is **45**
> retracted (plus 6 broken). Flagged rather than silently adopted, since §6 is
> the section about not repeating numbers from memory.

**Added after the section above was written:** comment collection was resumed
and finished clean — 400 threads, 401 calls, **0 errors, one HTTP 422**, 21.5
minutes — doubling the comment corpus. Two entities turned CONTRADICTION on the
new comments and reading them split the pair cleanly. **`predictionhunt.com` is
real**: 8 scam-flavoured windows out of 17, specific and consistent, on a site
that still returns HTTP 200 — recorded as users' allegations, not adjudicated
fact, and it is the one finding here that could stop money being lost this week.
**MetaMask was a false positive of a new kind**: its three windows read *"steal
**from the linked** metamask account"* and *"the remaining $1k usdt **in my**
MetaMask to get stolen"* — the accusation is against a third-party site and the
wallet is the **victim**. `victim_not_perpetrator()` now suppresses that shape
and records it as `NAMED_AS_VICTIM` rather than dropping it. MetaMask →
AGREE_POSITIVE; predictionhunt.com survived. **Six lexicon defects are now
documented and every one was found by reading — two of them by reading the
survivors of the previous fix.** That is why no precision number is claimed.

### ⚠ Cross-session correction: `trust_me_bro` moved my verdicts (2026-08-04)

`social-signal`'s reputation table treated `signal-github`'s **`trust_me_bro`**
flag as evidence **against** a tool, built on that project's n=822 reading that
it was *uncorrelated* with substance (rho +0.029, p 0.41).

**That session has since overturned its own number at n=2,717: rho +0.064,
p 0.0009 — weakly POSITIVE**, flagged repos median `s_adj` +0.19 against
−0.20.

**I trust theirs**, on the same instrument at 3.3× the sample and with an
explicable direction — making a results claim at all requires having built
something. So the flag never belonged in a set called AGAINST. It fires on *"a
results claim with <10 commits and no artifact"*, which is an **honesty** signal,
and the ported rubric is explicit that S and H are never averaged: **discount the
results, not the tooling.**

`TRUST_ME_BRO` now discounts a tool's **claims** without condemning the tool.
**AGREE_NEGATIVE 11 → 8**: `OpenPoly`, `polymarket-hft-engine`,
`prediction-market-arbitrage-bot`, `lmsr-pricing-engine` and `QuantConnect` were
negative on that flag alone and are not any more.
`polymarket-market-maker` stayed negative — its negative is an archived v1
CLOB client, independent of the flag.

Recorded as `social-signal/DECISIONS.md` **D12**.

---

## bot-hunt â€” market-to-strategy pipeline, extractors first (2026-08-04)

`bot-hunt/` Â· `PRIOR_ART.md`, `SHORTLIST.md`, `DATA.md`, `PREREGISTRATION.md`,
`DECISIONS.md`, `HANDOFF.md` and `src/` committed Â· `data/`, `reports/`
gitignored Â· full write-up in [bot-hunt/HANDOFF.md](bot-hunt/HANDOFF.md).

**Cost $0.00. Every call public, unauthenticated, read-only. No order endpoint
exists in that folder's code by construction.**

### âš  `market-selection/` already did Step 2, and nothing in this file said so

A complete market-selection pass dated **2026-08-02** exists in
[market-selection/](market-selection/) â€” the full 24 h exchange-wide tape
(**8,867,978 trades, 2,205 series**), a depth recorder, a pre-registered kill
gate, and four ranked families. **It has no row in the thread tables above**,
which is why a later brief was written as though no market selection had ever
been done. It is now referenced; it should get a thread row too.

### Its #1 entry is dead, on an axis it never measured

South American / Mexican soccer was ranked first on **40â€“101 settlements per
week**. That is a *rate*. Measured today, the **retrievable settled events** are:

| series | events | vs LEDGER K014's 481 |
|---|---|---|
| KXMLSGAME | 53 | 0.11Ã— |
| KXARGPREMDIVGAME | 42 | 0.09Ã— |
| KXLIGAMXGAME | 28 | 0.06Ã— |
| KXDIMAYORGAME | 21 | 0.04Ã— |
| KXCOPADOBRASILGAME | 8 | 0.02Ã— |
| **all five** | **152** | **0.32Ã—** (and 0.07Ã— the 2.4Â¢ cost bar) |

Its counterparty and cost figures reproduce live and are fine. There is simply
no sample. **Same shape as its own K005 retraction â€” "celebrating the wrong
axis" â€” on the dimension its own `killed.md` calls KILL 5.** The irony is exact:
this is the one family whose sharp reference price *is* backfillable (14 years
of free Pinnacle closes) and the Kalshi side has 152 matches.

### ðŸ”‘ Pinnacle's guest API is free, and 3 of 3,195 repos use it

`guest.api.arcadia.pinnacle.com` â€” verified by fetching, unauthenticated, no
account: **27,582** priced soccer markets, **3,728** tennis (including period-1
handicaps), **1,920** baseball, **643 esports**, each carrying `maxRiskStake`
limits. Against **129** repos in the `signal-github` corpus that use the *keyed*
`the-odds-api` and **82** that merely name Pinnacle.

This is the fair-value input for the only strategy in any corpus attached to
this repo with a **public wallet and a reconciled four-line P&L** â€” Polymarket
esports, passive-only, de-vig the sharp book and quote it: **+$8,293 arbitrage,
âˆ’$3,184 unhedged residual, âˆ’$134 cancellations, +$4,973 net** over 3,858 fills
and $96k volume. **Its author switched it off** as the win rate decayed
50.2 â†’ 48.3 â†’ 43.4% monthly.

> **The most useful single number found: adverse selection cost that author
> 38% of gross.** That is the term appearing in no fee model anywhere in this
> repo. It reconciles the standing tension â€” `signal-github` says maker-only
> quoting wins on fees, a 20-year professional says be a taker, **both are
> right, and 38% is the size of the missing term.** It is also the same
> mechanism S008/S009 measured as fatal on tennis without sizing it.

> âš  **T014 is NOT retracted.** tennis-data.co.uk really did stop carrying
> Pinnacle in 2026 (coverage 5.1%). That is the *historical CSV*. **Live**
> Pinnacle is a different object and is free â€” so a route believed closed is
> open *going forward only*. It cannot be backfilled for tennis.

### Kalshi retention is a fixed calendar boundary, not a rolling window

Four independent queries â€” `status=settled`, `min_close_ts` at âˆ’365 days, no
status filter, and a window placed entirely before the boundary â€” return the
same earliest `close_time`, and **13 of 18 unrelated families share the identical
date 2026-05-25**. The **market listing** and the **trade tape** have the *same*
boundary, and the listing binds because it supplies the result label.

> âš  **`market-selection/WHAT_IS_LEFT.md` calls the tape "THE DECAYING ITEM"** â€”
> 69 days, rolling one day per day, overlap gone by **2026-08-19**. It bisected
> the boundary to **2026-05-25** on 08-02; this session bisects it to
> **2026-05-25** on 08-04, so the window **grew** 69 â†’ 71 days. **Two points is
> not enough to overturn the claim â€” it is enough to stop treating the deadline
> as established. Re-bisect before acting on it.**

### Free-source regressions and one trap, all fetch-verified today

- âš  **`site.api.espn.com` scoreboard: 403 on 7 of 7 leagues.**
  `market-selection` used that feed on **08-02** to find 3,699 priced DraftKings
  props, and **that finding killed its own #1 mechanism** and established
  `KXMLBRFI`'s no-free-reference property. The `sports.core.api.espn.com` v2
  path still returns 200. **Re-establish it or withdraw the claim.**
- **Esports domain data confirmed dead**: Oracle's Elixir 404, HLTV 403,
  vlr.gg 402, PandaScore 403, GRID 404. Liquipedia (475 KB) and bo3.gg alive.
- **The football-data trap reproduced exactly**, two independent ways â€”
  `COL.csv` â‰¡ `POL.csv` (sha `b9d1c59553b70628`, its own League column reads
  **Ekstraklasa**) and `KOR.csv` â‰¡ `NOR.csv` (`aa649e866b03d2ea`,
  **Eliteserien**). HTTP 200, no error. **Belongs in GUARDS.md as a 13th guard:
  a 200 is not a correct file â€” hash it and check its own content column.**

### Engine validated on 5 controls; the leak canary reproduced T010/T011

`bot-hunt/src/engine.py` imports `common/kalshi_fees.py` and never
reimplements it; it deliberately does **not** adopt `evan-kolberg`'s fill model
(makers pay 0 in its instrument metadata, 0.07 in its fee model, same repo).
`validate_engine.py` passes a martingale check on the generator, a null control,
a 5 pp positive control, a 1 pp sensitivity floor, and a deliberate mid-price
leak that must light up (+0.32Â¢ â€” half the quoted spread, exactly what T008
recovered by marking at the mid).

**Independent reproduction of T010/T011 on a sport that work never touched:** on
Kalshi esports at a **âˆ’0h** anchor, **23.62% of quotes are extreme and 100% of
them are correct**; at **âˆ’60 min** and **âˆ’6 h**, **0% extreme**.

### Step 6 ran and is NOT reportable â€” which is the gate working

271 events (of ~2,867 targeted; the candle pull was still running), 92 cells,
**0 survive BH-FDR with a CI above zero**, selection canary correctly
**UNTESTABLE** (MDE 5.95pp > 2.0pp), and the **negative-control gate UNTESTABLE**
because the control family had no candle panel yet. **No number from that run is
a finding, and the gate says so itself.**

### Three corrections from this session, recorded not buried

1. **A false kill on the best lead, by my own recorder.** `tag_slug=esports`
   ordered by 24 h volume returns mostly `acceptingOrders=false` events (96 of
   156) and read **0% two-sided**. Per-game slugs the same minute: `dota-2`
   **51 of 60 two-sided**, top market **$51,029/24 h at a 1.0Â¢ spread**.
   **Third occurrence of this shape in this repo** â€” `market-selection`'s
   stale-ticker bug produced **19 wrong kills**, and `killed.md` opens with its
   own correction of the same kind. **A dimension-A probe that samples the wrong
   markets fails silently and always toward a kill.**
2. **My validation failed on a bad pass condition, not a bad engine** â€” a fixed
   0.25Â¢ tolerance against a bootstrap SE of 0.66Â¢. Replaced with a statistical
   condition.
3. **My negative-control gate read ABSENT as CLEAN** â€” a control with no data
   returned 0 survivors and printed "reportable". Fixed to three-valued.

### Recording started 2026-08-04 21:27 UTC and must not be killed

`bot-hunt/src/record.py`, 10-minute cycles. Pinnacle, the Kalshi book and the
Polymarket touch are **all live-only and none can be backfilled**. 18 Kalshi
series (re-listed every cycle), 8 Polymarket game slugs, 6 Pinnacle sports.
Two known-dead weather families ride along as a **negative control on the
instrument itself** â€” they read 42%/67% two-sided against 100% elsewhere.

**Single next action:** pull `KXMLBGAME` candles so the control gate can be
decided, then re-run `src/run_grid.py`. Nothing from the test family is
reportable until it passes.

---

## extractor-upgrade — the rubric graded against known answers (2026-08-04)

`extractor-upgrade/` · `FINDINGS_T1.md`, `FINDINGS_T2.md`, `FINDINGS_T3.md`,
`HOW_TO_CALL.md`, `PAID_OPTIONS.md`, `DECISIONS.md`, `HANDOFF.md` and `src/`
committed · `data/`, `reports/`, `frames/` gitignored · full write-up in
[extractor-upgrade/HANDOFF.md](extractor-upgrade/HANDOFF.md).

**Cost $0.00.** Every sibling database opened `mode=ro` in the URI, so this
project cannot have caused a third lock-contention failure.

### The rubric had never been tested. It has now, on 24 cases with known answers

Every label is fixed **outside** the rubric — arithmetic on the source's own
numbers, a live API check, a fact this repo already primary-sourced, or an
internal contradiction. 17 of 24 are **bands** rather than points, each tabled
with what fixes its bound, because encoding taste as ground truth makes a
confusion matrix an opinion poll.

| instrument | exact | false RECOMMEND | stale caught |
|---|---|---|---|
| **the pipeline as it actually ran** | **17/23 = 74%** | 2 | **0 of 2** |
| **the mechanical lexicon** | **10/24 = 42%** | 6 | 0 of 2 |
| **rubric v2 (the fix)** | 13/24 = 54% | 5 | **2 of 2** |

**The model read is the instrument; the lexicon is a ranker that should never
have been allowed to emit a verdict.** That is now a number rather than an
opinion, and it matters to `social-signal`, whose reputation table joins both.

### Six defects, measured not asserted

1. **Staleness is invisible BY CONSTRUCTION** — nothing in either instrument
   asks whether the thing being taught still exists. A Polymarket CLOB v1
   tutorial is the pipeline's `BUILD_AND_RECOMMEND`. Verified live: both v1
   clients archived, `py-sdk` pushed today. **The trap: `pip install
   py-clob-client` STILL WORKS** — PyPI serves 0.34.6 while the repo is
   archived, so nothing errors and nothing warns.
2. **Components fire on spans that say the opposite.** S1 (+3, top-weighted)
   fires on *"I haven't added fees or slippage yet"*. A post warning ABOUT
   strategy sellers scored **H = −6** on the language it quotes to condemn.
3. **Two components are unreachable and three are intercepts — and the two
   implementations disagree about which.** `H1b` has a weight and **no
   detector**, so it is unreachable in 4,432 posts. `H9`/`H10` never fire in 38
   reads. `S5` 95%, `S4` 92%, `H4` 87% — which is most of why 38 reads produced
   **zero SKIPs**. *The same component name means different things in the two
   corpora, so a score is not comparable across them.*
4. **The prompt does not declare 6 of the 21 components the code scores.**
   `B1`–`B5` and `H10` appear nowhere in the `RUBRIC` string and the schema has
   no `b_components` key — yet `validate_response` and `totals` both read one.
5. **No verdict in the database can be recomputed from the database.**
   `verdict()` consumes `teaching_quality`, which is never persisted.
6. The brief's named failure (Part Time Larry, S=3 H=9 → SKIP) **is already
   fixed** by the B axis added 08-03. Kept as a regression case.

v2 adds a currency **gate** rebuilt from the GitHub and PyPI APIs on every run,
plus negation / condemnation / third-party / debunk guards. Over **5,567
documents neither rubric was tuned on, 10.7% change action** — a targeted fix,
not a rewrite. **Each guard trades one error for another: false RECOMMEND went
6 → 5, not 6 → 0.** The ceiling is stated: every remaining failure has the same
shape — the words look honest and the dishonesty is in the relationship between
two numbers, or in a denominator that is *absent* and therefore unmatchable.

> **One of the brief's five named cases is not in this repo.** No transcript or
> markdown anywhere contains "23.53". Recorded as missing and two verifiable
> cases substituted, rather than writing an unverifiable label into a test set
> whose whole premise is verifiable labels.

### ⛔ Vision: built, validated, and every route to a YouTube frame is a `Disallow` line

`youtube.com/robots.txt` disallows `/get_video`, `/get_video_info`,
`/file_download`, `/youtubei/` and `/api/`; `i.ytimg.com/robots.txt` disallows
`/sb/` — the storyboard path, which was the cheap route. yt-dlp calls
`/youtubei/v1/`. **There is no fourth route.**

> ### ⚠ It lands on `youtube-signal`, not just on this task
> **`youtube-transcript-api` fetches from `www.youtube.com/youtubei/v1/player`**
> (`_settings.py:2`) — the same `Disallow` line, and `/api/` and
> `/timedtext_video` are disallowed by name too. `social-signal` killed
> Reddit's own JSON API, X, TikTok and Instagram on exactly this standard and
> wrote *"a User-Agent string is not consent"*. **The project has been on one
> side of a line it drew itself on the other side of.**
>
> **Nothing was stopped, changed or deleted.** It is the user's call and the
> options are not equivalent: transcripts are the basis of 38 reads, 484 claims
> and a 190,000-character knowledge file.

So `src/frames.py` was built, validated end to end against a synthetic video
with known content at known seconds (5/5), and points at **local files**. It
renders `SPOKEN: I made 40 percent` beside `SCREEN: Total P/L −18.4%` — the
mismatch the task is about.

**Would vision have changed anything?** 22 of 38 videos flagged
`visual_dependent`; **4.9% of runtime** sits inside a `watch_segment`; **8 of
484 claims** say their evidence was on screen; **0 of 24 test-set labels needed
a frame**. *The bias in that zero runs against vision and is stated*: the test
set only admits cases whose answer is independently verifiable, and a claim
settled only by looking at a screen is exactly the case it could not include.

### Four sources are open and unused, one refuses AI by name

Probed three ways — robots, then live, then **does the content contain what it
claims**, which is the check prior sessions skipped.

**Open and permitted:** Hacker News's official Firebase API, any Discourse
forum's `/latest.json`, **PodcastIndex keyless** (12,440 bytes, no header), and
arctic-shift re-verified. **Closed:** Apple Podcasts (`Disallow: /search*`) and
**Lobsters**, whose `robots.txt` carries `Content-Signal: ai-input=no,
ai-train=no`. Its JSON returns 200 and 12,772 bytes of good data. It was not
taken.

> **396 of 1,197 video descriptions already on disk carry ≥3 chapter markers —
> 33.1%.** YouTube chapters live in the description and nothing reads them. An
> author-written table of contents is a strictly better `watch_segment` seed
> than a phrase list, and it needs no network call, no dependency and nobody's
> permission. **Highest value-to-work item found.**

### One command, offline, for any session mid-investigation

`extractor-upgrade/src/ask.py` queries all four corpora at once — 484 claims,
3,165 scored repos, 4,432 scored posts, 240 joined entities — read-only, no
network, seconds. `--tested` · `--backtester` · `--datasources` · `--tool`.
See [extractor-upgrade/HOW_TO_CALL.md](extractor-upgrade/HOW_TO_CALL.md).

> ⚠ **Both SKILL.md files quote numbers their own projects have retracted.**
> `github-signal/SKILL.md` still says `trust_me_bro` is *uncorrelated* with
> substance (rho +0.03, p 0.41); that project overturned it at n=2,717 —
> **rho +0.064, p 0.0009, weakly POSITIVE**. It also quotes the stars
> correlation at n=2,260 against full coverage n=3,165, and
> `youtube-signal/SKILL.md` gives the **laptop** path as project root.
> The `K015 = W011` shape again. Not edited — they are sibling files.

### Task 5 was already built, and the axis added to it found nothing new

`social-signal`'s cross-platform table exists (240 entities, 946 observations,
11 CONTRADICTIONs), so it was not rebuilt. A dated, re-runnable **liveness**
verdict was joined onto all 176 entities carrying a repo or URL: **148 ALIVE,
and the only two provably gone — `thebetterers.com` (no DNS) and
`polymarket/agents` (archived, 637 days) — were already in the table by hand.**
A live currency check surfaces nothing the reading did not. Its value is that
it is now automated and dated, so it catches what dies next.

### Two refinements of sibling findings, and neither is a contradiction

- **`bot-hunt` is right about Pinnacle.** `/0.1/sports` returns 401 with no
  header and 403 with the public guest key, but **`/0.1/sports/29/matchups`
  returns 200 and 1.7 MB with no header at all.** The index is gated; the
  endpoint that matters is not. A session probing `/sports` first would wrongly
  conclude the API is dead.
- **`oracleselixir.com` returns HTTP 200** (3,919 bytes, a shell) against a
  recorded 404. Different URLs, so not a contradiction — check the data path
  rather than either line.

### Five of my own errors, recorded because the shape repeats

Three false kills and one false refusal, all from probes sampling the wrong
thing: counting every 404 as death (killed three live API hosts); patching that
with a path-segment heuristic that immediately killed a versioned API base; a
robots parser that **ignored `Allow:`** and called Hacker News's explicitly
permitted API forbidden; and a currency alias table that matched the ordinary
word `agents`. Plus an ffmpeg call that returned **exit code 0 and a blank
frame**, caught by looking at the image.

**Three candidates for [GUARDS.md](GUARDS.md):** a robots check without `Allow`
is not a robots check · a 404 never establishes death · a zero exit code is not
a rendered artifact.

### THIRD INDEX CROSS-CONTAMINATION, and it happened to this session

`CLAUDE.md` section 5 says *"Stage explicit paths. NEVER `git add -A`. Two
sessions have already cross-contaminated commits that way."* This session staged
explicit paths only, and it still happened.

**Commit `fbe0f62` is titled `bot-hunt: AMENDMENT A1` and contains four
`extractor-upgrade` files** — `FINDINGS_T3.md`, `HANDOFF.md`, `PAID_OPTIONS.md`
and `src/find_sources.py`. A concurrent `bot-hunt` session ran `git commit`
while those files sat in the index, and **git's index is shared by every
session in the working tree.** Explicit staging protects you from *your own*
next command; it does not protect you from somebody else's.

**Not rewritten.** The other session is running now and the content is correct;
only the attribution is wrong. Recorded here so the history reads honestly.

> **The rule that would actually work** is not about `-A` at all: **stage and
> commit in the same command**, so nothing of yours is ever resident in the
> shared index while another session might commit. `git add <paths> && git
> commit` as one shell invocation, never as two turns. Worth a
> [GUARDS.md](GUARDS.md) row and worth amending section 5 to say so, because the
> rule as written has now failed three times.

**Single next action:** read the chapter markers out of the 396 descriptions
already on disk. Free, offline, needs nobody's permission.

### bot-hunt â€” Step 6 complete (2026-08-05)

Full write-up: [bot-hunt/RESULTS.md](bot-hunt/RESULTS.md).

**0 of 260 cells survive BH-FDR with a CI above zero on the test family
(esports: CS2 + LoL + Valorant, 2,779 events); 0 of 148 on the MLB control.
Every surviving cell is significantly NEGATIVE. The holdout is untouched â€”
nothing qualified to face it.** Exactly what the pre-registration predicted, for
the reasons it gave.

#### The leak gate voided my own anchor, and the fix is AMENDMENT A1

The pre-registered âˆ’60 min anchor **VOIDed**: 13.96% of quotes extreme and
**99.7% of those correct** â€” the T010/T011 signature, on n = 2,779. My modelling
error, not a market fact: **`close_time` is when the market SETTLES, not when
the match starts**, so âˆ’60 min was usually mid-match. `occurrence_datetime` is
no help â€” LEDGER **T010** already retracted a headline over it (*"at/after match
end"*).

Anchor re-found by measurement per T011. **The rule is MONOTONE cleanliness, not
first-clean** â€” v1 of my sweep took the smallest lead labelled clean, and
`KXVALORANTGAME` reads clean at 30 min on **98.5%** (just under a hard 99%
cutoff) then VOID at 60/120/180 min. `KXLOLGAME` is the extreme case: still
**7.76% extreme and 100% correct at âˆ’6 h**, clean only at **âˆ’24 h**.

Primary is now a uniform **âˆ’24 h**; per-series monotone-clean anchors are the
sensitivity arm, in the same BH denominator. **Amendment committed before the
re-run, decided on the leak diagnostic alone** â€” no return number at those
anchors had been seen.

#### âš  The finding that outlives the null: dimension C is measured at a moment you cannot trade

Every cost bar in [bot-hunt/SHORTLIST.md](bot-hunt/SHORTLIST.md) â€” and in
`market-selection` before it â€” comes from probing **the touch, on the busiest
markets**. Measured instead over **all** settled markets by lead time:

| series | median 15 min â†’ âˆ’24 h | **p90 15 min â†’ âˆ’24 h** | **mean 15 min â†’ âˆ’24 h** |
|---|---|---|---|
| KXCS2GAME | 3.0Â¢ â†’ 4.0Â¢ | **12Â¢ â†’ 69Â¢** | **6.44Â¢ â†’ 18.33Â¢** |
| KXLOLGAME | 1.0Â¢ â†’ 3.0Â¢ | **4Â¢ â†’ 62Â¢** | **3.19Â¢ â†’ 12.46Â¢** |
| KXVALORANTGAME | 2.0Â¢ â†’ 3.0Â¢ | 7Â¢ â†’ 10Â¢ | 3.73Â¢ â†’ 6.16Â¢ |
| **KXMLBGAME** | **1.0Â¢ â†’ 1.0Â¢** | **1Â¢ â†’ 1Â¢** | **1.12Â¢ â†’ 1.08Â¢** |

**The median barely moves; the tail explodes.** A strategy that must trade every
qualifying event pays the **mean**, not the median â€” which is exactly why the
naive benchmarks came back at **âˆ’6.8Â¢ (random side)** and **âˆ’8.7Â¢ (buy the kept
side)** against a "2.2Â¢ cost bar".

> **`market-selection` reported 1.0Â¢ median and 21,236 at the touch on
> KXCS2GAME. I measure 3.0Â¢ even at 15 minutes.** Both are right and they
> measure different things â€” its stated convention was *"each family's BEST
> case"*, mine is the population of settled markets. **Neither file was wrong,
> and nothing said the two were not comparable.** The strategy pays the
> population number, so esports' real pre-match cost is **3â€“6Ã— the figure it was
> ranked on**.

**MLB moneyline is 1.0Â¢ at every lead from 15 minutes to 24 hours, p90
included** â€” the only family here whose quoted cost a pre-match strategy could
rely on.

#### The brief's premise is refuted: Kalshi L2 history exists, and covers esports

Following the sibling's retraction (`9ba0682`), I opened one archive file
(`2026-05-30T17`, 19,310,089 rows): **esports 498,434 rows / 74 tickers
(2.58%)**, tennis 2,092,158 (10.8%), MLB 70,629, **South American soccer ZERO** â€”
a third independent confirmation the prior #1 entry has no history. 550 files,
2026-05-19T06 â†’ 2026-06-11T03.

> âš  **Correction for the sibling's estimate.** Their disk projection uses tennis
> â‰ˆ 0.6% of rows, measured on `2026-05-17T02` â€” an overnight hour. At
> `2026-05-30T17` tennis is **10.8%**, an **18Ã—** difference. ~230 MB is low;
> the window is nearer **4 GB** for tennis and ~1 GB for esports. Not acted on
> unilaterally â€” it is their pull.

**H10 (passive quoting) is now runnable and is the most informative untested
cell.** The corpus says nothing adoptable exists: of 3,201 repo archives,
**queue position fires on 5.2% and trade-through on 3.0%** â€” the two signals
that decide whether a maker backtest is honest are the two rarest.

#### One more esports datum, and it cuts both ways

The largest esports record in any corpus (public wallet, 211 days, $65M closed
volume, 5,187 resolved, ~$1M realised): **League of Legends 1,819 positions at a
49.0% win rate for +$1.47M**, while **"Other" 1,705 positions at a 69.8% win
rate loses $506K**. The value shape and the leaderboard-farming shape in one
wallet. **ROI 1.6% on closed volume, profit factor 1.09** â€” thin, against a
6â€“18Â¢ mean pre-match spread. Third-party analysis of a wallet selected *because*
it ranks #128, so **W015** applies: a lead, not a result.

### ✅ Kalshi window RESCUED — 610 tennis matches at tick resolution (2026-08-04)

Acted on the D14 retraction rather than leaving it as a question.
`social-signal/src/pull_kalshi_archive.py`, 61 minutes, **$0.00**.

| | |
|---|---|
| coverage | **15–27 May 2026, 312 of 312 hours, ZERO gaps** |
| rows kept | **200,626,400** |
| snapshots | 171,644 — **92% carry a full price/size ladder** |
| deltas | 200,454,756 `(price, delta, side)` |
| tickers | 1,220 — 626 `KXATPMATCH` + 594 `KXWTAMATCH`, **0 off-prefix** |
| **distinct matches** | **610** |
| streamed / kept | 34.5 GB in → **1.21 GB on disk** (filtered in flight, raw discarded) |

**Why this window and not another:** Kalshi's API is a ~69-day window and closed
markets 404. On 4 Aug that reaches back to about **27 May**, so everything here
is already unobtainable from the venue, and the archive's own Kalshi feed is dead
at 11 June so it never grows back. **It shrank by a day for every day it was left.**

**What it is NOT.** It does **not** reopen the set-1 overshoot thread, which
closed on arithmetic — *"n≈3,970 needed for a 2¢ edge; more slicing has
negative EV."* Finer depth does not move a cost bar. And **610 matches of order
book is not 610 settled tests of a strategy**: it sits above the ~481-settlement
bar this programme uses for copy-trading questions, but whether it clears any
bar depends entirely on the question asked of it.

**Two traps recorded in `social-signal/DECISIONS.md` D14–D16**, both of which
cost real time here:

1. **The parquet files are on a different host** (`r2kalshi.pmxt.dev`), not under
   the listing path. Guessing `/data/Kalshi/<name>` returns the single-page-app
   shell with **HTTP 200**. A 200 is not evidence you fetched what you asked for
   — it took an 18,990-byte "parquet file" with no magic bytes to notice.
2. **A 26-row sample said the opposite of the truth.** Every ladder in those 26
   `orderbook_snapshot` rows was empty and the conclusion drafted was *"the book
   cannot be anchored"*, which would have written off the dataset. A census over
   all 312 files found **92% populated**. Same failure as the 100-trade YouTube
   backtest, the n=105 stars correlation and the n=822 `trust_me_bro` reading.

---

## extractor-upgrade, session 2 — I was wrong about frames, and the GitHub ranking recommends dead code (2026-08-05)

Full write-up: [extractor-upgrade/HANDOFF.md](extractor-upgrade/HANDOFF.md).
Cost $0.00.

### ⛔ RETRACTION, same day: "frame acquisition from YouTube is closed" was too strong

**Three full-resolution video frames per video are permitted and I missed them.**

```
https://i.ytimg.com/vi/<id>/maxres1.jpg   1280x720, ~110 KB
https://i.ytimg.com/vi/<id>/maxres2.jpg   ~25 / 50 / 75% of runtime
https://i.ytimg.com/vi/<id>/maxres3.jpg   AUTO-EXTRACTED VIDEO FRAMES
```

`i.ytimg.com/robots.txt` disallows **`/sb/` only**. I read that line, correctly
concluded storyboards were forbidden, and **did not then ask what else lived on
that host.** Verified: `/sb/` → **403**, `/vi/maxres1.jpg` → **200 and 114,833
bytes**. Same shape as the false kills already recorded — a probe that samples
the wrong thing fails toward the conservative answer.

**What survives:** the media *stream* is forbidden at every hop. All three
`googlevideo.com` hosts checked return `User-agent: * / Disallow: /`, so a
third-party downloader site is **the same act with one extra hop** — it fetches
from `googlevideo.com` on your behalf.

### The measurement vision was supposed to make, made

38 videos · 114 frames · 14.5 MB · **6 sheets read in full**, chosen as the ones
whose stored verdict a screen could plausibly overturn. A loaded sample, so the
rate below is not a corpus rate. **6 of 6 produced something a transcript could
not.** Detail: `reports/T2b_screen_evidence.md`.

> ### The one that changes a verdict
> **`8u6jy8v56ww`** — the 96.83%-win-rate Polymarket BTC study, stored as
> **ABSORB_AND_RECOMMEND** on S=10 H=6. It projects a $20,000 bankroll at $100 a
> trade producing **over $300,000 monthly**.
>
> **The account visible on screen holds $1.79.** `Portfolio $1.79 · Cash $1.79 ·
> Amount $0`, no position open. The same frame shows **Up 37¢ / Down 67¢ = 104¢**
> — a 4% two-sided spread on a market whose break-even the video itself states as
> 51.02%, so the screen also quantifies the cost side the projection omits.
>
> **That verdict is wrong and vision is why.** It is the first verdict in this
> programme changed by looking at a screen.

The other five: a **paid course sales page with "Coin Bureau viewers get an
exclusive 10% discount"** terminating a video whose stored verdict is ABSORB
(`YknxNkTgNWk`) — plus a results card on screen, *"TBO Trend $25 → $321
(+1,182%, 75% win rate)"*, in **no recorded claim**, for the exact entity
`social-signal` already flags as CONTRADICTION and whose site now returns **no
DNS**; unattributed **Bloomberg Brief broadcast footage** and an enabled
**"Front-Run Institutional"** toggle in the scam case (`PeutA_HKxew`), neither
ever spoken; a wallet table where the **100.0% win-rate row wagered $752.16 and
returned $1.99** while a 42.9% row returned +45.4% ROI (`yxfTHAGfaDc`); the
archived v1 client's own method names, `client.get_order_book` and
`client.cancel(order_id=…)`, confirming the staleness gate from the code rather
than the date (`lVqF8oLzVAU`); and a **B=10 build score on a video whose own
on-screen overlay reads "NO CODE"** (`86AlV6174KI`, logged as TENSION — three
samples cannot prove absence).

**Frames are ephemeral, per instruction:** 159 images / 14.8 MB deleted after
extraction. 114 evidence rows kept, screen-derived fields stored apart from
transcript-derived ones.

### signal-github: 27% of the corpus is discontinued by its own owner

`signal-github/src/currency.py` — a new **gate**, not a component.

| | |
|---|---|
| scored repos | 2,732 |
| **discontinued by their own owner** | **739 = 27.0%** |
| …importing the archived Polymarket v1 client | 711 |
| …archived outright by the owner | 28 |
| **in the top 25 by `s_adj`** | **6 = 24.0%** |
| **in the top 100** | **35 = 35.0%** |

**The share is worse at the top than in the corpus.** `is_archived`, `pushed_at`
and `pm_client` were all already computed and **none of them was read by the
ranking**. And `pip install py-clob-client` still succeeds — PyPI serves 0.34.6
while the repo is archived — so nothing warns a reader until the order endpoint.

**Gating costs nothing measurable.** Against the external ground truth this
project already validated `s_adj` against — repos that provably model Kalshi's
*maker* fee correctly — the top 100 goes **6 → 9** and the top 200 **10 → 17**,
with **zero fee-correct repos lost.** Removing dead weight promotes the live
repos underneath it.

**And the ranking has now been graded, which had never been done.** Labels fixed
outside the instrument: five repos read in full, plus **739 by the owner's own
statement**, which is not an inference. On the five hand-read cases the ranking
agrees on **1 of 5** — it would RECOMMEND `hcharper/polyBot-Weather` (rank 3,
**one commit**, a README claiming *"Guaranteed profit"*, v1 client) and merely
ABSORB `aulekator` (557 stars, 4 commits, `fee_rate_bps=0` in the live path).
Five is not a precision estimate; it is five demonstrations that **`s_adj` alone
must never be read as a recommendation.**
`extractor-upgrade/reports/T6_github_validation.md`.

### Both SKILL files corrected — they quoted numbers their own projects retracted

- `github-signal`: `trust_me_bro` *"uncorrelated with substance, rho +0.03,
  p 0.41"* was n=822 and is **withdrawn**. At n=2,717 it is **rho +0.064,
  p 0.0009 — weakly POSITIVE**; flagged repos score *higher*. It is an honesty
  signal: discount the claims, not the tooling. Stars corrected to n=3,165.
- `youtube-signal`: gave the **laptop** path as project root, so its documented
  commands have been broken since the machine switch. Now also records that
  three permitted frames per video exist.

### ✅ User decision recorded: the transcript tool keeps running

`youtube-transcript-api` fetches from `www.youtube.com/youtubei/v1/player`, which
is a `Disallow` line. **The user's decision is to keep using it**, and it is
recorded here rather than left unexamined. Nothing was stopped or deleted.

**Single next action, unchanged:** read the chapter markers out of the 396
descriptions already on disk. Free, offline, needs nobody's permission.

### bot-hunt â€” H10 run on real Kalshi L2, and only one number survived (2026-08-05)

Full write-up: [bot-hunt/RESULTS_H10.md](bot-hunt/RESULTS_H10.md).

H10 (rest a passive bid) was pre-registered on 08-04 and left unrun because it
needs the order book, not candles. It became runnable when a sibling's
retraction (`9ba0682`) established that **Kalshi L2 history does exist**.

**Built:** a range-request puller that reads **72â€“76% of each file instead of
100%** (column pruning over HTTP `Range` â€” it is a volunteer archive and a
sibling is already pulling the same files), a snapshot+delta **book replay** â€”
which `market-selection` called *"the single biggest piece of unbuilt
machinery"* â€” and a queue-aware fill model that never lets a touch count as a
fill. **6.9M L2 rows, 112 esports markets, 5,581 simulated resting orders.**

#### The result: one measurement, and a lot of noise

`src/h10_stability.py` re-runs the whole simulation over **nested prefixes** of
the corpus and watches each statistic's trajectory â€” the method that killed this
repo's own stars-vs-substance false positive.

| statistic | across prefixes | verdict |
|---|---|---|
| **fill rate, strict** | **30.8â€“31.2%**, last-3 drift **0.01** | âœ… **STABLE â€” the deliverable** |
| net P&L per filled contract | **âˆ’1.71Â¢ â€¦ +1.34Â¢** | âŒ **SIGN-FLIPS â€” noise** |
| adverse selection | âˆ’13.29 â†’ âˆ’8.52pp, monotone to zero | âš ï¸ artifact signature |
| "monopoly regime" thin-book edge | +1.47 â†’ +10.25pp, monotone up | âš ï¸ **GUARDS #10 warning sign** |

> **The 31% is independently corroborated.** The corpora were queried *before*
> the run: an r/quant bot author diagnosing his own too-good results â€”
> *"the reason my results are too good is likely the 100% fill rate; when it's
> 30% it will be way less."* **My strict measure lands at 31.1%.** Two routes,
> one number. **Fill rate is NOT the constraint on maker strategies here** â€” the
> pre-registered falsification (<20%) is not met.

> âš ï¸ **The most exciting number is the one to distrust.** The thin-far-side
> edge is the only quantity that STRENGTHENED with sample size, reaching
> +10.25pp [+1.35, +19.92]. GUARDS #10 pre-registered that exact pattern:
> *"monotone strengthening is evidence of contamination until proven
> otherwise."* Recorded as a lead needing a contamination check, not a finding.

#### âš ï¸ A correction inside the same session

I committed the H10 headline at `5186158` as **"you set out to earn +1.50Â¢ and
you get âˆ’1.50Â¢"** on 21 hourly files. Seven more hours moved it to **+0.38Â¢**.
The CI contained zero at both sizes â€” nothing was ever significant â€” but I led
with a point estimate that was noise. Marked inline, not rewritten.

#### Two of my own bugs, both caught by canaries

1. **The replay never re-synced.** Skipping a snapshot when state already
   existed let stale levels accumulate; books ended **crossed by 83Â¢**, which is
   impossible. **The conservation canary passed throughout at 0.047%** â€” stale
   levels are not negative levels. It took looking at the output. A
   **crossed-book canary** now exists and would have caught it instantly.
2. **A fill metric that measured nothing** â€” reported a 99.6% *lower* bound
   against a 45.8% *upper* bound. Inverted, therefore impossible. Cause: for an
   order that improves the touch, the market's best bid is below our price by
   construction, so "traded through" fires on every order.

The crossed-book canary also settled a data question worth carrying: **pre-event
crossing 5.60% vs post-event 83.65%**, and the alternative price-space reading
crosses ~100%. So the Kalshi bid/bid convention in `bot-hunt/src/venues.py` is
right, and **settled books are simply not maintained** â€” any L2 study must
restrict to pre-event observations.

#### What it says about the standing maker-vs-taker tension

`signal-github` said maker-only quoting is *"the one strategy whose income is not
required to overcome a fee first"*. **Correct and irrelevant** â€” the maker fee on
these series is genuinely zero (`fee_type = quadratic`, verified). The
20-year-professional's free-roll warning is **directionally supported and
unconfirmed**. **S008/S009's tennis result is not contradicted**; it is also not
independently reproduced, because at this sample size nothing is.

**Next:** the pull is extending to 48 hours. Re-run `src/h10_stability.py` on the
full window â€” if net P&L still sign-flips and adverse selection still decays,
that closes H10 as underpowered rather than negative.


#### H10 final, on the complete 2-day window (2026-08-05)

47 hourly files, **~13M L2 rows**, 7,182 + 5,777 simulated resting orders across
**81 events**. `src/h10_stability.py` re-runs the statistics over nested time
prefixes; the verdicts are its output, not my reading of them.

| statistic (JOIN) | prefix range | 1st half â†’ 2nd | verdict |
|---|---|---|---|
| fill rate, permissive | 62.8â€“68.7% | +63.9 â†’ +66.6 | âœ… **STABLE** |
| **fill rate, strict** | **29.0â€“35.7%** | +31.6 â†’ +34.5 | âœ… **STABLE** |
| **net P&L per filled contract** | **âˆ’1.48 â€¦ +2.55Â¢** | âˆ’0.35 â†’ +2.35 | âŒ **SIGN-FLIPS â€” noise** |
| adverse selection | âˆ’14.04 â†’ âˆ’4.03pp | âˆ’10.30 â†’ âˆ’4.52 | âš ï¸ **DECAYING â€” artifact** |
| "monopoly regime" thin-book edge | +2.05 â†’ +8.83pp | +4.22 â†’ +8.06 | âš ï¸ **STRENGTHENING â€” GUARDS #10** |

**One number from H10 is a measurement: the fill rate.** Everything about P&L
is noise, and the mechanism I most expected to find â€” adverse selection, the
free-roll â€” **decays toward zero as data is added**, the same trajectory shape
as this repo's stars-vs-substance false positive. It is not shown absent; it is
**unmeasurable at 81 events**.

> **The fill rate is corroborated three independent ways**, and this is the
> transferable output: my strict measure off the tape (**31â€“35%**), an r/quant
> bot author's diagnosis of his own too-good results (*"when it's 30% it will be
> way less"*), and `eshan327/kalshi-arb`'s hardcoded
> `PAPER_SIM_PASSIVE_BASE_FILL_PROB = 0.35`. **Fill rate is NOT the constraint
> on maker strategies on Kalshi esports** â€” the pre-registered <20%
> falsification fails.

**The fill model is validated against the API itself.** `hbere/kalshi-transport`
wraps `GET /portfolio/orders/{id}/queue_position`, documented as *"shares
resting ahead of this order under **price-time priority**"* â€” so joining the
back of a price level is Kalshi's actual discipline, not my assumption. Only
**5.2% of 3,201 repo archives model queue position at all, and 3.0%
trade-through**; the two things that decide whether a maker backtest is honest
are the two rarest.

âš ï¸ **A performance error of mine, recorded.** v1 of the stability script re-ran
the full replay per prefix â€” O(nÂ²) in files, ~350 parses of 200 MB parquet, and
it produced nothing in 15 minutes. Replaced by replaying once and slicing orders
by placement timestamp, which is exactly equivalent because an order placed in
hour 12 cannot depend on a file from hour 40.

---

## extractor-upgrade — chapters, a fifth corpus, and four bugs of my own (2026-08-05)

Full write-up: [extractor-upgrade/HANDOFF.md](extractor-upgrade/HANDOFF.md) ·
[FINDINGS_T7.md](extractor-upgrade/FINDINGS_T7.md) ·
[FINDINGS_T8.md](extractor-upgrade/FINDINGS_T8.md). Cost **$0.00**.

### Chapters — a free index, and a prediction of mine that failed

**367 of 1,197 descriptions already on disk (30.7%)** satisfy YouTube's own
chapter rule — first stamp `0:00`, at least three, at least 10 s apart.
**3,384 chapters**, median 8 per video, **538 (15.9%)** whose title names screen
content. The rule is implemented, not assumed: counting any description with ≥3
timestamps gives 396, and the 29 difference never render a chapter bar at all.

> ⛔ **I withdraw yesterday's claim.** `FINDINGS_T3` said a chapter list is *"a
> strictly better `watch_segment` seed than the phrase list."* **Measured: 2 of
> 19 watch_segments (11%) fall inside a chapter whose title names screen
> content.** n=19 is small, so this does not make chapters worse — it shows the
> two signals measure **different things**, which my sentence assumed they did
> not. A chapter indexes a *topic* over ~2.5 minutes; a watch_segment indexes a
> *moment needing eyes* over ~60 seconds. Written up before it was measured.

What chapters *are* good for, measured:

- **Retrieval with no transcript read.** `ask.py --chapters "results|p&l"`
  returns videos **nobody has read** whose authors already stated the result and
  the period in a structured field. Best of them: `-F0dZ2GxSuA` has a chapter
  titled **"3-hour results: $13 profit"** — a number *and* a denominator, free,
  in a column that had been fetched and never queried. Author vocabulary across
  3,384 chapters: `live` 78 · `code` 68 · `api` 64 · `results` 56 · `profit` 40.
- **Labelling where the permitted frames landed**, which immediately sharpened
  an open finding. `86AlV6174KI` is the corpus's only perfect `S=10 B=10`. Its
  author labels `7m23s "Running Your First Strategy Backtest"` and
  `13m41s "Coding & Optimizing Your Strategy"`. **The permitted frames land at
  ~8m19s and ~16m39s, inside both, and both show a man talking to camera against
  a garden wall.** A chapter is 6 minutes and a frame is one instant, so this
  proves nothing alone — but the video's TENSION flag now has a second
  independent leg beside its own on-screen **"NO CODE"** overlay.

### A fifth corpus: Hacker News, on an explicit `Allow`

`hacker-news.firebaseio.com/robots.txt` reads `Allow: /*.json$` **before**
`Disallow: /`, so the API is explicitly permitted and only the HTML is not.
`hn.algolia.com` serves **no robots.txt at all** — undecidable, not permitted —
so Algolia is used *only* to turn a search term into integer ids and **every
byte of content comes from Firebase.** Enforced by construction.

**607 stories · 312 beginner-family / 298 insider-family · 3 in both ·
Jaccard 0.005.**

> The **direction** reproduces on a fourth corpus with a completely different
> retrieval engine. **The magnitude does not, and I am not claiming it does** —
> 0.005 is about seven times lower than `youtube-signal`'s 0.037 and
> `signal-github`'s 0.032/0.033/0.036, and the likely reason is that **I wrote
> both term lists myself** and made them more disjoint than the video families
> were. A number whose inputs I chose is not an independent replication of a
> number somebody else measured.

**537 of 607 score SKIP — and that is a finding about my collection, not about
Hacker News.** Comments were skipped for speed (~25× the requests) and on HN a
story is usually a headline and a URL with no body text, so a substance rubric
has nothing to read. **The comment pass is running now.** What the stories layer
surfaces for free is the **Launch HN for Kalshi itself** — 148 points, **165
comments**, the venue this programme trades, announced by its founders, replied
to by 165 people with no reason to be polite.

### ⚠ Four bugs of mine today, and two would have produced a false result

1. **The frame retraction** (§ previous section) — I read `Disallow: /sb/`,
   correctly concluded storyboards were forbidden, and never asked what else
   lived on that host.
2. **Algolia AND-matches every term**, so `"adverse selection market making"`
   returns **0** while `"adverse selection"` returns 20 and `"market making"`
   returns 1,343. Long phrases are how a human describes a concept and not how
   an index is queried.
3. **My dedup decided the headline number.** `collect()` skipped ids it already
   held, so a story found by *both* families was filed under whichever reached
   it first — making the overlap **structurally zero whatever the corpus
   contains**. The first run returned Jaccard **0.000** and **I was one commit
   from writing it up as the fourth independent corroboration of this
   programme's own finding.** It would have been a fabricated result that agreed
   with three prior measurements, which is exactly when a number is least likely
   to be questioned.
4. **The comment pass was a silent no-op that reported progress.** Comments were
   fetched inside the `if already have this story: skip` branch, so on any
   corpus that already existed it re-ran every query, printed every count, and
   wrote nothing. Same shape as the bug this repo already has on record that
   *"reported 358 repos scored when 92 had real data."*

**A silent no-op that reports progress is worse than a crash**, and a
self-inflicted number that agrees with your prior results is worse than either.

### The HN comment pass finished, and it went the other way

**3,272 comments across 374 threads · 3,886 items scored.** My prediction was
*"the substance is in the comments."*

| | non-SKIP | rate |
|---|---|---|
| stories | 70 / 614 | **11.4%** |
| comments | 127 / 3,272 | **3.9%** |
| whole corpus | 197 / 3,886 | **5.1%** |

**Absolute yield nearly tripled (70 -> 197) and the rate more than halved.**
88.5% SKIP became **94.9%**. Comments diluted the corpus. Both readings are
true and answer different questions: a comment is mostly not worth collecting
(25 per story to find 0.34 useful ones), and the pass was still worth running.

The four that justify it all land on threads this repo has closed — a
practitioner at **$6B monthly crypto volume** writing *"nothing we tried with
usual strategies worked consistently… everything failed out of sample"*; the
backtest-to-live collapse in one sentence; someone doing this repo's own
cost-bar arithmetic in a comment box; and **a structural mechanism for
long-shot overpricing that this repo did not have** — PredictIt's **$850
per-market risk limit** caps how much informed money can correct a mispriced
long shot. `youtube-signal` measured the same bias on Kalshi (5c contracts
resolve YES 4.18% over 72M trades) with **no mechanism attached**. This
supplies one.

> ### ⚠ HN did NOT find a repo GitHub search missed, and I nearly said it did
> 90 GitHub repos are named across the HN corpus, 18 trading-relevant, and
> **17 of those 18 absent from `signal-github`'s 4,017.** That reads as a
> retrieval failure. Checking killed it: **only two of the 18 are
> prediction-market repos at all** — `rodlaf/kalshimarketmaker`, which is
> **already in the corpus** (226 stars, alive), and
> `Gabagool2-2/polymarket-trading-bot-python`, which returns **HTTP 404 and does
> not exist**. The other 16 are Binance bots, `zipline`, `awesome-quant`,
> `Chronicle-Queue` — correctly excluded by the topic gate.
>
> **The negative result is the finding: `signal-github`'s six retrieval axes
> have complete coverage of the on-topic space as probed from an independently
> built corpus.** Nobody had tested that from outside. Recorded because the
> 17-of-18 framing survived three of my own commands before I checked what the
> 17 were. **A striking ratio with a mixed denominator is not a finding.**

**Verdict on Hacker News: keep, at low priority.** 5.1% non-SKIP is a thin seam
and it adds no code coverage — but it is the only corpus here containing people
who traded professionally, writing about why it stopped working, with nothing
to sell.

**Single next action:** nothing is running. The open items are the four new
[GUARDS.md](GUARDS.md) rows (13-16) landing in other projects' checks, and
pointing `youtube-signal`'s reader at podcasts via the keyless PodcastIndex.

---

## bot-forensics â€” the night the bot made money (2026-08-05)

`bot-forensics/` Â· code, `FINDINGS.md` (Tasks 1â€“2), `VERDICT.md` (Tasks 3â€“5),
`DECISIONS.md` and `out/` all committed â€” `out/` is ~250 KB of plain text and
CSV holding market tickers only, so the evidence is checkable over the web.
**Read-only throughout: the bot was not started, no order endpoint was touched,
and `TRADING_DISABLED` is untouched.**

### There was no profitable night

**The live tennis bot's lifetime P&L is âˆ’$6.92 over 108 matches** (74
independent entry bursts), mean âˆ’$0.064/match, 95% CI **[âˆ’$0.97, +$0.78]**. Its
equity curve *does* peak at **+$32.19** after 60 matches, at 13:32 UTC on
28 Jul, and then loses $39.12 over the remaining 48.

**That split was found at the argmax of the equity curve, which is the most
selection-biased cut available.** Against 200,000 random reorderings of the same
108 results:

| statistic | observed | null median | p |
|---|---|---|---|
| peak of the curve | +$32.19 | +$13.40 | **0.052** |
| mean(before) âˆ’ mean(after) | +$1.3515 | +$0.9971 | **0.272** |

A zero-drift process with this dispersion shows a positive argmax gap **85%** of
the time.

> **The account DID go up about $99 in this window and none of it was the bot.**
> All of it was hand-traded on 25â€“26 Jul, before the bot placed its first order
> at 05:58 UTC on 27 Jul. Separating the two was not optional: a first attempt
> split bot from manual on order notional and classified a hand-placed 6c NO
> longshot (+$14.51 â€” **half the apparent bot total**) as a bot trade. The
> classifier is now structural (`side==yes`, price 10â€“90c, notional $4.60â€“6.30)
> and cannot see the outcome.

### Three things established that were not known before

**1. The martingale is in the profitable stretch too, and it went 7 for 7.**
12 of 101 traded markets averaged DOWN â€” each leg cheaper and therefore
*larger*. Those 12 are **âˆ’$16.43**; the other 94 matches are **+$9.63**. *The
bot's entire loss is the martingale.* Before the peak there were **seven
averaging-down sequences and seven winners, +$6.63**; after it the same
mechanism lost ~$23, with SAGLEV alone (âˆ’$8.79) bigger than all seven early wins
combined. **A martingale that is winning is indistinguishable from skill.**
Minor correction to the existing record: the SAGLEV legs were **749s and later
apart, not 24s** â€” the 24s figure is the gap from stop-out *fill* to re-entry,
which is the right number for the re-arm question but overstates how frantic the
entry sequence looked.

**2. The stale-score bug is now measured, not just asserted.** Over 4,398
game/set changes in the recorder tape, **only 2.6% of the repricing falls after
our snapshot showed the new score** â€” +4.68c before, +0.17c after, with a
placebo five minutes earlier at +0.18c confirming it is not ordinary momentum.
Whatever the mix of feed lag and honest anticipation, **the entry signal arrived
after the move it was meant to predict.**

**3. Overnight ITF books are 2â€“6Ã— wider, so the night/day comparison is
confounded AGAINST the night.** Mean spread by tier in the 40â€“80c band: ATP
1.17c Â· WTA 1.24c Â· Challenger 1.57c Â· ITF-M 2.80c (night **5.26c**) Â· ITF-W
4.48c (night **7.16c**). The bucket that looks better has the worse book.
**0 of 13 permutation-tested time/tier buckets clear BH-FDR at 5%** â€” the same
answer the set-1 overshoot study reached at 0 of 25.

### â›” Task 3 â€” the decisive test. The strategy loses on ITF worst of all.

`tennis_engine.evaluate()` was **imported and called**, not reimplemented, with
the night's Config reconstructed from that file's dated comments plus the order
record. Execution via `backtest/engine._walk`, so the fee/slippage/tie rules are
the sweep's own.

> âš ï¸ **`backtest/data/sofascore_matches.jsonl` contains ATP, Challenger and WTA
> and NOT ONE ITF MATCH** â€” while ITF is 10,261 of 13,658 market views and 64 of
> the 108 matches the bot actually traded. A second arm with a price proxy for
> "won a set and ahead" covers all 13,658.

| | c/trade | ranks against |
|---|---|---|
| S2 buy-and-hold (best known here) | âˆ’2.29 | |
| 480-config sweep, best of 480 | âˆ’4.90 | |
| **night's config, ATP/Ch/WTA, real scores** | **âˆ’5.64** | â‰ˆ rank 55 of 481 |
| **night's config, all tiers, proxy** | **âˆ’8.08** | |
| S5 **random entry** | âˆ’8.28 | |
| **night's config, ITF only** | **âˆ’9.13** | t = âˆ’26.0, n = 2,599 matches |
| S1, the v3 strategy | âˆ’9.36 | |

Every variant, every tier, train **and holdout**, both arms: negative. ITF-only
holdout is âˆ’8.77c on 1,045 matches, t = âˆ’16.0. There is no climb threshold
(0/5/10/15/20/30c) at which it turns.

**The live 39 hours are consistent with this.** Live âˆ’$0.064/match (se 0.284)
against the backtest's âˆ’$0.755/match (se 0.077) â†’ t = 2.35. The live window ran
about two standard errors better than its own backtest predicts, which is what a
good run looks like.

> **Four independent files now agree the STOP LOSS is the most expensive
> component**, and this contradicts the live bot's design. `high_entry`: âˆ’0.78c
> becomes **âˆ’3.77c** when a stop is added to identical trades. `high_sweep`'s
> best rows are all hold-to-settlement. S2 beats S1 by 7.07c. And removing the
> stop is the single best change in the replay (âˆ’6.47 â†’ âˆ’4.59c). The live bot
> stopped out of 77% of backtested trades.

**`high_sweep.py`, `high_entry.py` and `longshot.py` re-run and SAVED** to
`bot-forensics/out/rerun_*.txt`, closing `audit/LEDGER.md` R6 â€” those four
findings no longer exist only in a memory file.

### ðŸ”“ Task 4 â€” one thread REOPENS, and two corrections to this file

**ITF data exists, contrary to the prior session's "NO free ITF source at all".**
`livetennisapi.com` â€” eleven official client libraries on GitHub, every one
pushed within two days. Verified directly, not from a README:
`GET api.livetennisapi.com/api/public/v1/health` â†’ **200 `{"status":"ok"}`**, no
key; `/v1/matches?status=live` â†’ 401. Advertises **ATP + WTA + Challenger + ITF,
singles and doubles**, a **free tier** for live scores, market odds at $29.99,
and a point-by-point tape Jan 2023 â€“ Jul 2026 including ITF.
**Not verified that the free tier really returns ITF** â€” that needs an API key,
which needs an account, which is the user's to create. **This is the
highest-value open item in the report.** Note it reopens *data availability*, not
the trade â€” Task 3 says ITF economics are the worst of any tier.

> âš ï¸ **Correction to this file: "Sackmann upstream is 404" is too strong.**
> Checked today: `JeffSackmann/tennis_atp`, `tennis_wta` and
> `tennis_slam_pointbypoint` **are** 404, but **`tennis_MatchChartingProject` is
> live, 399â˜…, pushed 2026-05-25**, and `Aneeshers/tennis-sackmann-archive` is a
> live third-party mirror of the ATP/WTA/Grand-Slam point-by-point data pushed
> 2026-06-25. `kalshi-tennis/data` is still worth protecting; it is not the only
> copy of its inputs.

**Nobody has published a working in-play tennis strategy with evidence â€” and the
field is crowded.** 32 distinct Kalshi/Polymarket tennis repos, **30 created in
the last 180 days**, 135 stars between all of them (129 in one repo), and every
repo that states its mode says **paper**. Consistent with finding #9 above: if
the obvious in-play tennis trade were available it would not survive thirty
simultaneous discoverers.

**Overnight-vs-daytime in prediction-market sports books: nobody documents it.**
Four targeted GitHub queries returned one repo between them. In 1,135 YouTube
transcripts (39.8M chars) "overnight" appears 142 times and **every hit is
equity/futures session language**. **"ITF" appears zero times.**

> âš ï¸ **A claim in the YouTube corpus is FALSE and was checkable from disk.**
> `ELpX7I0sPtc` states that on prediction markets a tennis medical withdrawal
> settles "at the number they were at at the time of the withdrawal".
> `_settled_all.json` holds 9,352 settled tennis markets: **4,676 `yes` and
> 4,676 `no`, exactly mirrored, zero non-binary.** `KXITFWMATCH-26JUL23KUJCIO`
> closed at 43c/61c and settled **yes** for the 43c side â€” a retirement pays a
> 43c holder 100. `tennis_engine.py:332` has it right. One more entry against
> the stop loss: that windfall is invisible to one.

### Verdict â€” A and B jointly. C contributes. **D is refuted.**

**A (variance) and B (a martingale that happened to win) together.** C (the
stale-score bug) is real and measured, but it predicts a persistent negative
drift and so makes the profitable stretch *less* explicable, not more â€” it
explains why there is no edge, not why one run went up. **D is refuted**: the
condition proposed is the worst cell in a 13,658-market test at t = âˆ’26.

**One sentence:** the account did go up ~$30, the bot's own trades were not what
did it, the shape everyone remembers is the shape a fair coin makes, and the
mechanism behind the run of small wins is the same one that produced the âˆ’$8.79
that ended it.

**No action on the bot. `TRADING_DISABLED` stays.** This is the second
independent verdict on the same strategy, now from the live record as well as
the backtest.

---

## bot-forensics — independent re-run and ledgering (2026-08-05, later session)

A second session re-ran the analysis from scratch and put the project into
[LEDGER.md](LEDGER.md). **Nothing above was rewritten; the verdict is unchanged.**

### Every headline number reproduced bit-identically

`t2_master.py`, `t2b_nightday.py`, `t2c_costbar.py`, `t2d_martingale.py` and
`t3b_proxy.py` were re-executed. −$6.92 over 108 matches, 74 bursts, CI
[−$0.97, +$0.78], peak +$32.19 at 13:32 UTC, argmax p = 0.052, 12 martingale
sequences at −$16.43, 97.4% of repricing already done, and the decisive ITF
replay at **−9.13c/trade on 6,135 trades / 2,599 matches** all came back
unchanged. `t3b_proxy.py`'s full output diffs **identical** to the committed
copy. **The verdict rests on numbers that now reproduce on a second run.**

### ⚠ One reporting selection found, and it is the only correction

**`t2b_nightday.py` prints "buckets tested: 21 · BH discoveries at FDR 5%: 3" —
and always did, it is in the committed output at line 93 — while `FINDINGS.md`,
`VERDICT.md` and `HANDOFF.md` all state "0 of 13" without naming which arm.**

**⚠ Correcting the first version of this entry: [GUARDS.md](GUARDS.md) #17 *does*
state it** ("three buckets cleared on t-statistics and none survived label
permutation"). So this is a **propagation gap — the reusable guard kept the
caveat and the project's own three write-ups dropped it** — not a suppressed
result, and a smaller problem than first written. **No new guard is needed;**
GUARDS #17 already carries both traps.

They are two different tests: "0 of 13" is the **permutation** arm (200,000
shuffles), "3 of 21" is the **parametric** arm over a family that adds the
tier×night cells. **The 0 is correct and the 3 is the broken test** — the three
"discoveries" are n = 4, 5 and 6; one of them is a *loss* bucket (WTA|day, all
four losers); and the parametric p for the 04–07 bucket is 0.0002 against a
permutation p of **0.0477 on the same five matches, 240× larger.** A t-test at
n = 4 is anti-conservative, which is precisely why the permutation arm exists.

Marked inline in all three files rather than quietly fixed, because a reader who
runs the script sees the 3. Ledgered as **B005a**.

### The project is now in the root ledger — Section 7, rows B001–B020

**21 rows.** Tally 233 → **254**; RETRACTED stays **45** (no B-row is itself a
retraction). Like `kalshi-market-scan` before it, `bot-forensics` had **no rows
in this ledger at all**, and it is the project most likely to be acted on
because it is the only one about **money that actually moved**.

**Ledgering it immediately corrected two stale rows in Section 5, exactly as the
K015=W011 episode predicted:**

| row | was | now |
|---|---|---|
| **CH044** | "position-sizing blowout … **never diagnosed, never fixed**" | **wrong on both counts.** Diagnosed 08-03 as a martingale, fixed the same day — and **B007 shows it was never one match: twelve averaging-down sequences, −$16.43, while the other 94 matches were +$9.63** |
| **CH031** | score-staleness bug recorded as a fact, **no magnitude for months** | **B008 sizes it**: 97.4% of repricing already complete before the bot could see the score |

Also closed: **`kalshi-inplay-bot/audit/LEDGER.md` R6** is now marked resolved
inline with the four rescued findings restated in the row itself, so they survive
even if `bot-forensics/out/` is lost. And `FINDINGS.md` pointed at a
`MARTINGALE.md` that was never written — repointed at the analysis, which is in
`FINDINGS.md` itself.

**The Sackmann correction is now marked where the claim is made** (the "Threads —
CLOSED" table and the "Data on disk" table), not only at the bottom of this file.
The Stage 0–5 derived caches are still the only copy; their *inputs* are partly
recoverable.

### The ITF check is now built and waiting on one free signup

**Still the user's, but no longer unprepared.**
[bot-forensics/ITF_CHECK.md](bot-forensics/ITF_CHECK.md) has click-by-click
steps against the **verified** current form (one field, "Your email"; button
"Get my key"; no password, no card), and `src/t5_itf_probe.py` runs the check in
**6 requests** and prints PASS / FAIL / INCONCLUSIVE.

**Endpoint paths are verified, not guessed:** `/matches`, `/tournaments`,
`/players`, `/fixtures` and `/usage` all return **401, not 404**, so those routes
exist and only want a key. `/health` is 200 without one. Both failure paths (no
key, bad key) were tested. **The key is never printed, stored or committed** —
only its length and `twjp_` prefix.

**One thing I could not verify and said so rather than guessing:** whether the
key appears on screen or arrives by email. The page does not say. `ITF_CHECK.md`
tells the user to check the page first, then the inbox.

**Sharpened reading of the vendor's claim.** ITF appears in the hero blurb, the
FAQ and the historical-tape description. The Free tier card restricts by
**capability** (no odds, no model, no WebSocket) and **rate** (30/min, 1,000/day)
and **states no tour restriction anywhere.** That makes free ITF plausible — but
the site never affirms it either, so it stays an inference written by the vendor.
**Which is exactly why it gets measured rather than believed.**

**It reopens data availability only** — B009 says ITF economics are the worst of
any tier (−9.13c/trade, t = −26). **In none of the three verdicts does the bot
come back on.**


### bot-hunt â€” the shortlist's #1 mechanism, tested for the first time (2026-08-05)

Full write-up: [bot-hunt/RESULTS_CROSSVENUE.md](bot-hunt/RESULTS_CROSSVENUE.md).

`SHORTLIST.md` ranked esports first on a mechanism **nobody in this repo had
ever tested**: de-vig a sharp sportsbook, compare to the prediction market,
trade the difference. It cannot be backtested â€” Pinnacle is live-only and every
free historical esports odds source is dead â€” so the recorder started
**2026-08-04 21:27 UTC** was the entire apparatus. 145 cycles, **13.4M Pinnacle
priced records**, 710 esports matchups, 99k Kalshi book snapshots.

**Result, on 5,334 paired observations at a median 7-second time alignment:**

| de-vig | median buy edge (fair âˆ’ Kalshi ask) | >2Â¢ | >5Â¢ |
|---|---|---|---|
| multiplicative | **âˆ’0.72Â¢** | 13.1% | 2.9% |
| power | **âˆ’0.75Â¢** | 12.4% | 0.7% |
| worst-case | **âˆ’1.64Â¢** | 5.9% | 0.5% |

**The median edge is negative under every method.** Pinnacle's overround is
4.82pp. **This is the fourth independent confirmation that Kalshi is the sharp
line** â€” after tennis (**T012**, r=0.9878 vs the Betfair close), MLB moneyline
(0.37Â¢), and 3-way soccer ladders (0 of 93) â€” now against the sharpest book in
the world at 7-second alignment.

> **The de-vig METHOD decides most of the apparent tail**: >5Â¢ buy edge on 2.9%
> of observations under multiplicative but **0.5%** under worst-case. That is
> exactly what the one author with a reconciled live P&L reported when his Shin
> implementation *"ran hot on favourites"*.

#### âš  The join is where cross-venue work dies, and mine had a real phantom

Matching on the Kalshi **ticker** matched **3 of 218** events â€” its outcome
codes are 2â€“4 letter abbreviations (`REDA`, `ODK`, `WAVE`) while every other
venue uses full names. Matching on full names gave 97, and **hand-auditing every
one** found a **`KXCS2GAME` market paired to a Mobile Legends matchup**. The
join never looked at the league.

Two filters added, and they are the precision step the corpora insist on:
**game consistency**, and **roster-suffix AGREEMENT** â€” an organisation fields
several teams, so the test is not whether "Academy" is present (both venues
legitimately say it when the match really is between academies) but whether they
**agree**. 97 â†’ 84 events. The 13 contributing events were unchanged, so the
numbers stand â€” **that is luck, not design.**

> My first audit script flagged 6 of 10 pairs suspect and **most flags were
> wrong**: it fired whenever a suffix appeared at all. A detector that fires on
> the correct case is not a detector. Fixed to compare, not detect.

#### A recorder gap found and fixed

`k_book` stored no market title, which is why the join had to be reconstructed
from a separately-pulled universe. Added a **`k_names`** table, populated for
every listed market (names are free once the listing is in hand). Recorder
restarted. **Anyone building a live cross-venue system hits this on day one.**

#### Contamination check on the one positive result: not killed, not confirmed

`src/contamination_check.py`, four tests against the thin-far-side "monopoly
regime" edge that GUARDS #10 flagged for strengthening with n:

| test | JOIN | reading |
|---|---|---|
| baseline | +8.19pp | the claimed effect |
| **within-event** | **+6.08pp** [âˆ’6.13, +20.13] | keeps **74%** â†’ **not** a between-event artifact, but 75 events cannot resolve it |
| time-to-event | thin is **2,149** min out vs thick **1,467** | âš ï¸ a real ~11 h confound; effect present in both strata |
| price-stratified | +7.04pp | price is **not** the confound |
| **placebo** (even vs odd placement minute) | **âˆ’3.7pp = 45% of the effect** | âš ï¸ the estimator's noise floor |

**Stays a lead.** The binding constraint is **81 events**, not 13M rows â€” more
hours of the same matches add orders and no independent information. Pulling
2026-06-01..06-04 for ~10Ã— the events.

> âš ï¸ **I nearly recorded the opposite conclusion.** My first rule printed
> *"DOES NOT SURVIVE â€” the effect is BETWEEN events"* whenever the within-event
> CI included zero. A point estimate keeping 74% of its size has not collapsed;
> the *interval* widened. The rule is now three-valued â€” SURVIVES / UNDERPOWERED
> / COLLAPSES â€” which is **GUARDS #1's principle applied beyond the selection
> canary: UNTESTABLE must never be rendered as a verdict about the effect.**


### bot-hunt â€” the Polymarket leg, and five new GUARDS entries (2026-08-06)

Detail in [bot-hunt/RESULTS_CROSSVENUE.md](bot-hunt/RESULTS_CROSSVENUE.md) Â§3b.

**Polymarket was the venue left untested and the one that mattered** â€” it is
where the only reconciled live P&L came from (+$4,973 net over 3,858 fills), and
makers there are **paid a rebate rather than charged**, the one structural
difference that could have changed the answer.

#### The structural finding is bigger than the edge

Of **436 recorded esports (slug, outcome) pairs**: **247 map/game-N markets,
111 props, 62 handicaps â€” and only 16 plausible moneylines.** Polymarket esports
is **~96% derivative markets**. The moneyline surface, the only thing a
sportsbook line can be de-vigged against, is a thin corner of it.

#### The measurement

291 paired observations, 3 markets, median alignment 256 s. **Median buy edge
âˆ’2.62Â¢ (multiplicative), âˆ’0.83Â¢ (power), âˆ’2.62Â¢ (worst-case)** â€” under two of
three methods even the *90th percentile* observation is negative. Polymarket's
spread is 1.00Â¢ median; Pinnacle's overround 7.06pp.

**Same direction as Kalshi and slightly worse.** Three markets is a direction,
not a result, and it is quoted only because it agrees rather than contradicts.

> âš ï¸ **Four of twelve matches were phantoms, from a one-character team name.**
> "FOKUS Sakura", "Gentle Mates GC", "Natus Vincere" and "SK Nebula" all matched
> the *same* "Trace vs A Team" â€” because Pinnacle's **"A Team" normalises to
> `"a"`** once the stopword *team* is stripped, and `"a" in name` is true for
> almost everything. Fixed with a length floor on both strings and by requiring
> the **opponent** to appear in the slug. 12 â†’ 5, all five genuine. **Here the
> phantoms WERE contributing observations**, so only post-filter numbers are
> quoted.

#### Two recorder gaps found, fixed, and PROVEN

Both were the same class â€” cheap to record, impossible to reconstruct afterwards:

| gap | consequence | fix |
|---|---|---|
| `k_book` stored no market title | joining Pinnacle to Kalshi on the ticker matched **3 of 218** events, because the codes are abbreviations | **`k_names`** table â€” live, **1,273 rows**. `NCX`â†’Necaxa, `VPP`â†’VP.Prodigy |
| `p_book` stored only the **first** outcome token | *"slugs with â‰¥2 recorded outcomes: 0 of 436"* â€” no two-sided book, no crossed-market detection | probes both tokens â€” **17 of 17** in test |

> **Both times the live table read 0 and the obvious inference was wrong** â€”
> cycles run ~14 min and the changed stage had not run yet. Verified against a
> scratch DB instead. **GUARDS #13: assert the content, not the call** â€” and
> "the table is empty" is a statement about timing as often as about code.

#### GUARDS.md 17 â†’ 22

Guards 13â€“17 (from `extractor-upgrade` and `bot-forensics`) already covered the
football-data trap and probes-that-fail-toward-a-kill, so only what is new was
added:

- **#18 the structural-invariant canary** â€” conservation ran at **0.047% and
  PASSED** while the replay produced books **crossed by 83Â¢**. Stale levels are
  not negative levels. Assert an invariant the *real object* must satisfy.
- **#19 the stability curve** â€” flat = a measurement, sign-flips = noise, decays
  to zero = artifact, strengthens with n = contamination.
- **#20 the placebo split** â€” splitting on the parity of the placement minute
  produced **45% of a claimed effect**. That is the noise floor a claim must
  clear. And when a bootstrap and a permutation test disagree, believe the
  permutation test.
- **#21 UNTESTABLE is a verdict about the TEST, never about the effect.**
- **#22 cross-venue joins** â€” name similarity is recall; the second side is
  precision.


---

## bot-forensics — ITF settled, and the player-feature hypothesis tested (2026-08-06)

Overnight autonomous session. **Read-only against the bot: it was not started,
`TRADING_DISABLED` untouched, nothing in `kalshi-inplay-bot/` changed.**
Full write-up: [bot-forensics/FINDINGS_T7.md](bot-forensics/FINDINGS_T7.md).
Design fixed in advance in
[bot-forensics/PREREGISTRATION_T6.md](bot-forensics/PREREGISTRATION_T6.md),
committed **before** any number existed.

### 🔓 The ITF thread was closed on a false premise

The user supplied a free `livetennisapi` key. **`GET /tournaments?tour=itf`
returns `total: 7786` on the free tier.** A free ITF data source exists.
`B016` UNVERIFIED → **SETTLED** via new ledger row **B021**.

**This reopens data availability only.** B009 still says ITF economics are the
worst of any tier (−9.13c/trade, t = −26). Nothing about the bot changes.

> ⚠ **The vendor's own rate limit is wrong by 10×** (ledger **B022**). The site
> advertises 1,000/day; the API's `/usage` returns `per_day: 100`. Anything
> planned against the advertised figure is planned wrong.

> ⚠ **The API key is in a chat transcript and should be treated as disposable.**
> It is never written to disk or committed by any script here. Rotate when
> convenient — it is free to replace.

### The user's hypothesis, tested properly: a clean null

*"Kalshi is efficient in aggregate, but individual matches contain more —
form, head-to-head, rest, surface."* The premise is right and had never been
tested on pre-match player features. It has now been.

Built **6,519 events** with leak-free form / rest / workload / H2H / round
features, using `markets.parquet`'s `player` column — which carries names for
all 14,162 markets, so no external data was needed. Selection canary **0.5005,
z = +0.09, PASS**.

| | |
|---|---|
| cells swept | **2,008**, one BH-FDR denominator over all of them |
| BH discoveries, real data | **2** |
| BH discoveries, **shuffled** data | **4.1 on average** |
| max \|t\|, real vs null | **4.17** vs **4.40** |

**A sweep that finds less than its own null has found nothing.** (Ledger **B023**.)

The one survivor — "buy the heavy favourite", +4.31pp on train, same sign on
holdout — **died on execution.** Its residual is monotonic in the width of the
opening book: **+1.18pp (t = 0.64) on tradeable ≤2c books, +7.92pp on >8c
books.** Net at the ask on holdout: **−0.77c**. (Ledger **B024**.)

### The strongest positive result of the night, and it is about the market

`t8_calibration.py`: **on tradeable books (spread ≤ 2c), 0 of 10 price bands
from 1c to 99c deviate from calibration.** Pooled residual **+0.03pp, se 1.09pp,
t = +0.03**. On wide books, 2 of 10 deviate.

**Where Kalshi tennis is liquid, its opening price is right across the whole
range.** This also **resolves B026 in K009's favour** — "the favourite-longshot
bias does not exist on Kalshi" is now confirmed on independent data by a
different method. Ledger **B027**.

### ⚠ Two bugs in my own analysis code, both pushing toward a false positive

Caught before publication and recorded as **B025**:

1. The first permutation null shuffled outcomes **within tier only**. Favourites
   really win ~92%, so handing them the tier average manufactured a −38pp
   residual and **1,010 false discoveries of 2,008, max \|t\| = 22.** The tell
   was that the null was *worse* than the real data.
2. Entries were priced at the **mid**. A taker lifts the ask — worth 2–3c here,
   **larger than every effect measured.**

### What could NOT be done, stated rather than worked around

- **Surface retrospectively:** no join key. Kalshi's records carry tier, not
  tournament name. **But surface IS on every upcoming fixture** — recording
  fixtures from now makes surface analysis possible in ~a month. Cheap, and a
  recorder job rather than an analysis one.
- **Serve %, double faults, aces:** absent from the feed at any reachable tier.
- **Head-to-head:** built, but only **1.2%** of events had a prior meeting.

### The honest limit on the null, and the one thing worth $9.99

**Every weak part of this study traces to the corpus being 29 days long.**
`corr(prior win rate, outcome)` was **+0.0058** because the median player appears
about three times. **B023 should be read as "not demonstrated on 29 days of form
data", not "player features cannot work."**

`livetennisapi`'s history plan is **$9.99** for **43 months, Jan 2023 → Jul 2026,
point-by-point, including ITF.** That would let this exact study re-run on three
years instead of four weeks and settle it properly. **B027 does not depend on the
window and stands regardless.**

**Ledger: +7 rows (B021–B027), tally 254 → 261.** RETRACTED still 45 — the
directional prior held for the 46th time.

---

### bot-hunt — the de-vig test: never actually run, now pre-registered, and NOT reachable on MLB (2026-08-06)

Full write-up: [bot-hunt/PREREGISTRATION_DEVIG.md](bot-hunt/PREREGISTRATION_DEVIG.md)
(committed `d163484`, **before any return existed**) and
[bot-hunt/RESULTS_DEVIG.md](bot-hunt/RESULTS_DEVIG.md). **No settlement outcome
has been joined to any price in either file.**

**The question:** de-vig Pinnacle → fair value → compare to the executable Kalshi
price → **count it only when the gap beats cost**. **It has never been run here.**
Step 6 tested H1–H9 on **Kalshi's own price only**; RESULTS_CROSSVENUE measured
the **distribution** of the de-vigged gap on esports with **no settlement, no
gate and no P&L** (its own §4.3 says so). T012 is a calibration statistic.

**The answer is arithmetic, not statistics.** Pinnacle's MLB overround is
**2.01 pp** — that is the whole quantity de-vigging removes, ~1 pp per side. The
Kalshi taker fee at 50¢ is **1.75¢** and the quoted spread **2.0¢**, so the cost
bar at 1¢ slippage is **2.75¢**. *The cost bar is larger than the entire vig.*

Measured qualifying rate **q = 0 of 17 events** at the primary cell (1 of 17 at
zero slippage). The **best** per-event net gap, choosing the entry with hindsight
across each event's full 24 h window, is **−0.91¢** — no event is positive at any
moment. Rule-of-three upper bound `q ≤ 0.18`, and all timelines below use that
optimistic figure.

| stage | events needed | verdict |
|---|---|---|
| **A** — is the de-vigged reference a *better forecast* than Kalshi's price (paired Brier) | **≈ 440 ≈ 30 MLB days ≈ early Sept 2026** | **REACHABLE** |
| **B** — the gated P&L test as asked | 5¢ edge → **4,356 events = 1.8 seasons**; 3¢ → **5.0 seasons**. Rest of this season resolves only **11.6¢** | **NOT REACHABLE** |

No historical shortcut: Pinnacle has no historical endpoint at any price, and the
only free historical sharp line found is **soccer only**. Baseball is
forward-only.

> ### ⚠ THE RECORDER WAS DEAD FOR 2.5 HOURS AND NOTHING NOTICED
> Last cycle **2026-08-06T15:13Z**, no process alive at 17:41Z, **zero bytes in
> `recorder3.err`.** It had been launched from a prior session's shell and died
> with it. Restarted detached. **Nothing monitors it** — and it is the only asset
> in the project that cannot be bought back later.

**Two recorder defects found and fixed.** (1) `record.py` probed `mkts[:60]` in
Kalshi's **undocumented** listing order; `KXMLBGAME` lists 85–104, so ~40 got no
book per cycle and the server chose which — snapshots per MLB ticker ran **min 1,
p25 25, median 94** over 214 cycles. Now sorted by `close_time` ascending.
(2) The club-name join silently dropped the **Athletics** (`A's` → `a s`, under
the length-4 floor that exists to stop the Polymarket one-character phantom); 5
of 53 events lost, fixed with an exact 30-club code map, join 17 → 21.

> ### ⚠ Third Kalshi time field to mislead this repo
> **`close_time` on a LIVE Kalshi MLB market is the game start plus exactly
> 72 h** (94 of 94 active markets). On **settled** markets Kalshi rewrites it to
> the true settlement instant, 2.4–3.2 h after start. Anchoring a live market on
> it anchors **69 hours after first pitch.** After Amendment A1 and LEDGER T010,
> this is the third. Start is now derived from the ticker, verified exact against
> Pinnacle's independent `starts_utc` on **22 of 22** jointly-listed games.
>
> ✅ **The old MLB control is NOT damaged** — it ran on settled markets, where the
> field is the true settlement instant. Checked specifically; the opposite would
> have voided RESULTS.md's control gate.

> ⚠ **Correction to [bot-hunt/RESULTS.md](bot-hunt/RESULTS.md) §3.** Its
> "`KXMLBGAME` is **1.0¢** at every lead" is a **candle** measurement. The
> recorded live touch is **median 2.0¢, p90 7.0¢**, and the strategy pays the
> touch. Marked inline rather than deleted.

**MLB was Step 6's negative control, and promoting it to test family is
legitimate — with one thing genuinely broken.** The control is **spent**, not
reserved: it gated one candle-based run of H1–H9 and reported PASS. The **data**
is not reused — a hard boundary excludes any game starting before
**2026-08-05T00:00:00Z**, clearing the control set's latest game start
(**2026-08-04T23:40:00Z**), asserted in code. What breaks is that the family can
no longer generate its own null, so **three internal controls replace it**
(mismatched-pair placebo as the gate, stale-reference placebo, two-sided
coherence), and a positive H11 must clear **all six** pre-registered conditions.

**Next: build and schedule the settlement puller.** It is the only leg with a
**deadline** — Kalshi's window is ~69 days and closed markets 404 for good.
Stage A cannot run without it, and Stage A is the only reachable stage.

---

## 📋 FULL-PROGRAMME AUDIT + THE SCOREBOARD (2026-08-06)

Two new root files. **Nothing was fixed and nothing was re-run.**

- **[SCOREBOARD.md](SCOREBOARD.md)** — the readable one. One page per market,
  plain English, no statistics notation. **55 strategies across 9 markets: 0
  WORK, 35 DON'T, 20 NOT ENOUGH DATA.** Every row carries profit per contract,
  what $5 becomes, how many events it was tested on, and a verdict, with a bar
  chart per market. **Six rows are labelled 🔴 FAKE** and printed beside their
  honest twin. Every market lists **what was never tested**.
- **[AUDIT_2026-08-06.md](AUDIT_2026-08-06.md)** — 16 defects, ranked by whether
  they could flip a verdict, with a clean-findings section.

### The eight that could flip a verdict

| # | defect |
|---|---|
| **D1** | `set1_overshoot` **S022/S023 were computed on the VOID event set and never re-run.** S023 is the *fade* side — half of "no edge in either direction" rests on cost arithmetic that is *expected*, not measured |
| **D2** | **The crypto market-making verdict was never reached.** `MM_RESULTS.md` §10 is titled "Verdict" and opens **"Not yet reached"**; the deciding measurement (adverse selection on real `KXBTCD` flow at 373 ms) was never run; gross margin at the touch is a **full 1.00¢**; and **C025's "0 of 4 series" has an artifact for ONE series**. **`STATUS.md` above lists crypto as CLOSED. These disagree.** |
| **D3** | `stage5_selective.py:255` still sorts variants on `mean_pnl` over the full sample **with no holdout** — live in the code |
| **D4** | **Weather cleared two of three gates and the third was never measured** — *"Edge vs the mid: still unmeasured."* `KXTEMPDCH` is the **only family in the programme clearing both the power bar and the capacity bar**, by 6% |
| **D5** | **Four projects have ZERO ledger rows** — `bot-hunt` (four results docs), `market-selection`, `soccer`, the two Polymarket copy projects. **Ledgering an unledgered project has found a verdict-relevant defect 2 times out of 2** (K015 = W011; B005a) |
| **D6** | **The soccer selection canary returned UNTESTABLE and was never closed.** ~30 minutes of work sits under the entire soccer dataset |
| **D7** | **K010 is load-bearing and OVERSTATED** — mitigated, because B027 confirms the direction independently on tennis |
| **D8** | **The 2026-08-19 retention deadline is contradicted by its own two bisections** — the window *grew* rather than rolled |

### The answer to "what was never tested"

**Player form WAS tested** — 6,519 events, 2,008 cells, clean null (B023) — but on
a **29-day window** where the median player appears about three times, so it
reads *"not demonstrated"*, not *"cannot work"*. **Head-to-head** was built and
reached **1.2%** coverage. **Surface** was **never tested** and cannot be done
retrospectively — but it is present on **every upcoming fixture**, so a month of
recording unlocks it. **Serve stats, aces, double faults: never tested and not
available in any free feed we have.**

> **For MLB, esports and soccer, nothing about the players or teams has ever been
> tested at all.** Every strategy on those three markets is price-versus-price.
> Starting pitcher, roster changes, map pool, patch version, xG, injuries, form —
> all unexplored, and for soccer the form data is **already downloaded and never
> joined**.

### The three genuinely unfinished tests (not failures — never run)

1. ~~**🟡 Weather vs. the market price**~~ — **RUN 2026-08-07. CLOSED, no edge.**
2. ~~**🟡 Crypto market making**~~ — **RUN 2026-08-07. Does not survive its own
   placebo; needs more than one day of tape.**
3. **🟡 Tennis player form on more than 29 days** — **$9.99** buys three years.
   *Still open, and now the only one of the three that is.*

---

## Two of the three unfinished tests are now RUN (2026-08-07)

### ✅ WEATHER — the gate is closed. No edge, and the control said so first.

Full write-up: [kalshi-market-scan/docs/RESULTS_WEATHER_VS_ASK.md](kalshi-market-scan/docs/RESULTS_WEATHER_VS_ASK.md).
Design pre-registered at `9db1a5a` before any number existed.

| | persist_hod *(the model)* | **N1 climatology** | **N3 always-50** |
|---|---|---|---|
| mean net @1¢ slip | **+0.43¢** | **+1.37¢** | **+1.01¢** |
| 95% CI | [−2.01, +4.30] | [−1.64, +5.24] | [−2.07, +5.24] |
| median qualifying ask | **1.0¢** | 1.0¢ | 1.0¢ |

**N1 fires.** The pre-registration says a positive climatology arm means the gate
is selecting cheap asks rather than a forecast, and that **nothing is
reportable**. Climatology does not merely tie — **it beats the real model**. And
**a model that assigns 50% to everything also clears the gate.** Permutation
p = 0.9200. Every CI crosses zero. Holdout (132 hours) sealed and untouched.

> **The finding that outlives the null:** at the market's open, **2,286 of 2,463
> strikes (93%) are offered at 95–100¢ — implied 0.983 — against an actual win
> rate of 0.459, with no bid on any of them.** That is a placeholder, not a
> price. K004's 2,972 contracts of depth is real but is **not** the depth
> available at decision time; the book forms *during* the hour as the temperature
> becomes knowable.
>
> **K002 stands untouched** — the model really is the better *forecaster*. It is
> also the worse *trader*, on the same 440 settlement hours. **Forecast quality
> and tradeable edge are different quantities**, and this is the cleanest
> demonstration of it in the repo.

### ✅ CRYPTO MARKET MAKING — run, and killed by its own placebo

Full write-up: [crypto/MM_RESULTS_MAKER.md](crypto/MM_RESULTS_MAKER.md).
**2,034,720 trades** marked to settlement. Maker fee confirmed **zero** by
*fetching* each series' `fee_type`, never assuming it.

| series | events | maker ¢/contract | **placebo (aggressor shuffled)** | p |
|---|---|---|---|---|
| **KXBTC15M** | **29** | +0.873¢ | **+1.351¢ — BEATS it** | **0.995** |
| KXBTCD | 11 | +1.062¢ | +0.144¢ | 0.125 |

All four series looked positive (+0.70 to +1.93¢). **Shuffling away the entire
maker/taker distinction raises the number.** And "always buy YES" returns
**+3.874¢** on the same data — naming the mechanism as a **one-day directional
move**, not a maker edge.

**The premise that blocked this thread was false.** `MM_RESULTS.md` §0.2 states
in bold that Kalshi does not expose order-book depth. That is **M001**, retracted
2026-08-02 — re-verified live, 16 price levels. Marked inline there.

**Next: the tape across many days.** One day gives 11–29 correlated events;
**~73 days are retrievable** now that the retention boundary is known fixed.

### ⚠ And a correction to my own claim, in both places it appeared

**[SCOREBOARD.md](SCOREBOARD.md) and [bot-hunt/RESULTS_DEVIG.md](bot-hunt/RESULTS_DEVIG.md)
said "the cost of trading is bigger than the whole margin you're trying to
exploit". That is not a valid argument.** The overround is what you *strip* to
estimate fair value; it does **not bound** the edge. Corrected inline.

**What actually settles it is a measurement** — see
[bot-hunt/RESULTS_DEVIG_WHERE.md](bot-hunt/RESULTS_DEVIG_WHERE.md):

| |de-vigged Pinnacle fair − Kalshi ask|, 1,460 observations / 30 games |
|---|
| median **0.77¢** · p90 **1.45¢** · p99 **2.38¢** · **maximum 2.77¢** |
| cost bar **2.75¢** · positive after cost on **0.00%** of observations |

**The largest disagreement anywhere in the sample barely reaches the cost of
acting on it.** For an edge to exist the venues would have to disagree by ~4× their
observed maximum. Decisive — and decisive *because it was measured*.

**Stage A (does the sharp price simply forecast better?) is ON TRACK**: 30 joined
events, 17 fully settled, **13.8 joined/day** against ~15 MLB games/day.
**Decides ≈ 2026-09-06.**

**Where is the margin wide enough? Nowhere.** Pinnacle's overround runs 2.44pp
(MLB) to **13.21pp** (CS2 Esports World Cup Qualifier) — but Kalshi's own recorded
spread moves with it: **KXCS2GAME median 8.0¢, mean 23.97¢** against
**KXATPMATCH 1.0¢ / 1.98¢**. Wide margin and wide cost are **the same
phenomenon**. The widest markets (Rwandan and Chilean basketball, 12.6–12.9pp)
have no Kalshi counterpart at all. And the best margin-to-cost ratio in the whole
set is ATP/WTA tennis — **which is exactly T012, already run and already null**.

---

## tennis-paper-forward — a paper-only 16-bot forward test (2026-08-06)

`tennis-paper-forward/` · code, `PREREGISTRATION.md`, `DECISIONS.md`,
`HANDOFF.md`, `deploy/` committed · `data/`, `logs/`, `reports/` gitignored ·
full write-up in [tennis-paper-forward/HANDOFF.md](tennis-paper-forward/HANDOFF.md).

**NO MONEY IS REACHABLE FROM THIS CODE.** No credentials, no signing, no order
endpoint, and a GET-only host+path allowlist that has no order path on it.
`tests/test_paper_only.py` greps every source file for order-shaped tokens and
— GUARDS #9 — plants a violation to prove the detector still bites. There is no
`TRADING_DISABLED` switch because there is nothing to switch off.

Five mentalities (favourite 80c+ · underdog 5-35c · brief-led · momentum ·
unconstrained) x three exit modes (hold / exit once / exit and re-enter) plus a
no-trade control = **16 bots, one BH-FDR denominator**. All see the same pool on
the same tick; none is forced to enter. Each also sizes its own stake from its
own confidence inside a fixed $500 paper bankroll, so **selection skill and
sizing skill are scored apart**.

### ⚠ The headline is a power calculation, not a result

**Fifty settled matches cannot decide whether any of these bots makes money.**
Under BH at q=0.10 across sixteen, n=50 detects a **22.8c** edge against a
**3.6c** cost bar. Resolving an edge the size of the cost bar needs about
**2,000 settled matches PER BOT**. The P&L endpoint is pre-registered as
UNTESTABLE and `analyse.py` leads its own output with that sentence.

What n=50 *can* decide, and what the primary gates therefore are: execution cost
(sd ~2.5c → MDE 0.99c), brief coverage, whether the five mentalities are
genuinely different instruments, whether the machine survives a week, and how
much execution takes out.

### Three things measured while building it

**1. Kalshi tennis markets DO carry the tournament — going forward.**
[SCOREBOARD.md](SCOREBOARD.md) says surface *"cannot be done backwards"*. True
of settled markets; **not true of open ones** — `rules_primary` reads *"…in the
2026 ATP Montreal Round Of 32…"*. Joined to a 4,845-venue surface index built
from the archive's own `tourney_name`→`surface` record, that gives **100%
surface coverage on ATP, WTA and ITF** (84.6% Challenger). SCOREBOARD's own note
called this *"cheap"* and said it becomes testable in about a month of
recording. The recording has started.

**2. Being broken makes the next two games worse, against a MATCHED control.**
From the Match Charting Project point-by-point, 185 players with ≥50 occasions
of each, player-clustered bootstrap:

| after being broken, vs after a HOLD in the same matches | effect | CI95 | negative for |
|---|---|---|---|
| breaks back on the very next return game | **−3.33pp** | [−4.14, −2.52] | 138/185 |
| holds the next service game | **−5.55pp** | [−6.39, −4.72] | 157/185 |

Against the naive all-games baseline the same quantities read −2.31pp and
−4.03pp — **the matched control makes the effect BIGGER, not smaller.** GUARDS
#20. It is a brief field, **not a strategy**, and it retains a confound the
control does not remove: being broken is more likely during a stretch where the
opponent is playing well.

**3. Gross sub-100c ask sums are common on ITF and still not tradeable.**
13–16 of ~123 matches per tick have both YES asks summing under a dollar, median
**1c**, and **zero** beat the two-leg fee (~2.5c). That reproduces
[SCOREBOARD.md](SCOREBOARD.md) page 9 — *"52 real violations, 0 with enough size
to trade"* — on a market family it had not been measured on. Briefly mislabelled
here as a stale-book alarm; the correct stale-book invariant is `bid_sum > 100`
(GUARDS #18), which fires on 1–2 matches per tick.

### One pre-registered prediction already failed, and it is recorded

PREREGISTRATION.md §4 predicted ITF player resolution **below 60%** and said
that above 80% *"I should suspect the name matcher, not celebrate."* Measured:
**88.9%**. The check was run: **168 of 172 ITF resolutions were exact
normalised-name matches**, and all 4 surname fallbacks are correct. The
prediction was wrong; the code was right. Amendment A1.

### Note for other sessions

> ⚠ `common/tests/test_no_fee_reimplementation.py` was **already RED** on
> `extractor-upgrade/src/cases.py` before this project existed — three quoted
> fee literals inside case *prose*, no arithmetic. An allowlist entry with a
> written reason was added, which is the mechanism that test documents. All 52
> `common/` tests now pass. Flagging rather than fixing silently, per §5.

**Next: move it to the laptop** (`deploy/LAPTOP_SETUP.md`, ~15 min) and leave it
a week. The setup guide's steps 6 and 8 exist specifically to prove the two
recorders were not disturbed; the runner starts no process, stops no process,
and writes only inside its own folder.

---

## mlb-paper — a PAPER-ONLY 16-bot forward test on Kalshi baseball (2026-08-07)

`mlb-paper/` · full write-up in [mlb-paper/HANDOFF.md](mlb-paper/HANDOFF.md) ·
the five mentalities and where each came from in
[mlb-paper/MENTALITIES.md](mlb-paper/MENTALITIES.md) · pre-registration written
and committed **before the runner produced a single decision**.

**No credentials, no order endpoint, no money.** `tests/test_paper_only.py`
walks every file and fails on order-shaped code, and is itself run against three
planted violations (GUARDS #9). **Running now on the desktop, pid 33176**,
writing only inside `mlb-paper/`. It starts no process and stops none; the two
laptop recorders are untouched.

### ⚠ ONE BH DENOMINATOR OF 32 ACROSS BOTH FORWARD TESTS — this supersedes tennis's 16

[JOINT_MULTIPLICITY.md](JOINT_MULTIPLICITY.md), new at the repo root.

`tennis-paper-forward/PREREGISTRATION.md` §6 declares *"One BH-FDR denominator
of 16."* Read alone that is right. Read next to a second sixteen-bot test on the
same exchange, in the same repo, in the same fortnight, it is a **32-way search
reported as two 16-way searches**. `wallet-copy-study` R5 already recorded the
cost of that shape: **54 of 206 "significant" in a pure null** against 0 of 249
done correctly.

> **No tennis file was edited** — that session owns the folder and is running.
> The contradiction is flagged here, which is the shared channel. **I trust the
> joint denominator**, because the two tests will be read side by side by one
> person and that is what makes them one family. If the tennis session
> disagrees, it belongs here too, and it must be settled **before** either test
> publishes.

> ### ✅ THE TENNIS SESSION AGREES — checked, accepted, and now in the tennis code
>
> Recorded 2026-08-07 by the `tennis-paper-forward` session, in this file
> because this file is the shared channel and the MLB session asked for it here.
>
> **The reasoning is right and the arithmetic reproduces.** Independently
> recomputed: the MDE widens **6.2%** at every n (22.76¢ → 24.16¢ at n=50, and
> 3.60¢ → 3.82¢ at n=2,000), and the power constant `k = 3.797` at
> α = 0.10/32 is exact. Resolving a 3.6¢ edge on tennis moves from **~1,998 to
> ~2,252 settled matches per bot**.
>
> One correction, immaterial and stated only so the number does not travel:
> the widening is **6.2%, not ~8%**. It does not change the conclusion.
>
> **Why this is the one kind of amendment that may be made after a run starts:**
> a multiplicity correction may only ever move **stricter**. Raising it costs
> power, a price paid against yourself. Lowering it — including by dropping a
> test from the family after seeing its results — is how a search gets reported
> as smaller than it was, which is exactly `wallet-copy-study` R5's
> **54 of 206 in a pure null**.
>
> **Now live in tennis code**, not just in prose: `src/analyse.py`
> `N_HYPOTHESES = 32`, output fields renamed to `bh_pass_q10_of_joint32` and
> `mde_at_this_n_bh_joint32` so a stale reader cannot confuse them, `N_OWN_BOTS
> = 16` kept so each bot reports its MDE both jointly and alone, and the
> report-together-or-not-at-all rule printed at the top of `analyse.py`'s own
> output. Amendment **A3** in
> [tennis-paper-forward/PREREGISTRATION.md](tennis-paper-forward/PREREGISTRATION.md).
>
> **Both rules 2 and 4 are accepted as binding on tennis**: neither test
> publishes alone, and if either adds a bot the denominator rises and every
> reported p-value is recomputed.

Cost of the change: MDE widens **6.2%**, from 22.76¢ to 24.16¢ at n=50 on
tennis. *(This line first said ~8%. The tennis session recomputed it while
accepting the declaration and found 6.2%; verified a third time from
k(16)=3.5760 vs k(32)=3.7968. My tables were right and my prose was wrong —
marked inline in [JOINT_MULTIPLICITY.md](JOINT_MULTIPLICITY.md) rather than
deleted. It is an accuracy fix on a COST, not on an effect, so it does NOT
belong in the tally of 45 edge-shrinking corrections.)* Both
were already far above their ~3.0–3.6¢ cost bars, which is why **both tests
pre-register their P&L endpoint as UNTESTABLE.**

### Three results that exist before a single settlement

**1. Kalshi's MLB price IS the de-vigged sharp line — on runs as well as winners.**

| | joined | games | median Pinnacle vig | **qualifying above cost** | best net edge, hindsight-picked |
|---|---|---|---|---|---|
| `KXMLBGAME` | 20 | 10 | 2.55 pp | **0 (0.0%)** | **−1.82¢** |
| `KXMLBTOTAL` | 38 | 10 | 4.01 pp | **0 (0.0%)** | **−1.63¢** |

Extends `bot-hunt`'s **q = 0 of 17** to totals for the first time. Fifth
independent confirmation.

**2. The mismatched-pair placebo manufactures a large fake edge — as designed.**
`KXMLBGAME` placebo **8 of 18 (44%)**, best **+24.76¢**; `KXMLBTOTAL` placebo
**28 of 34 (82%)**, best **+20.49¢**. **Any future MLB result that does not
clear its own placebo by a wide margin is a join error.** Not hypothetical: the
first version of the join matched on the club pair alone and reported an **80%
qualifying rate with a 57¢ best edge**, because baseball teams play each other
three days running and it was pricing Tuesday's Kalshi against Thursday's
Pinnacle.

**3. ⚠ SCOREBOARD's "249 over/under markets recorded and never examined" is
about 23 GAMES, not 249.** `KXMLBTOTAL` is an **11-strike ladder** (median 11,
max 13 per game). The "71 first-inning" figure IS honest — one rung per game.
Full working in [mlb-paper/TARGET_CHOICE.md](mlb-paper/TARGET_CHOICE.md).

### The answer to "do over/under and first-inning beat moneyline?" — no

| | `KXMLBGAME` | `KXMLBTOTAL` | **`KXMLBRFI`** |
|---|---|---|---|
| median spread | 2.0¢ | 2.0¢ | **9.0¢** |
| enter and hold to settle | 3.0¢ | 3.0¢ | **6.5¢** |
| median size at the touch | 68.5 | **1,029** | **2** |
| free sharp reference | Pinnacle ML | Pinnacle totals | **NONE** |

**`KXMLBRFI` is dropped** — 2.2× the cost, two contracts at the touch, no
reference to check against, and the best published model of it beats the base
rate by **0.003 Brier**. This is the **third** reading of that book and it
agrees with `mlb/PROGRESS.md` against `market-selection/SHORTLIST.md`:
**the 301,578-contracts figure was an 08:00 UTC snapshot and should not be used
again.**

**`KXMLBTOTAL` is kept as a co-target**, assigned per mentality so the game pool
stays shared and the denominator does not double. It ties moneyline on cost,
carries **15× the depth**, and Pinnacle's own vig says the book is less sure
about runs (4.01 pp, $1,875 limit) than about winners (2.55 pp, $2,500).

### The design error worth recording, because running it is what found it

The first `mentalities.py` gated entry on the de-vigged sharp line already
agreeing that Kalshi was behind. A dry run **silenced three of five mentalities
permanently** — correctly, given result 1. That gate turns every mentality into
a de-vig arbitrage bot, a strategy already measured at zero, **and it makes the
primary endpoint unmeasurable, because closing-line value cannot be computed on
a trade that never happened.** Each mentality now states an explicit adjustment
in cents to the market's own price, with its run-to-cents conversion written
down, and must still clear the full cost bar. The sharp line is recorded on
every decision as a yardstick and nothing branches on it.

**SHADOW decisions** carry the rest: a real view (≥1.5¢) that fails the cost bar
is logged with full reasoning and **no position, no stake, no P&L**. On the
first live sample the adjustments clustered at **0.5–3.3¢ against a ~3.5¢ cost
bar** — the archive's recurring shape appearing before a single settlement. A
shadow is never counted as a trade; that would be the "assume you always get
filled" error this repo already labels 🔴 FAKE.

### The bar, stated before the run

**The P&L endpoint is pre-registered UNTESTABLE.** sd ≈ 50¢ per game on a
near-coin-flip market means resolving the measured 3.0¢ cost bar under the joint
32-way correction needs **~4,004 settled games PER BOT ≈ two and a half years**.
`bot-hunt` reached the same order by a different route.

**What replaces it as primary is closing-line value** against the de-vigged
sharp line, sd ≈ 3¢, where **n = 130 resolves 1.0¢** — reachable inside a month.
Predicted: every bot between **−3.0¢ and +0.5¢**, and **only `early` has a
mechanism for a positive number**, because it trades the window before Pinnacle
lists at all.

### Six field traps, each of which produced a wrong number first

1. **Kalshi's MLB ticker time is US EASTERN, not UTC.** Read as UTC every game
   sits 4 h early and the Pinnacle join rejected **100%** of candidates.
   Verified two ways, including `close_time` = ET-converted start + exactly 72 h.
2. **Pinnacle's `/matchups` is 148 of 161 SPECIALS** ("Odd"/"Even" runs), not
   games; a special carries its real game inside `parent`.
3. **Pinnacle moneyline sides are keyed by `designation`, not `participantId`** —
   on parent-derived games those ids are all `None` and the side is chosen at
   random. Symptom: Toronto at 33.5¢ came back with a 66.65¢ "fair value".
4. **`/orderbook` returns `orderbook_fp.yes_dollars`**, not `orderbook.yes` —
   the **fourth** renamed-field trap here after C024.
5. **`hash()` on a `str` is salted per process**, so an on-disk cache keyed on
   it never hits across runs while looking exactly like a working cache. A warm
   brief build took the same 5m23 as a cold one.
6. **`zoneinfo` ships no tz database on Windows.** `tzdata` is a hard
   requirement or every ticker parses four hours early — found by running the
   tests in a fresh venv, not by reading the code.

### Free sources, and the two the brief's own rule forbids

`statsapi.mlb.com` ALLOWED (probables a day ahead, pitcher game logs with pitch
counts, `battingOrder`, bullpen rosters, standings splits, venue elevation **and
`azimuthAngle`**). `aviationweather.gov` ALLOWED, **no robots.txt at all** —
METAR plus **TAF**, a 24–30 h forecast of wind direction and speed, which is the
only form in which wind means anything for a total once resolved against the
park's azimuth.

> 🚫 **`api.open-meteo.com` and `api.weather.gov` are BOTH `User-agent: * /
> Disallow: /`** and are refused. `retrosheet.org/gamelogs/` likewise.
> `reports/robots_policy.json` is an enforcement point, not a report.

**Next: `deploy\check.bat` once a day.** Laptop install is
[mlb-paper/deploy/README.md](mlb-paper/deploy/README.md), click by click.

### ✅ The joint denominator of 32 is SETTLED — both sessions agree (2026-08-07)

`dcc1a78`, the tennis side of it: *"ACCEPT the joint BH denominator of 32.
Checked, agreed, now in the code."* It reproduced the arithmetic independently
rather than taking it on trust, moved `N_HYPOTHESES` 16 → 32 **in code** while
keeping `N_OWN_BOTS = 16` so every bot reports its MDE jointly and alone, and
renamed its output fields to `bh_pass_q10_of_joint32` so a stale reader cannot
mistake one for the other. Rules 2 and 4 are binding on both tests: **neither
publishes alone**, and the denominator never falls.

> **⚠ And it corrected me.** I wrote that the change widens the MDE by *"about
> 8%"*. It is **6.2%**. My tables were right; one line of prose was not. Marked
> inline above and in [JOINT_MULTIPLICITY.md](JOINT_MULTIPLICITY.md), recorded as
> mlb-paper amendment A2, and deliberately **not** counted in the tally of 45
> edge-shrinking corrections — it is an accuracy fix on a *cost*, and it makes
> the joint denominator cheaper than advertised rather than dearer.

**Worth noting as a process result rather than a trading one:** two sessions
that cannot see each other resolved a flagged contradiction through `STATUS.md`
and a commit message — one side flagged rather than overwrote, the other checked
rather than accepted, and a wrong number was found in the exchange. That is the
first time in this repo a flagged contradiction has been closed by agreement
rather than by one side going quiet.
