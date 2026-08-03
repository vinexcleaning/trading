"""Does the retrieval win CASH OUT? Pre-registered test.

THE OPEN QUESTION, carried unanswered since Phase 1:

  F1 (beginner vocabulary) and F2 (insider vocabulary) return almost disjoint
  video sets -- mean pairwise Jaccard 0.037 -- and F2 yields 2.25x more
  sub-5k-view videos. That is a retrieval fact and it is solid.

  It is NOT a quality fact. "Finds different videos" and "finds better videos"
  are different claims, and only the first one has ever been measured. A query
  family that reliably surfaces different-but-worse videos would produce exactly
  the same Jaccard.

So: do the insider-exclusive videos actually SCORE higher once read?

=== PRE-REGISTRATION ===================================================

Written before the scores it consumes exist, so the analysis cannot be tuned to
the answer. Committed as-is; if it is later edited, the diff is the audit trail.

H0   Insider-exclusive videos score no higher than beginner-exclusive ones.
H1   Insider-exclusive videos score higher.

GROUPS   from read_set.family_bucket, which is assigned by which families
         retrieved the video and is fixed at selection time:
           INSIDER  = F2_only + F2B_only   (found ONLY by practitioner terms)
           BEGINNER = F1_only              (found ONLY by newcomer terms)
         `multi` is reported but is not in the primary test: a video both
         families found is by definition not evidence about either.

PRIMARY OUTCOME   max(S, B), 0-10.
         Not S alone. S structurally cannot score a pure build video -- that is
         the documented rubric bug the B axis was added to fix -- and testing a
         retrieval family on an axis that cannot score half its output would
         measure the rubric, not the retrieval. max(S,B) is "did this video
         carry value on EITHER route in", which is the question the read set
         exists to answer.

SECONDARY   S alone; B alone; H; and P(verdict != SKIP).

TEST     Two-sided permutation test on the difference in MEANS, 200k resamples,
         seed 20260803. Two-sided because the honest alternative is that insider
         terms find WORSE videos -- more scammy niche content -- and a one-sided
         test would hide that. Rank-biserial correlation as the effect size.
         Permutation rather than a t-test because n is small and 0-10 scores are
         bounded and lumpy.

DECISION RULE, fixed in advance:
  p < 0.05 and effect favours INSIDER  -> CASHED OUT. The retrieval win is real.
  p < 0.05 and effect favours BEGINNER -> REFUTED, and F2/F2B should be reweighted.
  p >= 0.05                            -> NOT DEMONSTRATED. Report the minimum
                                          detectable effect so the null is
                                          interpretable instead of merely empty.

--- AMENDMENT, added after 4 of 60 videos were read, BEFORE any group was full
--- and before any between-group comparison had been computed.

A confound was found in the read_set itself, not in this script. Two declared
sensitivity analyses are added now rather than after the primary result, because
adding them afterwards would be fishing and adding them now is just honesty.

  CHANNEL CLUSTERING. select_read_set.py's ANCHOR rule admits every passing
  video from one channel (Nates Tokens). All three of them landed in F2_only,
  i.e. entirely inside the INSIDER arm, placed there by a rule that has nothing
  to do with which query family found them. Three videos from one creator share
  a house style, an honesty profile and a tooling stack, so they are not three
  independent observations. Untreated, this is pseudo-replication that inflates
  INSIDER's apparent n and can manufacture a difference on its own.

  SENSITIVITY 1 -- drop every video whose selection_rule is not 'stratified',
  removing the anchor block and the longest-video pick.
  SENSITIVITY 2 -- collapse each channel to its mean score and test on channel
  means, so a channel contributes exactly one observation whatever its count.

The PRIMARY test is still the one registered above, reported first and
unchanged. If the primary and the two sensitivities disagree, the honest
reading is the most conservative of the three, and this file says so rather
than letting a reader pick.

POWER IS REPORTED WHETHER OR NOT IT IS FLATTERING. A null at n=12 per group is
not evidence of no effect, and this script says so in its own output rather than
leaving the reader to work it out.

=== PART A ============================================================

Part A re-measures the Phase 1 retrieval facts (exclusivity, Jaccard, low-view
yield) on the whole gated corpus, where n is in the hundreds. Those numbers are
the premise of the question. If they do not replicate, Part B is moot.
"""

