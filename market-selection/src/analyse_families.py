"""TASK 2 — dimensions A, B, C per market family, and the kill switch.

Joins three measured sources, none of them documentation:
  data/kalshi_trades_24h.jsonl   the exchange-wide public trade tape
  data/kalshi_markets_open.jsonl the full 419,828-market open universe
  data/depth_broad/**/depth.jsonl the live 20-level book recorder

THE KILL SWITCH (pre-registered in DECISIONS.md D8 before the tape finished
downloading, so it cannot have been fitted to the result). A family survives
only if it clears ALL THREE:
    >= 100 trades/day
    >= 20 distinct markets traded/day
    >= 50% two-sided quote uptime
Weather markets in a prior study had perfect free settlement data going back to
2003 and ZERO fills. No counterparty means no trade at any edge size, so this
runs before anything else is considered.

Cost is NOT a kill switch. A large enough edge beats any cost. What the cost
bar reports is the SIZE of edge required.

Unit of observation is stated for every number. Trades are not independent
events: 5,000 trades in one market is not the same evidence as 5,000 trades
across 500 markets, which is why distinct-markets-traded is a separate gate
(GUARDS #8).
"""
import json
import os
import sys
import glob
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "common"))
import kalshi_api as K  # noqa: E402
import costbar  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")

MIN_TRADES_DAY = 100
MIN_MARKETS_DAY = 20
MIN_TWO_SIDED = 0.50


def pct(sorted_list, q):
    if not sorted_list:
        return None
    i = min(int(len(sorted_list) * q), len(sorted_list) - 1)
    return sorted_list[i]


def load_tape(path):
    """Per-series trade statistics from the public tape."""
    ser = defaultdict(lambda: {"n": 0, "mkts": set(), "contracts": 0.0,
                               "notional": 0.0, "prices": [], "block": 0,
                               "taker_yes": 0, "hours": set()})
    n = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                t = json.loads(line)
            except json.JSONDecodeError:
                continue        # tolerate a torn final line while still writing
            tk = t.get("ticker")
            if not tk:
                continue
            s = ser[K.series_of(tk)]
            c = K.f(t.get("count_fp")) or 0.0
            p = K.f(t.get("yes_price_dollars"))
            s["n"] += 1
            s["mkts"].add(tk)
            s["contracts"] += c
            if p is not None:
                s["prices"].append(p * 100.0)
                s["notional"] += c * p
            s["block"] += bool(t.get("is_block_trade"))
            s["taker_yes"] += (t.get("taker_outcome_side") == "yes")
            ct = t.get("created_time") or ""
            if len(ct) >= 13:
                s["hours"].add(ct[:13])
            n += 1
    return ser, n


def load_depth():
    """Per-series quote/depth statistics from the live recorder."""
    ser = defaultdict(lambda: {"snap": 0, "nonempty": 0, "two_sided": 0,
                               "spreads": [], "bid_sz": [], "ask_sz": [],
                               "top5": [], "at_tick": 0, "levels": []})
    files = glob.glob(os.path.join(DATA, "depth_broad", "*", "*", "depth.jsonl"))
    rows = 0
    for f in files:
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                s = ser[d.get("series", "?")]
                s["snap"] += 1
                rows += 1
                yes, no = d.get("yes") or [], d.get("no") or []
                if yes or no:
                    s["nonempty"] += 1
                s["levels"].append(len(yes) + len(no))
                yb, ya = d.get("yes_bid_c"), d.get("yes_ask_c")
                if yb is not None and ya is not None:
                    s["two_sided"] += 1
                    sp = ya - yb
                    s["spreads"].append(sp)
                    if sp <= 1.0:
                        s["at_tick"] += 1
                    if d.get("bid_sz") is not None:
                        s["bid_sz"].append(d["bid_sz"])
                    if d.get("ask_sz") is not None:
                        s["ask_sz"].append(d["ask_sz"])
                    # depth within 5c of the touch, both sides
                    dep = sum(sz for p, sz in yes if p >= yb - 5.0)
                    dep += sum(sz for p, sz in no if p >= (100.0 - ya) - 5.0)
                    s["top5"].append(dep)
    return ser, rows, len(files)


