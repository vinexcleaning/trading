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
SYNC a3f9c21 · pushed · STATUS.md updated · 2026-08-04 14:32

WHAT I JUST DID — two sentences, plain English, no jargon
WHAT IT MEANS — did this help, hurt, or change nothing? If a number matters,
  say whether bigger is better and what it would have to be to be worth acting on
WHAT I NEED FROM YOU — "nothing, continuing", or a specific decision written as
  a question with the options spelled out
NEXT — one line
BRIEF — https://raw.githubusercontent.com/.../briefs/BRIEF-2026-08-04-03.md
```

### The last line: the brief address

**End the block with a `BRIEF —` line carrying the current brief address.**
After you have pushed, run this and paste its single line of output:

```bash
py -3 coordinator\brief.py url
```

**Why it is there.** The coordinating chat cannot reach a fresh page on its own.
Two things were measured against it, not assumed: `BRIEF.md` at the repo root is
**cached frozen** for it and will never update, and an address printed inside a
`.md` file is **not a link it can follow**. So it can only open an address the
user pastes.

**One paste per page is the floor. That is accepted, not a bug to engineer
around.** Putting the address at the bottom of every message is the whole fix —
it is sitting there ready to copy, and the user never has to go and find it.

**Never give out the repo-root `BRIEF.md` address.** It looks current and is
not. Give only the `briefs/...` address the command prints.

### The sync marker

The block **opens with a sync marker**, in exactly that format. **If you did no
work this turn, still emit it** with the current `HEAD`.

**Field 1 — the short commit hash of the repo's current `HEAD`:**

```bash
git rev-parse --short HEAD
```

**Run the command. Never invent the hash** — the whole point is that he can
verify it against GitHub.

**Field 2 — the state of your work. Four valid values; pick the honest one:**

| Value | Meaning |
|---|---|
| `pushed` | everything you did this turn is committed **and on the remote** |
| `local only` | you committed and **deliberately** did not push. Say why in one clause — `local only (untested, want a run first)` |
| `uncommitted` | work in progress, not yet committed. Say why briefly |
| `push failed` | you tried and it did not land. Give the reason |

**Deciding NOT to push is a legitimate call and is often the right one. Never
push work you are not confident in just to satisfy this rule.** The marker
exists to report the truth, not to force a push.

**Field 3 — whether `STATUS.md` was updated.** One of:

- `STATUS.md updated`
- `STATUS.md unchanged (no material change)`
- `STATUS.md pending (holding until X verifies)`

**Field 4 — the date and time**, `YYYY-MM-DD HH:MM`.

**Why this exists.** He coordinates several sessions through a **separate chat
that reads this repo from GitHub over the web**. That chat can **only see pushed
work**. When your marker says anything other than `pushed`, he knows the
coordinating chat is looking at an older state — which is fine, as long as
everyone knows it. **Silence about it is the problem, not the unpushed work.**

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

### The one exception: a NEW IDEA gets a plan first, then a pause

**Added 2026-08-08, and it is the only thing that overrides "never ask, just
continue".** When he brings a new idea — a hypothesis, a thing to test, a
strategy — **do not start.** Reply first with, in plain English and under a
page:

1. **What you understand the idea to be**, in your own words. If you have it
   wrong, that is the cheapest possible moment to find out.
2. **What you would actually do** — the data, the sample, the unit of
   observation, roughly how long.
3. **What could go wrong** — the ways this measurement could produce a number
   that looks real and is not.

Then **stop and wait.** He knows things about these sports that are not in this
repo and not in your training, and the whole point of the pause is to let him
put that in before the work is shaped around a wrong assumption.

**Once he says go, execute all the way through without asking anything else.**
The pause is once, at the start, on the idea. It is not a habit of checking in.
Everything in this section still applies from that point on: no progress
reports, no "should I continue", conservative choice logged in `DECISIONS.md`
and keep moving.

**This does not apply to work already agreed** — continuing a running test,
fixing a bug, answering mail, finishing a milestone. Those start immediately,
exactly as before.

### When you disagree with one of his ideas

Say so — he would rather be corrected than agreed with. But **"we tried that"
is banned**, and so is every version of it: *"already tested"*, *"that's been
done"*, *"same as the X study"*. Those sentences hide the only thing that
matters, and one of them has already killed a live idea in this repo.

If you think an idea will not work because of past work, you must give **all
five** of these or you have not made the argument:

1. **What was tested**, in the words it was recorded in, with its ID.
2. **What the data was** — how many observations, and what *one* observation
   was.
3. **What dates** the data covers.
4. **What came out**, and whether it was later corrected.
5. **How his version differs from it** — or an explicit *"I cannot tell whether
   this is the same question"*.

Point 5 is the one that matters and it is the one that gets skipped. The
recorded failure: the tennis work swept **price and market features** and found
nothing, and that sweep was cited to close down a question about **individual
players**, which it never tested. Running a test twice is cheap. Deleting a live
idea is not, and nobody ever finds out it happened.

`py -3 coordinator\idea.py check --idea "..."` prints those five fields for
every related claim in every ledger. Use it rather than arguing from memory.

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

### The brief: ONE file, one section each (changed 2026-08-07)

**There is one brief for the whole repo: [BRIEF.md](BRIEF.md) at the root.** It
replaced six separate `BRIEF_*.md` files. **Do not create `BRIEF_*.md` any more,
dated or otherwise** — the coordinating chat has been pointed at `BRIEF.md` and
will not read anything else.

At the end of every session, write **your own section only**:

```bash
py -3 coordinator\brief.py write <slug> --file <a file holding your section>
```

Slugs: `tennis` · `mlb` · `devig` · `signal` · `coordinator`. That command
replaces only the text between your two markers, re-reads the file inside a
lock, and has no whole-file mode — so it cannot flatten another session's
section. Same content rules as before: `## Title`, an `**As of YYYY-MM-DD.**`
line, under 20 lines, plain English, no acronyms.

