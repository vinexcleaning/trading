# HANDOFF — social-signal

**Session of 2026-08-04**, desktop `C:\Users\vinig`, working directory
`C:\Users\vinig\trading\social-signal`. Ran unattended start to finish.
**Cost: $0.00.** No API key for any platform exists or was needed.

Two sibling sessions were running **in this same working tree** throughout.
Everything here reads their databases and never writes to them, and every commit
staged explicit paths.

---

## 0. Read this first — three premises in the brief were wrong, and one of them
## was the top-priority platform

| the brief said | measured 2026-08-04 |
|---|---|
| Reddit: *"free JSON API, no key: add `.json` to any URL. Rate limit ~60/min"* | `reddit.com`, `old.reddit.com` and `oauth.reddit.com` **all** return `User-agent: *` / `Disallow: /`. `/r/<sub>/hot.json` returns **403** to a bot UA and a browser UA alike. |
| *"Pushshift-style archives for history"* | `api.pushshift.io` → **403 `{"detail":"Not authenticated"}`** — moderators only. |
| Discord: *"176 messages and **174 owner trade calls**"* | 174 owner messages, yes. **47 carry a directional call verb; folding to one observation per (date, player) gives 34.** The headline overstates the real sample **5.1×**. |

Nothing was worked around. Collection runs against
**`arctic-shift.photon-reddit.com`**, the public Reddit research archive that
replaced Pushshift for non-moderators: its `robots.txt` is `Disallow:` — empty,
everything permitted — it publishes a documented JSON API, and it returns
`X-RateLimit-Reset` headers, which `src/reddit.py` obeys.

> ### The uncomfortable half, stated rather than buried
> These probes send a **browser** User-Agent, because `signal-github` lost a
> session to reading an intermittent 429 as a block. With that header,
> `reddit.com/r/algotrading/.rss` returns **HTTP 200 and 54,474 bytes** of live
> content and `x.com/kalshi` returns **HTTP 200 and 200,795 bytes**.
>
> **The constraint on this project is not technical and this report does not
> pretend it is.** The content is one GET away. It is not taken, because a
> site's machine-readable statement of who may crawl it says nobody may, and a
> User-Agent string is not consent.

---

## 1. The numbers

| | |
|---|---|
| entities in the reputation table | **231** |
| observations behind them | **924** |
| Reddit corpus | **39,629 posts · 6,077 comments** across 10 subreddits |
| whole-repo source archives scanned | **3,165** (~2.8 GB, one pass, 50 s) |
| URLs fetched and classified | **166** (65 entities carry no URL at all) |
| Discord messages read | 176 |
| threads read in full by a human | **13** |

### Verdicts

| verdict | n | meaning |
|---|---|---|
| **CONTRADICTION** | **10** | someone advocates it, another source shows it dead, broken, flagged or condemned |
| **AGREE_NEGATIVE** | **11** | evidence against, nobody advocating |
| **UNDISCLOSED** | **12** | advocated with an incentive, corroborated by nobody independent |
| SINGLE_SOURCE | 16 | one platform has ever mentioned it |
| AGREE_POSITIVE | 162 | two or more platforms, independently corroborated, nothing against |
| NOT_SOFTWARE | 20 | an exchange, an institution or an idea |

`ADVOCACY` ("use this") is kept separate from `CORROBORATION` (a repo imports
it, its artifact answers when fetched). A stale repo somebody mentioned in
passing is a stale repo, not a contradiction.

### The single sharpest number from the corpus scan

> **The needle `clob-client` appears in 1,009 of 3,165 whole-repo source
> archives — 32% of the corpus — and `Polymarket/clob-client` was archived by
> Polymarket itself.**

It also matches `py-clob-client`, which is the point: both V1 clients are
archived. `signal-github` measured v1:v2 = 578:121 from the classifier side.
Two instruments, one conclusion, and this one is a direct count over source text
rather than a heuristic.

### And the one nobody had looked for

> **`polymarket/agents` — Polymarket's own agents framework, 3,760 stars — is
> ARCHIVED and 636 days cold, while 693 archived repos still reference it.**

It sits in `signal-github`'s corpus as a `PASS` and is one of its top-starred
entries. No computed component in either sibling project asks "is this
archived?", and neither had joined it to anything.

---

## 2. T1 — the join, and what it is made of

`src/join_corpora.py` · `reports/T1_cross_platform.md` (gitignored)

Four sources, none previously joined to another:

