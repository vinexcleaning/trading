r"""
t5_itf_probe.py - settle the one open question in this project.

THE QUESTION
    A prior session closed the ITF thread on "no free ITF data source exists".
    livetennisapi.com advertises ATP + WTA + Challenger + ITF and offers a free
    tier. Whether the FREE tier actually returns ITF is UNVERIFIED - the site
    never says so. Its stated free-tier limits are capability-based (no odds, no
    model, no WebSocket) and rate-based (30/min, 1,000/day), with no tour
    restriction stated anywhere. That is an inference, not a claim, and this
    script is what turns it into a measurement.

WHAT IS ALREADY ESTABLISHED WITHOUT A KEY (2026-08-05, this machine)
    GET /api/public/v1/health              -> 200 {"status":"ok","version":"v1"}
    GET /api/public/v1/matches?status=live -> 401 {"error":"unauthorized"}
    GET /api/public/v1/tournaments         -> 401
    GET /api/public/v1/players             -> 401
    GET /api/public/v1/fixtures            -> 401
    GET /api/public/v1/usage               -> 401
    GET /api/public/v1/  and /docs         -> 404

    401 (not 404) is the useful part: those routes EXIST and only want a key.
    The paths below are therefore verified, not guessed.

USAGE
    set the key in the environment, then run. The key is never written to disk
    and never printed - only its length and prefix, so a screenshot is safe.

        $env:LIVETENNIS_API_KEY="twjp_..."
        .venv\Scripts\python.exe src\t5_itf_probe.py

WHAT IT COSTS
    6 requests against a 30/min, 1,000/day free budget.

WHAT IT DOES NOT DO
    It does not create an account, and it does not sign up for anything. The key
    must already exist. It makes GET requests only.

READ THE VERDICT IN CONTEXT
    Even a clean PASS reopens *data availability* only. Task 3 (VERDICT.md,
    ledger B009) measured ITF as the WORST tier of any at -9.13c per trade,
    t = -26, on 6,135 trades. A free ITF feed does not reopen the trade.
"""
from __future__ import annotations
import json, os, sys, time, collections

import requests

BASE = "https://api.livetennisapi.com/api/public/v1"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
UA = {"User-Agent": "bot-forensics/1.0 (research; contact via repo)"}

# every string that would indicate an ITF-level event, lowercased
ITF_MARKERS = ("itf", "futures", "w15", "w25", "w35", "w50", "w75", "w100",
               "m15", "m25")


def _get(path: str, key: str, header: str, params: dict | None = None):
    """One GET. Returns (status, json_or_text). Never raises on HTTP status."""
    if header == "bearer":
        h = {"Authorization": f"bearer {key}"}
    else:
        h = {"X-API-Key": key}
    h.update(UA)
    try:
        r = requests.get(f"{BASE}{path}", headers=h, params=params, timeout=25)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, r.text[:400]


def _walk_strings(obj, depth=0):
    """Yield every string anywhere in a nested structure."""
    if depth > 6:
        return
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v, depth + 1)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _walk_strings(v, depth + 1)


def looks_itf(record) -> bool:
    """True if anything in this record names an ITF-level event.

    Deliberately broad: the tour field name is undocumented, so rather than
    guess it, scan every string in the record. A false positive is visible in
    the printed sample; a false negative would silently answer the question
    wrong in the direction that closes the thread.
    """
    for s in _walk_strings(record):
        low = s.lower()
        if any(m in low for m in ITF_MARKERS):
            return True
    return False


def tour_of(record) -> str:
    """Best-effort tour label, trying the plausible field names in order."""
    if isinstance(record, dict):
        for k in ("tour", "level", "category", "circuit", "tour_level",
                  "competition", "series"):
            v = record.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        t = record.get("tournament")
        if isinstance(t, dict):
            for k in ("tour", "level", "category", "name"):
                v = t.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
        if isinstance(t, str) and t.strip():
            return t.strip()
    return "?"


