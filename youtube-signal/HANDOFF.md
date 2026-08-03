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

**Both recorders named in the root STATUS.md are dead:**
- PID 17892 `record_depth.py` (tennis depth) — **NOT RUNNING.** Last write to
  `set1_overshoot\data\depth` was **09:59**, now 12:46 → **~2h47m gap.**
  STATUS.md states these gaps are irrecoverable; Kalshi has no historical
  order-book endpoint. **Nobody has restarted it.**
- PID 24756 `record_15m_opens_v2.py` (crypto) — not running, but **a parallel
  session restarted it at 12:46:33 as PID 22260**. Gap 08:30 → 12:46, ~4h16m.

**Processes running, none of them mine:** 21208 wallet-copy-study · 17996 and
17308 `fetch_repo.py` (signal-github, one of them borrowing this project's venv) ·
22260 the restarted crypto recorder.
