"""Autonomous overnight chain: wait for the download, build, test, report.

Runs unattended. Each stage only starts if the previous one produced what it
was supposed to, and every stage writes its own log, so a fresh session can
read `mlb/reports/PIPELINE.txt` and see exactly how far it got and why it
stopped.
"""
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
# ⚠ The interpreter running THIS script, never a hardcoded path.
# This was a LAPTOP path until 2026-09-01 -- a recording box, not the machine
# any of this runs on -- so the whole pipeline chain crashed here on a path
# that does not exist. CLAUDE.md section 10: never write an absolute
# interpreter path into anything.
PY = sys.executable
LOG = os.path.join(ROOT, "reports", "PIPELINE.txt")


def log(m):
    line = f"[{datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S}] {m}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def run(script, stage):
    log(f"START {stage}: {script}")
    out = os.path.join(ROOT, "reports", f"{stage}.txt")
    with open(out, "w", encoding="utf-8") as fh:
        p = subprocess.run([PY, "-u", os.path.join(HERE, script)],
                           stdout=fh, stderr=subprocess.STDOUT, cwd=ROOT)
    log(f"END   {stage}: exit={p.returncode}  -> reports/{stage}.txt")
    return p.returncode == 0


def main():
    log("=" * 60)
    log("pipeline starting")

    # ---- stage 1: wait for the statcast download
    dl = os.path.join(ROOT, "data", "statcast_fetch.out")
    waited = 0
    while waited < 3600:
        if os.path.exists(dl):
            txt = open(dl, encoding="utf-8", errors="replace").read()
            if "\nDONE" in txt or txt.startswith("DONE"):
                log("statcast download reports DONE")
                break
        time.sleep(30)
        waited += 30
    else:
        log("statcast download did not finish in 60 min; continuing with "
            "whatever chunks exist")

    scdir = os.path.join(ROOT, "data", "statcast")
    n = len([f for f in os.listdir(scdir)
             if f.endswith(".csv")]) if os.path.isdir(scdir) else 0
    log(f"statcast chunks on disk: {n}")
    if n < 10:
        log("ABORT: too few statcast chunks to build features")
        return

    # ---- stage 2: features
    if not run("statcast_features.py", "stage2_sc_features"):
        log("ABORT: feature build failed")
        return
    f = os.path.join(ROOT, "data", "sc_features.jsonl")
    if not os.path.exists(f) or os.path.getsize(f) < 10000:
        log("ABORT: sc_features.jsonl missing or tiny")
        return

    # ---- stage 3: the gate
    run("model_rfi_v2.py", "stage3_gate_v2")

    # ---- stage 4: descriptive book work, which the archive CAN support
    run("../../market-selection/src/book_first_look.py", "stage4_book")

    log("pipeline complete")
    log("=" * 60)


if __name__ == "__main__":
    sys.exit(main())
