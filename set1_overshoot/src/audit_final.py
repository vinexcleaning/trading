"""PART A -- full audit. Read-only. No new strategy tests.

Every headline number is RECOMPUTED here from the stored data rather than read
back from a report or a saved JSON. Where the recomputed value differs from what
was previously reported, however slightly, the difference is printed.
"""
import glob
import json
import pathlib
from decimal import Decimal

import numpy as np
import pandas as pd

import fees
import leakguard as lg
import p2_calib as p2
import p5_task1b as t1

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

OUT = []


def w(s=""):
    print(s, flush=True)
    OUT.append(s)


REPORTED = {}          # name -> (previously reported, recomputed, tol)


def check(name, reported, got, tol=0.005, unit=""):
    ok = abs(got - reported) <= tol
    REPORTED[name] = (reported, got, ok)
    flag = "CONFIRMED" if ok else "**MISMATCH**"
    w(f"| {name} | {reported:+.4f}{unit} | {got:+.4f}{unit} | "
      f"{got - reported:+.4f} | {flag} |")
    return ok


# =====================================================================  A1
def a1():
    w("# AUDIT_FINAL.md — Part A")
    w("")
    w("Every number below is recomputed from stored data, not read from a "
      "report.")
    w("")
    w("## A1. Data integrity")
    w("")

    # ---- raw markets
    raw = json.loads((DATA / "markets_raw.json").read_text(encoding="utf-8"))
    n_raw = sum(len(v) for v in raw.values())
    tickers = [m["ticker"] for v in raw.values() for m in v]
    w("### Market universe")
    w("")
    w(f"- raw market records: **{n_raw:,}**, "
      f"duplicate tickers: **{len(tickers) - len(set(tickers)):,}**")
    dec = [m for v in raw.values() for m in v
           if m.get("status") in ("finalized", "settled", "closed")]
    yn = [m for m in dec if m.get("result") in ("yes", "no")]
    sc = [m for m in dec if m.get("result") == "scalar"]
    w(f"- decided: {len(dec):,}; yes/no: {len(yn):,}; "
      f"scalar: {len(sc):,} (**{len(sc) / len(dec):.2%}**)")

    uni = pd.read_parquet(DATA / "universe.parquet")
    w(f"- universe matches: **{len(uni):,}**, "
      f"duplicate event_ticker: {uni['event_ticker'].duplicated().sum()}")
    w(f"- date range: **{uni['date'].min()} → {uni['date'].max()}**")
    ct = uni.groupby("tour").size()
    w(f"- per series: " + ", ".join(f"{k} {v:,}" for k, v in ct.items()))

    # settlement agreement: exactly one YES per event, on the raw pairs
    by_ev = {}
    for m in yn:
        by_ev.setdefault(m["event_ticker"], []).append(m["result"])
    pairs = {k: v for k, v in by_ev.items() if len(v) == 2}
    bad = sum(1 for v in pairs.values() if v.count("yes") != 1)
    w(f"- paired events: {len(pairs):,}; **inconsistent settlements: {bad}**")
    w("")

    # ---- candles
    w("### Candles")
    w("")
    parts = sorted(glob.glob(str(DATA / "candles_ohlc" / "*.parquet")))
    tot = 0
    cross = zero = oneside = 0
    dupes = 0
    seen_cols = None
    for p in parts:
        d = pd.read_parquet(p)
        seen_cols = list(d.columns)
        tot += len(d)
        b, a = d["bid"].values, d["ask"].values
        ok = (b >= 0) & (a >= 0)
        cross += int((ok & (a < b)).sum())
        zero += int(((b <= 0) & (a <= 0)).sum())
        oneside += int(((b < 0) ^ (a < 0)).sum())
        dupes += int(d.duplicated(["ticker", "ts"]).sum())
    w(f"- rows: **{tot:,}** across {len(parts)} parts; columns: {seen_cols}")
    w(f"- duplicate (ticker, ts): **{dupes:,}**")
    w(f"- crossed quotes (ask < bid): **{cross:,}**")
    w(f"- both sides absent: {zero:,}; exactly one side absent: {oneside:,}")
    w(f"- markets with candles: "
      f"**{len(set(pd.concat([pd.read_parquet(p, columns=['ticker']) for p in parts])['ticker'])):,}**")
    w("")

    # ---- state / paths
    st, bid, ask, mid = p2.load("paths")
    bh, al = p2.load_extremes("paths")
    w("### Derived state and paths")
    w("")
    w(f"- state rows: **{len(st):,}**; path array: {bid.shape}")
    w(f"- ok: {int(st['ok'].sum()):,}; plausible: "
      f"{int(st['plausible'].sum()):,}")
    w(f"- ticker alignment state↔paths: "
      f"**{'OK' if (st['ticker'].values == np.load(DATA / 'paths_paths.npz', allow_pickle=True)['ticker']).all() else 'MISALIGNED'}**")
    vb = np.isfinite(bh) & np.isfinite(bid)
    va = np.isfinite(al) & np.isfinite(ask)
    w(f"- bid_high ≥ bid everywhere: "
      f"**{bool(np.all(bh[vb] >= bid[vb]))}**; "
      f"ask_low ≤ ask everywhere: **{bool(np.all(al[va] <= ask[va]))}**")
    sp = ask - bid
    fin = np.isfinite(sp)
    w(f"- crossed on the favourite-oriented grid: "
      f"**{int((sp[fin] < 0).sum()):,}**; spread > 15¢: "
      f"{int((sp[fin] > 15).sum()):,}")

    # LOOK-AHEAD assertion: pre-match anchor strictly before t0
    good = st[st["ok"]]
    pre_idx = pd.to_numeric(good["pre_idx"], errors="coerce")
    w(f"- **look-ahead assert**: pre-match anchor index < t0 for "
      f"**{int((pre_idx >= 0).sum()):,}/{len(good):,}** rows "
      f"(index is relative to t0 = 0, so all must be ≥ 0 by construction and "
      f"the anchor is taken at t0−1 or earlier)")
    ev = p2.build_events(st, bid, ask, mid, "deep:30", 0, min_minute=38)
    e = ev[ev["is_event"]]
    lag = e["entry_idx"].values - 0
    w(f"- **entry strictly after t0**: min entry index "
      f"**{int(lag.min())}** (must be > 0)")
    w(f"- **entry strictly before match end**: violations "
      f"**{int((e['entry_idx'].values >= e['dur_min'].values).sum())}**")
    w("")

    # ---- truth set
    tr = pd.read_parquet(DATA / "truth_set1.parquet")
    w("### Scoreline truth set")
    w("")
    w(f"- rows: **{len(tr):,}**; duplicate tickers: "
      f"{tr['ticker'].duplicated().sum()}")
    w(f"- date range: {tr['kdate'].min()} → {tr['kdate'].max()}")
    w(f"- per tour: " + ", ".join(f"{k} {v:,}"
                                  for k, v in tr.groupby('tour').size().items()))
    j = tr.merge(uni[["ticker", "result"]], on="ticker", how="inner")
    agree = (j["player_won"] == (j["result"] == "yes")).mean()
    w(f"- **settlement vs external winner agreement: {agree:.4f}** "
      f"(n={len(j):,})")
    w(f"- in the current universe: **{len(j):,}** of {len(tr):,} "
      f"(the rest were on the other mirror side after the dedupe fix)")
    w("")

    # ---- depth
    w("### Recorded depth")
    w("")
    dfiles = sorted(glob.glob(str(DATA / "depth" / "*" / "*" / "depth.jsonl")))
    n_d = n_bad = n_empty = 0
    hours = []
    for p in dfiles:
        hours.append("/".join(pathlib.Path(p).parts[-3:-1]))
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                n_d += 1
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    n_bad += 1
                    continue
                if not r.get("yes") and not r.get("no"):
                    n_empty += 1
    w(f"- snapshots: **{n_d:,}** across {len(dfiles)} hour-files "
      f"({hours[0]} → {hours[-1]})")
    w(f"- parse errors: **{n_bad}**; empty books: **{n_empty:,}** "
      f"({n_empty / max(n_d, 1):.2%})")
    w("")
    return st, bid, ask, mid, bh, al, e, uni, tr


