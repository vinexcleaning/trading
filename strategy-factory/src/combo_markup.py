"""HOW FAR ABOVE ITS LEGS DOES A COMBO QUOTE SIT?

The one number that decides whether a Kalshi parlay can ever be worth taking,
measured rather than argued. Pre-registered in `PREREGISTRATION_COMBOS.md`
BEFORE this file computed anything.

    markup = price actually paid / (product of the legs' own asks at that time)

⚠ THE ASK, NEVER THE MIDDLE PRICE. Buying the legs separately means paying the
ask. Comparing a paid price against a middle price would manufacture a markup
that is really just the legs' own spread, which is the single easiest way to
invent an edge in this whole project.

⚠ ONE OBSERVATION IS ONE DISTINCT SET OF LEGS, NOT ONE COMBO. Combos are built
from one evening's handful of games, so two of them routinely share four legs
of six and their outcomes are nearly the same event. Every count below is
reported twice - combos, and distinct leg-sets - and the smaller one is what
any confidence statement may use.

⚠ THE TIMING ASSUMPTION IS THE WEAK POINT AND IT IS TESTED, NOT ASSERTED.
Kalshi gives `created_time` for the combo market but NO timestamp on the trade
itself. Because the market is created by a request for a quote, the fill is
taken to happen at creation. The pre-registration requires the whole
measurement to be re-run at creation minus and plus one hour; if the middle
markup moves by more than 1 point across that span, the assumption is doing the
work and the answer must be quoted as a range.

⚠ THE TAPE THIS READS IS `devig`'s, NOT MINE, AND THAT IS DELIBERATE.
`bot-hunt/data/combos.db` holds 597,461 distinct combos and 4.5 million legs
covering 2026-08-06 to 09-15. My own recorder was given the same job, died 25
minutes in, and could not restart because of a lock bug of my own making. Two
captures of one public endpoint was already flagged as waste; measuring on the
one that WORKS beats re-capturing what already exists. **Read-only, and this
folder writes nothing into `bot-hunt/`** - DECISIONS.md D2.

⚠ QUERY SHAPE MATTERS MORE THAN THE FILTER. `wide_top` is 30 million rows
indexed on (series, ticker, ts_utc). Looking a leg up by ticker alone scans the
lot and does not finish. Every lookup here passes the series first. This is the
same lesson mailbox 005 gave about the sum-to-one test, arriving again.

    py -3 strategy-factory/src/combo_markup.py
    py -3 strategy-factory/src/combo_markup.py --offset-min -60
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sqlite3
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent))
from common.kalshi_fees import fee_rate_cents  # noqa: E402

COMBO_RATE = 0.07          # every KXMVE* series: fee_multiplier 1, live API
# ⚠ THIS WAS 2 HOURS AND IT WAS WRONG, AND THE WAY IT WAS WRONG THREW AWAY 78
# PERCENT OF THE SAMPLE. `wide_top` is a CHANGE-ONLY tape: a row is written only
# when a quote moves, so a leg that has not traded for three hours has no recent
# row **because its price has not changed**, not because nothing is known. The
# last row before the moment IS the price at that moment. Treating "old row" as
# "no price" excluded 2,347 of 3,000 combos on the first run and would have made
# the whole measurement a statement about which legs happen to be busy.
# 24 hours is a guard against the recorder having been DOWN, which is a
# different question and is reported separately below.
MAX_STALE_H = 24.0


def series_of(ticker: str) -> str:
    return ticker.split("-")[0] if ticker else ""


MONTHS = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
     "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}
TICK_TIME = re.compile(r"^[A-Z0-9]+-(\d{2})([A-Z]{3})(\d{2})(\d{4})")


def event_start(ticker):
    """When the underlying event starts, read out of the ticker itself.

    ⚠ THIS EXISTS BECAUSE NEITHER OBVIOUS TIMESTAMP WORKS, and both failures
    are worth recording rather than quietly routing around.

      * Pricing the legs at the moment the COMBO opened fails: the median leg
        quote was then 57 hours old, because a combo's opening timestamp is not
        the moment somebody asked for the quote.
      * Pricing the legs at their LAST recorded quote fails much worse and in
        the direction that manufactures an edge: a leg's final quote is taken
        minutes after its game finishes, so a losing leg is worth almost
        nothing, the product of the legs collapses towards zero, and the markup
        ratio explodes to six and seven figures. The first run of that version
        reported a middle markup of +211% and a maximum of ten trillion per
        cent, which is not a fee, it is a division by nearly nothing.

    Kalshi's sports tickers carry the event's own start time - `26SEP042005`
    is 4 September 2026, 20:05 - so the reference price is the leg's last ask
    **at least 30 minutes before its own event starts**. That is a real,
    tradeable, pre-game price and it does not depend on any timestamp the
    exchange declines to publish.
    """
    m = TICK_TIME.match(ticker or "")
    if not m:
        return None
    yy, mon, dd, hhmm = m.groups()
    if mon not in MONTHS:
        return None
    try:
        return datetime(2000 + int(yy), MONTHS[mon], int(dd),
                        int(hhmm[:2]), int(hhmm[2:]), tzinfo=timezone.utc)
    except ValueError:
        return None


def parse_ts(s):
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    except ValueError:
        return None


def load_combos(con, limit=0):
    """Settled combos with a price somebody actually paid, one row per combo.

    `devig`'s recorder writes one row per combo PER READ DAY, on the assumption
    that a combo's quote keeps moving. A combo cannot be sold, so I expect it
    cannot - and rather than argue, the query takes the EARLIEST read of each
    ticker and `--price-drift` measures whether the later reads ever disagree.
    """
    sql = ("select c.ticker, c.series_ticker, c.last_price_c, c.volume, "
           "c.open_interest, c.result, c.open_utc, c.close_utc, c.n_legs "
           "from combos c "
           "join (select ticker, min(read_date) rd from combos group by ticker) "
           "     f on f.ticker = c.ticker and f.rd = c.read_date "
           "where c.result is not null and c.result != '' "
           "  and c.last_price_c is not null and c.last_price_c > 0 "
           "  and c.open_utc >= '2026-08-18'")
    if limit:
        sql += " limit %d" % int(limit)
    rows = []
    for (tk, ser, price_c, vol, oi, result, opened, close, n) in con.execute(sql):
        rows.append(dict(ticker=tk, series=ser, price=price_c / 100.0,
                         volume=vol, oi=oi, result=result,
                         created=parse_ts(opened), close=parse_ts(close),
                         n_legs=n, legs=None))
    return rows


def attach_legs(con, rows):
    """Legs come from their own table, one row each, joined by ticker."""
    want = {r["ticker"] for r in rows}
    legs = defaultdict(list)
    for tk, mt, side in con.execute(
            "select ticker, leg_market_ticker, leg_side from combo_legs "
            "order by ticker, leg_index"):
        if tk in want:
            legs[tk].append((mt, side))
    out = []
    for r in rows:
        r["legs"] = legs.get(r["ticker"]) or []
        if r["legs"]:
            out.append(r)
    return out


class LegPrices:
    """Leg asks off this project's own recorded tape.

    Only the tape is used, and the coverage it gives is reported rather than
    quietly patched with a second source. A leg the recorder never saw is
    EXCLUDED WITH THE REASON STORED, never defaulted - the pre-registration
    says so, and `soccer/` defaulting missing features to 0.0 is a recorded
    defect in this repo.
    """

    def __init__(self, path):
        self.c = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
        self.cache = {}
        self.misses = defaultdict(int)

    def last_ask(self, ticker):
        """The leg's LAST recorded ask before it stopped being quoted.

        ⚠ THIS REPLACES A LOOKUP AT THE COMBO'S OPENING TIME, AND THE REASON IS
        A FACT ABOUT KALSHI THAT ALSO INVALIDATES AN EARLIER REPORT OF MINE.

        `close_time` on a Kalshi sports market is NOT when trading stops. Checked
        2026-09-18: `KXMLBGAME-26SEP042005TBTEX` is a game played on 4 September
        at 20:05; its last quote on this tape is 5 September at 02:02, minutes
        after the game ended; and its `close_time` is **8 September** - nearly
        four days later. Every one of 358 baseball markets closing 1-14
        September shows the same ~70-hour offset, so it is the product, not a
        gap.

        That means `reports/COMPLETENESS-01.md`'s finding - "only 7,645 of
        299,360 settled markets had a two-sided quote 60 minutes before close" -
        **was measuring 60 minutes before a settlement deadline that falls days
        after trading ends.** It understates coverage and needs re-running. For
        once a correction in this repo makes the data better rather than worse.

        So the reference price here is the leg's last real quote, which is a
        stable, well-defined moment - "what the leg cost just before its game" -
        rather than a wall-clock lookup against a timestamp the exchange does
        not publish for the trade.
        """
        if ticker in self.cache:
            return self.cache[ticker]
        row = self.c.execute(
            "select ts_utc, yes_ask_c from w_top "
            "where series=? and ticker=? and yes_ask_c is not null "
            "order by ts_utc desc limit 1",
            (series_of(ticker), ticker)).fetchone()
        out = (row[1], 0.0) if row else (None, None)
        if row is None:
            self.misses[series_of(ticker)] += 1
        self.cache[ticker] = out
        return out

    def ask(self, ticker, when):
        """Best recorded ask at or before `when`, plus how stale it is."""
        key = (ticker, when)
        if key in self.cache:
            return self.cache[key]
        ser = series_of(ticker)
        row = self.c.execute(
            "select ts_utc, yes_ask_c from w_top "
            "where series=? and ticker=? and ts_utc<=? and yes_ask_c is not null "
            "order by ts_utc desc limit 1",
            (ser, ticker, when.strftime("%Y-%m-%dT%H:%M:%SZ"))).fetchone()
        if row is None:
            self.misses[ser] += 1
            out = (None, None)
        else:
            seen = parse_ts(row[0])
            out = (row[1], (when - seen).total_seconds() / 3600.0)
        self.cache[key] = out
        return out


def price_one(combo, lp, offset_min=0):
    """Product of the legs' asks for one combo, or a reason it cannot be done."""
    when = combo["created"]
    if when is None:
        return None, "no created_time"
    when = when + timedelta(minutes=offset_min)
    prod = 1.0
    worst_stale = 0.0
    for mt, side in combo["legs"]:
        start = event_start(mt)
        if start is None:
            return None, "leg ticker carries no event time"
        ask_c, stale = lp.ask(mt, start - timedelta(minutes=30 - offset_min))
        if ask_c is None:
            return None, "leg not on tape"
        if stale > MAX_STALE_H:
            return None, "leg quote stale"
        # A NO leg is bought at 100 minus the YES bid, not at 100 minus the
        # YES ask. Inverting is not negating - the same trap corrected in
        # screen.py on 2026-08-20. Legs seen so far are all `yes`; anything
        # else is refused rather than guessed.
        if side != "yes":
            return None, "non-yes leg, not priced here"
        prod *= ask_c / 100.0
        worst_stale = max(worst_stale, stale)
    return (prod, worst_stale), None


