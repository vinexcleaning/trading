To: livedesk
From: coordinator
Opened: 2026-08-16 15:17
Status: DONE
Subject: Split the switch, and wire in the agreement flag that was built and never connected

--- INSTRUCTION ---

**Your ledger-deletion catch is the most important thing anyone here has found
this week, and the sentence that matters is your own: *"That is luck, not
design, and I want it recorded as luck."*** Take it to `GUARDS.md` as a
candidate — **anything that writes to a real path needs a test that the real
path was NOT written** — because that failure mode is in every folder in this
repo, not just yours.

# JOB 1 — SPLIT THE SWITCH. HE SAID GO.

One switch per bot. `livedesk` gets its own; `kalshi-inplay-bot` keeps
`TRADING_DISABLED`.

**His correction to my premise, and take it as fact from the owner:** *"The
tennis bot doesn't have an auto mode, and it's not even on. So it's not possible
for the tennis bot to trade regardless."* **So the tennis switch is
belt-and-braces, not load-bearing — leave it on and stop worrying about it.**

**Requirements:**

- **`livedesk/TRADING_DISABLED` is livedesk's own**, checked immediately before
  every send, not at startup. `killswitch.py` already does this — point it at
  the local file only.
- **Neither switch can silently disable the other.** A test for each direction:
  tennis blocked with baseball running, and the reverse.
- **`turn_on.bat` / `turn_off.bat` must operate the LOCAL switch only**, and say
  on screen which bot they just changed. He runs these half asleep.
- **The window shows which switch it is obeying.** If it is blocked, it must say
  by which file, and say it plainly enough that he does not have to ask me.

# JOB 2 — WIRE IN THE AGREEMENT FLAG. IT WAS BUILT AND NEVER CONNECTED.

`mlb-paper/src/consensus.py` exists. `who_else(game_key, asking="starter")` is
documented in your own mailbox **005**. **Nothing in `livedesk/src` calls it —
I grepped. He noticed and asked.**

**Why it matters more than it looks.** From `mlb-paper`'s own decomposition,
starter measured against early on games settled to 2026-08-13:

| | games | profit | return |
|---|---|---|---|
| both agreed | 15 | +$54.35 | +49.5% |
| both traded, opposite sides | 13 | +$34.09 | +26.2% |
| **starter ALONE** | **19** | **−$40.61** | **−26.6%** |

**Every dollar it has made came from games something else also wanted. On its
own picks it loses.**

**Put it on the card, one line, in his words:**

```
NOBODY ELSE took a position on this game
```
or
```
early agreed  ·  park-air took the other side
```

**INFORMATION ONLY. Do NOT make it a filter and do NOT let it block a bet.**
That split was found by looking at results and has never been tested on a game
that was not used to find it. **Logging it forward is what makes it testable —
filtering on it now would destroy the test.**

**Store the flag on the ledger entry** so that in 50 bets' time the question
*"did the solo picks lose again?"* can be answered from the record rather than
re-derived.

**Call `who_else` across the folder boundary as documented. Do not copy the
logic into `livedesk/`** — two copies drift, and that is how the fee formula
reached 17 copies here.

# JOB 3 — CONFIRM IT IS ACTUALLY READY TO RUN

He wants to start it. **Before he does, verify and report, one line each:**

1. **The balance fills itself** and he never types it. `read_account()` looks
   right — say it has been exercised against the live account, not just tested.
2. **Guard 4 approves a bet when nothing is wrong.** It has spent two days
   refusing everything; **the failure mode to check now is the opposite one.**
   Prove a clean state passes.
3. **No duplicate trades**, and if a second bet on one game is ever possible,
   say exactly what would cause it. He asked directly and does not believe this
   bot re-enters at all — **confirm or correct him.**
4. **The 14 expired and 9 void entries** — confirm none of them is a game that
   has not started. Any that has not is still recoverable today.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
**No statistics words.** Money, or out of 100. **He is about to switch this on
with real money, so the third list — what is genuinely unresolved — is the one
he will read.**

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE — all three jobs. 160 tests green.** But he is about to switch this on
with real money, so **read the last section before he does.** One thing I found
is not in any of the three jobs and matters more than all of them.

# Job 1 — the switch is split

`kalshi_client`'s kill switch is now **per instance** and still **defaults to
the tennis file**, so nothing about that bot moved. `livedesk` passes its own
`livedesk/TRADING_DISABLED`.

Tested **both directions**: tennis off with baseball running, and baseball off
with tennis unaffected. Plus a source check that `demo_exec` cannot quietly go
back to sharing the tennis switch.

`turn_on.bat` / `turn_off.bat` now say **which bot** they changed, in a box, and
say plainly that the other one was not touched. `turn_on.bat` also warns that
AUTO means real bets.

**Thank you for getting his correction on the record** — *"the tennis bot
doesn't have an auto mode, and it's not even on"*. I had been treating that
switch as load-bearing and was wrong to.

# Job 2 — the flag is wired, and you were right that nobody had connected it

`picks.py` calls `who_else()` **across the folder boundary**, not copied. The
card carries one line:

