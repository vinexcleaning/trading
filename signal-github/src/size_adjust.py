"""Take the repository-size advantage out of the strict score.

Measured 2026-08-03 over 862 deep-fetched repos:

    rho(tree_files, S_strict) = +0.593   p < 0.0001
    rho(stars,      S_strict) = -0.004   p = 0.898

File count is by far the strongest predictor of the strict score, and it is
largely **mechanical**: S_strict is a sum of binary components, and a repo with
1,000 files has more chances for each pattern to appear somewhere than a repo
with 20. That is a property of the instrument, not of the repo. It is also
gameable - one repo in the corpus has 42 of its 104 files as committed
`__pycache__/*.pyc`, every one of which `tree_files` counts.

The fix here is deliberately the least invasive one that works: do not redesign
the rubric, just remove the part of the score that size alone explains.

    s_adj = S_strict - (a + b * log10(1 + tree_files))

fitted by least squares across the corpus. `s_adj` is a residual in score
points: **+2 means "scores two points better than repos of its size typically
do"**, 0 means exactly typical, negative means worse. Both columns are kept -
`s_strict` is still the raw measurement and is not overwritten.

This is a ranking correction, not a quality verdict. A big repo with a genuinely
high score is not being punished for being big; it is being compared against
other big repos instead of against everything.

    python src/size_adjust.py
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import gh  # noqa: E402


def ranks(xs):
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
    n = len(a)
    if n < 3:
        return None, None
    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = math.sqrt(sum((x - ma) ** 2 for x in ra))
    dbv = math.sqrt(sum((y - mb) ** 2 for y in rb))
    if da == 0 or dbv == 0:
        return None, None
    rho = num / (da * dbv)
    if abs(rho) >= 1:
        return rho, 0.0
    t = rho * math.sqrt((n - 2) / (1 - rho * rho))
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))
    return rho, p


def main():
    con = db.connect()
    con.execute("PRAGMA busy_timeout = 60000")  # a fetch may be writing
    cols = {c[1] for c in con.execute("PRAGMA table_info(repos)")}
    if "s_strict" not in cols:
        print("s_strict does not exist yet - run src/rescore.py first")
        return
    if "s_adj" not in cols:
        con.execute("ALTER TABLE repos ADD COLUMN s_adj REAL")
        con.commit()

    # MIN_FILES exists because the first version of this script did not have it
    # and the result was wrong in an obvious way: repos with ONE file and a
    # strict score of 2 rose 400+ ranks, because the fit predicts ~0.3 for a
    # 1-file repo so scoring 2 "beats expectation". A one-file repo is not a
    # repo that punches above its weight, it is an empty repo. The log fit
    # extrapolates badly below about ten files, so those are excluded from both
    # the fit and the ranking rather than flattered by it.
    MIN_FILES = 10
    rows = con.execute(
        "SELECT full_name, stars, tree_files, s_total, s_strict FROM repos "
        "WHERE fetched>=1 AND s_strict IS NOT NULL AND tree_files IS NOT NULL "
        "AND tree_files >= ?", (MIN_FILES,)
    ).fetchall()
    excluded = con.execute(
        "SELECT count(*) FROM repos WHERE fetched>=1 AND s_strict IS NOT NULL "
        "AND COALESCE(tree_files,0) < ?", (MIN_FILES,)).fetchone()[0]
    print(f"excluded {excluded} repos with fewer than {MIN_FILES} files - "
          f"too small to judge, and the log fit extrapolates badly there\n")
    if len(rows) < 30:
        print(f"only {len(rows)} scored repos - not enough to fit")
        return

    x = [math.log10(1 + (r["tree_files"] or 0)) for r in rows]
    y = [float(r["s_strict"]) for r in rows]
    n = len(rows)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((v - mx) ** 2 for v in x)
    b = sum((xv - mx) * (yv - my) for xv, yv in zip(x, y)) / sxx if sxx else 0.0
    a = my - b * mx

    print(f"n = {n} deep-fetched, strictly scored repos\n")
    print(f"fit:  S_strict  =  {a:.3f}  +  {b:.3f} * log10(1 + tree_files)")
    print(f"      a repo with 10 files is predicted {a + b*math.log10(11):.2f}; "
          f"with 1,000 files, {a + b*math.log10(1001):.2f}  "
          f"-> size alone is worth {b*(math.log10(1001)-math.log10(11)):.2f} points\n")

    adj = [yv - (a + b * xv) for xv, yv in zip(x, y)]

    r_before, p_before = spearman([r["tree_files"] or 0 for r in rows], y)
    r_after, p_after = spearman([r["tree_files"] or 0 for r in rows], adj)
    r_stars, p_stars = spearman([r["stars"] or 0 for r in rows], adj)
    print("did it work?  (closer to 0 is better for the first two)")
    print(f"  rho(tree_files, S_strict) = {r_before:+.3f}  p={p_before:.4f}   <- before")
    print(f"  rho(tree_files, s_adj)    = {r_after:+.3f}  p={p_after:.4f}   <- after")
    print(f"  rho(stars,      s_adj)    = {r_stars:+.3f}  p={p_stars:.4f}   "
          f"(stars stay uninformative, as they should)")

    con.executemany("UPDATE repos SET s_adj=? WHERE full_name=?",
                    [(v, r["full_name"]) for v, r in zip(adj, rows)])
    con.commit()

    order_raw = sorted(range(n), key=lambda i: (-y[i], -(rows[i]["stars"] or 0)))
    order_adj = sorted(range(n), key=lambda i: -adj[i])
    rank_raw = {i: k for k, i in enumerate(order_raw, 1)}
    rank_adj = {i: k for k, i in enumerate(order_adj, 1)}

    print("\n=== top 20 after adjusting for size ===")
    print(f"  {'repo':52} {'s_adj':>6} {'strict':>6} {'files':>6} {'stars':>6}  rank move")
    for i in order_adj[:20]:
        r = rows[i]
        move = rank_raw[i] - rank_adj[i]
        print(f"  {r['full_name'][:52]:52} {adj[i]:+6.2f} {r['s_strict']:6} "
              f"{r['tree_files']:6} {r['stars']:6}  {move:+5}")

    print("\n=== biggest fallers: scored well, but only for their size ===")
    fell = sorted(range(n), key=lambda i: rank_adj[i] - rank_raw[i], reverse=True)
    for i in [j for j in fell if y[j] >= 8][:12]:
        r = rows[i]
        print(f"  {r['full_name'][:52]:52} strict {r['s_strict']:2} -> s_adj {adj[i]:+.2f}"
              f"   {r['tree_files']:6} files   rank {rank_raw[i]} -> {rank_adj[i]}")

    print("\n=== biggest risers: small repos that punch above their size ===")
    rose = sorted(range(n), key=lambda i: rank_raw[i] - rank_adj[i], reverse=True)
    for i in rose[:12]:
        r = rows[i]
        print(f"  {r['full_name'][:52]:52} strict {r['s_strict']:2} -> s_adj {adj[i]:+.2f}"
              f"   {r['tree_files']:6} files   rank {rank_raw[i]} -> {rank_adj[i]}")

    # --- independent validation -------------------------------------------
    # The fee audit found, by reading source, which repos model Kalshi's maker
    # fee correctly. That is an OBJECTIVE fact with a published ground truth and
    # it is completely independent of any S component. If the size-adjusted
    # ranking is better than the raw one, it should surface those repos higher.
    import json
    fa = os.path.join(gh.ROOT, "reports", "fee_audit.json")
    if os.path.exists(fa):
        with open(fa, encoding="utf-8") as fh:
            findings = json.load(fh)["findings"]
        correct = {f["repo"] for f in findings
                   if any("maker 0.0175 OK" in v for v in f["verdict"])}
        idx = {rows[i]["full_name"]: i for i in range(n)}
        hits = [r for r in correct if r in idx]
        if hits:
            print(f"\n=== validation against the fee audit ({len(hits)} repos that "
                  f"provably model Kalshi's maker fee correctly) ===")
            for topn in (25, 50, 100, 200):
                in_raw = sum(1 for r in hits if rank_raw[idx[r]] <= topn)
                in_adj = sum(1 for r in hits if rank_adj[idx[r]] <= topn)
                print(f"  in the top {topn:3}:  raw S_strict {in_raw:2}   "
                      f"size-adjusted {in_adj:2}   {'BETTER' if in_adj > in_raw else ('same' if in_adj == in_raw else 'WORSE')}")

    out = os.path.join(gh.ROOT, "reports", "size_adjust.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# Size-adjusted strict score\n\n")
        fh.write(f"n = {n}. Fit `S_strict = {a:.3f} + {b:.3f} * log10(1 + tree_files)`.\n\n")
        fh.write(f"| | rho vs tree_files | p |\n|---|---|---|\n")
        fh.write(f"| S_strict (raw) | {r_before:+.3f} | {p_before:.4f} |\n")
        fh.write(f"| **s_adj** | **{r_after:+.3f}** | {p_after:.4f} |\n\n")
        fh.write("`s_adj` is a residual in score points: +2 means the repo scores two "
                 "points better than repos of its size typically do. `s_strict` is kept "
                 "unchanged alongside it.\n\n## Top 30 by s_adj\n\n")
        fh.write("| repo | s_adj | strict | files | stars |\n|---|---|---|---|---|\n")
        for i in order_adj[:30]:
            r = rows[i]
            fh.write(f"| {r['full_name']} | {adj[i]:+.2f} | {r['s_strict']} | "
                     f"{r['tree_files']} | {r['stars']} |\n")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
