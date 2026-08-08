"""Canaries for the two things the upgrade added, and for the ways they lie.

Every check here exists because of a specific way this code could be
confidently wrong in front of a non-engineer. A table that is wrong is worse
than no table, because he acts on it.

Run:  py -3 coordinator\\tests\\test_where_and_runners.py
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

COORD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(COORD))

import runners as R          # noqa: E402
import where as W            # noqa: E402
import newprompt as N        # noqa: E402


FAILURES: list[str] = []


def ok(cond, msg: str) -> None:
    if cond:
        print(f"  ok   {msg}")
    else:
        print(f"  FAIL {msg}")
        FAILURES.append(msg)


# --------------------------------------------------------------------------
def test_pid_probe_does_not_kill() -> None:
    """os.kill(pid, 0) on Windows calls TerminateProcess.

    If anyone ever swaps the ctypes probe back for os.kill, this module would
    kill the very runner it is reporting on -- silently, and only on the
    machine that matters. Grep for it rather than trust the comment.
    """
    src = (COORD / "runners.py").read_text(encoding="utf-8")
    code = "\n".join(l for l in src.splitlines()
                     if not l.strip().startswith(("#", '"', "'")))
    ok("os.kill" not in code.replace("os.kill(pid, 0)   # POSIX", "")
       or "sys.platform != \"win32\"" in code,
       "the process probe never reaches os.kill on Windows")


def test_pid_probe_answers_sensibly() -> None:
    import os
    ok(R.pid_alive(os.getpid()) is True, "this very process reads as alive")
    # 0x7FFFFFF0 is inside the valid pid range and will not be in use.
    ok(R.pid_alive(0x7FFFFFF0) in (False, None),
       "a pid that does not exist does not read as alive")


def test_four_states_not_two() -> None:
    """A finished one-shot job must not be reported as a failure.

    crypto's tape pull completed cleanly and a two-state check would have
    shouted STALE at it on every run forever. A check that cries wolf gets
    ignored -- decision D8.
    """
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "logs").mkdir()
        log = root / "logs" / "job.log"
        log.write_text("working\nworking\n== DONE\n", encoding="utf-8")
        old = time.time() - 60 * 60 * 24
        import os
        os.utime(log, (old, old))

        real_repo, R.REPO = R.REPO, root
        try:
            entry = {"id": "x", "kind": "one-shot", "machine": "desktop",
                     "heartbeat": ["logs/job.log"], "done_marker": "== DONE",
                     "stale_after_minutes": 30}
            ok(R.check(entry)["state"] == R.FINISHED,
               "a one-shot job whose log says DONE reads FINISHED, not STALE")

            entry["kind"] = "continuous"
            entry.pop("done_marker")
            ok(R.check(entry)["state"] == R.STALE,
               "a continuous job quiet for a day reads STALE")

            fresh = time.time()
            os.utime(log, (fresh, fresh))
            ok(R.check(entry)["state"] == R.ALIVE,
               "a continuous job that just wrote reads ALIVE")

            entry["heartbeat"] = ["logs/nothing-here.log"]
            ok(R.check(entry)["state"] == R.NEVER,
               "a job with no log at all reads NEVER RUN")
        finally:
            R.REPO = real_repo


def test_laptop_is_never_called_dead() -> None:
    entry = {"id": "y", "kind": "continuous", "machine": "laptop",
             "heartbeat": [], "stale_after_minutes": 5}
    r = R.check(entry)
    ok(r["state"] == R.UNSEEN,
       "a laptop runner reads 'can't see from this machine', never STALE")
    ok(r["needs_a_human"] is False,
       "an unobservable runner does not raise an alarm it cannot justify")


def test_registry_is_loadable_and_complete() -> None:
    data = json.loads((COORD / "runners.json").read_text(encoding="utf-8"))
    entries = data.get("runners", [])
    ok(bool(entries), "runners.json parses and holds at least one runner")
    for e in entries:
        for key in ("id", "workstream", "title", "plain_english", "kind",
                    "machine", "stale_after_minutes", "restart"):
            ok(key in e, f"runner '{e.get('id', '?')}' declares '{key}'")
        ok(e["kind"] in ("continuous", "one-shot"),
           f"runner '{e['id']}' has a known kind")
        ok(e["machine"] in ("desktop", "laptop"),
           f"runner '{e['id']}' names a machine we can reason about")
        if e["kind"] == "one-shot":
            ok(bool(e.get("done_marker")),
               f"one-shot runner '{e['id']}' says how it announces finishing "
               f"-- without that it can only ever read STALE")


def test_every_runner_belongs_to_a_real_workstream() -> None:
    import scan
    data = json.loads((COORD / "runners.json").read_text(encoding="utf-8"))
    for e in data.get("runners", []):
        ok(e["workstream"] in scan.WORKSTREAMS,
           f"runner '{e['id']}' is attached to a workstream that exists "
           f"(otherwise it appears in no row of the table)")


def test_guessed_cells_are_marked() -> None:
    """A guess presented as a quote is the failure this whole design guards."""
    doc = ("# HANDOFF — thing\n\n## State: doing the thing\n\n"
           "## Next actions, in order\n\n1. Finish the thing.\n")
    ok(W.guess_doing(doc).startswith("doing the thing"),
       "a '## State:' heading is read as 'doing now'")
    ok("Finish the thing" in W.guess_left(doc),
       "a '## Next actions' heading is read as 'what's left'")

    declared = ("<!-- COORDINATOR-STATE\ndoing: A\nleft: B\nneeds: yes - pay for data\n-->")
    d = W.declared(declared)
    ok(d == {"doing": "A", "left": "B", "needs": "yes - pay for data"},
       "a declared block is parsed exactly, including the needs question")
    ok(W.declared("no block here") == {},
       "a document with no block declares nothing rather than guessing")


def test_left_heading_does_not_over_match() -> None:
    """`next` on its own matched 'what the next session should do'.

    That put a sentence about reading order into the 'what's left' column of
    the page the user acts on.
    """
    doc = ("# HANDOFF\n\n## 0. READ FIRST — two things that change what the "
           "next session should do\n\nSomething about reading order.\n")
    ok(W.guess_left(doc) == "",
       "'the next session' is not mistaken for 'the next action'")


def test_workstream_order_beats_file_timestamp() -> None:
    """Ordering HANDOFFs by mtime described the wrong project.

    The tennis row quoted kalshi-tennis, an old analysis folder, instead of
    tennis-paper-forward, the thing actually running.
    """
    import scan
    for slug in scan.WORKSTREAMS:
        found = [f for _, f, _ in W.handoffs(slug)]
        if len(found) < 2:
            continue
        first_listed = [f for f in scan.WORKSTREAMS[slug]["folders"]
                        if f in found]
        ok(found[0] == first_listed[0],
           f"{slug} is described by {first_listed[0]}, its primary folder")


def test_prompt_generator_copies_the_idea_verbatim() -> None:
    """The coordinator does not get an opinion on the trading work."""
    idea = ("test de-vig against a RETAIL book, not Pinnacle -- "
            "weird phrasing kept on purpose")
    text = N.build(idea, "T", "devig", "bot-hunt")
    ok(idea.splitlines()[0] in text,
       "the idea appears in the prompt exactly as it was given")
    ok("was not paraphrased" in text or "not paraphrased" in text,
       "the prompt says out loud that the idea was not judged")
    ok("not evidence the idea is new" in text,
       "the keyword cross-check states its own limit next to its results")


def test_prompt_generator_writes_only_inside_coordinator() -> None:
    src = (COORD / "newprompt.py").read_text(encoding="utf-8")
    ok("OUT = HERE / \"prompts\"" in src,
       "generated prompts land inside coordinator/, not the repo root")
    ok("INBOX" in src and "does not write" in src,
       "it prints the INBOX.md line rather than writing outside its folder")


def test_the_docs_state_the_limits_before_the_features() -> None:
    """If the limits section is ever dropped, the tool starts overclaiming."""
    # Whitespace is collapsed first: this prose is hard-wrapped at 79 columns,
    # so any phrase long enough to be worth asserting on spans a line break.
    import re as _re
    doc = _re.sub(r"\s+", " ",
                  (COORD / "COORDINATOR.md").read_text(encoding="utf-8"))
    for phrase in [
        "ALIVE",
        "It cannot restart anything",
        "cannot know what a session is doing",
        "A guess is labelled and never presented as a fact",
        "can't see from this machine",
        "cannot tell you whether the idea is any good",
    ]:
        ok(phrase in doc,
           f"COORDINATOR.md still states the limit: '{phrase[:44]}'")


def main() -> int:
    for fn in sorted(
        (v for k, v in globals().items() if k.startswith("test_")),
        key=lambda f: f.__code__.co_firstlineno,
    ):
        print(f"\n{fn.__name__}")
        fn()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} failure(s).")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    raise SystemExit(main())
