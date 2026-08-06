r"""
t6_features.py - build a LEAK-FREE pre-match player-feature table.

Design fixed in advance: see ../PREREGISTRATION_T6.md.

WHAT THIS ANSWERS
    The user's question: Kalshi tennis is efficient in aggregate, but is it
    efficient once you condition on how the players have actually been
    performing? Recent form, head-to-head, rest, round, tier.

THE ONE RULE THAT MATTERS
    Every feature for a match is computed ONLY from matches that had already
    CLOSED before this match OPENED. `close_ts < open_ts`, strictly. No
    same-match leakage, no same-day leakage, no future results.

    This is enforced by a chronological single pass: features are read out of
    the running history BEFORE the match's own result is written into it.
    That ordering is the guard, and there is a test for it at the bottom.

UNIT AND DEDUPE
    One observation per EVENT, not per market. Kalshi lists two mirrored
    markets per match and their residuals are exactly anti-correlated, so
    keeping both would double n for free.

    The kept side is chosen by TICKER ORDER (alphabetically first). NEVER by
    volume / open interest / last price - that is the S011 bug that voided four
    phases of set1_overshoot. The selection canary at the end asserts
    P(kept side wins) = 0.50.

TARGET
    residual = outcome - implied,  implied = opening mid / 100.
    Not the raw win rate. A feature that picks favourites moves the win rate
    legitimately; to be an edge it must move the RESIDUAL.
"""
from __future__ import annotations
import os, sys, json, pickle, math, collections, re

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BT = os.path.abspath(os.path.join(HERE, "..", "..", "kalshi-inplay-bot", "backtest"))
# views.pkl holds pickled engine.MarketView objects, so `engine` must be
# importable before it can be unpickled.
if BT not in sys.path:
    sys.path.insert(0, BT)
OUT = os.path.abspath(os.path.join(HERE, "..", "out"))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
os.makedirs(OUT, exist_ok=True)
os.makedirs(DATA, exist_ok=True)

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 300)

DAY = 86400.0


# ----------------------------------------------------------------------
# round parsing, from the market title
# ----------------------------------------------------------------------
ROUND_PATTERNS = [
    (r"qualification final|qualifying final", "QualF"),
    (r"qualification|qualifying", "Qual"),
    (r"round of 128", "R128"),
    (r"round of 64", "R64"),
    (r"round of 32", "R32"),
    (r"round of 16", "R16"),
    (r"quarter.?final", "QF"),
    (r"semi.?final", "SF"),
    (r"\bfinal\b", "F"),
]
ROUND_ORDER = {"Qual": 0, "QualF": 1, "R128": 2, "R64": 3, "R32": 4,
               "R16": 5, "QF": 6, "SF": 7, "F": 8}


def parse_round(title: str) -> str:
    t = (title or "").lower()
    for pat, lab in ROUND_PATTERNS:
        if re.search(pat, t):
            return lab
    return "?"


def load_opening_prices():
    """Opening mid (cents) and opening spread per ticker, from the views."""
    with open(os.path.join(BT, "data", "views.pkl"), "rb") as f:
        views, _markets = pickle.load(f)
    op = {}
    for v in views:
        live = np.flatnonzero(v.live)
        if len(live) == 0:
            continue
        i = int(live[0])
        op[v.ticker] = (float(v.mid[i]), float(v.spread[i]), int(v.ts[i]),
                        int(v.n), str(v.tournament))
    return op


