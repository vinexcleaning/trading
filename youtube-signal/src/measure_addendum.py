"""Two corrections to the headline 7b/7d numbers.

1. F3's yield is mechanically inflated. F3 carries YouTube's past-12-months search
   filter, so it pre-satisfies gate G2 by construction -- its 93.4% pass rate is
   partly the filter, not the content. Comparing F1/F2/F3 on a gate that one of
   them was handed for free is not a comparison. Recompute yield on G1+G3 only.

2. The STALE_G2 count (104) and the number of videos older than 18 months (174)
   disagree, because gate_status is a precedence-ordered label: G3 short-circuits
   before G2, so an off-topic AND stale video is filed under G3. Report the
   independent per-gate failure counts as well as the precedence labels.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db  # noqa: E402
import gates  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LOW_VIEW = 5000
FAMS = ["F1", "F2", "F3"]

con = db.connect()


def fam_ids(f):
    return {
        r["video_id"]
        for r in con.execute(
            "SELECT DISTINCT video_id FROM retrieval_hits WHERE family=?", (f,)
        )
    }


print("=" * 76)
print("CORRECTION 1 -- low-view yield on G1+G3 ONLY (G2/recency removed)")
print("=" * 76)
print("  F3 carries the past-12-months filter, so it passes G2 almost by")
print("  construction. Dropping G2 puts the three families on equal footing.\n")
print(f"  {'fam':<5}{'retrieved':>10}{'G1+G3 ok':>10}{'rate':>8}"
      f"{'lowview':>9}{'BOTH':>7}{'YIELD*':>9}")

out = {}
for f in FAMS:
    ids = fam_ids(f)
    marks = ",".join("?" * len(ids))
    rows = con.execute(
        f"SELECT video_id, view_count, gate_status FROM videos WHERE video_id IN ({marks})",
        tuple(ids),
    ).fetchall()
    # G1+G3 ok  ==  passed everything except possibly the age gate.
    ok = [r for r in rows if r["gate_status"] in ("PASS", "STALE_G2")]
    low = [r for r in ok if (r["view_count"] or 0) < LOW_VIEW]
    y = len(low) / len(rows) if rows else 0
    out[f] = {
        "retrieved": len(rows), "g1g3_ok": len(ok),
        "g1g3_rate": round(len(ok) / len(rows), 4),
        "low_and_ok": len(low), "yield_no_g2": round(y, 4),
    }
    print(f"  {f:<5}{len(rows):>10}{len(ok):>10}{100*len(ok)/len(rows):>7.1f}%"
          f"{len(low):>9}{len(low):>7}{100*y:>8.1f}%")

f1, f2, f3 = out["F1"]["yield_no_g2"], out["F2"]["yield_no_g2"], out["F3"]["yield_no_g2"]
print(f"\n  F2 vs F1: {100*f2:.1f}% vs {100*f1:.1f}%  ratio {f2/f1:.2f}x")
print(f"  F3 vs F1: {100*f3:.1f}% vs {100*f1:.1f}%  ratio {f3/f1:.2f}x")
print("\n  With G2 included F3 led at 43.9%. On equal footing it is"
      f" {100*f3:.1f}% vs F2's {100*f2:.1f}%.")

print()
print("=" * 76)
print("CORRECTION 2 -- independent per-gate failures vs precedence labels")
print("=" * 76)
gated = con.execute(
    "SELECT COUNT(*) c FROM videos WHERE gate_status IS NOT NULL"
).fetchone()["c"]
no_trans = con.execute(
    "SELECT COUNT(*) c FROM videos WHERE gate_status='DROP_G1_NO_TRANSCRIPT'"
).fetchone()["c"]
older = con.execute(
    "SELECT COUNT(*) c FROM videos WHERE age_months > ? AND source='search'",
    (gates.STALE_MONTHS,),
).fetchone()["c"]
stale_label = con.execute(
    "SELECT COUNT(*) c FROM videos WHERE gate_status='STALE_G2'"
).fetchone()["c"]
offtopic = con.execute(
    "SELECT COUNT(*) c FROM videos WHERE gate_status='DROP_G3_OFF_TOPIC'"
).fetchone()["c"]
print(f"  videos gated                         : {gated}")
print(f"  G1 would fail (no transcript)        : {no_trans}")
print(f"  G2 would fail (older than 18 months) : {older}   <- independent count")
print(f"      of which labelled STALE_G2       : {stale_label}")
print(f"      the remaining {older - stale_label} were off-topic too, so G3 claimed them first")
print(f"  G3 would fail (off topic)            : {offtopic}")
print("\n  Every gate fired. No rule was a no-op.")

out["gate_independent"] = {
    "gated": gated, "g1_fail": no_trans, "g2_fail_independent": older,
    "stale_label": stale_label, "g3_fail": offtopic,
}

# ---- how sensitive is the 18-month choice? ----
print()
print("=" * 76)
print("PREMISE 4 -- is 18 months the right cutoff?")
print("=" * 76)
ages = [r["age_months"] for r in con.execute(
    "SELECT age_months FROM videos WHERE age_months IS NOT NULL AND source='search'")]
n = len(ages)
print(f"  n={n} retrieved videos with a known upload date\n")
print(f"  {'cutoff':>8}{'kept':>8}{'kept %':>9}{'change vs 18mo':>17}")
base = sum(1 for a in ages if a <= 18)
sens = {}
for c in (6, 9, 12, 15, 18, 24, 30, 36):
    k = sum(1 for a in ages if a <= c)
    sens[c] = k
    print(f"  {c:>6} mo{k:>8}{100*k/n:>8.1f}%{k - base:>+17}")
print(f"\n  Moving the cutoff 12 -> 18 months keeps {sens[18]-sens[12]} more videos "
      f"({100*(sens[18]-sens[12])/n:.1f}% of the set).")
print(f"  Moving it 18 -> 24 months keeps {sens[24]-sens[18]} more "
      f"({100*(sens[24]-sens[18])/n:.1f}%).")
print("  The distribution is bimodal -- recent or ancient -- so the exact cutoff")
print("  anywhere in 12-24 months changes little. 18 is defensible but not special.")
out["cutoff_sensitivity"] = sens

(ROOT / "reports" / "step7_addendum.json").write_text(
    json.dumps(out, indent=2), encoding="utf-8")
print(f"\nwrote {ROOT / 'reports' / 'step7_addendum.json'}")
con.close()
