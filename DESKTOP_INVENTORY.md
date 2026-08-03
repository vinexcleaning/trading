# DESKTOP_INVENTORY.md

Machine: `C:\Users\vinig` (desktop). Inventory taken **2026-08-03**, read-only.
Nothing was started, stopped, moved, edited or traded during Phase 1.

Companion documents: repo `STATUS.md` / `LEDGER.md` / `GUARDS.md` (laptop-authored,
read from GitHub), and the on-disk audit at `C:\Users\vinig\kalshi\audit\` (2026-07-30).

---

## 1. HEADLINE — what is not backed up

**Five directories exist on this machine and nowhere else.** No git remote, or no
repository at all. Together they hold **~8.4 GB of data that cannot be re-pulled**.

| Rank | Path | Size | Git | Why it matters |
|---|---|---|---|---|
| **1** | `C:\Users\vinig\tennis copy trade` | **7.0 GB** | **none** | `best.db` 3.67 GB (71,497 positions, 2.04M price obs), `tape_scan.db` 372 MB (6,937 matches, 1.77M trades, 42,652 wallets), `real.db` 740 MB. ~2.5 h to rebuild the tape the fast way, ~200 h the per-wallet way. **Also holds `data/follow-list.json`, the only ungameable forward test anyone has set up.** |
| **2** | `C:\Users\vinig\kalshi markets` | **853 MB** | repo, 21 commits, **no remote** | Contains the **only live Kalshi order-book recording on this machine** (07:30→17:32 UTC, 30 Jul, ~2.03M trades). Kalshi publishes no historical order-book endpoint at any price. 21 commits of history exist only in `.git` here. |
| **3** | `C:\Users\vinig\kalshi` | **453 MB** | **none** | The live money bot. Holds `bot_state.json` (5 open positions with live Kalshi order ids), the signing key, and the 14,162-market backtest inputs. **No version control at all on the code that places real orders.** |
| **4** | `…\Codex\2026-07-23\files-mentioned-by-the-user-master-2` (PTIS) | **561 MB** | `.git` present but **empty — 0 commits** | `ptis.sqlite3` 267 MB, cohort rows Mar 9 – Jul 24 2026, 1,467 public trades. |
| **5** | `C:\Users\vinig\OneDrive\Desktop\kalshi` | 1.5 MB | none | Only copy of the **Discord trading-server export** (176 messages, 174 owner calls, 30 Jun → 29 Jul). OneDrive-synced, so technically replicated to a cloud folder — but it is not in any repo. |

Backed up, for contrast:

| Path | Git | State |
|---|---|---|
| `…\Codex\weather-market-bot` | `github.com/vinexcleaning/weather-market-bot`, 13 commits | **0 ahead / 0 behind `origin/main`** — fully pushed. Its 2.9 GB `data/` is gitignored and local-only, but the code is safe. |
| `C:\Users\vinig\Vinex-OS` | `github.com/vinexcleaning/Vinex-OS`, 109 commits | Pushed. **Out of scope** — business/life-planning, not trading. |

---

## 2. HEADLINE — what is frozen by a running process

**Nothing. Zero directories are frozen.**

- `Get-CimInstance Win32_Process` filtered on `python|pythonw|node|deno|bun|jupyter|conda|Rscript|julia`: **no matches.** The full 120-name process table contains no interpreter of any kind.
- No `.recorder.lock` anywhere on the machine (the only `.lock` files are Claude Code task locks and a Phasmophobia save).
- Startup folder contains only `desktop.ini`.
- No scheduled task matches `kalshi|tennis|bot|record|trade|crypto`.

**Consequence: every move in Phase 2 is safe from the open-handle failure mode.**
The two recorders named in the repo's `STATUS.md` (PIDs 17892 and 24756) are on the
**laptop** under `C:\Users\gianf\`, not here. Nothing on this machine must be left
in place to protect a writer.

The corollary is less comfortable: **this machine has recorded nothing since
17:32 UTC on 30 July.** The 8.5-hour book recording in `kalshi markets` is a
closed, finite asset, not a growing one.

---

## 3. HEADLINE — every DIVERGENT pair

Two pairs share a name or a purpose and have **different contents**. Neither may be
resolved by a folder-level copy in either direction.

### D-1. `C:\Users\vinig\kalshi` ↔ `C:\Users\vinig\OneDrive\Desktop\kalshi` — DIVERGENT

Same name, 6 files overlap by name, **4 of the 6 differ by hash.**

| File | Desktop | `~\kalshi` | Verdict |
|---|---|---|---|
| `kalshi_client.py` | 5.2 KB | 15.7 KB | **DIVERGENT** — 29 lines only on Desktop, 269 only in `~\kalshi` |
| `scanner.py` | 7.8 KB | 17.1 KB | **DIVERGENT** — 20 / 214 |
| `tennis_engine.py` | 10.4 KB | 19.9 KB | **DIVERGENT** — 12 / 170 |
| `SETUP.md` | 3.8 KB | 6.0 KB | **DIVERGENT** — 0 / 62 (clean superset) |
| `kalshi_private_key.pem` | 1.6 KB | 1.6 KB | IDENTICAL (SHA-256 match) — **and this is the live signing key, sitting in a cloud-synced folder** |
| `RICH0FFTENN1S … rot-trades […].json` | 1.5 MB | — | **Desktop-only. Unique. Not duplicated anywhere.** |

**Read:** the Desktop copy is a **26 Jul snapshot superseded by the 27–28 Jul rewrite**
in `~\kalshi`. The 12–29 "only on Desktop" lines per file are old code that was
rewritten, not work that was lost — but that judgement rests on a line diff, not a
semantic one, so the Desktop copy is **archived, never deleted**. The Discord export
is genuinely unique and must be preserved as a first-class artifact.

### D-2. `…\Codex\weather-market-bot` ↔ `…\2026-07-22\…untrusted\work\weather-market-bot-staging` — DIVERGENT-but-redundant

| | Main (P5) | Staging (P8) |
|---|---|---|
| files (excl. `.git`/`.venv`/`__pycache__`) | 4,270 | 56 |
| relative paths in common | 53 | 53 |
| **common paths differing in size** | **25** | |
| paths only in staging | **3 — all `.ruff_cache` entries** | |

**Read:** staging is an early skeleton. 25 shared files differ, so it is *not* a byte
subset — but every file that exists in staging also exists in main, and the only
staging-exclusive files are lint-cache blobs. Main is pushed to GitHub. Staging is
**fully redundant**; archive it.

### D-3. `C:\Users\vinig\kalshi` (desktop) ↔ `C:\Users\gianf\kalshi` (laptop) — DIVERGENT, cross-machine

Cannot be hashed from here. The repo's `STATUS.md` states the two share **zero files**:
desktop is the live in-play tennis bot, laptop is the Stage 0–5 research pipeline.
**This is the highest-consequence name collision in the programme** and is the reason
Phase 2 renames the desktop folder.

### Not divergent

| Pair | Class |
|---|---|
| `tennis copy trade` (P3) vs PTIS (P6) | **UNRELATED codebases, same research question.** Two full independent implementations of Polymarket copy-trade analysis, built four days apart, with no cross-reference in either direction. No file overlap. |
| `tennis copy trade/data/tape_scan.db` vs `kalshi markets` | **UNRELATED at file level.** `kalshi markets` Phase 6 *re-analyses* the tape but holds no copy of the db. Only one `tape_scan.db` exists on the machine. |
| `…master\outputs\polymarket-shadow-copy` (P7) vs PTIS (P6) | **SUBSET/superseded.** 31 files, 0.3 MB skeleton, subsumed by P6. |

---

## 4. Full directory inventory — identified by contents

Scope call: `Vinex-OS`, the Codex Vinex clones, and `2026-07-24\vinex-meta-ads-manager`
are **business/life-planning work, not trading**. Classified from listings and left
untouched, consistent with the instruction to ignore the Nexus-family work.

| ID | Path | What it actually is | Modified | Size | Files | Git | Open handles |
|---|---|---|---|---|---|---|---|
| **P1** | `C:\Users\vinig\kalshi` | **The live money bot.** Kalshi tennis in-play momentum trader (`gui.py`, `tennis_engine.py`, `kalshi_client.py`), free Sofascore score feed, tape recorder, paper bot, and a 14,162-market backtest with 115 MB of 1-min candles. **Dormant but armed** — `bot_state.json` holds 5 open positions with live Kalshi order ids and resting 95¢ take-profits from 28 Jul. | 30 Jul 18:17 | **453 MB** | 94 | **none** | none |
| **P2** | `C:\Users\vinig\kalshi markets` | **Exchange-wide Kalshi edge scan**, one session on 30 Jul. 116 hypotheses across 22 market families, tiered recorders, arb scanner, a correct `Decimal`-based `fees.py`, 21 commits. Verdict reached: **zero tradeable Kalshi edges**; only `KXTEMPDCH` weather survives as an unmeasured question. | 30 Jul 17:52 | **853 MB** | 19,936 | repo, 21 commits, clean, **no remote** | none |
| **P3** | `C:\Users\vinig\tennis copy trade` | **Polymarket tennis copy-trade analytics** — FastAPI backend + React dashboard + 13 analysis scripts. Ingestion, tape sweep, wallet screening, delay-decay copyability model, cluster detection, paper trading, 293 tests. Thesis closed (42,652 wallets, 0 discoveries at FDR 5%/10%) but **one frozen 4-wallet forward list awaits scoring**. | 30 Jul 10:01 | **7.0 GB** | 14,571 | **none** | none |
| **P4** | `C:\Users\vinig\OneDrive\Desktop\kalshi` | **Stale 26 Jul snapshot of P1's four core files, plus the unique Discord export.** Not a project — a partial copy that also happens to hold the only trading-server message corpus. | 30 Jul 11:30 | 1.5 MB | 6 | none | none |
| **P5** | `…\Documents\Codex\weather-market-bot` | **Kalshi weather/temperature bot.** NDFD forecast archive (Jan 9 – May 22 2026), probability model, backtests, forward paper collector. **Closed 23 Jul**: model Brier 0.2048 vs market-ask 0.1690 — the market won. Its final 20% test split is **sealed and must stay sealed**. | 25 Jul 19:02 | 3.3 GB | 16,234 | repo, 13 commits, clean, **pushed 0/0** | none |
| **P6** | `…\Codex\2026-07-23\files-mentioned-by-the-user-master-2` | **PTIS — Polymarket Trader Intelligence System.** Independent copy-trade discovery, execution sim, consensus backtest. **Closed 24 Jul**: leaderboard-consensus copying rejected, the control lost $40.17 on $40. | 24 Jul | 561 MB | 980 | `.git` present, **0 commits** | none |
| **P7** | `…\Codex\2026-07-23\files-mentioned-by-the-user-master\outputs\polymarket-shadow-copy` | Early Polymarket shadow-copy skeleton, **superseded by P6**. | 23 Jul | 0.3 MB | 31 | `.git`, 0 commits | none |
| **P8** | `…\Codex\2026-07-22\…untrusted\work\weather-market-bot-staging` | **Staging twin of P5**, redundant (see D-2). | 23 Jul | 151 MB | 5,906 | `.git`, 0 commits | none |
| — | `C:\Users\vinig\Downloads\DiscordChatExporter.win-x64` | Supporting tool that produced P4's export. Not a project. | 30 Jul | 48 MB | — | — | none |
| — | `C:\Users\vinig\Vinex-OS` + `Codex\2026-07-06\…\Vinex-OS` + `Codex\2026-07-24\vinex-meta-ads-manager` | **Out of scope** — business/life-planning. Pushed to GitHub. Not touched. | — | ~21 MB | 960 | pushed | none |
| — | `C:\Users\vinig\Documents\Codex\.git` | **Empty directory.** `git` reports "not a repository". Harmless artifact. | — | 0 | 0 | — | — |
| — | `C:\Users\vinig\.MUMUNX` | Empty. | — | 0 | 0 | — | — |

Loose trading-related files outside any project:

| Path | What |
|---|---|
| `Downloads\audit_prompt.md` | byte-identical twin of `kalshi\audit_prompt.md` — **IDENTICAL, redundant** |
| `Downloads\KXBTC15M_overnight_prompt.md`, `kalshi_edge_scan_overnight_prompt_v2.md` (+ ` (1)` dup), `kalshi-tennis-bot-v3-spec.md` | Session prompts. **`kalshi-tennis-bot-v3-spec.md` is the spec the live bot implements** and exists nowhere else. |
| `Downloads\SETUP_1.md` | Older copy of `kalshi\SETUP.md`. Placeholders only. |

---

## 5. Duplicate classification summary

| Pair | Class | Evidence |
|---|---|---|
| P4 → P1 | **DIVERGENT** (4 of 6 files differ by SHA-256; P1 newer in every case) | hashes + line diffs, §3 D-1 |
| P4 Discord export | **UNIQUE** | no other copy on the machine |
| P8 → P5 | **DIVERGENT but redundant** (25 of 53 shared paths differ; 3 staging-only files are all lint cache) | path+size comparison, §3 D-2 |
| P7 → P6 | **SUBSET / superseded** | 31 files vs 980, same problem domain |
| P3 ↔ P6 | **UNRELATED** | zero file overlap, independent implementations |
| `Downloads\audit_prompt.md` → `kalshi\audit_prompt.md` | **IDENTICAL** | same size, same mtime |
| `Downloads\kalshi_edge_scan_overnight_prompt_v2 (1).md` → `…_v2.md` | **IDENTICAL** | browser re-download |
| P1 (desktop) ↔ laptop `kalshi` | **DIVERGENT, cross-machine, zero shared files** | repo `STATUS.md` |

**Nine independent implementations of the Kalshi fee formula** exist across five of
these codebases; only two guard the `175.00000000000003` float-dust bug, and the two
in the live money path (`tennis_engine.py:240`, `paper_bot.py:85`) are **not** among
them. This is code duplication, not file duplication, so it is out of scope for a
folder move — but it is the most consequential redundancy on the machine.

---

## 6. Credentials sweep

Paths only. No secret values were read, printed or copied.

### Real credentials — must never be committed

| Path | What | Note |
|---|---|---|
| `C:\Users\vinig\kalshi\kalshi_private_key.pem` | **Live Kalshi RSA signing key.** Places real orders on the real account. Not a demo key. | Must be gitignored before any commit |
| `C:\Users\vinig\OneDrive\Desktop\kalshi\kalshi_private_key.pem` | **Byte-identical copy of the above, in a OneDrive-synced folder.** | ⚠ **Flagged.** A live order-placing key is being replicated to Microsoft's cloud. Not something I will move or delete unilaterally — see §8. |

### Placeholders only — verified, safe

| Path | Match | Actual value |
|---|---|---|
| `kalshi\SETUP.md:44,157` | `KALSHI_KEY_ID=`, `APIFY_TOKEN=` | `paste-your-key-id-here`, `your-apify-token` |
| `Downloads\SETUP_1.md:44` | `KALSHI_KEY_ID=` | `paste-your-key-id-here` |
| `tennis copy trade\.env.example` | env template | placeholders |
| `Codex\weather-market-bot\.env.example` and its staging twin | env template | placeholders |

No `.env` (as opposed to `.env.example`), no `.pem` other than the two above, no
`.p12`/`.pfx`/`.key`/`.crt`, and **no match anywhere in the trading tree** for
`sk-ant-*`, `sk-*`, `ghp_*`, `github_pat_*`, `apify_api_*`, `AKIA*`, `xox[baprs]-*`,
or JWT-shaped strings.

### Out of scope, reported for completeness

`C:\Users\vinig\.clasprc.json` (Google Apps Script OAuth) and
`C:\Users\vinig\.lunarclient\settings\game\accounts.json` (+ backup) contain
credential-shaped strings. Neither is trading work; neither goes near the repo.

`C:\Users\vinig\.claude\projects\C--Users-vinig-kalshi\*.jsonl` — Claude Code chat
transcripts. They match on `API_KEY`-shaped text and are **excluded from the repo by
`.gitignore` as a category**, unreviewed, on the conservative assumption that a
transcript may quote something a placeholder scan would miss.

---

## 7. Proposed target structure

Repo `github.com/vinexcleaning/trading` → clone to `C:\Users\vinig\trading`.
Everything lands as **siblings**. Nothing nested inside anything else.

```
C:\Users\vinig\trading\                       (the clone; STATUS/LEDGER/GUARDS at root)
│
├─ DESKTOP_INVENTORY.md                       ← this document
│
├─ kalshi-tennis-bot\                         ← MOVED from C:\Users\vinig\kalshi
│                                               RENAMED. "kalshi" collides with the
│                                               laptop's zero-overlap "kalshi".
│                                               data/, *.pem, *.jsonl, *.pkl,
│                                               *.parquet gitignored
│
├─ kalshi-market-scan\                        ← MOVED from C:\Users\vinig\kalshi markets
│                                               RENAMED (space in path + "kalshi"
│                                               prefix collision). Inner .git log
│                                               preserved, inner .git removed
│
├─ polymarket-tennis-copy\                    ← MOVED from C:\Users\vinig\tennis copy trade
│                                               RENAMED (space in path). 7 GB data/
│                                               gitignored, stays on disk
│
├─ ptis-polymarket\                           ← MOVED from Codex\2026-07-23\
│                                               files-mentioned-by-the-user-master-2
│                                               RENAMED (the name is meaningless).
│                                               Empty .git removed
│
├─ discord-trades-export\                     ← Discord JSON from OneDrive\Desktop\kalshi
│                                               NEW. The unique artifact, promoted out
│                                               of a stale snapshot folder
│
├─ prompts\                                   ← the four session prompts from Downloads,
│                                               incl. kalshi-tennis-bot-v3-spec.md
│
└─ _archive\                                  ← moved, never deleted
   ├─ desktop-kalshi-snapshot-26jul\          ← OneDrive\Desktop\kalshi minus the .pem
   ├─ weather-market-bot-staging\             ← P8, redundant vs pushed P5
   ├─ polymarket-shadow-copy\                 ← P7, superseded by P6
   ├─ duplicate-prompts\                      ← the two byte-identical Downloads dupes
   └─ GIT_LOG_PRE_CONSOLIDATION.txt           ← preserved logs of every removed inner .git
