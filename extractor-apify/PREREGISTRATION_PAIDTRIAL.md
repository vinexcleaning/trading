# PREREGISTRATION_PAIDTRIAL.md

**Written 2026-08-18, before a single record was pulled from any vendor.** No
token existed on this machine when this was written, so nothing had been seen.

---

## The question

**Are X, TikTok or Instagram worth paying for, measured exactly the way Reddit,
Mastodon and Bluesky were measured?**

Not "do they have posts about Kalshi" — they will. The question is whether what
comes back carries **claims with numbers behind them**, or whether all three are
what the three free platforms turned out to be: a name, a link, and no argument.

## The hypothesis, stated so it can fail

**H-PT1.** All three paid platforms behave like Mastodon and Bluesky, not like
Reddit: high on-topic passage, near-zero items carrying a real denominator.

**H-PT2.** If any one of them beats the others it is **X**, because it is the
only one of the three where written argument is the native format. TikTok and
Instagram are video and image platforms whose text is a caption.

**What would make me drop the whole idea:** if the three platforms together
produce **fewer than 5 items carrying a real countable denominator**, the answer
is that paying for social data does not buy substance, and no follow-up spend is
justified at any price.

**What would make me recommend paying:** **one item of the shape the bar
describes** — a stranger's study with denominators on its claims, of the kind 13
Reddit threads produced. One is enough, because one was enough on Reddit.

## The unit of observation

**One post**, with its caption/body text. This matches how Mastodon and Bluesky
were scored and it is the only unit all three vendors return comparably.

⚠ **Reddit's published numbers are on a different unit** (post + comment
thread). That confound is measured, not guessed: re-scoring Reddit post-only
moves the Reddit/Mastodon gap from 41x to 34x, so the unit is worth about one
part in six. **Reddit is quoted on both units wherever it appears in the
report.**

## The sample, fixed now

**Search terms — the same narrow venue set used for Bluesky**, so all four
platforms are answering one question:

`kalshi` · `polymarket` · `prediction market` · `prediction markets` ·
`event contract` · `predictit`

**Volume, and it is a hard cap:**

| platform | records | why this split |
|---|---|---|
| **X** | **3,500** | H-PT2 says this is the only real candidate, so it gets the most |
| **TikTok** | **1,000** | enough to detect a rate above ~1 in 100 |
| **Instagram** | **500** | the least likely to carry text; smallest bet |
| **total** | **5,000** | exactly the free monthly allowance |

**Date range:** whatever the discovery returns, recorded after collection, never
chosen. Reported alongside the counts.

## The money rule, which is not negotiable

- **The free allowance is 5,000 records a month. The client refuses to request
  more than 5,000 in total** and refuses any single request that would take the
  running total past it.
- **A preflight runs first and spends nothing**: it lists the account's
  scrapers, prints which one it picked for each platform and why, prints the
  exact request it would send, and stops.
- **If anything is ambiguous — two scrapers match, a dataset name is not what
  was expected, the account reports a balance — it stops and asks.** It never
  guesses and then spends.
- **No payment method is entered under any circumstances**, and if the account
  turns out to have one on file that is reported before anything is triggered.

## The controls

**Control 1 — the shuffled placebo**, as before. Same documents, words shuffled
inside each one. Every rubric component is a phrase pattern; a score that
survives shuffling was never reading phrases. **On Reddit this is already known
to leave about half the recommend-grade verdicts standing**, so the number to
watch is whether the paid platforms are better or worse than that.

**Control 2 — read, do not trust the pattern.** The rubric's `S3` component
("states a sample size") is **already measured at 37% false positives on
Reddit** — it fires on phrases like *"30 days"*. So for every platform:

1. report the raw `S3` count, and
2. **read every single item it fired on**, plus every item raised by the wider
   pattern built for the shapes `S3` is blind to (single digits, written
   numbers, win-loss records, "N out of M"), and
3. **report the read count as the headline, not the pattern count.**

On Bluesky that turned 3 into 0. It is the only number in this work that has
survived contact with reading.

## What gets reported either way

- Records returned, records that cleared the gate, records reaching
  recommend-grade, **and the read-verified count of items carrying a real
  denominator** — per platform, never pooled.
- **Cost per item that survived reading.** That is the whole point of the
  exercise and it is the number that decides whether anything gets bought. Free
  platforms have a cost of zero and so cannot be beaten on it — so the
  comparison is stated as *"what did the money buy that free did not"*.
- The best single item on each platform, quoted, with its link.
- **A list of what was NOT tested** (`CLAUDE.md` §9c Step 7).

## What this cannot answer

- **It cannot tell a vendor's failure from a platform's emptiness.** If X comes
  back with 200 records instead of 3,500, that is a fact about Bright Data's
  scraper, not about X. Delivery counts are reported separately from content
  counts for exactly this reason.
- **One vendor is not the market.** Apify's actors would return a different
  sample of the same platforms. A null here is a null for *this route*.
- **6 search terms, one language, one month of allowance.** A specialist
  community under a term not searched will not be found.
