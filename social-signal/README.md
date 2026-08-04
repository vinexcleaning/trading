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

```bash
python src/join_corpora.py     # T1  merge YouTube + GitHub, scan whole-repo source
python src/verify_live.py      # T1b fetch every recorded URL; nothing is trusted on paper
python src/reddit_fetch.py     # T2  free JSON API, paced, no key
python src/reddit_score.py     # T2  port of the S/B/H rubric, applied to threads
python src/discord_measure.py  # T3  the paid server's calls
python src/feasibility.py      # T4  X / TikTok / Instagram, honest kill reports
python src/join_corpora.py --decide-only   # recompute verdicts over everything
```

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
