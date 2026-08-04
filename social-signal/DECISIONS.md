# DECISIONS

Method decisions taken without asking, with the reasoning and the measurement
that forced each one. Conservative reading taken wherever ambiguous.

Written retrospectively at the end of the 2026-08-04 session, after `CLAUDE.md`
§2 was re-read — the decisions below were taken and recorded in commit messages
and `HANDOFF.md` at the time, but not in this file, because this file did not
exist. That is itself the first thing to record.

---

## D1 — Reddit is collected from an archive, not from reddit.com
**2026-08-04.** The brief specified `reddit.com/*.json`. Measured:
`reddit.com`, `old.reddit.com` and `oauth.reddit.com` all return
`User-agent: *` / `Disallow: /`, and `.json` returns **403** to a bot UA and a
browser UA alike. `api.pushshift.io` returns 403 "Not authenticated".
`arctic-shift.photon-reddit.com` publishes a documented JSON API, its
`robots.txt` is `Disallow:` (empty, everything permitted), and it returns
`X-RateLimit-Reset` headers.
**Conservative reading:** with a browser User-Agent, `reddit.com/.rss` returns
**200 and 54 KB** — the block is not technical. Not taken anyway, because a
User-Agent string is not consent. A "cannot be done within the rules" result is
a real result.

## D2 — Entities are matched on an exact key or a URL, never a name search
**2026-08-04.** Both sibling projects recorded that free-text name resolution
returns a different project at rank 0, confidently. A compact key hitting more
than **3** repos is refused rather than resolved, and name-matched rows carry ⚠
in the report.
**Risk accepted:** `OpenClaw` still matched `daidue/OpenClaw` (0★), very likely
a different project — OpenClaw is also a game reimplementation. Flagged, not
adjudicated.

## D3 — ADVOCACY is separate from CORROBORATION
**2026-08-04.** The first verdict logic counted any positive stance against any
negative one, which made every ordinary tool with a critical comment a
"contradiction". A `CONTRADICTION` now requires someone **telling you to use it**
plus evidence against. A stale repo somebody mentioned in passing is a stale
repo.

## D4 — A Reddit negative needs ≥3 windows AND ≥10% share before it reaches a verdict
**2026-08-04.** Measured: `arxiv.org` scored `SCAM_ALLEGED` **twice against 309
neutral windows** and came out a CONTRADICTION; `archive.pmxt.dev` scored it
twice on the promotional post's own sentence *"charging devs for raw market data
is basically a scam"* — an accusation aimed at other vendors, counted against
the speaker. CONTRADICTION fell 25 → 10, AGREE_NEGATIVE 24 → 11.
**Chosen once and stated in the report, NOT tuned against the output.** A
threshold picked to produce a nicer table is a threshold that means nothing.
**Conservative reading:** raw counts stay in the table as evidence; the floor
gates the *verdict*, not the record.

## D5 — An accusation naming the entity as the victim is suppressed, not counted
**2026-08-04.** MetaMask came out a CONTRADICTION on three `SCAM_ALLEGED`
windows reading *"steal **from the linked** metamask account"* and *"the
remaining $1k usdt **in my** MetaMask to get stolen"*. The accusation is against
a third-party site; the wallet is the victim.
**Conservative reading:** the test is deliberately narrow — possessive and
source-marking constructions only. It will miss cases and will not invent any,
which is the right way round for something that **suppresses** evidence.
Suppressed windows are recorded as `NAMED_AS_VICTIM` rather than dropped, so the
count stays auditable. `predictionhunt.com` (8 scam windows of 17) survived it.

## D6 — The rubric was NOT patched after its defects were found
**2026-08-04.** Five reads produced five defects, including in the document the
scorer ranks highest. Tuning patterns until they fire correctly on five examples
you happened to read is the overfitting this programme exists to catch, and it
would swap a *known-bad* instrument for an *unknown* one.
**Consequence accepted:** the stance lexicon's precision is **UNKNOWN** and no
number is quoted for it anywhere. No verdict in `TOOL_REPUTATION.md` rests on
the proxy; it ranks what to read next and nothing else.

