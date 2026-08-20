"""Guards on the shared capacity tool.

These deliberately do NOT touch the 76 GB recorder database. The part worth
testing is the judgement, not the SQL: whether bucketing changes the answer,
and whether the verdict refuses to average a good bucket together with a dead
one.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from common.capacity import Slice, _hours, verdict  # noqa: E402


def S(bucket, spread, touch, n=1000):
    return Slice(bucket=bucket, n=n, mean_spread_c=spread,
                 median_touch_usd=touch, median_depth5_usd=touch * 10,
                 median_ask_size=touch)


# --------------------------------------------------------------------------
# The reason this tool buckets at all
# --------------------------------------------------------------------------

def test_a_good_bucket_is_not_averaged_away_by_a_dead_one():
    """The real KXITFMATCH case. Flat, it reads 10.1c and $47 and looks dead.
    Bucketed, the last two hours read 5.6c and $124 and are a different market.
    A verdict that averaged them would report the wrong answer."""
    itf = [S("last 2h", 5.6, 124), S("2-12h", 9.7, 46), S("over 12h", 19.9, 13)]
    v = verdict(itf, want_usd=100.0, max_spread_c=5.0)
    assert "124" in v, f"the live bucket vanished from the verdict: {v}"
    assert "last 2h" in v.lower()


def test_thin_everywhere_is_called_thin():
    dead = [S("last 2h", 4.0, 12), S("2-12h", 9.0, 6)]
    v = verdict(dead, want_usd=100.0)
    assert v.startswith("TOO THIN"), v
    assert "12" in v, "the verdict must say what was actually there"


def test_deep_but_wide_is_not_called_tradeable():
    """Depth without a tight quote is the trap: the money is there and it costs
    a fortune to reach. The archive's fake heavy-favourite edge GREW with the
    spread for exactly this reason."""
    wide = [S("last 2h", 12.0, 5000)]
    v = verdict(wide, want_usd=100.0, max_spread_c=5.0)
    assert v.startswith("WIDE"), v
    assert "12.0c" in v


def test_deep_and_tight_is_tradeable():
    atp = [S("last 2h", 1.2, 9599), S("2-12h", 1.4, 6644)]
    v = verdict(atp, want_usd=100.0, max_spread_c=5.0)
    assert v.startswith("TRADEABLE"), v


def test_no_data_is_its_own_answer_not_a_zero():
    """GUARDS #21 and #15. An unrecorded family is unknown, not empty, and
    reporting $0 would read as 'measured and found nothing'."""
    v = verdict([], want_usd=100.0)
    assert "NO DATA" in v
    assert "not in the recorder" in v


def test_the_verdict_names_the_bucket_rather_than_a_family_average():
    """If a future edit ever averages the buckets, this fails: the mean of
    5.6, 9.7 and 19.9 is 11.7, which appears nowhere in a correct verdict."""
    itf = [S("last 2h", 5.6, 124), S("2-12h", 9.7, 46), S("over 12h", 19.9, 13)]
    v = verdict(itf, want_usd=100.0, max_spread_c=5.0)
    assert "11.7" not in v and "11.73" not in v


# --------------------------------------------------------------------------
# Time arithmetic
# --------------------------------------------------------------------------

def test_hours_between_two_stamps():
    assert _hours("2026-08-20T00:00:00Z", "2026-08-20T02:30:00Z") == 2.5
    assert _hours("2026-08-20T02:30:00Z", "2026-08-20T00:00:00Z") == -2.5


def test_hours_handles_the_offset_form_the_recorder_writes():
    assert _hours("2026-08-20T00:00:00+00:00", "2026-08-20T01:00:00Z") == 1.0
