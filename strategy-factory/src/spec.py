"""THE STRATEGY SPEC — written down before any data is touched, and validated.

His instruction, verbatim: *"Strategies are written specs before any data is
touched: id, market family, what it bets on, entry rule, exit rule, size rule,
what would make it wrong, who suggested it, date. The exit dimension is part of
the spec and not an afterthought — hold to settlement, sell at a level, buy
more at a level, which level, one mentality or two, what happens when two
disagree."*

Every one of those nine fields is required here and the file will not validate
without it. `wrong_if` cannot be empty: a strategy with no result that would
kill it is not a test, it is a hope.

One JSON file per spec in `specs/`, not one big registry. Specs are the thing a
human argues with, and a 400-line diff on a shared file is not arguable.

    py -3 strategy-factory/src/spec.py --validate
    py -3 strategy-factory/src/spec.py --new SF042
    py -3 strategy-factory/src/spec.py --list
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECS = ROOT / "specs"

#: Where an idea came from. `STRATEGY_FACTORY.md` stage 2 names four sources
#: and says all four run. `user` is the one this repo cannot generate and is
#: therefore the one never to let go stale.
SOURCES = {"reasoning", "github", "youtube", "reddit", "discord", "reopen",
           "user", "ledger"}

#: His exit dimension, made into an enumeration so it cannot be skipped.
EXIT_MODES = {
    "hold_to_settlement",   # buy, do nothing, let it settle
    "sell_at_level",        # take profit or cut at a stated price
    "scale_in",             # buy more at a stated worse price
    "sell_and_scale",       # both, and `on_disagreement` must say which wins
    "time_exit",            # out at a stated time regardless of price
}

SIZE_RULES = {"flat", "depth_capped", "fraction_of_bankroll"}

REQUIRED = ["id", "created", "author", "source", "source_detail", "families",
            "thesis", "unit", "entry", "exit", "size", "wrong_if", "slow"]

TEMPLATE = {
    "id": "SFxxx",
    "created": "2026-08-18",
    "author": "claude:factory",
    "source": "reasoning",
    "source_detail": "one line: which repo, which video and timestamp, which "
                     "ledger id, or which sentence of his",
    "families": ["KXEXAMPLE"],
    "thesis": "One plain sentence. What this bets on, and the mechanism that "
              "would make it work. No jargon.",
    "unit": "one settled market",
    "entry": {
        "when": "the condition, stated so that code could not disagree with a "
                "human reading it",
        "side": "yes",
        "min_price_c": 3,
        "max_price_c": 97,
        "max_spread_c": 3,
    },
    "exit": {
        "mode": "hold_to_settlement",
        "sell_at_c": None,
        "buy_more_at_c": None,
        "time_exit_utc_rule": None,
        "second_mentality": None,
        "on_disagreement": None,
    },
    "size": {
        "rule": "depth_capped",
        "usd_per_bet": 10,
        "max_share_of_depth": 0.25,
    },
    "wrong_if": [
        "at least one result that would make me drop this, stated as a number"
    ],
    "slow": False,
    "notes": "",
}


def rule_fingerprint(spec: dict) -> str:
    """A hash of the RULE, ignoring id, author, date and prose.

    PREREGISTRATION.md section 4: "A variant of it is a new strategy with a new
    id, and it counts against the screened total." The corollary is that the
    SAME rule under a new id is not a new strategy, and the screened count is
    the number everything else is judged against. So the rule is fingerprinted
    and a duplicate is an error, not a curiosity.
    """
    core = {k: spec.get(k) for k in ("families", "entry", "exit", "size",
                                     "unit")}
    return hashlib.sha256(
        json.dumps(core, sort_keys=True, default=str).encode()).hexdigest()[:16]


def validate(spec: dict, path: Path) -> list:
    bad = []
    for k in REQUIRED:
        if k not in spec:
            bad.append("missing required field %r" % k)
    if bad:
        return bad
    if not re.fullmatch(r"SF\d{3,4}", str(spec["id"])):
        bad.append("id %r is not SF followed by 3-4 digits" % spec["id"])
    if path.stem != str(spec["id"]):
        bad.append("filename %s does not match id %s" % (path.stem, spec["id"]))
    if spec["source"] not in SOURCES:
        bad.append("source %r not one of %s" % (spec["source"], sorted(SOURCES)))
    if not str(spec.get("source_detail") or "").strip():
        bad.append("source_detail is empty - who suggested it, and where")
    if not spec["families"] or not isinstance(spec["families"], list):
        bad.append("families must be a non-empty list of Kalshi series")
    if len(str(spec.get("thesis") or "")) < 20:
        bad.append("thesis is too short to be a thesis")

    e = spec.get("entry") or {}
    if not str(e.get("when") or "").strip():
        bad.append("entry.when is empty")
    if e.get("side") not in ("yes", "no", "either"):
        bad.append("entry.side must be yes, no or either")

    x = spec.get("exit") or {}
    mode = x.get("mode")
    if mode not in EXIT_MODES:
        bad.append("exit.mode %r not one of %s" % (mode, sorted(EXIT_MODES)))
    # The consistency checks are the point of the enumeration. An exit mode
    # naming a level, with no level, is the afterthought he told us not to
    # write.
    if mode in ("sell_at_level", "sell_and_scale") and x.get("sell_at_c") is None:
        bad.append("exit.mode %s but no exit.sell_at_c - which level?" % mode)
    if mode in ("scale_in", "sell_and_scale") and x.get("buy_more_at_c") is None:
        bad.append("exit.mode %s but no exit.buy_more_at_c - which level?" % mode)
    if mode == "time_exit" and not x.get("time_exit_utc_rule"):
        bad.append("exit.mode time_exit but no exit.time_exit_utc_rule")
    if x.get("second_mentality") and not x.get("on_disagreement"):
        bad.append("two mentalities declared but exit.on_disagreement is "
                   "empty - what happens when they disagree?")

    s = spec.get("size") or {}
    if s.get("rule") not in SIZE_RULES:
        bad.append("size.rule %r not one of %s" % (s.get("rule"),
                                                   sorted(SIZE_RULES)))
    if not isinstance(s.get("usd_per_bet"), (int, float)) or s["usd_per_bet"] <= 0:
        bad.append("size.usd_per_bet must be a positive number")

    w = spec.get("wrong_if")
    if not isinstance(w, list) or not [q for q in w if str(q).strip()]:
        bad.append("wrong_if is empty - a strategy with no result that would "
                   "kill it is not a test")
    if not isinstance(spec.get("slow"), bool):
        bad.append("slow must be true or false - does this family settle "
                   "often enough to be judged inside a month?")
    return bad


def load_all():
    out = []
    for p in sorted(SPECS.glob("SF*.json")):
        try:
            out.append((p, json.loads(p.read_text(encoding="utf-8"))))
        except ValueError as exc:
            out.append((p, {"_parse_error": str(exc)}))
    return out


def cmd_validate() -> int:
    specs = load_all()
    if not specs:
        print("no specs in %s" % SPECS)
        return 0
    fails = 0
    fps = Counter()
    ids = Counter()
    for p, s in specs:
        if "_parse_error" in s:
            print("FAIL %s: does not parse: %s" % (p.name, s["_parse_error"]))
            fails += 1
            continue
        bad = validate(s, p)
        ids[s.get("id")] += 1
        fps[rule_fingerprint(s)] += 1
        if bad:
            fails += 1
            print("FAIL %s" % p.name)
            for b in bad:
                print("      - %s" % b)
    for i, n in ids.items():
        if n > 1:
            print("FAIL duplicate id %s used %d times" % (i, n))
            fails += 1
    for f, n in fps.items():
        if n > 1:
            who = [s["id"] for _, s in specs
                   if "_parse_error" not in s and rule_fingerprint(s) == f]
            print("FAIL identical rule under %d ids: %s -- the same rule "
                  "under a new id is not a new strategy" % (n, who))
            fails += 1
    print("\n%d specs, %d problems" % (len(specs), fails))
    return 1 if fails else 0


def cmd_new(new_id: str) -> int:
    SPECS.mkdir(parents=True, exist_ok=True)
    p = SPECS / ("%s.json" % new_id)
    if p.exists():
        print("%s already exists" % p)
        return 1
    t = dict(TEMPLATE)
    t["id"] = new_id
    p.write_text(json.dumps(t, indent=1), encoding="utf-8")
    print("wrote %s" % p)
    return 0


def cmd_list() -> int:
    specs = [(p, s) for p, s in load_all() if "_parse_error" not in s]
    print("%-8s %-10s %-26s %-20s %s"
          % ("id", "source", "families", "exit", "thesis"))
    for p, s in specs:
        print("%-8s %-10s %-26s %-20s %s"
              % (s.get("id"), s.get("source"),
                 ",".join(s.get("families") or [])[:26],
                 (s.get("exit") or {}).get("mode", "?"),
                 str(s.get("thesis"))[:60]))
    print("\n%d specs" % len(specs))
    by = Counter(s.get("source") for _, s in specs)
    print("by source: %s" % dict(by))
    print("slow (cannot be judged inside a month): %d"
          % sum(1 for _, s in specs if s.get("slow")))
    return 0


def cmd_coverage() -> int:
    """THE QUOTA CHECK — the mechanism that makes narrowing visible.

    Mailbox 001: *"A total is how narrowing hides. 200 strategies all on
    baseball satisfies '200 strategies' and fails him completely."* So the
    check is not how many specs exist, it is **how many categories have none**,
    and it names them.

    A category is only in the quota if `categories.py` judged a strategy could
    ever be tested there — and that judgment carries a written reason, so a
    category cannot drop out of the quota silently either.
    """
    ROOT = SPECS.parent
    cats_p = ROOT / "data" / "categories.json"
    if not cats_p.exists():
        print("run src/categories.py first - %s missing" % cats_p)
        return 1
    quota = json.loads(cats_p.read_text(encoding="utf-8"))["quota_categories"]

    # ⚠ Read the category from shape.json, which is the SAME source
    # `categories.py` used to build the quota. Reading it from `census.db`'s
    # `series` table instead put SF017 in an "(unmatched)" bucket and reported
    # its category as having no spec — because `KXMLBWINS` is listed with 106
    # open markets and has **no series row at all**, so the lookup missed and
    # the miss looked like a gap in coverage. Two sources of truth for one
    # label is how a coverage checker reports a hole that is not there, which
    # is worse than useless: it sends the next session to fill a filled slot.
    ser_cat = {s: (d.get("category") or "?")
               for s, d in json.loads(
                   (ROOT / "data" / "shape.json").read_text(encoding="utf-8")
               )["per_series"].items()}

    #: A spec may name a wildcard family like `*tier_a_economics` instead of
    #: real tickers. The wildcard carries its own category, so it is read here
    #: rather than silently counting as "no category".
    def cats_of(spec):
        out = set()
        for f in spec.get("families") or []:
            if f.startswith("*"):
                for c in quota:
                    if c.lower().split()[0] in f.lower():
                        out.add(c)
                if f in ("*all_tier_a", "*tier_a_no_maker_fee",
                         "*tier_a_no_maker_fee_non_financial",
                         "*tier_a_scheduled_release"):
                    out.add("(cross-category)")
            elif f in ser_cat:
                out.add(ser_cat[f])
        return out or {"(unmatched)"}

    per = Counter()
    for _, s in load_all():
        if "_parse_error" in s:
            continue
        for c in cats_of(s):
            per[c] += 1

    print("%-26s %6s   %s" % ("category", "specs", "quota"))
    missing = []
    for c in quota:
        n = per.get(c, 0)
        if n == 0:
            missing.append(c)
        print("%-26s %6d   %s" % (c, n, "OK" if n else "**NONE**"))
    for c in sorted(set(per) - set(quota)):
        print("%-26s %6d   (not in quota)" % (c, per[c]))
    print()
    total = len([1 for _, s in load_all() if "_parse_error" not in s])
    print("%d specs across %d of %d quota categories"
          % (total, len(quota) - len(missing), len(quota)))
    if missing:
        print()
        print("QUOTA NOT MET. No second spec should be written for any "
              "category until these have one:")
        for c in missing:
            print("   - %s" % c)
        return 1
    print("QUOTA MET - every testable category has at least one strategy.")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--new", default="")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--coverage", action="store_true")
    args = ap.parse_args()
    if args.new:
        sys.exit(cmd_new(args.new))
    if args.list:
        sys.exit(cmd_list())
    if args.coverage:
        sys.exit(cmd_coverage())
    sys.exit(cmd_validate())


if __name__ == "__main__":
    main()
