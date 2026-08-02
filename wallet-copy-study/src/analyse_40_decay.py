"""Phase 4c: edge decay. How fast does a copyable signal stop being worth copying?

Runs on the MARKET panel, which holds every fill in each sampled market. The
wallet panel cannot answer this: "the next trade after the signal" is only
meaningful if you can see all the trades, and the wallet panel sees only the
sampled wallets'.

Method. For each signal fill (a BUY at price p0 at time t), find the first
subsequent fill in the SAME token at or after t+d, for each delay d. Its price
is the best available estimate of what a copier would have transacted at. Return
to copying at delay d, held to settlement, is

    outcome - p_d - fee(p_d)

against the signal wallet's own outcome - p0 - fee(p0).

Three honest limits, all reported rather than smoothed over:

1. **Traded prices, not quotes.** The subgraph carries fills, not books, so
   p_d is a trade price and carries bid-ask bounce. A copier BUYS and would pay
   the ask, so a trade-price estimate FLATTERS the copier. Every number here is
   therefore an upper bound on copy profitability, before the spread adjustment
   applied at the end.
2. **Polygon block time is ~2s.** A +1s delay is not physically resolvable; the
   +1s column is really "the next fill in the next block or later" and is
   reported as such.
3. **Illiquid markets have no next fill for minutes.** Where no fill exists in
   the window, the observation is counted as missing rather than carried
   forward, because carrying the last price forward would invent an executable
   price that was never there.

Reflexivity is estimated from the price path after buys: a signal that is
copyable moves the price precisely because people copy it, so the measured
post-signal drift is an upper bound on what a copier keeps.
"""
import json
import math
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILLS = ROOT / "data" / "fills.jsonl"
OUT = ROOT / "reports" / "phase4c_decay.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

FEE_RATE = 0.10
DELAYS = [0, 1, 10, 60, 300, 1800]
MAX_LOOKAHEAD = 6 * 3600         # give up after 6h with no next fill
SEED = 20260801
N_BOOT = 1000


def fee(p):
    return FEE_RATE * min(p, 1 - p)


# ------------------------------------------------------------------ load
print("loading fills, grouping by token...", flush=True)
by_token = defaultdict(list)     # token -> [(ts, price, is_winner, cid, side)]
n = 0
t0 = time.time()
for line in FILLS.open(encoding="utf-8"):
    f = json.loads(line)
    n += 1
    if f.get("is_winner") is None:
        continue
    by_token[f["token"]].append(
        (f["ts"], f["price"], f["is_winner"], f["cid"], f["maker_side"]))
    if n % 2_000_000 == 0:
        print(f"  {n:,} fills  {time.time()-t0:.0f}s", flush=True)

for k in by_token:
    by_token[k].sort()
print(f"read {n:,} fills over {len(by_token):,} tokens in {time.time()-t0:.0f}s")

# ----------------------------------------------------------------- decay
print("\nmeasuring decay...", flush=True)
# per market, per delay: list of (copy_return_net, signal_return_net, dprice)
per_mkt = defaultdict(lambda: defaultdict(list))
stats = Counter()
t0 = time.time()

for tok, evs in by_token.items():
    ts_list = [e[0] for e in evs]
    L = len(evs)
    for i, (t, p0, win, cid, side) in enumerate(evs):
        if side != "BUY":
            continue
        stats["signals"] += 1
        outcome = 1.0 if win else 0.0
        sig_ret = outcome - p0 - fee(p0)
        j = i
        for d in DELAYS:
            target = t + d
            # advance to first fill at or after target
            while j < L and evs[j][0] < target:
                j += 1
            if j >= L:
                stats[f"missing_d{d}"] += 1
                continue
            t_d, p_d = evs[j][0], evs[j][1]
            if t_d - t > MAX_LOOKAHEAD:
                stats[f"stale_d{d}"] += 1
                continue
            copy_ret = outcome - p_d - fee(p_d)
            per_mkt[cid][d].append((copy_ret, sig_ret, p_d - p0, t_d - t))
            stats[f"obs_d{d}"] += 1
    if stats["signals"] > 4_000_000:
        stats["signal_cap_hit"] = 1
        break

print(f"  {stats['signals']:,} buy signals in {time.time()-t0:.0f}s")


