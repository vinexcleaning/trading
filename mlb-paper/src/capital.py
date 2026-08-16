"""The capital squeeze, and what three selection rules would have returned.

Mailbox 015. His observation: bets go on days before first pitch and are held to
settlement, so money is locked up for a long time. With 10-15 games a day he
runs out of cash before he runs out of signals — **so he is already choosing
which bets to take, by accident, in the order they arrive.**

Three jobs, all measurement, nothing changed:

  1. how long money is tied up, how much is committed at once, how many
     signals would have been unaffordable
  2. the agreement split re-run, and split by BEFORE/AFTER the day the pattern
     was found -- because the games that suggested a pattern cannot also test it
  3. what three rules would have returned, and the capital each needed:
     take everything | skip the alone ones | agreed only

    python src/capital.py [--bankroll 100] [--stake-pct 5]
"""
from __future__ import annotations

import argparse
import collections
import math
import statistics
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine as E                     # noqa: E402

# A cp1252 console cannot print a warning glyph, and the crash lands
# AFTER the numbers are on screen -- which looks like the analysis
# failed when it had already succeeded. Force UTF-8 on stdout.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

FOUND_ON = "2026-08-13"      # the day the agreement pattern was first reported
BOT = "starter__hold"
OTHER = "early__hold"


def binom_tail(k, n, p):
    return sum(math.comb(n, i) * p**i * (1 - p)**(n - i) for i in range(k, n + 1))


def load(con, bot=BOT):
    return con.execute(
        "SELECT game_key, ticker, contracts, entry_price_c, entry_fee_c, "
        "       pnl_c, opened_utc, closed_utc, status "
        "FROM positions WHERE bot=? AND status IN ('settled','closed') "
        "ORDER BY opened_utc", (bot,)).fetchall()


# ------------------------------------------------------------------- job 1

