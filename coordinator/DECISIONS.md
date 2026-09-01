# DECISIONS.md — coordinator

Judgment calls taken without asking, per `CLAUDE.md` §2. Each one names the
conservative alternative that was rejected, so it can be reversed.

---

### D1 — One `BRIEF.md` with HTML-comment section markers, not one file per project

**2026-08-07.** The alternative was to keep separate files and just enforce fixed
names. Rejected: the coordinating chat then has to fetch N URLs and work out
which are current, which is the job we are trying to remove. Markers are
invisible in rendered Markdown on GitHub, so the page reads as one document.

**Reversible:** the sections are ordinary Markdown between comments. Splitting
them back out is a ten-line script.

### D2 — Deleted the three dated brief files; left the three fixed-name ones as redirect stubs

**2026-08-07.** `BRIEF_2026-08-07.md`, `BRIEF_DEVIG_2026-08-07.md` and
`BRIEF_TENNIS_2026-08-07.md` were duplicates or frozen snapshots of the
fixed-name files. Deleted — content is in `BRIEF.md` and in git history.

`BRIEF_TENNIS.md`, `BRIEF_MLB.md` and `BRIEF_DEVIG.md` were **not** deleted but
replaced with a three-line redirect, because the coordinating chat may hold those
URLs and a 404 tells it nothing while a redirect tells it exactly what happened.

**This edited files owned by other sessions**, which `CLAUDE.md` §5 discourages.
Taken because the user's instruction was explicitly to migrate them and tell the
other sessions, and because leaving six brief files in place is the problem being
fixed. Flagged to the user rather than done quietly. Each owning session also has
a mailbox message saying so.

### D3 — The mailbox reply protocol is "edit the file", not "run a command"

**2026-08-07.** A CLI for replying would be tidier and would give real read
receipts. Rejected: a session that has to learn a tool to answer will skip it,
and the whole value is that instructions actually get answered. Editing a
Markdown file is what a session does anyway.

**Cost, accepted:** there is no true read receipt. `Status: OPEN` counts as
unread. A session that reads a message and does nothing is indistinguishable
from one that never looked.

### D4 — Sessions may write inside `coordinator/mailbox/<their-slug>/`

**2026-08-07.** This is a documented exception to `CLAUDE.md` §5. The
alternative was a reply channel inside each session's own folder, which the
coordinator would then have to discover by scanning every project. Rejected as
more moving parts for no gain. The exception is narrow: own mailbox folder only.

### D5 — Standard library only, no virtual environment, `py -3` launcher

**2026-08-07.** `python` on PATH here is a Microsoft Store stub. A dedicated
venv would be one more thing to create and keep alive for three small scripts
that import nothing external. `start.bat` tries `py -3`, then the known absolute
interpreter path, then two project venvs, and fails with a plain-English message
rather than a traceback.

### D6 — The coordinator makes no network call at all, not even a read

**2026-08-07.** It could usefully fetch the GitHub commit list to compare
against local `HEAD`. Rejected: "makes no network call of any kind" is a claim a
test can enforce and a non-engineer can trust, and the same information is
available from `git log origin/main..HEAD` locally. Trading credentials and a
coordination tool should never be one review away from each other.

### D7 — A `signal` section was written by the coordinator, not by that workstream

**2026-08-07.** No session has touched those folders since 2026-08-05, so
`BRIEF.md` would have had a hole where a real workstream should be. The section
is labelled at the top as written by the coordinator from repo state and not
re-audited. The conservative alternative — leave it blank — was rejected because
a missing section reads as "nothing here" rather than "nobody has reported".

### D8 — The freshness check is "is this commit findable", not "is this the newest commit"

**2026-08-07.** The first version of the stamp said *"if the newest commit on
GitHub is not `X`, you are reading a cached copy"*. **That was wrong and would
have fired on every single read.** The stamp is written *before* the commit that
carries it exists, so it can never name that commit — it always lags by one.

Reworded: the commit named must be **findable in the history**. If it is not,
the page predates it and is cached. Being one or two commits behind is normal
and the stamp now says so. A check that cries wolf every time is worse than no
check, because it trains the reader to ignore it.

