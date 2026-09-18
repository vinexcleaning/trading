"""IS HE RIGHT ABOUT WHICH SPORTS ARE PREDICTABLE? A measurement, not an opinion.

Mailbox 015 recorded what he knows about sport, and it is the one input this
project cannot generate for itself:

    "MLB bro there is a lot of money to be made in MLB"
    "football games too... maybe not the NFL but the college games" are
        "pretty fucking predictable"
    "the one thing that I think are very risky are soccer games I do not trust
        them shits at all"
    "basketball is probably predictable as fuck too because it's just high
        scoring ass games... one moment of brilliance doesn't change the whole
        outcome"

**The mechanism he describes is real and it is testable.** A sport where one
event swings the whole result is a sport whose outcome is mostly luck, and luck
cannot be forecast by anybody - not by us, not by the market. A high-scoring
sport lets the better team's advantage accumulate, so the result concentrates
on the better team.

TWO MEASURES, AND THE SECOND ONE IS THE HONEST TEST

1. **How far from even money the market prices a typical game**, 30 minutes
   before it starts. If one event can swing a soccer match, nobody can price a
   soccer match far from even, no matter how mismatched the teams. This needs
   no outcomes at all - it is the market's own statement about how knowable the
   sport is.

2. **How often the favourite actually wins.** The check on measure 1: a market
   that prices confidently and is then wrong is not forecasting, it is
   guessing loudly.

⚠ WHAT THIS CANNOT DO, STATED BEFORE THE NUMBERS.
**It does not measure whether WE can beat the price.** A sport can be highly
forecastable and completely unprofitable, because the forecast is already in
the price - which is the base case here and has been for every family this
project has screened. What it measures is where the *outcome* carries signal
rather than noise, which is where any edge would have to live if one exists.

⚠ AND THE CONFOUND, NAMED UP FRONT. A sport whose fixtures are lopsided (a
cup competition with minnows) prices far from even money for a reason that has
nothing to do with scoring. So the two measures are reported side by side and
neither is quoted alone.

    py -3 strategy-factory/src/forecastable.py
"""
from __future__ import annotations

import re
import sqlite3
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Head-to-head "who wins" families only. A totals or props market has no
# favourite in this sense, so mixing them in would measure something else.
# ⚠ SERIES ARE DISCOVERED FROM THE TAPE, NOT TYPED IN. The first version of
# this file listed 18 series by hand and only THREE of them existed - the
# exchange's real head-to-head families are things like KXTTELITEMATCH (table
# tennis, 12,810 markets) and KXITFMATCH (tennis, 5,996) that nobody here had
# heard of. A hand-typed list would have reported "we looked at every sport"
# while looking at a sixth of one.
SPORT_OF = [
    ("MLB", "baseball"), ("NPB", "baseball"), ("KBO", "baseball"),
    ("NFL", "american football"), ("NCAAF", "american football (college)"),
    ("NBA", "basketball"), ("WNBA", "basketball"), ("NCAAB", "basketball (college)"),
    ("NCAAM", "basketball (college)"), ("NCAAW", "basketball (college)"),
    ("TT", "table tennis"), ("DARTS", "darts"), ("T20", "cricket"),
    ("ATP", "tennis"), ("WTA", "tennis"), ("ITF", "tennis"),
    ("UFC", "combat sports"), ("BOXING", "combat sports"),
    ("NHL", "ice hockey"),
    ("LOL", "esports"), ("CS2", "esports"), ("CSGO", "esports"),
    ("VALORANT", "esports"), ("DOTA", "esports"), ("R6", "esports"),
    ("SOCCER", "soccer"), ("EPL", "soccer"), ("UCL", "soccer"),
    ("MLS", "soccer"), ("FACUP", "soccer"), ("EFL", "soccer"),
    ("SERIE", "soccer"), ("LALIGA", "soccer"), ("BUND", "soccer"),
    ("BRASILEIRO", "soccer"), ("ARG", "soccer"), ("DIMAYOR", "soccer"),
    ("CLUBF", "soccer"), ("ENGNL", "soccer"), ("USL", "soccer"),
    ("VENFUT", "soccer"), ("SVKCUP", "soccer"), ("ETTAN", "soccer"),
    ("TACAPORT", "soccer"),
]


def sport_of(series):
    body = series[2:] if series.startswith("KX") else series
    for key, name in SPORT_OF:
        if body.startswith(key):
            return name
    return None


def discover(con, min_markets=60):
    out = {}
    for s, n in con.execute(
            "select series, count(*) from w_names "
            "where series like '%GAME' or series like '%MATCH' "
            "   or series like '%FIGHT' "
            "group by series having count(*) >= ?", (min_markets,)):
        name = sport_of(s)
        if name:
            out[s] = name
    return out


MONTHS = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
     "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}
# ⚠ TWO TICKER SHAPES, AND ASSUMING ONE OF THEM LOSES MOST OF THE EXCHANGE.
# Baseball and table tennis carry a time - `26SEP042005`. Soccer, tennis,
# college football and most others carry only a DATE - `26AUG30STLDAL`. The
# first version of this file required the time and silently dropped every
# date-only sport, which is every soccer competition on the board and the exact
# sport he asked about.
TICK_DT = re.compile(r"^[A-Z0-9]+-(\d{2})([A-Z]{3})(\d{2})(\d{4})")
TICK_D = re.compile(r"^[A-Z0-9]+-(\d{2})([A-Z]{3})(\d{2})")


