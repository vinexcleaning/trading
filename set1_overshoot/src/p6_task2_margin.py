"""TASK 2 (C3) -- selection on set-1 margin, with the cost bar computed PER BUCKET.

Specified as "reuses Task 1's data". Task 1 is blocked (Apify hard limit +
dayOffsets range), so this runs on the EXISTING truth set, which already carries
set-1 game scores. The blocker removed the extra labels, not the existing ones.

Buckets pre-registered in the task brief before running:
  margin 6-0/6-1, 6-2/6-3, 6-4/7-5, 7-6 ; tiebreak flag ; best-of ; games in set 1

Expected outcome, stated in advance: at n=479 label-verified events, buckets run
n~60-180 and MDE is 7-12 c. Almost everything will be UNTESTABLE. That is the
honest result, not a failure to find something.
"""
import pathlib
import re

import numpy as np
import pandas as pd

import fees
import ledger
import leakguard as lg
import p2_calib as p2

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = []
# NB: the cost bar is deliberately NOT a constant anywhere in this file. It is
# recomputed inside every bucket from that bucket's own quotes, which is the
# whole point of the task. A module-level BAR_REF existed briefly and was
# removed unused -- a hard-coded bar is exactly how a pooled figure leaks into
# a per-bucket table.


def w(s=""):
    print(s, flush=True)
    OUT.append(s)


def cell(e, label, rng, factor, min_n=40):
    n = len(e)
    if n < min_n:
        w(f"| {label} | {n} | – | – | – | – | *n<{min_n}* |")
        ledger.add(phase="6-margin", factor=factor, level=label, n=n,
                   note=f"skipped n<{min_n}")
        return None
    fb = e["entry_bid"].values
    fm = e["entry_mid"].values
    imp = (100.0 - fm) / 100.0
    fill = np.minimum(100.0 - fb + p2.SLIP, 99.0)
    fee = np.array([float(fees.fee_rate_cents(int(round(f)))) for f in fill])
    obs = 1.0 - e["fav_won"].values
    net = 100.0 * obs - fill - fee
    eff = 100 * (obs.mean() - imp.mean())
    bar = 100 * (((fill + fee) / 100.0).mean() - imp.mean())
    lo, hi = p2.bootstrap_ci(net, rng, n=6000)
    mde = (1.96 + 0.8416) * net.std() / np.sqrt(n)
    _, two = p2.poisson_binom_p(int(obs.sum()), imp, rng)
    if lo > 0:
        v = "**CLEARS**"
    elif net.mean() > 0 and net.mean() < mde:
        v = f"UNTESTABLE (MDE {mde:.1f}¢)"
    elif net.mean() > 0:
        v = "positive, CI spans 0"
    else:
        v = "loses"
    w(f"| {label} | {n} | {eff:+.2f} | {bar:+.2f} | **{net.mean():+.2f}** | "
      f"[{lo:+.1f}, {hi:+.1f}] | {v} |")
    ledger.add(phase="6-margin", factor=factor, level=label, n=n,
               mis_pp=round(eff, 3), ci_lo=round(lo, 3), ci_hi=round(hi, 3),
               p_two=round(two, 5), net_c=round(net.mean(), 4),
               note=f"bar {bar:+.2f}pp MDE {mde:.2f}c")
    return {"label": label, "n": n, "net": net.mean(), "lo": lo, "hi": hi,
            "mde": mde, "idx": e.index}


