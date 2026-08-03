"""STEP 3 -- the n-check. Arithmetic, no LLM.

For a claimed win rate over n trades, compute the Wilson score interval and compare
its lower bound to break-even. The Wilson interval is used rather than the normal
(Wald) approximation because Wald is badly wrong at the small n and extreme p that
these claims actually involve -- which is the entire point of the check.

Verdicts:
  SUPPORTED                    lower bound is above break-even
  INDISTINGUISHABLE FROM NOISE interval straddles break-even
  REFUTED                      upper bound is below break-even

Break-even is a parameter, not a constant. For a 50/50 binary bet at no cost it is
0.50, but on a prediction market paying $1 against a price p it is p, and fees
push it higher. Callers pass what applies; the default 0.50 is only a default.
"""

import math

Z95 = 1.959963984540054


def wilson(k, n, z=Z95):
    """Wilson score interval for k successes in n trials. Returns (lo, hi)."""
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0 <= k <= n:
        raise ValueError("k must be in [0, n]")
    p = k / n
    d = 1 + z * z / n
    centre = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - half) / d, (centre + half) / d


def n_check(win_rate, n, breakeven=0.50, z=Z95):
    """win_rate as a fraction (0.55) or a percent (55). Returns a verdict dict."""
    if win_rate is None or n is None:
        return {"verdict": "NOT CHECKABLE", "reason": "missing win_rate or n"}
    if win_rate > 1.0:                      # tolerate "55" meaning 55%
        win_rate = win_rate / 100.0
    if n <= 0:
        return {"verdict": "NOT CHECKABLE", "reason": "n <= 0"}

    k = round(win_rate * n)
    lo, hi = wilson(k, n, z)
    if lo > breakeven:
        verdict = "SUPPORTED"
    elif hi < breakeven:
        verdict = "REFUTED"
    else:
        verdict = "INDISTINGUISHABLE FROM NOISE"

    se = math.sqrt(win_rate * (1 - win_rate) / n)
    return {
        "verdict": verdict,
        "win_rate": round(win_rate, 4),
        "n": n,
        "successes_implied": k,
        "breakeven": breakeven,
        "wilson_lo": round(lo, 4),
        "wilson_hi": round(hi, 4),
        "normal_se_pp": round(100 * se, 2),
        "margin_over_breakeven_pp": round(100 * (lo - breakeven), 2),
        # How many trials this claim WOULD need to clear break-even, holding the
        # rate fixed. This is the number that makes the result concrete.
        "n_needed": n_needed(win_rate, breakeven, z),
    }


def n_needed(win_rate, breakeven=0.50, z=Z95, cap=2_000_000):
    """Smallest n at which this win rate's Wilson lower bound clears break-even."""
    if win_rate <= breakeven:
        return None
    lo_n, hi_n = 1, 1024
    while hi_n < cap:
        k = round(win_rate * hi_n)
        if wilson(k, hi_n, z)[0] > breakeven:
            break
        lo_n, hi_n = hi_n, hi_n * 2
    else:
        return None
    while lo_n < hi_n:                      # binary search the crossing point
        mid = (lo_n + hi_n) // 2
        k = round(win_rate * mid)
        if wilson(k, mid, z)[0] > breakeven:
            hi_n = mid
        else:
            lo_n = mid + 1
    return lo_n


if __name__ == "__main__":
    print("SANITY CHECKS\n" + "=" * 68)

    # The check the brief specifies: 33 trades cannot distinguish 55% from a coin
    # flip. If this line does not say INDISTINGUISHABLE, the code is wrong.
    r = n_check(0.55, 33)
    print(f"55% over n=33   -> {r['verdict']}")
    print(f"   Wilson 95% [{r['wilson_lo']:.3f}, {r['wilson_hi']:.3f}], "
          f"normal SE {r['normal_se_pp']} pp")
    print(f"   would need n = {r['n_needed']} to clear 50%")
    assert r["verdict"] == "INDISTINGUISHABLE FROM NOISE", r
    assert 8.0 < r["normal_se_pp"] < 9.5, r          # brief says SE ~ 8.7pp
    print("   OK -- matches the brief's worked example\n")

    for wr, n, be in [(0.55, 33, 0.50), (0.55, 400, 0.50), (0.55, 1000, 0.50),
                      (0.90, 10, 0.50), (0.30, 200, 0.50), (0.52, 5000, 0.50),
                      (0.60, 50, 0.55), (0.75, 20, 0.50)]:
        r = n_check(wr, n, be)
        need = r["n_needed"] if r["n_needed"] else "-"
        print(f"  {100*wr:>5.1f}% over n={n:<5} vs breakeven {100*be:>4.1f}%  "
              f"[{r['wilson_lo']:.3f},{r['wilson_hi']:.3f}]  "
              f"{r['verdict']:<28} n_needed={need}")

    print("\n  edge cases:")
    print("   ", n_check(None, 33)["verdict"])
    print("   ", n_check(0.55, 0)["verdict"])
    print("   ", f"percent form 55 -> {n_check(55, 33)['win_rate']}")
    assert n_check(55, 33)["win_rate"] == 0.55
    assert n_check(0.90, 10)["verdict"] == "SUPPORTED"
    assert n_check(0.30, 200)["verdict"] == "REFUTED"
    print("\nall assertions passed")
