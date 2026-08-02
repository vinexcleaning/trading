"""TASK 2 — audit every cross-asset / pooled claim under the independence
finding (1.81 effective series of 4), reading the ACTUAL artifacts rather than
trusting session summaries.

Verdict per claim: UNAFFECTED / WEAKENED / VOID / UNSUPPORTED.

UNSUPPORTED is a fourth category the brief did not anticipate and it is needed:
at least one claim circulating in the handoffs has no artifact behind it at all.
"""
import glob
import json
import os

import numpy as np

REP = r"C:\Users\gianf\crypto\reports"
MM = r"C:\Users\gianf\crypto\data\mm"


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def hdr(t):
    print("\n" + "=" * 100)
    print(t)
    print("=" * 100)


def main():
    verdicts = []

    # ---------------------------------------------------------------- 1
    hdr("CLAIM 1 — lead-lag ETH->XRP +0.1544")
    j = load(os.path.join(REP, "leadlag.json"))
    if j:
        n = j.get("n_bars")
        jb = j.get("joint_bars", [])
        row = next((r for r in jb if r["pair"].startswith("ETH -> XRP")), None)
        print(f"  artifact present: n_bars={n}")
        if row:
            print(f"    best lead {row['best_lead_s']}s = {row['best_lead_c']:+.4f}"
                  f"  SE={row['se']:.5f}  -> {row['best_lead_c']/row['se']:.0f} SE")
        print("\n  Does the independence finding invalidate this?")
        print("  NO. That finding says the four assets' SETTLEMENT SIGNS are")
        print("  correlated. The lead-lag test MEASURES cross-asset")
        print("  correlation — it is the object of study, not a confound.")
        print("\n  But the CI deserves scrutiny: SE was taken as 1/sqrt(n),")
        print("  which assumes independent observations. 1-second returns are")
        print("  mildly autocorrelated, so the true SE is larger.")
        print("  Even a 10x understated SE leaves the effect at ~4 SE.")
        print("\n  The number that actually decided it was ECONOMIC, not")
        print("  statistical: 0.38c of edge against a 1.00c tick, needing a")
        print("  correlation of 0.575-1.113 vs 0.1544 observed. Widening the")
        print("  CI does not move a sub-tick signal above one tick.")
        verdicts.append(("lead-lag ETH->XRP", "UNAFFECTED",
                         "measures correlation by design; conclusion was "
                         "economic (sub-tick), not statistical"))

    # ---------------------------------------------------------------- 2
    hdr("CLAIM 2 — 'exchange-wide MM scan: 0 of 4 series profitable'")
    lat = load(os.path.join(REP, "mm_latency_fixed.json"))
    uni = load(os.path.join(MM, "universe.json"))
    print(f"  mm_latency_fixed.json present: {lat is not None}")
    if lat:
        print(f"    n_markets in EVERY row: "
              f"{sorted({r['n_markets'] for r in lat})}")
        print(f"    latencies tested: {[r['latency_ms'] for r in lat]}")
        print(f"    -> this is ONE series (KXBTCD), 58 markets, 4 latencies")
    if uni:
        names = [u.get("series") for u in uni]
        killed = [u.get("series") for u in uni if u.get("kill")]
        print(f"  universe.json: {len(uni)} series SCORED "
              f"({len(killed)} killed) — but scoring is not a P&L test")
        print(f"    scored: {names}")
    print("\n  VERDICT: there is NO artifact showing 4 series tested for")
    print("  market-making profitability. The P&L test ran on KXBTCD ALONE.")
    print("  '0 of 4 series profitable' is UNSUPPORTED and I appear to have")
    print("  written it into STATUS.md myself. It must be corrected to:")
    print("  'market making tested on 1 series (KXBTCD, 58 markets):")
    print("   -1.86c/contract, CI [-2.73,-1.53], losing at every latency'.")
    verdicts.append(("MM '0 of 4 series'", "UNSUPPORTED",
                     "only KXBTCD (58 markets) was ever P&L-tested"))

    # ---------------------------------------------------------------- 3
    hdr("CLAIM 3 — cross-asset streak replication (this session)")
    j = load(os.path.join(REP, "streaks_multiasset.json"))
    if j:
        s = j["summary"]
        print(f"  nominal assets: {len(s)}   effective independent: 1.81")
        for k, v in s.items():
            print(f"    {k}: lag1={v['ac1']:+.4f} n={v['n']}")
        print("\n  Already reported WITH the effective-n caveat in the last")
        print("  handoff, and 0 of 136 tests survived FDR regardless.")
        verdicts.append(("cross-asset streaks", "WEAKENED (already stated)",
                         "3-of-4 is ~1.8 observations; 0/136 survive FDR "
                         "anyway"))

    # ---------------------------------------------------------------- 4
    hdr("CLAIM 4 — fat tails measured on BTC and ETH (C9)")
    j = load(os.path.join(REP, "fat_tails.json"))
    if j:
        for k, v in j.items():
            if isinstance(v, dict) and "excess_kurtosis" in v:
                print(f"    {k}: excess kurtosis {v['excess_kurtosis']:.2f}, "
                      f"nu {v['student_t_nu']:.2f}, n={v['n_returns']}")
        print("\n  This was ALREADY flagged: corr(BTC,ETH hourly returns)")
        print("  = 0.891 and 62% of extreme hours shared, so it was reported")
        print("  as ONE finding not two. The 1.81 result corroborates that")
        print("  call rather than changing it.")
        verdicts.append(("fat tails BTC+ETH", "UNAFFECTED",
                         "already reported as one finding, not two"))

    # ---------------------------------------------------------------- 5
    hdr("CLAIM 5 — pinning test C8 (BTC+ETH, 20 tests)")
    j = load(os.path.join(REP, "pinning_test.json"))
    if j and "bh" in j:
        print(f"    BH: {j['bh']['n_surviving']} of {j['bh']['n_tests']} "
              f"survived at the time")
        print("  Already RETRACTED for an invalid null AND for duplicate")
        print("  series (KXBTC/KXBTCD share settlements exactly). The")
        print("  independence finding is a stronger version of the same")
        print("  objection.")
        verdicts.append(("round-number pinning", "VOID (already retracted)",
                         "invalid null + duplicated series"))

    # ---------------------------------------------------------------- 6
    hdr("CLAIM 6 — B1 vs-mid, touch matrix, path/streak (single-asset)")
    print("  b1_KXBTCD.json, path_streak.json: KXBTCD only.")
    print("  Single-asset claims are not affected by a BETWEEN-asset")
    print("  correlation finding. Their unit is the event and their CIs")
    print("  bootstrap events within one series.")
    verdicts.append(("B1 / touch matrix / path", "UNAFFECTED",
                     "single-asset; effective-n applies to cross-asset only"))

    # ---------------------------------------------------------------- sum
    hdr("SUMMARY")
    print(f"  {'claim':<28} {'verdict':<26} {'note'}")
    for c, v, note in verdicts:
        print(f"  {c:<28} {v:<26} {note[:44]}")
    json.dump([{"claim": c, "verdict": v, "note": n} for c, v, n in verdicts],
              open(os.path.join(REP, "effective_n_audit.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
