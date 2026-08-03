"""The read shortlist: substance AND credibility, because neither alone works.

Three independent axes now exist, and this session demonstrated that each one
alone picks something the others reject:

  s_adj        substance, with repository size removed (src/size_adjust.py).
               Validated against the fee audit: it surfaces repos that provably
               model Kalshi's maker fee correctly, where the raw score put zero
               of them in its top 25.
               BUT its own #1 pick, hcharper/polyBot-Weather, has ONE commit and
               a README claiming "Guaranteed profit".

  trust_me_bro a results claim in the README, under 10 commits, no artifact.
               Fires on 20.9% of the corpus - against 7.5% in the previous
               session's top-40 slice, which is the measured version of that
               handoff's warning that the corpus is less honest than its top.

  fee audit    does the repo hardcode a venue fee, and is it right? An objective
               fact with a published ground truth, independent of every S
               component (src/fee_audit.py).

Ranking on any one of them is a mistake this session made and caught. The
shortlist below requires substance, then subtracts for the credibility flags,
and shows all three columns so a human can disagree with the ordering.

    python src/shortlist.py [--top 40]
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import gh  # noqa: E402


def main():
    top = 40
    if "--top" in sys.argv:
        top = int(sys.argv[sys.argv.index("--top") + 1])

    con = db.connect()
    cols = {c[1] for c in con.execute("PRAGMA table_info(repos)")}
    for need in ("s_strict", "s_adj"):
        if need not in cols:
            print(f"{need} missing - run src/rescore.py then src/size_adjust.py")
            return

    fee_ok, fee_bad = set(), {}
    fa = os.path.join(gh.ROOT, "reports", "fee_audit.json")
    if os.path.exists(fa):
        for f in json.load(open(fa, encoding="utf-8"))["findings"]:
            v = " ".join(f["verdict"])
            if "maker 0.0175 OK" in v:
                fee_ok.add(f["repo"])
            elif "hardcoded 0" in v or "set to 0.07" in v:
                fee_bad[f["repo"]] = v

    rows = con.execute(
        """SELECT full_name, stars, commits, span_days, contributors, tree_files,
                  s_total, s_strict, s_adj, trust_me_bro, claimed_results, read_at
           FROM repos
           WHERE fetched>=1 AND s_adj IS NOT NULL AND gate IN ('PASS','STALE')
           ORDER BY s_adj DESC""").fetchall()
    print(f"{len(rows)} repos with a size-adjusted score\n")

    scored = []
    for r in rows:
        penalty = 0.0
        why = []
        if r["trust_me_bro"] == 1:
            penalty += 3.0
            why.append("trust_me_bro")
        if (r["commits"] or 99) < 5:
            penalty += 1.5
            why.append(f"{r['commits']} commits")
        if r["full_name"] in fee_bad:
            penalty += 1.0
            why.append("fee model wrong")
        if r["full_name"] in fee_ok:
            penalty -= 1.5
            why.append("fee model CORRECT")
        scored.append((r["s_adj"] - penalty, r, why))

    scored.sort(key=lambda x: -x[0])

    print(f"{'repo':46} {'final':>6} {'s_adj':>6} {'strict':>6} {'cmts':>5} {'stars':>6}  notes")
    for final, r, why in scored[:top]:
        print(f"{r['full_name'][:46]:46} {final:+6.2f} {r['s_adj']:+6.2f} "
              f"{r['s_strict']:6} {str(r['commits'] or '?'):>5} {r['stars']:6}  "
              f"{', '.join(why)}")

    undecided = sum(1 for _f, r, _w in scored if r["trust_me_bro"] is None)
    if undecided:
        print(f"\n{undecided} repos have no credibility data yet (commits NULL) - "
              "their ranking here is substance-only. Run `fetch_repo.py full`.")

    out = os.path.join(gh.ROOT, "reports", "shortlist.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# Read shortlist — substance and credibility together\n\n")
        fh.write("`final = s_adj − 3(trust_me_bro) − 1.5(<5 commits) "
                 "− 1(fee model wrong) + 1.5(fee model correct)`\n\n")
        fh.write("The weights are a judgement, not a measurement. All three "
                 "component columns are shown so the ordering can be disputed.\n\n")
        fh.write("| repo | final | s_adj | strict | commits | stars | notes |\n")
        fh.write("|---|---|---|---|---|---|---|\n")
        for final, r, why in scored[:60]:
            fh.write(f"| {r['full_name']} | {final:+.2f} | {r['s_adj']:+.2f} | "
                     f"{r['s_strict']} | {r['commits'] or '?'} | {r['stars']} | "
                     f"{', '.join(why)} |\n")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
