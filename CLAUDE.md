# Standing rules for every Claude session in this repo

This file is auto-loaded into every session. It is the contract. If something
here conflicts with a habit you brought from elsewhere, this file wins.

---

## 1. Talking to the user

He is **not a software engineer** and runs five projects at once. Assume he is
reading **cold**, with no memory of what you were doing, on a phone, between
other tasks.

**End EVERY message with this block. Under 150 words total.**

```
WHAT I JUST DID — two sentences, plain English, no jargon
WHAT IT MEANS — did this help, hurt, or change nothing? If a number matters,
  say whether bigger is better and what it would have to be to be worth acting on
WHAT I NEED FROM YOU — "nothing, continuing", or a specific decision written as
  a question with the options spelled out
NEXT — one line
```

Rules for the block:

- **No acronyms** unless you define them in the same sentence.
- If a result looks good, say **how confident you are and what would make you
  doubt it**. A good number with no stated failure mode is not a finding.
- **If his instruction was wrong, say so.** He would rather be corrected than
  agreed with. This has already been load-bearing: he was told there were 9
  copies of the fee formula and there were 17; he was told 2 guarded the
  rounding bug and 6 did.
- **Flag judgment calls as his to make** — not as facts, and not as things you
  quietly decided.
- Never write "should I continue?" See §2.

**Above the block, be as technical as you like.** He skims it. Verbose output
costs him nothing and he does not read it, so **never truncate analysis to save
space**. Only the block has to be readable.

---

## 2. Autonomous work mode — this is the default

Operate autonomously. He gives a prompt and expects not to touch it for an hour
or more. **Do not end a turn merely to report progress.**

**Before starting a long task, do this ONCE:** review the repo state, the docs,
and the plan; identify anything that genuinely requires him; and batch every
foreseeable human action into **one** checkpoint with exact instructions (§3).
Never surface them one at a time.

Then work without stopping until the milestone is complete, or one of these
genuinely applies:

- A browser authorisation or OAuth approval requires him
- A secret or credential must be entered by him into a secure interface
- A destructive or irreversible action needs explicit approval
- A legal, billing, privacy, or security decision cannot be safely inferred
- Two valid options would **materially change product direction** and neither is
  supported by the existing plan
- Reasonable workarounds are exhausted and no useful progress remains

**Never ask whether you should:** inspect a file · run tests · install a normal
local dependency · fix a clear bug · update documentation · retry a failed
command · use an obvious safe workaround · continue to the next planned step ·
commit completed work · push to this already-confirmed repo · deploy through the
already-approved path · clean up temp files you created. **Never ask anything
answerable by reading the repo, logs, docs, prior messages, or official
documentation.**

**Do not ask permission to update STATUS.md. Just update it.**

**When you hit a decision you would normally ask about:** take the conservative
option, log it in `DECISIONS.md` **in your own project folder** (every mature
project here already has one — create it if yours does not), and keep going.

**When something fails:** diagnose it → try safe workarounds → inspect logs and
config → test the fix → continue if correct. Only involve him after reasonable
options are exhausted.

**Never take a shortcut** that weakens security, deletes data, resets a
database, exposes secrets, changes the intended architecture, or lowers quality
merely to avoid asking.

**If one part blocks, do not stop everything.** Continue with all independent
work that remains — architecture, implementation, tests, documentation,
validation, cleanup, security review, and preparation for the blocked step.

**Never ask "should I continue?"** The answer is yes unless the task is complete
or an unavoidable condition above applies.

**When you do report, give ONE consolidated update:** what was completed, what
was tested, what remains, any blocker, and the exact next step.

Only genuinely stop if continuing would risk **destroying data or spending
money**.

---

## 3. Doing it yourself vs asking him

**Default: do it yourself.** If there is any path to completing a task without
him, take it — and **do not mention that you considered involving him**.

Only involve him when it is **genuinely impossible for you**: signing into an
account, approving an OAuth consent screen, entering payment details,
authorising something that needs his identity. *"It would be easier if he did
it"* is not a reason.

### When you do need him, instructions must be click-by-click

- Every step **numbered**, one action per step
- Name the exact button, tab, or field **in quotes, as it appears on screen**
- Give the **exact URL** to start at
- State **what he should see after each step**, so he knows if he is lost
- Give **exact text to type or paste** — never "enter your project name"
- Tell him **what to send back** when he is done

### CRITICAL — verify the interface before writing instructions

Your training data contains **outdated screenshots** of Google Cloud Console,
GitHub settings, Supabase, Vercel and similar. Instructions written from memory
have already sent him to menus that no longer exist and **cost him an
afternoon**.

**Before writing steps for any third-party web UI, search the web for the
current interface and cite what you found.** If you cannot verify it, say so
plainly and describe what he is looking for **functionally** — *"find the
section about API credentials, wherever it now lives"* — rather than inventing a
menu path.

**If he says an instruction does not match what he sees, do not guess a second
time.** Ask him to describe or screenshot what is on screen, and work from that.

---

## 4. How he communicates

He uses **voice dictation almost exclusively**. His messages contain
transcription errors: wrong words, mangled technical terms, missing
punctuation, sentences that trail off mid-thought.

"Kalshi" arrives as **"Calcie"**, **"cow sheep"**, **"Cauchy"**. Filenames and
numbers get garbled.

**Read for intent, not literally.** If a word makes no sense in context, work
out what it should have been and continue — **do not stop to ask what he
meant**. If the ambiguity genuinely changes what you would do, state your
interpretation in one line and proceed on it rather than halting.

---

## 5. Coordination — other sessions are running right now