def build():
    mk = pd.read_parquet(os.path.join(BT, "data", "markets.parquet"))
    print(f"markets: {len(mk)}   events: {mk.event_ticker.nunique()}")

    op = load_opening_prices()
    print(f"tickers with an opening live price: {len(op)}")

    mk["open_mid"] = mk.ticker.map(lambda t: op.get(t, (np.nan,))[0])
    mk["open_spread"] = mk.ticker.map(
        lambda t: op.get(t, (np.nan, np.nan))[1] if t in op else np.nan)
    mk["round"] = mk.title.map(parse_round)

    # settlement is 1.0 / 0.0 already; keep only rows we can score and price
    mk = mk[mk.settlement.isin([0.0, 1.0]) & mk.open_mid.notna()].copy()
    print(f"scoreable + priced markets: {len(mk)}")

    # ---- collapse to one row per event, keeping BOTH players ----------
    # the kept SIDE is decided by ticker order; the other side supplies the
    # opponent's identity. This is the audited-clean dedupe rule.
    mk = mk.sort_values(["event_ticker", "ticker"], kind="mergesort")
    g = mk.groupby("event_ticker", sort=False)
    keep = g.head(1).set_index("event_ticker")
    other = g.tail(1).set_index("event_ticker")
    both = keep.join(other[["player", "settlement", "open_mid"]],
                     rsuffix="_opp", how="inner")
    both = both[both.index.map(g.size()) == 2]          # true mirrored pairs
    print(f"events with a clean mirrored pair: {len(both)}")

    both = both.reset_index().sort_values("open_ts", kind="mergesort")

    # ---- chronological pass: read history, THEN write it --------------
    hist = collections.defaultdict(list)     # player -> [(close_ts, won)]
    h2h = collections.defaultdict(list)      # (a,b) sorted -> [(close_ts, a_won)]
    rows = []

    # to_dict("records") rather than itertuples: "round" is awkward as a
    # namedtuple field and silently fell through to a tuple index.
    for r in both.to_dict("records"):
        pa, pb = r["player"], r["player_opp"]
        t0 = float(r["open_ts"])

        def feats(p):
            past = [(c, w) for (c, w) in hist[p] if c < t0]
            n = len(past)
            wins = sum(w for _, w in past)
            last3 = [w for _, w in past[-3:]]
            last5 = [w for _, w in past[-5:]]
            rest = (t0 - past[-1][0]) / DAY if n else np.nan
            in7 = sum(1 for c, _ in past if t0 - c <= 7 * DAY)
            return dict(n=n, wins=wins,
                        wr=wins / n if n else np.nan,
                        last3=np.mean(last3) if last3 else np.nan,
                        last5=np.mean(last5) if last5 else np.nan,
                        rest=rest, in7=in7)

        fa, fb = feats(pa), feats(pb)
        key = tuple(sorted((pa, pb)))
        hpast = [(c, w) for (c, w) in h2h[key] if c < t0]
        h_n = len(hpast)
        # h2h stored as "did the alphabetically-first player win"
        first_is_a = (key[0] == pa)
        h_a_wins = sum((w if first_is_a else (1 - w)) for _, w in hpast)

        outcome = float(r["settlement"])
        implied = float(r["open_mid"]) / 100.0

        rows.append(dict(
            event=r["event_ticker"], ticker=r["ticker"], tier=r["tournament"],
            round=r["round"],
            open_ts=int(r["open_ts"]), close_ts=int(r["close_ts"]),
            player=pa, opponent=pb,
            outcome=outcome, implied=implied,
            residual=outcome - implied,
            open_mid=float(r["open_mid"]), open_spread=float(r["open_spread"]),
            volume=float(r["volume"]),
            a_n=fa["n"], a_wr=fa["wr"], a_last3=fa["last3"], a_last5=fa["last5"],
            a_rest=fa["rest"], a_in7=fa["in7"],
            b_n=fb["n"], b_wr=fb["wr"], b_last3=fb["last3"], b_last5=fb["last5"],
            b_rest=fb["rest"], b_in7=fb["in7"],
            h2h_n=h_n, h2h_wins=h_a_wins,
        ))

        # ---- ONLY NOW write this match into history -------------------
        close = float(r["close_ts"])
        hist[pa].append((close, outcome))
        hist[pb].append((close, 1.0 - outcome))
        h2h[key].append((close, outcome if first_is_a else 1.0 - outcome))

    df = pd.DataFrame(rows)

    # ---- derived difference features ----------------------------------
    df["wr_diff"] = df.a_wr - df.b_wr
    df["last3_diff"] = df.a_last3 - df.b_last3
    df["last5_diff"] = df.a_last5 - df.b_last5
    df["rest_diff"] = df.a_rest - df.b_rest
    df["load_diff"] = df.a_in7 - df.b_in7
    df["exp_diff"] = df.a_n - df.b_n
    df["h2h_rate"] = np.where(df.h2h_n > 0, df.h2h_wins / df.h2h_n.replace(0, np.nan),
                              np.nan)
    df["round_ord"] = df["round"].map(ROUND_ORDER)
    df["fav"] = (df.open_mid >= 50).astype(int)

    # time-ordered split, fixed in the pre-registration
    df = df.sort_values("open_ts", kind="mergesort").reset_index(drop=True)
    cut = int(len(df) * 0.70)
    df["split"] = np.where(df.index < cut, "train", "holdout")

    df.to_csv(os.path.join(OUT, "t6_features.csv"), index=False)
    print(f"\nwritten: out/t6_features.csv   {len(df)} events "
          f"({(df.split=='train').sum()} train / {(df.split=='holdout').sum()} holdout)")
    return df


