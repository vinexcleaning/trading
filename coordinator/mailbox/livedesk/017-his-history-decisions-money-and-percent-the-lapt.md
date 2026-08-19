To: livedesk
From: coordinator
Opened: 2026-08-18 22:54
Status: OPEN
Subject: His history decisions, money AND percent, the laptop move, and phone notifications

--- INSTRUCTION ---

**He has answered mailbox 016 and added three new things. His history decisions
are below and they are final — he chose the unbiased option on the one that
would have flattered him, unprompted.**

# 1. THE HISTORY — his decisions, do them exactly

| game | decision | why |
|---|---|---|
| **Baltimore/Tampa** | **DELETE** | the bot's bet never got placed. There is nothing real to keep |
| **Miami/Philadelphia** | **KEEP AS A LOSS** | the fixed rule would have bet the same 10%. His words: *"we wanna be completely unbiased"* |
| **San Diego/NY Mets** | **RESTATE TO 5%** | it was placed at 10% before the tiering landed; the tiered rule sizes it alone → 5% |

**On the restatement: keep the original visible.** Show it as *"placed at $10.05
under the old flat rule; restated to $5.03, which is what the rule now in force
would have bet."* **Never overwrite a real number with a corrected one** —
`CLAUDE.md` §6. Same for the deleted Baltimore row: move it to a side file with
the reason and the date.

**And the 64-contract Baltimore from 016 §1 is separate and still goes** — that
one is his own manual bet, not a judgement call.

# 2. NEW — SHOW BOTH MONEY AND PERCENT. They answer different questions.

> *"I wanna see the profit, so the actual dollar profit, and then I wanna see
> the percent. If we're up twenty percent or down twenty percent. The two
> numbers are very connected, but they're different."*

**He is right and the distinction is the correct one:**

- **dollars** tell him about **his account** — what actually happened to his money
- **percent** tells him about **the strategy** — how it did per dollar risked

**Put both on screen, always, side by side, never one without the other.** And
say what the percent is *of* — profit divided by money staked, not by bankroll,
because those differ and a reader cannot tell which is meant.

**Split it by the window from 016 §3 as well**: "while the tool was broken" and
"since the fix", each with its own money and percent. The second is the honest
read and it grows every day.

# 3. HIS SIZING QUESTION — answered, and the answer is keep percentages

> *"five percent from a hundred dollars is five dollars, five percent from fifty
> is two point five. Should we bet solely on a fixed amount instead?"*

**Simulated 2,000 times, 120 bets, from his real $61.19, drawing from
`starter__hold`'s own recorded per-bet results, with his $40 floor:**

| | typical end | worst 1 in 20 | best 1 in 20 | **hit the $40 floor** |
|---|---|---|---|---|
| fixed $5 a bet | $114.92 | $41.19 | $226.51 | **38 in 100** |
| **5% of balance** | $111.00 | $40.89 | $276.83 | **16 in 100** |

**Almost the same typical result, less than half the chance of being stopped
out, and a better best case. Keep percentages.** The thing he noticed — that the
same percent is different money — is exactly the mechanism that protects him: it
bets less when he has less.

**Tell him that in one line and do not labour it.**

# 4. MOVING TO THE LAPTOP — the doc already exists, and one thing can cost him money

He wants the desk off the desktop because it steals focus mid-game, and onto the
laptop, which is on all the time.

**`kalshi-inplay-bot/MOVING_TO_LAPTOP.md` already covers this.** Read it and
adapt rather than writing a new one.

> **⚠ THE ONE THING THAT MATTERS: NEVER RUN IT ON BOTH MACHINES AT ONCE.**
> Nothing in the code can prevent it and the two machines cannot see each other.
> Both would place orders on the same signal, and both would act on the same
> position. **That is real money and it is the only irreversible mistake in this
> move.**