import json
import random
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db_phase2  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEED = 20260803
N_PERM = 200_000
LOW_VIEW = 5_000


# ---------------------------------------------------------------- statistics
def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def median(xs):
    if not xs:
        return float("nan")
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def perm_test(a, b, n_perm=N_PERM, seed=SEED):
    """Two-sided permutation test on the difference in means.

    Exact enumeration when the number of distinct splits is small enough that
    sampling would be the less accurate choice.
    """
    if not a or not b:
        return {"p": None, "diff": None, "n_perm": 0, "exact": False}
    obs = mean(a) - mean(b)
    pool = list(a) + list(b)
    na = len(a)

    from math import comb
    n_splits = comb(len(pool), na)
    rnd = random.Random(seed)

    if n_splits <= n_perm:
        hits = 0
        for idx in combinations(range(len(pool)), na):
            sel = set(idx)
            ga = [pool[i] for i in sel]
            gb = [pool[i] for i in range(len(pool)) if i not in sel]
            if abs(mean(ga) - mean(gb)) >= abs(obs) - 1e-12:
                hits += 1
        return {"p": hits / n_splits, "diff": obs, "n_perm": n_splits, "exact": True}

    hits = 0
    for _ in range(n_perm):
        rnd.shuffle(pool)
        if abs(mean(pool[:na]) - mean(pool[na:])) >= abs(obs) - 1e-12:
            hits += 1
    # +1/+1 so a p of exactly 0 is never reported from a sampled test.
    return {"p": (hits + 1) / (n_perm + 1), "diff": obs,
            "n_perm": n_perm, "exact": False}


def rank_biserial(a, b):
    """P(a > b) - P(b > a). Ties count half. -1..+1, 0 is no separation."""
    if not a or not b:
        return None
    gt = sum(1 for x in a for y in b if x > y)
    lt = sum(1 for x in a for y in b if x < y)
    return (gt - lt) / (len(a) * len(b))


def min_detectable_effect(a, b, seed=SEED, alpha=0.05, target_power=0.80,
                          n_sim=600):
    """Smallest constant shift this design would catch 80% of the time.

    Simulated by re-permuting the OBSERVED pooled values with a shift added, so
    it inherits the real spread rather than assuming a normal one. This is the
    number that makes a null interpretable: "no effect found, and we could only
    have found one of at least X" is a result. "No effect found" alone is not.
    """
    if len(a) < 2 or len(b) < 2:
        return None
    pool = list(a) + list(b)
    na, nb = len(a), len(b)
    rnd = random.Random(seed)
    for delta in [x * 0.25 for x in range(1, 41)]:      # 0.25 .. 10.0
        wins = 0
        for _ in range(n_sim):
            sa = [rnd.choice(pool) + delta for _ in range(na)]
            sb = [rnd.choice(pool) for _ in range(nb)]
            # cheap 2000-resample permutation inside the power loop
            r = perm_test(sa, sb, n_perm=2000, seed=rnd.randrange(1 << 30))
            if r["p"] is not None and r["p"] < alpha:
                wins += 1
        if wins / n_sim >= target_power:
            return round(delta, 2)
    return None