def summarise_c(name, vals):
    """Same shape, in cents per contract rather than as a ratio."""
    if not vals:
        print("  %-22s (none)" % name)
        return
    v = sorted(vals)
    print("  %-22s n=%-5d  low %+7.2fc  quarter %+7.2fc  MIDDLE %+7.2fc  "
          "three-quarter %+7.2fc  high %+8.2fc"
          % (name, len(v), v[0], v[len(v) // 4], statistics.median(v),
             v[3 * len(v) // 4], v[-1]))


def summarise(name, vals):
    if not vals:
        print("  %-22s (none)" % name)
        return
    v = sorted(vals)
    print("  %-22s n=%-5d  low %6.1f%%  quarter %6.1f%%  MIDDLE %6.1f%%  "
          "three-quarter %6.1f%%  high %6.1f%%"
          % (name, len(v), 100 * (v[0] - 1), 100 * (v[len(v) // 4] - 1),
             100 * (statistics.median(v) - 1),
             100 * (v[3 * len(v) // 4] - 1), 100 * (v[-1] - 1)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offset-min", type=int, default=0,
                    help="shift the assumed fill time, in minutes")
    ap.add_argument("--placebo-seed", type=int, default=0)
    ap.add_argument("--limit", type=int, default=0,
                    help="cap the number of combos read, for a quick pass")
    args = ap.parse_args()

    con = sqlite3.connect(
        "file:%s?mode=ro" % (ROOT.parent / "bot-hunt" / "data" / "combos.db"),
        uri=True)
    combos = attach_legs(con, load_combos(con, args.limit))
    print("settled combos with a paid price: %d" % len(combos))
    if not combos:
        print("nothing to measure yet - let the recorder finish a sweep")
        return

    lp = LegPrices(ROOT / "data" / "wide_top.db")
    rows, why = [], defaultdict(int)
    for c in combos:
        got, reason = price_one(c, lp, args.offset_min)
        if got is None:
            why[reason] += 1
            continue
        prod, stale = got
        if prod <= 0:
            why["product is zero"] += 1
            continue
        rows.append(dict(c, prod=prod, markup=c["price"] / prod,
                         markup_c=(c["price"] - prod) * 100.0, stale=stale))

    print("priced against the tape: %d  (excluded: %s)"
          % (len(rows), dict(why)))
    if not rows:
        print("\nNOTHING MEASURABLE. That is a coverage result, not a null - "
              "see PREREGISTRATION_COMBOS.md section 5 kill condition 2.")
        return

    # ---- distinct leg-sets, because combos share games -------------------
    sets = defaultdict(list)
    for r in rows:
        sets[frozenset(mt for mt, _ in r["legs"])].append(r)
    distinct_legs = {mt for r in rows for mt, _ in r["legs"]}
    print("distinct leg-sets: %d   distinct legs covered: %d"
          % (len(sets), len(distinct_legs)))

    print("\nMARKUP OVER THE PRODUCT OF THE LEGS' ASKS "
          "(0%% = quoted exactly at the legs; higher = dearer)")
    summarise("every combo", [r["markup"] for r in rows])
    summarise("one per leg-set", [v[0]["markup"] for v in sets.values()])
    by_n = defaultdict(list)
    for r in rows:
        by_n[len(r["legs"])].append(r["markup"])
    for n in sorted(by_n):
        summarise("%d legs" % n, by_n[n])

    # ---- the fee, at the combo's own rate --------------------------------
    fees = [float(fee_rate_cents(r["price"] * 100.0, COMBO_RATE))
            for r in rows]
    stakes = [r["price"] * 100.0 for r in rows]
    print("\nFEE AT THE COMBO'S OWN RATE (0.07, fee_multiplier 1 from the API)")
    print("  middle fee per contract        %.3fc" % statistics.median(fees))
    print("  middle fee per dollar staked   %.2f%%"
          % (100 * statistics.median([f / s for f, s in zip(fees, stakes)])))

    # ---- the naive benchmark --------------------------------------------
    won = [r for r in rows if r["result"] == "yes"]
    print("\nWHAT HAPPENED (the naive benchmark sits beside it)")
    print("  combos that paid out: %d of %d" % (len(won), len(rows)))
    paid = sum(r["price"] * 100.0 for r in rows)
    back = sum(100.0 for r in won)
    fee_tot = sum(fees)
    print("  staked %.0fc, returned %.0fc, fees %.0fc  ->  %+.1f per 100 risked"
          % (paid, back, fee_tot, 100.0 * (back - paid - fee_tot) / paid))
    leg_stake = sum(sum(100.0 * a for a in [r["prod"]]) for r in rows)
    print("  the same money at the legs' own product price would have staked "
          "%.0fc for the same outcomes -> %+.1f per 100 risked"
          % (leg_stake, 100.0 * (back - leg_stake) / leg_stake))

    # ---- scalar / did-not-play, reported on their own line ----------------
    odd = [r for r in rows if r["result"] not in ("yes", "no")]
    print("  results that are neither yes nor no (scalar/DNP): %d" % len(odd))

    # ---- the placebo arm -------------------------------------------------
    rnd = random.Random(args.placebo_seed)
    pool = defaultdict(list)
    for r in rows:
        pool[r["created"].date()].append(r)
    fake = []
    for day, rs in pool.items():
        legs_today = [l for r in rs for l in r["legs"]]
        if len(legs_today) < 2:
            continue
        for r in rs:
            pick = rnd.sample(legs_today, min(len(r["legs"]), len(legs_today)))
            got, _ = price_one(dict(r, legs=pick), lp, args.offset_min)
            if got and got[0] > 0:
                fake.append(r["price"] / got[0])
    print("\nPLACEBO - the same arithmetic on legs re-paired at random from the "
          "same day")
    summarise("shuffled legs", fake)
    print("  If the shuffled markup looks like the real one, this measures the "
          "shape of the day's prices rather than anything about combos.")


if __name__ == "__main__":
    main()