`STATUS.md` is unchanged and still the detailed channel *between* sessions.
`BRIEF.md` is the short channel *out*.

### Declare your state in four lines, so the coordinator quotes you

The coordinator answers *"where is everything at"* with one table: which chat ·
doing now · what's left · is its background test alive · does it need the user.
**The two middle columns can only say what you last wrote down.** Put this
anywhere in your own `HANDOFF.md` (or in your `BRIEF.md` section) and update it
when it stops being true:

```
<!-- COORDINATOR-STATE
doing: one line, present tense, what you are working on
left: one line, what still has to happen
needs: no
-->
```

`needs:` is `no`, or `yes - <the question, in one line>` — that line is shown to
the user verbatim. It is an HTML comment, so it is invisible in rendered
Markdown. **Without it your two columns are guessed out of your `HANDOFF.md` and
marked `~`**, and the guesses have already described the wrong folder once.

### Check your mailbox at the start of every session

`coordinator/mailbox/<your-slug>/` holds instructions addressed to you. **Read
it before you start work.** To answer, edit the message file itself: change
`Status: OPEN` to `Status: DONE` or `BLOCKED`, and type under the reply line.
No script to run.

**This is the one documented exception to "work only inside your own folder":**
you may write inside `coordinator/mailbox/<your-slug>/` and nowhere else in
`coordinator/`.

### The dictator chat is the window he actually talks to

He does not open five windows and type into each. He talks to **one** window —
the **dictator chat**, documented in [DICTATOR.md](DICTATOR.md) — and it files
instructions into your mailbox. **It does no project work**, so nothing it
writes competes with yours.

What that means for you:

- **An idea may arrive as mail rather than as a typed prompt.** It comes with a
  prior-work section listing every related claim in every ledger, with what was
  tested, on what data, over what dates. **Read that before writing code**, and
  record in your `DECISIONS.md` whether it is the same question as any of it.
- **Your opening line is `next`.** He types one word. Everything you need is in
  the mailbox and in this file. If your window needs anything else typed, that
  is a defect in your own `HANDOFF.md`, not something for him to remember.
- **Your name is in `coordinator/chats.json`.** If a new chat is spun up for
  work that overlaps yours, that file is where the folder ownership is settled.

