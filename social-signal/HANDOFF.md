# HANDOFF — social-signal

**Session of 2026-08-04**, desktop `C:\Users\vinig`. Working directory
`C:\Users\vinig\trading\social-signal`. Ran unattended start to finish.
Cost: **$0.00**. No API key for any platform exists or was needed.

Two sibling sessions were **running concurrently in this same working tree**
throughout. Everything below reads their databases and never writes to them, and
every commit here stages explicit paths.

---

## 0. Read this first — three premises in the brief were wrong, and one of them
## was the highest-priority platform

| the brief said | measured 2026-08-04 |
|---|---|
| Reddit: "free JSON API, no key: add `.json` to any URL. Rate limit ~60/min unauthenticated" | `reddit.com/robots.txt`, `old.reddit.com` and `oauth.reddit.com` all return **`User-agent: *` / `Disallow: /`**. `/r/<sub>/hot.json` returns **403** to a bot UA *and* a browser UA. |
| "Pushshift-style archives for history" | `api.pushshift.io` returns **403 `{"detail":"Not authenticated"}`** — moderators only. |
| Discord: "176 messages and **174 owner trade calls**" | 174 owner messages, yes. **47 carry a directional call verb, and folding to one observation per (date, player) gives 34.** The headline overstates the real sample **5.1×**. |

None of that was worked around. The route this project uses instead is
`arctic-shift.photon-reddit.com` — the public Reddit research archive that
replaced Pushshift for non-moderators. Its `robots.txt` is `Disallow:` (empty,
everything permitted), it publishes a documented JSON API, and it returns
`X-RateLimit-Reset` headers, which `src/reddit.py` obeys.

### The uncomfortable half, stated rather than buried

These probes send a **browser** User-Agent, because `signal-github` lost a
session to reading an intermittent 429 as a block. With that header:

- `reddit.com/r/algotrading/.rss` → **HTTP 200, 54,474 bytes** of live content
- `x.com/kalshi` → **HTTP 200, 200,795 bytes**

**The constraint on this project is not technical and the report does not
pretend it is.** The content is one GET away. It is not taken, because the
site's own machine-readable statement of who may crawl it says nobody may, and
a User-Agent string is not consent.

---

## 1. T1 — the cross-platform join. The headline.

`src/join_corpora.py` · report `reports/T1_cross_platform.md` (gitignored)

Four sources, none of which had ever been joined to another:

| source | size |
|---|---|
| `youtube-signal/data/signal.db` | 87 tools, 750 videos |
| `youtube-signal/data/signal_kalshi_edge.db` | 25 tools (**grew from 10 to 25 during this session** — a sibling was reading) |
| `signal-github/data/github.db` | 4,017 repos, 2,540+ scored |
| `signal-github/cache/*.arch.json` | **~2.8 GB of whole-repo source, 3,117 archives** |

The fourth is what makes this more than a name lookup. Every scored repo's
complete source text is already on disk, so *"does anyone actually build with
the thing this video is selling?"* is answerable by counting. One pass over
3,117 archives takes **42 seconds** and tests every needle at once.

### The single sharpest number

> **The needle `clob-client` appears in 1,009 of 3,117 whole-repo source
> archives — 32% of the corpus — and `Polymarket/clob-client` was archived by
> Polymarket itself.**

(That needle also matches `py-clob-client`, which is the point: both V1 clients
are archived. `signal-github` measured the same thing from the classifier side
and got v1:v2 = 578:121. Two instruments, one conclusion, and this one is a
direct count over source text rather than a heuristic.)

### Join discipline

Match on an exact key or a URL, **never on a free-text name search** — both
siblings recorded that name resolution returns a different project at rank 0,
confidently. A compact key hitting more than three repos is refused rather than
resolved. Name-matched rows are marked ⚠ in the report so a reader can see the
provenance of every claim.

### Verdicts, and the distinction that makes them mean anything

`ADVOCACY` (someone tells you to use it) is kept separate from `CORROBORATION`
(a repo imports it, its own artifact answers when fetched). A `CONTRADICTION`
needs advocacy **and** evidence against. A stale repo somebody mentioned in
passing is a stale repo, not a contradiction.

---

## 2. T1b — every URL fetched, because two prior sessions listed dead links

`src/verify_live.py` · report `reports/T1b_live_verification.md`

| stance | n |
|---|---|
| **NO_URL_RECORDED** | **66** |
| LIVE | 24 |
| ALIVE (repo / account / package) | 5 |
| API_ROOT_404 | 3 |
| BLOCKED | 2 |
| UNKNOWN | 2 |
| ARCHIVED | 1 |
| GONE | 1 |

Three things worth carrying forward.

**`thebetterers.com` does not resolve.** Promoted with a *disclosed* referral
link by a video scoring **S=10**, and the domain is gone. High substance and a
dead product are independent, which is exactly what the S/H separation exists
to express.

