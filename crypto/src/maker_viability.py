"""M1 — does a resting order capture enough spread to cover the pick-off cost?

Design fixed in advance: PREREGISTRATION_MAKER_VIABILITY.md (+ Amendment A1),
committed before any number from this design existed.

MM_RESULTS_MAKER.md section 6b measured one half: adverse selection costs
~0.5c/contract, negative on 8 of 8 days. This measures the other half.

  capture_c    = mid_at_fill - our_fill_price     (what resting paid us)
  adverse_c(D) = mid_at_fill - mid_at_fill+D      (what the market took back)
  net_c(D)     = mid_at_fill+D - our_fill_price - fee   == capture - adverse - fee

PRIMARY HORIZON IS 60 SECONDS, not settlement, and section 6b is why: marking to
settlement makes every fill in a day share one BTC trajectory, which is what made
the tape measurement unresolvable (day-clustered CI 7.78c vs event-clustered
1.36c). Settlement is reported beside it; if the two disagree in SIGN, that
disagreement is the finding and it means inventory rather than adverse selection
is fatal.

BOTH SIDES ARE QUOTED, because the placebo needs a side to randomise. A real
maker rests a yes-bid and a no-bid; a no-bid fill at q is a YES sale at 100-q.

Fills: trade-through only, last in queue -- reusing bot-hunt's engine rules.
H10 found that trade-through is meaningless for an IMPROVE order (the market's
best bid is BY CONSTRUCTION below our price, so the test fires immediately), so
JOIN is primary and IMPROVE is reported with that caveat.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT.parent / "bot-hunt" / "src"))
import replay as R  # noqa: E402
import venues as V  # noqa: E402
from common.kalshi_fees import SeriesFees, maker_fee_order_cents  # noqa: E402

L2 = ROOT.parent / "bot-hunt" / "data" / "l2"
REP = ROOT / "reports"
SERIES = "KXBTCD"
HORIZONS = [1, 10, 60, 300]          # seconds; 60 is PRIMARY
PRIMARY_H = 60
SAMPLE_MIN = 5                       # place a fresh pair every 5 minutes
MAX_HOLD_MIN = 60
N_BOOT = 4000
N_PERM = 300
SEED = 20260807


@dataclass
class Order:
    ticker: str
    side: str            # 'yes' = we rest a yes-bid; 'no' = we rest a no-bid
    mode: str            # 'join' | 'improve'
    price: int           # our resting price, in cents, on our own side
    queue_ahead: float
    placed_ts: datetime
    mid_at_place: float
    spread_c: float
    removed: float = 0.0
    through: bool = False
    filled_ts: datetime | None = None
    mid_at_fill: float | None = None
    perm_filled_ts: datetime | None = None
    perm_mid_at_fill: float | None = None
    marks: dict = field(default_factory=dict)


def mid_of(bk):
    yb, nb = bk.best_yes_bid(), bk.best_no_bid()
    if yb is None or nb is None:
        return None, None, None
    ask = 100 - nb
    if ask <= yb:
        return None, None, None          # crossed: not a tradeable book
    return (yb + ask) / 2.0, yb, ask


def run():
    files = sorted(L2.glob(f"btcd_*.parquet"))
    if not files:
        print("no btcd_*.parquet on disk - run the L2 pull first")
        return None
    print(f"replaying {len(files)} hourly files")

    live = defaultdict(list)
    done = []
    pending = defaultdict(list)      # filled orders awaiting horizon marks
    last_place = {}
    skipped = defaultdict(int)

    def on_event(ts, tk, bk, i, d):
        mid, yb, ask = mid_of(bk)
        if mid is None:
            skipped["no_two_sided_book"] += 1
            return
        side_ev = d["side"][i]
        price_c = R.to_cents(d["price"][i])
        delta = float(d["delta"][i])

        # ---- 1. mark any filled order whose horizon has arrived
        still_p = []
        for o in pending[tk]:
            for h in HORIZONS:
                if h not in o.marks and ts >= o.filled_ts + timedelta(seconds=h):
                    o.marks[h] = mid
            if len(o.marks) < len(HORIZONS):
                still_p.append(o)
            else:
                done.append(o)
        pending[tk] = still_p

        # ---- 2. progress live orders
        still = []
        for o in live[tk]:
            if side_ev == o.side and price_c == o.price and delta < 0:
                o.removed += -delta
            if o.mode == "join":
                best = bk.best_yes_bid() if o.side == "yes" else bk.best_no_bid()
                if best is not None and best < o.price:
                    o.through = True
            # TWO fill models, and the difference between them IS control N3.
            #
            # STRICT = the book must trade THROUGH our level AND our queue must
            # clear. PERMISSIVE = queue clears, nothing more. The pre-registered
            # N3 diagnostic requires the permissive arm to look MATERIALLY
            # BETTER; if it does not, the conservative model is not biting and
            # the engine is suspect.
            #
            # ⚠ BUG IN MY OWN v1, caught on the smoke test: I required
            # `through` for BOTH modes, and `through` is only ever set for
            # `join`. So IMPROVE could never fill and reported 0 fills. H10
            # documented why trade-through is meaningless for an improve order
            # -- the market's best bid is BY CONSTRUCTION below our price once
            # we have improved on it -- and I re-broke it in the other
            # direction. Improve now fills on queue depletion alone, which is
            # the only honest signal available for it, and is labelled as such.
            queue_clear = o.removed > o.queue_ahead
            strict_ok = queue_clear and (o.through or o.mode == "improve")
            if queue_clear and o.perm_filled_ts is None:
                o.perm_filled_ts = ts
                o.perm_mid_at_fill = mid
            if strict_ok and o.filled_ts is None:
                o.filled_ts = ts
                o.mid_at_fill = mid
                pending[tk].append(o)
                continue
            if ts - o.placed_ts > timedelta(minutes=MAX_HOLD_MIN):
                done.append(o)               # expired unfilled
                continue
            still.append(o)
        live[tk] = still

        # ---- 3. place a fresh pair on the cadence
        for mode in ("join", "improve"):
            for side in ("yes", "no"):
                key = (tk, mode, side)
                lp = last_place.get(key)
                if lp is not None and ts - lp < timedelta(minutes=SAMPLE_MIN):
                    continue
                base = bk.best_yes_bid() if side == "yes" else bk.best_no_bid()
                if base is None:
                    continue
                p = base if mode == "join" else base + 1
                other = (100 - bk.best_no_bid()) if side == "yes" else (100 - bk.best_yes_bid())
                if mode == "improve" and p >= other:
                    continue
                if p < 1 or p > 99:
                    continue
                last_place[key] = ts
                live[tk].append(Order(tk, side, mode, p,
                                      bk.size_at(side, p), ts, mid, ask - yb))

    R.replay(files, on_event=on_event, verbose=False)
    for tk, os_ in list(live.items()) :
        done.extend(os_)
    for tk, os_ in list(pending.items()):
        done.extend(os_)
    print(f"orders placed {len(done):,}   skipped {dict(skipped)}")
    return done


def analyse(orders):
    sf = None
    r = V.k_get(f"/series/{SERIES}")
    if r is not None and r.status_code == 200:
        obj = (r.json() or {}).get("series") or {}
        if "fee_type" in obj:
            sf = SeriesFees.from_api(obj)
    if sf is None:
        print("no fee schedule retrieved - refusing to price it")
        return {}
    print(f"fee schedule: {sf.fee_type}  charges_maker={sf.charges_maker}")

    rng = np.random.default_rng(SEED)
    out = {"series": SERIES, "fee_type": sf.fee_type}

    filled = [o for o in orders if o.filled_ts is not None and o.mid_at_fill]
    print(f"\nfill rate: {len(filled):,} of {len(orders):,} "
          f"({100*len(filled)/max(len(orders),1):.1f}%)")

    # ---- N4: an unfilled order must contribute exactly zero
    unfilled = [o for o in orders if o.filled_ts is None]
    assert all(not o.marks for o in unfilled), \
        "N4 FAILED: an unfilled order carries horizon marks"
    print(f"N4 OK: {len(unfilled):,} unfilled orders carry no marks")

    # ⚠⚠ MEASURED 2026-08-07, AND IT VOIDS THE IMPROVE ARM.
    #
    # The archive feed carries exactly two event types -- `orderbook_delta`
    # (822,213 rows in a sampled hour) and `orderbook_snapshot` (700). THERE IS
    # NO TRADE EVENT TYPE. A negative delta is a level shrinking, which is
    # EITHER a trade OR a cancellation, and nothing in the feed separates them.
    #
    # For JOIN the trade-through requirement is a real, if imperfect, filter:
    # the best bid must move below our price. For IMPROVE there is no such
    # filter available (H10 documented why), so `removed > queue_ahead` reduces
    # to `removed > 0` -- and EVERY CANCELLATION AT OUR PRICE COUNTS AS A FILL.
    #
    # That is why the smoke test showed IMPROVE at +1.506c capture and +1.700c
    # day-clustered net with a CI excluding zero, while JOIN -- the honest arm --
    # showed capture of MINUS 0.209c. A maker who "fills" whenever a neighbour
    # cancels is being handed the moments when the book is thin and the mid is
    # far from their price. It is the touch-counts-as-fill fake in a new costume,
    # and `high_sweep`'s header already calls that "the single easiest way to
    # fake a profitable backtest".
    #
    # IMPROVE is therefore reported as VOID, not as a result. Fixing it needs a
    # TRADE TAPE aligned to the book, which is a defined next step and not a
    # measurement this data can support.
    for mode in ("join", "improve"):
        sub = [o for o in filled if o.mode == mode and PRIMARY_H in o.marks]
        if mode == "improve":
            print("\n" + "=" * 70)
            print("IMPROVE — VOID, not reported as a result.")
            print("  The feed has no trade event type, so without trade-through")
            print("  a cancellation at our price is indistinguishable from a")
            print("  fill. Numbers below are printed for the record only.")
            print("=" * 70)
        if len(sub) < 20:
            print(f"\n{mode}: {len(sub)} fills with a {PRIMARY_H}s mark - too few")
            continue
        # yes-equivalent economics. A no-bid fill at q is a YES sale at 100-q,
        # so its P&L is the negative of a yes purchase at that price.
        cap, adv, net, day, ev, sgn = [], [], [], [], [], []
        for o in sub:
            fee = float(maker_fee_order_cents(o.price, 1, sf))
            s = 1.0 if o.side == "yes" else -1.0
            eff = o.price if o.side == "yes" else 100 - o.price
            c = s * (o.mid_at_fill - o.price) if o.side == "yes" \
                else ((100 - o.price) - o.mid_at_fill)
            a = s * (o.mid_at_fill - o.marks[PRIMARY_H])
            n = c - a - fee
            cap.append(c); adv.append(a); net.append(n)
            day.append(str(o.filled_ts)[:10]); ev.append(o.ticker); sgn.append(s)
        cap, adv, net = np.array(cap), np.array(adv), np.array(net)
        day, ev = np.array(day), np.array(ev)

        def clus(vals, keys):
            k, n = np_factor(keys)
            m = np.bincount(k, weights=vals, minlength=n) / np.bincount(k, minlength=n)
            return m

        dm, em = clus(net, day), clus(net, ev)
        bd = dm[rng.integers(0, len(dm), size=(N_BOOT, len(dm)))].mean(axis=1)
        be = em[rng.integers(0, len(em), size=(N_BOOT, len(em)))].mean(axis=1)
        dlo, dhi = np.percentile(bd, 2.5), np.percentile(bd, 97.5)
        elo, ehi = np.percentile(be, 2.5), np.percentile(be, 97.5)

        print(f"\n{'='*70}\n{mode.upper()}  fills={len(sub):,}  "
              f"days={len(dm)}  events={len(em)}\n{'='*70}")
        print(f"   capture           {cap.mean():+7.3f}c")
        print(f"   adverse @{PRIMARY_H}s      {adv.mean():+7.3f}c")
        print(f"   NET @{PRIMARY_H}s          {net.mean():+7.3f}c")
        print(f"   DAY-clustered     {dm.mean():+7.3f}c  95% CI "
              f"[{dlo:+.3f},{dhi:+.3f}]   width {dhi-dlo:.3f}c")
        print(f"   event-clustered   {em.mean():+7.3f}c  95% CI "
              f"[{elo:+.3f},{ehi:+.3f}]   width {ehi-elo:.3f}c"
              f"   -> DAY/EVENT width ratio {(dhi-dlo)/max(ehi-elo,1e-9):.2f}x")

        # ---- N1: the side placebo
        perm = []
        for _ in range(N_PERM):
            ss = rng.choice([1.0, -1.0], size=len(sub))
            c2 = np.where(ss > 0, cap, -cap)
            a2 = np.where(ss > 0, adv, -adv)
            perm.append(float(clus(c2 - a2, day).mean()))
        perm = np.array(perm)
        print(f"   N1 side placebo   {perm.mean():+7.3f}c  sd {perm.std():.3f}"
              f"   real-placebo {dm.mean()-perm.mean():+.3f}c")

        for h in HORIZONS:
            s2 = [o for o in sub if h in o.marks]
            if not s2:
                continue
            aa = np.array([(1.0 if o.side == "yes" else -1.0)
                           * (o.mid_at_fill - o.marks[h]) for o in s2])
            print(f"      adverse @{h:>4}s  {aa.mean():+7.3f}c  (n={len(s2):,})")

        out[mode] = {
            "fills": len(sub), "days": int(len(dm)), "events": int(len(em)),
            "capture_c": round(float(cap.mean()), 4),
            "adverse_c": round(float(adv.mean()), 4),
            "net_c": round(float(net.mean()), 4),
            "day_clustered": [round(float(dm.mean()), 4), round(float(dlo), 4),
                              round(float(dhi), 4)],
            "event_clustered": [round(float(em.mean()), 4), round(float(elo), 4),
                                round(float(ehi), 4)],
            "width_ratio_day_over_event": round(float((dhi-dlo)/max(ehi-elo, 1e-9)), 3),
            "n1_placebo_c": round(float(perm.mean()), 4),
        }
    return out


def np_factor(keys):
    uniq, codes = np.unique(keys, return_inverse=True)
    return codes, len(uniq)


def main():
    REP.mkdir(parents=True, exist_ok=True)
    orders = run()
    if not orders:
        return
    out = analyse(orders)
    (REP / "maker_viability.json").write_text(json.dumps(out, indent=1),
                                              encoding="utf-8")
    print("\nwrote reports/maker_viability.json")


if __name__ == "__main__":
    main()