## D7 — The tool probe's comment leg is off by default
**2026-08-04.** `?subreddit=X&body=Y` returns
`422 {"error":"Timeout. Maybe slow down a bit"}` while the equivalent post
search returns 200 instantly. It is not a malformed request — the same call
without a subreddit returns 400 with a different message. My transport had been
retrying 422 at 5/10/15/20 s, which is how something whose own docstring says
"back off, never hammer" ends up hammering a volunteer research service.
**Decision:** 422 now backs off in minutes; the comment leg needs
`--tool-comment-search` to run at all. It is near-redundant anyway —
`reddit_stance.py` searches the local corpus offline for free.

## D8 — Collection was stopped at 125 of 400 threads on the first comment pass
**2026-08-04.** The archive was degrading and the remaining session budget was
better spent on analysis than on a 2.5-hour pull.
**Superseded the same session:** the user asked for it to be resumed, it ran
400/400 in **401 calls with 0 errors and one 422 in 21.5 minutes**, and the
corpus doubled. **The degradation was mine, not the archive's** — see D7.

## D9 — Discord author identities are salted per run and the salt is discarded
**2026-08-04.** `discord-trades-export/` names real private individuals and this
repo is PUBLIC (`CLAUDE.md` §7). Pseudonyms are generated from a salt created at
import and **never written anywhere**, so they cannot be reversed after the
process exits. No handle, user id, server name or message text reaches any
report.

## D10 — `STATUS.md` is edited at byte level with each substitution asserted unique
**2026-08-04.** Several sections of `STATUS.md` carry mojibake from an earlier
cp1252 round-trip. Decoding and re-encoding the file would either preserve that
or silently "fix" another session's text. Edits are byte-level and every
replacement asserts exactly one occurrence, so a stray match elsewhere aborts
rather than rewriting a sibling's entry.

## D11 — Checked whether an extractor already exists, and it does. The kills stand, but the trade-off is now explicit and it is the user's call.
**2026-08-04**, prompted by the user asking whether a scraper already exists
rather than accepting my own probes. `signal-github`'s corpus was queried first
(free, cached): **8 hits, all market scrapers, zero social-media extractors** —
so new retrieval was needed, run from this folder rather than by editing theirs.

**1. TikTok transcripts, free: NO.** Every "tiktok subtitle/transcription" repo
found *generates* captions for video you are publishing — Whisper-based clip
tools — rather than *extracting* them from an existing post. The real TikTok
scrapers do metadata, video files and comments, and the biggest
(`drawrowfly/tiktok-scraper`, 5,165★) was last pushed **1,173 days ago**. The
only working path is download-then-Whisper-it-yourself.
**Does not reopen the kill:** that kill was on **substance**, measured — a
45-second clip cannot carry a denominator whether or not you transcribe it.

**2. X without the paid API: YES, tools exist and some are alive.**
`d60/twikit` (4,599★, *"Twitter Internal API | Free"*), `zedeus/nitter`
(13,394★, alive), `bocchilorenzo/ntscraper` (258★);
`bisguzar/twitter-scraper` (4,010★) is **archived**.
**Does not reopen the kill either:** that kill was on **terms**, not capability.
These work by calling X's *internal* API without a key, which is the
circumvention route, not an alternative to it. A tool that works does not change
a rule that says do not.

**3. Reddit: independently confirmed, and here is the uncomfortable part.**
`mvanhorn/last30days-skill` — **57,240★, MIT, pushed 2 days ago** — states in
its own README: *"Reddit's public .json API died; the free path came back
stronger. Keyless RSS + shreddit scraping."*

So the largest, most actively maintained tool in this space reaches the same
diagnosis this project did **and solves it by scraping reddit.com anyway** —
the thing declined in D1. It gets live scores and current threads; this project
gets an archive. **Both work. Only one of them is inside the site's stated
rules.**

**Decision: unchanged, and flagged as the user's to overturn.** This project
keeps using the archive. The trade-off is now written down instead of implied:
declining to scrape costs live scores and current threads, and a widely used
alternative exists that pays that cost differently.

> **Also found, and it should have been found on day one:**
> `last30days-skill` covers **Reddit, X, YouTube, TikTok, HN, Polymarket,
> Threads, Bluesky** in one skill, is MIT licensed, and **is already the
> highest-starred repo in `signal-github`'s own corpus** — where nobody had
> looked at it. It is much closer to "the social media extractor" as described
> than anything built here. Its X and TikTok legs need keys or cookies; its
> Reddit leg scrapes.

