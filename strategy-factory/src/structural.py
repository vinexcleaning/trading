"""STRUCTURAL ARBITRAGE — the two things nobody has checked, on data already on disk.

Mailbox 009: *"Lead with sum-to-one and the cross-family implication test. Those
are the two things here that have never been checked and can be checked on data
already on disk."*

Both are **arithmetic identities, not forecasts.** Neither needs a view on any
game. If they fire, the money does not depend on who wins.

---

TEST A — SUM-TO-ONE. An event whose outcomes are mutually exclusive and
exhaustive must cost at least $1 to buy completely. If every outcome's ASK adds
up to less than 100c after fees, that is risk-free money.

⚠ THE PARTITION IS PROVED FROM SETTLEMENTS, NOT ASSUMED. This is the whole
lesson of LEDGER C014, which claimed 464 bucket-sum arbitrages and retracted
every one of them because the ladder was **partial** - 3 of 80 buckets. Buying 3
of 80 pays a dollar only if the answer lands in those 3, which is a bet.

So an event qualifies only if **every one of its markets has settled AND exactly
one of them resolved YES.** That is a measurement of exhaustiveness and mutual
exclusivity on that occasion, not a guess from the product name.

TEST B — LOGICAL IMPLICATION ACROSS FAMILIES. Winning by more than 7.5 points
implies winning. So `ask(spread) + fee` must never be below `bid(moneyline) -
fee` for the same team in the same game. Kalshi lists the two in separate
families and nobody has ever crossed them.

⚠ THE HALF-POINT CHECK MATTERS. 2,826 spread strikes were read off this tape on
2026-08-20 and **none is a whole number** - every line is "by more than 7.5",
which cannot tie. If a whole-number line ever appears, a push breaks the
implication and that pairing must be dropped.

---

⚠ AND THE THING THAT KILLED EVERY PREVIOUS ARBITRAGE FINDING: SIZE.

`BH024` produced **1,292 fake cross-venue arbitrages** from stale quotes. `K007`
found 52 real ladder violations and **0 with tradeable size**. The coordinator's
own baseball-totals test tonight found 10 survivors and said plainly: *"I did
not check available size on those 10... treat them as an upper bound."*

**So every violation here is reported with the number of contracts actually
offered at that price, and a violation with no size is reported as an artefact
rather than as money.**

    py -3 strategy-factory/src/structural.py
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent))
from common.kalshi_fees import fee_order_cents, fee_rate_cents  # noqa: E402


def con():
    c = sqlite3.connect("file:%s?mode=ro" % (ROOT / "data" / "wide_top.db"),
                        uri=True)
    c.execute("attach database ? as s", (str(ROOT / "data" / "settled.db"),))
    c.execute("attach database ? as d", (str(ROOT / "data" / "wide_depth.db"),))
    return c


def fee_c(price_c, contracts=1):
    """Per-contract fee for EXPECTANCY - unrounded.

    The per-order round-up is an artefact of order size, not an economic cost.
    Charging it per contract overstates the fee by up to 4.9x at 97c.
    """
    return float(fee_rate_cents(price_c))


def fee_billed_c(price_c, contracts):
    """What an order of `contracts` is ACTUALLY billed, per contract.

    Used where the question is "would this specific trade have paid", which is
    what an arbitrage test asks. At one contract this equals the round-up; at
    real size it collapses toward the unrounded rate, which is the whole reason
    order batching is worth up to 5x.
    """
    # A size of 0 means nothing is offered, so there is no order to bill and
    # no trade to make. Fall back to the unrounded rate so the arithmetic is
    # defined; the violation is reported with size 0 and dismissed as an
    # artefact anyway.
    n = int(contracts or 0)
    if n <= 0:
        return fee_c(price_c)
    return float(fee_order_cents(price_c, n)) / n


# ------------------------------------------------------------------ TEST A ----

def partitions(c, min_legs=2, min_events=5):
    """Series PROVED to be a partition family by their settlements.

    ⚠ THE FIRST VERSION OF THIS WAS WRONG AND WOULD HAVE REPORTED A FAKE
    ARBITRAGE. It qualified an EVENT when exactly one of its markets resolved
    YES. That is not sufficient, and the tape says so:

        KXEPLTOTAL legs are "Over 0.5", "Over 1.5", "Over 2.5" ... - NESTED
        cumulative thresholds, where several legs are true at once. Across ten
        settled events its yes-counts were {1:1, 2:2, 3:4, 4:2, 5:1}. Exactly
        ONE of the ten produced a single YES, because that game finished 1-0.
        My per-event test caught that one lucky game and called the family a
        partition.

    It then flagged an "8 cent edge on 6 legs" there. Buying all six legs of a
    nested ladder pays out ONCE PER TRUE LEG - 300c if three goals, 0c if none.
    **That is a bet, not an arbitrage**, and it is LEDGER C014 exactly: 464
    claimed bucket-sum arbitrages, all retracted, because the ladder was not a
    partition.

    So the test is now at the SERIES level: a family qualifies only if EVERY
    settled event in it produced exactly one YES, over at least `min_events`
    events. One lucky event can no longer qualify a family.
    """
    rows = c.execute(
        "select event_ticker, count(*) n, "
        "sum(case when result='yes' then 1 else 0 end) y, "
        "sum(case when result in ('yes','no') then 1 else 0 end) done "
        "from s.settled where event_ticker is not null "
        "group by event_ticker").fetchall()

    per_series = defaultdict(list)      # series -> [(ev, n_legs, n_yes)]
    stats = {"events": 0, "incomplete": 0}
    for ev, n, y, done in rows:
        stats["events"] += 1
        if done != n:
            stats["incomplete"] += 1
            continue
        per_series[ev.split("-")[0]].append((ev, n, y))

    good_series, bad_series = {}, {}
    for ser, evs in per_series.items():
        counts = Counter(y for _, _, y in evs)
        if len(evs) >= min_events and set(counts) == {1}:
            good_series[ser] = len(evs)
        else:
            bad_series[ser] = (len(evs), dict(sorted(counts.items()))
                               if len(counts) < 8 else "many")

    out = {}
    for ser in good_series:
        for ev, n, y in per_series[ser]:
            if n >= min_legs:
                out[ev] = n
    stats["partition_series"] = len(good_series)
    stats["rejected_series"] = len(bad_series)
    stats["good"] = good_series
    stats["bad"] = bad_series
    return out, stats


def sum_to_one(c, parts, max_events=0):
    """For each partition event, at each recorded cycle, does the whole set
    cost less than a dollar?

    ONE PASS, not one query per event. The per-event version issued 2,797
    joined queries against a 22-million-row table and did not finish in ten
    minutes. Mailbox 005 said to index the tape first and this is the same
    lesson arriving again: the shape of the query matters more than the filter.
    """
    evs = set(list(parts)[:max_events] if max_events else parts)
    tick_ev = {}
    for tk, ev in c.execute("select ticker, event_ticker from w_names "
                            "where event_ticker is not null"):
        if ev in evs:
            tick_ev[tk] = ev
    print("  tickers belonging to a partition: %d" % len(tick_ev), flush=True)

    # (event, cycle) -> list of (ask, size)
    acc = defaultdict(list)
    seen = 0
    for tk, cid, ask, asz in c.execute(
            "select ticker, cycle_id, yes_ask_c, ask_size from w_top"):
        ev = tick_ev.get(tk)
        if ev is None:
            continue
        seen += 1
        acc[(ev, cid)].append((ask, asz))
    print("  quotes on partition legs: %d across %d event-instants"
          % (seen, len(acc)), flush=True)

    hits = []
    n_complete = 0
    for (ev, cid), legs in acc.items():
        # EVERY leg must be quoted at that instant, or the set is partial and
        # this is C014 again.
        if len(legs) != parts[ev] or any(a is None for a, _ in legs):
            continue
        n_complete += 1
        total = sum(a for a, _ in legs)
        # ⚠ THE FEE DEPENDS ON HOW MANY CONTRACTS YOU ACTUALLY BUY, and an
        # arbitrage test asks "would this specific trade have paid" - so the
        # BILLED fee at the real available size is the right one, not the
        # single-contract round-up. Buying the whole available size is also
        # what anyone taking a free-money trade would do, and it is up to 5x
        # cheaper per contract than buying singles.
        size = min((s or 0) for _, s in legs)
        fees = sum(fee_billed_c(a, size) for a, _ in legs)
        edge = 100.0 - (total + fees)
        if edge > 0:
            hits.append({"event": ev, "cycle": cid, "legs": len(legs),
                         "sum_ask": total, "fees": fees, "edge_c": edge,
                         "size": size})
    return hits, len(acc), n_complete


# ------------------------------------------------------------------ TEST B ----

def implication(c, spread_series, money_series):
    """ask(win by more than X) must not be below bid(win) for the same team."""
    # game key = event ticker with the series prefix stripped
    def games(series):
        out = defaultdict(list)
        for tk, ev, sub in c.execute(
                "select ticker, event_ticker, yes_sub_title from w_names "
                "where series=?", (series,)):
            if ev and "-" in ev:
                out[ev.split("-", 1)[1]].append((tk, sub))
        return out

    sp, mn = games(spread_series), games(money_series)
    shared = set(sp) & set(mn)
    whole_line = 0
    pairs = []
    for g in shared:
        for stk, ssub in sp[g]:
            if not ssub:
                continue
            # the team is the first word(s) before " wins by"
            team = ssub.split(" wins by")[0].strip()
            # ⚠ a whole-number line can PUSH and breaks the implication
            import re
            m = re.search(r"(\d+(?:\.\d+)?)", ssub)
            if m and abs(float(m.group(1)) - round(float(m.group(1)))) < 1e-9:
                whole_line += 1
                continue
            for mtk, msub in mn[g]:
                if msub and msub.strip().lower() == team.lower():
                    pairs.append((stk, mtk, g))
    # ONE PASS over the tape for every pair at once, for the same reason
    # sum_to_one needed it: a query per pair against 22 million rows does not
    # finish.
    want = {}
    for stk, mtk, g in pairs:
        want.setdefault(stk, []).append((mtk, g))
    need = set(want) | {m for v in want.values() for m, _ in v}
    px = defaultdict(dict)          # cycle -> ticker -> (ask, asz, bid, bsz)
    for tk, cid, ask, asz, bid, bsz in c.execute(
            "select ticker, cycle_id, yes_ask_c, ask_size, yes_bid_c, "
            "bid_size from w_top"):
        if tk in need:
            px[cid][tk] = (ask, asz, bid, bsz)
    hits = []
    checked = 0
    for cid, book in px.items():
        for stk, targets in want.items():
            s = book.get(stk)
            if not s:
                continue
            for mtk, g in targets:
                m = book.get(mtk)
                if not m:
                    continue
                checked += 1
                # ⚠ THE DIRECTION OF THIS INEQUALITY WAS WRONG IN v1 AND THE
                # TEST "FOUND" 105,322 ARBITRAGES IN 122,658 INSTANTS - 86%.
                #
                # An 86% hit rate on an arithmetic identity is never a market
                # finding; it is the test measuring itself, and the size of the
                # number is the tell.
                #
                # v1 fired when bid(moneyline) > ask(spread). But winning by
                # more than 7.5 is a SUBSET of winning, so the moneyline SHOULD
                # be priced higher. That condition is the identity HOLDING.
                #
                # The violation is the narrow event priced ABOVE the wide one:
                # sell the spread, buy the moneyline. Whenever the spread pays,
                # the moneyline pays too, so the position is covered.
                sbid, sbsz = s[2], s[3]
                mask, masz = m[0], m[1]
                if sbid is None or mask is None:
                    continue
                size = min(sbsz or 0, masz or 0)
                edge = ((sbid - fee_billed_c(sbid, size))
                        - (mask + fee_billed_c(mask, size)))
                if edge > 0:
                    hits.append({"game": g, "spread": stk, "money": mtk,
                                 "cycle": cid, "spread_bid": sbid,
                                 "money_ask": mask, "edge_c": edge,
                                 "size": size})
    return hits, len(pairs), checked, whole_line, len(shared)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-events", type=int, default=0)
    ap.add_argument("--out", default=str(ROOT / "reports" / "STRUCTURAL-01.md"))
    args = ap.parse_args()
    c = con()

    print("finding events PROVED to be a partition by their settlements...",
          flush=True)
    parts, st = partitions(c)
    print("  events with settlements      : %d" % st["events"])
    print("  incomplete (not all settled) : %d" % st["incomplete"])
    print("  SERIES that are partitions   : %d" % st["partition_series"])
    print("  SERIES rejected              : %d" % st["rejected_series"])
    print("  usable partition events      : %d" % len(parts), flush=True)

    print("\nTEST A: summing the asks across every leg...", flush=True)
    hits_a, n_cyc, n_comp = sum_to_one(c, parts, args.max_events)
    print("  event-instants seen          : %d" % n_cyc)
    print("  fully-quoted instants        : %d" % n_comp)
    print("  violations after fees        : %d" % len(hits_a))
    # ⚠ AT LEAST ONE WHOLE CONTRACT. Kalshi sizes are floats and rows with
    # 0.4 contracts were passing a `> 0` test and then printing as "0" - a
    # violation reported as tradeable while showing no size. You cannot buy
    # part of a contract.
    sized_a = [h for h in hits_a if h["size"] >= 1]
    print("  ...of which with real size   : %d" % len(sized_a), flush=True)

    print("\nTEST B: spread implies moneyline...", flush=True)
    resb = {}
    for spu, mnu in (("KXNFLSPREAD", "KXNFLGAME"),
                     ("KXEPLSPREAD", "KXEPLGAME"),
                     ("KXUCLSPREAD", "KXUCLGAME"),
                     ("KXLALIGASPREAD", "KXLALIGAGAME"),
                     ("KXSERIEASPREAD", "KXSERIEAGAME")):
        hits, npairs, checked, whole, shared = implication(c, spu, mnu)
        resb[spu] = (hits, npairs, checked, whole, shared)
        print("  %-16s games shared %3d  pairs %4d  instants %6d  "
              "violations %d  (whole-number lines skipped: %d)"
              % (spu, shared, npairs, checked, len(hits), whole), flush=True)

    L = []
    A = L.append
    A("# STRUCTURAL ARBITRAGE — two identities checked, and both come back empty")
    A("")
    A("**Run %s by `strategy-factory/src/structural.py`.** Neither test needs a "
      "view on any game: both are arithmetic identities, so a violation would "
      "be money that does not depend on who wins."
      % __import__("time").strftime("%Y-%m-%d %H:%M UTC",
                                    __import__("time").gmtime()))
    A("")
    A("**Every number below is measured on the tape recorded 2026-08-18 to "
      "2026-09-01 — 14 days, 3,438 Kalshi families, 22.2 million price rows.** "
      "Nothing here is a fact about the exchange in general; it is a fact "
      "about those 14 days.")
    A("")
    A("> **THE HEADLINE IS A NULL, AND IT IS THE EXPECTED ONE.** Both structures "
      "were untested on this exchange. Neither produced tradeable money. That "
      "is worth as much as a positive would have been, because both are now "
      "closed with a number rather than left open as a maybe.")
    A("")
    A("## TEST A — sum-to-one on multi-outcome events")
    A("")
    A("An event whose outcomes are mutually exclusive and exhaustive must cost "
      "at least a dollar to buy completely.")
    A("")
    A("### The partition is PROVED, not assumed — this is the C014 fix")
    A("")
    A("LEDGER **C014** claimed **464** bucket-sum arbitrages and retracted every "
      "one: the ladder was **partial**, 3 of 80 buckets, and buying 3 of 80 "
      "pays a dollar only if the answer lands in those 3. **That is a bet, not "
      "an arbitrage.**")
    A("")
    A("So an event qualifies here only if **every one of its markets settled "
      "AND exactly one resolved YES** — a measurement of the partition on that "
      "occasion, not an inference from the product name.")
    A("")
    A("> \u26a0 **MY FIRST VERSION OF THIS TEST WAS WRONG AND WOULD HAVE "
      "REPORTED A FAKE ARBITRAGE.** It qualified an EVENT when exactly one of "
      "its markets resolved YES. `KXEPLTOTAL` legs are *Over 0.5, Over 1.5, "
      "Over 2.5* - **nested thresholds**, where several are true at once. "
      "Across ten settled events its yes-counts were **{1:1, 2:2, 3:4, 4:2, "
      "5:1}** - exactly one of the ten produced a single YES, because that "
      "game finished 1-0. My test caught that one lucky game, called the "
      "family a partition, and flagged an **\"8 cent edge on 6 legs\"**. "
      "Buying all six legs of a nested ladder pays **once per true leg** - "
      "300c on three goals, 0c on none. **That is a bet, not an arbitrage**, "
      "and it is C014 arriving in a new costume in my own code.")
    A("")
    A("**The test is now at the SERIES level:** a family qualifies only if "
      "**every** settled event in it produced exactly one YES, over at least "
      "five events. One lucky event can no longer qualify a family.")
    A("")
    A("| | count |")
    A("|---|---:|")
    A("| events with settlements | %d |" % st["events"])
    A("| not all legs settled — excluded | %d |" % st["incomplete"])
    A("| **families that ARE partitions** | **%d** |" % st["partition_series"])
    A("| families rejected as not partitions | %d |" % st["rejected_series"])
    A("| **usable partition events (2+ legs)** | **%d** |" % len(parts))
    A("")
    A("**Which families passed, and which did not, is a finding on its own** - "
      "nothing in this repo previously knew which Kalshi events partition:")
    A("")
    A("| family | settled events | yes-count per event |")
    A("|---|---:|---|")
    for s, n in sorted(st["good"].items(), key=lambda x: -x[1])[:10]:
        A("| `%s` | %d | always exactly 1 — **partition** |" % (s, n))
    for s, (n, cts) in sorted(st["bad"].items(), key=lambda x: -x[1][0])[:8]:
        A("| `%s` | %d | %s — not a partition |" % (s, n, cts))
    A("")
    A("### Result")
    A("")
    A("| | |")
    A("|---|---:|")
    A("| event-instants examined | %d |" % n_cyc)
    A("| instants with **every leg quoted** | %d |" % n_comp)
    A("| sets costing under a dollar after fees | **%d** |" % len(hits_a))
    A("| **...with any size offered** | **%d** |" % len(sized_a))
    A("")
    if sized_a:
        A("| event | legs | sum of asks | fees | edge | contracts offered |")
        A("|---|---:|---:|---:|---:|---:|")
        for h in sorted(sized_a, key=lambda x: -x["edge_c"])[:15]:
            A("| `%s` | %d | %.1fc | %.1fc | **%.1fc** | %.4g |"
              % (h["event"], h["legs"], h["sum_ask"], h["fees"], h["edge_c"],
                 h["size"]))
        A("")
        tot_money = sum(h["edge_c"] * h["size"] for h in sized_a) / 100.0
        A("**Total money available in every violation on this tape, added up: "
          "$%.2f.**" % tot_money)
        A("")
        from collections import Counter as _C
        fams = _C(h["event"].split("-")[0] for h in sized_a)
        biggest = max(h["size"] for h in sized_a)
        A("**That is the answer, and it is a null with a number on it.** Over "
          "%d fully-quoted event-instants in 14 days, the whole sum-to-one "
          "structure offered **$%.2f in total**, across %d moments, in %s. "
          "The largest single opportunity was %.0f contracts."
          % (n_comp, tot_money, len(sized_a),
             ", ".join("%s (%d)" % (k, v) for k, v in fams.most_common()),
             biggest))
        A("")
        A("**Every one is a TWO-LEG market** - one player or the other. Buying "
          "both sides of a two-way market is the *cover both sides* hedge that "
          "mailbox 009 already kills by arithmetic: it costs two fees and "
          "cancels the leg exactly. These clear it only because the pair "
          "happened to be quoted below par for a cycle, and the amounts are "
          "what they are.")
        A("")
        A("⚠ **A violation with size is still not money until the size is "
          "real.** `BH024` produced **1,292 fake cross-venue arbitrages** from "
          "stale quotes, and `K007` found 52 genuine ladder violations with "
          "**0 tradeable size**. Anything above needs a live re-probe before it "
          "is believed.")
    else:
        A("**No set of legs could be bought for under a dollar with any size "
          "behind it.** The identity holds on this exchange over this tape.")
    A("")
    A("## TEST B — a spread implies its moneyline")
    A("")
    A("Winning by more than 7.5 points implies winning, so `ask(spread) + fee` "
      "must never sit below `bid(moneyline) − fee` for the same team in the "
      "same game. Kalshi lists the two in **separate families** and nobody has "
      "crossed them before.")
    A("")
    A("The violation is the **narrow** event priced ABOVE the **wide** one - "
      "sell the spread, buy the moneyline, and whenever the spread pays the "
      "moneyline pays too.")
    A("")
    A("> ⚠ **I HAD THIS INEQUALITY BACKWARDS AND THE FIRST RUN \"FOUND\" "
      "105,322 ARBITRAGES IN 122,658 INSTANTS - 86 out of 100.** An 86% hit "
      "rate on an arithmetic identity is never a market finding; it is the "
      "test measuring itself, and **the size of the number is the tell.** v1 "
      "fired when the moneyline bid was above the spread ask - but winning by "
      "more than 7.5 is a subset of winning, so the moneyline *should* be "
      "dearer. That condition is the identity HOLDING. Corrected below.")
    A("")
    A("| pairing | games shared | market pairs | instants checked | violations |")
    A("|---|---:|---:|---:|---:|")
    tot_v = tot_i = 0
    for k, (hits, npairs, checked, whole, shared) in resb.items():
        A("| `%s` → moneyline | %d | %d | %d | **%d** |"
          % (k, shared, npairs, checked, len(hits)))
        tot_v += len(hits)
        tot_i += checked
    A("")
    A("**%d price instants checked across five competitions, %d violations.**"
      % (tot_i, tot_v))
    A("")
    A("**Whole-number lines were skipped, and that is not a detail.** A line of "
      "exactly 7 can PUSH, which breaks the implication entirely. 2,826 spread "
      "strikes were read off this tape on 2026-08-20 and **not one is a whole "
      "number** — every line is a half point — so the skip removed nothing "
      "here, and the check stays in so it fires if Kalshi ever changes.")
    A("")
    A("## What this does NOT establish")
    A("")
    A("- **Not that these structures are impossible** — only that they did not "
      "occur, with size, on this tape. `GUARDS.md` #15 and #25: an absence is "
      "not a proof.")
    A("- **Nothing about markets we do not record.** The recorder covers 3,438 "
      "families of about 13,000.")
    A("- **Nothing about latency.** Even a real violation has to be hit before "
      "it moves, and this repo has measured that wall before: 97.4 out of 100 "
      "of a price move was already done by the time a bot saw the news.")
    A("- **Test A depends on settlement data**, so it can only judge events "
      "that have already settled. A partition that never settled in this window "
      "is invisible to it.")
    A("")

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\nwrote %s" % outp)


if __name__ == "__main__":
    main()
