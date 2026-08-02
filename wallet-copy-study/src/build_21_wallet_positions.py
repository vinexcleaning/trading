"""Phase 1f: positions for the WALLET panel, scored against settlement.

Same accounting rules as build_13: maker leg only (probe_08 -- the taker also
appears as a maker in the same transaction in 298/298 cases, so counting both
legs double-counts), per-token rather than per-market-net (mint/merge matches
put both parties on the same side), and

    edge = realised value per share - average entry price
         = (exit proceeds + settlement value) / shares bought - cost / shares bought

never a win rate. A wallet buying at 0.90 and winning 90% has zero edge.

STREAMING, not load-into-memory. The panel's fill file runs to several GB and
this box has ~4.7GB free, so fills are aggregated incrementally and flushed per
wallet. That is safe because each wallet's rows are written contiguously and in
timestamp order by the puller; both properties are VERIFIED here rather than
assumed, and violations are counted.

Tokens with no settlement are separated into market-open, closed-without-winner,
and not-in-our-map. Collapsing those three into one "unresolved" bucket would
hide survivorship bias behind an average.
"""
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNI = ROOT / "data" / "markets_clob.jsonl"
FILLS = ROOT / "data" / "wallet_fills.jsonl"
OUT = ROOT / "data" / "wallet_positions.jsonl"
STATS = ROOT / "data" / "wallet_positions_stats.json"

FEE_START = 1767830400          # 2026-01-08
EPS = 1e-6

# ------------------------------------------- token -> market map (compact)
# token_id(int) -> cid_index*4 + code, code: 0 loser, 1 winner, 2 unknown
print("building token -> market map...", flush=True)
cids, cid_meta = [], []
tok2 = {}
n_mkt = 0
t0 = time.time()
for line in UNI.open(encoding="utf-8"):
    m = json.loads(line)
    idx = len(cids)
    cids.append(m["condition_id"])
    cid_meta.append((m.get("end_ts"), m["settle_verdict"], bool(m.get("neg_risk"))))
    win = m.get("winner_token")
    for t in m["tokens"]:
        if not t:
            continue
        try:
            k = int(t)
        except Exception:  # noqa: BLE001
            continue
        code = 2 if not win else (1 if t == win else 0)
        tok2[k] = idx * 4 + code
    n_mkt += 1
    if n_mkt % 500_000 == 0:
        print(f"  {n_mkt:,} markets  {len(tok2):,} tokens  "
              f"{time.time()-t0:.0f}s", flush=True)
print(f"  {n_mkt:,} markets -> {len(tok2):,} tokens in {time.time()-t0:.0f}s")

stats = Counter()
miss = Counter()
n_out = 0
fh = OUT.open("w", encoding="utf-8")


