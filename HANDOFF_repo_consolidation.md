# HANDOFF_repo_consolidation.md

Thread: **repo consolidation + LEDGER/GUARDS/STATUS**. Last updated 2026-08-03.

Named `HANDOFF_repo_consolidation.md`, not `HANDOFF.md`, because the root
`HANDOFF.md` belongs to a different session and must not be clobbered.

## What this thread did

Consolidated five scattered project directories into `C:\Users\gianf\trading`,
wrote `.gitignore` before the first commit, secret-scanned everything, and built
the three root inventory documents:

| File | Contents |
|---|---|
| `LEDGER.md` | 216 claims across four projects, 41 retractions, each with its artifact or `NONE` |
| `GUARDS.md` | 12 reusable canaries and controls + per-project coverage table |
| `STATUS.md` | threads alive/closed, what's running, data on disk, do-not-touch |
| `README.md` | entry point |

This thread is **complete**. Nothing is half-finished and nothing is blocked.

## Repo state

Working repo `C:\Users\gianf\trading`, remote
`https://github.com/vinexcleaning/trading` (public), branch `main`, clean and in
sync with `origin/main`.

**Nothing to commit from this thread** — every file it produced was committed and
pushed in the four commits below, all of which are on the remote:

```
4084c00  STATUS.md and README: threads, running processes, data locations, do-not-touch
251b4ac  GUARDS.md: 12 reusable canaries and controls, with per-project coverage
5e0b547  LEDGER.md: 212 claims across four projects, 41 retractions
692dc31  Consolidate five trading projects into one repo
```

`STATUS.md` has since been edited by another session (youtube-signal rows added).
That is expected and was left alone.

## ⚠️ THE OPEN PROBLEM — two directories still outside the repo

This is the thing a fresh session most needs to know.

| Directory | Size | Version control | Backed up? |
|---|---|---|---|
| `C:\Users\gianf\kalshi\set1_overshoot` | 555 MB | own `.git`, **41 commits, NO REMOTE** | ❌ **No** |
| `C:\Users\gianf\crypto` | 3.6 GB | **not a git repository at all** | ❌ **No** |

Both were deliberately left in place during consolidation because each held a
live recorder with open file handles, and moving a directory under an open handle
fails on Windows. **Only code copies went into the repo** — they live at
`trading/set1_overshoot/` and `trading/crypto/`.

**Both recorders have since stopped** (see below), so the original blocker is
gone. The directories can now be moved — but **do not move them without the
user's say-so**; they asked to be told, not to have it done.

The two in-repo copies have **diverged** from the originals. The originals are
authoritative. Edit those, not the copies.

## Processes

**This thread has none running and never started any.**

Two recorders that this thread protected have since stopped, not by this session:

| Was | Writes to | Last write | Status |
|---|---|---|---|
| `record_depth.py` (was PID 17892) | `kalshi\set1_overshoot\data\depth\<date>\<hh>\depth.jsonl` | **2026-08-03 09:59** local | stopped; log ends mid-cycle at "tracking 143 markets" |
| `record_15m_opens_v2.py` (was PID 24756) | `crypto\data\btc15m_opens\opens_all_<date>.jsonl` | **2026-08-02 21:19** | stopped; log ends clean at `rows=20112 rejected=0 errors=0` |

Any window they missed is **irrecoverable** — Kalshi publishes no historical
order-book endpoint.

Three unrelated python processes belong to **other sessions** and were not
touched: PID 21208 (`wallet-copy-study/src/spec_20_pull_missing.py`), PID 17996
and PID 17308 (`youtube-signal/src/fetch_repo.py tree 400`).

## Untracked files this thread created

None inside the repo. Everything it wrote is tracked and pushed.

Gitignored by design, and correct to be:

- `trading/_archive/kalshi-tennis-backup-DUPLICATE/` (296 KB) — verified
  **byte-identical** to `kalshi-tennis/src` + `reports`. Redundant, safe to delete.
- all `data/` directories — `wallet-copy-study/data` 12 GB,
  `kalshi-tennis/data` 1.6 GB.
- `**/.claude/settings.local.json` — machine-specific paths.
- `kalshi-chat-audit/max_convos/`, `pro_convos/` — exported chat transcripts,
  personal data, deliberately excluded from a public repo.

Outside the repo, in the session scratchpad and disposable:
`GIT_LOG_set1_overshoot.txt`, `GIT_LOG_wallet-copy-study.txt` — the redacted
copies of both are committed as `GIT_LOG_PRE_CONSOLIDATION.txt` inside each
project.

## Secret-scan status

Clean, and re-verified before the last push. No API keys, tokens, private keys,
or credential-shaped strings in any tracked file or anywhere in history. One
personal email (`vinigian2022@gmail.com`) appeared in the git-log exports this
thread generated and was redacted to `<redacted@local>` **before** the first
commit — it never entered a commit.

The code reads no authentication environment variables at all, only analysis
parameters. Every venue call in the repo is a public unauthenticated endpoint.
**Signing credentials live on the desktop** (`kalshi_client.py`), not here.

Known pre-existing issue, documented by another session in `STATUS.md`:
youtube-signal Phase 0/1 reports naming real creators **remain in public git
history**. Not introduced by this thread.

## Next actions

1. **Decide what to do with the two orphan directories.** They now hold 4.2 GB of
   unbacked-up work, including 41 commits with no remote. The recorders no longer
   block a move.
2. If restarting the recorders matters, do that **before** any move — and check
   why `record_depth.py` stopped mid-cycle.
3. `_archive/kalshi-tennis-backup-DUPLICATE/` can be deleted at any time.

## Rules carried forward

- **Never copy folder-over-folder** between `C:\Users\gianf\kalshi` and
  `C:\Users\vinig\kalshi`. Same name, zero shared files, one is a research
  pipeline and the other a live trading bot.
- `trading/kalshi-tennis/data/` is the **only** copy of the Stage 0–5 work; its
  upstream (Sackmann) is 404 and it runs on a frozen mirror ending 2026-06-02.
- Kalshi's API is a **~69-day window**. Closed markets 404 and are gone. Never
  re-pull to "replace" a local archive.
