# The extractors: what exists, what cannot, and why

One table, then the evidence. Every row is a measurement, not a recollection —
reproduce with `python src/robots_policy.py` and `python src/probe_platforms.py`.

| platform | extractor | permitted? | returns scoreable text? | status |
|---|---|---|---|---|
| **Reddit** | `reddit_fetch.py` | via archive | **yes — full posts + comments** | **WORKING · 39,633 posts, 12,846 comments** |
| **Mastodon** | `mastodon_fetch.py` | **yes** | **yes — full post text** | **WORKING · 5,870+ posts** |
| **YouTube** | *(sibling `youtube-signal`)* | **site yes, ENDPOINT NO** | yes — transcripts | ⚠ **see below** |
| TikTok | — | **NO — names this agent** | (caption available, moot) | **refused** |
| X / Twitter | — | no — `Disallow: /` | no — API 401, oEmbed 404 | **refused + closed** |
| Instagram | — | no policy served | no — login wall | **closed** |
| Facebook | — | named, path-list only | **no — every endpoint 400** | **closed** |
| Bluesky | — | yes | **no — 403 to every client** | **closed** |
| Threads | — | no policy served | not reached | closed |

Two independent questions decide each row, and conflating them is how you talk
yourself into a scraper:

1. **Does the platform permit an agent of this kind?** Not "does robots.txt have
   a `*` block" — see TikTok below.
2. **Does it hand back text a rubric can grade?** A title, an author and a
   thumbnail score nothing.

---

## ⚠ YouTube — this project has been on both sides of its own line

**Found by `extractor-upgrade`, verified here, and it is a real inconsistency.**

This file classified YouTube **PERMITTED**, because `youtube.com/robots.txt` has
no `Disallow: /` in its `*` block and names no AI agent. Both true. But the
checker only ever asked the **site-level** question, and the `*` block contains:

```
Disallow: /youtubei/          Disallow: /api/          Disallow: /timedtext_video
```

`youtube-transcript-api` — the library behind `youtube-signal`'s entire corpus —
calls **`https://www.youtube.com/youtubei/v1/player`** (`_settings.py:2`).

**So the transcript pipeline runs on a `Disallow`ed endpoint**, while this same
project killed Reddit's `.json`, X, TikTok and Instagram on exactly that
standard and wrote *"a User-Agent string is not consent"*. `extractor-upgrade`
put it plainly: *"the project has been on one side of a line it drew itself on
the other side of."* They are right.

**`robots_policy.py` is fixed** — it now checks the specific paths this
programme calls, longest-match, and prints every refused one. Re-running it
flags YouTube with 3 refused paths, and confirms Mastodon and the Arctic Shift
archive are clean at path level too, so the two working extractors stand.

**What this is NOT: a decision.** The stakes are 38 videos read, 484 claims and
a ~190,000-character knowledge file, and `/oembed` and `/watch` are *not*
refused, so parts of YouTube remain open. **This is the user's call, and the
options are not equivalent.** It is recorded here so the inconsistency is
visible rather than resting on nobody having checked.

## TikTok — the one that nearly got built

TikTok's `User-agent: *` block is **permissive**, and generously so:

```
User-agent: *
Allow: /foryou      Allow: /discover    Allow: /tag
Allow: /music       Allow: /share       Allow: /amp
Disallow: /search?  Disallow: /search/video?
```

`/tag` is a complete discovery path — hashtag pages list videos. And TikTok's
oEmbed endpoint is **documented, keyless, and returns HTTP 200** with the full
post caption in its `title` field:

```
title  (82 chars)  Scramble up ur name & I'll try to guess it😍❤️ #foryoupage #petsoftiktok
author_name        Scout, Suki & Stella
author_unique_id   scout2015
```

Discovery plus text. Everything an extractor needs. **And it is not ours to
take**, because the file *opens* with a different group:

```
User-agent: GPTBot          User-agent: OAI-SearchBot
User-agent: anthropic-ai    User-agent: ClaudeBot
User-agent: Claude-User     User-agent: Claude-SearchBot
User-agent: PerplexityBot   User-agent: meta-externalagent
User-agent: CCBot           User-agent: Bytespider          ... and 15 more
Disallow: /
```

**robots.txt specificity means the named group wins over `*`.** TikTok names
this agent **four times** and refuses the entire site. The permissive block is
for search engines. Building on `/tag` would require not identifying as what we
are, and the whole value of this project is that its refusals are real.

