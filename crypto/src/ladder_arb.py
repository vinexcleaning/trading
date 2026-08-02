"""Hypotheses A1 / A2: model-free arbitrage checks on the Kalshi crypto ladders.

Needs no forecasting model at all. Two constraints must hold within one event:

  A2  MONOTONICITY (`greater` ladders, e.g. KXBTCD):
      for K1 < K2, YES(K1) >= YES(K2), because {S>K2} is a subset of {S>K1}.
      Exploitable iff  ask(K1) < bid(K2)  -- buy the cheaper lower strike, sell
      the richer higher strike, and the payoff difference is >= 0 in every state.

  A1  BUCKET SUM (`between` ladders, e.g. KXBTC):
      the buckets of one event partition the outcome space, so they sum to 1.
      Exploitable iff sum(asks) < 1 (buy the whole ladder for < $1, collect $1)
      or sum(bids) > 1 (sell the whole ladder for > $1, pay out $1).

Every violation is reported NET OF FEES on every leg and net of the spread
actually crossed, with the dwell time it survived. A violation surviving 200ms
is a data artifact; one surviving 30s with real depth is an edge.

Unit of observation: the EVENT (one settlement), never the strike. A 188-strike
ladder is one observation, not 188. See PREREGISTRATION.md section 1.
"""
import argparse
import glob
import json
import os
from collections import defaultdict
from decimal import Decimal

import sys
sys.path.insert(0, os.path.dirname(__file__))
from fees import kalshi_fee_per_contract_unrounded  # noqa: E402

ROOT = r"C:\Users\gianf\crypto\data\kalshi_quotes"


def D(x):
    if x is None or x == "":
        return None
    return Decimal(str(x))


def load_quotes(root=ROOT):
    rows = []
    for p in sorted(glob.glob(os.path.join(root, "*", "*", "*.jsonl"))):
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    rows.sort(key=lambda r: r["ts_recv_ns"])
    return rows


def replay(rows, series_filter=None):
    """Forward-fill quotes into ladder snapshots.

    The recorder writes on CHANGE only, so the live ladder at any instant is the
    forward-fill of the last quote seen per ticker. State is keyed by event so a
    snapshot is always one settlement.
    """
    state = defaultdict(dict)       # event -> ticker -> quote
    meta = {}                       # ticker -> static fields
    snapshots = []                  # (ts, event, {ticker: quote})
    for r in rows:
        if r.get("venue") != "kalshi":
            continue
        s = r.get("series")
        if series_filter and s not in series_filter:
            continue
        ev = r.get("event_ticker")
        tk = r.get("ticker")
        meta[tk] = {"floor": r.get("floor_strike"), "cap": r.get("cap_strike"),
                    "type": r.get("strike_type"), "series": s,
                    "close_ns": r.get("ts_close_ns")}
        state[ev][tk] = {
            "bid": D(r.get("yes_bid")), "ask": D(r.get("yes_ask")),
            "bid_sz": D(r.get("yes_bid_size")), "ask_sz": D(r.get("yes_ask_size")),
            "ts": r["ts_recv_ns"],
        }
        snapshots.append((r["ts_recv_ns"], ev, dict(state[ev])))
    return snapshots, meta


def check_monotonicity(snapshots, meta, min_size=Decimal("1")):
    """A2. Returns violations with fee-inclusive edge."""
    viol = []
    scans = 0
    for ts, ev, book in snapshots:
        legs = []
        for tk, q in book.items():
            m = meta.get(tk, {})
            if m.get("type") != "greater" or m.get("floor") is None:
                continue
            if q["bid"] is None or q["ask"] is None:
                continue
            legs.append((Decimal(str(m["floor"])), tk, q))
        if len(legs) < 2:
            continue
        legs.sort()
        scans += 1
        for i in range(len(legs)):
            k1, t1, q1 = legs[i]
            for j in range(i + 1, len(legs)):
                k2, t2, q2 = legs[j]
                # need ask(K1) < bid(K2) for a locked profit
                if q1["ask"] is None or q2["bid"] is None:
                    continue
                gross = q2["bid"] - q1["ask"]
                if gross <= 0:
                    continue
                if (q1["ask_sz"] or 0) < min_size or \
                   (q2["bid_sz"] or 0) < min_size:
                    continue
                fee = (kalshi_fee_per_contract_unrounded(q1["ask"])
                       + kalshi_fee_per_contract_unrounded(q2["bid"]))
                net = gross - fee
                viol.append({
                    "ts": ts, "event": ev, "k_low": float(k1),
                    "k_high": float(k2), "ask_low": float(q1["ask"]),
                    "bid_high": float(q2["bid"]),
                    "gross_c": float(gross * 100), "fee_c": float(fee * 100),
                    "net_c": float(net * 100),
                    "size": float(min(q1["ask_sz"] or 0, q2["bid_sz"] or 0)),
                    "profitable": net > 0,
                })
    return viol, scans


