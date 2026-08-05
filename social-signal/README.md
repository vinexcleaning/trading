# social-signal

Extract signal from social platforms — Reddit, Discord, X, TikTok, Instagram —
and, more importantly, **join it to what the sibling projects already know**.

Single-platform signal is weak. A tool praised in a YouTube tutorial and called
a scam in three Reddit threads is a finding no single source produces. So the
primary deliverable here is not a corpus, it is a **cross-platform tool
reputation table** that joins `youtube-signal`, `signal-github` and Reddit.

Nothing is rewritten that a sibling already built. The credibility rubric is
ported from `youtube-signal/src/read_video.py`; the persistence, shrinkage and
edge-decay methods are `polymarket-tennis-copy/scripts/`; the free-transport
discipline is `signal-github/src/gh.py`.

## Run order

**How an item gets graded, in plain English, and what the score is not worth:**
[`GRADING.md`](GRADING.md).

**Which platforms can be extracted at all, and why the rest cannot:**
[`PLATFORMS.md`](PLATFORMS.md). Two extractors work — **Reddit** (via the
research archive) and **Mastodon**. TikTok, X, Instagram, Facebook and Bluesky
each return nothing usable, for five different and separately measured reasons.

```bash
python src/robots_policy.py     # P0  which platforms permit an agent of THIS kind
python src/probe_platforms.py   # P0  which return text a rubric can grade
python src/mastodon_fetch.py    # T2b the second working extractor
python src/join_corpora.py      # T1  YouTube + GitHub, and scan 3k whole-repo sources
python src/reddit_fetch.py      # T2a collect from the archive (NOT reddit.com — see reddit.py)
python src/reddit_discover.py   # T2b the join backwards: tools only Reddit knows
python src/join_corpora.py      # T1  again, so the newly discovered entities get GitHub evidence
python src/verify_live.py       # T1b fetch every URL; nothing is trusted on paper
python src/reddit_stance.py     # T2c what a room of critics says about each tool
python src/reddit_score.py      # T2d the ported rubric over threads; the read queue
python src/discord_measure.py   # T3  the paid server's calls
python src/feasibility.py       # T4  X / TikTok / Instagram, honest kill reports
python src/join_corpora.py --decide-only    # recompute verdicts over everything
python src/unified_table.py     # T5  the deliverable, plus the fourth bucket
```

`join_corpora.py` appears twice on purpose. The first pass builds entities from
the YouTube corpora; `reddit_discover.py` then adds entities Reddit knows and
neither sibling does; the second pass gives those new entities their GitHub
evidence and re-runs the source-archive scan over them. Every step is
idempotent, so re-running the whole list is safe and cheap.

Every script is stdlib-only. No API key exists for any platform here and none is
needed.

## What is gitignored, and why

This repo is **public**. `data/`, `reports/`, `cache/` and any knowledge file
stay local because they carry judgments about named real people — Reddit
accounts, Discord members, YouTube creators. `discord-trades-export/` is
gitignored at the repo root for the same reason. Aggregates may be committed;
names, handles and message text may not, and `discord_measure.py` enforces that
with per-run salted pseudonyms whose salt is never stored.

## The rules this project runs under

- **Free sources only.** Anything that would cost money goes in `PAID_OPTIONS.md`
  rather than being bought.
- **Verify by fetching, not by finding a link.** Two prior sessions in this repo
  listed sources that turned out to be 404 or 403. `verify_live.py` exists for
  exactly that.
- **A "cannot be done within the terms" finding is a real result.** X is not
  scraped here, and the report says so with the evidence.
- **`NO_FOOTPRINT` is never `POSITIVE`.** Absence of complaints about a small
  tool is absence of evidence, not a clean bill of health. Inherited from
  `youtube-signal/src/tool_reputation.py` and kept as a separate stored value so
  the two can never be merged by accident.