def main():
    tape_path = os.path.join(DATA, "kalshi_trades_24h.jsonl")
    tape, n_trades = load_tape(tape_path)
    depth, n_depth, n_files = load_depth()
    uni = {r["series"]: r for r in
           json.load(open(os.path.join(REP, "kalshi_universe.json"),
                          encoding="utf-8"))}

    hours = set()
    for s in tape.values():
        hours |= s["hours"]
    span_h = max(len(hours), 1)
    scale = 24.0 / span_h
    print(f"tape: {n_trades:,} trades over {span_h} distinct hours "
          f"(scaling to 24h by x{scale:.2f})")
    print(f"depth recorder: {n_depth:,} snapshots in {n_files} hour-files")
    print(f"universe: {len(uni):,} series\n")

    rows = []
    for s, t in tape.items():
        u = uni.get(s, {})
        d = depth.get(s)
        sp = sorted(d["spreads"]) if d else []
        prices = sorted(t["prices"])
        two_up = (d["two_sided"] / d["snap"]) if d and d["snap"] else None
        med_sp = pct(sp, 0.5)
        # cost bar at the family's own median spread and median traded price
        med_price = pct(prices, 0.5)
        bar = None
        if med_sp is not None and med_price is not None:
            bar = costbar.cost_bar_cents(round(med_price), med_sp, "kalshi")["total_c"]
        rows.append({
            "series": s,
            "category": u.get("category", ""),
            "title": (u.get("title") or "")[:44],
            "fee_type": u.get("fee_type"),
            "n_markets_open": u.get("n_markets"),
            "trades_day": round(t["n"] * scale),
            "markets_traded_day": round(len(t["mkts"]) * scale),
            "contracts_day": round(t["contracts"] * scale),
            "notional_day": round(t["notional"] * scale),
            "pct_block": round(100.0 * t["block"] / t["n"], 1),
            "taker_yes_pct": round(100.0 * t["taker_yes"] / t["n"], 1),
            "med_trade_price_c": round(med_price, 1) if med_price else None,
            "depth_snaps": d["snap"] if d else 0,
            "two_sided_uptime": round(two_up, 3) if two_up is not None else None,
            "nonempty_uptime": round(d["nonempty"] / d["snap"], 3) if d and d["snap"] else None,
            "spread_med_c": round(med_sp, 2) if med_sp is not None else None,
            "spread_p75_c": round(pct(sp, .75), 2) if sp else None,
            "spread_p90_c": round(pct(sp, .90), 2) if sp else None,
            "frac_spread_above_tick": round(1 - d["at_tick"] / len(sp), 3) if sp else None,
            "bid_sz_med": round(pct(sorted(d["bid_sz"]), .5), 1) if d and d["bid_sz"] else None,
            "ask_sz_med": round(pct(sorted(d["ask_sz"]), .5), 1) if d and d["ask_sz"] else None,
            "depth_5c_med": round(pct(sorted(d["top5"]), .5), 1) if d and d["top5"] else None,
            "cost_bar_c": bar,
        })

    # ---- the kill switch
    for r in rows:
        fails = []
        if r["trades_day"] < MIN_TRADES_DAY:
            fails.append(f"trades/day {r['trades_day']} < {MIN_TRADES_DAY}")
        if r["markets_traded_day"] < MIN_MARKETS_DAY:
            fails.append(f"markets/day {r['markets_traded_day']} < {MIN_MARKETS_DAY}")
        if r["two_sided_uptime"] is None:
            fails.append("no depth recorded (not sampled by the recorder)")
        elif r["two_sided_uptime"] < MIN_TWO_SIDED:
            fails.append(f"two-sided uptime {r['two_sided_uptime']:.1%} < {MIN_TWO_SIDED:.0%}")
        r["kill_reasons"] = fails
        r["survives"] = not fails

    rows.sort(key=lambda r: -r["trades_day"])
    with open(os.path.join(REP, "family_scorecard.json"), "w",
              encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)

    sampled = [r for r in rows if r["depth_snaps"] > 0]
    surv = [r for r in sampled if r["survives"]]
    print(f"series appearing in the tape: {len(rows)}")
    print(f"series also covered by the depth recorder: {len(sampled)}")
    print(f"of those, surviving the kill switch: {len(surv)}\n")

    hdr = (f"{'series':26s} {'cat':12s} {'trd/d':>7s} {'mkt/d':>6s} "
           f"{'2side':>6s} {'sprMed':>6s} {'p90':>5s} {'>tick':>6s} "
           f"{'bidSz':>7s} {'d5c':>8s} {'bar':>5s}  fee")
    print("SURVIVORS")
    print(hdr)
    for r in sorted(surv, key=lambda r: -r["trades_day"]):
        print(f"{r['series'][:26]:26s} {str(r['category'])[:12]:12s} "
              f"{r['trades_day']:7d} {r['markets_traded_day']:6d} "
              f"{r['two_sided_uptime']*100:5.1f}% "
              f"{str(r['spread_med_c']):>6s} {str(r['spread_p90_c']):>5s} "
              f"{str(r['frac_spread_above_tick']):>6s} "
              f"{str(r['bid_sz_med']):>7s} {str(r['depth_5c_med']):>8s} "
              f"{str(r['cost_bar_c']):>5s}  {str(r['fee_type'])[:24]}")

    print("\nKILLED (sampled by the recorder but failed a gate)")
    print(hdr)
    for r in sorted((r for r in sampled if not r["survives"]),
                    key=lambda r: -r["trades_day"]):
        print(f"{r['series'][:26]:26s} {str(r['category'])[:12]:12s} "
              f"{r['trades_day']:7d} {r['markets_traded_day']:6d} "
              f"{(str(round(r['two_sided_uptime']*100,1))+'%') if r['two_sided_uptime'] is not None else '-':>6s} "
              f"{str(r['spread_med_c']):>6s} {str(r['spread_p90_c']):>5s} "
              f"{str(r['frac_spread_above_tick']):>6s} "
              f"{str(r['bid_sz_med']):>7s} {str(r['depth_5c_med']):>8s} "
              f"{str(r['cost_bar_c']):>5s}  {'; '.join(r['kill_reasons'])[:40]}")

    print("\nTOP 30 BY TRADES/DAY, whether or not depth was sampled")
    print(f"{'series':28s} {'cat':14s} {'trd/d':>8s} {'mkt/d':>6s} "
          f"{'ctr/d':>10s} {'blk%':>5s} {'medPx':>6s}")
    for r in rows[:30]:
        print(f"{r['series'][:28]:28s} {str(r['category'])[:14]:14s} "
              f"{r['trades_day']:8d} {r['markets_traded_day']:6d} "
              f"{r['contracts_day']:10d} {r['pct_block']:5.1f} "
              f"{str(r['med_trade_price_c']):>6s}")
    print("\nwrote reports/family_scorecard.json")


if __name__ == "__main__":
    main()
