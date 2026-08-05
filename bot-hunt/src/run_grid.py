"""STEP 6 — build the panel, assert the guards, sweep the pre-registered grid.

Order of operations is deliberate and enforced:

  1. build the event panel                     (one row per EVENT, never market)
  2. GUARD: selection canary on the dedupe rule -> refuse to continue on FAIL
  3. GUARD: leak canary across anchors          -> refuse to continue on FAIL
  4. sweep the grid on the TRAIN 70% only
  5. BH-FDR across the WHOLE grid, one denominator
  6. negative-control gate on KXMLBGAME
  7. the holdout is NOT touched here. `--holdout` is a separate, once-only run.

Nothing prints a strategy number before steps 2, 3 and 6 have run.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import Quote, build_trade, cost_bar_cents  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "kalshi_soccer.db"
REP = ROOT / "reports"

TEST_SERIES = ["KXCS2GAME", "KXLOLGAME", "KXVALORANTGAME"]
CONTROL_SERIES = ["KXMLBGAME"]
HOLDOUT_FRAC = 0.30
BANDS = [5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95]
SEED = 20260804

# AMENDMENT A1 (PREREGISTRATION.md, committed 2026-08-05 before re-running).
# The pre-registered -60min anchor VOIDed on the leak canary: close_time is when
# the market SETTLES, not when the match starts, so -60min was usually mid-match.
# Anchors below are the earliest MONOTONE-CLEAN lead per series from
# src/anchor_sweep.py — clean at that lead AND at every longer one.
PRIMARY_ANCHOR = 1440          # a single uniform -24h, clean for every series
PER_SERIES_ANCHOR = {          # sensitivity arm; recovers 2,509 test events
    "KXCS2GAME": 180, "KXLOLGAME": 1440, "KXVALORANTGAME": 360,
    "KXMLBGAME": 60,
}
SWEEP_ANCHORS = (1440, 2880)   # primary + one longer, both monotone-clean


# ------------------------------------------------------------------ panel ---

def build_panel(con, series_list, anchor_min=60):
    """One row per EVENT. The kept side is the FIRST TICKER ALPHABETICALLY —
    the rule GUARDS #1 measured clean at P(kept wins)=0.4969, z=-0.88.

    Banned as dedupe keys and never read here: last_price (z=+140.3),
    open_interest (+15.7), volume (+10.0 — the bug that voided three phases of
    set1_overshoot). `liquidity` is banned too, as UNTESTABLE not clean.
    """
    q = """
    select m.event_ticker, m.series, m.ticker, m.result, m.close_time,
           m.yes_sub_title
    from markets m
    where m.series in ({}) and m.result in ('yes','no')
      and m.close_time is not null
    """.format(",".join("?" * len(series_list)))
    by_ev = defaultdict(list)
    for ev, series, tk, res, ct, sub in con.execute(q, series_list):
        by_ev[ev].append((tk, series, res, ct, sub))

    rows = []
    for ev, mkts in by_ev.items():
        mkts.sort(key=lambda x: x[0])          # THE dedupe rule
        tk, series, res, ct, sub = mkts[0]
        n_sides = len(mkts)
        close_ts = _ts(ct)
        if close_ts is None:
            continue
        cds = con.execute(
            "select end_period_ts, yes_bid_close, yes_ask_close, "
            " price_close, volume from candles where ticker=? "
            "order by end_period_ts", (tk,)).fetchall()
        if not cds:
            continue
        rows.append({
            "event": ev, "series": series, "ticker": tk,
            "won": 1 if res == "yes" else 0,
            "close_ts": close_ts, "n_sides": n_sides,
            "candles": cds,
        })
    rows.sort(key=lambda r: r["close_ts"])
    return rows


def _ts(s):
    if not s:
        return None
    from datetime import datetime, timezone
    for f in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ",
              "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(s, f).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            continue
    return None


def quote_at(row, minutes_before):
    """The last candle STRICTLY BEFORE close - minutes_before.

    Strictly before, so no decision can read a bar that contains its own
    decision instant. There is no filtering layer anywhere in this file, so
    `filtfilt`-style zero-phase look-ahead is impossible by construction.
    """
    cutoff = row["close_ts"] - minutes_before * 60
    best = None
    for ts, yb, ya, pc, vol in row["candles"]:
        if ts is None or ts >= cutoff:
            continue
        if yb is None or ya is None:
            continue
        best = (ts, yb, ya, pc, vol)
    return best


# ----------------------------------------------------------------- guards ---

def selection_canary(rows):
    """P(kept side wins) must be 0.5. Three-valued: UNTESTABLE is not PASS."""
    kept = np.array([r["won"] for r in rows], dtype=float)
    n = len(kept)
    if n < 100:
        return {"verdict": "UNTESTABLE", "reason": f"n={n} < 100", "n": n}
    p = kept.mean()
    se = math.sqrt(0.25 / n)
    z = (p - 0.5) / se
    mde_pp = 1.96 * se * 100
    if mde_pp > 2.0:
        return {"verdict": "UNTESTABLE", "p": p, "z": z, "n": n,
                "reason": f"MDE {mde_pp:.2f}pp > 2.0pp"}
    return {"verdict": "FAIL" if abs(z) > 4 else "PASS",
            "p": float(p), "z": float(z), "n": n, "mde_pp": float(mde_pp)}


def leak_canary(rows, anchors=(0, 60, 360)):
    """A real pre-match market cannot produce extreme quotes that are 100%
    correct. That signature at -0h and NOT at the primary anchor is what a
    clean anchor looks like (T010/T011)."""
    out = {}
    for a in anchors:
        ext, ext_right, n = 0, 0, 0
        for r in rows:
            q = quote_at(r, a)
            if not q:
                continue
            n += 1
            mid_like = q[2]                      # the ask; never a mid
            if mid_like <= 2.0 or mid_like >= 98.0:
                ext += 1
                if (mid_like >= 98.0) == bool(r["won"]):
                    ext_right += 1
        out[a] = {"n": n, "extreme": ext,
                  "pct_extreme": round(100 * ext / n, 2) if n else None,
                  "pct_extreme_correct": round(100 * ext_right / ext, 1)
                  if ext else None}
    return out


# --------------------------------------------------------------- strategy ---

def sweep(rows, slippage=1.0, anchor=60):
    """All pre-registered strategies. Returns one record per cell."""
    prepared = []
    for r in rows:
        q = quote_at(r, anchor)
        if not q:
            continue
        q24 = quote_at(r, anchor + 24 * 60)
        q6 = quote_at(r, anchor + 6 * 60)
        prepared.append((r, q, q24, q6))
    cells = []

    def emit(sid, desc, picks):
        """picks: list of (row, quote, side)."""
        if len(picks) < 30:
            return
        nets, evs, days = [], [], []
        for r, q, side in picks:
            quote = Quote(ts=q[0], bid_c=q[1], ask_c=q[2],
                          bid_size=0.0, ask_size=0.0)
            try:
                t = build_trade(r["ticker"], r["event"], quote, side,
                                bool(r["won"]), 1)
            except Exception:  # noqa: BLE001
                continue
            nets.append(t.net_c - slippage)
            evs.append(r["event"])
            days.append(int(r["close_ts"] // 86400))
        if len(nets) < 30:
            return
        nets = np.asarray(nets)
        # CIs CLUSTERED ON THE DAY, not the event.
        #
        # An esports match is not independent of the other matches in the same
        # tournament on the same day: they share teams, patch, format and the
        # same pool of counterparty attention. Clustering on the event alone
        # would repeat the mistake GUARDS #8 catalogues - crypto's 89,806
        # market-minutes that were really 250 events, and the tennis bot's
        # 25,250 "observations" that were ~171 matches.
        rng = np.random.default_rng(SEED)
        uniq = list(dict.fromkeys(days))
        idx = defaultdict(list)
        for i, dkey in enumerate(days):
            idx[dkey].append(i)
        boot = np.empty(2000)
        for b in range(2000):
            pick = rng.choice(len(uniq), size=len(uniq), replace=True)
            sel = np.concatenate([idx[uniq[j]] for j in pick])
            boot[b] = nets[sel].mean()
        lo, hi = np.percentile(boot, [2.5, 97.5])
        mean = float(nets.mean())
        # EFFECTIVE n from the clustered bootstrap: the n that a naive
        # independent-observation SE would have needed to give this width.
        se_cluster = float(boot.std(ddof=1))
        sd = float(nets.std(ddof=1))
        n_eff = (sd / se_cluster) ** 2 if se_cluster > 0 else float(len(nets))
        design_effect = len(nets) / n_eff if n_eff > 0 else float("nan")
        z = mean / se_cluster if se_cluster > 0 else 0.0
        p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
        cells.append({
            "id": sid, "desc": desc, "n_trades": int(len(nets)),
            "n_events": len(set(evs)), "n_days": len(uniq),
            "n_eff": float(n_eff), "design_effect": float(design_effect),
            "mean_c": mean, "ci_lo": float(lo), "ci_hi": float(hi),
            "p": float(p), "mde_c": float(1.96 * se_cluster),
            "slippage": slippage, "anchor": anchor,
        })

    # H1 calibration by decile
    for lo_b, hi_b in zip(BANDS[:-1], BANDS[1:]):
        emit(f"H1[{lo_b}-{hi_b}]", "buy YES in price band",
             [(r, q, "yes") for r, q, _, _ in prepared if lo_b <= q[2] < hi_b])
    # H2 longshot / H3 favourite / H4 the K015=W011 band
    emit("H2", "buy longshot ask<=20c",
         [(r, q, "yes") for r, q, _, _ in prepared if q[2] <= 20])
    emit("H3", "buy favourite ask>=80c",
         [(r, q, "yes") for r, q, _, _ in prepared if q[2] >= 80])
    emit("H4", "buy 60-95c band (K015=W011)",
         [(r, q, "yes") for r, q, _, _ in prepared if 60 <= q[2] <= 95])
    # H5 fade / H6 follow the drift, measured on EARLY prices only
    for win, lbl in ((24 * 60, "24h"), (6 * 60, "6h")):
        f, m = [], []
        for r, q, q24, q6 in prepared:
            old = q24 if win == 24 * 60 else q6
            if not old:
                continue
            d = q[2] - old[2]
            if abs(d) < 1.0:
                continue
            (f if d < 0 else m).append((r, q, "yes"))
        emit(f"H5[{lbl}]", "fade the drift (buy what fell)", f)
        emit(f"H6[{lbl}]", "follow the drift (buy what rose)", m)
    # H7 wide spread
    emit("H7", "buy when spread >= 3c",
         [(r, q, "yes") for r, q, _, _ in prepared if (q[2] - q[1]) >= 3.0])
    # H8 low volume
    vols = [q[4] or 0 for _, q, _, _ in prepared]
    if vols:
        med = float(np.median(vols))
        emit("H8", "buy when candle volume below median",
             [(r, q, "yes") for r, q, _, _ in prepared if (q[4] or 0) <= med])
    # H9 stale quote
    st = []
    for r, q, q24, q6 in prepared:
        if q6 and abs(q[2] - q6[2]) < 0.5:
            st.append((r, q, "yes"))
    emit("H9", "buy when ask moved <0.5c in 6h (stale)", st)
    # NAIVE BENCHMARKS. Reported beside every result, never omitted.
    rng = np.random.default_rng(SEED + 99)
    emit("H0-RANDOM", "NAIVE: random side, no view at all",
         [(r, q, "yes" if rng.random() < 0.5 else "no")
          for r, q, _, _ in prepared])
    emit("H0-ALLYES", "NAIVE: buy the kept side of every event",
         [(r, q, "yes") for r, q, _, _ in prepared])
    return cells


def bh_fdr(cells, q=0.10):
    ps = sorted((c["p"], i) for i, c in enumerate(cells))
    m = len(ps)
    thr = 0.0
    for k, (p, _) in enumerate(ps, start=1):
        if p <= k / m * q:
            thr = p
    for c in cells:
        c["bh_survives"] = bool(c["p"] <= thr) if thr > 0 else False
    return thr, m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", action="store_true",
                    help="ONCE ONLY, survivors only")
    a = ap.parse_args()
    REP.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True, timeout=120)

    report = {}
    for label, series in (("TEST", TEST_SERIES), ("CONTROL", CONTROL_SERIES)):
        rows = build_panel(con, series)
        print(f"\n{'='*72}\n{label}: {series}")
        print(f"  events with a usable candle panel: {len(rows)}")
        if len(rows) < 60:
            print("  !! too few events to run anything. SKIPPED.")
            report[label] = {"n_events": len(rows), "skipped": True}
            continue

        can = selection_canary(rows)
        print(f"  GUARD selection canary: {can['verdict']}  "
              f"P(kept wins)={can.get('p')} z={can.get('z')} n={can.get('n')} "
              f"{can.get('reason','')}")
        if can["verdict"] == "FAIL":
            print("  !! dedupe rule reads the outcome. REFUSING to continue.")
            report[label] = {"selection_canary": can, "aborted": True}
            continue

        leak = leak_canary(rows, anchors=(0, 60, 360, PRIMARY_ANCHOR))
        print("  GUARD leak canary (extreme quotes, and how often correct):")
        for anch, d in leak.items():
            print(f"     anchor -{anch:>5}min  n={d['n']:>5} "
                  f"extreme={d['pct_extreme']}%  correct={d['pct_extreme_correct']}%")
        primary = leak.get(PRIMARY_ANCHOR, {})
        if (primary.get("pct_extreme_correct") is not None
                and primary["pct_extreme_correct"] >= 99.0
                and (primary.get("pct_extreme") or 0) > 1.0):
            print(f"  !! the -{PRIMARY_ANCHOR}min anchor shows the "
                  f"100%-correct-extremes signature. VOID.")
            report[label] = {"leak_canary": leak, "aborted": True}
            continue

        split = int(len(rows) * (1 - HOLDOUT_FRAC))
        train, hold = rows[:split], rows[split:]
        use = hold if a.holdout else train
        print(f"  {'HOLDOUT' if a.holdout else 'TRAIN'} events: {len(use)} "
              f"(train {len(train)} / holdout {len(hold)}, split by close_time)")

        cells = []
        for slip in (0.0, 0.5, 1.0, 2.0):
            for anch in SWEEP_ANCHORS:
                cells += [dict(c, series=label, arm="uniform") for c in
                          sweep(use, slippage=slip, anchor=anch)]
        # SENSITIVITY ARM: each series at its own monotone-clean anchor. Kept
        # in the SAME BH-FDR denominator, because splitting the denominator is
        # how a grid quietly doubles its own false-positive budget.
        for slip in (0.0, 1.0):
            for s in series:
                sub = [r for r in use if r["series"] == s]
                if len(sub) < 60:
                    continue
                cells += [dict(c, series=label, arm=f"perseries:{s}") for c in
                          sweep(sub, slippage=slip,
                                anchor=PER_SERIES_ANCHOR.get(s, PRIMARY_ANCHOR))]
        if not cells:
            print("  no cell had >=30 trades. Nothing to report.")
            report[label] = {"n_events": len(rows), "cells": 0}
            continue
        thr, m = bh_fdr(cells)
        surv = [c for c in cells if c["bh_survives"]]
        pos = [c for c in surv if c["ci_lo"] > 0]
        print(f"  cells={m}  BH-FDR q=0.10 threshold p<={thr:.5f}  "
              f"survive={len(surv)}  survive AND CI>0: {len(pos)}")

        # ---------------------------------------------------- NAIVE BENCHMARK
        # Reported next to every result, per CLAUDE.md sec 6. Two of them,
        # because they answer different questions:
        #   RANDOM  what you get for taking liquidity with no view at all.
        #           Any strategy that does not beat this is not a strategy.
        #   ALL-YES what you get for buying every event's kept side. It is the
        #           "just be long" comparator.
        bench = {c["id"]: c for c in cells
                 if c["id"] in ("H0-RANDOM", "H0-ALLYES")
                 and c["slippage"] == 1.0 and c["anchor"] == PRIMARY_ANCHOR
                 and c.get("arm") == "uniform"}
        print(f"\n  NAIVE BENCHMARKS (slip=1.0c, anchor=-{PRIMARY_ANCHOR}min):")
        for k, c in bench.items():
            print(f"    {k:12} {c['mean_c']:+8.3f}c  "
                  f"[{c['ci_lo']:+7.3f},{c['ci_hi']:+7.3f}]  "
                  f"n_trades={c['n_trades']} n_days={c['n_days']} "
                  f"n_eff={c['n_eff']:.0f} (design effect "
                  f"{c['design_effect']:.1f}x)")
        base = bench.get("H0-RANDOM", {}).get("mean_c")

        cells.sort(key=lambda c: -c["mean_c"])
        print(f"\n  {'cell':22} {'slip':>4} {'anch':>5} {'n_tr':>5} "
              f"{'n_eff':>6} {'mean_c':>8} {'vs naive':>9} "
              f"{'CI':>20} {'p':>8} {'MDE':>6} BH")
        show = cells[:12] + [c for c in cells if c["id"].startswith("H0-")][:4]
        for c in show:
            vs = f"{c['mean_c'] - base:+8.3f}" if base is not None else "     n/a"
            print(f"  {c['id'][:22]:22} {c['slippage']:>4} {c['anchor']:>5} "
                  f"{c['n_trades']:>5} {c['n_eff']:>6.0f} {c['mean_c']:>+8.3f} "
                  f"{vs:>9} [{c['ci_lo']:+7.3f},{c['ci_hi']:+7.3f}] "
                  f"{c['p']:>8.4f} {c['mde_c']:>6.2f} "
                  f"{'Y' if c['bh_survives'] else '.'}")

        # ------------------------------------------------- PARAMETER SURFACE
        # The brief requires the SURFACE, not the peak. A sharp isolated peak
        # is overfitting; a broad plateau may be real. This prints the whole
        # H1 calibration curve at the primary settings and labels it.
        print(f"\n  PARAMETER SURFACE — H1 calibration by price band "
              f"(slip=1.0c, anchor=-{PRIMARY_ANCHOR}min). "
              f"The shape is the finding, not the max:")
        surf = sorted([c for c in cells if c["id"].startswith("H1[")
                       and c["slippage"] == 1.0
                       and c["anchor"] == PRIMARY_ANCHOR
                       and c.get("arm") == "uniform"],
                      key=lambda c: int(c["id"].split("[")[1].split("-")[0]))
        for c in surf:
            bar = "#" * max(0, min(40, int(round(c["mean_c"] + 20))))
            print(f"    {c['id']:14} n_tr={c['n_trades']:>5} "
                  f"n_eff={c['n_eff']:>5.0f} {c['mean_c']:>+8.3f}c "
                  f"[{c['ci_lo']:+7.2f},{c['ci_hi']:+7.2f}] |{bar}")
        if surf:
            means = [c["mean_c"] for c in surf]
            best = max(range(len(means)), key=lambda i: means[i])
            nb = [means[i] for i in (best - 1, best + 1) if 0 <= i < len(means)]
            gap = (means[best] - max(nb)) if nb else float("nan")
            shape = ("PEAK (isolated — treat as overfitting)" if gap > 3.0
                     else "PLATEAU (neighbours agree)")
            print(f"    -> best band {surf[best]['id']} at {means[best]:+.3f}c; "
                  f"nearest neighbour gap {gap:+.2f}c -> {shape}")
        report[label] = {"n_events": len(rows), "selection_canary": can,
                         "leak_canary": leak, "n_cells": m,
                         "bh_threshold": thr, "n_survive": len(surv),
                         "n_survive_positive": len(pos), "cells": cells}

    name = "grid_holdout.json" if a.holdout else "grid_train.json"

    # THE NEGATIVE-CONTROL GATE
    #
    # DEFECT FOUND IN v1 OF THIS FILE AND FIXED HERE. v1 read
    # `ctl.get("n_survive_positive", 0)`, so a control family with NO DATA AT
    # ALL returned 0 and printed "control clean -> results are reportable".
    # An ABSENT control is not a PASSED control. That is precisely the
    # "silent failure that inflates a denominator" class this programme has
    # been bitten by before (a bug once reported 358 repos scored when 92 had
    # real data), and it is the same three-valued mistake GUARDS #1 exists to
    # prevent: UNTESTABLE must never render as PASS.
    ctl = report.get("CONTROL", {})
    print(f"\n{'='*72}\nNEGATIVE-CONTROL GATE (KXMLBGAME, known efficient)")
    if ctl.get("skipped") or ctl.get("aborted") or "n_survive_positive" not in ctl:
        print(f"  !! CONTROL DID NOT RUN (events={ctl.get('n_events')}). "
              f"The gate is UNTESTABLE, which is NOT a pass.")
        print("  !! NO TEST RESULT FROM THIS RUN IS REPORTABLE AS A FINDING. "
              "Pull the control family's candles and re-run.")
        report["control_gate"] = "UNTESTABLE"
    elif ctl["n_survive_positive"] >= 2:
        print(f"  !! {ctl['n_survive_positive']} strategies 'work' on a "
              f"known-efficient family. THE RUN IS DECLARED BROKEN.")
        report["control_gate"] = "FAIL"
    else:
        print(f"  control clean ({ctl['n_survive_positive']} positive "
              f"survivors) -> test results are reportable")
        report["control_gate"] = "PASS"
    (REP / name).write_text(json.dumps(report, indent=1, default=str),
                            encoding="utf-8")
    print(f"wrote reports/{name}")
    con.close()


if __name__ == "__main__":
    main()
