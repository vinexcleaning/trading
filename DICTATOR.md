# DICTATOR.md — the one chat you talk to

This is the window you open. It is called the **dictator chat** because you
dictate to it and it does the routing. **It does no project work.** It does not
run tests, does not analyse markets, does not write trading code. It reads what
the other chats have written down and it files instructions to them.

It lives in this repo. It has no server, no login, no app. Starting it is
opening a Claude Code window here and saying one sentence.

> **Read section 1 before section 2.** Section 1 is the list of things this
> chat cannot do, and it was written before any of the code. Everything in it
> is a real limit, not a to-do list. The repo's own record is that a tool
> described by its best case gets trusted past its actual case.

---

## 1. WHAT THE DICTATOR CHAT CANNOT DO

### It cannot place a trade, and it cannot hold a password

There is no key, no password, no token, and no `.env` file anywhere in
`coordinator/`. It makes **no network call of any kind** — not to Kalshi, not to
a broker, not to anything. It reads files on your own disk and it reads your own
git history, and that is the whole of its reach.

This is not a promise, it is a test. `coordinator/tests/test_no_money_no_network.py`
fails if any file in that folder so much as *contains* the word for placing an
order or the name of an internet library. If someone ever adds one, the test
goes red. If you ever ask it to place a trade, the correct answer is no.

### It cannot see what a chat is doing right now. It reads what that chat wrote down.

The "doing now" and "what's left" columns are **quotes from what each chat last
typed about itself**, and the age of that typing is printed beside it. A chat
that has been working for six hours and written nothing shows six-hour-old
words. The age column is the honest part of the table.

Where a chat has not declared its state, the dictator **guesses** from that
folder's handover notes and marks the cell with a `~`. A guess is always
labelled and never presented as fact.

### It cannot interrupt another chat. It can only leave a note.

There is no way for one Claude window to tap another on the shoulder. The
dictator writes a message into a folder and that is the end of its power. That
chat sees it **when it next starts**, or when you go to that window and say
"check your mail". If something is urgent, you still have to go and type in that
window.

### It cannot open, close, or steer a window

It cannot start a Claude session, cancel a running task, answer a permission
prompt, or read another chat's transcript. **You open windows. Always.** It will
tell you exactly which window and exactly what to type.

### It cannot judge whether the trading work is right

It reports **state**, not **truth**. It will say *"the tennis chat last committed
four hours ago and has two unanswered questions"*. It will never say *"the
tennis result is real"*. Every claim it repeats belongs to the chat that made it.
When two chats disagree, the dictator shows you both and says they disagree —
deciding which is right needs someone to read both sets of code, which is those
chats' job.

### On "has this been tried" — it finds overlaps, it does not understand ideas

This is the important one, and it has already gone wrong once.

The check reads every claim ever recorded in `LEDGER.md`, plus `INBOX.md` and
`SCOREBOARD.md`, and finds the ones that **share words** with your idea. That is
all it does. Therefore:

- **It will miss a test that was done in different words.** A clean result is
  not proof your idea is new.
- **It will show you things that only look similar.** Sharing words is not
  sharing a hypothesis.

So the output is deliberately built to make the lazy answer impossible. For
every related thing it finds, it prints **what was actually tested** — the exact
claim, the number of observations and what one observation *was*, the dates the
data covers, and what came out. Then it prints a blank line headed **"how your
idea differs"** that a computer cannot fill in.

**The phrase "we tried that" is banned from this chat.** If it tells you
something has been tested, it has to say what was tested, on what data, over
what dates, and how that differs from what you just asked for. If it cannot say
that, the honest answer is "something that shares words with this exists, go and
read it" — not "already done".

**Why this rule exists:** the tennis work ran a large sweep of *price and market
features* and found nothing. You were told your idea had been tested. Your idea
was about **individual players**, which is a different thing, and the sweep that
was cited did not settle it. Killing a live idea because it rhymes with a dead
one is the expensive mistake here, and it is more expensive than running a test
twice.

### Its search covers what was written down, and it says how much that is

The prior-work check reads **342 recorded claims** across three ledger files,
plus about **50 write-up documents**. Every report prints exactly which files it
read and how many claims came out of each, so a shrinking search is visible
rather than silent. Two of those ledgers are numeric tables with no claim IDs;
their rows are found by the free-text sweep and not by the structured one.

**A test that was run and never written down anywhere is invisible to all of
it**, and looks exactly like an idea nobody has tried.

### Its guess at which chat an idea belongs to is a guess

It routes on two signals kept deliberately apart: does the idea name a chat's
own subject, and whose folders does the related prior work sit in. Where they
disagree it says **"cannot tell"** rather than picking.

