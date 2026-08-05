"""
t2_master.py - TASK 1 and TASK 2. The definitive per-match ledger, and the
night-versus-day test.

CLASSIFIER (final). A BUY order is the bot's iff
      side == yes            the engine never buys NO; all 4 buy/no are manual
  and 10c <= price <= 90c    manual buys are marketable limits typed at 99c,
                             or 1-6c longshots
  and $4.60 <= qty*price <= $6.30
                             the engine sizes qty = int(stake/price). The stake
                             is NOT constant: it steps 5.1 -> 5.9 -> 6.25 over
                             27 Jul, which is `--bankroll` being restarted at a
                             higher number as the account grew (gui.py takes it
                             as a CLI argument; nothing updates it live).
None of the three can see the outcome. The earlier notional-only rule called a
hand-placed 6c NO longshot (SHIDON, +$14.51) a bot trade; this one does not.

A MATCH is bot-only iff every buy order on either of its two mirrored markets
passes. Mixed matches are reported separately and excluded from bot totals.

P&L per ticker, from Kalshi's own settlement report where it exists:
      payout = yes_ct*v + no_ct*(1-v),  v = value/100
      pnl    = payout - yes_cost - no_cost - fee
`fee` there is the cumulative TRADING fee and is not an extra charge.
Eight tickets traded after the last settlement pull are computed from fills
plus the result from the public market endpoint (out/late_outcomes.json).
"""
from __future__ import annotations
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pandas as pd
import load

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 500)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")

O = load.orders(); F = load.fills(); S = load.settlements()
LATE = json.load(open(os.path.join(OUT, "late_outcomes.json"), encoding="utf-8"))

# ----------------------------------------------------------------------
# classifier
# ----------------------------------------------------------------------
B = O[O.action == "buy"].copy()
B["cents"] = (B.px * 100).round().astype(int)
B["notional"] = B.initial * B.px
B["bot"] = ((B.side == "yes") & B.cents.between(10, 90)
            & B.notional.between(4.60, 6.30))
klass = B.groupby("ticker").bot.agg(
    lambda s: "bot" if s.all() else ("manual" if not s.any() else "mixed"))

# ----------------------------------------------------------------------
# per-ticker P&L
# ----------------------------------------------------------------------
S = S.copy()
S["v"] = S.value / 100.0
S["pnl"] = S.yes_ct * S.v + S.no_ct * (1 - S.v) - S.yes_cost - S.no_cost - S.fee
pnl = S.set_index("ticker").pnl.to_dict()
cost = (S.set_index("ticker").yes_cost + S.set_index("ticker").no_cost).to_dict()
feed = S.set_index("ticker").fee.to_dict()
contr = S.set_index("ticker").yes_ct.to_dict()

for tk, rec in LATE.items():
    g = F[F.ticker == tk]
    buy = g[(g.action == "buy") & (g.side == "yes")]
    sell = g[g.action == "sell"]
    v = 1.0 if rec["result"] == "yes" else 0.0
    yc = (buy.qty * buy.yes_px).sum()
    nc = (sell.qty * sell.no_px).sum()
    fe = g.fee.sum()
    pnl[tk] = buy.qty.sum() * v + sell.qty.sum() * (1 - v) - yc - nc - fe
    cost[tk] = yc + nc
    feed[tk] = fe
    contr[tk] = buy.qty.sum()

# ----------------------------------------------------------------------
# ticker frame
# ----------------------------------------------------------------------
tks = sorted(set(pnl) | set(klass.index))
L = pd.DataFrame(index=pd.Index(tks, name="ticker"))
L["pnl"] = pd.Series(pnl)
L["cost"] = pd.Series(cost)
L["fee"] = pd.Series(feed)
L["contracts"] = pd.Series(contr)
L["klass"] = klass.reindex(L.index).fillna("unknown")
L["tier"] = L.index.map(load.tier_of)
L["event"] = L.index.map(load.event_of)
fb = O[O.action == "buy"].sort_values("t").groupby("ticker")
L["t_entry"] = fb.t.min().reindex(L.index)
L["entry_c"] = (fb.px.first().reindex(L.index) * 100).round()
L["n_buys"] = fb.size().reindex(L.index)
L = L[L.tier != "OTHER"]              # tennis only
L.to_csv(os.path.join(OUT, "master_ticker.csv"))

print("=" * 78)
print("TASK 1  -  what actually happened, tennis only")
print("=" * 78)
print(L.groupby("klass").agg(tickers=("pnl", "size"), pnl=("pnl", "sum"),
                             cost=("cost", "sum"), fee=("fee", "sum")).to_string())

