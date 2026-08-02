"""Phase 1 -- clean the candle series and reconstruct match state from price.

Produces one row per match plus a fixed-width price path, so nothing downstream
has to touch the raw candles again.

Conventions, fixed here and used everywhere after:
  * All prices are integer cents.
  * The series is always expressed from the FAVOURITE's point of view. If the
    kept market's player is the underdog, the favourite is traded as the NO side
    of the same market, so fav_bid = 100 - kept_ask and fav_ask = 100 - kept_bid.
    That is the executable arithmetic, not a mid-price approximation.
  * t0 is the inferred first minute of play; the pre-match price is the last
    quote strictly before t0, so it cannot contain in-play information.
"""
import argparse
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

MAX_SPREAD = 15          # cents; wider quotes were never actionable
FFILL_MAX = 25           # minutes a stale quote is allowed to stand
# Play-window detector, tuned in p1_tune_t0.py against Sackmann playing minutes:
# gap alone let sparse pre-match repricing bleed in (median error +28 min,
# MAD 24). Adding an activity-density floor cut that to +6 min, MAD 5.
GAP_MIN = 12             # minutes of a frozen quote that ends the in-play run
DENS_WIN = 30            # window for the activity-density floor
DENS_MIN = 8             # quote changes required inside that window
PATH_MIN = 300           # minutes of path stored per match
MIN_PLAY = 25            # plausibility bounds on inferred match duration
MAX_PLAY = 330


def load_candles(subdir="candles"):
    parts = sorted((DATA / subdir).glob("*.parquet"))
    df = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    return df.sort_values(["ticker", "ts"], kind="stable")


