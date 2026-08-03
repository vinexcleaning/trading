"""STEP 7 -- the measurement. Phase 1 succeeds or fails here.

7a recall of the four known creators
7b low-view yield per family  (the central hypothesis)
7c overlap between families
7d the census
"""

import json
import statistics
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import channels as CH  # noqa: E402
import db  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LOW_VIEW = 5000
FAMS = ["F1", "F2", "F3"]


def hr(t):
    print("\n" + "=" * 74)
    print(t)
    print("=" * 74)


def family_video_ids(con, fam):
    return {
        r["video_id"]
        for r in con.execute(
            "SELECT DISTINCT video_id FROM retrieval_hits WHERE family=?", (fam,)
        )
    }


def main():
    con = db.connect()
    res = {}

    # ---------------- 7a ----------------
    hr("7a -- RECALL OF THE FOUR KNOWN CREATORS")
    seeds = CH.load_seeds()
    recall = []
    for s in seeds:
        cid = s["channel_id"]
        rows = con.execute(
            """SELECT h.family, h.query, MIN(h.rank) rank,
                      COUNT(DISTINCT h.run_idx) runs, v.video_id, v.title,
                      v.view_count, v.gate_status
               FROM retrieval_hits h JOIN videos v ON v.video_id = h.video_id
               WHERE v.channel_id = ?
               GROUP BY h.family, h.query, v.video_id
               ORDER BY rank""",
            (cid,),
        ).fetchall()
        by_fam = {}
        for r in rows:
            f = r["family"]
            if f not in by_fam or r["rank"] < by_fam[f]["rank"]:
                by_fam[f] = {
                    "rank": r["rank"], "query": r["query"], "video_id": r["video_id"],
                    "title": r["title"], "views": r["view_count"], "runs": r["runs"],
                    "gate": r["gate_status"],
                }
        n_vids = len({r["video_id"] for r in rows})
        print(f"\n  {s['name']}  ({s['subscribers']:,} subs, median {s['median_views']:,} views)")
        if not rows:
            print("      RETRIEVED: NO  -- no family surfaced any of this channel's videos")
        else:
            print(f"      RETRIEVED: YES -- {n_vids} distinct video(s)")
            for f in FAMS:
                if f in by_fam:
                    d = by_fam[f]
                    print(f"        {f}: rank {d['rank']:>2} on {d['query']!r}, "
                          f"stability {d['runs']}/3, {d['views'] or '?'} views, "
                          f"gate={d['gate']}")
                    print(f"            {(d['title'] or '')[:64]}")
                else:
                    print(f"        {f}: not retrieved")
        recall.append({
            "name": s["name"], "channel_id": cid, "retrieved": bool(rows),
            "n_videos": n_vids,
            "by_family": {f: by_fam.get(f) for f in FAMS},
        })
    res["recall_7a"] = recall

    nates = next(r for r in recall if r["name"] == "Nates Tokens")
    print("\n  CRITICAL CASE -- Nates Tokens:")
    if not nates["retrieved"]:
        print("      *** NOT RETRIEVED BY ANY FAMILY. RETRIEVAL IS BROKEN. ***")
        print("      The rest of the Step 7 numbers describe a retrieval set that")
        print("      misses a known, confirmed on-topic, low-view target. Do not")
        print("      read 7b as evidence for or against the insider hypothesis.")
    else:
        fams_hit = [f for f in FAMS if nates["by_family"][f]]
        print(f"      retrieved by {fams_hit}")

    # ---------------- 7b ----------------
    hr("7b -- LOW-VIEW YIELD PER FAMILY  (the central hypothesis)")
    print(f"  numerator: videos with <{LOW_VIEW:,} views AND gate_status='PASS'")
    print("  denominator: unique videos that family retrieved\n")
    print(f"  {'fam':<5}{'retrieved':>10}{'passed':>8}{'pass%':>8}"
          f"{'lowview':>9}{'lowview%':>10}{'BOTH':>7}{'YIELD':>9}")
    yields = {}
    for fam in FAMS:
        ids = family_video_ids(con, fam)
        if not ids:
            continue
        marks = ",".join("?" * len(ids))
        rows = con.execute(
            f"SELECT video_id, view_count, gate_status FROM videos WHERE video_id IN ({marks})",
            tuple(ids),
        ).fetchall()
        n = len(rows)
        passed = [r for r in rows if r["gate_status"] == "PASS"]
        low = [r for r in rows if (r["view_count"] or 0) < LOW_VIEW]
        both = [r for r in passed if (r["view_count"] or 0) < LOW_VIEW]
        yields[fam] = {
            "retrieved": n, "passed": len(passed), "low_view": len(low),
            "both": len(both), "yield": round(len(both) / n, 4) if n else None,
            "pass_rate": round(len(passed) / n, 4) if n else None,
            "low_view_rate": round(len(low) / n, 4) if n else None,
        }
        y = yields[fam]
        print(f"  {fam:<5}{n:>10}{len(passed):>8}{100*y['pass_rate']:>7.1f}%"
              f"{len(low):>9}{100*y['low_view_rate']:>9.1f}%{len(both):>7}"
              f"{100*y['yield']:>8.1f}%")
    res["low_view_yield_7b"] = yields

    if "F1" in yields and "F2" in yields:
        f1, f2 = yields["F1"]["yield"], yields["F2"]["yield"]
        ratio = (f2 / f1) if f1 else None
        diff_pp = 100 * (f2 - f1)
        print(f"\n  F2 yield {100*f2:.1f}%  vs  F1 yield {100*f1:.1f}%   "
              f"difference {diff_pp:+.1f} pp"
              + (f", ratio {ratio:.2f}x" if ratio else ""))
        if ratio is None:
            verdict = "F1 yield is zero -- ratio undefined"
        elif ratio >= 1.5:
            verdict = ("SUPPORTED -- F2's low-view yield substantially exceeds F1's. "
                       "Insider vocabulary is doing the work the project assumes.")
        elif ratio <= 1.15:
            verdict = ("NOT SUPPORTED -- F1 and F2 yield roughly equally. The "
                       "insider-vocabulary hypothesis, which is the premise of the "
                       "whole retrieval strategy, is not carrying its weight.")
        else:
            verdict = ("WEAK -- F2 is ahead but not decisively. Not enough to justify "
                       "a 12-query family over a 4-query one on this evidence.")
        print(f"\n  VERDICT: {verdict}")
        res["hypothesis_verdict"] = {"f1_yield": f1, "f2_yield": f2,
                                     "ratio": ratio, "diff_pp": round(diff_pp, 2),
                                     "verdict": verdict}

    # ---------------- 7c ----------------
    hr("7c -- OVERLAP BETWEEN FAMILIES")
    sets = {f: family_video_ids(con, f) for f in FAMS}
    overlap = {}
    print(f"  {'pair':<10}{'|A|':>6}{'|B|':>6}{'shared':>8}{'jaccard':>9}"
          f"{'  share of smaller'}")
    for a, b in combinations(FAMS, 2):
        A, B = sets[a], sets[b]
        if not (A and B):
            continue
        inter, union = len(A & B), len(A | B)
        smaller = min(len(A), len(B))
        overlap[f"{a}-{b}"] = {
            "a": len(A), "b": len(B), "shared": inter,
            "jaccard": round(inter / union, 3),
            "share_of_smaller": round(inter / smaller, 3),
        }
        print(f"  {a}-{b:<7}{len(A):>6}{len(B):>6}{inter:>8}"
              f"{inter/union:>9.3f}{inter/smaller:>18.3f}")
    exclusive = {
        f: len(sets[f] - set().union(*[sets[g] for g in FAMS if g != f]))
        for f in FAMS if sets[f]
    }
    print("\n  videos found ONLY by that family:")
    for f, n in exclusive.items():
        print(f"    {f}: {n}/{len(sets[f])} ({100*n/len(sets[f]):.1f}%)")
    res["overlap_7c"] = {"pairwise": overlap, "exclusive": exclusive}

    # ---------------- 7d ----------------
    hr("7d -- THE CENSUS")
    tot_hits = con.execute("SELECT COUNT(*) c FROM retrieval_hits").fetchone()["c"]
    uniq_search = con.execute(
        "SELECT COUNT(*) c FROM videos WHERE source='search'"
    ).fetchone()["c"]
    uniq_all = con.execute("SELECT COUNT(*) c FROM videos").fetchone()["c"]
    print(f"  total hits (video x family x query x run) : {tot_hits}")
    print(f"  unique videos from search                 : {uniq_search}")
    print(f"  unique videos incl. channel expansion     : {uniq_all}")

    print("\n  gate census:")
    gate_rows = con.execute(
        "SELECT gate_status, COUNT(*) n FROM videos WHERE gate_status IS NOT NULL"
        " GROUP BY gate_status ORDER BY n DESC"
    ).fetchall()
    gate_census = {r["gate_status"]: r["n"] for r in gate_rows}
    gated = sum(gate_census.values())
    for k, v in gate_census.items():
        print(f"    {k:<26} {v:>5}  ({100*v/gated:.1f}%)")

    print("\n  drop reasons:")
    for r in con.execute(
        "SELECT gate, COUNT(*) n FROM drops GROUP BY gate ORDER BY n DESC"
    ):
        print(f"    gate {r['gate']:<6} {r['n']:>5}")

    ages = [
        r["age_months"] for r in con.execute(
            "SELECT age_months FROM videos WHERE age_months IS NOT NULL"
        )
    ]
    age_stats = None
    if ages:
        ages.sort()
        buckets = [(0, 6), (6, 12), (12, 18), (18, 24), (24, 36), (36, 1e9)]
        print(f"\n  age distribution (n={len(ages)} with a known upload date):")
        print(f"    median {statistics.median(ages):.1f} mo, "
              f"min {min(ages):.1f}, max {max(ages):.1f}")
        for lo, hi in buckets:
            c = sum(1 for a in ages if lo <= a < hi)
            label = f"{lo}-{hi} mo" if hi < 1e9 else f"{lo}+ mo"
            print(f"      {label:<12} {c:>5}  ({100*c/len(ages):>5.1f}%)")
        within = sum(1 for a in ages if a <= 18)
        print(f"    within the 18-month cutoff: {within}/{len(ages)} "
              f"({100*within/len(ages):.1f}%)  -> "
              f"{len(ages)-within} tagged STALE")
        age_stats = {
            "n": len(ages), "median": round(statistics.median(ages), 2),
            "min": round(min(ages), 2), "max": round(max(ages), 2),
            "within_18mo": within, "stale": len(ages) - within,
            "buckets": {f"{lo}-{hi}": sum(1 for a in ages if lo <= a < hi)
                        for lo, hi in buckets},
        }

    step345 = json.loads((ROOT / "reports" / "step345_retrieval.json").read_text())
    print(f"\n  jaccard per family (run-to-run stability): {step345['jaccard_per_family']}")
    print(f"  retrieval wall clock: {step345['wall_clock_s']}s")
    print(f"  throttle verdict    : {step345['throttle']['verdict']}")

    res["census_7d"] = {
        "total_hits": tot_hits, "unique_search": uniq_search, "unique_all": uniq_all,
        "gate_census": gate_census, "age": age_stats,
        "jaccard_per_family": step345["jaccard_per_family"],
        "retrieval_wall_clock_s": step345["wall_clock_s"],
        "throttle": step345["throttle"],
    }

    (ROOT / "reports" / "step7_measurement.json").write_text(
        json.dumps(res, indent=2, default=str), encoding="utf-8"
    )
    print(f"\nwrote {ROOT / 'reports' / 'step7_measurement.json'}")
    con.close()


if __name__ == "__main__":
    main()