# ----------------------------------------------------------------------
# fold to one row per MATCH
# ----------------------------------------------------------------------
M = (L.groupby("event")
      .agg(tier=("tier", "first"), t_entry=("t_entry", "min"),
           pnl=("pnl", "sum"), cost=("cost", "sum"), fee=("fee", "sum"),
           contracts=("contracts", "sum"), n_tickers=("pnl", "size"),
           n_buys=("n_buys", "sum"), entry_c=("entry_c", "first"),
           klass=("klass", lambda s: s.iloc[0] if s.nunique() == 1 else "mixed"))
      .sort_values("t_entry"))
M.to_csv(os.path.join(OUT, "master_match.csv"))

print()
print("folded to one observation per MATCH:")
print(M.groupby("klass").agg(matches=("pnl", "size"), pnl=("pnl", "sum"),
                             cost=("cost", "sum"), fee=("fee", "sum"),
                             contracts=("contracts", "sum")).to_string())

B_ = M[M.klass == "bot"].copy()
print()
print("=" * 78)
print(f"THE BOT:  {len(B_)} matches, total P&L ${B_.pnl.sum():+.2f}")
print("=" * 78)
print(f"  first entry      {B_.t_entry.min()}")
print(f"  last entry       {B_.t_entry.max()}")
print(f"  capital deployed ${B_.cost.sum():,.2f}   fees ${B_.fee.sum():,.2f}")
print(f"  contracts        {B_.contracts.sum():,.0f}")
print(f"  mean per match   ${B_.pnl.mean():+.4f}   median ${B_.pnl.median():+.4f}")
print(f"  sd per match     ${B_.pnl.std():.4f}")
print(f"  winners          {(B_.pnl > 0).sum()} / {len(B_)}  "
      f"({(B_.pnl > 0).mean():.1%})")
print(f"  per contract     {B_.pnl.sum() / B_.contracts.sum() * 100:+.2f}c")
print()
print("distribution of per-match P&L:")
print(B_.pnl.describe().to_string())
print()
print("deciles:")
print(B_.pnl.quantile(np.arange(0, 1.01, 0.1)).round(3).to_string())
print()
print("the 8 largest winners and 8 largest losers:")
print(pd.concat([B_.nlargest(8, "pnl"), B_.nsmallest(8, "pnl")])
      [["tier", "t_entry", "entry_c", "n_buys", "contracts", "pnl"]].to_string())

# ----------------------------------------------------------------------
# the equity curve, and where "the night" is
# ----------------------------------------------------------------------
print()
print("=" * 78)
print("BOT EQUITY BY HOUR OF ENTRY (UTC).  cum = running total")
print("=" * 78)
B_["hr"] = B_.t_entry.dt.floor("h")
h = B_.groupby("hr").agg(n=("pnl", "size"), pnl=("pnl", "sum"))
h["cum"] = h.pnl.cumsum()
h["utc_hour"] = h.index.hour
h["et"] = (h.index.tz_convert("America/New_York")).strftime("%m-%d %H:%M")
print(h.to_string())

# ----------------------------------------------------------------------
# TASK 2  -  night vs day
# ----------------------------------------------------------------------
print()
print("=" * 78)
print("TASK 2  -  night versus day, and tier versus tier")
print("=" * 78)


def wilsonless(x):
    """mean, sd, se, t, and a normal 95% CI - clustered at MATCH level,
    which is what x already is."""
    x = np.asarray(x, float)
    n = len(x)
    if n < 2:
        return dict(n=n, mean=x.mean() if n else np.nan, se=np.nan,
                    lo=np.nan, hi=np.nan, t=np.nan)
    m, sd = x.mean(), x.std(ddof=1)
    se = sd / np.sqrt(n)
    return dict(n=n, mean=m, sd=sd, se=se, lo=m - 1.96 * se, hi=m + 1.96 * se,
                t=m / se if se else np.nan)


def table(df, by, label):
    rows = []
    for k, g in df.groupby(by, observed=True):
        r = wilsonless(g.pnl.values)
        r[by if isinstance(by, str) else "key"] = k
        r["total"] = g.pnl.sum()
        r["contracts"] = g.contracts.sum()
        r["c_per_contract"] = g.pnl.sum() / g.contracts.sum() * 100 if g.contracts.sum() else np.nan
        # minimum detectable effect on the per-match mean, two-sided 5%, 80%
        r["mde_$"] = 2.8 * r["se"] if r.get("se") == r.get("se") else np.nan
        rows.append(r)
    t = pd.DataFrame(rows).set_index(by if isinstance(by, str) else "key")
    print(f"\n--- {label}")
    print(t[["n", "total", "mean", "sd", "se", "lo", "hi", "t", "mde_$",
             "contracts", "c_per_contract"]].round(4).to_string())
    return t


B_["utc_hour"] = B_.t_entry.dt.hour
B_["et_hour"] = B_.t_entry.dt.tz_convert("America/New_York").dt.hour
# 4-hour UTC blocks
B_["block"] = pd.cut(B_.utc_hour, [-1, 3, 7, 11, 15, 19, 23],
                     labels=["00-03", "04-07", "08-11", "12-15", "16-19", "20-23"])