def reference_moment(ticker):
    """A moment that is BEFORE the event for every sport, chosen uniformly.

    Where the ticker carries a start time, it is 30 minutes before that. Where
    it carries only a date - most of the exchange - it is midnight UTC at the
    start of the event's own day, which is before first whistle in every time
    zone a fixture is played in. Slightly early, but early by the same amount
    for every sport, which is what makes the comparison fair.
    """
    m = TICK_DT.match(ticker or "")
    if m:
        yy, mon, dd, hhmm = m.groups()
        if mon in MONTHS:
            try:
                return datetime(2000 + int(yy), MONTHS[mon], int(dd),
                                int(hhmm[:2]), int(hhmm[2:]),
                                tzinfo=timezone.utc) - timedelta(minutes=30)
            except ValueError:
                pass
    m = TICK_D.match(ticker or "")
    if not m:
        return None
    yy, mon, dd = m.groups()
    if mon not in MONTHS:
        return None
    try:
        return datetime(2000 + int(yy), MONTHS[mon], int(dd),
                        tzinfo=timezone.utc)
    except ValueError:
        return None


def main():
    top = sqlite3.connect(
        "file:%s?mode=ro" % (ROOT / "data" / "wide_top.db"), uri=True)
    top.execute("attach database ? as s",
                (str(ROOT / "data" / "settled.db"),))

    SPORTS = discover(top)
    results = {}
    for tk, res in top.execute(
            "select ticker, result from s.settled where result in ('yes','no')"):
        results[tk] = res

    print("HOW KNOWABLE IS EACH SPORT, from this project's own tape")
    print("Prices are the real ask 30 minutes before the event starts, "
          "18 Aug - 18 Sep 2026.")
    print()
    print("%-28s %7s %10s %12s %12s"
          % ("sport", "games", "confident", "favourite won", "quoted"))
    print("%-28s %7s %10s %12s %12s"
          % ("", "", "(from 50)", "", ""))

    agg = defaultdict(lambda: {"dists": [], "wins": [], "ev": 0, "q": 0,
                               "series": set()})
    out = []
    for series, name in SPORTS.items():
        # One row per EVENT, not per market: a two-sided game lists both teams
        # and counting both would double every sport.
        per_event = defaultdict(list)
        for tk, ev in top.execute(
                "select ticker, event_ticker from w_names where series=?",
                (series,)):
            if ev:
                per_event[ev].append(tk)
        if not per_event:
            continue

        dists, wins, n_quoted, n_events = [], [], 0, 0
        for ev, tickers in per_event.items():
            start = reference_moment(tickers[0])
            if start is None:
                continue
            n_events += 1
            when = start.strftime("%Y-%m-%dT%H:%M:%SZ")
            best = None
            for tk in tickers:
                row = top.execute(
                    "select yes_ask_c from w_top where series=? and ticker=? "
                    "and ts_utc<=? and yes_ask_c is not null "
                    "order by ts_utc desc limit 1", (series, tk, when)).fetchone()
                if row is None:
                    continue
                # The favourite is the dearest side to buy.
                if best is None or row[0] > best[1]:
                    best = (tk, row[0])
            if best is None:
                continue
            n_quoted += 1
            # ⚠ AN EVEN SPLIT IS NOT ALWAYS 50 CENTS. Soccer lists a TIE, so a
            # three-way event is even at 33c, not 50c. Measuring soccer's
            # distance from 50 would make the sport look MORE confidently
            # priced the more evenly matched it is - backwards, and on the one
            # sport he specifically asked about.
            even = 100.0 / max(len(tickers), 1)
            dists.append(best[1] - even)
            if best[0] in results:
                wins.append(1 if results[best[0]] == "yes" else 0)

        a = agg[name]
        a["dists"] += dists
        a["wins"] += wins
        a["ev"] += n_events
        a["q"] += n_quoted
        a["series"].add(series)

    for name, a in agg.items():
        if a["q"] < 40:
            continue
        wr = (100.0 * sum(a["wins"]) / len(a["wins"])) if len(a["wins"]) >= 30             else None
        out.append((statistics.median(a["dists"]), name, a["ev"], a["q"], wr,
                    len(a["wins"]), len(a["series"])))

    for conf, name, n_events, n_quoted, wr, nw, nser in sorted(out,
                                                              reverse=True):
        print("%-28s %7d %9.1fc %12s %11.0f%%"
              % (name, n_quoted, conf,
                 ("%.0f in 100 (%d)" % (wr, nw)) if wr is not None
                 else "no outcomes yet",
                 100.0 * n_quoted / max(n_events, 1)))

    print()
    print("'confident' = how far from an even-money 50 cents the favourite is "
          "priced, in cents.")
    print("  Bigger means the market thinks it knows who wins. 20c means the "
          "favourite is")
    print("  priced at 70 cents - about 7 wins in every 10.")
    print("'favourite won' = how often that favourite actually won, out of 100.")
    print("'quoted' = share of that sport's games with a real price 30 minutes "
          "out. A low")
    print("  number means the sport is barely tradeable whatever its "
          "forecastability.")


if __name__ == "__main__":
    main()
