"""THE SCREENING ENGINE — stage 3, and it reports nothing to him as money.

`STRATEGY_FACTORY.md` rule 1: **the backtest chooses; only the forward test
counts.** Every number this file produces selects candidates and nothing else.
Every report states how many specs were screened, because without that a return
is uninterpretable: the best of 2,000 zero-skill strategies clears +30% about
**34 times in 100** (`bestofn.py`, exact).

WHAT IT ENFORCES, and each is a rule this repo paid for:

  * **Real bid and real ask from the tape. Never the mid.** Buying YES lifts the
    ask; buying NO lifts `100 - yes_bid`. GUARDS #7.
  * **Real fees from `common/kalshi_fees.py` only.** Guard #6, test-enforced.
  * **Return on CASH OUT OF POCKET**, price plus fee, not on price staked. One
    cent of difference in the denominator halved the best-of-N answer once
    already (DECISIONS.md D6).
  * **Capacity on every result**, by walking the recorded ladder for $50, $200
    and $500. A result without a capacity line is not finished.
  * **A placebo arm in every run.** Same machinery, labels shuffled WITHIN
    (series, day) so the placebo keeps the real price and fee distribution and
    destroys only the link between rule and outcome. If the placebo scores at or
    above the real arm, **the whole run is void and says so.**
  * **The unit is the settled market**, and where a family is a ladder on one
    event the EVENT count is reported beside it. LEDGER K003 was retracted for
    counting a 10-strike ladder as 10 observations.

WHAT IT DOES NOT DO, said out loud rather than hidden. Most specs in this folder
need data this project does not have - goal times, club identities, line-up
publication times, external reference prices. Those are reported as **NOT
SCREENED, with the reason**, and they still count toward the screened total.
Pretending to screen them would be the most expensive kind of output.

    py -3 strategy-factory/src/screen.py --index
    py -3 strategy-factory/src/screen.py
"""
from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT / "src"))
from decimal import Decimal  # noqa: E402
from common.kalshi_fees import (  # noqa: E402
    TAKER_RATE, fee_order_cents, fee_rate_cents)

IDX = ROOT / "data" / "index.db"

# ⚠ THE FEE IS PER SERIES, AND 19 KALSHI FAMILIES CHARGE HALF.
#
# Kalshi exposes `fee_multiplier` on every series and the exchange actually uses
# it: **every baseball family is 0.5** - KXMLBGAME, KXMLBTOTAL, KXMLBKS and 16
# more - so their real taker rate is 0.035, not 0.07. Fourteen further series
# are 0.0, genuinely free. Verified against the live `/series/{t}` endpoint on
# 2026-09-01, not just off the census snapshot.
#
# `common/kalshi_fees.py` has supported this the whole time via
# `SeriesFees.taker_rate`. This engine was not using it, and neither is
# `mlb-paper` - which means baseball costs were being overstated by a factor of
# two, at 0.875c per contract at middling prices.
_RATES = {}


def rate_for(series):
    """Taker rate for one series, from the census. Defaults to standard."""
    if not _RATES:
        try:
            cc = sqlite3.connect(
                "file:%s?mode=ro" % (ROOT / "data" / "census.db"), uri=True)
            for tk, mult in cc.execute(
                    "select ticker, fee_multiplier from series"):
                if mult is not None:
                    _RATES[tk] = TAKER_RATE * Decimal(str(mult))
            cc.close()
        except sqlite3.Error:
            pass
    return _RATES.get(series, TAKER_RATE)
# ⚠ THE PER-ORDER ROUND-UP IS NOT AN ECONOMIC COST, AND CHARGING IT PER
# CONTRACT INFLATED EVERY FEE THIS ENGINE REPORTED.
#
# v1 used `fee_order_cents(price, 1)` everywhere - the cost Kalshi bills for an
# order of ONE contract, which is rounded UP to a whole cent. Used as a
# per-contract expectancy cost that is simply wrong, and it is worst exactly
# where it matters most:
#
#     price   true per-contract fee   what v1 charged   inflation
#       5c           0.333c                1.000c          3.01x
#      50c           1.750c                2.000c          1.14x
#      97c           0.204c                1.000c          4.91x
#
# So the bug was largest at the extreme prices where the fee-curvature lens says
# the value is - it was actively hiding the thing that column exists to reveal.
#
# `common/kalshi_fees.py` separates the two on purpose:
#   fee_rate_cents  - unrounded, for expectancy: "is there an edge here"
#   fee_order_cents - rounded up per order, for "what will THIS order be billed"
#
# This is not hypothetical. bot-forensics charged the round-up on single-contract
# orders and a recorded result read -0.77c per contract when the fee-fair number
# is about -0.37c.


IDX_SCHEMA = """
-- One row per settled market that we also have a price for. This is the join
-- the whole engine runs on, materialised once instead of every query: w_top is
-- 2.7 million rows and its index is (series, ticker, ts), so a bare
-- ticker-keyed join scans the lot. Mailbox 005: "index the tape first".
create table if not exists ev (
  ticker text primary key, series text, event_ticker text,
  result text, close_utc text,
  n_quotes integer,
  first_ts text, last_ts text,
  entry_ts text, entry_bid_c real, entry_ask_c real,
  entry_bid_size real, entry_ask_size real,
  last_bid_c real, last_ask_c real);
create index if not exists ix_ev_ser on ev(series, close_utc);
"""


def idx_con(ro=False):
    if ro:
        return sqlite3.connect("file:%s?mode=ro" % IDX, uri=True)
    c = sqlite3.connect(IDX, timeout=120.0)
    c.execute("pragma journal_mode=WAL")
    c.executescript(IDX_SCHEMA)
    return c


# ----------------------------------------------------------------- index ----

