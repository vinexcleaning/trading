To: extractors
From: coordinator
Opened: 2026-08-14 20:19
Status: BLOCKED
Subject: Bluesky is free and only needs a login - then one $5 trial across X, TikTok and Instagram

--- INSTRUCTION ---

You are a NEW chat. Create `extractor-apify/` with `README.md`, `HANDOFF.md`
and `DECISIONS.md`.

**Your job: find out which social platforms are worth paying a vendor for, by
spending as close to nothing as possible.**

# ⚠ THE CREDENTIAL RULE, FIRST, BECAUSE IT ALREADY WENT WRONG ONCE

**The user pasted his Apify token into a chat window on 2026-08-14.** He has
been told to revoke it and store the replacement at `C:\Users\vinig\keys\apify.txt`,
**outside this repo, which is public.**

- **Read the token from that path at runtime. Never copy it into a file here.**
- **Never print it, never log it, never put it in an error message.**
- `.gitignore` now blocks `*apify*token*`, `apify.txt`, `*_token.txt` and
  `keys/` **as a backstop, not as permission.** The rule is that it lives
  outside the repo.
- **Copy `livedesk/tests/test_paper_only.py` into your `tests/`** and adapt it:
  it must fail the build if a token-shaped string appears anywhere in your
  folder. Keep its planted-violation test.

# THE STATE OF PLAY, MEASURED 2026-08-14

| platform | route | price | who runs it |
|---|---|---|---|
| **X / Twitter** | Apify `apidojo/tweet-scraper` | **$0.40 / 1,000** | community, 7,262 users |
| **TikTok** | Apify `clockworks/tiktok-scraper` | **$1.70 / 1,000** | **Apify**, 19,583 users |
| **Instagram** | Apify `apify/instagram-scraper` | **$2.70 / 1,000** free tier | **Apify**, 39,364 users |
| **Bluesky** | free, needs a login | **$0** | — |

**X through Apify is ~12x cheaper than buying from X directly** (their own API
is about $5 per 1,000 posts). **Verify that before relying on it** — I read it
off the store page, not from an invoice.

**Apify free tier is $5/month and stops dead when spent** — no overage. That is
the budget.

# JOB 1 — BLUESKY FIRST, BECAUSE IT IS FREE

`social-signal/PLATFORMS.md` records Bluesky as **closed**: `403 Forbidden` to
every client on `public.api.bsky.app/xrpc/app.bsky.feed.searchPosts`.

**That is not a block, it is a login requirement**, and it is a documented quirk
— `bluesky-social/bsky-docs` issue #332. The docs say it works logged out and it
does not.

**So: a free Bluesky account, authenticate, and the search works.** Write the
click-by-click for him if account creation is needed — he will do it.

**Then correct `PLATFORMS.md`.** It currently reads *"permitted, and it still
says no"* and that is wrong. **Mark the correction inline, do not delete the old
line** — `CLAUDE.md` §6.

# JOB 2 — ONE PAID TRIAL, THREE PLATFORMS, INSIDE THE FREE $5

**Same question on all three, so the answers are comparable:**

| platform | volume | cost |
|---|---|---|
| X | 5,000 posts | $2.00 |
| TikTok | 1,000 videos | $1.70 |
| Instagram | 500 posts | $1.35 |

**$5.05 total.** Five pence over the free credit — **so trim one of them
slightly rather than triggering a charge. Do not spend his money without
asking.**

**The question to search is not "trading".** Use something specific enough that
a hit is obviously a hit — Kalshi, Polymarket, prediction markets, named
strategies. **Say what you searched, exactly, so the result can be reproduced.**

## WHAT DECIDES IT — and this is the whole point of the trial

**Not volume. Substance per dollar.**

The bar to beat is already known: **13 Reddit threads produced one stranger's
study of 4,604 real resolved markets with denominators on every claim.** That is
what a good source looks like.

**So for each platform report: how many items came back, how many contained a
claim with a sample size attached, and what the best single item was.** A
platform returning 5,000 posts of opinion is worth less than one returning 50
with numbers in them.

**Reuse the existing rubric** — `social-signal/src/rubric.py`, three scores
never averaged. Do not write a new one.

# JOB 3 — IS APIFY THE RIGHT VENDOR AT ALL?

He asked directly. **42,715 actors from 2,148 publishers is the scale, but scale
is not the question.** Check the alternatives — Bright Data, ScrapingBee,
Firecrawl, Zyte, and anything else that actually competes — on **price for the
same platforms, whether they run the scraper or sell you a proxy, and what the
free tier is.**

**Say plainly if Apify wins.** It probably does on integration breadth, and
saying so with the comparison behind it is a result.

# WHAT IS OUT OF SCOPE

- **Google Maps.** The biggest thing on Apify by users and it is local business
  data. **That belongs to `Vinex-OS`, not this repo** (`CLAUDE.md` §7). Note it
  in your handoff and stop.
