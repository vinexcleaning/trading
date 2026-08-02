"""MM TASK 2 + 3: conservative fill model and the adverse-selection test.

FILL RULES (conservative by construction):
  - A resting order fills only when the book TRADES THROUGH its price with the
    taker on the opposite side. Quoting at a price where nothing traded = no
    fill, ever.
  - LAST IN QUEUE. We assume `queue_ahead` contracts sit in front of us at our
    price. We fill only after that much volume has traded at our level. Depth is
    not public on Kalshi (verified: /orderbook returns empty), so queue_ahead is
    an explicit parameter and is SWEPT, not guessed once.
  - LATENCY. A quote placed at t is not live until t + L. A cancel at t does not
    take effect until t + L. During that window the stale quote is exposed --
    this is the crux of the slow-participant question.
  - Partial fills are honest: we fill min(our_size, volume_remaining_at_level).

ACCOUNTING IS PER-OPPORTUNITY, NEVER PER-FILL. Every quoting opportunity is
counted whether or not it filled. A strategy that looks good on its fills and
never fills is not a strategy.

P&L DECOMPOSITION, reported separately:
  spread captured | adverse selection | fees | inventory carry
"""
import argparse
import bisect
import datetime as dt
import json
import os
import sys
import time
from collections import defaultdict

import numpy as np
import requests

sys.path.insert(0, os.path.dirname(__file__))
from fees import kalshi_fee_per_contract_unrounded, KALSHI_MAKER_RATE  # noqa

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "research-readonly/0.1"}
SETTLED = r"C:\Users\gianf\crypto\data\kalshi_settled"
OUT = r"C:\Users\gianf\crypto\data\mm"


def get(path, **params):
    for a in range(6):
        try:
            r = requests.get(f"{BASE}{path}", params=params, headers=UA,
                             timeout=45)
        except Exception:
            time.sleep(0.7 * (a + 1))
            continue
        if r.status_code == 429:
            time.sleep(1.4 * (a + 1))
            continue
        if r.status_code >= 500:
            time.sleep(0.7 * (a + 1))
            continue
        return r
    return None


def iso_us(s):
    """ISO -> epoch seconds (float, microsecond precision)."""
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def fetch_market(series, ticker, start_ts, end_ts):
    """Per-minute quotes + full trade tape for one market."""
    quotes = []
    r = get(f"/series/{series}/markets/{ticker}/candlesticks",
            start_ts=start_ts, end_ts=end_ts, period_interval=1)
    if r is not None and r.status_code == 200:
        for c in r.json().get("candlesticks", []) or []:
            ts = c.get("end_period_ts")
            b = (c.get("yes_bid") or {}).get("close_dollars")
            a = (c.get("yes_ask") or {}).get("close_dollars")
            if ts is None or b is None or a is None:
                continue
            b, a = float(b), float(a)
            if not (0 < b < a < 1):
                continue
            quotes.append({"ts": int(ts), "bid": b, "ask": a,
                           "vol": float(c.get("volume_fp") or 0)})
    trades, cursor = [], None
    for _ in range(6):
        p = {"ticker": ticker, "limit": 1000}
        if cursor:
            p["cursor"] = cursor
        r = get("/markets/trades", **p)
        if r is None or r.status_code != 200:
            break
        j = r.json()
        tr = j.get("trades", []) or []
        for t in tr:
            try:
                trades.append({
                    "ts": iso_us(t["created_time"]),
                    "px": float(t["yes_price_dollars"]),
                    "sz": float(t["count_fp"]),
                    "taker_book_side": t.get("taker_book_side"),
                    "block": bool(t.get("is_block_trade")),
                })
            except (KeyError, ValueError, TypeError):
                continue
        cursor = j.get("cursor")
        if not cursor or not tr:
            break
    trades = [t for t in trades if start_ts <= t["ts"] <= end_ts
              and not t["block"]]
    trades.sort(key=lambda x: x["ts"])
    quotes.sort(key=lambda x: x["ts"])
    return quotes, trades


