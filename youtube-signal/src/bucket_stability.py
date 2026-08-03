"""Is the family bucket STABLE? It is the independent variable of the whole test.

WHY THIS EXISTS

retrieval_payoff.py compares videos found only by insider queries against videos
found only by beginner queries. That grouping -- `read_set.family_bucket` -- is
treated throughout as a property OF THE VIDEO. It is not. It is a property of a
particular retrieval run.

YouTube search is not deterministic. run_retrieval.py already knows this: it runs
every query three times and unions the results precisely because a single run is
unstable, and it measures within-family Jaccard at 0.69-0.76, meaning roughly a
quarter of results churn between runs of the SAME query.

A video that F1 happens to return on Monday and misses on Tuesday moves between
`multi` and `F2_only`. If that happens often, the test's groups are partly noise,
and non-differential misclassification attenuates any real effect toward zero --
so a null result would be uninterpretable for a reason that has nothing to do
with retrieval quality.

Two independent full retrieval runs now exist: the laptop's corpus (transferred
via `_from_laptop/signal.db`) and this machine's rebuild. Every video present in
both is a paired observation of the same underlying video labelled twice. That
is a direct measurement of label reliability, and it needs no new network calls.

Reports raw agreement and Cohen's kappa. Kappa corrects for agreement that would
happen by chance given the marginal distribution, which matters here because the
buckets are very unequal -- F2_only is large, so two random labellers would agree
often on that alone.

Usage:  python src/bucket_stability.py
"""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db_phase2  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LAPTOP_DB = ROOT / "_from_laptop" / "signal.db"
BUCKETS = ["F1_only", "F2_only", "F2B_only", "multi"]


def bucket_of(families):
    if families == {"F1"}:
        return "F1_only"
    if families == {"F2"}:
        return "F2_only"
    if families == {"F2B"}:
        return "F2B_only"
    return "multi"


def buckets_from(con):
    fam = {}
    for r in con.execute("SELECT DISTINCT video_id, family FROM retrieval_hits"):
        fam.setdefault(r["video_id"], set()).add(r["family"])
    return {v: bucket_of(f) for v, f in fam.items() if f}


def kappa(pairs):
    """Cohen's kappa over (label_a, label_b) pairs."""
    n = len(pairs)
    if not n:
        return None
    obs = sum(1 for a, b in pairs if a == b) / n
    ma = {b: sum(1 for a, _ in pairs if a == b) / n for b in BUCKETS}
    mb = {b: sum(1 for _, x in pairs if x == b) / n for b in BUCKETS}
    exp = sum(ma[b] * mb[b] for b in BUCKETS)
    return obs, exp, (obs - exp) / (1 - exp) if exp < 1 else None


def main():
    if not LAPTOP_DB.exists():
        print(f"no laptop DB at {LAPTOP_DB}; nothing to compare")
        return

    lc = sqlite3.connect(LAPTOP_DB)
    lc.row_factory = sqlite3.Row
    dc = db_phase2.connect()

    lap = buckets_from(lc)
    desk = buckets_from(dc)
    shared = sorted(set(lap) & set(desk))

    print("=" * 76)
    print("BUCKET LABEL STABILITY across two independent retrieval runs")
    print("=" * 76)
    print(f"  laptop run  : {len(lap):>5} videos with a family label")
    print(f"  desktop run : {len(desk):>5}")
    print(f"  in BOTH     : {len(shared):>5}   <- the paired sample")

    if len(shared) < 10:
        print("\n  too few shared videos to judge.")
        return

    pairs = [(lap[v], desk[v]) for v in shared]
    obs, exp, k = kappa(pairs)

    print(f"\n  raw agreement      {100*obs:.1f}%")
    print(f"  chance agreement   {100*exp:.1f}%   (buckets are very unequal)")
    print(f"  Cohen's kappa      {k:.3f}")
    verdict = ("almost perfect" if k > .8 else "substantial" if k > .6 else
               "moderate" if k > .4 else "fair" if k > .2 else "SLIGHT / near chance")
    print(f"  -> {verdict}")

    print("\n  confusion matrix (rows laptop, cols desktop):")
    print(f"    {'':<10}" + "".join(f"{b:>10}" for b in BUCKETS) + f"{'total':>8}")
    for a in BUCKETS:
        row = [sum(1 for x, y in pairs if x == a and y == b) for b in BUCKETS]
        print(f"    {a:<10}" + "".join(f"{c:>10}" for c in row) + f"{sum(row):>8}")
    tot = [sum(1 for _, y in pairs if y == b) for b in BUCKETS]
    print(f"    {'total':<10}" + "".join(f"{c:>10}" for c in tot) + f"{sum(tot):>8}")

    # The number that actually decides whether the test is viable: how often does
    # a video keep the EXCLUSIVITY that defines the two test arms?
    print("\n  the number that matters for retrieval_payoff.py:")
    ins = {"F2_only", "F2B_only"}
    arms = []
    for a, b in pairs:
        ga = "INSIDER" if a in ins else "BEGINNER" if a == "F1_only" else "MULTI"
        gb = "INSIDER" if b in ins else "BEGINNER" if b == "F1_only" else "MULTI"
        arms.append((ga, gb))
    for g in ("INSIDER", "BEGINNER"):
        same = sum(1 for a, b in arms if a == g and b == g)
        tot_g = sum(1 for a, _ in arms if a == g)
        if tot_g:
            print(f"    labelled {g:<9} on the laptop -> still {g:<9} here: "
                  f"{same}/{tot_g} ({100*same/tot_g:.0f}%)")
    stable = sum(1 for a, b in arms if a == b)
    print(f"    test-arm assignment identical in both runs: "
          f"{stable}/{len(arms)} ({100*stable/len(arms):.0f}%)")

    out = {
        "n_shared": len(shared), "raw_agreement": round(obs, 4),
        "chance_agreement": round(exp, 4), "kappa": round(k, 4),
        "arm_stability": round(stable / len(arms), 4),
    }
    (ROOT / "reports" / "bucket_stability.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote reports/bucket_stability.json")
    lc.close(); dc.close()


if __name__ == "__main__":
    main()