**Caught by pushing and looking at the result**, not by a test. There is no test
for this; the honest statement is that the wording is verified by eye.

### D9 — RETRACTED: the `?v=` cache-buster. Replaced by a chain of dated paths.

**2026-08-07.** D8 and §7 of `COORDINATOR.md` both told the coordinating chat to
fetch `BRIEF.md?v=<hash>`. **The user tested it and it does not work.** That
fetcher keys its cache on the **path** and discards the query string: a request
for `?v=f9b4d3f` returned the body cached under `?v=13b8e61`. No
query-parameter scheme can work against it.

**I asserted this without testing it.** It is exactly the failure this repo
keeps recording — a mechanism that sounds right, stated as though measured.
Marked inline in `COORDINATOR.md` §7 rather than deleted.

**Replacement:** every generation of the page is also written to a permanent
path, `briefs/BRIEF-<date>-<NN>.md`, plus a per-day page. Each page names the
path of the next one. The reader follows next-links until one 404s. A cached
entry point is no longer a dead end, because the frozen copy still carries a
forward link.

**Rejected alternative:** a single rolling `briefs/latest.md`. Same path every
time, so the same cache freeze, one file later. The whole point is that the path
must differ.

**The cost, accepted:** the folder grows by one small file per *changed*
generation. Identical content does not mint a page. And the reader must be
willing to follow a link — a reader that only re-fetches one URL cannot be
rescued by anything here.

**New failure mode, guarded:** a snapshot on disk but not pushed makes the next
link 404, and a walking reader then believes a stale page is the newest. That is
silent and points the wrong way, so `scan.py` reports unpushed snapshots as the
first item in the digest, and `brief.py check` fails on any gap in the
numbering.

### D10 — RETRACTED: "no user copy-paste". One paste per page is the floor.

**2026-08-08.** A connection test settled three things, each of which killed an
assumption I had shipped as though it were measured.

1. **`BRIEF.md` at the repo root is permanently frozen for that reader.** The
   word `PELICAN` was pushed into the page. The chat found it at
   `briefs/BRIEF-2026-08-08-01.md` and **not** at `BRIEF.md`. That address
   cached on first fetch and has never updated. **It is no longer given out.**
2. **The `briefs/` pages work.** Fresh content, correct stamp, first try.
3. **The chain cannot be walked automatically.** An address printed inside a
   plain-text `.md` is not a link that fetcher follows. D9's "the reader follows
   next-links until one 404s" **is retracted** — it can only open an address the
   user pastes.

**So the claim that instructions and briefs would flow with no user copy-paste
is withdrawn.** Three attempts to remove that paste have now failed on three
different mechanisms. The user's call, and the right one: **accept it rather
than engineer around it.**

**What replaced it:** every session's closing block now ends with a `BRIEF —`
line carrying the current address (`CLAUDE.md` §1). `py -3 coordinator\brief.py
url` prints it alone. The paste stays; the *hunting* for what to paste is gone.

**Also changed in the pages themselves:** they no longer advertise a next
address. Promising a walk the reader cannot do is worse than promising nothing,
because the 404 reads to it as "nothing newer exists" — the failure points the
wrong way. Each page now says: this page never changes, and to get a newer one,
ask the user for the address at the bottom of their last session message.
`tests/test_brief_chain.py` asserts the page does **not** contain a next
address.

**What is unchanged and still earning its keep:** one permanent address per
changed generation, never rewritten. An immutable page cannot go quietly stale —
what it says is what was true at its timestamp. That property is why the test
passed at all.

### D11 — The background-test check has four states, not two

**2026-08-08.** The obvious design is ALIVE / STALE. It was rejected after
looking at real data: `crypto/data/tape_pull.log` **completed cleanly** on
2026-08-07 and ends `== DONE`. A two-state check calls that STALE forever.

That is exactly the failure already recorded as **D8** — a check that cries wolf
on every run trains the reader to ignore it, which is worse than having no
check. So one-shot jobs are registered as one-shot, declare the line they print
when they finish, and read **FINISHED**.

The fourth state, **NEVER RUN**, separates "the log is old" from "the log has
never existed", because those need different actions.

