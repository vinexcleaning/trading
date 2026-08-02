"""Re-probe the families the wide sweep called dead, using FRESH market lists.

The wide sweep picked tickers from a market dump taken at 02:12 UTC. By probe
time that dump was ~5.5 h stale, and short-lived families -- KXBTC15M and the
other 15-minute crypto series, in-play game markets -- had already settled the
markets it chose. "No depth" on a settled market is not "no counterparty"; it
is a closed book.

KXBTC15M is the single busiest family in the tape (1.19 M trades). Killing it
on a stale ticker would be exactly the class of error this project keeps
finding in its own history, so every family the sweep called dead is re-listed
live and re-probed before any kill is written down.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import kalshi_api as K  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
REP = os.path.join(ROOT, "reports")
PER = 4


def main():
    sweep = json.load(open(os.path.join(REP, "depth_sweep_wide.json"),
                           encoding="utf-8"))
    dead = [r for r in sweep
            if r.get("status") == "ok" and r.get("sampled") and r["two_sided"] == 0]
    dead.sort(key=lambda r: -r["trades_in_tape"])
    print(f"re-probing {len(dead)} families with FRESH listings\n")
    print(f"{'series':30s} {'trades':>8s} {'open':>5s} {'samp':>5s} "
           f"{'2sided':>6s} {'spread':>7s} {'bidSz':>10s}  verdict")
    out = []
    for r in dead:
        s = r["series"]
        rr = K.get("/markets", {"series_ticker": s, "status": "open",
                                "limit": 200})
        ms = rr.json().get("markets", []) if rr and rr.status_code == 200 else []
        # busiest first, by CURRENT 24h volume
        ms.sort(key=lambda m: -(K.f(m.get("volume_24h_fp")) or 0.0))
        rec = {"series": s, "trades_in_tape": r["trades_in_tape"],
               "open_now": len(ms), "sampled": 0, "two_sided": 0,
               "any_depth": 0, "spreads": [], "bid_sz": []}
        for m in ms[:PER]:
            yes, no = K.orderbook(m["ticker"])
            if yes is None and no is None:
                continue
            yes, no = yes or [], no or []
            rec["sampled"] += 1
            if yes or no:
                rec["any_depth"] += 1
            yb, ya, bs, _ = K.touch(yes, no)
            if yb is not None and ya is not None:
                rec["two_sided"] += 1
                rec["spreads"].append(round(ya - yb, 2))
                if bs is not None:
                    rec["bid_sz"].append(bs)
        n = rec["sampled"] or 1
        rec["pct_two_sided"] = round(100 * rec["two_sided"] / n, 1)
        rec["spread_med_c"] = (sorted(rec["spreads"])[len(rec["spreads"]) // 2]
                               if rec["spreads"] else None)
        rec["bid_sz_med"] = (round(sorted(rec["bid_sz"])[len(rec["bid_sz"]) // 2], 1)
                             if rec["bid_sz"] else None)
        if rec["open_now"] == 0:
            rec["verdict"] = "NO OPEN MARKETS"
        elif rec["two_sided"] > 0:
            rec["verdict"] = "REVIVED -- stale ticker, family is quoted"
        elif rec["any_depth"] > 0:
            rec["verdict"] = "ONE-SIDED only"
        else:
            rec["verdict"] = "CONFIRMED no book"
        out.append(rec)
        print(f"{s[:30]:30s} {rec['trades_in_tape']:8d} {rec['open_now']:5d} "
              f"{rec['sampled']:5d} {rec['pct_two_sided']:5.1f}% "
              f"{str(rec['spread_med_c']):>7s} {str(rec['bid_sz_med']):>10s}  "
              f"{rec['verdict']}")

    with open(os.path.join(REP, "reprobe_dead.json"), "w",
              encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    rev = [r for r in out if r["verdict"].startswith("REVIVED")]
    conf = [r for r in out if r["verdict"] == "CONFIRMED no book"]
    one = [r for r in out if r["verdict"] == "ONE-SIDED only"]
    print(f"\nREVIVED (the sweep was wrong): {len(rev)}")
    print(f"ONE-SIDED only:                 {len(one)}")
    print(f"CONFIRMED no book:              {len(conf)}")
    print(f"NO OPEN MARKETS right now:      "
          f"{sum(1 for r in out if r['verdict']=='NO OPEN MARKETS')}")


if __name__ == "__main__":
    main()
