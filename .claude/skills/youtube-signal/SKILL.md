---
name: youtube-signal
description: Find the genuinely informative YouTube videos on any topic, read their transcripts, and extract the substance — tools, sites, step-by-step methods, specific claims — into a knowledge file, so the user never has to watch them. Use when the user wants the best videos, channels, tutorials or strategies on a subject; wants YouTube researched or absorbed for a project; or asks for educational picks worth their own time. Works for any niche (trading, AP Stats, Roblox, SAT). Triggers on "/youtube-signal", "find me the best videos on X", "what does YouTube say about X", "research X on YouTube".
---

# youtube-signal

Turn YouTube into a knowledge file. Retrieval and ranking are FREE (no API key of
any kind). Only the final reading step needs a model, and that can be done by you
in-session at no cost.

**Project root:** `C:\Users\gianf\trading\youtube-signal`
**Python:** `C:\Users\gianf\trading\youtube-signal\.venv\Scripts\python.exe`
(`python` on PATH is a Microsoft Store stub and will fail.)

## What this is, and what it is not

It is an **absorber**, not a recommender. The ranking exists only to decide what to
read. The deliverable is `KNOWLEDGE.md`: rows, not prose.

It is **not** a summariser. A summary flattens "this person has a public repo with
3,693 stars" and "trust me bro" into the same paragraph. Every extracted line keeps
its video ID, timestamp and expiry so those stay distinguishable months later.

It is **not** view-count ranked. YouTube already surfaces popular videos. This
targets the 400-view video with the actual specifics. In testing, an 8-view video
scored 10/10 and a 10-view video produced 10 claims and needed zero watching.

## Two kinds of output — keep them separate

| | who it is for | criteria |
|---|---|---|
| **INFORMATIVE** | the model absorbs it; user never watches | substance only (S ≥ 4) |
| **EDUCATIONAL** | worth the USER's own minutes | S ≥ 5, H ≥ 0, ≤ 20 min, well taught |

Ask which the user wants. "Find me videos to learn X" means EDUCATIONAL. "Learn
everything about X for this project" means INFORMATIVE.

## Pipeline

```
1. queries.py     define search terms for the topic     free
2. run_retrieval  search + collect (union of 3 runs)    free, ~3 min
3. run_gates      transcript + age + on-topic + cache   free, ~2.2s/video
4. rank_substance rank all of them by keyword proxy     free, seconds
5. READ the top N in full  <- the only expensive step
6. verify_tools + tool_reputation  do the tools exist?  free
7. build_knowledge  regenerate KNOWLEDGE.md             free
```

### Retrieving for a NEW topic

Edit `src/queries.py`. Add a topic key to `TOPICS` with two families that must stay
separate:

- **F1 — beginner phrasing.** What a newcomer types.
- **F2 — insider vocabulary.** What only a practitioner says.

**This split is the whole engine.** Measured on the trading corpus, F1 and F2
returned near-disjoint sets — Jaccard **0.037**, 16 shared videos out of 446 — and
F2's yield of sub-5,000-view videos beat F1's by **2.25×**. A second batch of
insider terms was 88.5% exclusive again, so corpus size scales with insider term
count. Generate F2 by asking: *what would an expert say that a beginner never
would?* Write the generated list into the report for the user to correct — they
know the domain and you do not.

Then:
```bash
.venv\Scripts\python.exe src\run_retrieval.py
.venv\Scripts\python.exe src\run_gates.py
.venv\Scripts\python.exe src\rank_substance.py
```

### Reading (the only step that costs anything)

```bash
.venv\Scripts\python.exe src\dump_transcripts.py --top 5
.venv\Scripts\python.exe src\dump_transcripts.py <video_id>
```

Read the printed transcript yourself, write
`reports/extractions/<video_id>.json`, then:
```bash
.venv\Scripts\python.exe src\load_extraction.py reports\extractions\<id>.json
.venv\Scripts\python.exe src\build_knowledge.py
```

**Read one video per turn.** Transcripts accumulate in context and the cost is
quadratic — 15 videos read in one session processes ~2.7M tokens against 244k of
actual text. One per turn, write the JSON, move on.

An `ANTHROPIC_API_KEY` in `.env` enables `read_video.py` for unattended batches
(~$0.06/video on Sonnet). It is optional and **has never been run** — validate on
two videos by hand before trusting it.

## Scoring

**S — substance, 0–10.** S1 names the cost side (+3) · S2 separates backtest from
live (+2) · S3 states a sample size (+2) · S4 gives the mechanism, who is on the
other side (+2) · S5 names specific tools rather than gesturing (+1)

**H — honesty, −10 to +11.** H1 shows a failure without selling a fix (+3) ·
H1b failure that sets up the sale (+1) · H2 verifiable artifact that RESOLVES (+3) ·
H3 claim carries n + period + capital (+2) · H4 names own weakness (+1) ·
H5 discloses own products (+2) · H6 claim with no denominator (−4) ·
H7 sells without disclosing mechanism (−2) · H8 urgency language (−1)

**Never average S and H.** A promotional video can carry excellent mechanism. Keep
the tools flagged and absorb the maths.

**Hard rule: every point needs a timestamp and a verbatim quote under 15 words.**
Enforced in `load_extraction.py`, not trusted. No quote, no point.

## The n-check — arithmetic, never judgment

Any stated win rate over n trades goes through a Wilson interval against its own
break-even. Verified behaviour: 55% over 33 trades → `INDISTINGUISHABLE FROM
NOISE`; 51.5% over 1.34 billion trades → `SUPPORTED`. Same-looking claims, opposite
verdicts. Never let a model override this.

## Verifying tools — two separate questions

1. `verify_tools.py` — does the URL resolve? GitHub repos are checked for size and
   last push, so a README-only repo reads as dead.
2. `tool_reputation.py` — does anyone INDEPENDENT vouch for it? Verdicts
   `POSITIVE` / `MIXED` / `NEGATIVE` / `NO_FOOTPRINT` / `ESTABLISHED`.

**`NO_FOOTPRINT` is never `POSITIVE`.** Absence of complaints about a small tool is
absence of evidence. Vendor blogs, affiliate "review" sites and Medium posts by
crypto accounts are the vendor talking — not corroboration.

Do not spend searches asking whether the SEC or DuckDB is a scam. Mark established
institutions `ESTABLISHED` and spend the searches on small commercial tools.

**Auto-captions garble product names.** A bot transcribed as "Creo" was actually
"Kreo". Search name variants before recording `NO_FOOTPRINT`.

## Traps that already cost real work

- **Age gates leak.** A video-level staleness cutoff silently excluded 184 videos,
  10 of which out-scored the entire passing top 30. Recency belongs on the CLAIM:
  mechanisms and maths never expire; procedures 12 months, tool recommendations 4,
  prices/fees/API specs 3, performance results 3.
- **Never resolve a channel by name.** Searching "Nate Tokens" returned a different
  human at rank 0, confidently. Channels enter only via a retrieved video's own
  `channel_id`, or pinned in `channels.json`.
- **Channel expansion by ratio does not work.** A ≥50% on-topic bar pruned nothing
  and admitted Fireship and freeCodeCamp; the strict alternative pruned the single
  most valuable creator in the set. Left at the Phase 1 rule deliberately.
- **`NULL != NULL`.** A `UNIQUE(name, url)` constraint silently allows duplicates
  when the url is null. Use `COALESCE(url, '')`.

## Privacy

`data/`, `reports/` and `KNOWLEDGE.md` are gitignored. They attach honesty
judgments to named real people and the repo is public. Code is committed;
judgments stay local.
