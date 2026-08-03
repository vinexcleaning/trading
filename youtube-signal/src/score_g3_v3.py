"""Score the Phase 2 (v3) G3 lexicon against every video judged by hand so far.

64 videos: the 40-video first sample plus the 24-video holdout. Both sets were
judged under the SAME boundary Phase 2 has now made official -- discretionary,
manual trading education counted as off topic -- so they are a valid test of the
new rule, not a rewrite of the old one.

Contamination warning, stated up front: sample 1 was used to find v2's bugs and
both samples informed v3's design. Neither is a clean holdout for v3 any more.
The honest reading is that these numbers are an upper bound and a fresh sample is
needed for a true one.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gates  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FILES = [
    ("sample1 (used to fix v2 -- contaminated)", ROOT / "reports" / "g3_validation.json"),
    ("holdout (clean for v2, informs v3)", ROOT / "reports" / "g3_validation_holdout.json"),
]


def score(items, label):
    tp = fp = fn = tn = 0
    misses = []
    for it in items:
        truth = bool(it["llm_says_on_topic"])
        pred, ev = gates.g3_on_topic(it["title"], it["head_500_words"])
        if pred and truth:
            tp += 1
        elif pred and not truth:
            fp += 1
            misses.append(("FP", it, ev))
        elif not pred and truth:
            fn += 1
            misses.append(("FN", it, ev))
        else:
            tn += 1
    n = tp + fp + fn + tn
    agree = tp + tn
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    print(f"\n{label}")
    print(f"  n={n}  agreement {agree}/{n} ({100*agree/n:.1f}%)")
    print(f"  TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"  precision {prec:.3f}" if prec is not None else "  precision n/a", end="")
    print(f"   recall {rec:.3f}" if rec is not None else "   recall n/a")
    for kind, it, ev in misses:
        print(f"    {kind} {it['video_id']}  {it['title'][:52]}")
        print(f"        rule: {ev['rule']}")
    return {"n": n, "agreement": agree, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": prec, "recall": rec}


out = {}
allitems = []
for label, path in FILES:
    items = [i for i in json.loads(path.read_text(encoding="utf-8"))
             if i.get("llm_says_on_topic") is not None]
    out[label] = score(items, label)
    allitems += items

print("\n" + "=" * 70)
out["combined (all 64 hand-judged)"] = score(allitems, "COMBINED -- all 64 hand-judged videos")

print("\n" + "=" * 70)
print("v2 -> v3 comparison, recall is what was being bought:")
print("  v2 holdout : agreement 79.2%  precision 0.833  recall 0.769")
h = out["holdout (clean for v2, informs v3)"]
print(f"  v3 holdout : agreement {100*h['agreement']/h['n']:.1f}%  "
      f"precision {h['precision']:.3f}  recall {h['recall']:.3f}")

(ROOT / "reports" / "g3_v3_score.json").write_text(
    json.dumps(out, indent=2), encoding="utf-8")
print(f"\nwrote {ROOT / 'reports' / 'g3_v3_score.json'}")
