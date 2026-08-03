# HANDOFF — youtube-signal

**Updated 2026-08-03 12:46.** Laptop `gianf`.
Working directory: `C:\Users\gianf\trading\youtube-signal` — **inside the repo**,
tracked and pushed. Repo `github.com/vinexcleaning/trading`.

**Cost to date: $0.00. YouTube API quota: 0 units. No API key exists or is needed.**
The read is done in-session by the model reading the transcript itself
(`dump_transcripts.py` → hand-written JSON → `load_extraction.py`), which has now
run 20 times. `read_video.py` (the API path) has still **never executed** and is
unvalidated. Do not spend money to unblock something that is not blocked.

---

## 0. What this project is

Finds genuinely informative YouTube videos on a topic, reads the transcripts, and
extracts the substance — tools, methods, specific claims — into `KNOWLEDGE.md` so
they never have to be watched. `CLAUDE.md` at the repo root points every future
session at that file.

Corpus: **11,277 videos known, 683 transcripts cached, 553 gated and ranked, 20
read in full.** 205 claims, 18 methods, 63 tools.

---

## 1. State: what runs, and in what order

```
src/run_retrieval.py      searches YouTube (yt-dlp, no key), 3 runs, union
src/run_gates.py          G1 transcript / G2 age / G3 on-topic, + descriptions
src/rank_substance.py     free keyword ranking of all 553 — decides reading order
src/dump_transcripts.py   prints ONE transcript for reading
src/load_extraction.py    validates evidence, runs n-check, writes to DB
src/build_knowledge.py    regenerates KNOWLEDGE.md
src/verify_tools.py       do the claimed URLs/repos exist and have commits
src/tool_reputation.py    what does the internet say that the vendor did not write
src/coverage.py           what is covered, what is unread — the steering wheel
```

**One video per turn.** Holding transcripts in context is quadratic: 15 videos in
one session costs ~2.7M tokens against ~244k done singly.

## 2. Scoring — three axes, never averaged

**S substance /10** · S1 cost side +3 · S2 backtest vs live +2 · S3 sample size +2
· S4 mechanism +2 · S5 names tools +1

**B build /10** (added this session) · B1 working code +3 · B2 named endpoints +2 ·
B3 complete auth→order path +2 · B4 the gotcha +2 · B5 resolvable artifact +1

**H honesty −10..+11** · H1 failure not sold +3 · H1b failure sets up sale +1 ·
H2 verifiable artifact +3 · H3 n+period+capital +2 · H4 own weakness +1 ·
H5 discloses own product +2 · **H6 no denominator −4** · H7 sells w/o mechanism −2
· H8 urgency −1

**Every component needs a timestamp and a verbatim quote under 15 words.**
`load_extraction.py` enforces it and rejects anything else. This is the rule that
makes the output auditable — do not relax it.

Verdicts: `BUILD` · `BUILD_AND_RECOMMEND` · `ABSORB` · `ABSORB_AND_RECOMMEND` ·
`ABSORB_RESULTS_DISCOUNTED` · `SKIP`. Current spread: ABSORB 9,
BUILD_AND_RECOMMEND 4, ABSORB_AND_RECOMMEND 4, ABSORB_RESULTS_DISCOUNTED 2,
**SKIP 0**.

## 3. What changed this session

**Video descriptions are now captured.** They were not, and that was a real gap.
The transcript is auto-captioned *speech*; the description is *typed* and holds the
literal URLs. Backfilled all 19 read videos → 54 URLs recovered, including:
- `t.me/KreoPolyBot?start=ref-begin` — the correct spelling *and* proof of a
  referral. Two web searches had been spent deriving "Creo" → "Kreo".
- `github.com/jon-becker/prediction-market-analysis` — the 72M-trade repo,
  previously stored as the bare string `"github.com"`, which had granted a false
  H2 (+3) that had to be revoked.
