"""The decisive comparison: our probability vs Kalshi's mid, on recorded books.

This is the headline test the brief asks for, and it is the one thing that cannot be
back-filled -- Kalshi exposes no historical order book, so it needs recorded quotes.
The script is written to run continuously as the tape grows: it takes whatever
complete market lifecycles exist and reports n honestly rather than pretending.

It also reports the microstructure profile through a market's life (spread and depth
at the touch vs time to expiry), which is well-powered from a single market's
snapshots and directly determines the real cost bar.
"""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kalshi_research.api import KalshiPublicClient  # noqa: E402
from kalshi_research.evaluate import brier, compare_to_mid  # noqa: E402
from kalshi_research.fees import breakeven_edge_cents  # noqa: E402
from kalshi_research.models import (  # noqa: E402
    ewma_vol,
    settlement_aware_prob_above,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)


def load_books(prefix: str) -> pd.DataFrame:
    fs = sorted(glob.glob(str(RAW / "source=kalshi_book_tier*" / "**" / "*.parquet"),
                          recursive=True))
    if not fs:
        return pd.DataFrame()
    df = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    df = df[df.side.isin(["yes", "no"]) & df.ticker.str.startswith(prefix)]
    return df


def top_of_book(df: pd.DataFrame) -> pd.DataFrame:
    """Best yes bid and best yes ask per (ticker, snapshot).

    Kalshi's book is quoted as two one-sided ladders: `yes_dollars` are bids to buy
    YES, `no_dollars` are bids to buy NO. A bid of p on NO is an offer to sell YES
    at 1-p, so the YES ask is 1 - best_no_bid.
    """
    if df.empty:
        return df
    yes = (
        df[df.side == "yes"].groupby(["ticker", "recv_ns"])
        .apply(lambda g: pd.Series({
            "yes_bid": g.price.max(),
            "yes_bid_size": g.loc[g.price.idxmax(), "size"],
        }), include_groups=False)
    )
    no = (
        df[df.side == "no"].groupby(["ticker", "recv_ns"])
        .apply(lambda g: pd.Series({
            "no_bid": g.price.max(),
            "no_bid_size": g.loc[g.price.idxmax(), "size"],
        }), include_groups=False)
    )
    tob = yes.join(no, how="inner").reset_index()
    tob["yes_ask"] = 1.0 - tob.no_bid
    tob["yes_ask_size"] = tob.no_bid_size
    tob["mid"] = (tob.yes_bid + tob.yes_ask) / 2
    tob["spread_c"] = (tob.yes_ask - tob.yes_bid) * 100
    tob["touch_depth"] = tob[["yes_bid_size", "yes_ask_size"]].min(axis=1)
    return tob


