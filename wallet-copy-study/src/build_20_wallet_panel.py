"""Phase 1e: build the WALLET panel -- complete fill histories for sampled wallets.

Why a second panel. The CLOB enumeration passed 1.18M markets, so a
4,000-market sample observes ~0.4% of any wallet's activity; a wallet trading
1,000 markets would show up in about four of them. Persistence (4a) and skill
-vs-luck (4b) need many INDEPENDENT MARKETS per wallet in each of two periods,
which a market-drawn sample structurally cannot provide. probe_09 confirmed the
subgraph filters on `maker` at ~0.49s per 1000-row page, so complete per-wallet
histories are affordable. `maker_in` is rejected, so it is one wallet per query.

How wallets are drawn, and what that does and does not bias. Wallets are taken
from randomly chosen time windows spread across the whole history, which makes
the draw ACTIVITY-WEIGHTED: a wallet trading more often is likelier to be
caught. That is deliberate and stated rather than corrected -- a wallet too
inactive to appear is also too inactive to copy. What matters is that nothing
in the draw touches PERFORMANCE. Selecting wallets on past returns and then
measuring their returns is the circularity that manufactures a leaderboard of
lucky coinflips.

The market panel (build_11/12) is kept for Phase 3, where the sampling unit
really is the market.
"""
import json
import random
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "wallet_fills.jsonl"
WALLETS_OUT = ROOT / "data" / "panel_wallets.json"
STATS = ROOT / "data" / "wallet_panel_stats.json"

ORDERBOOK = ("https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw"
             "/subgraphs/orderbook-subgraph/prod/gn")

SUBGRAPH_START = 1669060209      # 2022-11-21
SUBGRAPH_END = 1777374040        # 2026-04-28
FEE_START = 1767830400           # 2026-01-08
SEED = 20260801

N_WINDOWS = 260                  # sampling windows spread over the history
WINDOW_SEC = 900                 # 15 minutes each
TARGET_WALLETS = 2500
MAX_PAGES = 80                   # 80k fills/wallet cap; truncation recorded
WORKERS = 6
USDC = 1_000_000.0

_local = threading.local()


def sess():
    if not hasattr(_local, "s"):
        s = requests.Session()
        s.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})
        _local.s = s
    return _local.s


def gql(q, v, retries=5, timeout=120):
    for a in range(retries):
        try:
            r = sess().post(ORDERBOOK, json={"query": q, "variables": v},
                            timeout=timeout)
            if r.status_code != 200:
                time.sleep(1.5 * (a + 1))
                continue
            b = r.json()
            if "errors" in b:
                time.sleep(2.0 * (a + 1))
                continue
            return b["data"]
        except Exception:  # noqa: BLE001
            time.sleep(2.0 * (a + 1))
    return None


Q_WINDOW = """
query($lo:BigInt!,$hi:BigInt!){
  orderFilledEvents(first:1000, orderBy:timestamp, orderDirection:asc,
    where:{timestamp_gte:$lo, timestamp_lt:$hi}){ maker } }
"""

Q_WALLET = """
query($w:String!,$skip:Int!){
  rows: orderFilledEvents(first:1000, skip:$skip, orderBy:timestamp,
      orderDirection:asc, where:{maker:$w}){
    id timestamp transactionHash maker taker
    makerAssetId takerAssetId makerAmountFilled takerAmountFilled fee } }
"""


# ------------------------------------------------------ 1. draw the wallets
def draw_wallets():
    rng = random.Random(SEED)
    starts = sorted(rng.randrange(SUBGRAPH_START, SUBGRAPH_END - WINDOW_SEC)
                    for _ in range(N_WINDOWS))
    seen, per_window = {}, []

    def one(lo):
        d = gql(Q_WINDOW, {"lo": str(lo), "hi": str(lo + WINDOW_SEC)})
        if not d:
            return lo, []
        return lo, [str(x["maker"]).lower() for x in d["orderFilledEvents"]]

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(one, lo) for lo in starts]
        for i, f in enumerate(as_completed(futs)):
            lo, makers = f.result()
            per_window.append({"start": lo, "n_fills": len(makers),
                               "n_distinct": len(set(makers))})
            for m in makers:
                seen.setdefault(m, lo)
            if (i + 1) % 40 == 0:
                print(f"  windows {i+1}/{len(starts)}  wallets so far "
                      f"{len(seen):,}", flush=True)
    return seen, per_window, starts


print("== drawing wallet sample from random windows ==", flush=True)
t0 = time.time()
seen, per_window, starts = draw_wallets()
print(f"  {len(seen):,} distinct wallets from {len(starts)} windows "
      f"in {time.time()-t0:.0f}s")

