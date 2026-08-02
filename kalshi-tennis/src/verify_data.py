"""Sanity-check the archival mirror before building anything on it.

The upstream repos are gone, so the mirror's fidelity is an assumption that
needs testing, not trusting: schema, date coverage, and known results.
"""
import glob
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
SACK = ROOT / "data" / "sackmann"

EXPECTED_COLS = {
    "tourney_id", "tourney_name", "surface", "draw_size", "tourney_level",
    "tourney_date", "match_num", "winner_id", "winner_name", "winner_hand",
    "winner_ht", "winner_ioc", "winner_age", "loser_id", "loser_name",
    "loser_hand", "loser_ht", "loser_ioc", "loser_age", "score", "best_of",
    "round", "minutes", "w_ace", "w_df", "w_svpt", "w_1stIn", "w_1stWon",
    "w_2ndWon", "w_SvGms", "w_bpSaved", "w_bpFaced", "l_ace", "l_df",
    "l_svpt", "l_1stIn", "l_1stWon", "l_2ndWon", "l_SvGms", "l_bpSaved",
    "l_bpFaced", "winner_rank", "winner_rank_points", "loser_rank",
    "loser_rank_points",
}

GROUPS = {
    "atp_main": "atp/atp_matches_[12]*.csv",
    "atp_qual_chall": "atp/atp_matches_qual_chall_*.csv",
    "atp_futures": "atp/atp_matches_futures_*.csv",
    "wta_main": "wta/wta_matches_[12]*.csv",
    "wta_qual_itf": "wta/wta_matches_qual_itf_*.csv",
}


def load(pattern):
    files = sorted(glob.glob(str(SACK / pattern)))
    frames = []
    for f in files:
        try:
            frames.append(pd.read_csv(f, low_memory=False, encoding="utf-8",
                                      encoding_errors="replace"))
        except Exception as e:  # noqa: BLE001
            print(f"  !! unreadable {pathlib.Path(f).name}: {e!r}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def main():
    print("=" * 78)
    print("MIRROR VERIFICATION")
    print("=" * 78)
    all_frames = {}
    for name, pat in GROUPS.items():
        df = load(pat)
        all_frames[name] = df
        if df.empty:
            print(f"\n{name}: EMPTY")
            continue
        d = pd.to_datetime(df["tourney_date"], format="%Y%m%d", errors="coerce")
        missing = EXPECTED_COLS - set(df.columns)
        extra = set(df.columns) - EXPECTED_COLS
        has_serve = df["w_svpt"].notna() & (df["w_svpt"] > 0) if "w_svpt" in df else pd.Series(dtype=bool)
        print(f"\n{name}")
        print(f"  rows          {len(df):,}")
        print(f"  date range    {d.min().date()} .. {d.max().date()}")
        print(f"  serve stats   {has_serve.mean() * 100:.1f}% of rows")
        print(f"  missing cols  {sorted(missing) if missing else 'none'}")
        print(f"  extra cols    {sorted(extra) if extra else 'none'}")
        print(f"  surfaces      {df['surface'].value_counts(dropna=False).to_dict()}")

    print("\n" + "=" * 78)
    print("RECENCY (rows per month, last 8 months of data)")
    print("=" * 78)
    for name, df in all_frames.items():
        if df.empty:
            continue
        d = pd.to_datetime(df["tourney_date"], format="%Y%m%d", errors="coerce")
        recent = d[d >= d.max() - pd.Timedelta(days=250)]
        counts = recent.dt.to_period("M").value_counts().sort_index()
        print(f"\n{name}: " + "  ".join(f"{p}={c}" for p, c in counts.items()))

    print("\n" + "=" * 78)
    print("KNOWN-RESULT SPOT CHECKS")
    print("=" * 78)
    atp = all_frames["atp_main"]
    wta = all_frames["wta_main"]
    checks = [
        (atp, 2019, "Wimbledon", "F", "Djokovic beat Federer 2019 Wimbledon final"),
        (atp, 2008, "Wimbledon", "F", "Nadal beat Federer 2008 Wimbledon final"),
        (atp, 2023, "Us Open", "F", "Djokovic beat Medvedev 2023 US Open final"),
        (wta, 2017, "Us Open", "F", "Stephens beat Keys 2017 US Open final"),
    ]
    for df, year, tourney, rnd, label in checks:
        d = pd.to_datetime(df["tourney_date"], format="%Y%m%d", errors="coerce")
        sel = df[(d.dt.year == year)
                 & df["tourney_name"].str.contains(tourney, case=False, na=False)
                 & (df["round"] == rnd)]
        if sel.empty:
            print(f"  MISSING: {label}")
        else:
            r = sel.iloc[0]
            print(f"  {r['winner_name']} d. {r['loser_name']} {r['score']}   <- {label}")

    print("\n" + "=" * 78)
    print("PLAYER / RANKING FILES")
    print("=" * 78)
    for tour in ("atp", "wta"):
        p = pd.read_csv(SACK / tour / f"{tour}_players.csv", low_memory=False,
                        encoding="utf-8", encoding_errors="replace")
        rk = pd.read_csv(SACK / tour / f"{tour}_rankings_current.csv", low_memory=False)
        rd = pd.to_datetime(rk["ranking_date"], format="%Y%m%d", errors="coerce")
        print(f"  {tour}_players.csv    {len(p):,} rows, cols={list(p.columns)}")
        print(f"  {tour}_rankings_current  {len(rk):,} rows, latest={rd.max().date()}")


if __name__ == "__main__":
    main()
