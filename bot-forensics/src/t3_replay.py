"""
t3_replay.py - TASK 3. The decisive test.

Runs THE ACTUAL CONFIGURATION THAT WAS LIVE on 27-28 July over the 14,162-market
backtest data, using the bot's own decision code.

WHAT IS FAITHFUL HERE
    * `tennis_engine.evaluate()` is imported and called. The entry rules are
      not reimplemented, they are the same function the live bot ran.
    * The night's Config is reconstructed from the dated comments in
      tennis_engine.py plus the order record (see FINDINGS.md): no price floor,
      85c favourite cap, 22c stop, 10 concurrent positions, no daily loss
      limit, and none of the 3 Aug runaway guards.
    * Real set scores from `backtest/data/sofascore_matches.jsonl` (1,406
      matches with reconstructed set boundaries) supply `sets_won`,
      `sets_lost` and `set_scores`, so `require_set_resolved` and
      `min_set_margin` are evaluated for real rather than proxied by price.
    * Execution and exits use `backtest/engine._walk`, the same causal replay
      the 480-config sweep used: buy at the next candle's ask + 1c slippage,
      stop-before-target on same-candle ties, exact Decimal fees, hold to
      settlement if neither fires.
    * One position per EVENT at a time, exactly as strategies.py does.

WHAT IS NOT, AND CANNOT BE
    * Score coverage is 1,406 of ~7,081 matches. The scored subset is what it
      is; it was not chosen by outcome, but it is not the whole book.
    * The candle grid is 1 minute. The live bot polled every ~20-60s. Entries
      here are on a coarser clock.
    * `score_age_sec` is set to 0, i.e. THE STALE-SCORE BUG IS SWITCHED OFF.
      This test therefore measures the strategy as DESIGNED, which is the more
      generous reading. The live bot had a feed arriving after the market had
      already moved (FINDINGS.md), so the live result should if anything be
      worse than this.

BENCHMARKS it is ranked against, all from BACKTEST_RESULTS.md, metric =
net cents per trade:
    480-config sweep      -11.43 .. -4.90   (0 of 480 positive)
    S5 random entry        -8.28
    S1 the v3 strategy     -9.36
    S2 buy and hold        -2.29   <- the best thing anyone has found here
"""
from __future__ import annotations
import sys, os, json, pickle, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
BT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "..", "..", "kalshi-inplay-bot", "backtest"))
BOT = os.path.dirname(BT)
for p in (BT, BOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
import pandas as pd
import engine
from engine import _walk
import tennis_engine as te

# `autoscan._name_matches` decides which side of a Sofascore match a Kalshi
# market is about. pull_scores.py and score_test.py both use it, so this replay
# must use the SAME function or the join differs.
#
# Importing autoscan outright pulls in kalshi_client -> requests -> the live
# order-signing path, which a read-only forensic script has no business
# loading. So the module's source is executed up to the first dataclass, with
# only the two live-stack imports filtered out. Nothing is retyped, and the
# cut point is asserted rather than assumed.
def _load_autoscan_names():
    src_path = os.path.join(BOT, "autoscan.py")
    with open(src_path, encoding="utf-8") as f:
        lines = f.readlines()
    cut = next(i for i, ln in enumerate(lines) if ln.startswith("@dataclass"))
    body = [ln for ln in lines[:cut]
            if not ln.startswith(("from kalshi_client", "from sofascore_feed",
                                  "from tennis_engine"))]
    ns = {"__name__": "_autoscan_names"}
    exec(compile("".join(body), src_path, "exec"), ns)
    assert "_name_matches" in ns and "_norm" in ns, "autoscan layout changed"
    return ns["_name_matches"]


_name_matches = _load_autoscan_names()

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 400)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
SLIP = 1.0

# ----------------------------------------------------------------------
# the two configurations
# ----------------------------------------------------------------------
BIG = 10 ** 9

