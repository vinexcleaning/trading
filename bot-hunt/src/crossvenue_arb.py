"""Mailbox 023 job 1: how often did a REAL cross-venue arbitrage exist on the tape?

A QUERY over `bot-hunt/data/record.db`, not a scanner. No live connection, no
execution, no new ingestion. Kalshi and Polymarket were recorded **on one clock**
-- the same `cycle_id` -- since 2026-08-04, and nobody has ever asked this of it.

THE DISTINCTION THAT IS THE WHOLE POINT
----------------------------------------
    THEORETICAL   the two headline prices crossed.
    EXECUTABLE    they crossed AFTER fees on BOTH venues, AND there was enough
                  size at those levels, AND it lasted long enough to hit both legs.

Both are reported, separately, always.

THE MATCH KEY, AND WHY IT IS UNUSUALLY SAFE HERE
-------------------------------------------------
The usual trap -- "Miami to win" vs "Miami moneyline including overtime" -- is
about settlement rules differing between venues. **Run totals dodge most of it
because both venues put the LINE IN THE IDENTIFIER:**

    Kalshi       KXMLBTOTAL-26AUG061805WSHPHI-9   "Over 8.5 runs scored"
    Polymarket   mlb-wsh-phi-2026-08-06-total-8pt5     outcomes Over / Under

So a pair matches only when **the same two clubs, on the same date, at the same
numeric line** appear on both venues. That is three independent agreements, and
a mismatch on any one drops the pair rather than guessing.

⚠ WHAT THAT STILL DOES NOT PROVE, AND IT IS RECORDED AS A LIMIT NOT A FOOTNOTE:
the two venues could still resolve differently on a suspended, shortened or
rain-called game. **Nothing in either tape records the settlement rules**, so
this reports every candidate as a PRICE crossing and never as free money.

FEES -- FROM PRIMARY SOURCES, AS INSTRUCTED, NOT ASSUMED
---------------------------------------------------------
* **Kalshi**  `common/kalshi_fees.py`, the repo's only implementation:
  taker = roundup(0.07 x C x P x (1-P)). Published schedule effective 2026-07-07.
* **Polymarket**  https://docs.polymarket.com/trading/fees, retrieved 2026-08-31:
  *"fee = C x feeRate x p x (1 - p)"*, and **Sports markets carry a taker rate of
  0.05**. *"Makers are never charged fees. Only takers pay fees."* Worked example
  given there: 100 shares at $0.50 costs $1.25.

  ⚠ **This repo has previously assumed Polymarket was free to trade. It is not,
  on sports.** Both venues charge the SAME quadratic shape and differ only in the
  coefficient -- 7% against 5% -- so a two-legged taker arbitrage pays
  **0.12 x p x (1-p)** in total, which is about **3 cents at a 50c price.** That
  is the bar, and it is why a 1-cent theoretical crossing is not a trade.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT.parent))
from common.kalshi_fees import fee_rate_cents  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

DB = ROOT / "data" / "record.db"
REP = ROOT / "reports"
ET = ZoneInfo("America/New_York")
TSFMT = "%Y-%m-%dT%H:%M:%SZ"
MON = {m: i + 1 for i, m in enumerate(
    "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split())}
CLUBS = {"ATH", "ATL", "AZ", "BAL", "BOS", "CHC", "CIN", "CLE", "COL", "CWS",
         "DET", "HOU", "KC", "LAA", "LAD", "MIA", "MIL", "MIN", "NYM", "NYY",
         "PHI", "PIT", "SD", "SEA", "SF", "STL", "TB", "TEX", "TOR", "WSH"}
ALIAS = {"ARI": "AZ", "CHW": "CWS", "WAS": "WSH", "SDP": "SD", "SFG": "SF",
         "TBR": "TB", "KCR": "KC", "OAK": "ATH"}

POLY_SPORTS_RATE = 0.05          # docs.polymarket.com/trading/fees, 2026-08-31


def poly_fee_cents(price_c: float) -> float:
    """Polymarket taker fee, in cents per share, from their published formula."""
    p = price_c / 100.0
    return 100.0 * POLY_SPORTS_RATE * p * (1.0 - p)


def split_pair(sfx: str):
    ok = [(sfx[:i], sfx[i:]) for i in range(2, len(sfx) - 1)
          if sfx[:i] in CLUBS and sfx[i:] in CLUBS]
    return ok[0] if len(ok) == 1 else None


def build_match(con):
    """The gate. Returns {key: (kalshi_ticker, poly_slug)} for TOTALS."""
    kal = {}
    for tk, st in con.execute(
            "select ticker, yes_sub_title from k_names where series='KXMLBTOTAL'"):
        m = re.match(r"^KXMLBTOTAL-(\d{2})([A-Z]{3})(\d{2})\d{4}([A-Z]+)-", tk or "")
        ln = re.match(r"Over ([\d.]+) runs scored", st or "")
        if not m or not ln:
            continue
        pair = split_pair(m.group(4))
        if not pair:
            continue
        d = f"20{m.group(1)}-{MON[m.group(2)]:02d}-{m.group(3)}"
        kal[(d, frozenset(pair), float(ln.group(1)))] = tk

    poly = {}
    for (slug,) in con.execute(
            "select distinct slug from p_book "
            "where slug like 'mlb-%-total-%' and slug not like '%f5%'"):
        m = re.match(r"^mlb-([a-z]+)-([a-z]+)-(\d{4}-\d{2}-\d{2})-total-(\d+)pt(\d)$",
                     slug or "")
        if not m:
            continue
        a, b = m.group(1).upper(), m.group(2).upper()
        a, b = ALIAS.get(a, a), ALIAS.get(b, b)
        if a not in CLUBS or b not in CLUBS or a == b:
            continue
        poly[(m.group(3), frozenset((a, b)),
              float(f"{m.group(4)}.{m.group(5)}"))] = slug
    keys = sorted(set(kal) & set(poly))
    return {k: (kal[k], poly[k]) for k in keys}, len(kal), len(poly)


def main() -> None:
    REP.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    print("=" * 78)
    print("CROSS-VENUE ARBITRAGE ON THE RECORDED TAPE — Kalshi vs Polymarket")
    print("=" * 78)
    print("A query over record.db. No live connection, no execution.")
    print("Fees: Kalshi 0.07*P*(1-P) (common/kalshi_fees.py); Polymarket sports")
    print("0.05*p*(1-p) taker (docs.polymarket.com/trading/fees, 2026-08-31).\n")

    match, nk, np_ = build_match(con)
    games = {(k[0], k[1]) for k in match}
    dates = sorted({k[0] for k in match})
    print("STEP 1 — THE GATE. How many genuinely equivalent pairs exist at all?")
    print(f"   Kalshi run-total rungs keyed          : {nk:,}")
    print(f"   Polymarket run-total markets keyed    : {np_:,}")
    print(f"   ⚠ MATCHED on club-pair + date + line  : {len(match):,}")
    print(f"      distinct games                     : {len(games):,}")
    print(f"      dates covered                      : {len(dates)}  "
          f"({dates[0]} → {dates[-1]})" if dates else "")
    if not match:
        print("\n   NOTHING MATCHES. That is the complete answer.")
        return

    print("\nSTEP 2 — were both venues quoted in the SAME cycle? (one clock)")
    rows, per_pair = [], {}
    no_overlap = 0
    cyc_ts = {c: t for c, t in con.execute("select cycle_id, started_utc from cycles")}
    inplay_skipped = 0
    for key, (tk, slug) in match.items():
        # first pitch, straight off the Kalshi ticker. BH012: the ticker time is
        # exact against Pinnacle's start on 22 of 22, while close_time is NOT.
        mm = re.match(r"^KXMLBTOTAL-(\d{2})([A-Z]{3})(\d{2})(\d{2})(\d{2})", tk)
        start_utc = None
        if mm:
            try:
                start_utc = datetime(2000 + int(mm.group(1)), MON[mm.group(2)],
                                     int(mm.group(3)), int(mm.group(4)),
                                     int(mm.group(5)), tzinfo=ET
                                     ).astimezone(timezone.utc).strftime(TSFMT)
            except (ValueError, KeyError):
                start_utc = None
        kq = {cid: (yb, ya, bs, asz, d5y, d5n)
              for cid, yb, ya, bs, asz, d5y, d5n in con.execute(
                  "select cycle_id, yes_bid_c, yes_ask_c, bid_size, ask_size, "
                  "depth5_yes, depth5_no from k_book where series='KXMLBTOTAL' "
                  "and ticker=?", (tk,))}
        if not kq:
            continue
        pq = defaultdict(dict)
        for cid, outc, b, a, bsz, asz, d5 in con.execute(
                "select cycle_id, outcome, bid_c, ask_c, bid_size, ask_size, depth5 "
                "from p_book where slug=?", (slug,)):
            o = (outc or "").strip().lower()
            if o in ("over", "under"):
                pq[cid][o] = (b, a, bsz, asz, d5)
        shared = sorted(set(kq) & {c for c, v in pq.items() if len(v) == 2})
        if not shared:
            no_overlap += 1
            continue
        hits = []
        for cid in shared:
            # ⚠ PRE-GAME ONLY. THE CORRECTION THAT KILLED v1's HEADLINE.
            # v1 reported 1,292 "executable" arbitrages, median 3.47c, max 92c.
            # The biggest were IN-PLAY markets already decided: "Over 20.5 runs"
            # with Kalshi bid 50 / ask 84 while BOTH venues priced the over ~99.
            # That 34c spread is a stale limit order on a settled question and
            # the ask is GONE by the next cycle. Two independent reasons it is
            # not a trade, either fatal: (1) CLAUDE.md §9b, in-play is paper only
            # -- this repo's bot read scores after 97.4% of the price move had
            # happened, on 4,398 events; (2) the two venues are recorded a MEDIAN
            # 6.5 MINUTES apart inside one cycle_id (max 23.8), so a run scoring
            # inside that gap manufactures the crossing outright.
            if start_utc is not None and cyc_ts.get(cid, "") >= start_utc:
                inplay_skipped += 1
                continue
            yb, ya, bs, asz, d5y, d5n = kq[cid]
            ov, un = pq[cid]["over"], pq[cid]["under"]
            for leg, k_price, k_size, p_price, p_size, label in (
                    (1, ya, asz, un[1], un[3], "buy Kalshi OVER + Poly UNDER"),
                    (2, (100 - yb) if yb is not None else None, bs,
                     ov[1], ov[3], "buy Kalshi UNDER(no) + Poly OVER")):
                if k_price is None or p_price is None:
                    continue
                gross = 100.0 - (k_price + p_price)
                if gross <= 0:
                    continue
                fee = float(fee_rate_cents(k_price)) + poly_fee_cents(p_price)
                net = gross - fee
                hits.append({"cycle": cid, "leg": label,
                             "k_price": k_price, "p_price": p_price,
                             "gross_c": gross, "fee_c": fee, "net_c": net,
                             "k_size": k_size, "p_size": p_size,
                             "size": min(k_size or 0, p_size or 0)})
        if hits:
            # PERSISTENCE: how many CONSECUTIVE recorded cycles did a crossing
            # survive on this pair? The instruction is right that this single
            # number decides whether any of it is actionable -- an edge that
            # exists in one snapshot and is gone by the next cannot be hit on
            # two venues by a human or by anything this repo is allowed to run.
            cyc_hit = sorted({h["cycle"] for h in hits})
            runs, cur = [], 1
            for a, b in zip(cyc_hit, cyc_hit[1:]):
                if b - a == 1:
                    cur += 1
                else:
                    runs.append(cur)
                    cur = 1
            runs.append(cur)
            for h in hits:
                h["pair_longest_run_cycles"] = max(runs)
                h["pair_cycles_with_a_crossing"] = len(cyc_hit)
            per_pair[key] = hits
            rows.extend(hits)
    print(f"   pairs with NO shared cycle (never quoted together): {no_overlap:,}")
    print(f"   observations DISCARDED as IN-PLAY (after first pitch): {inplay_skipped:,}")
    print(f"   pairs usable                                      : {len(match)-no_overlap:,}")

    print("\n" + "=" * 78)
    print("STEP 3 — THEORETICAL vs EXECUTABLE")
    print("=" * 78)
    if not rows:
        print("   ⚠ THE HEADLINE PRICES NEVER CROSSED, on any pair, in any cycle.")
        print("   That is a complete answer and it needs no fee model.")
        theo = []
    else:
        theo = rows
    print(f"   THEORETICAL crossings (gross > 0)  : {len(theo):,} "
          f"observations on {len(per_pair):,} pairs")
    if theo:
        g = np.array([r["gross_c"] for r in theo])
        f = np.array([r["fee_c"] for r in theo])
        n = np.array([r["net_c"] for r in theo])
        print(f"      gross margin  median {np.median(g):.2f}c  max {g.max():.2f}c")
        print(f"      fee to cross both venues  median {np.median(f):.2f}c")
        pos = [r for r in theo if r["net_c"] > 0]
        print(f"   AFTER FEES, still positive         : {len(pos):,} of {len(theo):,}")
        if pos:
            sz = np.array([r["size"] for r in pos])
            print(f"      net margin median {np.median([r['net_c'] for r in pos]):.2f}c")
            print(f"      ⚠ size available at BOTH legs: median {np.median(sz):.0f} "
                  f"contracts, max {sz.max():.0f}")
            withsz = [r for r in pos if r["size"] >= 10]
            print(f"   EXECUTABLE (net>0 AND >=10 contracts both legs): {len(withsz):,}")
            byp = defaultdict(list)
            for r in pos:
                byp[r["cycle"]].append(r)
            print(f"      spread over {len(byp)} distinct cycles")
            runs = [r["pair_longest_run_cycles"] for r in pos]
            print("")
            print("   ⚠ PERSISTENCE — the number that decides whether actionable:")
            print(f"      longest unbroken run of cycles with a crossing, per pair:")
            print(f"        median {np.median(runs):.0f} cycles   p90 "
                  f"{np.percentile(runs,90):.0f}   max {max(runs)}")
            one = sum(1 for r in runs if r == 1)
            print(f"      crossings that lasted a SINGLE cycle and were gone: "
                  f"{one:,} of {len(runs):,} ({100*one/len(runs):.0f} out of 100)")
            print(f"      one cycle is ~13 minutes of wall clock, and the two")
            print(f"      venues inside it are a median 6.5 minutes apart.")
        else:
            print("   ⚠ NONE survives the fee on both legs. EXECUTABLE = 0.")

    out = {"matched_pairs": len(match), "distinct_games": len(games),
           "dates": len(dates), "pairs_no_shared_cycle": no_overlap,
           "theoretical_observations": len(theo),
           "after_fee_positive": sum(1 for r in theo if r["net_c"] > 0),
           "poly_fee_source": "docs.polymarket.com/trading/fees 2026-08-31, "
                              "sports taker 0.05*p*(1-p)",
           "rows": theo[:2000]}
    (REP / "crossvenue_arb.json").write_text(json.dumps(out, indent=1),
                                             encoding="utf-8")
    print("\n   wrote reports/crossvenue_arb.json")


if __name__ == "__main__":
    main()