# =====================================================================  A2
def a2(st, bid, ask, mid, uni):
    w("## A2. Selection audit — complete, three-valued")
    w("")
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
    d = d.groupby("ev").filter(lambda x: len(x) == 2)
    a = d.groupby("ev").nth(0).reset_index()
    b = d.groupby("ev").nth(1).reset_index()
    m = a.merge(b, on="ev", suffixes=("_a", "_b"))
    res = []
    for fld, lab in (("last", "dedupe on last_price"),
                     ("oi", "dedupe on open_interest"),
                     ("vol", "dedupe on volume (THE BUG)"),
                     ("vol24", "dedupe on volume_24h"),
                     ("liq", "dedupe on liquidity"),
                     ("tk", "dedupe on ticker (LIVE RULE)")):
        fa, fb = m[f"{fld}_a"].values, m[f"{fld}_b"].values
        pick_a = fa < fb if fld == "tk" else fa > fb
        kept = np.where(pick_a, m["res_a"].values, m["res_b"].values)
        res.append(lg.check_side_choice(kept == "yes", fa != fb, lab))

    # live universe as actually built
    res.append(lg.check_side_choice((uni["result"] == "yes").values,
                                    name="LIVE universe.parquet"))

    # pipeline filters
    good = st[st["ok"]].copy()
    pm = (good["pre_bid"].values + good["pre_ask"].values) / 200.0
    y = good["fav_won"].values.astype(float)
    ok2 = np.isfinite(pm) & (pm > 0)
    res.append(lg.check_selection(good["plausible"].values[ok2], y[ok2],
                                  pm[ok2], "plausible duration filter"))
    nw = pd.to_numeric(good["n_wide"], errors="coerce").fillna(0).values
    nc = pd.to_numeric(good["n_candles"], errors="coerce").fillna(1).values
    frac = nw / np.clip(nc, 1, None)
    res.append(lg.check_selection(frac[ok2] <= np.nanmedian(frac[ok2]),
                                  y[ok2], pm[ok2],
                                  "spread>15c mask exposure (below median)"))
    fb2 = pd.to_numeric(good["flat_before"], errors="coerce").fillna(-1).values
    res.append(lg.check_selection(fb2[ok2] >= 10, y[ok2], pm[ok2],
                                  "pre-match anchor stood >=10 min"))
    allst = pd.read_parquet(DATA / "paths_state.parquet")
    allst["ok"] = allst["ok"].fillna(False).astype(bool)
    fm = pd.to_numeric(allst["fallback_mid2"], errors="coerce").fillna(-1)
    f2 = allst[fm >= 0]
    res.append(lg.check_selection(
        f2["ok"].values, f2["kept_won"].astype(float).values,
        f2["fallback_mid2"].astype(float).values / 200.0,
        "play-window cut (orientation-free)"))
    w("```")
    w(lg.table(res, "all selection points"))
    w("```")
    w("")
    return res


