"""WHY the replay disagrees with the live bots, by cause. Mailbox 023 job 2.

A fidelity percentage is not actionable. This compares the replay's INPUTS
against the inputs the live bot recorded in its own decision log, game by game,
and attributes each disagreement to the field that differed.

    python src/drift.py
"""
from __future__ import annotations

import collections
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import engine as E                                     # noqa: E402
import replay as R                                     # noqa: E402
import statsapi as S                                   # noqa: E402


def live_early(con):
    """What the live `early` actually saw, per game: records, ERAs, price."""
    out = {}
    for r in con.execute(
            "SELECT game_key, ts_utc, kind, ticker, stated_prob_c, "
            "quoted_price_c, reasoning_json FROM decisions "
            "WHERE mentality='early' ORDER BY ts_utc"):
        d = json.loads(r["reasoning_json"] or "{}")
        det = d.get("reasoning") or d.get("detail") or d
        rec = {"ts": r["ts_utc"], "kind": r["kind"], "ticker": r["ticker"],
               "away_record": det.get("away_record"),
               "home_record": det.get("home_record"),
               "fair_home_c": det.get("fair_home_c"),
               "price_c": det.get("price_c") or r["quoted_price_c"],
               "starters": det.get("starters") or {}}
        if rec["away_record"]:
            out.setdefault(r["game_key"], rec)
    return out


if __name__ == "__main__":
    con = E.connect()
    cache = R.cache()
    recs = R.records_as_of(cache)
    live = live_early(con)
    print(f"live `early` decisions with full inputs recorded: {len(live)} games\n")

    cause = collections.Counter()
    examples = collections.defaultdict(list)
    checked = 0
    for gk, L in live.items():
        day, teams = gk.split(":")
        away, home = teams.split("@")
        g = cache.execute(
            "SELECT * FROM game WHERE game_date=? AND away_code=? AND "
            "home_code=?", (day, away, home)).fetchone()
        if not g:
            cause["game not in the replay cache at all"] += 1
            continue
        checked += 1
        # what the replay would have used, at the live bot's own timestamp
        as_of = datetime.fromisoformat(L["ts"])
        dd = as_of.date().isoformat()
        r2 = recs.get(dd) or {}
        ma = r2.get(g["away_id"])
        mh = r2.get(g["home_id"])
        if ma is None or mh is None:
            cause["no point-in-time record for that date"] += 1
            continue
        if list(ma) != L["away_record"] or list(mh) != L["home_record"]:
            cause["team RECORD differs"] += 1
            if len(examples["team RECORD differs"]) < 4:
                examples["team RECORD differs"].append(
                    f"{gk}: live {L['away_record']}/{L['home_record']}, "
                    f"replay {list(ma)}/{list(mh)}")
            continue
        # records match -- check the starter ERA the live bot used
        diff = False
        for side, pid in (("away", g["away_prob_id"]),
                          ("home", g["home_prob_id"])):
            le = ((L["starters"] or {}).get(side) or {}).get("season_era")
            if le is None or not pid:
                continue
            p = R.profile(pid, as_of.astimezone(timezone.utc))
            me = (p or {}).get("season_era")
            if me is not None and abs(float(me) - float(le)) > 0.005:
                diff = True
        if diff:
            cause["starter season ERA differs"] += 1
            continue
        cause["inputs MATCH (any difference is price or timing)"] += 1

    print("WHY the replay and the live bot see different things:")
    for k, v in cause.most_common():
        print(f"  {v:>5}  {k}")
    print()
    for k, ex in examples.items():
        print(f"  examples -- {k}")
        for e in ex:
            print(f"    {e}")
    con.close()
