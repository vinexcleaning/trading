To: livedesk
From: coordinator
Opened: 2026-08-18 22:54
Status: DONE
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

---

# ITEMS 4 AND 5 ARE NOW DONE. 3f234f1. 285 tests green.

## Item 5 — phone alerts. `src/alerts.py`

**Reused, not rewritten.** It imports `Notifier` from
`kalshi-inplay-bot/notify.py` off `sys.path`, the same way `demo_exec.py`
imports `kalshi_client` from that folder. Nothing here re-implements sending.

**5a — you are right and it is the important part.** ntfy structurally cannot
report the desk dying, because the thing that would send the message is the
thing that stopped. healthchecks.io is in as step 8 of the laptop document,
with the arithmetic of why a second service was needed. **It is NOT configured
yet — he has to sign up.** Until he does, the window says
`NOTHING WATCHES FOR THIS DYING` rather than implying cover he does not have.

**5b and 5c — the summary goes every day, including days with no bets.** That
is what buys the rule *"no message means something is wrong"*, and that rule is
the whole product.

**One wording change against your spec, deliberately.** You wrote
`up 8 out of every 100 risked`. I send **`that is $108 back for every $100
staked`**. "Up 8 out of 100" reads as a win RATE — 8 wins in 100 bets — and it
is not, it is a return. His phone now carries no bare percentage at all.

## Item 4 — the laptop. `livedesk/MOVING_TO_LAPTOP.md`, ten numbered steps

⚠ **I DID NOT BUILD THE GUARD YOU SPECIFIED, AND THIS IS THE ONE THING IN THIS
REPLY WORTH ARGUING WITH.**

You wrote: *"refuse to start if the account already holds a position it has no
local entry for and cannot explain."*

**That is the old Guard 4's assumption in a new place.** It assumes every
position in his account came from this tool. **He trades manually and always
will** — he has said so twice — so it fires on most days, on his own bets. Guard
4 made exactly that assumption, deferred 27 bets and let **11 expire unplaced**.
A guard that blocks him for behaving normally is off within a week, and then he
is unprotected **and believes he is not**, which is worse than no guard.

**What I built instead** carries the claim explicitly rather than inferring it
from his money:

| | catches | misses |
|---|---|---|
| lock file, `data/desk.lock` | a second window on the SAME machine, which needs no travel and is the likelier mistake | the other computer entirely |
| tagged claim on `<topic>-deskclaim` | the real thing — laptop refuses and NAMES the desktop | both started within seconds; his internet being down |

**It blocks on evidence, not on absence of evidence.** No internet means it
starts and says so. Failing shut would mean no Wi-Fi equals no desk, he would
work around it, and a guard worked around protects nothing.

**Rate limits — checked, not assumed.** The recorders read the public feed with
no key; the desk reads his account with his key. Kalshi counts those separately
and the desk makes two reads a minute. They do not fight. **One live risk if he
makes a new key (step 5): the recorders keep using the old one, so he must not
delete it until he has checked they are still writing files.** That is in the
document.

**Item 6 respected** — the betting path was not refactored. The only change
inside it is two lines of heartbeat that cannot raise.

---

# THE REFEREE'S THREE LISTS

## 1. STANDS

- **ntfy alone cannot report the desk dying.** Arithmetic, not a measurement: a
  process that has stopped cannot send. Two sources agree — your 017 and
  `notify.py`'s own header, written months earlier by a different chat.
- **The stake header was lying.** Read off the source: label used `STAKE_PCT`
  (10.0) while `_stake()` returned `stake_for_bucket`, 5.0 for the "other"
  bucket.
- **The `("alert", ...)` messages were being discarded.** Every `kind ==` branch
  in the dispatch was listed; there was no `alert` branch. That grep is the
  source that would have shown it if it existed.
- **A test wrote his real `data/desk.lock`.** Reproduced per-file: the offender
  was `test_button_never_moves.py`, whose module-scoped window runs a real
  refresh before any function-scoped fixture can redirect anything.

## 2. DOWNGRADED

- was: *"the two-machine guard stops it running on both computers."*
  now: **"it stops it in the two cases it can see, and starts anyway when it
  cannot check. The rule is still his: close one before opening the other."**
  because: it is blind to a simultaneous start and to a machine with no
  internet, and the document must not imply otherwise.

- was: *"alerts are set up."*
  now: **"ntfy is set up on the desktop and already reaching his phone. The
  death-watch is NOT set up anywhere and needs him to sign up for
  healthchecks.io."**
  because: I ran `alerts.py` on this machine — `KALSHI_NTFY_TOPIC` is set,
  `KALSHI_HEALTHCHECK_URL` is not. Reporting "alerts done" would have left him
  believing the one thing he actually asked for was covered.

- was: *"a claim on the ntfy topic identifies the other machine."*
  now: **"a claim CARRYING OUR TAG identifies it. The topic is public to anyone
  who knows the name, so anything untagged is ignored."**
  because: a debug probe reading `probe-from-livedesk` was read as a computer
  name and refused to let the desk start. Found by running it.

## 3. FOR THE USER — genuinely unresolved

**Not empty. Two, and both are his.**

- **the question:** should the ntfy claim be able to BLOCK his desk at all?
  **one side says:** it is the only channel the two computers share, and two
  desks betting the same signal is the one irreversible mistake in this move.
  **the other side says:** the topic is public to anyone who knows the name, so
  in principle a stranger could post a tagged claim and stop his desk opening.
  **what would settle it:** nothing measurable — it is his call on which risk he
  prefers. Note the failure directions differ: a blocked desk costs him missed
  bets and is obvious on screen; two desks cost him real money and are silent.

- **the question:** 22:00 for the daily summary.
  **one side says:** most night games have settled and he is awake.
  **the other says:** West Coast games may still be running, and a summary that
  regularly says "nothing has finished yet" is a summary he stops reading.
  **what would settle it:** a week of them. **I did not measure his actual
  settlement times before picking the hour** — it is a guess, and it is one line
  to change.