def main():
    st, bid, ask, mid = p2.load("paths")
    rng = np.random.default_rng(6161)
    tr = pd.read_parquet(DATA / "truth_set1.parquet")
    ev = p2.build_events(st, bid, ask, mid, "deep:30", 0, min_minute=38)
    e = ev[ev["is_event"]].copy()
    e["close_time"] = pd.to_datetime(e["close_time"], utc=True)

    kf = st.set_index("ticker")["kept_is_fav"].to_dict()
    t2 = tr[tr["ticker"].isin(kf)].copy()
    fav_lost = np.array([(not x) if kf.get(t, False) else bool(x)
                         for t, x in zip(t2["ticker"], t2["player_won_s1"])])
    t2 = t2[fav_lost]
    t2["hi_g"] = t2[["s1_w", "s1_l"]].max(axis=1)
    t2["lo_g"] = t2[["s1_w", "s1_l"]].min(axis=1)
    t2["games"] = t2["s1_w"] + t2["s1_l"]

    # best-of-5 = Grand Slam men's singles MAIN draw
    txt = pd.read_parquet(DATA / "universe_text.parquet")
    slam = re.compile(r"(wimbledon|roland garros|french open|us open|"
                      r"australian open)", re.I)
    men = re.compile(r"men", re.I)
    qual = re.compile(r"qualif", re.I)
    bo5 = set()
    for tk, rules in zip(txt["ticker"], txt["rules_primary"]):
        s = rules or ""
        if slam.search(s) and men.search(s) and not qual.search(s):
            bo5.add(tk)

    lab = e.merge(t2[["ticker", "hi_g", "lo_g", "games"]], on="ticker",
                  how="inner")
    lab.index = range(len(lab))

    w("# Task 2 (C3) — selection on set-1 margin")
    w("")
    w("**Task 1 is blocked** (Apify monthly hard limit + `dayOffsets` range "
      "−7..+7 cannot")
    w("reach a −68-day window). This runs on the existing 2,887-row truth set, "
      "which")
    w("already carries set-1 game scores.")
    w("")
    w("## Sample, before analysing it")
    w("")
    w(f"- label-verified events where the favourite truly lost set 1: "
      f"**{len(lab):,}**")
    w(f"- drawn from: Sackmann frozen mirror (all tiers, tourney weeks to "
      f"2026-06-02) + tennis-data (ATP/WTA main tour, to 2026-07-26)")
    w(f"- date range: {lab['close_time'].min():%Y-%m-%d} → "
      f"{lab['close_time'].max():%Y-%m-%d}")
    w(f"- tier mix: " + ", ".join(
        f"{k} {v}" for k, v in lab["tour"].value_counts().items()))
    w(f"- **not a random sample of the 3,436 events** — it is whatever the two "
      f"external sources happened to cover")
    w("")
    w("Expected in advance: at this n, buckets run 40–180 and MDE is 7–12 ¢. "
      "Almost")
    w("everything should come back UNTESTABLE. That is the honest answer at "
      "this sample")
    w("size, not a failure to look.")
    w("")

    hdr = ("| bucket | n | effect pp | bar pp | net ¢ | 95% CI | verdict |\n"
           "|---|---|---|---|---|---|---|")
    res = []

    w("## Reference")
    w("")
    w(hdr)
    res.append(cell(lab, "all label-verified", rng, "reference"))
    w("")

    w("## Set-1 margin")
    w("")
    w(hdr)
    for lo_g, label in ((0, "6-0 / 6-1"), (2, "6-2 / 6-3"), (4, "6-4 / 7-5"),
                        (6, "7-6 tiebreak")):
        if lo_g == 0:
            m = lab["lo_g"] <= 1
        elif lo_g == 2:
            m = lab["lo_g"].isin([2, 3])
        elif lo_g == 4:
            m = lab["lo_g"].isin([4, 5])
        else:
            m = lab["lo_g"] >= 6
        r = cell(lab[m], label, rng, "set-1 margin")
        if r:
            res.append(r)
    w("")

    w("## Tiebreak flag")
    w("")
    w(hdr)
    for lab_, m in (("set 1 went to a tiebreak", lab["lo_g"] >= 6),
                    ("set 1 did not", lab["lo_g"] < 6)):
        r = cell(lab[m], lab_, rng, "tiebreak")
        if r:
            res.append(r)
    w("")

    w("## Games played in set 1")
    w("")
    w(hdr)
    for lo_b, hi_b, label in ((0, 8, "6–8 games (blowout)"),
                              (9, 10, "9–10 games"),
                              (11, 99, "11+ games (long set)")):
        m = (lab["games"] >= lo_b) & (lab["games"] <= hi_b)
        r = cell(lab[m], label, rng, "games in set 1")
        if r:
            res.append(r)
    w("")

    w("## Best-of format")
    w("")
    w(hdr)
    lab["bo5"] = lab["ticker"].isin(bo5)
    w(f"| *(best-of-5 identified: {int(lab['bo5'].sum())} events)* | | | | | | |")
    for lab_, m in (("best-of-5 (Slam men's main draw)", lab["bo5"]),
                    ("best-of-3 (everything else)", ~lab["bo5"])):
        r = cell(lab[m], lab_, rng, "best-of")
        if r:
            res.append(r)
    w("")

    res = [r for r in res if r]
    tested = [r for r in res if r["label"] != "all label-verified"]
    clear = [r for r in tested if r["lo"] > 0]
    pos = [r for r in tested if r["net"] > 0]
    w("## Multiplicity and verdict")
    w("")
    w(f"- buckets tested: **{len(tested)}** (added to the ledger)")
    w(f"- positive mean net: **{len(pos)}**; expected by chance if all truly "
      f"zero: **{len(tested) / 2:.1f}**")
    w(f"- **CI entirely above zero: {len(clear)}**; expected by chance at 5% "
      f"one-sided: **{len(tested) * 0.025:.2f}**")
    w(f"- median MDE across buckets: "
      f"**{np.median([r['mde'] for r in tested]):.1f} ¢** against a target "
      f"effect of ~2 ¢")
    w("")
    if clear:
        w("### Train/holdout on anything that clears")
        w("")
        cut = lab["close_time"].quantile(0.60)
        w("| bucket | full ¢ | train ¢ | holdout ¢ |")
        w("|---|---|---|---|")
        for r in clear:
            sub = lab.loc[r["idx"]]
            for nm, s in (("t", sub[sub["close_time"] <= cut]),
                          ("h", sub[sub["close_time"] > cut])):
                pass
            a = sub[sub["close_time"] <= cut]
            b = sub[sub["close_time"] > cut]
            def nn(x):
                if len(x) < 25:
                    return None
                fb = x["entry_bid"].values
                fill = np.minimum(100.0 - fb + p2.SLIP, 99.0)
                fee = np.array([float(fees.fee_rate_cents(int(round(f))))
                                for f in fill])
                return (100.0 * (1 - x["fav_won"].values) - fill - fee).mean()
            va, vb = nn(a), nn(b)
            w(f"| {r['label']} | {r['net']:+.2f} | "
              f"{'–' if va is None else f'{va:+.2f}'} | "
              f"{'–' if vb is None else f'{vb:+.2f}'} |")
    else:
        w("**No bucket has a confidence interval above zero.** Nothing to "
          "holdout-test.")
    w("")

    # selection canary on the label join itself
    w("## Selection canary on the label join")
    w("")
    e["labelled"] = e["ticker"].isin(set(tr["ticker"]))
    imp_all = (100.0 - e["entry_mid"].values) / 100.0
    obs_all = 1.0 - e["fav_won"].values
    r = lg.check_selection(e["labelled"].values, obs_all, imp_all,
                           "label join (labelled vs unlabelled events)")
    w("```")
    w(lg.table([r], "join canary"))
    w("```")
    ledger.add(phase="6-margin", factor="join canary", level="labelled join",
               n=len(e), note=r.verdict)

    (ROOT / "reports" / "p6_task2_margin.md").write_text("\n".join(OUT),
                                                         encoding="utf-8")
    print(f"\n-> {ROOT / 'reports' / 'p6_task2_margin.md'}")


if __name__ == "__main__":
    main()
