"""Run ONLY the new F2B family through the Phase 1 retrieval protocol.

Same union protocol as Phase 1: every query 3 times, >=20s between rounds, union
of the three runs, per-run hits stored so stability and Jaccard stay computable.
F1/F2 hits already in the DB are left alone.
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
N_RUNS, ROUND_GAP_S, TOP_N = 3, 20, 25
FAM = "F2B"


def main():
    t0 = time.time()
    con = db.connect()
    r = retrieval.Retriever(con, today=dt.date(2026, 8, 2))
    qs = Q.TOPICS["prediction_markets"][FAM]

    before = {x["video_id"] for x in con.execute("SELECT video_id FROM videos")}
    print(f"{FAM}: {len(qs)} queries x {N_RUNS} runs = {len(qs)*N_RUNS} searches")
    print(f"corpus before: {len(before)} videos\n")

    for run_idx in range(N_RUNS):
        if run_idx:
            print(f"\n--- waiting {ROUND_GAP_S}s before round {run_idx+1} ---")
            time.sleep(ROUND_GAP_S)
        print(f"===== ROUND {run_idx+1}/{N_RUNS} =====")
        for q in qs:
            entries, secs, err = r.search(q, FAM, run_idx, sp=None, n=TOP_N)
            if err:
                print(f"  {q[:44]:<46} FAILED {err[:60]}")
                continue
            r.record_hits(entries, FAM, q, run_idx)
            print(f"  {q[:44]:<46} {len(entries):>3} results {secs:>5.1f}s")

    after = {x["video_id"] for x in con.execute("SELECT video_id FROM videos")}
    f2b_ids = {x["video_id"] for x in con.execute(
        "SELECT DISTINCT video_id FROM retrieval_hits WHERE family=?", (FAM,))}
    f1 = {x["video_id"] for x in con.execute(
        "SELECT DISTINCT video_id FROM retrieval_hits WHERE family='F1'")}
    f2 = {x["video_id"] for x in con.execute(
        "SELECT DISTINCT video_id FROM retrieval_hits WHERE family='F2'")}

    print(f"\n===== WHAT F2B ADDED =====")
    print(f"  F2B unique videos      : {len(f2b_ids)}")
    print(f"  brand new to the corpus: {len(after - before)}")
    print(f"  overlap with F2        : {len(f2b_ids & f2)}  "
          f"(Jaccard {len(f2b_ids & f2)/len(f2b_ids | f2):.3f})")
    print(f"  overlap with F1        : {len(f2b_ids & f1)}  "
          f"(Jaccard {len(f2b_ids & f1)/len(f2b_ids | f1):.3f})")
    excl = len(f2b_ids - f1 - f2)
    print(f"  exclusive to F2B       : {excl}/{len(f2b_ids)} "
          f"({100*excl/len(f2b_ids):.1f}%)")

    jac = []
    for a, b in combinations(range(N_RUNS), 2):
        A = {x["video_id"] for x in con.execute(
            "SELECT DISTINCT video_id FROM retrieval_hits WHERE family=? AND run_idx=?",
            (FAM, a))}
        B = {x["video_id"] for x in con.execute(
            "SELECT DISTINCT video_id FROM retrieval_hits WHERE family=? AND run_idx=?",
            (FAM, b))}
        if A | B:
            jac.append(len(A & B) / len(A | B))
    print(f"  run-to-run Jaccard     : {sum(jac)/len(jac):.3f}")

    print("\n  per-query yield:")
    for q in qs:
        ids = {x["video_id"] for x in con.execute(
            "SELECT DISTINCT video_id FROM retrieval_hits WHERE family=? AND query=?",
            (FAM, q))}
        new = len(ids - f1 - f2)
        print(f"    {q[:44]:<46} {len(ids):>3} uniq, {new:>3} not in F1/F2")

    tr = r.throttle_report()
    print(f"\n  throttle: {tr['verdict']}  "
          f"({tr['mean_results_first_half']} -> {tr['mean_results_second_half']} results)")

    out = {
        "family": FAM, "queries": qs, "unique": len(f2b_ids),
        "new_to_corpus": len(after - before),
        "overlap_f2": len(f2b_ids & f2), "overlap_f1": len(f2b_ids & f1),
        "exclusive": excl, "run_jaccard": round(sum(jac)/len(jac), 3),
        "wall_clock_s": round(time.time() - t0, 1), "throttle": tr,
    }
    (ROOT / "reports" / "f2b_retrieval.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwall clock {out['wall_clock_s']}s; wrote reports/f2b_retrieval.json")
    con.close()


if __name__ == "__main__":
    main()
