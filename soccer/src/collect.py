"""TASK 1 collector: Kalshi settled soccer markets + ESPN matches, joined.

Writes:
  data/kalshi_soccer_markets.jsonl   every settled/open market in the 6 series
  data/espn_events.jsonl             every ESPN match in the window, 5 leagues
  data/join.json                     the fixture-level join, with FAILURES kept
  reports/join_report.txt

The join is {franchise pair} + date, with a +/-1 day tolerance because Kalshi's
ticker carries a LOCAL match date while ESPN stamps UTC -- a 19:00 local kickoff
in Mexico is the next calendar day in UTC. The matched offset is recorded per
fixture rather than assumed.

Read-only, paced, public endpoints.
"""
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import requests

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "market-selection", "src"))
import kalshi_api as K  # noqa: E402
import teammatch as TM  # noqa: E402

ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
UA = {"User-Agent": "Mozilla/5.0 (soccer-research/1.0)"}
SITE = "https://site.api.espn.com/apis/site/v2/sports/soccer"

# Kalshi series -> ESPN league code. MLS included; Copa do Brasil is a cup so
# its matches appear under bra.copa_do_brazil, with bra.1 as a fallback.
LEAGUES = {
    "KXLIGAMXGAME": ["mex.1"],
    "KXLIGAMXTOTAL": ["mex.1"],
    "KXARGPREMDIVGAME": ["arg.1"],
    "KXDIMAYORGAME": ["col.1"],
    "KXCOPADOBRASILGAME": ["bra.copa_do_brazil", "bra.1"],
    "KXMLSGAME": ["usa.1"],
}
MONTHS = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT",
     "NOV", "DEC"])}


def espn_get(path, params, tries=4):
    for i in range(tries):
        try:
            r = requests.get(SITE + path, params=params, headers=UA, timeout=45)
        except requests.RequestException:
            time.sleep(1.5 * (i + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2.5 * (i + 1))
            continue
        time.sleep(0.2)
        return r
    return None


def kalshi_markets():
    out = []
    for s in LEAGUES:
        for status in ("settled", "open"):
            r = K.get("/markets", {"series_ticker": s, "status": status,
                                   "limit": 1000})
            ms = r.json().get("markets", []) if r and r.status_code == 200 else []
            for m in ms:
                m["_series"] = s
                m["_status_q"] = status
                out.append(m)
            print(f"  {s:22s} {status:8s} {len(ms)}", flush=True)
    return out


def kalshi_fixtures(markets):
    """Group markets into fixtures keyed by (pair, local date)."""
    by_event = defaultdict(list)
    for m in markets:
        by_event[m.get("event_ticker")].append(m)
    fx = []
    unparsed = []
    for ev, ms in by_event.items():
        m0 = ms[0]
        teams = TM.teams_from_kalshi_title(m0.get("title"))
        mm = re.match(r"[A-Z0-9]+-(\d\d)([A-Z]{3})(\d\d)", ev or "")
        if not teams or not mm:
            unparsed.append({"event": ev, "title": m0.get("title")})
            continue
        yy, mon, dd = mm.groups()
        d = f"20{yy}-{MONTHS[mon]:02d}-{int(dd):02d}"
        fx.append({
            "event_ticker": ev, "series": m0["_series"],
            "kalshi_date": d,
            "team_a": teams[0], "team_b": teams[1],
            "pair": list(TM.pair_key(*teams)),
            "n_markets": len(ms),
            "markets": [{"ticker": m["ticker"],
                         "yes_sub": m.get("yes_sub_title"),
                         "result": m.get("result"),
                         "status": m.get("status"),
                         "open_time": m.get("open_time"),
                         "close_time": m.get("close_time")} for m in ms],
        })
    return fx, unparsed


def espn_events(days_back=80):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)
    out = []
    codes = sorted({c for v in LEAGUES.values() for c in v})
    for code in codes:
        got = 0
        # ESPN caps a scoreboard range; walk it in 10-day chunks
        # 7-day chunks. A 10-day range returned only 85 MLS matches over 80
        # days where ~170 were expected, so ESPN caps a scoreboard response
        # regardless of `limit`. Smaller windows, more calls.
        d = start
        while d < end + timedelta(days=7):
            d2 = d + timedelta(days=7)
            r = espn_get(f"/{code}/scoreboard",
                         {"dates": f"{d:%Y%m%d}-{d2:%Y%m%d}", "limit": 400})
            if r is not None and r.status_code == 200:
                for e in r.json().get("events", []):
                    e["_league"] = code
                    out.append(e)
                    got += 1
            d = d2 - timedelta(days=1)      # overlap so no boundary day is lost
        print(f"  {code:22s} {got} events", flush=True)
    # dedupe by id
    seen, uniq = set(), []
    for e in out:
        if e["id"] in seen:
            continue
        seen.add(e["id"])
        uniq.append(e)
    return uniq


