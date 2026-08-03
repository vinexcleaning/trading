# CLAUDE CODE PROMPT — Social Signal: X, TikTok, Instagram

**Prompt 3 of 3.** Prompt 1 covers GitHub, prompt 2 covers Reddit and Discord.
Run them in parallel sessions; they write to different folders and DB files.
**Stage explicit paths when committing — never `git add -A`.**

Expect this one to be the least productive of the three, and that is fine. These
platforms are hostile to unauthenticated access and their trading content is the
most marketing-dense on the internet. **"All three blocked, here is the evidence"
is a perfectly good result.** Timebox each to ~30 minutes and stop.

Do not create accounts on any of them. Do not pay for API access. Do not automate
a logged-in personal account — that is what these platforms ban people for.

Paste this into a fresh Claude Code session in `C:\Users\gianf\trading`.
**It requires no input from the user. If anything blocks, record it and move to the
next platform. Never wait for an answer.**

---

## PREMISE WARNING — READ FIRST

A sibling project, `youtube-signal/`, already works end to end. Read
`youtube-signal/HANDOFF.md` and `.claude/skills/youtube-signal/SKILL.md` before
writing code. The architecture transfers; the lessons below were paid for.

Verified facts, treat as true:

- **Retrieval and ranking can be free.** yt-dlp searches YouTube with no API key.
  The equivalent free path exists for GitHub (public REST API) and partially for
  Reddit. Find it before assuming a paid scraper is needed.
- **Insider vocabulary and beginner vocabulary return near-disjoint sets** —
  Jaccard 0.037 on YouTube, and a second insider batch was 88.5% exclusive again.
  Corpus size scales with insider term count. Build both families, never merge them.
- **A ranking pass costs nothing; a reading pass costs everything.** Rank
  everything with keyword proxies, read only the top N.
- **Reading in one session is quadratic.** 15 documents read in one conversation
  processes ~11x their raw token count. One document per turn, write the extraction
  to disk, move on.
- **`NO_FOOTPRINT` is not `POSITIVE`.** Absence of complaints is absence of evidence.
- **Never resolve an identity by name.** Name search returns confident wrong
  people. Go artifact → author ID, never name → author.

New premises this project must test. Assume none of them:

1. **Each platform is reachable without paid API access.** Unknown per platform.
   Step 0 settles it, platform by platform.
2. **Signal exists off YouTube at all.** Reddit and GitHub may carry far more
   substance per token; TikTok and Instagram may carry almost none. Measure it.
3. **The S/H scoring transfers.** It was designed for spoken transcripts. A GitHub
   repo has no "shows a failure" moment but has commit history, which is stronger
   evidence than anything a video can offer. The scheme probably needs per-platform
   components. Report which ones never fire.

---

## THE GOAL

The user is building a knowledge base his Claude sessions read before answering.
`youtube-signal/KNOWLEDGE.md` already does this for YouTube. This project adds
sources. Same output shape, same rules: **rows, not prose; every claim carries
provenance and an expiry; a summary is not an output.**

Current topic focus: **prediction markets, trading bots, algorithmic trading,
Kalshi and Polymarket specifically.** Topic must be a parameter throughout — the
user will point this at SAT prep and Roblox later.

**Priority is ACTIONABLE over EDUCATIONAL.** The YouTube corpus is rich in "here is
why market making works" and thin on "here is a strategy you can implement and
test". Weight retrieval and scoring toward: working code, repeatable procedures,
concrete parameters, and results with a verifiable artifact behind them.

---

## STEP 0 — REACHABILITY (do this first, all platforms, then report)

For each of **GitHub, Reddit, X, TikTok, Instagram**, determine in this order:

1. Is there an official free API? What are its limits without authentication?
2. If it needs auth, is it free-tier auth (a token, not a card)?
3. Is there a mature open-source client that works keylessly?
4. If none of the above, **record it as blocked and move on.** Do not build a
   browser-automation scraper. Do not sign up for anything. Do not pay for anything.

Write `reports/step0_reachability.md` with, per platform: reachable yes/no, the
mechanism, the rate limit, and what breaks. **Then keep going with whatever
reached.** A partial project delivering GitHub and Reddit is a success; stalling
until all five work is a failure.

Expected, but verify rather than trusting this:
- **GitHub** — public REST API, 60 req/hour unauthenticated, 5,000 with a free
  token. Almost certainly the strongest source in this project.
- **Reddit** — public `.json` endpoints exist; the official API changed and may
  need a free app registration. Old-reddit JSON often works unauthenticated.
- **X / TikTok / Instagram** — hostile to unauthenticated access. Expect blocked.
  Record and move on. Do not spend the session fighting them.

---

## STEP 1 — GITHUB (do this one properly; it is the highest-value source)

GitHub is the strongest signal source available, because **commit history cannot be
faked cheaply.** A YouTube creator claiming a profitable bot is an assertion. A repo
with 400 commits over 18 months, open issues, and a backtest directory is evidence.

### Retrieval
Two query families, kept separate, exactly as in `youtube-signal/src/queries.py`:
- **F1 beginner:** `kalshi bot`, `polymarket bot`, `prediction market trading`
- **F2 insider:** `kalshi api python`, `polymarket clob client`, `avellaneda stoikov`,
  `market making inventory`, `orderbook imbalance`, `walk forward backtest`,
  `negrisk polymarket`, `kalshi websocket`, `event contract arbitrage`

