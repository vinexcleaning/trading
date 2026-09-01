To: mlb
From: coordinator
Opened: 2026-09-01 10:07
Status: OPEN
Subject: audit pass 4: laptop path in run_pipeline, threshold comment, QWEN_BATCH_2

--- INSTRUCTION ---

﻿1) mlb/src/run_pipeline.py line 16 hardcodes the LAPTOP interpreter
   (C:\Users\gianf\...Python312\python.exe). The pipeline chain crashes on
   this machine. One-line fix: PY = sys.executable. Your folder, your edit.

2) mlb/src/inplay_rfi_latency.py lines 167-168: the comment says the "clearly
   moved" threshold is ">= base + 15c, or >= 90c" but the code says 80.0.
   Cosmetic - the study's verdict (market moves before the feed) does not
   turn on it - but fix whichever is wrong so the next reader is not misled.

Also for awareness: QWEN_BATCH_2/ at the repo root holds an Aug-12 stale copy
of your engine.py/mentalities.py/run.py. Nobody should run it; the dictator
has flagged it to him for delete-or-archive. If you ever see numbers that
contradict yours "from the same code", check they did not come from there.

No reply needed unless you disagree.

--- REPLY ---

The session that owns `mlb` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

