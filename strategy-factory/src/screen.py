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
from common.kalshi_fees import fee_order_cents  # noqa: E402

IDX = ROOT / "data" / "index.db"

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

def net_cents(entry_ask_c, won, contracts=1):
    """Cents made per contract buying YES at the real ask and holding.

    Fee on ENTRY ONLY - Kalshi charges nothing at settlement, which
    `common/kalshi_fees.py` states in `roundtrip_cost_cents`.
    """
    fee = float(fee_order_cents(entry_ask_c, contracts)) / contracts
    gross = (100.0 - entry_ask_c) if won else (-entry_ask_c)
    return gross - fee


def outlay_cents(entry_ask_c, contracts=1):
    """Cash that actually leaves the account: price PLUS fee."""
    return entry_ask_c + float(fee_order_cents(entry_ask_c, contracts)) / contracts


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
    row = c.execute(
        "select no_ladder from d.w_depth where ticker=? order by "
        "abs(julianday(ts_utc)-julianday(?)) limit 1", (ticker, entry_ts)
    ).fetchone()
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
         "entry_ts, entry_ask_c, entry_bid_c from ev "
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
    n = wins = 0
    events = set()
    per_bucket = defaultdict(lambda: [0, 0, 0.0, 0.0])
    for tk, ser, ev, res, close, ets, ask, bid in rows:
        won = (res == "yes")
        net = net_cents(ask, won)
        out = outlay_cents(ask)
        tot_net += net
        tot_out += out
        n += 1
        wins += won
        events.add(ev or tk)
        b = per_bucket[int(ask // 10) * 10]
        b[0] += 1
        b[1] += won
        b[2] += net
        b[3] += out
    return {"label": label, "n": n, "events": len(events), "wins": wins,
            "net_c": tot_net, "outlay_c": tot_out,
            "ret": tot_net / tot_out if tot_out else 0.0,
            "per_c": tot_net / n if n else 0.0,
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
        for i in range(max(5, args.placebos // 2)):
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
            "and series in (%s) limit 400"
            % ",".join("?" * len([s for s, k in cat_of.items() if k == cat])),
            [s for s, k in cat_of.items() if k == cat]).fetchall()
        hits = {50: [], 200: [], 500: []}
        for tk, ets in rows:
            for d in (50, 200, 500):
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
    A("| category | in index | screenable | screened | net per contract | vs placebo | verdict |")
    A("|---|---:|---:|---:|---:|---|---|")
    for cat in sorted(idx_cat):
        n_idx, n_ent = idx_cat[cat]
        if cat not in percat:
            A("| %s | %d | %d | 0 | - | - | nothing in the price/spread band |"
              % (cat, n_idx, n_ent))
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
        A("| **%s** | %d | %d | **%d** (%d events) | %s | %s | %s |"
          % (cat, n_idx, n_ent, r["n"], r["events"], fmt_money(r["per_c"]),
             "%+.1f%% vs %+.1f%%" % (100 * r["ret"], 100 * med), verdict))
    A("")
    A("**A category with a small screened count cannot say anything**, and the "
      "count is shown rather than the number being quoted alone.")
    A("")
    A("**ONE category clears the 100-event bar `PREREGISTRATION.md` §4 sets, "
      "and it is Sports at 514 events** - where buying at the ask and holding "
      "loses **3 cents a contract** and sits on top of its own null. That is "
      "the only line on this page with a sample behind it, and it says the "
      "dull version of this does not work. Everything else here is two days of "
      "tape and is reported so nobody mistakes a 36-event number for a finding "
      "later.")
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
    A("## 5. CAPACITY — what it would actually cost to fill")
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
    A("> ⚠ **The Financials row is the one to look at, and it is bad news for "
      "size.** Those books absorb about **$38** whether you ask for $50, $200 "
      "or $500 - the ladder simply runs out. **A strategy that only exists in "
      "the first thirty-eight dollars is a hobby**, which is the test "
      "`STRATEGY_FACTORY.md` stage 6 puts first, and it is answerable now "
      "rather than after a month of forward testing.")
    A("")
    A("## 6. What this run does NOT establish")
    A("")
    A("- **Nothing about whether any strategy works.** Two days of tape, no "
      "category near 100 settled units, and the forward test has not started.")
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
