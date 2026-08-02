"""Dimension B and C for Polymarket — real executable depth from the CLOB.

The gamma `/events` crawl gives `bestBid`/`bestAsk` but does not say which
outcome they describe, and carries no size at all. So depth has to come from
the CLOB `/book` endpoint, per token. That endpoint is public and needs no key.

Sampling: the busiest markets inside the busiest tags, i.e. each family's BEST
case, the same convention used for the Kalshi recorder so the two venues are
compared like for like. A family whose busiest markets are thin is safely
killed; a family that looks good here has only been shown to have good
headline markets.

Read-only, paced, public endpoints.
"""
import json
import os
import sys
import time
from collections import defaultdict

import requests

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
CLOB = "https://clob.polymarket.com"
UA = {"User-Agent": "market-selection-research/1.0"}
PACE = 0.25
TOP_TAGS = 26
PER_TAG = 8


def fnum(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def book(token, tries=3):
    for i in range(tries):
        try:
            r = requests.get(CLOB + "/book", {"token_id": token},
                             headers=UA, timeout=30)
        except requests.RequestException:
            time.sleep(1.0 * (i + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2.0 * (i + 1))
            continue
        time.sleep(PACE)
        if r.status_code != 200:
            return None
        return r.json() or {}
    return None


def main():
    # rank tags by 24h volume, then take the busiest live markets in each
    tag_vol = defaultdict(float)
    per_tag = defaultdict(list)
    with open(os.path.join(DATA, "poly_events.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            e = json.loads(line)
            tags = [t.get("label") for t in (e.get("tags") or []) if t.get("label")]
            for m in (e.get("markets") or []):
                if not m.get("acceptingOrders"):
                    continue
                try:
                    toks = json.loads(m.get("clobTokenIds") or "[]")
                    outs = json.loads(m.get("outcomes") or "[]")
                except json.JSONDecodeError:
                    continue
                if len(toks) < 1:
                    continue
                v = fnum(m.get("volume24hr"))
                for tg in tags:
                    tag_vol[tg] += v
                    per_tag[tg].append((v, toks[0], outs[0] if outs else "",
                                        m.get("slug"),
                                        m.get("orderPriceMinTickSize")))

    tags = [t for t, _ in sorted(tag_vol.items(), key=lambda x: -x[1])[:TOP_TAGS]]
    print(f"probing CLOB /book on {TOP_TAGS} tags x up to {PER_TAG} markets\n")
    # NO global dedup across tags. Polymarket tags are overlapping views, not a
    # partition -- a market tagged `Iran` is usually also `Geopolitics` and
    # `World`. A first version deduped by token, so whichever tag was probed
    # first claimed the market and later tags fell to n=1 or 2, which is not a
    # measurement. Books are cached per token so the re-probe costs nothing.
    rows = []
    cache = {}
    for tg in tags:
        for v, tok, out, slug, tick in sorted(per_tag[tg], reverse=True)[:PER_TAG]:
            if tok in cache:
                d = cache[tok]
            else:
                d = book(tok)
                cache[tok] = d
            if d is None:
                rows.append({"tag": tg, "slug": slug, "http_fail": True})
                continue
            bids = d.get("bids") or []
            asks = d.get("asks") or []
            bb = max((float(x["price"]) for x in bids), default=None)
            ba = min((float(x["price"]) for x in asks), default=None)
            bsz = sum(float(x["size"]) for x in bids
                      if bb is not None and float(x["price"]) == bb)
            asz = sum(float(x["size"]) for x in asks
                      if ba is not None and float(x["price"]) == ba)
            # depth within 5c of the touch, both sides
            d5 = sum(float(x["size"]) for x in bids
                     if bb is not None and float(x["price"]) >= bb - 0.05)
            d5 += sum(float(x["size"]) for x in asks
                      if ba is not None and float(x["price"]) <= ba + 0.05)
            rows.append({
                "tag": tg, "slug": slug, "outcome": out, "vol24": v,
                "tick": tick,
                "bid_c": None if bb is None else round(bb * 100, 2),
                "ask_c": None if ba is None else round(ba * 100, 2),
                "spread_c": None if (bb is None or ba is None) else round((ba - bb) * 100, 2),
                "bid_sz": round(bsz, 1), "ask_sz": round(asz, 1),
                "depth_5c": round(d5, 1),
                "n_bid_levels": len(bids), "n_ask_levels": len(asks),
                "two_sided": bb is not None and ba is not None,
            })
    with open(os.path.join(REP, "poly_depth.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)

    agg = defaultdict(lambda: {"n": 0, "two": 0, "sp": [], "bsz": [], "d5": [],
                               "lv": []})
    for r in rows:
        if r.get("http_fail"):
            continue
        a = agg[r["tag"]]
        a["n"] += 1
        if r["two_sided"]:
            a["two"] += 1
            a["sp"].append(r["spread_c"])
            a["bsz"].append(r["bid_sz"])
            a["d5"].append(r["depth_5c"])
            a["lv"].append(r["n_bid_levels"] + r["n_ask_levels"])

    def q(xs, p):
        if not xs:
            return None
        xs = sorted(xs)
        return round(xs[min(int(len(xs) * p), len(xs) - 1)], 2)

    print(f"{'tag':26s} {'n':>4s} {'2sid%':>6s} {'sprMed':>7s} {'sprP90':>7s} "
          f"{'bidSz':>9s} {'depth5c':>10s} {'levels':>7s}")
    out = []
    for tg, a in sorted(agg.items(), key=lambda x: -x[1]["n"]):
        row = {"tag": tg, "n_sampled": a["n"],
               "pct_two_sided": round(100 * a["two"] / a["n"], 1) if a["n"] else 0,
               "spread_med_c": q(a["sp"], .5), "spread_p90_c": q(a["sp"], .9),
               "bid_sz_med": q(a["bsz"], .5), "depth_5c_med": q(a["d5"], .5),
               "levels_med": q(a["lv"], .5)}
        out.append(row)
        print(f"{tg[:26]:26s} {row['n_sampled']:4d} {row['pct_two_sided']:6.1f} "
              f"{str(row['spread_med_c']):>7s} {str(row['spread_p90_c']):>7s} "
              f"{str(row['bid_sz_med']):>9s} {str(row['depth_5c_med']):>10s} "
              f"{str(row['levels_med']):>7s}")
    with open(os.path.join(REP, "poly_depth_by_tag.json"), "w",
              encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(f"\n{len(rows)} markets probed; wrote reports/poly_depth*.json")


if __name__ == "__main__":
    main()
