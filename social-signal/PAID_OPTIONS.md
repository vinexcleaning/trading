# PAID_OPTIONS.md — what would cost money, and whether it is worth it

Nothing here has been bought. This project runs on free sources only; this file
exists so that the decision not to spend is a recorded decision rather than an
omission. Every price is the list price seen at the date given and is a `spec`
claim, so it **expires in 3 months** under this repo's own rule.

Ordered by whether the spend would change an answer.

---

## 1. Reddit official API — free, but needs a human once

**Cost: $0.** Reddit's free tier is 100 queries/minute per OAuth client for
non-commercial use. It is listed here because it is **not free of a human
step**: it needs a Reddit account and a registered "script" app, and creating
accounts is outside what this session may do.

**Would it change an answer?** Somewhat. The Arctic Shift archive already
supplies posts and comments and its `robots.txt` permits the crawl, so the
corpus exists. What the official API adds is *current* scores and *live*
threads, plus the ability to read a specific thread on demand rather than only
what the archive has ingested.

**What to do, if you want it (about five minutes):**

1. reddit.com/prefs/apps → "create another app" → type **script**.
2. Redirect URI can be `http://localhost:8080`.
3. Put the client id and secret in `social-signal/.env` as
   `REDDIT_CLIENT_ID=` and `REDDIT_CLIENT_SECRET=` — that path is already
   gitignored by the root rule `*.env`.
4. `src/reddit.py` reads them if present and keeps using the archive if not.

**Do not** point a collector at `reddit.com/*.json` with or without a token
until robots.txt changes: measured 2026-08-04 it is `User-agent: *` /
`Disallow: /`.

---

## 2. X / Twitter API — the only permitted route, and it is not cheap

**Cost, seen 2026-08-04 (`api.x.com` returns 401 without a key):** X's own tiers
are Free (post-only, no search), Basic (~$200/month) and Pro (~$5,000/month).
Only paid tiers return search.

**Would it change an answer? Probably not, and this is the honest reason:**
X's format has the same defect the duration test in `reports/T4_feasibility.md`
measures on short-form video. A post carries a claim and not a denominator, and
the rubric's strongest signal — showing what did not work — needs room. Buying
Basic would buy a stream of results-without-denominators, which the H6
component exists to discount to zero.

**Verdict: do not buy.** If X ever matters it will be as a pointer to a thread
elsewhere, and the pointer is usually reachable from the elsewhere.

---

## 3. TikTok Research API — free, but application-gated and academic

**Cost: $0**, and unavailable: the programme is for accredited academic
researchers at non-profit institutions. `open.tiktokapis.com/v2/research/...`
404s without approval.

**Would it change an answer? No.** The documented keyless oEmbed endpoint does
return 200 and returns a title, an author name and a thumbnail — no transcript,
no comments, no description. Even fully approved, the payload cannot carry a
cost side, a sample size or a technical objection.

---

## 4. Instagram / Meta Graph API — free tier, app-gated

**Cost: $0** for oEmbed, but `graph.facebook.com/instagram_oembed` returns 400
without a Facebook app token, and getting one requires a Meta developer account
and app review for the `oembed_read` permission.

**Verdict: do not pursue.** Same substance argument as TikTok, and a heavier
setup.

---

## 5. Discord — re-export with media

**Cost: $0 in money, and it requires membership in the server.**
`reports/T3_discord.md` records that all 85 attachment URLs in the existing
export carry a signed CDN expiry that has already passed, so the prices behind
the calls are unrecoverable from what is on disk. DiscordChatExporter's
`--media` flag downloads the images at export time.

**Would it change an answer? No.** The measurement is bounded by 34 folded
observations against a ~481 requirement. Re-exporting buys a better-measured
underpowered result. Only a **forward** record, logged with prices from today
against a pre-declared cost bar, changes anything.

---

## 6. OCR for the Discord screenshots

Free options exist (Tesseract locally). Not pursued for the same reason as #5:
the sample size, not the legibility, is the binding constraint.

---

## Summary

| option | cost | changes an answer? |
|---|---|---|
| Reddit official API | $0 + one human step | marginally — live scores and on-demand threads |
| X Basic | ~$200/mo | no — buys claims without denominators |
| X Pro | ~$5,000/mo | no |
| TikTok Research API | $0, academic only | no — payload carries no substance |
| Instagram Graph oEmbed | $0 + Meta app review | no |
| Discord re-export + OCR | $0 + server access | no — underpowered either way |

**Nothing on this list is worth buying.** The one item worth doing is #1, and it
is free.