def job1(con, bankroll, stake_pct):
    print("=" * 76)
    print("JOB 1 -- THE CAPITAL SQUEEZE")
    print("=" * 76)
    rows = load(con)
    if not rows:
        print("  no settled positions")
        return {}

    holds = []
    for r in rows:
        if not r["closed_utc"]:
            continue
        a = datetime.fromisoformat(r["opened_utc"])
        b = datetime.fromisoformat(r["closed_utc"])
        holds.append((b - a).total_seconds() / 3600.0)
    holds.sort()
    print(f"\n## how long money is tied up ({len(holds)} bets)\n")
    print(f"  median   {holds[len(holds)//2]:>6.1f} hours "
          f"({holds[len(holds)//2]/24:.1f} days)")
    print(f"  worst    {holds[-1]:>6.1f} hours ({holds[-1]/24:.1f} days)")
    print(f"  quickest {holds[0]:>6.1f} hours")

    # money committed on each calendar day: a bet occupies cash from the moment
    # it is opened until it settles.
    day_cash = collections.defaultdict(float)
    day_open = collections.defaultdict(int)
    for r in rows:
        if not r["closed_utc"]:
            continue
        a = datetime.fromisoformat(r["opened_utc"]).date()
        b = datetime.fromisoformat(r["closed_utc"]).date()
        cost = (r["contracts"] * r["entry_price_c"] + r["entry_fee_c"]) / 100.0
        d = a
        while d <= b:
            day_cash[d] += cost
            day_open[d] += 1
            d += timedelta(days=1)
    days = sorted(day_cash)
    peak_d = max(day_cash, key=lambda k: day_cash[k])
    print(f"\n## how much is committed at once, on the REAL sizes it used\n")
    print(f"  days observed        {len(days)}  ({days[0]} -> {days[-1]})")
    print(f"  peak money at risk   ${day_cash[peak_d]:.2f} on {peak_d}")
    print(f"  peak bets open       {max(day_open.values())}")
    print(f"  median day           ${statistics.median(day_cash.values()):.2f} "
          f"across {statistics.median(day_open.values()):.0f} bets")

    # the capacity question, in his terms
    stake = bankroll * stake_pct / 100.0
    cap = int(bankroll / stake)
    per_day = collections.Counter()
    for r in rows:
        per_day[datetime.fromisoformat(r["opened_utc"]).date()] += 1
    sig = statistics.median(per_day.values()) if per_day else 0
    hold_days = holds[len(holds)//2] / 24
    concurrent = sig * hold_days
    print(f"\n## the sentence that decides everything\n")
    print(f"  ON A ${bankroll:.0f} BANKROLL AT {stake_pct:.0f}% A BET "
          f"(${stake:.2f}), YOU CAN HOLD {cap} BETS AT ONCE.")
    print(f"  THE BOT GENERATED A MEDIAN OF {sig:.0f} A DAY AND HOLDS EACH FOR "
          f"{hold_days:.1f} DAYS,")
    print(f"  SO IT NEEDS ROOM FOR ABOUT {concurrent:.0f} AT ONCE.")
    short = concurrent - cap
    if short > 0:
        print(f"\n  ** SHORT BY ABOUT {short:.0f} BETS. "
              f"{100*short/concurrent:.0f} out of 100 signals go untaken, **")
        print(f"  ** and today they are dropped in arrival order rather than "
              f"by quality. **")
    else:
        print(f"\n  Comfortable: capacity {cap} against a need of "
              f"{concurrent:.0f}.")
    return {"median_hold_h": holds[len(holds)//2], "peak_cash": day_cash[peak_d],
            "capacity": cap, "need": concurrent}


# ------------------------------------------------------------------- job 2

def buckets(con, bot=BOT, other=OTHER, since=None, until=None):
    def sel(b):
        q = ("SELECT game_key, ticker, contracts, entry_price_c, entry_fee_c, "
             "pnl_c, opened_utc FROM positions WHERE bot=? AND "
             "status IN ('settled','closed')")
        a = [b]
        if since:
            q += " AND opened_utc >= ?"
            a.append(since)
        if until:
            q += " AND opened_utc < ?"
            a.append(until)
        return {r["game_key"]: r for r in con.execute(q, a)}
    A, B = sel(bot), sel(other)
    agree, opp, alone = {}, {}, {}
    for g, r in A.items():
        if g not in B:
            alone[g] = r
        elif r["ticker"] == B[g]["ticker"]:
            agree[g] = r
        else:
            opp[g] = r
    return agree, opp, alone


def summarise(name, d):
    if not d:
        return {"label": name, "games": 0}
    pnl = sum(r["pnl_c"] or 0 for r in d.values()) / 100.0
    staked = sum(r["contracts"] * r["entry_price_c"] + r["entry_fee_c"]
                 for r in d.values()) / 100.0
    won = sum(1 for r in d.values() if (r["pnl_c"] or 0) > 0)
    return {"label": name, "games": len(d), "won": won,
            "profit": round(pnl, 2), "staked": round(staked, 2),
            "return_pct": round(100 * pnl / staked, 1) if staked else None}


def job2(con):
    print("\n" + "=" * 76)
    print("JOB 2 -- THE AGREEMENT SPLIT, AND BEFORE vs AFTER THE DAY IT WAS FOUND")
    print("=" * 76)
    ag, op, al = buckets(con)
    print(f"\n## everything settled so far\n")
    print(f"{'bucket':<20} {'games':>6} {'won':>5} {'profit$':>9} "
          f"{'staked$':>9} {'return':>8}")
    tot = {}
    for nm, d in (("agreed", ag), ("opposite sides", op), ("ALONE", al)):
        s = summarise(nm, d)
        tot[nm] = s
        if s["games"]:
            print(f"{nm:<20} {s['games']:>6} {s['won']:>5} {s['profit']:>9.2f} "
                  f"{s['staked']:>9.2f} {str(s['return_pct'])+'%':>8}")

    print(f"\n## split on {FOUND_ON}, the day the pattern was first reported\n")
    print("  The games that SUGGESTED a pattern cannot also TEST it. Only the")
    print("  'new since' column is evidence; the 'found on' column is the")
    print("  hypothesis being tested.\n")
    print(f"{'bucket':<20} {'found on (<=' + FOUND_ON + ')':>28} "
          f"{'new since':>24}")
    before = buckets(con, until=FOUND_ON)
    after = buckets(con, since=FOUND_ON)
    out = {}
    for i, nm in enumerate(("agreed", "opposite sides", "ALONE")):
        b = summarise(nm, before[i])
        a = summarise(nm, after[i])
        out[nm] = {"before": b, "after": a}
        bs = (f"{b['return_pct']:+.1f}% ({b['games']})" if b["games"]
              else "-")
        as_ = (f"{a['return_pct']:+.1f}% ({a['games']})" if a["games"]
               else "-")
        print(f"{nm:<20} {bs:>28} {as_:>24}")

    # how many more agreed games until it is a decision
    print("\n## how many more AGREED games before this is a decision\n")
    a_after = summarise("agreed", after[0])
    al_after = summarise("alone", after[2])
    n_new = a_after["games"]
    print(f"  agreed games since {FOUND_ON}: {n_new}")
    if n_new < 30:
        rows = load(con)
        per_day = collections.Counter(
            datetime.fromisoformat(r["opened_utc"]).date() for r in rows)
        days = max(1, len(per_day))
        ag_all = summarise("agreed", ag)["games"]
        rate = ag_all / days
        for target, why in ((30, "a first real read"),
                            (60, "enough to act on")):
            need = max(0, target - n_new)
            eta = need / rate if rate else float("inf")
            when = (datetime.now(timezone.utc)
                    + timedelta(days=eta)).date().isoformat()
            print(f"  to reach {target:>3} NEW agreed games ({why}): "
                  f"{need} more, ~{eta:.0f} days, about {when}")
        print(f"\n  at the observed rate of {rate:.1f} agreed games a day.")
    return out


# ------------------------------------------------------------------- job 3

def job3(con, bankroll, stake_pct):
    print("\n" + "=" * 76)
    print("JOB 3 -- THREE RULES: what each would have returned, and the cash")
    print("=" * 76)
    ag, op, al = buckets(con)
    rules = {
        "take everything": {**ag, **op, **al},
        "skip the ALONE ones": {**ag, **op},
        "agreed only": dict(ag),
    }
    print(f"\n{'rule':<24} {'games':>6} {'profit$':>9} {'staked$':>9} "
          f"{'return':>8} {'peak cash$':>11} {'bets at once':>13}")
    out = {}
    for nm, d in rules.items():
        s = summarise(nm, d)
        # capital needed under this rule
        day_cash = collections.defaultdict(float)
        day_n = collections.defaultdict(int)
        for g, r in d.items():
            row = con.execute(
                "SELECT opened_utc, closed_utc FROM positions WHERE bot=? "
                "AND game_key=?", (BOT, g)).fetchone()
            if not row or not row["closed_utc"]:
                continue
            a = datetime.fromisoformat(row["opened_utc"]).date()
            b = datetime.fromisoformat(row["closed_utc"]).date()
            cost = (r["contracts"] * r["entry_price_c"] + r["entry_fee_c"]) / 100.0
            dd = a
            while dd <= b:
                day_cash[dd] += cost
                day_n[dd] += 1
                dd += timedelta(days=1)
        peak = max(day_cash.values()) if day_cash else 0.0
        peak_n = max(day_n.values()) if day_n else 0
        out[nm] = dict(s, peak_cash=round(peak, 2), peak_bets=peak_n)
        print(f"{nm:<24} {s['games']:>6} {s['profit']:>9.2f} "
              f"{s['staked']:>9.2f} {str(s['return_pct'])+'%':>8} "
              f"{peak:>11.2f} {peak_n:>13}")

    cap = int(bankroll / (bankroll * stake_pct / 100.0))
    print(f"\n  On a ${bankroll:.0f} bankroll at {stake_pct:.0f}% a bet you can "
          f"hold {cap} at once.")
    for nm, s in out.items():
        fits = "FITS" if s["peak_bets"] <= cap else \
            f"NEEDS {s['peak_bets']} -- does not fit"
        print(f"    {nm:<24} {fits}")
    print("\n  ⚠ 'agreed only' is chosen by looking at which bucket won. It is")
    print("    the SAFE half of that error -- declining a losing bucket rather")
    print("    than doubling into a winning one -- but it is still selection")
    print("    on the past, and the numbers above include the games that")
    print("    suggested it. Job 2's 'new since' column is the honest read.")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bankroll", type=float, default=100.0)
    ap.add_argument("--stake-pct", type=float, default=5.0)
    a = ap.parse_args()
    con = E.connect()
    job1(con, a.bankroll, a.stake_pct)
    job2(con)
    job3(con, a.bankroll, a.stake_pct)
    print("\n" + "=" * 76)
    print("At 10% a bet, capacity halves. Re-run with --stake-pct 10.")
    con.close()