def main() -> None:
    books = load_books("KXBTC15M")
    if books.empty:
        print("no KXBTC15M books recorded yet")
        return
    tob = top_of_book(books)
    print(f"KXBTC15M top-of-book snapshots: {len(tob)} across "
          f"{tob.ticker.nunique()} markets")

    # market metadata: strike and settlement
    c = KalshiPublicClient(rps=5)
    meta = {}
    for tk in tob.ticker.unique():
        try:
            m = (c.get("/markets", {"tickers": tk, "limit": 1}).get("markets") or [{}])[0]
            meta[tk] = {
                "close_ts": pd.Timestamp(m.get("close_time")),
                "floor_strike": pd.to_numeric(m.get("floor_strike"), errors="coerce"),
                "status": m.get("status"),
                "result": m.get("result") or "",
                "expiration_value": pd.to_numeric(
                    m.get("expiration_value"), errors="coerce"
                ),
            }
        except Exception as e:  # noqa: BLE001
            print(f"  meta fail {tk}: {str(e)[:50]}")
    tob["close_ns"] = tob.ticker.map(
        lambda t: meta.get(t, {}).get("close_ts", pd.NaT)
    ).astype("datetime64[ns, UTC]").astype("int64")
    tob["secs_to_expiry"] = (tob.close_ns - tob.recv_ns) / 1e9
    tob["strike"] = tob.ticker.map(lambda t: meta.get(t, {}).get("floor_strike"))
    live = tob[(tob.secs_to_expiry > 0) & (tob.secs_to_expiry <= 900)].copy()

    # ---- microstructure profile: this is well-powered from one market -------
    print("\n=== MICROSTRUCTURE through a market's life "
          "(the real cost bar, not an estimate) ===")
    live["bucket"] = pd.cut(
        live.secs_to_expiry, [0, 60, 120, 300, 600, 900],
        labels=["0-60s", "60-120s", "2-5m", "5-10m", "10-15m"],
    )
    prof = live.groupby("bucket", observed=True).agg(
        n=("mid", "size"),
        median_spread_c=("spread_c", "median"),
        median_touch_depth=("touch_depth", "median"),
        median_mid=("mid", "median"),
    )
    prof["fee_c_at_mid"] = prof.median_mid.map(
        lambda p: breakeven_edge_cents(float(np.clip(p, 0.01, 0.99)), 0.0)
    )
    prof["total_breakeven_c"] = prof.fee_c_at_mid + prof.median_spread_c
    print(prof.round(2).to_string())
    prof.to_csv(REPORTS / "btc15m_microstructure.csv")

    print("\n  The cost bar measured from live books, rather than assumed:")
    for b, r in prof.iterrows():
        print(f"    {b:>8s}: spread {r.median_spread_c:.2f}c + fee "
              f"{r.fee_c_at_mid:.2f}c = {r.total_breakeven_c:.2f}c to break even, "
              f"depth {r.median_touch_depth:.0f}")

    # ---- the vs-mid comparison, on whatever has settled --------------------
    settled = [t for t, m in meta.items() if m.get("result") in ("yes", "no")]
    print(f"\n=== VS-MID COMPARISON: {len(settled)} of {tob.ticker.nunique()} "
          f"markets have settled ===")
    if not settled:
        print("  Not yet answerable. The recorded markets have closed but not "
              "finalised (Kalshi applies a settlement timer), so no outcome exists "
              "to score against.")
        print("  This is the headline test and it needs days of recording, not "
              "minutes. The machinery is in place; n is the only missing ingredient.")
        (REPORTS / "vs_mid.json").write_text(json.dumps({
            "status": "insufficient settled markets",
            "n_markets_recorded": int(tob.ticker.nunique()),
            "n_settled": 0,
            "n_snapshots": int(len(tob)),
            "note": "microstructure profile written to btc15m_microstructure.csv",
        }, indent=1))
        return

    # spot for the model
    sfs = sorted(glob.glob(str(RAW / "source=ext_spot" / "**" / "*.parquet"),
                           recursive=True))
    spot = pd.concat([pd.read_parquet(f) for f in sfs], ignore_index=True)
    spot = spot[(spot.symbol == "BTCUSD") & (spot.venue == "coinbase")]
    spot = spot.sort_values("recv_ns")
    spot["logret"] = np.log(spot.last).diff()
    sigma_1s = float(np.nanstd(spot.logret.values))

    rows = []
    for tk in settled:
        m = meta[tk]
        g = live[live.ticker == tk].sort_values("recv_ns")
        if g.empty:
            continue
        s_at = np.interp(g.recv_ns.values, spot.recv_ns.values, spot.last.values)
        # spot samples arrive ~2s apart; scale sigma to the remaining window
        n_steps = np.maximum(g.secs_to_expiry.values / 2.0, 1e-9)
        sig = sigma_1s * np.sqrt(n_steps)
        p_model = settlement_aware_prob_above(
            s_at, np.full(len(g), m["floor_strike"]), sig,
            g.secs_to_expiry.values, 60.0,
        )
        y = np.full(len(g), 1 if m["result"] == "yes" else 0)
        rows.append(pd.DataFrame({
            "ticker": tk, "secs_to_expiry": g.secs_to_expiry.values,
            "mid": g["mid"].values, "p_model": p_model, "y": y,
        }))
    if not rows:
        print("  no overlapping spot data")
        return
    panel = pd.concat(rows, ignore_index=True)
    cmp = compare_to_mid(panel.p_model.values, panel["mid"].values, panel.y.values,
                         n_boot=2000, seed=11)
    print(f"  snapshots scored: {len(panel)} from {panel.ticker.nunique()} markets")
    print(f"  our Brier    {brier(panel.p_model.values, panel.y.values):.5f}")
    print(f"  mid Brier    {brier(panel['mid'].values, panel.y.values):.5f}")
    print(f"  paired diff  {cmp.paired_diff_mean:+.5f} "
          f"CI [{cmp.paired_diff_ci[0]:+.5f}, {cmp.paired_diff_ci[1]:+.5f}]")
    print("\n  WARNING: snapshots within one market are NOT independent -- a single "
          "settlement drives every row. The effective n is the number of MARKETS "
          f"({panel.ticker.nunique()}), not snapshots. Treat this as a pipeline "
          "check, not evidence.")
    panel.to_parquet(REPORTS / "vs_mid_panel.parquet", index=False)
    (REPORTS / "vs_mid.json").write_text(json.dumps({
        "n_markets": int(panel.ticker.nunique()),
        "n_snapshots": int(len(panel)),
        "brier_model": brier(panel.p_model.values, panel.y.values),
        "brier_mid": brier(panel["mid"].values, panel.y.values),
        "paired_diff": cmp.paired_diff_mean,
        "ci": list(cmp.paired_diff_ci),
        "caveat": "snapshots within a market are not independent; effective n = markets",
    }, indent=1, default=str))


if __name__ == "__main__":
    main()
