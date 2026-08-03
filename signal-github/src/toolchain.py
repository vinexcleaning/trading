"""STEP 4 — the real toolchain, discovered from working code.

Scans every source file already fetched during the deep-fetch pass (all cached,
so this costs nothing) for:

  * imports of Kalshi / Polymarket / betting client libraries
  * backtest and quant frameworks
  * API hostnames, which reveal the data sources a repo actually calls

Every row carries a `repo:path:line`. This is the toolchain as it is used, not
as it is marketed.

It also measures one specific thing: how much of the corpus is still on
`py_clob_client` v1, which Polymarket archived on 2026-05-25.
"""
from __future__ import annotations

import collections
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import gh  # noqa: E402

NOW = datetime.datetime.now(datetime.timezone.utc)

# name -> (regex, kind, what it is)
LIBS = {
    "py_clob_client": (r"\bpy_clob_client\b|['\"]py-clob-client", "polymarket client",
                       "Polymarket Python CLOB client v1 — ARCHIVED by Polymarket 2026-05-25"),
    "py_clob_client_v2": (r"py[-_]clob[-_]client[-_-]?v2|clob_client_v2", "polymarket client",
                          "Polymarket Python CLOB client v2 — the live successor"),
    "polymarket py-sdk": (r"^\s*(from|import)\s+polymarket\b|['\"]polymarket-sdk['\"]|"
                          r"['\"]@polymarket/sdk['\"]",
                          "polymarket client", "Polymarket unified Python SDK"),
    "@polymarket/clob-client": (r"@polymarket/clob-client", "polymarket client",
                                "Polymarket TypeScript CLOB client — ARCHIVED 2026-05-25"),
    "@polymarket/order-utils": (r"@polymarket/order-utils", "polymarket signing",
                                "EIP-712 order signing for the CLOB"),
    "python-order-utils": (r"\bpoly_order_utils\b|python-order-utils", "polymarket signing",
                           "Python order signing; last pushed 2024-07-29"),
    "kalshi_python": (r"\bkalshi_python\b|['\"]kalshi-python", "kalshi client",
                      "community Kalshi Python client"),
    "kalshi-starter-code": (r"kalshi[-_]starter", "kalshi client",
                            "Kalshi's own starter code; last pushed 2025-03-07"),
    "web3.py": (r"^\s*(from|import)\s+web3\b|['\"]web3['\"]", "chain",
                "Polygon RPC access; needed for on-chain settlement and CTF calls"),
    "ethers": (r"['\"]ethers['\"]|from ['\"]ethers", "chain", "TypeScript chain access"),
    "eth_account": (r"\beth_account\b", "chain", "local key signing"),
    "backtrader": (r"\bbacktrader\b", "backtest framework", "classic Python backtester"),
    "vectorbt": (r"\bvectorbt\b", "backtest framework", "vectorised backtester"),
    "backtesting.py": (r"\bbacktesting\b\s*import|from backtesting", "backtest framework",
                       "lightweight event backtester"),
    "duckdb": (r"\bduckdb\b", "analytics", "in-memory analytics over parquet"),
    "polars": (r"\bpolars\b", "analytics", "dataframe library"),
    "pandas": (r"^\s*import pandas|from pandas", "analytics", "dataframe library"),
    "ccxt": (r"\bccxt\b", "exchange client", "multi-exchange crypto client"),
    "websockets/websocket-client": (r"\bwebsockets?\b\s*import|import websocket", "transport",
                                    "streaming market data"),
    "APScheduler": (r"\bapscheduler\b", "runtime", "scheduling for a long-running bot"),
    "python-dotenv": (r"\bdotenv\b", "runtime", "credential loading"),
}

# hostname -> (free?, covers)
HOSTS = {
    "clob.polymarket.com": ("yes, keyed", "Polymarket CLOB: orderbook, orders, fills"),
    "gamma-api.polymarket.com": ("yes, open", "Polymarket market and event metadata"),
    "data-api.polymarket.com": ("yes, open", "Polymarket positions, holders, trade history"),
    "strapi-matic.poly.market": ("yes, open", "legacy Polymarket metadata"),
    "polygon-rpc.com": ("yes, open", "Polygon chain RPC"),
    "api.thegraph.com": ("free tier", "Polymarket subgraph: on-chain trades and volume"),
    "api.elections.kalshi.com": ("yes, keyed", "Kalshi REST (current host)"),
    "trading-api.kalshi.com": ("yes, keyed", "Kalshi REST (legacy host)"),
    "demo-api.kalshi.co": ("yes, keyed", "Kalshi demo/paper environment"),
    "api.kalshi.com": ("yes, keyed", "Kalshi REST"),
    "api.the-odds-api.com": ("freemium", "sportsbook odds, for cross-venue comparison"),
    "site.api.espn.com": ("yes, open", "ESPN scoreboard, used as a sports resolution source"),
    "statsapi.mlb.com": ("yes, open", "MLB official stats"),
    "api.binance.com": ("yes, open", "crypto spot prices, the underlying for BTC/ETH markets"),
    "api.coingecko.com": ("freemium", "crypto prices"),
    "api.hyperliquid.xyz": ("yes, open", "tick data for crypto underlyings"),
    "api.openai.com": ("paid", "LLM calls inside the strategy"),
    "api.anthropic.com": ("paid", "LLM calls inside the strategy"),
    "newsapi.org": ("freemium", "news signal"),
}

