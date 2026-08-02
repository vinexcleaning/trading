"""Download tennis-data.co.uk season files (ATP + WTA main tour).

Free, updated weekly, and carries closing bookmaker odds -- which gives an
independent market benchmark alongside Kalshi for Stages 4-5. No serve stats.
"""
import io
import pathlib

import pandas as pd
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "tennisdata"

BASE = "http://www.tennis-data.co.uk"
YEARS = range(2020, 2027)
TOURS = {"ATP": "{y}/{y}.xlsx", "WTA": "{y}w/{y}.xlsx"}

HEADERS = {"User-Agent": "Mozilla/5.0"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frames = []
    for tour, tmpl in TOURS.items():
        for y in YEARS:
            url = f"{BASE}/{tmpl.format(y=y)}"
            try:
                r = requests.get(url, headers=HEADERS, timeout=120)
                r.raise_for_status()
            except Exception as e:  # noqa: BLE001
                print(f"  {tour} {y}: {e!r}")
                continue
            dest = OUT / f"{tour}_{y}.xlsx"
            dest.write_bytes(r.content)
            df = pd.read_excel(io.BytesIO(r.content))
            df["tour"] = tour
            frames.append(df)
            d = pd.to_datetime(df["Date"], errors="coerce")
            print(f"  {tour} {y}: {len(df):5d} rows  {d.min().date()} .. {d.max().date()}")

    allm = pd.concat(frames, ignore_index=True)

    # Set/game score columns and odds are numeric but arrive with stray
    # whitespace tokens ('\t') in a few rows.
    score_cols = [f"{s}{i}" for s in ("W", "L") for i in range(1, 6)]
    odds_cols = [c for c in allm.columns
                 if c.startswith(("B365", "PS", "Max", "Avg", "EX", "LB", "SJ"))]
    for col in score_cols + odds_cols + ["WRank", "LRank", "WPts", "LPts",
                                         "Wsets", "Lsets", "Best of"]:
        if col in allm.columns:
            allm[col] = pd.to_numeric(allm[col], errors="coerce")

    allm["Date"] = pd.to_datetime(allm["Date"], errors="coerce")
    # The source has occasional year typos (a 2026 file row dated 2029).
    # Clamp to the file's own season rather than silently trusting it.
    yr = allm["Date"].dt.year
    bad = allm["Date"].isna() | (yr < 2019) | (yr > 2027)
    if bad.any():
        print(f"\n!! {bad.sum()} rows with implausible dates -- dropped:")
        print(allm.loc[bad, ["tour", "Date", "Tournament", "Winner", "Loser"]]
              .to_string(index=False))
        allm = allm[~bad].copy()

    for col in allm.columns:
        if allm[col].dtype == object:
            allm[col] = allm[col].astype("string")

    allm.to_parquet(OUT / "tennisdata_all.parquet", index=False)
    print(f"\ntotal {len(allm):,} rows -> {OUT / 'tennisdata_all.parquet'}")
    print(f"\ncolumns:\n{list(allm.columns)}")

    for t in ("ATP", "WTA"):
        d = allm.loc[allm["tour"] == t, "Date"]
        print(f"most recent {t} match: {d.max().date()}")
    print("\nsample of most recent rows:")
    cols = [c for c in ["Date", "Tournament", "Surface", "Round", "Winner",
                        "Loser", "WRank", "LRank", "Comment", "PSW", "PSL",
                        "AvgW", "AvgL"] if c in allm.columns]
    print(allm.sort_values("Date").tail(8)[cols].to_string(index=False))


if __name__ == "__main__":
    main()