- **Five referral links in one video that the audio never disclosed** (odinbot,
  gmgn, axiom, photon, Kreo). That video had scored H5 +2 for disclosing its own
  product; it disclosed one and stayed quiet about five. Descriptions are where
  undisclosed monetisation lives. Tools 58 → 63, referral-flagged 9 → 14.

**The B axis, and why.** S1/S2/S3 all require a *trading claim*, so a pure API
tutorial capped at S=3 and auto-classified SKIP however good the code was. That is
how a Kalshi build with 100 lines of working code and a public repo (H=9) came out
as SKIP. B asks the different question. Rescored all 19 from verbatim transcript
evidence via `src/b_candidates.py` (greps candidate quotes; judgment stays human).

Build shortlist now findable as a group:
| B | video | |
|---|---|---|
| 10 | Part Time Larry — Kalshi + Perplexity in 100 lines | *was SKIP* |
| 8 | Robot Traders — Kalshi API in Python, live order placed |
| 7 | wangr — Polymarket CLOB API, order placed and cancelled |
| 6 | Emil Nielsen — Polymarket WebSockets, local order book |

11 of 19 score B=0 — correct, not a gap: they are explanation videos, which is
what S measures. All five B components fired.

**Three deliberate withholdings** (each looks like a B point and is not):
JunkieAI says *"sadly I remove the GitHub"* — artifact gone, B5 does not fire
(B=5, rescued SKIP→ABSORB, correctly short of BUILD). Moon Dev is titled "Full
Code" but says *"this one's not on my GitHub"* — same call. Emil Nielsen says
*"too much into the actual code"* — declining to show code, so B1 does not fire.
B5 is the most gameable component on the axis; withholding matters more than
awarding.

## 4. The single most important finding in the knowledge base

**Polymarket CLOB V2 went live 28 Apr 2026 and both V1 clients are ARCHIVED**
(`py-clob-client` 1,234★ archived 11 May; `clob-client` 513★). V1-signed orders
are unsupported on production. **Two tutorials in this knowledge base teach V1**,
one of them scored RECOMMEND. Nothing in them is wrong; following them today
produces a bot that cannot sign an order. Migrate to `Polymarket/py-sdk`.

That is the finding the whole system exists to produce: a good, honest, recent
tutorial silently expired.

## 5. What is wrong, unfinished or untrusted

1. **`read_video.py` has never run.** Draft, unvalidated below the API call.
2. **Both G3 validation samples have informed the lexicon's design**, so its
   85.9% / precision 0.809 / recall 1.000 are **upper bounds, not a clean holdout**.
3. **`expansion_v2.py` does not work** and was applied anyway because it was a
   decision, not a suggestion. The ≥50%-of-retrieved bar pruned 0 channels and
   admitted 46 more (Fireship, freeCodeCamp, a16z). Recommend reverting to the
   Phase 1 rule and deferring until an LLM can score catalogue titles.
4. **The 681-minute video is unread** — does not fit a context window, chunking
   not built.
5. **Three silent-default bugs have now been found in this project** (UNIQUE
   ignoring NULL urls; a bare `github.com` URL granting a false H2; `b_total`
   never persisting so the BUILD section rendered empty). All three passed
   inspection and were only caught by reading the actual output afterwards.
   **Do not trust a green commit message from an unattended session.**

## 6. The single next thing to do

Clone `Polymarket/py-sdk`, place and cancel one order from a **$10 throwaway
wallet**, and record which of the eleven documented steps changed. Costs nothing
and converts the most actionable method in the file from *probably broken* to
*verified*.

---

## 7. Infrastructure — findings outside this project, 2026-08-03 12:46

**Not backed up anywhere:**
- `C:\Users\gianf\kalshi\set1_overshoot` — is a git repo, clean, last commit
  `f9a1e88 checkpoint`, but has **ZERO remotes**. One disk failure from gone.
- `C:\Users\gianf\crypto` — **not a git repo at all.** No backup of any kind.

