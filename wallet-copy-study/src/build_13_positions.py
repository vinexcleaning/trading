"""Phase 1d: reconstruct actual positions. Outcome lookups are NOT P&L.

Unit of accounting is (wallet, market, outcome token). Each `orderFilledEvent`
is one order-fill belonging to ONE wallet -- the `maker` field. probe_08 showed
the taker address also appears as a maker in the same transaction in 298 of 298
transactions, so the aggressor has its own row; using both legs would
double-count every trade.

Per-token accounting, not per-market-net, because Polymarket matches include
mint (both parties BUY complementary tokens) and merge (both SELL) types --
probe_08 found 218 of 298 transactions had all makers on the same side. A
wallet buying NO at 0.30 is a different position from one selling YES at 0.70
even though the exposure rhymes, and netting them would erase the entry price
that the whole study is built on.

The metric is realised value per share MINUS average entry price. Never a win
rate: a wallet buying at 0.90 and winning 90% of the time has zero edge.

Realised value per share = (exit proceeds + settlement value) / shares bought

so a position exited early is scored at its exit price and one held to
settlement at 0 or 1. That is the wallet's realised outcome, which is what the
`won` field failed to be.

Negative running balances are FLAGGED, not repaired: a wallet can acquire
tokens by splitting USDC into a complete set, and splits/merges are
ConditionalTokens events absent from the orderbook subgraph. Those positions
have an entry cost we cannot see, so they are excluded from edge statistics and
reported as a coverage gap.
"""
import json
import math
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILLS = ROOT / "data" / "fills.jsonl"
SAMPLE = ROOT / "data" / "sample_markets.jsonl"
OUT = ROOT / "data" / "positions.jsonl"
STATS = ROOT / "data" / "positions_stats.json"

FEE_START = 1767830400          # 2026-01-08
EPS = 1e-6

markets = {}
for l in SAMPLE.open(encoding="utf-8"):
    m = json.loads(l)
    markets[m["condition_id"]] = m

print(f"markets in sample: {len(markets)}")

# ---------------------------------------------------- group fills by wallet
# (wallet, cid, token) -> list of (ts, side, shares, price, fee)
book = defaultdict(list)
n = 0
t0 = time.time()
for line in FILLS.open(encoding="utf-8"):
    f = json.loads(line)
    book[(f["maker"], f["cid"], f["token"])].append(
        (f["ts"], f["maker_side"], f["shares"], f["price"], f["maker_fee_usd"]))
    n += 1
    if n % 2_000_000 == 0:
        print(f"  read {n:,} fills  {time.time()-t0:.0f}s", flush=True)
print(f"read {n:,} fills into {len(book):,} (wallet,market,token) groups "
      f"in {time.time()-t0:.0f}s")

stats = Counter()
n_out = 0

with OUT.open("w", encoding="utf-8") as fh:
    for (wallet, cid, token), evs in book.items():
        m = markets.get(cid)
        if m is None:
            stats["market_missing"] += 1
            continue
        evs.sort()

        shares_in = cost = shares_out = proceeds = fees = 0.0
        bal = 0.0
        min_bal = 0.0
        n_buy = n_sell = 0
        for ts, side, s, p, fee in evs:
            fees += fee
            if side == "BUY":
                shares_in += s
                cost += s * p
                bal += s
                n_buy += 1
            else:
                shares_out += s
                proceeds += s * p
                bal -= s
                n_sell += 1
            min_bal = min(min_bal, bal)

        first_ts, last_ts = evs[0][0], evs[-1][0]
        end_ts = m.get("end_ts")
        is_winner = (token == m.get("winner_token"))
        final_bal = bal

        # --- coverage flags, applied rather than silently repaired
        flags = []
        if min_bal < -EPS:
            flags.append("negative_balance_split_or_external")
            stats["flag_negative_balance"] += 1
        if shares_in <= EPS:
            flags.append("no_buys_sell_only")
            stats["flag_sell_only"] += 1
        if final_bal < -EPS:
            flags.append("ends_short")
            stats["flag_ends_short"] += 1

        settle_value = max(final_bal, 0.0) * (1.0 if is_winner else 0.0)
        held_to_settlement = final_bal > EPS

        # --- the edge metric
        if shares_in > EPS:
            entry_px = cost / shares_in
            realised_per_share = (proceeds + settle_value) / shares_in
            edge = realised_per_share - entry_px
            # net of the fee the wallet actually paid, per share bought
            edge_net = edge - (fees / shares_in)
        else:
            entry_px = realised_per_share = edge = edge_net = None

        pnl = proceeds + settle_value - cost - fees
        frac_held = (max(final_bal, 0.0) / shares_in) if shares_in > EPS else None

        row = {
            "wallet": wallet, "cid": cid, "token": token,
            "is_winner": is_winner,
            "n_trades": len(evs), "n_buys": n_buy, "n_sells": n_sell,
            "shares_in": round(shares_in, 6), "shares_out": round(shares_out, 6),
            "cost": round(cost, 6), "proceeds": round(proceeds, 6),
            "fees": round(fees, 8),
            "final_balance": round(final_bal, 6),
            "settle_value": round(settle_value, 6),
            "held_to_settlement": held_to_settlement,
            "frac_held_to_settlement": round(frac_held, 4) if frac_held is not None else None,
            "entry_px": round(entry_px, 6) if entry_px is not None else None,
            "realised_per_share": round(realised_per_share, 6) if realised_per_share is not None else None,
            "edge": round(edge, 6) if edge is not None else None,
            "edge_net": round(edge_net, 6) if edge_net is not None else None,
            "pnl": round(pnl, 6),
            "first_ts": first_ts, "last_ts": last_ts, "end_ts": end_ts,
            "hold_seconds": last_ts - first_ts,
            "hold_to_end_seconds": (end_ts - first_ts) if end_ts else None,
            "fee_regime": ("post" if first_ts >= FEE_START else "pre"),
            "flags": flags,
        }
        fh.write(json.dumps(row) + "\n")
        n_out += 1
        stats["positions"] += 1
        if held_to_settlement:
            stats["held_to_settlement"] += 1
        else:
            stats["fully_exited_before_settlement"] += 1

