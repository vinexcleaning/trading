"""The disallowed-route transcript collection stays stopped.

**A user decision, 2026-08-14:** *"stop pulling from the address YouTube's own
rules disallow. Keep the 1,135 transcripts already collected and keep the 484
findings that rest on them, but do not collect more that way."*

**Why a test and not a comment.** This repo already learned that paper-only is
enforced by a test rather than a promise -- `tennis-paper-forward` and
`mlb-paper` both walk their own source and fail if order-shaped code appears.
The same reasoning applies here: a policy that lives only in a docstring is one
absent-minded edit from being undone, and the person who undoes it will not know
it was ever a decision.

**What this does NOT do:** it does not delete or invalidate anything already
collected. 1,135 transcripts and the 484 claims drawn from them stand. Only
future collection through the disallowed endpoints is blocked.

    py -3 -m pytest tests/test_no_disallowed_route.py -q
"""
import os
import sys

import pytest

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "src")
sys.path.insert(0, SRC)

import transcripts  # noqa: E402


def test_switch_is_off():
    """The one switch that re-enables collection must stay off."""
    assert transcripts._ALLOW_DISALLOWED_ROUTE is False, (
        "Transcript collection through YouTube's disallowed endpoints was "
        "stopped by the user on 2026-08-14. If that decision has genuinely "
        "changed, update the module docstring and this test together -- "
        "flipping the flag alone hides a policy change inside a diff.")


def test_fetch_refuses():
    with pytest.raises(transcripts.CollectionStopped):
        transcripts.fetch("dQw4w9WgXcQ")


@pytest.mark.parametrize("fn", ["fetch_via_api", "fetch_via_ytdlp"])
def test_each_path_refuses_directly(fn):
    """Both paths, not just the wrapper -- either is individually callable."""
    with pytest.raises(transcripts.CollectionStopped):
        getattr(transcripts, fn)("dQw4w9WgXcQ")


def test_no_reachable_caller_bypasses_the_wrapper():
    """No REACHABLE code may call the underlying transcript paths directly.

    `fetch()` is the guarded door. A module that imports `fetch_via_api` and
    calls it itself routes around the decision -- which is exactly how this kind
    of rule usually dies, and exactly what the first run of this test found in
    `retrieval.py`.

    **Reachability is decided on the syntax tree, not on line matching.**
    Quarantined originals are kept deliberately -- named `*_disabled`, never
    called -- so the decision can be reversed by a person rather than by
    someone re-deriving a fetcher months from now. Those bodies contain the
    calls by design. A grep cannot tell them apart from a live bypass; the
    enclosing function name can.
    """
    import ast

    offenders, quarantined = [], []
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".py") or fn == "transcripts.py":
            continue
        path = os.path.join(SRC, fn)
        tree = ast.parse(open(path, encoding="utf-8-sig").read())
        # map every node to its enclosing function name
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for call in [n for n in ast.walk(node) if isinstance(n, ast.Call)]:
                name = getattr(call.func, "attr", None) or getattr(
                    call.func, "id", None)
                if name not in ("fetch_via_api", "fetch_via_ytdlp",
                                "_fetch_disabled"):
                    continue
                where = f"{fn}:{call.lineno} {node.name}() calls {name}"
                (quarantined if node.name.endswith("_disabled")
                 else offenders).append(where)

    assert not offenders, (
        "these are REACHABLE and route around the stop: "
        + "; ".join(offenders))
    # the quarantined bodies must stay quarantined, not silently disappear
    assert quarantined, (
        "expected the quarantined original to still exist -- if it was deleted "
        "on purpose, delete this assertion too and say so")


def test_quarantined_originals_are_never_called():
    """Nothing calls the `*_disabled` bodies either."""
    import ast

    called = []
    for fn in sorted(os.listdir(SRC)):
        if not fn.endswith(".py"):
            continue
        tree = ast.parse(open(os.path.join(SRC, fn), encoding="utf-8-sig").read())
        for call in [n for n in ast.walk(tree) if isinstance(n, ast.Call)]:
            name = getattr(call.func, "attr", None) or getattr(
                call.func, "id", None)
            if name and name.endswith("_disabled"):
                called.append(f"{fn}:{call.lineno} calls {name}")
    assert not called, "quarantined code is being called: " + "; ".join(called)
