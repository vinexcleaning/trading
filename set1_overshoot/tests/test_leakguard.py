"""Tests for the selection guards, plus live regression tests against the real
universe so the Phase 0 bug cannot come back silently.

Run: pytest tests/ -q
"""
import json
import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import leakguard as lg  # noqa: E402


# ---------------------------------------------------------------- unit tests
def test_fair_side_choice_passes():
    rng = np.random.default_rng(0)
    r = lg.check_side_choice(rng.random(20000) < 0.5, name="fair")
    assert r.verdict == lg.PASS


def test_biased_side_choice_fails():
    rng = np.random.default_rng(1)
    r = lg.check_side_choice(rng.random(20000) < 0.5356, name="volume-like")
    assert r.verdict == lg.FAIL
    with pytest.raises(lg.SelectionLeak):
        r.raise_if_bad()


def test_last_price_scale_bias_fails():
    rng = np.random.default_rng(2)
    r = lg.check_side_choice(rng.random(5000) < 0.999, name="last-price-like")
    assert r.verdict == lg.FAIL


# --- the hole that v1 of this file had -------------------------------------
def test_degenerate_field_is_untestable_not_pass():
    """A rule whose field is constant decides nothing and must not pass.

    This is the liquidity_dollars case: it scored z=+0.88 and was recorded as a
    clean alternative dedupe rule. It reads 0 on both sides of every settled
    tennis market, so it never actually chooses.
    """
    rng = np.random.default_rng(3)
    kept_won = rng.random(20000) < 0.5
    disc = np.zeros(20000, bool)          # field identical on both sides
    r = lg.check_side_choice(kept_won, disc, name="all-null field")
    assert r.verdict == lg.UNTESTABLE
    assert "emptiness" in r.msg
    with pytest.raises(lg.Untestable):
        r.raise_if_bad()


def test_mostly_degenerate_field_is_untestable():
    rng = np.random.default_rng(4)
    n = 20000
    disc = rng.random(n) < 0.039          # the volume_24h case
    r = lg.check_side_choice(rng.random(n) < 0.5, disc, name="mostly null")
    assert r.verdict == lg.UNTESTABLE


def test_underpowered_side_rule_is_untestable():
    rng = np.random.default_rng(5)
    r = lg.check_side_choice(rng.random(300) < 0.5, name="tiny but varying")
    assert r.verdict == lg.UNTESTABLE
    assert "detect" in r.msg


def test_a_biased_degenerate_field_still_fails_when_it_does_decide():
    """Degeneracy must not become a way to hide a real bias."""
    rng = np.random.default_rng(6)
    n = 60000
    disc = rng.random(n) < 0.5
    kept = np.where(disc, rng.random(n) < 0.60, rng.random(n) < 0.50)
    r = lg.check_side_choice(kept, disc, name="biased where it decides")
    assert r.verdict == lg.FAIL


# --- filters ---------------------------------------------------------------
def test_neutral_filter_passes():
    rng = np.random.default_rng(7)
    n = 40000
    p = rng.uniform(0.2, 0.8, n)
    y = (rng.random(n) < p).astype(float)
    r = lg.check_selection(rng.random(n) < 0.6, y, p, "random filter")
    assert r.verdict == lg.PASS


def test_outcome_correlated_filter_fails():
    rng = np.random.default_rng(8)
    n = 40000
    p = rng.uniform(0.2, 0.8, n)
    y = (rng.random(n) < p).astype(float)
    mask = np.where(y == 1, rng.random(n) < 0.7, rng.random(n) < 0.5)
    r = lg.check_selection(mask, y, p, "outcome-correlated")
    assert r.verdict == lg.FAIL


def test_tiny_arm_is_untestable_not_pass():
    rng = np.random.default_rng(9)
    n = 20000
    p = rng.uniform(0.2, 0.8, n)
    y = (rng.random(n) < p).astype(float)
    mask = np.ones(n, bool)
    mask[:40] = False                     # 40-row dropped arm
    r = lg.check_selection(mask, y, p, "tiny dropped arm")
    assert r.verdict == lg.UNTESTABLE


# ------------------------------------------------------- live regression tests
DATA = ROOT / "data"


@pytest.mark.skipif(not (DATA / "universe.parquet").exists(),
                    reason="universe not built")
def test_live_universe_dedupe_is_outcome_neutral():
    uni = pd.read_parquet(DATA / "universe.parquet")
    r = lg.check_side_choice((uni["result"] == "yes").values,
                             name="live universe dedupe")
    assert r.verdict == lg.PASS, r.msg


@pytest.mark.skipif(not (DATA / "markets_raw.json").exists(),
                    reason="raw markets not pulled")
def test_known_bad_rules_still_detected():
    """Guard-rot test: the rules known to be biased must still trip it."""
    raw = json.loads((DATA / "markets_raw.json").read_text(encoding="utf-8"))
    rows = []
    for _, ms in raw.items():
        for m in ms:
            if m.get("result") in ("yes", "no"):
                rows.append((m["event_ticker"], m["ticker"], m["result"],
                             float(m.get("volume_fp") or 0),
                             float(m.get("open_interest_fp") or 0),
                             float(m.get("last_price_dollars") or 0)))
    d = pd.DataFrame(rows, columns=["ev", "tk", "res", "vol", "oi", "last"])
    d = d.groupby("ev").filter(lambda x: len(x) == 2)
    a = d.groupby("ev").nth(0).reset_index()
    b = d.groupby("ev").nth(1).reset_index()
    m = a.merge(b, on="ev", suffixes=("_a", "_b"))
    for field in ("vol", "oi", "last"):
        fa, fb = m[f"{field}_a"].values, m[f"{field}_b"].values
        kept = np.where(fa > fb, m["res_a"].values, m["res_b"].values)
        r = lg.check_side_choice(kept == "yes", fa != fb, field)
        assert r.verdict == lg.FAIL, f"{field} no longer detected: {r.msg}"


@pytest.mark.skipif(not (ROOT / "src" / "p0_universe.py").exists(),
                    reason="pipeline missing")
def test_universe_builder_enforces_the_canary():
    src = (ROOT / "src" / "p0_universe.py").read_text(encoding="utf-8")
    assert "SELECTION CANARY" in src
    assert "check_side_choice" in src and "raise_if_bad" in src, (
        "canary is printed but not enforced through leakguard")
    banned = ("volume", "open_interest", "last_price", "liquidity")
    for line in src.splitlines():
        code = line.split("#", 1)[0]
        if "sort_values" in code and "event_ticker" in code:
            assert not any(b in code for b in banned), (
                f"dedupe sort reads a post-settlement field: {code.strip()}")
