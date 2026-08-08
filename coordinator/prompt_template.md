# CLAUDE CODE PROMPT — %%TITLE%%

**Written by `coordinator\newprompt.py` on %%WHEN%%.** Open a **new** Claude Code
session in `C:\Users\vinig\trading` and paste this entire file as the first
message.

**Work autonomously start to finish.** Do not stop to report progress and never
ask "should I continue?" — `CLAUDE.md` §2 is the contract and it wins over any
habit. If something blocks, record it in `DECISIONS.md`, do every independent
piece of work that remains, and carry on.

---

## 1. THE IDEA, IN THE USER'S OWN WORDS

> %%IDEA_QUOTED%%

**Copied verbatim.** It was not paraphrased, tightened or judged — the
coordinator does not get an opinion on the trading work. If a word looks wrong,
it is probably a voice-dictation slip (`CLAUDE.md` §4): read it for intent,
state your reading in one line, and proceed on it. Do not stop to ask.

---

## 2. READ THESE BEFORE YOU WRITE ANY CODE

1. `git pull`, then read `STATUS.md` — the shared channel between sessions.
2. `coordinator/mailbox/%%SLUG%%/` — instructions already addressed to you.
3. `LEDGER.md` — every claim this repo has made and its current status. **The
   `RETRACTED` count is the number that matters.** Read it there; do not repeat
   a number from memory, it has gone stale twice.
4. `GUARDS.md` — **12 reusable canaries. Use them. Do not reimplement them.**
5. `common/kalshi_fees.py` — the **only** implementation of fee arithmetic.
   Copying it is a test failure, enforced repo-wide. It reached 17 copies while
   the rule was only a convention.

### Possibly related prior work — keyword hits, go and read them

%%CROSS_CHECK%%

**A clean list above is not evidence the idea is new.** This is keyword
matching; it misses every paraphrase.

---

## 3. WHERE YOUR WORK LIVES

- **Your folder: `%%FOLDER%%/`.** Work only inside it. It gets its own virtual
  environment, its own `DECISIONS.md` and its own `HANDOFF.md`.
- **`python` on PATH is a Microsoft Store stub.** Use a full interpreter path or
  a project `.venv\Scripts\python.exe`.
- **Stage explicit paths when you commit. Never `git add -A`.** Two sessions
  have already cross-contaminated commits that way.
- **This repo is PUBLIC.** No credentials, no `.env`, nothing naming a real
  private individual. `data/` and `reports/` are gitignored for that reason.

---

## 4. PRE-REGISTER BEFORE YOU MEASURE

Write `%%FOLDER%%/PREREGISTRATION.md` **before** you look at any result, and state
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

- `%%FOLDER%%/PREREGISTRATION.md`, written first and not softened.
- `%%FOLDER%%/DECISIONS.md` — every judgment call you took instead of asking, with
  the conservative option you rejected, so it can be reversed.
- `%%FOLDER%%/HANDOFF.md` — the detail, for whoever picks this up next.
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
  py -3 coordinator\brief.py write %%SLUG%% --file <a file holding your section>
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
