"""PREREGISTRATION_PROPS.md section 3a: WHEN is the sharp prop reference actually live?

This is the free kill-test and it runs before anything is priced.

WHY IT EXISTS. Pinnacle's free feed carried 62 two-sided player props on
2026-08-14 at 06:20Z and ZERO on 2026-08-18 at 04:30Z -- same endpoint, control
passing (1.13 MB, 290 matchups, 23 MLB games). So the reference is intermittent,
and the likeliest reason is that pitcher props are posted close to first pitch.

THE KILL CONDITION, WRITTEN BEFORE THE ANSWER EXISTS: if props are live for
fewer than two hours before first pitch, then Kalshi's ladder -- quoted days
ahead -- and Pinnacle's line barely coexist, there is no window in which any
disagreement could be acted on, and P1 is over. That would end the idea on
apparatus, for free, before a single price is compared.

⚠ IT RECORDS ABSENCE ONLY WITH A CONTROL, per GUARDS #27. An empty prop list is
logged as EMPTY only when the same call returned a full payload of everything
else; otherwise it is logged as NO-ACCESS and says nothing about the board. The
two are the same bytes at the endpoint and this repo has manufactured three
false absences by not separating them.
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT.parent))
import venues as V  # noqa: E402

# ⚠ ADDED 2026-08-21: launched by the watchdog these inherit the Windows cp1252
# console default, and a print containing a warning glyph then raises
# UnicodeEncodeError and kills the run. It cost one capture already.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

OUT = ROOT / "reports" / "prop_watch.jsonl"
PIN = "https://guest.api.arcadia.pinnacle.com/0.1/sports/3"


def sample():
    mus = V.get(f"{PIN}/matchups", pace=0.3, tries=2, timeout=30)
    mk = V.get(f"{PIN}/markets/straight", pace=0.3, tries=2, timeout=30)
    now = datetime.now(timezone.utc)
    # the CONTROL: this call must come back full, or nothing below means anything
    if mus is None or mus.status_code != 200 or len(mus.content) < 100_000:
        return {"ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "state": "NO-ACCESS",
                "http": None if mus is None else mus.status_code,
                "bytes": 0 if mus is None else len(mus.content)}
    rows = mus.json()
    props, kinds = {}, {}
    for m in rows:
        sp = m.get("special") or {}
        cat = (sp.get("category") or "").strip()
        if m.get("parentId"):
            kinds[cat or "derivative"] = kinds.get(cat or "derivative", 0) + 1
        if cat == "Player Props":
            mm = re.match(r"(.+?) Total (Strikeouts|Home Runs)",
                          sp.get("description") or "")
            if mm:
                props[m["id"]] = (mm.group(1).strip(), mm.group(2))
    priced, lines = 0, []
    if mk is not None and mk.status_code == 200:
        for m in mk.json():
            if m.get("matchupId") in props:
                pr = [p for p in (m.get("prices") or []) if p.get("price") is not None]
                if len(pr) >= 2:
                    priced += 1
                    pts = {p.get("points") for p in pr if p.get("points") is not None}
                    nm, kind = props[m["matchupId"]]
                    lines.append({"player": nm, "kind": kind, "line": sorted(pts)})
    # how long until the next game starts? that is the axis the kill test needs
    starts = []
    for m in rows:
        lg = m.get("league") or {}
        if (lg.get("name") if isinstance(lg, dict) else None) == "MLB" \
                and not m.get("parentId") and m.get("startTime"):
            try:
                starts.append(datetime.strptime(m["startTime"], "%Y-%m-%dT%H:%M:%SZ")
                              .replace(tzinfo=timezone.utc))
            except ValueError:
                pass
    nxt = min((s for s in starts if s > now), default=None)
    return {"ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "state": "PROPS" if props else "EMPTY",
            "prop_parents": len(props), "priced_markets": priced,
            "child_kinds": kinds, "mlb_games_listed": len(starts),
            "hours_to_next_first_pitch":
                None if nxt is None else round((nxt - now).total_seconds() / 3600, 2),
            "lines": lines[:40]}


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    every = 1200
    if "--every" in sys.argv:
        every = int(sys.argv[sys.argv.index("--every") + 1])
    hours = 48
    if "--hours" in sys.argv:
        hours = float(sys.argv[sys.argv.index("--hours") + 1])
    end = time.time() + hours * 3600
    print(f"prop_watch: every {every}s for {hours}h -> {OUT}", flush=True)
    while time.time() < end:
        try:
            r = sample()
        except Exception as e:  # noqa: BLE001
            r = {"ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "state": "ERROR", "error": str(e)[:200]}
        with OUT.open("a", encoding="utf-8") as f:
            f.write(json.dumps(r) + "\n")
        print(f"  {r['ts']}  {r['state']:9} parents={r.get('prop_parents')} "
              f"priced={r.get('priced_markets')} "
              f"h_to_first_pitch={r.get('hours_to_next_first_pitch')}", flush=True)
        time.sleep(every)


if __name__ == "__main__":
    main()
