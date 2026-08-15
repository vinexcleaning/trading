# VENDORS.md — is Apify the right vendor, and what would it actually cost

**As of 2026-08-14.** Every price here is a list price read off a public page on
that date. Under this repo's own expiry rule a price is a `spec` claim and
**goes stale in 3 months — recheck before spending anything on it.**

**Nothing has been bought. No token has been read.** `C:\Users\vinig\keys\`
**was listed and the directory itself is not there** — so `apify.txt` cannot be,
and nothing in this folder needs it. That is a directory listing, not an
inference.

---

## The short answer

**Apify is a good vendor and it is the wrong one to start with, because
somebody else will do the same job for nothing.**

Bright Data gives **5,000 records every month, free, no card**, across X,
TikTok and Instagram. Apify gives **$5 of credit** — and the cheapest X scraper
on it **will not serve a free account at all**. So the trial the mailbox
instruction described cannot be run for $5.05 on Apify, and can be run for **$0**
somewhere else.

---

## ⚠ The instruction's plan does not work as written, and this is why

The mailbox laid out a $5.05 trial: 5,000 X posts at $0.40 per thousand, 1,000
TikTok videos at $1.70, 500 Instagram posts at $2.70, trimmed slightly to stay
inside the free credit.

**The prices are right. The plan still fails on the first line.**

`apidojo/tweet-scraper` — the $0.40 one — restricts free accounts to **demo
mode: five runs a month of ten items each, and no API access at all.** That is
**50 posts a month**, not 5,000, and you cannot reach it from a script.

Two independent sources say so, including the actor's own store page. That
matters: the recorded failure mode in this repo is reading one source and
concluding, and eight of nine errors in one session had that exact shape.

**So the real Apify price of the X arm is $29–39 for a month of Starter,
and then the $2.00 of posts.** Roughly **$31–41, not $2.00.** It was never a
$5 experiment.

## What each vendor actually sells — and this is the part that decides it

There are two different products being compared and the price-per-thousand
tables hide it.

| | what you are buying | what you still have to build |
|---|---|---|
| **Apify** | somebody else's finished scraper for **this exact site**, returning structured fields | nothing — you call it and get rows |
| **Bright Data** | both: finished per-platform scrapers **and** raw proxy access | nothing, for the platforms it covers |
| **ScrapingBee** | a page fetcher that gets through blocking and hands you **HTML** | the entire X/TikTok/Instagram parser, and you re-fix it whenever they change |
| **Zyte** | same shape as ScrapingBee, priced by how hard the target is | same |
| **Firecrawl** | a page fetcher that returns clean text or structured output | the platform-specific part |
| **ScraperAPI** | a proxy layer, you parse the HTML | same |

**Four of those six are not really competitors for this job.** Buying raw HTML
of a logged-out Instagram page and writing the parser yourself is a project, not
a purchase — and it is a project against a site actively trying to stop it.

**The genuine comparison is Apify against Bright Data.** Everything else is a
different product wearing a similar price tag.

## Price, for the same thing

| vendor | free every month | pay-as-you-go per 1,000 | card needed to start? |
|---|---|---|---|
| **Bright Data** social scrapers | **5,000 records** | **$1.50** | **no** |
| **Apify** X (`apidojo/tweet-scraper`) | 50 items, demo mode, no API | **$0.40** | plan needed first |
| **Apify** TikTok (`clockworks`) | from the $5 credit | **$1.70** | no |
| **Apify** Instagram (`apify/instagram-scraper`) | from the $5 credit | **$2.70** | no |
| **X's own API** | none — free tier discontinued | **$5.00** ($0.005 a post) | yes |

**Apify's $0.40 for X is real and it is the cheapest number on this page** —
about **12 times cheaper than buying the same posts from X directly**, which is
what the mailbox claimed and it checks out. It is just not reachable without a
subscription first.

**Bright Data's 5,000 free is a recurring monthly allowance, not a trial.** Its
own documentation says credits reset on the first of the month, do not roll
over, and the account **hard-stops rather than billing you**.

⚠ **That last part is the one that matters, and it is a vendor's word about its
own billing.** Two Bright Data pages say it — the product page and the billing
docs — and **that is one source twice, not two sources.** No account was created
and no bill was seen. **Treat "cannot accidentally spend" as unverified until
the account exists and shows no payment method on file.** This repo has been
caught by exactly this once already: a vendor page advertised 1,000 requests a
day while its own usage endpoint said 100 (`B022`).

## So what should actually happen

**Run the trial on Bright Data's free tier, not on Apify's.** Same three
platforms, same question, and the volume is larger than the plan asked for:

| platform | the plan wanted | Bright Data free covers it? |
|---|---|---|
| X | 5,000 posts | ✅ |
| TikTok | 1,000 videos | ✅ |
| Instagram | 500 posts | ✅ |
| **total** | **6,500 records** | 5,000/month free — **needs two months, or trim to 5,000** |

Trim to **3,500 X + 1,000 TikTok + 500 Instagram = 5,000** and it fits inside
one month at **zero cost and zero risk of a bill.**

**If it turns out to be worth paying for, Apify is then the cheaper place to
scale X** — $0.40 against $1.50 is nearly 4× — and the $29 plan pays for itself
past about 26,000 posts a month. **That decision comes after evidence, not
before it.**

## What this comparison did NOT test

Required by `CLAUDE.md` §9c Step 7, and written whether the answer is positive
or negative.

- **Nothing was actually run on any vendor.** Every number is a list price off a
  public page. No account was created, nothing was bought, no data came back.
  **Success rates are not compared at all**, and a cheap scraper that fails half
  its requests is not cheap.
- **Bright Data's "no credit card" is from Bright Data.** Its own docs say it,
  and a second page repeats it. Neither is an invoice. It is verified at signup
  or it is not verified.
- **Oxylabs, Decodo, SocialCrawl, twitterapi.io and the smaller X-only
  resellers** were seen in search results and not priced out. At least one
  (`xquik/x-tweet-scraper`) advertises **$0.15 per 1,000** on Apify itself,
  under half `apidojo`'s price, and it was not checked for free-tier gating or
  for whether it works.
- **Whether any of them return the reply threads**, which is where substance
  lives. `PLATFORMS.md` and the Bluesky work here both find that a lone short
  post carries a claim without its denominator. A vendor that sells 5,000 posts
  and no replies may be selling the useless half.
- **LinkedIn, YouTube comments, Reddit via a vendor, Discord** — not priced.
- **Google Maps** — deliberately out of scope. It belongs to `Vinex-OS`
  (`CLAUDE.md` §7).

---

## The Referee — what stands, what is downgraded, what is his

Both checkers run: `py -3 coordinator\reflect.py --file` on this draft, and
`--referee`.

### 1. Stands

- **The mailbox's $5.05 trial cannot be run for $5.05.** Two independent sources
  say `apidojo/tweet-scraper` gates free accounts to demo mode with no API
  access. One of them is the actor's own store page.
- **Apify's $0.40 per 1,000 X posts is ~12× cheaper than X's own API.** X moved
  to pay-per-use in February 2026 at **$0.005 per post read = $5.00 per
  thousand**, and the old $200/$5,000 tiers are closed to new signups. The
  mailbox's claim checks out.
- **Four of the six vendors are not competitors for this job.** ScrapingBee,
  Zyte, Firecrawl and ScraperAPI sell page fetching. Buying raw HTML of a
  logged-out Instagram page and writing the parser is a project, not a purchase.

### 2. Downgraded

- **was:** "Bright Data gives 5,000 records free with no risk of a bill."
  **now:** "Bright Data's own documentation says 5,000 recurring monthly
  credits, no card, hard stop. **Nobody has opened an account to check.**"
  **because:** two Bright Data pages is one source twice. `B022` in this repo is
  a vendor page that advertised 10× its real limit.

- **was:** "Apify is the wrong vendor."
  **now:** "Apify is the wrong vendor **to start with**. It is the cheapest
  place to scale X once something is worth scaling — $0.40 against Bright Data's
  $1.50, with the $29 plan paying for itself past roughly 26,000 posts a month."
  **because:** the two statements were being run together and they are different
  decisions.

### 3. For the user — genuinely unresolved

**One, and it is the signup.**

- **the question:** open a free Bright Data account, or leave the paid platforms
  unmeasured?
- **one side says:** it costs nothing but five minutes, needs no card, and it is
  the only way to answer "is X worth paying for" with data instead of a price
  list. Three platforms, 5,000 records, same rubric.
- **the other side says:** three free platforms have now been measured — Reddit,
  Mastodon, Bluesky — and the two short-form ones produced nothing. **X, TikTok
  and Instagram are all short-form.** The prior on this experiment is poor and
  it costs attention, which §9c says is the scarce thing.
- **what would settle it:** nothing cheaper than running it. **The measured
  reason to run it anyway is that all three paid platforms are much larger than
  Mastodon and Bluesky, and none of the three free nulls tested a platform where
  professionals actually post.**

**And nothing here contradicts another session's published work.** Stated out
loud rather than left off.

## Sources

- [Tweet Scraper V2 — Apify](https://apify.com/apidojo/tweet-scraper)
- [TikTok Scraper — Apify](https://apify.com/clockworks/tiktok-scraper)
- [Instagram Scraper — Apify](https://apify.com/apify/instagram-scraper)
- [Bright Data free tier — Bright Data docs](https://docs.brightdata.com/general/account/billing-and-pricing/free-tier)
- [Social Media Scraper — Bright Data](https://brightdata.com/products/web-scraper/social-media-scrape)
- [X API pricing 2026 — SocialCrawl](https://www.socialcrawl.dev/blog/x-twitter-api-2026)
- [Apify free plan — use-apify.com](https://use-apify.com/docs/what-is-apify/apify-free-plan) *(Apify-affiliated site; treated as a vendor claim, not a neutral one)*
- [Web scraping pricing compared — use-apify.com](https://use-apify.com/blog/web-scraping-pricing-guide-all-platforms) *(same caveat)*