**Reversible:** the states are computed in one function, `runners.check()`.

### D12 — A runner on the laptop is reported as unobservable, never as dead

**2026-08-08.** `STATUS.md` lists two recorders running on the laptop under
`C:\Users\gianf\...`. From the desktop those paths do not exist, so the naive
answer is STALE — and it would be **wrong every single time**, about the one
dataset in this repo that cannot be re-pulled.

They carry `"machine": "laptop"` and read **"can't see from this machine"**.
Saying "dead" about something you cannot observe is worse than saying nothing.

**The cost, accepted:** if a laptop recorder really does die, nothing here will
notice. That is a genuine hole and it is not papered over.

### D13 — "Doing now" and "what's left" are quoted where possible and marked `~` where guessed

**2026-08-08.** The user asked for a table with those two columns. Nothing on
disk holds them: a session's current task is in its head, not in a file.

Three options were considered.

1. **Guess from `HANDOFF.md` and present it plainly.** Rejected — a guess that
   reads as a fact is the failure mode this whole repo is organised against.
2. **Leave the columns out.** Rejected — he asked for them, and the information
   does mostly exist, just unlabelled.
3. **Taken:** an optional `<!-- COORDINATOR-STATE -->` block a session writes
   about itself, which is **quoted**; a guess from `HANDOFF.md` when there is no
   block, prefixed `~`; and a printed count of how many of each, every run.

At the time of writing that count is **1 of 5** — only `coordinator` has
declared. A mailbox message went to the other four. **If they ignore it the
table stays mostly guesses, and it will keep saying so.**

**Two bugs in the guesser were found by looking at its output, not by a test**,
and both are now tested:

- It ordered `HANDOFF.md` files by modification time, so the tennis row
  described `kalshi-tennis` — an old analysis folder — instead of
  `tennis-paper-forward`, the thing actually running. Registry order encodes
  which folder *is* the workstream; a timestamp does not.
- Its "what's left" heading pattern matched a bare `next`, which caught *"what
  the next session should do"* in `bot-hunt/HANDOFF.md` and put a sentence about
  reading order into a column the user acts on.

### D14 — The prompt text moved out of `newprompt.py` into `prompt_template.md`

**2026-08-08.** The generated prompt tells a new session to pull the repo, and
`tests/test_no_money_no_network.py` fails any coordinator `.py` file containing
the name of a writing git verb. The canary fired.

**The canary was not weakened.** Two alternatives were rejected: rewording the
prompt to dodge the string (degrades the prompt to satisfy a scanner), and
adding an exemption list to the canary (every exemption list eventually holds
the thing it was meant to catch).

Prose telling a *different* session what to run is not an action, and the canary
already exempts documents. So the text lives in `prompt_template.md`, and the
canary **gained** a check that the template exists and is not near-empty —
because when it goes missing the temptation is to paste the text back into the
module.

**Judgment call flagged for the user:** this is the coordinator deciding how one
of its own guards should read. The guard got stricter, not looser, but it is his
to overrule.

### D15 — `newprompt.py` copies the idea verbatim and cross-checks by keyword only

**2026-08-08.** It could summarise or sharpen the idea before writing the
prompt. Rejected: "it reports state, not truth" is the line the coordinator does
not cross, and paraphrasing a one-sentence idea is where a misunderstanding gets
laundered into an hour of a session's work.

It does do a **keyword** overlap check against `LEDGER.md`, `INBOX.md` and
`SCOREBOARD.md` and prints the hits, flagged as *possibly related, go and read
it*. On the first real test — *"test de-vig against a retail bookmaker with a
fat margin instead of Pinnacle"* — it surfaced the exact `INBOX.md` line where
that idea is already queued, plus three related `LEDGER.md` rows. **That is one
useful hit, not a validated retrieval rate**, and the prompt says so: keyword
matching misses every paraphrase, so a clean cross-check is not clearance.

### D16 — The coordinator added a paragraph to the repo-root `CLAUDE.md`

**2026-08-08.** Adding `COORDINATOR-STATE` to §5 touches a file every session
loads and nobody owns, which `CLAUDE.md` §5 itself discourages.

