"""Is Polymarket esports actually bookless, or is the recorder's probe wrong?

Dimension A is the kill switch and this is the family the extractor corpus
pointed hardest at — the only strategy anywhere in the corpora with a public
wallet and a four-line reconciled P&L (+$8,293 arb / -$3,184 directional /
-$134 cancellations / +$4,973 net, 3,858 fills, $96k volume, r/algotrading
`1u17e2v`). Recorder cycle 1 read **11 tokens with any quote out of 95, and 0%
two-sided**. Before that kills the family it has to survive three objections:

  1. wrong tag_slug, so the sample is not esports at all
  2. wrong endpoint, so a real book reads as empty (this exact failure mode
     already cost two sessions here — Kalshi's `orderbook_fp` key)
  3. time of day: it was 21:30 UTC, and LoL/CS2 are EU/Asia daytime sports

Objection 3 cannot be settled in one pass; the recorder settles it over a day.
This file settles 1 and 2, and characterises what IS there.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import venues as V  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "reports"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}

    # --- 1. does the tag exist, and what are the real slugs? ---
    r = V.p_gamma("/tags", {"limit": 500})
    tags = []
    if r is not None and r.status_code == 200:
        try:
            tags = r.json() or []
        except ValueError:
            tags = []
    hits = [t for t in tags
            if any(w in (t.get("label", "") + t.get("slug", "")).lower()
                   for w in ("esport", "csgo", "cs2", "league-of-legends", "lol",
                             "dota", "valorant", "counter"))]
    print(f"/tags -> {len(tags)} tags; esports-ish: "
          f"{[(t.get('slug'), t.get('label')) for t in hits][:15]}")
    report["tag_matches"] = [(t.get("id"), t.get("slug"), t.get("label"))
                             for t in hits]

    # --- 2. events under each candidate slug, with real book probes ---
    for slug in ["esports", "csgo", "cs2", "league-of-legends", "dota-2",
                 "valorant", "games"]:
        r = V.p_gamma("/events", {"tag_slug": slug, "closed": "false",
                                  "limit": 100, "order": "volume24hr",
                                  "ascending": "false"})
        if r is None or r.status_code != 200:
            print(f"  slug={slug:20} http={None if r is None else r.status_code}")
            report[f"slug:{slug}"] = {"http": None if r is None else r.status_code}
            continue
        try:
            events = r.json() or []
        except ValueError:
            events = []
        rows, states = [], Counter()
        for e in events:
            for m in (e.get("markets") or []):
                states["market"] += 1
                if not m.get("acceptingOrders"):
                    states["not_accepting"] += 1
                    continue
                try:
                    toks = json.loads(m.get("clobTokenIds") or "[]")
                except (json.JSONDecodeError, TypeError):
                    states["bad_tokens"] += 1
                    continue
                if not toks:
                    states["no_tokens"] += 1
                    continue
                bk = V.p_book(toks[0])
                if bk is None:
                    states["book_http_fail"] += 1
                    continue
                bid, ask, bs, asz, nb, na = V.p_touch(bk)
                if bid is None and ask is None:
                    states["empty_book"] += 1
                elif bid is None or ask is None:
                    states["one_sided"] += 1
                else:
                    states["two_sided"] += 1
                rows.append({"slug": m.get("slug"), "q": e.get("title", "")[:70],
                             "vol24": V.fnum(m.get("volume24hr"), 0.0),
                             "liq": V.fnum(m.get("liquidity"), 0.0),
                             "bid_c": bid, "ask_c": ask, "bid_sz": bs,
                             "ask_sz": asz, "levels": (nb, na),
                             "end": m.get("endDate")})
                if len(rows) >= 60:
                    break
            if len(rows) >= 60:
                break
        two = [x for x in rows if x["bid_c"] is not None and x["ask_c"] is not None]
        print(f"  slug={slug:20} events={len(events):>3} probed={len(rows):>3} "
              f"{dict(states)}")
        for x in sorted(two, key=lambda z: -z["vol24"])[:5]:
            print(f"      2S vol24=${x['vol24']:>10,.0f} "
                  f"bid={x['bid_c']:.1f} ask={x['ask_c']:.1f} "
                  f"spread={x['ask_c']-x['bid_c']:.1f}c "
                  f"sz={x['bid_sz']:.0f}/{x['ask_sz']:.0f}  {x['q'][:52]}")
        report[f"slug:{slug}"] = {"http": 200, "events": len(events),
                                  "states": dict(states), "rows": rows}

    (OUT / "poly_esports_probe.json").write_text(
        json.dumps(report, indent=1, default=str), encoding="utf-8")
    print("\nwrote reports/poly_esports_probe.json")


if __name__ == "__main__":
    main()