def flush(wallet, groups):
    """Emit one position row per (market, token) for a finished wallet."""
    global n_out
    for (idx, tokk), a in groups.items():
        end_ts, verdict, neg = cid_meta[idx]
        code = a["code"]
        if code == 2:
            is_win = None
            settle_state = ("market_open" if verdict == "open"
                            else "closed_no_winner" if verdict in
                            ("closed_no_winner", "closed_multi_winner")
                            else "unknown")
            stats[f"unsettled_{settle_state}"] += 1
        else:
            is_win = (code == 1)
            settle_state = "settled"
            stats["settled"] += 1

        shares_in, cost = a["si"], a["cost"]
        proceeds, fees = a["proc"], a["fees"]
        final_bal = a["bal"]

        flags = []
        if a["minbal"] < -EPS:
            flags.append("negative_balance_split_or_external")
            stats["flag_negative_balance"] += 1
        if shares_in <= EPS:
            flags.append("no_buys_sell_only")
            stats["flag_sell_only"] += 1
        if settle_state != "settled":
            flags.append(f"unsettled_{settle_state}")

        held = final_bal > EPS
        settle_value = (max(final_bal, 0.0) * (1.0 if is_win else 0.0)
                        if is_win is not None else None)

        if shares_in > EPS and settle_value is not None:
            entry_px = cost / shares_in
            realised = (proceeds + settle_value) / shares_in
            edge = realised - entry_px
            edge_net = edge - fees / shares_in
            pnl = proceeds + settle_value - cost - fees
        else:
            entry_px = (cost / shares_in) if shares_in > EPS else None
            realised = edge = edge_net = pnl = None

        fh.write(json.dumps({
            "wallet": wallet, "cid": cids[idx], "token": str(tokk),
            "is_winner": is_win, "settle_state": settle_state,
            "n_trades": a["n"], "n_buys": a["nb"], "n_sells": a["ns"],
            "shares_in": round(shares_in, 6), "shares_out": round(a["so"], 6),
            "cost": round(cost, 6), "proceeds": round(proceeds, 6),
            "fees": round(fees, 8), "final_balance": round(final_bal, 6),
            "held_to_settlement": held,
            "frac_held": round(max(final_bal, 0.0) / shares_in, 4) if shares_in > EPS else None,
            "entry_px": round(entry_px, 6) if entry_px is not None else None,
            "realised_per_share": round(realised, 6) if realised is not None else None,
            "edge": round(edge, 6) if edge is not None else None,
            "edge_net": round(edge_net, 6) if edge_net is not None else None,
            "pnl": round(pnl, 6) if pnl is not None else None,
            "notional": round(cost, 6),
            "first_ts": a["t0"], "last_ts": a["t1"], "end_ts": end_ts,
            "hold_seconds": a["t1"] - a["t0"],
            "fee_regime": "post" if a["t0"] >= FEE_START else "pre",
            "neg_risk": neg,
            "flags": flags,
        }) + "\n")
        n_out += 1
        stats["held_to_settlement" if held else "fully_exited"] += 1


print("\nstreaming fills...", flush=True)
cur_w = None
groups = {}
seen_wallets = set()
n = 0
t0 = time.time()

for line in FILLS.open(encoding="utf-8"):
    f = json.loads(line)
    n += 1
    w = f["wallet"]
    if w != cur_w:
        if cur_w is not None:
            flush(cur_w, groups)
        if w in seen_wallets:
            miss["wallet_block_reappeared"] += 1
        seen_wallets.add(w)
        cur_w, groups = w, {}
    try:
        k = int(f["token"])
    except Exception:  # noqa: BLE001
        miss["bad_token_id"] += 1
        continue
    packed = tok2.get(k)
    if packed is None:
        miss["token_not_in_universe"] += 1
        continue
    idx, code = packed >> 2, packed & 3
    key = (idx, k)
    a = groups.get(key)
    if a is None:
        a = groups[key] = {"si": 0.0, "so": 0.0, "cost": 0.0, "proc": 0.0,
                           "fees": 0.0, "bal": 0.0, "minbal": 0.0,
                           "n": 0, "nb": 0, "ns": 0,
                           "t0": f["ts"], "t1": f["ts"], "code": code}
    if f["ts"] < a["t1"]:
        miss["out_of_order_within_group"] += 1
    s, p = f["shares"], f["price"]
    a["fees"] += f["fee_usd"]
    a["n"] += 1
    if f["side"] == "BUY":
        a["si"] += s
        a["cost"] += s * p
        a["bal"] += s
        a["nb"] += 1
    else:
        a["so"] += s
        a["proc"] += s * p
        a["bal"] -= s
        a["ns"] += 1
    if a["bal"] < a["minbal"]:
        a["minbal"] = a["bal"]
    a["t1"] = max(a["t1"], f["ts"])
    if n % 2_000_000 == 0:
        print(f"  {n:,} fills  {n_out:,} positions  {time.time()-t0:.0f}s",
              flush=True)

if cur_w is not None:
    flush(cur_w, groups)
fh.close()
print(f"  {n:,} fills -> {n_out:,} positions in {time.time()-t0:.0f}s")
print(f"  integrity: {dict(miss)}")

