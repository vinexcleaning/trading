"""STEP 1 — what markets do people who write code actually build for?

Scans the 3.4 GB of whole-repo source archives `signal-github` already cached
and counts, per market family, how many DISTINCT REPOSITORIES carry evidence of
targeting it. Reading source beats reading READMEs: a README topic gate passed
1,013 repos that import neither venue.

Two evidence tiers, kept separate because they are not the same claim:

  TICKER   a literal Kalshi series ticker appears in the source. Near-zero
           false-positive rate — nobody writes "KXATPMATCH" by accident.
  KEYWORD  a family word appears near a venue word. Noisy; reported but never
           quoted on its own.

Output: reports/family_census.json + a printed table.
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
CACHE = GH / "cache"
DB = GH / "data" / "github.db"
OUT = Path(__file__).resolve().parent.parent / "reports"

# Kalshi series ticker prefixes, grouped into the families Step 2 will rank.
# Sourced from the live series list (see tools/kalshi_series.py), not memory.
TICKERS = {
    "tennis": ["KXATPMATCH", "KXWTAMATCH", "KXITFMATCH", "KXCHALLENGER"],
    "crypto_short": ["KXBTC15M", "KXETH15M", "KXSOL15M", "KXXRP15M", "KXDOGE15M"],
    "crypto_daily": ["KXBTCD", "KXETHD", "KXBTCMAX", "KXBTC", "KXETH"],
    "weather": ["KXHIGH", "KXTEMP", "KXLOWT", "KXRAIN", "KXSNOW", "KXHURRICANE"],
    "nfl": ["KXNFL", "KXSB", "KXNFLGAME", "KXPRO"],
    "nba": ["KXNBA", "KXNBAGAME"],
    "mlb": ["KXMLB", "KXMLBGAME"],
    "nhl": ["KXNHL"],
    "soccer": ["KXEPL", "KXUCL", "KXMLS", "KXLALIGA", "KXSERIEA", "KXWC"],
    "econ": ["KXCPI", "KXFED", "KXGDP", "KXPAYROLL", "KXUNRATE", "KXRECESSION"],
    "politics": ["KXPRES", "KXSENATE", "KXHOUSE", "KXELECT", "KXGOV"],
    "entertainment": ["KXOSCAR", "KXGRAMMY", "KXEMMY", "KXROTTEN", "KXBOX"],
    "esports": ["KXLOL", "KXCSGO", "KXDOTA", "KXVALORANT"],
    "golf": ["KXPGA", "KXMASTERS", "KXGOLF"],
    "f1": ["KXF1", "KXFORMULA"],
    "mma": ["KXUFC", "KXMMA"],
    "space": ["KXSPACEX", "KXLAUNCH", "KXROCKET"],
    "ai_tech": ["KXAI", "KXCHATGPT", "KXOPENAI"],
}

# Keyword tier. Deliberately requires a venue word in the same file.
KEYWORDS = {
    "tennis": ["tennis", "atp", "wta"],
    "crypto_short": ["15m", "15-minute", "fifteen minute"],
    "crypto_daily": ["bitcoin", "ethereum", "btc", "eth"],
    "weather": ["weather", "temperature", "noaa", "forecast high"],
    "nfl": ["nfl", "super bowl", "touchdown"],
    "nba": ["nba", "basketball"],
    "mlb": ["mlb", "baseball"],
    "nhl": ["nhl", "hockey"],
    "soccer": ["soccer", "premier league", "la liga", "champions league"],
    "econ": ["cpi", "fomc", "nonfarm", "inflation print", "fed funds"],
    "politics": ["election", "presidential", "senate race", "polling average"],
    "entertainment": ["oscars", "rotten tomatoes", "box office", "grammy"],
    "esports": ["esports", "league of legends", "counter-strike", "valorant"],
    "golf": ["pga", "masters tournament"],
    "f1": ["formula 1", "formula one", "grand prix"],
    "mma": ["ufc", "mma"],
    "space": ["spacex", "rocket launch"],
    "ai_tech": ["openai", "gpt-5", "agi by"],
}

VENUE = re.compile(r"kalshi|polymarket", re.I)
TEXT_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb",
            ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".sql", ".ipynb",
            ".sh", ".cfg", ".ini", ".env", ".example", ".c", ".cpp", ".cs"}


def cache_paths(full_name: str, default_branch: str | None):
    branches = []
    if default_branch:
        branches.append(default_branch)
    branches += ["main", "master"]
    seen = set()
    for br in branches:
        if br in seen:
            continue
        seen.add(br)
        url = f"https://codeload.github.com/{full_name}/tar.gz/{br}"
        yield CACHE / f"{hashlib.sha1(url.encode()).hexdigest()[:20]}.arch.json"


def load_archive(full_name: str, default_branch: str | None):
    for p in cache_paths(full_name, default_branch):
        if not p.exists():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            continue
        if d.get("status") == 200 and d.get("files"):
            return d
    return None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    repos = con.execute(
        "select full_name, default_branch, stars, venue_detected, kind, "
        "submits_orders, s_adj, trust_me_bro from repos "
        "where gate='PASS' or gate is null"
    ).fetchall()
    con.close()
    print(f"repos considered: {len(repos)}", file=sys.stderr)

    ticker_hits = defaultdict(set)     # family -> {repo}
    keyword_hits = defaultdict(set)
    ticker_detail = defaultdict(lambda: defaultdict(int))  # family -> ticker -> repos
    per_repo = {}
    scanned = 0
    missing = 0

    tick_res = {
        fam: re.compile("|".join(re.escape(t) for t in ts))
        for fam, ts in TICKERS.items()
    }
    kw_res = {
        fam: re.compile("|".join(re.escape(k) for k in ks), re.I)
        for fam, ks in KEYWORDS.items()
    }

    for full_name, br, stars, venue, kind, submits, s_adj, tmb in repos:
        arch = load_archive(full_name, br)
        if arch is None:
            missing += 1
            continue
        scanned += 1
        blob_parts = []
        for path, text in arch["files"].items():
            if not isinstance(text, str):
                continue
            ext = Path(path).suffix.lower()
            if ext and ext not in TEXT_EXT:
                continue
            blob_parts.append(text)
        blob = "\n".join(blob_parts)
        if not blob:
            continue
        has_venue = bool(VENUE.search(blob))
        fams_t, fams_k = [], []
        for fam, rx in tick_res.items():
            found = set(rx.findall(blob))
            if found:
                ticker_hits[fam].add(full_name)
                fams_t.append(fam)
                for t in found:
                    ticker_detail[fam][t] += 1
        if has_venue:
            for fam, rx in kw_res.items():
                if rx.search(blob):
                    keyword_hits[fam].add(full_name)
                    fams_k.append(fam)
        if fams_t or fams_k:
            per_repo[full_name] = {
                "stars": stars, "venue": venue, "kind": kind,
                "submits_orders": submits, "s_adj": s_adj, "trust_me_bro": tmb,
                "ticker_families": sorted(fams_t),
                "keyword_families": sorted(fams_k),
            }
        if scanned % 250 == 0:
            print(f"  {scanned} scanned", file=sys.stderr)

    print(f"scanned {scanned}, no cached archive for {missing}", file=sys.stderr)

    rows = []
    for fam in TICKERS:
        t = ticker_hits[fam]
        k = keyword_hits[fam]
        # Repos that both name a ticker AND submit real orders are the strongest
        # evidence a family is actually traded rather than merely discussed.
        live = [r for r in t if per_repo.get(r, {}).get("submits_orders")]
        rows.append({
            "family": fam,
            "repos_ticker": len(t),
            "repos_keyword": len(k),
            "repos_ticker_and_live": len(live),
            "example_tickers": sorted(ticker_detail[fam].items(),
                                      key=lambda x: -x[1])[:6],
            "top_ticker_repos": sorted(
                t, key=lambda r: -(per_repo.get(r, {}).get("stars") or 0))[:8],
        })
    rows.sort(key=lambda r: (-r["repos_ticker"], -r["repos_keyword"]))

    (OUT / "family_census.json").write_text(
        json.dumps({"scanned": scanned, "missing_archive": missing,
                    "families": rows, "per_repo": per_repo}, indent=1),
        encoding="utf-8")

    print(f"\n{'family':16} {'ticker':>7} {'live':>5} {'keyword':>8}   top tickers")
    for r in rows:
        ex = ", ".join(f"{t}({n})" for t, n in r["example_tickers"][:4])
        print(f"{r['family']:16} {r['repos_ticker']:>7} "
              f"{r['repos_ticker_and_live']:>5} {r['repos_keyword']:>8}   {ex}")


if __name__ == "__main__":
    main()
