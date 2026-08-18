# CLAUDE CODE PROMPT — STRATEGY FACTORY

**Written by `coordinator\newprompt.py` on 2026-08-18 00:18.** Open a **new** Claude Code
session in `C:\Users\vinig\trading` and paste this entire file as the first
message.

**Work autonomously start to finish.** Do not stop to report progress and never
ask "should I continue?" — `CLAUDE.md` §2 is the contract and it wins over any
habit. If something blocks, record it in `DECISIONS.md`, do every independent
piece of work that remains, and carry on.

---

## 1. THE IDEA, IN THE USER'S OWN WORDS

> Build the STRATEGY FACTORY. The full plan is committed at
> coordinator/STRATEGY_FACTORY.md -- READ IT FIRST, IN FULL, before writing
> anything. This paragraph is a summary of it, not a replacement for it.
> 
> His idea, in his own words: use the extractors, use Claude's own reasoning,
> think outside the box, come up with strategies, backtest them, and also forward
> paper-trade them with bots -- so that a month from now there are hundreds of
> strategies, dozens for EACH market rather than dozens overall, across everything
> Kalshi lists rather than sports alone. Crypto, weather, economics, anything.
> Running constantly, not as a one-off.
> 
> YOUR FIRST JOB IS NOT STRATEGIES. It is the recorder, and it is urgent for a
> reason that cannot be undone. bot-hunt/data/record.db holds 62 GB of Kalshi
> bid/ask WITH DEPTH plus Polymarket books and Pinnacle prices on one clock -- but
> it covers 19 Kalshi series and the exchange has 12,396. One family in every 650.
> Kalshi's history window is about 69 days and rolling; a closed market 404s and
> is gone permanently. So every day a family is not recorded is a day of its
> history that no amount of money will ever buy back. Widen it first. Coordinate
> with the `devig` chat, which owns bot-hunt -- do not edit that folder without
> agreeing it in STATUS.md first.
> 
> THE ONE RULE THAT MAKES THIS WORK, AND IT IS MEASURED, NOT AN OPINION: the
> backtest chooses, and only the forward test counts. One strategy showing +30%
> over 100 bets happens 1 time in 10,000 by luck -- the user is right that this is
> not coin-flipping and the analogy is banned. But the best of 2,000 zero-skill
> strategies typically looks like +29.5% and clears +30% thirty-seven times in
> 100. At the scale he is asking for, the winner will look like a huge edge even
> if nothing has any edge at all. A backtest number is therefore never reported to
> him as money, never sized on, and never called a result. It selects candidates
> and nothing else. Every report states how many strategies were screened to
> produce the one being shown.
> 
> Every screening run carries a placebo arm -- the same machinery on shuffled
> labels. If it finds an edge in noise, everything that run produced is void.
> 
> Real bid and real ask from k_book, never the mid. Real fees from
> common/kalshi_fees.py and nothing else -- a repo-wide test enforces that fee
> arithmetic has exactly one implementation. His low-liquidity question is
> directly answerable and he asked for it explicitly: k_book carries bid_size,
> ask_size, depth5_yes and depth5_no, so "what would it cost to put $500 into this
> thin market" means walking the book, not reading the top price.
> 
> Strategies are written specs before any data is touched: id, market family, what
> it bets on, entry rule, exit rule, size rule, what would make it wrong, who
> suggested it, date. The exit dimension is part of the spec and not an
> afterthought -- hold to settlement, sell at a level, buy more at a level, which
> level, one mentality or two, what happens when two disagree.
> 
> Four sources of ideas and all four run: the extractors (GitHub repos that really
> trade, YouTube methods with timestamps, Reddit and Discord claims); your own
> reasoning about market structure; the 51 claims out of 612 that the `reopen`
> chat found were closed for the wrong reason; and the user's own domain
> knowledge, which is the one input this repo cannot generate.
> 
> Survivors get a PREREGISTRATION_<NAME>.md committed BEFORE the forward test
> starts, stating the rule in full, the unit of observation, how many observations
> before it can be judged, the start date, and what result makes us drop it.
> 
> Forward paper trading is the only stage that produces a result. No money and no
> keys anywhere in this project -- copy tests/test_paper_only.py from
> tennis-paper-forward or mlb-paper before writing the first feature, do not
> invent a third style. Every strategy carries its no-skill range printed beside
> its result, the way the tennis chat now does for all 17 of its bots. A strategy
> is not "working" until its forward result sits OUTSIDE that range.
> 
> Promotion asks capacity first: at his actual bankroll, in that market's actual
> depth, how much money could this hold? A great edge in a market that takes $12
> is a hobby.
> 
> Known hazards, written before starting. Disk is the most likely thing to
> actually break -- 62 GB in 14 days on 19 families, so widening needs a tiered
> rate (full depth where a strategy is live, slower heartbeat on the long tail)
> and the numbers written down before it is switched on. Generation is cheap and
> screening is not, so index the tape before running thousands of specs against
> it. The forward test is slow by nature: a month gives real answers on
> fast-settling families and nothing on slow ones, so say which is which up front
> rather than reporting a shrug in September.
> 
> STAY AWAY FROM livedesk. It trades real money and is mid-repair.
> 
> Everything must be free. If a paid tier ever becomes the blocker, give him the
> arithmetic -- what the free tier allows, what the paid one costs, and what it
> would have to be worth -- and let him decide. Never a request without the
> numbers.