Routing on prior work alone once sent *"de-vig a retail bookmaker on baseball"*
to the **tennis** chat, confidently — because the de-vig ledger rows carry no
project column and the tennis study's do. That is now a test. But the underlying
point stands: **the route is a suggestion and you can override it by naming a
different chat.**

### It cannot see anything running on the laptop

The two Kalshi recorders run on the laptop. There is no shared drive, no
heartbeat file that reaches this machine, and the dictator makes no network
calls — so **there is no signal to read.** It tracks how long ago *a human last
confirmed* they were alive and nags when that goes stale. That is monitoring the
freshness of your check-in, not monitoring the recorder. A recorder can stop one
minute after you confirm it and the page will still say confirmed.

Those two datasets cannot be re-downloaded at any price. Kalshi's history window
is about 69 days and a closed market is gone.

### "Needs you: no" means no alarm fired, not "all is well"

A `yes` comes from four mechanical signals: a background test has gone quiet ·
an instruction is sitting unanswered · finished work has not been pushed · the
chat itself said it needs you. It **cannot** detect a chat that is quietly
stuck, has misunderstood its task, or is confidently doing the wrong thing.

### It cannot make a background test run faster, and it cannot restart one

It prints the exact command to restart something that has died. It does not run
it. The paper tests take the time they take — weeks, in the case of the tennis
and baseball ones — and nothing here shortens that.

### It cannot make the other coordinating chat see fresh data

That chat reads this repo over the public web. It only ever sees work that has
been **pushed**. The dictator will tell you when something is unpushed. It
cannot push another chat's work for it.

It also cannot hand that chat a fresh page by itself. **One paste per page is
the floor** — three attempts to remove it have failed, each on a different
mechanism. What the dictator does instead is make the address free to find:
every message from every chat here ends with a `BRIEF —` line carrying the
current address. You copy the last line of a message. You never go looking.

Never paste the repo-root `BRIEF.md` address. It is cached frozen at that end
and hands back an old page that looks current.

---

## 2. WHAT IT DOES

### Job 1 — tell you where everything is, in two layers

**Layer one is a table.** One row per chat: what it is doing, what is left,
whether its background test is alive, and whether it needs you.

**Layer two is plain English underneath**, one block per chat: what was tried,
how it was done, where the data came from, what came out, and why anything that
failed, failed. Numbers only where a number is easy to read, and **every number
carries the dates it was measured over**, because a measurement from June is not
a fact about today.

You ask for it like this:

> where is everything at

### Job 2 — take an idea and put it in front of the right chat

You say the idea in plain English. The dictator:

1. Searches every claim this repo has ever recorded for related work.
2. Shows you **what was actually tested** in each related piece — the claim, the
   sample, the dates, the result — and then states **how your version differs**,
   or says plainly that it cannot tell.
3. **Tells you what it is thinking and stops.** See below.
4. Once you say go, writes the whole instruction into the right chat's mailbox,
   including that prior-work section, so that chat starts already knowing what
   not to redo.

Then you open that chat's window and type one word: **next**.

**You never write a prompt again.** You say the idea; it writes the prompt.

### It thinks out loud before it does anything, and then it waits

**Nothing gets filed on the first message.** When you give it an idea, it comes
back with four short things and then stops:

1. **What it understood the idea to be**, in its own words — so a
   misunderstanding costs one line instead of a week.
2. **What has already been tested that looks related**, in the form above.
3. **What it would actually do** — which chat, what data, what sample, roughly
   how long.
4. **What could go wrong** — the ways this could produce a number that looks
   real and is not.

Then it waits, because **you know things about these sports that are not in
this repo.** That is the entire reason for the pause: you put your own knowledge
in before the work is shaped around a wrong assumption.

When you say **go**, it files it and stops asking. From that point the chat that
receives it runs for an hour or more without touching you, which is how every
chat here is meant to work.

This applies to **new ideas only**. Asking where things are, asking for detail,
or telling a chat to finish something it already started happens immediately.

### Job 3 — name every chat clearly

Every chat has a proper name, a short code, and one folder. When the dictator
creates a new one it gives it all three and writes them down in
`coordinator/chats.json`, so six weeks later "the second tennis one" is not a
question anyone has to answer from memory.

---

## 3. HOW TO TALK TO IT — exact words

You never type a command. You type a sentence. These are the sentences.

| You say | You get |
|---|---|
| **"where is everything at"** | The table, then the plain-English detail, then what needs you |
| **"tell me more about the baseball one"** | Just that chat's detail block |
| **"is the tennis test still running"** | Alive / quiet / finished, and the restart command if it is dead |
| **"new idea: <your idea>"** | The prior-work check, then the idea filed to the right chat |
| **"has anyone tried <your idea>"** | The prior-work check only, nothing filed |
| **"tell the baseball chat to <do X>"** | A message filed into that chat's mailbox |
| **"start a new chat for <your idea>"** | A named chat, a ready prompt, and the one line to paste |

