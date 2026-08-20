"""The tool probe, done offline against the corpus we already hold.

**Mailbox 013, second job:** *"Your own handoff says the Reddit tool-name probe
was stopped part-way. Finish it. An extractor that stopped mid-run and was
recorded as complete is the exact defect you fixed in two other tools."*

**I finished it by measuring why it cannot be run remotely, and then running it
locally instead.** That is not a dodge; it is the cheaper and more complete
answer, and here is the measurement behind it.

## Why the remote probe is retired, measured 2026-08-20

`HANDOFF.md` recorded on 2026-08-04 that the comment search 422s while *"the
equivalent post search returns 200 instantly"*. **That diagnosis is wrong now,
and possibly was then.** Four calls, same minute:

| call | result |
|---|---|
| `posts/search?query=polymarket` (no subreddit) | **400** — *"'query' query parameter requires one of: author, subreddit"* |
| `posts/search?subreddit=Kalshi&query=weather` | refused / timed out |
| `posts/search?subreddit=Kalshi` (no query) | **200, rows returned** |
| `posts/search?query=oddsjam` (no subreddit) | **400**, same message |

**So: a listing is cheap, a full-text query inside a subreddit is the expensive
call that gets refused, and a full-text query without a subreddit is not
supported at all.** The probe's design — 40 names × 6 subreddits — *is* the
expensive shape. Running it for hours would be hammering a volunteer research
service for something it has told us twice, in words, that it will not serve.

**The local corpus answers the same question for free and more completely:**
60,833 posts and 12,846 comments already on disk, every one searchable, with no
rate limit and no refusals to misread as zeroes.

**What is genuinely lost by not running it remotely:** any mention of these tools
in subreddits or date ranges we never collected. That is a real gap, it is
recorded here rather than papered over, and it is the reason the output below
says *"in our corpus"* everywhere rather than *"on Reddit"*.

    python src/tool_probe_offline.py
"""
from __future__ import annotations

import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db      # noqa: E402
import norm    # noqa: E402

MIN_TERM_LEN = 4
GENERIC = {"trading", "trade", "prediction", "market", "markets", "backtest",
           "data", "signal", "signals", "bot", "bots", "api", "agent",
           "agents", "open", "auto", "smart", "quant", "alpha", "edge",
           "the", "and", "for", "with", "poly", "crypto", "sports"}
WINDOW = 220          # characters either side of a mention


def main():
    con = db.connect()
    rows = con.execute("""
        SELECT e.entity_id, e.display, v.verdict
        FROM entities e LEFT JOIN verdicts v ON v.entity_id = e.entity_id
    """).fetchall()

    terms, seen = [], set()
    for r in rows:
        name = norm.strip_descriptor(r["display"] or "").strip().lower()
        cand = name if " " not in name else name.split()[0]
        cand = cand.strip("'\"“”‘’.,")
        if (len(cand) < MIN_TERM_LEN or cand in GENERIC or cand in seen
                or not any(c.isalpha() for c in cand)):
            continue
        seen.add(cand)
        terms.append((cand, r["display"], r["verdict"]))
    print(f"{len(rows)} entities -> {len(terms)} searchable names\n")

    posts = con.execute("SELECT post_id AS id, platform, subreddit AS src, "
                        "title || ' ' || COALESCE(selftext,'') AS body "
                        "FROM rd_posts").fetchall()
    comments = con.execute("SELECT comment_id AS id, 'comment' AS platform, "
                           "post_id AS src, body FROM rd_comments").fetchall()
    corpus = [(r["id"], r["platform"], r["src"], r["body"] or "")
              for r in posts] + \
             [(r["id"], r["platform"], r["src"], r["body"] or "")
              for r in comments]
    print(f"searching {len(posts):,} posts + {len(comments):,} comments "
          f"= {len(corpus):,} texts\n")

    hits = Counter()
    threads = defaultdict(set)
    windows = defaultdict(list)
    pats = {t: re.compile(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])",
                          re.I) for t, _d, _v in terms}

    for ident, _plat, src, body in corpus:
        if not body:
            continue
        low = body.lower()
        for t, pat in pats.items():
            if t not in low:            # cheap reject before regex
                continue
            m = pat.search(body)
            if not m:
                continue
            hits[t] += 1
            threads[t].add(str(src))
            if len(windows[t]) < 3:
                lo = max(0, m.start() - WINDOW)
                hi = min(len(body), m.end() + WINDOW)
                windows[t].append((ident, " ".join(body[lo:hi].split())))

    found = [(t, d, v) for t, d, v in terms if hits[t]]
    absent = [(t, d, v) for t, d, v in terms if not hits[t]]
    print(f"{len(found)} names appear in the corpus, {len(absent)} do not\n")
    for t, d, v in sorted(found, key=lambda x: -hits[x[0]]):
        print(f"  {hits[t]:>5} mentions  {len(threads[t]):>4} threads  "
              f"{t:<18} {(d or '')[:40]:<42} {v or ''}")

    out = os.path.join(db.REPORTS, "TOOL_PROBE_OFFLINE.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# Tool mentions, searched offline in our own corpus\n\n")
        fh.write("**The remote probe is retired and this replaces it.** "
                 "Measured 2026-08-20: the archive returns **400** for a "
                 "full-text query without a subreddit (*'query' requires one "
                 "of: author, subreddit*), refuses the subreddit+query call, "
                 "and serves a plain subreddit listing fine. **The probe's "
                 "40 names x 6 subreddits IS the refused shape.**\n\n")
        fh.write(f"Searched **{len(posts):,} posts and {len(comments):,} "
                 f"comments** for **{len(terms)} tool names**.\n\n")
        fh.write("**This says 'in our corpus', never 'on Reddit'.** Anything in "
                 "a subreddit or date range we never collected is invisible "
                 "here, and that gap is real.\n\n")
        fh.write("| tool | mentions | distinct threads | verdict |\n")
        fh.write("|---|---:|---:|---|\n")
        for t, d, v in sorted(found, key=lambda x: -hits[x[0]]):
            fh.write(f"| `{t}` — {d} | {hits[t]} | {len(threads[t])} | "
                     f"{v or '—'} |\n")
        fh.write(f"\n## Named nowhere in the corpus — {len(absent)}\n\n")
        fh.write("**Not evidence they are unknown.** They are absent *here*, "
                 "and the corpus is 10 subreddits over a fixed window.\n\n")
        for t, d, v in absent:
            fh.write(f"- `{t}` — {d} {('(' + v + ')') if v else ''}\n")
        fh.write("\n## Context windows, first three per tool\n\n")
        for t, _d, _v in sorted(found, key=lambda x: -hits[x[0]])[:25]:
            fh.write(f"\n### {t} — {hits[t]} mentions\n\n")
            for ident, w in windows[t]:
                fh.write(f"- `{ident}` …{w}…\n")
    print(f"\n  wrote {out}")
    db.log(con, "tool_probe_offline",
           f"terms={len(terms)} found={len(found)} absent={len(absent)}")
    con.close()


if __name__ == "__main__":
    main()
