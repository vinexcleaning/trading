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
| **youtube-signal** (new, moved in 08-02) | Phase 1 retrieval done. 470 videos gated, 263 pass, 439 transcripts cached, 43 channels expanded. **0 API units — no key needed.** Insider-vocabulary hypothesis **supported at 2.25×**; F1∩F2 Jaccard **0.037**. | **Define the on-topic boundary, then re-validate G3.** It disagrees with a careful human on ~1 video in 5, and the biggest cause is an undecided spec question, not a bug. Blocks Phase 2 scoring. |

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
| youtube-signal DB: 470 gated videos, 439 cached transcripts, 4,964 known videos | `trading\youtube-signal\data\signal.db` | ~25 MB | **Yes**, but slowly — ~35 min of paced fetching to rebuild. Gitignored. |

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
