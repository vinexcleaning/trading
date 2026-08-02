"""TASK 2: Deribit-implied risk-neutral pricer.

P(S_T > K) = -dC/dK on the undiscounted call curve.

Method (see docs/deribit_method.md):
  2a  chain hygiene   -- drop one-sided, stale, and thin expiries; report counts
  2b  surface fit     -- interpolate TOTAL VARIANCE w = sigma^2 * tau against
                         LOG-MONEYNESS k = ln(K/F), then rebuild prices and
                         differentiate. Differentiating a raw noisy price curve
                         amplifies noise badly.
  2b  no-arbitrage    -- calls decreasing and convex in K; total variance
                         monotone in tau. Violations REPORTED, not smoothed away.
  2b  confidence band -- reprice at bid-IV and ask-IV to bracket P(S>K)
  2c  term interp     -- linear in total variance along tau
  2d  settlement adj  -- Kalshi settles on a 60-SECOND AVERAGE, whose variance
                         is below a point sample's

Read-only, public API, no auth.
"""
import json
import math
import os
import time
from bisect import bisect_left
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np
import requests

BASE = "https://www.deribit.com/api/v2/public"
UA = {"User-Agent": "research-readonly/0.1"}
OUT = r"C:\Users\gianf\crypto\data\deribit"

# --- chain hygiene thresholds (stated and justified in deribit_method.md) ---
MAX_QUOTE_AGE_S = 600      # 10 min: Deribit marks refresh continuously; older
                           # than this and the quote predates recent spot moves
MIN_STRIKES_PER_EXPIRY = 8  # below this the -dC/dK differencing has too few
                           # nodes to define a curve rather than interpolate one
MIN_IV = 0.01
MAX_IV = 5.0


def get(method, **params):
    for a in range(6):
        try:
            r = requests.get(f"{BASE}/{method}", params=params, headers=UA,
                             timeout=45)
        except Exception:
            time.sleep(1.2 * (a + 1))
            continue
        if r.status_code == 429:
            time.sleep(1.5 * (a + 1))
            continue
        if r.status_code >= 400:
            return None
        return r.json().get("result")
    return None


# ------------------------------------------------------------ Black-76 call
def bs_call(F, K, w):
    """Undiscounted Black-76 call. w = total variance = sigma^2 * tau."""
    if w <= 0:
        return max(F - K, 0.0)
    s = math.sqrt(w)
    d1 = (math.log(F / K) + 0.5 * w) / s
    d2 = d1 - s
    return F * _ncdf(d1) - K * _ncdf(d2)


def _ncdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def implied_w(F, K, C, lo=1e-8, hi=25.0, tol=1e-10, iters=200):
    """Invert an undiscounted Black-76 call price to TOTAL VARIANCE w.

    Bisection: bs_call is strictly increasing in w, so this is unconditionally
    stable (no Newton blow-ups at the wings, which is where we most need it).
    Returns None if the price is outside the no-arbitrage bounds.
    """
    intrinsic = max(F - K, 0.0)
    if C <= intrinsic + 1e-12:
        return None            # at or below intrinsic -> zero/undefined vol
    if C >= F - 1e-12:
        return None            # at or above the forward -> unbounded
    a, b = lo, hi
    if bs_call(F, K, b) < C:
        return None
    for _ in range(iters):
        m = 0.5 * (a + b)
        if bs_call(F, K, m) < C:
            a = m
        else:
            b = m
        if b - a < tol:
            break
    return 0.5 * (a + b)


def bs_digital(F, K, w):
    """Closed-form P(S>K) under the fitted lognormal at total variance w.

    Used as a cross-check on the numerical -dC/dK."""
    if w <= 0:
        return 1.0 if F > K else 0.0
    s = math.sqrt(w)
    d2 = (math.log(F / K) - 0.5 * w) / s
    return _ncdf(d2)