**Both recorders named in the root STATUS.md were dead. BOTH ARE NOW BACK UP** —
re-verified 12:48:48, two minutes after the lines above were written.

- `record_depth.py` (tennis depth) — **RUNNING again as PID 14072, started
  12:46:47.** Confirmed live: `set1_overshoot\data\depth\2026-08-03\16\depth.jsonl`
  written at **12:48:07**, 41 s before the check. **Gap is 09:59:12 → 12:48:07 =
  ~2h49m and is permanently lost** — Kalshi has no historical order-book endpoint,
  so this cannot be backfilled by anyone, ever.
- `record_15m_opens_v2.py` (crypto) — **RUNNING as PID 22260**, restarted 12:46:33
  with `--hours 168`. Its log and err files were written at start. **Caveat: the
  data file `crypto\data\btc15m_opens\opens_all_2026-08-03.jsonl` has not been
  appended to since 08:30:58.** Two minutes in that is expected — it waits for the
  next 15-minute boundary — but if it is still 08:30 an hour from now the process
  is up and not collecting. **Check that file's mtime, not the process list.**
  Gap so far 08:30 → 12:46, ~4h16m.

**Machine sleep:** `powercfg SUB_SLEEP STANDBYIDLE` AC index = `0x00000000` —
never sleeps on mains. On battery it is not covered by that setting; both
recorders die on sleep and neither gap is recoverable. Keep it plugged in.

**Processes running, NONE of them mine** (this session started no background job):
| PID | what | writes to | dies on sleep |
|---|---|---|---|
| 14072 | `record_depth.py` — tennis order-book depth | `kalshi\set1_overshoot\data\depth\<date>\<hr>\depth.jsonl` | **yes, unrecoverable** |
| 22260 | `record_15m_opens_v2.py --hours 168` — crypto 15m opens | `crypto\data\btc15m_opens\opens_all_<date>.jsonl` | **yes, unrecoverable** |
| 21208 | `wallet-copy-study\src\spec_20_pull_missing.py`, running since 10:29 | `wallet-copy-study\reports\` | re-runnable |
| 17996 | `src/fetch_repo.py tree 400` (signal-github) — **borrowing this project's venv** | signal-github | re-runnable |
| 17308 | `src/fetch_repo.py tree 400` (signal-github, second copy) | signal-github | re-runnable |

The two recorders are the only irreplaceable things in that list.

## 8. Checkpoint status, 2026-08-03 12:48

**Working directory `C:\Users\gianf\trading\youtube-signal` — inside the repo.**
Git top level is `C:\Users\gianf\trading`.

**Working tree is CLEAN. Nothing untracked.** `git add -A` and
`git commit -m "checkpoint"` are both no-ops right now — a parallel session's
`checkpoint` commit (`3137c2d`) already swept everything at 12:4x.

**PUSH SUCCEEDED — everything is backed up remotely.** `origin/main` tip is
`094279f`, verified with `git rev-list --left-right --count` = **0 ahead, 0
behind**. It took three attempts and the failures are worth recording: two
denials from the Claude Code permission classifier (transient stage-2 error, not
git and not the remote), then one `Failed to connect to github.com:443 after
21054 ms`. In between, a parallel session pushed the backlog of 15. If a push
looks blocked here, retry before concluding anything — none of the three failures
meant what it appeared to mean.

Ignored and deliberately not committed (privacy — the repo is public and these
hold judgments about named creators): `youtube-signal/KNOWLEDGE.md`,
`youtube-signal/reports/`, `youtube-signal/data/`.

**One thing to look at in `3137c2d` before pushing:** that `git add -A` swept 13
new `wallet-copy-study/reports/*.json` files into history, two of which carry
wallet addresses (`rec_probe.json` 2, `spec_latency_panels.json` 22). That
directory was *already* tracked and public — 39 such files are on `origin/main`
already — so this is not a new class of exposure, but it is the exact mechanism
`CLAUDE.md` forbids `git add -A` for, firing for the fourth time.
