"""Mailbox 017 job 1: WHICH retail books are free, two-sided, and cover Kalshi's markets?

CLAUDE.md §9c step 1 -- a blocker reported without the list of what was tried is
not a blocker. This is the list.

⚠ ONE CORRECTION TO THE INSTRUCTION FIRST. It says my last finding "closed the
retail-book route", citing coverage that "fell from everything in 2022 to nothing
in 2026". **That was M018 -- football-data.co.uk's HISTORICAL closing-line files
for four soccer leagues.** It is a real and dead route, but it is not the
retail-book idea. The retail idea is a LIVE soft book quoted against a Kalshi
market, and two messages ago I found one: Bovada, 447 of 448 MLB markets
two-sided, free, no key, robots.txt disallow list EMPTY. **That route is open and
pre-registered (PREREGISTRATION_RETAIL.md).** The two got conflated.

So this does the job properly: probe every retail book reachable, and for each
record endpoint, HTTP, whether prices are TWO-SIDED, and how many of Kalshi's
own MLB games it covers.

ROBOTS IS CHECKED FIRST AND IS A HARD GATE. A book whose robots file disallows
us is recorded as such and NOT fetched -- `social-signal`'s rule, already in this
repo: "a User-Agent string is not consent." ESPN is the live example: its
robots.txt carries `User-agent: anthropic-ai / Disallow: /`.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import venues as V  # noqa: E402

REP = ROOT / "reports"

BOOKS = [
    ("Bovada", "https://www.bovada.lv",
     "/services/sports/event/coupon/events/A/description/baseball/mlb"),
    ("BetOnline", "https://www.betonline.ag", "/sportsbook/baseball/mlb"),
    ("MyBookie", "https://www.mybookie.ag", "/sportsbook/mlb/"),
    ("BetUS", "https://www.betus.com.pa", "/sportsbook/baseball/mlb/"),
    ("Everygame", "https://www.everygame.eu", "/sportsbook/Baseball"),
    ("Bookmaker", "https://www.bookmaker.eu", "/sportsbook/baseball"),
    ("ESPN/DraftKings", "https://site.api.espn.com",
     "/apis/site/v2/sports/baseball/mlb/scoreboard"),
    ("the-odds-api", "https://api.the-odds-api.com",
     "/v4/sports/baseball_mlb/odds/?regions=us&markets=h2h"),
]

UA_HDR = None   # send no User-Agent: honest, and not impersonating a browser


def robots_verdict(origin: str, path: str):
    """Returns (verdict, detail). A named disallow for us is a hard NO."""
    r = V.get(urllib.parse.urljoin(origin, "/robots.txt"), pace=0.4, tries=1,
              timeout=20)
    if r is None or r.status_code != 200:
        # ⚠ FAIL CLOSED. v1 returned "NO ROBOTS FILE" here and then FETCHED,
        # which is a robots checker that fails OPEN -- the dangerous direction.
        # It mislabelled ESPN as unrestricted when ESPN's robots.txt in fact
        # carries `User-agent: anthropic-ai / Disallow: /`; the file simply 403s
        # to us as well. A permission check that cannot read the permission must
        # not conclude permission.
        return "UNREADABLE - TREAT AS NO", f"robots.txt HTTP {None if r is None else r.status_code}"
    txt = r.text
    low = txt.lower()
    # a group naming us specifically outranks the wildcard group
    for token in ("anthropic-ai", "claudebot", "claude-web"):
        m = re.search(rf"user-agent:\s*{token}\s*(.*?)(?=user-agent:|\Z)",
                      low, re.S)
        if m and re.search(r"disallow:\s*/\s*$", m.group(1).strip(), re.M):
            return "FORBIDDEN", f"names `{token}` and disallows /"
    m = re.search(r"user-agent:\s*\*\s*(.*?)(?=user-agent:|\Z)", low, re.S)
    if m:
        body = m.group(1)
        dis = [l.split(":", 1)[1].strip()
               for l in body.splitlines() if l.strip().startswith("disallow:")]
        if not any(dis) or dis == [""]:
            return "ALLOWED", "wildcard disallow is empty"
        if "/" in dis:
            return "FORBIDDEN", "wildcard disallows /"
        blocked = [d for d in dis if d and path.startswith(d.rstrip("*"))]
        if blocked:
            return "FORBIDDEN", f"path blocked by {blocked[0]}"
        return "ALLOWED", f"{len(dis)} rules, none covering this path"
    return "ALLOWED", "no wildcard group"


def count_two_sided(name: str, body: bytes):
    """Very deliberately crude: count American-odds pairs. A precise parser per
    book is not the question -- the question is whether BOTH sides are priced."""
    txt = body.decode("utf-8", "replace")
    if name == "Bovada":
        try:
            d = json.loads(txt)
        except ValueError:
            return None, None
        ev = [e for g in d for e in (g.get("events") or [])]
        tot = two = 0
        for e in ev:
            for dg in (e.get("displayGroups") or []):
                for m in (dg.get("markets") or []):
                    tot += 1
                    if len([o for o in (m.get("outcomes") or [])
                            if (o.get("price") or {}).get("american")]) >= 2:
                        two += 1
        return tot, two
    odds = re.findall(r'[+-]\d{3,4}\b', txt)
    return len(odds), None


def main() -> None:
    REP.mkdir(parents=True, exist_ok=True)
    out = []
    print(f"{'book':18} {'robots':11} {'HTTP':>5} {'bytes':>9}  two-sided")
    print("-" * 72)
    for name, origin, path in BOOKS:
        verdict, why = robots_verdict(origin, path)
        row = {"book": name, "origin": origin, "path": path,
               "robots": verdict, "robots_detail": why}
        if verdict.startswith("FORBIDDEN") or verdict.startswith("UNREADABLE"):
            print(f"{name:18} {'FORBIDDEN':11} {'--':>5} {'--':>9}  "
                  f"NOT FETCHED — {why}")
            row.update(http=None, bytes=0, note="not fetched, robots forbids")
            out.append(row)
            continue
        r = V.get(origin + path, pace=0.6, tries=1, timeout=25)
        code = None if r is None else r.status_code
        n = len(r.content) if r is not None else 0
        tot = two = None
        if r is not None and r.status_code == 200 and n > 2000:
            tot, two = count_two_sided(name, r.content)
        desc = ("—" if tot is None else
                (f"{two:,} of {tot:,} markets" if two is not None
                 else f"{tot:,} price tokens (unparsed)"))
        print(f"{name:18} {verdict:11} {str(code):>5} {n:>9,}  {desc}")
        row.update(http=code, bytes=n, markets=tot, two_sided=two)
        out.append(row)

    (REP / "retail_book_census.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print("\nwrote reports/retail_book_census.json")


if __name__ == "__main__":
    main()
