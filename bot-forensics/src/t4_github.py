"""
t4_github.py - TASK 4, the GitHub arm.

WHY THIS IS NOT JUST `classify.py --need tennis`.

It was tried first. `signal-github`'s corpus holds 3,137 classified repos and
exactly FIVE match "tennis". That corpus was retrieved with Kalshi/Polymarket
terms and its gate is a prediction-market topic gate, so a repo that scrapes
ITF draws and never mentions Kalshi is invisible to it by construction -
correctly, for that project's purpose, and uselessly for this question.

Adding tennis terms to `signal-github/src/queries.py` would push them through
that same gate and DROP them. So this is a separate, narrow retrieval that
reuses signal-github's cached, authenticated client (`gh.py`) and writes
nothing into that project's database.

FOUR QUESTIONS
  Q1  a working in-play tennis strategy for prediction markets, with evidence
  Q2  free live tennis score/odds sources people with real results actually use
  Q3  ITF-specific data - the one that could reopen a closed thread
  Q4  an overnight-vs-daytime effect in prediction-market sports books
"""
from __future__ import annotations
import sys, os, json, time, re
SG = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "..", "..", "signal-github", "src"))
sys.path.insert(0, SG)
import gh

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
CACHE = os.path.join(OUT, "t4_github_raw.json")

QUERIES = {
    "Q1_inplay_strategy": [
        "in-play tennis trading",
        "live tennis trading bot",
        "betfair tennis trading",
        "tennis in play betting model",
        "kalshi tennis",
        "polymarket tennis",
        "tennis momentum betting",
    ],
    "Q2_score_sources": [
        "sofascore api",
        "sofascore scraper",
        "flashscore scraper",
        "livescore tennis api",
        "tennis live scores scraper",
        "tennis api wrapper",
        "tennis point by point data",
        "betfair exchange tennis odds",
        "the-odds-api",
    ],
    "Q3_itf": [
        "itf tennis",
        "itf world tennis tour",
        "itf tennis scraper",
        "tennis futures results scraper",
        "tennisexplorer scraper",
        "itf juniors results",
        "tennis abstract sackmann",
        "atp challenger scraper",
    ],
    "Q4_time_of_day": [
        "prediction market overnight liquidity",
        "sports betting market overnight",
        "kalshi liquidity by hour",
        "prediction market microstructure sports",
    ],
}

CODE_QUERIES = [
    "api.sofascore.com/api/v1/sport/tennis",
    "live.tennis.com",
    "itftennis.com api",
    "www.itftennis.com/tennis/api",
    "tennisexplorer.com",
    "api.sofascore.com event/live",
    "flashscore.com/x/feed",
]


def run():
    got = {}
    if os.path.exists(CACHE):
        got = json.load(open(CACHE, encoding="utf-8"))
    for fam, qs in QUERIES.items():
        got.setdefault(fam, {})
        for q in qs:
            if q in got[fam]:
                continue
            rows = []
            try:
                for page in (1, 2):
                    r = gh.search("repositories", q, per_page=100, page=page)
                    items = (r or {}).get("items") or []
                    for it in items:
                        rows.append({
                            "full_name": it.get("full_name"),
                            "desc": (it.get("description") or "")[:300],
                            "stars": it.get("stargazers_count") or 0,
                            "forks": it.get("forks_count") or 0,
                            "lang": it.get("language") or "",
                            "pushed": it.get("pushed_at") or "",
                            "created": it.get("created_at") or "",
                            "archived": bool(it.get("archived")),
                            "size_kb": it.get("size") or 0,
                            "topics": it.get("topics") or [],
                            "url": it.get("html_url") or "",
                        })
                    if len(items) < 100:
                        break
            except Exception as e:
                rows = [{"ERROR": f"{type(e).__name__}: {e}"}]
            got[fam][q] = rows
            print(f"{fam:22s} {q:42s} -> {len(rows)}")
            time.sleep(1.2)

    got.setdefault("CODE", {})
    for q in CODE_QUERIES:
        if q in got["CODE"]:
            continue
        try:
            r = gh.code_search(q, pages=1)
            names = sorted({(x.get("repository") or {}).get("full_name")
                            for x in (r or []) if isinstance(x, dict)} - {None})
        except Exception as e:
            names = [f"ERROR {type(e).__name__}: {e}"]
        got["CODE"][q] = names
        print(f"{'CODE':22s} {q:42s} -> {len(names)}")
        time.sleep(2.0)

    json.dump(got, open(CACHE, "w", encoding="utf-8"), indent=1)
    return got


def report(got):
    """Rank and de-duplicate. Never by stars - signal-github measured
    rho(stars, substance) = -0.008 at n=3,165."""
    import datetime as dt
    now = dt.datetime(2026, 8, 5, tzinfo=dt.timezone.utc)
    lines = []
    for fam in list(QUERIES) + [] :
        seen = {}
        for q, rows in (got.get(fam) or {}).items():
            for r in rows:
                if "full_name" not in r or not r["full_name"]:
                    continue
                e = seen.setdefault(r["full_name"], dict(r, queries=set()))
                e["queries"].add(q)
        lines.append(f"\n{'='*78}\n{fam}   ({len(seen)} distinct repos)\n{'='*78}")
        rank = []
        for fn, r in seen.items():
            try:
                age = (now - dt.datetime.fromisoformat(
                    r["pushed"].replace("Z", "+00:00"))).days
            except Exception:
                age = 9999
            r["age_d"] = age
            # substance-ish proxy available without downloading: size + recency
            # + query breadth. NOT stars.
            r["score"] = (min(r["size_kb"], 20000) / 1000.0
                          + 3 * len(r["queries"])
                          - (age / 180.0)
                          - (10 if r["archived"] else 0))
            rank.append(r)
        rank.sort(key=lambda z: -z["score"])
        for r in rank[:22]:
            lines.append(f"  {r['full_name'][:52]:52s} {r['stars']:6d}* "
                         f"{r['age_d']:5d}d {r['size_kb']:8d}kb "
                         f"{'ARCH' if r['archived'] else '    '} {r['lang'][:10]:10s}")
            lines.append(f"      {r['desc'][:150]}")
    lines.append(f"\n{'='*78}\nCODE SEARCH (the import a README never mentions)\n{'='*78}")
    for q, names in (got.get("CODE") or {}).items():
        lines.append(f"\n  {q}  -> {len(names)}")
        for n in names[:18]:
            lines.append(f"      {n}")
    return "\n".join(lines)


if __name__ == "__main__":
    g = run()
    txt = report(g)
    print(txt)
    open(os.path.join(OUT, "t4_github.txt"), "w", encoding="utf-8").write(txt)
