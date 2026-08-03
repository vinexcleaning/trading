r"""The specialist pipeline, as a module, so the synthetic control runs the SAME code.

A control that re-implements the pipeline tests the re-implementation, not the
pipeline. Everything the real run does -- ranking, filtering, top-decile
selection, event-clustered bootstrap, naive benchmark -- lives here and is
called identically by the real driver and by the synthetic-control driver.

The one rule that governs the whole design: **selection uses period-1 data only,
measurement uses period-2 data only, and the two windows never overlap.**
Selecting on past performance is what copy trading IS and is not a bias.
Measuring over the window you selected on is, and that is enforced by
`assert_no_lookahead` rather than by convention.
"""
import math
import random

import numpy as np
from collections import Counter, defaultdict

FEE_RATE = 0.10
SEED = 20260801
N_BOOT = 2000
MAX_BOOT_CLUSTERS = 20_000

PX_BANDS = [(0.00, 0.10), (0.10, 0.25), (0.25, 0.40), (0.40, 0.60),
            (0.60, 0.75), (0.75, 0.90), (0.90, 1.00)]


def fee(p):
    return FEE_RATE * min(p, 1.0 - p)


def band_of(p):
    for lo, hi in PX_BANDS:
        if lo <= p < hi:
            return f"{lo:.2f}-{hi:.2f}"
    return "1.00"