def main():
    os.makedirs(DATA, exist_ok=True)
    print("=== Kalshi soccer markets ===")
    mk = kalshi_markets()
    with open(os.path.join(DATA, "kalshi_soccer_markets.jsonl"), "w",
              encoding="utf-8") as fh:
        for m in mk:
            fh.write(json.dumps(m) + "\n")
    fx, unparsed = kalshi_fixtures(mk)
    print(f"  {len(mk)} markets -> {len(fx)} fixtures "
          f"({len(unparsed)} unparsed titles)")
    for u in unparsed[:5]:
        print(f"    unparsed: {u}")

    print("\n=== ESPN events ===")
    evs = espn_events()
    with open(os.path.join(DATA, "espn_events.jsonl"), "w",
              encoding="utf-8") as fh:
        for e in evs:
            fh.write(json.dumps(e) + "\n")
    print(f"  {len(evs)} distinct ESPN matches")

    # Per-league ESPN roster: a CLOSED set of 20-30 clubs to resolve against.
    roster = defaultdict(set)
    for e in evs:
        h, a = TM.teams_from_espn_event(e)
        if h:
            roster[e["_league"]].add(h)
        if a:
            roster[e["_league"]].add(a)
    roster = {k: sorted(v) for k, v in roster.items()}

    # index ESPN by (pair of ESPN names, utc date)
    idx = defaultdict(list)
    for e in evs:
        h, a = TM.teams_from_espn_event(e)
        if not h or not a:
            continue
        d = (e.get("date") or "")[:10]
        idx[(TM.pair_key(h, a), d)].append(e)

    matched, failed = [], []
    offsets = defaultdict(int)
    resolutions = {}
    for f in fx:
        # resolve Kalshi club names onto the ESPN roster for this league
        lgs = LEAGUES[f["series"]]
        ra = rb = None
        for lg in lgs:
            rs = roster.get(lg) or []
            ra_, sa, wa = TM.resolve_against_roster(f["team_a"], rs)
            rb_, sb, wb = TM.resolve_against_roster(f["team_b"], rs)
            if ra_ and rb_:
                ra, rb = ra_, rb_
                resolutions[f["team_a"]] = (lg, ra_, wa)
                resolutions[f["team_b"]] = (lg, rb_, wb)
                break
            f["_resolve_why"] = f"{f['team_a']}->{wa} ; {f['team_b']}->{wb}"
        if ra and rb:
            f["espn_team_a"], f["espn_team_b"] = ra, rb
            pk = TM.pair_key(ra, rb)
        else:
            pk = tuple(f["pair"])
        base = datetime.fromisoformat(f["kalshi_date"])
        hit = None
        for off in (0, 1, -1, 2):
            d = (base + timedelta(days=off)).strftime("%Y-%m-%d")
            cand = idx.get((pk, d))
            if cand:
                hit = (cand[0], off)
                break
        if hit:
            e, off = hit
            offsets[off] += 1
            h, a = TM.teams_from_espn_event(e)
            st = ((e.get("status") or {}).get("type") or {})
            f.update({"espn_id": e["id"], "espn_league": e["_league"],
                      "espn_date": e.get("date"), "espn_name": e.get("name"),
                      "espn_home": h, "espn_away": a,
                      "date_offset_days": off,
                      "espn_completed": st.get("completed"),
                      "espn_status": st.get("name")})
            matched.append(f)
        else:
            failed.append(f)

    out = {"matched": matched, "failed": failed, "unparsed": unparsed,
           "offsets": dict(offsets),
           "roster": roster,
           "resolutions": {k: list(v) for k, v in resolutions.items()}}
    with open(os.path.join(DATA, "join.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)

    tot = len(fx)
    print(f"\n=== JOIN ===")
    print(f"  Kalshi fixtures      {tot}")
    print(f"  matched to ESPN      {len(matched)}  ({100*len(matched)/max(tot,1):.1f}%)")
    print(f"  failed to match      {len(failed)}")
    print(f"  date offsets used    {dict(offsets)}")
    per = defaultdict(lambda: [0, 0])
    for f in matched:
        per[f["series"]][0] += 1
    for f in failed:
        per[f["series"]][1] += 1
    print(f"\n  {'series':24s} {'matched':>8s} {'failed':>7s} {'rate':>7s}")
    for s, (m, fl) in sorted(per.items()):
        print(f"  {s:24s} {m:8d} {fl:7d} {100*m/max(m+fl,1):6.1f}%")
    print(f"\n  FAILURES (first 30) -- inspect, do not assume:")
    for f in failed[:30]:
        print(f"    {f['series'][:18]:18s} {f['kalshi_date']} "
              f"{f['team_a'][:20]:20s} vs {f['team_b'][:20]:20s} "
              f"| {str(f.get('_resolve_why'))[:70]}")
    print(f"\nwrote data/join.json")


if __name__ == "__main__":
    main()