class Chain:
    """One expiry's cleaned, fitted surface slice."""

    def __init__(self, expiry_ms, tau, F, ks, ws, w_bid, w_ask, meta):
        self.expiry_ms = expiry_ms
        self.tau = tau              # years
        self.F = F                  # forward (index used as proxy)
        self.ks = np.asarray(ks)    # log-moneyness ln(K/F), sorted
        self.ws = np.asarray(ws)    # total variance at each k
        self.w_bid = np.asarray(w_bid)
        self.w_ask = np.asarray(w_ask)
        self.meta = meta

    def w_at(self, k):
        """Total variance at log-moneyness k, linear in k, flat extrapolation."""
        return float(np.interp(k, self.ks, self.ws))

    def w_band_at(self, k):
        return (float(np.interp(k, self.ks, self.w_bid)),
                float(np.interp(k, self.ks, self.w_ask)))

    def call(self, K, w=None):
        k = math.log(K / self.F)
        return bs_call(self.F, K, self.w_at(k) if w is None else w)

    def digital(self, K, h_rel=1e-3):
        """P(S>K) = -dC/dK by central difference on the FITTED curve."""
        h = max(K * h_rel, 1e-6)
        return (self.call(K - h) - self.call(K + h)) / (2 * h)

    def digital_band(self, K, h_rel=1e-3):
        """Bracket P(S>K) using bid-IV and ask-IV surfaces.

        Where Deribit's own quotes are wide its implied probability is
        imprecise, and a Kalshi disagreement inside this band is not evidence
        of anything."""
        h = max(K * h_rel, 1e-6)
        out = []
        for arr in (self.w_bid, self.w_ask):
            def c(x):
                return bs_call(self.F, x,
                               float(np.interp(math.log(x / self.F),
                                               self.ks, arr)))
            out.append((c(K - h) - c(K + h)) / (2 * h))
        return (min(out), max(out))


def build_chains(currency, now_ms=None, verbose=True):
    """2a + 2b. Returns (chains, hygiene_report)."""
    now_ms = now_ms or int(time.time() * 1000)
    idx = get("get_index_price", index_name=f"{currency.lower()}_usd")
    if not idx:
        return [], {"error": "no index"}
    S = float(idx["index_price"])

    book = get("get_book_summary_by_currency", currency=currency,
               kind="option") or []
    instr = get("get_instruments", currency=currency, kind="option",
                expired="false") or []
    meta = {i["instrument_name"]: i for i in instr}

    # NOTE: get_book_summary_by_currency returns NO bid_iv/ask_iv (verified:
    # null on all 870 BTC instruments). It returns bid_price/ask_price quoted
    # in units of the UNDERLYING, plus a per-expiry `underlying_price` which is
    # the FORWARD for that expiry -- 63,964 vs a 62,910 index on the Dec-26
    # contract, i.e. 1.7% carry. Using the spot index as the forward would bias
    # every digital. Invert bid/ask PRICES to total variance directly.
    by_exp = defaultdict(list)
    fwd_of = {}
    disc = defaultdict(lambda: defaultdict(int))
    for b in book:
        n = b.get("instrument_name")
        m = meta.get(n)
        if not m:
            disc["_"]["no_instrument"] += 1
            continue
        e = m["expiration_timestamp"]
        if e <= now_ms:
            disc[e]["expired"] += 1
            continue
        if m["option_type"] != "call":
            continue
        F = b.get("underlying_price")
        if not F or F <= 0:
            disc[e]["no_forward"] += 1
            continue
        fwd_of[e] = float(F)
        bp, ap = b.get("bid_price"), b.get("ask_price")
        # --- two-sided quote required ---
        if not bp or not ap or bp <= 0 or ap <= 0 or ap < bp:
            disc[e]["one_sided"] += 1
            continue
        # --- staleness ---
        ts = b.get("creation_timestamp") or b.get("timestamp")
        if ts and (now_ms - ts) / 1000.0 > MAX_QUOTE_AGE_S:
            disc[e]["stale"] += 1
            continue
        K = float(m["strike"])
        # Deribit quotes crypto options in units of the underlying.
        Cb, Ca = float(bp) * F, float(ap) * F
        wb = implied_w(F, K, Cb)
        wa = implied_w(F, K, Ca)
        mark_iv = b.get("mark_iv")
        tau_ = (e - now_ms) / (1000.0 * 365.25 * 86400.0)
        wm = ((mark_iv / 100.0) ** 2 * tau_) if mark_iv else None
        if wb is None or wa is None:
            disc[e]["uninvertible"] += 1
            continue
        if wa < wb:
            disc[e]["crossed_iv"] += 1
            continue
        w = wm if wm is not None else 0.5 * (wb + wa)
        iv = math.sqrt(w / tau_) if tau_ > 0 else 0.0
        if not (MIN_IV < iv < MAX_IV):
            disc[e]["bad_iv"] += 1
            continue
        by_exp[e].append({"K": K, "w": w, "w_bid": wb, "w_ask": wa,
                          "oi": b.get("open_interest") or 0})

    chains, report = [], {"currency": currency, "index": S, "expiries": []}
    for e, rows in sorted(by_exp.items()):
        tau = (e - now_ms) / (1000.0 * 365.25 * 86400.0)
        if tau <= 0:
            continue
        rows.sort(key=lambda r: r["K"])
        # dedupe strikes
        seen, uniq = set(), []
        for r in rows:
            if r["K"] in seen:
                continue
            seen.add(r["K"])
            uniq.append(r)
        rows = uniq
        kept = len(rows)
        if kept < MIN_STRIKES_PER_EXPIRY:
            disc[e]["thin_expiry"] = kept
            report["expiries"].append(
                {"expiry": e, "tau_h": tau * 365.25 * 24, "kept": 0,
                 "discarded": dict(disc[e]), "reason": "thin"})
            continue
        F = fwd_of[e]          # the per-expiry FORWARD, not the spot index
        ks = [math.log(r["K"] / F) for r in rows]
        ws = [r["w"] for r in rows]
        wb = [r["w_bid"] for r in rows]
        wa = [r["w_ask"] for r in rows]
        ch = Chain(e, tau, F, ks, ws, wb, wa,
                   {"n_strikes": kept, "strikes": [r["K"] for r in rows],
                    "oi": sum(r["oi"] for r in rows)})
        chains.append(ch)
        report["expiries"].append(
            {"expiry": e, "tau_h": round(tau * 365.25 * 24, 2),
             "kept": kept, "discarded": dict(disc[e]),
             "strike_lo": rows[0]["K"], "strike_hi": rows[-1]["K"]})

    if verbose:
        print(f"\n{currency} chain hygiene   index={S:.2f}")
        print(f"  {'expiry (UTC)':<20} {'tau(h)':>8} {'kept':>5} "
              f"{'strikes':>16} {'discarded'}")
        for r in report["expiries"]:
            dt = datetime.fromtimestamp(r["expiry"] / 1000, timezone.utc)
            rng = (f"{r.get('strike_lo',0):.0f}-{r.get('strike_hi',0):.0f}"
                   if r["kept"] else "-")
            print(f"  {str(dt)[:19]:<20} {r['tau_h']:>8.2f} {r['kept']:>5} "
                  f"{rng:>16} {r['discarded']}")
    return chains, report


