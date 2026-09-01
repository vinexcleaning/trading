"""Are heavy favourites mispriced? Market implied probability vs observed win rate.

Priority 1 of his research program, answered from data already on disk.

METHOD. One market = one observation. Implied probability is the PREMATCH mid
(state.pre_bid/pre_ask for tennis). Observed win rate is the settled result.
Wilson intervals because the extreme bands are exactly where a normal
approximation misleads.

THE NUMBER THAT MATTERS IS NOT THE GAP. It is the gap against the ASK, because
you cannot buy at the mid. A +1.3 point edge on a 2-cent spread is not an edge.
"""
import sqlite3, math, sys
from pathlib import Path
sys.path.insert(0, r"C:/Users/vinig/trading")
from common.kalshi_fees import fee_order_dollars

BANDS = [(50,55),(55,60),(60,65),(65,70),(70,75),(75,80),(80,85),
         (85,90),(90,92.5),(92.5,95),(95,97.5),(97.5,99),(99,100)]

def wilson(k,n,z=1.96):
    if n==0: return (0,0,0)
    p=k/n; d=1+z*z/n
    c=(p+z*z/(2*n))/d
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return (p,max(0,c-h),min(1,c+h))

def band_of(p):
    for lo,hi in BANDS:
        if lo<=p<hi: return (lo,hi)
    return None

def report(title, rows):
    """rows = list of (implied_pct, ask_pct, won_bool)"""
    print(f"\n{'='*82}\n{title}\n{'='*82}")
    print(f"{'band':>12}{'n':>7}{'implied':>9}{'observed':>10}{'gap':>8}"
          f"{'95% CI of gap':>20}{'EV at ask':>11}")
    buckets={}
    for imp,ask,won in rows:
        b=band_of(imp)
        if b: buckets.setdefault(b,[]).append((imp,ask,won))
    for b in BANDS:
        v=buckets.get(b)
        if not v or len(v)<30:
            if v: print(f"{f'{b[0]}-{b[1]}':>12}{len(v):>7}   (sparse, under 30)")
            continue
        n=len(v); k=sum(1 for x in v if x[2])
        imp=sum(x[0] for x in v)/n
        obs,lo,hi=wilson(k,n)
        gap=100*obs-imp
        glo,ghi=100*lo-imp,100*hi-imp
        # EV of buying at the ask and holding to settlement, per $1 staked
        tot=0.0; st=0.0
        for i2,ask,won in v:
            a=max(1,min(99,round(ask)))
            cost=a/100.0+float(fee_order_dollars(a,1))
            st+=cost; tot+=(1.0 if won else 0.0)-cost
        ev=100*tot/st if st else 0
        print(f"{f'{b[0]}-{b[1]}':>12}{n:>7}{imp:>8.1f}%{100*obs:>9.1f}%"
              f"{gap:>+7.1f}{f'[{glo:+.1f}, {ghi:+.1f}]':>20}{ev:>+10.1f}%")

# ---------------- TENNIS: prematch price vs result, 35,990 markets
db=Path(r"C:/Users/vinig/trading/set1_overshoot/data/maker.db")
c=sqlite3.connect(f"file:{db}?mode=ro",uri=True); c.row_factory=sqlite3.Row
# ⚠ CORRECTED 2026-09-02. The first committed version read every row with a
# prematch price and never read the ok flag p6_state.py stores. 22,974 of
# 35,990 rows (67%) were ones that study had REJECTED, almost all
# 'pre-match book empty' (spread wider than PRE_SPREAD_MAX=10c) - a mid from a
# 1/99 book says 50 and means nothing. The contaminated output was published in
# RESEARCH_PROGRAM.md and corrected inline there (commit 6b44936).
# THE RULE THIS BUG YIELDS: an analysis reading another study's table must
# honour that study's own ok/why flags, and say so.
pre={}
for r in c.execute("SELECT ticker,pre_bid,pre_ask FROM state WHERE ok=1"):
    if r["pre_bid"] and r["pre_ask"] and 0<r["pre_bid"]<=r["pre_ask"]<100:
        pre[r["ticker"]]=(r["pre_bid"],r["pre_ask"])
by_series={}
for r in c.execute("SELECT ticker,series,result FROM markets WHERE result IN ('yes','no')"):
    p=pre.get(r["ticker"])
    if not p: continue
    mid=(p[0]+p[1])/2.0
    by_series.setdefault(r["series"],[]).append((mid,p[1],r["result"]=="yes"))
c.close()
allt=[]
for s,v in sorted(by_series.items(), key=lambda x:-len(x[1])):
    allt+=v
    if len(v)>=400: report(f"TENNIS {s} - prematch price vs actual, {len(v)} markets", v)
report(f"TENNIS, ALL SERIES POOLED - {len(allt)} markets", allt)

# ---------------- BASEBALL: archive, price near close vs result
db2=Path(r"C:/Users/vinig/trading/mlb-paper/data/kalshi_truth.db")
if db2.exists():
    c=sqlite3.connect(f"file:{db2}?mode=ro",uri=True); c.row_factory=sqlite3.Row
    res={r["ticker"]:r["result"]=="yes" for r in
         c.execute("SELECT ticker,result,series FROM market WHERE result IN ('yes','no') AND series='KXMLBGAME'")}
    rows=[]
    seen=set()
    for r in c.execute("SELECT ticker,yes_bid_close_c,yes_ask_close_c FROM candle "
                       "WHERE yes_bid_close_c IS NOT NULL AND yes_ask_close_c IS NOT NULL "
                       "ORDER BY ticker, end_ts"):
        t=r["ticker"]
        if t in seen or t not in res: continue
        seen.add(t)                     # FIRST candle = earliest observed price
        b,a=r["yes_bid_close_c"],r["yes_ask_close_c"]
        if 0<b<=a<100: rows.append(((b+a)/2.0,a,res[t]))
    c.close()
    report(f"BASEBALL who-wins, earliest recorded price vs actual - {len(rows)} markets", rows)