rng = random.Random(SEED + 1)
all_w = sorted(seen.keys())
panel = all_w if len(all_w) <= TARGET_WALLETS else rng.sample(all_w, TARGET_WALLETS)
panel = sorted(panel)
WALLETS_OUT.write_text(json.dumps(
    {"seed": SEED, "n_windows": N_WINDOWS, "window_sec": WINDOW_SEC,
     "n_discovered": len(all_w), "n_panel": len(panel),
     "draw": "activity-weighted: all distinct makers in randomly placed windows; "
             "NO performance criterion enters the draw",
     "wallets": panel}, indent=2), encoding="utf-8")
print(f"  panel: {len(panel):,} wallets")


# --------------------------------------------------- 2. pull each history
def decode(x):
    ma, ta = x["makerAssetId"], x["takerAssetId"]
    mf, tf = int(x["makerAmountFilled"]), int(x["takerAmountFilled"])
    if ma == "0" and ta != "0":
        side, token, shares, usdc = "BUY", ta, tf, mf
    elif ta == "0" and ma != "0":
        side, token, shares, usdc = "SELL", ma, mf, tf
    else:
        return None
    if shares <= 0 or usdc <= 0:
        return None
    p = usdc / shares
    if not (0.0 < p < 1.0):
        return None
    return side, token, shares / USDC, usdc / USDC, p


write_lock = threading.Lock()
counters = Counter()
per_wallet = {}


def pull(w):
    rows, trunc = [], False
    for pg in range(MAX_PAGES):
        d = gql(Q_WALLET, {"w": w, "skip": pg * 1000})
        if d is None:
            trunc = True
            break
        r = d["rows"]
        rows += r
        if len(r) < 1000:
            break
        if pg == MAX_PAGES - 1:
            trunc = True
    out = []
    for x in rows:
        if str(x["maker"]).lower() != w:
            counters["stray_maker"] += 1
            continue
        d = decode(x)
        if d is None:
            counters["undecodable"] += 1
            continue
        side, token, shares, usdc, p = d
        raw_fee = int(x["fee"])
        fee_usd = (raw_fee / USDC * p if side == "BUY" else raw_fee / USDC) if raw_fee else 0.0
        out.append({
            "wallet": w, "ts": int(x["timestamp"]), "tx": x["transactionHash"],
            "token": token, "side": side,
            "price": round(p, 8), "shares": round(shares, 6),
            "usdc": round(usdc, 6), "fee_usd": round(fee_usd, 8),
            "taker": str(x["taker"]).lower(),
        })
    return w, out, trunc, len(rows)


print("\n== pulling complete fill histories ==", flush=True)
t0 = time.time()
done = 0
with OUT.open("w", encoding="utf-8") as fh, \
        ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futs = {ex.submit(pull, w): w for w in panel}
    for f in as_completed(futs):
        w, out, trunc, n_raw = f.result()
        with write_lock:
            for r in out:
                fh.write(json.dumps(r) + "\n")
        per_wallet[w] = {"n_fills": len(out), "n_raw": n_raw, "truncated": trunc}
        counters["wallets_done"] += 1
        counters["fills"] += len(out)
        if trunc:
            counters["wallets_truncated"] += 1
        done += 1
        if done % 100 == 0:
            el = time.time() - t0
            print(f"  {done:>5}/{len(panel)}  fills={counters['fills']:>9,}  "
                  f"{el:>6.0f}s  eta {(len(panel)-done)/(done/el)/60:>5.1f}m",
                  flush=True)

el = time.time() - t0
nf = sorted(v["n_fills"] for v in per_wallet.values())
summary = {
    "seed": SEED,
    "draw": {
        "n_windows": N_WINDOWS, "window_sec": WINDOW_SEC,
        "n_discovered": len(all_w), "n_panel": len(panel),
        "weighting": "activity-weighted by construction; no performance filter",
    },
    "pull": {
        "seconds": round(el), "counters": dict(counters),
        "wallets_truncated": counters["wallets_truncated"],
        "truncation_cap_fills": MAX_PAGES * 1000,
    },
    "fills_per_wallet": {
        "total": counters["fills"],
        "mean": round(sum(nf) / len(nf), 1) if nf else 0,
        "median": nf[len(nf) // 2] if nf else 0,
        "p90": nf[int(len(nf) * 0.9)] if nf else 0,
        "p99": nf[int(len(nf) * 0.99)] if nf else 0,
        "max": nf[-1] if nf else 0,
        "zero": sum(1 for v in nf if v == 0),
    },
    "windows": {
        "mean_fills": round(sum(w["n_fills"] for w in per_window) / len(per_window), 1),
        "mean_distinct_makers": round(
            sum(w["n_distinct"] for w in per_window) / len(per_window), 1),
        "windows_hitting_1000_cap": sum(1 for w in per_window if w["n_fills"] >= 1000),
        "n_windows": len(per_window),
    },
}
STATS.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
print(f"\nwrote {OUT}, {WALLETS_OUT}, {STATS}")
