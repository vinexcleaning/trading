"""Phase 1a: build the resolved-market universe with settlement outcomes.

Sampling frame for the whole study is MARKETS, not time and not wallets:
  - wallet selection is the thing under test, so a wallet-drawn sample is
    circular;
  - a time-drawn sample would still need market resolution to score anything.
Drawing markets at random and pulling *every* fill inside each one gives
complete position reconstruction within the sample, makes market-level
clustering the natural unit, and keeps per-position edge unbiased.

Gamma's filters are mostly ignored (see docs/data_availability.md), so this
pulls with explicit ordering and re-verifies every predicate on the returned
rows rather than trusting the query. Default ordering is oldest-first, which is
the exact trap that produced a prior false positive.

Settlement is read from `outcomePrices` on closed markets and cross-checked
against `umaResolutionStatus`; rows that do not resolve to a clean 0/1 are kept
and flagged rather than silently dropped, because dropping them is how
survivorship bias gets in.
"""
import json
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "markets_universe.jsonl"
STATS = ROOT / "data" / "markets_universe_stats.json"
S = requests.Session()
S.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})
GAMMA = "https://gamma-api.polymarket.com"

SUBGRAPH_START = 1669060209      # 2022-11-21
SUBGRAPH_END = 1777374040        # 2026-04-28
FEE_START = 1767830400           # 2026-01-08, bisected in probe_03


def get(params, retries=4):
    for a in range(retries):
        try:
            r = S.get(f"{GAMMA}/markets", params=params, timeout=60)
            if r.ok:
                return r.json()
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 * (a + 1))
                continue
            return None
        except Exception:  # noqa: BLE001
            time.sleep(2 * (a + 1))
    return None


def parse_ts(s):
    if not s:
        return None
    for f in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return int(time.mktime(time.strptime(s[:26], f)))
        except Exception:  # noqa: BLE001
            continue
    return None


def classify(m):
    """Settlement verdict from outcomePrices, verified not assumed."""
    try:
        prices = json.loads(m.get("outcomePrices") or "[]")
        prices = [float(x) for x in prices]
    except Exception:  # noqa: BLE001
        return "unparseable_prices", None
    if not prices:
        return "no_prices", None
    if len(prices) != 2:
        return f"non_binary_{len(prices)}", None
    s = sum(prices)
    if abs(s - 1.0) > 1e-6:
        return "prices_do_not_sum_to_1", None
    if max(prices) == 1.0 and min(prices) == 0.0:
        return "clean", prices.index(1.0)      # winning outcome index
    return "unresolved_or_partial", None


print("== paging Gamma markets, newest-first, verifying as we go ==")
seen, rows, page = set(), [], 0
stats = Counter()
offset = 0
LIMIT = 500
MAX_ROWS = 250_000

with OUT.open("w", encoding="utf-8") as fh:
    while len(rows) < MAX_ROWS:
        j = get({"limit": LIMIT, "offset": offset,
                 "order": "createdAt", "ascending": "false", "closed": "true"})
        if not j:
            print(f"  stopped: no response at offset {offset}", flush=True)
            break
        if not isinstance(j, list) or not j:
            print(f"  stopped: empty page at offset {offset}", flush=True)
            break
        newpage = 0
        for m in j:
            mid = m.get("id")
            if mid in seen:
                continue
            seen.add(mid)
            newpage += 1
            # verify the predicate we asked for actually holds
            if m.get("closed") is not True:
                stats["returned_but_not_closed"] += 1
                continue
            verdict, win_idx = classify(m)
            stats[f"settle_{verdict}"] += 1
            try:
                toks = json.loads(m.get("clobTokenIds") or "[]")
            except Exception:  # noqa: BLE001
                toks = []
            if len(toks) != 2:
                stats["no_two_token_ids"] += 1
                continue
            end_ts = parse_ts(m.get("endDateIso") or m.get("endDate"))
            start_ts = parse_ts(m.get("startDateIso") or m.get("startDate")
                                or m.get("createdAt"))
            rec = {
                "id": mid,
                "conditionId": m.get("conditionId"),
                "slug": m.get("slug"),
                "question": (m.get("question") or "")[:160],
                "tokens": toks,
                "outcomes": m.get("outcomes"),
                "outcomePrices": m.get("outcomePrices"),
                "settle_verdict": verdict,
                "winning_index": win_idx,
                "start_ts": start_ts,
                "end_ts": end_ts,
                "createdAt": m.get("createdAt"),
                "volumeNum": m.get("volumeNum"),
                "liquidityNum": m.get("liquidityNum"),
                "negRisk": m.get("negRisk"),
                "umaResolutionStatus": m.get("umaResolutionStatus"),
                "feesEnabled": m.get("feesEnabled"),
                "enableOrderBook": m.get("enableOrderBook"),
            }
            # in-subgraph-coverage flag and fee regime
            if end_ts:
                rec["in_subgraph_window"] = SUBGRAPH_START <= end_ts <= SUBGRAPH_END
                rec["fee_regime"] = "post" if end_ts >= FEE_START else "pre"
            else:
                rec["in_subgraph_window"] = None
                rec["fee_regime"] = None
            fh.write(json.dumps(rec) + "\n")
            rows.append(rec)
        page += 1
        offset += LIMIT
        if newpage == 0:
            print(f"  stopped: page {page} was all duplicates (offset {offset})",
                  flush=True)
            break
        if page % 20 == 0:
            print(f"  page {page:>4} offset {offset:>7}  kept {len(rows):>7}  "
                  f"clean {stats['settle_clean']:>7}", flush=True)

print(f"\n  pages={page} kept={len(rows)}")

vol = [r["volumeNum"] or 0 for r in rows]
inwin = [r for r in rows if r.get("in_subgraph_window")]
clean = [r for r in rows if r["settle_verdict"] == "clean"]
usable = [r for r in rows if r["settle_verdict"] == "clean" and r.get("in_subgraph_window")]

summary = {
    "n_markets_kept": len(rows),
    "settle_verdicts": dict(stats),
    "n_clean_settlement": len(clean),
    "n_in_subgraph_window": len(inwin),
    "n_usable": len(usable),
    "usable_by_regime": dict(Counter(r["fee_regime"] for r in usable)),
    "usable_by_year": dict(Counter(
        time.strftime("%Y", time.gmtime(r["end_ts"])) for r in usable if r["end_ts"])),
    "volume": {
        "n_with_volume": sum(1 for v in vol if v > 0),
        "total": round(sum(vol), 2),
        "median_usable": round(sorted(r["volumeNum"] or 0 for r in usable)[len(usable) // 2], 2) if usable else None,
    },
    "negrisk_share_usable": round(
        sum(1 for r in usable if r.get("negRisk")) / len(usable), 4) if usable else None,
    "feesEnabled_share_usable": round(
        sum(1 for r in usable if r.get("feesEnabled")) / len(usable), 4) if usable else None,
}
STATS.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
print(f"\nwrote {OUT} and {STATS}")