Taken because a convention that lives only in `coordinator/README.md` will be
read by nobody — the same reasoning that put the mailbox rule in `CLAUDE.md` on
2026-08-07, and the same reasoning behind the fee formula reaching 17 copies
while its rule was only a convention. The addition is **additive, four lines,
and touches no existing text.** Every session also has the mailbox message.

**Flagged rather than done quietly**, and trivially reversible.

### D17 — The laptop recorders are registered as "confirmation-monitored", which is NOT monitoring

**2026-08-08.** The user asked directly: *"add them to runners.json as
monitored-only if you can, or tell me plainly why not."*

**Monitoring is not possible from this machine, and no config change makes it
possible.** Checked rather than assumed:

| Channel | State |
|---|---|
| shared or mapped drive | **none** — only `C:` and `D:` exist here |
| network call | forbidden by **D6** and enforced by test; also no endpoint |
| cloud-sync folder | none present |
| git | the recorders' data is gitignored and they push no heartbeat |

There is no signal. A registry entry that produced `ALIVE` from an edited
config would be the worst outcome available, because these two recorders are
accruing the one dataset in this repo that **cannot be re-pulled at any price**.

**What was done instead.** They carry `"monitor": "confirmation"`. The
coordinator tracks how long ago a **human** last confirmed them, nags when that
goes stale, and prints the exact check. Two states, named so they cannot be
misread — `CONFIRMED (by hand)` and `CHECK IT BY HAND` — and neither contains
the word ALIVE, which a test asserts.

**This monitors a check-in, not a recorder.** One can die a minute after a
confirmation and the page reads `CONFIRMED` for the rest of the window. That
sentence is printed next to the state every single time.

**Why it is still an improvement.** The old behaviour said *"can't see from this
machine"* and set `needs_a_human = False`, so the row **never appeared under
"what needs you" again**. The hole was not merely unmonitored, it was silent.
It now nags every 24 hours.

**Rejected: a git-carried heartbeat** — the laptop writes a timestamp file and
pushes it on a timer; the coordinator reads the timestamp out of the committed
file. It would be real monitoring. Not built, because it is work on the laptop,
requires git to be able to push from there (unverified), and adds a commit
every few minutes to a public repo. **Shipping it as an entry while the writing
half did not exist would be an asserted-not-measured claim**, which is the
failure this repo keeps recording. It is written down here as the one option
that would change the answer, with its cost, and it is the user's call.

**`confirm` refuses to run on a heartbeat-watched runner** — that would replace
a measurement with an opinion.

### D18 — The two runner registries are compared, not merged

**2026-08-08.** Another session built `runners/` — a shared watchdog with its
own `runners.json` — while this work was in flight. There are now two lists
naming the same runners.

Merging them was rejected: they answer different questions. `runners/` owns
**what runs** (folder, interpreter, arguments, how to prove it is safe).
`coordinator/runners.json` owns **whether it is producing anything** (heartbeat
files, thresholds, one-shot versus continuous, plain English).

But two lists of the same runners drift, and the record here is the fee formula
reaching 17 copies while its rule was only a convention. So every run compares
them and reports a runner in one and not the other — in both directions, each
with the specific failure it would cause:

- watchdog starts it, nothing watches it → *restarted forever while writing
  nothing, and this page never mentions it*
- watched here, watchdog will not start it → *stays down after a reboot, and
  the row reads STALE with no explanation*

**That catches drift. It does not prevent it.**

**Consequences absorbed the same day:** both restart instructions were rewritten
— the answer is no longer `deploy\run_forward.bat` but *"the watchdog restarts
it within 10 minutes; if it is STALE for longer, the watchdog is what stopped"*
— and `logs\wrapper.log` was added as the first heartbeat for both tests.

### D19 — Two overclaims were caught by tests and are recorded rather than quietly fixed

**2026-08-08.**

1. **The table said *"the laptop recorder is not running"*.** It cannot know
   that. The only true statement is that nobody has confirmed it. This is the
   exact failure the confirmation mechanism exists to prevent, and it shipped
   inside the same change that introduced the mechanism. A test now asserts the
   words are not used about anything this machine cannot see.
