"""Is the "monopoly regime" edge real, or is thin-book selecting on the outcome?

The only positive-direction result in this project: resting orders placed when
the FAR SIDE of the book is thin show +2.05 -> +8.83pp as the sample grows,
reaching a CI that excludes zero. r/quant `1ski9e8` (Paradigm challenge, placed
#2) predicts exactly this — *"the monopoly regime, when competitor quotes
vanish, accounted for 60% of total edge"*.

It is also the ONLY quantity here that STRENGTHENED with n, and GUARDS #10
pre-registers that pattern as evidence of contamination until proven otherwise:
the archive's worst-ever inference was arguing an effect was real *because* it
strengthened with detector precision, when precision and bias were one knob.

So: four ways to kill it, each targeting a different confound.

  T1 WITHIN-EVENT.  Compare thin vs thick orders INSIDE THE SAME MATCH. If the
     effect is about book state it survives; if it is about WHICH MATCHES are
     thin, it vanishes. This is the decisive test.
  T2 TIME-TO-EVENT. Thin books may simply be early (nobody quoting yet) or late
     (everyone withdrawn). Stratify.
  T3 PRICE LEVEL.   Thin books may cluster at extreme prices where
     `outcome - price` is not mean-zero.
  T4 PLACEBO.       Split on something that CANNOT matter — the parity of the
     placement minute. If the placebo shows an effect, the estimator is broken
     and none of the above means anything.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h10_passive as H  # noqa: E402
from diagnose_cross import event_time  # noqa: E402

REP = Path(__file__).resolve().parent.parent / "reports"
SEED = 20260805


def edge(rows):
    return [100.0 * (r["won"] - r["price"] / 100.0) for r in rows]


def clustered_ci(rows, n=2000, seed=SEED):
    if len(rows) < 10:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = defaultdict(list)
    for i, r in enumerate(rows):
        idx[r["event"]].append(i)
    keys = list(idx)
    v = np.asarray(edge(rows))
    out = np.empty(n)
    for b in range(n):
        pick = rng.choice(len(keys), size=len(keys), replace=True)
        sel = np.concatenate([idx[keys[j]] for j in pick])
        out[b] = v[sel].mean()
    return tuple(float(x) for x in np.percentile(out, [2.5, 97.5]))


def split_report(label, thin, thick):
    if len(thin) < 10 or len(thick) < 10:
        print(f"    {label:34} n too small ({len(thin)}/{len(thick)})")
        return None
    et, ek = float(np.mean(edge(thin))), float(np.mean(edge(thick)))
    lo1, hi1 = clustered_ci(thin)
    diff = et - ek
    print(f"    {label:34} thin {et:+7.2f}pp [{lo1:+6.2f},{hi1:+6.2f}] "
          f"(n={len(thin):>5})   thick {ek:+7.2f}pp (n={len(thick):>5})   "
          f"diff {diff:+7.2f}pp")
    return diff


def main():
    orders, outcomes = H.run(verbose=False)
    rows = H.summarise(orders, outcomes)
    for o, r in zip([o for o in orders if o.ticker in outcomes], rows):
        r["placed"] = o.placed_ts
        et = event_time(o.ticker)
        r["mins_to_event"] = ((et - o.placed_ts).total_seconds() / 60
                              if et else None)
    rows = [r for r in rows if r.get("mins_to_event") is not None]
    filled = [r for r in rows if r["filled"]]
    print(f"{len(rows):,} orders, {len(filled):,} filled, "
          f"{len({r['event'] for r in rows})} events\n")

    results = {}
    for mode in ("join", "improve"):
        sub = [r for r in filled if r["mode"] == mode]
        if len(sub) < 100:
            continue
        med = float(np.median([r["depth_other"] for r in sub]))
        print("=" * 78)
        print(f"{mode.upper()}   n={len(sub):,} filled, "
              f"median far-side depth = {med:.0f}")
        print("=" * 78)

        thin = [r for r in sub if r["depth_other"] <= med]
        thick = [r for r in sub if r["depth_other"] > med]
        base = split_report("BASELINE (the claimed effect)", thin, thick)
        results[f"{mode}.baseline"] = base

        # ---- T1: WITHIN-EVENT. The decisive test. ----
        print(f"\n    T1 — WITHIN-EVENT (does it survive inside one match?)")
        per_ev, wts = [], []
        n_ev = 0
        for ev in {r["event"] for r in sub}:
            e_rows = [r for r in sub if r["event"] == ev]
            e_med = float(np.median([r["depth_other"] for r in e_rows]))
            a = [r for r in e_rows if r["depth_other"] <= e_med]
            b = [r for r in e_rows if r["depth_other"] > e_med]
            if len(a) < 3 or len(b) < 3:
                continue
            n_ev += 1
            per_ev.append(float(np.mean(edge(a)) - np.mean(edge(b))))
            wts.append(min(len(a), len(b)))
        if per_ev:
            w = np.asarray(wts, dtype=float)
            d = np.asarray(per_ev)
            wm = float((d * w).sum() / w.sum())
            rng = np.random.default_rng(SEED)
            bs = np.empty(2000)
            for i in range(2000):
                pick = rng.choice(len(d), size=len(d), replace=True)
                bs[i] = float((d[pick] * w[pick]).sum() / w[pick].sum())
            lo, hi = np.percentile(bs, [2.5, 97.5])
            print(f"      within-event thin-minus-thick = {wm:+7.2f}pp  "
                  f"CI [{lo:+6.2f},{hi:+6.2f}]   ({n_ev} events with both)")
            # THREE-VALUED, because "the point estimate collapsed" and "the
            # interval widened" are different findings and conflating them is
            # how a wrong conclusion gets recorded.
            #
            # v1 printed "DOES NOT SURVIVE - the effect is BETWEEN events"
            # whenever the CI included zero. But the point estimate barely
            # moved (+7.13 within-event against a +9.32 baseline), which means
            # the effect is NOT between-events at all - the within-event test
            # simply has 73 events instead of 81 orders' worth of leverage and
            # cannot resolve it. GUARDS #1's rule applies to any test, not just
            # the selection canary: UNTESTABLE is never rendered as a verdict
            # about the effect.
            kept = wm / base if base else float("nan")
            if lo > 0:
                v = "SURVIVES — real within a match, not a between-event artifact"
            elif abs(kept) > 0.6:
                v = (f"UNDERPOWERED — point estimate keeps {100*kept:.0f}% of "
                     f"the baseline, so it is NOT a between-event artifact, "
                     f"but {n_ev} events cannot resolve it")
            else:
                v = ("COLLAPSES — the effect is BETWEEN events, not within "
                     "them")
            print(f"      baseline was {base:+7.2f}pp  -> {v}")
            results[f"{mode}.within_event"] = {"diff": wm, "ci": [float(lo), float(hi)],
                                               "n_events": n_ev}
        else:
            print("      no event has both arms — untestable")

        # ---- T2: time to event ----
        print(f"\n    T2 — TIME-TO-EVENT confound")
        tmed = float(np.median([r["mins_to_event"] for r in sub]))
        print(f"      median minutes-to-event: thin "
              f"{np.median([r['mins_to_event'] for r in thin]):.0f}  "
              f"thick {np.median([r['mins_to_event'] for r in thick]):.0f}"
              f"   (if these differ a lot, thin IS time)")
        for lab, sel in (("early (>median mins out)",
                          lambda r: r["mins_to_event"] > tmed),
                         ("late  (<median mins out)",
                          lambda r: r["mins_to_event"] <= tmed)):
            a = [r for r in sub if sel(r) and r["depth_other"] <= med]
            b = [r for r in sub if sel(r) and r["depth_other"] > med]
            split_report(lab, a, b)

        # ---- T3: price level ----
        print(f"\n    T3 — PRICE-LEVEL confound")
        print(f"      median price: thin {np.median([r['price'] for r in thin]):.0f}c  "
              f"thick {np.median([r['price'] for r in thick]):.0f}c")
        num = den = 0.0
        for b0 in range(0, 100, 20):
            a = [r for r in sub if b0 <= r["price"] < b0 + 20
                 and r["depth_other"] <= med]
            b = [r for r in sub if b0 <= r["price"] < b0 + 20
                 and r["depth_other"] > med]
            d = split_report(f"price {b0}-{b0+20}c", a, b)
            if d is not None:
                w = min(len(a), len(b))
                num += d * w
                den += w
        if den:
            print(f"      price-stratified thin-minus-thick = "
                  f"{num/den:+7.2f}pp  (baseline {base:+7.2f}pp)")
            results[f"{mode}.price_stratified"] = num / den

        # ---- T4: PLACEBO ----
        print(f"\n    T4 — PLACEBO (parity of the placement minute; must be ~0)")
        a = [r for r in sub if r["placed"].minute % 2 == 0]
        b = [r for r in sub if r["placed"].minute % 2 == 1]
        pl = split_report("even minute vs odd minute", a, b)
        results[f"{mode}.placebo"] = pl
        if pl is not None and base:
            ratio = abs(pl) / abs(base)
            print(f"      -> placebo is {100*ratio:.0f}% of the claimed effect.")
            print(f"         This is the ESTIMATOR'S NOISE FLOOR on an "
                  f"arbitrary split: any real effect must clear it by a wide "
                  f"margin.")
            print(f"         {'!! the effect is not clearly above the noise floor'
                              if ratio > 0.5 else
                              f'the effect is ~{abs(base)/abs(pl):.1f}x the noise floor'}")
        print()

    (REP / "contamination_check.json").write_text(
        json.dumps(results, indent=1, default=str), encoding="utf-8")
    print("wrote reports/contamination_check.json")


if __name__ == "__main__":
    main()
