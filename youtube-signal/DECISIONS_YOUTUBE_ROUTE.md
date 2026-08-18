# The transcript route was stopped, and what a permitted one costs

**2026-08-14. A user decision, in his words:** *"stop pulling from the address
YouTube's own rules disallow. Keep the 1,135 transcripts already collected and
keep the 484 findings that rest on them, but do not collect more that way. If
there is a route that is allowed, price it and tell me what it costs."*

---

## What was stopped

Both collection paths reached YouTube through endpoints its own `robots.txt`
disallows — `youtube-transcript-api` hits `/api/timedtext`, and `yt-dlp`
resolves the player through `/youtubei/`. **This programme killed four other
platforms on exactly that test**, so continuing here was the single
inconsistency in the whole access policy.

**Stopped in three places, because one was not enough:**

| where | what it does |
|---|---|
| `src/transcripts.py` | `fetch()` raises `CollectionStopped`; both underlying paths raise individually |
| `src/retrieval.py` | `transcript()` raises before doing anything |
| `tests/test_no_disallowed_route.py` | **6 tests**, fails the build if the route returns |

**The test earned its place on its first run.** It found that `retrieval.py`
called `fetch_via_api` **directly**, bypassing the wrapper entirely — and worse,
its `except Exception` would have caught `CollectionStopped` and filed it as
just another fetch error, so a stopped collector would have looked like a
blocked one and carried on. **A guard on the front door only would have done
nothing.**

## What was NOT retracted

**The 1,135 transcripts on disk stay, and so do the 484 claims and 36 methods
drawn from them.** He was explicit about that split, and it is the right one:
nothing about how those were *read* is in question — only how the next one would
be *obtained*.

---

## The permitted routes, priced

**Verified against Google's own documentation on 2026-08-14**, not from memory.

### 1. The official Data API key — free, worth having, and it does not solve this

| | |
|---|---|
| cost | **free. No billing account, no card.** |
| allowance | **10,000 units/day**, plus 100 `search.list` calls |
| `videos.list` | **1 unit**, and it takes **50 video ids per call** |
| `captions.list` | 50 units — tells you a caption track *exists* |
| `captions.download` | 200 units — **owner-only, unusable for us** |
| more quota | a compliance audit, not money |

**What it buys us, in our own numbers:** metadata for **all 11,277 known video
ids** costs **226 calls at 1 unit each — 226 of the 10,000 daily units.** A
complete metadata refresh of the entire corpus is **2% of one day's free
allowance.**

**What it does not buy: a single word of transcript.** `captions.download`
works only on videos the authenticated account owns; third-party download was
withdrawn by YouTube. **There is no price at which this route returns a
stranger's captions.**

### 2. Creator-granted access — free, and not realistic

A channel owner can grant caption access to a specific account. Free, fully
permitted, and it would need **1,135 separate creators to agree**. Listed for
completeness, not proposed.

### 3. His own saved videos — free, and already the accepted shape

He exports videos he has saved and hands them over. **His data, breaks nothing.**
This is the same route already accepted for TikTok and it needs no new
permission from anyone.

### 4. Paid transcript vendors — the only thing that would actually replace it

Roughly **$0.05–$0.30 a video** at typical list prices, so the existing 1,135
would have been **$57–$340**. **Not recommended, and not because of the money:**
these vendors obtain captions the same way we just stopped doing, and buying the
output does not change where it came from. **It moves the problem to an invoice.**

---

## The bottom line for him

**Nothing needs buying.** The free key is worth setting up — it costs nothing,
needs no card, and covers our entire metadata need in 2% of one day — **but it
buys metadata and search, not words.**

**Transcripts have no free permitted route.** The corpus of 1,135 is now a fixed
asset rather than a growing one. Given that reading was already the bottleneck —
**16 threads read of 7,411 that passed the gate** — a corpus that stops growing
is close to no loss at all.
