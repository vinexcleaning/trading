"""Read a Reddit thread in full from the local social corpus — post body plus
every stored comment, ordered by score.

Reading is the step that has repeatedly found what scoring could not (5 defects
from 4 repos; 5 defects from 5 posts). This is the tool for doing it.

Usage:
    read_thread.py find <regex-on-title>       list matching post ids
    read_thread.py <post_id> [<post_id> ...]   dump the threads
"""
from __future__ import annotations

import re
import sqlite3
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

SOCIAL = Path(r"C:\Users\vinig\trading\social-signal\data\social.db")


def ro():
    return sqlite3.connect(f"file:{SOCIAL.as_posix()}?mode=ro", uri=True)


def when(ts):
    if not ts:
        return "?"
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")


def dump(con, pid: str) -> None:
    r = con.execute(
        "select post_id, subreddit, title, selftext, score, upvote_ratio, "
        "num_comments, permalink, created_utc from rd_posts where post_id=?",
        (pid,)).fetchone()
    if not r:
        print(f"!! no post {pid}")
        return
    print("=" * 78)
    print(f"r/{r[1]}  {when(r[8])}  score={r[4]} ratio={r[5]} comments={r[6]}")
    print(f"TITLE: {r[2]}")
    print(f"URL:   https://reddit.com{r[7]}")
    print("-" * 78)
    body = (r[3] or "").strip()
    for para in body.split("\n"):
        print(textwrap.fill(para, 96) if para.strip() else "")
    cs = con.execute(
        "select author, body, score, depth, created_utc from rd_comments "
        "where post_id=? order by score desc", (pid,)).fetchall()
    if cs:
        print("-" * 78)
        print(f"COMMENTS STORED: {len(cs)}")
        for a, b, sc, d, ts in cs:
            print(f"\n  [{sc:>4}] depth={d} {when(ts)}")
            for para in (b or "").strip().split("\n"):
                if para.strip():
                    print(textwrap.fill(para, 92, initial_indent="    ",
                                        subsequent_indent="    "))
    print()


def main() -> None:
    con = ro()
    if sys.argv[1] == "find":
        rx = sys.argv[2]
        con.create_function("RX", 2,
                            lambda p, s: 1 if s and re.search(p, s, re.I) else 0)
        for r in con.execute(
                "select post_id, subreddit, score, num_comments, "
                "(select count(*) from rd_comments c where c.post_id=p.post_id), "
                "title, created_utc from rd_posts p where RX(?, title) "
                "order by score desc limit 60", (rx,)):
            print(f"{r[0]:10} r/{r[1]:<18} s={r[2]:>4} c={r[3]:>4} "
                  f"stored={r[4]:>3} {when(r[6])}  {r[5][:88]}")
    else:
        for pid in sys.argv[1:]:
            dump(con, pid)
    con.close()


if __name__ == "__main__":
    main()
