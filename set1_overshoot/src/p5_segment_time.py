"""Time-of-day and tier segmentation, with the cost bar computed PER BUCKET.

The Phase 3 gate is lifted for this test only; the justification is in
PREREGISTRATION_PARTB.md 5c. In short: the gate stops the slicing of a null, and
theta is not null.

The identity that makes the table honest:

    effect_pp = 100 * (observed  - implied)
    bar_pp    = 100 * (breakeven - implied)      breakeven = (fill + fee) / 100
    net_c     = effect_pp - bar_pp               == 100*observed - fill - fee

so the three columns are not three separate estimates, they are a decomposition
that must add up. A bucket whose effect grows while its bar grows faster is a
loss, and a pooled bar would conceal it.
"""
import pathlib

import numpy as np
import pandas as pd

import fees
import ledger
import leakguard as lg
import p2_calib as p2

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

MIN_N = 150            # below this a cell is not reported as a result
SD_ASSUMED = 45.0      # per-contract sd, for the MDE
Z_A, Z_B = 1.96, 0.8416


def mde_cents(n):
    return (Z_A + Z_B) * SD_ASSUMED / np.sqrt(max(n, 1))


def cells(e, rng):
    """Per-bucket effect / bar / net, on the FADE (buy the underdog)."""
    fav_mid = e["entry_mid"].values
    fav_bid = e["entry_bid"].values
    implied = (100.0 - fav_mid) / 100.0
    fill = np.minimum(100.0 - fav_bid + p2.SLIP, 99.0)
    fee = np.array([float(fees.fee_rate_cents(int(round(f)))) for f in fill])
    obs = 1.0 - e["fav_won"].values
    net = 100.0 * obs - fill - fee
    breakeven = (fill + fee) / 100.0
    return implied, obs, breakeven, net


def row(e, label, rng, w, phase, factor, results):
    n = len(e)
    if n < MIN_N:
        w(f"| {label} | {n:,} | – | – | – | – | *n < {MIN_N}* |")
        ledger.add(phase=phase, factor=factor, level=label, n=n,
                   note=f"skipped, n<{MIN_N}")
        return None
    implied, obs, be, net = cells(e, rng)
    eff = 100 * (obs.mean() - implied.mean())
    bar = 100 * (be.mean() - implied.mean())
    lo, hi = p2.bootstrap_ci(net, rng, n=4000)
    m = mde_cents(n)
    _, two = p2.poisson_binom_p(int(obs.sum()), implied, rng)
    testable = abs(net.mean()) >= m
    verdict = ("**CLEARS**" if net.mean() > 0 and lo > 0 else
               "positive, CI spans 0" if net.mean() > 0 else
               "loses")
    if not testable and net.mean() > 0:
        verdict = f"UNTESTABLE (MDE {m:.2f}¢)"
    w(f"| {label} | {n:,} | {eff:+.2f} | {bar:+.2f} | **{net.mean():+.3f}** | "
      f"[{lo:+.2f}, {hi:+.2f}] | {verdict} |")
    ledger.add(phase=phase, factor=factor, level=label, n=n,
               mis_pp=round(eff, 3), ci_lo=round(lo, 3), ci_hi=round(hi, 3),
               p_two=round(two, 5), net_c=round(net.mean(), 4),
               note=f"bar {bar:+.2f}pp; MDE {m:.2f}c")
    results.append({"label": label, "n": n, "eff": eff, "bar": bar,
                    "net": net.mean(), "lo": lo, "hi": hi, "mde": m,
                    "net_arr": net, "mask_index": e.index})
    return results[-1]


