"""Join Pinnacle esports to Kalshi esports on TEAM NAMES, and measure the gap.

This is the shortlist's #1 mechanism and nobody in this repo has ever tested it:
de-vig a sharp sportsbook to a fair probability, compare it to the prediction
market's executable price, and see whether the difference clears the cost.

WHY THE FIRST JOIN FAILED, and it is worth recording. Matching on the Kalshi
TICKER matched **3 of 218 events**: Kalshi's outcome codes are 2-4 letter
abbreviations (`REDA`, `ODK`, `WAVE`) and Pinnacle uses full names. The full
names live in the market's `yes_sub_title`, which **the recorder does not
store** — a real gap in `record.py`, worked around here by joining through the
market universe already pulled into `kalshi_soccer.db`.

DE-VIG. Three methods, because the corpora are explicit the choice is not
cosmetic — the one author with a reconciled live P&L reported his Shin
implementation *"ran hot on favourites"*:
  multiplicative  divide by the overround; biases toward favourites
  power           solve k with sum(p_i^k) = 1; usually the best empirical fit
  worst-case      the least favourable of the two; the only conservative choice
All three are computed and reported side by side. None is picked for us.

NOTHING HERE IS AN EDGE CLAIM. It measures the DISTRIBUTION of the gap and the
join's own reliability. A gap is only an edge if the pair is genuinely the same
contract, and the corpora are unanimous that resolution-equivalence — not name
similarity — is what decides that.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
REC = ROOT / "data" / "record.db"
MKT = ROOT / "data" / "kalshi_soccer.db"
REP = ROOT / "reports"

STOP = re.compile(r"\b(team|esports?|gaming|club|the|gg|e-?sports|kills|maps?|"
                  r"handicap|total)\b")


def norm(s):
    if not s:
        return ""
    s = STOP.sub(" ", s.lower())
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(s.split())


def american_to_prob(american):
    a = float(american)
    return (-a) / ((-a) + 100.0) if a < 0 else 100.0 / (a + 100.0)


def devig(p_home, p_away):
    """Returns {method: (fair_home, fair_away)}."""
    s = p_home + p_away
    out = {}
    if s <= 0:
        return out
    out["multiplicative"] = (p_home / s, p_away / s)
    lo, hi = 0.2, 5.0
    for _ in range(60):
        k = (lo + hi) / 2
        if p_home ** k + p_away ** k > 1:
            lo = k
        else:
            hi = k
    k = (lo + hi) / 2
    tot = p_home ** k + p_away ** k
    out["power"] = (p_home ** k / tot, p_away ** k / tot)
    # worst case for a BUYER of home: the highest fair prob any method gives
    # the away side, i.e. the lowest for home.
    out["worst_case"] = (min(v[0] for v in out.values()),
                         min(v[1] for v in out.values()))
    return out


def main():
    REP.mkdir(parents=True, exist_ok=True)
    mk = sqlite3.connect(f"file:{MKT.as_posix()}?mode=ro", uri=True, timeout=180)
    # ticker -> the full outcome name Kalshi shows
    names = {}
    for tk, sub, title in mk.execute(
            "select ticker, yes_sub_title, title from markets "
            "where series in ('KXCS2GAME','KXLOLGAME','KXVALORANTGAME')"):
        if sub:
            names[tk] = (sub, title)
    mk.close()
    print(f"Kalshi esports tickers with a full outcome name: {len(names):,}")

    rec = sqlite3.connect(f"file:{REC.as_posix()}?mode=ro", uri=True, timeout=180)

    # --- Pinnacle side: moneyline (type='moneyline', period 0) per matchup ---
    pin = defaultdict(dict)     # matchup_id -> {ts: {designation: price}}
    meta = {}
    for mid, lg, home, away, starts in rec.execute(
            "select matchup_id, max(league), max(home), max(away), "
            "max(starts_utc) from pin_matchup where sport='esports' "
            "group by matchup_id"):
        if home and away:
            meta[mid] = {"league": lg, "home": home, "away": away,
                         "starts": starts}
    print(f"Pinnacle esports matchups with both names: {len(meta):,}")

    for mid, ts, desig, price in rec.execute(
            "select matchup_id, ts_utc, designation, price_american "
            "from pin_market where sport='esports' and market_type='moneyline' "
            "and period=0 and designation is not null"):
        if mid in meta:
            pin[mid].setdefault(ts, {})[desig] = price
    print(f"  with priced moneylines: {len(pin):,}")

    # --- the join, on normalised team names ---
    pairs = []
    kal_by_event = defaultdict(list)
    for tk in names:
        kal_by_event[tk.rsplit("-", 1)[0]].append(tk)

    # THE PRECISION FILTER. Name similarity is a recall net; this is what
    # decides whether a pair is the same contract.
    #
    # DEFECT FOUND BY HAND-AUDITING THE MATCHES. v1 matched the Kalshi CS2
    # market `KXCS2GAME-26JUN110730FUTVIT` ("FUT Esports" / "Vitality") to the
    # Pinnacle matchup "Bigetron by Vitality vs FUT" — which is in
    # **Mobile Legends**, a different game entirely. The join never looked at
    # the league. This is precisely the failure the corpora describe:
    # *"a 50c+ cross-venue gap is almost always two different contracts"* and
    # *"the phantoms have HIGH token overlap, not low."*
    GAME = {"KXCS2GAME": ("cs2", "counter-strike", "counter strike"),
            "KXLOLGAME": ("league of legends", "lol"),
            "KXVALORANTGAME": ("valorant",)}

    def game_ok(event_ticker, league):
        series = event_ticker.split("-")[0]
        want = GAME.get(series)
        if not want or not league:
            return False
        lg = league.lower()
        return any(w in lg for w in want)

    rejected_game = 0
    for ev, tks in kal_by_event.items():
        if len(tks) != 2:
            continue
        outs = {tk: norm(names[tk][0]) for tk in tks}
        for mid, m in meta.items():
            if not game_ok(ev, m.get("league")):
                rejected_game += 1
                continue
            h, a = norm(m["home"]), norm(m["away"])
            if not h or not a:
                continue
            match = {}
            for tk, o in outs.items():
                if not o:
                    continue
                if o == h or (len(o) > 3 and (o in h or h in o)):
                    match[tk] = "home"
                elif o == a or (len(o) > 3 and (o in a or a in o)):
                    match[tk] = "away"
            if len(match) == 2 and set(match.values()) == {"home", "away"}:
                # ROSTER-SUFFIX AGREEMENT. An organisation fields several
                # teams; "CYBERSHOKE Esports" and "CYBERSHOKE Prospects" are
                # different contracts. The test is not whether a suffix is
                # PRESENT — both sides legitimately say "Academy" when the
                # match really is between academies — but whether the two
                # venues AGREE on it.
                SUF = ("academy", "junior", "prospect", "youth", "female",
                       "women")
                bad = False
                for tk, sidev in match.items():
                    kn = names[tk][0].lower()
                    pn = (m["home"] if sidev == "home" else m["away"]).lower()
                    if {s for s in SUF if s in kn} != {s for s in SUF if s in pn}:
                        bad = True
                if bad:
                    continue
                pairs.append({"event": ev, "matchup": mid,
                              "map": match, "meta": m,
                              "names": {tk: names[tk][0] for tk in tks}})
                break

    print(f"\n== JOIN on full team names: {len(pairs)} matched events "
          f"(of {len(kal_by_event)} Kalshi events)")
    for p in pairs[:10]:
        ks = " / ".join(f"{v}={p['names'][k]}" for k, v in p["map"].items())
        print(f"   {p['event'][:40]:40} {ks[:44]:44} <-> "
              f"{p['meta']['home'][:18]} vs {p['meta']['away'][:18]}")
    if not pairs:
        print("   nothing matched — stop here rather than force it")
        return

    # --- for each matched pair, compare the closest-in-time quotes ---
    rows = []
    for p in pairs:
        kq = {}
        for tk in p["map"]:
            for ts, yb, ya in rec.execute(
                    "select ts_utc, yes_bid_c, yes_ask_c from k_book "
                    "where ticker=? order by ts_utc", (tk,)):
                if yb is not None and ya is not None:
                    kq.setdefault(tk, []).append((ts, yb, ya))
        if len(kq) < 2:
            continue
        pts = sorted(pin[p["matchup"]])
        for tk, quotes in kq.items():
            side = p["map"][tk]
            for ts, yb, ya in quotes:
                near = min(pts, key=lambda x: abs(
                    datetime.strptime(x, "%Y-%m-%dT%H:%M:%SZ")
                    - datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")),
                    default=None)
                if near is None:
                    continue
                dt = abs((datetime.strptime(near, "%Y-%m-%dT%H:%M:%SZ")
                          - datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")).total_seconds())
                if dt > 900:            # never compare quotes >15 min apart
                    continue
                d = pin[p["matchup"]][near]
                if "home" not in d or "away" not in d:
                    continue
                ph, pa = american_to_prob(d["home"]), american_to_prob(d["away"])
                fv = devig(ph, pa)
                if not fv:
                    continue
                for method, (fh, fa) in fv.items():
                    fair = fh if side == "home" else fa
                    rows.append({
                        "event": p["event"], "ticker": tk, "side": side,
                        "method": method, "ts": ts, "dt_s": dt,
                        "fair_c": 100 * fair,
                        "kalshi_bid": yb, "kalshi_ask": ya,
                        "overround_pp": 100 * (ph + pa - 1),
                        # buying YES lifts the ASK. Never the mid.
                        "edge_buy_c": 100 * fair - ya,
                        "edge_sell_c": yb - 100 * fair,
                    })
    rec.close()
    print(f"\n== {len(rows):,} paired quote observations "
          f"({len({r['event'] for r in rows})} events, "
          f"{len({r['ticker'] for r in rows})} markets)")
    if not rows:
        return

    ov = [r["overround_pp"] for r in rows if r["method"] == "multiplicative"]
    print(f"   Pinnacle overround: median {np.median(ov):.2f}pp  "
          f"p10 {np.percentile(ov,10):.2f}  p90 {np.percentile(ov,90):.2f}")
    print(f"   quote time-alignment: median {np.median([r['dt_s'] for r in rows]):.0f}s")

    print(f"\n   {'devig':16} {'n':>6} {'edge BUY (fair-ask)':>26} "
          f"{'edge SELL (bid-fair)':>26}")
    out = {}
    for m in ("multiplicative", "power", "worst_case"):
        sub = [r for r in rows if r["method"] == m]
        if not sub:
            continue
        eb = np.array([r["edge_buy_c"] for r in sub])
        es = np.array([r["edge_sell_c"] for r in sub])
        print(f"   {m:16} {len(sub):>6} "
              f"med {np.median(eb):+7.2f}c p90 {np.percentile(eb,90):+7.2f}c "
              f"  med {np.median(es):+7.2f}c p90 {np.percentile(es,90):+7.2f}c")
        out[m] = {"n": len(sub), "edge_buy_med": float(np.median(eb)),
                  "edge_buy_p90": float(np.percentile(eb, 90)),
                  "edge_sell_med": float(np.median(es)),
                  "edge_sell_p90": float(np.percentile(es, 90)),
                  "frac_buy_over_2c": float(np.mean(eb > 2.0)),
                  "frac_buy_over_5c": float(np.mean(eb > 5.0))}
        print(f"   {'':16} {'':>6} buy-edge > 2c on "
              f"{100*np.mean(eb>2):.1f}% of observations, "
              f"> 5c on {100*np.mean(eb>5):.1f}%")

    (REP / "crossvenue_join.json").write_text(
        json.dumps({"pairs": len(pairs), "observations": len(rows),
                    "methods": out,
                    "examples": [{k: v for k, v in p.items() if k != "map"}
                                 for p in pairs[:20]]},
                   indent=1, default=str), encoding="utf-8")
    print("\nwrote reports/crossvenue_join.json")


if __name__ == "__main__":
    main()
