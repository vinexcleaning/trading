"""Running count of every hypothesis evaluated, with Benjamini-Hochberg FDR.

Every combination that is looked at goes in here, including ones abandoned
mid-way and including the entry-timing grid. The point of the ledger is that the
denominator of the multiplicity correction is not chosen after seeing which
tests were interesting.
"""
import csv
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "HYPOTHESIS_LEDGER.md"
CSV = ROOT / "reports" / "hypothesis_ledger.csv"

FIELDS = ["phase", "factor", "level", "n", "mis_pp", "ci_lo", "ci_hi",
          "p_one", "p_two", "net_c", "note"]


def reset():
    CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, FIELDS).writeheader()


def add(**kw):
    row = {k: kw.get(k, "") for k in FIELDS}
    with open(CSV, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, FIELDS).writerow(row)


def bh(p, q=0.10):
    """Benjamini-Hochberg. Returns the boolean reject vector and the threshold."""
    p = np.asarray(p, float)
    ok = np.isfinite(p)
    m = ok.sum()
    if m == 0:
        return np.zeros(len(p), bool), 0.0
    order = np.argsort(np.where(ok, p, 2.0))
    ranked = p[order][:m]
    crit = q * np.arange(1, m + 1) / m
    passing = np.where(ranked <= crit)[0]
    if len(passing) == 0:
        return np.zeros(len(p), bool), 0.0
    k = passing[-1]
    thr = ranked[k]
    return (p <= thr) & ok, float(thr)


def finalise(q=0.10):
    df = pd.read_csv(CSV)
    df["p_one"] = pd.to_numeric(df["p_one"], errors="coerce")
    df["p_two"] = pd.to_numeric(df["p_two"], errors="coerce")
    # BH runs on TWO-SIDED p-values. The one-sided column is oriented toward
    # overshoot for most rows and toward undershoot for the Phase 4 fade rows,
    # so correcting across it would be mixing directions. The study genuinely
    # cares about both tails -- an undershoot is a finding, not a non-result --
    # so two-sided is the honest denominator.
    p_use = df["p_two"].where(df["p_two"].notna(),
                              2 * np.minimum(df["p_one"], 1 - df["p_one"]))
    df["p_bh"] = p_use
    rej, thr = bh(p_use.values, q)
    df["bh_reject"] = rej
    df.to_csv(CSV, index=False)

    lines = ["# HYPOTHESIS_LEDGER.md", "",
             "Every hypothesis evaluated in this study, in the order it was "
             "evaluated.",
             "Benjamini-Hochberg FDR is applied across **this entire table**, "
             "not per phase.", "",
             f"- **Total hypotheses evaluated: {len(df)}**",
             f"- Tests with a computable p-value: "
             f"{int(p_use.notna().sum())}",
             "- BH is applied to **two-sided** p-values, because an undershoot "
             "is a finding here and a one-sided overshoot test would hide it.",
             f"- BH threshold at q={q}: "
             f"{'p <= %.5f' % thr if thr else 'none pass'}",
             f"- **Surviving FDR: {int(rej.sum())}**", "",
             "| # | phase | factor | level | n | mis pp | 95% CI | p (2-sided) "
             "| net c | BH | note |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(df.itertuples(), 1):
        def fmt(x, d=2):
            try:
                return f"{float(x):+.{d}f}"
            except (TypeError, ValueError):
                return "-"
        ci = (f"[{fmt(r.ci_lo)}, {fmt(r.ci_hi)}]"
              if str(r.ci_lo) not in ("", "nan") else "-")
        p = (f"{float(r.p_bh):.4f}"
             if pd.notna(r.p_bh) else "-")
        lines.append(
            f"| {i} | {r.phase} | {r.factor} | {r.level} | {r.n} | "
            f"{fmt(r.mis_pp)} | {ci} | {p} | {fmt(r.net_c, 3)} | "
            f"{'**yes**' if r.bh_reject else 'no'} | {r.note} |")
    PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nledger: {len(df)} hypotheses, {int(rej.sum())} survive "
          f"BH at q={q}  -> {PATH}")
    return df