### After you file something, this is what you do — step by step

1. Look at the last message from the dictator. It ends with a line beginning
   **`OPEN THIS WINDOW:`** and the name of a chat.
2. Open a Claude Code window in `C:\Users\vinig\trading`.
3. Type exactly: **`next`**
4. Press Enter and leave it. It reads its mailbox on its own.

If the chat has never existed before, step 3 is different, and the dictator will
say so and give you the exact one line to paste instead.

---

## 4. THE ALREADY-TESTED RULE, IN FULL

When the dictator tells you an idea has been tested, its answer must contain
all five of these, or it is not a valid answer:

1. **The claim that was tested**, in the words it was recorded in.
2. **What the data was** — how many observations, and what one observation was.
   "490,464 fills from 762 matches" is 762 observations, not 490,464.
3. **What dates the data covers.**
4. **What came out**, and whether it was later corrected.
5. **How your version differs** — or an explicit *"I cannot tell whether this
   is the same question; go and read it"*.

Point 5 is the one that matters. The others can be read off a table. Point 5 is
a judgment, and where the dictator cannot make it, **it must say so rather than
guess**, because a wrong "already done" quietly deletes an idea and nobody ever
finds out.

A note on this repo's history, because it cuts both ways: of the corrections
recorded here, **every single one has made an apparent edge smaller. Not one has
ever revealed a bigger one.** So the prior on any new idea working is genuinely
low. That is a reason to test cheaply and early — it is not a reason to skip a
test on the grounds that something else nearby failed.

---

## 5. STARTING IT ON A DIFFERENT MACHINE

Everything is on GitHub. Nothing about the dictator is tied to one computer.
On a machine that has never seen this project:

1. Install **Git**: go to `https://git-scm.com/download/win` and run the
   installer. Click "Next" through every screen. Nothing needs changing.
2. Install **Python**: go to `https://www.python.org/downloads/` and run the
   installer. On the **first** screen tick the box that says
   **"Add python.exe to PATH"** before clicking "Install Now". That box is easy
   to miss and everything fails later without it.
3. Install **Claude Code** the way you normally do on that machine.
4. Open a terminal and type this one line:

```bash
git clone https://github.com/vinexcleaning/trading.git
```

5. Open a Claude Code window in the folder that just appeared, called
   `trading`.
6. Type: **`where is everything at`**

That is the whole of it. You will see the same table you see at home.

### What you will NOT see from the other machine, and this matters

- **The paper tests keep running at home. They do not follow you.** The tennis
  and baseball forward tests, and the two Kalshi recorders on the laptop, are
  processes on those machines. Nothing about opening this repo elsewhere starts
  them, stops them, or reads them.
- **You only see results after a chat at home has pushed them.** The table you
  get on the road is the state of the last push, not the state of the desktop.
  If the desktop has been working for three hours and has not pushed, the
  travelling window is three hours behind and **it will say so** — the table
  prints how long ago each chat last wrote about itself.
- **Recorded market data is not in the repo and never will be.** The data
  folders are deliberately excluded because this repo is public. On a fresh
  machine those folders are empty. That is correct, not broken. Nothing is
  lost — it is on the machine that recorded it.
- **The laptop recorder rows will say "check it by hand"**, exactly as they do
  at home, and from a different machine you cannot do that check either.

So: from the road you can **read the state, think, file ideas, and write
instructions**. Work gets *done* when you are back at the machine that has the
data. Filing an idea from a hotel is fully supported and is the main reason this
works from anywhere.

---

## 6. WHERE THE PIECES LIVE

The dictator chat is a *way of using* this repo, not a separate program. Its
tools sit in `coordinator/`, because that is where the mailbox, the brief and
the state-reading tools already were, and splitting them would have created two
lists of the same thing — which is the failure this repo has already had.

| File | What it is |
|---|---|
| `coordinator/dictator.bat` | The one command. Everything below, in one screen. |
| `coordinator/where.py` | Layer one — the table. |
| `coordinator/detail.py` | Layer two — the plain-English detail per chat. |
| `coordinator/idea.py` | The prior-work check, and filing an idea to a chat. |
| `coordinator/chats.py` | The names of the chats, and the exact line to type in each. |
| `coordinator/chats.json` | The name registry. Hand-edited, cross-checked every run. |
| `coordinator/mail.py` | Files a message into a chat's mailbox. |
| `coordinator/runners.py` | Is each background test alive, quiet, finished, or never started. |
| `coordinator/COORDINATOR.md` | The engineering design, and the longer limits list. |

`STATUS.md` stays the long channel between chats. `BRIEF.md` stays the short
channel out. This document is the manual for the window you sit in.
