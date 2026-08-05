"""TASK 1 - run the rubric against known answers and report where it fails.

Three instruments are measured against the same 24-case labelled set:

  A  PIPELINE   the verdict the current pipeline actually RECORDED. For
                youtube-signal that is a model read routed through
                `read_video.verdict`; for social-signal it is the lexicon.
                This is the instrument as deployed.
  B  LEXICON    `social-signal/src/rubric.py` run uniformly on every case's
                text. This is the portable instrument - the one that scales to
                a corpus nobody will ever read.
  C  V2         the fix, `rubric_v2.py`, run on the same text.

A is not comparable to B case-for-case (different readers), so both are
reported against ground truth separately rather than against each other.

The scoring:

  exact       predicted action == ground-truth action
  MAE         mean |rank(pred) - rank(gt)| on REJECT<DISCOUNT<ABSORB<RECOMMEND
  FALSE REC   predicted RECOMMEND when the truth is DISCOUNT, REJECT or STALE.
              The costly error: it hands a bad thing to a reader as good.
  FALSE REJ   predicted REJECT when the truth is ABSORB or RECOMMEND.
              The cheap error: it loses good content silently.
  STALE       of the cases that teach a dead path, how many were flagged.

    python src/validate_rubric.py [--v2]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cases as CS            # noqa: E402
import corpora                # noqa: E402

REPORTS = corpora.REPORTS
REPORTS.mkdir(exist_ok=True)


# ------------------------------------------------------------------ scoring

def action_of(verdict: str | None) -> str | None:
    if verdict is None:
        return None
    v = verdict.split(" ", 1)[0].strip().rstrip("-").strip()
    return CS.VERDICT_TO_ACTION.get(v) or CS.VERDICT_TO_ACTION.get(verdict)


def evaluate(name, preds, stale_flags=None):
    """preds: {cid: action or None}. stale_flags: {cid: bool} or None."""
    rows, exact, total, abserr = [], 0, 0, 0
    false_rec, false_rej, missing = [], [], []
    mat = defaultdict(Counter)
    for c in CS.CASES:
        p = preds.get(c.cid)
        if p is None:
            missing.append(c.cid)
            continue
        total += 1
        mat[c.gt_action][p] += 1
        d = c.distance(p)
        abserr += d
        if c.accepts(p):
            exact += 1
        # The two errors that decide anything. Both are judged against the
        # band's edges, so widening a band can never manufacture a pass here.
        hi = c.band[1] if c.band else c.gt_action
        lo = c.band[0] if c.band else c.gt_action
        if p == "RECOMMEND" and (hi != "RECOMMEND" or c.gt_stale):
            false_rec.append(c.cid)
        if p == "REJECT" and CS.ACTION_RANK[lo] >= 2:
            false_rej.append(c.cid)
        rows.append((c, p, d))

    stale_cases = [c.cid for c in CS.CASES if c.gt_stale]
    stale_caught = ([cid for cid in stale_cases if (stale_flags or {}).get(cid)]
                    if stale_flags is not None else [])
    return {
        "name": name, "rows": rows, "matrix": mat, "n": total,
        "exact": exact, "acc": exact / total if total else 0.0,
        "mae": abserr / total if total else 0.0,
        "false_recommend": false_rec, "false_reject": false_rej,
        "missing": missing,
        "stale_cases": stale_cases, "stale_caught": stale_caught,
        "stale_measured": stale_flags is not None,
    }


def matrix_md(mat):
    out = ["| truth \\ predicted | " + " | ".join(CS.ACTIONS) + " |",
           "|---|" + "---|" * len(CS.ACTIONS)]
    for gt in CS.ACTIONS:
        row = [f"**{gt}**"]
        for pr in CS.ACTIONS:
            n = mat[gt][pr]
            row.append(f"**{n}**" if n and gt == pr else (str(n) if n else "."))
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


# ------------------------------------------------- component diagnostics

def component_diagnostics():
    """Two questions the brief asks: does any component never fire, or fire on
    everything - and are the components independent or redundant?"""
    pop = corpora.all_scored_components()
    n = len(pop)
    lv = corpora.llm_rubric()
    declared = (list(lv.S_WEIGHTS) + list(lv.B_WEIGHTS) + list(lv.H_WEIGHTS))

    fired = Counter()
    for _, _, comps in pop:
        fired.update(comps)

    rates = {c: fired.get(c, 0) / n for c in declared}

    # Pairwise phi (Matthews) between component indicators, same axis or not.
    import math
    vecs = {c: [1 if c in comps else 0 for _, _, comps in pop] for c in declared}
    pairs = []
    for i, a in enumerate(declared):
        for b in declared[i + 1:]:
            va, vb = vecs[a], vecs[b]
            n11 = sum(1 for x, y in zip(va, vb) if x and y)
            n10 = sum(1 for x, y in zip(va, vb) if x and not y)
            n01 = sum(1 for x, y in zip(va, vb) if not x and y)
            n00 = n - n11 - n10 - n01
            den = math.sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
            if den == 0:
                continue
            phi = (n11 * n00 - n10 * n01) / den
            pairs.append((abs(phi), phi, a, b, n11))
    pairs.sort(reverse=True)
    return {"n": n, "rates": rates, "fired": fired, "declared": declared,
            "top_pairs": pairs[:12]}


def prompt_code_audit():
    """Does the prompt that produces the components declare all of them?

    Checked mechanically against the RUBRIC string rather than asserted.
    """
    lv = corpora.llm_rubric()
    txt = lv.RUBRIC
    declared = list(lv.S_WEIGHTS) + list(lv.B_WEIGHTS) + list(lv.H_WEIGHTS)
    absent = [c for c in declared if c not in txt]
    schema_keys = [k for k in ("s_components", "h_components", "b_components")
                   if k in txt]
    return {"absent_from_prompt": absent, "schema_keys": schema_keys,
            "n_declared": len(declared)}


# ------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2", action="store_true",
                    help="also run rubric_v2 and report the delta")
    args = ap.parse_args()

    lex = corpora.lexicon()

    texts, metas = {}, {}
    for c in CS.CASES:
        try:
            texts[c.cid] = corpora.text_for(c.corpus, c.key)
            metas[c.cid] = corpora.meta_for(c.corpus, c.key)
        except KeyError as e:
            print(f"  !! {c.cid} {e}")

    # --- A: what the pipeline recorded
    a_pred, a_detail = {}, {}
    for c in CS.CASES:
        sv = corpora.stored_verdict(c.corpus, c.key)
        a_detail[c.cid] = sv
        if sv:
            a_pred[c.cid] = action_of(sv.get("verdict"))

    # --- B: the lexicon, uniformly
    b_pred, b_detail = {}, {}
    for c in CS.CASES:
        if c.cid not in texts:
            continue
        s, b, h, comps = lex.score(texts[c.cid])
        v = lex.verdict(s, b, h)
        b_pred[c.cid] = action_of(v)
        b_detail[c.cid] = (s, b, h, v, [x["component"] for x in comps])

    A = evaluate("A - PIPELINE as recorded", a_pred)
    B = evaluate("B - LEXICON on case text", b_pred, stale_flags={})

    C = None
    if args.v2:
        import rubric_v2
        c_pred, c_detail, c_stale = {}, {}, {}
        for c in CS.CASES:
            if c.cid not in texts:
                continue
            r = rubric_v2.score(texts[c.cid], meta=metas.get(c.cid, {}),
                                corpus=c.corpus)
            c_pred[c.cid] = action_of(r["verdict"])
            c_stale[c.cid] = r["stale"]
            c_detail[c.cid] = r
        C = evaluate("C - RUBRIC v2", c_pred, stale_flags=c_stale)

    diag = component_diagnostics()
    audit = prompt_code_audit()

    write_report(A, B, C, b_detail, a_detail,
                 c_detail if args.v2 else None, diag, audit)

    for r in (A, B, C):
        if r:
            print(f"{r['name']:28s} n={r['n']:2d} exact={r['exact']:2d}"
                  f" ({r['acc']:.0%}) MAE={r['mae']:.2f}"
                  f" falseREC={len(r['false_recommend'])}"
                  f" falseREJ={len(r['false_reject'])}"
                  f" stale={len(r['stale_caught'])}/{len(r['stale_cases'])}")


def write_report(A, B, C, b_detail, a_detail, c_detail, diag, audit):
    L = []
    w = L.append
    w("# TASK 1 - the rubric against known answers\n")
    w(f"**{len(CS.CASES)} labelled cases** across four corpora. Every label is "
      "fixed by something outside the rubric: arithmetic on the source's own "
      "numbers (ARITH), a live API check (LIVE), a fact this repo already "
      "primary-sourced (EXTERN), or an internal contradiction (SELFCON). A "
      "case with no such anchor is not in the set.\n")

    w("## The instruments\n")
    w("| | what it is | where it lives |")
    w("|---|---|---|")
    w("| **A PIPELINE** | the verdict actually recorded - a model read routed "
      "through `verdict()` for video, the lexicon for Reddit, a hand read for "
      "GitHub | `scores` / `rd_scores` / `repos` |")
    w("| **B LEXICON** | the mechanical proxy run uniformly on every case's "
      "text | `social-signal/src/rubric.py` |")
    if C:
        w("| **C V2** | the fix | `extractor-upgrade/src/rubric_v2.py` |")
    w("")
    w("> Neither rubric was copied. Both are imported from where they live, so "
      "this file cannot drift into a private fork of an instrument it is "
      "supposed to be testing.\n")

    for r in (A, B, C):
        if not r:
            continue
        w(f"## {r['name']}\n")
        w(f"**exact {r['exact']}/{r['n']} = {r['acc']:.0%} · "
          f"mean ordinal error {r['mae']:.2f} · "
          f"false RECOMMEND {len(r['false_recommend'])} · "
          f"false REJECT {len(r['false_reject'])}**\n")
        if r["missing"]:
            w(f"Not scored by this instrument: {', '.join(r['missing'])}\n")
        w(matrix_md(r["matrix"]))
        w("")
        if r["false_recommend"]:
            w(f"**Recommended something it should not have:** "
              f"{', '.join(r['false_recommend'])} - "
              + "; ".join(CS.BY_ID[c].label for c in r["false_recommend"]) + "\n")
        if r["false_reject"]:
            w(f"**Rejected something worth keeping:** "
              f"{', '.join(r['false_reject'])} - "
              + "; ".join(CS.BY_ID[c].label for c in r["false_reject"]) + "\n")
        if r["stale_measured"]:
            w(f"**Staleness:** {len(r['stale_caught'])} of "
              f"{len(r['stale_cases'])} cases that teach a dead path were "
              "flagged.\n")
        else:
            w(f"**Staleness: 0 of {len(r['stale_cases'])} - not by failure but "
              "by construction. No component in this instrument asks whether "
              "the thing being taught still exists.**\n")

    w("## Case by case\n")
    w("`truth` is a band where the outside evidence fixes a bound rather than "
      "a point; the reasons are tabled below. A wider band can never turn a "
      "false RECOMMEND or a false REJECT into a pass, because both are judged "
      "against the band's own edges.\n")
    w("| case | class | truth | A pipeline | B lexicon"
      + (" | C v2" if C else "") + " | why the truth is known |")
    w("|---|---|---|---|---|" + ("---|" if C else ""))
    for c in CS.CASES:
        a = a_detail.get(c.cid)
        av = (a or {}).get("verdict", "")
        av = (av or "")[:26]
        bd = b_detail.get(c.cid)
        bs = f"S{bd[0]} B{bd[1]} H{bd[2]} {bd[3]}" if bd else "-"
        row = [c.cid, c.gt_class, c.band_str, av or "-", bs]
        if C:
            cd = (c_detail or {}).get(c.cid)
            row.append(f"S{cd['s']} B{cd['b']} H{cd['h']} "
                       f"{'STALE ' if cd['stale'] else ''}{cd['verdict']}"
                       if cd else "-")
        row.append(c.why)
        w("| " + " | ".join(row) + " |")
    w("")
    w("### The banded labels, and what fixes each bound\n")
    w("| case | band | what the outside evidence actually fixes |")
    w("|---|---|---|")
    for cid, why in CS.BAND_REASON.items():
        w(f"| {cid} | {CS.BY_ID[cid].band_str} | {why} |")
    w(f"\n{len(CS.BAND_REASON)} of {len(CS.CASES)} labels are banded; "
      f"{len(CS.CASES) - len(CS.BAND_REASON)} are points.\n")

    w("## Component diagnostics - dead weight and redundancy\n")
    w(f"Measured on **all {diag['n']} videos the model rubric has read**, not "
      "on the test cases. A fire rate measured on cases chosen for being "
      "interesting is not a fire rate.\n")
    w("| component | fires on | rate | reading |")
    w("|---|---|---|---|")
    for comp in diag["declared"]:
        n = diag["fired"].get(comp, 0)
        rate = diag["rates"][comp]
        if n == 0:
            note = "**DEAD - never fires**"
        elif rate >= 0.85:
            note = "**near-universal - carries almost no information**"
        elif rate <= 0.10:
            note = "very rare"
        else:
            note = ""
        w(f"| {comp} | {n}/{diag['n']} | {rate:.0%} | {note} |")
    w("")
    w("### Are the components independent?\n")
    w("Pairwise phi (Matthews) between component indicators, |phi| ranked. "
      f"n={diag['n']}, so nothing here is significant on its own - it is a "
      "redundancy screen, not a hypothesis test.\n")
    w("| a | b | phi | co-fire |")
    w("|---|---|---|---|")
    for _, phi, a, b, n11 in diag["top_pairs"]:
        w(f"| {a} | {b} | {phi:+.2f} | {n11} |")
    w("")

    w("### The prompt does not declare every component the code scores\n")
    w(f"Checked mechanically against the `RUBRIC` string in "
      f"`youtube-signal/src/read_video.py`. Of {audit['n_declared']} components "
      f"the code assigns weights to, **{len(audit['absent_from_prompt'])} never "
      f"appear in the prompt at all**: "
      f"`{', '.join(audit['absent_from_prompt']) or 'none'}`.\n")
    w(f"The JSON schema the prompt asks for contains "
      f"`{', '.join(audit['schema_keys'])}`.\n")

    w("## Cases in the brief that are not in this repo\n")
    for claim, finding in CS.MISSING_FROM_BRIEF:
        w(f"- **{claim}** - {finding}")
    w("")

    (REPORTS / "T1_rubric_validation.md").write_text("\n".join(L),
                                                     encoding="utf-8")
    payload = {"A": {k: v for k, v in A.items() if k != "rows" and k != "matrix"},
               "B": {k: v for k, v in B.items() if k != "rows" and k != "matrix"},
               "C": ({k: v for k, v in C.items() if k not in ("rows", "matrix")}
                     if C else None),
               "component_rates": diag["rates"], "n_pop": diag["n"],
               "prompt_audit": audit}
    (REPORTS / "T1_rubric_validation.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8")
    print(f"  wrote {REPORTS / 'T1_rubric_validation.md'}")


if __name__ == "__main__":
    main()
