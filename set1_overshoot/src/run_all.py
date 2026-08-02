"""Run the whole study end to end, in order, once the candle pull has landed.

Phase 2's gate is enforced here rather than by hand: if the base effect does not
clear its cost breakeven, Phase 3 does not run. Slicing a null into subgroups
until one looks positive is how this project produced four false positives.
"""
import pathlib
import subprocess
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
DATA = ROOT / "data"
PY = sys.executable


def run(script, *args, must=True):
    print(f"\n{'=' * 78}\n$ {script} {' '.join(args)}\n{'=' * 78}", flush=True)
    r = subprocess.run([PY, str(SRC / script), *args], cwd=str(SRC))
    if r.returncode and must:
        sys.exit(f"{script} failed with {r.returncode}")
    return r.returncode


def main():
    import ledger

    run("p0_mirror.py", must=False)
    run("p1_state.py", "--subdir", "candles", "--out", "paths")
    run("p1_tune_t0.py", must=False)
    run("p1_validate.py")

    ledger.reset()
    run("p2_calib.py", "--tag", "paths", "--out", "p2_base.txt", "--grid")

    # ---- the Phase 2 gate --------------------------------------------------
    import numpy as np
    import p2_calib as p2
    st, bid, ask, mid = p2.load("paths")
    ev = p2.build_events(st, bid, ask, mid, p2.BASE_RULE, p2.BASE_OFFSET)
    e = ev[ev["is_event"]]
    rng = np.random.default_rng(3)
    p = (e["entry_mid"] / 100.0).values
    win = e["fav_won"].values
    mis = 100 * (win - p)
    lo, hi = p2.bootstrap_ci(mis, rng)
    net, fill, fee = p2.costed(e["entry_mid"].values, e["entry_ask"].values, win)
    nlo, nhi = p2.bootstrap_ci(net, rng)

    print(f"\n{'#' * 78}\n# PHASE 2 GATE\n{'#' * 78}")
    print(f"n = {len(e):,}")
    print(f"miscalibration {mis.mean():+.2f} pp, 95% CI [{lo:+.2f}, {hi:+.2f}]")
    print(f"net expectancy {net.mean():+.3f} c, 95% CI "
          f"[{nlo:+.3f}, {nhi:+.3f}]")

    clears = nhi > 0 and hi > 0
    if not clears:
        print("\nGATE NOT CLEARED. The base effect does not reach zero net "
              "expectancy at\nthe upper end of its confidence interval. "
              "Phase 3 is SKIPPED by design.")
    else:
        print("\nGate cleared -- running Phase 3.")
        run("p3_segment.py", "--tag", "paths", "--out", "p3_segments.md")

    run("p4_validate.py", "--tag", "paths")
    ledger.finalise(q=0.10)
    print("\nall done")


if __name__ == "__main__":
    sys.path.insert(0, str(SRC))
    main()