2. **The error path had an error in it.** `Path.relative_to` raises on a path
   outside the repo, and it was used inside the message reporting a *missing*
   watchdog registry — so the report about the broken thing was itself a crash.
   Found by pointing the registry at a temp folder in a test.

Fixing (1) required attributing every "needs you" reason to its source. A reason
the **coordinator derived** is its own claim and must survive *how do you know
that*. A reason a **session declared** is that session's text, quoted, and is
not the coordinator's to reword — it is now printed with *"that chat said so, in
its own words"*.

---

### D20 — The dictator chat is a *name for a window*, not a new folder

**2026-08-08.** The instruction was to build "the dictator chat" — the one
window the user talks to. The obvious reading is a new top-level folder. That
was rejected.

The mailbox, the brief writer, the state scanner, the runner check and the
naming registry are all already in `coordinator/`, and they are exactly what a
main chat needs. A second folder would have produced **two lists of the same
five workstreams**, which is this repo's recorded failure mode — the fee formula
reached 17 copies while its rule was only a convention, and there are already
two runner registries that have to be compared every run because they drifted.

So: the tools stay in `coordinator/`, and [`DICTATOR.md`](../DICTATOR.md) at the
repo root is the document the user reads. **"Dictator chat" names the window;
`coordinator/` is where its tools live.** The chat is registered under the
existing `coordinator` slug so nothing about the mailbox, the brief section or
`scan.py`'s workstream list had to change.

### D21 — Two signals for routing an idea, kept apart, and "cannot tell" is allowed

**2026-08-08.** The first version routed a new idea to whichever chat owned the
folders the related prior work sat in. It sent *"de-vig a retail bookmaker on
baseball"* to the **tennis** chat, confidently.

The cause is structural, not a bug: several `LEDGER.md` tables have **no project
column at all** — the whole MLB and de-vig block is one of them — so those
workstreams are invisible to a folder-based vote, while `set1_overshoot` and
`kalshi-tennis` have ~55 rows between them and win every count.

The fix is two signals that are **never added together**: (1) does the idea name
a chat's own subject, from a hand-written `subjects` list in `chats.json`;
(2) whose folders does the related work sit in. Signal 1 wins where it fires.
Where they disagree the answer is **"could not tell"**, which costs one question
and is cheaper than delivering work to a chat that does not own the folders.
Four cases are pinned in `tests/test_dictator.py`.

**Adding a subject word is a config line, not a code change.** That is
deliberate — the alternative is tuning a scorer, and a tuned scorer is a thing
nobody can audit later.

### D22 — Ranking alone is not allowed to decide what the user sees

**2026-08-08.** The prior-work check ranks related claims. On its **first run**
it demonstrated its own founding failure: asked about *individual tennis
players*, it buried **B023** — the pre-match player-feature sweep, which is the
single row anyone must read before calling that idea settled, and the row whose
misuse the user cited as the reason for this whole build.

Three changes, in order of how much they mattered:

1. **A per-word pass.** For every distinctive word in the idea, show what the
   repo has on *that word*, preferring claims that are actually about it. This
   is a mechanical guarantee, not a better ranking, and it is what surfaces
   B023.
2. **Rare words count for more**, so a distinctive word is not drowned by
   `tennis`, which appears in 152 claims.
3. **A word in the CLAIM counts triple** a word anywhere else in the row. A row
   whose *sample* is counted in players is not a row *about* players.

**One ranked list will always bury something.** The design conclusion is to stop
relying on one.

### D23 — An escaped pipe inside a table cell was silently shifting columns

**2026-08-08.** One `LEDGER.md` row writes an absolute value as `max\|t\| 4.17`.
Splitting table rows on every `|` shifted that row's later columns by two, which
put its STATUS in the wrong field. **Seven rows read as status unknown**, and
B023 — again — was one of them, so the closest related claim to a live question
was also the one whose result could not be read.

The parser now splits on unescaped pipes only. `?` statuses went from 7 to 1,
and `test_dictator.py` fails if more than 5% of rows lose their status, because
the visible symptom of a future column shift is the same.

### D24 — The prior-work report is structured so that "we tried that" is not sayable