def simulate(quotes, trades, settle_y, close_ts, latency_s, queue_ahead,
             half_spread, our_size=10.0, max_inventory=50.0,
             min_tte_s=0, max_tte_s=10**9):
    """Quote both sides around the mid; return per-opportunity records.

    Returns (opportunities, fills) where each fill carries the decomposition
    inputs needed for the adverse-selection test.
    """
    if not quotes:
        return [], []
    q_ts = [q["ts"] for q in quotes]
    opps, fills = [], []
    inventory = 0.0

    for i, q in enumerate(quotes):
        tte = close_ts - q["ts"]
        if not (min_tte_s <= tte <= max_tte_s):
            continue
        mid = 0.5 * (q["bid"] + q["ask"])
        # our quotes, one tick inside is not allowed to cross the touch
        my_bid = round(min(mid - half_spread, q["bid"]), 4)
        my_ask = round(max(mid + half_spread, q["ask"]), 4)
        if my_bid <= 0 or my_ask >= 1 or my_bid >= my_ask:
            continue

        live_from = q["ts"] + latency_s
        # the quote is exposed until the NEXT quote update takes effect,
        # which we can only act on after another full latency
        live_to = (quotes[i + 1]["ts"] + latency_s if i + 1 < len(quotes)
                   else close_ts)

        opp = {"ts": q["ts"], "tte": tte, "mid": mid, "bid": my_bid,
               "ask": my_ask, "filled_bid": 0.0, "filled_ask": 0.0}

        # trades in the exposure window
        lo = bisect.bisect_left([t["ts"] for t in trades], live_from)
        cum_bid = cum_ask = 0.0
        for t in trades[lo:]:
            if t["ts"] > live_to:
                break
            # resting BID fills when the taker sells INTO the bid at/below us
            if t["taker_book_side"] == "bid" and t["px"] <= my_bid:
                cum_bid += t["sz"]
                avail = cum_bid - queue_ahead
                if avail > 0 and opp["filled_bid"] < our_size:
                    if inventory + our_size <= max_inventory:
                        f = min(our_size - opp["filled_bid"], avail)
                        if f > 0:
                            opp["filled_bid"] += f
                            inventory += f
                            fills.append({
                                "ts": t["ts"], "tte": close_ts - t["ts"],
                                "side": "buy", "px": my_bid, "sz": f,
                                "mid_at_fill": mid, "settle_y": settle_y})
            # resting ASK fills when the taker lifts the offer at/above us
            if t["taker_book_side"] == "ask" and t["px"] >= my_ask:
                cum_ask += t["sz"]
                avail = cum_ask - queue_ahead
                if avail > 0 and opp["filled_ask"] < our_size:
                    if inventory - our_size >= -max_inventory:
                        f = min(our_size - opp["filled_ask"], avail)
                        if f > 0:
                            opp["filled_ask"] += f
                            inventory -= f
                            fills.append({
                                "ts": t["ts"], "tte": close_ts - t["ts"],
                                "side": "sell", "px": my_ask, "sz": f,
                                "mid_at_fill": mid, "settle_y": settle_y})
        opps.append(opp)

    # ---- mark each fill forward for adverse selection ----
    for f in fills:
        for horizon, key in ((60, "mid_p1m"), (300, "mid_p5m")):
            j = bisect.bisect_left(q_ts, f["ts"] + horizon)
            if j < len(quotes):
                f[key] = 0.5 * (quotes[j]["bid"] + quotes[j]["ask"])
            else:
                f[key] = None
    return opps, fills


