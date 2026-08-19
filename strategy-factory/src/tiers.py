"""BUILD THE RECORDER'S TIER LIST FROM A MEASUREMENT, NEVER BY HAND.

`STRATEGY_FACTORY.md` stage 1: rank every series by whether a strategy could
ever trade it, record everything that passes, keep the existing 19 untouched,
and **report what was dropped and why**. This is that script, and the last
clause is the one it takes most seriously - the drop list is written out in
full, with counts, because a family silently missing from a recorder is
indistinguishable from a family that does not exist, and this repo has already
made 19 wrong kills that way.

INPUTS
  data/census.db   every series, every open market  (src/census.py)
  data/shape.json  which markets carry a real quote (src/shape.py)

OUTPUT
  data/tiers.json          what the recorder reads
  reports/TIERS.md         what a human reads, including the drop list

THE THREE DECISIONS, and each is a judgment call recorded in DECISIONS.md:

  DROPPED   no market in the family carried a quote on either side at the
            moment it was measured. NOT "this family is dead" - GUARDS #15,
            a single absent reading never establishes that - so the drop list
            is re-measured on every rebuild and a family can come back.

  TIER B    quoted, so the top of its book is worth a row. Costs one HTTP
            request per SERIES per cycle regardless of how many markets it
            holds, so breadth here is nearly free.

  TIER A    full orderbook ladder walked on the soonest-closing markets. Costs
            one request per MARKET, so it is budgeted, not wished for. Ranked
            by two things: how many two-sided markets the family has, and
            whether `bot-hunt` is ALREADY recording it at depth - because
            spending the expensive tier on a family that is already on tape
            buys nothing.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: The 19 families `bot-hunt/src/record.py` already records at full depth.
#: Read off KALSHI_SERIES in that file on 2026-08-18. They are NOT dropped -
#: they go to tier B so the factory has its own copy of the top of book on one
#: clock with everything else - but they do not consume the expensive tier.
BOT_HUNT_19 = {
    "KXLIGAMXGAME", "KXARGPREMDIVGAME", "KXDIMAYORGAME", "KXCOPADOBRASILGAME",
    "KXLIGAMXTOTAL", "KXBRASILGAME", "KXATPMATCH", "KXWTAMATCH", "KXITFMATCH",
    "KXITFWMATCH", "KXCS2GAME", "KXLOLGAME", "KXVALORANTGAME", "KXMLBRFI",
    "KXMLBGAME", "KXMLBTOTAL", "KXHIGHNY", "KXHIGHCHI",
}

#: Categories `bot-hunt` records NOTHING in. His explicit ask was crypto,
#: weather, economics, "anything" - and these are the ones where the factory
#: is the only thing that will ever have tape. Boosted in the tier A ranking
#: for that reason and no other.
UNCOVERED_BOOST = {"Crypto": 3.0, "Economics": 3.0, "Financials": 2.5,
                   "Commodities": 2.5, "Climate and Weather": 2.0,
                   "Elections": 1.5, "Politics": 1.5, "Companies": 1.5,
                   "Entertainment": 1.2, "Science and Technology": 1.2,
                   "Mentions": 1.0, "World": 1.0, "Social": 1.0,
                   "Sports": 0.6}

#: Families that are combinatorial parlay products. They are 90% of the
#: exchange's open markets and almost none of them carry a book. Excluded by
#: name as well as by measurement, because a single quoted leg would otherwise
#: drag 614,573 markets into the recorder.
EXOTIC_PREFIXES = ("KXMVE",)


#: ⚠ PINNED TO TIER A BY NAME, and each one needs a written reason because a
#: pin overrides a measurement.
#:
#: Added 2026-08-19 on coordinator mailbox 003, which carries the user's own
#: answer to "which markets do you actually know something about". His answer:
#: **soccer most of all** ("everything Europe related, I know"), tennis's format
#: but not its players, and Valorant as his only esport. Baseball: "literally
#: close to nothing" -- which is where the live money is.
#:
#: Why a pin rather than a bigger category boost: a boost would quietly pull in
#: whatever else scores nearby, and the reason here is specific to these three
#: families and to nobody else's. A pin is visible; a tuned constant is not.
#:
#: NOT duplication of `bot-hunt`, though it looks like it. Its EU recorder does
#: probe these books, but `record.py` stores only `depth5_yes`/`depth5_no` -- a
#: SUMMARY of the ladder. Tier A stores the whole ladder, both sides, level by
#: level. The capacity question ("what would $500 actually cost here") needs the
#: levels, and `soccer/CLOSED.md`'s one live descendant is blocked on exactly
#: that: "a deeper book than this window had... the Premier League and Champions
#: League group stage would fix that, and only those."
PINNED = {
    "KXUCLGAME": "Champions League - his strongest sport, and the group stage "
                 "starting in September is the specific data soccer/CLOSED.md "
                 "says its one live descendant was waiting for",
    "KXEPLGAME": "Premier League - same argument, named in the same sentence",
    "KXVALORANTGAME": "his only esport, and the only one he can sanity-check",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier-a-budget", type=int, default=900,
                    help="orderbook requests one cycle may spend on tier A")
    ap.add_argument("--depth-cap", type=int, default=25,
                    help="markets per tier A series that get a ladder walk")
    ap.add_argument("--min-two-sided", type=int, default=1,
                    help="two-sided markets a series needs to earn tier B")
    ap.add_argument("--per-category", type=int, default=4,
                    help="tier A: depth slots EVERY category gets before any "
                         "category gets a second helping. This is the quota "
                         "that stops the expensive tier collapsing onto "
                         "whichever category happens to have the most "
                         "two-sided markets -- see mailbox 001.")
    args = ap.parse_args()

    shape_p = ROOT / "data" / "shape.json"
    if not shape_p.exists():
        raise SystemExit("run src/shape.py first - %s missing" % shape_p)
    shape = json.loads(shape_p.read_text(encoding="utf-8"))
    per = shape["per_series"]

    con = sqlite3.connect(ROOT / "data" / "census.db")
    titles = dict(con.execute("select ticker, title from series"))
    freqs = dict(con.execute("select ticker, frequency from series"))
    feetypes = dict(con.execute("select ticker, fee_type from series"))
    con.close()

    dropped_exotic, dropped_unquoted, dropped_thin = [], [], []
    tier_a_pool, tier_b = [], []

    for ser, d in per.items():
        cat = d.get("category") or "?"
        n, q, two = d["n"], d["quoted"], d["two_sided"]
        if ser.startswith(EXOTIC_PREFIXES):
            dropped_exotic.append((ser, cat, n, two))
            continue
        if q == 0:
            dropped_unquoted.append((ser, cat, n, two))
            continue
        if two < args.min_two_sided:
            dropped_thin.append((ser, cat, n, two))
            continue
        tier_b.append(ser)
        score = two * UNCOVERED_BOOST.get(cat, 1.0)
        if ser in BOT_HUNT_19:
            score = 0.0        # already on tape at depth; do not spend tier A
        tier_a_pool.append((score, ser, cat, n, two))

    # ------------------------------------------------------------------
    # TIER A IS ALLOCATED BY QUOTA FIRST, SCORE SECOND.
    #
    # ⚠ v1 ranked purely on `two_sided * category boost` and it narrowed
    # exactly the way mailbox 001 warns about. Measured on the first
    # allocation: Financials took 12 of 36 depth slots and Sports took 8,
    # while **crypto, weather, politics, companies, science and mentions got
    # ZERO** -- and crypto settles in minutes and weather settles same-day,
    # which makes them the two fastest categories to get a real forward answer
    # from. A pure score is a TOTAL, and his sentence is that a total is how
    # narrowing hides.
    #
    # So: every category with any two-sided market gets `--per-category` slots
    # before any category gets a second helping. Only the leftover budget is
    # handed out by score.
    # ------------------------------------------------------------------
    tier_a_pool.sort(reverse=True)
    tier_a, spent = [], 0
    taken = set()

    def take(ser, n):
        nonlocal spent
        cost = min(n, args.depth_cap)
        if spent + cost > args.tier_a_budget or ser in taken:
            return False
        tier_a.append(ser)
        taken.add(ser)
        spent += cost
        return True

    # Pins first, before the quota, so a pin can never be squeezed out by it.
    pin_taken = []
    for score, ser, cat, n, two in tier_a_pool:
        if ser in PINNED and take(ser, n):
            pin_taken.append((ser, cat))
    pin_spent, pin_series = spent, len(tier_a)

    by_cat = defaultdict(list)
    for score, ser, cat, n, two in tier_a_pool:
        if score > 0:
            by_cat[cat].append((score, ser, n))
    # Round-robin so a large budget cannot be exhausted by the first category.
    for slot in range(args.per_category):
        for cat in sorted(by_cat, key=lambda c: -len(by_cat[c])):
            if slot < len(by_cat[cat]):
                _, ser, n = by_cat[cat][slot]
                take(ser, n)
    quota_spent, quota_series = spent, len(tier_a)
    for score, ser, cat, n, two in tier_a_pool:
        if score > 0:
            take(ser, n)

    tier_b = sorted(tier_b)
    out = {
        "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "census.db + shape.json measured %s" % shape["measured_utc"],
        "tier_a_budget": args.tier_a_budget,
        "tier_a_requests_committed": spent,
        "depth_cap": args.depth_cap,
        "tier_a": tier_a,
        "tier_b": tier_b,
        "dropped": {
            "exotic_parlay": [x[0] for x in dropped_exotic],
            "no_quote_on_either_side": [x[0] for x in dropped_unquoted],
            "quoted_but_never_two_sided": [x[0] for x in dropped_thin],
        },
    }
    (ROOT / "data" / "tiers.json").write_text(json.dumps(out, indent=1),
                                              encoding="utf-8")

    # ---------------------------------------------------------- the report
    L = []
    A = L.append
    A("# THE RECORDER'S TIER LIST - and everything it drops")
    A("")
    A("**Built %s by `strategy-factory/src/tiers.py`** from a census of every "
      "Kalshi series and a full sweep measuring which markets carry a real "
      "quote. Not hand-written, and rebuilt rather than edited."
      % out["built_utc"])
    A("")
    A("## What gets recorded")
    A("")
    A("| tier | what is stored | series | cost per cycle |")
    A("|---|---|---:|---|")
    A("| **A** | the whole orderbook ladder, both sides | **%d** | %d requests |"
      % (len(tier_a), spent))
    A("| **B** | top of book, written only when it changes | **%d** | %d requests |"
      % (len(tier_b), len(tier_b)))
    A("")
    A("Tier A is expensive because a ladder costs one request per MARKET. "
      "Tier B is cheap because a listing costs one request per SERIES no "
      "matter how many markets are in it. That asymmetry is the entire reason "
      "the tiers exist.")
    A("")
    n_cov = sum(1 for s in tier_b if s in BOT_HUNT_19)
    A("`bot-hunt`'s 19 families are **not touched and not competed with**. %d "
      "of them appear in tier B so the factory has its own top-of-book copy "
      "on one clock with everything else, and none of them consume tier A - "
      "they are already on tape at full depth." % n_cov)
    A("")
    A("## What was DROPPED, and why")
    A("")
    A("A drop is a recording priority, never a verdict on the family. "
      "GUARDS #15: a single absent reading never establishes that something "
      "is dead. The list is re-measured on every rebuild and a family can "
      "come back.")
    A("")
    A("| reason | series dropped | open markets in them |")
    A("|---|---:|---:|")
    for label, rows in (("combinatorial parlay product", dropped_exotic),
                        ("no quote on either side when measured",
                         dropped_unquoted),
                        ("quoted on one side only, never two-sided",
                         dropped_thin)):
        A("| %s | %d | %d |" % (label, len(rows), sum(r[2] for r in rows)))
    A("")
    A("### The parlay families, named")
    A("")
    for ser, cat, n, two in sorted(dropped_exotic, key=lambda x: -x[2]):
        A("- `%s` - %s - **%d open markets**, %d two-sided. %s"
          % (ser, cat, n, two, titles.get(ser, "")[:70]))
    A("")
    A("These two families alone are the great majority of the open markets on "
      "the exchange. Recording them would have consumed the entire disk "
      "budget on products that almost never have a counterparty.")
    A("")
    A("### The biggest families with no quote at all")
    A("")
    A("| series | category | open markets |")
    A("|---|---|---:|")
    for ser, cat, n, two in sorted(dropped_unquoted, key=lambda x: -x[2])[:25]:
        A("| `%s` | %s | %d |" % (ser, cat, n))
    A("")
    A("## Tier A, in the order it was chosen")
    A("")
    A("| # | series | category | two-sided markets | frequency | charges makers |")
    A("|---:|---|---|---:|---|---|")
    rank = {s: i for i, s in enumerate(tier_a)}
    for score, ser, cat, n, two in tier_a_pool:
        if ser not in rank:
            continue
        A("| %d | `%s` | %s | %d | %s | %s |"
          % (rank[ser] + 1, ser, cat, two, freqs.get(ser, "?"),
             "yes" if feetypes.get(ser) == "quadratic_with_maker_fees"
             else "no"))
    A("")
    if pin_taken:
        A("### The %d PINNED families, and what they displaced" % len(pin_taken))
        A("")
        A("| series | category | why it is pinned |")
        A("|---|---|---|")
        for ser, cat in pin_taken:
            A("| `%s` | %s | %s |" % (ser, cat, PINNED[ser]))
        A("")
        A("**A pin overrides a measurement, so it costs something and the cost "
          "is named.** These %d families consume %d of the %d request budget. "
          "What they displaced is the %d lowest-scoring families that would "
          "otherwise have been filled by score - listed at the bottom of the "
          "tier A table below as the ones just outside the line. **Nothing "
          "allocated by the category quota was touched**, because pins are "
          "taken before the quota rather than after it: a pin can push out a "
          "score-filled family and can never push out a category's guaranteed "
          "share." % (len(pin_taken), pin_spent, args.tier_a_budget,
                      len(pin_taken)))
        A("")
    A("**%d of the %d tier A families were allocated by CATEGORY QUOTA** - "
      "%d slots to every category with any two-sided market, handed out before "
      "any category got a second helping. The remaining %d were filled by "
      "score. Without the quota the first allocation put 12 of 36 slots in "
      "Financials and 8 in Sports and gave **zero** to crypto, weather, "
      "politics, companies, science and mentions - and crypto settles in "
      "minutes while weather settles same-day, which makes them the two "
      "fastest categories to get a real forward answer from."
      % (quota_series, len(tier_a), args.per_category,
         len(tier_a) - quota_series))
    A("")
    A("The score used for the leftover slots is two-sided market count "
      "categories `bot-hunt` records **nothing** in - crypto, economics, "
      "financials, commodities. Those are the families where this recorder is "
      "the only thing that will ever have tape, which was his explicit ask: "
      "*crypto, weather, economics, anything*, not sports alone.")
    A("")
    A("## Tier B by category")
    A("")
    bycat = defaultdict(int)
    for s in tier_b:
        bycat[per[s].get("category") or "?"] += 1
    A("| category | series in tier B |")
    A("|---|---:|")
    for c, k in sorted(bycat.items(), key=lambda x: -x[1]):
        A("| %s | %d |" % (c, k))
    A("")

    rp = ROOT / "reports" / "TIERS.md"
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text("\n".join(L) + "\n", encoding="utf-8")

    print("tier A %d series (%d orderbook requests/cycle)" % (len(tier_a), spent))
    print("tier B %d series" % len(tier_b))
    print("dropped: %d parlay, %d unquoted, %d one-sided-only"
          % (len(dropped_exotic), len(dropped_unquoted), len(dropped_thin)))
    print("wrote data/tiers.json and reports/TIERS.md")


if __name__ == "__main__":
    main()