# ---------------------------------------------------------------- part A
def part_a(con):
    print("=" * 74)
    print("PART A -- do the Phase 1 RETRIEVAL facts replicate on this corpus?")
    print("=" * 74)

    fam = {}
    for r in con.execute("SELECT DISTINCT video_id, family FROM retrieval_hits"):
        fam.setdefault(r["video_id"], set()).add(r["family"])

    vids = {r["video_id"]: r for r in con.execute(
        "SELECT video_id, view_count, gate_status FROM videos WHERE source='search'")}

    fams = sorted({f for s in fam.values() for f in s})
    print(f"\nfamilies present: {fams}")
    print(f"videos retrieved by search: {len(fam)}")

    # --- pairwise Jaccard between families (the 0.037 number) ---
    print("\n  pairwise Jaccard between families (union over all runs):")
    members = {f: {v for v, s in fam.items() if f in s} for f in fams}
    jac = {}
    for x, y in combinations(fams, 2):
        A, B = members[x], members[y]
        j = len(A & B) / len(A | B) if (A | B) else 0.0
        jac[f"{x}|{y}"] = round(j, 4)
        print(f"    {x:<5} vs {y:<5}  Jaccard {j:.4f}   "
              f"|{x}|={len(A)} |{y}|={len(B)} shared={len(A & B)}")

    # --- exclusivity and low-view yield per family ---
    print("\n  per family: exclusivity, PASS rate, low-view yield")
    print(f"    {'fam':<6}{'found':>7}{'excl':>7}{'excl%':>8}"
          f"{'PASS':>7}{'PASS%':>8}{'<5k views':>11}{'low%':>8}")
    per_fam = {}
    for f in fams:
        A = members[f]
        excl = {v for v in A if fam[v] == {f}}
        passing = {v for v in A if vids.get(v, {}) and vids[v]["gate_status"] == "PASS"}
        low = {v for v in passing if (vids[v]["view_count"] or 0) < LOW_VIEW}
        per_fam[f] = {
            "found": len(A), "exclusive": len(excl),
            "exclusive_pct": round(100 * len(excl) / len(A), 1) if A else 0,
            "passing": len(passing),
            "pass_pct": round(100 * len(passing) / len(A), 1) if A else 0,
            "low_view": len(low),
            "low_view_pct_of_pass": round(100 * len(low) / len(passing), 1) if passing else 0,
        }
        d = per_fam[f]
        print(f"    {f:<6}{d['found']:>7}{d['exclusive']:>7}{d['exclusive_pct']:>7.1f}%"
              f"{d['passing']:>7}{d['pass_pct']:>7.1f}%{d['low_view']:>11}"
              f"{d['low_view_pct_of_pass']:>7.1f}%")

    # --- the 2.25x low-view ratio ---
    ratio = None
    if "F1" in per_fam and "F2" in per_fam and per_fam["F1"]["low_view_pct_of_pass"]:
        ratio = round(per_fam["F2"]["low_view_pct_of_pass"]
                      / per_fam["F1"]["low_view_pct_of_pass"], 2)
        print(f"\n  low-view yield ratio F2/F1: {ratio}x   (Phase 1 measured 2.25x)")

    return {"jaccard": jac, "per_family": per_fam, "low_view_ratio_f2_f1": ratio}


