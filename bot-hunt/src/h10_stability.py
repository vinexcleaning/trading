"""Which H10 statistics CONVERGE as data is added, and which just wander?

Built because the H10 headline flipped sign between 21 and 28 hourly files
(-1.50c -> +0.38c) while the fill rate barely moved (31.0% -> 31.1%). That was
discovered by accident. This measures it on purpose.

The logic is the one that killed this repo's own stars-vs-substance false
positive: measure the statistic over NESTED subsamples of the SAME corpus and
watch the trajectory. A quantity decaying monotonically toward zero as n grows
was a small-sample artifact (rho went +0.241 at n=105 to -0.007 at n=3,165).
A quantity that holds is measuring something.

PERFORMANCE NOTE, recorded because v1 was wrong. v1 re-ran the whole replay for
every prefix, which is O(n^2) in files: 14 cuts over 47 files is ~350 parses of
~200 MB parquet and it had produced nothing after 15 minutes. It is replaced by
replaying ONCE and slicing the resulting orders by placement timestamp, which is
exactly equivalent - an order placed in hour 12 is in the hour-18 prefix and
nothing about it depends on files that came later - and roughly 14x faster.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h10_passive as H  # noqa: E402
import replay as R  # noqa: E402

REP = Path(__file__).resolve().parent.parent / "reports"


def stats_from_rows(rows):
    out = {}
    for mode in ("join", "improve"):
        sub = [r for r in rows if r["mode"] == mode]
        if len(sub) < 50:
            continue
        filled = [r for r in sub if r["filled"]]
        unf = [r for r in sub if not r["filled"]]
        through = [r for r in sub if r["through"]]
        ef = [100 * (r["won"] - r["price"] / 100.0) for r in filled] or [0.0]
        eu = [100 * (r["won"] - r["price"] / 100.0) for r in unf] or [0.0]
        med_depth = float(np.median([x["depth_other"] for x in sub]))
        thin = [100 * (r["won"] - r["price"] / 100.0) for r in filled
                if r["depth_other"] <= med_depth]
        out[mode] = {
            "orders": len(sub),
            "events": len({r["event"] for r in sub}),
            "fill_pct": 100 * len(filled) / len(sub),
            "through_pct": 100 * len(through) / len(sub),
            "net_c": float(np.mean(ef)),
            "advsel_pp": float(np.mean(ef) - np.mean(eu)),
            "thin_edge_pp": float(np.mean(thin)) if len(thin) > 10 else None,
        }
    return out


def main():
    files = R.hours_on_disk()
    print(f"{len(files)} hourly files; replaying ONCE, then slicing by "
          f"placement time\n")
    orders, outcomes = H.run(verbose=True)
    rows = H.summarise(orders, outcomes)
    # attach the placement hour so prefixes can be sliced
    for o, r in zip([o for o in orders if o.ticker in outcomes], rows):
        r["placed"] = o.placed_ts
    rows = [r for r in rows if r.get("placed") is not None]
    if not rows:
        print("no rows")
        return
    t0 = min(r["placed"] for r in rows)
    for r in rows:
        r["hour"] = int((r["placed"] - t0).total_seconds() // 3600)
    max_h = max(r["hour"] for r in rows)
    cuts = [c for c in range(6, max_h + 2, 3)]
    if cuts and cuts[-1] < max_h + 1:
        cuts.append(max_h + 1)

    traj = {}
    for c in cuts:
        sub = [r for r in rows if r["hour"] < c]
        s = stats_from_rows(sub)
        if not s:
            continue
        traj[c] = s
        for mode, v in s.items():
            print(f"  hours<{c:>3} {mode:8} orders={v['orders']:>5} "
                  f"events={v['events']:>4} fill={v['fill_pct']:>5.1f}% "
                  f"through={v['through_pct']:>5.1f}% "
                  f"net={v['net_c']:+6.2f}c advsel={v['advsel_pp']:+7.2f}pp "
                  f"thin={('%+.2f' % v['thin_edge_pp']) if v['thin_edge_pp'] is not None else '    -':>7}pp")

    print("\n" + "=" * 78)
    print("TRAJECTORIES — a statistic that wanders was never a measurement")
    print("=" * 78)
    verdicts = {}
    for mode in ("join", "improve"):
        series = [(c, traj[c][mode]) for c in sorted(traj) if mode in traj[c]]
        if len(series) < 4:
            continue
        print(f"\n{mode.upper()}   (final n = {series[-1][1]['orders']} orders, "
              f"{series[-1][1]['events']} events)")
        for key, unit in (("fill_pct", "%"), ("through_pct", "%"),
                          ("net_c", "c"), ("advsel_pp", "pp"),
                          ("thin_edge_pp", "pp")):
            vals = [v[key] for _, v in series if v.get(key) is not None]
            if len(vals) < 4:
                continue
            half = len(vals) // 2
            first, second = float(np.mean(vals[:half])), float(np.mean(vals[half:]))
            signs = {int(np.sign(v)) for v in vals if abs(v) > 1e-9}
            flip = len(signs) > 1
            span = max(vals) - min(vals)
            scale = abs(float(np.mean(vals))) + 1.0
            if flip:
                verdict = "SIGN-FLIPS — noise"
            elif span < 0.25 * scale:
                verdict = "STABLE"
            elif abs(second) < abs(first) * 0.7:
                verdict = "DECAYING toward zero — artifact signature"
            elif abs(second) > abs(first) * 1.4:
                verdict = "STRENGTHENING — GUARDS #10 warning sign"
            else:
                verdict = "drifting"
            verdicts[f"{mode}.{key}"] = verdict
            print(f"   {key:14} {min(vals):+8.2f}..{max(vals):+8.2f}{unit}"
                  f"  1st half {first:+7.2f} -> 2nd half {second:+7.2f}"
                  f"   -> {verdict}")

    (REP / "h10_stability.json").write_text(
        json.dumps({"trajectory": {str(k): v for k, v in traj.items()},
                    "verdicts": verdicts}, indent=1), encoding="utf-8")
    print("\nwrote reports/h10_stability.json")


if __name__ == "__main__":
    main()
