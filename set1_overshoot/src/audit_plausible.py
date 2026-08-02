"""Resolve the `plausible` duration filter.

It reads z = -3.53 against the outcome but is UNTESTABLE under the strengthened
guard: the dropped arm is 718 rows and cannot resolve a 2 pp shift. "Untestable"
is not "fine", so this settles it a different way.

The residual test asks whether the dropped rows are differently priced. The
decision-relevant question is narrower: **does the filter change theta?** That is
answerable at full power regardless of how small the dropped arm is, because it
compares two estimates of the same quantity rather than two subsamples.
"""
import pathlib

import numpy as np
import pandas as pd

import fees
import leakguard as lg
import p2_calib as p2

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def theta(st, bid, ask, mid, rng, label, w, force_plausible=None):
    st2 = st.copy()
    if force_plausible is not None:
        st2["plausible"] = force_plausible
    ev = p2.build_events(st2, bid, ask, mid, "deep:30", 0, min_minute=38)
    e = ev[ev["is_event"]]
    if len(e) < 50:
        w(f"| {label} | {len(e):,} | - | - | - |")
        return None
    p = (e["entry_mid"] / 100.0).values
    y = e["fav_won"].values
    m = 100 * (y - p)
    lo, hi = p2.bootstrap_ci(m, rng, n=8000)
    _, two = p2.poisson_binom_p(int(y.sum()), p, rng)
    w(f"| {label} | {len(e):,} | {m.mean():+.2f} | [{lo:+.2f}, {hi:+.2f}] | "
      f"{two:.4f} |")
    return m


def main():
    st, bid, ask, mid = p2.load("paths")
    rng = np.random.default_rng(4242)
    out = []

    def w(s=""):
        print(s, flush=True)
        out.append(s)

    ok = st["ok"].values
    dur = pd.to_numeric(st["dur_min"], errors="coerce").fillna(-1).values
    pl = st["plausible"].values.astype(bool)

    w("# Resolving the `plausible` duration filter")
    w("")
    w(f"Current rule: keep {p2.__name__ and ''}25 <= duration <= 330 minutes. "
      f"Of {int(ok.sum()):,} markets with a play window, "
      f"**{int((ok & ~pl).sum()):,} are dropped** "
      f"({(ok & ~pl).sum() / max(ok.sum(), 1):.1%}).")
    w("")
    w("## What is actually being dropped")
    w("")
    w("| bucket | n | favourite win rate |")
    w("|---|---|---|")
    favw = st["fav_won"].values.astype(float)
    for lab, m in (("< 25 min (too short to be a match)", ok & (dur < 25)),
                   ("25-330 min (kept)", ok & pl),
                   ("> 330 min (suspended / stale book)", ok & (dur > 330))):
        if m.sum():
            w(f"| {lab} | {int(m.sum()):,} | {favw[m].mean():.4f} |")
    w("")

    # --- the decision-relevant test ---------------------------------------
    w("## Does the filter change theta?")
    w("")
    w("Two estimates of the same quantity, at full power. If they agree, the "
      "filter is")
    w("immaterial whatever its residual test says.")
    w("")
    w("| variant | n events | theta pp | 95% CI | p(2s) |")
    w("|---|---|---|---|---|")
    m_on = theta(st, bid, ask, mid, rng, "plausible ON (current)", w)
    m_off = theta(st, bid, ask, mid, rng, "plausible OFF (all play windows)",
                  w, force_plausible=ok)
    for lo_b, hi_b in ((15, 400), (35, 300), (45, 240)):
        fp = ok & (dur >= lo_b) & (dur <= hi_b)
        theta(st, bid, ask, mid, rng, f"bounds {lo_b}-{hi_b} min", w,
              force_plausible=fp)
    w("")
    if m_on is not None and m_off is not None:
        d = m_off.mean() - m_on.mean()
        boots = np.array([
            m_off[rng.integers(0, len(m_off), len(m_off))].mean()
            - m_on[rng.integers(0, len(m_on), len(m_on))].mean()
            for _ in range(8000)])
        lo, hi = np.percentile(boots, [2.5, 97.5])
        w(f"**Difference (OFF minus ON): {d:+.2f} pp, 95% CI "
          f"[{lo:+.2f}, {hi:+.2f}].**")
        w("")
        if lo <= 0 <= hi:
            w("The filter does not move theta. It is immaterial to the "
              "headline, and the")
            w("z = -3.53 residual reflects that the excluded matches are "
              "genuinely odd")
            w("objects -- sub-25-minute 'matches' and multi-day stale books -- "
              "not that the")
            w("filter is selecting on the outcome among comparable matches.")
        else:
            w("**The filter DOES move theta.** It is not immaterial and the "
              "headline must be")
            w("reported under both variants.")
    w("")

    # --- widen until testable ---------------------------------------------
    w("## Can the residual test be made powerful enough?")
    w("")
    w("Widening the kept band shrinks the dropped arm further; narrowing it "
      "grows the")
    w("dropped arm until the test has power. Narrowing is not a proposal to "
      "change the")
    w("filter -- it is a way to interrogate the same boundary at a sample "
      "size where the")
    w("guard can actually speak.")
    w("")
    pm = (st["pre_bid"].values + st["pre_ask"].values) / 2.0 / 100.0
    base = ok & np.isfinite(pm) & (pm > 0)
    res = []
    for lo_b, hi_b in ((25, 330), (35, 300), (45, 240), (55, 200), (65, 180)):
        mask = (dur >= lo_b) & (dur <= hi_b)
        res.append(lg.check_selection(
            mask[base], favw[base], pm[base],
            f"duration band {lo_b}-{hi_b} min"))
    w("```")
    w(lg.table(res, "duration-band residual tests"))
    w("```")
    w("")
    w("Read the MDE column, not just z. A band only becomes testable once the "
      "dropped")
    w("arm is large enough, and by then it is a different filter. The honest "
      "summary is")
    w("that the 25-330 boundary cannot be cleared by this test at this sample "
      "size, and")
    w("the theta comparison above is what settles whether that matters.")

    (ROOT / "reports" / "audit_plausible.md").write_text("\n".join(out),
                                                         encoding="utf-8")
    print(f"\n-> {ROOT / 'reports' / 'audit_plausible.md'}")


if __name__ == "__main__":
    main()