# --------------------------------------------------- 2b no-arbitrage checks
def check_no_arbitrage(ch, n=60):
    """Calls decreasing and convex in K on the FITTED surface."""
    lo, hi = ch.F * math.exp(ch.ks[0]), ch.F * math.exp(ch.ks[-1])
    Ks = np.linspace(lo, hi, n)
    C = np.array([ch.call(float(k)) for k in Ks])
    dC = np.diff(C)
    d2C = np.diff(C, 2)
    mono = int(np.sum(dC > 1e-9))            # calls must DECREASE in K
    convex = int(np.sum(d2C < -1e-9))        # calls must be CONVEX in K
    dig = np.array([ch.digital(float(k)) for k in Ks])
    dig_mono = int(np.sum(np.diff(dig) > 1e-9))
    return {"n_nodes": n, "monotonicity_violations": mono,
            "convexity_violations": convex,
            "digital_monotonicity_violations": dig_mono,
            "digital_max": float(dig.max()), "digital_min": float(dig.min())}


def check_calendar(chains):
    """Total variance must be monotone non-decreasing in tau at fixed k."""
    out = []
    for k in [-0.15, -0.05, 0.0, 0.05, 0.15]:
        ws = [(c.tau, c.w_at(k)) for c in sorted(chains, key=lambda c: c.tau)]
        bad = sum(1 for (t1, w1), (t2, w2) in zip(ws, ws[1:]) if w2 < w1 - 1e-12)
        out.append({"k": k, "violations": bad, "n_pairs": max(0, len(ws) - 1)})
    return out


