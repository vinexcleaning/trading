"""Did v2 fix a rubric, or memorise 24 cases?

The test set has 24 rows. A rubric can be bent to fit 24 rows and be worse
everywhere else, and nothing inside `validate_rubric.py` can tell the
difference. This runs v1 and v2 over the WHOLE population neither was tuned on
- 4,432 scored Reddit posts and every transcript in both video corpora - and
reports the shift.

What a targeted fix looks like: most of the corpus does not move, and the rows
that do move are the ones the named defects predict (staleness flags appearing,
condemnation-quoting posts climbing out of SKIP, denominator-free boasts
dropping out of RECOMMEND).

What a rewrite looks like: a large fraction of the corpus changes verdict, at
which point the 24-case improvement is not evidence of anything.

    python src/population_check.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cases as CS      # noqa: E402
import corpora          # noqa: E402
import rubric_v2        # noqa: E402

LEX = corpora.lexicon()


def population():
    """(id, text, meta, corpus) for everything, deliberately unfiltered."""
    out = []
    con = corpora.ro("reddit")
    for r in con.execute("SELECT p.post_id, p.title, p.selftext, p.created_utc "
                         "FROM rd_posts p JOIN rd_scores s "
                         "ON s.post_id = p.post_id"):
        out.append((f"reddit:{r['post_id']}",
                    f"{r['title']}\n{r['selftext'] or ''}",
                    {"created_utc": r["created_utc"]}, "reddit"))
    con.close()
    for corpus in ("yt", "yt_kalshi"):
        con = corpora.ro(corpus)
        for r in con.execute(
                "SELECT t.video_id, v.title, v.upload_date, t.snippets_json "
                "FROM transcripts t JOIN videos v ON v.video_id = t.video_id"):
            body = " ".join(s["text"] for s in json.loads(r["snippets_json"]))
            out.append((f"{corpus}:{r['video_id']}",
                        f"{r['title']}\n{body}",
                        {"upload_date": r["upload_date"]}, corpus))
        con.close()
    return out


def main():
    pop = population()
    print(f"population: {len(pop)} documents")

    v1c, v2c, moved = Counter(), Counter(), Counter()
    stale_hits, n_stale, examples = [], 0, []
    naked = 0
    for did, text, meta, corpus in pop:
        s, b, h, _ = LEX.score(text)
        a1 = CS.VERDICT_TO_ACTION[LEX.verdict(s, b, h)]
        r = rubric_v2.score(text, meta=meta, corpus=corpus)
        a2 = CS.VERDICT_TO_ACTION[r["verdict"]]
        v1c[a1] += 1
        v2c[a2] += 1
        if a1 != a2:
            moved[f"{a1}->{a2}"] += 1
            if len(examples) < 12:
                examples.append((did, a1, a2, r["verdict"],
                                 (r["stale_why"] or [""])[0][:90]))
        if r["stale"]:
            n_stale += 1
            if len(stale_hits) < 25:
                stale_hits.append((did, r["stale_why"][0][:110]))
        if r["naked_claim"]:
            naked += 1

    n = len(pop)
    L = ["# Population check - did v2 fix a rubric or memorise 24 cases?\n",
         f"Run over **{n:,} documents** - every scored Reddit post plus every "
         "transcript in both video corpora. Neither rubric was tuned on this "
         "set; the 24 test cases are a 0.5% slice of it.\n",
         "## Action distribution\n",
         "| action | v1 lexicon | v2 | change |", "|---|---|---|---|"]
    for a in CS.ACTIONS:
        d = v2c[a] - v1c[a]
        L.append(f"| {a} | {v1c[a]:,} ({v1c[a]/n:.1%}) | "
                 f"{v2c[a]:,} ({v2c[a]/n:.1%}) | {d:+,} |")
    total_moved = sum(moved.values())
    L.append(f"\n**{total_moved:,} of {n:,} documents changed action = "
             f"{total_moved/n:.1%}.**\n")
    L.append("## Which way they moved\n")
    L.append("| transition | n |")
    L.append("|---|---|")
    for k, v in moved.most_common():
        L.append(f"| {k} | {v:,} |")
    L.append(f"\n## The new axis\n")
    L.append(f"**{n_stale:,} of {n:,} ({n_stale/n:.2%}) flagged as teaching a "
             "path that no longer works.** Every flag names the identifier and "
             "the check that killed it, so each one is falsifiable by a single "
             "API call.\n")
    L.append("| document | why |")
    L.append("|---|---|")
    for did, why in stale_hits:
        L.append(f"| `{did}` | {why} |")
    L.append(f"\n**{naked:,} of {n:,} ({naked/n:.1%}) carry a performance "
             "claim of their own with no denominator anywhere in the text.**\n")
    L.append("## A sample of what moved\n")
    L.append("| document | v1 | v2 | v2 verdict | note |")
    L.append("|---|---|---|---|---|")
    for did, a1, a2, v, why in examples:
        L.append(f"| `{did}` | {a1} | {a2} | {v} | {why} |")
    L.append("")

    out = corpora.REPORTS / "T1_population_check.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"  moved {total_moved}/{n} = {total_moved/n:.1%}; "
          f"stale {n_stale}; naked {naked}")
    print(f"  wrote {out}")


if __name__ == "__main__":
    main()