def main():
    st, bid, ask, mid = p2.load("paths")
    rng = np.random.default_rng(8080)
    ev = p2.build_events(st, bid, ask, mid, "deep:30", 0, min_minute=38)
    ev["row"] = np.arange(len(ev))
    e = ev[ev["is_event"]].copy()

    # entry timestamp = t0 + entry minute. That is when the order is placed.
    t0 = pd.to_numeric(st["t0_epoch"], errors="coerce").values
    e["entry_ts"] = t0[e["row"].values] + e["entry_idx"].values * 60
    t = pd.to_datetime(e["entry_ts"], unit="s", utc=True)
    e["utc_h"] = t.dt.hour
    e["est_h"] = (t.dt.hour - 4) % 24            # EDT = UTC-4 in August
    e["utc_b"] = (e["utc_h"] // 4) * 4
    e["est_b"] = (e["est_h"] // 4) * 4
    e["close_time"] = pd.to_datetime(e["close_time"], utc=True)

    out, results = [], []

    def w(s=""):
        print(s, flush=True)
        out.append(s)

    w("# Time-of-day and tier segmentation")
    w("")
    w("**Gate lifted for this test only.** Justification in "
      "`PREREGISTRATION_PARTB.md` §5c:")
    w("the Phase 3 gate exists to stop slicing a *null*, and θ = −2.42 pp "
      "(p = 0.0009) is")
    w("not null. Buckets were fixed before running.")
    w("")
    w("**Power, computed in advance.** Per-contract sd ≈ 45 ¢, so detecting a "
      "+2 ¢ edge at")
    w("80% power needs **n ≈ 3,970**. The whole event sample is "
      f"**{len(e):,}**. No bucket can")
    w("be individually powered for a 2 ¢ edge. Each cell reports its own MDE; "
      "a cell whose")
    w("apparent edge is smaller than its MDE is marked UNTESTABLE.")
    w("")
    w("`effect` = 100×(observed − implied). `bar` = 100×(breakeven − implied), "
      "**computed")
    w("per bucket**. `net` = effect − bar, exactly, and equals ¢/contract.")
    w("")

    hdr = ("| bucket | n | effect pp | bar pp | net ¢ | 95% CI | verdict |\n"
           "|---|---|---|---|---|---|---|")

    imp, obs, be, net = cells(e, rng)
    w("## Pooled reference")
    w("")
    w(hdr)
    row(e, "ALL", rng, w, "5-seg", "pooled", results)
    w("")

    w("## T1 — entry hour, UTC, 4-hour blocks")
    w("")
    w(hdr)
    for b in sorted(e["utc_b"].unique()):
        row(e[e["utc_b"] == b], f"{b:02d}:00–{b + 4:02d}:00 UTC", rng, w,
            "5-seg", "T1 hour UTC", results)
    w("")

    w("## T2 — entry hour, US/Eastern (EDT)")
    w("")
    w(hdr)
    for b in sorted(e["est_b"].unique()):
        row(e[e["est_b"] == b], f"{b:02d}:00–{b + 4:02d}:00 ET", rng, w,
            "5-seg", "T2 hour ET", results)
    w("")

    w("## T3 — tier")
    w("")
    w(hdr)
    for tr in sorted(e["tour"].unique()):
        row(e[e["tour"] == tr], tr, rng, w, "5-seg", "T3 tier", results)
    w("")

    w("## T4 — hour × tier (cells with n ≥ 150)")
    w("")
    w(hdr)
    n4 = 0
    for tr in sorted(e["tour"].unique()):
        for b in sorted(e["est_b"].unique()):
            sub = e[(e["tour"] == tr) & (e["est_b"] == b)]
            if len(sub) < MIN_N:
                continue
            n4 += 1
            row(sub, f"{tr} @ {b:02d}:00–{b + 4:02d}:00 ET", rng, w,
                "5-seg", "T4 hour x tier", results)
    if n4 == 0:
        w("| *no cell reaches n ≥ 150* | – | – | – | – | – | – |")
    w("")

    # ---- tier composition by hour: tests explanation (c) -----------------
    w("## Does tier composition explain the hour pattern?")
    w("")
    w("The live observation was profit overnight and losses once the main "
      "tournaments")
    w("started. If that is really a *tier* effect wearing an *hour* costume, "
      "the mix below")
    w("will show it.")
    w("")
    mix = pd.crosstab(e["est_b"], e["tour"], normalize="index") * 100
    cnt = e.groupby("est_b").size()
    w("| ET block | n | " + " | ".join(mix.columns) + " | median spread ¢ |")
    w("|---" * (len(mix.columns) + 3) + "|")
    for b in mix.index:
        sp = e.loc[e["est_b"] == b, "entry_spread"].median()
        w(f"| {b:02d}:00–{b + 4:02d}:00 | {cnt[b]:,} | "
          + " | ".join(f"{mix.loc[b, c]:.0f}%" for c in mix.columns)
          + f" | {sp:.1f} |")
    w("")

    # ---- multiplicity ----------------------------------------------------
    tested = [r for r in results if r["label"] != "ALL"]
    pos = [r for r in tested if r["net"] > 0]
    clear = [r for r in tested if r["lo"] > 0]
    w("## Multiplicity — how many buckets should look good by chance")
    w("")
    w(f"- buckets tested: **{len(tested)}**")
    w(f"- buckets with positive mean net: **{len(pos)}**")
    w(f"- expected positive by chance if every bucket were truly zero: "
      f"**{len(tested) / 2:.1f}**")
    w(f"- buckets with a 95% CI entirely above zero: **{len(clear)}**")
    w(f"- expected by chance at 5%, one-sided: "
      f"**{len(tested) * 0.025:.2f}**")
    w("")
    if clear:
        w("### Two-period split and holdout on every bucket that clears")
        w("")
        w("| bucket | full net ¢ | train net ¢ | **holdout net ¢** | verdict |")
        w("|---|---|---|---|---|")
        cut = e["close_time"].quantile(0.60)
        for r in clear:
            sub = e.loc[r["mask_index"]]
            tr_ = sub[sub["close_time"] <= cut]
            ho_ = sub[sub["close_time"] > cut]
            def nm(x):
                if len(x) < 30:
                    return None
                _, _, _, nn = cells(x, rng)
                return nn.mean()
            a, b_ = nm(tr_), nm(ho_)
            verdict = ("**survives**" if b_ is not None and b_ > 0
                       else "*dies on holdout*" if b_ is not None
                       else "*holdout too small*")
            w(f"| {r['label']} | {r['net']:+.3f} | "
              f"{'–' if a is None else f'{a:+.3f}'} | "
              f"{'–' if b_ is None else f'{b_:+.3f}'} | {verdict} |")
        w("")
    else:
        w("**No bucket has a confidence interval above zero.** Nothing to "
          "holdout-test.")
        w("")

    (ROOT / "reports" / "p5_segment_time.md").write_text("\n".join(out),
                                                         encoding="utf-8")
    print(f"\n-> {ROOT / 'reports' / 'p5_segment_time.md'}")


if __name__ == "__main__":
    main()