table(B_, "block", "by 4-hour UTC block of entry")
table(B_, "tier", "by tour tier")
B_["day"] = B_.t_entry.dt.date
table(B_, "day", "by UTC calendar day of entry")

print()
print("--- tier x block: total P&L (cells with n<3 are noise)")
print(B_.pivot_table(index="tier", columns="block", values="pnl", aggfunc="sum",
                     observed=True).round(2).to_string())
print()
print("--- tier x block: n matches")
print(B_.pivot_table(index="tier", columns="block", values="pnl", aggfunc="size",
                     observed=True).to_string())

# ----------------------------------------------------------------------
# the peak, and what happened either side of it
# ----------------------------------------------------------------------
print()
print("=" * 78)
print("THE PEAK")
print("=" * 78)
Bs = B_.sort_values("t_entry").copy()
Bs["cum"] = Bs.pnl.cumsum()
pk = Bs.cum.idxmax()
pk_i = Bs.index.get_loc(pk)
print(f"running total peaks at ${Bs.cum.max():+.2f} after {pk_i + 1} matches, "
      f"at {Bs.loc[pk, 't_entry']}  ({Bs.loc[pk, 't_entry'].tz_convert('America/New_York')} ET)")
pre, post = Bs.iloc[:pk_i + 1], Bs.iloc[pk_i + 1:]
for nm, g in (("BEFORE the peak", pre), ("AFTER the peak", post)):
    r = wilsonless(g.pnl.values)
    print(f"\n{nm}: n={len(g)} matches  total ${g.pnl.sum():+.2f}  "
          f"mean ${r['mean']:+.4f}  se {r['se']:.4f}  t={r['t']:+.2f}  "
          f"win rate {(g.pnl > 0).mean():.1%}  contracts {g.contracts.sum():.0f}  "
          f"{g.pnl.sum() / g.contracts.sum() * 100:+.2f}c/contract")
    print("  tier mix: " + ", ".join(f"{k} {v}" for k, v in g.tier.value_counts().items()))

# ----------------------------------------------------------------------
# ENTRY BURSTS - the real unit of independence
# ----------------------------------------------------------------------
print()
print("=" * 78)
print("ENTRY BURSTS.  The scanner fires everything that qualifies in one pass,")
print("so matches entered seconds apart share one feed state and one score")
print("snapshot. They are not independent observations even at match level.")
print("=" * 78)
Bs = Bs.sort_values("t_entry")
gap = Bs.t_entry.diff().dt.total_seconds().fillna(1e9)
Bs["burst"] = (gap > 120).cumsum()          # a new burst after a 2-minute gap
bu = Bs.groupby("burst").agg(n=("pnl", "size"), t=("t_entry", "min"),
                             pnl=("pnl", "sum"),
                             tiers=("tier", lambda s: ",".join(sorted(set(s)))))
print(f"{len(Bs)} matches collapse into {len(bu)} bursts "
      f"(a burst = entries <=120s apart)")
print(bu[bu.n > 1].to_string())
rb = wilsonless(bu.pnl.values)
print(f"\nclustered at BURST level: n={rb['n']}  total ${bu.pnl.sum():+.2f}  "
      f"mean ${rb['mean']:+.4f}  se {rb['se']:.4f}  95% CI "
      f"[{rb['lo']:+.4f}, {rb['hi']:+.4f}]  t={rb['t']:+.2f}")
rm = wilsonless(Bs.pnl.values)
print(f"clustered at MATCH level: n={rm['n']}  mean ${rm['mean']:+.4f}  "
      f"se {rm['se']:.4f}  t={rm['t']:+.2f}")
print(f"design effect (se_burst*sqrt(n_burst)) / (se_match*sqrt(n_match)) "
      f"variance ratio on the TOTAL: "
      f"{(rb['sd']**2 * rb['n']) / (rm['sd']**2 * rm['n']):.2f}")

# ----------------------------------------------------------------------
# drop-the-extremes stress test
# ----------------------------------------------------------------------
print()
print("=" * 78)
print("STRESS TEST - delete the k best and k worst matches")
print("=" * 78)
for k in (0, 1, 2, 3, 5):
    s = Bs.pnl.sort_values()
    trimmed = s.iloc[k:len(s) - k] if k else s
    print(f"  drop {k:2d} each end: n={len(trimmed):3d}  total ${trimmed.sum():+8.2f}  "
          f"mean ${trimmed.mean():+.4f}")
print()
for k in (1, 3, 5):
    s = Bs.pnl.sort_values()
    print(f"  drop the {k} WORST only: total ${s.iloc[k:].sum():+8.2f}   "
          f"drop the {k} BEST only: total ${s.iloc[:len(s) - k].sum():+8.2f}")

B_.to_csv(os.path.join(OUT, "bot_matches.csv"))
print(f"\nwritten: out/master_ticker.csv, out/master_match.csv, out/bot_matches.csv")