| source | size |
|---|---|
| `youtube-signal/data/signal.db` | 87 tools, 750 videos |
| `youtube-signal/data/signal_kalshi_edge.db` | 25 tools — **grew 10 → 19 → 25 during this session**, a sibling was reading |
| `signal-github/data/github.db` | 4,017 repos |
| `signal-github/cache/*.arch.json` | **3,165 whole-repo archives, ~2.8 GB** |

The fourth is what makes this more than a name lookup. Every scored repo's
complete source is already on disk, so *"does anyone actually build with the
thing this video is selling?"* is answerable by counting. One pass tests every
needle at once.

**Join discipline:** match on an exact key or a URL, **never on a free-text name
search** — both siblings recorded that name resolution returns a different
project at rank 0, confidently. A compact key hitting more than three repos is
refused rather than resolved, and name-matched rows carry a ⚠ in the report.

---

## 3. T1b — every URL fetched, because two prior sessions listed dead links

`src/verify_live.py` · `reports/T1b_live_verification.md`

| stance | n |
|---|---|
| LIVE | 116 |
| **NO_URL_RECORDED** | **65** |
| ALIVE (repo / account / package) | 21 |
| BLOCKED | 10 |
| GONE | 4 |
| API_ROOT_404 | 3 |
| THIN | 3 |
| STALE · ARCHIVED · BROKEN · UNKNOWN | 2 each |
| TLS_UNVERIFIED | 1 |

Four things worth carrying forward.

**`thebetterers.com` does not resolve.** Promoted with a *disclosed* referral
link by a video scoring **S=10**. High substance and a dead product are
independent, which is what the S/H separation exists to express.

**`API_ROOT_404` is its own stance and not a death.** `api.exchange.coinbase.com/`
has no document at `/` and never did. Recording that as GONE would have been a
fact about REST conventions.

**`TLS_UNVERIFIED` is its own stance for the same reason.** The first run called
`edition.cnn.com` GONE on *"unable to get local issuer certificate"* — a fact
about this machine's CA bundle. An **expired** certificate is the site's own and
stays a real signal; an untrusted issuer is not.

**`api.binance.com` returns HTTP 451 — unavailable for legal reasons in this
region.** Not a rate limit, not a bad request: geo-blocked from this machine.
`crypto/` treats Binance as a data source in places, and anything depending on
it will fail here for a reason that looks like a network error and is not one.

**65 of 231 entities carry no URL at all.** A gap in `youtube-signal`'s
extraction — it records a URL only when one is spoken or shown — and precisely
why the Reddit pass matters: a *name* is searchable when an address was never
given.

---

## 4. T1c — eight hand-researched verdicts that had never been loaded anywhere

`src/import_sibling_findings.py`

`youtube-signal/src/tool_reputation.py` holds eight tool verdicts researched by
hand, with sources. **`signal.db`'s `tools` table has no `reputation` column**,
so that module has never run on this machine and the research existed only as a
Python dict in a file nobody imports.

Same failure `LEDGER.md` records as **K015 = W011**: a claim that travels between
projects gets a fresh status each time, and the weakest one is what a reader
finds.

It also carried a correction this table needed: the transcript said **"Creo"**,
the product is **"Kreo"**. A Reddit search under the wrong name would have
returned nothing and been recorded as `NO_FOOTPRINT`.

---

## 5. T2 — Reddit

`src/reddit.py` · `reddit_fetch.py` · `reddit_discover.py` · `reddit_stance.py`
· `reddit_score.py`

**39,629 posts and 6,077 comments across 138 threads**, from 10 subreddits.

> ### ⚠ Coverage is dense recently and sparse historically — do not read the
> ### earliest date as coverage
> The **sweep** walks back from today and was capped at 4,000 posts per
> subreddit; **eight of ten hit the cap** rather than reaching the 2024-06-01
> floor. The **venue probes** then added older matching posts with no date
> bound, so the earliest post in r/sportsbook is from **2013** — but nothing
> between the probe hits and the sweep window was collected. **Any count
> compared across subreddits, or across time, is comparing different
> populations.**

### The scoring pass, and why its numbers carry a warning

| bucket | n |
|---|---|
| PASS the gate | 4,362 |
| DROP_G1_THIN (under 200 chars of thread text) | 25,313 |
| DROP_G3_OFF_TOPIC | 9,954 |
| ABSORB | 565 |
| ABSORB_AND_RECOMMEND | 234 |
| ABSORB_RESULTS_DISCOUNTED | 97 |
| BUILD_AND_RECOMMEND | 19 |
| BUILD | 4 |
| SKIP | 3,443 |