print(f"wrote {n_out:,} positions")

# ------------------------------------------------ hedging, at market level
print("computing hedge rate...")
per_wm = defaultdict(list)
for line in OUT.open(encoding="utf-8"):
    r = json.loads(line)
    per_wm[(r["wallet"], r["cid"])].append(r)

hedge = Counter()
for (w, cid), rows in per_wm.items():
    toks = {r["token"] for r in rows}
    if len(toks) > 1:
        # held both outcomes with positive balance at the end?
        pos = [r for r in rows if r["final_balance"] > EPS]
        hedge["traded_both_outcomes"] += 1
        if len({r["token"] for r in pos}) > 1:
            hedge["held_both_outcomes_at_settlement"] += 1
    else:
        hedge["single_outcome_only"] += 1

# ------------------------------------------------------------- composition
rows = [json.loads(l) for l in OUT.open(encoding="utf-8")]
clean = [r for r in rows if not r["flags"] and r["edge"] is not None]
holds = sorted(r["hold_seconds"] for r in rows)
wallets = Counter(r["wallet"] for r in rows)
mk_per_wallet = Counter()
for (w, cid) in per_wm:
    mk_per_wallet[w] += 1
mkc = sorted(mk_per_wallet.values())

summary = {
    "n_fills_read": n,
    "n_positions": len(rows),
    "n_wallet_markets": len(per_wm),
    "n_distinct_wallets": len(wallets),
    "counters": dict(stats),
    "hedging": dict(hedge),
    "hedge_rate_traded_both": round(
        hedge["traded_both_outcomes"] / max(len(per_wm), 1), 4),
    "settlement": {
        "held_to_settlement": stats["held_to_settlement"],
        "fully_exited": stats["fully_exited_before_settlement"],
        "frac_held": round(stats["held_to_settlement"] / max(len(rows), 1), 4),
    },
    "coverage_gaps": {
        "negative_balance_split_or_external": stats["flag_negative_balance"],
        "sell_only_no_entry_price": stats["flag_sell_only"],
        "ends_short": stats["flag_ends_short"],
        "frac_positions_flagged": round(
            sum(1 for r in rows if r["flags"]) / max(len(rows), 1), 4),
        "n_clean_for_edge_stats": len(clean),
    },
    "hold_seconds": {
        "median": holds[len(holds) // 2] if holds else None,
        "p25": holds[len(holds) // 4] if holds else None,
        "p75": holds[3 * len(holds) // 4] if holds else None,
        "max": holds[-1] if holds else None,
    },
    "markets_per_wallet": {
        "median": mkc[len(mkc) // 2] if mkc else None,
        "p90": mkc[int(len(mkc) * 0.9)] if mkc else None,
        "p99": mkc[int(len(mkc) * 0.99)] if mkc else None,
        "max": mkc[-1] if mkc else None,
        "n_wallets_ge_20_markets": sum(1 for v in mkc if v >= 20),
        "n_wallets_ge_50_markets": sum(1 for v in mkc if v >= 50),
        "n_wallets_ge_100_markets": sum(1 for v in mkc if v >= 100),
    },
    "by_regime": dict(Counter(r["fee_regime"] for r in rows)),
}
STATS.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
print(f"\nwrote {OUT} and {STATS}")
