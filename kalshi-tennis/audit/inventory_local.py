"""Inventory every Kalshi dataset already on this machine.

Read-only. Touches nothing, writes nothing except stdout. Run it again any time
to re-check; it derives everything from the files themselves rather than from
any project's own claims about them.
"""
import json
import pathlib
import sys

import pandas as pd
import pyarrow.parquet as pq

ROOT = pathlib.Path(r"C:\Users\gianf\kalshi")


def hdr(s):
    print(f"\n{'=' * 78}\n{s}\n{'=' * 78}", flush=True)


def iso(v):
    try:
        return str(pd.to_datetime(v, utc=True, errors="coerce"))[:19]
    except Exception:  # noqa: BLE001
        return "?"


def markets_json(path, label):
    """markets_raw.json / tennis_markets.json -- dict-of-series or list."""
    if not path.exists():
        print(f"{label:34s} MISSING")
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    if isinstance(raw, dict):
        for series, ms in raw.items():
            for m in ms:
                m = dict(m)
                m["_series_pulled"] = series
                rows.append(m)
    else:
        rows = raw
    df = pd.DataFrame(rows)
    print(f"\n--- {label}  ({path.stat().st_size / 1e6:.0f} MB) ---")
    print(f"markets            {len(df):,}")
    if "_series_pulled" in df:
        print("by series pulled   "
              + ", ".join(f"{k}={v}" for k, v in
                          df["_series_pulled"].value_counts().items()))
    for col in ("status", "result", "market_type", "settlement_source"):
        if col in df:
            vc = df[col].astype(str).value_counts()
            print(f"{col:18s} " + ", ".join(f"{k}={v}" for k, v in
                                            vc.head(8).items()))
    for col in ("open_time", "close_time"):
        if col in df:
            s = pd.to_datetime(df[col], utc=True, errors="coerce")
            print(f"{col:18s} {iso(s.min())} -> {iso(s.max())}"
                  f"   ({s.isna().sum()} unparseable)")
    # which price fields actually carry data vs are all-null
    pricey = [c for c in df.columns
              if any(k in c for k in ("price", "bid", "ask", "volume",
                                      "open_interest", "liquidity"))]
    if pricey:
        print("price/vol fields   (non-null %)")
        for c in sorted(pricey):
            nn = df[c].notna().mean() * 100 if c in df else 0
            uniq = df[c].astype(str).nunique()
            print(f"   {c:28s} {nn:5.1f}%   distinct={uniq}")
    print(f"total columns      {len(df.columns)}")
    return df


def parquet_summary(path, label, timecols=("close_time", "ts", "end_period_ts")):
    if not path.exists():
        print(f"{label:34s} MISSING")
        return
    try:
        pf = pq.ParquetFile(path)
        n = pf.metadata.num_rows
        cols = [f.name for f in pf.schema_arrow]
    except Exception as e:  # noqa: BLE001
        print(f"{label:34s} UNREADABLE ({e})")
        return
    print(f"{label:34s} {n:>10,} rows  {len(cols):3d} cols  "
          f"{path.stat().st_size / 1e6:7.1f} MB")
    return cols


def candle_dirs():
    hdr("CANDLE / DEPTH DIRECTORIES")
    base = ROOT / "set1_overshoot" / "data"
    for d in sorted(p for p in base.iterdir() if p.is_dir()):
        files = list(d.rglob("*"))
        files = [f for f in files if f.is_file()]
        size = sum(f.stat().st_size for f in files)
        if not files:
            print(f"{d.name:22s} EMPTY")
            continue
        exts = {}
        for f in files:
            exts[f.suffix] = exts.get(f.suffix, 0) + 1
        mtimes = sorted(f.stat().st_mtime for f in files)
        print(f"{d.name:22s} {len(files):6,} files  {size / 1e6:8.1f} MB  "
              f"{exts}")
        print(f"{'':22s} written {iso(pd.to_datetime(mtimes[0], unit='s'))}"
              f" -> {iso(pd.to_datetime(mtimes[-1], unit='s'))}")
    for fail in sorted(base.glob("*failed*.txt")):
        n = len([x for x in fail.read_text().splitlines() if x.strip()])
        print(f"{fail.name:22s} {n:6,} FAILED tickers listed")


def candle_content():
    """Actually open the candle store and measure coverage."""
    hdr("CANDLE CONTENT (the file that backtests actually read)")
    for name in ("candles_ohlc", "candles", "candles_scalar"):
        d = ROOT / "set1_overshoot" / "data" / name
        parts = sorted(d.rglob("*.parquet"))
        if not parts:
            print(f"{name:16s} no parquet parts")
            continue
        tot, tmin, tmax, tickers = 0, None, None, set()
        cols = None
        for p in parts:
            try:
                df = pd.read_parquet(p)
            except Exception:  # noqa: BLE001
                continue
            cols = cols or list(df.columns)
            tot += len(df)
            tc = next((c for c in ("end_period_ts", "ts", "timestamp")
                       if c in df.columns), None)
            if tc:
                s = pd.to_datetime(df[tc], unit="s", utc=True, errors="coerce")
                tmin = s.min() if tmin is None else min(tmin, s.min())
                tmax = s.max() if tmax is None else max(tmax, s.max())
            if "ticker" in df.columns:
                tickers |= set(df["ticker"].unique())
        print(f"{name:16s} {tot:>10,} rows  {len(parts)} parts  "
              f"{len(tickers):,} tickers")
        print(f"{'':16s} window {iso(tmin)} -> {iso(tmax)}")
        print(f"{'':16s} cols {cols}")


def main():
    hdr("A. RAW MARKET PULLS")
    markets_json(ROOT / "set1_overshoot" / "data" / "markets_raw.json",
                 "set1_overshoot/markets_raw.json")
    markets_json(ROOT / "data" / "kalshi" / "tennis_markets.json",
                 "kalshi/tennis_markets.json (older pull)")

    hdr("B. DERIVED PARQUET")
    for p in sorted((ROOT / "set1_overshoot" / "data").glob("*.parquet")):
        parquet_summary(p, p.name)
    print()
    for p in sorted((ROOT / "data" / "cache").glob("*.parquet")):
        parquet_summary(p, "cache/" + p.name)

    candle_dirs()
    candle_content()


if __name__ == "__main__":
    sys.exit(main())
