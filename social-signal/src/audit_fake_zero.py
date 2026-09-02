"""Can any extractor here report "nothing found" when it was actually refused?

**GUARDS #25, aimed straight at this folder.** The `reopen` audit put it
plainly: *"your folders are the ones that make absence claims for a living. If
any extractor here records 'no results' without recording the status code and a
second attempt, it can manufacture exactly this."*

**It was right, and this file exists because the first thing it found was mine.**
`find_extractors.py::search()` returned `[]` on a genuine empty result, on an
HTTP error, and on a network error — three different worlds, one return value.
Its entire purpose is answering *"does an extractor for X already exist?"*, which
is an absence question, and a GitHub 403 rate-limit refusal would have been
recorded as "no such tool exists".

**What this checks, statically.** For every `src/*.py`, find functions whose
`except` branch returns an empty container (`[]`, `{}`, `()`, `0`, `""`, `None`)
that is **the same shape** as their success return. Those are the places where a
refusal and a real zero are indistinguishable to the caller.

**What it deliberately does NOT do:** judge whether the code prints a warning.
Printing is not recording — a human reading a log later is not a data structure,
and every count in every report is built from the return value, not the log.

    python src/audit_fake_zero.py
"""
from __future__ import annotations

import ast
import os
import sys

# **All three folders this session owns, not just its own. Widened
# 2026-09-01.** The `reopen` audit found the fake-zero pattern alive in
# `extractor-upgrade/src/hn.py` and noted that this auditor could never have
# caught it, because it only ever scanned the folder it lives in. An auditor
# whose blind spot is "everywhere except here" is most of the way to useless.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
SRC_DIRS = [
    os.path.join(_ROOT, "social-signal", "src"),
    os.path.join(_ROOT, "signal-github", "src"),
    os.path.join(_ROOT, "extractor-upgrade", "src"),
]
SRC = SRC_DIRS[0]          # kept: the report still names files relative to it
EMPTY = {"[]", "{}", "()", "0", "''", '""', "None", "set()", "0.0"}


def literal(node) -> str | None:
    """Render a returned expression if it is an empty-ish literal."""
    if node is None:
        return "None"
    if isinstance(node, ast.Constant):
        if node.value is None:
            return "None"
        if node.value in (0, "", 0.0, False):
            return repr(node.value)
        return None
    if isinstance(node, (ast.List, ast.Tuple)) and not node.elts:
        return "[]" if isinstance(node, ast.List) else "()"
    if isinstance(node, ast.Dict) and not node.keys:
        return "{}"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id in ("set", "list", "dict") and not node.args:
        return f"{node.func.id}()"
    return None


def main():
    findings = []
    targets = []
    for d in SRC_DIRS:
        if not os.path.isdir(d):
            print(f"  !! {d} is not a directory -- SKIPPED, and that is a gap")
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".py") and fn != os.path.basename(__file__):
                targets.append((os.path.relpath(d, _ROOT).replace("\\", "/")
                                + "/" + fn, os.path.join(d, fn)))
    print(f"scanning {len(targets)} files across "
          f"{len(SRC_DIRS)} folders")
    print("")
    for fn, path in targets:
        try:
            # **utf-8-sig, not utf-8.** The first run of this audit reported
            # "soccer_sources.py does not parse" because a byte-order mark
            # tripped ast.parse. Python's own import machinery strips it, so
            # the file was fine and the auditor was wrong — which is the same
            # class of mistake the audit exists to catch, one level up.
            tree = ast.parse(open(path, encoding="utf-8-sig").read())
        except SyntaxError as e:
            print(f"  !! {fn} does not parse: {e}")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            # empty returns inside except handlers
            bad = []
            for h in [n for n in ast.walk(node)
                      if isinstance(n, ast.ExceptHandler)]:
                for r in [n for n in ast.walk(h) if isinstance(n, ast.Return)]:
                    lit = literal(r.value)
                    if lit is not None:
                        bad.append((r.lineno, lit))
            if not bad:
                continue
            # what does the happy path return? if it is the same shape, the
            # caller cannot tell a refusal from a real empty result.
            handlers = {id(n) for h in [x for x in ast.walk(node)
                                        if isinstance(x, ast.ExceptHandler)]
                        for n in ast.walk(h)}
            ok_shapes = set()
            for r in [n for n in ast.walk(node) if isinstance(n, ast.Return)]:
                if id(r) in handlers:
                    continue
                lit = literal(r.value)
                ok_shapes.add(lit if lit else "VALUE")
            findings.append((fn, node.name, node.lineno, bad, ok_shapes))

    print(f"{len(findings)} function(s) return an empty value from an "
          f"except branch\n")
    worst = []
    for fn, name, ln, bad, ok in findings:
        # the dangerous case: happy path can also return a real value, so the
        # empty return is silently in the same channel
        danger = "VALUE" in ok or (ok & EMPTY)
        flag = "AMBIGUOUS" if danger else "ok-ish"
        if danger:
            worst.append((fn, name, ln))
        print(f"  [{flag:<9}] {fn}:{ln}  {name}()")
        print(f"      except returns: "
              f"{', '.join(f'{l}@{n}' for n, l in bad)}")
        print(f"      success returns: {sorted(ok) or '(falls off the end)'}")

    print(f"\n  {len(worst)} function(s) where a REFUSAL is indistinguishable "
          f"from a real empty result:")
    for fn, name, ln in worst:
        print(f"    {fn}:{ln}  {name}()")
    print("""
  The fix is not "log the error". Every count in every report is built from the
  RETURN VALUE, and a human reading a log later is not a data structure. Either
  raise, or return something the caller is forced to look at.""")


if __name__ == "__main__":
    main()
