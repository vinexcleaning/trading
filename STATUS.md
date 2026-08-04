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
| **Stage 0â€“5 player model** | **The model loses to the bookmakers**: +0.01922 Brier [+0.01438,+0.02417], n=2,645. Stage 4 gate failed. | None. Sackmann features end 2026-06-02 and the upstream repos are 404. |
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
| **youtube-signal** | **UNBLOCKED and productive. 33 videos read, $0.00 spent, 0 API units.** The old "buy $5 of API credit" blocker was wrong â€” transcripts are read in-session. Two corpora now: the broad one (746 videos, 370 PASS, 29 read) and a **targeted Kalshi/Polymarket one** (470 videos, 328 PASS, 4 read). See `youtube-signal/HANDOFF.md`. | **Read more of the targeted corpus.** `$env:SIGNAL_DB="kalshi_edge"` then `src/target_rank.py`. The broad corpus's retrieval test is still NOT DEMONSTRATED and is secondary to the practical hunt. |
| **signal-github** | **Working, not blocked.** 4,017 retrieved / 3,252 gated / **2,260 scored (69.5%) for ZERO core API calls** via codeload tarballs; 822 credibility; 4 read. Token in signal-github/.env -> 5,000/hr + code search (916 repos no other axis found). Callable as **/github-signal**. Stars settled: rho -0.007 p 0.73 at n=2,260 - the earlier +0.241 correction was itself the error. 	rust_me_bro 22.2% and **uncorrelated with substance**. Fees now primary-sourced on both venues (C1/C1a/C2). | **Read the KalshiEX Rulebook** - the member agreement is silent on automation and says the Rulebook governs, so it is the only open item that could change the venue answer. It defeats HTTP and a real browser. |

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
| Stage 0â€“5 caches, Sackmann, tennis-data | `trading\kalshi-tennis\data\` | **1.6 GB** | **No.** Sackmann upstream is 404; this runs on a frozen mirror ending 2026-06-02. **Only copy.** |
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

**35 videos read total. Cost $0.00. YouTube API quota 0 units.** Full detail in
[youtube-signal/HANDOFF.md](youtube-signal/HANDOFF.md).

Two corpora, deliberately separate (`$env:SIGNAL_DB` selects one):

| | broad | **targeted (`kalshi_edge`)** |
|---|---|---|
| queries | 28 | **27**, in build / strategy / data / validate |
| videos â†’ PASS | 746 â†’ 370 (50%) | **470 â†’ 328 (70%)** |
| within-family Jaccard | 0.69â€“0.76 | **0.86â€“0.92** |
| read | 29 | 6 |

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
| **deep-fetched and scored** | ~~105 (4.1%)~~ â†’ **2,260 = 69.5% of gated, for ZERO core API calls** |
| credibility metrics | **822** (was 40) |
| repos read in full | **4 this session**, loaded via `load_extraction.py` with zero rejections |
| **code search** | GitHub's own index: **1,141 hits, 916 found by no other axis** (Sourcegraph managed 15) |
| **F1âˆ©F2 Jaccard** | **0.032** â€” fourth measurement, with 0.033, 0.036 and YouTube's 0.037 |
| strict S â‰¥ 9 | 151 of 2,260 (**6.7%**) â€” 7.5% at n=40, 7.4% at n=862. Stable across a 56Ã— change in sample. |

### âš  Two coverage numbers exist in this repo and both are correct

`3a2f36a` says "2472 scored (96%)"; `19d5dba` says 2,260 at 69.5%. They measure
**two different databases on two machines** â€” `data/github.db` is gitignored, so
laptop and desktop each built their own corpus from shared code. Denominators
differ too: 2,472/2,562 there, 2,260/**3,252** here, because this machine's
retrieval included the code-search axis that added 916 repos the other corpus
does not have. **The machine with the lower percentage has the larger corpus.**
Always state which machine a coverage figure came from.

### Stars: settled, and the previous correction was the error

`rho(stars, S_strict) = âˆ’0.007, p = 0.73` **at n = 2,260**. The n=105 sample gave
+0.241 (p 0.013) and the project withdrew its "stars carry no information" claim
on it; the bump decays monotonically 105 â†’ 200 â†’ 400 â†’ 600 â†’ 862 â†’ 2,260. It was
a small-sample artifact. **The original claim stands; the withdrawal was wrong.**

What replaced it: `rho(tree_files, S_strict) = +0.593` â€” the score was 59%
explained by **file count**. `src/size_adjust.py` fits it out (rho â†’ 0.12).
Validated against an external fact: of 19 repos that provably model Kalshi's
maker fee correctly, the raw score put **0** in its top 25, the adjusted one **5**.

### Three axes, and none of them works alone

`trust_me_bro` fires on **182 of 822 (22.2%)** against 3 of 40 (7.5%) last
session â€” the sampling-bias warning, quantified. And it is **uncorrelated with
substance**: rho +0.029, p 0.41. Flagged repos score the same as clean ones.
`s_adj`'s own top pick had **1 commit** and claimed "Guaranteed profit".
`src/shortlist.py` combines substance, credibility and fee-correctness.

### What the corpus actually contains (`src/classify.py`, venue from imports)

| | |
|---|---|
| venue | polymarket 991 Â· **none 603** Â· kalshi 358 Â· both 284 |
| kind | live_trader 680 Â· market_maker 449 Â· data_collector 435 Â· backtester 221 Â· arbitrage 151 Â· copy_trader 103 |
| places real orders | 1,097 of 2,236 |
| Polymarket client | **v1-ARCHIVED 578 vs v2 121** â€” 4.8:1 toward the dead library |

**603 repos (27%) import neither venue.** They passed the README topic gate and
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
the venue answer; (2) finish the last 30% of coverage,
`python src/fetch_repo.py tree 1200`; (3) extend credibility past 822.

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