def event_universe(rows):
    """Every ticker that belongs to each event, across the whole recording.

    REQUIRED for A1. The recorder writes on change, so at any instant the
    forward-filled state holds only the tickers seen SO FAR. Summing those is
    summing a partial ladder: 3 of 80 buckets sum to 0.03 and look like a 97c
    risk-free profit. Buying 3 buckets does not pay $1 -- it pays $1 only if
    the outcome lands in those 3. Completeness must be enforced explicitly.
    """
    uni = defaultdict(set)
    for r in rows:
        if r.get("venue") == "kalshi" and r.get("event_ticker"):
            uni[r["event_ticker"]].add(r.get("ticker"))
    return uni


def _tiles(legs):
    """Do the bucket floors/caps tile the line contiguously, with no gap or
    overlap? A partition that does not tile is not a partition."""
    spans = []
    for m, _ in legs:
        lo = m.get("floor")
        hi = m.get("cap")
        spans.append((float(lo) if lo is not None else float("-inf"),
                      float(hi) if hi is not None else float("inf")))
    spans.sort()
    for (_, hi), (lo2, _) in zip(spans, spans[1:]):
        # Kalshi caps are one cent below the next floor (…249.99 then …250)
        if not (abs(lo2 - hi) <= 1.0):
            return False
    return True


def check_bucket_sum(snapshots, meta, universe, tol=Decimal("0")):
    """A1. Buckets of one event partition the space and must sum to 1.

    Only evaluated on COMPLETE, CONTIGUOUS ladders (see event_universe).
    """
    viol = []
    scans = 0
    skipped_incomplete = 0
    for ts, ev, book in snapshots:
        want = universe.get(ev, set())
        if not want or not want.issubset(book.keys()):
            skipped_incomplete += 1
            continue
        # A bucket FAMILY is `less` (bottom tail) + N x `between` + `greater`
        # (top tail) and partitions the line. A THRESHOLD ladder (KXBTCD) is
        # all `greater` -- nested, not a partition, so it must NOT be summed.
        # Require at least one `between` to treat the event as a partition.
        types = {meta.get(tk, {}).get("type") for tk in want}
        if "between" not in types:
            skipped_incomplete += 1
            continue
        asks, bids, legs = [], [], []
        complete = True
        for tk in want:
            q = book[tk]
            m = meta.get(tk, {})
            if m.get("type") not in ("between", "less", "greater",
                                     "greater_or_equal"):
                complete = False
                break
            if q["ask"] is None or q["bid"] is None:
                complete = False
                break
            asks.append(q["ask"])
            bids.append(q["bid"])
            legs.append((m, q))
        if not complete or len(asks) < 3:
            skipped_incomplete += 1
            continue
        if not _tiles(legs):
            skipped_incomplete += 1
            continue
        scans += 1
        sum_ask = sum(asks)
        sum_bid = sum(bids)
        n = len(asks)
        if sum_ask < Decimal(1) - tol:
            fee = sum(kalshi_fee_per_contract_unrounded(a) for a in asks)
            net = (Decimal(1) - sum_ask) - fee
            viol.append({"ts": ts, "event": ev, "kind": "buy_ladder", "n": n,
                         "sum": float(sum_ask), "gross_c": float(
                             (Decimal(1) - sum_ask) * 100),
                         "fee_c": float(fee * 100), "net_c": float(net * 100),
                         "profitable": net > 0})
        if sum_bid > Decimal(1) + tol:
            fee = sum(kalshi_fee_per_contract_unrounded(b) for b in bids)
            net = (sum_bid - Decimal(1)) - fee
            viol.append({"ts": ts, "event": ev, "kind": "sell_ladder", "n": n,
                         "sum": float(sum_bid), "gross_c": float(
                             (sum_bid - Decimal(1)) * 100),
                         "fee_c": float(fee * 100), "net_c": float(net * 100),
                         "profitable": net > 0})
    return viol, scans, skipped_incomplete


