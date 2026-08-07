"""Pinnacle's free guest API, MLB only, with the traps this repo has already hit.

`guest.api.arcadia.pinnacle.com/0.1` needs no key and no headers. Three things
about it are not obvious and each one has already produced a wrong number in
this session:

1. **`/sports/3/matchups` is mostly NOT games.** 148 of 161 entries were
   `type: "special"` -- "odd or even total runs", player props, and so on --
   whose participants are named "Odd"/"Even" and aligned `neutral`. Only
   `type == "matchup"` with `home`/`away` alignment is a game.

2. **A special carries its real game inside `parent`.** Games that the
   top-level list has dropped are still reachable that way, so the index is
   built from top-level matchups *and* embedded parents.

3. **Teams play each other three days running.** Joining Kalshi to Pinnacle on
   the club pair alone matches Tuesday's game to Thursday's price. That is not
   a hypothetical: the first run of `target_choice.py` reported an 80%
   qualifying rate and a 57c edge purely from it. The join here requires the
   start times to agree, and reports how many candidates it threw away.

Also read here and used by the brief: `participants[].pitcher` is Pinnacle's
listed starter, which is how a "listed pitchers" market knows to void.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://guest.api.arcadia.pinnacle.com/0.1"
UA = {"User-Agent": "trading-research/1.0 (personal research)"}
SPORT_BASEBALL = 3


CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache_pin"
CACHE_TTL_S = 240          # the recorder polls at 600 s; this is well inside it


def _g(url, tries=4, ttl_s=CACHE_TTL_S):
    """Cached GET. Pinnacle 401s under load and that must not kill a brief.

    The guest API returns **HTTP 401** intermittently -- not a credential
    problem, a rate limit wearing a misleading status code. `ask.py
    --datasources` already records the sibling trap ("the /0.1/sports INDEX
    returns 401, probing that first makes a live API look dead"). Two
    consequences, both deliberate:
      * a short on-disk cache, because bot-hunt's recorder is polling the same
        host every 600 s from this machine and the two should not compete;
      * on final failure this raises, and EVERY caller in this project treats
        the Pinnacle reference as OPTIONAL. A brief with no sharp reference is
        a brief that says so, not a crash.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    # NOTE: `hash()` on a str is SALTED PER PROCESS (PYTHONHASHSEED), so a
    # cache keyed on it never hits across runs -- it silently degrades to no
    # cache at all while looking like one. The first version of this did
    # exactly that and a second brief build cost the same 6 minutes as the
    # first. hashlib is stable across processes and machines.
    f = CACHE_DIR / (hashlib.sha1(url.encode("utf-8")).hexdigest()[:20] + ".json")
    if ttl_s > 0 and f.exists() and (time.time() - f.stat().st_mtime) < ttl_s:
        try:
            return json.loads(f.read_text())
        except json.JSONDecodeError:
            pass
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.load(r)
            if ttl_s > 0:
                f.write_text(json.dumps(d))
            return d
        except Exception as e:                     # noqa: BLE001
            last = e
            if i < tries - 1:
                time.sleep(3 * (2 ** i))
    # last resort: a stale cache beats no reference at all, and the staleness
    # is visible because every consumer records `pinnacle_fetched_at`.
    if f.exists():
        try:
            return json.loads(f.read_text())
        except json.JSONDecodeError:
            pass
    raise RuntimeError(f"pinnacle unavailable: {url}: {last}")


def _iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def _game_from(m):
    """A game record, or None if this entry is not a game."""
    parts = m.get("participants") or []
    home = away = None
    hp = ap = None
    for p in parts:
        if p.get("alignment") == "home":
            home, hp = p.get("name"), p.get("pitcher")
        elif p.get("alignment") == "away":
            away, ap = p.get("name"), p.get("pitcher")
    if not home or not away:
        return None
    return {
        "id": m.get("id"),
        "home": home, "away": away,
        "home_pitcher": hp, "away_pitcher": ap,
        "starts": _iso(m.get("startTime")),
        "starts_raw": m.get("startTime"),
        "is_live": bool(m.get("isLive")),
        "participant_names": {p.get("id"): p.get("name") for p in parts},
        "participant_alignment": {p.get("id"): p.get("alignment")
                                  for p in parts},
    }


def games(league="MLB"):
    """id -> game. Top-level matchups plus the parents embedded in specials."""
    raw = _g(f"{BASE}/sports/{SPORT_BASEBALL}/matchups")
    out = {}
    for m in raw:
        lg = (m.get("league") or {}).get("name")
        if league and lg != league:
            continue
        if m.get("type") == "matchup" and not m.get("special"):
            gme = _game_from(m)
            if gme:
                out[gme["id"]] = gme
        par = m.get("parent")
        if par:
            gme = _game_from(par)
            if gme and gme["id"] not in out:
                # a parent carries no startTime of its own; inherit the
                # special's, which is the same game clock
                gme["starts"] = gme["starts"] or _iso(m.get("startTime"))
                gme["starts_raw"] = gme["starts_raw"] or m.get("startTime")
                out[gme["id"]] = gme
    return _dedupe(out)


def _dedupe(idx):
    """One record per (away, home, start).

    A game reachable both as a top-level matchup and as some special's parent
    appears twice under two ids. Keeping both would double-count every joined
    game and quietly halve every per-game denominator.
    """
    best = {}
    for g in idx.values():
        key = (g["away"], g["home"],
               g["starts"].isoformat() if g["starts"] else None)
        cur = best.get(key)
        if cur is None:
            best[key] = g
        else:
            # prefer the id that the markets endpoint actually keys on; that is
            # decided by the caller, so keep both ids on the surviving record
            cur.setdefault("alt_ids", []).append(g["id"])
    return {g["id"]: g for g in best.values()}


def straight_markets():
    """matchupId -> {'moneyline': mkt, 'totals': [...], 'spreads': [...]}.

    Full game only (`period == 0`). Alternate lines are kept and flagged,
    because Kalshi's total ladder runs 1.5 to 13.5 and only one rung is
    Pinnacle's main line.
    """
    raw = _g(f"{BASE}/sports/{SPORT_BASEBALL}/markets/straight")
    out = {}
    for mk in raw:
        if mk.get("period") != 0:
            continue
        if (mk.get("status") or "open") != "open":
            continue
        mid = mk.get("matchupId")
        rec = out.setdefault(mid, {"moneyline": None, "totals": [],
                                   "spreads": [], "team_totals": []})
        lim = max((l.get("amount", 0) for l in (mk.get("limits") or [])),
                  default=0)
        entry = {"prices": mk.get("prices") or [], "limit": lim,
                 "cutoff": mk.get("cutoffAt"),
                 "is_alternate": bool(mk.get("isAlternate")),
                 "key": mk.get("key")}
        t = mk.get("type")
        if t == "moneyline":
            if not entry["is_alternate"]:
                rec["moneyline"] = entry
        elif t == "total":
            rec["totals"].append(entry)
        elif t == "spread":
            rec["spreads"].append(entry)
        elif t == "team_total":
            rec["team_totals"].append(entry)
    return out


def markets_for(game, mkts):
    """The straight markets for a game, trying every id it is known by."""
    for i in [game["id"]] + list(game.get("alt_ids") or []):
        if i in mkts:
            return mkts[i]
    return {}


def american_to_prob(price):
    price = float(price)
    if price < 0:
        return (-price) / ((-price) + 100.0)
    return 100.0 / (price + 100.0)


def devig(p_a, p_b, method="multiplicative"):
    """Return (fair_a, fair_b, overround). Overround is in probability units."""
    tot = p_a + p_b
    if tot <= 0:
        return None, None, None
    if method == "additive":
        adj = (tot - 1.0) / 2.0
        return p_a - adj, p_b - adj, tot - 1.0
    if method == "power":
        # solve p^k summing to 1; cheap bisection, no scipy
        lo, hi = 0.5, 2.0
        for _ in range(60):
            k = (lo + hi) / 2
            s = p_a ** k + p_b ** k
            if s > 1:
                lo = k
            else:
                hi = k
        k = (lo + hi) / 2
        return p_a ** k, p_b ** k, tot - 1.0
    return p_a / tot, p_b / tot, tot - 1.0


def over_under(entry):
    """(over_price, under_price, points) from a total market, by DESIGNATION.

    Never by list position. The designation field is present on this feed; if
    it ever is not, this returns None rather than guessing, because guessing
    the side of a totals market inverts the sign of every edge computed from
    it.
    """
    over = under = None
    pts = None
    for pr in entry["prices"]:
        d = str(pr.get("designation", "")).lower()
        if d == "over":
            over, pts = pr, pr.get("points")
        elif d == "under":
            under = pr
    if over is None or under is None:
        return None
    return over.get("price"), under.get("price"), pts


if __name__ == "__main__":
    gs = games()
    mk = straight_markets()
    now = datetime.now(timezone.utc)
    print(f"MLB games indexed: {len(gs)}")
    upcoming = [g for g in gs.values() if g["starts"] and g["starts"] > now]
    print(f"  not yet started: {len(upcoming)}")
    withm = [g for g in gs.values() if g["id"] in mk]
    print(f"  with a full-game market: {len(withm)}")
    for g in sorted(gs.values(), key=lambda x: (x["starts"] or now))[:14]:
        m = markets_for(g, mk)
        tt = m.get("totals") or []
        main = [t for t in tt if not t["is_alternate"]]
        print(f"  {g['starts_raw']}  {g['away']} @ {g['home']}  "
              f"ml={'Y' if m.get('moneyline') else '-'} "
              f"totals={len(tt)} (main {len(main)}) "
              f"SP={g['away_pitcher']}/{g['home_pitcher']}")