Related: [HOW_THIS_WORKS.md](HOW_THIS_WORKS.md) is the short operating manual;
this file is the detailed contract.
[coordinator/COORDINATOR.md](coordinator/COORDINATOR.md) is the design of the
coordinator and, explicitly, the list of what it cannot do.

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

---

## 9b. Four lines that get re-argued, and the answers. Hold them.

**Handed over 2026-08-08 from the chat that had been coordinating this work.**
Each of these has come back more than once. Each answer is arithmetic or a
measurement, not an opinion, so **agreeing to re-open one is not being helpful.**

**1. A money target with a deadline.** "$80 to $180 in a week" needs roughly a
**15% edge per trade**. The largest real effect ever measured in this repo is
**2.4pp against a 3.6pp cost bar** — i.e. negative. Refuse the deadline, not the
ambition. **A deadline silently changes what counts as evidence**, which is how
every one of the 51 retractions started.

**2. Anything trading live and in-play.** His own bot was reading scores after
**97.4% of the price move had already happened** (n=4,398 score-change events),
and stop-and-re-enter turned **−2.29¢ into −9.36¢**. **Paper only.** This is not
a maturity gate that time passes; it is a latency measurement.

**3. "The $25 to $130 run proves something."** It was **buying heavy
favourites** — many small wins, then one loss that eats thirty. The same shape
was separately tested and is negative twice (**B024**). Do not let it be
re-derived under a new name.

**4. He chases a new idea before finishing the last one, and asked to be told.**
So tell him — once, plainly, as a fact about the queue, and then do the work
anyway if he says go. **It is his call, not a veto you hold.** The useful form
is *"tennis is two months out and baseball three weeks; this is a new thing —
here is what it costs in attention"*, not a lecture.

**The limiting factor is attention, not ability.** He is also in school with an
SAT coming. **Anything that can be answered offline on free historical data
costs him nothing but the reading** — prefer that shape over anything that needs
him to babysit a process.

---

## 10. What every folder is, and what every folder must have

**Added 2026-08-08 after reading all 23 project folders on disk.** Sessions have
been briefed separately and have drifted. Everything below was read off the
files, not off anyone's account of them. **If a rule is not in this file it is
not shared** — so the conventions that only some folders follow are written
down here, and the folders that do not follow them are named.

### The folders, and which chat owns each

| Folder | What is actually in it | Owner |
|---|---|---|
| `tennis-paper-forward` | 16 bots paper-trading live Kalshi tennis. Own venv, own tests, `test_paper_only.py` enforces no order code | tennis |
| `set1_overshoot` | Finished study: does the market overshoot after set 1. 97 hypotheses, mostly nulls and retractions | tennis |
| `kalshi-tennis` | Finished data audit of Kalshi's tennis book. Coverage and leak findings | tennis |
| `mlb-paper` | 16 bots paper-trading Kalshi baseball. Own venv, three test files, one of them a paper-only canary | mlb |
| `mlb` | Loose scripts: Statcast pulls, in-play latency, data hunting. **No README, no HANDOFF, no DECISIONS** | mlb |
| `bot-hunt` | The live de-vig and market-making work. Largest active codebase, own venv, two pre-registrations | devig |
| `crypto` | Bitcoin/ETH ladder study: fat tails, arbitrage, maker viability. Own tests | devig |
| `kalshi-market-scan` | Exchange-wide screen: weather models, flow, capacity. 4,597 files, own venv. **No HANDOFF** | devig |
| `market-selection` | Which market families are worth trading. **No README, no HANDOFF** | devig |
| `signal-github` | 24,940 files. Scores public trading repos for whether they really trade | signal |
| `youtube-signal` | Reads video transcripts into a scored knowledge file. **No DECISIONS** | signal |
| `social-signal` | Reddit/Discord/X/TikTok extractors, joined across platforms | signal |
| `extractor-upgrade` | Rebuild of the extraction pipeline. Opens sibling databases read-only, on purpose | signal |
| `bot-forensics` | Reconstruction of a real bot's real trades. The only project about money that moved | signal |
| `coordinator` | The dictator chat's tools. No network, no credentials, enforced by test | coordinator |
| `common` | Shared code. **`kalshi_fees.py` is the only fee implementation in the repo** | coordinator |
| `runners` | The watchdog registry for background tests on this machine | coordinator |
| `wallet-copy-study`, `soccer`, `ptis-polymarket`, `polymarket-tennis-copy`, `kalshi-inplay-bot`, `kalshi-chat-audit`, `discord-trades-export` | Dormant. No commits since 2026-08-05 or earlier. Their claims are still live in `LEDGER.md` and still count | nobody |