def build_index(entry_lead_min: int) -> int:
    """Materialise settled-market + price into one table.

    `entry_lead_min` is how long before close the entry quote is taken. It is a
    parameter and it is FIXED BEFORE THE RUN, not swept - sweeping the entry
    time and reporting the best is the best-of-N trap applied to a parameter
    instead of a strategy.
    """
    c = idx_con()
    c.execute("attach database ? as s", (str(ROOT / "data" / "settled.db"),))
    c.execute("attach database ? as w", (str(ROOT / "data" / "wide_top.db"),))
    print("indexing... (one pass over the tape, then one pass over settlements)",
          flush=True)

    # Pull every quote for tickers that settled, in one ordered scan.
    c.execute("create temp table want as select ticker, result, close_utc, "
              "series, event_ticker from s.settled where result in ('yes','no')")
    c.execute("create index tw on want(ticker)")
    n_want = c.execute("select count(*) from want").fetchone()[0]
    print("  settled markets with a yes/no result: %d" % n_want, flush=True)

    rows = defaultdict(list)
    got = 0
    for tk, ts, yb, ya, bs, asz in c.execute(
            "select t.ticker, t.ts_utc, t.yes_bid_c, t.yes_ask_c, "
            "t.bid_size, t.ask_size from w.w_top t "
            "where t.ticker in (select ticker from want) order by t.ts_utc"):
        rows[tk].append((ts, yb, ya, bs, asz))
        got += 1
    print("  recorded quotes for those markets: %d across %d tickers"
          % (got, len(rows)), flush=True)

    import datetime as dt
    F = "%Y-%m-%dT%H:%M:%SZ"
    out = []
    for tk, res, close, ser, ev in c.execute(
            "select ticker, result, close_utc, series, event_ticker from want"):
        q = rows.get(tk)
        if not q:
            continue
        try:
            cl = dt.datetime.strptime(close, F)
        except (TypeError, ValueError):
            continue
        # ENTRY = the last quote at least `entry_lead_min` before close, and
        # both sides must be quoted. A one-sided book is not an entry.
        cut = cl - dt.timedelta(minutes=entry_lead_min)
        ent = None
        for ts, yb, ya, bs, asz in q:
            try:
                t = dt.datetime.strptime(ts, F)
            except ValueError:
                continue
            if t <= cut and yb is not None and ya is not None:
                ent = (ts, yb, ya, bs, asz)
        last = q[-1]
        out.append((tk, ser, ev, res, close, len(q), q[0][0], q[-1][0],
                    ent[0] if ent else None, ent[1] if ent else None,
                    ent[2] if ent else None, ent[3] if ent else None,
                    ent[4] if ent else None, last[1], last[2]))
    c.executemany("insert or replace into ev values "
                  "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", out)
    c.commit()
    n_ent = c.execute("select count(*) from ev where entry_ask_c is not null"
                      ).fetchone()[0]
    print("  indexed %d markets, %d with a two-sided entry quote %d min before "
          "close" % (len(out), n_ent, entry_lead_min), flush=True)
    c.close()
    return n_ent


# ------------------------------------------------------------- economics ----

def net_cents(entry_ask_c, won, contracts=1, rate=None):
    """Cents made per contract buying YES at the real ask and holding.

    Fee on ENTRY ONLY - Kalshi charges nothing at settlement, which
    `common/kalshi_fees.py` states in `roundtrip_cost_cents`.
    """
    fee = float(fee_rate_cents(entry_ask_c, rate or TAKER_RATE))
    gross = (100.0 - entry_ask_c) if won else (-entry_ask_c)
    return gross - fee


def outlay_cents(entry_ask_c, contracts=1, rate=None):
    """Cash that actually leaves the account: price PLUS fee."""
    return entry_ask_c + float(fee_rate_cents(entry_ask_c, rate or TAKER_RATE))


def inverted_net_cents(entry_bid_c, won, contracts=1, rate=None):
    """Cents made per contract taking the OTHER SIDE at ITS real ask.

    ⚠ INVERTING IS NOT NEGATING. This is the whole point of the screen and the
    reason a naive "flip the losers" produces a null.

    Buying YES lifts the YES ask. Buying NO lifts the NO ask, which on Kalshi is
    `100 - yes_bid`. So the inverted trade **pays the spread again, in the other
    direction, and pays a fee again**. A strategy that loses exactly what it
    costs to trade therefore loses the same amount inverted - there is nothing
    to recover. Only a strategy losing materially MORE than its cost bar has
    something underneath the costs to flip.

    `mlb-paper` measured both cases on real bots, which is what makes this a
    screen rather than a slogan: `bullpen__free` went -34.3% to +18.9% at a 4c
    spread assumption, while `early__free` went -14.9% to -0.3% and had nothing
    in it.
    """
    no_ask_c = 100.0 - entry_bid_c
    fee = float(fee_rate_cents(no_ask_c, rate or TAKER_RATE))
    gross = (100.0 - no_ask_c) if (not won) else (-no_ask_c)
    return gross - fee


def cost_bar_cents(entry_bid_c, entry_ask_c, contracts=1, rate=None):
    """What it costs to trade this market at all, at ITS OWN price.

    ⚠ COMPUTED AT THE PRICE THE STRATEGY ACTUALLY TRADES AT, never at 50c.
    `CLAUDE.md` §9c step 5 is explicit that this repo quotes a habitual "3.6 to
    4.8 cents" that is wrong by roughly twenty times at extreme prices - the fee
    at 97c is 0.20c. A screen that judged "does it lose more than the bar" with
    a constant bar would call every cheap strategy anti-predictive and every
    expensive one fee-leaking.

    Two components, both real:
      * half the spread - buying at the ask when the fair value is the mid
      * the entry fee at that price, from the one fee implementation

    Slippage beyond the touch is NOT included and that is a stated limitation:
    entries here are priced at the recorded touch, so a strategy that would have
    walked the book pays more than this bar says. Capacity is reported
    separately for that reason.
    """
    half_spread = max(0.0, (entry_ask_c - entry_bid_c) / 2.0)
    fee = float(fee_rate_cents(entry_ask_c, rate or TAKER_RATE))
    return half_spread + fee


def fee_c_at(price_c, contracts=1, rate=None):
    """The fee at THIS price, per contract. Never at 50c."""
    if not price_c or price_c <= 0 or price_c >= 100:
        return 0.0
    return float(fee_rate_cents(price_c, rate or TAKER_RATE))


