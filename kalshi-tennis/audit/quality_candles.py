"""How good is the candle archive we already hold?

Not "does it exist" -- does it survive the checks a backtest depends on:
completeness per market, gaps, absent quotes, crossed books, and whether the
markets with no data are missing at random or concentrated somewhere that
would bias a result.
"""
import pathlib

import numpy as np
import pandas as pd

D = pathlib.Path(r"C:\Users\gianf\kalshi\set1_overshoot\data")
SRC = D / "candles_ohlc"


def main():
    uni = pd.read_parquet(D / "universe.parquet")
    # NB: these columns are datetime64[us], so .astype(int64) yields MICROseconds.
    # Going through total_seconds() keeps this correct whatever the unit is.
    o = pd.to_datetime(uni["open_time"], utc=True)
    c = pd.to_datetime(uni["close_time"], utc=True)
    uni["open_ts"] = o.astype("int64") // 10**6
    uni["close_ts"] = c.astype("int64") // 10**6
    uni["life_min"] = (c - o).dt.total_seconds() / 60

    parts = sorted(SRC.glob("*.parquet"))
    df = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
    print(f"candles      {len(df):,} rows   {df['ticker'].nunique():,} tickers")
    print(f"universe     {len(uni):,} markets\n")

    have = set(df["ticker"].unique())
    missing = uni[~uni["ticker"].isin(have)]
    print(f"markets with NO candle rows at all : {len(missing):,} "
          f"({len(missing) / len(uni) * 100:.2f}%)")
    if len(missing):
        print("   by series : " + str(missing["series"].value_counts().to_dict()))
        print("   by result : " + str(missing["result"].value_counts().to_dict()))
        print("   MAR check -- win rate of missing vs present:")
        wm = (missing["result"] == "yes").mean()
        wp = (uni[uni["ticker"].isin(have)]["result"] == "yes").mean()
        print(f"     missing yes-rate {wm:.4f}  present yes-rate {wp:.4f}"
              f"   gap {(wm - wp) * 100:+.2f} pp")

    g = df.groupby("ticker").agg(n=("ts", "size"), t0=("ts", "min"),
                                 t1=("ts", "max"))
    m = uni.set_index("ticker").join(g, how="inner")
    m["span_min"] = (m["t1"] - m["t0"]) / 60 + 1
    m["fill"] = m["n"] / m["span_min"].clip(lower=1)
    m["cover"] = m["span_min"] / m["life_min"].clip(lower=1)

    print("\nPER-MARKET COMPLETENESS (candles present / minutes spanned)")
    for q in (0.01, 0.05, 0.25, 0.5, 0.75, 0.95):
        print(f"   p{q * 100:>4.0f}  fill={m['fill'].quantile(q):6.3f}   "
              f"cover_of_listed_life={m['cover'].quantile(q):6.3f}")
    print(f"   markets with fill < 0.50 : {(m['fill'] < 0.5).sum():,}")
    print(f"   markets with < 10 candles: {(m['n'] < 10).sum():,}")

    print("\nQUOTE AVAILABILITY  (-1 = field absent in the API response)")
    for c in ("bid", "ask", "bid_h", "ask_l", "last"):
        absent = (df[c] == -1).mean() * 100
        print(f"   {c:6s} absent {absent:6.2f}%   "
              f"range [{df.loc[df[c] != -1, c].min()}, "
              f"{df.loc[df[c] != -1, c].max()}]")

    ok = df[(df["bid"] != -1) & (df["ask"] != -1)]
    crossed = (ok["bid"] > ok["ask"]).mean() * 100
    spread = (ok["ask"] - ok["bid"])
    print(f"\n   crossed (bid>ask)   {crossed:.4f}%  of {len(ok):,} two-sided rows")
    print(f"   spread cents        median {spread.median():.0f}  "
          f"mean {spread.mean():.2f}  p90 {spread.quantile(0.9):.0f}")
    print(f"   spread == 99c (1/100 quote) {(spread >= 98).mean() * 100:5.2f}%")
    print(f"   two-sided rows      {len(ok) / len(df) * 100:.2f}% of all rows")

    print("\n   ZERO-LIQUIDITY MINUTES (the mid-price trap)")
    for lo, hi, lab in ((0, 1, "bid=0"), (99, 100, "ask=100")):
        pass
    wide = ok[(ok["bid"] <= 1) & (ok["ask"] >= 99)]
    print(f"   rows quoting 0-1 / 99-100 : {len(wide):,} "
          f"({len(wide) / len(ok) * 100:.2f}%)")
    per = ok.groupby("ticker").apply(
        lambda d: ((d["bid"] <= 1) & (d["ask"] >= 99)).mean(),
        include_groups=False)
    print(f"   markets >50% of life at 0/100 quote: "
          f"{(per > 0.5).sum():,} / {len(per):,} ({(per > 0.5).mean() * 100:.1f}%)")

    print("\nVOLUME")
    vol = df.groupby("ticker")["vol"].max()
    print(f"   markets with zero traded volume ever: "
          f"{(vol == 0).sum():,} ({(vol == 0).mean() * 100:.1f}%)")
    for q in (0.1, 0.5, 0.9, 0.99):
        print(f"   p{q * 100:>4.0f} final volume {vol.quantile(q):,.0f}")


if __name__ == "__main__":
    main()
