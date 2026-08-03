"""PHASE 0 -- verify the premises. Runs everything that can be run, reports what
cannot, and stops. Builds nothing downstream.

    .venv\\Scripts\\python.exe src\\phase0.py
"""

import json
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import channels  # noqa: E402
import quota  # noqa: E402
import transcripts  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "phase0_findings.json"

# (name as given in the prompt, search query that actually resolves it).
# Three of the four names were wrong. Searching the bare prompt name for
# 'Nate Tokens' resolves to the wrong person entirely (Nate B Jones, 309k subs),
# so that one needs topic context in the query to disambiguate.
CREATORS = [
    ("Nate Tokens", "Nates Tokens polymarket"),
    ("MindMathMoney", "MindMathMoney"),
    ("Trading with DavidTech", "Trading with DaviddTech"),
    ("Patrick Dang", "Patrick Dang"),
]

# Three arbitrary on-topic videos, discovered keylessly so the test uses real
# material rather than a hand-picked video known to have captions.
PROBE_QUERY = "how to build a trading bot"


def hr(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def check_api_key():
    hr("PREMISE 2 -- YouTube Data API key")
    from dotenv import load_dotenv

    for candidate in (ROOT / ".env", ROOT.parent / ".env", Path.home() / ".env"):
        if candidate.exists():
            load_dotenv(candidate)
            print(f"  loaded {candidate}")
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        print("  VERDICT: FAIL -- YOUTUBE_API_KEY is not set and no .env supplies it.")
        return {"present": False, "valid": None}
    print(f"  key present (len={len(key)}, ...{key[-4:]})")
    con = quota.connect()
    try:
        quota.charge(con, "videos.list", phase="phase0", detail="key validity probe")
        from googleapiclient.discovery import build

        yt = build("youtube", "v3", developerKey=key, cache_discovery=False)
        resp = yt.videos().list(part="id", id="dQw4w9WgXcQ").execute()
        ok = bool(resp.get("items"))
        print(f"  VERDICT: {'PASS' if ok else 'FAIL'} -- videos.list returned "
              f"{len(resp.get('items', []))} item(s), 1 unit charged")
        return {"present": True, "valid": ok}
    except Exception as exc:  # noqa: BLE001
        print(f"  VERDICT: FAIL -- {type(exc).__name__}: {str(exc)[:200]}")
        return {"present": True, "valid": False, "error": str(exc)[:300]}
    finally:
        con.close()


def check_transcripts():
    hr("PREMISE 1 -- transcript fetching from this machine")
    print(f"  discovering probe videos keylessly: ytsearch3:{PROBE_QUERY!r}")
    try:
        hits = channels.search_videos(PROBE_QUERY, n=3)
    except Exception as exc:  # noqa: BLE001
        print(f"  FAIL -- keyless search itself failed: {type(exc).__name__}: {exc}")
        return {"searched": False, "error": str(exc)[:300]}

    results = []
    for h in hits:
        print(f"\n  --- {h['video_id']}  {h['channel']} -- {(h['title'] or '')[:52]}")
        r = transcripts.fetch(h["video_id"])
        for path, outcome in r["paths"].items():
            if outcome["ok"]:
                print(f"      {path:<24} OK   {outcome['n_snippets']:>5} snippets, "
                      f"{outcome['n_words']:>6} words, generated={outcome['generated']}")
            else:
                print(f"      {path:<24} FAIL {outcome['error_class']}: {outcome['error'][:90]}")
        if r["snippets"]:
            head = " ".join(s["text"] for s in r["snippets"][:6])[:150]
            print(f"      first words: {head!r}")
        results.append(
            {
                "video_id": h["video_id"],
                "channel": h["channel"],
                "title": h["title"],
                "paths": r["paths"],
                "via": r["via"],
                "n_words": len(" ".join(s["text"] for s in r["snippets"]).split())
                if r["snippets"]
                else 0,
            }
        )

    n = len(results)
    any_ok = sum(1 for r in results if r["via"])
    a_ok = sum(1 for r in results if r["paths"].get("youtube-transcript-api", {}).get("ok"))
    b_ok = sum(1 for r in results if r["paths"].get("yt-dlp", {}).get("ok"))
    print(f"\n  success rate: any path {any_ok}/{n} | "
          f"youtube-transcript-api {a_ok}/{n} | yt-dlp {b_ok}/{n}")
    print(f"  VERDICT: {'PASS' if any_ok == n else ('PARTIAL' if any_ok else 'FAIL')}")
    return {"searched": True, "n": n, "any_ok": any_ok, "api_ok": a_ok,
            "ytdlp_ok": b_ok, "videos": results}


def check_channels():
    hr("PREMISE 3 -- the four creator names resolve to real channels")
    out = []
    for prompt_name, query in CREATORS:
        note = "" if query == prompt_name else f"  (prompt name corrected to {query!r})"
        print(f"\n  --- {prompt_name!r}{note}")
        try:
            res = channels.resolve_by_search(query)
        except Exception as exc:  # noqa: BLE001
            print(f"      RESOLVE FAILED {type(exc).__name__}: {str(exc)[:120]}")
            out.append({"prompt_name": prompt_name, "query": query,
                        "resolved": False, "error": str(exc)[:200]})
            continue
        if not res:
            print("      NOT RESOLVED -- no channel in the top hits")
            out.append({"prompt_name": prompt_name, "query": query, "resolved": False})
            continue
        res["prompt_name"] = prompt_name
        res["name_matches_prompt"] = (
            res["resolved_name"].strip().lower() == prompt_name.strip().lower()
        )
        flag = "" if res["name_matches_prompt"] else "   <-- NAME DIFFERS FROM PROMPT"
        print(f"      channel_id : {res['channel_id']}")
        print(f"      actual name: {res['resolved_name']!r}{flag}")
        print(f"      confidence : {res['hits_in_top']}/{res['probe_size']} top hits, "
              f"best rank {res['best_rank']}")
        try:
            st = channels.channel_stats(res["channel_id"])
        except Exception as exc:  # noqa: BLE001
            print(f"      STATS FAILED {type(exc).__name__}: {str(exc)[:120]}")
            out.append({**res, "resolved": True, "stats_error": str(exc)[:200]})
            continue
        floor = "+" if st["upload_count_is_floor"] else ""
        print(f"      subscribers: {st['subscribers']:,}" if st["subscribers"] is not None
              else "      subscribers: unknown")
        print(f"      uploads    : {st['upload_count']}{floor}")
        print(f"      views      : median {st['median_views']:,} "
              f"(min {st['min_views']:,} / max {st['max_views']:,}, "
              f"n={st['videos_with_view_data']})" if st["median_views"] is not None
              else "      views      : unknown")
        out.append({**res, "resolved": True, "stats": st})
    return out


def main():
    print("PHASE 0 -- premise verification")
    print(f"project root: {ROOT}")

    findings = {}
    findings["api_key"] = check_api_key()
    try:
        findings["transcripts"] = check_transcripts()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        findings["transcripts"] = {"crashed": True}
    try:
        findings["channels"] = check_channels()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        findings["channels"] = {"crashed": True}

    hr("PREMISE 4 -- quota ledger")
    con = quota.connect()
    print(quota.report(con))
    con.close()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(findings, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
