"""Answer the questions a trader actually asks, instead of a generic quality score.

The S score says "is this repo substantial". That is not the question. The
questions are:

    Which venue is it really for?   (not what the README claims - what it imports)
    What KIND of thing is it?       live trader / backtester / data collector /
                                    scraper / market maker / arbitrage / copy
                                    trader / dashboard / library
    Does it actually place orders?  or only talk about it
    Is it alive?                    last push, and whether the client it imports
                                    is one of the ARCHIVED v1 Polymarket libs
    Does it model costs correctly?  joined from fee_audit.json

Everything here reads the cached archives. **Zero API calls and zero model
context** - it is pure local classification, which is the whole point: the
expensive step (reading) should only ever see repos this has already narrowed.

    python src/classify.py                          # classify everything, write report
    python src/classify.py --venue kalshi --kind market_maker
    python src/classify.py --venue polymarket --kind backtester --alive
    python src/classify.py --need tennis            # freeform: match source + README
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import gh  # noqa: E402

NOW = datetime.datetime.now(datetime.timezone.utc)

# --- venue: what it IMPORTS or CALLS, not what the README says ---------------
VENUE_SIG = {
    "kalshi": [
        r"api\.elections\.kalshi\.com", r"trading-api\.kalshi\.com",
        r"demo-api\.kalshi\.co", r"\bkalshi_python\b", r"\bKalshiHttpClient\b",
        r"\bKalshiClient\b", r"from\s+kalshi", r"import\s+kalshi",
    ],
    "polymarket": [
        r"clob\.polymarket\.com", r"gamma-api\.polymarket\.com",
        r"data-api\.polymarket\.com", r"\bpy_clob_client\b", r"\bClobClient\b",
        r"@polymarket/clob-client", r"\bnegRisk\b", r"\bConditionalTokens\b",
    ],
}

# --- kind: ordered, most specific first. First match wins for `primary`. -----
KIND_SIG = [
    ("market_maker", [r"market[_ -]?mak", r"\bquote[sd]?\b.*\bspread\b", r"post[_ ]only",
                      r"avellaneda", r"reservation[_ ]price", r"inventory[_ ]skew",
                      r"two[- ]sided", r"\bmaker\b.*\brest(ing)?\b"]),
    ("arbitrage", [r"\barb(itrage)?\b", r"cross[_ ]venue", r"price[_ ]discrepan",
                   r"\bhedge[d]?\b.*\bboth\b", r"kalshi.*polymarket.*spread"]),
    ("copy_trader", [r"copy[_ ]trad", r"mirror[_ ]trad", r"follow[_ ]wallet",
                     r"smart[_ ]money", r"\bwhale\b.*\bfollow\b"]),
    ("backtester", [r"(^|/)backtest", r"\bwalk[_ -]?forward\b", r"\breplay\b.*\bbook\b",
                    r"\bsharpe\b", r"\bequity[_ ]curve\b", r"\bprofit[_ ]factor\b"]),
    ("live_trader", [r"place[_ ]order", r"create[_ ]order", r"submit[_ ]order",
                     r"post[_ ]order", r"\blive[_ ]trad", r"\bexecute[_ ]trade"]),
    ("data_collector", [r"\brecord(er|ing)?\b", r"\bsnapshot\b", r"\bingest",
                        r"\bwebsocket\b.*\bstore\b", r"\bhistorical\b.*\bdownload"]),
    ("scraper", [r"\bscrape[rd]?\b", r"beautifulsoup", r"\bselenium\b", r"\bplaywright\b",
                 r"\bcrawl(er)?\b"]),
    ("dashboard", [r"\bstreamlit\b", r"\bdash\b.*\bplotly\b", r"\bnext\.js\b",
                   r"\breact\b.*\bchart", r"\bgrafana\b"]),
    ("library", [r"\bclient\b.*\bwrapper\b", r"\bsdk\b", r"setup\.py", r"pyproject"]),
]

# Real order submission, borrowed from rescore.py so the two agree.
SUBMIT = re.compile(r"(create_order|post_order|place_order|submit_order|"
                    r"create_and_post_order|createOrder|postOrder|placeOrder|"
                    r"\.create_order\(|orders\.create)")

# Polymarket v1 clients are ARCHIVED (see GITHUB_KNOWLEDGE.md). Importing one is
# a liveness signal in itself: the code cannot be current.
V1_ARCHIVED = re.compile(r"\bpy_clob_client\b|@polymarket/clob-client(?!-v2)")
V2_LIVE = re.compile(r"py-clob-client-v2|py_clob_client_v2|@polymarket/clob-client-v2|"
                     r"polymarket/py-sdk|\bpy_sdk\b")

SKIP = re.compile(r"(^|/)(node_modules|\.venv|venv|site-packages|dist|build|vendor)/")
CODE_EXT = (".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".go", ".java", ".rb",
            ".cs", ".sol", ".ipynb")


def days_since(iso):
    if not iso:
        return None
    try:
        d = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    return (NOW - d).days


def classify_one(fn, branch_hint, default_branch):
    arch = gh.archive(fn, branches=tuple(dict.fromkeys(
        [b for b in (branch_hint, default_branch or "", "main", "master") if b])))
    files = arch.get("files") or {}
    paths = arch.get("paths") or []
    if not files:
        return None

    code = {p: t for p, t in files.items()
            if p.lower().endswith(CODE_EXT) and not SKIP.search(p)}
    blob = "\n".join(code.values())[:1_500_000]
    pathblob = "\n".join(paths)
    readme = next((t for p, t in files.items()
                   if "/" not in p and os.path.splitext(p)[0].lower() == "readme"), "")

    venues = []
    venue_ev = {}
    for v, pats in VENUE_SIG.items():
        hits = [p for p in pats if re.search(p, blob, re.I)]
        if hits:
            venues.append(v)
            venue_ev[v] = hits[:3]
    venue = "+".join(sorted(venues)) if venues else "none"

    kinds = []
    kind_ev = {}
    hay = pathblob + "\n" + blob + "\n" + readme
    for k, pats in KIND_SIG:
        n = sum(1 for p in pats if re.search(p, hay, re.I))
        if n:
            kinds.append((k, n))
            kind_ev[k] = n
    kinds.sort(key=lambda kv: -kv[1])
    primary = kinds[0][0] if kinds else "unknown"

    submits = bool(SUBMIT.search(blob))
    v1 = bool(V1_ARCHIVED.search(blob))
    v2 = bool(V2_LIVE.search(blob))

    return {
        "venue": venue, "venue_ev": venue_ev,
        "kind": primary, "kinds": [k for k, _ in kinds[:4]], "kind_scores": kind_ev,
        "submits_orders": submits,
        "polymarket_client": "v2" if v2 else ("v1-ARCHIVED" if v1 else ""),
        "n_code_files": len(code),
    }


def report(out, want_venue, want_kind, need, alive_only, limit, summary=True):
    """Print the census and/or a filtered view. Pure formatting - no I/O."""
    if summary:
        print("venue (from imports and API hosts, not the README):")
        for v, n in Counter(x["venue"] for x in out).most_common():
            print(f"  {v:22} {n:5}")
        print("\nkind:")
        for k, n in Counter(x["kind"] for x in out).most_common():
            print(f"  {k:22} {n:5}")
        print("\nplaces real orders:", sum(1 for x in out if x["submits_orders"]))
        pm = Counter(x["polymarket_client"] for x in out if x["polymarket_client"])
        print(f"Polymarket client: {dict(pm)}   "
              f"(v1 is ARCHIVED - importing it means the code cannot be current)")

    sel = out
    if want_venue:
        sel = [x for x in sel if want_venue in x["venue"]]
    if want_kind:
        sel = [x for x in sel if want_kind == x["kind"] or want_kind in x["kinds"]]
    if alive_only:
        sel = [x for x in sel if (x["days_since_push"] or 9999) <= 365]
    if need:
        rx = re.compile(need, re.I)
        sel = [x for x in sel
               if rx.search(x["repo"]) or rx.search(x.get("description") or "")]

    if not (want_venue or want_kind or need or alive_only):
        return
    print(f"\n=== venue={want_venue or '*'}  kind={want_kind or '*'}  "
          f"need={need or '*'}  alive={alive_only}  ->  {len(sel)} repos ===")
    sel.sort(key=lambda x: -(x["s_adj"] or -99))
    for x in sel[:(limit or 30)]:
        print(f"{x['repo'][:44]:44} {(x['s_adj'] or 0):+6.2f} {x['kind'][:15]:15} "
              f"{x['venue'][:18]:18} {str(x['days_since_push']):>5}d "
              f"{'ord' if x['submits_orders'] else '-':>4} "
              f"{x.get('fee_model') or '-':>8} "
              f"{'TRUST-ME-BRO' if x['trust_me_bro'] else '':>12}")


def main():
    args = sys.argv[1:]

    def opt(name, default=None):
        return args[args.index(name) + 1] if name in args else default

    want_venue = (opt("--venue") or "").lower()
    want_kind = (opt("--kind") or "").lower()
    need = opt("--need")
    alive_only = "--alive" in args
    limit = int(opt("--limit", "0") or 0)

    outp = os.path.join(gh.ROOT, "reports", "classified.json")

    # Classification is expensive (it reads every cached archive, ~10 minutes)
    # and its answer does not change until the corpus does. A QUERY must not pay
    # that cost: load the saved result unless --reclassify is asked for. The
    # first version re-classified on every query, which is the same waste as
    # re-reading a transcript you have already read.
    if os.path.exists(outp) and "--reclassify" not in args:
        with open(outp, encoding="utf-8") as fh:
            out = json.load(fh)
        print(f"loaded {len(out)} classified repos from cache "
              f"(pass --reclassify to rebuild)\n")
        report(out, want_venue, want_kind, need, alive_only, limit, summary=not any(
            [want_venue, want_kind, need, alive_only]))
        return

    con = db.connect()
    cols = {c[1] for c in con.execute("PRAGMA table_info(repos)")}
    for c, decl in (("venue_detected", "TEXT"), ("kind", "TEXT"),
                    ("submits_orders", "INTEGER"), ("pm_client", "TEXT")):
        if c not in cols:
            con.execute(f"ALTER TABLE repos ADD COLUMN {c} {decl}")
    con.commit()

    fee_ok, fee_bad = set(), set()
    fa = os.path.join(gh.ROOT, "reports", "fee_audit.json")
    if os.path.exists(fa):
        for f in json.load(open(fa, encoding="utf-8"))["findings"]:
            v = " ".join(f["verdict"])
            (fee_ok if "maker 0.0175 OK" in v or "taker 0.07 OK" in v else fee_bad).add(f["repo"])

    sel = ("SELECT full_name, default_branch, stars, pushed_at, commits, s_strict, "
           "s_adj, trust_me_bro, evidence, description FROM repos "
           "WHERE fetched>=1 AND gate IN ('PASS','STALE')")
    if "s_adj" in cols:
        sel += " ORDER BY COALESCE(s_adj,-99) DESC"
    rows = con.execute(sel).fetchall()
    print(f"classifying {len(rows)} deep-fetched repos (cache only, no API, no model)\n",
          flush=True)

    out, done = [], 0
    for r in rows:
        try:
            ev = json.loads(r["evidence"] or "{}")
        except json.JSONDecodeError:
            ev = {}
        c = classify_one(r["full_name"], (ev.get("branch") or [""])[0], r["default_branch"])
        done += 1
        if done % 250 == 0:
            print(f"  {done}/{len(rows)}", flush=True)
        if not c:
            continue
        age = days_since(r["pushed_at"])
        rec = dict(c)
        rec.update({
            "repo": r["full_name"], "stars": r["stars"], "days_since_push": age,
            "commits": r["commits"], "s_strict": r["s_strict"], "s_adj": r["s_adj"],
            "trust_me_bro": r["trust_me_bro"],
            "fee_model": "ok" if r["full_name"] in fee_ok else
                         ("suspect" if r["full_name"] in fee_bad else ""),
            "description": (r["description"] or "")[:100],
        })
        out.append(rec)
        con.execute("UPDATE repos SET venue_detected=?, kind=?, submits_orders=?, "
                    "pm_client=? WHERE full_name=?",
                    (rec["venue"], rec["kind"], int(rec["submits_orders"]),
                     rec["polymarket_client"], r["full_name"]))
    con.commit()

    print(f"\nclassified {len(out)} repos with readable source\n")
    with open(outp, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    report(out, want_venue, want_kind, need, alive_only, limit, summary=True)
    print(f"\nwrote {outp}")


if __name__ == "__main__":
    main()