**`API_ROOT_404` is its own stance and not a death.** `api.exchange.coinbase.com/`
has no document at `/` and never did. Recording that as GONE would have been a
fact about REST conventions.

**`api.binance.com` returns HTTP 451 — unavailable for legal reasons in this
region.** Not a rate limit and not a bad request: the API is geo-blocked from
this machine. `crypto/` treats Binance as a data source in places; anything that
depends on it will fail here for a reason that looks like a network error and
is not one.

**66 of 104 entities carry no URL at all.** That is a gap in `youtube-signal`'s
extraction — it records a URL only when one is spoken or shown — and it is
precisely why the Reddit pass matters: a *name* is searchable even when an
address was never given.

---

## 3. T1c — eight hand-researched verdicts that were never loaded anywhere

`src/import_sibling_findings.py`

`youtube-signal/src/tool_reputation.py` holds eight tool verdicts researched by
hand with their sources. **`signal.db`'s `tools` table has no `reputation`
column**, so that module has never run on this machine and the research existed
only as a Python dict in a file nobody imports.

This is the same failure `LEDGER.md` records as **K015 = W011**: a claim that
travels between projects gets a fresh status each time, and the weakest status
is the one a reader happens to find.

It also carried a correction this project needed: the transcript said **"Creo"**,
the product is **"Kreo"**, and this table was holding it under the wrong name —
so a Reddit search for it would have returned nothing and been recorded as
`NO_FOOTPRINT`.

---

## 4. T3 — the paid Discord server, read for the first time

`src/discord_measure.py` · report `reports/T3_discord.md`

176 messages, 174 from the owner, 29 days, 3 distinct authors.

| | |
|---|---|
| owner messages carrying a **price** | **4 of 174** |
| owner messages carrying a **side and a price** | **0 of 174** |
| messages carrying a directional call verb | 47 |
| distinct (date, player) pairs — **the folded n** | **34** |
| required for a powered test (`polymarket-tennis-copy`) | ~481 |
| **shortfall** | **14.1× short; 34 is 7% of the requirement** |

**The calls are prose, not a structured feed** — "I like <surname>", median
message 40 characters. The prices are in 83 attached screenshots, and **all 85
attachment URLs carry a Discord CDN `ex=` signature that expired on
2026-07-31**. The direction of every call survives in the text; the price does
not.

So the two price-based measurements (edge decay, adverse selection) are dead
outright, and the two outcome-based ones are recoverable only with an external
tennis results feed — which the local `kalshi-tennis` Sackmann mirror cannot
supply, because it ends **2026-06-02** and this export starts 30 June.

**UNDERPOWERED is the finding, and it is decidable without ever seeing a price.**

One thing the rubric could measure anyway: **the seller posts losses.** 6
loss-flavoured messages against 34 win-flavoured, and 22 messages (13%) hedge
the call explicitly. That is H1 territory and it is the opposite of the pure
marketing shape — *and* a 5.7:1 self-reported win ratio is not a track record.
Honest-sounding and unmeasurable are not in tension; this channel is both.

> **Privacy.** `discord-trades-export/` names real private individuals and is
> gitignored at the repo root. `discord_measure.py` replaces every author with
> a per-run salted pseudonym and **does not store the salt**. No handle, user
> id, server name or message text is written to any report.

---

## 5. T4 — X, TikTok, Instagram: three kills, and the short-form expectation TESTED

`src/feasibility.py` · report `reports/T4_feasibility.md`

| platform | verdict | evidence |
|---|---|---|
| **Reddit** | **COLLECT — via the archive, never the site** | robots `Disallow: /`, `.json` 403; the archive permits everything and rate-limits politely |
| **X / Twitter** | **KILL — not possible free and within the rules** | robots `Disallow: /`; API v2 **401** without a paid key; mirrors are the same act with an extra hop |
| **TikTok** | **KILL — retrievable, and empty of what the rubric needs** | the documented keyless oEmbed endpoint **returns 200** — and returns a title, an author and a thumbnail. No transcript, no comments. |
| **Instagram** | **KILL — app-gated** | `graph.facebook.com/instagram_oembed` **400** without a Meta app token |

### The expectation was tested, not assumed — and it held

The brief predicts short-form is mostly marketing. That is answerable for free
on data already on disk: `youtube-signal` gated 1,220 videos and recorded every
duration.

| duration band | n | PASS | rate | 95% Wilson |
|---|---|---|---|---|
| **<1 min (short-form)** | **38** | 12 | **31.6%** | [19.1, 47.5] |
| 1–3 min | 105 | 47 | 44.8% | [35.6, 54.3] |
| 3–10 min | 458 | 264 | 57.6% | [53.1, 62.1] |
| **10–30 min** | **483** | 320 | **66.3%** | [61.9, 70.3] |
| 30+ min | 136 | 59 | 43.4% | [35.3, 51.8] |

Short-form and the 10–30 minute band **do not overlap**.

