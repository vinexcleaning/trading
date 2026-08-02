"""Re-run the latency curve with the per-market settlement marking fix."""
import json
import sys

import numpy as np

sys.path.insert(0, r"C:\Users\gianf\crypto\src")
from mm_fill_model import simulate, decompose  # noqa: E402

md = json.load(open(r"C:\Users\gianf\crypto\data\mm\mmdata_KXBTCD.json"))
for m in md:
    m["close_ts"] = int(m["close_ts"])
    m["settle_y"] = float(m["settle_y"])
    for q in m["quotes"]:
        q["ts"] = int(q["ts"])
    for t in m["trades"]:
        t["ts"] = float(t["ts"])
        t["px"] = float(t["px"])
        t["sz"] = float(t["sz"])

print(f"markets={len(md)}  events={len({m['event'] for m in md})}")
hdr = (f"{'lat':>8} {'fill%':>7} {'contracts':>10} {'spread':>9} "
       f"{'adverse':>9} {'invent':>9} {'NET':>9} {'95% CI (market)':>20} "
       f"{'inv_max':>8}")
print(hdr)
out = []
for lat in [0.0, 0.1, 0.373, 1.0]:
    opps, pm = [], []
    for m in md:
        o, f = simulate(m["quotes"], m["trades"], m["settle_y"],
                        m["close_ts"], latency_s=lat, queue_ahead=0.0,
                        half_spread=0.005)
        opps += o
        d = decompose(f, terminal_mark=m["settle_y"])
        if d:
            pm.append(d)
    w = np.array([x["contracts"] for x in pm])
    agg = {k: float(np.average([x[k] for x in pm], weights=w))
           for k in ("spread_per_contract", "adverse_per_contract",
                     "inventory_per_contract", "net_per_contract")}
    nb = np.array([x["net_per_contract"] for x in pm])
    rng = np.random.default_rng(3)
    bs = np.array([nb[rng.integers(0, len(nb), len(nb))].mean()
                   for _ in range(2000)])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    nf = sum(1 for o in opps if o["filled_bid"] > 0 or o["filled_ask"] > 0)
    invmax = max(abs(x["residual_inventory"]) for x in pm)
    invmean = float(np.mean([abs(x["residual_inventory"]) for x in pm]))
    ci = f"[{lo:+.3f},{hi:+.3f}]"
    print(f"{lat*1000:>6.0f}ms {100*nf/len(opps):>6.2f}% {w.sum():>10.0f} "
          f"{agg['spread_per_contract']:>+9.4f} "
          f"{agg['adverse_per_contract']:>+9.4f} "
          f"{agg['inventory_per_contract']:>+9.4f} "
          f"{agg['net_per_contract']:>+9.4f} {ci:>20} {invmax:>8.0f}")
    out.append({"latency_ms": lat * 1000, "n_markets": len(pm),
                "contracts": float(w.sum()), "fill_rate": nf / len(opps),
                "ci_lo": float(lo), "ci_hi": float(hi),
                "inv_max": float(invmax), "inv_mean_abs": invmean, **agg})

print("\nunit of observation = MARKET (n={}), CI bootstraps markets"
      .format(len(md)))
json.dump(out, open(r"C:\Users\gianf\crypto\reports\mm_latency_fixed.json",
                    "w"), indent=2)