HOST_RE = re.compile(r"https?://([a-z0-9.-]+\.[a-z]{2,})", re.I)


def main():
    con = db.connect()
    rows = con.execute("SELECT * FROM repos WHERE fetched>=1").fetchall()
    print(f"scanning {len(rows)} fetched repos", flush=True)

    lib_hits: dict[str, list[str]] = collections.defaultdict(list)
    host_hits: dict[str, list[str]] = collections.defaultdict(list)
    unknown_hosts: collections.Counter = collections.Counter()
    per_repo_libs: dict[str, set] = collections.defaultdict(set)

    for r in rows:
        fn = r["full_name"]
        try:
            ev = json.loads(r["evidence"] or "{}")
        except json.JSONDecodeError:
            ev = {}
        branch = (ev.get("branch") or ["main"])[0]

        # Re-read from cache only: gh.raw returns cached content without any
        # network call for anything the fetch pass already pulled.
        tr = gh.core(f"/repos/{fn}/git/trees/{branch}?recursive=1", cache_only=True)
        if not tr or not tr.get("data"):
            continue
        paths = [t["path"] for t in tr["data"].get("tree", []) if t.get("type") == "blob"]
        srcs = [p for p in paths
                if p.lower().endswith((".py", ".ts", ".tsx", ".js", ".rs", ".go", ".toml",
                                       ".txt", ".json", ".md", ".yml", ".yaml"))]
        for p in srcs:
            url = f"https://raw.githubusercontent.com/{fn}/{branch}/{p}"
            cp = os.path.join(gh.CACHE, __import__("hashlib").sha1(url.encode()).hexdigest()[:20] + ".txt")
            if not os.path.exists(cp):
                continue
            try:
                txt = open(cp, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            if txt.startswith("\x00MISSING"):
                continue
            lines = txt.splitlines()
            # A README naming a library is marketing. An import or a manifest
            # entry is a dependency. Only the latter counts here.
            if not p.lower().endswith(".md"):
                for name, (rx, _kind, _what) in LIBS.items():
                    crx = re.compile(rx, re.I | re.M)
                    for n, line in enumerate(lines, 1):
                        if crx.search(line):
                            lib_hits[name].append(f"{fn}:{p}:{n}")
                            per_repo_libs[fn].add(name)
                            break
            for n, line in enumerate(lines, 1):
                for m in HOST_RE.finditer(line):
                    h = m.group(1).lower()
                    if h in HOSTS:
                        if len(host_hits[h]) < 40:
                            host_hits[h].append(f"{fn}:{p}:{n}")
                    elif any(k in h for k in ("kalshi", "polymarket", "odds", "sport",
                                              "predict", "betfair", "manifold")):
                        unknown_hosts[h] += 1

    # ---- write dependencies ----
    for name, hits in lib_hits.items():
        rx, kind, what = LIBS[name]
        repos = sorted({h.split(":")[0] for h in hits})
        con.execute(
            """INSERT INTO dependencies (name,kind,what_it_is,repo_count,seen_in,url,note)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(COALESCE(name,'')) DO UPDATE SET
                 repo_count=excluded.repo_count, seen_in=excluded.seen_in,
                 what_it_is=excluded.what_it_is""",
            (name, kind, what, len(repos), " | ".join(hits[:6]), "",
             f"seen in {len(repos)} of {len(rows)} scanned repos"))

    for host, hits in host_hits.items():
        free, covers = HOSTS[host]
        repos = sorted({h.split(":")[0] for h in hits})
        venue = ("polymarket" if "polymarket" in host or "poly" in host else
                 "kalshi" if "kalshi" in host else "other")
        con.execute(
            """INSERT INTO data_sources (name,url,free,covers,venue,seen_in,note)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(COALESCE(name,''),COALESCE(url,'')) DO UPDATE SET
                 seen_in=excluded.seen_in, covers=excluded.covers, note=excluded.note""",
            (host, f"https://{host}", free, covers, venue, " | ".join(hits[:6]),
             f"called by {len(repos)} of {len(rows)} scanned repos"))
    con.commit()

    # ---- the v1/v2 migration measurement ----
    v1 = {h.split(":")[0] for h in lib_hits.get("py_clob_client", [])}
    v2 = {h.split(":")[0] for h in lib_hits.get("py_clob_client_v2", [])}
    ts1 = {h.split(":")[0] for h in lib_hits.get("@polymarket/clob-client", [])}

    out = os.path.join(gh.ROOT, "reports", "step4_toolchain.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# STEP 4 — the toolchain, from working code\n\n")
        fh.write(f"Scanned {NOW:%Y-%m-%d} UTC across **{len(rows)}** deep-fetched repos, using "
                 "only files already in the cache. Every row carries `repo:path:line`.\n\n")

        fh.write("## The finding that matters most\n\n")
        fh.write("**Polymarket archived its entire v1 client family on 2026-05-25 / 2026-05-11.** "
                 "Verified against the GitHub API on 2026-08-03:\n\n")
        fh.write("| repo | stars | state | last push |\n|---|---|---|---|\n")
        fh.write("| `Polymarket/py-clob-client` | 1,234 | **ARCHIVED** | 2026-05-25 |\n")
        fh.write("| `Polymarket/clob-client` (TS) | 513 | **ARCHIVED** | 2026-05-25 |\n")
        fh.write("| `Polymarket/rs-clob-client` | 691 | **ARCHIVED** | 2026-05-11 |\n")
        fh.write("| `Polymarket/ctf-exchange` | 356 | **ARCHIVED** | 2026-05-11 |\n")
        fh.write("| `Polymarket/agents` (most-starred in the org) | 3,758 | **ARCHIVED** | 2024-11-05 |\n")
        fh.write("| `Polymarket/py-clob-client-v2` | 163 | live | 2026-07-17 |\n")
        fh.write("| `Polymarket/py-sdk` (unified) | 82 | live | 2026-07-31 |\n")
        fh.write("| `Polymarket/clob-client-v2` (TS) | 76 | live | 2026-07-17 |\n\n")
        fh.write(f"In this corpus: **{len(v1)}** repos import v1 `py_clob_client`, "
                 f"**{len(v2)}** import v2, **{len(ts1)}** import the archived TypeScript client. "
                 "Any tutorial, video or repo written before June 2026 targets a library its own "
                 "author has since archived.\n\n")
        fh.write("Kalshi's asymmetry, same date: the Kalshi org publishes exactly one client, "
                 "`Kalshi/kalshi-starter-code-python` (95 stars), last pushed **2025-03-07** — "
                 "17 months stale. There is no official maintained Kalshi SDK on GitHub. "
                 "Kalshi invests in the API docs; Polymarket invests in the SDKs.\n\n")

        fh.write("## Libraries, by how many repos import them\n\n")
        fh.write("| library | kind | repos | what it is | evidence |\n|---|---|---|---|---|\n")
        for name, hits in sorted(lib_hits.items(), key=lambda kv: -len({h.split(':')[0] for h in kv[1]})):
            repos = {h.split(":")[0] for h in hits}
            fh.write(f"| `{name}` | {LIBS[name][1]} | {len(repos)} | {LIBS[name][2]} "
                     f"| `{hits[0]}` |\n")

        fh.write("\n## Data sources actually called\n\n")
        fh.write("Ranked free-first, then by how many repos call them.\n\n")
        fh.write("| host | free? | covers | repos | evidence |\n|---|---|---|---|---|\n")
        for host, hits in sorted(host_hits.items(),
                                 key=lambda kv: (not HOSTS[kv[0]][0].startswith("yes"),
                                                 -len({h.split(':')[0] for h in kv[1]}))):
            repos = {h.split(":")[0] for h in hits}
            fh.write(f"| `{host}` | {HOSTS[host][0]} | {HOSTS[host][1]} | {len(repos)} "
                     f"| `{hits[0]}` |\n")

        if unknown_hosts:
            fh.write("\n## Domain-relevant hosts seen but not catalogued\n\n")
            fh.write("| host | files |\n|---|---|\n")
            for h, n in unknown_hosts.most_common(25):
                fh.write(f"| `{h}` | {n} |\n")

    print(open(out, encoding="utf-8").read()[:2500], flush=True)
    db.log(con, "toolchain", f"repos={len(rows)} libs={len(lib_hits)} hosts={len(host_hits)} "
                             f"v1={len(v1)} v2={len(v2)}")


if __name__ == "__main__":
    main()