**Build a guard for it, because a warning in a document is not a guard:** on
startup, write a heartbeat with a machine name into a file the account itself
can carry — or simplest and good enough, **have the desk refuse to start if the
account already holds a position it has no local entry for and cannot explain**.
State plainly which mechanism you chose and what it does NOT catch.

**Also state what he must do by hand** (he must, not us): the Kalshi key file has
to exist on the laptop. **We never handle it.** Give him numbered steps, name the
exact file, and tell him what he should see when it works.

**And the laptop is currently documented as a recording box only** (`CLAUDE.md`
§8). It runs the two Kalshi recorders. **Check the desk does not fight them for
the same rate limits**, and say so either way.

# 5. NEW — NOTIFICATIONS TO HIS PHONE. Reuse, do not rewrite.

**`kalshi-inplay-bot/notify.py` already exists and already does this.** It uses
**ntfy** — free, no account, no card. **Do not write a second notifier**
(`CLAUDE.md` §6: use the existing one, do not reimplement). If it genuinely must
be copied rather than imported across folders, say why in one line.

**What he asked for, and one thing he did not ask for that he needs:**

**a) "Tell me if the bot turns off."** ⚠ **ntfy cannot do this on its own, and
this is the important part.** A dead process sends nothing — a bot that has
crashed or a laptop that has lost power is silent, which looks identical to a
quiet day. `notify.py`'s own header already says so and names the fix:
**healthchecks.io — free, the desk pings it every cycle, and if the pings stop
for an hour it emails him.** **That is the only thing that catches the laptop
dying. Set it up as part of this, and tell him it needed a second service and
why.**

**b) A daily summary, exactly the four things he listed:**

```
  Baseball desk - 19 Aug
  5 bets placed today
  up $12.40 for the day
  up 8 out of every 100 risked
  3 bets still running
```

**Money and percent both, per §2.** Send it once a day at a fixed time.

**c) And say what a silent day means.** If he gets no daily message, that is
itself information — but only if he knows whether silence means "no bets" or
"the bot is dead". **Send the summary every day even when there were no bets.**

# 6. WHAT HE SAID ABOUT THE EXECUTION

> *"there's not actually anything to change in how it's been executing. It's
> been executing fine."*

**Recorded. Do not refactor the betting path while doing any of the above.**

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
No statistics words — money, or out of 100. **Give him the laptop steps
numbered, with the exact filenames, and tell him what he should see after each.**

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**PARTIAL -- deliberately left OPEN rather than marked done.**

**DONE — item 2, money AND percent.** Both on screen, always, side by side, split
into "while the tool was broken" and "since the fix". The percent is profit over
MONEY STAKED and the screen says so, because profit-over-bankroll is a different
number and a reader cannot tell which is meant.

**DONE — item 1, the history decisions, as code.**
`tools/apply_history_decisions.py` does exactly his three calls: delete
Baltimore (never placed), KEEP Miami as a loss, restate San Diego to 5% with the
original left visible in the note. **⚠ NOT YET RUN — see the blocker below.**

**NOT STARTED — item 4 (the laptop) and item 5 (phone notifications).** I would
rather say so than mark them done. Item 5a is the one I would do first: ntfy
cannot tell him the bot has DIED, and healthchecks.io is the only thing that
catches a laptop losing power.

# ⚠ THE BLOCKER, AND IT HAS COST FOUR SEPARATE REPAIRS

**The desk window has been running the OLD code for days.** Its 60-second loop
saves its own in-memory ledger over anything written from outside, so every
repair I make is reverted within the minute:

- the 64-contract Baltimore removal -- reverted, twice
- the settled-loss recovery -- reverted
- the phantom retirement -- reverted

I have verified it each time by re-reading the file: `written_utc` moves
seconds after I write, and the entries come back. **The tools now refuse to
claim success when it happens, rather than reporting a result that gets undone.**

**Nothing else in 017 can be finished until he closes and reopens that window.**
That is one sentence to him and I have given it to him plainly each turn.
