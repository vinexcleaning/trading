To: devig
From: coordinator
Opened: 2026-08-11 14:31
Status: OPEN
Subject: GO on the retail book idea - and be precise about what your prop census did and did not unblock

--- INSTRUCTION ---

**The user has said go on the retail-book idea.** It has sat in `INBOX.md` since
2026-08-07 marked *"QUEUED, NOT STARTED"*, and the thing blocking it was
refuted by your own census yesterday.

# BE PRECISE ABOUT WHAT WAS AND WAS NOT UNBLOCKED

**Two related things, and they are not the same. Say which one you are doing.**

**(a) The idea in `INBOX.md`: de-vig a RETAIL book.** Every de-vig test in this
repo used **Pinnacle, the sharpest book in the world**, and all came back null
(`RESULTS_DEVIG_WHERE.md`; mlb-paper's 0 of 58 markets). The untested version is
a **soft book with a fat margin on a market Kalshi quotes tightly**. Its blocker
was M024 — ESPN's DraftKings props carried one side only, so nothing could be
de-vigged.

**(b) What you actually measured yesterday: PINNACLE'S OWN PROPS are two-sided,
free, and much wider than its moneyline** — 1,650 soccer, 79 baseball, median
overround 5.73 and 3.86 against the moneyline's 2.01.

**(b) does not deliver (a).** A wide Pinnacle prop is still Pinnacle. **Do not
let (b) be written up as "the retail book idea, done"** — that is exactly the
substitution that gets an idea recorded as tested when it was not.

**Both are worth doing. Do (b) first because it is free and immediate, and
report (a)'s status honestly rather than folding it in.**

# JOB 1 — the wide-prop test (this is (b), and it runs today)

**The question:** de-vig those 1,650 two-sided props into a fair probability,
join them to the matching Kalshi market, and measure the gap.

**Why it is not obviously the same as the null you already have.** Your existing
null is Pinnacle's **moneyline**, which is the sharpest price in world sport and
which Kalshi tracks to 0.37¢ (M011, and note that row is **SUGGESTIVE on 13
games** and is quoted as fact in eight places). A prop at 2.9× the margin is a
market Pinnacle itself is **less confident about**. That cuts two ways and you
should say which one wins:

- **Against us:** a wider margin means a noisier de-vigged number, and the
  standard de-vig assumption (margin splits proportionally) is worst exactly
  where the margin is fat.
- **For us:** it is a market the sharp book is less sure of, so Kalshi has less
  to copy from, and may be further off.

**Try more than one way of removing the margin.** Proportional is the default
and is known to be wrong at long odds. Also run the logarithmic and
Shin methods and **report whether the answer depends on which you pick.** If it
does, that is the finding and the edge is not real.

**Cost side, and use the one implementation:** `common/kalshi_fees.py`. The fee
is near its minimum at extreme prices — 0.20¢ at 97¢, not the habitual
3.6–4.8¢ this repo quotes. Quoting the habitual figure at the wrong price is
itself an error and has been made here twice.

**Two filters that select, and the soccer chat just proved how much that
matters.** It found the trade was not mispriced but **absent by construction** —
Kalshi stops quoting the losing side exactly when the match becomes
near-certain, so every available price was on a different question. **Check
before you conclude:** which props have a Kalshi market at all, and which
have a two-sided quote with size behind it. Report the true rate inside and
outside the tradeable set. If they differ, the gap you measured is a selection
effect, not an edge.

# JOB 2 — is (a) still blocked, and can it be unblocked?

The original idea needs a **free, two-sided, retail** feed. M024 said ESPN's
DraftKings props carry one side. **You refuted M024's method once already** —
you found the label on the matchup record and the prices on a different record,
joined on `matchupId`, and your first pass looked in the wrong place and got
zero, which is how the original error was made.

**So check whether the same shape of mistake is hiding a retail feed**, and list
what you tried: which books, which endpoints, one side or two, free or not.
**A blocker reported without that list is not a blocker** (`CLAUDE.md` §9c
step 1).

If no free two-sided retail feed exists, say so with the list, and **close (a)
with what was not tested** per §9c step 7 rather than leaving it open forever.

# BEFORE YOU REPORT

`py -3 coordinator\reflect.py --file <draft>` then
`py -3 coordinator\reflect.py --referee`. **Both.** The report ends with the
Referee's three lists and an empty third list is said out loud.

Pre-register as `bot-hunt/PREREGISTRATION_RETAIL.md` before the first number
exists, including **what result makes you drop it**. Hold data back.

**No statistics words.** Money, or out of 100.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

