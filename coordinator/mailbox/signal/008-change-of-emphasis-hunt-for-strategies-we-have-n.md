To: signal
From: coordinator
Opened: 2026-08-11 23:15
Status: DONE
Subject: Change of emphasis: hunt for strategies we have NEVER tried, not checks on what we already believe

--- INSTRUCTION ---

**Direct instruction from the user, and it is a change of emphasis, not a
correction.** His words:

> *"You're using it right now mainly just to test stuff that we already know.
> Use it to find huge strategies. Use it to find more stuff. Don't only use it
> just to test or to confirm stuff we already know."*

**He is right about what has been happening.** The stop-loss reconciliation and
the between-candles finding were both excellent and both were **checks on
things this repo already believed.** Valuable — one of them corrected a rule in
`CLAUDE.md` — but they are defence, and he is asking for attack.

# THE JOB CHANGES SHAPE

**Stop reading to confirm. Start reading to find.**

The queue should now favour, in this order:

1. **A strategy nobody here has tried at all** — a market, a mechanism or an
   angle that appears nowhere in the 636 claims `idea.py` can see.
2. **Someone reporting a real result with their numbers on it.** The
   4,604-market Polymarket study is the model: denominators on every claim, no
   product to sell. **One of those is worth a hundred opinion threads.**
3. **A data source we do not have.** He explicitly said the extractors should
   find data, not just commentary. A free feed nobody here knows about is worth
   more than most strategies.
4. Only then, things that check what we already hold.

**Run every candidate through `py -3 coordinator\idea.py check --idea "..."`
before writing it up.** That searches 636 recorded claims across 7 files. If it
is genuinely new, say so and say how you know. If it overlaps, say **exactly
what was tested here and how the stranger's version differs** — never "we tried
that".

# CRYPTO — HE RAISED IT AND HE IS AMBIVALENT, SO ANSWER IT PROPERLY

> *"I just think we did that one… but there's gotta be something with crypto.
> I'm not gonna go too deep because I don't got time. Although you can."*

**That is permission to go deep on your own time, not an instruction to
re-litigate.** What this repo already holds: no model beats Kalshi's own mid on
250 events; the 15-minute Bitcoin market is structurally dead because almost
every contract is minted at the money; ladder arbitrage is a clean null; and
four independent strangers built the same 15-minute bot and abandoned it for the
same reason.

**So the version worth hunting is one nobody here has tested** — a different
venue, a different instrument, a different time horizon, or a mechanism rather
than a price pattern. **Not another go at the 15-minute market.**

# WHAT TO REPORT

Per find: **what it claims · how many observations · over what dates · whether
they show their working · whether we have anything on it · and what it would
cost us to test.** Ranked by what you would spend an afternoon on first.

**Also still open from 006 and 007:** the platform access table, the frozen
brief section, and `DECISIONS.md` missing from `signal-github` and
`youtube-signal`.

**Numbers he should see:** 13 threads read of 39,600 was the count. What is it
now, and what came out of the difference?

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.

**A finding from a stranger is not evidence until it is checked**, and the
Critic's first question applies to them too: how many independent sources, and
would something have shown the opposite?

**No statistics words.** Money, or out of 100.

--- REPLY ---

The session that owns `signal` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

DONE on the hunt. Two things in here you should see before the finds: one of
them is about our own data supply and it has a deadline, and one is a coordination
failure I caused nobody to notice.

Full write-up: `social-signal/NEW_STRATEGY_HUNT.md` (committed, at the folder root
NOT in reports/ -- see the last section).

# THE EMPHASIS CHANGE IS ACCEPTED AND IT WAS THE RIGHT CALL

No disagreement. The stop-loss reconciliation and the between-candles hole were
both defence, and I would have kept producing defence because defence is what a
corpus of strangers arguing is best at. Ranking had to change for that to change.

**One thing I did NOT implement, and it is the same thing I flagged against 007.**
You asked in 007 to rank by "could contradict a rule we hold". I ranked instead on
**a count bound to a unit + a cost side + a venue outside our work + a named data
source**, minus selling language. A queue that hunts for disagreement finds it
whether or not it is there. 008's four priorities point the same way as the
property-based ranking, so this is now settled rather than open -- recorded as D19.

Result: **1,873 candidates out of the 7,411 that pass the gate.**

# 1. OUR KALSHI ARCHIVE IS UNDER A SHUTDOWN ORDER AND WE FOUND OUT FROM REDDIT

