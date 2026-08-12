"""Does the User-Agent decide whether a source "exists"?

WHY THIS CHAT IS RUNNING IT. `soccer` measured (SO014) that one edge network
returns **403 to browser-shaped User-Agents and 200 to curl's**, and that every
ESPN script in its folder was therefore **dead rather than degraded**. Eleven
scripts in `market-selection/` and `mlb/` fetch the same host with the same
shape of User-Agent.

One of those scripts is `market-selection/src/check_tennis_live.py`, which
produced **M027 -- "No free data source covering ITF tennis was found"**, a
SETTLED absence claim that `B021` later refuted. It probes six sources with a
SINGLE User-Agent, and two of the six recorded failures are **403**.

**So the question is not "is M027 wrong" -- B021 settled that. It is whether a
method artifact manufactured it**, because if one header turns "blocked" into
"does not exist", every multi-source absence probe in this repo inherits it.

This measures it instead of inferring it: same URL, same minute, four headers.

Read-only. GET only. A handful of requests, paced. Writes inside reopen/ only.

  py -3 reopen\\src\\check_user_agent.py
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "reports"

PACE_SEC = 1.5
TIMEOUT = 30

# The four shapes that matter, named by who uses them in this repo.
AGENTS = {
    "market-selection style": "Mozilla/5.0 (market-selection-research/1.0)",
    "bare product token": "market-selection-research/1.0",
    "curl": "curl/8.4.0",
    "python-urllib default": None,        # send no User-Agent override
}

# The sources M027 recorded as failing, plus one ESPN endpoint that several
# other folders depend on. Nothing here is fetched for its content -- only the
# status code is used.
TARGETS = {
    "ESPN tennis scoreboard":
        "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard",
    "Sofascore live tennis":
        "https://api.sofascore.com/api/v1/sport/tennis/events/live",
    "ATP results archive":
        "https://www.atptour.com/en/scores/results-archive",
}


def probe(url: str, ua: str | None):
    req = urllib.request.Request(url)
    if ua is not None:
        req.add_header("User-Agent", ua)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, len(r.read(4096))
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:                                    # noqa: BLE001
        return f"ERR {type(e).__name__}", None


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict[str, object]] = {}

    for tname, url in TARGETS.items():
        print(f"\n{tname}")
        results[tname] = {"url": url, "by_agent": {}}
        for aname, ua in AGENTS.items():
            status, nbytes = probe(url, ua)
            results[tname]["by_agent"][aname] = {
                "user_agent": ua, "status": status, "first_bytes": nbytes}
            shown = "(none sent)" if ua is None else ua
            print(f"   {aname:24s} {str(status):>6}   {shown}")
            time.sleep(PACE_SEC)

    # The finding is a DISAGREEMENT between headers on the same URL.
    split = []
    for tname, row in results.items():
        codes = {a: d["status"] for a, d in row["by_agent"].items()}
        ok = [a for a, c in codes.items() if c == 200]
        bad = [a for a, c in codes.items() if c != 200]
        if ok and bad:
            split.append(tname)
            print(f"\n  ⚠ {tname}: the header decides it. "
                  f"200 for {ok}; {[codes[a] for a in bad]} for {bad}")

    print("\n" + "=" * 70)
    if split:
        print("HEADER-DEPENDENT on: " + ", ".join(split))
        print("On those hosts a probe that sends one User-Agent and records a "
              "failure as 'not found' is manufacturing an absence claim.")
    else:
        print("No disagreement found on these hosts today. That does NOT clear "
              "the method -- SO014 measured a real 403/200 split on ESPN, and "
              "a block can be intermittent, path-specific or since lifted.")

    path = OUT / "user_agent_check.json"
    path.write_text(json.dumps({
        "note": ("Same URL, same minute, four User-Agents. Status codes only; "
                 "no content was used."),
        "prompted_by": ["SO014 (soccer)", "M027 (market-selection)"],
        "results": results,
        "header_dependent": split,
    }, indent=2), encoding="utf-8")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