- **Do not go round any platform's stated rules.** Apify is a vendor with its
  own terms; that is a different thing from us evading a robots policy, and the
  line does not move.
- **Do not touch `livedesk/` or `kalshi-inplay-bot/`** — another tool is editing
  both.

# BEFORE REPORTING

`py -3 coordinator\reflect.py --file <draft>` then `--referee`. Both.
**No statistics words.** Money, or out of 100.

--- REPLY ---

The session that owns `extractors` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**Answered 2026-08-14 by the `extractors` chat.** Folder created:
`extractor-apify/` with `README.md`, `HANDOFF.md`, `DECISIONS.md`,
`PREREGISTRATION_BLUESKY.md`, `tests/test_no_secrets.py` and two reports.

**Jobs 1 and 3 are DONE. Job 2 is BLOCKED on one free signup — and it is now a
free one, which it was not when this was written.**

---

## Two things in this instruction are wrong, and both matter

**1. "Bluesky is free and only needs a login." It needs no login.**

`PLATFORMS.md`'s 403 is real and reproduces today — **on
`public.api.bsky.app`.** `api.bsky.app` returns **200** to the identical
logged-out request. `src/ua_test.py` puts **7 clients × 2 hosts × 2 tries**: a
browser string, an honest research string, a bare project name, Python's
default, an **empty** User-Agent and `curl` all get 200 on one host and 403 on
the other. **Not User-Agent filtering, nothing talked round**, and
`api.bsky.app/robots.txt` permits it in words.

So **no account was created and no click-by-click was written.** Asking him to
sign up for something that needs no signup spends the thing §9c calls scarce.

`PLATFORMS.md` is corrected inline with the original left standing. ⚠ **That is
`signal`'s file** — flagged in `STATUS.md` rather than done quietly.

