"""A3 -- every selection point, under the strengthened guard.

v1 of this reported `liquidity_dollars` as a clean alternative dedupe rule. It
is not: the field reads 0 on almost every settled tennis market, so the rule
almost never chooses anything and the tie-break does the work. Any mostly-null
field passes a correlation test for free. The guard now demands that a rule
actually discriminate, and that the test have the power to see a bias that
would matter, before it is allowed to say PASS.
"""
import argparse
import json
import pathlib

import numpy as np
import pandas as pd

import leakguard as lg

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

SIDE_RULES = [
    ("last", False, "higher last_price_dollars"),
    ("oi", False, "higher open_interest_fp"),
    ("vol", False, "higher volume_fp   (THE PHASE 0 BUG)"),
    ("vol24", False, "higher volume_24h_fp"),
    ("liq", False, "higher liquidity_dollars"),
    ("tk", True, "first ticker alphabetically   (THE FIX)"),
]


def load_pairs():
    raw = json.loads((DATA / "markets_raw.json").read_text(encoding="utf-8"))
    rows = []
    for _, ms in raw.items():
        for m in ms:
            if m.get("result") in ("yes", "no"):
                rows.append((m["event_ticker"], m["ticker"], m["result"],
                             float(m.get("volume_fp") or 0),
                             float(m.get("volume_24h_fp") or 0),
                             float(m.get("open_interest_fp") or 0),
                             float(m.get("last_price_dollars") or 0),
                             float(m.get("liquidity_dollars") or 0)))
    d = pd.DataFrame(rows, columns=["ev", "tk", "res", "vol", "vol24", "oi",
                                    "last", "liq"])
    return d.groupby("ev").filter(lambda x: len(x) == 2)


def side_results(d):
    """For each rule: kept-side outcome, plus whether the field discriminated."""
    out = []
    a = d.groupby("ev").nth(0).reset_index()
    b = d.groupby("ev").nth(1).reset_index()
    merged = a.merge(b, on="ev", suffixes=("_a", "_b"))
    for field, asc, label in SIDE_RULES:
        fa = merged[f"{field}_a"].values
        fb = merged[f"{field}_b"].values
        if field == "tk":
            pick_a = fa < fb
            disc = fa != fb
        else:
            pick_a = fa > fb if not asc else fa < fb
            disc = fa != fb
        kept_res = np.where(pick_a, merged["res_a"].values,
                            merged["res_b"].values)
        out.append(lg.check_side_choice(kept_res == "yes", disc, label))
    return out


def pipeline_filters(state_tag):
    """Every row filter in the Phase 1-4 pipeline, tested against the outcome."""
    p = DATA / f"{state_tag}_state.parquet"
    if not p.exists():
        return [], f"({state_tag}_state.parquet not present)"
    st = pd.read_parquet(p)
    st["ok"] = st["ok"].fillna(False).astype(bool)
    res = []

    have = st["ok"] & st["pre_bid"].notna()
    base = st[have].copy()
    base["pm"] = (base["pre_bid"] + base["pre_ask"]) / 2.0 / 100.0
    base["fav_won"] = base["fav_won"].fillna(False).astype(float)
    base["plausible"] = base["plausible"].fillna(False).astype(bool)
    y, imp = base["fav_won"].values, base["pm"].values

    res.append(lg.check_selection(
        base["plausible"].values, y, imp,
        "duration filter, 25-330 min (p1_state MIN_PLAY/MAX_PLAY)"))

    # t0 agreement: matches where the causal and backward-walk detectors differ
    # by more than 5 min are ones the activity-density floor treated differently
    if "t0_causal_delta" in base:
        d0 = base["t0_causal_delta"].abs().values
        res.append(lg.check_selection(
            d0 <= 5, y, imp,
            "t0 detectors agree within 5 min (activity-density floor)"))

    # pre-match anchor staleness: proxy for the play-window cut biting late
    if "flat_before" in base:
        fb = pd.to_numeric(base["flat_before"], errors="coerce").fillna(-1)
        res.append(lg.check_selection(
            (fb >= 10).values, y, imp,
            "pre-match anchor stood >=10 min (t0 detected cleanly)"))

    # wide-quote exposure: share of the market's grid masked for spread>15c
    if "n_wide" in base and "n_candles" in base:
        nw = pd.to_numeric(base["n_wide"], errors="coerce").fillna(0)
        nc = pd.to_numeric(base["n_candles"], errors="coerce").fillna(1)
        frac = (nw / nc.clip(lower=1)).values
        res.append(lg.check_selection(
            frac <= np.nanmedian(frac), y, imp,
            "below-median exposure to the spread>15c mask"))

    # ---- the play-window cut, now testable ------------------------------
    # p1_state records a kept-market-oriented early mid for every market that
    # has any quote at all, including the ones this cut drops, precisely so
    # this test can run. Orientation-free: residual is measured on the kept
    # market, because dropped rows have no identified favourite.
    allst = pd.read_parquet(p)
    allst["ok"] = allst["ok"].fillna(False).astype(bool)
    n_drop = int((~allst["ok"]).sum())
    if "fallback_mid2" in allst.columns:
        f = allst[pd.to_numeric(allst["fallback_mid2"],
                                errors="coerce").fillna(-1) >= 0].copy()
        imp2 = f["fallback_mid2"].astype(float).values / 200.0
        y2 = f["kept_won"].astype(float).values
        res.append(lg.check_selection(
            f["ok"].values, y2, imp2,
            "play-window cut (kept-market residual, orientation-free)"))
        untestable = len(allst) - len(f)
        note = (f"play-window cut drops {n_drop:,}/{len(allst):,} "
                f"({n_drop / len(allst):.1%}); {untestable:,} markets have no "
                f"quote at all and remain structurally excluded")
    else:
        note = (f"play-window cut drops {n_drop:,}/{len(allst):,} "
                f"({n_drop / len(allst):.1%}); state file predates the "
                f"fallback price, so this cut is NOT yet testable")
    return res, note


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="paths")
    ap.add_argument("--out", default="audit_a3.txt")
    ap.add_argument("--label", default="CONTAMINATED universe (volume dedupe)")
    args = ap.parse_args()

    out = []

    def w(s=""):
        print(s, flush=True)
        out.append(s)

    w("A3 -- SELECTION POINTS UNDER THE STRENGTHENED GUARD")
    w("=" * 78)
    w(f"universe: {args.label}")
    w("")
    w("Guard now returns three values. UNTESTABLE is not a pass: it means the")
    w("rule either fails to discriminate (a mostly-null field chooses nothing,")
    w("so the tie-break does the work) or the test lacks the power to see a")
    w(f"{lg.MDE_MAX_PP:.0f} pp bias. Either way the rule is rejected.")
    w("")

    d = load_pairs()
    w(f"## 1. Mirrored-side rules.  Null: P(kept wins) = 0.5000, "
      f"{d['ev'].nunique():,} events")
    w("")
    w(lg.table(side_results(d), "side-choice rules"))
    w("")

    res, note = pipeline_filters(args.tag)
    w("## 2. Row filters in the Phase 1-4 pipeline")
    w("")
    if res:
        w(lg.table(res, "pipeline filters"))
    else:
        w(note)
    w("")
    w(f"  note: {note}")

    (ROOT / "reports" / args.out).write_text("\n".join(out), encoding="utf-8")
    print(f"\n-> {ROOT / 'reports' / args.out}")


if __name__ == "__main__":
    main()
