"""Composition of the CLOB universe, computed streaming.

build_10b enumerated 2,108,796 markets successfully but its summary step tried
to hold all of them in memory at once, reached 8.65GB, and was killed. The
.jsonl was already complete and closed at that point, so only the summary is
recomputed here -- in a single pass that keeps nothing but counters.

This is the "report the sample's composition before analysing anything" step.
Polymarket's market count is dominated by 5-minute crypto up/down series, and if
that is true of the ELIGIBLE set too, then any result carries a market-type
caveat that has to be visible from the start rather than discovered later.
"""
import json
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNI = ROOT / "data" / "markets_clob.jsonl"
STATS = ROOT / "data" / "markets_clob_stats.json"

FEE_START = 1767830400          # 2026-01-08


def guess_type(slug, question):
    s = f"{slug or ''} {question or ''}".lower()
    for key, pats in [
        ("crypto_updown_5m", ("updown-5m", "-updown-", "up-or-down")),
        ("crypto_other", ("bitcoin", "btc", "ethereum", "eth", "solana", "sol-",
                          "xrp", "doge", "crypto")),
        ("sports", ("nba", "nfl", "mlb", "nhl", "soccer", "premier", "laliga",
                    "ufc", "tennis", "cricket", "-vs-", "epl", "ncaa",
                    "champions-league", "serie-a", "bundesliga", "f1-")),
        ("politics", ("election", "president", "senate", "congress", "trump",
                      "biden", "harris", "governor", "parliament",
                      "prime-minister", "mamdani")),
        ("econ", ("fed-", "cpi", "inflation", "gdp", "unemployment",
                  "rate-cut", "recession", "jobs-")),
        ("entertainment", ("oscar", "grammy", "movie", "album", "netflix",
                           "box-office", "rotten", "spotify")),
        ("science_tech", ("openai", "gpt", "-ai-", "spacex", "nasa", "launch")),
    ]:
        if any(p in s for p in pats):
            return key
    return "other"


c = Counter()
elig_type = Counter()
elig_year = Counter()
elig_month = Counter()
all_type = Counter()
end_min = end_max = None
n = 0
t0 = time.time()

for line in UNI.open(encoding="utf-8"):
    m = json.loads(line)
    n += 1
    c[f"verdict_{m['settle_verdict']}"] += 1
    if m.get("closed"):
        c["closed"] += 1
    if m.get("enable_order_book"):
        c["orderbook_enabled"] += 1
    if m.get("neg_risk"):
        c["neg_risk"] += 1
    ty = guess_type(m.get("slug"), m.get("question"))
    all_type[ty] += 1

    e = m.get("end_date_iso")
    if e:
        end_min = e if end_min is None or e < end_min else end_min
        end_max = e if end_max is None or e > end_max else end_max

    # Eligibility: clean settlement, inside subgraph coverage, dated.
    #
    # `enable_order_book` is deliberately NOT required. It reports whether a
    # market is CURRENTLY accepting orders, not whether it ever had a book:
    # only 120,868 of 2,108,796 markets carry it, and a cross-tab found 288,566
    # closed+cleanly-settled markets with it false against 2,768 open markets
    # with it true. Requiring it excluded markets precisely for having finished
    # and left zero eligible rows. Tradability is instead established
    # empirically -- a market with no fills contributes nothing downstream.
    if (m["settle_verdict"] == "clean" and m.get("in_subgraph_window")
            and m.get("end_ts")):
        c["ELIGIBLE"] += 1
        elig_type[ty] += 1
        ts = m["end_ts"]
        elig_year[time.strftime("%Y", time.gmtime(ts))] += 1
        elig_month[time.strftime("%Y-%m", time.gmtime(ts))] += 1
        c["elig_" + ("post" if ts >= FEE_START else "pre") + "_fee"] += 1
        if m.get("neg_risk"):
            c["elig_neg_risk"] += 1
    else:
        if m["settle_verdict"] != "clean":
            c["drop_not_clean"] += 1
        elif not m.get("in_subgraph_window"):
            c["drop_outside_subgraph_window"] += 1
        else:
            c["drop_no_end_date"] += 1

    if n % 500_000 == 0:
        print(f"  {n:,}  eligible {c['ELIGIBLE']:,}  {time.time()-t0:.0f}s",
              flush=True)

elig = c["ELIGIBLE"]
summary = {
    "n_markets": n,
    "end_date_range": [end_min, end_max],
    "counters": dict(c),
    "n_eligible": elig,
    "frac_eligible": round(elig / n, 5),
    "eligible_by_regime": {"pre": c["elig_pre_fee"], "post": c["elig_post_fee"]},
    "eligible_by_year": dict(sorted(elig_year.items())),
    "eligible_by_month": dict(sorted(elig_month.items())),
    "eligible_by_type": dict(elig_type.most_common()),
    "eligible_type_shares": {k: round(v / elig, 4)
                             for k, v in elig_type.most_common()} if elig else {},
    "all_markets_by_type": dict(all_type.most_common()),
    "eligible_neg_risk_share": round(c["elig_neg_risk"] / elig, 4) if elig else None,
}
STATS.write_text(json.dumps(summary, indent=2), encoding="utf-8")

print(f"\n=== CLOB UNIVERSE COMPOSITION ({n:,} markets, {time.time()-t0:.0f}s) ===")
print(f"  end dates      : {end_min} .. {end_max}")
print(f"  eligible       : {elig:,} ({elig/n:.2%})")
print(f"  by regime      : pre={c['elig_pre_fee']:,}  post={c['elig_post_fee']:,}")
print(f"  by year        : {dict(sorted(elig_year.items()))}")
print("  eligible by type:")
for k, v in elig_type.most_common():
    print(f"      {k:>18}: {v:>9,}  ({v/elig:.2%})")
print("  drops:")
for k in ("drop_not_clean", "drop_outside_subgraph_window",
          "drop_no_orderbook", "drop_no_end_date"):
    print(f"      {k:>30}: {c[k]:>9,}")
print(f"\nwrote {STATS}")
