"""Build decision-time panels for the non-BTC ladder series, sequentially.

Sequential on purpose: other sessions share this API and parallel pulls have
already halved throughput once. One series at a time, paced.

KXETHD / KXSOLD / KXXRPD are the `greater` above/below ladders, the direct
analogues of KXBTCD which produced the BTC hold-to-settlement result.
"""
import subprocess
import sys
import time

PY = r"C:\Users\gianf\AppData\Local\Programs\Python\Python312\python.exe"
SCRIPT = r"C:\Users\gianf\crypto\src\build_panel.py"

SERIES = ["KXETHD", "KXSOLD", "KXXRPD"]

for s in SERIES:
    t0 = time.time()
    print(f"\n=== building panel for {s} ===", flush=True)
    r = subprocess.run(
        [PY, "-u", "-W", "ignore", SCRIPT, "--series", s,
         "--events", "150", "--strikes", "6"],
        capture_output=True, text=True)
    for line in (r.stdout or "").splitlines()[-6:]:
        print("   " + line, flush=True)
    if r.returncode != 0:
        print(f"   ** {s} exited {r.returncode}", flush=True)
        for line in (r.stderr or "").splitlines()[-6:]:
            print("   ERR " + line, flush=True)
    print(f"=== {s} done in {time.time()-t0:.0f}s ===", flush=True)
print("\nALL PANELS DONE", flush=True)
