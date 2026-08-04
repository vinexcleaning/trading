"""What is actually IN the social corpus — subreddit census and how much of it
is prediction-market rather than general algo-trading.

Written because the first prior-art search returned mostly SPY/options posts:
before quoting anything from this corpus, know its denominator.
"""
import re
import sqlite3
from pathlib import Path

SOCIAL = Path(r"C:\Users\vinig\trading\social-signal\data\social.db")
con = sqlite3.connect(f"file:{SOCIAL.as_posix()}?mode=ro", uri=True)
con.create_function("RX", 2, lambda p, s: 1 if s and re.search(p, s, re.I) else 0)

PM = r"kalshi|polymarket|prediction market|event contract"

print("== posts by subreddit (top 25), and the prediction-market share")
rows = con.execute(
    "select subreddit, count(*), "
    " sum(RX(?, title||' '||coalesce(selftext,''))) "
    "from rd_posts group by subreddit order by count(*) desc limit 25",
    (PM,)).fetchall()
tot = pm_tot = 0
for sub, n, pm in rows:
    pm = pm or 0
    tot += n
    pm_tot += pm
    print(f"  {sub:26} {n:>6}  pm={pm:>5} ({100*pm/n:>5.1f}%)")
allp = con.execute("select count(*), sum(RX(?, title||' '||coalesce(selftext,'')))"
                   " from rd_posts", (PM,)).fetchone()
print(f"  ALL POSTS {allp[0]}  prediction-market {allp[1]} "
      f"({100*allp[1]/allp[0]:.1f}%)")

allc = con.execute("select count(*), sum(RX(?, body)) from rd_comments",
                   (PM,)).fetchone()
print(f"  ALL COMMENTS {allc[0]}  prediction-market {allc[1]} "
      f"({100*allc[1]/allc[0]:.1f}%)")

print("\n== prediction-market posts by subreddit")
for sub, n in con.execute(
        "select subreddit, count(*) from rd_posts "
        "where RX(?, title||' '||coalesce(selftext,'')) "
        "group by subreddit order by count(*) desc limit 20", (PM,)):
    print(f"  {sub:26} {n:>6}")

print("\n== date range")
for label, tbl, col in (("posts", "rd_posts", "created_utc"),
                        ("comments", "rd_comments", "created_utc")):
    lo, hi = con.execute(f"select min({col}), max({col}) from {tbl}").fetchone()
    import datetime as dt
    f = lambda x: dt.datetime.utcfromtimestamp(x).date() if x else None
    print(f"  {label}: {f(lo)} -> {f(hi)}")
con.close()
