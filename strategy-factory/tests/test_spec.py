"""The spec validator, and a guard-rot check on it.

GUARDS #9: a guard nobody has tested against a real violation is a guard nobody
knows still works. The whole value of `spec.py` is that it refuses a spec with
no kill condition and refuses the same rule filed twice under two ids, so both
of those are tested against deliberately broken specs rather than trusted.

    py -3 -m pytest strategy-factory/tests -q
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
import spec as S  # noqa: E402


def good():
    d = copy.deepcopy(S.TEMPLATE)
    d["id"] = "SF001"
    d["families"] = ["KXHIGHNY"]
    d["thesis"] = "A long enough sentence to count as a thesis, with a reason."
    d["entry"]["when"] = "any condition stated precisely"
    d["wrong_if"] = ["forward result inside the no-skill range at 100 markets"]
    return d


def test_a_good_spec_validates():
    assert S.validate(good(), Path("SF001.json")) == []


def test_every_real_spec_on_disk_validates():
    """The specs actually committed to this folder must pass. This is the test
    that turns the validator from a tool into a rule."""
    problems = {}
    for p, s in S.load_all():
        if "_parse_error" in s:
            problems[p.name] = [s["_parse_error"]]
            continue
        bad = S.validate(s, p)
        if bad:
            problems[p.name] = bad
    assert not problems, problems


def test_no_two_specs_share_a_rule():
    """The same rule under a new id is not a new strategy, and the screened
    count is the number every reported return is judged against."""
    seen = {}
    for p, s in S.load_all():
        if "_parse_error" in s:
            continue
        fp = S.rule_fingerprint(s)
        assert fp not in seen, ("%s and %s are the same rule under two ids"
                                % (seen[fp], s["id"]))
        seen[fp] = s["id"]


def test_empty_wrong_if_is_rejected():
    d = good()
    d["wrong_if"] = []
    assert any("wrong_if" in b for b in S.validate(d, Path("SF001.json")))
    d["wrong_if"] = ["   "]
    assert any("wrong_if" in b for b in S.validate(d, Path("SF001.json")))


def test_exit_mode_naming_a_level_must_carry_the_level():
    """His words: the exit dimension is part of the spec and not an
    afterthought. A mode that says 'sell at a level' with no level IS the
    afterthought."""
    d = good()
    d["exit"]["mode"] = "sell_at_level"
    assert any("sell_at_c" in b for b in S.validate(d, Path("SF001.json")))
    d["exit"]["sell_at_c"] = 80
    assert S.validate(d, Path("SF001.json")) == []


def test_two_mentalities_must_say_who_wins():
    d = good()
    d["exit"]["second_mentality"] = "the other bot holds to settlement"
    assert any("disagreement" in b for b in S.validate(d, Path("SF001.json")))
    d["exit"]["on_disagreement"] = "the selling mentality wins; it is the "\
                                   "one being tested"
    assert S.validate(d, Path("SF001.json")) == []


def test_id_and_filename_must_match():
    assert any("filename" in b for b in S.validate(good(), Path("SF999.json")))


def test_fingerprint_ignores_prose_but_not_the_rule():
    a, b = good(), good()
    b["id"] = "SF002"
    b["author"] = "someone else"
    b["thesis"] = "Completely different words describing the same mechanism."
    assert S.rule_fingerprint(a) == S.rule_fingerprint(b), \
        "renaming a spec must not disguise it as a new strategy"
    b["entry"]["max_price_c"] = 60
    assert S.rule_fingerprint(a) != S.rule_fingerprint(b), \
        "changing the rule must produce a different strategy"
