"""Rank all passing videos by substance PROXIES, using cached transcripts only.

No LLM, no API, no network, no cost.

This is not the S score. The S score needs a model to read the video and cite
evidence. This is a cheap stand-in whose only job is to decide WHAT TO READ FIRST,
so that a limited amount of real reading is spent on the most promising material
rather than on a sample designed to be representative.

The signals are the things that are hard to fake in an auto-generated transcript:

  concrete   distinct URLs, github links, and named tools actually spoken
  cost       does it name the cost side at all -- fees, spread, slippage, gas
  numeric    density of real numbers (%, $, counts) per 1000 words
  evidence   backtest-vs-live language, sample sizes, "out of N trades"
  mechanism  causal language -- why it works, who is on the other side
  marketing  PENALTY: link-in-description, my course, sign up, limited time

Weights are deliberately crude. This decides reading order, nothing else, and a
wrong order costs a little attention rather than a wrong conclusion.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db_phase2  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

URL = re.compile(r"(?:https?://|www\.)[^\s]+|\b[a-z0-9-]+\.(?:com|io|org|net|dev|ai|xyz|co)\b")
GITHUB = re.compile(r"github(?:\.com)?[/ ]", re.I)
NUM = re.compile(r"\b\d[\d,]*\.?\d*\s?(?:%|percent|dollars?|bucks|trades?|bets?|days?|k\b|usd)", re.I)
MONEY = re.compile(r"\$\s?\d[\d,]*")

COST = ["fee", "fees", "spread", "slippage", "commission", "gas fee", "taker",
        "maker", "rebate", "vig", "juice", "funding rate", "cost basis",
        "transaction cost", "bid ask", "bid-ask"]
EVID = ["backtest", "back test", "forward test", "paper trade", "paper trading",
        "live account", "real money", "out of sample", "sample size", "win rate",
        "sharpe", "drawdown", "expectancy", "track record", "over the last",
        "trades i", "n equals"]
MECH = ["the reason", "because the", "why this works", "the other side",
        "counterparty", "who is taking", "edge comes from", "inefficiency",
        "mispricing", "the mechanism", "arbitrage between", "this works because",
        "market maker", "adverse selection", "liquidity provider"]
MARKET = ["link in the description", "link in description", "my course",
          "my program", "join my", "sign up below", "limited time", "discount code",
          "promo code", "use my code", "dm me", "book a call", "free training",
          "spots left", "act now", "before it's too late", "referral link"]

TAG = re.compile(r"\[[^\]]*\]|\([^)]*\)")


def count_terms(text, terms):
    return sum(len(re.findall(r"(?<![a-z])" + re.escape(t) + r"s?(?![a-z])", text))
               for t in terms)


def score(text):
    low = TAG.sub(" ", text).lower()
    words = max(len(low.split()), 1)
    per1k = 1000.0 / words

    urls = {u.rstrip(".,)") for u in URL.findall(low)}
    gh = len(GITHUB.findall(low))
    nums = len(NUM.findall(low)) + len(MONEY.findall(low))
    cost = count_terms(low, COST)
    evid = count_terms(low, EVID)
    mech = count_terms(low, MECH)
    mkt = count_terms(low, MARKET)

    parts = {
        "concrete": min(len(urls) * 1.5 + gh * 3.0, 15.0),
        "cost": min(cost * 1.2, 12.0),
        "numeric": min(nums * per1k * 2.0, 10.0),
        "evidence": min(evid * 1.5, 12.0),
        "mechanism": min(mech * 2.0, 12.0),
        "marketing_penalty": -min(mkt * per1k * 6.0, 12.0),
    }
    return sum(parts.values()), parts, {
        "urls": sorted(urls)[:8], "n_urls": len(urls), "github_mentions": gh,
        "n_cost": cost, "n_evidence": evid, "n_mechanism": mech,
        "n_marketing": mkt, "words": words,
    }


def main():
    con = db_phase2.connect()
    rows = con.execute(
        """SELECT v.video_id, v.title, v.channel_name, v.view_count, v.duration_s,
                  t.snippets_json
           FROM videos v JOIN transcripts t ON t.video_id = v.video_id
           WHERE v.gate_status = 'PASS'"""
    ).fetchall()
    print(f"ranking {len(rows)} passing videos with cached transcripts\n")

    out = []
    for r in rows:
        text = " ".join(s["text"] for s in json.loads(r["snippets_json"]))
        total, parts, detail = score(text)
        out.append({
            "video_id": r["video_id"], "title": r["title"],
            "channel": r["channel_name"], "views": r["view_count"],
            "duration_s": r["duration_s"], "proxy_score": round(total, 2),
            "parts": {k: round(v, 2) for k, v in parts.items()}, **detail,
        })
    out.sort(key=lambda x: -x["proxy_score"])

    print(f"{'#':>3} {'score':>6} {'views':>9} {'min':>5}  {'urls':>4} {'cost':>4} "
          f"{'evid':>4} {'mech':>4} {'mkt':>4}  title")
    for i, x in enumerate(out[:30], 1):
        v = f"{x['views']:,}" if x["views"] is not None else "?"
        print(f"{i:>3} {x['proxy_score']:>6.1f} {v:>9} "
              f"{(x['duration_s'] or 0)/60:>5.0f}  {x['n_urls']:>4} {x['n_cost']:>4} "
              f"{x['n_evidence']:>4} {x['n_mechanism']:>4} {x['n_marketing']:>4}  "
              f"{(x['title'] or '')[:46]}")

    print(f"\n  score distribution: max {out[0]['proxy_score']:.1f}, "
          f"median {out[len(out)//2]['proxy_score']:.1f}, min {out[-1]['proxy_score']:.1f}")
    low = [x for x in out[:30] if (x["views"] or 0) < 5000]
    print(f"  of the top 30, {len(low)} have under 5,000 views")

    (ROOT / "reports" / "substance_ranking.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote reports/substance_ranking.json ({len(out)} videos ranked)")
    con.close()


if __name__ == "__main__":
    main()