```

**Stays where it is:**

| Path | Why |
|---|---|
| `…\Codex\weather-market-bot` | Already a pushed repo with its own remote. Moving it in would either nest a `.git` or destroy 13 commits of independent history for no gain. **Recorded in STATUS.md instead.** |
| `Vinex-OS`, the Codex Vinex clones, `vinex-meta-ads-manager` | Out of scope. |
| `Downloads\DiscordChatExporter.win-x64` | A tool, not work product. Re-downloadable. |
| The `.pem` files | **Not moved by me.** See §8. |

---

## 8. Which moves are safe, and which are not

**Safe now — nothing is frozen, so all of these proceed:**

| Move | Risk |
|---|---|
| `kalshi` → `trading\kalshi-tennis-bot` | Low. No process, no handle. `bot_state.json` moves with it; the bot is not running to be confused by the new path. |
| `kalshi markets` → `trading\kalshi-market-scan` | Low. Clean tree, 21 commits preserved to a log file first. |
| `tennis copy trade` → `trading\polymarket-tennis-copy` | Low, but **7 GB across 14,571 files** — verify count and byte total after. |
| PTIS → `trading\ptis-polymarket` | Low. Empty `.git`, nothing to preserve. |
| Discord export → `trading\discord-trades-export` | Low. Copy-then-verify, since it is the only copy. |
| P7, P8, Desktop snapshot, duplicate prompts → `_archive\` | Low. Move, not delete. |

**Must wait / must not happen:**

| Item | Why |
|---|---|
| **`kalshi_private_key.pem` — both copies** | I will **not** move, copy, delete or commit a live order-signing key. It is gitignored so it can never enter the public repo, and it is left byte-for-byte where the bot expects it. **The OneDrive copy is a real exposure and removing it is your call, not mine** — deleting it could also break the Desktop snapshot's ability to authenticate if you ever fall back to it. Recommendation: rotate the key on kalshi.com, then delete both copies of the old one. |
| **`bot_state.json`** | Moves with P1, untouched. **5 open positions with live Kalshi order ids.** The bot adopts positions from this file; editing or losing it would cause fresh stops to be set on positions that may no longer exist. Confirm on kalshi.com whether those 5 and their resting 95¢ sells resolved — that cannot be inferred from disk. |
| **`weather-market-bot`'s sealed 20% test split** | Not moved, not opened. The only untouched evaluation set in the corpus. |
| **`tennis copy trade\data\follow-list.json`** | Moves with P3. **Never regenerate it to "update" it.** Regenerating destroys the only ungameable test set up. |
| **`kalshi markets\data\raw_empty_books_prefix\`** | Moves with P2. Quarantined corrupt output, kept deliberately as evidence. Not a bug to clean up. |
| **Any recorded order book** | `kalshi markets\data\raw\kalshi_book_tier1/2`. Not re-pullable at any price. |

---

## 9. Corrections to documents already on disk

| Document | Says | Actually |
|---|---|---|
| `kalshi\audit\INVENTORY.md` | `kalshi markets` has **23 commits** | **21** (`git rev-list --count HEAD`) |
| `kalshi markets\MORNING_REPORT.md:925` | "Still running: Kalshi tiered recorder, external recorder, arb scanner" | **Stopped 17:32 UTC 30 Jul.** Nothing has run on this machine since. |
| `kalshi markets\data\gaps_report.md` | coverage ends 09:23 UTC | understates the dataset by **~8 hours** |
| repo `STATUS.md` "What is running, where" | lists only laptop PIDs | correct, and now explicitly: **the desktop contributes zero running processes** |
