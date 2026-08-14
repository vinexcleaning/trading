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


---

# AMENDMENT — he restated the design and added the reasoning behind it

**His words, and they sharpen job 2:**

> *"The retrievable ones straight from Kalshi should be pretty much our source of
> truth. The outside archive should also be pretty good because it's tracking
> the Kalshi prices, but it could be delayed or something like that. Once we get
> past the 76-day threshold we won't be able to compare any more. But if we
> compare before and we see that it's accurate, we can assume it's probably
> gonna be accurate after."*

**That is the right logic and it is worth stating in the write-up in his own
words.** Three sources, one truth, calibrate where truth exists, extrapolate
where it does not.

**His guess about the archive is also worth testing rather than assuming:** he
expects it to track Kalshi closely but possibly with a lag. **So measure the lag,
not just the gap.** If the archive is Kalshi's price from five minutes ago, that
is a fixable offset. If it disagrees at random, it is not.

# ⚠ THE WEAKNESS IN THE EXTRAPOLATION, AND IT MUST BE IN THE REPORT

**"Accurate before, so probably accurate after" is an assumption, not a
measurement**, and there is a specific reason to doubt it here:

**The `devig` chat already found a bookmaker whose coverage went from everything
in 2022 to nothing in 2026** (M018, football-data.co.uk soccer closing lines).
**A source's relationship to reality is not constant over years.** Kalshi itself
has grown enormously in that time, so its liquidity and pricing behaviour in
2024 are not what they are now.

**So the extrapolation cannot be checked directly — by definition, there is no
truth to check it against out there.** What CAN be done, and should be:

- **Measure whether the agreement is STABLE ACROSS the 76 days you do have.**
  Split the window into halves or weeks and report the gap in each. **If it
  drifts inside 76 days it will drift more outside them.** If it is flat across
  the whole window, that is mild evidence it travels — mild, and say so.
- **Report the agreement separately by market thickness.** Thin markets are
  where substitutes fail, and old Kalshi was thinner than new Kalshi. If the
  substitute only tracks well on liquid games, that is a warning about the past.
- **State the assumption in one plain sentence in the headline**, not in a
  footnote: *"everything before 2026-05-25 rests on the assumption that a
  substitute measured over 76 days in 2026 behaves the same way in 2024, which
  is not checkable."*

**None of that kills the idea.** It is still the only route to a sample bigger
than 47 games, and 47 is why nothing here can be settled. **It just has to be
reported as a conditional result rather than a measured one.**

# ⚠ RE-READ YOUR MAILBOX BEFORE YOU COMMIT

This amendment landed AFTER he typed `next`. **The `livedesk` chat lost five
hours of work to exactly this** — read the mailbox at 23:34, pushed at 04:15,
and never re-read the file that had been amended thirteen minutes after it
first looked. **Pull and re-read this file before you commit.**
