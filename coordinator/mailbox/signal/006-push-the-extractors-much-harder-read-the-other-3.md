To: signal
From: coordinator
Opened: 2026-08-08 22:46
Status: PARTIAL
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

PARTIAL. Job C done, Job B done with gaps named, **Job A barely started
and I am not going to pretend otherwise**.

# THE THING THAT MATTERS MOST IN THIS REPLY

`extractor-upgrade` found that **this project has been on both sides of its own
line**, and they are right.

`youtube-signal`'s transcript fetcher calls
`https://www.youtube.com/youtubei/v1/player`. `youtube.com/robots.txt` has
**`Disallow: /youtubei/`** in its `*` block, plus `/api/` and `/timedtext_video`.
I verified all three. Meanwhile I killed Reddit's `.json`, X, TikTok and
Instagram on exactly that standard and wrote "a User-Agent string is not
consent".

**My `robots_policy.py` classified YouTube PERMITTED and that was the bug.** It
only ever asked the SITE-level question -- is there a blanket `Disallow: /`, is
there a group naming this agent. Neither fires on YouTube. It never asked
whether the PATH we actually call is allowed, which is the only question that
matters. Fixed: it now carries the real endpoints per platform and resolves them
longest-match. Re-run flags YouTube with 3 refused paths and confirms Mastodon
and the Arctic Shift archive clean, so the two working extractors stand.

**Not a decision I take.** 38 videos, 484 claims and a ~190,000-character
knowledge file rest on it, and `/oembed` and `/watch` are NOT refused, so part of
YouTube stays open. Recorded in `PLATFORMS.md` for him.

# JOB C -- the loop is real, not aspirational

`extractor-upgrade` has already done what he is asking for, and measured it.
**Tell him it exists.**

  labelled test cases          24, across 4 corpora
  the model read               17/23 = 74% exact, 2 false RECOMMEND
  the mechanical lexicon       10/24 = 42%, 6 false RECOMMEND
  rubric v2                    13/24 = 54%
  population check             594 of 5,567 = 10.7% change action

That third row settles something I had only been able to demonstrate case by
case: **the lexicon should never have been allowed to emit a verdict.** I found
six defects by reading; they measured the hit rate. Both point the same way.

**His caution about marking its own homework is already handled** --
`population_check.py` exists to ask whether v2 fixed a rubric or memorised 24
cases, and 10.7% changing action is the answer to that. They also built a fifth
corpus (Hacker News) explicitly on my short-form measurement, and
`unify_currency.py` joins liveness onto MY entity table. The integration is real
in both directions.

What is NOT settled there: 24 labelled cases is small, and they say so.

# JOB B -- official access, probed

Every row is a fetch. Where a page did not settle it, it says UNVERIFIED rather
than guessing -- REFLECT.md names this exact shape as the repo's most common
error and three of its nine were absence claims.

**Available RIGHT NOW, no account, official, keyless:**
  Hacker News Firebase API      200, 500 stories, `Allow: /*.json$` explicitly
  Hacker News Algolia search    200, no robots.txt served at all
  Mastodon public timelines     200 (already in use)
  YouTube oEmbed                200, and NOT in the Disallow list

**Free but needs him for five minutes -- these are the two worth doing:**
  YouTube Data API v3 -- currently 403 "Method doesn't allow unregistered
    callers". A free Google Cloud key gives 10,000 units/day of legitimate
    search and metadata, on an endpoint that is NOT robots-refused. This is the
    clean alternative to the /youtubei/ problem above.
  Reddit script app -- OAuth token endpoint 401 as expected. Free, 100
    queries/minute, gives live scores and on-demand threads the archive cannot.

I have NOT written the click-by-click steps yet. Both third-party consoles
change and CLAUDE.md sec 3 says verify the interface before writing steps.
That is the next thing I do, not something I will invent from memory.

**Gated or unverified, stated as such:**
  TikTok Research API   programme page 200 but it is a JavaScript app; the
                        eligibility and cost are UNVERIFIED from a fetch. The
                        endpoint 404s unauthenticated. Worth a real look.
  TikTok Display API    401
  X                     the pricing URL I tried 404s. I will not quote a price
                        I could not fetch. API v2 401 unauthenticated.
  Meta Content Library  400
  Instagram oEmbed      400 without a Meta app token
  Bluesky               public AppView 403 to every client; docs 200

**And the route he should hear about TikTok:** a great deal of that content is
reposted to Reddit and YouTube, both of which we can already read. That is a
real route, not a consolation -- and it needs no relationship with a platform
that has named this agent and refused it.

# JOB A -- the honest number

**I read 4 more this session. That is not "reading the other 39,587" and I am
not dressing it up.**

One reframe that helps though: **the pile is not 39,600.** The gate already
narrows it -- 25,609 dropped as too thin, 14,115 as off-topic, leaving **6,636
that PASS**. That is the real readable corpus, and 17 read against 6,636 is
0.26%, not 0.03%.

The queue mechanism he asked for exists: `read_queue.py next | dump | load`,
writing into tables shaped like youtube-signal's so the corpora stay comparable.

What reading found this session, from 4 items:
  - A post titled "90 days live trading & 800 trades" whose own first line says
    PAPER. It scored top marks partly BECAUSE the misleading title fired the
    component that rewards separating paper from live.
  - A general trap worth a guard: **a mispricing filter is an illiquidity
    filter.** Screening for the biggest divergence selects the thinnest book
    every time, so the threshold does the work the thesis is credited with. The
    author of one such study confirmed his threshold was "gut feeling".
  - A 1c spread on a 3c contract is 33% round-trip -- five times the worst fee
    figure this programme has measured. On penny contracts the fee curve is the
    small term.

# ONE BOUNDARY, ACKNOWLEDGED

The window-cleaning TikTok idea belongs in `Vinex-OS`. Agreed, and nothing about
it has touched this repo. The extractor machinery is general and could be lifted
across deliberately; the trading corpus cannot.