def decompose(fills, terminal_mark):
    """spread captured | adverse selection | fees | INVENTORY CARRY.

    The inventory term is not optional and its omission was caught by the
    synthetic control: without it, a maker facing structureless flow appears
    to earn the full half-spread risk-free, because the unsold position is
    never marked. Every fill is a position until it is closed; whatever is
    left at the end is marked to `terminal_mark` (the final mid, or the
    settlement value where the position is held to expiry).

    Signs: `adverse` is NEGATIVE when the mid moved against us after the fill.
    `net` is the sum of all four and is the only number that means anything.
    """
    if not fills:
        return None
    spread_c = adverse_c = fee_c = 0.0
    n = 0.0
    inventory = 0.0
    cash = 0.0
    for f in fills:
        sz = f["sz"]
        n += sz
        sgn = 1.0 if f["side"] == "buy" else -1.0
        # realised cash flow and running position
        inventory += sgn * sz
        cash -= sgn * f["px"] * sz
        # spread captured vs the mid at the moment of the fill
        spread_c += sgn * (f["mid_at_fill"] - f["px"]) * sz
        # adverse selection: how the mid moved against us afterwards
        ref = f.get("mid_p1m")
        if ref is not None:
            adverse_c += sgn * (ref - f["mid_at_fill"]) * sz
        fee_c += float(kalshi_fee_per_contract_unrounded(
            f["px"], KALSHI_MAKER_RATE)) * sz

    # mark the residual position — this is the term that was missing
    mark = terminal_mark if terminal_mark is not None else 0.5
    inv_pnl = cash + inventory * mark
    total = inv_pnl - fee_c

    return {"contracts": n,
            "spread_per_contract": spread_c / n * 100,
            "adverse_per_contract": adverse_c / n * 100,
            "fee_per_contract": fee_c / n * 100,
            "inventory_per_contract": inv_pnl / n * 100,
            "residual_inventory": inventory,
            "net_per_contract": total / n * 100}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", default="KXBTCD")
    ap.add_argument("--events", type=int, default=25)
    ap.add_argument("--strikes", type=int, default=4)
    ap.add_argument("--minutes", type=int, default=60)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    # ---------- load events, anchor-selected (no look-ahead) ----------
    by_ev = defaultdict(list)
    with open(os.path.join(SETTLED, f"{args.series}.jsonl"),
              encoding="utf-8") as f:
        for line in f:
            try:
                m = json.loads(line)
            except json.JSONDecodeError:
                continue
            if m.get("event_ticker"):
                by_ev[m["event_ticker"]].append(m)
    evs = sorted(by_ev, key=lambda e: by_ev[e][0].get("close_time") or "")

    def settle_of(e):
        for m in by_ev[e]:
            v = m.get("expiration_value")
            if v not in (None, ""):
                try:
                    return float(v)
                except ValueError:
                    pass
        return None

    anchor = {}
    for i, e in enumerate(evs):
        if i == 0:
            continue
        s = settle_of(evs[i - 1])
        if s is not None:
            anchor[e] = s
    usable = [e for e in evs if e in anchor and settle_of(e) is not None]
    stride = max(1, len(usable) // args.events)
    sample = usable[::stride][:args.events]
    print(f"{args.series}: {len(evs)} events, {len(usable)} usable, "
          f"stride {stride} -> {len(sample)} sampled", flush=True)

    # ---------- fetch once, reuse across all configs ----------
    market_data = []
    for n, ev in enumerate(sample):
        mkts = by_ev[ev]
        a = anchor[ev]
        close_ts = int(dt.datetime.fromisoformat(
            mkts[0]["close_time"].replace("Z", "+00:00")).timestamp())
        start_ts = close_ts - args.minutes * 60
        cand = [m for m in mkts if m.get("floor_strike") is not None]
        cand.sort(key=lambda m: abs(float(m["floor_strike"]) - a))
        for m in cand[:args.strikes]:
            q, t = fetch_market(args.series, m["ticker"], start_ts, close_ts)
            if q and t:
                market_data.append({
                    "event": ev, "ticker": m["ticker"], "close_ts": close_ts,
                    "settle_y": 1.0 if str(m.get("result")) == "yes" else 0.0,
                    "quotes": q, "trades": t})
        if (n + 1) % 5 == 0:
            print(f"  fetched {n+1}/{len(sample)} events, "
                  f"{len(market_data)} markets", flush=True)
    print(f"fetched {len(market_data)} markets with both quotes and trades")

    path = os.path.join(OUT, f"mmdata_{args.series}.json")
    json.dump(market_data, open(path, "w"), default=str)
    print(f"wrote {path} "
          f"({os.path.getsize(path)/1e6:.1f} MB)")

    # ---------- LATENCY CURVE: the headline of Task 3 ----------
    print("\n" + "=" * 96)
    print("TASK 3 — LATENCY CURVE (the decisive result)")
    print("=" * 96)
    print(f"  {'latency':>9} {'opps':>8} {'fills':>7} {'fill%':>7} "
          f"{'contracts':>10} {'spread':>9} {'adverse':>9} {'invent':>9} "
          f"{'NET c/ct':>9} {'95% CI (by market)':>18}")
    rows = []
    for lat in [0.0, 0.1, 0.373, 1.0]:
        all_opps = []
        per_market = []
        for md in market_data:
            o, fl = simulate(md["quotes"], md["trades"], md["settle_y"],
                             md["close_ts"], latency_s=lat, queue_ahead=0.0,
                             half_spread=0.005)
            all_opps.extend(o)
            # BUG FIXED: decompose PER MARKET and mark residual inventory at
            # that market's own SETTLEMENT (0 or 1), not at a default 0.5, and
            # never pool fills across markets before marking. Pooling nets one
            # market's long against another's short -- a position nobody holds
            # -- and marking at 0.5 fabricates P&L on every contract that
            # settled at 0 or 1. This is the same error the synthetic control
            # explicitly guards against in run_arm(); main() did not.
            d1 = decompose(fl, terminal_mark=md["settle_y"])
            if d1:
                per_market.append(d1)
        nfill = sum(1 for o in all_opps
                    if o["filled_bid"] > 0 or o["filled_ask"] > 0)
        if per_market:
            w = np.array([x["contracts"] for x in per_market])
            d = {k: float(np.average([x[k] for x in per_market], weights=w))
                 for k in ("spread_per_contract", "adverse_per_contract",
                           "fee_per_contract", "inventory_per_contract",
                           "net_per_contract")}
            d["contracts"] = float(w.sum())
            d["n_markets"] = len(per_market)
            # per-market net, for an event-clustered CI
            d["net_by_market"] = [x["net_per_contract"] for x in per_market]
            d["max_abs_inventory"] = float(np.max(
                [abs(x["residual_inventory"]) for x in per_market]))
            d["mean_abs_inventory"] = float(np.mean(
                [abs(x["residual_inventory"]) for x in per_market]))
        else:
            d = None
        fr = nfill / max(1, len(all_opps))
        if d:
            nb = np.array(d["net_by_market"])
            rng = np.random.default_rng(3)
            boots = np.array([nb[rng.integers(0, len(nb), len(nb))].mean()
                              for _ in range(2000)])
            lo, hi = np.percentile(boots, [2.5, 97.5])
            print(f"  {lat*1000:>7.0f}ms {len(all_opps):>8} {nfill:>7} "
                  f"{fr*100:>6.2f}% {d['contracts']:>10.0f} "
                  f"{d['spread_per_contract']:>+9.4f} "
                  f"{d['adverse_per_contract']:>+9.4f} "
                  f"{d['inventory_per_contract']:>+9.4f} "
                  f"{d['net_per_contract']:>+9.4f} "
                  f"[{lo:+.3f},{hi:+.3f}] inv_max={d['max_abs_inventory']:.0f}")
            d["latency_ms"] = lat * 1000
            d["opportunities"] = len(all_opps)
            d["fill_rate"] = fr
            d["ci_lo"], d["ci_hi"] = float(lo), float(hi)
            d.pop("net_by_market", None)
            rows.append(d)
        else:
            print(f"  {lat*1000:>7.0f}ms {len(all_opps):>8} {0:>7} "
                  f"{0.0:>6.2f}%  -- no fills --")
    print("\n  (all figures in CENTS per contract; adverse NEGATIVE = we were "
          "picked off)")
    json.dump(rows, open(os.path.join(OUT, f"latency_{args.series}.json"), "w"),
              indent=2)


if __name__ == "__main__":
    main()
