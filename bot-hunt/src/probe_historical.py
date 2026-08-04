"""Can the sharp reference price be BACKFILLED, or only recorded forward?

This is the question that decides whether Steps 4-6 can run on real history in
this session or must wait weeks for the recorder to accrue.

Pinnacle's guest API is live-only — verified: no historical endpoint exists on
it. Two backfill routes surfaced from the repo corpus and both are checked here
by fetching:

  1. sportsbookreview.com historical odds — named in a plan document inside
     `Dankerbadge/betting-bot`: "scrapes 4 years of historical sharp-bookmaker
     odds (sportsbookreview.com), matches each game to a Jon-Becker Kalshi
     market".
  2. `Jon-Becker/prediction-market-analysis` — the Kalshi side of that same
     pairing, and a repo already in the signal-github corpus.

Plus the two archive services that are the only route to a real L2 backtest.

Nothing here is trusted from a link. Every row is a fetch with a byte count.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parent.parent / "reports"
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/126.0 Safari/537.36"),
      "Accept": "*/*"}

TARGETS = [
    ("sbr_root", "https://www.sportsbookreview.com/"),
    ("sbr_odds_mlb", "https://www.sportsbookreview.com/betting-odds/mlb-baseball/"),
    ("sbr_api_gql", "https://sportsbookreview.com/ms-odds-v2/odds-v2-service"),
    ("sbr_consensus", "https://www.sportsbookreview.com/betting-odds/mlb-baseball/consensus/"),

    ("oddsportal", "https://www.oddsportal.com/"),
    ("oddsshark_mlb", "https://www.oddsshark.com/mlb/odds"),
    ("covers_mlb", "https://www.covers.com/sports/mlb/matchups"),
    ("aussportsbetting", "https://www.aussportsbetting.com/historical_data/"),

    # Kalshi-side historical datasets
    ("jonbecker_repo", "https://api.github.com/repos/Jon-Becker/prediction-market-analysis"),
    ("kalshi_trades_api", "https://api.elections.kalshi.com/trade-api/v2/markets/trades?limit=1"),

    # order-book archives
    ("pmxt_index", "https://archive.pmxt.dev/"),
    ("pmxt_r2v2_list", "https://r2v2.pmxt.dev/?list-type=2&max-keys=5"),

    # sharp exchange with a public historical route
    ("betfair_hist", "https://historicdata.betfair.com/"),
    ("betfair_api_root", "https://api.betfair.com/"),
]


def probe(key, url):
    rec = {"key": key, "url": url}
    try:
        r = requests.get(url, headers=UA, timeout=45)
    except requests.RequestException as exc:
        rec.update(status=None, error=f"{type(exc).__name__}: {exc}"[:160])
        return rec
    b = r.content or b""
    rec.update(status=r.status_code, bytes=len(b),
               sha=hashlib.sha256(b).hexdigest()[:12],
               ctype=r.headers.get("Content-Type", "")[:40])
    txt = b.decode("utf-8", "replace")
    if "json" in rec["ctype"]:
        try:
            d = r.json()
            rec["json_keys"] = list(d)[:10] if isinstance(d, dict) else f"list[{len(d)}]"
        except ValueError:
            pass
    else:
        rec["text_chars"] = len(re.sub(r"<[^>]+>", " ", txt))
        m = re.search(r"<title[^>]*>(.*?)</title>", txt, re.S | re.I)
        rec["title"] = (m.group(1).strip()[:80] if m else "")
        # does the page actually carry PRICES, or just chrome?
        rec["n_american_odds"] = len(re.findall(r"[+-]\d{3,4}\b", txt))
        rec["mentions_download"] = bool(re.search(r"\.csv|\.xlsx|download", txt, re.I))
    return rec


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    out = []
    for k, u in TARGETS:
        rec = probe(k, u)
        out.append(rec)
        flag = "OK " if rec.get("status") == 200 else "!! "
        extra = ""
        if rec.get("json_keys"):
            extra = f" keys={rec['json_keys']}"
        elif rec.get("text_chars") is not None:
            extra = (f" text={rec['text_chars']:>7} odds#={rec['n_american_odds']:>5}"
                     f" dl={rec['mentions_download']} {rec.get('title','')!r}")
        print(f"{flag}{k:22} {str(rec.get('status')):>5} "
              f"{rec.get('bytes', 0):>9}B{extra}")
        if rec.get("error"):
            print(f"      {rec['error']}")
    (OUT / "historical_probe.json").write_text(json.dumps(out, indent=1),
                                               encoding="utf-8")
    print(f"\n{sum(1 for r in out if r.get('status') == 200)}/{len(out)} at 200"
          f" -> reports/historical_probe.json")


if __name__ == "__main__":
    main()
