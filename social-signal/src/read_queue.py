"""The READ step — dump an item for the model to read, and load what it found.

The mechanical scorer ranks; **reading extracts**. That distinction is the whole
lesson of the sibling projects: `signal-github` read 4 repos and found 6 defects
invisible to every computed component, in repos scoring 9 and 10, and every
finding this project has produced came from reading the top of the queue rather
than from the score.

Two commands.

    python src/read_queue.py next --n 5      # what to read, and why
    python src/read_queue.py dump <post_id>  # the full thread, ready to read
    python src/read_queue.py load <file.json>

The read itself is done **in-session by the model**, not by an API call. That is
`youtube-signal`'s conclusion after a session spent believing it needed a key:
`read_video.py` there has still never executed, because the transcript is read
directly. Same here — `dump` prints, the model reads, `load` records.

The extraction schema is deliberately the same shape as that project's, so the
two corpora stay comparable:

    {"post_id": "...", "s_total": 8, "b_total": 4, "h_total": 3,
     "verdict": "ABSORB_AND_RECOMMEND",
     "summary": "one paragraph, what it actually says",
     "why_it_matters": "what it changes for this repo, or 'nothing'",
     "claims": [{"claim_text": "...", "claim_type": "result",
                 "stated_n": 4604, "stated_period": "7 months",
                 "stated_capital": null, "stated_win_rate": null,
                 "quote": "under fifteen words, verbatim"}],
     "tools":  [{"name": "...", "url": null, "purpose": "...",
                 "is_authors_own": "no|disclosed|undisclosed"}],
     "methods":[{"title": "...", "steps": ["...", "..."]}]}

**Never invent a denominator.** `stated_n` is null unless the author wrote a
number. The n-check exists to test whether a stated sample can clear its own
break-even; inventing the sample defeats it entirely.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

EXPIRY_MONTHS = {"mechanism": 999, "math": 999, "concept": 999,
                 "procedure": 12, "tool_rec": 4, "spec": 3, "result": 3}


def cmd_next(con, args):
    """The queue, with the reason each item is on it."""
    rows = con.execute("""
        SELECT p.post_id, p.platform, p.subreddit, p.title, p.score,
               p.num_comments, p.permalink,
               s.s_total, s.b_total, s.h_total, s.verdict
        FROM rd_scores s
        JOIN rd_posts p ON p.post_id = s.post_id
        WHERE p.post_id NOT IN (SELECT post_id FROM sc_readings)
        ORDER BY (CASE WHEN s.s_total > s.b_total THEN s.s_total
                       ELSE s.b_total END) DESC,
                 s.h_total DESC, p.num_comments DESC
        LIMIT ?""", (args.n,)).fetchall()
    done = con.execute("SELECT COUNT(*) c FROM sc_readings").fetchone()["c"]
    print(f"{done} read so far. Next {len(rows)}:\n")
    for i, r in enumerate(rows, 1):
        link = (f"https://reddit.com{r['permalink']}"
                if (r["platform"] or "reddit") == "reddit" else r["permalink"])
        print(f"{i}. [{r['platform'] or 'reddit'}] S={r['s_total']} "
              f"B={r['b_total']} H={r['h_total']}  {r['verdict']}  "
              f"{r['num_comments']} replies")
        print(f"   {(r['title'] or '')[:88]}")
        print(f"   {r['post_id']}  {link}\n")


def cmd_dump(con, args):
    """The whole thread — post plus every comment — for reading."""
    p = con.execute("SELECT * FROM rd_posts WHERE post_id=?",
                    (args.post_id,)).fetchone()
    if not p:
        raise SystemExit(f"no such post: {args.post_id}")
    cs = con.execute("""SELECT body, score FROM rd_comments WHERE post_id=?
                        ORDER BY score DESC""", (args.post_id,)).fetchall()
    plat = p["platform"] or "reddit"
    print("=" * 90)
    print(f"[{plat}] {p['subreddit']}   score {p['score']}   "
          f"{p['num_comments']} replies")
    print(p["title"])
    print(f"{p['permalink']}")
    print("=" * 90)
    print(textwrap.fill(" ".join((p["selftext"] or "").split()), 90))
    if cs:
        print(f"\n--- {len(cs)} comments, by score ---")
        for c in cs[:args.comments]:
            print(f"\n[{c['score']}] "
                  + textwrap.fill(" ".join((c["body"] or "").split()), 88,
                                  subsequent_indent="    "))


def cmd_load(con, args):
    with open(args.path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    docs = doc if isinstance(doc, list) else [doc]
    n_r = n_c = n_t = n_m = 0
    for d in docs:
        pid = d["post_id"]
        if not con.execute("SELECT 1 FROM rd_posts WHERE post_id=?",
                           (pid,)).fetchone():
            print(f"  SKIP {pid}: not in rd_posts")
            continue
        plat = con.execute("SELECT platform FROM rd_posts WHERE post_id=?",
                           (pid,)).fetchone()["platform"]
        con.execute("""INSERT OR REPLACE INTO sc_readings
                       (post_id, platform, s_total, b_total, h_total, verdict,
                        summary, why_it_matters, read_utc)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (pid, plat, d.get("s_total"), d.get("b_total"),
                     d.get("h_total"), d.get("verdict"), d.get("summary"),
                     d.get("why_it_matters"), db.now()))
        n_r += 1
        for c in d.get("claims") or []:
            ct = c.get("claim_type") or "concept"
            con.execute("""INSERT OR IGNORE INTO sc_claims
                           (post_id, claim_text, claim_type, stated_n,
                            stated_period, stated_capital, stated_win_rate,
                            expires_after_months, quote)
                           VALUES (?,?,?,?,?,?,?,?,?)""",
                        (pid, c["claim_text"], ct, c.get("stated_n"),
                         c.get("stated_period"), c.get("stated_capital"),
                         c.get("stated_win_rate"),
                         EXPIRY_MONTHS.get(ct, 12), c.get("quote")))
            n_c += 1
        for t in d.get("tools") or []:
            con.execute("""INSERT OR IGNORE INTO sc_tools_seen
                           (post_id, name, url, purpose, is_authors_own)
                           VALUES (?,?,?,?,?)""",
                        (pid, t["name"], t.get("url"), t.get("purpose"),
                         t.get("is_authors_own") or "no"))
            n_t += 1
        for m in d.get("methods") or []:
            con.execute("""INSERT OR IGNORE INTO sc_methods
                           (post_id, title, steps_json) VALUES (?,?,?)""",
                        (pid, m.get("title"), json.dumps(m.get("steps") or [])))
            n_m += 1
    con.commit()
    print(f"  loaded {n_r} readings, {n_c} claims, {n_t} tools, {n_m} methods")
    tot = con.execute("SELECT COUNT(*) c FROM sc_readings").fetchone()["c"]
    nd = con.execute("SELECT COUNT(*) c FROM sc_claims "
                     "WHERE claim_type='result' AND stated_n IS NULL").fetchone()["c"]
    nn = con.execute("SELECT COUNT(*) c FROM sc_claims "
                     "WHERE claim_type='result'").fetchone()["c"]
    print(f"  {tot} items read in total")
    if nn:
        print(f"  result claims WITHOUT a denominator: {nd}/{nn} "
              f"({100*nd/nn:.0f}%) — that ratio IS the measurement")
    db.log(con, "read_queue.load",
           f"readings={n_r} claims={n_c} tools={n_t} methods={n_m} total={tot}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("next"); a.add_argument("--n", type=int, default=5)
    b = sub.add_parser("dump")
    b.add_argument("post_id"); b.add_argument("--comments", type=int, default=40)
    c = sub.add_parser("load"); c.add_argument("path")
    args = ap.parse_args()

    con = db.connect()
    {"next": cmd_next, "dump": cmd_dump, "load": cmd_load}[args.cmd](con, args)
    con.close()


if __name__ == "__main__":
    main()
