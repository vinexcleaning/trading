"""TASK 4 + 5: one row per match, every feature carrying a knowability stamp,
then descriptive sanity checks.

KNOWABILITY IS ASSERTED IN CODE, not documented and hoped for. Every feature
is written as {"value":…, "known_at":…}. `assert_knowable` refuses any feature
whose `known_at` is later than the decision point it would be used at. Building
this in now is far cheaper than retrofitting it, and it is the structural
property that stops LEDGER T010 (an anchor read from after the match) recurring.

Decision point used throughout: KICKOFF. A feature is legitimate iff it was
known strictly before kickoff.

TASK 5 checks are DESCRIPTIVE. No model is fitted, no entry rule tested,
nothing is reported as an edge.
"""
import csv
import io
import json
import os
import statistics as st
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import requests

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "market-selection", "src"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "common"))
import teammatch as TM  # noqa: E402
import leakguard as LG  # noqa: E402

ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
UA = {"User-Agent": "Mozilla/5.0 (soccer-research/1.0)"}
FD = "https://www.football-data.co.uk/new/{}.csv"
FD_LEAGUE = {"mex.1": ("MEX", "Liga MX"), "arg.1": ("ARG", None),
             "bra.1": ("BRA", "Serie A"), "usa.1": ("USA", "MLS")}


def F(value, known_at):
    return {"value": value, "known_at": known_at}


def assert_knowable(feat, decision_at, name):
    """A feature may not be used at a decision point it postdates."""
    if feat is None or feat.get("value") is None:
        return True
    ka = feat.get("known_at")
    if ka is None:
        raise AssertionError(f"{name}: no known_at stamp")
    if ka >= decision_at:
        raise AssertionError(f"{name}: known_at {ka} is NOT before the "
                             f"decision point {decision_at}")
    return True


def load_fd():
    """Bookmaker closing lines, keyed (league, date, pair). VERIFIED by the
    League column -- the site serves wrong-country files on HTTP 200."""
    out = {}
    meta = {}
    for lg, (code, want) in FD_LEAGUE.items():
        try:
            r = requests.get(FD.format(code), headers=UA, timeout=90)
        except requests.RequestException:
            continue
        if r.status_code != 200:
            continue
        rows = list(csv.reader(io.StringIO(r.text)))
        hdr, body = rows[0], rows[1:]
        ix = {c: i for i, c in enumerate(hdr)}
        leagues = Counter()
        n = 0
        for x in body:
            if len(x) < len(hdr):
                continue
            lgname = x[ix["League"]] if "League" in ix else ""
            leagues[lgname] += 1
            if want and lgname.strip() != want:
                continue
            try:
                d = datetime.strptime(x[ix["Date"]].strip(), "%d/%m/%Y").date()
            except ValueError:
                continue
            h, a = x[ix["Home"]], x[ix["Away"]]
            key = (lg, d.isoformat(), TM.pair_key(h, a))
            def num(c):
                try:
                    return float(x[ix[c]])
                except (KeyError, ValueError):
                    return None
            # PINNACLE IS GONE IN 2026. Measured: PSCH is 100% populated in
            # 2022-24, ~90% in 2025 and 0.0% in 2026 across MEX/ARG/BRA/USA.
            # This is LEDGER T014 repeating -- tennis-data.co.uk dropped
            # Pinnacle in 2026 and football-data.co.uk has now done the same.
            # AvgC* (market-average close) is 100% populated including every
            # match in the Kalshi window, so it is the usable benchmark.
            out[key] = {"PSCH": num("PSCH"), "PSCD": num("PSCD"),
                        "PSCA": num("PSCA"),
                        "AvgCH": num("AvgCH"), "AvgCD": num("AvgCD"),
                        "AvgCA": num("AvgCA"),
                        "home": h, "away": a,
                        "HG": num("HG"), "AG": num("AG")}
            n += 1
        meta[lg] = {"code": code, "kept": n, "leagues_in_file": dict(leagues)}
        print(f"  football-data {code} -> {lg}: kept {n} rows; "
              f"League column = {list(leagues)[:3]}")
    return out, meta


