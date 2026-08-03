# CLAUDE CODE PROMPT — GitHub Signal: real Kalshi/Polymarket bots

Paste into a fresh Claude Code session in `C:\Users\gianf\trading`.
**Runs start to finish with no user input. If something blocks, record it and move
on. Never wait for an answer. Never ask a question you can answer yourself.**

This is prompt 1 of 3. Prompts 2 (Reddit) and 3 (social) can run in parallel
sessions. They write to different folders and different DB files, so they will not
collide — but **stage explicit paths when committing, never `git add -A`.** Two
sessions have already cross-contaminated commits in this repo.

---

## WHY THIS ONE MATTERS MOST

The user has spent a session extracting YouTube. It produced good *explanations* —
how market making works, why fees peak at 50/50 — and almost nothing he can *run*.
That is the gap you exist to close.

**GitHub is the strongest signal source available, because commit history cannot be
faked cheaply.** A YouTuber claiming a profitable bot is an assertion. A repo with
400 commits over 18 months, a backtest directory and open issues is evidence. You
are not looking for people who say they have a bot. You are looking for bots.

Read first, do not skip:
- `youtube-signal/KNOWLEDGE.md` — what is already known. Do not re-derive it.
- `.claude/skills/youtube-signal/SKILL.md` — the architecture and the traps.

---

## PREMISE WARNING

Verified, treat as true:
- Retrieval and ranking can be free. GitHub's REST API is 60 req/hour
  unauthenticated, 5,000 with a free token (no card). Confirm before building.
- **Insider and beginner vocabulary return near-disjoint sets** (Jaccard 0.037 on
  YouTube). Build both families, never merge them.
- Ranking everything is free; reading is the only expensive step. Rank all, read few.
- Reading many documents in one session is quadratic in tokens. **One repo per
  turn**, write the extraction to disk, move on.
- `python` on PATH is a Store stub. Use a venv interpreter.

Untested, and your job to test:
1. **That good Kalshi/Polymarket bots exist publicly at all.** They may not. A
   plausible finding is "37 repos, 3 alive, none with a working backtest". **That
   is a real result — report it plainly, do not pad it.**
2. **That the S/H scoring transfers to code.** It was built for spoken transcripts.
   Report which components never fire.
3. **That stars correlate with substance.** Suspect they do not, exactly as views
   did not on YouTube. Measure it.

---

## STEP 0 — REACHABILITY

Confirm the unauthenticated GitHub API works and record the real rate limit from
the response headers. If a free token is available in the environment, use it; **do
not create an account, do not ask the user for one.** If unauthenticated access is
too tight, throttle and continue — do not stop.

Write `signal-github/reports/step0.md`. Then keep going regardless.

---

## STEP 1 — RETRIEVAL

Two families, kept separate and separately reported:

**F1 beginner:** `kalshi bot`, `polymarket bot`, `prediction market trading bot`,
`sports betting bot`

**F2 insider:** `kalshi api python`, `polymarket clob client`, `py-clob-client`,
`avellaneda stoikov`, `market making inventory risk`, `orderbook imbalance`,
`walk forward backtest`, `negrisk polymarket`, `kalshi websocket`,
`event contract arbitrage`, `prediction market maker`, `polymarket copy trading`

Search **repositories AND code**. Code search finds repos whose README never
mentions the term but whose source imports the client library — a genuinely
different population, and usually a more serious one.

Also enumerate: **forks and dependents of
`github.com/Jon-Becker/prediction-market-analysis`** (3,693 stars, 162MB, the
largest public Kalshi+Polymarket trade dataset, 72.1M trades). People building on
that dataset are precisely the population worth finding.

Deduplicate by `full_name`. Cache every API response. Never clone.

## STEP 2 — GATES

- **G1** not empty: size > 0 and more than one commit
- **G2** pushed within 24 months, else tag `STALE` and set aside — **do not delete.**
  (A video-level age cutoff in the YouTube project silently discarded 184 items, 10
  of which outranked everything kept. Age gates leak. Tag, never drop.)
- **G3** genuinely on topic, from README + top-level file tree

