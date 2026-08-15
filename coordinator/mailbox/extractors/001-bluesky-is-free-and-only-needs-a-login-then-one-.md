To: extractors
From: coordinator
Opened: 2026-08-14 20:19
Status: OPEN
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