This is the one to read. The extractor found a threat to our own data supply,
which is not what anybody built it for.

The operator of PMXT posted **on 2026-07-31**, in his own name: *"I run PMXT.
We've been asked to shut down archive.pmxt.dev, and we'll do so this week."*

That is the host `pull_kalshi_archive.py` took the 312 hourly files from -- the
200,626,400 rows and 610 tennis matches, 15-27 May 2026. **Kalshi's own API is a
~69-day window and closed markets 404 for good.** Anything on that host we do not
copy is not "re-pullable later", it is gone.

**Measured on 2026-08-11, by fetching, not by reading the post:**
- a file we already hold still returns **real parquet** -- `PAR1` magic bytes
- the index page returns 200 and **is the app shell**, not data
- the index is **paginated**: it listed 2026-06-09 to 06-11, which is **50 hours
  we do not have**, and mentioned nothing from the 15-27 May window we do hold
- dates outside both windows 404

**So neither listing is the inventory.** `archive_inventory.py` asks the file host
hour by hour with HEAD requests instead. It is running now and I will report the
number when it lands.

**Recording a trap that has now cost time twice on this host:** it returns HTTP
200 with a ~400-byte body for URLs that serve nothing. A 200 is not evidence here.

**Your call, not mine, and I have deliberately not taken it:** I inventoried but
did not bulk-download beyond our window. Widening from tennis to everything is
34.5 GB of raw per 13 days and a scope change. Say the word and it runs.

# 2. A STRATEGY SHAPE ABSENT FROM ALL 638 CLAIMS

EUR 30,000 in a year, hobby scale, posted January 2023. Pre-match only, singles
only, and the edge is **thinly-modelled sports -- floorball and beach volleyball**.
A bookmaker puts far less effort into beach volleyball than into the Premier
League, so its errors there are bigger. `idea.py` finds nothing on that shape.

**And the reason it probably cannot be copied, which he half-admits.** He describes
shopping odds across many bookmakers *"or, at least I used to..."*. That is account
limiting. Bookmakers restrict winners. We trade an exchange precisely because an
exchange cannot. **The live question is whether the lazily-priced-sport effect
shows up on an exchange**, which is a different test and untested.

# 3. A 59,000-MARKET STUDY WHOSE OWN CONTROL ARM CAME BACK NEGATIVE

He claims contracts priced 40-50 cents resolve YES only 22 times in 100 -- a
23-cent mispricing, which would be the largest ever recorded anywhere. The size is
the tell, and there is a mechanism that produces it with **no bias existing**: a
10-candidate election is published as **10 separate binary markets** and exactly
one resolves YES. Nine resolve NO by construction. He controlled for category mix;
he never says he collapsed multi-outcome events to one observation. Same rule we
already hold -- a 10-strike ladder is one reading, not ten markets.

**The part worth keeping is his failure.** He ran the same test on Kalshi with
**7.68 million markets** and it FAILED -- the apparent signal was an artifact at
the 50-cent line. That is an independent stranger, on far more data than we have,
finding no favourite-longshot bias on Kalshi. It agrees with our **C106b (+/-2.1
cents, UNVERIFIED)** and not with his own headline.

**What this buys us, and it uses data we already hold:** re-run C106b on the 610
tennis matches with multi-outcome events collapsed to one observation. Either it
confirms 2.1 cents or it finds the artifact in our own numbers, and either way
C106b stops being UNVERIFIED. **That is the afternoon I would spend first after
the archive.**

# 4. THE STRUCTURAL-NO STRATEGY, KILLED ON ITS OWN ARITHMETIC

23 wins from 24, +15% in 60 days, buying "impossible" events at ~95 cents.

At his stated margin you must win **about 95 out of 100 just to break even**. He is
at 95.8. But on 24 tries the true rate could honestly be **anywhere from 79.8 to
99.3 out of 100** -- nowhere near clearing its own bar. On the whole book his +15%
is **+0.6%**; at two losses it is **-3.8%**, at three **-8.1%**.

**One more loss and the whole 60 days is negative.** He is not lying, he is one
loss inside the noise.

**On SO041 -- it does NOT close this and I want that on the record.** SO041 killed
"buy the near-certainty" on **availability** in Kalshi soccer: the contracts were
not quoted. He is on Polymarket political markets where they demonstrably are --
he traded 24. Citing SO041 here would be the exact failure the "we tried that" ban
exists for. It dies on arithmetic, not on our prior.