A post is scored on its own text **plus its comment thread**, because on Reddit
the substance is frequently not in the post — a "how do I build a Kalshi bot"
question scores nothing and the reply explaining the maker fee is the artifact.
Only 138 threads have comments, so **most PASS posts were scored without the
half of the platform that carries the substance.**

### The stance pass, and the floor under it

`reddit_stance.py` classifies a 440-character window around each mention. **164
of 231 entities have a Reddit footprint; 67 have none** — and `NO_FOOTPRINT` is
stored as a distinct value from any positive, because absence of complaints
about a small tool is absence of evidence.

The first full-corpus run marked **`arxiv.org` a CONTRADICTION** on two
`SCAM_ALLEGED` windows against 309 neutral ones, and **`archive.pmxt.dev`
AGREE_NEGATIVE** on two more — both firing on the promotional post's own
sentence, *"charging devs for raw market data is basically a scam"*, an
accusation aimed at other vendors and counted against the speaker.

So a Reddit negative now reaches a verdict only if it appears in **≥3 windows
AND ≥10% of everything said about that entity**. Chosen once, stated in the
report, **not tuned against the output**. CONTRADICTION fell 25 → 10 and
AGREE_NEGATIVE 24 → 11, and what survives is defensible. The raw counts stay in
the table as evidence either way — the floor gates the verdict, not the record.

### The join run backwards

`reddit_discover.py` reads every GitHub URL and domain out of the corpus and
creates entities for what neither sibling knows. `youtube-signal`'s 750 videos
are people **selling** and `signal-github`'s 4,017 repos are people
**building**; neither population contains the thing a practitioner recommends in
a comment because somebody asked.

It also reports **subreddit spread per host**, which immediately exposed its own
top four "discoveries" — `sportsbook.link`, `dhodds.com`, `oddscrowd.com`,
`pikkit.link` at 98 threads each — as one subreddit's daily-thread template.
Raw count was measuring automod.

---

## 6. T3 — the paid Discord server, read for the first time

`src/discord_measure.py` · `reports/T3_discord.md`

176 messages, 174 from the owner, 29 days, 3 distinct authors.

| | |
|---|---|
| owner messages carrying a **price** | **4 of 174** |
| owner messages carrying a **side and a price** | **0 of 174** |
| messages carrying a directional call verb | 47 |
| **distinct (date, player) pairs — the folded n** | **34** |
| required for a powered test (`polymarket-tennis-copy`) | ~481 |
| **shortfall** | **14.1× short; 34 is 7% of the requirement** |

**The calls are prose, not a structured feed** — "I like *surname*", median
message 40 characters. The prices are in 83 attached screenshots, and **all 85
attachment URLs carry a Discord CDN `ex=` signature that expired 2026-07-31**.
The direction of every call survives in the text; the price does not.

So the two price-based measurements — edge decay, adverse selection — are dead
outright, and the two outcome-based ones are recoverable only with an external
tennis results feed, which the local `kalshi-tennis` Sackmann mirror cannot
supply: it ends **2026-06-02** and this export starts 30 June.

**UNDERPOWERED is the finding, and it is decidable without ever seeing a price.**

The rubric could measure one thing anyway: **the seller posts losses** — 6
loss-flavoured messages against 34 win-flavoured, 22 (13%) hedging the call
explicitly. H1 fires. And a 5.7:1 self-reported ratio is not a track record.
Honest-sounding and unmeasurable are not in tension; this channel is both.

> **Privacy.** `discord-trades-export/` names real private individuals and is
> gitignored at the repo root. `discord_measure.py` replaces every author with a
> per-run salted pseudonym and **does not store the salt**. No handle, user id,
> server name or message text reaches any report.

---

## 7. T4 — three kills, and the short-form expectation TESTED

`src/feasibility.py` · `reports/T4_feasibility.md`

| platform | verdict | evidence |
|---|---|---|
| **Reddit** | **COLLECT — via the archive, never the site** | robots `Disallow: /`, `.json` 403; the archive permits everything and rate-limits politely |
| **X / Twitter** | **KILL — not possible free and within the rules** | robots `Disallow: /`; API v2 **401** without a paid key; mirrors are the same act with an extra hop |
| **TikTok** | **KILL — retrievable, and empty of what the rubric needs** | the documented keyless oEmbed endpoint **returns 200** — and returns a title, an author and a thumbnail. No transcript, no comments. |
| **Instagram** | **KILL — app-gated** | `graph.facebook.com/instagram_oembed` **400** without a Meta app token |

**The expectation was tested, not assumed**, on 1,220 videos `youtube-signal`
had already gated and whose durations it had already recorded:

