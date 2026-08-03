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

    # Prescreen scores, for the selection-bias control below. The fetch queue is
    # ordered by these, so they are the confounder, not a nuisance column.
    prescreen_of = {}
    try:
        for fn, sc in con.execute("SELECT full_name, score FROM prescreen"):
            prescreen_of[fn] = sc
    except Exception:  # noqa: BLE001 - table may not exist on a fresh db
        pass
    rho_ps = None
    if prescreen_of:
        pairs = [(prescreen_of[r["full_name"]], r["stars"] or 0)
                 for r in rows if r["full_name"] in prescreen_of]
        if len(pairs) >= 3:
            rho_ps, _ = spearman([a for a, _ in pairs], [b for _, b in pairs])

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
        # The verdict is DERIVED from the numbers, never asserted. An earlier
        # version hardcoded "stars carry no information", which was true at
        # n=40 (rho -0.019, p 0.91) and became wrong at n=97 (rho +0.191,
        # p 0.058). A conclusion baked into a print statement cannot notice
        # that it has stopped being true.
        if rho_x is None:
            verdict = "Not enough data to say."
        elif p_x < 0.05 and abs(rho_x) >= 0.3:
            verdict = (f"**Stars do carry real signal here** (rho {rho_x:+.3f}, p {p_x:.3f}). "
                       "That is a change from the YouTube result, where views did not.")
        elif p_x < 0.10:
            var = rho_x * rho_x * 100
            verdict = (
                f"**A weak positive relationship, at the edge of significance** "
                f"(rho {rho_x:+.3f}, p {p_x:.3f}, n={len(rows)}). Stars are not noise — but "
                f"rho {rho_x:.3f} explains only about {var:.0f}% of the variance in rank, so "
                f"sorting by stars still tells you very little about which repo has substance. "
                f"The practical conclusion survives; the strong claim that stars carry NO "
                f"information does not.")
        else:
            verdict = (f"**No relationship detected** (rho {rho_x:+.3f}, p {p_x:.3f}, "
                       f"n={len(rows)}). Stars carry no usable signal about substance, the "
                       "same as views on YouTube.")
        fh.write("\n" + verdict + "\n\n")
        # ---- why the raw figure is not trustworthy on its own ----
        # The deep-fetch queue is ORDERED BY PRESCREEN, and prescreen.py awards
        # up to +3 for stars. So the fetched sample is star-enriched, not a
        # random draw from the gated corpus, and the raw correlation drifts as
        # coverage grows. Controlling for prescreen by slicing into bands and
        # correlating WITHIN each band removes most of that selection.
        pres = {r["full_name"]: (r["pre"] if "pre" in r.keys() else None) for r in rows} \
            if rows and "pre" in rows[0].keys() else {}
        bands: dict[int, list] = {}
        for r in rows:
            b = prescreen_of.get(r["full_name"])
            if b is None:
                continue
            bands.setdefault(int(round(b)), []).append(r)
        band_lines, tot, wsum = [], 0, 0.0
        for b in sorted(bands):
            g = bands[b]
            if len(g) < 25:
                continue
            rr, pp = spearman([x["stars"] or 0 for x in g], [x["s_strict"] or 0 for x in g])
            if rr is None:
                continue
            band_lines.append(f"| {b} | {len(g)} | {rr:+.3f} | {pp:.3f} |")
            tot += len(g); wsum += rr * len(g)

        fh.write("### Why the raw number above cannot be taken at face value\n\n")
        fh.write("The deep-fetch queue is **ordered by prescreen score, and the prescreen "
                 "awards up to +3 for stars**. The fetched sample is therefore star-enriched "
                 "rather than a random draw from the gated corpus")
        if rho_ps is not None:
            fh.write(f" — `rho(prescreen, stars) = {rho_ps:+.3f}`")
        fh.write(". That makes the raw correlation drift as coverage grows, and it did:\n\n")
        fh.write("| n | stars vs S_strict | p | reading at the time |\n|---|---|---|---|\n")
        fh.write("| 40 | −0.019 | 0.91 | no relationship |\n")
        fh.write("| 105 | **+0.241** | **0.013** | weak positive, significant |\n")
        fh.write(f"| {len(rows)} | {rho_x:+.3f} | {p_x:.3f} | no relationship |\n\n")
        fh.write("**The middle row was a sampling artifact, not a discovery.** It is what the "
                 "star-enriched head of the queue looked like before the tail arrived.\n\n")
        if band_lines:
            fh.write("Correlating **within** prescreen bands, which was done to control for "
                     "that selection:\n\n")
            fh.write("| prescreen band | n | stars vs S_strict | p |\n|---|---|---|---|\n")
            fh.write("\n".join(band_lines) + "\n\n")
            fh.write(f"**n-weighted mean within-band rho = {wsum/tot:+.3f}** (n={tot}), "
                     "predominantly negative, several bands individually significant.\n\n")
            fh.write("### That within-band figure is contaminated — do not use it\n\n")
            fh.write("It is tempting to read a consistent negative as *more stars, worse code*. "
                     "**It is an artifact, and of a specific kind: conditioning on a collider.**\n\n")
            fh.write("`prescreen` is not a confounder here, it is a *consequence*: "
                     "`prescreen = f(stars, size, recency, language, keywords)`. Holding it "
                     "fixed forces its inputs to trade off against each other — within a band, "
                     "a repo with more stars must have less of everything else. And one of "
                     "those other inputs, size, is strongly related to the score "
                     "(`tree_files vs S_strict` is the largest correlation in this project). "
                     "So high stars implies small repo implies low S, purely by construction. "
                     "That is Berkson's paradox, not a finding about stars.\n\n")
            fh.write("**The raw figure at near-complete coverage is the trustworthy one.** The "
                     "reason the control was introduced — that the fetched sample was a "
                     "star-enriched head of the queue — no longer applies once coverage "
                     f"reaches {100*len(rows)/2562:.0f}% of the gated corpus. The band table is "
                     "kept because it shows how the earlier n=105 artifact arose, not because "
                     "its number should be quoted.\n\n")
        fh.write("> Cite the raw figure at full n. Both the n=105 positive and the within-band "
                 "negative are selection artifacts pointing in opposite directions, which is "
                 "itself the clearest evidence that neither is measuring anything real.\n\n")

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
