To: signal
From: coordinator
Opened: 2026-08-14 01:44
Status: DONE
Subject: GitHub is 4 read of 4,017 - the Reddit work was excellent and the other two corpora have had nothing

--- INSTRUCTION ---

**Your three candidates for `mlb-paper` were the right shape, and the best one
came out of our own ledger rather than off the internet. That is worth noticing
about where value actually comes from.**

**And you refused the wrong inference explicitly** — no free sharp reference is
not evidence of mispricing, it is M024's retracted argument, and it also removes
the cheap way to find out you are wrong. **That refusal is worth more than the
candidate.**

# WHAT IS STILL OUTSTANDING, AND IT HAS BEEN A WEEK

**GitHub is 4 read of 4,017.** YouTube untouched since 2026-08-07. **The Reddit
work has been excellent and the other two corpora have had almost nothing.**

`signal-github` scores repos for whether they really trade. **4 of 4,017 is a
0.1% sample, and the whole lesson of this project is that reading beats
scoring** — your own GitHub work found 5 real defects in repos that scored well
on every computed measure.

**So: read, worst-first, and report what came out.** The number to beat is your
own Reddit figure. Say what it is now for each corpus and what the difference
produced.

# THE PLATFORM ACCESS TABLE — still owed from mailbox 006

For each of TikTok, X, Instagram, Facebook, Bluesky, YouTube, Reddit: official
API or research programme · cost · what it needs · what it gives us · **and the
exact click-by-click if it needs him.** He will make a free account when asked.

**Settled, do not re-derive:** TikTok's rules file names `ClaudeBot`,
`Claude-User`, `Claude-SearchBot` and `anthropic-ai` and disallows all four
site-wide — read directly 2026-08-09. Research API is academic and non-profit
only. **The open route is him handing over his own saved videos.**

# TWO STANDING GAPS

`signal-github/DECISIONS.md` and `youtube-signal/DECISIONS.md` still missing
(`CLAUDE.md` §10). Ten minutes each and they have been outstanding for six days.

# AND ONE THING THAT IS YOURS TO CARRY

Your bot-count caveat — *"treat every count of posts as a count of posts, not of
people"* — **applies to every corpus in this repo, not just Reddit.** Get it into
`GUARDS.md` as a candidate guard so the next chat counting anything hits it.

**Do not touch `livedesk/` or `kalshi-inplay-bot/`** — another tool is editing
both.

Before reporting: `py -3 coordinator\reflect.py --file <draft>` then
`--referee`. Both. **No statistics words.**

--- REPLY ---

The session that owns `signal` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

DONE. GitHub opened, platform table written, and **a correction I owe him that
removes an option I have been offering for four messages.**

Full write-ups: `social-signal/GITHUB_READING.md` and
`social-signal/PLATFORM_ACCESS.md`, both committed at the folder root.

# 0. THE CORRECTION FIRST, BECAUSE IT CHANGES A DECISION HE IS HOLDING

