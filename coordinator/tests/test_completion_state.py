"""Canary: the completion signal, and the one property that makes it work.

⚠ WHAT THIS IS FOR. Nothing in this repo can watch a chat window. A session
thinking hard and a session that died look identical from disk. Three derived
signals were measured before anything was added, and all three failed:

  * mail `Status:` -- self-reported and lagging. Seven livedesk messages read
    OPEN while the commits proved the work was finished.
  * commits after a message opened -- measured across all 119 messages. It
    fires on ACTIVITY, not completion, and its single hit was a false positive.
  * HANDOFF.md changes -- same defect.

So the signal is explicit. The property that makes it more than another
self-report is that **a WORKING claim EXPIRES**: a participant that says WORKING
and then stops refreshing its timestamp becomes STALLED without cooperating,
which is exactly the stopped-midway case nothing could previously see.

`test_absent_block_is_unchanged_behaviour` is the compatibility guarantee. If
someone makes the fields required, it fails.

Run:  py -3 coordinator\\tests\\test_completion_state.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

COORD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(COORD))

import where  # noqa: E402

NOW = datetime(2026, 8, 22, 12, 0, 0)


def block(**fields) -> str:
    inner = "\n".join(f"{k}: {v}" for k, v in fields.items())
    return f"<!-- COORDINATOR-STATE\n{inner}\n-->"


# ---------------------------------------------------------------- compatibility

def test_absent_block_is_unchanged_behaviour():
    """A participant that never opts in must read exactly as it always did."""
    d = where.declared(block(doing="x", left="y", needs="no"))
    assert d.get("doing") == "x" and d.get("left") == "y"
    state, why = where.liveness(d, NOW)
    assert state == "UNKNOWN", f"got {state}"
    assert "not declared a state" in why


def test_the_original_three_fields_still_parse():
    """The fields every existing worker writes must be untouched."""
    d = where.declared(block(doing="a", left="b", needs="yes - a question"))
    assert d["doing"] == "a"
    assert d["left"] == "b"
    assert d["needs"] == "yes - a question"


def test_no_block_at_all():
    assert where.declared("just some prose") == {}
    assert where.liveness({}, NOW)[0] == "UNKNOWN"


# ---------------------------------------------------------------- the states

def test_done_is_reported():
    d = where.declared(block(doing="x", left="y", needs="no", state="DONE"))
    assert where.liveness(d, NOW)[0] == "DONE"


def test_blocked_is_reported():
    d = where.declared(block(doing="x", left="", needs="no", state="BLOCKED"))
    assert where.liveness(d, NOW)[0] == "BLOCKED"


def test_case_and_whitespace_do_not_matter():
    d = where.declared(block(doing="x", left="y", needs="no", state="  done  "))
    assert where.liveness(d, NOW)[0] == "DONE"


def test_working_and_fresh():
    fresh = (NOW - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M")
    d = where.declared(block(doing="x", left="y", needs="no",
                             state="WORKING", updated=fresh))
    state, why = where.liveness(d, NOW)
    assert state == "WORKING", why
    assert "10 minutes ago" in why


# ------------------------------------------------- THE ONE THAT MATTERS

def test_a_working_claim_expires_by_itself():
    """The stopped-midway case. Nothing cooperates; silence is the signal."""
    old = (NOW - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M")
    d = where.declared(block(doing="x", left="y", needs="no",
                             state="WORKING", updated=old))
    state, why = where.liveness(d, NOW)
    assert state == "STALLED", f"got {state}: {why}"
    assert "6.0 hours" in why
    assert "stopped midway" in why


def test_the_expiry_boundary_is_where_it_says():
    just_ok = (NOW - timedelta(minutes=where.STALE_AFTER_MIN - 1)) \
        .strftime("%Y-%m-%dT%H:%M")
    just_not = (NOW - timedelta(minutes=where.STALE_AFTER_MIN + 1)) \
        .strftime("%Y-%m-%dT%H:%M")
    ok = where.declared(block(state="WORKING", updated=just_ok))
    bad = where.declared(block(state="WORKING", updated=just_not))
    assert where.liveness(ok, NOW)[0] == "WORKING"
    assert where.liveness(bad, NOW)[0] == "STALLED"


def test_working_without_a_timestamp_is_not_believed():
    """An un-expirable WORKING claim is worth nothing and must not read WORKING."""
    d = where.declared(block(doing="x", left="y", needs="no", state="WORKING"))
    state, why = where.liveness(d, NOW)
    assert state == "UNKNOWN", f"got {state}"
    assert "cannot expire" in why


def test_done_does_not_need_a_timestamp():
    """Only WORKING expires. DONE and BLOCKED are terminal."""
    d = where.declared(block(state="DONE"))
    assert where.liveness(d, NOW)[0] == "DONE"


# ---------------------------------------------------------------- robustness

def test_a_nonsense_state_reads_unknown_and_says_so():
    d = where.declared(block(doing="x", state="finished-ish"))
    state, why = where.liveness(d, NOW)
    assert state == "UNKNOWN"
    assert "not one of" in why


def test_an_unparseable_timestamp_does_not_crash():
    d = where.declared(block(state="WORKING", updated="last tuesday"))
    state, _ = where.liveness(d, NOW)
    assert state == "UNKNOWN"


def test_several_timestamp_shapes_are_accepted():
    for shape in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M"):
        stamp = (NOW - timedelta(minutes=5)).strftime(shape)
        d = where.declared(block(state="WORKING", updated=stamp))
        assert where.liveness(d, NOW)[0] == "WORKING", shape


def test_a_future_timestamp_does_not_read_as_stalled():
    """Clock skew between machines must not invent a stall."""
    ahead = (NOW + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M")
    d = where.declared(block(state="WORKING", updated=ahead))
    assert where.liveness(d, NOW)[0] == "WORKING"


def test_the_real_repo_still_parses():
    """Every live COORDINATOR-STATE block in the repo must survive this."""
    seen = 0
    for p in list(COORD.parent.glob("*/HANDOFF.md")) + \
            [COORD.parent / "BRIEF.md"]:
        if not p.exists():
            continue
        d = where.declared(p.read_text(encoding="utf-8", errors="replace"))
        if d:
            seen += 1
            state, why = where.liveness(d)
            assert state in ("WORKING", "DONE", "BLOCKED", "STALLED", "UNKNOWN")
            assert why
    assert seen >= 3, f"expected several real state blocks, found {seen}"


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  ok    {name}")
        except AssertionError as exc:
            failures += 1
            print(f"  FAIL  {name}: {exc}")
    print("\nall good" if not failures else f"\n{failures} FAILED")
    raise SystemExit(1 if failures else 0)