def wilson(k, n):
    """A range for a rate, wide when n is small. Reported as 'out of 100'."""
    if n == 0:
        return (0.0, 1.0)
    z = 1.96
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return ((c - r) / d, (c + r) / d)


# --------------------------------------------------------------- capacity ----

def capacity(c, ticker, entry_ts, dollars):
    """What it ACTUALLY costs to fill `dollars` here, by walking the ladder.

    His explicit question, and the reason tier A stores whole ladders rather
    than a depth summary: not "what is the price" but "what would it cost me to
    put five hundred dollars in".

    Returns (filled_dollars, avg_price_c, levels_used) or None when this market
    has no recorded ladder - in which case the answer is NOT ASSUMED. A market
    with no depth data gets no capacity claim.
    """
    # ⚠ PASS THE SERIES. `w_depth`'s index is (series, ticker, ts_utc), so a
    # ticker-only predicate cannot use it and scans 300,000+ rows -- times
    # three dollar targets, times every sampled market. That is what made a
    # screening run die after ten minutes without writing anything.
    row = c.execute(
        "select no_ladder from d.w_depth where series=? and ticker=? "
        "order by abs(julianday(ts_utc)-julianday(?)) limit 1",
        (ticker.split("-")[0], ticker, entry_ts)).fetchone()
    if not row or not row[0]:
        return None
    try:
        no_lv = json.loads(row[0])
    except ValueError:
        return None
    # Buying YES lifts the ask, and the YES ask ladder is the NO bid ladder
    # mirrored: a NO bid at p is a YES offer at 100-p. Best offer = highest NO
    # bid = last element.
    offers = sorted(((100.0 - p, sz) for p, sz in no_lv if sz > 0))
    spent = 0.0
    contracts = 0.0
    used = 0
    for px, sz in offers:
        if spent >= dollars:
            break
        take = min(sz, (dollars - spent) / (px / 100.0))
        if take <= 0:
            break
        spent += take * px / 100.0
        contracts += take
        used += 1
    if contracts <= 0:
        return None
    return (spent, spent / contracts * 100.0, used)


# ---------------------------------------------------------------- screen ----