*This is a stronger and more honest answer than the one this project gave
first*, which was that short-form video is marketing-dominated. That remains
true and measured — sub-minute video clears `youtube-signal`'s substance gate at
**31.6% [19.1, 47.5]** against **66.3% [61.9, 70.3]** at 10–30 minutes — but it
was never the binding constraint.

## X / Twitter — refused, and now closed as well

`robots.txt` is `Disallow: /` for `*`; no group names us, so `*` binds. Beyond
that, both routes are shut:

- `api.x.com/2/tweets/search/recent` → **401 Unauthorized** (paid tiers only)
- `publish.twitter.com/oembed` → **404**. This is new. It was the one documented
  keyless X endpoint and it no longer answers.

Working scrapers exist — `twikit` (4,599★, *"Twitter Internal API | Free"*),
`nitter` (13,394★) — and they work by calling X's internal API without a key.
That is the circumvention route, not an alternative to it.

## Facebook — permitted in principle, closed in practice

Facebook's robots.txt **does** name `ClaudeBot`, but with a long path-specific
`Disallow` list rather than a blanket refusal — so parts of the site are
formally open to us. It does not matter:

| endpoint | result |
|---|---|
| `graph.facebook.com/v20.0/oembed_post` | **400** `(#100) Invalid parameter` |
| `facebook.com/facebook` (public page) | **400** |
| `mbasic.facebook.com/facebook` | **400** |

Nothing keyless returns anything. Closed, not forbidden — a distinction worth
keeping, because it could change if Meta reopens an endpoint.

## Instagram and Threads — no policy served at all

Both return **HTML** at `/robots.txt` — Instagram 400 KB of it, Threads 257 KB.
That is not a permissive robots file; it is **no robots file**, and absence of a
stated policy is not permission. Instagram's legacy keyless oEmbed now serves a
login wall, and `graph.facebook.com/instagram_oembed` returns **400** without a
Meta app token.

## Bluesky — permitted, and it still says no

The only platform where robots and reality disagree in this direction.
`robots.txt` permits everything, and the AT Protocol AppView is designed to be
consumed publicly. But:

```
public.api.bsky.app/xrpc/app.bsky.feed.searchPosts  ->  403 Forbidden
```

**403 to a research User-Agent and 403 to a browser User-Agent alike**, so it is
not UA filtering and there is nothing to "fix" that would not be circumvention.
Recorded as closed. Worth re-testing later — this one looks like infrastructure,
not policy.

## Reddit — refused at the site, permitted at the archive

`reddit.com`, `old.reddit.com` and `oauth.reddit.com` all serve
`User-agent: * / Disallow: /`, and the `.json` route returns **403**.

Collection runs against **`arctic-shift.photon-reddit.com`**, the public research
archive that replaced Pushshift for non-moderators: `robots.txt` is `Disallow:`
(empty — everything permitted), a documented JSON API, and `X-RateLimit-Reset`
headers the client obeys.

> **Stated plainly, because it is the uncomfortable part:** with a browser
> User-Agent, `reddit.com/r/algotrading/.rss` returns **200 and 54 KB** of live
> content. The constraint is not technical. The most popular tool in this space,
> `last30days-skill` (57,240★), solves the same problem by scraping the site
> anyway and says so in its README. Both work. Only one is inside the site's
> stated rules.

## Mastodon — the one that just works

Permitted by robots, keyless, and it returns everything the rubric needs.

| instance | `/timelines/public` | `/timelines/tag/<tag>` |
|---|---|---|
| mastodon.social | needs a token | **OK** |
| mas.to | **OK** | **OK** |
| fosstodon.org | **OK** | **OK** |
| mstdn.social | **OK** | **OK** |

Per post: full text, author handle, ISO timestamp, favourite count, reply count,
language, and a permalink. Discovery by hashtag, paginated with `max_id`.

It is not a like-for-like X replacement — the population is smaller and skews
technical — but it is the same *shape* of content (short public posts, threaded
replies, engagement counts), it permits us, and it is free.

### And now that it is graded: high passage, almost no substance

Both platforms scored on the **same** rubric, split because a rate averaged
across them is an average of two different objects:

| platform | items | PASS the gate | recommend-grade | recommend rate |
|---|---|---|---|---|
| **reddit** | 39,633 | 4,434 (11%) | **282** | **6.4% of PASS** |
| **mastodon** | 6,727 | 2,202 (**33%**) | **4** | **0.18% of PASS** |

Mastodon clears the on-topic gate at **three times Reddit's rate** and yields
recommend-grade items at **one thirty-fifth** of it. `DROP_G1_THIN` — under 200
characters of thread text — fires on 64% of Reddit and only 5% of Mastodon,
which is the mechanism: Mastodon posts almost always have *some* text, and
almost never enough.