Log a drop reason for every rejection. Report the census.

## STEP 3 — SCORE, FROM THE REPO ITSELF

Most of this is computed, not judged. Compute it.

**Substance (0–10):**
| | | |
|---|---|---|
| S1 | Handles the cost side — `fee`, `slippage`, `spread` appear in source, not just README | +3 |
| S2 | Has a backtest **and** a live/paper path, distinguishable from each other | +2 |
| S3 | Has tests, or a results directory with real committed output | +2 |
| S4 | README explains the **mechanism**, not just installation | +2 |
| S5 | Runnable — pinned dependencies, obvious entry point | +1 |

**Credibility, all computed:** commit count, commit span in days, contributor
count, open/closed issue ratio, whether the last commit is substantive or a README
tweak, and whether any performance claim in the README has an artifact behind it.

**A README with a P&L chart and 3 commits is the GitHub equivalent of "trust me
bro." Flag it explicitly.**

**Every scored component needs evidence: a file path and a line, or a commit SHA.**
No evidence, no score. This rule is enforced in the YouTube project and it is the
reason its output is auditable — keep it.

## STEP 4 — EXTRACT (rows, not prose)

`repos`: `full_name`, `url`, `stars`, `commits`, `span_days`, `last_push`,
`contributors`, `language`, `what_it_does`, `strategy_type`, `venue`
(kalshi/polymarket/both/other), `has_backtest`, `has_tests`, `has_live_trading`,
`claimed_results`, `artifact_behind_claim`, `license`, `s_total`, `verdict`

`strategies`: one row per identifiable strategy — `repo`, `name`, `description`,
`entry_logic`, `exit_logic`, `parameters`, `costs_modelled` (bool),
`backtest_evidence`, `file_path`

`dependencies`: libraries that matter — the actual Kalshi/Polymarket client
libraries, backtest frameworks, data sources. **This is one of the most valuable
outputs**: it is the real toolchain, discovered from working code rather than from
someone selling a course.

`data_sources`: every place a repo gets historical data from, with whether it is
free, and what it covers.

## STEP 5 — THE QUESTIONS THE USER ACTUALLY ASKED

Answer these explicitly in the report, in plain English, with evidence:

1. **How do working bots actually do it?** What strategies recur across repos?
2. **Kalshi or Polymarket — which is the better venue for an automated bot?**
   Compare on API quality, fees, liquidity, and rules on automation.
   **Check each platform's terms on automated trading and report what they say.**
3. **Where do you get historical data to backtest?** Rank by free-first.
4. **How do you build a good backtest?** Extract the actual method from repos that
   have one, including how they model fees and slippage.
5. **How much can be automated end to end, and where must a human click?**
6. **Is there a strategy here worth testing?** Name it, with its evidence and its
   costs. If the honest answer is "nothing here clears its own cost bar", **say
   that** — the user's own tennis project found a real edge that was uncollectable
   after costs, and that was the correct and valuable finding.

## STEP 6 — CROSS-REFERENCE

For every tool named in `youtube-signal/KNOWLEDGE.md`, check whether a repo exists
and whether it is alive. **A tool recommended in a recent video whose repo died two
years ago is exactly the kind of finding this whole system exists to produce.**
Write those conflicts down.

---

## OUTPUTS

1. `signal-github/data/github.db` — gitignored
2. `signal-github/reports/*.md` — gitignored
3. `signal-github/GITHUB_KNOWLEDGE.md` — gitignored. Same shape as
   `youtube-signal/KNOWLEDGE.md`: rows, provenance, **and a date on every claim**
   (repos rot; a 2024 API integration may simply no longer work).
4. Code committed. Stage explicit paths.

## AT THE END

`signal-github/HANDOFF.md`:
1. Reachability outcome and the real rate limits
2. Premises tested and verdicts — especially whether good public bots exist
3. The numbers, **including the bad ones**
4. **What was built vs what actually ran on real data** — keep separate
5. What is wrong, unfinished or untrusted — **this section matters most**
6. The single next thing to do, and why

Append a short section to repo-root `STATUS.md`. Artifacts and numbers, not
narration. Do not narrate the session.
