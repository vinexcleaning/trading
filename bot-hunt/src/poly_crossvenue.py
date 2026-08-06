"""Pinnacle vs POLYMARKET esports — the venue the reconciled live P&L came from.

Kalshi came back with a median buy edge of -0.72c: no edge, and a fourth
confirmation it is the sharp line. Polymarket is the one venue left, and it is
structurally different in the way that matters — **makers are paid a rebate
rather than charged a fee** — which is the difference the whole maker argument
turned on.

TWO STRUCTURAL FACTS MEASURED FIRST, because they bound what this can say:

  1. **Only 16 of 436 recorded esports (slug, outcome) pairs are plausible
     moneylines.** The surface is 247 map/game-N markets, 111 props and 62
     handicaps. Polymarket esports is overwhelmingly DERIVATIVE markets, and
     pairing a moneyline to a handicap is the classic phantom.
  2. The recorder stored only the first outcome token per market (fixed
     2026-08-06), so each market has one book here. That is workable — a single
     token's ask is the price of that outcome and 1 - its bid is the price of
     the complement — but it means the two sides' independent spreads cannot be
     compared on the recorded window.

Slugs carry team text (`val-fpx-jdg-2026-08-06`) and the outcome column carries
the full team name (`FunPlus Phoenix`), so the join is on the OUTCOME NAME —
avoiding the abbreviation problem that made the Kalshi ticker join match 3 of
218.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
REC = ROOT / "data" / "record.db"
REP = ROOT / "reports"

STOP = re.compile(r"\b(team|esports?|gaming|club|the|gg|e-?sports)\b")
DERIV = re.compile(r"handicap|-game\d|-map\d|game-\d|rampage|clutch|ace|"
                   r"first-|will-|total-|over-|under-|kills|winner$|champion",
                   re.I)


def norm(s):
    if not s:
        return ""
    s = STOP.sub(" ", s.lower())
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(s.split())


def american_to_prob(a):
    a = float(a)
    return (-a) / ((-a) + 100.0) if a < 0 else 100.0 / (a + 100.0)


def devig(ph, pa):
    s = ph + pa
    if s <= 0:
        return {}
    out = {"multiplicative": (ph / s, pa / s)}
    lo, hi = 0.2, 5.0
    for _ in range(60):
        k = (lo + hi) / 2
        if ph ** k + pa ** k > 1:
            lo = k
        else:
            hi = k
    k = (lo + hi) / 2
    t = ph ** k + pa ** k
    out["power"] = (ph ** k / t, pa ** k / t)
    out["worst_case"] = (min(v[0] for v in out.values()),
                         min(v[1] for v in out.values()))
    return out


def main():
    REP.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{REC.as_posix()}?mode=ro", uri=True, timeout=180)

    # --- Pinnacle esports moneylines ---
    meta = {}
    for mid, lg, home, away, starts in con.execute(
            "select matchup_id, max(league), max(home), max(away), "
            "max(starts_utc) from pin_matchup where sport='esports' "
            "group by matchup_id"):
        if home and away:
            meta[mid] = {"league": lg, "home": home, "away": away,
                         "starts": starts}
    pin = defaultdict(dict)
    for mid, ts, desig, price in con.execute(
            "select matchup_id, ts_utc, designation, price_american "
            "from pin_market where sport='esports' and market_type='moneyline' "
            "and period=0 and designation is not null"):
        if mid in meta:
            pin[mid].setdefault(ts, {})[desig] = price
    print(f"Pinnacle esports matchups with names: {len(meta)}, "
          f"priced: {len(pin)}")

    # --- Polymarket recorded books, moneylines only ---
    poly = defaultdict(list)
    names = {}
    for slug, outcome, ts, bid, ask, d5 in con.execute(
            "select slug, outcome, ts_utc, bid_c, ask_c, depth5 from p_book "
            "where tag in ('cs2','dota-2','valorant') and outcome is not null "
            "and bid_c is not null and ask_c is not null"):
        if DERIV.search(slug or ""):
            continue
        if outcome in ("Yes", "No", "Over", "Under"):
            continue
        poly[(slug, outcome)].append((ts, bid, ask, d5))
        names[(slug, outcome)] = outcome
    print(f"Polymarket moneyline (slug,outcome) series: {len(poly)}")

    # --- join on the outcome's team name + game consistency ---
    GAME = {"val-": ("valorant",), "dota2-": ("dota 2", "dota2", "dota"),
            "cs2-": ("cs2", "counter-strike", "counter strike")}

    def game_ok(slug, league):
        lg = (league or "").lower()
        for pre, want in GAME.items():
            if (slug or "").lower().startswith(pre):
                return any(w in lg for w in want)
        return False

    rows = []
    matched = []
    for (slug, outcome), quotes in poly.items():
        o = norm(outcome)
        if not o:
            continue
        for mid, m in meta.items():
            if not game_ok(slug, m["league"]):
                continue
            h, a = norm(m["home"]), norm(m["away"])
            side = None
            # SUBSTRING MATCHING NEEDS A LENGTH FLOOR ON *BOTH* STRINGS.
            #
            # BUG FOUND BY AUDITING THE MATCHES. v1 required only `len(o) > 3`
            # and then tested `h in o or o in h`. Pinnacle's "A Team"
            # normalises to **"a"** once the stopword `team` is stripped, and
            # `"a" in o` is true for almost every outcome name — so "FOKUS
            # Sakura", "Gentle Mates GC", "Natus Vincere" and "SK Nebula" all
            # matched the SAME "Trace vs A Team" matchup. Four phantoms of
            # twelve. Exactly the failure mode the corpora describe, produced
            # by a one-character team name.
            def sim(x, y):
                if not x or not y:
                    return False
                if x == y:
                    return True
                return len(x) >= 4 and len(y) >= 4 and (x in y or y in x)

            if sim(o, h):
                side = "home"
            elif sim(o, a):
                side = "away"
            if side is None:
                continue
            # SECOND FILTER: the OPPONENT must appear in the slug.
            #
            # Recording one token per market means only one side's name is
            # available, so a single-name match cannot be verified the way the
            # Kalshi join verified both. The slug carries both teams as
            # abbreviations (`val-fpx-jdg-2026-08-06`), so requiring the
            # opponent's prefix to appear there restores a two-sided check.
            opp = a if side == "home" else h
            stem = re.sub(r"^(val|dota2|cs2)-|-\d{4}-\d{2}-\d{2}.*$", "",
                          (slug or "").lower())
            parts = [p for p in stem.split("-") if p]
            opp_words = [w for w in opp.split() if len(w) >= 3]
            if opp_words and not any(
                    any(p.startswith(w[:3]) or w.startswith(p[:3])
                        for p in parts if len(p) >= 2)
                    for w in opp_words):
                continue
            matched.append((slug, outcome, m["home"], m["away"], m["league"],
                            side))
            pts = sorted(pin[mid])
            for ts, bid, ask, d5 in quotes:
                if not pts:
                    continue
                near = min(pts, key=lambda x: abs(
                    datetime.strptime(x, "%Y-%m-%dT%H:%M:%SZ")
                    - datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")))
                dt = abs((datetime.strptime(near, "%Y-%m-%dT%H:%M:%SZ")
                          - datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
                          ).total_seconds())
                if dt > 900:
                    continue
                d = pin[mid][near]
                if "home" not in d or "away" not in d:
                    continue
                ph, pa = american_to_prob(d["home"]), american_to_prob(d["away"])
                fv = devig(ph, pa)
                for method, (fh, fa) in fv.items():
                    fair = fh if side == "home" else fa
                    rows.append({"slug": slug, "outcome": outcome,
                                 "method": method, "dt_s": dt,
                                 "fair_c": 100 * fair, "bid": bid, "ask": ask,
                                 "depth5": d5,
                                 "overround_pp": 100 * (ph + pa - 1),
                                 "edge_buy_c": 100 * fair - ask,
                                 "edge_sell_c": bid - 100 * fair,
                                 "spread_c": ask - bid})
            break

    print(f"\n== JOIN: {len(matched)} matched Polymarket moneylines")
    for m in matched[:12]:
        print(f"   {m[0][:34]:34} {m[1][:20]:20} -> {m[2][:16]} vs "
              f"{m[3][:16]}  [{m[4][:26]}]")
    print(f"\n== {len(rows):,} paired observations "
          f"({len({r['slug'] for r in rows})} markets)")
    if not rows:
        print("   nothing paired in time — the recorder window and these "
              "matches do not overlap")
        con.close()
        return

    print(f"   median time alignment: "
          f"{np.median([r['dt_s'] for r in rows]):.0f}s")
    sp = [r["spread_c"] for r in rows if r["method"] == "multiplicative"]
    print(f"   Polymarket spread: median {np.median(sp):.2f}c  "
          f"p90 {np.percentile(sp, 90):.2f}c")
    ov = [r["overround_pp"] for r in rows if r["method"] == "multiplicative"]
    print(f"   Pinnacle overround: median {np.median(ov):.2f}pp")

    print(f"\n   {'devig':16} {'n':>6} {'median buy edge':>17} {'p90':>9} "
          f"{'>2c':>7} {'>5c':>7}")
    out = {}
    for m in ("multiplicative", "power", "worst_case"):
        sub = [r for r in rows if r["method"] == m]
        if not sub:
            continue
        eb = np.array([r["edge_buy_c"] for r in sub])
        print(f"   {m:16} {len(sub):>6} {np.median(eb):>16.2f}c "
              f"{np.percentile(eb, 90):>8.2f}c "
              f"{100*np.mean(eb > 2):>6.1f}% {100*np.mean(eb > 5):>6.1f}%")
        out[m] = {"n": len(sub), "median": float(np.median(eb)),
                  "p90": float(np.percentile(eb, 90)),
                  "frac_over_2c": float(np.mean(eb > 2)),
                  "frac_over_5c": float(np.mean(eb > 5))}

    (REP / "poly_crossvenue.json").write_text(
        json.dumps({"matched": len(matched), "observations": len(rows),
                    "methods": out,
                    "pairs": [list(m) for m in matched[:40]]},
                   indent=1, default=str), encoding="utf-8")
    print("\nwrote reports/poly_crossvenue.json")
    con.close()


if __name__ == "__main__":
    main()