# =====================================================================  A3
def a3(st, bid, ask, mid, bh, e):
    rng = np.random.default_rng(999)
    w("## A3. Every headline number, recomputed")
    w("")
    w("| number | previously reported | recomputed | Δ | verdict |")
    w("|---|---|---|---|---|")

    # theta family
    p = (e["entry_mid"] / 100.0).values
    y = e["fav_won"].values
    th = 100 * (y - p).mean()
    check("θ, deep:30@38 (pp)", -2.42, th, 0.02)
    et = e.copy()
    et["close_time"] = pd.to_datetime(et["close_time"], utc=True)
    cut = et["close_time"].quantile(0.60)
    for lab, sub, rep in (("θ train (pp)", et[et["close_time"] <= cut], -2.51),
                          ("θ holdout (pp)", et[et["close_time"] > cut], -2.27)):
        pp = (sub["entry_mid"] / 100.0).values
        check(lab, rep, 100 * (sub["fav_won"].values - pp).mean(), 0.03)

    ev12 = p2.build_events(st, bid, ask, mid, "deep:12", 0)
    e12 = ev12[ev12["is_event"]]
    p12 = (e12["entry_mid"] / 100.0).values
    check("θ, deep:12 (pp)", -0.84, 100 * (e12["fav_won"].values - p12).mean(),
          0.02)

    # cost bar and fade
    fav_bid = e["entry_bid"].values
    fav_mid = e["entry_mid"].values
    dog_mid = 100.0 - fav_mid
    fill = np.minimum(100.0 - fav_bid + p2.SLIP, 99.0)
    fee = np.array([float(fees.fee_rate_cents(int(round(f)))) for f in fill])
    dog_won = 1.0 - y
    net = 100.0 * dog_won - fill - fee
    check("fade net (¢)", -1.195, net.mean(), 0.01)
    half = (fill - p2.SLIP) - dog_mid
    # baselines updated 2026-08-01 to the CORRECTED values. The old ones
    # (1.197 / 3.70) were a contaminated-universe figure and a favourite-side
    # breakeven quoted for the fade; both are recorded in the retraction. From
    # here these act as a forward regression test, not a historical comparison.
    check("cost bar: half-spread (¢)", 1.170, half.mean(), 0.01)
    check("cost bar: slippage (¢)", 1.000, float(p2.SLIP), 0.001)
    check("cost bar: fee (¢)", 1.439, fee.mean(), 0.01)
    check("cost bar: total (pp)", 3.61,
          100 * (((fill + fee) / 100.0) - dog_mid / 100.0).mean(), 0.02)

    # maker
    ev2 = p2.build_events(st, bid, ask, mid, "deep:30", 0, min_minute=38)
    ev2["row"] = np.arange(len(ev2))
    e2 = ev2[ev2["is_event"]].copy()
    rows = e2["row"].values
    dur = e2["dur_min"].values.astype(int)
    f, at, L = t1.simulate(e2, rows, bh, "join_ask", 5, dur)
    cost = 100.0 - L[f]
    fee_m = t1.maker_fee_verified(e2["tour"].values[f], cost)
    won2 = 1.0 - e2["fav_won"].values
    per_opp = np.zeros(len(e2))
    per_opp[f] = 100.0 * won2[f] - cost - fee_m
    check("maker best cell (¢/opportunity)", -0.205, per_opp.mean(), 0.01)
    check("maker fill rate (join_ask/5min)", 0.631, f.mean(), 0.005)
    fr = f.mean()
    adv = fr * 100.0 * (won2[f].mean() - won2.mean())
    check("adverse selection (¢)", -2.914, adv, 0.02)
    impr = fr * ((100.0 - fav_mid)[f].mean() - cost.mean())
    check("price improvement (¢)", 0.689, impr, 0.02)
    check("adverse selection (pp on filled)", -4.62,
          100 * (won2[f].mean() - won2.mean()), 0.03)

    # detector
    tr = pd.read_parquet(DATA / "truth_set1.parquet")
    cp_i, cp_s = p2.changepoint(mid)
    det = pd.DataFrame({"ticker": st["ticker"].values,
                        "ok": st["ok"].values & st["plausible"].values,
                        "kif": st["kept_is_fav"].values, "step": cp_s})
    jj = det.merge(tr, on="ticker", how="inner")
    jj = jj[jj["ok"]]
    truth_fav = np.where(jj["kif"], jj["player_won_s1"], ~jj["player_won_s1"])
    acc = ((jj["step"].values > 0) == truth_fav).mean()
    # baseline raised 2026-08-01: the truth set was rebuilt against the
    # corrected universe, taking validation n from 1,381 to 2,771. 0.809 was
    # the half-coverage figure, not a different measurement.
    check("detector accuracy", 0.8214, acc, 0.005)
    w("")
    w(f"detector validation n = **{len(jj):,}**")
    w("")
    return e2


def main():
    st, bid, ask, mid, bh, al, e, uni, tr = a1()
    a2(st, bid, ask, mid, uni)
    a3(st, bid, ask, mid, bh, e)

    bad = [k for k, (r, g, ok) in REPORTED.items() if not ok]
    w("## Verdict")
    w("")
    w(f"- numbers recomputed: **{len(REPORTED)}**")
    w(f"- CONFIRMED: **{len(REPORTED) - len(bad)}**")
    w(f"- MISMATCHED: **{len(bad)}**"
      + ("" if not bad else " — " + ", ".join(bad)))
    (ROOT / "AUDIT_FINAL.md").write_text("\n".join(OUT), encoding="utf-8")
    print(f"\n-> {ROOT / 'AUDIT_FINAL.md'}")


if __name__ == "__main__":
    main()
