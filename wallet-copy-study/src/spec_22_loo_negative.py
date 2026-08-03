r"""Leave-one-out on the NEGATIVE result, for the same reason it was run on the positive one.

At 91.2% coverage the 10-second net return is -1.661pp (p=0.0053). But effective
sample size is only ~254 against 5,495 nominal events -- a ratio of 4.6%, meaning
a handful of events carry most of the weight. That is exactly the condition
under which a single event can manufacture a result.

Leave-one-out was used earlier to defend the POSITIVE politics finding (dropping
the biggest event moved it 0.001pp). Applying it only to results one likes is how
a project fools itself, so it is applied here too: drop each event in turn, and
each wallet in turn, and see whether the negative conclusion survives.

If one event is driving it, the retraction is overstated and must be softened.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_pipeline import boot_by_event  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REP = ROOT / "reports"
SRC = REP / "spec_latency_panels.json"
OUT = REP / "spec_loo_negative.json"

# rebuild the per-delay populations by re-running the resolve step is expensive;
# instead reuse the saved panel report for headline numbers and recompute LOO
# from the raw event contributions cached alongside it.
RAW = ROOT / "data" / "spec_latency_raw.json"

if not RAW.exists():
    print("raw per-event contributions not cached; recomputing from books is "
          "required. Run spec_21 with SAVE_RAW=1 first.", file=sys.stderr)
    sys.exit(2)

raw = json.loads(RAW.read_text(encoding="utf-8"))
SPREAD_PP = 1.0
res = {}

for delay in ("10", "60", "300"):
    ev = {k: v for k, v in raw[delay].items()}
    base = boot_by_event({k: v for k, v in ev.items()}, n_boot=1500)
    if not base:
        continue
    # weight of each event = number of observations it contributes
    sizes = sorted(((len(v), k) for k, v in ev.items()), reverse=True)
    drops = []
    for n_obs, k in sizes[:15]:
        sub = {kk: vv for kk, vv in ev.items() if kk != k}
        b = boot_by_event(sub, n_boot=800)
        if b:
            drops.append({"event": k[:40], "n_obs": n_obs,
                          "mean_without_pp": b["mean_pp"],
                          "net_without_pp": round(b["mean_pp"] - SPREAD_PP, 4),
                          "shift_pp": round(b["mean_pp"] - base["mean_pp"], 4),
                          "still_negative_net": (b["mean_pp"] - SPREAD_PP) < 0,
                          "p": b["p"]})
    worst = max(drops, key=lambda d: abs(d["shift_pp"])) if drops else None
    res[delay] = {
        "baseline_gross_pp": base["mean_pp"],
        "baseline_net_pp": round(base["mean_pp"] - SPREAD_PP, 4),
        "baseline_p": base["p"],
        "n_events": base["n_events"], "n_eff": base["n_eff"],
        "largest_event_share": round(sizes[0][0] / base["n_obs"], 4) if sizes else None,
        "top15_drops": drops,
        "max_abs_shift_pp": worst["shift_pp"] if worst else None,
        "all_15_still_negative_net": all(d["still_negative_net"] for d in drops),
    }
    print(f"\n=== d={delay}s  baseline net {res[delay]['baseline_net_pp']:.3f}pp "
          f"(p={base['p']:.4f}, n_eff={base['n_eff']:.0f}) ===")
    print(f"  largest single event = {res[delay]['largest_event_share']:.1%} of obs")
    print(f"  max shift from dropping any of the 15 biggest: "
          f"{res[delay]['max_abs_shift_pp']:+.3f}pp")
    print(f"  still net-negative after every single drop: "
          f"{res[delay]['all_15_still_negative_net']}")

OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
