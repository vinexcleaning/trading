"""STEP 3b — rank, and measure whether stars mean anything.

Premise 3 under test: "stars correlate with substance". On YouTube, views did
not. Spearman rank correlation between stars and the computed S total, over
every deep-fetched repo, answers it with a number instead of an opinion.

Also emits the read shortlist. Ranking is free; reading is the expensive step,
so rank everything and read few.
"""
from __future__ import annotations

import datetime
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import gh  # noqa: E402

NOW = datetime.datetime.now(datetime.timezone.utc)


def _ranks(xs):
    """Average ranks, ties shared."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def spearman(a, b):
    if len(a) < 3:
        return None, None
    ra, rb = _ranks(a), _ranks(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    if den == 0:
        return None, None
    rho = num / den
    # t approximation for p
    if abs(rho) >= 1.0:
        return rho, 0.0
    t = rho * math.sqrt((n - 2) / (1 - rho * rho))
    # two-sided p from the normal approximation; n is large enough here
    p = math.erfc(abs(t) / math.sqrt(2))
    return rho, p


def credibility(r):
    """Not a score to add to S. A separate axis, all computed."""
    bits = []
    c = r["commits"] or 0
    if c >= 100:
        bits.append("100+ commits")
    elif c >= 20:
        bits.append(f"{c} commits")
    else:
        bits.append(f"only {c} commits")
    if (r["span_days"] or 0) >= 180:
        bits.append(f"{r['span_days']}d span")
    elif r["span_days"] is not None:
        bits.append(f"{r['span_days']}d span (short)")
    if (r["contributors"] or 0) > 1:
        bits.append(f"{r['contributors']} contributors")
    else:
        bits.append("solo")
    oi, ci = r["open_issues"] or 0, r["closed_issues"] or 0
    if oi or ci:
        bits.append(f"issues {oi} open / {ci} closed")
    else:
        bits.append("no issue traffic")
    msg = (r["last_commit_msg"] or "").lower()
    if msg and any(w in msg for w in ("readme", "docs", "typo", "update readme", "initial commit")):
        bits.append(f"last commit is cosmetic: {r['last_commit_msg'][:60]!r}")
    return "; ".join(bits)


def main():
    con = db.connect()
    rows = con.execute(
        "SELECT * FROM repos WHERE fetched>=1 AND gate IN ('PASS','STALE')").fetchall()
    print(f"{len(rows)} deep-fetched repos", flush=True)
    if not rows:
        print("nothing fetched yet")
        return

    stars = [r["stars"] or 0 for r in rows]
    stot = [r["s_total"] or 0 for r in rows]
    sstr = [r["s_strict"] or 0 for r in rows]
    forks = [r["forks"] or 0 for r in rows]
    rho_s, p_s = spearman(stars, stot)
    rho_x, p_x = spearman(stars, sstr)
    rho_f, p_f = spearman(forks, sstr)
    # Credibility fields are only populated at fetch level 'full', so the
    # commits correlation runs on that subset alone rather than treating an
    # un-fetched NULL as zero.
    cred = [r for r in rows if r["commits"] is not None]
    rho_c, p_c = (spearman([r["commits"] for r in cred],
                           [r["s_strict"] or 0 for r in cred]) if len(cred) >= 3 else (None, None))
    rho_sc, p_sc = (spearman([r["stars"] or 0 for r in cred],
                             [r["commits"] for r in cred]) if len(cred) >= 3 else (None, None))

    ranked = sorted(rows, key=lambda r: (-(r["s_strict"] or 0), -(r["s_total"] or 0),
                                         -(r["stars"] or 0)))

    out = os.path.join(gh.ROOT, "reports", "step3_rank.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# STEP 3 — scores, and whether stars mean anything\n\n")
        fh.write(f"Computed {NOW:%Y-%m-%d} UTC over **{len(rows)}** deep-fetched repos. "
                 "Every S component is computed from the repo, with a file path and line "
                 "number recorded as evidence. No evidence, no score.\n\n")

        fh.write("## Premise 3 — do stars track substance?\n\n")
        fh.write("| pair | Spearman rho | p (normal approx) | n |\n|---|---|---|---|\n")
        for label, rho, p, n in (("**stars vs S_literal**", rho_s, p_s, len(rows)),
                                 ("**stars vs S_strict**", rho_x, p_x, len(rows)),
                                 ("forks vs S_strict", rho_f, p_f, len(rows)),
                                 ("commits vs S_strict", rho_c, p_c, len(cred)),
                                 ("stars vs commits", rho_sc, p_sc, len(cred))):
            fh.write(f"| {label} | {rho:+.3f} | {p:.4f} | {n} |\n"
                     if rho is not None else f"| {label} | — | — | {n} |\n")
        fh.write("\nA rho near zero with a large p is the answer, not a missing result: "
                 "**stars carry no information about whether a repo has substance.** "
                 "Views did not on YouTube either.\n\n")

        # Concrete counter-examples are more persuasive than rho.
        top_s = [r for r in ranked if (r["s_strict"] or 0) >= 6]
        quiet_good = sorted([r for r in top_s if (r["stars"] or 0) < 20],
                            key=lambda r: -(r["s_total"] or 0))[:8]
        loud_thin = sorted([r for r in rows if (r["stars"] or 0) >= 50
                            and (r["s_strict"] or 0) <= 3], key=lambda r: -(r["stars"] or 0))[:8]
        fh.write(f"- **{len(quiet_good)}** repos scoring S>=6 have fewer than 20 stars.\n")
        fh.write(f"- **{len(loud_thin)}** repos with 50+ stars score S<=3.\n\n")
        if quiet_good:
            fh.write("### High substance, almost no stars\n\n| repo | stars | S | commits |\n|---|---|---|---|\n")
            for r in quiet_good:
                fh.write(f"| [{r['full_name']}]({r['url']}) | {r['stars']} | {r['s_total']} | {r['commits']} |\n")
            fh.write("\n")
        if loud_thin:
            fh.write("### Many stars, thin substance\n\n| repo | stars | S | commits |\n|---|---|---|---|\n")
            for r in loud_thin:
                fh.write(f"| [{r['full_name']}]({r['url']}) | {r['stars']} | {r['s_total']} | {r['commits']} |\n")
            fh.write("\n")

        fh.write("## Premise 2 — which S components never fire on code?\n\n")
        fh.write("| component | fired | of | rate |\n|---|---|---|---|\n")
        for comp, label in (("s1", "S1 cost side in source"), ("s2", "S2 backtest AND live"),
                            ("s3", "S3 tests or committed results"),
                            ("s4", "S4 README gives mechanism"), ("s5", "S5 runnable")):
            n = sum(1 for r in rows if (r[comp] or 0) > 0)
            fh.write(f"| {label} | {n} | {len(rows)} | {100*n/len(rows):.0f}% |\n")
        fh.write("\n")

        tmb = [r for r in rows if r["trust_me_bro"]]
        fh.write(f"## \"Trust me bro\" repos — a results claim in the README, "
                 f"under 10 commits, no artifact\n\n**{len(tmb)}** of {len(rows)}.\n\n")
        if tmb:
            fh.write("| repo | stars | commits | claim |\n|---|---|---|---|\n")
            for r in sorted(tmb, key=lambda r: -(r["stars"] or 0))[:15]:
                fh.write(f"| [{r['full_name']}]({r['url']}) | {r['stars']} | {r['commits']} "
                         f"| {(r['claimed_results'] or '')[:90]} |\n")
            fh.write("\n")

        fh.write("## Ranked — the read order\n\n")
        fh.write("| # | repo | S | S1..S5 | stars | commits | span | contrib | pushed | credibility |\n")
        fh.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for i, r in enumerate(ranked[:60], 1):
            comps = "".join(str(r[c] or 0) for c in ("s1", "s2", "s3", "s4", "s5"))
            fh.write(f"| {i} | [{r['full_name']}]({r['url']}){' `STALE`' if r['gate']=='STALE' else ''} "
                     f"| **{r['s_total']}** | {comps} | {r['stars']} | {r['commits']} "
                     f"| {r['span_days']} | {r['contributors']} | {(r['pushed_at'] or '')[:10]} "
                     f"| {credibility(r)} |\n")

        fh.write("\n## Evidence for the top 15\n\n")
        for r in ranked[:15]:
            fh.write(f"### {r['full_name']} — S={r['s_total']}\n\n")
            try:
                ev = json.loads(r["evidence"] or "{}")
            except json.JSONDecodeError:
                ev = {}
            for k in ("S1", "S2", "S3", "S4", "S5"):
                items = ev.get(k) or []
                if items:
                    fh.write(f"- **{k}**\n")
                    for it in items[:4]:
                        fh.write(f"  - `{it}`\n")
                else:
                    fh.write(f"- **{k}** — no evidence found, scored 0\n")
            fh.write("\n")

    print(f"wrote {out}", flush=True)
    db.log(con, "rank", f"n={len(rows)} rho_stars_S={rho_s} rho_commits_S={rho_c}")
    print(f"rho(stars,S)={rho_s} p={p_s}  rho(commits,S)={rho_c} p={p_c}", flush=True)


if __name__ == "__main__":
    main()
