"""H10 — REST A PASSIVE BID. The pre-registered strategy that was never run.

This is the question the whole programme keeps circling. `signal-github`
concluded maker-only quoting is "the one strategy whose income is not required
to overcome a fee first", reasoning from fee schedules. A 20-year professional
(youtube `rrKRhjye1sw`, 112k views) says the opposite: *"a resting offer is only
taken when it is good for the taker... you are effectively being free-rolled."*
Both are right, and the missing term is adverse selection. The only number
anyone has put on it is the **38% of gross** it cost the esports arb author.

This measures it directly, on real Kalshi L2, on the family with the only
publicly reconciled live P&L.

WHAT THE CORPORA SAID, and how each shaped this design
  * `Ea9BeOc_Yiw`  — maker = a limit that rests away from the price; taker =
    one that sits through it. Encoded exactly: a bid at or below the best bid.
  * `Jd0BHJflnw0`  — "simulate order queue, partial fills and failed legs."
  * r/quant `1rfu1yt` — a bot author's own diagnosis: *"the reason my results
    are too good is likely the 100% fill rate; when it's 30% it will be way
    less."* **30% is the number practitioners converge on.** The
    pre-registration set the falsification threshold at 20%, written before
    this was read.
  * r/quant `1ski9e8` (Paradigm challenge, placed #2) — *"the monopoly regime,
    when competitor quotes vanish, accounted for 60% of total edge"* and
    *"inventory skew removal = catastrophic; settlement risk dominates."*
    Both are tested below as MECHANISM, not assumed.

THE FILL MODEL, deliberately conservative
  A resting bid at price P fills only when cumulative REMOVED size at P exceeds
  the queue that was ahead of it. A touch never counts as a fill — the rule
  adopted from `artyomderkach-bit`, the most honest repo in the corpus.
  Cancellations are indistinguishable from trades in this feed, so removal is
  an UPPER bound on fills. Reported as such, with a strict lower bound
  (best-bid trades strictly through P) beside it. The truth is between them and
  both are printed.

RESTRICTED TO PRE-EVENT OBSERVATIONS. Post-event books are crossed 83.65% of
the time because settled books are not maintained (src/diagnose_cross.py).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import replay as R  # noqa: E402
from diagnose_cross import event_time  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REP = ROOT / "reports"
MKT_DB = ROOT / "data" / "kalshi_soccer.db"
SEED = 20260805


def load_outcomes():
    """ticker -> 1 if the market settled YES else 0. From the settled universe
    already pulled; markets with no result are excluded, never guessed."""
    con = sqlite3.connect(f"file:{MKT_DB.as_posix()}?mode=ro", uri=True,
                          timeout=120)
    out = {tk: (1 if res == "yes" else 0) for tk, res in con.execute(
        "select ticker, result from markets where result in ('yes','no')")}
    con.close()
    return out


class Order:
    __slots__ = ("ticker", "price", "queue_ahead", "removed", "placed_ts",
                 "filled_ts", "mode", "bid_at_place", "ask_at_place",
                 "through", "depth_other", "spread_at_place")

    def __init__(self, ticker, price, queue_ahead, ts, mode, bid, ask,
                 depth_other, spread):
        self.ticker, self.price = ticker, price
        self.queue_ahead, self.removed = queue_ahead, 0.0
        self.placed_ts, self.filled_ts = ts, None
        self.mode = mode
        self.bid_at_place, self.ask_at_place = bid, ask
        self.through = False
        self.depth_other = depth_other
        self.spread_at_place = spread


def run(sample_minutes=20, horizon_minutes=180, modes=("join", "improve"),
        verbose=True):
    outcomes = load_outcomes()
    files = R.hours_on_disk()
    if verbose:
        print(f"replaying {len(files)} hours; {len(outcomes)} settled tickers "
              f"known")

    live: dict[str, list[Order]] = defaultdict(list)
    done: list[Order] = []
    last_place: dict[tuple, datetime] = {}
    skipped = defaultdict(int)

    def on_event(ts, tk, bk, i, d):
        et = event_time(tk)
        if et is None or ts >= et:
            skipped["post_event_or_unknown"] += 1
            return
        if tk not in outcomes:
            skipped["no_settled_outcome"] += 1
            return

        yb, nb = bk.best_yes_bid(), bk.best_no_bid()
        if yb is None or nb is None:
            return
        ask = 100 - nb
        if ask <= yb:                      # crossed; not a tradeable book
            skipped["crossed"] += 1
            return

        # --- 1. progress every live order on this ticker ---
        side = d["side"][i]
        price_c = R.to_cents(d["price"][i])
        delta = float(d["delta"][i])
        still = []
        for o in live[tk]:
            if side == "yes" and price_c == o.price and delta < 0:
                o.removed += -delta
            # TRADE-THROUGH is only a meaningful fill signal for JOIN.
            #
            # BUG FOUND AND FIXED. v1 tested `best_yes_bid < o.price` for both
            # modes and reported IMPROVE at a 99.6% "lower bound" against a
            # 45.8% upper bound — bounds inverted, which is impossible and is
            # what gave it away. For an IMPROVE order the market's best bid is
            # BY CONSTRUCTION below our price (we improved on it) and our own
            # order is not in the replayed book, so the test fires immediately
            # on every order and measures nothing.
            #
            # For JOIN we rest AT the touch, so the touch falling below our
            # price really does mean the level cleared.
            if o.mode == "join":
                bb = bk.best_yes_bid()
                if bb is not None and bb < o.price:
                    o.through = True
            if o.removed > o.queue_ahead and o.filled_ts is None:
                o.filled_ts = ts
                done.append(o)
                continue
            if ts - o.placed_ts > timedelta(minutes=horizon_minutes) or ts >= et:
                done.append(o)
                continue
            still.append(o)
        live[tk] = still

        # --- 2. place new orders on a fixed cadence ---
        for mode in modes:
            key = (tk, mode)
            lp = last_place.get(key)
            if lp is not None and ts - lp < timedelta(minutes=sample_minutes):
                continue
            if mode == "join":
                p = yb
                qa = bk.size_at("yes", p)
            else:                           # improve the touch by 1c
                p = yb + 1
                if p >= ask:
                    continue
                qa = bk.size_at("yes", p)   # normally 0 — we are alone there
            if p < 1 or p > 99:
                continue
            last_place[key] = ts
            live[tk].append(Order(tk, p, qa, ts, mode, yb, ask,
                                  bk.depth("no", 5), ask - yb))

    R.replay(files, on_event=on_event, verbose=False)
    for tk, os_ in live.items():
        done.extend(os_)

    if verbose:
        print(f"orders placed: {len(done):,}   skipped: {dict(skipped)}")
    return done, outcomes


def summarise(orders, outcomes):
    rows = []
    for o in orders:
        won = outcomes.get(o.ticker)
        if won is None:
            continue
        rows.append({
            "ticker": o.ticker, "mode": o.mode, "price": o.price,
            "filled": o.filled_ts is not None, "through": o.through,
            "queue_ahead": o.queue_ahead, "removed": o.removed,
            "won": won, "spread": o.spread_at_place,
            "depth_other": o.depth_other,
            "mins_to_fill": ((o.filled_ts - o.placed_ts).total_seconds() / 60
                             if o.filled_ts else None),
            "event": o.ticker.rsplit("-", 1)[0],
            "day": o.placed_ts.date().isoformat(),
        })
    return rows


def boot_ci(vals, clusters, n=2000, seed=SEED):
    if len(vals) < 5:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = defaultdict(list)
    for i, c in enumerate(clusters):
        idx[c].append(i)
    keys = list(idx)
    v = np.asarray(vals, dtype=float)
    out = np.empty(n)
    for b in range(n):
        pick = rng.choice(len(keys), size=len(keys), replace=True)
        sel = np.concatenate([idx[keys[j]] for j in pick])
        out[b] = v[sel].mean()
    return tuple(float(x) for x in np.percentile(out, [2.5, 97.5]))


def report(rows):
    REP.mkdir(parents=True, exist_ok=True)
    print("\n" + "=" * 78)
    print("H10 — PASSIVE QUOTING ON KALSHI ESPORTS, REAL L2")
    print("=" * 78)
    if not rows:
        print("no orders — nothing to report")
        return

    for mode in sorted({r["mode"] for r in rows}):
        sub = [r for r in rows if r["mode"] == mode]
        n = len(sub)
        filled = [r for r in sub if r["filled"]]
        through = [r for r in sub if r["through"]]
        ev = len({r["event"] for r in sub})
        print(f"\n--- mode = {mode.upper()} "
              f"({'rest at the touch, behind the queue' if mode=='join' else 'improve the touch by 1c, alone at the level'})")
        print(f"    orders {n:,} across {ev} events, "
              f"{len({r['ticker'] for r in sub})} markets")
        print(f"    FILL RATE (removal-based, an UPPER bound — a cancel is "
              f"indistinguishable from a trade in this feed): "
              f"{100*len(filled)/n:5.1f}%   ({len(filled):,})")
        if mode == "join":
            print(f"    FILL RATE (touch traded strictly through, LOWER "
                  f"bound): {100*len(through)/n:5.1f}%   ({len(through):,})")
            print(f"      -> practitioner corroboration: an r/quant bot author "
                  f"diagnosed his own\n         too-good results as a 100% fill "
                  f"assumption and put the real figure at ~30%.")
        else:
            print(f"    FILL RATE (trade-through): NOT APPLICABLE to improve "
                  f"orders — see the note in the source.")
        print(f"    pre-registered falsification: fill rate < 20%  -> "
              f"{'FALSIFIED' if 100*len(filled)/n < 20 else 'not falsified'}")
        if filled:
            mins = [r["mins_to_fill"] for r in filled if r["mins_to_fill"]]
            if mins:
                mins.sort()
                print(f"    minutes to fill: med {mins[len(mins)//2]:.0f}  "
                      f"p90 {mins[int(0.9*len(mins))]:.0f}")

        # ---------- THE ADVERSE-SELECTION TEST ----------
        # A resting bid at price P is a bet that P/100 understates the true
        # probability. If fills are unbiased, E[won | filled] == P/100. Adverse
        # selection is exactly the gap, and comparing filled vs UNFILLED on the
        # same orders controls for the price level being chosen.
        print(f"\n    ADVERSE SELECTION — did the fills know something?")
        for label, grp in (("FILLED", filled),
                           ("NOT FILLED", [r for r in sub if not r["filled"]])):
            if len(grp) < 10:
                print(f"      {label:11} n={len(grp)} — too few")
                continue
            edge = [r["won"] - r["price"] / 100.0 for r in grp]
            lo, hi = boot_ci(edge, [r["event"] for r in grp])
            print(f"      {label:11} n={len(grp):>6}  "
                  f"mean(outcome - price) = {100*np.mean(edge):+7.2f}pp  "
                  f"CI [{100*lo:+7.2f},{100*hi:+7.2f}]  "
                  f"(events {len({r['event'] for r in grp})})")
        unf = [r for r in sub if not r["filled"]]
        if len(filled) >= 10 and len(unf) >= 10:
            # Bootstrap the DIFFERENCE, clustered on the event. Reading two
            # overlapping CIs and inferring a difference is a standard error;
            # the difference has its own sampling distribution and this is it.
            rng = np.random.default_rng(SEED)
            byev = defaultdict(lambda: {"f": [], "u": []})
            for r in sub:
                byev[r["event"]]["f" if r["filled"] else "u"].append(
                    r["won"] - r["price"] / 100.0)
            keys = [k for k, v in byev.items() if v["f"] and v["u"]]
            diffs = np.empty(2000)
            for b in range(2000):
                pick = rng.choice(len(keys), size=len(keys), replace=True)
                f = np.concatenate([byev[keys[j]]["f"] for j in pick])
                u = np.concatenate([byev[keys[j]]["u"] for j in pick])
                diffs[b] = f.mean() - u.mean()
            lo, hi = np.percentile(diffs, [2.5, 97.5])
            gap = float(np.mean([r["won"] - r["price"] / 100.0 for r in filled])
                        - np.mean([r["won"] - r["price"] / 100.0 for r in unf]))
            print(f"      -> RAW filled minus unfilled = "
                  f"{100*gap:+.2f}pp   CI [{100*lo:+.2f},{100*hi:+.2f}]  "
                  f"(paired on {len(keys)} events)")

            # ---- PRICE-STRATIFIED, which removes the confound at source ----
            # The raw difference is biased because filled and unfilled orders
            # sit at DIFFERENT PRICES and `outcome - price` is not mean-zero
            # across the price range. Under a full outcome shuffle the raw
            # estimator still reads about -2pp, which is the bias measured.
            # Comparing only within the same 10c price bucket removes it, so
            # this - not the raw number - is the estimate to quote.
            num = den = 0.0
            per_bucket = []
            for b0 in range(0, 100, 10):
                fb = [r["won"] - r["price"] / 100.0 for r in filled
                      if b0 <= r["price"] < b0 + 10]
                ub = [r["won"] - r["price"] / 100.0 for r in unf
                      if b0 <= r["price"] < b0 + 10]
                if len(fb) < 10 or len(ub) < 10:
                    continue
                d_ = float(np.mean(fb) - np.mean(ub))
                w = min(len(fb), len(ub))
                num += d_ * w
                den += w
                per_bucket.append((b0, len(fb), len(ub), d_))
            if den:
                strat = num / den
                print(f"      -> PRICE-STRATIFIED filled minus unfilled = "
                      f"{100*strat:+.2f}pp  (weighted over "
                      f"{len(per_bucket)} price buckets)")
                for b0, nf, nu, d_ in per_bucket:
                    print(f"           {b0:>2}-{b0+10:<3}c  "
                          f"filled n={nf:>5} unfilled n={nu:>5}  "
                          f"{100*d_:+7.2f}pp")
            print(f"         negative = you are filled precisely when the "
                  f"price was too high. The free-roll.")
            print(f"         {'CI EXCLUDES ZERO — adverse selection is real'
                              if hi < 0 else 'CI contains zero'}")

            # ---------- NET P&L, the number that decides the strategy --------
            # A maker earns the price improvement and pays for being wrong.
            # Kalshi charges makers nothing on these series (fee_type
            # `quadratic`), so the fee term is ZERO here and is stated rather
            # than silently assumed — C1a is the correction where two rigorous
            # repos charged themselves a maker fee that does not apply.
            net = [100.0 * (r["won"] - r["price"] / 100.0) for r in filled]
            nlo, nhi = boot_ci([x / 100.0 for x in net],
                               [r["event"] for r in filled])
            print(f"\n    NET P&L PER FILLED CONTRACT (maker fee = 0 on these "
                  f"series, verified via fee_type)")
            print(f"      {np.mean(net):+7.2f}c   CI "
                  f"[{100*nlo:+7.2f},{100*nhi:+7.2f}]   n={len(filled):,} "
                  f"fills across {len({r['event'] for r in filled})} events")
            print(f"      naive benchmark — half the spread you were trying to "
                  f"earn: {np.median([r['spread'] for r in filled])/2:+.2f}c")

        # ---------- the Paradigm 'monopoly regime' hypothesis ----------
        # "the monopoly regime, when competitor quotes vanish, accounted for
        # 60% of total edge". Proxy: thin depth on the other side at placement.
        if len(filled) >= 30:
            d = [r["depth_other"] for r in sub]
            med = float(np.median(d))
            thin = [r for r in filled if r["depth_other"] <= med]
            thick = [r for r in filled if r["depth_other"] > med]
            print(f"\n    MONOPOLY-REGIME CHECK (Paradigm #2's 60%-of-edge claim)")
            for lab, g in (("thin other side", thin), ("thick", thick)):
                if len(g) < 10:
                    continue
                e = [r["won"] - r["price"] / 100.0 for r in g]
                lo, hi = boot_ci(e, [r["event"] for r in g])
                print(f"      {lab:18} n={len(g):>6}  edge "
                      f"{100*np.mean(e):+7.2f}pp  CI [{100*lo:+7.2f},{100*hi:+7.2f}]")

    # ------------------------------------------------------ NULL CONTROL ----
    # The standing rule: validate on data with NO effect and confirm none is
    # found. Here the effect is the LINK between getting filled and the
    # outcome. Permuting outcomes ACROSS EVENTS destroys that link while
    # preserving every other feature — the fill rate, the price distribution,
    # the clustering. If the measured adverse selection survives the shuffle,
    # it is an artifact of the estimator, not a property of the market.
    print("\n" + "=" * 78)
    print("NULL CONTROL — permute outcomes across events, 400 draws")
    print("=" * 78)
    rng = np.random.default_rng(SEED + 7)
    for mode in sorted({r["mode"] for r in rows}):
        sub = [r for r in rows if r["mode"] == mode]
        filled = [r for r in sub if r["filled"]]
        unf = [r for r in sub if not r["filled"]]
        if len(filled) < 10 or len(unf) < 10:
            continue
        obs = (np.mean([r["won"] - r["price"] / 100.0 for r in filled])
               - np.mean([r["won"] - r["price"] / 100.0 for r in unf]))
        # per-event outcome, permuted between events
        ev_out = {}
        for r in sub:
            ev_out.setdefault(r["event"], {})[r["ticker"]] = r["won"]
        evs = list(ev_out)
        null = np.empty(400)
        for b in range(400):
            perm = rng.permutation(len(evs))
            remap = {evs[i]: evs[perm[i]] for i in range(len(evs))}
            f, u = [], []
            for r in sub:
                donor = ev_out[remap[r["event"]]]
                w = donor.get(r["ticker"])
                if w is None:
                    w = next(iter(donor.values()))
                (f if r["filled"] else u).append(w - r["price"] / 100.0)
            null[b] = np.mean(f) - np.mean(u)
        p = float(np.mean(np.abs(null) >= abs(obs)))
        print(f"  {mode.upper():8} observed {100*obs:+7.2f}pp   "
              f"null mean {100*null.mean():+6.2f}pp  "
              f"null sd {100*null.std():5.2f}pp   "
              f"permutation p = {p:.4f}")
        print(f"           -> {'the shuffle DESTROYS it: the effect is in the data'
                               if p < 0.10 else
                               'survives the shuffle: TREAT AS AN ARTIFACT'}")

    (REP / "h10_orders.json").write_text(
        json.dumps({"n": len(rows), "rows": rows[:4000]}, indent=1,
                   default=str), encoding="utf-8")
    print(f"\nwrote reports/h10_orders.json ({len(rows)} orders)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample-minutes", type=int, default=20)
    ap.add_argument("--horizon", type=int, default=180)
    a = ap.parse_args()
    orders, outcomes = run(sample_minutes=a.sample_minutes,
                           horizon_minutes=a.horizon)
    report(summarise(orders, outcomes))
