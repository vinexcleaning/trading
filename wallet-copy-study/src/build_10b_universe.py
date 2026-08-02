"""Phase 1a: resolved-market universe from the CLOB, with settlement.

Gamma is unusable as an enumerator: its offset ceiling is ~2400 ("use
/markets/keyset for deeper pagination") and most of its filters are silently
ignored. The CLOB's cursor paging returned 55,343 markets in 60 pages / 16s and
had not terminated, and its `tokens[].winner` flag is settlement reported by the
venue itself rather than inferred from a price string.

Output: one row per market with both outcome token ids and the winning token,
plus flags for subgraph coverage and fee regime. Markets that are closed but
carry no winner are KEPT and flagged -- dropping them silently is how
survivorship bias gets in.
"""
import json
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "markets_clob.jsonl"
STATS = ROOT / "data" / "markets_clob_stats.json"
S = requests.Session()
S.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})
CLOB = "https://clob.polymarket.com"

SUBGRAPH_START = 1669060209      # 2022-11-21, oldest fill
SUBGRAPH_END = 1777374040        # 2026-04-28, newest fill
FEE_START = 1767830400           # 2026-01-08, bisected in probe_03


def parse_iso(s):
    if not s:
        return None
    for f in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return int(time.mktime(time.strptime(s[:19], f[:len(f)].replace("%z", ""))))
        except Exception:  # noqa: BLE001
            continue
    try:
        return int(time.mktime(time.strptime(s[:10], "%Y-%m-%d")))
    except Exception:  # noqa: BLE001
        return None


def fetch(cursor, retries=5):
    for a in range(retries):
        try:
            r = S.get(f"{CLOB}/markets",
                      params={"next_cursor": cursor} if cursor else {}, timeout=90)
            if r.ok:
                return r.json()
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 * (a + 1))
                continue
            return None
        except Exception:  # noqa: BLE001
            time.sleep(2 * (a + 1))
    return None


print("== enumerating CLOB markets ==")
cur, pages, seen = "", 0, set()
stats = Counter()
t0 = time.time()
kept = 0

with OUT.open("w", encoding="utf-8") as fh:
    while True:
        j = fetch(cur)
        if j is None:
            print(f"  request failed at page {pages}, cursor={cur!r}", flush=True)
            break
        data = j.get("data") or []
        if not data:
            stats["stop_empty_page"] += 1
            break
        for m in data:
            cid = m.get("condition_id")
            if not cid or cid in seen:
                stats["dup_or_no_condition"] += 1
                continue
            seen.add(cid)
            toks = m.get("tokens") or []
            if len(toks) != 2:
                stats[f"tokens_{len(toks)}"] += 1
                continue
            stats["binary"] += 1
            winners = [t for t in toks if t.get("winner")]
            closed = bool(m.get("closed"))
            if closed and len(winners) == 1:
                verdict = "clean"
            elif closed and not winners:
                verdict = "closed_no_winner"
            elif closed and len(winners) > 1:
                verdict = "closed_multi_winner"
            elif not closed and winners:
                verdict = "open_but_winner"
            else:
                verdict = "open"
            stats[f"settle_{verdict}"] += 1

            end_ts = parse_iso(m.get("end_date_iso"))
            row = {
                "condition_id": cid,
                "question_id": m.get("question_id"),
                "slug": m.get("market_slug"),
                "question": (m.get("question") or "")[:200],
                "tokens": [t.get("token_id") for t in toks],
                "outcomes": [t.get("outcome") for t in toks],
                "winner_token": winners[0].get("token_id") if len(winners) == 1 else None,
                "winner_outcome": winners[0].get("outcome") if len(winners) == 1 else None,
                "settle_verdict": verdict,
                "closed": closed,
                "active": m.get("active"),
                "archived": m.get("archived"),
                "enable_order_book": m.get("enable_order_book"),
                "neg_risk": m.get("neg_risk"),
                "end_date_iso": m.get("end_date_iso"),
                "end_ts": end_ts,
                "game_start_time": m.get("game_start_time"),
                "min_tick": m.get("minimum_tick_size"),
                "min_order": m.get("minimum_order_size"),
                "tags": m.get("tags"),
                "maker_base_fee": m.get("maker_base_fee"),
                "taker_base_fee": m.get("taker_base_fee"),
            }
            if end_ts:
                row["in_subgraph_window"] = SUBGRAPH_START <= end_ts <= SUBGRAPH_END
                row["fee_regime"] = "post" if end_ts >= FEE_START else "pre"
            else:
                row["in_subgraph_window"] = None
                row["fee_regime"] = None
            fh.write(json.dumps(row) + "\n")
            kept += 1

        nxt = j.get("next_cursor") or ""
        pages += 1
        if pages % 50 == 0:
            print(f"  page {pages:>5}  markets {len(seen):>7}  kept {kept:>7}  "
                  f"{time.time()-t0:>6.0f}s", flush=True)
        if not nxt or nxt == "LTE=" or nxt == cur:
            stats["stop_terminal_cursor"] += 1
            break
        cur = nxt

el = time.time() - t0
print(f"\n  pages={pages}  distinct markets={len(seen)}  kept={kept}  {el:.0f}s")

# ------------------------------------------------------------- composition
rows = [json.loads(l) for l in OUT.open(encoding="utf-8")]
usable = [r for r in rows
          if r["settle_verdict"] == "clean" and r.get("in_subgraph_window")]

by_year = Counter()
for r in usable:
    if r["end_ts"]:
        by_year[time.strftime("%Y", time.gmtime(r["end_ts"]))] += 1

summary = {
    "pages": pages, "seconds": round(el),
    "n_markets": len(rows),
    "counters": dict(stats),
    "n_clean_settlement": sum(1 for r in rows if r["settle_verdict"] == "clean"),
    "n_in_subgraph_window": sum(1 for r in rows if r.get("in_subgraph_window")),
    "n_usable": len(usable),
    "usable_by_regime": dict(Counter(r["fee_regime"] for r in usable)),
    "usable_by_year": dict(sorted(by_year.items())),
    "usable_neg_risk_share": round(
        sum(1 for r in usable if r.get("neg_risk")) / len(usable), 4) if usable else None,
    "usable_orderbook_share": round(
        sum(1 for r in usable if r.get("enable_order_book")) / len(usable), 4) if usable else None,
    "end_date_range_all": [
        min((r["end_date_iso"] for r in rows if r.get("end_date_iso")), default=None),
        max((r["end_date_iso"] for r in rows if r.get("end_date_iso")), default=None)],
    "end_date_range_usable": [
        min((r["end_date_iso"] for r in usable if r.get("end_date_iso")), default=None),
        max((r["end_date_iso"] for r in usable if r.get("end_date_iso")), default=None)],
}
STATS.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
print(f"\nwrote {OUT} and {STATS}")
