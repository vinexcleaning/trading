r"""Task 5 pull, windowed: fetch only the price window each position actually needs.

The full-book pull was fetching entire token histories and a handful of
very-high-volume tokens dominated it -- batches 141-160 alone took 40 minutes
and pushed the ETA to 300 minutes, for tokens carrying a median of ONE survivor
position each.

Task 5 does not need a token's whole history. For a position entered at t it
needs prices in [t, t + 1800s], plus a lookahead buffer so the +1800s reading can
find the next print. So each token is fetched with a timestamp filter covering
only its own needed span, and tokens are SORTED BY WINDOW START before batching
so that 25 consecutive tokens share a tight time range instead of spanning
months.

Buffer and lookahead are kept consistent on purpose: the window extends to
t + 1800 + LOOKAHEAD and the analysis uses the same LOOKAHEAD, so any price the
analysis can find is guaranteed to be inside what was pulled. Getting that wrong
would silently drop the +1800s column for exactly the illiquid markets where it
matters most.

Resumes from the same journal as the full-book puller; the 4,000 tokens already
fetched in full are a superset of what is needed and are skipped.
"""
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "data" / "spec_panel.jsonl"
TARGETS = ROOT / "data" / "spec_task5_targets.json"
OUT = ROOT / "data" / "spec_task5_fills.jsonl"
DONE = ROOT / "data" / "spec_task5_done.json"
STATS = ROOT / "reports" / "spec_task5_pull_stats.json"

ORDERBOOK = ("https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw"
             "/subgraphs/orderbook-subgraph/prod/gn")
S = requests.Session()
S.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})

CUT = 1767830400
MAX_DELAY = 1800
LOOKAHEAD = 3600          # must match spec_08_latency MAX_LOOKAHEAD
PRE = 60
BATCH = 25
PAGE = 1000
MAX_PAGES = 60
USDC = 1_000_000.0

Q = """
query($toks:[BigInt!],$lo:BigInt!,$hi:BigInt!,$skip:Int!){
  rows: orderFilledEvents(first:1000, skip:$skip, orderBy:timestamp, orderDirection:asc,
      where:{%s:$toks, timestamp_gte:$lo, timestamp_lt:$hi}){
    id timestamp maker makerAssetId takerAssetId
    makerAmountFilled takerAmountFilled fee } }
"""
Q_MAKER = Q % "makerAssetId_in"
Q_TAKER = Q % "takerAssetId_in"


def gql(q, v, retries=4):
    for a in range(retries):
        try:
            r = S.post(ORDERBOOK, json={"query": q, "variables": v}, timeout=180)
            if r.status_code == 429:
                time.sleep(6 * (a + 1))
                continue
            if r.status_code != 200:
                time.sleep(2 * (a + 1))
                continue
            b = r.json()
            if "errors" in b:
                time.sleep(2 * (a + 1))
                continue
            return b["data"]
        except Exception:  # noqa: BLE001
            time.sleep(2 * (a + 1))
    return None


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
    if not 0.0 < p < 1.0:
        return None
    return side, token, shares / USDC, usdc / USDC, p


cfg = json.loads(TARGETS.read_text(encoding="utf-8"))
survivors = set(cfg["survivors"])
need = set(cfg["tokens_to_pull"])

print("computing per-token time windows...", flush=True)
win = {}
for line in PANEL.open(encoding="utf-8"):
    r = json.loads(line)
    if r["ts"] < CUT or r["w"] not in survivors:
        continue
    t = r["tok"]
    if t not in need:
        continue
    lo, hi = r["ts"] - PRE, r["ts"] + MAX_DELAY + LOOKAHEAD
    if t in win:
        a, b = win[t]
        win[t] = (min(a, lo), max(b, hi))
    else:
        win[t] = (lo, hi)
print(f"  {len(win):,} tokens need windows")

done = set(json.loads(DONE.read_text(encoding="utf-8"))) if DONE.exists() else set()
todo = sorted((t for t in win if t not in done), key=lambda t: win[t][0])
print(f"  {len(done):,} already pulled (full book); {len(todo):,} remaining")

spans = [win[t][1] - win[t][0] for t in todo]
spans.sort()
print(f"  window span: median {spans[len(spans)//2]/3600:.1f}h, "
      f"max {spans[-1]/3600:.1f}h" if spans else "  none")

batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
print(f"  {len(batches):,} batches of {BATCH}, sorted by window start\n",
      flush=True)

stats = Counter()
t0 = time.time()
n_rows = 0
with OUT.open("a", encoding="utf-8") as fh:
    for i, b in enumerate(batches):
        lo = min(win[t][0] for t in b)
        hi = max(win[t][1] for t in b)
        stats["batch_span_h"] += (hi - lo) / 3600
        got = {}
        for q in (Q_MAKER, Q_TAKER):
            for pg in range(MAX_PAGES):
                d = gql(q, {"toks": b, "lo": str(lo), "hi": str(hi),
                            "skip": pg * PAGE})
                if d is None:
                    stats["page_failed"] += 1
                    break
                rows = d["rows"]
                for r_ in rows:
                    got[r_["id"]] = r_
                if len(rows) < PAGE:
                    break
                if pg == MAX_PAGES - 1:
                    stats["batch_truncated"] += 1
        wanted = set(b)
        for x in got.values():
            dd = decode(x)
            if dd is None:
                continue
            side, token, shares, usdc, p = dd
            if token not in wanted:
                continue
            fh.write(json.dumps({
                "token": token, "ts": int(x["timestamp"]), "side": side,
                "price": round(p, 8), "shares": round(shares, 6),
                "usdc": round(usdc, 6), "maker": str(x["maker"]).lower(),
            }) + "\n")
            n_rows += 1
        done.update(b)
        stats["batches_done"] += 1
        if (i + 1) % 25 == 0:
            fh.flush()
            DONE.write_text(json.dumps(sorted(done)), encoding="utf-8")
            el = time.time() - t0
            rate = (i + 1) / el
            print(f"  batch {i+1:>5}/{len(batches)}  fills={n_rows:>9,}  "
                  f"{el:>6.0f}s  eta {(len(batches)-i-1)/rate/60:>6.1f}m",
                  flush=True)

DONE.write_text(json.dumps(sorted(done)), encoding="utf-8")
el = time.time() - t0
summary = {"mode": "windowed", "n_tokens_targeted": len(cfg["tokens_to_pull"]),
           "n_tokens_done": len(done), "n_new_fills": n_rows,
           "seconds": round(el), "batch_size": BATCH,
           "window": {"pre_s": PRE, "max_delay_s": MAX_DELAY,
                      "lookahead_s": LOOKAHEAD},
           "counters": {k: (round(v, 1) if isinstance(v, float) else v)
                        for k, v in stats.items()}}
STATS.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
print(f"\nwrote {OUT}")