**And the curve is not monotonic**, which is the part worth keeping: 30+ minutes
falls back to 43.4%. The rule is not "longer is better" — both ends are junk for
different reasons, and only the middle band reliably contains a cost side, a
sample size and a mechanism.

---

## 5b. What reading found — [`FINDINGS_FROM_READING.md`](FINDINGS_FROM_READING.md)

Committed, permalinks only, no usernames. Eight threads read in full. The four
that land on this repo's own threads:

1. **Copy trading: the leak may be exit fidelity, not entry latency.** A
   43-point r/algotrading post from someone who built a Hyperliquid copy bot and
   opens with *"I am not selling anything"*: *"entry latency is a red herring …
   simulating zero lag barely moved the numbers. all the leak was on the exit
   side."* **`wallet-copy-study` and `polymarket-tennis-copy` both model the
   follower's loss as an entry delay** — `delay_seconds`, follower ROI at
   +1s/+10s/+60s, and `follow_through.py`'s whole design. Does not reopen the
   NO-GO; means it may be right for a reason the instrument does not contain.
   Same post carries **e-values (always-valid sequential tests)** for the
   repeated-peeking problem Holm-Bonferroni does not fix — a tool this programme
   does not have, and every recorder here is watched daily. **Worth a GUARDS
   row.**
2. **Kalshi tennis series settle on who ADVANCES**, so a walkover pays out with
   zero play. `kalshi-inplay-bot` and `set1_overshoot` trade
   `KXATPMATCH`/`KXWTAMATCH` and have no model for that settlement path.
3. **`archive.pmxt.dev/Polymarket` → HTTP 200**: a free Polymarket historical
   order-book archive, verified by fetching. `pmxt-dev/pmxt` is 2,055★, alive,
   and was already the 11th most-starred repo in `signal-github`'s corpus with
   nothing joined to it. **STATUS's "recorded order books are not re-pullable at
   any price" is now partly false for that venue.**
4. **The claim that would reframe maker-only quoting, and it stays unverified.**
   r/quant on 5 GB of Kalshi NFL data: passive LPs *"aren't neutralizing
   inventory and capturing spread"* but accumulating directional exposure to
   settlement — underwriting, not market making. The cited SSRN page returns
   **403 behind a Cloudflare interstitial**, and this project does not solve bot
   challenges.

---

## 6. What is wrong, unfinished or untrusted

1. **The Reddit stance pass is a lexicon, not a read.** `reddit_stance.py`
   classifies a 440-character window around each mention by the first pattern
   that fires. It will mistake sarcasm for praise and a quoted accusation for an
   accusation. **Its precision against a hand read is UNKNOWN and no number is
   quoted for it.** `youtube-signal` recorded that both its G3 validation
   samples had informed the lexicon's own design, making its 85.9% an upper
   bound rather than a holdout; this project starts by claiming nothing.
2. **`rubric.py` scores are a mechanical proxy.** Same caveat, stated in the
   report header rather than in a footnote.
3. **The sweep is capped and the cap is stated, not hidden.** Eight of ten
   subreddits hit the 4,000-post cap rather than reaching the 2024-06-01 floor —
   only r/PredictionMarkets was exhausted. The coverage table prints each
   subreddit's oldest post, so truncation is visible rather than implied, and
   the effective window differs per subreddit: about seven months for
   r/algotrading, six weeks for r/sportsbetting. **Any count compared across
   subreddits is comparing different time windows.**
4. **`OpenClaw` matched `daidue/OpenClaw` (0★) by name.** That is very likely a
   different project — OpenClaw is also a well-known game reimplementation.
   Name-matched rows now carry a ⚠ marker, but the row itself has not been
   adjudicated.
5. **The YouTube corpora are a moving snapshot.** A sibling session was reading
   and scoring while this ran; `signal_kalshi_edge.db` went 10 → 19 → 25 tools
   mid-session, and `github.db` grew from 2,540 to 3,117 archives. Every script
   here is idempotent; re-run `join_corpora.py` to refresh.
6. **Reddit usernames are personal data.** `reports/` is gitignored. Nothing in
   this file names a Reddit account.

---

## 7. The next three things, in order

1. **Read the top of `reports/T2_reddit_scores.md`.** The proxy exists to rank
   what a human or a model should read next, and nothing has been read against
   it yet. Reading is what produced every defect in both sibling projects that
   scoring could not see.
2. **Register a free Reddit script app** (`PAID_OPTIONS.md` §1, five minutes,
   $0). It adds live scores and on-demand threads. Do **not** point a collector
   at `reddit.com/*.json` while robots.txt says `Disallow: /`.
3. **Decide the Discord question and close it.** The recommendation is: do not
   re-export. Steps 1–3 in `reports/T3_discord.md` buy a better-measured
   underpowered result. Only a forward record with prices, against a
   pre-declared cost bar, changes anything.
