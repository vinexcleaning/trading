"""Phase 0 probe, part 4: the fee regime break, and per-wallet endpoints.

probe_02 found fills carry fee = 0 from 2023-10 through 2026-01 and 96.6% by
2026-04. That is a regime break sitting inside the ranking window, so pin the
date down: wallets ranked on pre-break history earned their P&L without paying
the fee we would have to pay. Then check what the data API exposes per wallet,
since Phase 1 needs position accounting and a P&L cross-check.
"""
import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "probe_03_regime.json"
S = requests.Session()
S.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})
ORDERBOOK = ("https://api.goldsky.com/api/public/project_cl6mb8i9h0003e201j6li0diw"
             "/subgraphs/orderbook-subgraph/prod/gn")
DATA = "https://data-api.polymarket.com"
GAMMA = "https://gamma-api.polymarket.com"
res = {}


def rec(k, **kw):
    res[k] = kw
    print(f"  {k}: {kw.get('note', '')}", flush=True)


def gql(q, v=None):
    r = S.post(ORDERBOOK, json={"query": q, "variables": v or {}}, timeout=60)
    r.raise_for_status()
    b = r.json()
    if "errors" in b:
        raise RuntimeError(b["errors"])
    return b["data"]


def iso(ts, fmt="%Y-%m-%d"):
    return time.strftime(fmt, time.gmtime(int(ts)))


Q = """
query($lo:BigInt!,$hi:BigInt!){
  orderFilledEvents(first:1000, orderBy:timestamp, orderDirection:asc,
    where:{timestamp_gte:$lo, timestamp_lt:$hi}){ timestamp fee }
}"""


def frac_fee(day_ts):
    rows = gql(Q, {"lo": str(day_ts), "hi": str(day_ts + 86400)})["orderFilledEvents"]
    if not rows:
        return None, 0
    nz = sum(1 for r_ in rows if int(r_["fee"]) != 0)
    return nz / len(rows), len(rows)


print("== bisect the fee switch-on date (2026-01-01 .. 2026-04-28) ==")
lo, hi = 1767225600, 1777334400          # 2026-01-01, 2026-04-28
trace = []
while hi - lo > 86400:
    mid = ((lo + hi) // 2 // 86400) * 86400
    f, n = frac_fee(mid)
    trace.append({"date": iso(mid), "frac_fee": f, "n": n})
    print(f"    {iso(mid)}  n={n:>5}  fee!=0: "
          f"{'n/a' if f is None else format(f, '.2%')}", flush=True)
    if f is not None and f > 0.5:
        hi = mid
    else:
        lo = mid
rec("fee_switch_bisect", trace=trace, boundary_lo=iso(lo), boundary_hi=iso(hi),
    note=f"fees turn on between {iso(lo)} and {iso(hi)}")

print("\n== daily fraction around the boundary ==")
around = {}
for d in range(-6, 8):
    t = hi + d * 86400
    if t > 1777334400:
        break
    f, n = frac_fee(t)
    around[iso(t)] = {"frac_fee": f, "n": n}
    print(f"    {iso(t)}  n={n:>5}  fee!=0: "
          f"{'n/a' if f is None else format(f, '.2%')}", flush=True)
rec("fee_switch_daily", daily=around, note="shape of the switch-on")

print("\n== share of the subgraph history that is zero-fee ==")
first, last = 1669060209, 1777374040
rec("regime_split",
    history_start=iso(first), history_end=iso(last),
    fee_start_approx=iso(hi),
    zero_fee_days=round((hi - first) / 86400),
    fee_days=round((last - hi) / 86400),
    frac_history_zero_fee=round((hi - first) / (last - first), 4),
    note=f"{round((hi-first)/(last-first)*100)}% of on-chain history is zero-fee")

print("\n== data-api per-wallet endpoints ==")
WALLETS = ["0x173a1da136e359f050adef15a1a917b249fdeb85",
           "0xb7f945f9696f1adcbf095b5cd07af61fb1e66add"]
for w in WALLETS[:1]:
    for path, params in [
        ("/positions", {"user": w, "limit": 5}),
        ("/value", {"user": w}),
        ("/activity", {"user": w, "limit": 5}),
        ("/trades", {"user": w, "limit": 5}),
    ]:
        try:
            r = S.get(f"{DATA}{path}", params=params, timeout=45)
            j = r.json() if r.ok else None
            n = len(j) if isinstance(j, list) else None
            fields = (sorted(j[0].keys()) if isinstance(j, list) and j
                      and isinstance(j[0], dict) else None)
            rec(f"data-api{path}", ok=r.ok, http=r.status_code, n=n,
                fields=fields, sample=(j[0] if isinstance(j, list) and j else j),
                body=None if r.ok else r.text[:200],
                note=f"{'ok' if r.ok else 'FAIL'} n={n} "
                     f"fields={len(fields) if fields else 0}")
        except Exception as e:  # noqa: BLE001
            rec(f"data-api{path}", ok=False, error=repr(e), note="error")

# how deep does per-wallet activity page?
try:
    w = WALLETS[0]
    depths = {}
    for off in (0, 500, 2000, 10000):
        r = S.get(f"{DATA}/activity",
                  params={"user": w, "limit": 100, "offset": off}, timeout=45)
        j = r.json() if r.ok else None
        depths[off] = {"http": r.status_code,
                       "n": len(j) if isinstance(j, list) else None,
                       "body": None if r.ok else r.text[:120]}
    rec("data-api_activity_depth", depths=depths, note="per-wallet paging depth")
except Exception as e:  # noqa: BLE001
    rec("data-api_activity_depth", error=repr(e), note="error")

print("\n== gamma ordering ==")
for label, params in [("default", {"limit": 5}),
                      ("order=createdAt&ascending=false",
                       {"limit": 5, "order": "createdAt", "ascending": "false"}),
                      ("order=createdAt&ascending=true",
                       {"limit": 5, "order": "createdAt", "ascending": "true"})]:
    try:
        j = S.get(f"{GAMMA}/markets", params=params, timeout=45).json()
        rows = [{"id": x.get("id"), "createdAt": x.get("createdAt"),
                 "closed": x.get("closed")} for x in j]
        rec(f"gamma_order[{label}]", rows=rows,
            note=f"ids {[x['id'] for x in rows]} created {[str(x['createdAt'])[:10] for x in rows]}")
    except Exception as e:  # noqa: BLE001
        rec(f"gamma_order[{label}]", error=repr(e), note="error")

OUT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {OUT}")
