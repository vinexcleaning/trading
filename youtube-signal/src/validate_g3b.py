"""Honest re-validation of the FIXED G3 classifier.

The first 40-video sample was used to FIND the two bugs (plural matching, and
walk-forward education firing no core term). Re-scoring the fixed classifier on
that same sample would be circular -- it was tuned to it.

This draws a fresh sample, different seed, explicitly EXCLUDING every video in the
first sample, so the post-fix number is measured on data the fix never saw.
"""

import json
import random
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db  # noqa: E402
import gates  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIRST = ROOT / "reports" / "g3_validation.json"
STUB = ROOT / "reports" / "g3_validation_holdout.json"
N_PER_STRATUM = 12
SEED = 777


def sample():
    seen = {i["video_id"] for i in json.loads(FIRST.read_text(encoding="utf-8"))}
    con = db.connect()
    rnd = random.Random(SEED)
    strata = {
        "classified_on_topic": "v.gate_status IN ('PASS','STALE_G2')",
        "classified_off_topic": "v.gate_status = 'DROP_G3_OFF_TOPIC'",
    }
    items = []
    for label, where in strata.items():
        rows = [
            r for r in con.execute(
                f"""SELECT v.video_id, v.title, v.view_count, v.gate_status,
                           t.snippets_json
                    FROM videos v JOIN transcripts t ON t.video_id=v.video_id
                    WHERE {where}"""
            ) if r["video_id"] not in seen
        ]
        rnd.shuffle(rows)
        for r in rows[:N_PER_STRATUM]:
            snips = json.loads(r["snippets_json"])
            head = gates.head_words(snips, 500)
            _, ev = gates.g3_on_topic(r["title"], head)
            items.append({
                "video_id": r["video_id"], "stratum": label,
                "classifier_says_on_topic": ev["decision"],
                "classifier_rule": ev["rule"],
                "terms_fired": {k: ev[k] for k in ("core", "context", "method", "negative")},
                "title": r["title"], "views": r["view_count"],
                "head_500_words": head, "llm_says_on_topic": None,
            })
    con.close()
    rnd.shuffle(items)
    STUB.write_text(json.dumps(items, indent=2), encoding="utf-8")
    print(f"HOLDOUT sample: {len(items)} videos, none in the first sample\n")
    for i, it in enumerate(items):
        print("=" * 74)
        print(f"[{i}] {it['video_id']}  classifier={it['classifier_says_on_topic']}"
              f"  ({it['classifier_rule']})")
        print(f"    TITLE: {it['title']}")
        print(f"    CORE: {it['terms_fired']['core']}")
        print(textwrap.fill(it["head_500_words"][:300], width=74,
                            initial_indent="    ", subsequent_indent="    "))


def score():
    items = json.loads(STUB.read_text(encoding="utf-8"))
    j = [i for i in items if i["llm_says_on_topic"] is not None]
    if not j:
        print("no judgments filled in")
        return
    agree = sum(1 for i in j
                if bool(i["llm_says_on_topic"]) == bool(i["classifier_says_on_topic"]))
    tp = sum(1 for i in j if i["llm_says_on_topic"] and i["classifier_says_on_topic"])
    fp = sum(1 for i in j if not i["llm_says_on_topic"] and i["classifier_says_on_topic"])
    fn = sum(1 for i in j if i["llm_says_on_topic"] and not i["classifier_says_on_topic"])
    tn = sum(1 for i in j if not i["llm_says_on_topic"] and not i["classifier_says_on_topic"])
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    print(f"HOLDOUT n={len(j)}  agreement {agree}/{len(j)} ({100*agree/len(j):.1f}%)")
    print(f"  TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"  precision {prec if prec is None else round(prec,3)}   "
          f"recall {rec if rec is None else round(rec,3)}")
    for i in j:
        if bool(i["llm_says_on_topic"]) != bool(i["classifier_says_on_topic"]):
            print(f"  MISS {i['video_id']} clf={i['classifier_says_on_topic']} "
                  f"llm={i['llm_says_on_topic']}  {i['title'][:56]}")
    (ROOT / "reports" / "g3_holdout_score.json").write_text(json.dumps(
        {"n": len(j), "agreement": agree, "agreement_rate": round(agree/len(j), 4),
         "tp": tp, "fp": fp, "fn": fn, "tn": tn,
         "precision": prec, "recall": rec}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    score() if "--score" in sys.argv else sample()