NIGHT = te.Config(
    bankroll=125.0, stake_pct=5.0,
    min_entry_price=1,            # the 60c floor was added ON 28 Jul
    max_favorite_price=85,        # "75c, not 85c" - 85 was what ran
    thin_favorite_price=70,
    max_divergence_price=70,
    favorite_threshold=60, underdog_threshold=40,
    min_set_margin=2,
    favorite_target_price=95,
    favorite_exit_drop=22,        # "38c, widened from 22c on 28 Jul"
    divergence_exit_pct=0.40,
    max_open_positions=10,        # "Cut 10 -> 4 on 28 Jul"
    reentry_slots=1,
    max_daily_loss_pct=0.0,       # off
    max_contracts=BIG,            # did not exist
    reentry_cooldown_sec=0,       # did not exist
    max_reentries_per_event=BIG,  # did not exist
    max_hold_minutes=0,
    max_spread=3,
    require_set_resolved=True,
)

CURRENT = te.Config()             # whatever is in the file today

import dataclasses as _dc


def _v(base, **kw):
    return _dc.replace(base, **kw)


VARIANTS = {
    # the reconstructed live configuration
    "NIGHT (as it ran 27-28 Jul)": NIGHT,
    # the same, floored at the cheapest entry the bot actually took live (25c).
    # Live it never went below 24c; the unrestricted config will, and the
    # sub-40c region is a different trade. This isolates that.
    "NIGHT floored at 25c (live band)": _v(NIGHT, min_entry_price=25),
    # the 60c floor added ON 28 Jul, everything else as the night
    "NIGHT + the 60c floor only": _v(NIGHT, min_entry_price=60),
    # the 38c stop adopted on 28 Jul, everything else as the night
    "NIGHT + the 38c stop only": _v(NIGHT, favorite_exit_drop=38),
    # no stop at all - the backtest's own best strategy was hold-to-settlement
    "NIGHT + no stop (hold to settle)": _v(NIGHT, favorite_exit_drop=99,
                                           divergence_exit_pct=0.99),
    "CURRENT (post 3 Aug fixes)": CURRENT,
}


