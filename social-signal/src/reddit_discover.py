"""T2d — the join running the other way: tools Reddit knows and the siblings do not.

`join_corpora.py` starts from what a YouTuber said and asks whether GitHub and
Reddit corroborate it. That direction can only ever confirm or contradict a list
someone else wrote. This runs the join backwards: it reads every GitHub URL and
bare domain out of the Reddit corpus, ranks them by how many distinct threads
carry them, and creates entities for the ones neither sibling corpus has ever
heard of.

Why it matters more than it sounds: `youtube-signal`'s corpus is 750 videos of
people **selling**, and `signal-github`'s is 4,000 repos of people **building**.
Neither contains the thing a working practitioner recommends in a comment
because someone asked. That is a different population and it is the one with
the least incentive attached.

The output is deliberately raw. Being posted nine times is not a recommendation
— a vendor posting nine times looks identical — so the count is stored as
evidence and the stance work is left to `reddit_stance.py`, which reads the
windows around each mention.
"""
from __future__ import annotations

import argparse
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import norm  # noqa: E402

RE_GH = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", re.I)
RE_URL = re.compile(r"https?://([a-z0-9][a-z0-9.-]*\.[a-z]{2,12})", re.I)

# Hosts that are infrastructure for the conversation rather than a tool in it.
NOISE_HOSTS = {
    "reddit.com", "www.reddit.com", "old.reddit.com", "i.redd.it", "v.redd.it",
    "preview.redd.it", "imgur.com", "i.imgur.com", "youtube.com",
    "www.youtube.com", "youtu.be", "twitter.com", "x.com", "docs.google.com",
    "drive.google.com", "colab.research.google.com", "en.wikipedia.org",
    "medium.com", "substack.com", "discord.gg", "discord.com", "t.me",
    "github.com", "gist.github.com", "raw.githubusercontent.com",
    "pypi.org", "npmjs.com", "www.npmjs.com", "stackoverflow.com",
    "investopedia.com", "www.investopedia.com", "tradingview.com",
    "www.tradingview.com", "amazon.com", "www.amazon.com", "chatgpt.com",
    "openai.com", "anthropic.com", "claude.ai", "google.com", "www.google.com",
}
ONTOPIC = re.compile(
    r"\b(kalshi|polymarket|prediction market|event contract|order ?book|"
    r"backtest|arbitrage|market maker|clob|sportsbook|algo ?trading)\b", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-threads", type=int, default=2,
                    help="a link posted once is an anecdote; the default asks "
                         "for two distinct threads before it becomes an entity")
    ap.add_argument("--top", type=int, default=60)
    args = ap.parse_args()

    con = db.connect()
    docs = []
    sub_of = {}
    for p in con.execute("SELECT post_id, subreddit, title, selftext FROM rd_posts"):
        docs.append((p["post_id"], f"{p['title']}\n{p['selftext'] or ''}"))
        sub_of[p["post_id"]] = p["subreddit"]
    for c in con.execute("SELECT post_id, body FROM rd_comments"):
        docs.append((c["post_id"], c["body"] or ""))
    print(f"  scanning {len(docs)} documents")

    repo_threads = collections.defaultdict(set)
    host_threads = collections.defaultdict(set)
    for thread_id, text in docs:
        if not text or not ONTOPIC.search(text):
            continue
        for owner, repo in RE_GH.findall(text):
            repo = repo.split("#")[0].split("?")[0].rstrip(".,)")
            if repo.endswith(".git"):
                repo = repo[:-4]
            if not repo or repo.lower() in ("blob", "tree", "issues"):
                continue
            repo_threads[f"{owner}/{repo}"].add(thread_id)
        for host in RE_URL.findall(text):
            h = host.lower().removeprefix("www.")
            if h in NOISE_HOSTS or h.endswith(".redd.it"):
                continue
            host_threads[h].add(thread_id)

    known_repos = {(r["github_repo"] or "").lower()
                   for r in con.execute("SELECT github_repo FROM entities")}
    known_hosts = {norm.domain(r["canonical_url"] or "") or ""
                   for r in con.execute("SELECT canonical_url FROM entities")}

    # Everything above the threshold goes in the REPORT; only the ones no
    # corpus has seen become new entities. Reporting only the new ones made the
    # file shrink on every re-run — the second pass listed 43 hosts where the
    # first listed 102, because the first pass had made them known. A report
    # that is a diff against its own previous run is not a report.
    all_repos = sorted(((k, v) for k, v in repo_threads.items()
                        if len(v) >= args.min_threads),
                       key=lambda kv: -len(kv[1]))
    all_hosts = sorted(((k, v) for k, v in host_threads.items()
                        if len(v) >= args.min_threads),
                       key=lambda kv: -len(kv[1]))
    new_repos = [(k, v) for k, v in all_repos if k.lower() not in known_repos]
    new_hosts = [(k, v) for k, v in all_hosts if k not in known_hosts]

    added = 0
    for full_name, threads in new_repos[:args.top]:
        name = full_name.split("/")[1]
        eid = db.upsert_entity(con, norm.key(name), norm.compact(name), name,
                               kind="repo",
                               url=f"https://github.com/{full_name}",
                               repo=full_name)
        db.add_observation(con, eid, "reddit", "arctic-shift", full_name,
                           "POSTED_ON_REDDIT", strength=float(len(threads)),
                           detail=f"github.com/{full_name} posted in "
                                  f"{len(threads)} distinct on-topic threads. "
                                  "A count is not an endorsement — a vendor "
                                  "posting nine times looks identical.",
                           evidence="")
        added += 1
    for host, threads in new_hosts[:args.top]:
        eid = db.upsert_entity(con, norm.key(host), norm.compact(host), host,
                               kind="site", url=f"https://{host}")
        db.add_observation(con, eid, "reddit", "arctic-shift", host,
                           "POSTED_ON_REDDIT", strength=float(len(threads)),
                           detail=f"{host} linked in {len(threads)} distinct "
                                  "on-topic threads",
                           evidence="")
        added += 1
    con.commit()

    out = os.path.join(db.REPORTS, "T2_reddit_discovered.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# T2 — tools Reddit knows that neither sibling corpus does\n\n")
        fh.write(f"From {len(docs)} posts and comments. A link needs "
                 f"**{args.min_threads} distinct on-topic threads** to become "
                 "an entity; once is an anecdote.\n\n")
        fh.write("**A count is not an endorsement.** A vendor posting its own "
                 "repo nine times produces the same number as nine independent "
                 "recommendations. `reddit_stance.py` reads the windows around "
                 "each mention; this file only says what exists.\n\n")
        newr = {k for k, _ in new_repos}
        newh = {k for k, _ in new_hosts}
        fh.write("## GitHub repos posted in on-topic threads\n\n")
        fh.write("`new` = neither sibling corpus had this repo.\n\n")
        fh.write("| repo | threads | new |\n|---|---|---|\n")
        for full_name, threads in all_repos[:args.top]:
            fh.write(f"| [{full_name}](https://github.com/{full_name}) | "
                     f"{len(threads)} | {'yes' if full_name in newr else ''} |\n")
        fh.write("\n## Domains linked in on-topic threads\n\n")
        fh.write("**Read the `subs` column before the `threads` column.** A host "
                 "in 98 threads that are all one subreddit is that subreddit's "
                 "own sidebar or daily-thread template, not 98 recommendations. "
                 "Spread across subreddits is the signal; raw count is not.\n\n")
        fh.write("| host | threads | subs | where | new |\n|---|---|---|---|---|\n")
        for host, threads in all_hosts[:args.top]:
            subs = collections.Counter(sub_of.get(t, "?") for t in threads)
            flag = " ⚠ single-sub" if len(subs) == 1 and len(threads) >= 10 else ""
            fh.write(f"| `{host}` | {len(threads)} | {len(subs)}{flag} | "
                     + ", ".join(f"r/{s}x{n}" for s, n in subs.most_common(3))
                     + f" | {'yes' if host in newh else ''} |\n")
        fh.write(f"\n## Already known\n\n{len(repo_threads)-len(new_repos)} of "
                 f"{len(repo_threads)} repos and "
                 f"{len(host_threads)-len(new_hosts)} of {len(host_threads)} "
                 "hosts were either already in the entity table or below the "
                 "thread threshold.\n")
    print(f"  {len(new_repos)} new repos, {len(new_hosts)} new hosts, "
          f"{added} entities added")
    print(f"  wrote {out}")
    db.log(con, "reddit_discover",
           f"docs={len(docs)} new_repos={len(new_repos)} "
           f"new_hosts={len(new_hosts)} added={added}")
    con.close()


if __name__ == "__main__":
    main()
