"""Which repos price a prediction market off a SHARP SPORTSBOOK REFERENCE PRICE?

Follows github-signal's cost model: scans the cached whole-repo archives on
disk, putting zero bytes of repo source into the model's context. Only the
counts and the matched lines come back.

The question: the one strategy in any corpus here with a public wallet and a
reconciled four-line P&L works by de-vigging sharp bookmaker odds and quoting
that fair value passively on Polymarket. It needs NO domain data. If that
design is real, other people have built it. If almost nobody has, that is worth
knowing too — and so is whether the ones who did got the de-vig right.

De-vig methods differ materially and the choice is not cosmetic:
  multiplicative  divide by the overround. Biases toward favourites.
  Shin            solves for an insider-trading parameter. The arb author above
                  reported his Shin implementation "ran hot on favourites".
  power           raises to a common exponent; usually the best fit empirically.
  worst-case      take the least favourable; the only conservative choice.

Output: reports/devig_scan.json
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

SIGNALS = {
    # the concept
    "devig": r"\bde[-_ ]?vig\b|\bdevig|remove[_ ]vig|no[-_ ]?vig|\bvigorish\b",
    "overround": r"\boverround\b|\bbooksum\b|book_sum|implied_sum",
    # named methods — which one is a real discriminator of care
    "m_multiplicative": r"multiplicative[_ ]?devig|proportional[_ ]?devig",
    "m_shin": r"\bshin\b.{0,30}(devig|method|model|z\b)|shin_z|shin_method",
    "m_power": r"power[_ ]?(devig|method)|odds[_ ]?power",
    "m_worstcase": r"worst[_ ]?case[_ ]?(devig|odds)",
    "m_additive": r"additive[_ ]?devig",
    # sharp reference books
    "pinnacle": r"pinnacle",
    "pinnacle_guest_api": r"guest\.api\.arcadia\.pinnacle\.com",
    "betfair": r"betfair",
    "the_odds_api": r"api\.the-odds-api\.com|the[-_]odds[-_]api|ODDS_API_KEY",
    "draftkings": r"draftkings|sportsbook\.draftkings",
    "espn_odds": r"sports\.core\.api\.espn\.com|site\.api\.espn\.com",
    # the payoff concept
    "clv": r"closing[_ ]line[_ ]value|\bCLV\b",
    "fair_prob": r"fair_prob|fair_probability|fair_value|fair_odds",
    # cross-venue
    "cross_venue": r"(kalshi.{0,60}polymarket|polymarket.{0,60}kalshi)",
    # passive quoting against a fair value — the exact design in question
    "passive_quote": r"post_only|postOnly|GTC|maker[_ ]?only|limit_order|"
                     r"place_limit|resting[_ ]order",
}

TEXT_EXT = {".py", ".js", ".ts", ".tsx", ".go", ".rs", ".java", ".rb", ".md",
            ".ipynb", ".json", ".yaml", ".yml", ".sql", ".c", ".cpp", ".cs"}


def cache_files(full_name, default_branch):
    for br in [default_branch, "main", "master"]:
        if not br:
            continue
        url = f"https://codeload.github.com/{full_name}/tar.gz/{br}"
        p = CACHE / f"{hashlib.sha1(url.encode()).hexdigest()[:20]}.arch.json"
        if p.exists():
            yield p


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    repos = con.execute(
        "select full_name, default_branch, stars, venue_detected, kind, "
        "submits_orders, s_adj, has_backtest, trust_me_bro, pushed_at, "
        "is_archived, description from repos").fetchall()
    con.close()

    rx = {k: re.compile(v, re.I) for k, v in SIGNALS.items()}
    hits, counts = [], defaultdict(int)
    scanned = 0
    for (fn, br, stars, venue, kind, orders, s_adj, bt, tmb, pushed,
         arch, desc) in repos:
        blob = None
        for p in cache_files(fn, br):
            try:
                d = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            except json.JSONDecodeError:
                continue
            if d.get("status") != 200 or not d.get("files"):
                continue
            parts = []
            for path, text in d["files"].items():
                if isinstance(text, str) and (
                        not Path(path).suffix or
                        Path(path).suffix.lower() in TEXT_EXT):
                    parts.append(f"\n### {path}\n{text}")
            blob = "".join(parts)
            break
        if not blob:
            continue
        scanned += 1
        found = {}
        for k, r in rx.items():
            m = r.search(blob)
            if m:
                found[k] = len(r.findall(blob))
                counts[k] += 1
        # A hit needs the CONCEPT, not just a bookmaker's name in a README.
        core = any(k in found for k in
                   ("devig", "overround", "m_multiplicative", "m_shin",
                    "m_power", "m_worstcase", "clv"))
        if not core:
            continue
        # capture the matching lines so a claim can be checked at path:line
        lines = []
        cur_path = "?"
        for i, ln in enumerate(blob.splitlines()):
            if ln.startswith("### "):
                cur_path = ln[4:]
                continue
            for k in ("devig", "overround", "m_shin", "m_power",
                      "m_multiplicative", "m_worstcase", "clv"):
                if k in found and rx[k].search(ln):
                    lines.append(f"{cur_path}: {ln.strip()[:160]}")
                    break
            if len(lines) >= 25:
                break
        hits.append({
            "repo": fn, "stars": stars, "venue": venue, "kind": kind,
            "submits_orders": orders, "s_adj": s_adj, "has_backtest": bt,
            "trust_me_bro": tmb, "pushed_at": pushed, "archived": arch,
            "description": (desc or "")[:180],
            "signals": found, "lines": lines,
        })
        if scanned % 400 == 0:
            print(f"  {scanned} scanned, {len(hits)} hits", file=sys.stderr)

    print(f"\nscanned {scanned} cached archives; {len(hits)} carry a real "
          f"de-vig / CLV concept\n")
    print("signal prevalence across the whole scanned corpus:")
    for k, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"   {k:22} {n:>5} repos ({100*n/scanned:.1f}%)")

    hits.sort(key=lambda h: (-(h["s_adj"] or -9), -(h["stars"] or 0)))
    (OUT / "devig_scan.json").write_text(
        json.dumps({"scanned": scanned, "prevalence": dict(counts),
                    "hits": hits}, indent=1), encoding="utf-8")

    print(f"\n{'repo':52} {'s_adj':>6} {'star':>5} {'venue':11} "
          f"{'kind':14} ord bt tmb  methods")
    for h in hits[:40]:
        meth = ",".join(k[2:] for k in h["signals"] if k.startswith("m_")) or "-"
        books = ",".join(k for k in ("pinnacle", "betfair", "the_odds_api",
                                     "draftkings", "espn_odds")
                         if k in h["signals"]) or "-"
        print(f"{h['repo'][:52]:52} {str(h['s_adj'])[:6]:>6} "
              f"{str(h['stars']):>5} {str(h['venue'])[:11]:11} "
              f"{str(h['kind'])[:14]:14} "
              f"{'Y' if h['submits_orders'] else '.'}  "
              f"{'Y' if h['has_backtest'] else '.'}  "
              f"{'Y' if h['trust_me_bro'] else '.'}   {meth} | {books}")
    print(f"\nwrote reports/devig_scan.json")


if __name__ == "__main__":
    main()
