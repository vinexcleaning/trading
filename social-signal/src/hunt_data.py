"""Find free data sources named in the corpus that this repo does not already have.

**Priority 3 of the change-of-emphasis instruction, and arguably the highest
value of the four:** *"A data source we do not have. He explicitly said the
extractors should find data, not just commentary. A free feed nobody here knows
about is worth more than most strategies."*

This is the one place the corpus has an unfair advantage. A strategy someone
posts is one person's opinion; **a URL someone posts either serves data or it
does not, and that is checkable for free.** So this pass ignores every claim in
the corpus and extracts only the hosts, endpoints and archive names, then
subtracts everything the repo already uses.

**Nothing here is fetched.** The output is a candidate list with counts; the
fetching is a separate deliberate step, because a host named in a Reddit comment
is exactly the kind of link that should not be followed automatically.

    python src/hunt_data.py
"""
from __future__ import annotations

import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

HOST = re.compile(r"https?://([a-z0-9][a-z0-9.\-]{2,60}\.[a-z]{2,12})", re.I)

# Hosts this repo already pulls from, plus the social platforms themselves and
# the general web furniture. Anything left after this is a genuine candidate.
KNOWN = {
    # already in the repo's pipelines
    "api.elections.kalshi.com", "trading-api.kalshi.com", "kalshi.com",
    "demo-api.kalshi.co", "gamma-api.polymarket.com", "clob.polymarket.com",
    "polymarket.com", "strapi-matic.poly.market",
    "site.api.espn.com", "espn.com", "www.espn.com", "sports.core.api.espn.com",
    "statsapi.mlb.com", "baseballsavant.mlb.com", "api.github.com",
    "github.com", "raw.githubusercontent.com", "youtube.com", "www.youtube.com",
    "youtu.be", "arctic-shift.photon-reddit.com", "r2kalshi.pmxt.dev",
    "pmxt.dev", "reddit.com", "www.reddit.com", "old.reddit.com",
    # platforms and web furniture, not data sources
    "twitter.com", "x.com", "tiktok.com", "www.tiktok.com", "instagram.com",
    "www.instagram.com", "facebook.com", "www.facebook.com", "discord.gg",
    "discord.com", "imgur.com", "i.imgur.com", "i.redd.it", "v.redd.it",
    "preview.redd.it", "docs.google.com", "drive.google.com", "google.com",
    "www.google.com", "en.wikipedia.org", "wikipedia.org", "medium.com",
    "substack.com", "linkedin.com", "www.linkedin.com", "t.me",
    "stackoverflow.com", "news.ycombinator.com", "archive.org", "web.archive.org",
    "pypi.org", "npmjs.com", "readthedocs.io", "colab.research.google.com",
    "streamable.com", "gfycat.com", "twitch.tv", "patreon.com", "gumroad.com",
}
# A host is only interesting if it sits near a word that means "data".
NEAR_DATA = re.compile(
    r"\b(data|dataset|api|feed|archive|dump|historical|csv|parquet|json|"
    r"tick|odds|scores?|stats|prices?|endpoint|free|open)\b", re.I)
# News and blog hosts. They pass NEAR_DATA constantly because articles talk
# about data, and not one of them serves any.
NEWSY = re.compile(
    r"(wired|guardian|nytimes|cnbc|theverge|404media|heise|hackernoon|"
    r"hackaday|lobste\.rs|ppc\.land|europesays|rbfirehose|habr|"
    r"radwebhosting|jobsfordevelopers|rawchili|bocvip|bloomberg|reuters|"
    r"techcrunch|arstechnica|forbes|businessinsider|cnn|bbc|wsj|ft\.com|"
    r"substack|patreon|medium|dev\.to|infoq|zdnet|engadget|gizmodo)", re.I)
# Marketing hosts that mention data but sell a product.
PAYWALL = re.compile(r"\b(pricing|per month|/mo\b|subscri|paid plan|"
                     r"free trial|starting at \$)\b", re.I)


def main():
    con = db.connect()
    rows = list(con.execute(
        "SELECT post_id AS id, title||' '||COALESCE(selftext,'') AS body, "
        "subreddit AS src FROM rd_posts"))
    rows += list(con.execute(
        "SELECT comment_id AS id, body, post_id AS src FROM rd_comments"))

    hits: Counter = Counter()
    where: defaultdict = defaultdict(set)
    paywalled: Counter = Counter()
    for r in rows:
        body = r["body"] or ""
        if not body:
            continue
        for m in HOST.finditer(body):
            host = m.group(1).lower().rstrip(".")
            if host in KNOWN or host.endswith(".redd.it") or NEWSY.search(host):
                continue
            # only count it if the sentence around it is about data
            lo, hi = max(0, m.start() - 220), min(len(body), m.end() + 220)
            window = body[lo:hi]
            if not NEAR_DATA.search(window):
                continue
            hits[host] += 1
            where[host].add(str(r["src"]))
            if PAYWALL.search(window):
                paywalled[host] += 1

    # **Rank by DISTINCT THREADS, not mentions.** Mentions are dominated by
    # single spam megathreads — one thread posted `sportsbook.link` 1,441 times,
    # which is one recommendation, not 1,441. A host named by many separate
    # threads is the only shape that means anything here.
    ranked = sorted(((h, n) for h, n in hits.items() if len(where[h]) >= 3),
                    key=lambda t: (-len(where[t[0]]), -t[1]))
    out = os.path.join(db.REPORTS, "HUNT_DATA_SOURCES.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# Data sources named in the corpus that this repo does not use\n\n")
        fh.write("Extracted from every post and comment, keeping only hosts "
                 "that appear beside a word meaning *data*, and subtracting "
                 f"the {len(KNOWN)} hosts the repo already pulls from.\n\n")
        fh.write("**Nothing below has been fetched.** A host named in a Reddit "
                 "comment is exactly the kind of link that should not be "
                 "followed automatically; fetching is a separate deliberate "
                 "step.\n\n")
        fh.write("| host | mentions | distinct threads | smells paid |\n")
        fh.write("|---|---|---|---|\n")
        for h, n in ranked[:60]:
            fh.write(f"| `{h}` | {n} | {len(where[h])} | "
                     f"{'yes' if paywalled[h] else '—'} |\n")
    print(f"{len(rows)} texts scanned, {len(hits)} unknown data-adjacent hosts, "
          f"{len(ranked)} seen twice or more\n")
    for h, n in ranked[:40]:
        flag = " (smells paid)" if paywalled[h] else ""
        print(f"  {n:>4} x  {h}{flag}   [{len(where[h])} threads]")
    print(f"\n  wrote {out}")
    db.log(con, "hunt_data", f"unknown_hosts={len(hits)} repeated={len(ranked)}")
    con.close()


if __name__ == "__main__":
    main()
