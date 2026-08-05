"""What do the corpora ALREADY know about passive quoting and adverse selection?

Asked before reading any new video, per youtube-signal's own cost model:
retrieval and ranking are free, reading is the only expensive step, and
transcripts accumulate quadratically in context.

The four questions H10 needs answered:
  Q1  how do people decide whether a resting order would have filled?
      (queue position, trade-through vs touch, partial fills)
  Q2  what FILL RATES do real passive quoters report on thin books?
  Q3  how big is adverse selection as a fraction of gross maker income?
  Q4  did any maker strategy on a binary/event contract survive out of sample?

Searches both youtube corpora (claims + score_evidence, which carries the
verbatim quotes) and the social corpus. Prints claim text with video id and
n-check verdict so a marketer's assertion and a measured result stay
distinguishable.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

YT = {"kalshi_edge": r"C:\Users\vinig\trading\youtube-signal\data\signal_kalshi_edge.db",
      "broad": r"C:\Users\vinig\trading\youtube-signal\data\signal.db",
      "laptop": r"C:\Users\vinig\trading\youtube-signal\_from_laptop\signal.db"}
SOCIAL = r"C:\Users\vinig\trading\social-signal\data\social.db"
REP = Path(__file__).resolve().parent.parent / "reports"

QUERIES = {
    "Q1_fill_model": r"queue|resting|limit order|passive|maker.{0,20}fill|"
                     r"fill.{0,20}(model|rate|assumption)|trade.?through|"
                     r"partial fill|top of book|front of the (queue|line)",
    "Q2_fill_rate": r"fill rate|filled \d+%|\d+% of (my |our )?(orders|quotes)|"
                    r"never (get )?fill|didn'?t fill|got filled",
    "Q3_adverse": r"adverse selection|toxic flow|picked off|stale quote|"
                  r"informed (trader|flow)|only.{0,30}when.{0,20}wrong|"
                  r"against you|winner'?s curse",
    "Q4_maker_survival": r"market mak(ing|er).{0,80}(decay|stopped|out.?of.?sample|"
                         r"lost|unprofitable|worked)|"
                         r"(decay|out.?of.?sample).{0,80}market mak",
}


def ro(p):
    return sqlite3.connect(f"file:{Path(p).as_posix()}?mode=ro", uri=True)


def main():
    REP.mkdir(parents=True, exist_ok=True)
    out = {}
    for qname, rx in QUERIES.items():
        print("\n" + "=" * 78)
        print(f"{qname}")
        print("=" * 78)
        hits = []
        for corpus, path in YT.items():
            if not Path(path).exists():
                continue
            con = ro(path)
            con.create_function("RX", 2, lambda p, s:
                                1 if s and re.search(p, s, re.I) else 0)
            try:
                rows = con.execute(
                    "select c.video_id, coalesce(v.title,''), c.claim_text, "
                    "c.claim_type, c.stated_n, c.stated_win_rate, "
                    "coalesce(c.n_check_verdict,''), coalesce(v.view_count,0) "
                    "from claims c left join videos v on v.video_id=c.video_id "
                    "where RX(?, c.claim_text)", (rx,)).fetchall()
            except sqlite3.Error:
                rows = []
            for r in rows:
                hits.append({"corpus": corpus, "video": r[0], "title": r[1],
                             "claim": r[2], "type": r[3], "n": r[4],
                             "wr": r[5], "ncheck": r[6], "views": r[7]})
            # score_evidence carries the verbatim <15-word quotes
            try:
                ev = con.execute(
                    "select video_id, axis, component, weight, quote "
                    "from score_evidence where RX(?, quote)", (rx,)).fetchall()
            except sqlite3.Error:
                ev = []
            for e in ev:
                hits.append({"corpus": corpus + ":evidence", "video": e[0],
                             "title": f"{e[1]}{e[2]} w={e[3]}", "claim": e[4],
                             "type": "quote", "n": None, "wr": None,
                             "ncheck": "", "views": 0})
            con.close()
        # dedupe on claim text
        seen, uniq = set(), []
        for h in hits:
            k = (h["claim"] or "")[:120]
            if k in seen:
                continue
            seen.add(k)
            uniq.append(h)
        print(f"  {len(uniq)} distinct claims/quotes in the YouTube corpora")
        for h in uniq[:14]:
            nc = f" [{h['ncheck']}]" if h["ncheck"] else ""
            n = f" n={h['n']}" if h["n"] else ""
            print(f"\n  · {h['corpus']:18} {h['video']}  {h['views']:>7} views{n}{nc}")
            print(f"    {(h['claim'] or '')[:400]}")
        out[qname] = uniq

        # social corpus
        sc = ro(SOCIAL)
        sc.create_function("RX", 2, lambda p, s:
                           1 if s and re.search(p, s, re.I) else 0)
        pm = r"kalshi|polymarket|prediction market|event contract"
        posts = sc.execute(
            "select post_id, subreddit, score, title from rd_posts "
            "where RX(?, title||' '||coalesce(selftext,'')) and "
            "RX(?, title||' '||coalesce(selftext,'')) order by score desc limit 8",
            (rx, pm)).fetchall()
        coms = sc.execute(
            "select comment_id, post_id, score, substr(body,1,300) "
            "from rd_comments where RX(?, body) and RX(?, body) "
            "order by score desc limit 6", (rx, pm)).fetchall()
        sc.close()
        if posts or coms:
            print(f"\n  -- social corpus (prediction-market only) --")
            for p in posts:
                print(f"    [{p[2]:>4}] {p[0]:9} r/{p[1]:<18} {p[3][:78]}")
            for c in coms:
                print(f"    comment [{c[2]:>3}] on {c[1]}: {c[3][:200]}")
        out[qname + "_social"] = {"posts": [list(p) for p in posts],
                                  "comments": [list(c) for c in coms]}

    (REP / "maker_knowledge.json").write_text(
        json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("\n\nwrote reports/maker_knowledge.json")


if __name__ == "__main__":
    main()
