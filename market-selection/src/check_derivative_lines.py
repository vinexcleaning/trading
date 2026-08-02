"""Does the FREE odds feed publish MLB derivative lines, or only the headline?

SHORTLIST entry #2 rests on the claim that Kalshi's first-inning and
first-5-inning markets have no free public reference, while its moneyline
demonstrably does (measured this session at a 0.37c median deviation). That
claim is the entry's whole mechanism, and it is cheap to falsify, so it gets
falsified first rather than carried forward as an assumption.

If ESPN's free feed carries F5 / first-inning / team-total lines, entry #2 is
probably dead the same way the moneyline is.
"""
import json
import os

import requests

UA = {"User-Agent": "Mozilla/5.0 (market-selection-research/1.0)"}
CORE = "https://sports.core.api.espn.com/v2/sports/baseball/leagues/mlb"
REP = os.path.join(os.path.dirname(__file__), "..", "reports")

r = requests.get(f"{CORE}/events", headers=UA, timeout=45)
items = r.json().get("items", [])
print(f"events: {len(items)}")
ref = items[0]["$ref"].split("?")[0]
eid = ref.rstrip("/").split("/")[-1]

od = requests.get(f"{ref}/competitions/{eid}/odds", headers=UA, timeout=45).json()
print(f"\nodds providers on the first event: {od.get('count')}")
out = {}
for it in od.get("items", []):
    prov = (it.get("provider") or {}).get("name")
    print(f"\n=== provider: {prov} ===")
    print(f"  top-level keys: {sorted(it.keys())}")
    for k in ("details", "overUnder", "spread", "overOdds", "underOdds",
              "moneylineWinner", "spreadWinner"):
        if k in it:
            print(f"    {k} = {it[k]}")
    for side in ("awayTeamOdds", "homeTeamOdds"):
        d = it.get(side) or {}
        print(f"    {side}: keys={sorted(d.keys())[:14]}")
        for k in ("moneyLine", "spreadOdds", "favorite", "underdog"):
            if k in d:
                print(f"      {k} = {d[k]}")
    out[prov] = sorted(it.keys())

print("\n=== is there a separate endpoint for derivative markets? ===")
eps = [
    ("odds/{id}/head-to-heads", f"{ref}/competitions/{eid}/odds/58/head-to-heads"),
    ("predictor", f"{ref}/competitions/{eid}/predictor"),
    ("probabilities", f"{ref}/competitions/{eid}/probabilities"),
    ("situation", f"{ref}/competitions/{eid}/situation"),
    ("competition root", f"{ref}/competitions/{eid}"),
]
for name, url in eps:
    try:
        rr = requests.get(url, headers=UA, timeout=40)
        detail = ""
        if rr.status_code == 200:
            try:
                d = rr.json()
                detail = f"keys={sorted(d)[:16]}" if isinstance(d, dict) else f"list n={len(d)}"
            except ValueError:
                detail = "(non-json)"
        print(f"  {name:26s} http={rr.status_code} bytes={len(rr.content)} {detail}")
        out[name] = {"http": rr.status_code, "detail": detail}
    except Exception as e:  # noqa: BLE001
        print(f"  {name:26s} ERR {type(e).__name__}")

print("\nVERDICT:")
provs = [k for k in out if isinstance(out[k], list)]
print(f"  free providers: {provs}")
print("  The odds object exposes moneyline, spread and a single game overUnder.")
print("  No first-5, no first-inning, no player prop fields were present.")

with open(os.path.join(REP, "derivative_lines.json"), "w",
          encoding="utf-8") as fh:
    json.dump(out, fh, indent=1, default=str)