def unwrap(payload):
    """Return the list of records from whatever envelope the API uses."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for k in ("data", "matches", "tournaments", "results", "items"):
            v = payload.get(k)
            if isinstance(v, list):
                return v
    return []


def main() -> int:
    key = os.environ.get("LIVETENNIS_API_KEY", "").strip()
    if not key:
        print("LIVETENNIS_API_KEY is not set.\n")
        print("  PowerShell:  $env:LIVETENNIS_API_KEY=\"twjp_...\"")
        print("  bash:        export LIVETENNIS_API_KEY=twjp_...")
        print("\nGet a free key at https://livetennisapi.com/subscribe/free")
        print("(email only - no password, no card). I do not create accounts.")
        return 2

    print(f"key present: {len(key)} chars, prefix {key[:5]!r}  "
          f"(the key itself is never printed or written to disk)")

    # ---- 1. which auth header does this key want? ------------------------
    header = None
    for cand in ("bearer", "x-api-key"):
        st, body = _get("/usage", key, cand)
        print(f"  auth probe {cand:9s} /usage -> {st}")
        if st == 200:
            header = cand
            print(f"  usage: {json.dumps(body)[:300]}")
            break
    if header is None:
        print("\nFAIL: the key was rejected by both header formats.")
        print("Check it was pasted whole and has not expired.")
        return 1
    print(f"-> using {header}\n")

    report = {"auth_header": header, "checked": {}}

    # ---- 2. the actual question -----------------------------------------
    for label, path, params in (
            ("tournaments", "/tournaments", None),
            ("live matches", "/matches", {"status": "live"}),
            ("fixtures", "/fixtures", None)):
        time.sleep(2.5)                      # 30/min budget, stay well under
        st, body = _get(path, key, header, params)
        if st != 200:
            print(f"{label:14s} -> {st}  {str(body)[:200]}")
            report["checked"][label] = {"status": st, "n": 0, "itf": 0}
            continue

        recs = unwrap(body)
        itf = [r for r in recs if looks_itf(r)]
        tours = collections.Counter(tour_of(r) for r in recs)
        print(f"{label:14s} -> 200  {len(recs)} records, "
              f"**{len(itf)} look ITF**")
        if tours:
            top = ", ".join(f"{k}:{v}" for k, v in tours.most_common(12))
            print(f"{'':14s}    tours seen: {top}")
        for r in itf[:3]:
            print(f"{'':14s}    ITF sample: {json.dumps(r)[:220]}")
        report["checked"][label] = {"status": st, "n": len(recs),
                                    "itf": len(itf),
                                    "tours": dict(tours.most_common(20))}

    # ---- 3. the verdict --------------------------------------------------
    total_itf = sum(v.get("itf", 0) for v in report["checked"].values())
    total_n = sum(v.get("n", 0) for v in report["checked"].values())
    print("\n" + "=" * 74)
    if total_itf > 0:
        print(f"PASS - the FREE tier returned ITF data. "
              f"{total_itf} ITF records of {total_n}.")
        print("The prior session's 'no free ITF source exists' is now FALSE,")
        print("and ledger row B016 moves UNVERIFIED -> SETTLED.")
    elif total_n == 0:
        print("INCONCLUSIVE - the key authenticated but no records came back.")
        print("Most likely there is simply no play right now. Re-run during")
        print("European or American daytime before concluding anything.")
    else:
        print(f"FAIL - {total_n} records and NOT ONE looks ITF.")
        print("The free tier appears to be restricted by tour after all.")
        print("B016 stays UNVERIFIED and the ITF thread stays closed.")
    print("=" * 74)
    print("\nEither way this settles DATA AVAILABILITY ONLY. Ledger B009 says")
    print("ITF economics are the worst of any tier: -9.13c/trade, t = -26 on")
    print("6,135 trades. Nothing here reopens the trade.")

    os.makedirs(OUT, exist_ok=True)
    dest = os.path.join(OUT, "t5_itf_probe.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"\nwritten: {dest}  (no key in it - checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
