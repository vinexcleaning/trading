"""Does the favourite-longshot bias exist on KALSHI, or only on Polymarket?

The Phase 6 result found a large favourite-longshot bias in the Polymarket tennis tape
(+9.6pp at 0.7-0.8, -8.0pp at 0.2-0.3). The obvious question is whether it transfers to
the venue actually being traded. The user's own prior work says Kalshi tennis tracks
Betfair at r = 0.9878 with 1.95c MAD, which predicts the bias will be ABSENT here.

Method, mirroring the Polymarket test exactly so the numbers are comparable:
  - pull settled sports markets and their full public trade history
  - score each trade from the TAKER's perspective: price actually paid, and whether
    that side won. Crossing the spread is what a follower does.
  - bucket by price paid, compute realised edge = win_rate - mean_price
  - exclude the final N minutes, where convergence to 0/1 is mechanical rather than
    informative, and report the sensitivity to that cutoff

Leak discipline: a trade's price and timestamp both precede settlement by construction.
Nothing from the settlement is used except the outcome being predicted.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kalshi_research.api import KalshiPublicClient  # noqa: E402
from kalshi_research.fees import taker_fee_dollars  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

SERIES = [
    "KXATPMATCH", "KXWTAMATCH", "KXITFMATCH", "KXITFWMATCH",
    "KXMLBGAME", "KXNBAGAME", "KXNHLGAME", "KXWNBAGAME",
]
MARKETS_PER_SERIES = 120
MAX_TRADE_PAGES = 4  # 200 per page


def fetch_settled(c: KalshiPublicClient, series: str, n: int) -> list[dict]:
    out, cur = [], None
    while len(out) < n:
        p = {"series_ticker": series, "status": "settled", "limit": 200}
        if cur:
            p["cursor"] = cur
        try:
            d = c.get("/markets", p)
        except Exception:  # noqa: BLE001
            break
        mk = d.get("markets") or []
        if not mk:
            break
        out += [m for m in mk if m.get("result") in ("yes", "no")]
        cur = d.get("cursor")
        if not cur:
            break
    return out[:n]


def fetch_trades(c: KalshiPublicClient, ticker: str) -> list[dict]:
    out, cur = [], None
    for _ in range(MAX_TRADE_PAGES):
        p = {"ticker": ticker, "limit": 200}
        if cur:
            p["cursor"] = cur
        try:
            d = c.get("/markets/trades", p)
        except Exception:  # noqa: BLE001
            break
        tr = d.get("trades") or []
        if not tr:
            break
        out += tr
        cur = d.get("cursor")
        if not cur:
            break
    return out


def main() -> None:
    c = KalshiPublicClient(rps=4.0)
    rows = []
    for ser in SERIES:
        mkts = fetch_settled(c, ser, MARKETS_PER_SERIES)
        print(f"{ser}: {len(mkts)} settled markets with a yes/no result")
        got = 0
        for m in mkts:
            tk, res = m["ticker"], m["result"]
            close = pd.Timestamp(m["close_time"])
            trades = fetch_trades(c, tk)
            if not trades:
                continue
            got += 1
            for t in trades:
                try:
                    ts = pd.Timestamp(t["created_time"])
                    yes_px = float(t["yes_price_dollars"])
                    no_px = float(t["no_price_dollars"])
                    cnt = float(t["count_fp"])
                except (TypeError, ValueError, KeyError):
                    continue
                side = t.get("taker_outcome_side")
                if side not in ("yes", "no"):
                    continue
                # from the taker's perspective: what they paid, and whether it won
                paid = yes_px if side == "yes" else no_px
                won = int((res == "yes") if side == "yes" else (res == "no"))
                rows.append(
                    {
                        "series": ser, "ticker": tk, "side": side,
                        "price": paid, "won": won, "count": cnt,
                        "mins_to_close": (close - ts).total_seconds() / 60.0,
                    }
                )
        print(f"    trades pulled for {got} markets   (req={c.n_req} 429={c.n_429})")

    if not rows:
        print("no trades collected")
        return
    df = pd.DataFrame(rows)
    df = df[(df.price > 0.005) & (df.price < 0.995) & (df.mins_to_close >= 0)]
    df.to_parquet(REPORTS / "kalshi_longshot_trades.parquet", index=False)

    print("\n" + "=" * 84)
    print(f"KALSHI FAVOURITE-LONGSHOT TEST — {len(df):,} taker fills across "
          f"{df.ticker.nunique():,} settled markets, {df.series.nunique()} series")
    print("=" * 84)
    print(f"overall: mean price paid {df.price.mean():.4f}, win rate {df.won.mean():.4f}, "
          f"edge {(df.won.mean()-df.price.mean())*100:+.2f} pp")

    def table(d: pd.DataFrame, label: str) -> pd.DataFrame:
        b = pd.cut(d.price, [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0])
        t = d.groupby(b, observed=True).apply(
            lambda x: pd.Series({
                "n": len(x),
                "mean_price": x.price.mean(),
                "win_rate": x.won.mean(),
                "edge_pp": (x.won.mean() - x.price.mean()) * 100,
                "ci95_pp": 196 * (x.won - x.price).std(ddof=1) / np.sqrt(len(x)),
            }), include_groups=False)
        t["signif"] = t.edge_pp.abs() > t.ci95_pp
        print(f"\n--- {label} ---")
        print(t.round(3).to_string())
        return t

    full = table(df, "ALL fills")
    for cutoff in (5, 30, 120):
        sub = df[df.mins_to_close >= cutoff]
        if len(sub) > 500:
            table(sub, f"fills at least {cutoff} min before close (n={len(sub):,})")

    # the decisive comparison against the Polymarket numbers
    print("\n" + "=" * 84)
    print("KALSHI vs POLYMARKET, same buckets, same metric")
    print("=" * 84)
    poly = {"(0.1, 0.2]": -6.39, "(0.2, 0.3]": -8.03, "(0.4, 0.5]": -2.34,
            "(0.5, 0.6]": 5.09, "(0.6, 0.7]": 8.57, "(0.7, 0.8]": 9.63,
            "(0.9, 1.0]": 2.16}
    main_t = df[df.mins_to_close >= 30]
    kt = table(main_t, "KALSHI, >=30 min before close") if len(main_t) > 500 else full
    print(f"\n{'bucket':>12} {'Kalshi edge':>12} {'+/-95%':>9} {'Polymarket':>12} {'gap':>9}")
    for idx, r in kt.iterrows():
        key = str(idx)
        p = poly.get(key)
        ps = f"{p:+.2f}pp" if p is not None else "  --  "
        gap = f"{r.edge_pp - p:+.2f}" if p is not None else "  --  "
        print(f"{key:>12} {r.edge_pp:>+11.2f}pp {r.ci95_pp:>8.2f} {ps:>12} {gap:>9}")

    # net of fees: is any bucket tradeable?
    print("\n" + "=" * 84)
    print("NET OF FEES — a taker round trip, per contract")
    print("=" * 84)
    print(f"{'bucket':>12} {'gross':>9} {'fee':>7} {'NET':>9}  tradeable?")
    for idx, r in kt.iterrows():
        p = float(np.clip(r.mean_price, 0.01, 0.99))
        fee_c = 2 * taker_fee_dollars(10_000, p) * 100 / 10_000
        net = r.edge_pp - fee_c
        ok = "YES" if (r.edge_pp - r.ci95_pp) > fee_c else "no"
        print(f"{str(idx):>12} {r.edge_pp:>+8.2f}pp {fee_c:>6.2f}c {net:>+8.2f}pp  {ok}")

    (REPORTS / "kalshi_longshot_bias.json").write_text(json.dumps({
        "n_fills": int(len(df)), "n_markets": int(df.ticker.nunique()),
        "overall_edge_pp": float((df.won.mean() - df.price.mean()) * 100),
        "by_bucket_30min": kt.reset_index().astype(str).to_dict("records"),
    }, indent=1))
    print(f"\nwrote {REPORTS/'kalshi_longshot_bias.json'}")


if __name__ == "__main__":
    main()
