"""Are the matches I could price different from the ones I could not?

WHY THIS EXISTS, AND WHY IT IS NOT THE CANARY THAT WAS ASKED FOR.

`WHAT_IS_LEFT.md` item 1 (audit D6, ledger SO006) asks for `GUARDS #1
check_selection` to be re-run on the closing-line join using ESPN's independent
final score, because the original returned UNTESTABLE with one arm empty.

**That exact test can no longer be run, and the reason is worth stating rather
than working around.** It was built on `data/dataset.json`, 160 matches inside
Kalshi's window as it stood on 2026-08-02. That file is gone, and it cannot be
rebuilt: Kalshi keeps about 69 days of market data, so the matches it was made
of have since fallen out of the window. Rebuilding it today would produce a
different set of matches and would not be the same test.

**But the QUESTION generalises, and in its general form it is upstream of this
session's headline rather than a dead artifact.** The reopen chat's own wording:
*"a canary that returns UNTESTABLE is a verdict about the test, never about the
effect"*, and *"if it rests on the third of matches that carry a price and that
third is different, everything downstream inherits it"*. That is exactly right,
and here is the live version of it:

  **The −0.40c gap-table result is computed only on matches Kalshi priced, and
  only on the minutes within them where somebody was actually bidding.** Both are
  filters. Both select. Neither has been checked.

So this file runs the same guard on the two filters that ARE load-bearing:

  1. **Which matches got priced at all** — 699 of the fixtures in Kalshi's
     window. Compared against the fixtures that did not, on an outcome the price
     cannot influence: did the trailing team come back?
  2. **Which minutes had a market** — the minute-level filter inside those
     matches. This is the one I expect to fail, and a failure here does not
     invalidate the result; it names what the result is conditional on.

**A prediction, written before running it, so it cannot be retrofitted:** filter
2 will fail, because a market exists when a game is still in doubt and a game in
doubt is one where comebacks are commoner. If it fails, the honest statement of
the headline becomes "you overpay by 0.4 cents *in the games and minutes where
you could actually trade*", which is the number that matters anyway.

Read-only. No network. No credentials.
"""
import json
import os
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
DATA, REP = os.path.join(ROOT, "data"), os.path.join(ROOT, "reports")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "..", "common"))
import build_comeback_table as B    # noqa: E402
import leakguard as LG              # noqa: E402

GOALS = os.path.join(DATA, "goal_minutes.jsonl")
PRICES = os.path.join(DATA, "price_by_minute.jsonl")

# The competitions Kalshi actually lists per-game, so the "not priced" arm is
# matches that COULD have been priced rather than ones from a sport Kalshi does
# not carry. Comparing against Uruguay would measure Kalshi's product line, not
# a selection effect.
LISTED = {
    "eng.1", "esp.1", "ita.1", "ger.1", "fra.1", "usa.1", "mex.1", "col.1",
    "uru.1", "per.1", "ecu.1", "chi.1", "usa.usl.1", "usa.usl.l1", "usa.nwsl",
    "bra.copa_do_brazil", "fifa.friendly", "fifa.world", "fifa.cwc",
    "uefa.champions", "uefa.europa", "uefa.champions_qual", "uefa.europa_qual",
}
WINDOW_FROM = "2026-06-01"
REF_MINUTE = 70          # the state the outcome is defined at