# ------------------------------------------- market-clustered bootstrap
def boot_ci(vals_by_mkt, n_boot=N_BOOT, seed=SEED):
    """vals_by_mkt: cid -> list of floats. Resamples MARKETS."""
    keys = [k for k, v in vals_by_mkt.items() if v]
    if len(keys) < 5:
        return None
    pre = {k: (len(vals_by_mkt[k]), sum(vals_by_mkt[k])) for k in keys}
    rng = random.Random(seed)
    K = len(keys)
    out = []
    for _ in range(n_boot):
        c = s = 0
        for _ in range(K):
            a, b = pre[keys[rng.randrange(K)]]
            c += a
            s += b
        if c:
            out.append(s / c * 100)
    out.sort()
    if len(out) < 20:
        return None
    return [round(out[int(len(out) * .025)], 4), round(out[int(len(out) * .975)], 4)]


rows = {}
for d in DELAYS:
    copy_by_mkt = {cid: [x[0] for x in per_mkt[cid][d]] for cid in per_mkt if per_mkt[cid][d]}
    sig_by_mkt = {cid: [x[1] for x in per_mkt[cid][d]] for cid in per_mkt if per_mkt[cid][d]}
    dp_by_mkt = {cid: [x[2] for x in per_mkt[cid][d]] for cid in per_mkt if per_mkt[cid][d]}
    lag_all = [x[3] for cid in per_mkt for x in per_mkt[cid][d]]
    allc = [v for vs in copy_by_mkt.values() for v in vs]
    alls = [v for vs in sig_by_mkt.values() for v in vs]
    alldp = [v for vs in dp_by_mkt.values() for v in vs]
    if not allc:
        continue
    lag_all.sort()
    rows[d] = {
        "n_obs": len(allc),
        "n_markets": len(copy_by_mkt),
        "copy_return_net_pp": round(sum(allc) / len(allc) * 100, 4),
        "copy_return_ci95_pp": boot_ci(copy_by_mkt),
        "signal_return_net_pp": round(sum(alls) / len(alls) * 100, 4),
        "edge_kept_pp": round((sum(allc) / len(allc) - sum(alls) / len(alls)) * 100, 4),
        "mean_price_move_pp": round(sum(alldp) / len(alldp) * 100, 4),
        "median_actual_lag_s": lag_all[len(lag_all) // 2],
        "p90_actual_lag_s": lag_all[int(len(lag_all) * .9)],
    }
    print(f"  d={d:>5}s  n={len(allc):>9,}  copy={rows[d]['copy_return_net_pp']:>8.3f}pp  "
          f"signal={rows[d]['signal_return_net_pp']:>8.3f}pp  "
          f"dP={rows[d]['mean_price_move_pp']:>7.3f}pp  "
          f"lag_med={rows[d]['median_actual_lag_s']:>5}s", flush=True)

# ------------------------------------------------------- spread haircut
# A copier buys, so pays the ask. The subgraph has no book, so the spread is
# estimated from the dispersion of consecutive trade prices at the same instant
# -- an underestimate of the true quoted spread, and labelled as such.
print("\nestimating spread from same-second trade dispersion...", flush=True)
spreads = []
for tok, evs in list(by_token.items())[:200_000]:
    cur_t, lo, hi = None, None, None
    for t, p, *_ in evs:
        if t != cur_t:
            if cur_t is not None and hi is not None and hi > lo:
                spreads.append(hi - lo)
            cur_t, lo, hi = t, p, p
        else:
            lo, hi = min(lo, p), max(hi, p)
spreads.sort()
spread_est = {
    "n": len(spreads),
    "median_pp": round(spreads[len(spreads) // 2] * 100, 4) if spreads else None,
    "mean_pp": round(sum(spreads) / len(spreads) * 100, 4) if spreads else None,
    "p90_pp": round(spreads[int(len(spreads) * .9)] * 100, 4) if spreads else None,
    "note": "range of trade prices within the same block timestamp; a LOWER "
            "bound on the quoted spread, so the haircut below is optimistic",
}
print(f"  {spread_est}")

report = {
    "meta": {
        "n_fills": n,
        "n_tokens": len(by_token),
        "delays_s": DELAYS,
        "fee_formula": "0.10*min(p,1-p) per share (probe_02)",
        "max_lookahead_s": MAX_LOOKAHEAD,
        "clustering": "market-level bootstrap",
        "limits": [
            "p_d is a TRADE price, not an ask; a real copier pays the ask, so "
            "every copy return here is an upper bound",
            "Polygon block time ~2s, so the +1s row is really 'next block or later'",
            "no-next-fill observations counted missing, never carried forward",
        ],
    },
    "counters": dict(stats),
    "decay": {str(k): v for k, v in rows.items()},
    "spread_estimate": spread_est,
}
OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
