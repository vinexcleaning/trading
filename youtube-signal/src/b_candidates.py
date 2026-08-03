"""Surface VERBATIM candidate evidence for the B (Build) axis from cached transcripts.

Why this exists rather than re-reading 18 transcripts:

The evidence rule requires a real timestamp and a verbatim quote under 15 words.
Claim text in the extraction files is PARAPHRASE, so it cannot be used as a quote --
scoring B from it would mean inventing evidence, which is the exact failure the
rule exists to prevent.

So the transcript is searched for phrases that would accompany each B component,
and short verbatim windows are printed with their real timestamps. A human (or
Claude) then judges which candidates actually evidence the component. The machine
finds quotes; the judgment stays with the reader.

A candidate is not a score. Several videos will have B1-looking language and no
code on screen at all.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db_phase2  # noqa: E402

PATTERNS = {
    "B1_code_shown": [
        r"\bline[s]? of code\b", r"\bhere'?s the code\b", r"\byou'?ll see (?:i|we) have\b",
        r"\bimport\b", r"\bdef \b", r"\bthe script\b", r"\bthis function\b",
        r"\bwalk (?:you )?through the code\b", r"\bopen (?:up )?(?:my|the) (?:editor|ide)\b",
    ],
    "B2_endpoints": [
        r"\bendpoint\b", r"\bapi call\b", r"\bget request\b", r"\bpost request\b",
        r"\bparameter[s]?\b", r"\breturns? a json\b", r"\bwebsocket\b",
        r"\bcall(?:ing)? the [a-z ]{0,12}api\b", r"\bpayload\b",
    ],
    "B3_full_path": [
        r"\bapi key\b", r"\bprivate key\b", r"\bauthenticat", r"\bpip install\b",
        r"\bnpm install\b", r"\b\.env\b", r"\brequirements\.txt\b",
        r"\bvirtual environment\b", r"\bsign(?:ing)? the (?:order|request)\b",
        r"\bplace (?:an|the) order\b",
    ],
    "B4_gotcha": [
        r"\bthe problem is\b", r"\bdoesn'?t work\b", r"\bwon'?t work\b",
        r"\byou have to\b", r"\bbe careful\b", r"\bthe trick\b", r"\bgotcha\b",
        r"\brate limit\b", r"\bthrow[s]? an error\b", r"\bfail(?:s|ed)\b",
        r"\bkeep in mind\b", r"\bthe catch\b", r"\bonly works if\b",
    ],
    "B5_artifact": [
        r"\bgithub\b", r"\brepo(?:sitory)?\b", r"\blink in the description\b",
        r"\bdownload the code\b", r"\bclone\b", r"\bopen source\b",
    ],
}
COMPILED = {k: [re.compile(p, re.I) for p in v] for k, v in PATTERNS.items()}
MAX_WORDS = 14


def window(text, m):
    """A <15-word verbatim window centred on the match."""
    words = text.split()
    hit = len(text[:m.start()].split())
    lo = max(0, hit - 4)
    return " ".join(words[lo:lo + MAX_WORDS])


def main():
    con = db_phase2.connect()
    only = sys.argv[1:] or None
    q = ("SELECT s.video_id, v.title, v.channel_name, v.duration_s, s.s_total,"
         " s.h_total, COALESCE(s.b_total,0) b_total, s.verdict, t.snippets_json"
         " FROM scores s JOIN videos v ON v.video_id=s.video_id"
         " JOIN transcripts t ON t.video_id=s.video_id ORDER BY s.video_id")
    for r in con.execute(q):
        if only and r["video_id"] not in only:
            continue
        if r["b_total"]:
            continue  # already scored on B
        snips = json.loads(r["snippets_json"])
        found = {}
        for comp, regs in COMPILED.items():
            hits = []
            for s in snips:
                txt = s["text"]
                for rg in regs:
                    m = rg.search(txt)
                    if m:
                        hits.append((int(s["start"]), window(txt, m)))
                        break
                if len(hits) >= 2:
                    break
            if hits:
                found[comp] = hits
        print("=" * 76)
        print(f"{r['video_id']}  S={r['s_total']} H={r['h_total']} "
              f"{(r['duration_s'] or 0)/60:.0f}min  {r['verdict']}")
        print(f"  {r['channel_name']} — {(r['title'] or '')[:56]}")
        for comp in PATTERNS:
            if comp in found:
                for t, w in found[comp][:2]:
                    print(f"    {comp:<16} [{t}] {w[:74]}")
            else:
                print(f"    {comp:<16} --")
    con.close()


if __name__ == "__main__":
    main()
