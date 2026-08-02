"""Part B, in order, with the pre-registered gates enforced in code.

The order matters and is fixed in PREREGISTRATION_PARTB.md §5:

  1. rebuild state on the corrected universe
  2. re-run the selection-guard table on CLEAN data, report what moved
  3. mirrored-consistency gate -- pass or stop
  4. only then read a calibration number
  5. validation
  6. maker execution, which is a cost question and runs either way

Step 3 exits the whole script on failure. That is deliberate: in Phase 2 the
equivalent check existed as a footnote and four phases were built before anyone
ran it.
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PY = sys.executable


def run(script, *args, must=True, tee=None):
    print(f"\n{'=' * 78}\n$ {script} {' '.join(args)}\n{'=' * 78}", flush=True)
    r = subprocess.run([PY, str(SRC / script), *args], cwd=str(SRC))
    if r.returncode and must:
        sys.exit(f"\n*** {script} exited {r.returncode} -- stopping ***")
    return r.returncode


def main():
    # 1 -----------------------------------------------------------------
    run("p1_state.py", "--subdir", "candles_ohlc", "--out", "paths")

    # 2 -----------------------------------------------------------------
    run("audit_a3.py", "--tag", "paths", "--out", "audit_a3_clean.txt",
        "--label", "CLEAN universe (lexicographic dedupe)")

    # 3 -----------------------------------------------------------------
    rc = run("p5_gate3e.py", "--tag", "paths", must=False)
    if rc == 2:
        sys.exit("\n*** MIRRORED-CONSISTENCY GATE FAILED -- an "
                 "orientation-dependent discrepancy survives. Stopping before "
                 "any calibration number is read. See reports/p5_gate3e.md ***")
    if rc == 3:
        print("\n*** G2 failed while G1/G2b passed: the orientations agree, "
              "but the pre-match price is uniformly miscalibrated in the "
              "filtered subset. Continuing WITH THAT CAVEAT. ***", flush=True)
    elif rc:
        sys.exit(f"\n*** gate script errored ({rc}) ***")

    # 4 -----------------------------------------------------------------
    import ledger
    ledger.reset()
    run("p1_validate.py", must=False)
    run("p2_calib.py", "--tag", "paths", "--out", "p2_base_clean.txt", "--grid")
    run("p2_fade.py", must=False)

    # 5 -----------------------------------------------------------------
    run("p4_validate.py", "--tag", "paths", must=False)

    # 6 -----------------------------------------------------------------
    run("p5_task1b.py", "--tag", "paths", must=False)

    ledger.finalise(q=0.10)
    print("\nPart B complete")


if __name__ == "__main__":
    sys.path.insert(0, str(SRC))
    main()