**2. The $5.05 trial cannot be run for $5.05.** `apidojo/tweet-scraper` gives
free accounts **demo mode only: 5 runs of 10 items a month, and no API access at
all.** 50 posts, not 5,000. Two independent sources including its own store
page. **The real Apify cost of that arm is $29–39 for a plan first, then the
$2.00.** Nothing was bought; `C:\Users\vinig\keys\` does not exist on this
machine.

## The trial should run on Bright Data, free

**5,000 records every month, recurring, no card, hard stop instead of a bill**,
covering X, TikTok and Instagram. That is **more than the whole plan asked for,
at $0** instead of $31–41. Trim to 3,500 X + 1,000 TikTok + 500 Instagram.

⚠ **Caveat kept honest:** "no card" is Bright Data's word about its own billing,
on two of its own pages — one source twice. Unverified until an account exists.

**Apify's $0.40/1,000 for X is real and is the cheapest number found**, ~12×
cheaper than X's own API ($0.005 a post read, 2026 rates — that part of this
instruction checks out). It is the right place to **scale**, after evidence.

## Bluesky's content answer is a null, and a clean one

**3,671 posts, 322 reply threads expanded.** Scored on
`social-signal/src/rubric.py`, gate copied verbatim from `reddit_score.py`.

| | items | clear the gate | recommend-grade | **carry a real number** |
|---|---|---|---|---|
| reddit (threads) | 41,552 | 4,804 (11.6%) | 301 | **302** |
| mastodon (posts) | 19,281 | 2,607 (13.5%) | 4 | **9** |
| **bluesky (posts)** | 3,671 | 837 (**22.8%**) | 1 | **0** |

**The one recommend-grade post is a Craft CMS package** that matched because
*"a neutral audit event contract"* contains the search term. **All three
sample-size hits are the words "30 days".** Read, not scored.

**Zero is an absence claim**, so it was tested the way this repo requires: a
second, wider pattern for the shapes `S3` is blind to (single digits, written
numbers, win–loss records, "N out of M") raised **13 more candidates and all 13
were read.** None is a performance claim.

Threads help — gate passage 22.8% → **64.0%**, recommend 0.12% → 0.49% — **and
one item in 206 is still one item.** The best thing in the whole corpus is a
second-hand claim about someone else's bot (113 trades an hour at $2.12 average,
$500K in 5 months) from an account that sells bot-building, with no artifact and
no win rate.

## Two findings that outlive Bluesky and belong to `signal`

**1. `S3` is 37% duration phrases on Reddit too.** Splitting the pattern's own
clauses over 479 firings: **302 carry a real countable unit, 177 fired only on
something like "30 days" or "14 Days Free".** Reddit's real rate is **6.3 per
100** of what clears the gate, not 10.0. The claim survives; the headline was
inflated by a third.

**2. The rubric half-survives a placebo.** 4,000 Reddit threads with the words
shuffled inside each document still score **5.6 per 100** recommend-grade
against **11.4** real, and gate passage barely moves (14.7 vs 16.5). Some
components are legitimately single-word, so it is not broken — but a recommend
verdict is about **2-to-1 over vocabulary alone**. **Nothing was adjusted.**

**3. And the unit confound is real but small.** Reddit was scored on
post+comments and Mastodon on posts alone. Fixing it moves the gap **41× → 34×**
— one part in six was the artifact. **The published conclusion stands.** I
expected it not to.

## What is needed from him — one thing

**Open a free Bright Data account.** No card, no spend. Exact steps in the
session report. Then the three-platform trial runs at $0.

**Do not buy an Apify plan for this.**

## Not done

Six of ten pre-registered search terms (the sparse ones); 487 of 809 reply
threads; **nothing actually run on any vendor** — every price is a list price
read 2026-08-14 and expires in 3 months, and **success rates are not compared at
all**; whether any vendor returns reply threads; `xquik/x-tweet-scraper` at
$0.15/1,000, under half `apidojo`'s price, unchecked. **Google Maps: out of
scope, it is `Vinex-OS` work.**

Both checkers run on both reports. The Referee's three lists are at the end of
each, and list 3 is not empty in either.

---

## UPDATE 2026-08-18 — he confirmed the Bright Data account. Still BLOCKED, on a different thing.

**An account is not a credential.** The Web Scraper API authenticates with a
**Bearer API key**, and there is none on this machine. Checked, not assumed:
`C:\Users\vinig\keys\` does not exist, `BRIGHTDATA_TOKEN` is unset, and nothing
under his home directory matches `*bright*` or `*brd*`.

Creating the key means signing into his account, which this session may not do.
**So everything that does not depend on it is built and tested**, and the trial
runs the moment the key lands:

- `PREREGISTRATION_PAIDTRIAL.md` — written **before any record was pulled**.
  6 search terms, 3,500 X + 1,000 TikTok + 500 Instagram = the free 5,000, the
  read-every-hit rule, and what result would make me drop the idea entirely.
- `src/brightdata.py` — `preflight` (spends nothing) and `run`.
- `tests/test_brightdata_safety.py` — **the money guard**, 13 tests.
- `GET_THE_TOKEN.md` — five minutes, no card, verified against Bright Data's
  live documentation on 2026-08-18 rather than written from memory
  (`CLAUDE.md` §3).

**17 tests pass.**

## What the money guard actually stops, and why each has a planted violation

**1. Spending past the free allowance.** `HARD_CAP = 5000`. Spend is counted on
records **returned**, not requested — billing is per delivered record, and
counting requests would let an under-delivering run quietly buy a second
helping. The check runs **before** each request. One test seeds the allowance as
fully spent, replaces `trigger()` with a function that raises, and asserts the
run returns cleanly having never called it. There is also a test asserting
`HARD_CAP == 5000` whose failure message says: **raising it is a decision to
spend money and does not belong in a code change.**

**2. Guessing which scraper to use.** ⚠ **Bright Data does not publish the
`dataset_id` values for X, TikTok or Instagram discovery-by-keyword.** Four
documentation pages were read on 2026-08-18 — the Web Scraper API overview, the
trigger reference, the social-media-APIs overview, and the per-platform
introductions for X and Instagram. All four give the *shape* (`gd_` prefix,
endpoints named `{platform}-{object}-{action}-by-{input}`); **none carries the
values.** They live in the account's own Scraper Library, behind the login.

So the client **asks the account** and matches on platform **plus** post/video
**plus** evidence of discovery-by-keyword. **If two match, or none does, it
stops and prints the candidates.** A test plants two matching X entries and
asserts nothing is chosen; another plants an Instagram *collect-by-URL* entry
and asserts it is refused, because we have keywords and not post URLs and
triggering that would spend allowance for nothing.

Hardcoding an id off a blog post would have been quicker and is precisely the
failure `CLAUDE.md` §3 names — except here it costs money rather than an
afternoon.

**3. The key entering the repo.** The credential guard now knows Bright Data's
UUID-shaped key **and knows what not to flag**: a bare UUID is deliberately
ignored, because snapshot ids, dataset ids and request ids look identical and a
guard that cries wolf gets suppressed, which is how a real leak walks through.
What fires is a UUID **next to a Bright Data word** — what a paste looks like —
plus the `brd-customer-...` proxy format. Both carry plants; three new clean
cases were added to the cry-wolf test.

## One prediction recorded before the run, so it can be wrong

`PREREGISTRATION_PAIDTRIAL.md` says all three paid platforms will behave like
Mastodon and Bluesky — high on-topic passage, near-zero items carrying a real
denominator — and that if any beats the others it is **X**, because it is the
only one of the three where written argument is the native format.

**It also says what would make me drop the whole idea:** fewer than 5 items
across all three carrying a real countable denominator means paying for social
data does not buy substance, at any price. **And what would make me recommend
paying: one item of the shape the bar describes.** One was enough on Reddit.

## Still needed from him — one thing, and it is not the account

**The API key**, saved to `C:\Users\vinig\keys\brightdata.txt`. Steps in
`extractor-apify/GET_THE_TOKEN.md`. **No payment details at any point** — if a
screen asks for a card, that is not this and he should stop.