## D12 — `TRUST_ME_BRO` no longer counts as evidence AGAINST a tool
**2026-08-04**, forced by a sibling session's measurement, not by mine.

`signal-github` first measured the flag as **uncorrelated** with substance
(rho +0.029, p 0.41, n=822) — the number this project built on. At **n=2,717**
they measured it as **weakly POSITIVE and significant**: rho +0.064, p 0.0009,
flagged repos median `s_adj` **+0.19 against −0.20**. Their reading, which is
right: making a results claim at all requires having built something.

**So it never belonged in a set called AGAINST.** It fires on "a results claim
in the README with <10 commits and no artifact" — that is an **honesty** signal,
and the rubric this project ported is explicit that S and H are never averaged:
*discount the results, not the tooling*. A repo that overclaims may still be the
best code available.

`TRUST_ME_BRO` now discounts a tool's **claims** without condemning the tool,
which is exactly what `ABSORB_RESULTS_DISCOUNTED` does on the video side.
**Effect: AGREE_NEGATIVE 11 → 8.** `OpenPoly`, `polymarket-hft-engine`,
`prediction-market-arbitrage-bot`, `lmsr-pricing-engine` and `QuantConnect` were
negative on that flag **alone** and are not any more.
`polymarket-market-maker` stayed negative, correctly — its negative is an
archived v1 CLOB client, independent of the flag.

**Which measurement is trusted and why:** theirs, at n=2,717 over mine at n=822,
because it is the same instrument on 3.3× the sample and the direction is
explicable rather than merely different.

## D13 — The unanswered adopt-or-keep question resolved conservatively
**2026-08-04.** The user was asked to choose between keeping this
rules-compliant collector, switching to `last30days-skill` (57,240★, which
scrapes reddit.com), or installing it for a side-by-side comparison. The answer
was "resume autonomously" rather than a choice.

**Conservative option taken, per `CLAUDE.md` §2:** keep the archive-based
collector. Adopting a tool whose Reddit leg scrapes a site whose `robots.txt`
says `Disallow: /` is a decision with an outside-facing consequence, and it is
not mine to take by default. The comparison remains available and the question
stays open in `HANDOFF.md`.

## D14 — The Kalshi archive is tick-level, not hourly. 37 GB not taken unilaterally.
**2026-08-04.** Retraction first: this project recorded the pmxt archive as
"hourly snapshots" and wrote the Kalshi half off as substituting "for nothing
here". **Wrong.** One file was downloaded and opened rather than judged from its
filename: `kalshi_orderbook_2026-05-17T02.parquet` is **128.7 MB / 20,723,041
rows for one hour**, of which **18.9 M are `orderbook_delta`**, with microsecond
timestamps and full `yes_bids`/`no_bids` ladders across **642,054 tickers** —
including **97 `KXATPMATCH`/`KXWTAMATCH` tickers and 126,704 tennis rows in that
hour alone**. Hourly is the **batching**, not the resolution. It is finer than
this repo's own 0.55 s recorder.

**The decision.** The ~12 days Kalshi's own ~69-day window has already dropped
(≈15–27 May) is ~288 files ≈ **37 GB** pulled from a volunteer-run archive. That
is a real ask of somebody else's bandwidth, and the obvious use case — tennis —
is a **closed thread** (`STATUS.md`: *"Stop. n≈3,970 needed for a 2¢ edge; more
slicing has negative EV"*). Taking 37 GB to feed a thread that is closed is not
a decision to make by default.

**Conservative option taken:** correct the record now, and **do not pull 37 GB
unilaterally**. The efficient version, if it is wanted, is to stream each hour,
filter to the tickers of interest and discard the raw — tennis is 0.6% of rows,
so 37 GB of transfer becomes **~230 MB of disk**.

**This one has a deadline and that is why it is flagged rather than buried:**
the recoverable window shrinks by a day for every day that passes, because
Kalshi's 69-day cut-off moves forward and the archive's Kalshi feed is dead at
11 June.

---

## Open audit items

- **D2's `OpenClaw` row is unadjudicated.** One name match, plausibly the wrong
  project.
- **The stance lexicon has no precision estimate** (D6) and six known defects.
- **538 of 39,629 posts have their comments.** Stance and scoring run mostly on
  post text, which is the weaker half of the platform.
- **The tool probe has never run** in any form (D7).