| duration band | n | PASS | rate | 95% Wilson |
|---|---|---|---|---|
| **<1 min (short-form)** | 38 | 12 | **31.6%** | [19.1, 47.5] |
| 1–3 min | 105 | 47 | 44.8% | [35.6, 54.3] |
| 3–10 min | 458 | 264 | 57.6% | [53.1, 62.1] |
| **10–30 min** | 483 | 320 | **66.3%** | [61.9, 70.3] |
| 30+ min | 136 | 59 | 43.4% | [35.3, 51.8] |

Short-form and the 10–30 minute band **do not overlap**. **And the curve is not
monotonic** — 30+ minutes falls back to 43.4%. The rule is not "longer is
better": both ends are junk for different reasons, and only the middle band
reliably carries a cost side, a sample size and a mechanism.

---

## 8. What reading found — [`FINDINGS_FROM_READING.md`](FINDINGS_FROM_READING.md)

Committed, permalinks only, no usernames. Thirteen threads out of 39,629. The
five that land on this repo's own threads:

**1. Seven months, 4,604 resolved Polymarket 5-minute windows** — and it has 9
points. Every price band loses against price+fee (−1.6 to −6.5pp); momentum
continuation inverts monotonically across 346,094 windows; the Chainlink-Binance
lag is −0.4pp on 5,826 entries, i.e. **zero fillable lag**, and the "+$456
profit" version of that signal was **a measurement artifact** — a structural
0.12% offset larger than the 0.10% entry gate. Two of its results land directly
on work already done here: it independently names **break-even arming as "the
single biggest source of loss"** (the same mechanism as `STATUS.md`'s 28 July
martingale, `rearm_above = stop + 2`), and its adverse-selection section supplies
**the mechanism this repo's ladder-arbitrage null lacked** — rest both legs of a
split and the leg in demand fills while the worthless one hangs.

**2. The cross-platform contradiction in its purest form.** A 400,000-view
YouTube strategy: 100 trades, 56% win rate, +40%. Rebuilt over 16 years and
1,700+ trades: **−23%, 39% win rate, −36% max drawdown** — and *"the exact 100
trades shown in the video do appear in the backtest… a short lucky stretch
inside a much longer downtrend."* The sequel kills the obvious rescue: reversing
every signal raises the win rate to 61% and leaves expectancy at −0.01, because
**"when you reverse a strategy, you aren't reversing the costs."**

**3. Copy trading: the leak may be exit fidelity, not entry latency.**
*"simulating zero lag barely moved the numbers. all the leak was on the exit
side."* **`wallet-copy-study` and `polymarket-tennis-copy` both model the
follower's loss as an entry delay** — `delay_seconds`, follower ROI at
+1s/+10s/+60s, and `follow_through.py`'s entire design. Does not reopen the
NO-GO; means it may be right for a reason the instrument does not contain. Same
post carries **e-values (always-valid sequential tests)** for the repeated-peeking
problem Holm-Bonferroni does not fix. **Worth a GUARDS row.**

**4. Kalshi tennis series settle on who ADVANCES** — a walkover pays out with
zero play. `kalshi-inplay-bot` and `set1_overshoot` trade
`KXATPMATCH`/`KXWTAMATCH` and have no model for that settlement path.

**5. A free order-book archive, enumerated rather than trusted.**
`archive.pmxt.dev`, hourly Parquet, CC BY 4.0. **Polymarket v2: 21 Apr – 4 Aug
2026**, ~105 days at 412–534 MB/hour — so `STATUS.md`'s *"recorded order books
are not re-pullable at any price"* **is false for that venue**. **Kalshi: 15 May
– 11 June 2026 only**, hourly, feed dead. But Kalshi's own ~69-day window reaches
back to about 27 May, so **roughly twelve days of Kalshi books exist there that
Kalshi no longer serves** — and that window shrinks daily.

One claim recorded and deliberately left unverified: an r/quant post citing SSRN
6325658 argues Kalshi's passive LPs are **underwriting, not market making**.
`papers.ssrn.com` returns **403 behind a Cloudflare interstitial** and this
project does not solve bot challenges.

---

## 9. The instrument, audited by reading — five read, five defects

`reports/T2_rubric_audit.md`. Cases picked by **reading the corpus**, not by the
scorer's ranking; a scorer validated on cases it selected is validating its own
taste.

- A **satire post** enumerating every classic beginner error scores **S=7
  ABSORB**, because S1 (+3, "names the cost side") fires on *"I haven't added
  fees or slippage yet"*. **The lexicon cannot tell naming a cost from
  accounting for one**, and that is the top-weighted component.
