# HANDOFF.md — extractor-apify

<!-- COORDINATOR-STATE
doing: scoring a free Bluesky corpus and pricing social-data vendors
left: finish the Bluesky score, then the free trial on X/TikTok/Instagram once an account exists
needs: yes - sign up for a free Bright Data account (no card) so the X/TikTok/Instagram trial can run at zero cost instead of $31-41 on Apify
-->

**Owner: the `extractors` chat.** Created 2026-08-14 from
`coordinator/mailbox/extractors/001`.

---

## Where this got to

**Job 1 — Bluesky. Done, and the answer is better than the instruction
assumed.** Bluesky is not closed and does not need a login. `api.bsky.app`
answers a logged-out request; `public.api.bsky.app` — the host
`social-signal/PLATFORMS.md` tested — refuses everyone. No account was created
because none is needed.

**Job 3 — the vendor question. Done.** `reports/VENDORS.md`. Apify is a real
vendor and it is the wrong place to start: **Bright Data gives 5,000 records a
month free with no card**, and Apify's cheapest X scraper refuses free accounts
outright.

**Job 2 — the paid trial. Blocked on one signup, and it is now a FREE signup.**
See below.

## The one thing needed from a human

**Sign up for a free Bright Data account.** No payment method, no spend, hard
stop at the free allowance. Then the whole three-platform trial runs at **$0**
instead of the **$31–41** Apify would really have cost.

Exact steps are in `reports/VENDORS.md` and repeated in the session report.

**Do NOT create an Apify paid plan for this.** The $5.05 trial in the mailbox
cannot be run for $5.05 — the X actor gates free accounts to 50 items a month
and blocks API access entirely.

## What is in this folder

| file | what it is |
|---|---|
| `src/probe_bluesky.py` | 11 Bluesky routes, logged out. 6 answer |
| `src/ua_test.py` | 7 clients × 2 hosts × 2 tries. Not User-Agent filtering |
| `src/bluesky_fetch.py` | the collector. Walks time windows, because the cursor 403s |
| `src/unit_control.py` | re-scores the sibling corpus so platforms compare on one unit |
| `src/score_corpus.py` | gate + rubric + the shuffled placebo |
| `tests/test_no_secrets.py` | credential guard. Scans every file, not just `.py` |
| `PREREGISTRATION_BLUESKY.md` | written before any post was scored |
| `reports/VENDORS.md` | what each vendor sells, what it costs, what was not tested |
| `reports/BLUESKY.md` | the platform correction and the corpus result |
| `data/bluesky.db` | the corpus. Gitignored — it is collected data |

## Two findings that are not about Bluesky and matter more

**1. The sibling rubric half-survives a placebo.** Take 4,000 Reddit threads,
shuffle the words inside each one so no phrase survives, and the rubric still
calls 5.6 in 100 of them recommend-grade against 11.4 in 100 for the real text.
**About half of what it calls good it is calling good on vocabulary alone.**
That applies to every number this rubric has produced in this repo. Reported,
not tuned — `DECISIONS.md` D006.

**2. The published Reddit-vs-Mastodon gap is mostly real, and I expected it not
to be.** Reddit was scored on posts-plus-comments and Mastodon on posts alone,
so the comparison was confounded. Removing the confound moves the gap from 41×
to 34×. **One part in six was the artifact; five parts in six is the platform.**
`DECISIONS.md` D005.

## Next, in order

1. Score the finished Bluesky corpus (`src/score_corpus.py`) — how many items
   carry a claim with a number attached, which is the bar the mail set.
2. On a Bright Data account: the same query on X, TikTok and Instagram, same
   rubric, same three counts. 5,000 records, $0.
3. Only then decide whether anything is worth paying for.

## Rules this folder is under

- **The token lives outside the repo**, at `C:\Users\vinig\keys\apify.txt`,
  read at runtime, never copied here. `tests/test_no_secrets.py` fails the
  build otherwise. That file does not currently exist and nothing here needs it.
- **`py -3`.** No venv, standard library only.
- **Google Maps is out of scope** — it is `Vinex-OS` work.
