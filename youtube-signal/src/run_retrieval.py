"""STEPS 3-5 -- run the query families under the union protocol.

Every query runs 3 times, spaced >=20s apart at the round level. The retrieval set
is the UNION of the three runs; retrieval_stability records how many runs each
video appeared in. Mean pairwise Jaccard per family is computed from the stored
per-run hits, not from anything held in memory.

Search only. No transcripts, no gates -- those are Step 6 and run separately so a
throttle here does not cost the transcript work.
"""

import datetime as dt
import json
import sys
import time
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db  # noqa: E402
import queries as Q  # noqa: E402
import retrieval  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
N_RUNS = 3
ROUND_GAP_S = 20
TOP_N = 25


def main():
    t_start = time.time()
    con = db.connect()
    r = retrieval.Retriever(con, today=dt.date(2026, 8, 2))
    fams = Q.families("prediction_markets")

    total_q = sum(len(v) for v in fams.values())
    print(f"families: { {k: len(v) for k, v in fams.items()} }  "
          f"= {total_q} queries x {N_RUNS} runs = {total_q * N_RUNS} searches")
    print(f"pacing: >={retrieval.SEARCH_GAP_S}s between calls, "
          f">={ROUND_GAP_S}s between rounds\n")

    for run_idx in range(N_RUNS):
        if run_idx:
            print(f"\n--- waiting {ROUND_GAP_S}s before round {run_idx + 1} ---")
            time.sleep(ROUND_GAP_S)
        print(f"\n===== ROUND {run_idx + 1}/{N_RUNS} =====")
        for fam, qs in fams.items():
            sp = Q.FAMILY_SP[fam]
            for q in qs:
                entries, secs, err = r.search(q, fam, run_idx, sp=sp, n=TOP_N)
                if err:
                    print(f"  {fam} {q[:44]:<46} FAILED {err[:60]}")
                    continue
                r.record_hits(entries, fam, q, run_idx)
                print(f"  {fam} {q[:44]:<46} {len(entries):>3} results  {secs:>5.1f}s")

    # ---------- union + stability ----------
    print("\n===== UNION + STABILITY =====")
    rows = con.execute(
        """SELECT video_id, COUNT(DISTINCT run_idx) AS runs
           FROM retrieval_hits GROUP BY video_id"""
    ).fetchall()
    stability = {row["video_id"]: row["runs"] for row in rows}
    dist = {k: sum(1 for v in stability.values() if v == k) for k in (1, 2, 3)}
    print(f"  unique videos in union: {len(stability)}")
    for k in (3, 2, 1):
        pct = 100 * dist[k] / len(stability) if stability else 0
        print(f"    appeared in {k}/3 runs: {dist[k]:>4}  ({pct:.1f}%)")

    # ---------- Jaccard per family ----------
    print("\n===== STEP 4: MEAN PAIRWISE JACCARD PER FAMILY =====")
    jac = {}
    for fam in fams:
        per_run = {}
        for i in range(N_RUNS):
            ids = con.execute(
                "SELECT DISTINCT video_id FROM retrieval_hits WHERE family=? AND run_idx=?",
                (fam, i),
            ).fetchall()
            per_run[i] = {x["video_id"] for x in ids}
        vals = []
        for a, b in combinations(range(N_RUNS), 2):
            A, B = per_run[a], per_run[b]
            if A | B:
                vals.append(len(A & B) / len(A | B))
        jac[fam] = round(sum(vals) / len(vals), 3) if vals else None
        sizes = [len(per_run[i]) for i in range(N_RUNS)]
        print(f"  {fam}: mean pairwise Jaccard {jac[fam]}   per-run unique {sizes}")

    # Per-query Jaccard, so a single unstable query cannot hide inside a family mean.
    print("\n  per-query (worst 8):")
    perq = []
    for fam, qs in fams.items():
        for q in qs:
            pr = {}
            for i in range(N_RUNS):
                ids = con.execute(
                    "SELECT DISTINCT video_id FROM retrieval_hits"
                    " WHERE family=? AND query=? AND run_idx=?", (fam, q, i)
                ).fetchall()
                pr[i] = {x["video_id"] for x in ids}
            vals = [
                len(pr[a] & pr[b]) / len(pr[a] | pr[b])
                for a, b in combinations(range(N_RUNS), 2)
                if pr[a] | pr[b]
            ]
            if vals:
                perq.append((round(sum(vals) / len(vals), 3), fam, q))
    for j, fam, q in sorted(perq)[:8]:
        print(f"    {j:.3f}  {fam}  {q}")

    # ---------- throttling ----------
    print("\n===== STEP 5: THROTTLE CHECK (premise 2) =====")
    tr = r.throttle_report()
    for k, v in tr.items():
        print(f"  {k:<28} {v}")

    elapsed = round(time.time() - t_start, 1)
    print(f"\nwall clock: {elapsed}s")

    out = {
        "n_runs": N_RUNS,
        "families": {k: len(v) for k, v in fams.items()},
        "unique_videos": len(stability),
        "stability_distribution": dist,
        "jaccard_per_family": jac,
        "jaccard_per_query_worst": [
            {"jaccard": j, "family": f, "query": q} for j, f, q in sorted(perq)[:12]
        ],
        "throttle": tr,
        "wall_clock_s": elapsed,
    }
    (ROOT / "reports" / "step345_retrieval.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )
    print(f"wrote {ROOT / 'reports' / 'step345_retrieval.json'}")
    con.close()


if __name__ == "__main__":
    main()
