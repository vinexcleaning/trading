"""Which endpoint can actually enumerate resolved markets with settlement?

build_10 died twice over: Gamma stops responding past offset ~2500, and
newest-first paging lands entirely outside the subgraph window (markets closing
after 2026-04-28). Both are fixable only if some endpoint enumerates deeply.

Candidates:
  A. CLOB /markets  -- cursor-paged, and its `tokens[]` carry a `winner` flag,
     which would be settlement straight from the venue rather than inferred
     from Gamma's outcomePrices strings.
  B. Gamma with date filters -- but its filters are mostly ignored, so any
     filter used must be verified on the returned rows.
"""
import json
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "probe_06_universe_src.json"
S = requests.Session()
S.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})
CLOB = "https://clob.polymarket.com"
GAMMA = "https://gamma-api.polymarket.com"
res = {}


def rec(k, **kw):
    res[k] = kw
    print(f"  {k}: {kw.get('note', '')}", flush=True)


print("== A. CLOB /markets shape ==")
r = S.get(f"{CLOB}/markets", timeout=60)
j = r.json()
m0 = j["data"][0]
rec("clob_market_fields", fields=sorted(m0.keys()),
    tokens_sample=m0.get("tokens"),
    count=j.get("count"), next_cursor=j.get("next_cursor"),
    note=f"{len(j['data'])} rows/page; token fields="
         f"{sorted(m0['tokens'][0].keys()) if m0.get('tokens') else None}")

print("\n== A2. how deep does the CLOB cursor page? ==")
cur, pages, seen, t0 = "", 0, set(), time.time()
winners, closed_ct, end_dates = Counter(), Counter(), []
while pages < 60:
    rr = S.get(f"{CLOB}/markets", params={"next_cursor": cur} if cur else {},
               timeout=60)
    if not rr.ok:
        rec("clob_paging_stop", pages=pages, http=rr.status_code,
            body=rr.text[:200], note=f"stopped at page {pages}")
        break
    jj = rr.json()
    data = jj.get("data", [])
    if not data:
        rec("clob_paging_stop", pages=pages, note="empty page")
        break
    for m in data:
        seen.add(m.get("condition_id"))
        closed_ct[bool(m.get("closed"))] += 1
        toks = m.get("tokens") or []
        w = [t.get("winner") for t in toks]
        if m.get("closed"):
            winners["has_true_winner" if any(w) else "closed_no_winner"] += 1
        if m.get("end_date_iso"):
            end_dates.append(m["end_date_iso"][:10])
    cur = jj.get("next_cursor") or ""
    pages += 1
    if cur in ("LTE=", ""):
        rec("clob_paging_end", pages=pages, note="reached terminal cursor LTE=")
        break
el = time.time() - t0
rec("clob_paging", pages=pages, n_unique_conditions=len(seen),
    seconds=round(el, 1), per_page=round(len(seen) / max(pages, 1)),
    closed=dict(closed_ct), winner_flags=dict(winners),
    end_date_range=[min(end_dates), max(end_dates)] if end_dates else None,
    note=f"{len(seen)} markets in {pages} pages / {el:.0f}s; "
         f"end dates {min(end_dates) if end_dates else '?'}..{max(end_dates) if end_dates else '?'}")

print("\n== B. Gamma offset ceiling ==")
ceiling = {}
for off in (0, 1000, 2000, 2400, 2500, 3000, 5000, 10000):
    try:
        rr = S.get(f"{GAMMA}/markets",
                   params={"limit": 100, "offset": off, "order": "createdAt",
                           "ascending": "false"}, timeout=60)
        ceiling[off] = {"http": rr.status_code,
                        "n": len(rr.json()) if rr.ok else None,
                        "body": None if rr.ok else rr.text[:140]}
    except Exception as e:  # noqa: BLE001
        ceiling[off] = {"error": repr(e)[:140]}
    print(f"    offset={off:>6} {ceiling[off]}", flush=True)
rec("gamma_offset_ceiling", ceiling=ceiling, note="where Gamma stops")

print("\n== B2. do Gamma date filters actually filter? ==")
base = S.get(f"{GAMMA}/markets", params={"limit": 20, "order": "createdAt",
                                         "ascending": "false"}, timeout=60).json()
base_ids = [x.get("id") for x in base]
for name, params in [
    ("end_date_min=2024-01-01&end_date_max=2024-02-01",
     {"limit": 20, "order": "createdAt", "ascending": "false",
      "end_date_min": "2024-01-01T00:00:00Z", "end_date_max": "2024-02-01T00:00:00Z"}),
    ("start_date_min=2024-01-01",
     {"limit": 20, "order": "createdAt", "ascending": "false",
      "start_date_min": "2024-01-01T00:00:00Z"}),
    ("id_min=100000", {"limit": 20, "order": "id", "ascending": "true",
                       "id_min": 100000}),
]:
    try:
        rr = S.get(f"{GAMMA}/markets", params=params, timeout=60).json()
        ids = [x.get("id") for x in rr]
        ends = [str(x.get("endDate"))[:10] for x in rr]
        rec(f"gamma_datefilter[{name}]", n=len(rr),
            identical_to_unfiltered=(ids == base_ids),
            end_dates=ends[:6], ids=ids[:6],
            note=("IGNORED" if ids == base_ids
                  else f"filters -> ends {min(ends)}..{max(ends)}"))
    except Exception as e:  # noqa: BLE001
        rec(f"gamma_datefilter[{name}]", error=repr(e)[:140], note="error")

OUT.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {OUT}")