Search repos **and** code. Code search finds repos whose README never mentions the
term but whose source imports the client library — a different population.

### Gates
- **G1** repo is not empty (size > 0, has commits beyond the initial one)
- **G2** has been pushed to within 24 months, else tag `STALE` and keep aside
- **G3** genuinely on topic, from README plus top-level file names

### Scoring — this is where the YouTube scheme must change
Substance components that actually apply to code:

| | | |
|---|---|---|
| G-S1 | Handles the cost side — fees, slippage, spread appear in the code | +3 |
| G-S2 | Has a backtest AND live/paper execution path, distinguishable | +2 |
| G-S3 | Has tests, or a results directory with real output | +2 |
| G-S4 | README explains the mechanism, not just installation | +2 |
| G-S5 | Runnable — dependencies pinned, entry point obvious | +1 |

Honesty is mostly free here and should be computed, not judged:
commit count, commit span in days, contributor count, open/closed issue ratio,
whether the last commit is a real change or a README tweak, and whether a claimed
performance number in the README has any artifact behind it.

**A repo with a P&L chart in the README and 3 commits is the GitHub equivalent of
"trust me bro". Flag it.**

### Extract
`repo`, `url`, `stars`, `commits`, `span_days`, `last_push`, `language`,
`what_it_does`, `strategy_type`, `venue` (Kalshi/Polymarket/both), `has_backtest`,
`has_tests`, `has_live_trading`, `claimed_results`, `artifact_behind_claim`,
`dependencies_worth_knowing`.

**Clone nothing.** Read via the API — README, file tree, and up to ~10 key source
files. Cache everything by repo full name.

### Cross-reference against what already exists
`youtube-signal/KNOWLEDGE.md` names tools extracted from videos. For each, check
whether a repo exists and whether it is alive. A tool recommended in a video whose
repo has been dead for two years is a finding worth recording.

Start from this verified asset:
**`github.com/Jon-Becker/prediction-market-analysis`** — 3,693 stars, 162 MB, the
largest public Kalshi + Polymarket trade dataset (72.1M trades, $18.26B volume),
last pushed 2026-08-01. Read its README properly, record what analyses it already
ships, and follow its dependents and forks — people building on it are exactly the
population this project wants.

---

## STEP 2 — REDDIT

Subreddits worth trying: `r/algotrading`, `r/PredictionMarkets`, `r/Kalshi`,
`r/Polymarket`, `r/quant`, `r/sportsbook` (for closing-line-value discipline).

Reddit's value is **negative evidence**, which no other source provides. YouTube
never tells you a tool rugged. Reddit does. Weight accordingly:
- Complaint threads about a named tool → feed straight into tool reputation
- Post-mortems ("my bot lost money because…") → higher value than success posts
- Comments contradicting the parent post → the most informative text on the platform

Gates: score and comment-count thresholds, age, on-topic. Extract the same claim
rows, plus `sentiment_toward_named_tool`.

**Do not extract usernames into the knowledge base beyond what is needed for
provenance.** Link the permalink; do not build profiles of individuals.

---

## STEP 3 — X / TIKTOK / INSTAGRAM

Attempt in that order, timebox each to roughly 30 minutes of effort. If
unauthenticated access is blocked, **write it up and stop.** Record exactly what
was tried and what the failure was, so it is not re-attempted blind later.

Honest prior: these are low-substance-per-token for this topic and hostile to free
access. TikTok trading content is close to pure marketing. Instagram is worse. X has
real quant discussion but the free surface is heavily restricted. **Being told "all
three are blocked, here is the evidence" is a perfectly good outcome.**

---

## STEP 4 — MERGE

One knowledge file per source, plus a merged view. When two sources disagree about
a tool, **keep both and mark the conflict** — a video praising a tool and a Reddit
thread reporting a rug is the single most valuable pattern this whole system can
surface. Never collapse it to an average.

Write `SIGNAL_KNOWLEDGE.md` at repo root with a section per source and a combined
tools table carrying: name, what it does, whose it is, verification status,
reputation, and any conflict.

---

## OUTPUTS

1. `signal-scrapers/data/*.db` — SQLite per platform. Gitignored.
2. `signal-scrapers/reports/*.md` — gitignored.
3. `SIGNAL_KNOWLEDGE.md` — gitignored (it names people alongside judgments).
4. Code committed to `github.com/vinexcleaning/trading`.

---

## HOW TO WORK

- **Never wait for user input.** Blocked → record it → next step.
- Commit code after each step. **Stage explicit paths — never `git add -A`.** Two
  sessions have already cross-contaminated commits in this repo.
- `python` on PATH is a Store stub. Use a venv interpreter.
- A component that never fires is a bug or a bad rule, not a neutral result.
  Report counts.
- Do not spend money. Do not create accounts. Do not sign anything up.
- If a premise fails, write it into `HANDOFF.md` rather than working around it.

## AT THE END

Write `signal-scrapers/HANDOFF.md`:
1. Which platforms were reachable, and the exact mechanism for each
2. Premises tested and verdicts — especially whether S/H transfers to code
3. The numbers, including the bad ones
4. **What was built vs what actually ran on real data** — keep these separate
5. What is wrong, unfinished or untrusted — this section matters most
6. The single next thing to do, and why

Merge a short section into the repo-root `STATUS.md`. Artifacts and numbers, not
narration.