# ----------------------------------------------------------------------
# guards
# ----------------------------------------------------------------------
def guards(df):
    print("\n" + "=" * 74)
    print("GUARDS")
    print("=" * 74)

    # --- GUARD #1, selection canary on the dedupe rule -----------------
    p = df.outcome.mean()
    n = len(df)
    z = (p - 0.5) / math.sqrt(0.25 / n)
    verdict = "FAIL" if abs(z) > 4 else "PASS"
    print(f"selection canary  P(kept side wins) = {p:.4f}  n={n}  z={z:+.2f}"
          f"  -> {verdict}")
    print("  (ticker-order dedupe. NEVER volume - that is S011.)")

    # --- calibration of the market itself ------------------------------
    print(f"\nmarket calibration  mean residual = {df.residual.mean():+.4f}"
          f"  (0 = perfectly calibrated at the open)")
    for t, sub in df.groupby("tier"):
        se = sub.residual.std(ddof=1) / math.sqrt(len(sub))
        print(f"  {t:12s} n={len(sub):5d}  mean resid {sub.residual.mean():+.4f}"
              f"  se {se:.4f}  t={sub.residual.mean()/se:+.2f}")

    # --- leak check: a feature must not know the current result --------
    # if history were leaking, a player's prior-win-rate would correlate with
    # THIS match's outcome far beyond what the price already implies.
    sub = df[df.a_n >= 3].dropna(subset=["a_wr"])
    if len(sub) > 30:
        c_raw = np.corrcoef(sub.a_wr, sub.outcome)[0, 1]
        c_res = np.corrcoef(sub.a_wr, sub.residual)[0, 1]
        print(f"\nleak sanity  corr(prior winrate, outcome)  = {c_raw:+.4f}")
        print(f"             corr(prior winrate, residual) = {c_res:+.4f}  n={len(sub)}")
        print("  raw correlation SHOULD be positive (better players win more).")
        print("  residual correlation is the edge, and should be ~0 if the")
        print("  market already knows what we know.")

    # --- coverage -------------------------------------------------------
    print(f"\nfeature coverage (non-null):")
    for c in ["a_wr", "a_last3", "a_rest", "h2h_rate", "round_ord"]:
        print(f"  {c:10s} {df[c].notna().mean()*100:5.1f}%   "
              f"n={df[c].notna().sum()}")
    print(f"\nh2h with any prior meeting: {(df.h2h_n>0).sum()} events "
          f"({(df.h2h_n>0).mean()*100:.1f}%)")


if __name__ == "__main__":
    df = build()
    guards(df)
    print("\nrounds:", df["round"].value_counts().to_dict())
    print("tiers:", df.tier.value_counts().to_dict())