# ------------------------------------------------------------ statistics
def boot_by_event(by_ev, n_boot=N_BOOT, seed=SEED):
    """Bootstrap resampling EVENTS, never trades.

    21 bets on one match is one observation. A prior run produced a '+95pp
    genius wallet' that was exactly one coinflip counted 21 times.

    Vectorised. The pure-Python version was ~40M inner iterations per call and
    the full filter sweep would have taken hours; this is the same estimator,
    drawn in chunks so the index matrix stays small.
    """
    keys = [k for k, v in by_ev.items() if v]
    if len(keys) < 5:
        return None
    rng = random.Random(seed)
    if len(keys) > MAX_BOOT_CLUSTERS:
        keys = rng.sample(keys, MAX_BOOT_CLUSTERS)
    cnt = np.fromiter((len(by_ev[k]) for k in keys), dtype=np.float64,
                      count=len(keys))
    tot = np.fromiter((sum(by_ev[k]) for k in keys), dtype=np.float64,
                      count=len(keys))
    tn, ts = cnt.sum(), tot.sum()
    if tn <= 0:
        return None
    K = len(keys)
    gen = np.random.default_rng(seed)
    draws = np.empty(n_boot, dtype=np.float64)
    step = max(1, min(n_boot, max(1, 4_000_000 // max(K, 1))))
    done = 0
    while done < n_boot:
        b = min(step, n_boot - done)
        idx = gen.integers(0, K, size=(b, K))
        c = cnt[idx].sum(axis=1)
        s = tot[idx].sum(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            draws[done:done + b] = np.where(c > 0, s / c * 100.0, np.nan)
        done += b
    draws = draws[~np.isnan(draws)]
    if draws.size < 20:
        return None
    draws.sort()
    neg = float((draws <= 0).mean())
    pos = float((draws >= 0).mean())
    return {
        "mean_pp": round(float(ts / tn * 100), 4),
        "ci95": [round(float(draws[int(draws.size * .025)]), 4),
                 round(float(draws[int(draws.size * .975)]), 4)],
        "p": round(max(min(2 * min(neg, pos), 1.0), 1.0 / draws.size), 6),
        "n_obs": int(tn), "n_events": K,
        "n_eff": effective_n_arr(cnt),
    }


def effective_n_arr(cnt):
    s1 = float(cnt.sum())
    s2 = float((cnt * cnt).sum())
    return round((s1 * s1) / s2, 1) if s2 else 0.0


def effective_n(pre):
    """Kish effective sample size over event clusters.

    Nominal n counts trades; wallets piling into the same event are not
    independent. n_eff = (sum m_i)^2 / sum m_i^2 over cluster sizes.
    """
    ms = [a for a, _ in pre]
    s1 = sum(ms)
    s2 = sum(m * m for m in ms)
    return round((s1 * s1) / s2, 1) if s2 else 0.0


def bh_fdr(tests, alpha=0.05):
    """tests: list of (label, p). -> dict label -> verdict."""
    ps = sorted((p, lab) for lab, p in tests)
    m = len(ps)
    crit = None
    for i, (p, lab) in enumerate(ps, 1):
        if p <= i / m * alpha:
            crit = i
    return {
        "n_tests": m, "alpha": alpha, "n_significant": crit or 0,
        "detail": {lab: {"p": p, "bh_threshold": round(i / m * alpha, 6),
                         "significant": bool(crit and i <= crit)}
                   for i, (p, lab) in enumerate(ps, 1)},
    }


# ------------------------------------------------------- look-ahead guard
def assert_no_lookahead(sel_rows, meas_rows, cut, label=""):
    """Every selection input must be knowable before the cut; measurement after.

    Raises rather than warns. A silent overlap is the exact failure the brief
    describes: ranking on a window and then 'backtesting' over that same window
    restates why the wallets were chosen and calls it a forecast.
    """
    bad_sel = [r for r in sel_rows if r["ts"] >= cut]
    bad_meas = [r for r in meas_rows if r["ts"] < cut]
    if bad_sel or bad_meas:
        raise AssertionError(
            f"LOOK-AHEAD {label}: {len(bad_sel)} selection rows at/after cut, "
            f"{len(bad_meas)} measurement rows before cut")
    return {"selection_rows": len(sel_rows), "measurement_rows": len(meas_rows),
            "cut": cut, "overlap": 0, "verdict": "PASS"}


# --------------------------------------------------------------- ranking
def price_band_benchmark(rows):
    """Pooled mean edge per price band -- the 'buy this band blindly' return."""
    b = defaultdict(lambda: [0, 0.0])
    for r in rows:
        e = b[band_of(r["px"])]
        e[0] += 1
        e[1] += r["edge"]
    return {k: v[1] / v[0] for k, v in b.items() if v[0]}


def add_excess(rows, bench):
    for r in rows:
        r["ex"] = r["edge"] - bench.get(band_of(r["px"]), 0.0)
    return rows


def rank_within_category(sel_rows, cat, filters, half_life_days=None):
    """Rank wallets on period-1 data, using only trades in `cat`.

    filters: dict with min_trades, min_events, recent_within_days,
             max_gap_days, exclude (set of wallets).
    half_life_days: if set, exponentially decay older performance so a wallet
             that changed strategy and has been sharp since ranks on recent form.
    """
    rows = [r for r in sel_rows if r["cat"] == cat]
    if not rows:
        return {}, {}
    excl = filters.get("exclude") or set()
    t_end = max(r["ts"] for r in rows)

    per_w = defaultdict(list)
    for r in rows:
        if r["w"] in excl:
            continue
        per_w[r["w"]].append(r)

    scores, diag = {}, Counter()
    for w, rs in per_w.items():
        if len(rs) < filters.get("min_trades", 0):
            diag["drop_min_trades"] += 1
            continue
        evs = {r["ev"] for r in rs}
        if len(evs) < filters.get("min_events", 0):
            diag["drop_min_events"] += 1
            continue
        last = max(r["ts"] for r in rs)
        rw = filters.get("recent_within_days")
        if rw and (t_end - last) > rw * 86400:
            diag["drop_not_recent"] += 1
            continue
        mg = filters.get("max_gap_days")
        if mg:
            ts = sorted(r["ts"] for r in rs)
            gaps = [(b - a) / 86400 for a, b in zip(ts, ts[1:])]
            if gaps and max(gaps) > mg:
                diag["drop_cadence"] += 1
                continue
        if half_life_days:
            lam = math.log(2) / (half_life_days * 86400)
            num = den = 0.0
            for r in rs:
                wgt = math.exp(-lam * (t_end - r["ts"]))
                num += r["ex"] * wgt
                den += wgt
            score = num / den if den else 0.0
        else:
            # equal weight per EVENT first, then across events, so a wallet
            # with 21 bets on one match does not get 21 votes
            by_ev = defaultdict(list)
            for r in rs:
                by_ev[r["ev"]].append(r["ex"])
            per_ev = [sum(v) / len(v) for v in by_ev.values()]
            score = sum(per_ev) / len(per_ev)
        scores[w] = score
        diag["kept"] += 1
    return scores, dict(diag)


def measure(meas_rows, wallets, cat, sizing="equal"):
    """Copier return in period 2, restricted to `cat`, event-clustered.

    sizing:
      equal     -- fixed fraction of bankroll per signal (what the generalist
                   result did; already scale-invariant)
      notional  -- mirror the wallet's dollar sizes
      conviction-- weight by the wallet's own share of its period-2 volume
    """
    rows = [r for r in meas_rows if r["cat"] == cat and r["w"] in wallets]
    if not rows:
        return None, None
    if sizing == "conviction":
        tot = defaultdict(float)
        for r in rows:
            tot[r["w"]] += r["cost"]
    by_ev, bench_ev = defaultdict(list), defaultdict(list)
    for r in rows:
        ret = r["outcome"] - r["px"] - fee(r["px"])
        if sizing == "equal":
            wgt = 1.0
        elif sizing == "notional":
            wgt = r["cost"]
        else:
            wgt = r["cost"] / tot[r["w"]] if tot[r["w"]] > 0 else 0.0
        if wgt <= 0:
            continue
        # weighted values are represented by repeating the mean at unit weight,
        # so the event bootstrap still resamples events rather than dollars
        by_ev[r["ev"]].append(ret * wgt)
        bench_ev[r["ev"]].append(wgt)
    if sizing == "equal":
        return boot_by_event(by_ev), rows
    norm = {k: (sum(v) / sum(bench_ev[k])) if sum(bench_ev[k]) else 0.0
            for k, v in by_ev.items()}
    return boot_by_event({k: [v] for k, v in norm.items()}), rows


def naive_benchmark(meas_rows, cat, bands):
    """Buy every trade in these price bands blindly, same category, same window.

    If copying a wallet equals this, the wallet has exposure, not skill -- which
    is exactly what sank the earlier +7.05pp finding.
    """
    by_ev = defaultdict(list)
    for r in meas_rows:
        if r["cat"] != cat:
            continue
        if band_of(r["px"]) not in bands:
            continue
        by_ev[r["ev"]].append(r["outcome"] - r["px"] - fee(r["px"]))
    return boot_by_event(by_ev)


def paired_excess_over_naive(meas_rows, wallets, cat, n_boot=N_BOOT, seed=SEED):
    """PAIRED test: does copying beat buying the same bands blindly?

    This is the hypothesis that matters, and testing the copier return against
    ZERO instead is a real error -- a copier can be significantly profitable
    purely by holding favourites, which is precisely what sank the earlier
    +7.05pp finding. The synthetic control initially reported 54 of 206
    "significant" results for exactly that reason.

    Within each event, compare the mean return of the selected wallets'
    positions against the mean return of ALL positions in that event in the same
    price bands. Bootstrapping the per-event difference keeps the comparison
    paired, so event-level luck cancels instead of being counted twice.
    """
    sel_by_ev, all_by_ev = defaultdict(list), defaultdict(list)
    bands = set()
    for r in meas_rows:
        if r["cat"] != cat:
            continue
        if r["w"] in wallets:
            bands.add(band_of(r["px"]))
    if not bands:
        return None
    for r in meas_rows:
        if r["cat"] != cat or band_of(r["px"]) not in bands:
            continue
        ret = r["outcome"] - r["px"] - fee(r["px"])
        all_by_ev[r["ev"]].append(ret)
        if r["w"] in wallets:
            sel_by_ev[r["ev"]].append(ret)
    evs = [e for e in sel_by_ev if all_by_ev.get(e)]
    if len(evs) < 5:
        return None
    diff = np.fromiter(
        ((sum(sel_by_ev[e]) / len(sel_by_ev[e]))
         - (sum(all_by_ev[e]) / len(all_by_ev[e])) for e in evs),
        dtype=np.float64, count=len(evs))
    cnt = np.fromiter((len(sel_by_ev[e]) for e in evs), dtype=np.float64,
                      count=len(evs))
    K = diff.size
    gen = np.random.default_rng(seed)
    draws = np.empty(n_boot, dtype=np.float64)
    step = max(1, min(n_boot, max(1, 4_000_000 // max(K, 1))))
    done = 0
    while done < n_boot:
        b = min(step, n_boot - done)
        idx = gen.integers(0, K, size=(b, K))
        draws[done:done + b] = diff[idx].mean(axis=1) * 100.0
        done += b
    draws.sort()
    neg = float((draws <= 0).mean())
    pos = float((draws >= 0).mean())
    return {
        "excess_pp": round(float(diff.mean() * 100), 4),
        "ci95": [round(float(draws[int(draws.size * .025)]), 4),
                 round(float(draws[int(draws.size * .975)]), 4)],
        "p": round(max(min(2 * min(neg, pos), 1.0), 1.0 / draws.size), 6),
        "n_events": K, "n_selected_obs": int(cnt.sum()),
        "n_eff": effective_n_arr(cnt),
        "bands": sorted(bands),
    }