# ------------------------------------------------------- 2c term structure
def interp_total_variance(chains, target_ms, K, now_ms):
    """Interpolate w in tau at fixed log-moneyness, then price.

    Returns (w, tau, mode, bracket) where mode is 'interp' or 'EXTRAPOLATE'.
    Extrapolating a daily/weekly surface down to a 1-hour horizon is NOT
    interpolation and is flagged as such on every call.
    """
    tau_t = (target_ms - now_ms) / (1000.0 * 365.25 * 86400.0)
    if tau_t <= 0:
        return None
    cs = sorted(chains, key=lambda c: c.tau)
    taus = [c.tau for c in cs]
    k = math.log(K / cs[0].F)
    ws = [c.w_at(k) for c in cs]
    if tau_t < taus[0]:
        # flat-vol extrapolation: hold implied variance RATE constant
        w = ws[0] * (tau_t / taus[0])
        return w, tau_t, "EXTRAPOLATE_SHORT", (taus[0] / tau_t)
    if tau_t > taus[-1]:
        w = ws[-1] * (tau_t / taus[-1])
        return w, tau_t, "EXTRAPOLATE_LONG", (tau_t / taus[-1])
    i = bisect_left(taus, tau_t)
    t0, t1 = taus[i - 1], taus[i]
    w0, w1 = ws[i - 1], ws[i]
    lam = (tau_t - t0) / (t1 - t0)
    return w0 + lam * (w1 - w0), tau_t, "interp", 1.0


# --------------------------------------------- 2d settlement-average adjust
def averaging_variance_factor(tau, avg_window_s):
    """Kalshi settles on the MEAN of the final `avg_window_s` seconds.

    For a driftless BM, Var[mean of W over the final window] relative to
    Var[W_T] is:  1 - a/tau + a^2/(3 tau^2),  a = avg_window / tau_in_seconds.
    Always <= 1: an average is less variable than a point sample, so the
    correct price sits FURTHER from 50c than a point-sample model implies.
    """
    T = tau * 365.25 * 86400.0
    if T <= 0:
        return 1.0
    a = min(avg_window_s, T) / T
    return max(1e-9, 1.0 - a + (a * a) / 3.0)


def main():
    os.makedirs(OUT, exist_ok=True)
    now_ms = int(time.time() * 1000)
    allrep = {"captured_utc": datetime.now(timezone.utc).isoformat(),
              "now_ms": now_ms,
              "thresholds": {"max_quote_age_s": MAX_QUOTE_AGE_S,
                             "min_strikes_per_expiry": MIN_STRIKES_PER_EXPIRY}}
    for cur in ["BTC", "ETH"]:
        chains, rep = build_chains(cur, now_ms)
        allrep[cur] = rep
        if not chains:
            continue
        print(f"\n{cur} no-arbitrage checks on the FITTED surface")
        arb = []
        for ch in chains:
            a = check_no_arbitrage(ch)
            a["expiry"] = ch.expiry_ms
            a["tau_h"] = round(ch.tau * 365.25 * 24, 2)
            arb.append(a)
            print(f"  tau={a['tau_h']:>8.2f}h  mono_viol={a['monotonicity_violations']:>3} "
                  f"convex_viol={a['convexity_violations']:>3} "
                  f"digital_mono_viol={a['digital_monotonicity_violations']:>3} "
                  f"digital range [{a['digital_min']:.4f}, {a['digital_max']:.4f}]")
        cal = check_calendar(chains)
        print(f"  calendar (total variance monotone in tau): "
              f"{sum(c['violations'] for c in cal)} violations across "
              f"{sum(c['n_pairs'] for c in cal)} adjacent pairs")
        rep["no_arbitrage"] = arb
        rep["calendar"] = cal

        # demo: digital + band on the nearest expiry
        ch = min(chains, key=lambda c: c.tau)
        print(f"\n  {cur} nearest expiry tau={ch.tau*365.25*24:.2f}h "
              f"F={ch.F:.2f}: P(S>K) with bid/ask band")
        print(f"    {'K':>9} {'P(S>K)':>9} {'band_lo':>9} {'band_hi':>9} "
              f"{'width':>8} {'closed-form':>12}")
        for K in np.linspace(ch.F * 0.97, ch.F * 1.03, 9):
            d = ch.digital(float(K))
            lo, hi = ch.digital_band(float(K))
            cf = bs_digital(ch.F, float(K), ch.w_at(math.log(K / ch.F)))
            print(f"    {K:>9.0f} {d:>9.4f} {lo:>9.4f} {hi:>9.4f} "
                  f"{hi-lo:>8.4f} {cf:>12.4f}")

    with open(os.path.join(OUT, "pricer_report.json"), "w") as f:
        json.dump(allrep, f, indent=2, default=str)
    print(f"\nwrote {os.path.join(OUT, 'pricer_report.json')}")


if __name__ == "__main__":
    main()
