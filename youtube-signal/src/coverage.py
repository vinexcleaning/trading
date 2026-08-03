"""What have we looked at, and what is still unread?

This is the steering wheel. It answers two questions:

  "Have you covered Polymarket yet, or only Kalshi?"
  "What would you find if I told you to look at X?"

Coverage is measured per SUBJECT (a keyword group), not per query, because the
question a person actually asks is "do you know about Polymarket", not "did you
run query #7".
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db_phase2  # noqa: E402
import queries as Q  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Subjects, not queries. Edit this to change what "covered" means.
SUBJECTS = {
    "Kalshi": ["kalshi"],
    "Polymarket": ["polymarket", "poly market"],
    "Trading bots / automation": ["trading bot", "trading agent", "automate", "bot"],
    "Market making / spreads": ["market mak", "market-mak", "spread", "liquidity provid"],
    "Copy trading / wallets": ["copy trad", "copytrad", "wallet"],
    "Backtesting / validation": ["backtest", "back test", "walk forward", "overfit"],
    "APIs / data plumbing": ["api", "websocket", "clob", "order book", "orderbook"],
    "Fees / costs / slippage": ["fee", "slippage", "taker", "maker", "vig"],
    "Statistics / sample size": ["sample size", "confidence interval", "win rate",
                                 "brier", "kelly"],
    "Sports betting angle": ["sports bet", "closing line", "prizepicks", "oddsjam"],
}


def main():
    con = db_phase2.connect()

    print("=" * 74)
    print("WHAT IS BEING SEARCHED FOR")
    print("=" * 74)
    fams = Q.TOPICS["prediction_markets"]
    for fam in ("F1", "F2", "F2B"):
        terms = fams.get(fam, [])
        label = {"F1": "beginner phrasing", "F2": "insider vocabulary",
                 "F2B": "insider vocabulary, batch 2"}[fam]
        print(f"\n{fam} -- {label} ({len(terms)} terms)")
        for t in terms:
            n = con.execute(
                "SELECT COUNT(DISTINCT video_id) c FROM retrieval_hits WHERE query=?",
                (t,)).fetchone()["c"]
            print(f"   {n:>4} videos   {t}")
    print(f"\nF3 (date-filtered) was CUT. F4 (search by discovered tool name) "
          f"is not built yet.")

    print()
    print("=" * 74)
    print("SUBJECT COVERAGE  --  of the videos we actually have")
    print("=" * 74)
    vids = con.execute(
        """SELECT v.video_id, v.title, v.gate_status, s.video_id IS NOT NULL AS was_read
           FROM videos v LEFT JOIN scores s ON s.video_id=v.video_id
           WHERE v.gate_status IN ('PASS','STALE_G2')"""
    ).fetchall()
    ranked = {x["video_id"]: x["proxy_score"] for x in json.loads(
        (ROOT / "reports" / "substance_ranking.json").read_text(encoding="utf-8"))}

    print(f"{'subject':<30}{'have':>6}{'read':>6}{'top-ranked unread':>20}")
    print("-" * 74)
    for subj, keys in SUBJECTS.items():
        pat = re.compile("|".join(re.escape(k) for k in keys), re.I)
        hits = [v for v in vids if v["title"] and pat.search(v["title"])]
        read = sum(1 for v in hits if v["was_read"])
        unread = sorted((v for v in hits if not v["was_read"]),
                        key=lambda v: -ranked.get(v["video_id"], 0))
        best = unread[0]["title"][:34] if unread else "-- all read --"
        print(f"{subj:<30}{len(hits):>6}{read:>6}   {best}")

    print()
    print("=" * 74)
    print("READING PROGRESS")
    print("=" * 74)
    tot = len(vids)
    read = sum(1 for v in vids if v["was_read"])
    print(f"  in the pool (passed gates, transcript cached) : {tot}")
    print(f"  read in full by an LLM                         : {read}")
    print(f"  ranked by keyword proxy (free, no LLM)         : {len(ranked)}")
    print(f"\n  Reading is the only expensive step. Ranking all {len(ranked)} costs")
    print(f"  nothing; reading is done top-down and stops whenever you say so.")

    print()
    print("=" * 74)
    print("HOW TO STEER IT")
    print("=" * 74)
    print("  Add search terms   -> edit SUBJECTS/queries in src/queries.py, or just")
    print("                        say 'also search for X' and they get added.")
    print("  Change what counts -> src/gates.py holds the topic boundary.")
    print("  Change the ranking -> src/rank_substance.py holds the weights.")
    print("  Read more videos   -> src/dump_transcripts.py --top N")
    con.close()


if __name__ == "__main__":
    main()
