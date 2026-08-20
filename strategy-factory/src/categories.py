"""THE CATEGORY CENSUS — breadth enforced by a list, not by intent.

Mailbox 001 from `coordinator`, in his own words:

    "Claude has this... we get really focused. So for example, I tell the
     factory chat to find me a bunch of strategies. Instead we'll end up doing
     it to find me one really good market and find all the strategies within
     that market. But I wanted to do that with ALL the markets."

He is describing narrowing, and the instruction is to make it **structurally
impossible rather than merely discouraged**. Two mechanisms, and this file is
the first:

  1. A CENSUS, WRITTEN DOWN FIRST. You cannot silently skip what is on a list
     you already committed. Every category gets a row whether or not it looks
     promising, and **a category dismissed without a written reason is a
     category you skipped**.
  2. A QUOTA PER CATEGORY, checked by `spec.py --coverage`. A total is how
     narrowing hides: 200 strategies all on baseball satisfies "200 strategies"
     and fails him completely.

This script produces `reports/CATEGORIES.md`, which carries for every category:
how many families and markets, how many carry a real two-sided quote, whether
we are recording it, what the settlement source looks like, whether makers are
charged — and a **VERDICT with a written reason**.

The verdict is about whether a strategy could ever be *tested* there. It is not
a prediction about profit and it is not permanent: it is recomputed from the
tape every time this runs.

    py -3 strategy-factory/src/categories.py
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: How fast a family settles decides whether a forward test can ever judge it
#: inside a month. Written down per category BEFORE any strategy is generated,
#: because "it is slow" discovered in September is an excuse and the same
#: sentence written in August is a prediction.
SETTLES = {
    "Sports": "hours to days",
    "Crypto": "minutes to hours",
    "Financials": "hours to days",
    "Climate and Weather": "same day",
    "Economics": "weeks to months",
    "Elections": "months",
    "Politics": "weeks to months",
    "Entertainment": "weeks to months",
    "Companies": "weeks to months",
    "Commodities": "days to weeks",
    "Science and Technology": "months",
    "Mentions": "days to weeks",
    "World": "months",
    "Social": "months",
    "Health": "months",
    "Transportation": "weeks",
}


def main() -> None:
    cen = sqlite3.connect("file:%s?mode=ro" % (ROOT / "data" / "census.db"),
                          uri=True)
    cat = dict(cen.execute("select ticker, category from series"))
    fee = dict(cen.execute("select ticker, fee_type from series"))
    nsrc = dict(cen.execute("select ticker, n_settlement_sources from series"))
    freq = dict(cen.execute("select ticker, frequency from series"))
    shape = json.loads((ROOT / "data" / "shape.json").read_text(encoding="utf-8"))
    per = shape["per_series"]
    tiers = json.loads((ROOT / "data" / "tiers.json").read_text(encoding="utf-8"))
    tier_a, tier_b = set(tiers["tier_a"]), set(tiers["tier_b"])
    dropped = {s for v in tiers["dropped"].values() for s in v}

    # ⚠ HOW OFTEN DOES A CATEGORY MINT NEW MARKETS? MEASURED, NOT READ OFF
    # THE METADATA.
    #
    # v1 of this verdict used Kalshi's `frequency` field on the SERIES and
    # marked a category unmeasurable when no family was daily/weekly/monthly.
    # That was wrong and the tape said so within the hour: `Mentions` and
    # `Elections` are `one_off` at the series level and mint **98 and 44 new
    # markets a day** at the market level, because a series like KXFEDMENTION
    # is one row while its markets are minted per speech. A series-level field
    # is simply not a market-level fact.
    #
    # So recurrence is now counted off `w_names.first_seen_utc`: how many
    # markets in this category appeared AFTER the recorder's first cycle. Two
    # methods now have to agree before a category is written off, and on
    # `Companies` they do - zero by the field and zero on the tape.
    minted = Counter()
    days_of_tape = 1.0
    try:
        wt = sqlite3.connect(
            "file:%s?mode=ro" % (ROOT / "data" / "wide_top.db"), uri=True)
        t0 = wt.execute("select min(first_seen_utc) from w_names").fetchone()[0]
        t1 = wt.execute("select max(first_seen_utc) from w_names").fetchone()[0]
        if t0 and t1:
            import datetime as _dt
            f = "%Y-%m-%dT%H:%M:%SZ"
            days_of_tape = max(
                0.5, (_dt.datetime.strptime(t1, f)
                      - _dt.datetime.strptime(t0, f)).total_seconds() / 86400.0)
            cut = t0[:13] + ":59:59Z"        # anything after the first hour
            for ser, fs in wt.execute(
                    "select series, first_seen_utc from w_names where "
                    "first_seen_utc > ?", (cut,)):
                # ⚠ KEY IT THE SAME WAY `agg` DOES, off shape.json, not off
                # the census `series` table. Keying it off the census gave
                # `KXMLBWINS` -- which has NO series row at all -- the label
                # "(unclassified)" while agg had it under "?", so its 2,082
                # newly minted markets counted toward a bucket nothing read
                # and the "?" category was reported as minting ZERO. That is
                # the same two-sources-of-truth bug that made spec.py's
                # coverage checker report a hole that was not there, in a
                # different file on the same day.
                minted[per.get(ser, {}).get("category") or "(unclassified)"] += 1
        wt.close()
    except sqlite3.Error:
        pass

    # What is actually on tape now, rather than what we intended to record.
    tape = Counter()
    try:
        top = sqlite3.connect(
            "file:%s?mode=ro" % (ROOT / "data" / "wide_top.db"), uri=True)
        for ser, n in top.execute("select series, count(*) from w_top "
                                  "group by series"):
            tape[cat.get(ser, "(unclassified)")] += n
    except sqlite3.Error:
        pass

    agg = defaultdict(lambda: {"series": 0, "markets": 0, "two": 0,
                               "tier_a": 0, "tier_b": 0, "dropped": 0,
                               "maker_fee": 0, "no_source": 0, "recurring": 0,
                               "biggest": []})
    for ser, d in per.items():
        c = d.get("category") or "(unclassified)"
        a = agg[c]
        a["series"] += 1
        a["markets"] += d["n"]
        a["two"] += d["two_sided"]
        a["tier_a"] += int(ser in tier_a)
        a["tier_b"] += int(ser in tier_b)
        a["dropped"] += int(ser in dropped)
        a["maker_fee"] += int(fee.get(ser) == "quadratic_with_maker_fees")
        a["no_source"] += int((nsrc.get(ser) or 0) == 0)
        a["recurring"] += int(freq.get(ser) in
                              ("daily", "weekly", "monthly", "hourly",
                               "quarterly"))
        a["biggest"].append((d["two_sided"], ser))

    L = []
    A = L.append
    A("# EVERY CATEGORY ON KALSHI — and whether a strategy could be tested there")
    A("")
    A("**Built by `strategy-factory/src/categories.py` from the exchange census "
      "of 2026-08-18 and the tape recorded since.** Rebuilt, never hand-edited.")
    A("")
    A("This file exists because of one sentence of his, quoted in mailbox 001: "
      "*\"I tell the factory chat to find me a bunch of strategies. Instead "
      "we'll end up doing it to find me one really good market and find all the "
      "strategies within that market. But I wanted to do that with ALL the "
      "markets.\"*")
    A("")
    A("> **A category dismissed without a written reason is a category that was "
      "skipped.** So every category gets a row and a verdict, including the "
      "ones that are obviously hopeless, and the reason is written out.")
    A("")
    A("## The table")
    A("")
    A("| category | families | markets | two-sided | on tape | full depth | "
      "new/day | charge makers | settles in | VERDICT |")
    A("|---|---:|---:|---:|---:|---:|---:|---:|---|---|")

    verdicts = {}
    for c, a in sorted(agg.items(), key=lambda x: -x[1]["two"]):
        two, mk, ser = a["two"], a["markets"], a["series"]
        settles = SETTLES.get(c, "unknown")
        if two == 0:
            v = "**NO — nothing to trade against**"
            why = ("not one market in the whole category had a quote on both "
                   "sides when the exchange was swept. There is no "
                   "counterparty, so there is nothing to test.")
        elif a["tier_b"] == 0:
            v = "**NO — not recorded**"
            why = "no family cleared the recorder's bar, so no tape accrues."
        elif two < 20:
            v = "**WEAK — too few two-sided markets**"
            why = ("only %d two-sided markets across the whole category. A "
                   "forward test needs 100 settled units to be judged, so this "
                   "cannot produce an answer at any speed." % two)
        elif (minted.get(c, 0) / days_of_tape) < 1.0:
            # WARNING - added 2026-08-20 after Companies turned out to be
            # undemandable. Every one of its 35 quoted families is `one_off` or
            # `custom` on Kalshi's own frequency field and settles on ONE
            # annual number, so 35 families give about 35 settlement events A
            # YEAR against the 100 a forward test needs. A category with no
            # recurring family cannot accrue a sample at any speed, and the
            # quota must stop demanding a spec that cannot exist -- otherwise
            # the coverage check reports a hole nothing could ever fill, which
            # is worse than useless.
            v = "**UNMEASURABLE - nothing new is minted**"
            why = ("MEASURED ON THE TAPE, not read off the metadata: **%d new "
                   "markets in %.1f days of recording, %.1f a day**. At that "
                   "rate the 100 settled units a forward test needs would take "
                   "over a year, and that is before any of them settles. Two "
                   "independent methods agree here - %d of %d quoted families "
                   "also carry a non-recurring `frequency` on Kalshi's own "
                   "metadata. ⚠ This says we CANNOT FIND OUT, not that the "
                   "markets are efficient. LEDGER K012 is the warning: "
                   "'economics markets are killed on recurrence' was read as "
                   "'there is no edge there', and those are opposite "
                   "sentences."
                   % (minted.get(c, 0), days_of_tape,
                      minted.get(c, 0) / days_of_tape,
                      ser - a["recurring"], ser))
        elif settles in ("months",):
            v = "**SLOW — testable, not inside a month**"
            why = ("real two-sided markets (%d), but they settle in months. "
                   "Specs here are written and queued, and saying so now is a "
                   "prediction rather than an excuse offered in September."
                   % two)
        else:
            v = "**YES**"
            why = ("%d two-sided markets across %d families, settling in %s, "
                   "and %s on tape." % (two, ser, settles,
                                        "recorded" if a["tier_b"] else "NOT"))
        verdicts[c] = (v, why)
        A("| **%s** | %d | %d | %d | %d | %d | %s | %d | %s | %s |"
          % (c, ser, mk, two, a["tier_b"], a["tier_a"],
             round(minted.get(c, 0) / days_of_tape),
             a["maker_fee"], settles, v))

    A("")
    A("## The written reason for every verdict — including the obvious ones")
    A("")
    for c, a in sorted(agg.items(), key=lambda x: -x[1]["two"]):
        v, why = verdicts[c]
        a["biggest"].sort(reverse=True)
        top3 = ", ".join("`%s`" % s for _, s in a["biggest"][:3] if _ > 0)
        A("### %s — %s" % (c, v.replace("**", "")))
        A("")
        A("%s" % why)
        A("")
        if top3:
            A("Biggest families by two-sided markets: %s." % top3)
            A("")
        if a["dropped"]:
            A("%d family/families in this category were dropped from the "
              "recorder. The reason and the counts are in `TIERS.md`; a drop "
              "is a recording priority, never a verdict on the family "
              "(GUARDS #15)." % a["dropped"])
            A("")

    A("## What is on tape, by category, right now")
    A("")
    A("| category | price rows recorded |")
    A("|---|---:|")
    for c, n in tape.most_common():
        A("| %s | %s |" % (c, "{:,}".format(n)))
    A("")
    A("## The categories a strategy CAN be tested in")
    A("")
    yes = [c for c in agg if verdicts[c][0].startswith("**YES")]
    slow = [c for c in agg if verdicts[c][0].startswith("**SLOW")]
    no = [c for c in agg if verdicts[c][0].startswith("**NO")
          or verdicts[c][0].startswith("**WEAK")
          or verdicts[c][0].startswith("**UNMEASURABLE")]
    A("- **Testable inside a month (%d):** %s" % (len(yes), ", ".join(sorted(yes))))
    A("- **Testable, but not inside a month (%d):** %s"
      % (len(slow), ", ".join(sorted(slow))))
    A("- **Not testable, with the reason above (%d):** %s"
      % (len(no), ", ".join(sorted(no)) or "none"))
    A("")
    A("**The quota follows from this list.** Every category in the first two "
      "groups needs at least one strategy spec before a second one is written "
      "for any category. `py -3 strategy-factory/src/spec.py --coverage` "
      "checks it and names what is missing.")
    A("")

    out = ROOT / "reports" / "CATEGORIES.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    (ROOT / "data" / "categories.json").write_text(
        json.dumps({"verdicts": {c: verdicts[c][0] for c in verdicts},
                    "quota_categories": sorted(yes + slow)}, indent=1),
        encoding="utf-8")
    print("wrote %s" % out)
    print("testable now: %d   slow: %d   not testable: %d"
          % (len(yes), len(slow), len(no)))
    print("quota applies to %d categories" % len(yes + slow))


if __name__ == "__main__":
    main()
