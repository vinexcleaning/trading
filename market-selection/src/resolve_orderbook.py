"""STANDING BACKLOG #1 / TASK 2 — settle the LEDGER contradiction.

LEDGER.md carries two incompatible statements:
  (a) a session concluded Kalshi's /orderbook endpoint returns empty, so depth
      is not public;
  (b) S013 recorded 64,898 snapshots at 20 levels a side (set1_overshoot's
      depth recorder, still running as PID 17892).

The first probe of this session sampled 25 markets and got 0 non-empty books --
but every one of those 25 was a KXMVE* exotic parlay, i.e. a sampling artifact
of /markets default ordering, not a fact about the endpoint. This re-probes on
markets chosen BY 24h VOLUME from the full 419,828-market dump, across many
series, and also reads what the live recorder is actually writing.
"""
import json
import os
import random
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
import kalshi_api as K  # noqa: E402

DUMP = r"C:\Users\gianf\trading\market-selection\data\kalshi_markets_open.jsonl"
REP = os.path.join(os.path.dirname(__file__), "..", "reports")


def main():
    random.seed(20260802)
    by_series = defaultdict(list)
    with open(DUMP, encoding="utf-8") as fh:
        for line in fh:
            m = json.loads(line)
            v = K.f(m.get("volume_24h_fp")) or 0.0
            by_series[K.series_of(m["ticker"])].append((v, m["ticker"]))

    # top series by total 24h volume
    tot = sorted(((sum(v for v, _ in ms), s) for s, ms in by_series.items()),
                 reverse=True)
    print("top 25 series by 24h volume:")
    for v, s in tot[:25]:
        print(f"  {s:32s} {v:12.0f}  ({len(by_series[s])} markets)")

    # probe the single busiest market in each of the top 30 series,
    # plus a random market from each, so we see both ends
    probes = []
    for _, s in tot[:30]:
        ms = sorted(by_series[s], reverse=True)
        probes.append(("busiest", s, ms[0][1], ms[0][0]))
        if len(ms) > 1:
            v, t = random.choice(ms)
            probes.append(("random", s, t, v))

    print(f"\nprobing /markets/{{t}}/orderbook on {len(probes)} markets\n")
    print(f"{'kind':8s} {'series':26s} {'vol24':>9s} {'http':>4s} {'yes':>4s} {'no':>4s}")
    rows = []
    for kind, s, t, v in probes:
        r = K.get(f"/markets/{t}/orderbook", {"depth": 100})
        rec = {"kind": kind, "series": s, "ticker": t, "vol24": v,
               "http": None if r is None else r.status_code}
        if r is not None and r.status_code == 200:
            # ⚠ FIXED 2026-08-08 (mailbox 004). See probe_orderbook.py. The
            # third site, not in the original report -- the coordinator found it
            # by grepping before relaying, which is why the instruction said
            # "check for more rather than fixing exactly three".
            ob = (r.json() or {}).get("orderbook_fp") or {}
            yes, no = ob.get("yes_dollars"), ob.get("no_dollars")
            rec["yes_levels"] = len(yes) if yes else 0
            rec["no_levels"] = len(no) if no else 0
            rec["ob_keys"] = sorted(ob.keys())
            if yes:
                rec["yes_top"] = yes[:4]
            if no:
                rec["no_top"] = no[:4]
        rows.append(rec)
        print(f"{kind:8s} {s[:26]:26s} {v:9.0f} {str(rec['http']):>4s} "
              f"{str(rec.get('yes_levels','-')):>4s} {str(rec.get('no_levels','-')):>4s}")

    ok = [r for r in rows if (r.get("yes_levels") or 0) + (r.get("no_levels") or 0) > 0]
    print(f"\nnon-empty orderbooks: {len(ok)}/{len(rows)}")
    if ok:
        best = max(ok, key=lambda r: (r.get("yes_levels", 0) + r.get("no_levels", 0)))
        print("\ndeepest book seen:")
        print(json.dumps(best, indent=2)[:1200])
        lv = [r.get("yes_levels", 0) + r.get("no_levels", 0) for r in ok]
        lv.sort()
        print(f"\nlevels (both sides) on non-empty books: "
              f"min={lv[0]} median={lv[len(lv)//2]} max={lv[-1]}")

    with open(os.path.join(REP, "orderbook_resolution.json"), "w",
              encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1, default=str)
    print("\nwrote reports/orderbook_resolution.json")


if __name__ == "__main__":
    main()