**A dormant folder is not a dead claim.** `wallet-copy-study` has 29 ledger rows
and has not been touched since 2026-08-03; those rows still get cited.

### The four files every active folder has, and who is missing one

- **`README.md`** — what this folder is, in the first three lines, for someone
  who has never seen it.
- **`HANDOFF.md`** — the detail of where it got to. *Missing from:*
  `kalshi-market-scan`, `market-selection`, `mlb`, `soccer`.
- **`DECISIONS.md`** — every judgment call taken without asking, and why.
  *Missing from:* `kalshi-tennis`, `mlb`, `signal-github`, `soccer`,
  `youtube-signal`.
- **`PREREGISTRATION*.md`** — what a test had to clear, committed **before** the
  first result existed. Only 7 folders have one.

**If you own a folder in one of those "missing" lists, create the file this
session.** It is ten minutes and it is the difference between a result being
auditable later and being taken on trust.

### Pre-registration: the naming is now fixed

There are five different names on disk (`PREREGISTRATION.md`,
`PREREGISTRATION_DEVIG.md`, `PREREGISTRATION_T6.md`, `PREREGISTRATION_PARTB.md`,
`PREREGISTRATION_MAKER_VIABILITY.md`), which is why nothing can count them.
**New ones are `PREREGISTRATION_<SHORTNAME>.md` in the folder that runs the
test. Do not rename the existing five** — a pre-registration that changes after
results exist is worthless, and that includes its filename in a git log.

Every one must state, before any result exists: the hypothesis · the unit of
observation · the sample · the date range · the holdout split · **and what
result would make you drop the idea.** The last one is the one that gets left
out.

### Paper-only is enforced by a test, not by a promise

`tennis-paper-forward/tests/test_paper_only.py` and
`mlb-paper/tests/test_paper_only.py` walk every source file in their project and
fail if order-shaped code or a credential appears.
`coordinator/tests/test_no_money_no_network.py` does the same for the
coordinator.

**Any new folder that touches a live venue gets one of these before it gets its
first feature.** Copy the existing test; do not invent a third style.

### Which Python, everywhere

`python` on PATH is a Microsoft Store stub and will fail strangely. Eight
folders have their own `.venv` (`bot-forensics`, `bot-hunt`,
`extractor-upgrade`, `kalshi-market-scan`, `mlb-paper`,
`polymarket-tennis-copy`, `tennis-paper-forward`, `youtube-signal`) — **use that
folder's `.venv\Scripts\python.exe`.** Everything else uses `py -3`.

**Never write an absolute interpreter path into a document.**
`wallet-copy-study/HANDOFF.md` names `C:\Users\gianf\AppData\...\Python312`,
which is a machine that is no longer the primary one, and following it fails.

### `C:\Users\gianf\` is the laptop and is historical

Fifteen documents still carry those paths. **They are not errors to fix in bulk
and not paths to follow.** If you are editing a document that has one, correct
that one line to the desktop path or mark it historical. Do not sweep the repo
for them — several are accurate records of where a dataset actually still lives.

### Declare your state where the coordinator can find it

The `COORDINATOR-STATE` block (§5) may live in **either** your `HANDOFF.md`
**or** your `BRIEF.md` section. Both are read. Two chats use each right now, and
that is fine — what is not fine is neither.

### Two runner registries exist and they do not match

`runners/runners.json` lists what *runs* on this machine (`tennis`, `mlb`).
`coordinator/runners.json` lists how to tell whether each background job is
*producing anything* (`tennis-forward`, `mlb-paper`, `crypto-tape-pull`,
`tennis-depth-recorder`, `crypto-15m-opens`). They answer different questions
and are deliberately not merged, but **a new background job has to be added to
both** or it is either unwatched or unrestarted. Every run of
`coordinator\dictator.bat` prints anything in one and not the other.
