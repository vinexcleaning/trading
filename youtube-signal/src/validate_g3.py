"""Validate the G3 lexicon classifier against an actual LLM judgment.

The brief specifies an LLM yes/no for G3. There is no LLM API key on this machine,
so G3 is a deterministic lexicon classifier (see src/gates.py). A gate whose error
rate is unknown is not a gate, so this script draws a stratified sample, prints
exactly what the classifier saw (title + first 500 transcript words) plus which
terms fired, and writes a JSON stub for the LLM verdicts.

Agreement is then computed by --score against the filled-in stub. Sampling is
seeded so the sample is reproducible.
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
STUB = ROOT / "reports" / "g3_validation.json"
N_PER_STRATUM = 20
SEED = 20260802


def sample():
    con = db.connect()
    rnd = random.Random(SEED)
    strata = {
        "classified_on_topic": "gate_status IN ('PASS','STALE_G2')",
        "classified_off_topic": "gate_status = 'DROP_G3_OFF_TOPIC'",
    }
    items = []
    for label, where in strata.items():
        rows = con.execute(
            f"""SELECT v.video_id, v.title, v.view_count, v.gate_status, t.snippets_json
                FROM videos v JOIN transcripts t ON t.video_id = v.video_id
                WHERE {where}"""
        ).fetchall()
        rows = list(rows)
        rnd.shuffle(rows)
        for r in rows[:N_PER_STRATUM]:
            snips = json.loads(r["snippets_json"])
            head = gates.head_words(snips, 500)
            _, ev = gates.g3_on_topic(r["title"], head)
            items.append({
                "video_id": r["video_id"],
                "stratum": label,
                "classifier_says_on_topic": ev["decision"],
                "classifier_rule": ev["rule"],
                "terms_fired": {"core": ev["core"], "context": ev["context"],
                                "method": ev["method"], "negative": ev["negative"]},
                "title": r["title"],
                "views": r["view_count"],
                "head_500_words": head,
                "llm_says_on_topic": None,   # <- to be filled in
            })
    con.close()
    rnd.shuffle(items)
    STUB.write_text(json.dumps(items, indent=2), encoding="utf-8")
    print(f"wrote {len(items)} sampled videos to {STUB}\n")
    for i, it in enumerate(items):
        print("=" * 78)
        print(f"[{i}] {it['video_id']}   classifier={it['classifier_says_on_topic']}"
              f"  ({it['classifier_rule']})")
        print(f"     TITLE: {it['title']}")
        fired = {k: v for k, v in it["terms_fired"].items() if v}
        print(f"     FIRED: {fired}")
        print(textwrap.fill(it["head_500_words"][:900], width=76,
                            initial_indent="     ", subsequent_indent="     "))


def score():
    items = json.loads(STUB.read_text(encoding="utf-8"))
    judged = [i for i in items if i["llm_says_on_topic"] is not None]
    if not judged:
        print("no llm_says_on_topic values filled in yet")
        return
    agree = sum(
        1 for i in judged if bool(i["llm_says_on_topic"]) == bool(i["classifier_says_on_topic"])
    )
    # Treat the LLM judgment as truth.
    tp = sum(1 for i in judged if i["llm_says_on_topic"] and i["classifier_says_on_topic"])
    fp = sum(1 for i in judged if not i["llm_says_on_topic"] and i["classifier_says_on_topic"])
    fn = sum(1 for i in judged if i["llm_says_on_topic"] and not i["classifier_says_on_topic"])
    tn = sum(1 for i in judged if not i["llm_says_on_topic"] and not i["classifier_says_on_topic"])
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    print(f"n judged            : {len(judged)}")
    print(f"agreement           : {agree}/{len(judged)} ({100*agree/len(judged):.1f}%)")
    print(f"confusion (LLM=truth): TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"precision           : {prec:.3f}" if prec is not None else "precision: n/a")
    print(f"recall              : {rec:.3f}" if rec is not None else "recall: n/a")
    print("\ndisagreements:")
    for i in judged:
        if bool(i["llm_says_on_topic"]) != bool(i["classifier_says_on_topic"]):
            print(f"  {i['video_id']}  classifier={i['classifier_says_on_topic']} "
                  f"llm={i['llm_says_on_topic']}  {i['title'][:58]}")
    out = {"n_judged": len(judged), "agreement": agree,
           "agreement_rate": round(agree / len(judged), 4),
           "tp": tp, "fp": fp, "fn": fn, "tn": tn,
           "precision": prec, "recall": rec}
    (ROOT / "reports" / "g3_validation_score.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {ROOT / 'reports' / 'g3_validation_score.json'}")


if __name__ == "__main__":
    score() if "--score" in sys.argv else sample()
