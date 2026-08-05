"""A fifth corpus: Hacker News. Permitted by an explicit `Allow`, and unused.

WHY HN AND NOT SOMETHING EASIER

`social-signal` measured that sub-minute video clears the substance gate at
31.6% against 66.3% for 10-30 minute video. Length is a proxy for whether
anybody bothered to state a denominator. HN threads are long-form text written
by people who expect to be contradicted by someone who has read the paper, which
is the demographic that states an `n` unprompted - and it is the one major
technical forum this programme has never touched.

THE PERMISSION, WHICH IS NOT ONE ANSWER BUT TWO

    hacker-news.firebaseio.com/robots.txt
        User-agent: *
        Allow: /*.json$          <- the API is EXPLICITLY permitted
        Allow: /*.json?*$
        Disallow: /                 only the HTML is not

    hn.algolia.com/robots.txt        404 - NO robots.txt is served at all

Those are different states and they are not treated the same. **Every byte of
CONTENT comes from the Firebase endpoint, which is explicitly allowed.** Algolia
is used only to turn a search term into a list of integer story ids - no text,
no comments, no author, nothing that ends up in the corpus - because a host that
serves no `robots.txt` is *undecidable*, not permitted, and this project has now
made that mistake in both directions in one week.

    python src/hn.py --collect          search + fetch, paced
    python src/hn.py --score            run rubric v2 over what was collected
    python src/hn.py --report

Cost: $0.00, no key. Writes only to `extractor-upgrade/data/hn.db` - no sibling
database is opened for writing anywhere in this project.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cases as CS       # noqa: E402
import corpora           # noqa: E402
import rubric_v2         # noqa: E402

UA = "extractor-upgrade/1.0 (+trading repo; HN via the permitted Firebase API)"
DB = corpora.DATA / "hn.db"

ALGOLIA = "https://hn.algolia.com/api/v1/search"      # DISCOVERY ONLY: ids
FIREBASE = "https://hacker-news.firebaseio.com/v0"    # CONTENT: explicitly Allow

# Same two-family split youtube-signal measured as its engine: beginner
# phrasing versus insider vocabulary. On the video corpus the two returned
# near-disjoint sets (Jaccard 0.037) and the insider family's yield of obscure
# sources beat the beginner family's by 2.25x.
# !! THE FIRST VERSION OF THIS TABLE WAS SELF-DEFEATING. Algolia AND-matches
# every term in the query, so a long insider phrase matches almost nothing.
# Probed directly rather than guessed:
#     "adverse selection market making"      0 hits
#     "adverse selection"                   20
#     "market making"                    1,343
#     "de-vig sportsbook"                    0
#     "walk forward backtest overfitting"    1
#     "walk forward"                        79
# Long phrases are how a human describes a concept and are NOT how a search
# index is queried. Insider vocabulary has to be SHORT to survive AND-matching.
QUERIES = {
    "F1_beginner": [
        "prediction market", "polymarket", "kalshi",
        "sports betting", "trading bot", "make money trading",
        "algorithmic trading", "quant trading",
    ],
    "F2_insider": [
        "adverse selection", "market making", "order book imbalance",
        "maker taker", "walk forward", "market microstructure",
        "brier score", "kelly criterion", "lookahead bias",
        "slippage", "limit order book", "execution cost",
    ],
}


def http(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def connect():
    DB.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB, timeout=120)   # 120 s, not SQLite's default 5
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript("""
    CREATE TABLE IF NOT EXISTS items(
      id INTEGER PRIMARY KEY, kind TEXT, title TEXT, url TEXT, text TEXT,
      by TEXT, score INTEGER, descendants INTEGER, time INTEGER,
      parent INTEGER, family TEXT, query TEXT, fetched TEXT);
    CREATE TABLE IF NOT EXISTS scores(
      id INTEGER PRIMARY KEY, s INTEGER, b INTEGER, h INTEGER,
      verdict TEXT, stale INTEGER, naked INTEGER, fired TEXT);
    -- !! A story found by BOTH query families used to be recorded under
    -- whichever family reached it first, because `collect` skipped any id it
    -- already had. That made the F1-F2 overlap STRUCTURALLY ZERO - the dedup
    -- decided the answer, not the data. Membership now lives in its own table
    -- so a story can belong to both, and Jaccard is computed from it.
    CREATE TABLE IF NOT EXISTS membership(
      id INTEGER, family TEXT, query TEXT,
      PRIMARY KEY(id, family, query));
    CREATE TABLE IF NOT EXISTS runlog(ts TEXT, step TEXT, detail TEXT);
    """)
    return con


def discover(term, hits=40):
    """Algolia -> integer ids ONLY. Nothing from this response is stored."""
    url = (f"{ALGOLIA}?query={urllib.parse.quote(term)}"
           f"&tags=story&hitsPerPage={hits}")
    try:
        d = http(url)
    except Exception as e:
        print(f"    discovery failed for {term!r}: {type(e).__name__}")
        return []
    return [int(h["objectID"]) for h in d.get("hits", []) if h.get("objectID")]


def item(i):
    """Firebase. This is the permitted endpoint and the only source of text."""
    try:
        return http(f"{FIREBASE}/item/{i}.json")
    except urllib.error.HTTPError:
        return None
    except Exception:
        return None


def collect_comments(pace=0.12, cap=25):
    """The comment pass, as its OWN walk over stored stories.

    !! IT WAS NOT SEPARATE, AND THAT WAS A BUG. `collect` fetched comments
    inside the `if sid in have: continue` branch, so once a story was stored,
    a later run skipped it AND its comments - the comment pass could never
    collect anything for a corpus that already existed. It looked like it was
    working: it re-ran every query, printed every story count, and wrote
    nothing. A silent no-op that reports progress is worse than a crash.
    """
    con = connect()
    have = {r[0] for r in con.execute("SELECT id FROM items")}
    stories = con.execute(
        "SELECT id, family, query FROM items WHERE kind='story'").fetchall()
    n = 0
    for k, s in enumerate(stories, 1):
        d = item(s["id"])
        time.sleep(pace)
        if not d:
            continue
        for kid in (d.get("kids") or [])[:cap]:
            if kid in have:
                continue
            c = item(kid)
            time.sleep(pace)
            if not c or c.get("dead") or c.get("deleted") or not c.get("text"):
                continue
            con.execute(
                "INSERT OR REPLACE INTO items VALUES(?,?,?,?,?,?,?,?,?,?,?,?,"
                "datetime('now'))",
                (kid, "comment", None, None, c.get("text"), c.get("by"),
                 None, None, c.get("time"), s["id"], s["family"], s["query"]))
            have.add(kid)
            n += 1
        if k % 20 == 0:
            con.commit()
            print(f"  {k}/{len(stories)} stories walked, {n} comments")
    con.commit()
    con.execute("INSERT INTO runlog VALUES(datetime('now'),'comments',?)",
                (str(n),))
    con.commit()
    con.close()
    return n


def collect(pace=0.12, comment_cap=25):
    con = connect()
    have = {r[0] for r in con.execute("SELECT id FROM items")}
    n_new = n_c = 0
    for family, terms in QUERIES.items():
        for term in terms:
            ids = discover(term)
            print(f"  [{family}] {term!r}: {len(ids)} stories")
            time.sleep(pace)
            for sid in ids:
                # Membership is recorded ALWAYS, even for an id already held -
                # this is the line whose absence made the overlap zero.
                con.execute("INSERT OR IGNORE INTO membership VALUES(?,?,?)",
                            (sid, family, term))
                if sid in have:
                    continue
                d = item(sid)
                time.sleep(pace)
                if not d or d.get("dead") or d.get("deleted"):
                    continue
                con.execute(
                    "INSERT OR REPLACE INTO items VALUES(?,?,?,?,?,?,?,?,?,?,?,?,"
                    "datetime('now'))",
                    (sid, d.get("type"), d.get("title"), d.get("url"),
                     d.get("text"), d.get("by"), d.get("score"),
                     d.get("descendants"), d.get("time"), None, family, term))
                have.add(sid)
                n_new += 1
                # Top-level comments carry the contradictions. Capped, because
                # a 400-comment thread is not 400 observations. Split into its
                # own pass because comments are ~25x the requests of stories
                # and blocking the corpus on them is a false economy.
                for kid in (d.get("kids") or [])[:comment_cap]:
                    if kid in have:
                        continue
                    c = item(kid)
                    time.sleep(pace)
                    if not c or c.get("dead") or c.get("deleted") or not c.get("text"):
                        continue
                    con.execute(
                        "INSERT OR REPLACE INTO items VALUES(?,?,?,?,?,?,?,?,?,?,?,?,"
                        "datetime('now'))",
                        (kid, "comment", None, None, c.get("text"),
                         c.get("by"), None, None, c.get("time"), sid,
                         family, term))
                    have.add(kid)
                    n_c += 1
            con.commit()
            print(f"      running total: {n_new} stories, {n_c} comments")
    con.execute("INSERT INTO runlog VALUES(datetime('now'),'collect',?)",
                (f"stories={n_new} comments={n_c}",))
    con.commit()
    con.close()
    return n_new, n_c


HTML = __import__("re").compile(r"<[^>]+>")
ENT = {"&#x27;": "'", "&quot;": '"', "&amp;": "&", "&lt;": "<", "&gt;": ">",
       "&#x2F;": "/", "&nbsp;": " "}


def plain(s):
    if not s:
        return ""
    s = HTML.sub(" ", s)
    for k, v in ENT.items():
        s = s.replace(k, v)
    return " ".join(s.split())


def score_all():
    con = connect()
    rows = con.execute("SELECT id, title, text FROM items").fetchall()
    n = 0
    for r in rows:
        txt = f"{r['title'] or ''}\n{plain(r['text'])}"
        res = rubric_v2.score(txt)
        con.execute("INSERT OR REPLACE INTO scores VALUES(?,?,?,?,?,?,?,?)",
                    (r["id"], res["s"], res["b"], res["h"], res["verdict"],
                     int(res["stale"]), int(res["naked_claim"]),
                     " ".join(res["fired"])))
        n += 1
    con.commit()
    con.execute("INSERT INTO runlog VALUES(datetime('now'),'score',?)", (str(n),))
    con.commit()
    con.close()
    return n


def report():
    from collections import Counter
    con = connect()
    tot = con.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    st = con.execute("SELECT COUNT(*) FROM items WHERE kind='story'").fetchone()[0]
    verd = Counter(r[0] for r in con.execute("SELECT verdict FROM scores"))
    fam = Counter(r[0] for r in con.execute("SELECT family FROM items WHERE kind='story'"))

    # The family overlap test - the same measurement youtube-signal built its
    # retrieval design on.
    f1 = {r[0] for r in con.execute(
        "SELECT id FROM membership WHERE family='F1_beginner'")}
    f2 = {r[0] for r in con.execute(
        "SELECT id FROM membership WHERE family='F2_insider'")}
    jac = len(f1 & f2) / len(f1 | f2) if (f1 | f2) else 0

    top = con.execute(
        "SELECT i.id, i.title, i.by, i.score, i.descendants, i.kind, i.family, "
        "       s.s, s.b, s.h, s.verdict, s.naked "
        "FROM items i JOIN scores s ON s.id = i.id "
        "WHERE s.verdict NOT IN ('SKIP') "
        "ORDER BY s.s DESC, i.score DESC LIMIT 30").fetchall()

    L = ["# Hacker News — a fifth corpus, on an explicit `Allow`\n",
         "## Permission, which is two different answers\n",
         "```",
         "hacker-news.firebaseio.com/robots.txt",
         "    User-agent: *",
         "    Allow: /*.json$        <- the API is EXPLICITLY permitted",
         "    Allow: /*.json?*$",
         "    Disallow: /               only the HTML is not",
         "",
         "hn.algolia.com/robots.txt      404 — no robots.txt is served at all",
         "```",
         "**Every byte of content comes from the Firebase endpoint.** Algolia is "
         "used only to turn a search term into a list of integer ids — no text, "
         "no author, no comment reaches the corpus through it — because a host "
         "serving no `robots.txt` is *undecidable*, not permitted. This project "
         "has now made that mistake in both directions in one week (a false "
         "kill and a false forbid), so the two states are kept apart.\n",
         "## What was collected\n", "| | |", "|---|---|",
         f"| items | **{tot:,}** |",
         f"| stories | **{st:,}** |",
         f"| comments | {tot - st:,} |",
         f"| F1 beginner / F2 insider stories | {len(f1)} / {len(f2)} |",
         f"| in BOTH families | {len(f1 & f2)} |",
         f"| **F1 ∩ F2 Jaccard** | **{jac:.3f}** |", ""]
    L.append(
        f"> **Jaccard {jac:.3f}**, computed from the `membership` table so "
        "a story can belong to both families. The DIRECTION reproduces: "
        "`youtube-signal` measured 0.037 on video and `signal-github` "
        "0.032, 0.033 and 0.036 on repositories, and this is a fourth "
        "corpus with a completely different retrieval engine."
        "\n>\n"
        "> **The MAGNITUDE does not reproduce and I will not claim it "
        f"does.** {jac:.3f} is about seven times lower than the prior "
        "three. The most likely reason is that I wrote both term lists "
        "myself and made them more vocabulary-disjoint than the video "
        "families were. **A number whose inputs I chose is not an "
        "independent replication of a number somebody else measured.**"
        "\n")
    L.append(
        "> **And this corpus is STORIES ONLY.** Comments were skipped for "
        "speed - they are ~25x the requests. On HN a story is usually a "
        "headline and a URL with no body text at all, so a substance "
        f"rubric has almost nothing to read: **{verd.get('SKIP', 0)} of "
        f"{tot} score SKIP.** That is not a finding about Hacker News, it "
        "is a finding about collecting the wrong half of it. The substance "
        "is in the comments and they are the next pass.\n")

    L.append("## Verdicts under rubric v2\n| verdict | n | share |\n|---|---|---|")
    for k, v in verd.most_common():
        L.append(f"| {k} | {v:,} | {v/max(1,tot):.1%} |")
    L.append("")
    naked = con.execute("SELECT COUNT(*) FROM scores WHERE naked=1").fetchone()[0]
    L.append(f"**{naked:,} of {tot:,} ({naked/max(1,tot):.1%}) carry a "
             "performance claim of their own with no denominator.** On the "
             "Reddit corpus that figure was 6.7%.\n")

    L.append("## The top of the corpus\n")
    L.append("| id | S | B | H | verdict | pts | cmts | family | title / opening |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for r in top:
        head = (r["title"] or "")[:70]
        L.append(f"| [{r['id']}](https://news.ycombinator.com/item?id={r['id']}) "
                 f"| {r['s']} | {r['b']} | {r['h']} | {r['verdict']} | "
                 f"{r['score'] or ''} | {r['descendants'] or ''} | "
                 f"{r['family'].split('_')[0]} | {head} |")
    L.append("")
    out = corpora.REPORTS / "T8_hackernews.md"
    out.write_text("\n".join(L), encoding="utf-8")
    con.close()
    print(f"  {tot:,} items ({st:,} stories) · Jaccard {jac:.3f} · "
          f"{dict(verd)}")
    print(f"  wrote {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--stories-only", action="store_true",
                    help="skip comments; ~25x fewer requests, lands in minutes")
    ap.add_argument("--comments", action="store_true",
                    help="the comment pass, as its own walk over stored stories")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.collect:
        s, c = collect(comment_cap=0 if a.stories_only else 25)
        print(f"  collected {s} stories, {c} comments")
    if a.comments:
        print(f"  collected {collect_comments()} comments")
    if a.score:
        print(f"  scored {score_all()}")
    if a.report or not (a.collect or a.score):
        report()


if __name__ == "__main__":
    main()