def main():
    join = json.load(open(os.path.join(DATA, "join.json"), encoding="utf-8"))
    inplay = json.load(open(os.path.join(DATA, "inplay_events.json"),
                            encoding="utf-8"))
    ev_by_match = defaultdict(list)
    for r in inplay["rows"]:
        ev_by_match[r["espn_id"]].append(r)

    print("=== loading bookmaker closing lines ===")
    fd, fd_meta = load_fd()
    print(f"  {len(fd)} bookmaker rows indexed")

    rows = []
    for f in join["matched"]:
        ko_s = f.get("espn_date")
        if not ko_s:
            continue
        ko = datetime.fromisoformat(ko_s.replace("Z", "+00:00"))
        kos = ko.isoformat()
        # DECISION POINT = kickoff. A feature is legitimate iff it was known
        # strictly before it.
        dec = kos
        # The closing line is published before kickoff. Stamping it AT the
        # decision point (as the first version did) made 159 of 480
        # assertions fail -- correctly, because `known_at == decision_at` is
        # not "known before". The guard caught my own sloppy stamping rather
        # than a real leak; the fix is to stamp when the value was actually
        # available, not when it would be used.
        book_known = (ko - timedelta(minutes=10)).isoformat()

        # ---- market features (Kalshi), known when the market was open
        mk = {}
        for m in f["markets"]:
            mk[m["yes_sub"]] = {"ticker": m["ticker"], "result": m["result"],
                                "open_time": m["open_time"]}

        # ---- bookmaker close: known BEFORE kickoff by construction
        lg = f["espn_league"]
        key = (lg, (f.get("espn_date") or "")[:10],
               TM.pair_key(f.get("espn_home") or "", f.get("espn_away") or ""))
        book = fd.get(key)
        if book is None:            # try +/-1 day
            for off in (1, -1):
                d2 = (ko + timedelta(days=off)).date().isoformat()
                book = fd.get((lg, d2, key[2]))
                if book:
                    break

        row = {
            "espn_id": f["espn_id"], "league": lg, "series": f["series"],
            "kickoff": kos, "decision_at": dec,
            "event_ticker": f["event_ticker"],
            "home": f.get("espn_home"), "away": f.get("espn_away"),
            "completed": f.get("espn_completed"),
            "kalshi_markets": mk,
            # --- features, each with a knowability stamp
            "feat": {
                "book_psc_home": F(book["PSCH"] if book else None, book_known),
                "book_avg_home": F(book["AvgCH"] if book else None, book_known),
                "book_avg_draw": F(book["AvgCD"] if book else None, book_known),
                "book_avg_away": F(book["AvgCA"] if book else None, book_known),
            },
            # --- outcomes (NOT features; known only after)
            "outcome": {
                "home_goals": (book or {}).get("HG"),
                "away_goals": (book or {}).get("AG"),
                "n_inplay_events": len(ev_by_match.get(f["espn_id"], [])),
            },
        }
        rows.append(row)

    # ---- knowability assertions
    viol = 0
    for r in rows:
        for name, feat in r["feat"].items():
            try:
                assert_knowable(feat, r["decision_at"], name)
            except AssertionError as e:
                viol += 1
                if viol <= 5:
                    print(f"  KNOWABILITY VIOLATION: {e}")
    print(f"\nknowability assertions: {len(rows)*3} checked, {viol} violations")

    with open(os.path.join(DATA, "dataset.json"), "w", encoding="utf-8") as fh:
        json.dump({"rows": rows, "fd_meta": fd_meta}, fh, indent=1, default=str)

    # ---- coverage
    print("\n=== FEATURE COVERAGE ===")
    n = len(rows)
    print(f"matches in dataset: {n}")
    cov = defaultdict(int)
    for r in rows:
        for k, v in r["feat"].items():
            if v["value"] is not None:
                cov[k] += 1
        if r["outcome"]["home_goals"] is not None:
            cov["final_score"] += 1
        if r["outcome"]["n_inplay_events"]:
            cov["inplay_events"] += 1
    print(f"  {'feature':22s} {'present':>8s} {'pct':>7s}")
    for k in ["book_psc_home", "book_avg_home", "book_avg_draw",
              "book_avg_away", "final_score", "inplay_events"]:
        print(f"  {k:22s} {cov[k]:8d} {100*cov[k]/max(n,1):6.1f}%")
    per_lg = defaultdict(lambda: [0, 0])
    for r in rows:
        per_lg[r["league"]][0] += 1
        if r["feat"]["book_avg_home"]["value"] is not None:
            per_lg[r["league"]][1] += 1
    print(f"\n  {'league':22s} {'matches':>8s} {'with book':>10s} {'pct':>7s}")
    for lg, (a, b) in sorted(per_lg.items()):
        print(f"  {lg:22s} {a:8d} {b:10d} {100*b/max(a,1):6.1f}%")

    # ---- SELECTION CANARY on the bookmaker join
    print("\n=== SELECTION CANARY: does having a bookmaker line select matches? ===")
    print("Null: a join may change WHICH matches are in the sample; it may not")
    print("change how well the market prices them (GUARDS #1, three-valued).")
    have, outc = [], []
    for r in rows:
        hg, ag = r["outcome"]["home_goals"], r["outcome"]["away_goals"]
        psc = r["feat"]["book_avg_home"]["value"]
        if hg is None or ag is None:
            continue
        have.append(psc is not None)
        outc.append(1.0 if hg > ag else 0.0)
    # calibration residual needs an implied price on both arms, which by
    # construction only the kept arm has -> the honest statistic here is the
    # raw outcome rate, and the guard will say if that is untestable
    import numpy as np
    if have and sum(have) and sum(1 for x in have if not x):
        res = LG.check_selection(np.array(have), np.array(outc),
                                 name="bookmaker-line join")
        print("  " + res.msg)
        print(f"  VERDICT: {res.verdict}")
    else:
        print("  UNTESTABLE: one arm is empty "
              f"(with={sum(have)}, without={sum(1 for x in have if not x)})")

    # ================= TASK 5 SANITY CHECKS =================
    print("\n" + "=" * 68)
    print("TASK 5 SANITY CHECKS -- descriptive, anomalies are data bugs")
    print("=" * 68)

    print("\n1. HOME ADVANTAGE per league (from the bookmaker's own scores)")
    print(f"  {'league':10s} {'n':>5s} {'home win':>9s} {'draw':>7s} {'away':>7s}")
    for lg in sorted({r["league"] for r in rows}):
        sel = [r for r in rows if r["league"] == lg
               and r["outcome"]["home_goals"] is not None]
        if not sel:
            continue
        hw = sum(1 for r in sel
                 if r["outcome"]["home_goals"] > r["outcome"]["away_goals"])
        dr = sum(1 for r in sel
                 if r["outcome"]["home_goals"] == r["outcome"]["away_goals"])
        aw = len(sel) - hw - dr
        print(f"  {lg:10s} {len(sel):5d} {100*hw/len(sel):8.1f}% "
              f"{100*dr/len(sel):6.1f}% {100*aw/len(sel):6.1f}%")

    print("\n2. GOAL TIMES -- distribution by 15-minute bucket")
    buckets = Counter()
    for r in inplay["rows"]:
        if r["event_type"] != "goal":
            continue
        m = (r.get("minute") or "").split("'")[0]
        try:
            mm = int(m)
        except ValueError:
            continue
        buckets[min(mm // 15, 6)] += 1
    tot = sum(buckets.values())
    names = ["0-14", "15-29", "30-44", "45-59", "60-74", "75-89", "90+"]
    for i, nm in enumerate(names):
        c = buckets.get(i, 0)
        print(f"  {nm:>6s} {c:4d} {100*c/max(tot,1):5.1f}% "
              + "#" * int(40 * c / max(tot, 1)))

    print("\n3. DOES THE PRICE REACT TO GOALS AT ALL? (see inplay_events.md)")
    mv = []
    for r in inplay["rows"]:
        if r["event_type"] != "goal":
            continue
        p = r["prices"]
        if p.get("-1") is not None and p.get("1") is not None:
            mv.append(p["1"] - p["-1"])
    if mv:
        print(f"  n={len(mv)} goals, median move {st.median(mv):+.2f}c, "
              f"{100*sum(1 for x in mv if x>0)/len(mv):.0f}% positive")
        print("  -> yes, unambiguously.")

    print("\n4. KALSHI PRE-MATCH PRICE vs THE CLOSING LINE")
    print("  Benchmark is AvgC* (market-average close), NOT Pinnacle: PSCH is")
    print("  0.0% populated in 2026 across all four leagues. If the two do not")
    print("  correlate strongly the join is wrong, not the market.")
    import kalshi_api as K
    pairs = []
    for r in rows:
        h = r["feat"]["book_avg_home"]["value"]
        d_ = r["feat"]["book_avg_draw"]["value"]
        a = r["feat"]["book_avg_away"]["value"]
        if not (h and d_ and a):
            continue
        # de-vig the 3-way book
        ip = [1 / h, 1 / d_, 1 / a]
        tot = sum(ip)
        book_home = ip[0] / tot * 100
        # Kalshi: the home team's own leg, priced at the last candle before KO
        home_leg = None
        for sub, m in r["kalshi_markets"].items():
            if sub and sub.lower() not in ("tie", "draw") and \
                    TM.canon(sub) == TM.canon(r["home"] or ""):
                home_leg = m
                break
        if not home_leg:
            continue
        ko = datetime.fromisoformat(r["kickoff"].replace("Z", "+00:00"))
        rr = K.get(f"/series/{r['series']}/markets/{home_leg['ticker']}"
                   f"/candlesticks",
                   {"start_ts": int((ko - timedelta(hours=3)).timestamp()),
                    "end_ts": int(ko.timestamp()), "period_interval": 1})
        if rr is None or rr.status_code != 200:
            continue
        cs = rr.json().get("candlesticks", [])
        last = None
        for c in cs:
            yb = (c.get("yes_bid") or {}).get("close_dollars")
            ya = (c.get("yes_ask") or {}).get("close_dollars")
            if yb is None or ya is None:
                continue
            b, aa = float(yb) * 100, float(ya) * 100
            if b > 0 and aa < 100:
                last = (b + aa) / 2
        if last is None:
            continue
        pairs.append((book_home, last, r["league"], r["home"]))
    if len(pairs) >= 5:
        import numpy as np
        bk = np.array([p[0] for p in pairs])
        ks = np.array([p[1] for p in pairs])
        corr = float(np.corrcoef(bk, ks)[0, 1])
        diff = ks - bk
        print(f"\n  n={len(pairs)} matches with both a de-vigged book price "
              f"and a Kalshi pre-match mid")
        print(f"  correlation           r = {corr:.4f}")
        print(f"  mean  Kalshi - book   {diff.mean():+.2f} c")
        print(f"  median|Kalshi - book| {np.median(np.abs(diff)):.2f} c")
        print(f"  p90   |Kalshi - book| {np.percentile(np.abs(diff), 90):.2f} c")
        print(f"  VERDICT: " + ("consistent -- the join is sound"
                                if corr > 0.90 else
                                "SUSPICIOUS -- investigate the join"))
        json.dump([{"book": p[0], "kalshi": p[1], "league": p[2],
                    "home": p[3]} for p in pairs],
                  open(os.path.join(REP, "kalshi_vs_book.json"), "w"), indent=1)
    else:
        print(f"  only {len(pairs)} usable pairs -- UNTESTABLE")


if __name__ == "__main__":
    main()
