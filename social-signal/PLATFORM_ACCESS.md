# Official access, platform by platform — what exists, what it costs, what he must do

**As of 2026-08-14.** Owed since mailbox 006 and re-asked in 007, 009 and 011.
It kept losing to live work; that was my call and it was the wrong one four
times running.

**Every row is either something I fetched, or something I read in the
platform's own documentation and have labelled as such.** Where I could not
verify, the row says so rather than guessing — `CLAUDE.md` §3 exists because
instructions written from memory have already cost him an afternoon.

---

# ⚠ FIRST: a correction I owe him, and it removes an option I kept offering

**For four messages I have put this decision to him as three-way:** keep taking
YouTube transcripts from `youtube.com/youtubei/v1/player` (a path YouTube's own
`robots.txt` disallows), stop, **or switch to the official free API key**.

**The third option does not exist.** YouTube's `captions.download` works **only
for videos the authenticated account owns**. Third-party caption download was
removed. So an official key cannot fetch a stranger's transcript at any price,
free or paid.

**This is an absence claim and it is the one in this file that must not be
wrong, so here is what it rests on.** The source that would show third-party
download if it existed is Google's own `captions.download` reference, and it
states an OAuth ownership requirement rather than an API-key path. Two
independent developer threads report the same 403 for videos the caller does not
own, and both describe the third-party-contribution route as **withdrawn by
YouTube**, not as something we configured wrongly. **What I did NOT do: obtain a
key and try it.** That is the only test that would settle it beyond doubt, and
it needs his Google account — so if he wants certainty before deciding, that is
the experiment, and it is an hour.

**His real choice is two-way:** keep the current route, or lose YouTube
transcripts entirely — 1,135 of them are already on disk and 484 claims rest on
them. **I should have checked before offering the third door.**

---

# The table

| platform | official route | cost | what he must do | what it actually gives us |
|---|---|---|---|---|
| **YouTube** | Data API v3 | **free**, no billing account for the default quota | Google Cloud project + enable API + create key | **Metadata and search only.** 10,000 units/day; `captions.list` 50, `captions.download` 200 — but download is **owner-only**, so it does **not** replace what we do |
| **Reddit** | Data API, script app | free tier exists | create app at `reddit.com/prefs/apps` — **but see the 2026 gate below** | Posts and comments via OAuth. **We do not currently need it** — the Arctic Shift research archive is permitted and already gives us 60,833 posts |
| **TikTok** | Research API | free | **academic / non-profit only** | Nothing for us. `robots.txt` names `ClaudeBot`, `Claude-User`, `Claude-SearchBot`, `anthropic-ai` and disallows all four site-wide (read directly 2026-08-09) |
| **X** | paid API tiers | **not free** | — | Refused on terms as well as cost; the free-scraper route works by calling X's internal API without a key, which is circumvention, not an alternative |
| **Instagram / Threads** | Graph API, business accounts | free tier | business account + app review | Serves **no `robots.txt` at all**. Measured: every content endpoint we probed returns nothing usable without login |
| **Facebook** | Graph API | free tier | app + review | Path-listed in `robots.txt`; every endpoint we probed returned 400 |
| **Bluesky** | AT Protocol, public | free | none | **Permitted by `robots.txt`** but returned 403 to every client we tried. Unresolved — worth one more attempt, it is the only open-by-design one |
| **Mastodon** | public API | free | none | **Working now.** 19,281 posts, 189 calls, 0 errors. Our second live extractor |
| **the-odds-api.com** | free tier, key required | free tier | **make a free account, paste the key** | Bookmaker moneylines across US books. Newly relevant — see below |

---

# The two that need him, click-by-click

## A. `the-odds-api.com` — the one I would actually ask for

**Why this one and not the others.** Reading `mbordash/DRADIS` on 2026-08-14
turned up a working, coded integration against this API that derives something
we do not compute anywhere: **`book_dispersion`, the spread between the highest
and lowest implied probability across bookmakers** — how much the books
*disagree with each other*, as opposed to how much we disagree with one book.

That matters because `mlb-paper`'s binding constraint is *"beat Pinnacle"*.
**Book disagreement is a different question from beating any single book**, and
we have no free source for it today.

**Steps.** I have **not** verified this signup screen myself and am not going to
pretend otherwise — the site was not fetched. Functionally: go to
`the-odds-api.com`, find the free-tier signup, give an email, and it returns an
API key. **If what he sees does not match, he should say so and I will work from
his description rather than guess a second time.**

**What to send back:** the key, into a `.env` file — **never into the repo**,
which is public.

**The arithmetic before he bothers:** the free tier is capped per month.
DRADIS's author polls one nearest event at a time, which suggests the cap binds
quickly. **Worth doing only if someone is going to build the dispersion
measure** — not as a general-purpose odds feed.

## B. YouTube Data API key — worth having, but not for the reason we wanted

**It does not solve the transcript question** (see the correction above). It
does give legitimate metadata and search, which is what our discovery layer
currently takes from scraping.

**Verified from Google's own documentation, 2026-08-14:** default allocation is
**10,000 units/day** plus 100 `search.list` calls, **no billing account
required**, and exceeding it needs a compliance audit.

**Steps** — these are the shape of the flow, and the console layout changes
often, so **treat the names as functional descriptions and tell me if they do
not match**: create a project in Google Cloud Console → enable "YouTube Data API
v3" in the API library → create an **API key** credential (not OAuth, which is
only needed for owner-scoped calls) → restrict the key to that one API.

**What to send back:** the key, into `.env`, never the repo.

---

# ⚠ Reddit has a 2026 gate I could not confirm, and the reason is itself the finding

Independent write-ups of the 2026 signup say new API access now routes through a
**manual approval form under Reddit's "Responsible Builder Policy"**, so
registering an app no longer grants access by itself.

**I could not confirm this against Reddit's own pages.** `reddit.com` refuses
our fetches, and the search tool refuses the domain outright. **So this rests on
one class of source and should be treated as unconfirmed** — the recorded
failure here is reading one source, concluding, and stating it confidently.

**It does not currently block anything.** We do not use Reddit's API: Arctic
Shift is a permitted research archive and has supplied the whole corpus. This
matters only if someone wants live Reddit, and then the first step is him
opening the page and telling us what it says — **which is cheaper and more
reliable than any amount of searching from here.**

---

# What I still cannot answer

- **Whether Bluesky's 403 is fixable.** It is the only platform that permits us
  by its own rules and still refuses us in practice. Unresolved, and worth one
  more attempt because it is the cheapest possible win.
- **Whether `the-odds-api`'s free tier is large enough to be useful.** Not
  measured, because it needs the key first.