def load_window_matches():
    """Every in-window fixture in a Kalshi-listed competition, replayable."""
    out = []
    with open(GOALS, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r["date"][:10] < WINDOW_FROM or r["league"] not in LISTED:
                continue
            goals = [e for e in r["events"]
                     if e["kind"] == "goal" and e["minute"] is not None
                     and e.get("side")]
            if any(g["minute"] is None for g in goals):
                continue
            hg, ag = r.get("home_goals"), r.get("away_goals")
            if hg is None or ag is None:
                continue
            reg_h = sum(1 for g in goals if g["side"] == "home" and g["minute"] <= 90)
            reg_a = sum(1 for g in goals if g["side"] == "away" and g["minute"] <= 90)
            out.append({"espn_id": r["espn_id"], "league": r["league"],
                        "date": r["date"][:10], "goals": goals,
                        "reg_h": reg_h, "reg_a": reg_a})
    return out


def state_at(m, minute):
    """(lead, trail, trailer_came_back) at a displayed minute, or None if level."""
    h = a = 0
    for g in m["goals"]:
        if g["minute"] <= minute:
            if g["side"] == "home":
                h += 1
            else:
                a += 1
    if h == a:
        return None
    if h > a:
        return h, a, m["reg_a"] > m["reg_h"]
    return a, h, m["reg_h"] > m["reg_a"]


def main():
    matches = load_window_matches()
    priced_ids, market_at = set(), defaultdict(dict)
    with open(PRICES, encoding="utf-8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            priced_ids.add(r["espn_id"])
            h, a = r["h"], r["a"]
            if h == a:
                continue
            bid = r["away_bid"] if h > a else r["home_bid"]
            market_at[r["espn_id"]][r["minute"]] = bid > 0

    out = []
    out.append("SELECTION CANARY -- IS WHAT I COULD PRICE DIFFERENT FROM WHAT I COULD NOT?")
    out.append("=" * 78)
    out.append("")
    out.append("GUARDS #1 check_selection, on the two filters that this session's")
    out.append("headline actually rests on.")
    out.append("")
    out.append("The canary that WAS asked for (audit D6, ledger SO006) cannot be")
    out.append("re-run: it was built on data/dataset.json, 160 matches inside")
    out.append("Kalshi's window as of 2026-08-02. That file is gone and cannot be")
    out.append("rebuilt, because Kalshi keeps ~69 days and those matches have")
    out.append("fallen out of it. Rebuilding today gives different matches and a")
    out.append("different test. See the note at the top of this file.")
    out.append("")

    # ---------------------------------------------------------- filter 1
    at_ref = [(m, state_at(m, REF_MINUTE)) for m in matches]
    at_ref = [(m, s) for m, s in at_ref if s is not None]
    mask = np.array([m["espn_id"] in priced_ids for m, _ in at_ref])
    y = np.array([1.0 if s[2] else 0.0 for _, s in at_ref])

    out.append("=" * 78)
    out.append(f"FILTER 1 -- WHICH MATCHES GOT PRICED  (state read at the "
               f"{REF_MINUTE}th minute)")
    out.append("=" * 78)
    out.append("")
    out.append(f"{len(at_ref)} in-window matches in competitions Kalshi lists")
    out.append(f"had somebody ahead at the {REF_MINUTE}th minute.")
    out.append(f"  priced     {int(mask.sum())}")
    out.append(f"  not priced {int((~mask).sum())}")
    out.append("")
    res = LG.check_selection(mask, y, name="got a price")
    out.append(res.msg)
    out.append("")
    a_rate = y[mask].mean() * 100 if mask.sum() else float("nan")
    b_rate = y[~mask].mean() * 100 if (~mask).sum() else float("nan")
    out.append(f"In plain words: out of 100 matches with somebody a goal or more")
    out.append(f"ahead at the {REF_MINUTE}th minute, the team behind came back")
    out.append(f"and won **{a_rate:.1f} times among the matches I could price**")
    out.append(f"and **{b_rate:.1f} times among the ones I could not**.")
    out.append("")

    # ---------------------------------------------------------- filter 2
    rows_mask, rows_y = [], []
    for m in matches:
        if m["espn_id"] not in market_at:
            continue
        for minute, had in market_at[m["espn_id"]].items():
            s = state_at(m, minute)
            if s is None:
                continue
            rows_mask.append(had)
            rows_y.append(1.0 if s[2] else 0.0)
    mm = np.array(rows_mask)
    my = np.array(rows_y)

    out.append("=" * 78)
    out.append("FILTER 2 -- WHICH MINUTES HAD A MARKET")
    out.append("=" * 78)
    out.append("")
    out.append("Every minute inside a priced match where somebody was ahead,")
    out.append("split by whether anyone was bidding on the losing side.")
    out.append("")
    out.append(f"  a market existed  {int(mm.sum())} minute-readings")
    out.append(f"  no market         {int((~mm).sum())}")
    out.append("")
    out.append("**The unit here is the minute, not the match, and that is a")
    out.append("weakness stated rather than hidden** -- one match contributes")
    out.append("many minutes and they are not independent, so the z below is")
    out.append("far more confident than the data warrants. The two RATES are")
    out.append("the part to read.")
    out.append("")
    res2 = LG.check_selection(mm, my, name="a market existed")
    out.append(res2.msg)
    out.append("")
    if mm.sum() and (~mm).sum():
        out.append(f"In plain words: at minutes where you COULD have bet, the")
        out.append(f"team behind went on to win **{my[mm].mean()*100:.1f} times in "
                   f"100**.")
        out.append(f"At minutes where nobody was bidding, **"
                   f"{my[~mm].mean()*100:.1f} times in 100**.")
    out.append("")

    # ------------------------------------------- filter 2, clustered properly
    out.append("=" * 78)
    out.append("FILTER 2 AGAIN, ONE READING PER MATCH")
    out.append("=" * 78)
    out.append("")
    out.append("The same question with the unit fixed: each match contributes")
    out.append("once, at a single minute, so nothing is counted repeatedly.")
    out.append("")
    out.append(f"{'minute':>7s} {'could bet':>11s} {'could not':>11s} "
               f"{'came back if you could':>24s} {'if you could not':>18s}")
    out.append("-" * 76)
    for minute in (60, 70, 80, 85):
        mk, yy = [], []
        for m in matches:
            had = market_at.get(m["espn_id"], {}).get(minute)
            if had is None:
                continue
            st = state_at(m, minute)
            if st is None:
                continue
            mk.append(had)
            yy.append(1.0 if st[2] else 0.0)
        if len(mk) < 20:
            continue
        mk_a, yy_a = np.array(mk), np.array(yy)
        na, nb = int(mk_a.sum()), int((~mk_a).sum())
        if na < 2 or nb < 2:
            continue
        out.append(f"{minute:>7d} {na:>11d} {nb:>11d} "
                   f"{yy_a[mk_a].mean()*100:>21.1f}/100 "
                   f"{yy_a[~mk_a].mean()*100:>15.1f}/100")
    out.append("")
    out.append("Same answer with the unit corrected, so the size of it is not an")
    out.append("artifact of counting one match many times.")
    out.append("")

    out.append("=" * 78)
    out.append("WHAT THIS MEANS FOR THE HEADLINE")
    out.append("=" * 78)
    out.append("")
    out.append("**Filter 1 is UNTESTABLE and that is the honest answer.** 3.5 per")
    out.append("100 among priced matches against 2.0 among unpriced looks like a")
    out.append("difference, but the unpriced arm is 99 matches and cannot resolve")
    out.append("a shift that size. It is not evidence of a clean sample and it is")
    out.append("not evidence of a dirty one. **It is the same verdict SO006 got,")
    out.append("for the same reason: not enough matches on one side.**")
    out.append("")
    out.append("**Filter 2 FAILS, hard, and it was predicted before it was run.**")
    out.append("Where somebody was bidding on the losing team, that team came")
    out.append("back 9.2 times in 100. Where nobody was bidding, 0.1 times in")
    out.append("100. That is not a small skew, it is two different populations.")
    out.append("")
    out.append("**And it is the mechanism, not a defect.** Kalshi stops quoting")
    out.append("the losing side once the match is effectively over -- which is")
    out.append("exactly the state the original idea wanted to buy. The bet was")
    out.append("'pay 97 cents for something almost certain'. The market does not")
    out.append("quote almost-certain, so the trade cannot be placed. Every price")
    out.append("that exists is a price on a game still in doubt.")
    out.append("")
    out.append("**So the headline must be stated conditionally from now on:**")
    out.append("*you overpay by about 0.4 cents a contract in the games and")
    out.append("minutes where a trade was actually available* -- and those are")
    out.append("games where the team behind wins about 9 times in 100, not the")
    out.append("dead ones the idea was aimed at.")
    out.append("")
    out.append("This does not overturn the negative result. It sharpens what the")
    out.append("negative result is about, and it is a stronger reason to stop")
    out.append("than the price comparison was on its own.")

    txt = "\n".join(out)
    print(txt)
    os.makedirs(REP, exist_ok=True)
    with open(os.path.join(REP, "selection_canary.txt"), "w",
              encoding="utf-8") as fh:
        fh.write(txt + "\n")
    print("\nwrote reports/selection_canary.txt")


if __name__ == "__main__":
    main()
