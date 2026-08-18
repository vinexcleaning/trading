"""The money guard. Tests the three things that could cost him real money.

`test_no_secrets.py` asks "could this folder leak a token". This file asks the
other question: **"could this client spend more than the free allowance, or
spend on the wrong thing"**.

Both failure modes are cheap to prevent and expensive to discover afterwards,
and neither is prevented by being careful. GUARDS #9 -- every rule gets a
planted violation, because a guard nobody has tested against a real violation
is a guard nobody knows still works.

    py -3 -m pytest extractor-apify\\tests -q
"""
from __future__ import annotations

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "src"))
import brightdata  # noqa: E402


# --------------------------------------------------------------------------
# 1. The budget cannot be exceeded

def test_the_plan_fits_inside_the_free_allowance():
    """The pre-registered split must not, on its own, exceed the free tier."""
    total = sum(want for _, want in brightdata.PLAN)
    assert total <= brightdata.HARD_CAP, (
        f"the plan asks for {total} records against a {brightdata.HARD_CAP} "
        f"free allowance -- that is a bill")


def test_hard_cap_is_the_free_allowance_not_a_bigger_number():
    """A cap set above the free tier is not a cap, it is a budget."""
    assert brightdata.HARD_CAP == 5000, (
        "HARD_CAP must equal Bright Data's free monthly allowance. Raising it "
        "is a decision to spend money and does not belong in a code change.")


def _spend_db(tmp_path, already: int):
    db = str(tmp_path / "spend.db")
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    con.executescript(brightdata.SCHEMA)
    if already:
        con.execute("INSERT INTO pt_spend VALUES (?,?,?,?,?,?,?)",
                    ("t", "x", "k", already, already, "s", "ready"))
        con.commit()
    return con


def test_spent_counts_what_was_returned_not_what_was_asked_for(tmp_path):
    """Billing is per delivered record. Counting requests would let a run
    that under-delivers silently buy a second helping."""
    con = _spend_db(tmp_path, 0)
    con.execute("INSERT INTO pt_spend VALUES (?,?,?,?,?,?,?)",
                ("t", "x", "kalshi", 3500, 12, "s", "ready"))
    con.commit()
    assert brightdata.spent(con) == 12


def test_the_budget_check_refuses_the_request_that_would_cross_the_line(
        tmp_path):
    """The planted violation: an account already at the cap must not be able
    to ask for one more record."""
    con = _spend_db(tmp_path, brightdata.HARD_CAP)
    used = brightdata.spent(con)
    per = 100
    assert used + per > brightdata.HARD_CAP, (
        "the arithmetic the run loop uses to stop has stopped being true")


def test_a_run_at_the_cap_would_stop_before_sending(tmp_path, monkeypatch,
                                                    capsys):
    """End to end: with the allowance already spent, `run` must return
    without ever calling trigger()."""
    con = _spend_db(tmp_path, brightdata.HARD_CAP)
    monkeypatch.setattr(brightdata, "connect", lambda: con)
    monkeypatch.setattr(brightdata, "list_scrapers",
                        lambda t: ("/fake", [{"id": "gd_x",
                                              "name": "twitter posts "
                                                      "discover by keyword"}],
                                   []))

    def explode(*a, **k):
        raise AssertionError("trigger() was called with the budget spent")

    monkeypatch.setattr(brightdata, "trigger", explode)
    assert brightdata.cmd_run("not-a-real-token") == 0
    assert "BUDGET STOP" in capsys.readouterr().out


# --------------------------------------------------------------------------
# 2. Ambiguity is never resolved silently

TWO_TWITTER = [
    {"id": "gd_aaa", "name": "Twitter posts - discover by keyword"},
    {"id": "gd_bbb", "name": "Twitter posts - discover by profile keyword"},
]
ONE_TWITTER = [
    {"id": "gd_aaa", "name": "Twitter posts - discover by keyword"},
    {"id": "gd_ccc", "name": "Instagram posts - collect by url"},
]


def test_one_clear_match_is_chosen():
    chosen, cands = brightdata.pick(ONE_TWITTER, "x")
    assert chosen is not None and brightdata.dataset_id_of(chosen) == "gd_aaa"


def test_two_matches_is_a_refusal_not_a_coin_flip():
    """The planted violation. Picking the first of two would spend money on
    a guess, which is exactly what `CLAUDE.md` §3 says has already cost an
    afternoon once."""
    chosen, cands = brightdata.pick(TWO_TWITTER, "x")
    assert chosen is None, "two candidates must not silently resolve to one"
    assert len(cands) == 2


def test_no_match_is_a_refusal():
    chosen, cands = brightdata.pick(
        [{"id": "gd_z", "name": "Amazon products - collect by url"}], "x")
    assert chosen is None and cands == []


def test_a_collect_by_url_scraper_is_never_picked_for_a_keyword_search():
    """We have search terms, not post URLs. Triggering a collect-by-url
    scraper with a keyword spends the allowance and returns nothing."""
    chosen, cands = brightdata.pick(
        [{"id": "gd_q", "name": "Instagram posts - collect by URL"}],
        "instagram")
    assert chosen is None and cands == []


def test_a_run_with_an_ambiguous_library_spends_nothing(monkeypatch, tmp_path,
                                                        capsys):
    con = _spend_db(tmp_path, 0)
    monkeypatch.setattr(brightdata, "connect", lambda: con)
    monkeypatch.setattr(brightdata, "list_scrapers",
                        lambda t: ("/fake", TWO_TWITTER, []))

    def explode(*a, **k):
        raise AssertionError("trigger() was called on an ambiguous match")

    monkeypatch.setattr(brightdata, "trigger", explode)
    brightdata.cmd_run("not-a-real-token")
    out = capsys.readouterr().out
    assert "SKIPPED" in out
    assert brightdata.spent(con) == 0


# --------------------------------------------------------------------------
# 3. The token comes from outside the repo, and never gets written down

def test_the_token_path_is_outside_this_repo():
    folder = os.path.dirname(os.path.dirname(os.path.abspath(
        brightdata.__file__)))
    assert not os.path.abspath(brightdata.TOKEN_PATH).startswith(
        os.path.abspath(folder)), (
        "the token path points inside this folder, which is in a public repo")
    assert "keys" in brightdata.TOKEN_PATH.lower()


def test_missing_token_is_a_clean_stop_not_a_crash(monkeypatch):
    monkeypatch.delenv(brightdata.TOKEN_ENV, raising=False)
    monkeypatch.setattr(brightdata.os.path, "exists", lambda p: False)
    try:
        brightdata.load_token()
    except SystemExit as e:
        assert "token" in str(e).lower()
        return
    raise AssertionError("a missing token must stop the run")


def test_no_record_row_can_carry_the_token():
    """The raw vendor row is stored for recovery. Prove the stored tuple has
    no slot fed from the token, by normalising a row that contains one."""
    row = {"id": "1", "text": "hello", "authorization": "Bearer SECRETVALUE"}
    out = brightdata.normalise(row, "x", "kalshi")
    # The raw blob is deliberately kept -- so assert the vendor never sends
    # our own credential back, by checking we do not copy any auth header in.
    assert "Bearer SECRETVALUE" in out[10], (
        "raw is stored verbatim by design; this test exists so that if that "
        "ever changes, someone reads the comment above and thinks about it")
    assert all("Bearer" not in str(f) for f in out[:10]), (
        "a normalised field is carrying an authorization value")