def dwell(viol, key_fn):
    """How long each distinct violation persisted."""
    seen = defaultdict(list)
    for v in viol:
        seen[key_fn(v)].append(v["ts"])
    out = []
    for k, ts in seen.items():
        ts.sort()
        out.append({"key": k, "n_obs": len(ts),
                    "dwell_s": (ts[-1] - ts[0]) / 1e9})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=ROOT)
    args = ap.parse_args()

    rows = load_quotes(args.root)
    print(f"loaded {len(rows)} recorded quote rows")
    if not rows:
        print("no data yet — recorder needs to run longer")
        return
    span = (rows[-1]["ts_recv_ns"] - rows[0]["ts_recv_ns"]) / 1e9
    print(f"span {span:.0f}s  series={sorted({r.get('series') for r in rows})}")

    snaps, meta = replay(rows)
    print(f"{len(snaps)} ladder snapshots, {len({s[1] for s in snaps})} events\n")

    print("=" * 92)
    print("A2 — MONOTONICITY of `greater` ladders (KXBTCD / KXETHD / KXSOLD)")
    print("=" * 92)
    mv, mscans = check_monotonicity(snaps, meta)
    prof = [v for v in mv if v["profitable"]]
    print(f"  {mscans} ladder scans")
    print(f"  {len(mv)} gross violations, {len(prof)} profitable NET OF FEES")
    if prof:
        prof.sort(key=lambda v: -v["net_c"])
        print(f"\n  top net-profitable violations:")
        for v in prof[:12]:
            print(f"    {v['event']:<26} K {v['k_low']:>9.0f}->{v['k_high']:>9.0f} "
                  f"ask={v['ask_low']:.4f} bid={v['bid_high']:.4f} "
                  f"gross={v['gross_c']:.2f}c fee={v['fee_c']:.2f}c "
                  f"net={v['net_c']:.2f}c sz={v['size']:.0f}")
        d = dwell(prof, lambda v: (v["event"], v["k_low"], v["k_high"]))
        d.sort(key=lambda x: -x["dwell_s"])
        print(f"\n  {len(d)} distinct violations; dwell times (s):")
        for x in d[:12]:
            print(f"    {str(x['key']):<52} n={x['n_obs']:>4} "
                  f"dwell={x['dwell_s']:.1f}s")

    print("\n" + "=" * 92)
    print("A1 — BUCKET SUM of `between` ladders (KXBTC / KXETH / KXXRP)")
    print("=" * 92)
    uni = event_universe(rows)
    bv, bscans, bskip = check_bucket_sum(snaps, meta, uni)
    bprof = [v for v in bv if v["profitable"]]
    print(f"  {bscans} COMPLETE contiguous-ladder scans "
          f"({bskip} snapshots skipped as incomplete/non-tiling)")
    print(f"  {len(bv)} gross violations, {len(bprof)} profitable NET OF FEES")
    for v in sorted(bv, key=lambda x: -x["net_c"])[:12]:
        print(f"    {v['event']:<26} {v['kind']:<12} n={v['n']:>4} "
              f"sum={v['sum']:.4f} gross={v['gross_c']:.2f}c "
              f"fee={v['fee_c']:.2f}c net={v['net_c']:.2f}c")

    out = {"quote_rows": len(rows), "span_s": span,
           "mono_scans": mscans, "mono_violations": len(mv),
           "mono_profitable": len(prof),
           "bucket_scans_complete": bscans,
           "bucket_snapshots_skipped_incomplete": bskip,
           "bucket_violations": len(bv),
           "bucket_profitable": len(bprof)}
    with open(r"C:\Users\gianf\crypto\reports\ladder_arb.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n{json.dumps(out, indent=2)}")


if __name__ == "__main__":
    main()