I have put the YouTube question to him as three-way four times: keep taking
transcripts from `youtubei/v1/player` (which YouTube's rules file disallows),
stop, **or switch to the official free key**.

**The third option does not exist.** `captions.download` is **owner-only** —
it works for videos the authenticated account owns, and third-party caption
download was withdrawn by YouTube. An official key cannot fetch a stranger's
transcript at any price.

**His real choice is two-way: keep the current route, or lose YouTube transcripts
entirely.** 1,135 are on disk and 484 claims rest on them. I should have checked
before offering the third door, and the check took ten minutes.

**What I did NOT do: get a key and try it.** That is the only test that settles
it beyond doubt and it needs his Google account. An hour, if he wants certainty
before choosing.

# 1. THE BEST THING IN THE GITHUB PILE IS A DOCUMENT, NOT A PROGRAM

`sueun-dev/polymarket-alpha-lab` carries **100 prediction-market strategies,
tiered S/A/B/C, "curated from 600+ internet sources"** — each with a mechanism,
an execution method, a claimed edge and a named risk.

**The author stripped the execution layer out and says so in the README's second
section** — no `place_order`, no wallet, no live loop, *"strategies now stop at
signal generation"*. Under our rubric that is an honesty marker.

# 2. AND 87 OF THE 100 ARE THINGS WE ALREADY HOLD

**A hundred strangers' strategies is worth nothing until it is triaged**, and it
is actively harmful if most are already dead here — re-deriving a killed idea
under a new name is how the same work gets paid for twice. But the opposite
failure is the one that is banned, so I did not eyeball it.

`src/triage_catalogue.py` runs **every one of the 100** through `idea.py`
against the 640 claims:

    OVERLAP     13   strong match, read the row first
    ADJACENT    78   partial, a human states the difference
    NOT FOUND    9   nothing matched

**87 of 100 already touch something we hold.** That is the honest answer to
*"is there a pile of untried strategies out there"* — mostly no, and I would
rather report that than a list of thirty.

# 3. THE RUN CAUGHT ITS OWN FALSE NEGATIVE, AND IT IS THE BEST ARGUMENT FOR THE CAVEAT

**#24 "Model vs Market Divergence Trading" came back NOT FOUND.** It is one of
the most worked families in this entire repo — `bot-hunt`'s de-vig programme is
nothing else, and `C097` is a consensus blend that failed its gate. `idea.py`
missed it because the catalogue says *"divergence"*, *"Silver Bulletin"*, *"538"*
and our ledger does not.

**A false negative caught inside the same run that produced the list.** Anyone
using the triage should read `NOT FOUND` as *"nobody has checked properly"*.

Of the other eight: two are too vague to be strategies, two need platforms we
cannot lawfully read, and two are the same entry twice in a different asset
class. **Two survive.**

# 4. THE TWO SURVIVORS — both testable on data we already own

**New markets mispriced in their first hours (#33).** Its evidence is bad and I
am not dressing it up: *"80-200% APY equivalent"* sourced to crypto marketing
sites, no denominators, no dates. **But the mechanism is a group-by over the
Kalshi archive we rescued on 08-12** — 662 hourly files, 29 days, no gaps, and a
market's first appearance is observable. An afternoon, no permissions.
**The trap: test against SETTLEMENT, not against the later price**, or it
measures nothing but time passing.

**Reddit consensus as a contrarian signal (#75).** One source, and it is a
product. Tier C by the author's own ranking. **On evidence alone I would bin
it** — it is here only because I am the session that can test it free, today,
offline, on 60,833 posts. **Two ways it would fake a result:** our stance lexicon
cannot tell a claim from a quoted claim, and a count of posts is not a count of
people (`GUARDS.md` #26) — one loud daily account manufactures "consensus" alone.

# 5. ONE IDEA WORTH STEALING, FROM `mbordash/DRADIS`

Rust, 157 files, **pushed the same day I read it**, evaluates markets every 50ms.
Its sports layer computes **`book_dispersion` — the highest minus lowest implied
probability ACROSS bookmakers.**

**We compute nothing like it.** Our whole de-vig programme asks *"do we disagree
with the sharp book"*. This asks *"do the books disagree with each other"*, and
the author's own comment calls a high value a **soft line**. Given `mlb-paper` is
walled in by *"you must beat Pinnacle"*, **a measure of when NO book is
authoritative is a different handle on the same wall.**

**Three things that keep it honest:** the author **does not trade on it** and
says so in the file header — observe-only, not consumed by any sizing — so there
is a construct to borrow and **no result**. His de-vig is the crudest method
(normalise `1/decimal_odds` to sum to 1) and should not be inherited by accident.
And it needs a free key from `the-odds-api.com`.

# 6. THE COUNTS

    Reddit/Mastodon   16 threads   of 7,411 gated
    YouTube           60 in read set of 750; 1,135 transcripts on disk; 484 claims
    GitHub            6 now, was 4, of 4,017

**Two reads is not a fix and I will not call it one.** 6 of 4,017 is 0.15%.
**What changed is that the corpus stopped being unopened** — and the most
valuable thing in it was a *document*, which says the next reads should target
repos with `research/` or `docs/` folders rather than the top-scoring bots.

**The constraint nobody had written down:** unauthenticated GitHub allows **60
requests an hour** and reading a repo properly costs 4–10. **That caps honest
reading at 6–15 repos an hour.** This will never be a bulk job; selection beats
throughput, which is the same lesson as reading beating scoring.

# 7. PLATFORM ACCESS TABLE — written, and one row is worth his time

All seven platforms in `PLATFORM_ACCESS.md` with route, cost, what he must do,
and what it actually gives us.

**The one account I would actually ask him for is `the-odds-api.com`** — free
tier, and it is the only free source of the book-disagreement measure in item 5.
**I have NOT verified its signup screen and I say so in the file** rather than
inventing a menu path; if what he sees does not match, he describes it and I work
from that.

**Reddit has a 2026 approval gate I could not confirm.** Independent write-ups
say new API access now routes through a manual approval form. **I could not check
it against Reddit's own pages — they refuse our fetches and the search tool
refuses the domain.** So it rests on one class of source and is labelled
unconfirmed. It blocks nothing today: we use Arctic Shift, not Reddit's API.

# 8. THE TWO STANDING ITEMS, FOR THE FIFTH TIME

`signal-github/DECISIONS.md` (5,735 bytes) and `youtube-signal/DECISIONS.md`
(4,892 bytes) are on disk and on `origin/main`, committed **df56707 on
2026-08-08**. **And `GUARDS.md` #26 was added in 06f309d** — the row-count guard
you asked for in 009 is already there.

Both items have now been re-issued after being completed. **Something upstream
regenerates them from a stale check.** Worth finding: a phantom task repeated
five times is how a real one gets buried, and this reply is the fifth time I have
spent words on it instead of on work.

# BEFORE REPORTING — the Referee's three lists

**STANDS.** The triage counts — every one of the 100 actually run through
`idea.py`, not sampled. `book_dispersion` — read out of the source file, with the
author's own observe-only header quoted. The YouTube owner-only finding — Google's
own reference plus two independent developer reports of the same 403.

**DOWNGRADED.**
- was: "switch to the official YouTube key" (offered four times)
  now: **withdrawn — that option does not exist.**
- was: "9 strategies nobody here has tried"
  now: **"9 matched nothing, of which one is a proven false negative, two are
  too vague to be strategies, two need platforms we cannot read, and two are
  duplicates"** — leaving two real ones.
- was: (implied by the ask) reading GitHub would surface untried strategies
  now: **it surfaced that 87 of 100 are already ours** — a more useful result
  than a list, and the opposite of what I expected going in.

**FOR THE USER — genuinely unresolved. Two.**
1. **YouTube, now correctly stated as two-way:** keep taking transcripts from a
   path YouTube's rules file disallows, or lose them. There is no official
   route to a stranger's captions.
2. **The Polymarket archive, still open from 009:** 1.15 TB, free, 118 days with
   no gaps, on a host under a shutdown order.
