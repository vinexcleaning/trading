"""Which H10 statistics CONVERGE as data is added, and which just wander?

Built because the H10 headline flipped sign between 21 and 28 hourly files
(-1.50c -> +0.38c) while the fill rate barely moved (31.0% -> 31.1%). That was
discovered by accident. This measures it on purpose.

The logic is the same one this repo used to kill the stars-vs-substance
correction: measure the statistic over NESTED subsamples of the SAME corpus and
watch the trajectory. A quantity that decays monotonically toward zero as n
grows was a small-sample artifact (signal-github: rho went +0.241 at n=105 to
-0.007 at n=3,165). A quantity that holds is measuring something.

This is cheap - the replay is the only expensive part and it is re-run per
prefix, which is the honest way: a cumulative statistic computed by patching
earlier results would hide exactly the instability being looked for.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import replay as R  # noqa: E402
import h10_passive as H  # noqa: E402

REP = Path(__file__).resolve().parent.parent / "reports"


def stats_for(files, outcomes):
    """Run the H10 simulation over `files` only and return the headline stats."""
    live, done, last_place = defaultdict(list), [], {}
    from datetime import timedelta
    from diagnose_cross import event_time

    def on_event(ts, tk, bk, i, d):
        et = event_time(tk)
        if et is None or ts >= et or tk not in outcomes:
            return
        yb, nb = bk.best_yes_bid(), bk.best_no_bid()
        if yb is None or nb is None:
            return
        ask = 100 - nb
        if ask <= yb:
            return
        side, price_c = d["side"][i], R.to_cents(d["price"][i])
        delta = float(d["delta"][i])
        still = []
        for o in live[tk]:
            if side == "yes" and price_c == o.price and delta < 0:
                o.removed += -delta
            if o.mode == "join":
                bb = bk.best_yes_bid()
                if bb is not None and bb < o.price:
                    o.through = True
            if o.removed > o.queue_ahead and o.filled_ts is None:
                o.filled_ts = ts
                done.append(o)
                continue
            if ts - o.placed_ts > timedelta(minutes=180) or ts >= et:
                done.append(o)
                continue
            still.append(o)
        live[tk] = still
        for mode in ("join", "improve"):
            key = (tk, mode)
            lp = last_place.get(key)
            if lp is not None and ts - lp < timedelta(minutes=20):
                continue
            if mode == "join":
                p, qa = yb, bk.size_at("yes", yb)
            else:
                p = yb + 1
                if p >= ask:
                    continue
                qa = bk.size_at("yes", p)
            if p < 1 or p > 99:
                continue
            last_place[key] = ts
            live[tk].append(H.Order(tk, p, qa, ts, mode, yb, ask,
                                    bk.depth("no", 5), ask - yb))

    R.replay(files, on_event=on_event, verbose=False)
    for os_ in live.values():
        done.extend(os_)
    rows = H.summarise(done, outcomes)

    out = {}
    for mode in ("join", "improve"):
        sub = [r for r in rows if r["mode"] == mode]
        if len(sub) < 50:
            continue
        filled = [r for r in sub if r["filled"]]
        unf = [r for r in sub if not r["filled"]]
        through = [r for r in sub if r["through"]]
        edge_f = [100 * (r["won"] - r["price"] / 100.0) for r in filled] or [0]
        edge_u = [100 * (r["won"] - r["price"] / 100.0) for r in unf] or [0]
        thin = [100 * (r["won"] - r["price"] / 100.0) for r in filled
                if r["depth_other"] <= np.median([x["depth_other"] for x in sub])]
        out[mode] = {
            "orders": len(sub),
            "events": len({r["event"] for r in sub}),
            "fill_pct": 100 * len(filled) / len(sub),
            "through_pct": 100 * len(through) / len(sub),
            "net_c": float(np.mean(edge_f)),
            "advsel_pp": float(np.mean(edge_f) - np.mean(edge_u)),
            "thin_edge_pp": float(np.mean(thin)) if len(thin) > 10 else None,
        }
    return out


def main():
    outcomes = H.load_outcomes()
    files = R.hours_on_disk()
    print(f"{len(files)} hourly files available\n")
    cuts = [c for c in (6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 40, 44, 48)
            if c <= len(files)]
    if cuts and cuts[-1] != len(files):
        cuts.append(len(files))

    traj = {}
    for c in cuts:
        s = stats_for(files[:c], outcomes)
        traj[c] = s
        for mode, v in s.items():
            print(f"  hours={c:>3} {mode:8} orders={v['orders']:>5} "
                  f"events={v['events']:>4} fill={v['fill_pct']:>5.1f}% "
                  f"through={v['through_pct']:>5.1f}% "
                  f"net={v['net_c']:+6.2f}c advsel={v['advsel_pp']:+7.2f}pp "
                  f"thin={('%+.2f' % v['thin_edge_pp']) if v['thin_edge_pp'] is not None else '    -':>7}pp",
                  flush=True)
        print()

    print("=" * 78)
    print("TRAJECTORIES — a statistic that wanders was never a measurement")
    print("=" * 78)
    for mode in ("join", "improve"):
        series = [(c, traj[c][mode]) for c in cuts if mode in traj[c]]
        if len(series) < 3:
            continue
        print(f"\n{mode.upper()}")
        for key, unit in (("fill_pct", "%"), ("through_pct", "%"),
                          ("net_c", "c"), ("advsel_pp", "pp"),
                          ("thin_edge_pp", "pp")):
            vals = [v[key] for _, v in series if v.get(key) is not None]
            if len(vals) < 3:
                continue
            rng_ = max(vals) - min(vals)
            last3 = vals[-3:]
            drift = abs(last3[-1] - last3[0])
            signs = {np.sign(v) for v in vals if v != 0}
            flip = len(signs) > 1
            verdict = ("STABLE" if rng_ < 0.15 * (abs(np.mean(vals)) + 1e-9) + 2
                       else ("SIGN-FLIPS — noise" if flip else "drifting"))
            print(f"   {key:14} range {min(vals):+8.2f}..{max(vals):+8.2f}{unit}"
                  f"  span {rng_:6.2f}  last-3 drift {drift:5.2f}  -> {verdict}")

    (REP / "h10_stability.json").write_text(
        json.dumps({str(k): v for k, v in traj.items()}, indent=1),
        encoding="utf-8")
    print("\nwrote reports/h10_stability.json")


if __name__ == "__main__":
    main()