**Copied verbatim.** It was not paraphrased, tightened or judged — the
coordinator does not get an opinion on the trading work. If a word looks wrong,
it is probably a voice-dictation slip (`CLAUDE.md` §4): read it for intent,
state your reading in one line, and proceed on it. Do not stop to ask.

---

## 2. READ THESE BEFORE YOU WRITE ANY CODE

1. `git pull`, then read `STATUS.md` — the shared channel between sessions.
2. `coordinator/mailbox/factory/` — instructions already addressed to you.
3. `LEDGER.md` — every claim this repo has made and its current status. **The
   `RETRACTED` count is the number that matters.** Read it there; do not repeat
   a number from memory, it has gone stale twice.
4. `GUARDS.md` — **12 reusable canaries. Use them. Do not reimplement them.**
5. `common/kalshi_fees.py` — the **only** implementation of fee arithmetic.
   Copying it is a test failure, enforced repo-wide. It reached 17 copies while
   the rule was only a convention.

### Possibly related prior work — keyword hits, go and read them

- `LEDGER.md:596` — | **BH015** | ⚠ **R1 IS DEAD, on day one, before any game settled.** De-vig a LOOSE RETAIL book (Bovada) and compare it to the SHARP book (Pinnacle) on the same games: **they are the same opinion sold
- `LEDGER.md:664` — | **MB005** | **Selling out of a position when the other bot later takes the opposite side loses money, and the reason is mechanical rather than statistical.** | mlb-paper | **5 firing games** (of 72 
- `INBOX.md:37` — - **2026-08-07 — QUEUED, NOT STARTED: de-vig against a RETAIL book.** Every de-vig test in this repo used **Pinnacle, the sharpest book in the world**, and all are null (`bot-hunt/RESULTS_DEVIG_WHERE.
- `LEDGER.md:100` — | **MB004** | "The agreement pattern REVERSED out of sample — all three buckets flipped sign, and that is what a pattern being luck looks like" | mlb-paper | **A bug in my own code, not a result.** `c
- `LEDGER.md:412` — | **B016** | ⚠ **A free ITF data source may exist, reopening a thread closed on data availability.** | bot-forensics | `src/t4_github.py`, `src/t4b_verify.py` → `out/t4b_verify.txt` | 11 official clie
- `LEDGER.md:594` — | **BH013** | ~~`RESULTS.md` §3's "`KXMLBGAME` is 1.0¢ at every lead" is wrong because the recorded touch is 2.0¢~~ ⚠⚠ **MY CORRECTION WAS ITSELF WRONG. WITHDRAWN 2026-08-09.** | `src/mlb_scope.py`, r

**A clean list above is not evidence the idea is new.** This is keyword
matching; it misses every paraphrase.

---

## 3. WHERE YOUR WORK LIVES

- **Your folder: `strategy-factory/`.** Work only inside it. It gets its own virtual
  environment, its own `DECISIONS.md` and its own `HANDOFF.md`.
- **`python` on PATH is a Microsoft Store stub.** Use a full interpreter path or
  a project `.venv\Scripts\python.exe`.
- **Stage explicit paths when you commit. Never `git add -A`.** Two sessions
  have already cross-contaminated commits that way.
- **This repo is PUBLIC.** No credentials, no `.env`, nothing naming a real
  private individual. `data/` and `reports/` are gitignored for that reason.

---

## 4. PRE-REGISTER BEFORE YOU MEASURE

Write `strategy-factory/PREREGISTRATION.md` **before** you look at any result, and state
in it:

- the exact question, and what number would answer it;
- **what result would make you drop the idea** — if nothing would, it is not a
  test;
- the sample size you need and the smallest effect you could detect at it;
- the naive benchmark you will report alongside the result.

Then do not soften it afterwards. Amendments get numbered and dated in the same
file, never edited away.

---

## 5. EVIDENCE STANDARDS THAT HAVE ALREADY COST THIS REPO SOMETHING

Each of these is here because it was learned the expensive way.

- **Every recorded correction in this repo has shrunk the edge. Not one has ever
  revealed a larger effect.** Treat any positive result as presumptively wrong
  until it survives an untouched holdout.
- **Selecting on past performance is fine. Measuring returns over the same
  window you selected on is not.**
- **Cluster confidence intervals at the right unit, and say what the unit is.**
  A market settles once: 490,464 fills from 762 matches are **762**
  observations.
- **Report effective sample size, not nominal**, when observations are
  correlated. A 10-strike ladder is one temperature reading, not ten markets.
- **Report the naive benchmark next to every result.**
- **Mark retractions inline where the claim appears.** Deleting a wrong number
  is how the next session re-derives it.
- **Reading beats scoring.** In the GitHub work, reading found 5 defects across
  3 repos that every computed metric had rated well.

---

## 6. WHAT FINISHING LOOKS LIKE

- `strategy-factory/PREREGISTRATION.md`, written first and not softened.
- `strategy-factory/DECISIONS.md` — every judgment call you took instead of asking, with
  the conservative option you rejected, so it can be reversed.
- `strategy-factory/HANDOFF.md` — the detail, for whoever picks this up next.
- Your rows merged into `STATUS.md`. **Read it first. Never overwrite another
  session's entries.**
- **A `COORDINATOR-STATE` block** at the top of your `HANDOFF.md`, so the
  coordinator can report you accurately instead of guessing:

  ```
  <!-- COORDINATOR-STATE
  doing: one line, present tense, what this session is working on
  left: one line, what still has to happen
  needs: no
  -->
  ```

  `needs:` is `no`, or `yes - <the question, in one line>`. HTML comments are
  invisible in rendered Markdown, so this costs the page nothing.
- Your section of the brief:
  ```
  py -3 coordinator\brief.py write factory --file <a file holding your section>
  ```
  `## Title`, an `**As of YYYY-MM-DD.**` line, under 20 lines, plain English,
  **no acronyms**.
- **Committed and pushed.** The coordinating chat reads this repo over the
  public web. Unpushed work does not exist to it.

---

## 7. HOW TO END EVERY MESSAGE

`CLAUDE.md` §1 in full, and it is not optional. Under 150 words, and the sync
marker's commit hash comes from actually running `git rev-parse --short HEAD` —
**never invent it**, the whole point is that he can check it against GitHub.

The user is **not a software engineer**, runs five projects at once, and reads
cold on a phone. Above that block, be as technical as you like — he skims it,
and truncating analysis to save space costs him nothing and loses him something.

**If his instruction was wrong, say so.** He would rather be corrected than
agreed with. That has already been load-bearing here: he was told there were 9
copies of the fee formula and there were 17.
