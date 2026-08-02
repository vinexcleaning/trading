"""Phase 1.7: pull Kalshi SETTLED market history for the crypto ladder series.

These are re-pullable on this machine (unlike the desktop's recorded books).
Establishes how far back the API allows, and whether the settled records carry
enough to do Tier A settlement replay: strike, result, and a settlement value.

Read-only, unauthenticated.
"""
import argparse
import json
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

import requests

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = {"User-Agent": "research-readonly/0.1"}
OUT = r"C:\Users\gianf\crypto\data\kalshi_settled"

SERIES = ["KXBTC", "KXBTCD", "KXETH", "KXETHD", "KXSOLD", "KXXRP", "KXXRPD",
          "KXDOGED", "BTC", "BTCD", "ETHD", "KXBTC15M", "KXETH15M",
          "KXSOL15M", "KXXRP15M"]


def get(path, **params):
    for attempt in range(8):
        try:
            r = requests.get(f"{BASE}{path}", params=params, headers=UA,
                             timeout=45)
        except Exception:
            time.sleep(1.5 * (attempt + 1))
            continue
        if r.status_code == 429:
            time.sleep(1.5 * (attempt + 1))
            continue
        if r.status_code >= 500:
            time.sleep(1.0 * (attempt + 1))
            continue
        if r.status_code >= 400:
            return None
        return r.json()
    return None


def pull_series(series, max_pages=400, limit=1000):
    """Page settled markets backwards as far as the API allows."""
    cursor = None
    rows = []
    pages = 0
    while pages < max_pages:
        p = {"series_ticker": series, "status": "settled", "limit": limit}
        if cursor:
            p["cursor"] = cursor
        j = get("/markets", **p)
        if not j:
            break
        got = j.get("markets", []) or []
        rows.extend(got)
        cursor = j.get("cursor")
        pages += 1
        if not cursor or not got:
            break
        time.sleep(0.12)
    return rows, pages


def summarise(series, rows):
    if not rows:
        return {"series": series, "n": 0}
    def ts(m):
        s = m.get("close_time") or ""
        return s
    times = sorted(t for t in (ts(m) for m in rows) if t)
    results = Counter(str(m.get("result")) for m in rows)
    has_sv = sum(1 for m in rows
                 if m.get("expiration_value") not in (None, "", "0"))
    # Ladder test. Integer-roundness is the WRONG metric: KXBTCD strikes are
    # 54599.99 (a $100 ladder offset by a cent) and XRP strikes are ~1.062, so
    # both score 0 on roundness while being perfectly regular ladders. The real
    # question is whether strikes within one event are evenly spaced (a fixed
    # ladder) or whether each event has a single unrounded strike (minted ATM
    # at the previous window's settlement).
    by_ev = defaultdict(list)
    for m in rows:
        fs = m.get("floor_strike")
        if fs is not None:
            by_ev[m.get("event_ticker")].append(float(fs))
    strikes_per_event = None
    spacing_regular = None
    modal_spacing = None
    if by_ev:
        sizes = [len(v) for v in by_ev.values()]
        strikes_per_event = round(sum(sizes) / len(sizes), 2)
        gaps = []
        for v in by_ev.values():
            v = sorted(v)
            gaps.extend(round(b - a, 6) for a, b in zip(v, v[1:]))
        if gaps:
            c = Counter(gaps)
            modal_spacing, modal_n = c.most_common(1)[0]
            spacing_regular = round(modal_n / len(gaps), 4)
    return {
        "series": series,
        "n": len(rows),
        "first_close": times[0] if times else None,
        "last_close": times[-1] if times else None,
        "results": dict(results.most_common(6)),
        "with_expiration_value": has_sv,
        "n_events": len({m.get("event_ticker") for m in rows}),
        "strikes_per_event": strikes_per_event,
        "modal_strike_spacing": modal_spacing,
        "spacing_regularity": spacing_regular,
        "strike_types": dict(Counter(str(m.get("strike_type"))
                                     for m in rows).most_common(5)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", nargs="*", default=SERIES)
    ap.add_argument("--max-pages", type=int, default=400)
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    manifest = []
    for s in args.series:
        t0 = time.time()
        rows, pages = pull_series(s, max_pages=args.max_pages)
        el = time.time() - t0
        summ = summarise(s, rows)
        summ["pages"] = pages
        summ["seconds"] = round(el, 1)
        manifest.append(summ)
        if rows:
            path = os.path.join(OUT, f"{s}.jsonl")
            with open(path, "w", encoding="utf-8") as f:
                for m in rows:
                    f.write(json.dumps(m, separators=(",", ":")) + "\n")
            summ["path"] = path
        print(f"{s:<12} n={summ['n']:>7} pages={pages:>4} "
              f"events={str(summ.get('n_events')):>6} "
              f"{str(summ.get('first_close'))[:16]} -> "
              f"{str(summ.get('last_close'))[:16]} "
              f"strikes/ev={str(summ.get('strikes_per_event')):>7} "
              f"spacing={str(summ.get('modal_strike_spacing')):>10} "
              f"reg={str(summ.get('spacing_regularity')):>7} "
              f"({el:.0f}s)")

    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump({"pulled_utc": datetime.now(timezone.utc).isoformat(),
                   "series": manifest}, f, indent=2, default=str)
    print("\n--- manifest ---")
    print(json.dumps(manifest, indent=2, default=str)[:3000])


if __name__ == "__main__":
    main()