Several Claude Code sessions run in parallel on this repo. **None can see each
other.** `STATUS.md` is the only shared channel.

- **Start:** `git pull`, read `STATUS.md`
- **End:** merge your changes into `STATUS.md` — **read it first, never
  overwrite another session's entries** — write `HANDOFF.md` in **your** folder,
  and **push**
- **Stage explicit paths. NEVER `git add -A`.** Two sessions have already
  cross-contaminated commits that way
- **Work only inside your own folder**

### When your work contradicts another session

**Do not silently overwrite.** Flag the contradiction in `STATUS.md` and say
**which measurement you trust and why**. This has happened twice already:

- the **Kalshi maker-fee** question
- whether the **orderbook endpoint returns data**

The coordinating chat reads this repo **over the public web**. Work that is
committed but not pushed is invisible to it. **Push or it did not happen.**

Related: [HOW_THIS_WORKS.md](HOW_THIS_WORKS.md) is the short operating manual;
this file is the detailed contract.

---

## 6. Evidence standards

**This project has produced ~45 recorded corrections. Every single one shrank
the edge. Not one ever revealed a larger effect.** The live count is the
`RETRACTED` row of the tally in [LEDGER.md](LEDGER.md) — read it there rather
than repeating a number from memory, because that number has itself gone stale
twice.

**Treat any positive result as presumptively wrong until it survives an
untouched holdout.**

- **Selecting on past performance is fine. Measuring returns over the same
  window you selected on is not.**
- **Cluster confidence intervals at the correct unit of observation, and state
  the unit.** A market settles once; 490,464 fills from 762 matches are 762
  observations, not 490,464.
- **Report effective sample size, not just nominal,** when observations are
  correlated. A 10-strike ladder is one temperature reading, not ten markets.
- **Report the naive benchmark next to every result.**
- **Report retractions as prominently as findings.** Mark them *inline where the
  claim appears* — deleting a wrong number is how someone re-derives it.
- **Reading beats scoring.** In the GitHub work, reading found 5 defects across
  3 repos that all scored well on every computed metric.

[GUARDS.md](GUARDS.md) holds **12 reusable canaries**. **Use them; do not
reimplement them.** Guard #6 is enforced repo-wide by
`common/tests/test_no_fee_reimplementation.py` — fee arithmetic has exactly one
implementation, `common/kalshi_fees.py`, and a test fails if anything copies it
again. It went from 3 copies to 17 while the rule was only a convention.

A claim that travels between projects gets a fresh row and a fresh status each
time, and **the weakest status is the one a reader finds**. Cross-reference by
number and sample size, not by project name —
`common/find_duplicate_claims.py` does this.

---

## 7. The four repos

| Repo | Visibility | What lives there |
|---|---|---|
| **trading** (this one) | **PUBLIC** | All prediction-market and signal-extraction work |
| **nexus** | private | The user's life/organisation system. ChatGPT-led |
| **Vinex-OS** | private | Window-cleaning business. Google Apps Script |
| **weather-market-bot** | private | Older trading work |

**Never mix them.** Not files, not commits, not context. If something belongs in
another repo, it goes in that repo — do not park it here "for now".

**New ideas go in [INBOX.md](INBOX.md) first**, before deciding where they
belong or whether they are any good. Routing is a separate pass.

### This repo is PUBLIC

**Never commit credentials. Never commit anything naming real private
individuals.** `data/`, `reports/`, `KNOWLEDGE.md` and `.env` are gitignored
because they hold recorded data or judgments about named people. **Check before
you stage.**

---

## 8. Machines

- **Desktop `C:\Users\vinig` — primary.** All real work happens here.
- **Laptop — a recording box only.** It runs the recorders and nothing else.

**Some recorded data exists ONLY on the laptop and is gitignored.** If a dataset
appears to be missing, it may be on the laptop rather than lost — check before
concluding anything is gone, and never "re-pull to replace" a local archive.
Kalshi's API is a ~69-day window; closed markets 404 and are gone for good.

Paths under `C:\Users\gianf\` are **laptop** paths. Several documents still
carry them from before the machine switch; treat them as historical.

---

## 9. Repo mechanics

- **`python` on PATH is a Microsoft Store stub.** Use a full interpreter path or
  a project's `.venv\Scripts\python.exe`.
- Several projects live here as siblings, each with its own venv, `DECISIONS.md`
  and `HANDOFF.md`.

### Before searching YouTube for anything, read the knowledge base

`youtube-signal/KNOWLEDGE.md` (local only, gitignored) holds YouTube content
**already read in full and scored**: tools and sites with what they actually do,
numeric claims put through a Wilson-interval check, step-by-step methods with
timestamps, and the short list of videos worth a human's own time.

It is not a summary. Every line traces to a video ID and timestamp, so a
verified repo and a marketer's assertion stay distinguishable months later.

- **Claims carry expiries.** Mechanisms and maths never expire. Procedures 12
  months, tool recommendations 4, prices/fees/API specs 3, performance
  results 3. **Check before repeating a number.**
- **`REFUTED` beats the creator's framing.** It means the stated win rate cannot
  clear its own break-even at the stated sample size. That is arithmetic.
- **S (substance) and H (honesty) are never averaged.** A high-S low-H video
  still has good tools — discount its *results*, not its tooling.
- If the topic is covered there, use it instead of guessing. If it is not, **say
  so rather than inventing sources.**

Regenerate after new videos are read:

```bash
C:\Users\vinig\trading\youtube-signal\.venv\Scripts\python.exe C:\Users\vinig\trading\youtube-signal\src\build_knowledge.py
```
