"""STEP 4 VALIDATION — run BEFORE the engine is pointed at real data.

The brief calls this not optional and this project's history says why: a
synthetic control has caught fabricated profits three separate times, including
+9.46c that came from clipping a random walk and destroying the martingale
property.

Five controls, each with a pre-declared pass condition:

  L1  NULL         no edge planted -> the engine must find none.
  L2  POSITIVE     a 5pp edge planted -> the engine must find ~5pp.
  L3  SENSITIVITY  a 1pp edge planted -> reported with its CI, whatever it says.
                   A null control alone is passed by a pipeline that always
                   reports zero; a positive control alone does not tell you the
                   detection floor.
  L4  LEAK         the mid-price substitution turned on -> the engine must
                   light up. GUARDS #5: plant a LEAK, not an effect, and prove
                   the detector still bites.
  L5  MARTINGALE   the generator's own price process must be a martingale.
                   This is the control that caught the +9.46c: if E[settle|price]
                   != price the data has an edge nobody planted, and L1 would
                   then be measuring the generator, not the engine.

Everything is seeded. Nothing here touches the network.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import Quote, build_trade, cost_bar_cents  # noqa: E402

SEED = 20260804
N_EVENTS = 4000
SPREAD_C = 1.0


def make_events(rng, n, edge_pp=0.0, spread_c=SPREAD_C):
    """Generate n independent binary events.

    The market's mid is the TRUE probability shifted by `edge_pp`. With
    edge_pp = 0 the market is exactly right, so no strategy can profit and the
    process is a martingale by construction — L5 checks that it really is.
    """
    true_p = rng.uniform(0.05, 0.95, size=n)
    mid = np.clip(true_p - edge_pp / 100.0, 0.01, 0.99)
    settled = rng.random(n) < true_p
    bid = np.clip(mid * 100.0 - spread_c / 2.0, 0.5, 99.5)
    ask = np.clip(mid * 100.0 + spread_c / 2.0, 0.5, 99.5)
    return true_p, mid, settled, bid, ask


def run(rng, n, edge_pp, mark_to_mid=False, spread_c=SPREAD_C):
    """Buy YES on every event. Report net cents/contract with a bootstrap CI.

    Deliberately the dumbest possible strategy: it isolates the ENGINE. Any
    non-zero result at edge_pp=0 is the engine or the generator, not a strategy.
    """
    true_p, mid, settled, bid, ask = make_events(rng, n, edge_pp, spread_c)
    nets, edges, fees, slips = [], [], [], []
    for i in range(n):
        q = Quote(ts=float(i), bid_c=float(bid[i]), ask_c=float(ask[i]),
                  bid_size=500.0, ask_size=500.0, ref_prob=float(true_p[i]))
        t = build_trade(f"M{i}", cluster=f"E{i}", q_in=q, side="yes",
                        settled_yes=bool(settled[i]), contracts=1,
                        ref_prob=None, mark_to_mid=mark_to_mid)
        nets.append(t.net_c)
        edges.append(t.edge_c)
        fees.append(t.fee_c)
        slips.append(t.slippage_c)
    nets = np.asarray(nets)
    boot = rng.choice(nets, size=(4000, n), replace=True).mean(axis=1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {
        "n": n, "mean_c": float(nets.mean()), "ci": (float(lo), float(hi)),
        "contains_zero": bool(lo <= 0.0 <= hi),
        "mean_fee_c": float(np.mean(fees)),
        "mean_slip_c": float(np.mean(slips)),
        "cost_bar_c": cost_bar_cents(50.0, spread_c, slippage_c=0.0),
    }


def main() -> None:
    rng = np.random.default_rng(SEED)
    fails = []

    print("=" * 74)
    print("L5  MARTINGALE CHECK on the generator itself")
    print("    null: E[settle | mid] == mid, in every price bucket.")
    true_p, mid, settled, bid, ask = make_events(
        np.random.default_rng(SEED + 5), 200_000, edge_pp=0.0)
    bad = 0
    for lo in np.arange(0.05, 0.95, 0.10):
        m = (mid >= lo) & (mid < lo + 0.10)
        if m.sum() < 200:
            continue
        obs, exp = settled[m].mean(), mid[m].mean()
        se = math.sqrt(max(exp * (1 - exp), 1e-9) / m.sum())
        z = (obs - exp) / se
        flag = "" if abs(z) < 4 else "   <-- FAIL"
        if abs(z) >= 4:
            bad += 1
        print(f"    mid {lo:.2f}-{lo+0.10:.2f}  n={m.sum():>6} "
              f"obs={obs:.4f} exp={exp:.4f}  z={z:+.2f}{flag}")
    print(f"    -> {'PASS' if bad == 0 else 'FAIL'} "
          f"({bad} buckets beyond |z|=4)")
    if bad:
        fails.append("L5 martingale")

    print("=" * 74)
    print("L1  NULL CONTROL — no edge planted. Engine must find none.")
    # n is 10x the strategy runs: this control decides whether every later
    # number is trustworthy, so it should not be the underpowered one.
    r = run(np.random.default_rng(SEED + 1), N_EVENTS * 10, edge_pp=0.0)
    # The market is fair, so the ONLY expected loss is half-spread + fee. The
    # engine must report that and nothing more.
    expected = -(SPREAD_C / 2.0) + r["mean_fee_c"]
    print(f"    net {r['mean_c']:+.4f}c  CI [{r['ci'][0]:+.4f}, {r['ci'][1]:+.4f}]"
          f"  n={r['n']}")
    print(f"    expected from cost alone: {expected:+.4f}c "
          f"(half-spread {-SPREAD_C/2:+.3f} + fee {r['mean_fee_c']:+.4f})")
    # THE PASS CONDITION IS STATISTICAL, NOT A MAGIC TOLERANCE.
    #
    # v1 of this file asserted |observed - expected| < 0.25c and FAILED at
    # -0.258c. The bootstrap SE at n=4,000 is ~0.66c, so that gap is z ~= -0.4:
    # the tolerance was tighter than the noise, and the failure was mine, not
    # the engine's. A fixed threshold on a sampling distribution is exactly the
    # error GUARDS #8 exists to prevent, and it is worth having made it here in
    # a control rather than later in a result.
    ok = r["ci"][0] <= expected <= r["ci"][1] and r["mean_c"] < 0
    print(f"    cost-only expectation inside the bootstrap CI: "
          f"{r['ci'][0] <= expected <= r['ci'][1]}")
    print(f"    -> {'PASS' if ok else 'FAIL'} — no edge is manufactured; the "
          f"loss is indistinguishable from the cost")
    if not ok:
        fails.append("L1 null")

    print("=" * 74)
    print("L2  POSITIVE CONTROL — 5pp edge planted. Engine must find it.")
    r5 = run(np.random.default_rng(SEED + 2), N_EVENTS, edge_pp=5.0)
    detected = r5["mean_c"] - r["mean_c"]
    print(f"    net {r5['mean_c']:+.4f}c  CI [{r5['ci'][0]:+.4f}, "
          f"{r5['ci'][1]:+.4f}]")
    print(f"    net minus the null run = {detected:+.4f}c against 5.00c planted")
    ok = 3.5 < detected < 6.5 and r5["ci"][0] > 0
    print(f"    -> {'PASS' if ok else 'FAIL'}")
    if not ok:
        fails.append("L2 positive")

    print("=" * 74)
    print("L3  SENSITIVITY FLOOR — 1pp edge planted. Reported as measured.")
    r1 = run(np.random.default_rng(SEED + 3), N_EVENTS, edge_pp=1.0)
    d1 = r1["mean_c"] - r["mean_c"]
    print(f"    net {r1['mean_c']:+.4f}c  CI [{r1['ci'][0]:+.4f}, "
          f"{r1['ci'][1]:+.4f}]")
    print(f"    detected {d1:+.4f}c against 1.00c planted; CI excludes zero: "
          f"{not r1['contains_zero']}")
    print(f"    -> this is the DETECTION FLOOR at n={N_EVENTS}. A null result "
          f"below it means nothing.")

    print("=" * 74)
    print("L4  DELIBERATE LEAK — mark at the mid instead of the ask.")
    print("    The engine MUST report a better number. If it does not, the "
          "no-mid rule is not actually enforced.")
    rl = run(np.random.default_rng(SEED + 1), N_EVENTS, edge_pp=0.0,
             mark_to_mid=True)
    lift = rl["mean_c"] - r["mean_c"]
    print(f"    honest {r['mean_c']:+.4f}c   at-the-mid {rl['mean_c']:+.4f}c   "
          f"lift {lift:+.4f}c")
    ok = lift > 0.2
    print(f"    -> {'PASS' if ok else 'FAIL'} — the detector bites. Half the "
          f"quoted spread is exactly what T008 recovered by marking at the mid.")
    if not ok:
        fails.append("L4 leak")

    print("=" * 74)
    if fails:
        print(f"ENGINE NOT VALIDATED. Failures: {fails}")
        sys.exit(1)
    print("ENGINE VALIDATED on all five controls. It may now be pointed at "
          "real data — and not before.")


if __name__ == "__main__":
    main()