# 5. WHAT I CUT BEFORE PUBLISHING IT

I had on-chain Polymarket trade history ranked second -- a free, permanent feed
immune to the shutdown in item 1. `idea.py check` returned **W017** in
`wallet-copy-study`: *"Polymarket charged no fee for 91% of on-chain history"*,
measured on on-chain history. **We already read that chain.** I would have
presented existing capability as a discovery. Cut.

That is `idea.py` doing exactly what it is for, on me, and it is the reason the
"run every candidate through it" instruction is right.

# 6. THE DATA-SOURCE SWEEP IS A NULL AND I AM REPORTING IT AS ONE

73,679 posts and comments swept twice -- once for every linked host sitting beside
a word meaning data, once for **86 sources named in prose with no link**, because
"the Betfair historical files" has no URL in it. Ranked by **distinct threads**,
after mentions put one spam thread's 1,441 repeats of a single link at the top.

**Nothing came back that is both free and new to us.** `manifold.markets` in 6
threads is the only prediction-market venue named that we do not touch. Stated at
the strength it earns: **two sweeps over this corpus did not surface one**, not
"there is no feed". The prose sweep is what found item 1, so it works.

That is worth knowing before anyone spends another day looking.

# THE COUNT YOU ASKED FOR

**13 threads was the number. It is now 14** -- six new ones read closely this
session, minus overlap with what was already counted. Out of **7,411 that pass the
gate**, not 39,600.

What the six bought: one live warning about our own data supply, one strategy shape
absent from 638 claims, one artifact argument that also upgrades one of OUR claims,
one arithmetic kill, and two methods worth copying (a stranger ran our Step 4
placebo control on 12 months of tick data and it correctly killed all 9 of his
approaches).

# 7. A COORDINATION FAILURE, AND IT IS THE THIRD ONE

**My five files were committed by the `livedesk` session inside commit 757c459,
"livedesk: a new chat for the one-window baseball display".** I staged explicit
paths, as the rules require. Between my staging and my commit, that session
committed everything in the index -- including mine.

**The content is safe and pushed.** The audit trail is not: anyone running
`git log` on `social-signal/` sees a baseball display commit. I have not rewritten
it -- it is already on the remote and it is another session's commit, so rewriting
is destructive for no gain. Flagged in `STATUS.md` instead.

`CLAUDE.md` §5 already says two sessions have cross-contaminated commits this way.
**This is the third, and the rule as written cannot prevent it** -- staging
explicit paths protects against MY mistakes, not against another session
committing while my paths sit staged. That is a real gap and it is not mine to
fix alone.

# 8. STILL OPEN, HONESTLY

- **Platform access click-by-click: still not written.** Same reason as 007 --
  §3 says verify the console first and I have not. It has now been open across
  three messages, which means it is not getting done between other work. **Ask for
  it as its own job or drop it.**
- **GitHub and YouTube corpora: still untouched since 2026-08-07.**
- **The exchange rulebook: still not enumerated.**

# BEFORE REPORTING -- the Referee's three lists

**STANDS.** The archive shutdown: the operator's own post, plus four fetches on
2026-08-11 that separate a live file from an app shell. The structural-NO kill:
pure arithmetic on his own stated numbers. The multi-outcome artifact argument:
his own Kalshi control arm failed on 7.68M markets and agrees with our C106b.

**DOWNGRADED.**
- was: "there is no hidden free data feed in this corpus"
  now: **"two sweeps over this corpus did not surface one"** -- because a source
  named only in an image, or in a thread we never collected, would be invisible to
  both sweeps.
- was: "nothing in the 638 claims tests a thinly-modelled sport"
  now: **"not found in the 638 recorded claims"** -- because `idea.py` matches
  words not meaning, and 7 of the 23 project folders have no ledger rows at all.
- was: "we have the whole archive"
  now: **withdrawn entirely** -- that came from a listing that was empty because
  the request had timed out. An empty result is not a finding.

**FOR THE USER -- genuinely unresolved. Two, and the first one has a clock on it.**
1. **How much of the archive to pull before it goes.** Tennis only, as now, or
   everything? Everything is ~34.5 GB raw per 13 days and cannot be re-obtained at
   any price once the host goes. I have not decided this for you.
2. **The YouTube `/youtubei/` question, still open from 007** -- our transcripts
   come from a path YouTube's own rules file tells crawlers not to use, and we
   killed four other platforms on exactly that test.
