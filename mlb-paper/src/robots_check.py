"""robots.txt gate. NOTHING in mlb-paper fetches a host that has not passed it.

The brief said FREE SOURCES ONLY and DO NOT SCRAPE ANYTHING WHOSE robots.txt
DISALLOWS IT. social-signal already established that a site's machine-readable
statement of who may crawl is the constraint even when the content is one GET
away with a browser User-Agent -- reddit.com returns 200 and 54 KB to a browser
UA and is still Disallow: /.

This module is the enforcement point, not a report. `allowed(url)` is called by
every fetcher in this project before every request, and a host that has not
been checked is refused rather than allowed by default.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path

UA = "trading-research/1.0 (personal research)"
OUT = Path(__file__).resolve().parent.parent / "reports"
CACHE: dict[str, urllib.robotparser.RobotFileParser] = {}

# Every host mlb-paper may touch. Anything not here is refused by allowed().
CANDIDATES = [
    # --- the label and the schedule -------------------------------------
    ("https://statsapi.mlb.com/api/v1/schedule?sportId=1",
     "MLB Stats API: schedule, probable pitchers, linescore, boxscore"),
    ("https://baseballsavant.mlb.com/statcast_search",
     "Statcast search (pitch-level); also the CSV export"),
    # --- weather ---------------------------------------------------------
    # The obvious two are BOTH refused, which is why this file exists.
    ("https://api.open-meteo.com/v1/forecast",
     "Open-Meteo -- robots.txt is `Disallow: /`. REFUSED."),
    ("https://api.weather.gov/points/39.9,-75.1",
     "US NWS -- robots.txt is `Disallow: /`. REFUSED."),
    # What is left, and it is better than either: NOAA's Aviation Weather
    # Center. No key, no robots.txt at all (404 => unrestricted, RFC 9309),
    # and it publishes TAF -- a 24-30 h FORECAST of wind direction, wind
    # speed, gusts and precipitation at every major airport. Every ballpark
    # has one within ~15 miles.
    ("https://aviationweather.gov/api/data/taf?ids=KPIT&format=json",
     "NOAA Aviation Weather Center: METAR observed + TAF forecast wind/temp"),
    # --- reference / history ---------------------------------------------
    ("https://www.retrosheet.org/gamelogs/index.html", "Retrosheet game logs"),
    ("https://raw.githubusercontent.com/chadwickbureau/register/master/README.md",
     "Chadwick Bureau player register (raw.githubusercontent)"),
    ("https://api.github.com/rate_limit", "GitHub API"),
    # --- the venues -------------------------------------------------------
    ("https://api.elections.kalshi.com/trade-api/v2/exchange/status",
     "Kalshi public read API"),
    ("https://guest.api.arcadia.pinnacle.com/0.1/sports/3/matchups",
     "Pinnacle guest API (the sharp reference)"),
    # --- checked and expected to FAIL, recorded so the answer is on file --
    ("https://www.fangraphs.com/", "FanGraphs"),
    ("https://www.baseball-reference.com/", "Baseball-Reference"),
    ("https://www.rotowire.com/baseball/", "RotoWire"),
    ("https://www.espn.com/mlb/", "ESPN web"),
    ("https://www.reddit.com/r/baseball/", "Reddit (known Disallow: /)"),
    ("https://www.mlb.com/", "MLB.com web"),
]


def _robots_url(url):
    p = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((p.scheme, p.netloc, "/robots.txt", "", ""))


def parser_for(url):
    p = urllib.parse.urlsplit(url)
    host = f"{p.scheme}://{p.netloc}"
    if host in CACHE:
        return CACHE[host]
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(_robots_url(url))
    try:
        req = urllib.request.Request(_robots_url(url),
                                     headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            rp.parse(r.read().decode("utf-8", "replace").splitlines())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            rp.disallow_all = True        # RFC 9309: 4xx auth => full disallow
        else:
            rp.allow_all = True           # 404 => no restrictions published
    except Exception:
        rp.disallow_all = True            # unreachable => refuse, never assume
    CACHE[host] = rp
    return rp


ALLOWED_HOSTS = None                       # filled by load_policy()


def load_policy():
    """Host allowlist, from the last recorded run of this module."""
    global ALLOWED_HOSTS
    f = OUT / "robots_policy.json"
    if not f.exists():
        raise RuntimeError(
            "robots_policy.json missing -- run `python src/robots_check.py` "
            "before any fetcher. Nothing here fetches an unchecked host.")
    d = json.loads(f.read_text())
    ALLOWED_HOSTS = {h for h, v in d["hosts"].items() if v["allowed"]}
    return ALLOWED_HOSTS


def allowed(url):
    """True only if the host was checked AND robots.txt permits this path."""
    if ALLOWED_HOSTS is None:
        load_policy()
    p = urllib.parse.urlsplit(url)
    host = f"{p.scheme}://{p.netloc}"
    if host not in ALLOWED_HOSTS:
        return False
    return parser_for(url).can_fetch(UA, url)


def check_all():
    hosts, rows = {}, []
    for url, why in CANDIDATES:
        p = urllib.parse.urlsplit(url)
        host = f"{p.scheme}://{p.netloc}"
        rp = parser_for(url)
        ok = rp.can_fetch(UA, url)
        star = rp.can_fetch("*", url)
        delay = None
        try:
            delay = rp.crawl_delay(UA) or rp.crawl_delay("*")
        except Exception:
            pass
        rows.append({"url": url, "host": host, "why": why,
                     "allowed": bool(ok), "allowed_wildcard": bool(star),
                     "crawl_delay_s": delay})
        # Host-level flag records only that robots.txt was RETRIEVED and does
        # not blanket-ban this UA. Per-path permission is still decided by
        # can_fetch() at request time in allowed(), because a host can permit
        # one path and forbid another -- retrosheet.org allows most of the site
        # and forbids exactly /gamelogs/, which is the part we wanted.
        blanket = not rp.can_fetch(UA, host + "/")
        prev = hosts.get(host)
        hosts[host] = {
            "allowed": (not blanket) and (prev is None or prev["allowed"]),
            "example_path_allowed": bool(ok),
            "crawl_delay_s": delay}
        print(f"  {'ALLOW ' if ok else 'REFUSE'} {host:<46} {why}")
        time.sleep(0.2)
    return hosts, rows


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    print("robots.txt gate -- UA:", UA)
    hosts, rows = check_all()
    doc = {"checked_at_utc": datetime.now(timezone.utc).isoformat(
        timespec="seconds"), "user_agent": UA, "hosts": hosts, "urls": rows}
    (OUT / "robots_policy.json").write_text(json.dumps(doc, indent=2))
    n = sum(1 for v in hosts.values() if v["allowed"])
    print(f"\n{n} of {len(hosts)} hosts permitted. wrote "
          f"{OUT / 'robots_policy.json'}")
    if n == 0:
        sys.exit(1)
