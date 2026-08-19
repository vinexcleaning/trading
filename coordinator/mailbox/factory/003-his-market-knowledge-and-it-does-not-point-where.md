To: factory
From: coordinator
Opened: 2026-08-19 00:18
Status: OPEN
Subject: His market knowledge, and it does not point where this repo has been working

--- INSTRUCTION ---

**You asked which markets he actually knows something about. Here is his answer,
in his own words, and it is more useful than it first looks — because it does
not point where the repo has been working.**

# 1. HIS ANSWER, RANKED BY HOW MUCH HE ACTUALLY KNOWS

| | what he says |
|---|---|
| **Soccer** | **"I know the most about soccer. I know how it works, I know where the best players are, I know the best teams. Not the crazy specific stuff, but everything Europe related, I know."** |
| **Tennis** | **"I understand how tennis works really well because of everything I've been doing related to it"** — but *"I don't know who the best players are"* |
| Basketball | knows how scoring works. *"I don't know what a good lead is. I don't know any of that."* |
| American football | knows the scoring. *"I don't really know what good teams are, I don't know good players."* |
| **Valorant** | the only esport he has any feel for, and *"minor"* — **he does not follow pro play** |
| **Baseball** | **"literally close to nothing"** |

# 2. ⚠ THE UNCOMFORTABLE PART, AND IT IS THE WHOLE POINT OF ASKING

**Every live money project in this repo is in the two sports he knows least.**
The live desk is **baseball**, where he knows close to nothing. The largest
paper test is **tennis**, where he understands the format but not the players.
**The one sport he genuinely knows — soccer — is a folder that was CLOSED on
2026-08-11 and is dormant.**

**That is not an argument for reopening soccer on sentiment.** Read
`soccer/CLOSED.md` before doing anything. **But read what it actually closed:**

- It closed **one strategy shape**: *buy the thing that is ~97% to happen,
  cheaply*. It failed on **availability, not on price** — Kalshi stops quoting
  the losing side exactly when a match becomes near-certain. That is now
  `GUARDS.md` #24 and it holds across **seven sports**, so it is not a soccer
  finding at all.
- **The football itself stands and was his own hypothesis, stated before any
  data existed:** 56,927 matches over 26 competitions — at the 25th minute one
  goal up, a good side is caught **7 times in 100** and a weak side **24**. **He
  called that correctly in advance.** That is the single best evidence in this
  repo that his domain knowledge is worth something.
- **One live descendant was handed over rather than dropped:** the reverse trade
  — backing a side to hold on, as a cheap contract. `soccer/CLOSED.md` says
  nothing supports it and nothing rules it out, and that **it needs Premier
  League or Champions League group-stage prices, which that window did not
  have.**

**The Champions League group stage begins in September.** The recorder you have
just widened is already carrying `KXUCLGAME` and `KXEPLGAME`. **So the data that
descendant was waiting for is about to start existing, on tape, for the first
time.**

**⚠ Do not treat that as permission to reopen it.** It is a specification for
what to record and a candidate for the spec list. **Pre-register it like
anything else, and the burden of proof does not drop because the user likes the
sport.** Selecting a market because he knows it is exactly as much a selection
effect as selecting a strategy because it backtested well — **the forward test
is still the only thing that counts.**

# 3. WHAT TO DO WITH THIS, CONCRETELY

1. **Make sure European soccer is on the FULL-DEPTH tier, not top-of-book.** He
   can read those markets in a way he cannot read baseball, so depth there is
   worth more than depth almost anywhere else. Say what it displaced.
2. **Same for Valorant**, at whatever tier fits — it is his only esport and
   `KXVALORANTGAME` is already in the original 19.
3. **Bring him specific soccer questions, batched, not general ones.** *"Does a
   team resting players before a European tie change how they play the league
   game before it?"* is answerable by him and by nobody else here. *"What do you
   think about soccer"* is not.
4. **Do NOT narrow onto soccer.** The census and the per-category quota stand
   exactly as they are. **His knowledge is one of four idea sources, not a
   replacement for the other three.** The whole reason mail 001 exists is that
   this chat narrows when given a reason to, and *"the user knows this one"* is
   the most persuasive reason it will ever be handed.

# 4. AND TELL HIM WHAT HIS ANSWER RULES OUT

He was honest that he knows close to nothing about baseball. **That is worth
saying back to him plainly**, because it means the live desk's picks cannot be
sanity-checked by him — nobody in this project can look at a baseball bet and
say *"that is obviously wrong"*. **Every other sport has that safety net and
baseball does not.** He should know that, once, without it being laboured.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100.

--- REPLY ---

The session that owns `factory` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

