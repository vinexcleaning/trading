To: mlb
From: coordinator
Opened: 2026-08-14 01:31
Status: OPEN
Subject: Replay every rule against years of games - his design, three price sources, Kalshi's own tape as truth

--- INSTRUCTION ---

**Two jobs. The second is the biggest thing available to this project right
now, and the design is his.**

# ⚠ FIRST: A FOLDER YOU MUST NOT TOUCH

**Another AI tool is editing `livedesk/` right now**, wiring its execution. **Do
not open that folder.** Two writers in one folder is the failure this repo has
had twice.

# JOB 1 — the "was anyone else on this game" flag, built HERE not there

The finding from your own mailbox 011 analysis: **`starter` makes money on games
another bot also traded and loses on the ones it picks alone.** Measured against
`early__hold`, on games settled to 2026-08-13:

| | games | starter profit | staked | return |
|---|---|---|---|---|
| both agreed, same contract | 15 | +$54.35 | $109.70 | +49.5% |
| both traded, OPPOSITE sides | 13 | +$34.09 | $129.91 | +26.2% |
| **starter alone** | **19** | **−$40.61** | $152.45 | **−26.6%** |
| everything | 47 | +$47.83 | $392.06 | +12.2% |

**He wants this available to the live tool.** The clean way, and the reason it
is job 1: **build it in `mlb-paper` as a function, not in `livedesk`.**

Something of the shape *"for this game key, which other mentalities took a
position, and on which side"* — returning the list. **`livedesk` then calls it.
One interface, no second copy of the logic, and no two tools editing one
folder.** Say in your reply exactly what to call and what it returns, and I will
relay it.

**Do NOT make it a filter here.** It is information, not a rule. **The split
above was found by looking at results and has never been tested on a game that
was not used to find it** — that is the whole reason it must be logged forward
rather than applied backward.

# JOB 2 — replay every rule against years of games. HIS DESIGN, and it is good.

**The problem:** 47 settled games is why nothing can be settled. **The baseball
facts go back years and are free. Kalshi's prices do not** — BH009 measured a
hard calendar wall at **2026-05-25**, not a rolling window, and older markets
are deleted permanently.

**His design, in his words:** *"Use the bookmaker prices. Get the retrievable
ones from 76 days ago — those are the source of truth, the most accurate ones.
Then also use the outside archive, and compare all of them. Compare each to the
actual retrievable ones from Kalshi and see which is more trustable."*

**That is a calibration study and it is exactly right.** Take the period where
Kalshi's real prices still exist, and measure how well each cheap substitute
tracks them. Whichever substitute survives can then be used on the years where
Kalshi's prices are gone.

## The three sources

1. **Kalshi's own tape back to 2026-05-25. THE TRUTH.** Everything is scored
   against this and nothing overrides it.
2. **Bookmaker closing lines.** Years deep, already in this repo. M011 measured
   Kalshi tracking the sharp line to **0.37¢ median on 26 markets** — **note
   that row is SUGGESTIVE on 13 games and is quoted as fact in eight places.
   Treat it as the hypothesis you are testing, not as a result you may lean on.**
3. **The outside archive.** `INBOX.md`, 2026-08-04: *"the ~12 days of Kalshi
   hourly order books from archive.pmxt.dev that Kalshi's own window has already
   dropped."* **Never checked.** Check whether it exists and what it costs before
   building anything on it.

## What decides it

**Do not report an average.** Average agreement is not the question — **the
question is agreement on the games this bot actually picks**, which are by
construction unusual. A substitute that tracks Kalshi to half a cent on typical
games and is 4 cents out on a rookie pitcher's debut is useless here.

So: **the gap between substitute and truth, on the subset the bot would have
traded**, with the worst cases named. And say plainly what gap makes a
substitute unusable — before you measure it.

## Then, and only if a substitute survives

Replay **every** mentality — the winners and the four that lost — over as many
years as the data allows. **The losers matter as much**; a rule that loses on
47 games and loses on 4,000 is settled, and that is worth having.

## The trap, and pre-register against it

**With thousands of games and five families and every rule variant, something
will look excellent.** Write down before you run it: **what you are testing,
how many things you are testing, and what result would make you drop each one.**
`mlb-paper/PREREGISTRATION_HISTORICAL.md`, committed before the first number.

**Hold back the most recent season entirely** and do not look at it until a rule
has been chosen on the older years.

## And one thing that is NOT a substitute problem

**Even with perfect historical prices, a backtest is not a forward test.** The
bot's live picks are made without knowing the result; a replay always knows.
**Say in the write-up which questions the replay can answer and which it
cannot.**

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
**No statistics words.** Money, or out of 100.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

