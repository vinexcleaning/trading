"""What to read next, and in what ORDER -- so the pre-registered test can run.

WHY THIS EXISTS

The obvious reading order is "highest proxy score first". For the knowledge base
that is right. For the pre-registered retrieval test in retrieval_payoff.py it is
fatal, in two separate ways:

  1. COVERAGE. The test compares INSIDER-exclusive videos (F2_only, F2B_only)
     against BEGINNER-exclusive ones (F1_only). F1_only is much the smaller
     bucket. Read top-down by proxy score and it is entirely possible to read 40
     videos and have 3 from F1_only -- at which point there is no test, only a
     shrug. The groups have to be filled deliberately.

  2. SELECTION ON THE OUTCOME. proxy_score is built from the same surface
     features the S axis rewards -- cost terms, sample-size language, mechanism
     language, URLs. Reading the top of that ranking selects on a correlate of
     the outcome variable. If insider terms and beginner terms have different
     proxy distributions, ordering by proxy silently matches or anti-matches the
     groups on the very thing being tested.

So the order here is BUCKET-BALANCED ROUND ROBIN, and within a bucket it
preserves the read_set's own selection order, which select_read_set.py drew as a
seeded random sample within each (bucket x view band) cell. That keeps each
group a random sample of its bucket, which is the only thing that makes the
comparison mean what it claims to mean.

INSIDER and BEGINNER alternate first because they are the test. MULTI is read
last: a video that BOTH families found is by construction not evidence about
either one, so it earns its place in the knowledge base but not in the analysis.

THE CONFOUND THIS DOES *NOT* FIX, stated here so it is not discovered later as a
surprise: the buckets are unequal in size, and the read_set sampled them at
different depths. Whether that biases the comparison is checked directly in
retrieval_payoff.py Part A rather than assumed away.

Usage:  python src/next_reads.py [n]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db_phase2  # noqa: E402

GROUP_OF = {"F2_only": "INSIDER", "F2B_only": "INSIDER",
            "F1_only": "BEGINNER", "multi": "MULTI"}


def queue(con):
    """The full remaining read order, as [(group, row), ...]."""
    rows = con.execute(
        """SELECT r.video_id, r.family_bucket, r.view_band, r.selection_rule,
                  v.title, v.channel_name, v.view_count, v.duration_s,
                  v.gate_status, t.video_id AS has_transcript
           FROM read_set r
           JOIN videos v ON v.video_id = r.video_id
           LEFT JOIN transcripts t ON t.video_id = r.video_id
           WHERE r.video_id NOT IN (SELECT video_id FROM scores)
           ORDER BY r.rowid"""
    ).fetchall()

    buckets = {"INSIDER": [], "BEGINNER": [], "MULTI": []}
    for r in rows:
        if not r["has_transcript"]:
            continue                      # nothing to read; not a candidate
        buckets[GROUP_OF.get(r["family_bucket"], "MULTI")].append(r)

    order, i = [], 0
    # Alternate the two test groups until BOTH are exhausted, then MULTI.
    while buckets["INSIDER"] or buckets["BEGINNER"]:
        g = "INSIDER" if i % 2 == 0 else "BEGINNER"
        other = "BEGINNER" if g == "INSIDER" else "INSIDER"
        src = buckets[g] or buckets[other]
        order.append((g if buckets[g] else other, src.pop(0)))
        i += 1
    order.extend(("MULTI", r) for r in buckets["MULTI"])
    return order


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    con = db_phase2.connect()

    done = {}
    for r in con.execute(
            """SELECT r.family_bucket b, COUNT(*) c FROM read_set r
               JOIN scores s ON s.video_id=r.video_id GROUP BY r.family_bucket"""):
        done[GROUP_OF.get(r["b"], "MULTI")] = done.get(GROUP_OF.get(r["b"], "MULTI"), 0) + r["c"]
    print(f"already scored by group: "
          f"INSIDER {done.get('INSIDER',0)}  BEGINNER {done.get('BEGINNER',0)}  "
          f"MULTI {done.get('MULTI',0)}")

    order = queue(con)
    print(f"remaining readable: {len(order)}\n")
    print(f"  {'#':>3} {'group':<9}{'bucket':<10}{'views':>8}{'min':>5}  title")
    for i, (g, r) in enumerate(order[:n], 1):
        v = f"{r['view_count']:,}" if r["view_count"] is not None else "?"
        print(f"  {i:>3} {g:<9}{r['family_bucket']:<10}{v:>8}"
              f"{(r['duration_s'] or 0)/60:>5.0f}  {(r['title'] or '')[:44]}")
    print("\nids:")
    print(" ".join(r["video_id"] for _, r in order[:n]))
    con.close()


if __name__ == "__main__":
    main()
