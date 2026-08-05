"""Two corpus questions the brief mandates, answered before writing more code.

STEP 4 — "does a usable backtester already exist?"
  The brief's premise ("you CANNOT properly backtest Kalshi, no L2 history")
  was REFUTED today by a sibling session: archive.pmxt.dev carries Kalshi full
  L2, and I confirmed esports is in it (498,434 rows and 74 tickers in one
  hour). So the real question changed: **has anyone implemented an order-book
  REPLAY and a queue-aware fill model for Kalshi?** That is the part that is
  hard and the part I would otherwise write from scratch.

STEP 6 — "has anyone already tested this and failed?"
  Specifically for ESPORTS on a prediction market, which is now shortlist #1.

Scans the cached whole-repo archives (zero repo source enters context) and the
social corpus. Follows github-signal's cost model: query the cache, never
recompute; ask a narrow question.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

GH = Path(r"C:\Users\vinig\trading\signal-github")
CACHE, GDB = GH / "cache", GH / "data" / "github.db"
SOCIAL = Path(r"C:\Users\vinig\trading\social-signal\data\social.db")
REP = Path(__file__).resolve().parent.parent / "reports"

# --- Step 4: order-book replay and queue-aware fills ---
L2 = {
    "replay": r"\breplay\b|book_replay|orderbook_replay|reconstruct.{0,20}book",
    "delta_apply": r"apply_delta|orderbook_delta|book_delta|snapshot.{0,20}delta",
    "queue_pos": r"queue_position|queue_ahead|queue_prio|position_in_queue|"
                 r"time_priority|price_time",
    "trade_through": r"trade[_ ]?through|traded[_ ]?through|through the level|"
                     r"crossed[_ ]the[_ ]level",
    "partial_fill": r"partial_fill|partial fill|fill_ratio|filled_qty",
    "latency_model": r"latency|round[_ ]trip[_ ]ms|simulated_delay|ack_delay",
    "pmxt": r"pmxt|r2kalshi|archive\.pmxt",
    "parquet_book": r"parquet.{0,40}(orderbook|book)|(orderbook|book).{0,40}parquet",
    "l2_words": r"\bL2\b|level[_ ]2|market[_ ]by[_ ]order|\bMBO\b|full depth",
}
# --- Step 6: esports on a prediction market ---
ES = {
    "esports_venue": r"(esport|csgo|cs2|counter[- ]strike|league of legends|"
                     r"\blol\b|dota|valorant).{0,120}(kalshi|polymarket)|"
                     r"(kalshi|polymarket).{0,120}(esport|csgo|cs2|dota|valorant)",
    "esports_odds": r"(esport|csgo|cs2|dota|valorant).{0,80}(odds|devig|pinnacle|"
                    r"bookmaker|sportsbook)",
}
TEXT_EXT = {".py", ".js", ".ts", ".go", ".rs", ".md", ".ipynb", ".json",
            ".yaml", ".yml", ".sql", ".java", ".rb", ".cs", ".cpp"}


def load(fn, br):
    for b in [br, "main", "master"]:
        if not b:
            continue
        u = f"https://codeload.github.com/{fn}/tar.gz/{b}"
        p = CACHE / f"{hashlib.sha1(u.encode()).hexdigest()[:20]}.arch.json"
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            except json.JSONDecodeError:
                continue
            if d.get("status") == 200 and d.get("files"):
                return d
    return None


def main() -> None:
    REP.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{GDB.as_posix()}?mode=ro", uri=True)
    repos = con.execute(
        "select full_name, default_branch, stars, s_adj, kind, venue_detected, "
        "submits_orders, has_backtest, trust_me_bro, pushed_at from repos"
    ).fetchall()
    con.close()

    rxL2 = {k: re.compile(v, re.I) for k, v in L2.items()}
    rxES = {k: re.compile(v, re.I | re.S) for k, v in ES.items()}
    prevalence = defaultdict(int)
    l2_hits, es_hits = [], []
    scanned = 0

    for fn, br, stars, s_adj, kind, ven, orders, bt, tmb, pushed in repos:
        arch = load(fn, br)
        if not arch:
            continue
        scanned += 1
        parts = []
        for path, text in arch["files"].items():
            if isinstance(text, str) and (
                    not Path(path).suffix
                    or Path(path).suffix.lower() in TEXT_EXT):
                parts.append(f"\n### {path}\n{text}")
        blob = "".join(parts)
        if not blob:
            continue
        found = {k: len(r.findall(blob)) for k, r in rxL2.items()
                 if r.search(blob)}
        for k in found:
            prevalence[k] += 1
        # A REAL Kalshi L2 replay needs: the venue, book mechanics, AND a fill
        # notion. Any one alone is a keyword, not an implementation.
        core = sum(1 for k in ("replay", "delta_apply", "queue_pos",
                               "trade_through") if k in found)
        if core >= 2 and ven in ("kalshi", "kalshi+polymarket"):
            lines = []
            cur = "?"
            for ln in blob.splitlines():
                if ln.startswith("### "):
                    cur = ln[4:]
                    continue
                for k in ("queue_pos", "trade_through", "delta_apply", "replay"):
                    if k in found and rxL2[k].search(ln):
                        lines.append(f"{cur}: {ln.strip()[:140]}")
                        break
                if len(lines) >= 14:
                    break
            l2_hits.append({"repo": fn, "stars": stars, "s_adj": s_adj,
                            "kind": kind, "venue": ven, "orders": bool(orders),
                            "backtest": bool(bt), "tmb": bool(tmb),
                            "pushed": pushed, "signals": found, "lines": lines})
        esf = {k: len(r.findall(blob)) for k, r in rxES.items() if r.search(blob)}
        if esf:
            es_hits.append({"repo": fn, "stars": stars, "s_adj": s_adj,
                            "kind": kind, "venue": ven, "orders": bool(orders),
                            "backtest": bool(bt), "signals": esf})

    print(f"scanned {scanned} cached archives\n")
    print("STEP 4 — order-book mechanics prevalence across the WHOLE corpus:")
    for k, n in sorted(prevalence.items(), key=lambda x: -x[1]):
        print(f"   {k:16} {n:>5} repos ({100*n/scanned:.1f}%)")

    print(f"\nSTEP 4 — repos with >=2 core book mechanics AND a Kalshi import: "
          f"{len(l2_hits)}")
    l2_hits.sort(key=lambda h: -(h["s_adj"] or -9))
    for h in l2_hits[:10]:
        print(f"  {h['repo'][:48]:48} s_adj={str(h['s_adj'])[:5]:>5} "
              f"*{h['stars']} {h['kind']} ord={h['orders']} bt={h['backtest']} "
              f"{sorted(h['signals'])}")

    print(f"\nSTEP 6 — repos mentioning esports ON a prediction market: "
          f"{len(es_hits)}")
    es_hits.sort(key=lambda h: -(h["s_adj"] or -9))
    for h in es_hits[:12]:
        print(f"  {h['repo'][:48]:48} s_adj={str(h['s_adj'])[:5]:>5} "
              f"*{h['stars']} {h['kind']} venue={h['venue']} "
              f"ord={h['orders']} bt={h['backtest']}")

    # --- Step 6 from the social corpus ---
    print("\nSTEP 6 — esports prediction-market reports on Reddit:")
    sc = sqlite3.connect(f"file:{SOCIAL.as_posix()}?mode=ro", uri=True)
    sc.create_function("RX", 2,
                       lambda p, s: 1 if s and re.search(p, s, re.I | re.S) else 0)
    pat = (r"(esport|csgo|cs2|counter-strike|league of legends|dota|valorant)")
    pm = r"(kalshi|polymarket|prediction market)"
    rows = sc.execute(
        "select post_id, subreddit, score, title, substr(coalesce(selftext,''),1,300) "
        "from rd_posts where RX(?, title||' '||coalesce(selftext,'')) "
        "and RX(?, title||' '||coalesce(selftext,'')) order by score desc limit 25",
        (pat, pm)).fetchall()
    for r in rows:
        print(f"  [{r[2]:>4}] {r[0]:9} r/{r[1]:<18} {r[3][:88]}")
    ncom = sc.execute(
        "select count(*) from rd_comments where RX(?, body) and RX(?, body)",
        (pat, pm)).fetchone()[0]
    print(f"  ({len(rows)} posts shown; {ncom} comments also match)")
    sc.close()

    (REP / "l2_esports_scan.json").write_text(
        json.dumps({"scanned": scanned, "prevalence": dict(prevalence),
                    "l2_hits": l2_hits, "esports_hits": es_hits,
                    "reddit": [list(r) for r in rows]}, indent=1),
        encoding="utf-8")
    print("\nwrote reports/l2_esports_scan.json")


if __name__ == "__main__":
    main()
