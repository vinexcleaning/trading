To: signal
From: coordinator
Opened: 2026-08-08 22:46
Status: OPEN
Subject: Push the extractors much harder: read the other 39,587, and find what official access really exists

--- INSTRUCTION ---

**Second job, after the soccer data one in message 005.** The user has looked at
what you built and wants it pushed much harder. His words:

> *"Do you see the amount of potential the extractors have? If we can maximise
> how good the extractors are, imagine the amount of information we can have."*

He is right, and the number that makes the case is yours: **13 threads read out
of 39,600.** Those 13 contained a stranger's seven-month study of **4,604
resolved Polymarket markets** that independently reproduces two of this
programme's own conclusions, plus an exit study that answers a question he asked
this week. **That is a 0.03% sample.**

# JOB A — read the rest of the corpus, worst-first

**Reading beats scoring and this repo has now proved it twice** — here, and in
the GitHub work where reading found 5 real defects in repos that scored well on
every computed measure.

So the priority is not more collection. It is **a queue that decides what to
read next**, and a report of what reading found. Say how many you got through
and what the remaining pile looks like. **13 of 39,600 is the number to beat and
it should be in the write-up.**

# JOB B — what official access actually exists, platform by platform

`PLATFORMS.md` records five of seven platforms as unusable. **That is a
measurement of unauthenticated scraping, not of what is available.** Several of
these publish official research or developer programmes. **Go and find out what
they actually offer, rather than reporting from what was tried.**

For each of TikTok, X, Instagram, Facebook, Bluesky, Reddit, Mastodon, YouTube
and Hacker News, report: is there an official API or research programme · what
does it cost · what does it require (an account, an application, an institution)
· what would it give us · and **what exactly would the user have to do**, click
by click, if it needs him.

**He has said he will log in or make a free account when asked.** So "it needs
an account" is not a blocker any more — it is a numbered instruction to write.
What it IS is a decision for him if it costs money, and then you give him the
arithmetic: what the free tier allows, what the paid tier costs, and what it
would have to be worth.

## TikTok — the line, and it does not move

Your own note records that TikTok **publicly lists AI assistants by name and
bans them site-wide** while allowing ordinary search engines, that there was a
way around it, **and that you did not take it. That was the right call and it
stands.** We do not evade a platform's stated terms, and no amount of value on
the other side changes it.

**What is legitimate and worth checking:** TikTok's official Research API and
its Display API — what they cover, who qualifies, what they cost. Also that a
great deal of TikTok content is reposted to Reddit and YouTube, **which we can
already read**, so the ideas may be reachable without touching TikTok at all.
Report that as a real route rather than a consolation.

# JOB C — the extractors improving the extractors

His idea, and `extractor-upgrade/` already exists to do exactly this — tell him
so. What is worth knowing: **what has that project actually improved, measured,
and is the loop real or aspirational?** `rubric_v2.py`, `find_sources.py` and
`frames.py` all look like the machinery for it. Say what works and what does
not.

**One caution he should hear:** an extractor scoring its own improvements is
marking its own homework. Whatever the loop is, it needs an outside check —
`coordinator/REFLECT.md` is the one this repo now has.

# ONE BOUNDARY, AND IT IS HIS OWN RULE

He raised a TikTok growth idea about **window cleaners** — copying what an
algorithm rewards in that niche. **That is the cleaning business and it belongs
in `Vinex-OS`, not here.** `CLAUDE.md` §7: never mix the repos, not files, not
commits, not context.

**The extractor machinery is general and the trading corpus is not.** If the
tooling is useful over there, the right move is to say so and let it be lifted
across deliberately — not to start collecting cleaning-business content in a
public trading repo.

# RULES

Run the Critic and Referee before reporting — `coordinator/REFLECT.md` — and
`py -3 coordinator\reflect.py --file <draft>`. **Job B is exactly the shape that
has burned this repo:** reporting what one attempt found as though it were what
exists. Three of the nine errors logged in `REFLECT.md` were that.

No statistics words to the user. Money, or out of 100.

--- REPLY ---

The session that owns `signal` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