def screen_hold(c, series_list, lo, hi, max_spread, label, placebo_seed=None,
                null_at="mid"):
    """The hold-to-settlement family: buy at the real ask, wait, settle.

    This is the shape most specs in this folder reduce to. `placebo_seed` runs
    the SAME machinery with results shuffled within (series, close-day), which
    preserves the real distribution of prices, spreads and family sizes and
    destroys only the link between the rule and the outcome.
    """
    q = ("select ticker, series, event_ticker, result, close_utc, "
         "entry_ts, entry_ask_c, entry_bid_c, last_bid_c, last_ask_c from ev "
         "where entry_ask_c is not null and entry_ask_c between ? and ? "
         "and (entry_ask_c - entry_bid_c) <= ?")
    args = [lo, hi, max_spread]
    if series_list:
        q += " and series in (%s)" % ",".join("?" * len(series_list))
        args += list(series_list)
    rows = c.execute(q, args).fetchall()
    if not rows:
        return None

    if placebo_seed is not None:
        # ⚠ THE FIRST PLACEBO WAS ALGEBRAICALLY A NO-OP AND THE RUN CAUGHT IT.
        #
        # v1 shuffled the settlement labels WITHIN each (family, day) group.
        # Twenty seeds returned -8.44% every time, to the decimal, because:
        #
        #     total net = 100 * (number of wins) - sum(ask) - sum(fee)
        #
        # A within-group permutation preserves the number of wins, and ask and
        # fee never depended on the label at all. So the total is invariant by
        # construction. **A placebo that cannot move is not a control, it is
        # decoration** - and it would have signed off on every future run.
        #
        # THE CORRECT NULL for "the market price is the truth" is to redraw
        # each outcome from the market's OWN implied probability. That keeps
        # every price, spread and fee exactly as recorded and replaces only the
        # thing under test: whether the outcome is related to anything but the
        # price.
        #
        # ⚠ THIS IS THE ONE PLACE THE MID IS USED, AND IT IS NOT AN EXECUTION
        # PRICE. GUARDS #7 forbids marking or filling at the mid, and nothing
        # here does: entries are still the real ask. The mid is used only as
        # the market's own estimate of the probability, which is exactly what
        # the null hypothesis says it is.
        rng = random.Random(placebo_seed)
        rows = [list(r) for r in rows]
        for r in rows:
            ask, bid = r[6], r[7]
            p_imp = (ask / 100.0) if null_at == "ask" else ((ask + bid) / 2.0) / 100.0
            p_imp = min(max(p_imp, 0.0), 1.0)
            r[3] = "yes" if rng.random() < p_imp else "no"

    tot_net = 0.0
    tot_out = 0.0
    tot_inv = 0.0
    tot_bar = 0.0
    tot_px = 0.0
    tot_rate = 0.0
    tot_clv = 0.0
    n_clv = 0
    n = wins = 0
    events = set()
    per_bucket = defaultdict(lambda: [0, 0, 0.0, 0.0])
    for tk, ser, ev, res, close, ets, ask, bid, lbid, lask in rows:
        won = (res == "yes")
        rt = rate_for(ser)
        net = net_cents(ask, won, rate=rt)
        out = outlay_cents(ask, rate=rt)
        tot_net += net
        tot_out += out
        tot_inv += inverted_net_cents(bid, won, rate=rt)
        tot_bar += cost_bar_cents(bid, ask, rate=rt)
        tot_rate += float(rt)
        tot_px += ask
        # CLOSING-LINE VALUE: did we buy cheaper than the market ended up
        # pricing it? Mailbox 009 - it needs NO outcome data, so it gives a
        # signal long before enough markets settle to measure profit. The
        # closing mark is the last recorded MID, used here as a price level and
        # not as a fill (GUARDS #7 forbids the mid as an execution price, which
        # this is not).
        if lbid is not None and lask is not None:
            tot_clv += ((lbid + lask) / 2.0) - ask
            n_clv += 1
        n += 1
        wins += won
        events.add(ev or tk)
        b = per_bucket[int(ask // 10) * 10]
        b[0] += 1
        b[1] += won
        b[2] += net
        b[3] += out
    per_net = tot_net / n if n else 0.0
    per_inv = tot_inv / n if n else 0.0
    per_bar = tot_bar / n if n else 0.0
    # gross = what is left once the cost of trading is added back. It is the
    # part that is about PICKING rather than PAYING.
    per_gross = per_net + per_bar
    # INVERTIBLE only when the picking itself is bad by materially more than the
    # bar. "Materially" is one whole cost bar, fixed here and not tuned: a
    # threshold chosen after seeing which strategies pass it would be the
    # best-of-N trap wearing a parameter.
    invertible = per_gross < -per_bar and per_inv > 0
    avg_px = tot_px / n if n else 0.0
    # ⚠ FEE CURVATURE. Kalshi's fee is 0.07*C*p*(1-p): maximised at 50c and
    # collapsing at the extremes. A 2c edge at 95c survives as +1.67c; the SAME
    # 2c edge at 50c survives as +0.25c - nearly seven times less. So the price
    # a strategy trades at is part of its value, not a detail, and this column
    # exists because nothing in the engine knew that.
    avg_rate = Decimal(str(tot_rate / n)) if n else TAKER_RATE
    fee_at_px = fee_c_at(avg_px, rate=avg_rate)
    edge_after_fee = per_gross - fee_at_px
    per_clv = tot_clv / n_clv if n_clv else 0.0
    return {"label": label, "n": n, "events": len(events), "wins": wins,
            "net_c": tot_net, "outlay_c": tot_out,
            "ret": tot_net / tot_out if tot_out else 0.0,
            "per_c": per_net,
            "per_bar_c": per_bar, "per_gross_c": per_gross,
            "avg_px_c": avg_px, "fee_at_px_c": fee_at_px,
            "avg_rate": float(avg_rate),
            "edge_after_fee_c": edge_after_fee,
            "clv_c": per_clv, "n_clv": n_clv,
            "per_inv_c": per_inv, "invertible": invertible,
            "buckets": {k: v for k, v in sorted(per_bucket.items())}}


#: Which LIVE specs the hold-to-settlement machinery can actually run, and why
#: each of the others cannot. **This table is the honest half of the report.**
#: A spec listed as NOT SCREENED still counts toward the screened total; what it
#: does not do is produce a number nobody could defend.
SCREENABLE = {
    "SF005": "crypto hold-to-settlement price curve",
    "SF006": "economics hold-to-settlement price curve",
    "SF013": "commodities hold-to-settlement price curve",
    "SF023": "entertainment (Rotten Tomatoes) availability + hold",
    "SF024": "politics numeric-ladder hold",
    "SF025": "GPU monthly price ladder hold",
}
NOT_SCREENED = {
    "SF001": "needs strikes GROUPED into ladders per event, plus tier A depth "
             "on both legs at the same instant. The grouping code does not "
             "exist yet.",
    "SF002": "same as SF001, and additionally needs a proven-complete tiling - "
             "the exact check whose absence retracted LEDGER C014.",
    "SF003": "needs a fill model for a RESTING order. The tape records the "
             "book, not whether our hypothetical quote would have been hit, "
             "and inventing that model is how a maker strategy flatters "
             "itself.",
    "SF004": "same resting-order fill model as SF003.",
    "SF007": "needs the publication instant of each settlement source. Not on "
             "tape and not in the Kalshi metadata.",
    "SF008": "already run as a canary rather than a trade - 85,498 snapshots, "
             "0 crossed books (reports/RECORDER_LIVE.md). Nothing to screen.",
    "SF009": "needs spread and win markets PAIRED per game. The join is proven "
             "(32 of 32 NFL events) but the pairing code does not exist yet.",
    "SF010": "needs a margin ladder summed per race and paired to a winner "
             "market. Same missing grouping code as SF001.",
    "SF014": "unit is the SPEECH, and the tape has no speech calendar. Grouping "
             "word markets by event is possible; dating the speech is not.",
    "SF017": "needs all 30 MLB team ladders quoted at one instant plus games "
             "played to date. Neither is derivable from this tape alone.",
    "SF018": "needs GOAL TIMES and per-club behaviour history. No goal data in "
             "this project at all.",
    "SF019": "needs a fixture list to count games in the last 10 days.",
    "SF020": "needs line-up publication times.",
    "SF021": "needs goals scored per club and an opponent-quality table.",
    "SF022": "needs the same per-competition goal data as SF021.",
    "SF100": "tennis chat's spec - needs match-state data this project has "
             "not got. Left for the chat that wrote it.",
    "SF101": "tennis chat's spec - same.",
    "SF102": "tennis chat's spec - complement pairing, needs both player "
             "markets grouped per match.",
    "SF103": "tennis chat's spec - needs player history.",
    "SF110": "tennis chat's spec - needs an exit simulation.",
    "SF111": "tennis chat's spec, and it is already a FORWARD result rather "
             "than a candidate: 17 bots, 1,037 settled matches, every one "
             "inside its own no-skill range.",
}


def load_specs():
    import spec as SP
    return [(p, s) for p, s in SP.load_all() if "_parse_error" not in s]


def fmt_money(cents):
    return "%+.2fc" % cents


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", action="store_true")
    ap.add_argument("--entry-lead-min", type=int, default=60)
    ap.add_argument("--placebos", type=int, default=20)
    ap.add_argument("--out", default=str(ROOT / "reports" / "SCREEN-01.md"))
    args = ap.parse_args()

    if args.index:
        build_index(args.entry_lead_min)
        return

    if not IDX.exists():
        raise SystemExit("run with --index first")
    c = idx_con(ro=True)
    c.execute("attach database ? as d",
              (str(ROOT / "data" / "wide_depth.db"),))

    shape = json.loads((ROOT / "data" / "shape.json").read_text(encoding="utf-8"))
    per = shape["per_series"]
    specs = load_specs()
    n_specs = len(specs)
    n_live = sum(1 for _, s in specs if s.get("status", "LIVE") == "LIVE")

    # ---- what is actually in the index, per category
    cat_of = {}
    for ser in set(r[0] for r in c.execute("select distinct series from ev")):
        cat_of[ser] = per.get(ser, {}).get("category") or "(unclassified)"
    idx_cat = defaultdict(lambda: [0, 0])
    for ser, n, ne in c.execute(
            "select series, count(*), sum(case when entry_ask_c is not null "
            "then 1 else 0 end) from ev group by series"):
        k = cat_of.get(ser, "(unclassified)")
        idx_cat[k][0] += n
        idx_cat[k][1] += ne or 0

    # ---- THE RUN: real arm, then the placebo arm
    print("screening the whole index...", flush=True)
    real = screen_hold(c, None, 5, 95, 8, "ALL MARKETS")
    placebos, placebos_ask = [], []
    for i in range(args.placebos):
        r = screen_hold(c, None, 5, 95, 8, "p", placebo_seed=1000 + i)
        if r:
            placebos.append(r["ret"])
        r2 = screen_hold(c, None, 5, 95, 8, "p", placebo_seed=1000 + i,
                         null_at="ask")
        if r2:
            placebos_ask.append(r2["ret"])
    placebos.sort()
    placebos_ask.sort()
    print("  real %+.2f%%   placebo median %+.2f%%   placebo range %+.2f%% to "
          "%+.2f%%" % (100 * real["ret"], 100 * placebos[len(placebos) // 2],
                       100 * placebos[0], 100 * placebos[-1]), flush=True)

    # ---- per category
    percat = {}
    for cat in sorted(idx_cat):
        sers = [s for s, k in cat_of.items() if k == cat]
        r = screen_hold(c, sers, 5, 95, 8, cat)
        if not r:
            continue
        ps = []
        for i in range(max(5, args.placebos // 8)):
            q = screen_hold(c, sers, 5, 95, 8, "p", placebo_seed=2000 + i)
            if q:
                ps.append(q["ret"])
        ps.sort()
        percat[cat] = (r, ps)

    # ---- capacity, on the best category by return
    caps = []
    for cat, (r, ps) in percat.items():
        rows = c.execute(
            "select ticker, entry_ts from ev where entry_ask_c is not null "
            "and series in (%s) limit 80"
            % ",".join("?" * len([s for s, k in cat_of.items() if k == cat])),
            [s for s, k in cat_of.items() if k == cat]).fetchall()
        hits = {50: [], 200: [], 500: []}
        for tk, ets in rows:
            got500 = capacity(c, tk, ets, 500)
            if not got500:
                continue
            hits[500].append(got500[0])
            for d in (50, 200):
                got = capacity(c, tk, ets, d)
                if got:
                    hits[d].append(got[0])
        caps.append((cat, {d: (len(v), sum(v) / len(v) if v else 0.0)
                           for d, v in hits.items()}))

    L = []
    A = L.append
    A("# SCREENING RUN 01 — and not one number here is money")
    A("")
    A("**Run %s by `strategy-factory/src/screen.py`.**"
      % __import__("time").strftime("%Y-%m-%d %H:%M UTC",
                                    __import__("time").gmtime()))
    A("")
    A("> **THE BACKTEST CHOOSES. ONLY THE FORWARD TEST COUNTS.** Nothing below "
      "is a result, none of it may be sized on, and none of it should be "
      "repeated to anyone as an amount of money. It exists to pick candidates.")
    A("")
    A("**%d specs written, %d LIVE, and %d of them could actually be run.** "
      "That last number is the one that matters and it is small: most specs in "
      "this folder need data this project does not have. The list of what was "
      "NOT screened, and why, is section 4 - it is the honest half of this "
      "report." % (n_specs, n_live, len(SCREENABLE)))
    A("")
    A("## 1. THE PLACEBO ARM — read this before any other number")
    A("")
    A("The same machinery, on the same tape, with **every outcome redrawn from "
      "the market\'s own implied probability**. Prices, spreads and fees stay "
      "exactly as recorded; only the thing under test is replaced - whether "
      "the outcome is related to anything other than the price.")
    A("")
    A("> ⚠ **THE FIRST PLACEBO I BUILT WAS ALGEBRAICALLY A NO-OP, AND THIS RUN "
      "IS WHAT CAUGHT IT.** It shuffled settlement labels within each (family, "
      "day) group. Twenty seeds returned **-8.44% every single time, to the "
      "decimal.** The reason is one line of algebra: total net = 100 x (number "
      "of wins) - sum(ask) - sum(fee), a within-group permutation preserves "
      "the number of wins, and ask and fee never depended on the label. **The "
      "control could not move.** A placebo that cannot move is not a control, "
      "it is decoration, and it would have signed off on every run this engine "
      "ever does. Replaced with the null above.")
    A("")
    A("**One note on the mid, because this repo has a hard rule against it.** "
      "GUARDS #7 forbids marking or filling at the mid, and nothing here does - "
      "every entry is the real recorded ask. The mid appears once, as the "
      "market\'s own estimate of the probability when drawing the null. That "
      "is what the null hypothesis literally asserts, and it is not an "
      "execution price.")
    A("")
    A("| | return on cash |")
    A("|---|---:|")
    A("| **real arm** | **%+.2f%%** |" % (100 * real["ret"]))
    A("| placebo median (%d runs) | %+.2f%% |"
      % (len(placebos), 100 * placebos[len(placebos) // 2]))
    A("| placebo range | %+.2f%% to %+.2f%% |"
      % (100 * placebos[0], 100 * placebos[-1]))
    A("| **null drawn at the ASK** (matched to what we actually pay) | **%+.2f%%** |"
      % (100 * placebos_ask[len(placebos_ask) // 2]))
    A("| its range | %+.2f%% to %+.2f%% |"
      % (100 * placebos_ask[0], 100 * placebos_ask[-1]))
    A("")
    A("**TWO nulls, because one of them is unfair and it is the one that "
      "flatters nobody.** The mid null asks *\"is the mid the truth?\"* while "
      "our entries pay the **ask** - so it is advantaged by roughly half a "
      "spread before anything else happens, and the real arm should be below "
      "it even if the market is perfectly fair. The ask null asks the question "
      "that matters: *\"given what we actually paid, did the outcomes beat "
      "it?\"* Both are reported so neither can be quoted alone.")
    A("")
    med_ask = placebos_ask[len(placebos_ask) // 2]
    if real["ret"] <= med_ask:
        A("> ⚠ **THE REAL ARM DOES NOT BEAT ITS MATCHED NULL.** Buying "
          "indiscriminately at the recorded ask and holding to settlement did "
          "no better than the outcomes being drawn from the price we paid. "
          "**By the rule fixed in `PREREGISTRATION.md` §3 nothing this run "
          "produced may be promoted**, and it is reported that way rather than "
          "mined for a subset that looks better. This is also the expected "
          "answer: `CLAUDE.md` §9c step 3 says the general, all-markets version "
          "is normally flat or negative, and §7 of the pre-registration said so "
          "in advance.")
    else:
        A("> The real arm sits above its matched null. **That is the minimum "
          "bar and not evidence of anything** - it says the machinery is not "
          "finding an edge in pure noise, which is a statement about the "
          "machinery. No strategy may be promoted on it, and no category here "
          "is near the 100 settled units required.")
    A("")
    A("## 2. What the tape can actually answer")
    A("")
    A("| | |")
    A("|---|---:|")
    A("| settled markets with a recorded price | **%d** |"
      % c.execute("select count(*) from ev").fetchone()[0])
    A("| of those, with a **two-sided quote 60 min before close** | **%d** |"
      % c.execute("select count(*) from ev where entry_ask_c is not null"
                  ).fetchone()[0])
    A("| markets in the screened price and spread band | **%d** |" % real["n"])
    A("| distinct EVENTS behind them | **%d** |" % real["events"])
    A("")
    A("> ⚠ **The second row is a finding on its own and it is not good news for "
      "trading.** Most settled markets had no two-sided quote an hour before "
      "they closed. That is `GUARDS.md` #24 - *the market does not quote a "
      "near-certainty* - showing up across the whole exchange rather than in "
      "one sport. **A strategy cannot trade what is not quoted**, and any "
      "backtest that assumes it can is measuring a market that does not exist.")
    A("")
    A("**Markets and EVENTS are different numbers and both are shown**, because "
      "a ladder of strikes on one underlying is one observation, not twenty. "
      "LEDGER K003 was retracted for exactly that.")
    A("")
    A("## 3. BREADTH — every category in the census gets a row")
    A("")
    A("⚠ **`GUARDS.md` #24 requires the availability rate to be reported BESIDE "
      "the edge, always, and never used as a pass/fail gate** - *an edge "
      "measured on 5 out of 100 moments is a statement about those 5 moments*. "
      "The **quotable** column is that rate: of the settled markets we have a "
      "price for, how many had a two-sided quote when the rule wanted to "
      "enter. Read it next to every return on this table.")
    A("")
    A("| category | in index | **quotable** | screened | net per contract | vs null | verdict |")
    A("|---|---:|---:|---:|---:|---|---|")
    for cat in sorted(idx_cat):
        n_idx, n_ent = idx_cat[cat]
        # Below 1 in 100 needs a decimal, or a row reads "0 in 100" beside a
        # screened count of 130 and looks like a contradiction rather than a
        # very small number.
        rate = 100.0 * n_ent / max(n_idx, 1)
        avail = "%d (%s in 100)" % (
            n_ent, ("%.1f" % rate) if rate < 1 else ("%.0f" % rate))
        if cat not in percat:
            A("| %s | %d | %s | 0 | - | - | nothing in the price/spread band |"
              % (cat, n_idx, avail))
            continue
        r, ps = percat[cat]
        med = ps[len(ps) // 2] if ps else 0.0
        beats = r["ret"] > med
        # ⚠ THE VERDICT CARRIES ITS OWN SAMPLE GUARD, because a verdict is the
        # part that gets quoted alone. "above placebo" on 36 events is exactly
        # the sentence this whole project exists to stop travelling.
        if r["events"] < 100:
            verdict = "**too few events to say anything (%d)**" % r["events"]
        elif beats:
            verdict = "above its null - still not a result"
        else:
            verdict = "**at or below its null**"
        A("| **%s** | %d | **%s** | **%d** (%d events) | %s | %s | %s |"
          % (cat, n_idx, avail, r["n"], r["events"], fmt_money(r["per_c"]),
             "%+.1f%% vs %+.1f%%" % (100 * r["ret"], 100 * med), verdict))
    A("")
    A("**A category with a small screened count cannot say anything**, and the "
      "count is shown rather than the number being quoted alone.")
    A("")
    # ⚠ NOT `c`. This loop used `c` as the category name and silently rebound
    # the DATABASE CONNECTION to a string. It broke nothing for two runs
    # because nothing used the connection afterwards; the moment the invert
    # screen did, the run died with "'str' object has no attribute 'execute'"
    # after ten minutes of work and wrote no report. A one-letter name reused
    # for two things is a bug waiting for a later edit.
    big = [(cn, r) for cn, (r, _) in percat.items() if r["events"] >= 100]
    if big:
        # ⚠ "the only" printed once per row and claimed TWO different
        # categories were the only one. A sentence written for a single winner
        # must not be run in a loop.
        big.sort(key=lambda x: -x[1]["events"])
        if len(big) == 1:
            cn, r = big[0]
            A("**The only category with a real sample is %s: %d events, %s per "
              "contract.**" % (cn, r["events"], fmt_money(r["per_c"])))
        else:
            A("**%d categories clear the 100-event bar:** %s."
              % (len(big), "; ".join(
                  "**%s** %d events at %s per contract"
                  % (cn, r["events"], fmt_money(r["per_c"])) for cn, r in big)))
        A("")
        A("Those are the only lines on this page with a sample behind them, "
          "and they say the dull version does not work.")
    else:
        A("**No category reaches the 100-event bar `PREREGISTRATION.md` §4 "
          "sets.** Nothing here can be judged at all.")
    A("")
    A("Everything else is a few days of tape, reported so that nobody mistakes "
      "a %d-event number for a finding later."
      % max((r["events"] for cn, (r, _) in percat.items()
             if r["events"] < 100), default=0))
    A("")
    A("> ⚠ **ONE LIMITATION THE CRYPTO ROW EXPOSES, AND IT IS MINE NOT THE "
      "MARKET'S.** Crypto has **%d markets in the index and only %d that "
      "could be screened.** The entry rule takes the last two-sided quote at "
      "least 60 minutes before close - and a Kalshi crypto ladder is an HOURLY "
      "market, so 60 minutes before its close is at or before the moment it "
      "opens. **The fixed entry lead is simply wrong for fast families**, and "
      "the near-total absence of crypto here is an artefact of my parameter "
      "rather than a fact about crypto. Fixing it means an entry lead "
      "expressed as a FRACTION of each market's life, not a constant, and "
      "that is a change to make deliberately and re-run - not to tune until "
      "something looks good."
      % (idx_cat.get("Crypto", [0, 0])[0],
         percat.get("Crypto", ({"n": 0},))[0]["n"] if "Crypto" in percat else 0))
    A("")
    A("## 4. WHAT WAS NOT SCREENED, AND WHY — the honest half")
    A("")
    A("**%d of %d LIVE specs could not be run.** Every one still counts toward "
      "the screened total; what it does not do is produce a number nobody "
      "could defend." % (len(NOT_SCREENED), n_live))
    A("")
    A("| spec | why not |")
    A("|---|---|")
    for sid in sorted(NOT_SCREENED):
        A("| `%s` | %s |" % (sid, NOT_SCREENED[sid]))
    A("")
    A("**The pattern is one thing, and it is worth naming: almost every "
      "unscreenable spec needs data ABOUT THE WORLD rather than about the "
      "book** - goal times, club identities, fixture lists, speech calendars, "
      "line-up announcements. The recorder captures prices beautifully and "
      "captures none of that. **That is the single biggest constraint on this "
      "project and it was not visible until screening was attempted.**")
    A("")
    A("## 5. THE INVERT SCREEN — is a loser leaking fees, or picking the wrong side?")
    A("")
    A("His idea, and it is computable: *\"if we find a purely bad strategy that "
      "isn\'t just getting killed by the fees - pretty much what that\'s telling "
      "us is that this site is picking the wrong side. So we just pick the "
      "other side.\"*")
    A("")
    A("**Two losers look identical on a profit line and are completely "
      "different things.** One pays more in costs than its edge is worth. The "
      "other is actively wrong, and the other side of it is a real hypothesis. "
      "The cost bar is what separates them.")
    A("")
    A("⚠ **INVERTING IS NOT NEGATING**, and that is why this needs arithmetic "
      "rather than a minus sign. Buying the other side lifts the OTHER ask, so "
      "the inverted trade **pays the spread again and the fee again**. A "
      "strategy losing exactly its cost bar loses the same amount inverted.")
    A("")
    A("**The bar is computed at the prices each row actually trades at, never "
      "at 50 cents** - the fee at 97c is 0.20c against 2.00c at 50c, and a "
      "constant bar would call every cheap strategy anti-predictive.")
    A("")
    A("| category | net per contract | cost bar | gross (picking only) | inverted | invertible? |")
    A("|---|---:|---:|---:|---:|---|")
    n_invertible = 0
    for cat in sorted(percat):
        r = percat[cat][0]
        flag = "**YES**" if r["invertible"] else "no"
        if r["invertible"]:
            n_invertible += 1
        if r["events"] < 100:
            flag += " (too few events to act on: %d)" % r["events"]
        A("| %s | %s | %s | %s | %s | %s |"
          % (cat, fmt_money(r["per_c"]), fmt_money(r["per_bar_c"]),
             fmt_money(r["per_gross_c"]), fmt_money(r["per_inv_c"]), flag))
    A("")
    A("**Whole run:** net %s, cost bar %s, gross %s, inverted %s - **%s**."
      % (fmt_money(real["per_c"]), fmt_money(real["per_bar_c"]),
         fmt_money(real["per_gross_c"]), fmt_money(real["per_inv_c"]),
         "INVERTIBLE" if real["invertible"] else "not invertible: it loses "
         "about what it costs to trade, which is the fee-leaking case and "
         "there is nothing underneath to flip"))
    A("")
    A("### ⚠ The trap, and it is the same size as the one that governs everything here")
    A("")
    A("**Selecting the worst of N and inverting it is the best-of-N problem in "
      "a mirror. It is not a weaker version - it is the same size.** Measured "
      "on 16 baseball bots: a bot landing in the worst 2-in-100 tail happens to "
      "at least one of 16 with no skill anywhere **28 times in 100**.")
    A("")
    A("So: **%d categories were screened to produce %d invertible one(s)**, and "
      "an inverted strategy is a **NEW** strategy - it gets its own id, its own "
      "pre-registration and its own forward test before anything is believed "
      "about it. Nothing on this table is promotable."
      % (len(percat), n_invertible))
    A("")
    A("### The placebo for this screen specifically")
    A("")
    A("**Inverting a strategy that is merely fee-losing must NOT look good**, "
      "or the screen is finding noise. The null arm above is exactly that "
      "strategy: outcomes drawn from the price paid, so it loses its cost bar "
      "and nothing more, by construction.")
    ps = [screen_hold(c, None, 5, 95, 8, "p", placebo_seed=3000 + i,
                      null_at="ask") for i in range(12)]
    ps = [x for x in ps if x]
    if ps:
        inv = sorted(x["per_inv_c"] for x in ps)
        A("")
        A("| | inverted, per contract |")
        A("|---|---:|")
        A("| **the real arm** | **%s** |" % fmt_money(real["per_inv_c"]))
        A("| a merely fee-losing arm, median of %d | %s |"
          % (len(ps), fmt_money(inv[len(inv) // 2])))
        A("| its range | %s to %s |"
          % (fmt_money(inv[0]), fmt_money(inv[-1])))
        A("")
        if real["per_inv_c"] <= inv[len(inv) // 2]:
            A("**The real arm inverted does no better than a fee-losing arm "
              "inverted. The screen finds nothing here, and says so.**")
        else:
            A("The real arm inverted beats the fee-losing arm inverted. **That "
              "is the minimum bar and not a result** - it says the screen can "
              "tell the two cases apart, which is a statement about the screen.")
    A("")
    A("## 6. THE TWO STANDARD LENSES — fee curvature, and closing-line value")
    A("")
    A("### Fee curvature: the same edge is worth far more at extreme prices")
    A("")
    A("Kalshi's fee is `0.07 x contracts x p x (1-p)` — **maximised at 50 cents "
      "and collapsing at the extremes.** A 2-cent edge at 95c survives as "
      "**+1.67c**; the same 2-cent edge at 50c survives as **+0.25c**, nearly "
      "seven times less. **The price a strategy trades at is part of its value, "
      "not a detail**, and nothing in this engine knew that until now.")
    A("")
    A("**Every row carries its event count**, because a per-contract edge is "
      "the number that gets quoted alone and one of these rows sits on a "
      "single event.")
    A("")
    A("| category | events | avg price traded | fee at that price | gross edge | **edge after fee** |")
    A("|---|---:|---:|---:|---:|---:|")
    for cat in sorted(percat):
        r = percat[cat][0]
        cell = "**%s**" % fmt_money(r["edge_after_fee_c"])
        if r["events"] < 100:
            cell = "%s *(only %d events - not readable)*" % (
                fmt_money(r["edge_after_fee_c"]), r["events"])
        A("| %s | %d | %.0fc | %.2fc | %s | %s |"
          % (cat, r["events"], r["avg_px_c"], r["fee_at_px_c"],
             fmt_money(r["per_gross_c"]), cell))
    A("")
    A("### Closing-line value — a signal that needs no outcomes")
    A("")
    A("Did the entry buy cheaper than the market ended up pricing it? **It "
      "needs no settlement data at all**, so it gives a reading long before "
      "enough markets settle to measure profit.")
    A("")
    A("| category | events | markets with a close | closing-line value per contract |")
    A("|---|---:|---:|---:|")
    for cat in sorted(percat):
        r = percat[cat][0]
        cell = fmt_money(r["clv_c"])
        if r["events"] < 100:
            cell += " *(only %d events)*" % r["events"]
        A("| %s | %d | %d | %s |" % (cat, r["events"], r["n_clv"], cell))
    A("")
    A("**Negative closing-line value means we bought dearer than the market "
      "settled into** — which is what paying the ask does, and is the expected "
      "sign for a rule that crosses the spread on every entry. It is reported "
      "as a lens, not as a result.")
    A("")
    A("## 7. CAPACITY — what it would actually cost to fill")
    A("")
    A("Walked on the recorded ladder rather than assumed from the touch. A "
      "market with no recorded ladder gets **no capacity claim at all**.")
    A("")
    A("**Read the columns carefully: they are the money that ACTUALLY GOES IN, "
      "not whether the target was met.** Asking for $500 and getting $38 shows "
      "as $38, which is the whole point of walking the book.")
    A("")
    A("| category | markets with a ladder | asking $50, got | asking $200, got | asking $500, got |")
    A("|---|---:|---|---|---|")
    for cat, d in sorted(caps):
        if d[500][0] == 0:
            A("| %s | **0** | - | - | - |" % cat)
            continue
        A("| %s | %d | $%.0f | $%.0f | **$%.0f** |"
          % (cat, d[500][0], d[50][1], d[200][1], d[500][1]))
    A("")
    A("**Where the count is 0 the family has no full-depth ladder on tape** - it "
      "is recorded at top of book only, so the question cannot be answered and "
      "is not guessed at.")
    A("")
    # ⚠ COMPUTED, NOT TYPED. This sentence said "$38" for three runs after the
    # table beneath it had moved to $45. A hard-coded number in prose beside a
    # generated table is a retraction waiting to happen.
    worst = [(d[500][1], cat) for cat, d in caps
             if d[500][0] > 0 and d[500][1] < 200]
    if worst:
        amt, cat = min(worst)
        A("> ⚠ **The %s row is the one to look at, and it is bad news for "
          "size.** Those books absorb about **$%.0f** whether you ask for $50, "
          "$200 or $500 - the ladder simply runs out. **A strategy that only "
          "exists in the first $%.0f is a hobby**, which is the test "
          "`STRATEGY_FACTORY.md` stage 6 puts first, and it is answerable now "
          "rather than after a month of forward testing." % (cat, amt, amt))
    A("")
    A("## 8. What this run does NOT establish")
    A("")
    span = c.execute("select min(close_utc), max(close_utc) from ev").fetchone()
    days = "?"
    try:
        import datetime as _d
        f = "%Y-%m-%dT%H:%M:%SZ"
        days = "%.0f" % ((_d.datetime.strptime(span[1], f)
                          - _d.datetime.strptime(span[0], f)).days)
    except Exception:                                          # noqa: BLE001
        pass
    A("- **Nothing about whether any strategy works.** %s days of tape, and the "
      "forward test has not started." % days)
    A("- **Nothing about the specs that could not be run** - their absence "
      "here is a statement about our data, not about their merit.")
    A("- **Nothing that survives being quoted without its screened count.** "
      "%d specs were written to produce this page." % n_specs)
    A("- **The entry rule is one fixed choice** - the last two-sided quote at "
      "least 60 minutes before close. It was fixed before the run and NOT "
      "swept. Sweeping the entry time and reporting the best is the best-of-N "
      "trap applied to a parameter instead of a strategy.")
    A("")

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("wrote %s" % outp)


if __name__ == "__main__":
    main()