- A 214-point structural argument citing a multi-year study **scores SKIP** —
  there is no component for citing external evidence.
- A post **warning about** strategy sellers scores **H = −6**, because H6 and H7
  fire on the language it quotes in order to condemn.
- **PyKalshi** — a live 118★ client with `pip install`, a public repo and an
  explicit disclosure — scores **S=1 B=3 SKIP**. `youtube-signal`'s documented
  S1/S2/S3 bug reproducing on Reddit, and the B axis added to fix it still lands
  under its own threshold because B2–B5 look for a walkthrough.
- The **positive control**: the corpus's best document ranks top at S=10 — and
  **H1, show a failure without pivoting to a sale, does not fire on a post that
  is nothing but failures**, while H5 fires on the phrase "my bot" in an author
  who explicitly is not selling one. **Right ranking, two components wrong in
  opposite directions.**

**Nothing was patched.** Tuning patterns until they fire on five examples you
happened to read is the overfitting this programme exists to catch, and it would
swap a known-bad instrument for an unknown one. **No verdict in
`TOOL_REPUTATION.md` rests on the proxy.**

---

## 10. What is wrong, unfinished or untrusted

1. **I killed my own 45-minute collection run.** I ran the join and the live
   verification against `social.db` while the collector was writing to it;
   SQLite's default busy timeout is 5 seconds and the collector died with
   `database is locked`. The 39,629 posts already written survived; the tool
   probe and part of the comment collection did not. Fixed at the root:
   `db.connect()` now takes a 120-second busy timeout and enables WAL, and
   `reddit_fetch.py` gained `--only` and `--skip-sweep` so phases are
   individually runnable.
2. **The tool probe never ran.** ~30 product names × 6 subreddits × 3 fields,
   searching **comments** for each tool — the pass most likely to surface
   specific criticism of specific products. The archive was returning HTTP 422s
   and timeouts and comments were the better use of a degrading service.
   `python src/reddit_fetch.py --only tools` resumes it.
3. **Only 138 threads have comments.** The stance and scoring passes are
   therefore running mostly on post text, which is the weaker half.
   `--only comments --comments-for 400` continues where it stopped.
4. **The stance lexicon's precision is UNKNOWN and no number is quoted for it.**
   Five demonstrated defects (§9) and a stated floor (§5) are what stands in for
   a precision estimate. `youtube-signal` recorded that both its G3 validation
   samples had informed the lexicon's own design, making its 85.9% an upper
   bound rather than a holdout; this project claims nothing.
5. **`OpenClaw` matched `daidue/OpenClaw` (0★) by name** and is very likely a
   different project — OpenClaw is also a well-known game reimplementation.
   Name-matched rows carry ⚠ but the row has not been adjudicated.
6. **The YouTube corpora are a moving snapshot.** A sibling was reading and
   scoring while this ran; `signal_kalshi_edge.db` went 10 → 25 tools and
   `github.db`'s archive count went 2,655 → 3,165 mid-session. Every script here
   is idempotent; re-run `join_corpora.py` to refresh.
7. **Reddit usernames are personal data.** `reports/` is gitignored and nothing
   committed names a Reddit account.

---

## 11. The next five things, in order

1. **Read the top of `reports/T2_reddit_scores.md`.** Every finding in
   `FINDINGS_FROM_READING.md` came from reading; none came from scoring. The
   proxy exists to rank what to read next and it demonstrably ranks the best
   document top.
2. **Pull the Kalshi order books from `archive.pmxt.dev` now.** ~12 days —
   15 to 27 May 2026 — that Kalshi's own API no longer serves, and the window
   shrinks every day. Hourly, not sub-minute; decide whether that resolution is
   worth anything *before* pulling ~50 GB.
3. **Re-run `polymarket_fees_census.py`.** A 4,604-window study states the
   Polymarket 5-minute taker fee as `shares × 0.072 × price × (1−price)` — a
   **quadratic**. `signal-github`'s C2 measured **flat 0.04/0.05/0.07 by
   category** over 2,100 Gamma markets. Both agree makers pay zero; they
   disagree on the functional form, which is exactly what decides whether cheap
   contracts are penalised differently from coin-flips.
4. **Finish the Reddit collection** — `--only tools`, then
   `--only comments --comments-for 400`. Both are pure gain and neither needs a
   decision.
5. **Register a free Reddit script app** (`PAID_OPTIONS.md` §1 — five minutes,
   $0). Adds live scores and on-demand threads. **Do not** point a collector at
   `reddit.com/*.json` while robots.txt says `Disallow: /`.
