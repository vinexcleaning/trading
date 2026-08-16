To: livedesk
From: coordinator
Opened: 2026-08-16 15:17
Status: OPEN
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

