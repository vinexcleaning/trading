"""Phase 0b -- build the match universe: parse markets, verify the mirror
relationship, dedupe to one market per match.

Nothing about prices happens here. This produces the fetch list for candles and
the counts that go into the Phase 0 report.
"""
import collections
import datetime as dt
import json
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

SERIES_LABEL = {
    "KXATPMATCH": "ATP",
    "KXWTAMATCH": "WTA",
    "KXATPCHALLENGERMATCH": "CHALL",
    "KXITFMATCH": "ITF-M",
    "KXITFWMATCH": "ITF-W",
}


def ts(s):
    if not s:
        return None
    return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))


def main():
    raw = json.loads((DATA / "markets_raw.json").read_text(encoding="utf-8"))

    rows = []
    for series, mkts in raw.items():
        for m in mkts:
            rows.append({
                "series": series,
                "tour": SERIES_LABEL[series],
                "event_ticker": m.get("event_ticker"),
                "ticker": m.get("ticker"),
                "status": m.get("status"),
                "result": m.get("result"),
                "settlement_value": m.get("settlement_value_dollars"),
                "expiration_value": m.get("expiration_value"),
                "yes_sub_title": m.get("yes_sub_title"),
                "no_sub_title": m.get("no_sub_title"),
                "title": m.get("title"),
                "open_time": ts(m.get("open_time")),
                "close_time": ts(m.get("close_time")),
                "occurrence": ts(m.get("occurrence_datetime")),
                "expected_exp": ts(m.get("expected_expiration_time")),
                "settlement_ts": ts(m.get("settlement_ts")),
                "volume": float(m.get("volume_fp") or 0),
                "rules_primary": m.get("rules_primary") or "",
            })
    df = pd.DataFrame(rows)
    print(f"raw markets                     {len(df):,}")

    # --- keep only decided markets -----------------------------------------
    df = df[df["status"].isin(["finalized", "settled", "closed"])].copy()
    print(f"finalized/settled/closed        {len(df):,}")
    df = df[df["result"].isin(["yes", "no"])].copy()
    print(f"with a yes/no result            {len(df):,}")

    # --- mirror structure ---------------------------------------------------
    per_event = df.groupby("event_ticker").size()
    print("\nmarkets per event:")
    for k, v in per_event.value_counts().sort_index().items():
        print(f"   {k} market(s): {v:,} events")

    two = set(per_event[per_event == 2].index)
    df["paired"] = df["event_ticker"].isin(two)

    # settlement sanity: a 2-market event must have exactly one yes
    g = df[df["paired"]].groupby("event_ticker")["result"]
    nyes = g.apply(lambda s: (s == "yes").sum())
    bad = nyes[nyes != 1]
    print(f"\npaired events                   {len(nyes):,}")
    print(f"  with exactly one YES          {(nyes == 1).sum():,}")
    print(f"  inconsistent (dropped)        {len(bad):,}")
    df = df[~df["event_ticker"].isin(set(bad.index))].copy()

    # --- dates ---------------------------------------------------------------
    df["date"] = df["close_time"].dt.date
    print(f"\ndate range (close_time)         "
          f"{df['date'].min()} .. {df['date'].max()}")

    dur = (df["close_time"] - df["open_time"]).dt.total_seconds() / 3600
    print(f"open->close hours  median {dur.median():.1f}  "
          f"p10 {dur.quantile(.1):.1f}  p90 {dur.quantile(.9):.1f}  "
          f"max {dur.max():.1f}")

    # --- per series -----------------------------------------------------------
    print("\nper-series decided markets:")
    for s, sub in df.groupby("tour"):
        ev = sub["event_ticker"].nunique()
        print(f"   {s:6s} {len(sub):7,} markets  {ev:7,} events  "
              f"{sub['date'].min()} .. {sub['date'].max()}")

    # --- choose one market per event -------------------------------------------
    # DEDUPE MUST NOT LOOK AT THE OUTCOME.
    #
    # The first version of this kept the higher-volume side. Volume is read from
    # the API *after* settlement, and the winning side attracts more trading, so
    # that rule selected on the outcome: the higher-volume side wins 53.56% of
    # the time (z = +10.0). Open interest is worse still (55.58%, z = +15.8).
    # Because the analysis then splits on whether the kept player is the
    # favourite, the bias entered the two halves with opposite sign and produced
    # a +8.7pp / -3.7pp pre-match miscalibration that should have been zero.
    #
    # Lexicographic ticker order is independent of the result: 49.69% (z = -0.88).
    # Measured, not assumed -- see reports/p5_dedupe_bias.txt.
    df = df.sort_values(["event_ticker", "ticker"])
    keep = df.groupby("event_ticker", as_index=False).head(1).copy()
    keep["n_sides"] = keep["event_ticker"].map(per_event)
    print(f"\nafter dedupe: one market per match  {len(keep):,}")

    keep = keep[keep["paired"]].copy()
    print(f"restricted to paired events         {len(keep):,}")

    # ---- SELECTION CANARY -------------------------------------------------
    # An outcome-independent dedupe must keep the winning side exactly half the
    # time. The original volume-based rule scored 0.5356 (z = +10.0) and that
    # single number, had it been checked, would have caught the leak that voided
    # Phase 2. The temporal leak canary could not see it: that one watches for
    # look-ahead WITHIN a match, this was selection BETWEEN two markets.
    import leakguard as lg
    _r = lg.check_side_choice((keep["result"] == "yes").values,
                              name="universe dedupe")
    print("\nSELECTION CANARY")
    print("  " + _r.msg)
    _r.raise_if_bad()          # raises SelectionLeak or Untestable
    print("  passed -- the dedupe rule does not know who won")

    # weekly counts, to see how far usable history really goes
    keep["week"] = pd.to_datetime(keep["close_time"]).dt.tz_convert("UTC") \
        .dt.to_period("W").astype(str)
    print("\nmatches per week:")
    for w, n in keep.groupby("week").size().items():
        print(f"   {w}  {n:6,}")

    out = DATA / "universe.parquet"
    keep.drop(columns=["rules_primary"]).to_parquet(out, index=False)
    # rules kept separately -- needed later for tournament/round parsing
    keep[["event_ticker", "ticker", "title", "rules_primary"]].to_parquet(
        DATA / "universe_text.parquet", index=False)
    print(f"\n-> {out}")

    # also record BOTH sides of each kept event, for the mirror check on prices
    sides = df[df["event_ticker"].isin(set(keep["event_ticker"]))]
    sides[["event_ticker", "ticker", "series", "result", "open_time",
           "close_time", "volume"]].to_parquet(DATA / "sides.parquet",
                                               index=False)
    print(f"-> {DATA / 'sides.parquet'}  ({len(sides):,} market sides)")


if __name__ == "__main__":
    main()
