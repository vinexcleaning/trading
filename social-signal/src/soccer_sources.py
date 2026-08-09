"""Free sources for the MINUTE each goal was scored, in the competitions Kalshi runs.

The `soccer` chat needs to know who was losing in the 80th minute. This repo has
24,172 finished matches with **final scores only**, and a final score cannot tell
you that. So: which free sources give per-goal minutes, for which competitions,
how far back, and without an account?

**The competitions that matter are the awkward ones.** Early evidence says Kalshi
runs mostly international friendlies plus Uruguay, USL, Ecuador, Peru, NWSL,
Chile, MLS, Colombia and Liga MX â€” **not** the Premier League or the Champions
League. Free coverage of small South American leagues is exactly where it thins
out, so every claim here is a fetch, not a recollection.

Two prior sessions in this repo listed sources that turned out to be 404 or 403.
This one reports, per competition: does the endpoint answer, does the payload
carry a goal **minute**, and how far back does it go.

    python src/soccer_sources.py                 # probe every source
    python src/soccer_sources.py --deep usa.1    # one league, walk back by season
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

BROWSER = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/127.0 Safari/537.36")
PACE = 1.2

# ESPN's slugs for the competitions Kalshi actually lists.
ESPN_LEAGUES = {
    "international friendlies": "fifa.friendly",
    "MLS": "usa.1",
    "Liga MX": "mex.1",
    "NWSL": "usa.nwsl",
    "USL Championship": "usa.usl.1",
    "Uruguay Primera": "uru.1",
    "Ecuador Serie A": "ecu.1",
    "Peru Liga 1": "per.1",
    "Chile Primera": "chi.1",
    "Colombia Primera A": "col.1",
    "Argentina Liga Profesional": "arg.1",
    "Brazil Serie A": "bra.1",
}


def fetch_espn(url: str, timeout: int = 30):
    """ESPN needs NO User-Agent override, and this is counter-intuitive enough
    that it cost this session a full round of 403s before reading the sibling's
    code. `soccer/src/backfill_espn.py:38` records the measurement:

        ESPN (Akamai) began returning 403 to any Mozilla/... or unknown custom
        User-Agent on 2026-08-08. curl/8.4.0 -> 200, requests' default -> 200.
        Sending no override is what works; do not "fix" this by adding a
        browser string back.

    Everywhere else in this project a browser UA is the fix. Here it is the bug.
    """
    req = urllib.request.Request(url)          # deliberately no headers
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(2_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:600].decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"
    finally:
        time.sleep(PACE)


def fetch(url: str, timeout: int = 30, accept: str = "application/json"):
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER,
                                               "Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(2_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:600].decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"
    finally:
        time.sleep(PACE)


def espn_probe(slug: str, date_str: str):
    """Scoreboard for a date, then the summary of one finished match.

    The decisive test is not 'does it return matches' but 'does a finished match
    carry the CLOCK of each goal'. ESPN puts scoring plays under
    `scoringPlays[].clock.displayValue`.
    """
    url = ("https://site.api.espn.com/apis/site/v2/sports/soccer/"
           f"{slug}/scoreboard?dates={date_str}")
    st, body = fetch_espn(url)
    out = {"slug": slug, "scoreboard_status": st, "events": 0,
           "goal_minutes": None, "sample": "", "note": ""}
    if st != 200:
        out["note"] = body[:120]
        return out
    try:
        d = json.loads(body)
    except json.JSONDecodeError:
        out["note"] = "unparseable"
        return out
    evs = d.get("events") or []
    out["events"] = len(evs)
    done = [e for e in evs
            if ((e.get("status") or {}).get("type") or {}).get("completed")]
    if not done:
        out["note"] = f"{len(evs)} events, none completed on this date"
        return out
    eid = done[0].get("id")
    st2, body2 = fetch_espn("https://site.api.espn.com/apis/site/v2/sports/soccer/"
                       f"{slug}/summary?event={eid}")
    if st2 != 200:
        out["note"] = f"summary HTTP {st2}"
        return out
    try:
        s = json.loads(body2)
    except json.JSONDecodeError:
        out["note"] = "summary unparseable"
        return out
    plays = s.get("scoringPlays") or []
    mins = []
    for p in plays:
        clk = ((p.get("clock") or {}).get("displayValue")
               or (p.get("clock") or {}).get("value"))
        if clk:
            mins.append(str(clk))
    out["goal_minutes"] = len(mins)
    out["sample"] = ", ".join(mins[:6])
    if not plays:
        out["note"] = "completed match but scoringPlays empty (0-0, or not populated)"
    return out


# Non-ESPN candidates. Each is probed for: does it answer keyless, and does the
# payload contain a goal minute.
OTHER_SOURCES = [
    ("openfootball/football.json (GitHub raw)",
     "https://raw.githubusercontent.com/openfootball/football.json/master/"
     "2020-21/en.1.json", "json"),
    ("football-data.org v4 (free tier)",
     "https://api.football-data.org/v4/competitions", "json"),
    ("StatsBomb open data (GitHub raw)",
     "https://raw.githubusercontent.com/statsbomb/open-data/master/data/"
     "competitions.json", "json"),
    ("football-data.co.uk (final scores only, known)",
     "https://www.football-data.co.uk/mmz4281/2425/E0.csv", "csv"),
    ("FBref (known Cloudflare)",
     "https://fbref.com/en/comps/22/schedule/Major-League-Soccer-Scores-and-Fixtures",
     "html"),
    ("Sofascore unofficial API",
     "https://api.sofascore.com/api/v1/sport/football/scheduled-events/2026-08-02",
     "json"),
    ("worldfootball.net",
     "https://www.worldfootball.net/all_matches/usa-major-league-soccer-2025/",
     "html"),
    ("Wikipedia API (match reports)",
     "https://en.wikipedia.org/api/rest_v1/page/summary/2026_Major_League_Soccer_season",
     "json"),
]

ROBOTS = ["https://site.api.espn.com/robots.txt", "https://www.espn.com/robots.txt",
          "https://fbref.com/robots.txt", "https://api.sofascore.com/robots.txt",
          "https://www.worldfootball.net/robots.txt"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="20260802",
                    help="YYYYMMDD to probe the scoreboard on")
    ap.add_argument("--skip-espn", action="store_true")
    args = ap.parse_args()

    rows = []
    if not args.skip_espn:
        print(f"ESPN, scoreboard date {args.date}")
        for name, slug in ESPN_LEAGUES.items():
            r = espn_probe(slug, args.date)
            rows.append({"source": "ESPN", "competition": name, **r})
            gm = r["goal_minutes"]
            print(f"  {name:<28} {slug:<14} HTTP {r['scoreboard_status']:<4} "
                  f"{r['events']:>3} ev  goals w/ minute: "
                  f"{gm if gm is not None else '-':<4} {r['sample'][:34]}"
                  f"  {r['note'][:40]}", flush=True)

    print("\nOther candidate sources")
    others = []
    for name, url, kind in OTHER_SOURCES:
        st, body = fetch(url, accept="*/*")
        has_min = bool(re.search(r'"minute"|"clock"|\bminute\b|\'minute\'',
                                 body[:200_000], re.I))
        others.append({"source": name, "url": url, "status": st,
                       "bytes": len(body), "mentions_minute": has_min,
                       "head": body[:90].replace("\n", " ")})
        print(f"  {name:<44} {st:<5} {len(body):>8}B  "
              f"minute-field: {'YES' if has_min else 'no':<4} "
              f"{body[:50].strip()[:50] if st != 200 else ''}", flush=True)

    print("\nrobots.txt")
    robots = []
    for u in ROBOTS:
        st, body = fetch(u, accept="text/plain")
        star, rules = False, []
        for ln in body.splitlines():
            low = ln.strip().lower()
            if low.startswith("user-agent:"):
                star = low.split(":", 1)[1].strip() == "*"
            elif star and low.startswith(("disallow:", "allow:")):
                rules.append(ln.strip())
        robots.append({"url": u, "status": st, "rules": rules[:6]})
        print(f"  {u:<48} {st:<5} {' | '.join(rules[:3])[:70]}")

    out = os.path.join(db.REPORTS, "SOCCER_GOAL_TIME_SOURCES.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# Free sources for the minute each goal was scored\n\n")
        fh.write(f"Every row fetched {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d} "
                 f"UTC. Scoreboard probes use {args.date}.\n\n")
        fh.write("## ESPN, by competition\n\n")
        fh.write("| competition | ESPN slug | scoreboard | events | goals with a minute | sample | note |\n")
        fh.write("|---|---|---|---|---|---|---|\n")
        for r in rows:
            fh.write(f"| {r['competition']} | `{r['slug']}` | "
                     f"{r['scoreboard_status']} | {r['events']} | "
                     f"{r['goal_minutes'] if r['goal_minutes'] is not None else 'â€”'} | "
                     f"{r['sample']} | {r['note'][:70]} |\n")
        fh.write("\n## Other candidates\n\n")
        fh.write("| source | status | bytes | has a minute field | first bytes |\n")
        fh.write("|---|---|---|---|---|\n")
        for r in others:
            fh.write(f"| {r['source']} | **{r['status']}** | {r['bytes']:,} | "
                     f"{'YES' if r['mentions_minute'] else 'no'} | "
                     f"`{r['head'][:60]}` |\n")
        fh.write("\n## robots.txt\n\n| host | status | `*` rules |\n|---|---|---|\n")
        for r in robots:
            fh.write(f"| `{r['url']}` | {r['status']} | "
                     f"{' / '.join(r['rules'][:4]) or '(none)'} |\n")
    print(f"\n  wrote {out}")
    con = db.connect()
    db.log(con, "soccer_sources",
           f"espn={len(rows)} others={len(others)}")
    con.close()


if __name__ == "__main__":
    main()