def clean_one(ts, bid, ask, bid_h=None, ask_l=None):
    """Grid to 1-minute, mask unusable quotes, forward-fill within limits.

    Returns (minute_index, bid, ask, bid_high, ask_low, mid_x2, counts, n).
    mid_x2 is twice the mid so it stays an exact integer. -1 marks 'no usable
    quote'.

    bid_high / ask_low are the within-minute extremes, needed to answer "did the
    book trade THROUGH this price during this minute", which is the only honest
    way to decide whether a resting order would have filled. On a minute with no
    fresh candle the standing quote is carried in for all four series, since a
    stale quote has no range.
    """
    t_lo, t_hi = ts[0], ts[-1]
    n = int((t_hi - t_lo) // 60) + 1
    idx = ((ts - t_lo) // 60).astype(np.int64)
    b = np.full(n, -1, np.int32)
    a = np.full(n, -1, np.int32)
    bh = np.full(n, -1, np.int32)
    al = np.full(n, -1, np.int32)
    b[idx] = bid
    a[idx] = ask
    bh[idx] = bid_h if bid_h is not None else bid
    al[idx] = ask_l if ask_l is not None else ask

    absent = (b < 0) | (a < 0)
    crossed = ~absent & (a < b)
    wide = ~absent & ~crossed & ((a - b) > MAX_SPREAD)
    oob = ~absent & ((a > 100) | (b > 100))
    bad = absent | crossed | wide | oob
    b[bad] = -1
    a[bad] = -1
    bh[bad] = -1
    al[bad] = -1
    real = ~bad
    counts = (int(absent.sum()), int(crossed.sum()), int(wide.sum()),
              int(oob.sum()))

    # a quote stands until replaced; ffill across short holes only
    ok = np.where(b >= 0)[0]
    if len(ok) == 0:
        return None
    pos = np.searchsorted(ok, np.arange(n), side="right") - 1
    src = ok[np.clip(pos, 0, None)]
    use = (pos >= 0) & ((np.arange(n) - src) <= FFILL_MAX)
    filled_b = np.where(use, b[src], -1).astype(np.int32)
    filled_a = np.where(use, a[src], -1).astype(np.int32)
    # on a stale minute the standing quote is the whole range
    filled_bh = np.where(real, bh, filled_b).astype(np.int32)
    filled_al = np.where(real, al, filled_a).astype(np.int32)
    filled_bh = np.where(filled_b >= 0, filled_bh, -1)
    filled_al = np.where(filled_a >= 0, filled_al, -1)
    mid2 = np.where(filled_b >= 0, filled_b + filled_a, -1)
    return t_lo, filled_b, filled_a, filled_bh, filled_al, mid2, counts, n


def find_play_window(mid2, gap=None, dens_win=0, dens_min=0):
    """Infer [t0, t1]: the last contiguous run of price activity.

    Kalshi publishes no match-start field, so the start has to come from the
    price itself. Walking back from the final quote change and stopping at the
    first frozen stretch separates the match from the long dormant pre-match
    period. A pure gap rule alone lets sparse pre-match repricing bleed in, so
    an optional activity-density floor is applied first.
    """
    gap = GAP_MIN if gap is None else gap
    valid = mid2 >= 0
    changed = np.zeros(len(mid2), bool)
    changed[1:] = valid[1:] & valid[:-1] & (mid2[1:] != mid2[:-1])

    if dens_win:
        c = np.concatenate([[0], np.cumsum(changed)])
        n = len(mid2)
        lo = np.maximum(0, np.arange(n) - dens_win // 2)
        hi = np.minimum(n, np.arange(n) + dens_win // 2)
        dense = (c[hi] - c[lo]) >= dens_min
        changed = changed & dense

    ch = np.where(changed)[0]
    if len(ch) < 3:
        return None
    i = len(ch) - 1
    while i > 0 and (ch[i] - ch[i - 1]) < gap:
        i -= 1
    return int(ch[i]), int(ch[-1])


def find_play_start_causal(mid2, gap=None, dens_win=None, dens_min=None):
    """Forward-only match-start detector.

    find_play_window walks BACK from the last price change of the match, which
    means it uses information from after the entry decision. That is fine for a
    timing anchor and it is more accurate, but it must not be the only thing the
    study rests on. This version scans forward and fires the first time the
    trailing activity density clears the floor, using nothing after that minute.
    Results are reported under both.
    """
    gap = GAP_MIN if gap is None else gap
    dens_win = DENS_WIN if dens_win is None else dens_win
    dens_min = DENS_MIN if dens_min is None else dens_min
    valid = mid2 >= 0
    changed = np.zeros(len(mid2), bool)
    changed[1:] = valid[1:] & valid[:-1] & (mid2[1:] != mid2[:-1])
    c = np.concatenate([[0], np.cumsum(changed)])
    n = len(mid2)
    i = np.arange(n)
    trailing = c[i + 1] - c[np.maximum(0, i + 1 - dens_win)]
    hits = np.where(trailing >= dens_min)[0]
    if len(hits) == 0:
        return None
    # first firing minute; step back to the start of the burst that caused it
    f = int(hits[0])
    ch = np.where(changed[:f + 1])[0]
    if len(ch) == 0:
        return f
    j = len(ch) - 1
    while j > 0 and (ch[j] - ch[j - 1]) < gap:
        j -= 1
    return int(ch[j])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subdir", default="candles")
    ap.add_argument("--out", default="paths")
    ap.add_argument("--uni", default="universe.parquet")
    args = ap.parse_args()

    print("loading candles ...", flush=True)
    cd = load_candles(args.subdir)
    print(f"  {len(cd):,} rows, {cd['ticker'].nunique():,} markets", flush=True)

    uni = pd.read_parquet(DATA / args.uni)
    meta = uni.set_index("ticker")[
        ["event_ticker", "tour", "series", "result", "open_time",
         "close_time", "volume"]].to_dict("index")

    rows, paths_b, paths_a, paths_bh, paths_al = [], [], [], [], []
    n_wide = n_rows = n_grid = n_absent = n_cross = n_oob = 0
    grp_t = cd["ticker"].values
    grp_ts = cd["ts"].values
    grp_bid = cd["bid"].values.astype(np.int32)
    grp_ask = cd["ask"].values.astype(np.int32)
    grp_bh = cd["bid_h"].values.astype(np.int32)
    grp_al = (cd["ask_l"].values.astype(np.int32)
              if "ask_l" in cd.columns else grp_ask)
    grp_vol = cd["vol"].values.astype(np.int64)
    bounds = np.r_[0, np.where(grp_t[1:] != grp_t[:-1])[0] + 1, len(grp_t)]

    for k in range(len(bounds) - 1):
        s, e = bounds[k], bounds[k + 1]
        tick = grp_t[s]
        m = meta.get(tick)
        if m is None:                     # mirror-side market: skipped here
            continue
        res = clean_one(grp_ts[s:e], grp_bid[s:e], grp_ask[s:e],
                        grp_bh[s:e], grp_al[s:e])
        n_rows += e - s
        if res is None:
            rows.append({"ticker": tick, "ok": False, "why": "no_quotes"})
            for _L in (paths_b, paths_a, paths_bh, paths_al):
                _L.append(np.full(PATH_MIN, -1, np.int16))
            continue
        t_lo, b, a, bh, al, mid2, cnt, n = res
        n_absent += cnt[0]
        n_cross += cnt[1]
        n_wide += cnt[2]
        n_oob += cnt[3]
        nbad = sum(cnt)
        n_grid += n

        # A kept-market-oriented early price, recorded for EVERY market that
        # has any quote at all -- including the ones the play-window cut is
        # about to drop. Without it that cut is untestable, because dropped
        # rows would carry no price to form a calibration residual from. It is
        # deliberately orientation-free (kept market, not favourite) so it
        # exists even where the favourite cannot be identified.
        early = mid2[:max(1, int(0.6 * n))]
        early = early[early >= 0]
        fallback = float(np.median(early)) if len(early) else -1.0
        kept_won = int(m["result"] == "yes")

        w = find_play_window(mid2, GAP_MIN, DENS_WIN, DENS_MIN)
        if w is None:
            rows.append({"ticker": tick, "ok": False, "why": "no_activity",
                         "fallback_mid2": fallback, "kept_won": kept_won})
            for _L in (paths_b, paths_a, paths_bh, paths_al):
                _L.append(np.full(PATH_MIN, -1, np.int16))
            continue
        t0, t1 = w
        t0c = find_play_start_causal(mid2)
        t0c = t0 if t0c is None else t0c

        # pre-match quote: strictly before the first minute of play.
        # ASSERTION: this index is < t0 < any entry index, so no price used in
        # any decision can be timestamped at or after that decision.
        pre = t0 - 1
        while pre >= 0 and b[pre] < 0:
            pre -= 1
        assert pre < t0, "pre-match anchor is not strictly before t0"
        if pre < 0:
            rows.append({"ticker": tick, "ok": False, "why": "no_prematch",
                         "fallback_mid2": fallback, "kept_won": kept_won})
            for _L in (paths_b, paths_a, paths_bh, paths_al):
                _L.append(np.full(PATH_MIN, -1, np.int16))
            continue

        # ---- orient to the favourite -------------------------------------
        pre_mid2 = mid2[pre]
        kept_is_fav = pre_mid2 >= 100          # mid >= 50c
        if kept_is_fav:
            fb, fa, fbh, fal = b, a, bh, al
            fav_won = m["result"] == "yes"
        else:
            # The favourite is the NO side. Negating swaps bid and ask, and it
            # also swaps HIGH and LOW: the favourite's bid peaks exactly when
            # the kept market's ask bottoms out.
            fb = np.where(a >= 0, 100 - a, -1).astype(np.int32)
            fa = np.where(b >= 0, 100 - b, -1).astype(np.int32)
            fbh = np.where(al >= 0, 100 - al, -1).astype(np.int32)
            fal = np.where(bh >= 0, 100 - bh, -1).astype(np.int32)
            fav_won = m["result"] == "no"

        # sanity: the within-minute extremes must bracket the closes
        _v = (fb >= 0) & (fbh >= 0)
        assert np.all(fbh[_v] >= fb[_v]), "favourite bid high below bid close"
        _v = (fa >= 0) & (fal >= 0)
        assert np.all(fal[_v] <= fa[_v]), "favourite ask low above ask close"

        for src_arr, dst in ((fb, paths_b), (fa, paths_a),
                             (fbh, paths_bh), (fal, paths_al)):
            seg = src_arr[t0:t0 + PATH_MIN]
            p_ = np.full(PATH_MIN, -1, np.int16)
            p_[:len(seg)] = seg
            dst.append(p_)

        dur = t1 - t0
        vol_in = int(grp_vol[s:e][(grp_ts[s:e] - t_lo) // 60 >= t0].sum())

        # Guard against a late-detected t0 (a mid-match gap mistaken for the
        # start), which would silently turn an in-play quote into the
        # "pre-match" anchor. Two independent checks, both stored:
        #   flat_before -- how long the anchor quote had stood unchanged
        #   pre_mid_60  -- the mid a full hour earlier, which must agree
        j = pre
        while j > 0 and mid2[j - 1] == mid2[pre] and mid2[j - 1] >= 0:
            j -= 1
        flat_before = pre - j
        k60 = pre - 60
        pre60 = int(mid2[k60]) if k60 >= 0 and mid2[k60] >= 0 else -1
        if pre60 >= 0 and not kept_is_fav:
            pre60 = 200 - pre60
        rows.append({
            "ticker": tick,
            "event_ticker": m["event_ticker"],
            "tour": m["tour"],
            "ok": True, "why": "",
            "kept_is_fav": bool(kept_is_fav),
            "fav_won": bool(fav_won),
            "pre_bid": int(fb[pre]), "pre_ask": int(fa[pre]),
            "fallback_mid2": fallback, "kept_won": kept_won,
            "pre_idx": int(pre), "flat_before": int(flat_before),
            "t0_causal_delta": int(t0c - t0),
            "pre_mid2_60m": int(pre60),
            "t0_epoch": int(t_lo + t0 * 60),
            "t1_epoch": int(t_lo + t1 * 60),
            "dur_min": int(dur),
            "n_candles": int(e - s),
            "n_wide": int(nbad),
            "vol_inplay": vol_in,
            "close_time": m["close_time"],
            "plausible": bool(MIN_PLAY <= dur <= MAX_PLAY),
        })

    st = pd.DataFrame(rows)
    print(f"\ncandle rows seen                {n_rows:,}")
    print(f"1-minute grid slots             {n_grid:,}")
    g = max(n_grid, 1)
    print(f"  masked, no quote on either side   {n_absent:,}  "
          f"({n_absent / g:.1%})")
    print(f"  masked, crossed book              {n_cross:,}  "
          f"({n_cross / g:.1%})")
    print(f"  masked, spread > {MAX_SPREAD}c              {n_wide:,}  "
          f"({n_wide / g:.1%})")
    print(f"  masked, price out of range        {n_oob:,}  "
          f"({n_oob / g:.1%})")
    print(f"\nmarkets processed               {len(st):,}")
    print(st["why"].value_counts().to_string())
    good = st[st["ok"]]
    print(f"\nwith a play window              {len(good):,}")
    print(f"  duration plausible ({MIN_PLAY}-{MAX_PLAY}m)  "
          f"{good['plausible'].sum():,}")
    d = good["dur_min"]
    print(f"  duration  p10 {d.quantile(.1):.0f}  med {d.median():.0f}  "
          f"p90 {d.quantile(.9):.0f}  max {d.max():.0f}")
    pm = (good["pre_bid"] + good["pre_ask"]) / 2
    print(f"  pre-match mid  p10 {pm.quantile(.1):.0f}  med {pm.median():.0f}  "
          f"p90 {pm.quantile(.9):.0f}")
    print(f"  favourite won  {good['fav_won'].mean():.4f}  "
          f"(should be well above 0.5)")
    d0 = good["t0_causal_delta"]
    print(f"\ncausal vs backward-walk t0:  identical {(d0 == 0).mean():.3f}   "
          f"within 5 min {(d0.abs() <= 5).mean():.3f}   "
          f"median {d0.median():+.0f} min")
    print(f"pre-match anchor had been unchanged for: "
          f"median {good['flat_before'].median():.0f} min, "
          f"{(good['flat_before'] >= 10).mean():.1%} for 10+ min")
    p60 = good[good["pre_mid2_60m"] >= 0]
    agree = (np.abs(p60["pre_mid2_60m"]
                    - (p60["pre_bid"] + p60["pre_ask"])) <= 4).mean()
    print(f"pre-match mid agrees with the mid 60 min earlier (<=2c): "
          f"{agree:.3f}  (n={len(p60):,})")

    st.to_parquet(DATA / f"{args.out}_state.parquet", index=False)
    np.savez_compressed(DATA / f"{args.out}_paths.npz",
                        bid=np.array(paths_b, dtype=np.int16),
                        ask=np.array(paths_a, dtype=np.int16),
                        bid_h=np.array(paths_bh, dtype=np.int16),
                        ask_l=np.array(paths_al, dtype=np.int16),
                        ticker=st["ticker"].values.astype(str))
    print(f"\n-> {DATA / (args.out + '_state.parquet')}")
    print(f"-> {DATA / (args.out + '_paths.npz')}")


if __name__ == "__main__":
    main()