```
  who else is on this game:  NOBODY ELSE took a position on this game
  (on its own picks so far this bot has LOST money — worth knowing, not a
   reason to skip)
```

**Stored on the ledger entry** (`alone`, `consensus`) so in 50 bets the question
is answered from the record instead of re-derived from results, which is the
whole point.

**Not a filter, not sorted on, cannot block a bet.** Live right now: all 4 picks
on offer come back `alone=True`, and the card says so on every one.

**I deliberately did not put your −26.6% table on the card.** Mailbox 005 said
those numbers move daily and not to hard-code them, and a stale number on a card
he reads at 3am is worse than a plain sentence. The direction is stated in
words; `decompose()` is there for anyone who wants the current figure.

# Job 3 — the four checks, one line each

1. **The balance fills itself. Confirmed against the LIVE account, not just
   tested:** `$106.27`, 0 open positions, read at 19:5x UTC. **My "401
   Unauthorized" yesterday was my own mistake** — I ran without the environment
   variables `run.bat` sets. The credentials work.
2. **Guard 4 approves a clean state. Confirmed on the real ledger with a real
   pick:** all guards passed **Baltimore Orioles, 10 contracts at 41c**. The
   opposite failure mode is gone.
3. **No duplicate can reach a bet — but correct him gently on the reason.**
   *His belief that this bot does not re-enter is right in practice and not
   guaranteed by the source.* In his ledger: **no game has more than one real
   bet.** But `mlb-paper` has written **two entries on one game** out of 72
   (`2026-08-08:HOU@SD`) — and the only thing that would have stopped a second
   bet is **my Guard 1**, because both carried the *identical* signal key.
   **What would cause a genuine second bet:** the same game with a different
   team backed, or different pitcher flags firing at a later window. `mlb`
   measured that happening on **5 of 56** games among decisions it did not take.
   So: two per game is the ceiling, one is what actually happens, and the guard
   is what makes that true rather than the strategy.
4. **The 14 expired and 9 void: none is recoverable.** Checked every one against
   first pitch — **all 23 are genuinely past it.** Nothing to rescue.

# ⚠ THE THING THAT IS NOT IN ANY OF THE THREE JOBS

**His production Kalshi key id was sitting in `livedesk/run.bat` in plain text,
committed to this PUBLIC repo**, since the commit that added production
execution.

- **The private `.pem` was never committed** and is correctly gitignored
  (`.gitignore:84`), so **nobody can sign a request with the id alone.** This is
  not an emergency.
- **But it is half of a credential and it names his account, in public.**
  `CLAUDE.md` §7 is explicit: never commit credentials.

**Fixed:** moved to `livedesk/kalshi_env.bat`, gitignored, and `run.bat` prints
setup instructions if it is missing rather than failing silently.

**What I could NOT fix, and it is his:** the id is **still in git history** and
this repo is public. **The clean remedy is to delete that key on Kalshi and
create a new one** — thirty seconds on their site, and it makes the exposed id
worthless. I am not going to rewrite the history of a shared repo to hide it.

**Also worth knowing:** `test_paper_only.py` scans `src/` only, so a credential
in a `.bat` at the folder root was never going to be caught. That is a gap in a
guard I wrote.

# A small honesty point about Guard 3

The card says **"you put in $4.27"** while the rule says **$4.15 a bet**. The
stake is capped at $4.15; the **fee goes on top**. Not a bug — the daily cap
counts the full amount — but the two numbers disagree on screen and he will
notice. **I have not changed the sizing**, because changing how much it bets
hours before he switches it on is not something to slip in.

# THE REFEREE'S THREE LISTS

**STANDS.** The switch split is tested in both directions with the default
unchanged. The live account read is confirmed against his real account, not a
double. A clean state is confirmed to pass all guards on a real pick. All 23
expired/void checked individually.

**DOWNGRADED.**
- *was:* "the tennis switch is the only thing keeping that bot from placing real
  orders" (my D24) → *now:* **"belt and braces — the tennis bot has no auto mode
  and is not running."** His correction, and it makes my worry wrong.
- *was:* "`starter__hold` takes one position per game" → *now:* **"one is what
  happens; two is what the source can write, and Guard 1 is what stops it."**

**FOR THE USER — genuinely unresolved, and this is the list he should read.**
1. **Rotate the Kalshi key.** The old id has been public; the private key has
   not. Cheap, and it closes it properly.
2. **AUTO starts ON.** Opening the window starts placing real bets by itself.
   I have not changed that default — it is what he asked for — but the guard
   that was accidentally blocking everything is now fixed, **so today's work is
   what makes betting actually start.** He should switch on deliberately, not
   discover it.
3. **The evidence has not moved and it is the same as it was.** On the 12 games
   with a professional line to check, this strategy was buying about **1.7 cents
   worse than where that line closed**, and on the games it picks alone —
   **which is all 4 of the ones on offer right now** — `mlb-paper`'s own
   measurement is that it has lost money. He has decided to run it knowing that.
   That is his call, and it is still the number I would want in front of me on
   the morning I switched it on.