# ----------------------------------------------------------------------
# data
# ----------------------------------------------------------------------
def load_all():
    with open(os.path.join(BT, "data", "views.pkl"), "rb") as f:
        views, markets = pickle.load(f)
    scores = {}
    with open(os.path.join(BT, "data", "sofascore_matches.jsonl"),
              encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("boundaries") and r.get("sets"):
                scores[r["event"]] = r
    return views, markets, scores


def score_track(v, m, sc):
    """For each candle index, (sets_won, sets_lost, [(mine,theirs), ...]).

    Set boundaries come from Sofascore durations as reconstructed by
    pull_scores.py. A set counts only once its end_ts has passed, so nothing
    here reads the future.
    """
    player = m.player
    if _name_matches(player, sc.get("home") or ""):
        me, them = "home", "away"
    elif _name_matches(player, sc.get("away") or ""):
        me, them = "away", "home"
    else:
        return None
    bounds = sorted(sc["boundaries"], key=lambda b: b["set"])
    sets = sc["sets"]
    ends, pairs = [], []
    for b in bounds:
        g = sets.get(f"set{b['set']}") or {}
        a, d = g.get(me), g.get(them)
        if a is None or d is None:
            continue
        ends.append(b["end_ts"])
        pairs.append((int(a), int(d)))
    ends = np.array(ends, dtype=np.int64)
    # number of completed sets at each candle
    k = np.searchsorted(ends, v.ts, side="right")
    return k, pairs


def replay(views, markets, scores, cfg, label, restrict=None):
    by_tk = markets.set_index("ticker")
    cand = []
    seen_events = set()
    n_scored = 0
    for v in views:
        if np.isnan(v.settlement) or v.live.sum() < 10:
            continue
        if restrict is not None and v.event not in restrict:
            continue
        try:
            m = by_tk.loc[v.ticker]
        except KeyError:
            continue
        sc = scores.get(v.event)
        if sc is None:
            continue
        tr = score_track(v, m, sc)
        if tr is None:
            continue
        k, pairs = tr
        n_scored += 1
        seen_events.add(v.event)
        opened = float(v.mid[0])
        live_idx = np.flatnonzero(v.live)
        for i in live_idx:
            if i + 1 >= v.n:
                break
            nk = int(k[i])
            if nk == 0:
                continue                        # no set resolved yet
            done = pairs[:nk]
            sw = sum(1 for a, d in done if a > d)
            sl = nk - sw
            ask = int(round(v.ask_close[i]))
            bid = int(round(v.bid_close[i]))
            if not (1 <= ask <= 99):
                continue
            snap = te.Snapshot(
                player=str(m.player), match=v.event,
                ask=ask, bid=bid, depth_at_ask=10 ** 6,
                sets_won=sw, sets_lost=sl, set_in_progress=True,
                was_prematch_favorite=opened >= cfg.favorite_threshold,
                set_scores=list(done), open_price=int(round(opened)),
                score_age_sec=0, market_open=True, postponed=False,
                open_positions=0, daily_pnl_pct=0.0,
                already_hold_other_side=False, is_reentry=False,
            )
            d = te.evaluate(cfg, snap)
            if not d.take:
                continue
            cand.append((int(v.ts[i]), v, i, d))

    # Execute in time order, one position per event at a time. Re-entry after
    # an exit is permitted, which is what the night's config did - it had no
    # cooldown and no cap. The CURRENT config's 3 Aug guards
    # (reentry_cooldown_sec, max_reentries_per_event) are applied here so the
    # two are compared on their own terms rather than on the night's rules.
    #
    # THE PORTFOLIO CAP IS A REAL CONSTRAINT AND HAS TO BE HERE. Without it the
    # night's config takes ~8 entries per match at a 23c average, because with
    # no price floor and no cooldown every stop-out immediately re-qualifies.
    # Live it took 1.2 entries per match at a 65c average - because
    # max_open_positions physically capped it. Omitting the cap does not make
    # the test conservative, it makes it a different strategy.
    cand.sort(key=lambda x: x[0])
    busy, last_exit, nre = {}, {}, {}
    trades = []
    open_until = []                      # exit timestamps of live positions
    for ets, v, i, d in cand:
        open_until = [x for x in open_until if x > ets]
        if len(open_until) >= cfg.max_open_positions:
            continue
        if ets < busy.get(v.event, 0):
            continue
        if v.event in last_exit:
            if nre.get(v.event, 0) >= cfg.max_reentries_per_event:
                continue
            if ets - last_exit[v.event] < cfg.reentry_cooldown_sec:
                continue
            if cfg.reentry_respects_price_floor and \
                    round(v.ask_close[i]) < cfg.min_entry_price:
                continue
        e = engine._enter(v, i + 1, SLIP)
        if e is None:
            continue
        px, _ = e
        qty = max(1, int((cfg.bankroll * cfg.stake_pct / 100) / (px / 100)))
        qty = min(qty, cfg.max_contracts)
        target = float(cfg.favorite_target_price) if d.setup is te.Setup.FAVORITE \
            else float(d.target_price)
        stop = max(1.0, px - cfg.favorite_exit_drop) if d.setup is te.Setup.FAVORITE \
            else max(1.0, round(px * (1 - cfg.divergence_exit_pct)))
        tl = cfg.max_hold_minutes if cfg.max_hold_minutes > 0 else None
        t = _walk(v, i + 1, px, qty, target, stop, SLIP, tl, None)
        if t is None:
            continue
        t.spread = float(v.spread[i])
        trades.append(t)
        open_until.append(t.exit_ts)
        busy[v.event] = t.exit_ts
        if v.event in last_exit:
            nre[v.event] = nre.get(v.event, 0) + 1
        last_exit[v.event] = t.exit_ts
    return trades, n_scored, len(seen_events)


def summarize(trades, label):
    if not trades:
        return {"config": label, "trades": 0}
    df = pd.DataFrame([t.__dict__ for t in trades])
    df["net_c"] = df.net / df.contracts * 100.0
    # cluster at MATCH level - a match is one observation
    per_match = df.groupby("event").net.sum()
    se_m = per_match.std(ddof=1) / math.sqrt(len(per_match))
    return {
        "config": label,
        "trades": len(df), "matches": df.event.nunique(),
        "trades_per_match": len(df) / df.event.nunique(),
        "win_rate": (df.net > 0).mean() * 100,
        "net_$": df.net.sum(),
        "net_c_per_trade": df.net_c.mean(),
        "net_$_per_match": per_match.mean(),
        "se_$_per_match": se_m,
        "t_match": per_match.mean() / se_m if se_m else np.nan,
        "fees_$": df.fees.sum(),
        "avg_entry": df.entry.mean(),
        "settle_frac": (df.reason == "settlement").mean(),
        "stop_frac": (df.reason == "stop").mean(),
        "target_frac": (df.reason == "target").mean(),
    }


if __name__ == "__main__":
    views, markets, scores = load_all()
    print(f"views {len(views):,}   markets {len(markets):,}   "
          f"score-joined events {len(scores):,}")

    # train/holdout split, same function the sweep used
    import strategies as st
    tr, ho = st.split(views, markets)
    tr_ev = {v.event for v in tr}
    ho_ev = {v.event for v in ho}
    print(f"train events {len(tr_ev):,}   holdout events {len(ho_ev):,}")
    print(f"score-joined that are in holdout: "
          f"{len(set(scores) & ho_ev):,} / {len(scores):,}")

    rows = []
    keep = {}
    for label, cfg in VARIANTS.items():
        for scope, restrict in (("ALL", None), ("train", tr_ev), ("HOLDOUT", ho_ev)):
            trades, nsc, nev = replay(views, markets, scores, cfg, label, restrict)
            r = summarize(trades, f"{label} [{scope}]")
            r["scored_markets"] = nsc
            rows.append(r)
            if scope == "ALL":
                keep[label] = trades
            print(f"  {label:32s} {scope:8s} -> {r.get('trades', 0):5d} trades "
                  f"on {r.get('matches', 0):4d} matches, "
                  f"{r.get('net_c_per_trade', float('nan')):+.2f} c/trade")

    T = pd.DataFrame(rows)
    print()
    print("=" * 78)
    print("TASK 3 - the live configuration replayed on the backtest data")
    print("=" * 78)
    print(T.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    T.to_csv(os.path.join(OUT, "t3_replay.csv"), index=False)

    # ---------------- ranking against the 480-config sweep ---------------
    print()
    print("=" * 78)
    print("WHERE IT RANKS")
    print("=" * 78)
    BENCH = [("480-sweep best", -4.90), ("S2 buy&hold (best known)", -2.29),
             ("S5 random entry", -8.28), ("S1 the v3 strategy", -9.36),
             ("480-sweep worst", -11.43)]
    main = T[T.config.str.contains(r"NIGHT.*\[ALL\]", regex=True)]
    if len(main) and main.iloc[0].trades:
        v = float(main.iloc[0].net_c_per_trade)
        print(f"NIGHT config, all scored markets: {v:+.2f} c/trade")
        for nm, b in sorted(BENCH + [("** the night's config **", v)],
                            key=lambda z: -z[1]):
            print(f"    {b:+7.2f}  {nm}")
        print()
        n_worse = sum(1 for _, b in BENCH if b < v)
        print(f"The 480-config sweep spans -11.43 to -4.90 with 0 positive.")
        if v > -4.90:
            print(f"At {v:+.2f} the night's configuration would have ranked "
                  f"FIRST of 481 - above the entire sweep.")
        elif v < -11.43:
            print(f"At {v:+.2f} it would have ranked LAST of 481.")
        else:
            frac = (v - (-11.43)) / ((-4.90) - (-11.43))
            print(f"At {v:+.2f} it sits {frac:.0%} of the way up the sweep's "
                  f"range, i.e. roughly rank {int((1 - frac) * 480) + 1} of 481.")

    # ---------------- by tier and by band --------------------------------
    for label, trades in keep.items():
        if not trades:
            continue
        df = pd.DataFrame([t.__dict__ for t in trades])
        df["net_c"] = df.net / df.contracts * 100
        print(f"\n--- {label}: by tournament")
        print(df.groupby("tournament").agg(
            trades=("net", "size"), matches=("event", "nunique"),
            net=("net", "sum"), c_per_trade=("net_c", "mean")).round(2).to_string())
        print(f"--- {label}: by entry price band")
        df["band"] = pd.cut(df.entry, [0, 40, 50, 60, 70, 80, 100])
        print(df.groupby("band", observed=True).agg(
            trades=("net", "size"), net=("net", "sum"),
            c_per_trade=("net_c", "mean")).round(2).to_string())
        print(f"--- {label}: by exit reason")
        print(df.groupby("reason").agg(
            trades=("net", "size"), net=("net", "sum"),
            c_per_trade=("net_c", "mean")).round(2).to_string())
        pd.DataFrame([t.__dict__ for t in trades]).to_csv(
            os.path.join(OUT, f"t3_trades_{label.split()[0]}.csv"), index=False)