**2026-08-08.** The user's stated rule: never *"we tried that"*. A convention
would not have held — this repo's own record is that conventions decay — so it
is enforced by the shape of the output instead.

Every related claim prints six fields, and a test fails if any of them is
dropped: what was tested · the data, with the unit · the dates · what came out ·
**what the row does not cover**, derived mechanically from its own sample and
date range · **which words from the new idea appear nowhere in that row**.

That last field is the one that does the work. It is computable, it cannot be
fudged, and it points straight at the difference. A further test fails if any
banned phrase appears anywhere in the list of hits.

**What it still cannot do:** decide whether the difference matters. That is a
judgement, it is left blank on purpose, and the report says out loud that an
unanswerable comparison must be reported as *"go and read it"* rather than as
*"already tested"*.

---

## 2026-08-18 — answered "how long to recover my $100", with the range, not a number

**He asked**, at $61.19 with a $50 floor: how many days to get back to $100 at
the current rate. **A fair question, and it is the shape `CLAUDE.md` §9b #1
warns about** — a money target acquires a deadline, and a deadline changes what
counts as evidence. **I answered the arithmetic rather than refusing it**, and
gave the range instead of a single number, because a single number here would
be a prediction dressed as a fact.

**Method.** 600 runs from $61.19, 5% a bet, 7 signals a day, money back after
1.3 days, hard stop at the floor. Per-bet outcomes drawn two ways: from
`starter__hold`'s own 72 settled bets, and from the market's own prices with the
real fees — i.e. the same bot with no skill whatever.

| | back to $100 | median days | stopped out at the floor |
|---|---|---|---|
| if the strategy is as good as its record | **57 in 100** | 21 | 11 in 100 |
| if it has no edge at all | **10 in 100** | 20 | 26 in 100 |

**The honest statement is "about three weeks IF it works, and whether it works
is exactly the open question."** The median days barely differ between the two
rows — **speed is not the thing that separates them, and quoting the 21 days
without the 57-in-100 beside it would be the whole lie.**

**And the floor table, which is the decision he actually has in front of him:**

| floor | if the strategy is real | if it is not | most he can lose |
|---|---|---|---|
| $50 | 57 in 100 | 10 in 100 | $11.19 |
| $40 | 84 in 100 | 18 in 100 | $21.19 |
| $30 | 94 in 100 | 21 in 100 | $31.19 |

**Lowering the floor is not a recovery-speed setting. It is a bet on the
strategy being real** — it buys a great deal if it is (57 → 94) and almost
nothing if it is not (10 → 21), while the chance of being stopped out nearly
doubles (26 → 45 in 100). **Recorded so that if the floor is later lowered,
what it was known to be at the time is on the record.**

**Left open deliberately.** The floor is his money and his call. Nothing was
changed. `livedesk` has been told in mailbox 014 not to touch
`account_floor_usd` unless he says so in his own words.

**Not commented on:** he mentioned he may place his own bets separately to
recover faster. That is a different account, this chat cannot measure it, and
the repo's own record of that shape is §9b #3. Stated once to him, not argued.


---

## 2026-09-01 — added the argmax line to the Critic checklist without asking

**The audit scored guard #17 (the argmax null) as prose-only, and it guards the
failure this repo repeats most.** A mechanical test would lint reports for
"best of" without a shuffle control and would false-positive constantly, so the
honest enforcement point is the Critic pass every report already runs.

**Judgment call taken:** one required line added to `REFLECT.md` §3. This is my
own checklist file; the conservative option was tightening review rather than
adding a repo-wide test, which stays his decision (scoped in
`AUDIT_2026-09.md`). Reversible by deleting the line.

### D-model — His model rule, 2026-09-01, recorded verbatim in intent

Dictator runs on **Opus** by default. **Fable** is for audit-shaped work:
hostile re-reads, verifying a finding before he acts, recurring bugs a chat
cannot shake. He set a standing ask: any dictator session should proactively
recommend a Fable switch when a task fits — including temporarily switching a
specific worker chat (he named strategy-factory and the extractors chat).
He does the switching; our job is only to say so. Current session stays on
Fable until the test-less-folder code read is done, then back to Opus.
