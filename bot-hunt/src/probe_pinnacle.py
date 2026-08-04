"""Does Pinnacle's guest API actually serve LIVE ODDS free, or only a sports list?

Why this matters more than anything else probed today. Two independent sources
in the extractor corpora describe the same mechanism, and it is the only
mechanism with a publicly reconciled live P&L behind it:

  * youtube-signal `ANGZMUercB4`: `edge = fair probability - price - cost`,
    where fair probability is the **de-vigged sharp sportsbook consensus**, not
    your own model.
  * social-signal r/algotrading `1u17e2v`: a public-wallet bot that de-vigged
    sharp book odds and quoted Polymarket esports passively. +$8,293 arbitrage,
    3,858 fills, $96k volume — and it needed **no esports domain data at all**.

Both need one input: a free, sharp reference price. `market-selection`'s
dimension D asks "is there free data about the underlying thing?" and would
score esports ZERO — its data layer really has collapsed (Oracle's Elixir 404,
HLTV 403, vlr 402, pandascore 403, all re-verified today). That framing cannot
see this mechanism at all, because the input is another market's price.

So: is the reference price free? Verified by fetching, endpoint by endpoint.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parent.parent / "reports"
BASE = "https://guest.api.arcadia.pinnacle.com/0.1"
UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept": "application/json",
    "Referer": "https://www.pinnacle.com/",
    "Origin": "https://www.pinnacle.com",
    # Pinnacle's public web client sends this; recorded here rather than in a
    # comment because without it several endpoints 401.
    "X-API-Key": "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R",
}


def g(path: str, params=None):
    try:
        r = requests.get(BASE + path, params=params, headers=UA, timeout=30)
    except requests.RequestException as exc:
        return {"path": path, "error": f"{type(exc).__name__}: {exc}"}
    rec = {"path": path, "status": r.status_code, "bytes": len(r.content)}
    if r.status_code == 200:
        try:
            rec["json"] = r.json()
        except ValueError:
            rec["text"] = r.text[:400]
    else:
        rec["text"] = r.text[:300]
    return rec


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}

    sports = g("/sports")
    report["sports"] = {k: v for k, v in sports.items() if k != "json"}
    if "json" not in sports:
        print("sports endpoint failed:", sports)
        (OUT / "pinnacle_probe.json").write_text(json.dumps(report, indent=1),
                                                 encoding="utf-8")
        return

    js = sports["json"]
    print(f"/sports -> {len(js)} sports")
    # EXACT names, not substrings. A substring match on "tennis" resolves to
    # "Padel Tennis" (id 37, 6 matchups) instead of "Tennis" (id 33, 188) and
    # silently reports the wrong sport as thin. Caught by the matchup count
    # disagreeing with the /sports listing.
    WANT = {"E Sports": "esports", "Tennis": "tennis", "Soccer": "soccer",
            "Baseball": "baseball", "Basketball": "basketball",
            "Football": "amfootball", "Hockey": "hockey", "Golf": "golf",
            "Mixed Martial Arts": "mma", "Formula 1": "f1"}
    wanted = {}
    for s in js:
        print(f"   id={s.get('id'):<6} {s.get('name'):<28} "
              f"matchups={s.get('matchupCount')} featured={s.get('featureOrder')}")
        if s.get("name") in WANT and (s.get("matchupCount") or 0) > 0:
            wanted[WANT[s["name"]]] = s.get("id")
    report["sports_list"] = [{"id": s.get("id"), "name": s.get("name"),
                              "matchupCount": s.get("matchupCount")} for s in js]

    print(f"\nresolved sport ids: {wanted}")
    for tag, sid in wanted.items():
        for path in (f"/sports/{sid}/matchups", f"/sports/{sid}/markets/straight"):
            rec = g(path)
            n = None
            if isinstance(rec.get("json"), list):
                n = len(rec["json"])
            print(f"  {tag:11} {path:36} {rec.get('status')} "
                  f"{rec.get('bytes', 0):>9} B  items={n}")
            key = f"{tag}:{path}"
            report[key] = {k: v for k, v in rec.items() if k != "json"}
            report[key]["n_items"] = n
            if n:
                report[key]["sample"] = rec["json"][:2]
                # Does a straight-market record carry actual PRICES?
                if "markets/straight" in path:
                    pr = [x for x in rec["json"]
                          if isinstance(x, dict) and x.get("prices")]
                    report[key]["with_prices"] = len(pr)
                    print(f"                 -> {len(pr)} records carry `prices`")
                    if pr:
                        print("                 -> sample:",
                              json.dumps(pr[0], default=str)[:320])

    (OUT / "pinnacle_probe.json").write_text(
        json.dumps(report, indent=1, default=str), encoding="utf-8")
    print("\nwrote reports/pinnacle_probe.json")


if __name__ == "__main__":
    main()
