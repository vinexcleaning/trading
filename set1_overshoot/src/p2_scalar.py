"""Retirement / walkover sensitivity.

Kalshi settles a match that does not finish at a scalar value rather than 0 or 1.
Those markets have no yes/no `result`, so the main universe silently excludes
them. That exclusion is a survivorship choice, not a neutral filter: a
hold-to-settlement position is fully exposed to a retirement, and the exposure
is asymmetric because the player who retires is usually the one already losing.

This builds the scalar universe, pulls its candles, runs the same extraction,
and reports what including it does to the headline expectancy.
"""
import argparse
import json
import pathlib
import subprocess
import sys

import numpy as np
import pandas as pd

import p2_calib as p2

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PY = sys.executable

SERIES_LABEL = {
    "KXATPMATCH": "ATP", "KXWTAMATCH": "WTA",
    "KXATPCHALLENGERMATCH": "CHALL",
    "KXITFMATCH": "ITF-M", "KXITFWMATCH": "ITF-W",
}


def build_universe():
    raw = json.loads((DATA / "markets_raw.json").read_text(encoding="utf-8"))
    rows = []
    for series, mkts in raw.items():
        for m in mkts:
            if m.get("result") != "scalar":
                continue
            rows.append({
                "series": series, "tour": SERIES_LABEL[series],
                "event_ticker": m["event_ticker"], "ticker": m["ticker"],
                "result": "yes",          # placeholder; scalar handled below
                "settle": float(m.get("settlement_value_dollars") or 0),
                "open_time": pd.Timestamp(m["open_time"]),
                "close_time": pd.Timestamp(m["close_time"]),
                "volume": float(m.get("volume_fp") or 0),
            })
    df = pd.DataFrame(rows)
    # one side per event, same outcome-independent rule as the main universe
    df = df.sort_values(["event_ticker", "ticker"])
    df = df.groupby("event_ticker", as_index=False).head(1)
    df["plausible"] = True
    df.to_parquet(DATA / "scalar_universe.parquet", index=False)
    print(f"scalar events: {len(df):,}")
    print(df.groupby("tour").size().to_string())
    print(f"settlement value: median {df['settle'].median():.2f}  "
          f"mean {df['settle'].mean():.3f}  "
          f"at exactly 0.50: {(df['settle'] == 0.5).mean():.1%}")
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    args = ap.parse_args()

    uni = build_universe()
    if args.fetch:
        subprocess.run([PY, str(ROOT / "src" / "p0_candles.py"),
                        "--workers", "8", "--out", "candles_scalar",
                        "--uni", "scalar_universe.parquet"], check=True)
        subprocess.run([PY, str(ROOT / "src" / "p1_state.py"),
                        "--subdir", "candles_scalar", "--out", "scalar",
                        "--uni", "scalar_universe.parquet"], check=True)
    if not (DATA / "scalar_state.parquet").exists():
        print("\nrun p1_state.py --subdir candles_scalar --out scalar "
              "--uni scalar_universe.parquet first")
        return

    st, bid, ask, mid = p2.load("scalar")
    ev = p2.build_events(st, bid, ask, mid, p2.BASE_RULE, p2.BASE_OFFSET)
    ev = ev.merge(uni[["ticker", "settle"]], on="ticker", how="left")
    e = ev[ev["is_event"]].copy()
    print(f"\nscalar matches that would have been entered: {len(e):,}")
    if not len(e):
        return

    # main sample, for the mixing weight
    stm, bm, am, mm = p2.load("paths")
    evm = p2.build_events(stm, bm, am, mm, p2.BASE_RULE, p2.BASE_OFFSET)
    em = evm[evm["is_event"]]
    frac = len(e) / (len(e) + len(em))
    print(f"they are {frac:.2%} of all entered positions")

    fill_s = np.minimum(e["entry_ask"].values + p2.SLIP, 99.0)
    import fees
    fee_s = np.array([float(fees.fee_rate_cents(int(round(f)))) for f in fill_s])
    net_s = 100.0 * e["settle"].values - fill_s - fee_s

    net_m, _, _ = p2.costed(em["entry_mid"].values, em["entry_ask"].values,
                            em["fav_won"].values)
    blended = (net_m.sum() + net_s.sum()) / (len(net_m) + len(net_s))

    lines = [
        "RETIREMENT / WALKOVER SENSITIVITY",
        "=" * 60,
        f"scalar-settled matches in the whole book : {len(uni):,}",
        f"of those, ones this strategy would enter : {len(e):,}",
        f"share of all positions taken             : {frac:.2%}",
        f"median settlement value                  : "
        f"{e['settle'].median():.2f}",
        f"mean entry mid on those                  : "
        f"{e['entry_mid'].mean():.1f}c",
        "",
        f"net expectancy, completed matches only   : {net_m.mean():+.3f} c",
        f"net expectancy, scalar matches only      : {net_s.mean():+.3f} c",
        f"net expectancy, blended (the real one)   : {blended:+.3f} c",
        f"cost of the exclusion                    : "
        f"{blended - net_m.mean():+.3f} c/contract",
    ]
    print()
    print("\n".join(lines))
    (ROOT / "reports" / "p2_scalar.txt").write_text("\n".join(lines),
                                                    encoding="utf-8")


if __name__ == "__main__":
    main()
