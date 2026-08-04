"""STEP 1 — harvest what has already been TRIED, from the three corpora.

Three questions the brief asks, answered by search rather than by re-derivation:

  Q1  which markets do people report trading profitably, with evidence
  Q2  which markets are reported dead, and why
  Q3  which strategies were publicly tested and FAILED

Search is over social-signal's 39,629 Reddit posts + 12,846 comments and both
YouTube claim tables. Output is candidate passages with permalinks; nothing here
is a finding until a human-equivalent read confirms it, which is the next step.

Usage:  prior_art_search.py <mode> [terms...]
        modes: profit | dead | failed | family <name> | grep <regex>
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

SOCIAL = Path(r"C:\Users\vinig\trading\social-signal\data\social.db")
YT_BROAD = Path(r"C:\Users\vinig\trading\youtube-signal\data\signal.db")
YT_KALSHI = Path(r"C:\Users\vinig\trading\youtube-signal\data\signal_kalshi_edge.db")

PATTERNS = {
    # Deliberately asymmetric: a profit claim needs a number or a period to be
    # worth reading; "dead" and "failed" are cheap to state and cheap to check.
    "profit": r"(profitab|made \$|up \$|\+\d+%|roi of|my edge|consistently win|"
              r"been printing|pays for itself|net positive|after fees I)",
    "dead": r"(no volume|zero volume|nobody trades|illiquid|dead market|"
            r"no liquidity|can'?t get filled|never fills|no counterpart|"
            r"wide spread|spread is \d+|market is dead|abandoned)",
    "failed": r"(didn'?t work|does ?n'?t work|lost money|blew up|gave up on|"
              r"backtest(ed)? .{0,40}(fail|negative|lost)|stopped working|"
              r"edge (is )?gone|arb (is )?gone|got picked off|adverse selection|"
              r"overfit|curve.?fit|out.?of.?sample)",
}


def ro(p: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True)


def search_reddit(rx: str, extra: str | None, limit: int = 400):
    con = ro(SOCIAL)
    con.create_function("RX", 2, lambda pat, s: 1 if s and re.search(pat, s, re.I) else 0)
    out = []
    q = ("select post_id, subreddit, title, selftext, score, num_comments, "
         "permalink, created_utc from rd_posts "
         "where RX(?, title||' '||coalesce(selftext,''))")
    args = [rx]
    if extra:
        q += " and RX(?, title||' '||coalesce(selftext,''))"
        args.append(extra)
    q += " order by score desc limit ?"
    args.append(limit)
    for r in con.execute(q, args):
        out.append({"kind": "post", "id": r[0], "sub": r[1], "title": r[2],
                    "body": (r[3] or "")[:1400], "score": r[4], "comments": r[5],
                    "permalink": r[6], "created": r[7]})
    qc = ("select comment_id, post_id, body, score, permalink, created_utc "
          "from rd_comments where RX(?, body)")
    argsc = [rx]
    if extra:
        qc += " and RX(?, body)"
        argsc.append(extra)
    qc += " order by score desc limit ?"
    argsc.append(limit)
    for r in con.execute(qc, argsc):
        out.append({"kind": "comment", "id": r[0], "post": r[1],
                    "body": (r[2] or "")[:1400], "score": r[3],
                    "permalink": r[4], "created": r[5]})
    con.close()
    return out


def search_yt(rx: str, extra: str | None):
    out = []
    for tag, p in (("broad", YT_BROAD), ("kalshi", YT_KALSHI)):
        if not p.exists():
            continue
        con = ro(p)
        con.create_function("RX", 2, lambda pat, s: 1 if s and re.search(pat, s, re.I) else 0)
        q = ("select c.video_id, v.title, c.claim_text, c.claim_type, c.stated_n, "
             "c.stated_win_rate, c.n_check_verdict from claims c "
             "left join videos v on v.video_id=c.video_id where RX(?, c.claim_text)")
        args = [rx]
        if extra:
            q += " and RX(?, c.claim_text)"
            args.append(extra)
        for r in con.execute(q, args):
            out.append({"corpus": tag, "video": r[0], "video_title": r[1],
                        "claim": r[2], "type": r[3], "n": r[4],
                        "win_rate": r[5], "ncheck": r[6]})
        con.close()
    return out


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "profit"
    extra = sys.argv[2] if len(sys.argv) > 2 else None
    if mode == "grep":
        rx = sys.argv[2]
        extra = sys.argv[3] if len(sys.argv) > 3 else None
    elif mode == "family":
        rx = sys.argv[2]
        extra = None
    else:
        rx = PATTERNS[mode]
    reddit = search_reddit(rx, extra)
    yt = search_yt(rx, extra)
    outdir = Path(__file__).resolve().parent.parent / "reports"
    outdir.mkdir(parents=True, exist_ok=True)
    name = f"prior_art_{mode}{'_' + re.sub(r'[^a-z0-9]+', '', (extra or '').lower())[:20] if extra else ''}.json"
    (outdir / name).write_text(
        json.dumps({"mode": mode, "regex": rx, "extra": extra,
                    "reddit": reddit, "youtube": yt}, indent=1),
        encoding="utf-8")
    print(f"{mode}: reddit={len(reddit)} youtube_claims={len(yt)} -> {name}")
    for r in reddit[:25]:
        head = r.get("title") or (r["body"][:110].replace("\n", " "))
        print(f"  [{r['score']:>5}] {r['kind']:7} {head[:120]}")
    for y in yt[:15]:
        print(f"  YT {y['corpus']:6} {y['claim'][:130]}")


if __name__ == "__main__":
    main()