**This is the short-form finding again, on a text platform.** `youtube-signal`
measured sub-minute video clearing its substance gate at 31.6% against 66.3% for
10–30 minutes. The constraint was never the medium — it is **length**, and a
500-character post cannot carry a cost side, a sample size and a mechanism any
better than a 60-second clip can.

**Practical consequence: keep Mastodon, but weight it as a discovery layer, not
a substance layer.** It is cheap (189 calls, 0 errors, 13 minutes for 6,727
posts) and it names tools and links out. It will not produce the 4,604-window
autopsy that r/Polymarket produced.

### The component audit says exactly *why*, and it is not a broken instrument

The obvious worry with a 35× gap is that the rubric simply cannot reach short
posts. Splitting the component firing rates per platform settles it — and the
answer is the opposite of "broken":

| component | reddit (n=4,434) | mastodon (n=2,202) |
|---|---|---|
| **S5 — names specific tools, sites or steps** | 35.8% | **82.8%** |
| S1 — names the cost side | 17.5% | 4.0% |
| S2 — separates backtest from live | 24.7% | 2.7% |
| S3 — states a sample size | 9.9% | **0.5%** |
| S4 — gives a mechanism | 27.2% | 2.6% |
| B1 — shows working code | 3.8% | 0.9% |
| H1 — shows a failure | 4.5% | **0.1%** |
| **H10 — promotes a product, discloses nothing** | 2.1% | **4.9%** |

**Mastodon fires the tool-naming component at 2.3× Reddit's rate and every
other substance component at a fifth to a tenth.** `H3` (a claim with sample
size *and* period *and* capital), `H4` (names its own weakness), `H7`, `H9` and
`B5` are **dead on Mastodon** — zero firings in 2,202 scored posts.

That is a precise description of the content: **a name and a link, and no
argument.** It is why passage is high (S5 alone clears the gate) and
recommend-grade is near zero (nothing else fires). The instrument is working; it
is reporting a real property.

And the one component that fires *more* on Mastodon besides tool-naming is
**H10 — promotes a product and discloses no interest at all**, at 4.9% against
Reddit's 2.1%. More tool-naming *and* more undisclosed promotion is the
signature of a promotion channel, which is what a discovery layer largely is.

> **One dead component, flagged rather than fixed.** `H1b` — "shows a failure
> that sets up a sale" — fired **zero times on either platform**. That is either
> impossible in this corpus or the pattern is broken, and the two are told apart
> by reading, not by adjusting the pattern until it fires.

### Tripling the corpus with broader tags returned exactly nothing

The obvious next move after 6,727 posts was more tags. 25 were added —
`machinelearning`, `datascience`, `programming`, `bitcoin`, `opensource`, `ai`,
`security`, `privacy` and the rest — and the corpus went to 19,281.

| | items | PASS | recommend-grade |
|---|---|---|---|
| the original 10 narrow tags | 6,727 | 2,202 (**32.7%**) | 4 |
| after adding 25 broad tags | 19,281 | 2,607 (13.5%) | **4** |
| **the 12,554 posts added** | — | 405 (**3.2%**) | **0** |

**12,554 new posts, 405 of them on topic, and not one reached recommend-grade.**
`DROP_G3_OFF_TOPIC` went 4,159 → 15,498. The broad tags are pure volume.

This replicates `youtube-signal`'s own retrieval result on a different platform:
narrow venue-specific queries returned **70% PASS against 50%** there, and a
within-family Jaccard of 0.86–0.92 against 0.69–0.76. **Specificity is the whole
game in retrieval design, and "collect more" is not a strategy.**

Keep the narrow set — `kalshi`, `polymarket`, `predictionmarket(s)`, `trading`,
`algotrading`, `quant`, `sportsbetting`, `betting`, `finance`, `optionstrading`.
The rest cost 35 minutes of somebody's bandwidth and bought nothing.

---

## How to run them

```bash
python src/robots_policy.py          # who permits an agent of this kind
python src/probe_platforms.py        # who returns scoreable text
python src/reddit_fetch.py --only comments --comments-for 400
python src/mastodon_fetch.py --tags trading,kalshi,polymarket
python src/reddit_score.py           # one rubric, every platform, split per platform
python src/reddit_stance.py          # tool mentions and sentiment
python src/unified_table.py          # the cross-platform reputation table
```

`mastodon_fetch.py` writes into the same `rd_posts` table behind a `platform`
column, so the gate, the rubric and the stance pass apply to it unchanged. The
table keeps its Reddit-era name deliberately: renaming it would break every
sibling script for a cosmetic gain.
