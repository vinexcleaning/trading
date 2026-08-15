# DECISIONS.md — extractor-apify

Judgment calls taken without asking, and why. `CLAUDE.md` §2: take the
conservative option, write it down, keep going.

---

## D001 — Bluesky is not closed, and `PLATFORMS.md` is corrected rather than rewritten

**2026-08-14.** `social-signal/PLATFORMS.md` records Bluesky as **closed**, on
the strength of `public.api.bsky.app/xrpc/app.bsky.feed.searchPosts` returning
403. That measurement is correct and reproduces today.

**The conclusion drawn from it is not.** `src/probe_bluesky.py` asked eleven
routes the same question and **`api.bsky.app` returns 200 to the identical
logged-out request.** Six routes answer with no account and no token.

The correction is marked **inline where the old claim sits**, and the old line
is left in place — `CLAUDE.md` §6, "deleting a wrong number is how someone
re-derives it".

## D002 — the mail's premise that Bluesky "only needs a login" is wrong, and no account was created

The mailbox instruction says Bluesky is *"free, needs a login"* and offers to
have the user create an account. **It needs no login at all.** `src/ua_test.py`
puts seven different clients against both hosts twice each: `api.bsky.app`
answers a browser string, an honest research string, `curl`, and an **empty
User-Agent** alike, all 200.

So no account was created and no click-by-click was written. Asking the user to
sign up for something that does not need signing up for spends the one thing
`CLAUDE.md` §9c says is scarce — his attention.

## D003 — the 403 is transient, and that is measured, not assumed

A collection run died on 403 at its first call, and a run of the identical
request a minute later returned 200 three times in a row. A second run died on
a bare TCP timeout. **`api.bsky.app` drops requests intermittently.**

The client now retries 403 and connection errors with backoff, and a term that
fails no longer takes the other nine with it. **This is not talking a refusal
round**: `ua_test.py` establishes that an honest client is served, so the retry
is recovering from a blip and not from a policy.

**It is also the most likely explanation of the original wrong entry.** One 403,
taken at face value, closed a platform in this repo's own documentation for ten
days.

## D004 — the search cursor does not work, so the collector walks time instead

`searchPosts` returns 100 posts **and a cursor**. Feeding that cursor back
returns **403** — immediately, and again after waiting 20 seconds and 60
seconds — while the same request without a cursor returns 200 every time.

`since`/`until` **do** work. So the collector walks backwards in time in
windows, halving a window whenever it comes back full (a full window means
posts fell off the bottom of it).

**Recorded because the naive reading is "Bluesky caps you at 100 posts".** That
is what the first run looked like, and it is wrong.

## D005 — the unit control was run before any platform was compared, and it mostly cleared the published numbers

`PLATFORMS.md` publishes Reddit at 6.4 recommend-grade items per 100 that clear
the gate, against Mastodon at 0.18, and reads a 35-fold difference off it as a
property of the platforms.

The two rows are not the same object: `social.db` holds 12,846 comments and
**every one belongs to a Reddit post**. Reddit was scored on post-plus-comments,
Mastodon on post text alone.

`src/unit_control.py` re-scores Reddit on post text only. **The gap goes from 41
to 34.** So about 1 part in 6 of it was the unit of observation and 5 parts in 6
is real. **The published conclusion stands, slightly smaller.** Recorded because
the hypothesis was that the gap was mostly an artifact, and it was not.

## D006 — the placebo fires, and it is reported rather than tuned away

The same 4,000 Reddit threads with the words shuffled inside each document still
clear the gate at 14.7 per 100 against 16.5 real, and still reach recommend
grade at 5.6 per 100 against 11.4 real.

**So roughly half of what this rubric calls recommend-grade survives destroying
the word order completely.** Some of that is legitimate — several components are
deliberately single-word — but it means a recommend verdict is about a 2-to-1
signal over vocabulary alone, not the clean read the rate implies.

**Nothing was adjusted.** Changing a rubric after seeing what it does to a
corpus is how a measurement becomes an opinion. It is reported as a property of
the instrument, and it applies to every number this rubric has produced in this
repo, not only to Bluesky's.

## D007 — no money was spent, and the mail's $5.05 trial cannot be run as written

The mail budgets 5,000 X posts at $0.40/1,000 inside Apify's $5 free credit.
**`apidojo/tweet-scraper` refuses free-plan users the API entirely** — free
accounts get demo mode, 5 runs of 10 items, 50 posts a month. Two independent
sources say so, including the actor's own store page.

So the X arm of the trial needs an Apify paid plan first — **$29–39 a month
before the $2.00 of posts.** That is a spend, and it was not asked for.

**Nothing was bought. No token was read. `C:\Users\vinig\keys\apify.txt` does
not exist on this machine** — checked, not assumed.

## D008 — the credential guard scans every file, not only Python

`livedesk/tests/test_paper_only.py` walks `*.py`. The incident this folder is
guarding against is **a token pasted into a chat window**, and the thing in a
repo that most resembles a chat is a Markdown file. `tests/test_no_secrets.py`
scans everything except binaries.

It also **never prints the matched value** — only the shape, the offset and the
length. A guard that echoes the secret into a test log has leaked it itself.

## D009 — Google Maps noted and stopped

Largest actor on Apify by users, and it is local business data. That is
`Vinex-OS` work, not this repo (`CLAUDE.md` §7). Not investigated further.
