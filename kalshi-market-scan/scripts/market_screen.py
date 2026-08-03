"""Phase 1: structural screen. Scores series on the market-quality rubric.

The screen is for ELIMINATION, not discovery: the goal is to kill everything that
structurally cannot clear the cost bar even with a perfect model, so the expensive
modelling lands on the two or three families with a real reason to be inefficient.

Writes docs/market_screen.csv and the kill list that feeds docs/shortlist.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from kalshi_research.fees import breakeven_edge_cents  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True)

# Recurrence needed to validate anything. Below this a family is untestable and is
# killed regardless of how attractive it looks.
MIN_SETTLEMENTS = 50

# Ground-truth availability per family prefix, assessed in Phase 0. This is the one
# dimension that cannot be measured from the API and must be asserted.
GROUND_TRUTH = {
    # free, physical, machine-readable, updates faster than the market reprices
    "KXTEMP": 5, "KXHIGH": 5,
    # free reference price, but it IS the settlement source, so no independent edge
    "KXBTC": 3, "KXETH": 3, "KXSOL": 3, "KXXRP": 3, "KXDOGE": 3,
    "KXSHIBA": 3, "KXBNB": 3, "KXHYPE": 3, "KXZEC": 3, "KXNEAR": 3,
    "KXINX": 3, "KXNASDAQ100": 3, "KXDJI": 3,
    # released components are public and free, but releases are rare
    "KXCPI": 4, "KXPPI": 4, "KXFED": 3, "KXGDP": 4, "KXCLAIMS": 4, "KXJOBS": 4,
    "KXPAYROLL": 4, "KXUNEMP": 4,
}
# Human-judgement / unmodellable resolution -> dimension 1 scores 0
OPINION_PREFIXES = ("KXMVE",)
OPINION_CATEGORIES = {"Politics", "Culture", "Entertainment", "World", "Elections",
                      "Science and Technology", "Health", "Companies"}


def series_of(t: str) -> str:
    return str(t).split("-")[0]


def score_ground_truth(series: str, category: str) -> int:
    for pre, sc in sorted(GROUND_TRUTH.items(), key=lambda kv: -len(kv[0])):
        if series.startswith(pre):
            return sc
    if series.startswith(OPINION_PREFIXES):
        return 0
    if category in OPINION_CATEGORIES:
        return 0
    if category == "Sports":
        return 1  # scores are objective but not forecastable from free fast data
    return 1


def score_cost_bar(median_spread_c: float, median_price: float) -> int:
    """5 = cheap to trade. Fee is quadratic in price, so tails are cheaper."""
    if not np.isfinite(median_spread_c):
        return 0
    be = breakeven_edge_cents(
        float(np.clip(median_price, 0.01, 0.99)), median_spread_c
    )
    if be <= 2.0:
        return 5
    if be <= 3.5:
        return 4
    if be <= 5.0:
        return 3
    if be <= 8.0:
        return 2
    if be <= 12.0:
        return 1
    return 0


def score_liquidity(median_vol: float, quoted_frac: float, n_markets: int) -> int:
    if median_vol <= 0 or quoted_frac < 0.1:
        return 0
    s = 0
    s += 2 if median_vol > 10_000 else 1 if median_vol > 100 else 0
    s += 2 if quoted_frac > 0.9 else 1 if quoted_frac > 0.5 else 0
    s += 1 if n_markets > 20 else 0
    return min(s, 5)


def score_structural(n_per_event: float, strike_types: set[str]) -> int:
    """Internal constraints checkable with no forecast at all."""
    if n_per_event < 2:
        return 0
    s = 1
    if "between" in strike_types:
        s += 3  # exhaustive bucket family: must sum to 100
    elif strike_types & {"greater", "greater_or_equal", "less", "less_or_equal"}:
        s += 2  # nested ladder: monotone in strike
    if n_per_event >= 10:
        s += 1
    return min(s, 5)


def score_recurrence(n_settled: int, freq: str | None) -> int:
    if n_settled >= 5000:
        return 5
    if n_settled >= 1000:
        return 4
    if n_settled >= 200:
        return 3
    if n_settled >= MIN_SETTLEMENTS:
        return 2
    if n_settled > 0:
        return 1
    return 0


def score_settlement_clarity(series: str, category: str) -> int:
    if series.startswith(OPINION_PREFIXES):
        return 2
    if series.startswith(("KXTEMP", "KXHIGH")):
        return 5
    if series.startswith(("KXBTC", "KXETH", "KXINX", "KXNASDAQ", "KXDJI", "KXSOL")):
        return 5
    if category in ("Politics", "Culture", "Entertainment"):
        return 2
    return 3


def main() -> None:
    mk = pd.read_parquet(DATA / "markets_open.parquet")
    mk["series"] = mk.ticker.map(series_of)
    mk["is_combo"] = mk.mve_collection_ticker.notna()

    ser_meta = pd.read_parquet(DATA / "series.parquet").set_index("ticker")

    # settled-history counts, where we downloaded them
    settled_counts: dict[str, int] = {}
    sp = DATA / "settled" / "_summary.csv"
    if sp.exists():
        s = pd.read_csv(sp)
        settled_counts = dict(zip(s.series, s.n.fillna(0).astype(int)))

    for c in ("yes_bid_dollars", "yes_ask_dollars", "volume_24h_fp", "volume_fp",
              "yes_bid_size_fp", "yes_ask_size_fp"):
        mk[c] = pd.to_numeric(mk[c], errors="coerce")

    rows = []
    for series, g in mk.groupby("series"):
        cat = ser_meta.category.get(series)
        if not isinstance(cat, str):
            cat = "Unknown"
        fee_type = ser_meta.fee_type.get(series, "quadratic")
        freq = ser_meta.frequency.get(series)

        quoted = g[(g.yes_bid_dollars > 0) & (g.yes_ask_dollars > 0)]
        quoted_frac = len(quoted) / max(len(g), 1)
        spread_c = (
            float(((quoted.yes_ask_dollars - quoted.yes_bid_dollars) * 100).median())
            if len(quoted) else np.nan
        )
        med_price = (
            float(((quoted.yes_ask_dollars + quoted.yes_bid_dollars) / 2).median())
            if len(quoted) else np.nan
        )
        med_vol = float(g.volume_fp.fillna(0).median())
        n_per_event = float(g.groupby("event_ticker").size().median()) if len(g) else 0
        stypes = set(g.strike_type.dropna().unique())
        n_settled = settled_counts.get(series, 0)

        d1 = score_ground_truth(series, cat)
        d2 = score_cost_bar(spread_c, med_price)
        d3 = score_liquidity(med_vol, quoted_frac, len(g))
        d4 = score_structural(n_per_event, stypes)
        d5 = score_recurrence(n_settled, freq)
        d6 = np.nan  # counterparty fingerprint: needs recorded books, see below
        d7 = score_settlement_clarity(series, cat)
        d8 = 0 if series.startswith(("KXBTCY", "KXETHY")) else 5  # all data used is free

        be = (
            breakeven_edge_cents(float(np.clip(med_price, 0.01, 0.99)), spread_c)
            if np.isfinite(spread_c) and np.isfinite(med_price) else np.nan
        )

        kills = []
        if d1 == 0 and d4 == 0:
            kills.append("no ground truth and no structural check (pure opinion)")
        if np.isfinite(spread_c) and spread_c > 8:
            kills.append(f"median spread {spread_c:.1f}c exceeds any plausible edge")
        if not np.isfinite(spread_c):
            kills.append("no two-sided quotes: unpriceable and unfillable")
        if n_settled and n_settled < MIN_SETTLEMENTS:
            kills.append(f"only {n_settled} settlements available (<{MIN_SETTLEMENTS})")
        if d3 == 0:
            kills.append("no liquidity: zero median volume or quotes mostly absent")
        if g.is_combo.all():
            kills.append("combo/multivariate only: legs priced elsewhere")

        rows.append(
            {
                "series": series, "category": cat, "frequency": freq,
                "fee_type": fee_type, "n_open_markets": len(g),
                "n_settled_downloaded": n_settled,
                "median_spread_cents": round(spread_c, 2) if np.isfinite(spread_c) else None,
                "median_price": round(med_price, 4) if np.isfinite(med_price) else None,
                "quoted_fraction": round(quoted_frac, 3),
                "median_volume": round(med_vol, 1),
                "markets_per_event": n_per_event,
                "strike_types": ",".join(sorted(stypes)) if stypes else "",
                "breakeven_edge_cents": round(be, 2) if np.isfinite(be) else None,
                "d1_ground_truth": d1, "d2_cost_bar": d2, "d3_liquidity": d3,
                "d4_structural": d4, "d5_recurrence": d5,
                "d6_counterparty": d6, "d7_settlement": d7, "d8_data_cost": d8,
                "total_score": d1 + d2 + d3 + d4 + d5 + d7 + d8,
                "killed": bool(kills),
                "kill_reasons": "; ".join(kills),
            }
        )

    df = pd.DataFrame(rows).sort_values(
        ["killed", "total_score"], ascending=[True, False]
    )
    df.to_csv(DOCS / "market_screen.csv", index=False)

    print(f"scored {len(df)} series with >=1 open market")
    print(f"  killed:   {int(df.killed.sum())}")
    print(f"  survived: {int((~df.killed).sum())}")
    print("\n=== top 25 survivors ===")
    cols = ["series", "category", "n_open_markets", "n_settled_downloaded",
            "median_spread_cents", "median_price", "breakeven_edge_cents",
            "median_volume", "d1_ground_truth", "d4_structural", "d5_recurrence",
            "total_score"]
    print(df[~df.killed].head(25)[cols].to_string(index=False))
    print("\n=== kill reason frequency ===")
    kr: dict[str, int] = {}
    for s in df[df.killed].kill_reasons:
        for part in s.split("; "):
            key = part.split(":")[0].split("(")[0].strip()
            key = "".join(ch for ch in key if not ch.isdigit()).replace("  ", " ")
            kr[key] = kr.get(key, 0) + 1
    for k, v in sorted(kr.items(), key=lambda kv: -kv[1]):
        print(f"  {v:5d}  {k}")


if __name__ == "__main__":
    main()