# ---------------------------------------------------------------- part B
def part_b(con):
    print("\n" + "=" * 74)
    print("PART B -- PRE-REGISTERED: do exclusive videos SCORE higher?")
    print("=" * 74)

    rows = con.execute(
        """SELECT r.video_id, r.family_bucket, r.view_band, r.selection_rule,
                  s.s_total, s.h_total, COALESCE(s.b_total,0) AS b_total, s.verdict,
                  v.title, v.channel_name, v.view_count
           FROM read_set r
           JOIN scores s ON s.video_id = r.video_id
           JOIN videos v ON v.video_id = r.video_id"""
    ).fetchall()

    print(f"\nread AND scored: {len(rows)} videos")
    if len(rows) < 6:
        print("  too few scored videos for the test. Read more, then re-run.")
        return {"n_scored": len(rows), "status": "INSUFFICIENT_DATA"}

    groups = {"INSIDER": [], "BEGINNER": [], "MULTI": []}
    for r in rows:
        fb = r["family_bucket"]
        g = ("INSIDER" if fb in ("F2_only", "F2B_only")
             else "BEGINNER" if fb == "F1_only"
             else "MULTI")
        groups[g].append(dict(r))

    print("\n  group sizes (from read_set.family_bucket, fixed at selection):")
    for g, xs in groups.items():
        print(f"    {g:<9} n={len(xs)}")

    outcomes = {
        "max(S,B) [PRIMARY]": lambda r: max(r["s_total"] or 0, r["b_total"] or 0),
        "S": lambda r: r["s_total"] or 0,
        "B": lambda r: r["b_total"] or 0,
        "H": lambda r: r["h_total"] or 0,
        "not SKIP": lambda r: 1.0 if r["verdict"] != "SKIP" else 0.0,
    }

    out = {"n_scored": len(rows),
           "group_n": {g: len(x) for g, x in groups.items()}, "tests": {}}

    A, B = groups["INSIDER"], groups["BEGINNER"]
    if len(A) < 3 or len(B) < 3:
        print(f"\n  PRIMARY TEST NOT RUN -- need >=3 per group, have "
              f"INSIDER={len(A)} BEGINNER={len(B)}.")
        print("  This is a coverage gap, not a null result. Do not report it as one.")
        out["status"] = "UNDERPOWERED_NOT_RUN"
    else:
        print(f"\n  INSIDER (n={len(A)})  vs  BEGINNER (n={len(B)})")
        print(f"    {'outcome':<20}{'insider':>9}{'beginner':>10}{'diff':>8}"
              f"{'p':>9}{'effect':>9}")
        for name, fn in outcomes.items():
            a = [fn(r) for r in A]
            b = [fn(r) for r in B]
            t = perm_test(a, b)
            e = rank_biserial(a, b)
            out["tests"][name] = {
                "insider_mean": round(mean(a), 3), "beginner_mean": round(mean(b), 3),
                "insider_median": median(a), "beginner_median": median(b),
                "diff": round(t["diff"], 3), "p": round(t["p"], 5),
                "exact": t["exact"], "rank_biserial": round(e, 3),
                "n_insider": len(a), "n_beginner": len(b),
            }
            print(f"    {name:<20}{mean(a):>9.2f}{mean(b):>10.2f}{t['diff']:>+8.2f}"
                  f"{t['p']:>9.4f}{e:>+9.2f}")

        prim = out["tests"]["max(S,B) [PRIMARY]"]
        a = [outcomes["max(S,B) [PRIMARY]"](r) for r in A]
        b = [outcomes["max(S,B) [PRIMARY]"](r) for r in B]
        mde = min_detectable_effect(a, b)
        out["mde_primary"] = mde

        print("\n  === VERDICT on the pre-registered rule ===")
        if prim["p"] < 0.05 and prim["diff"] > 0:
            out["status"] = "CASHED_OUT"
            print("  CASHED OUT -- insider-exclusive videos score higher, p="
                  f"{prim['p']:.4f}.")
        elif prim["p"] < 0.05 and prim["diff"] < 0:
            out["status"] = "REFUTED"
            print("  REFUTED -- insider-exclusive videos score LOWER, p="
                  f"{prim['p']:.4f}. Reweight F2/F2B.")
        else:
            out["status"] = "NOT_DEMONSTRATED"
            print(f"  NOT DEMONSTRATED -- p={prim['p']:.4f}, observed difference "
                  f"{prim['diff']:+.2f} points.")
            if mde:
                print(f"  This design could only have detected a shift of >= {mde} "
                      f"points\n  with 80% power at n={len(a)}/{len(b)}. A smaller "
                      "real effect would be invisible here.")
                print("  So this is NOT evidence that the retrieval win is absent.")
            else:
                print("  Minimum detectable effect exceeds the 10-point scale: this "
                      "design\n  has essentially no power. Read more videos.")

    # ---- declared sensitivity analyses (see AMENDMENT in the module docstring)
    prim_fn = outcomes["max(S,B) [PRIMARY]"]
    out["sensitivity"] = {}

    def run_sens(label, a_rows, b_rows, note):
        a = [prim_fn(r) for r in a_rows]
        b = [prim_fn(r) for r in b_rows]
        if len(a) < 3 or len(b) < 3:
            print(f"    {label:<26} NOT RUN (n={len(a)}/{len(b)}, need >=3 each)")
            out["sensitivity"][label] = {"status": "NOT_RUN",
                                         "n_insider": len(a), "n_beginner": len(b)}
            return
        t = perm_test(a, b)
        e = rank_biserial(a, b)
        out["sensitivity"][label] = {
            "n_insider": len(a), "n_beginner": len(b),
            "insider_mean": round(mean(a), 3), "beginner_mean": round(mean(b), 3),
            "diff": round(t["diff"], 3), "p": round(t["p"], 5),
            "rank_biserial": round(e, 3), "note": note,
        }
        print(f"    {label:<26} n={len(a):>2}/{len(b):<2} "
              f"insider {mean(a):>5.2f}  beginner {mean(b):>5.2f}  "
              f"diff {t['diff']:>+5.2f}  p={t['p']:.4f}")

    print("\n  DECLARED SENSITIVITY ANALYSES (primary above is unchanged):")

    # 1 -- stratified only: removes the anchor block and the longest-video pick,
    #      both of which entered the read set by a rule unrelated to family.
    run_sens("1. stratified only",
             [r for r in A if r["selection_rule"] == "stratified"],
             [r for r in B if r["selection_rule"] == "stratified"],
             "anchor and longest rows dropped")

    # 2 -- one observation per channel. Three videos by one creator share a house
    #      style and an honesty profile; they are not three independent draws.
    def by_channel(rows_):
        acc = {}
        for r in rows_:
            acc.setdefault(r["channel_name"], []).append(prim_fn(r))
        return [{"channel_name": c, "s_total": mean(v), "b_total": 0,
                 "h_total": 0, "verdict": "", "selection_rule": "stratified"}
                for c, v in acc.items()]

    ca, cb = by_channel(A), by_channel(B)
    if len(ca) >= 3 and len(cb) >= 3:
        a = [r["s_total"] for r in ca]
        b = [r["s_total"] for r in cb]
        t = perm_test(a, b)
        out["sensitivity"]["2. one row per channel"] = {
            "n_insider_channels": len(a), "n_beginner_channels": len(b),
            "insider_mean": round(mean(a), 3), "beginner_mean": round(mean(b), 3),
            "diff": round(t["diff"], 3), "p": round(t["p"], 5),
        }
        print(f"    {'2. one row per channel':<26} n={len(a):>2}/{len(b):<2} "
              f"insider {mean(a):>5.2f}  beginner {mean(b):>5.2f}  "
              f"diff {t['diff']:>+5.2f}  p={t['p']:.4f}")
    else:
        print(f"    {'2. one row per channel':<26} NOT RUN "
              f"(channels {len(ca)}/{len(cb)}, need >=3 each)")
        out["sensitivity"]["2. one row per channel"] = {
            "status": "NOT_RUN", "n_insider_channels": len(ca),
            "n_beginner_channels": len(cb)}

    ps = [v.get("p") for v in out["sensitivity"].values() if v.get("p") is not None]
    if ps and out.get("status") == "CASHED_OUT" and any(p >= 0.05 for p in ps):
        out["status"] = "CASHED_OUT_BUT_NOT_ROBUST"
        print("\n  *** The primary test cleared 0.05 and at least one declared "
              "sensitivity did not.\n      Per the amendment, the conservative "
              "reading governs: NOT ROBUST.")

    # descriptive, always printed -- MULTI included
    print("\n  descriptive means by bucket (no test, MULTI included):")
    print(f"    {'bucket':<10}{'n':>4}{'max(S,B)':>10}{'S':>7}{'B':>7}{'H':>7}"
          f"{'%notSKIP':>10}")
    for g, xs in groups.items():
        if not xs:
            continue
        m = [max(r["s_total"] or 0, r["b_total"] or 0) for r in xs]
        print(f"    {g:<10}{len(xs):>4}{mean(m):>10.2f}"
              f"{mean([r['s_total'] or 0 for r in xs]):>7.2f}"
              f"{mean([r['b_total'] or 0 for r in xs]):>7.2f}"
              f"{mean([r['h_total'] or 0 for r in xs]):>7.2f}"
              f"{100*mean([1.0 if r['verdict'] != 'SKIP' else 0.0 for r in xs]):>9.0f}%")
    return out


def main():
    con = db_phase2.connect()
    a = part_a(con)
    b = part_b(con)
    p = ROOT / "reports" / "retrieval_payoff.json"
    p.write_text(json.dumps({"part_a": a, "part_b": b}, indent=2), encoding="utf-8")
    print(f"\nwrote {p}")
    con.close()


if __name__ == "__main__":
    main()
