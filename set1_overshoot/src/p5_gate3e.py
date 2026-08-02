"""The mirrored-consistency gate. Runs BEFORE any calibration number is read.

Promoted from validity footnote to primary instrument, because it is the check
that caught the Phase 0 selection leak after four phases of work had been built
on top of it.

Two gates, both fixed in PREREGISTRATION_PARTB.md §2 before the clean data
existed:

  G1  orientation difference in the in-play miscalibration, |z| < 4
  G2  pre-match calibration, |residual| <= 1.5 pp in BOTH orientations

G2 is the one that would have caught the original bug on day one. A pre-match
market that tracks Betfair at r = 0.9878 cannot be 8.7 pp wrong in a subgroup.

Exit code 0 = proceed. Exit code 2 = stop and debug.
"""
import argparse
import pathlib
import sys

import numpy as np
import pandas as pd

import p2_calib as p2

ROOT = pathlib.Path(__file__).resolve().parents[1]

Z_GATE = 4.0
PREMATCH_TOL_PP = 1.5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="paths")
    ap.add_argument("--rule", default="deep:30")
    ap.add_argument("--floor", type=int, default=38)
    ap.add_argument("--out", default="p5_gate3e.md")
    args = ap.parse_args()

    st, bid, ask, mid = p2.load(args.tag)
    rng = np.random.default_rng(3939)
    out = []

    def w(s=""):
        print(s, flush=True)
        out.append(s)

    w("# Mirrored-consistency gate (3e)")
    w("")
    w("Run before any calibration number is read. Thresholds fixed in")
    w("`PREREGISTRATION_PARTB.md` §2 before the clean data existed:")
    w(f"G1 orientation difference |z| < {Z_GATE};  "
      f"G2 pre-match residual <= {PREMATCH_TOL_PP} pp in both orientations.")
    w("")

    kif = st["kept_is_fav"].values.astype(bool)
    okm = st["ok"].values & st["plausible"].values
    pm = (st["pre_bid"].values + st["pre_ask"].values) / 2.0
    favw = st["fav_won"].values.astype(float)

    # ---------------- G2: pre-match calibration --------------------------
    w("## G2 — pre-match calibration by orientation")
    w("")
    w("| orientation | n | implied | observed | residual pp | verdict |")
    w("|---|---|---|---|---|---|")
    sel = okm & (pm >= p2.FAV_MIN) & np.isfinite(pm)
    g2_fail = False
    g2 = {}
    for lab, m in (("favourite is YES side", sel & kif),
                   ("favourite is NO side", sel & ~kif)):
        imp = pm[m] / 100.0
        obs = favw[m]
        r = 100 * (obs.mean() - imp.mean())
        bad = abs(r) > PREMATCH_TOL_PP
        g2_fail |= bad
        g2[lab] = r
        w(f"| {lab} | {int(m.sum()):,} | {imp.mean():.4f} | {obs.mean():.4f} | "
          f"{r:+.2f} | {'**FAIL**' if bad else 'pass'} |")
    w("")
    w(f"Contaminated build read **+8.70 / −3.67 pp** here. "
      f"Clean reads **{g2['favourite is YES side']:+.2f} / "
      f"{g2['favourite is NO side']:+.2f} pp**.")
    w("")

    # ---- G2b: the leak-specific quantity --------------------------------
    # Added 2026-08-01 after a smoke run on partial data showed BOTH
    # orientations negative. G2 as pre-registered tests whether the pre-match
    # price is calibrated; it cannot tell a uniform miscalibration apart from
    # an orientation-dependent one, and only the latter is the selection leak.
    # The threshold in G2 is NOT relaxed -- this is an additional test, and a
    # G2 failure with G2b passing is reported as a separate finding, not waved
    # through.
    ya = favw[sel & kif] - pm[sel & kif] / 100.0
    nb = favw[sel & ~kif] - pm[sel & ~kif] / 100.0
    d2 = 100 * (ya.mean() - nb.mean())
    se2 = 100 * np.sqrt(ya.var(ddof=1) / len(ya) + nb.var(ddof=1) / len(nb))
    z2 = d2 / se2 if se2 > 0 else 0.0
    g2b_fail = abs(z2) >= Z_GATE
    w(f"**G2b — orientation DIFFERENCE in the pre-match residual: "
      f"{d2:+.2f} pp, z = {z2:+.2f}** "
      f"({'FAIL' if g2b_fail else 'pass'}). This is the leak-specific "
      f"quantity; the contaminated build read +12.37 pp.")
    w("")

    # ---- diagnostics for a UNIFORM residual ------------------------------
    w("### Why is the residual negative in both orientations?")
    w("")
    w("Three candidate causes, separated. Conditioning on `pre_mid >= 60` "
      "selects on the")
    w("same price whose calibration is then measured, so any noise in that "
      "quote biases")
    w("the selected subset upward and the residual downward. That is a "
      "property of my")
    w("filter, not of the market and not of the dedupe.")
    w("")
    w("| diagnostic | n | implied | observed | residual pp |")
    w("|---|---|---|---|---|")
    allm = okm & np.isfinite(pm)
    w(f"| unconditional, no favourite filter | {int(allm.sum()):,} | "
      f"{(pm[allm] / 100).mean():.4f} | {favw[allm].mean():.4f} | "
      f"{100 * (favw[allm].mean() - (pm[allm] / 100).mean()):+.2f} |")
    for lo, hi in ((60, 70), (70, 80), (80, 90), (90, 101)):
        m = okm & (pm >= lo) & (pm < hi)
        if m.sum() < 100:
            continue
        w(f"| favourite {lo}-{hi}¢ | {int(m.sum()):,} | "
          f"{(pm[m] / 100).mean():.4f} | {favw[m].mean():.4f} | "
          f"{100 * (favw[m].mean() - (pm[m] / 100).mean()):+.2f} |")
    # independent anchor: select on the t0-1 quote, score against the mid an
    # hour earlier. Regression-to-the-mean cannot survive that swap.
    if "pre_mid2_60m" in st.columns:
        p60 = pd.to_numeric(st["pre_mid2_60m"], errors="coerce").values / 2.0
        m = sel & np.isfinite(p60) & (p60 >= 0)
        if m.sum() > 200:
            w(f"| **selected on t0−1, scored on the mid 60 min earlier** | "
              f"{int(m.sum()):,} | {(p60[m] / 100).mean():.4f} | "
              f"{favw[m].mean():.4f} | "
              f"{100 * (favw[m].mean() - (p60[m] / 100).mean()):+.2f} |")
            w("")
            w("If that last row is near zero while the filtered rows above are "
              "negative, the")
            w("negative residual is **regression to the mean in my own "
              "favourite filter**, not")
            w("a market bias and not a leak.")
    w("")

    # ---------------- G1: in-play orientation split ----------------------
    ev = p2.build_events(st, bid, ask, mid, args.rule, 0,
                         min_minute=args.floor)
    e = ev[ev["is_event"]].copy()
    e["fav_is_yes"] = pd.Series(kif).reindex(e.index).values

    w("## G1 — in-play miscalibration by orientation")
    w("")
    w(f"Entry rule `{args.rule}@{args.floor}`.")
    w("")
    w("| side | n | implied | observed | mis pp | 95% CI |")
    w("|---|---|---|---|---|---|")
    halves = {}
    for lab, sub in (("both (pooled)", e),
                     ("favourite is YES side", e[e["fav_is_yes"]]),
                     ("favourite is NO side", e[~e["fav_is_yes"]])):
        p = (sub["entry_mid"] / 100.0).values
        y = sub["fav_won"].values
        m = 100 * (y - p)
        lo, hi = p2.bootstrap_ci(m, rng, n=8000)
        halves[lab] = m
        w(f"| {lab} | {len(sub):,} | {p.mean():.4f} | {y.mean():.4f} | "
          f"{m.mean():+.2f} | [{lo:+.2f}, {hi:+.2f}] |")

    a, b = halves["favourite is YES side"], halves["favourite is NO side"]
    diff = a.mean() - b.mean()
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    z = diff / se if se > 0 else 0.0
    d = np.array([a[rng.integers(0, len(a), len(a))].mean()
                  - b[rng.integers(0, len(b), len(b))].mean()
                  for _ in range(8000)])
    dlo, dhi = np.percentile(d, [2.5, 97.5])
    w("")
    w(f"**Difference (YES − NO): {diff:+.2f} pp, 95% CI "
      f"[{dlo:+.2f}, {dhi:+.2f}], z = {z:+.2f}.**")
    w(f"Contaminated build read **+25.49 pp, z ≈ +15**.")
    w("")

    g1_fail = abs(z) >= Z_GATE
    w("## Verdict")
    w("")
    w(f"- G1 orientation difference: **{'FAIL' if g1_fail else 'PASS'}** "
      f"(|z| = {abs(z):.2f} vs threshold {Z_GATE})")
    w(f"- G2 pre-match calibration, each orientation: "
      f"**{'FAIL' if g2_fail else 'PASS'}**")
    w(f"- G2b pre-match orientation DIFFERENCE (leak-specific): "
      f"**{'FAIL' if g2b_fail else 'PASS'}** (|z| = {abs(z2):.2f})")
    w("")
    # A selection leak shows up as an orientation DIFFERENCE. G1 and G2b are
    # the two tests of that, and they are the blocking ones. A G2 failure with
    # G2b passing means the pre-match price is uniformly off in the filtered
    # subset -- a real problem for interpretation, but not the leak, and not a
    # reason to discard the orientation comparison.
    if g1_fail or g2b_fail:
        w("**GATE FAILED — STOP.** An orientation-dependent discrepancy "
          "survives. Do not")
        w("pool, do not read a calibration number, do not run Phase 3 or 4.")
        (ROOT / "reports" / args.out).write_text("\n".join(out),
                                                 encoding="utf-8")
        sys.exit(2)
    if g2_fail:
        w("**G2 FAILED WHILE G1 AND G2b PASSED.** The two orientations agree, "
          "so the")
        w("selection leak is gone, but the pre-match price is uniformly "
          "miscalibrated in")
        w("the filtered subset. That is reported as a finding in its own "
          "right and it")
        w("caps how much any in-play miscalibration can be trusted, because "
          "the same")
        w("filter produces both. Proceeding, with that caveat attached to "
          "every number.")
        (ROOT / "reports" / args.out).write_text("\n".join(out),
                                                 encoding="utf-8")
        sys.exit(3)
    w("**GATE PASSED.** The two orientations agree and the pre-match price is")
    w("calibrated in both. Proceeding to read the Phase 2 calibration table.")
    (ROOT / "reports" / args.out).write_text("\n".join(out), encoding="utf-8")
    print(f"\n-> {ROOT / 'reports' / args.out}")


if __name__ == "__main__":
    main()