# -------------------------------------------------- summarise (streaming)
print("\nsummarising...", flush=True)
per_w_mkts = defaultdict(set)
per_wm_toks = defaultdict(set)
holds, mk_regime = [], Counter()
n_clean = n_flagged = 0
p1, p2 = defaultdict(set), defaultdict(set)
CUTS = [1719792000, 1735689600, 1751328000, FEE_START]
cut_sets = [(defaultdict(set), defaultdict(set)) for _ in CUTS]

for line in OUT.open(encoding="utf-8"):
    r = json.loads(line)
    per_w_mkts[r["wallet"]].add(r["cid"])
    per_wm_toks[(r["wallet"], r["cid"])].add(r["token"])
    holds.append(r["hold_seconds"])
    mk_regime[r["fee_regime"]] += 1
    if r["flags"]:
        n_flagged += 1
    elif r["edge"] is not None:
        n_clean += 1
    for (a, b), cut in zip(cut_sets, CUTS):
        (a if r["first_ts"] < cut else b)[r["wallet"]].add(r["cid"])

holds.sort()
mkc = sorted(len(v) for v in per_w_mkts.values())
hedge = Counter()
for k, toks in per_wm_toks.items():
    hedge["traded_both_outcomes" if len(toks) > 1 else "single_outcome"] += 1


def q(xs, f):
    return xs[int(len(xs) * f)] if xs else None


def persistence(a, b, cut):
    both = [w for w in a if w in b]
    return {
        "cut_iso": time.strftime("%Y-%m-%d", time.gmtime(cut)),
        "n_wallets_p1": len(a), "n_wallets_p2": len(b),
        "n_wallets_both": len(both),
        "n_both_ge10_each": sum(1 for w in both if len(a[w]) >= 10 and len(b[w]) >= 10),
        "n_both_ge20_each": sum(1 for w in both if len(a[w]) >= 20 and len(b[w]) >= 20),
        "n_both_ge50_each": sum(1 for w in both if len(a[w]) >= 50 and len(b[w]) >= 50),
    }


summary = {
    "n_markets_in_map": n_mkt, "n_tokens_in_map": len(tok2),
    "n_fills_read": n, "integrity": dict(miss),
    "n_positions": n_out, "n_distinct_wallets": len(per_w_mkts),
    "counters": dict(stats),
    "settlement_availability": {
        "settled": stats["settled"],
        "market_open": stats["unsettled_market_open"],
        "closed_no_winner": stats["unsettled_closed_no_winner"],
        "unknown": stats["unsettled_unknown"],
        "frac_settled": round(stats["settled"] / max(n_out, 1), 4),
    },
    "coverage_gaps": {
        "negative_balance_split_or_external": stats["flag_negative_balance"],
        "sell_only_no_entry_price": stats["flag_sell_only"],
        "token_not_in_universe_fills": miss["token_not_in_universe"],
        "n_flagged": n_flagged, "n_clean_for_edge_stats": n_clean,
        "frac_flagged": round(n_flagged / max(n_out, 1), 4),
    },
    "settlement_behaviour": {
        "held_to_settlement": stats["held_to_settlement"],
        "fully_exited": stats["fully_exited"],
        "frac_held": round(stats["held_to_settlement"] / max(n_out, 1), 4),
    },
    "hedging": dict(hedge),
    "hedge_rate": round(hedge["traded_both_outcomes"] / max(len(per_wm_toks), 1), 4),
    "hold_seconds": {"p25": q(holds, .25), "median": q(holds, .5),
                     "p75": q(holds, .75), "p95": q(holds, .95),
                     "max": holds[-1] if holds else None},
    "markets_per_wallet": {
        "median": q(mkc, .5), "p90": q(mkc, .9), "p99": q(mkc, .99),
        "max": mkc[-1] if mkc else None,
        "n_ge_20": sum(1 for v in mkc if v >= 20),
        "n_ge_50": sum(1 for v in mkc if v >= 50),
        "n_ge_100": sum(1 for v in mkc if v >= 100)},
    "persistence_feasibility": [persistence(a, b, c)
                                for (a, b), c in zip(cut_sets, CUTS)],
    "by_regime": dict(mk_regime),
}
STATS.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
print(f"\nwrote {OUT} and {STATS}")
