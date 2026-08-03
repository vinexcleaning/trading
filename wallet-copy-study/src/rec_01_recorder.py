r"""Record the live CLOB order book, to measure the ONE number the study lacks.

Every "net" figure in this project subtracts a 1.0pp spread floor derived from
same-block trade-price dispersion. That is a LOWER bound, because the subgraph
carries no book. At a true effective spread of 1.5pp the politics edge is dead;
at 0.5pp it is alive. Nothing else outstanding changes the answer as much.

What is recorded, per token per cycle: the top 3 levels each side, so the
effective cost of crossing can be computed for a REAL order size rather than
just quoting top-of-book. A $500 order that walks two levels pays more than the
headline spread, and that difference is exactly what the study has been
guessing at.

Design notes:
  - `POST /books` batches up to 500 tokens per call (probed), so a few thousand
    tokens cost only a handful of requests per cycle. Paced deliberately.
  - The token universe is refreshed periodically because markets resolve and
    stop accepting orders during a long run; without that the tail of the
    recording would drift toward dead books.
  - Politics is over-weighted on purpose: it is the only category that survived
    every specification, so its spread is the one that decides the headline.
    The sampling is stated, not hidden, and other categories are still recorded
    so the comparison exists.
"""
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "data" / "book_recording_deep"
OUTDIR.mkdir(parents=True, exist_ok=True)
STATE = ROOT / "data" / "book_recording_state.json"
CLOB = "https://clob.polymarket.com"

S = requests.Session()
S.headers.update({"User-Agent": "copy-trading-feasibility-study/0.1"})

RUN_SECONDS = int(sys.argv[1]) if len(sys.argv) > 1 else 8 * 3600
CYCLE_SECONDS = 60
BATCH = 400
REFRESH_UNIVERSE_S = 1800
LEVELS = 10   # 3 was too shallow: 45.5% of $500 politics orders could not fill
PER_CAT_CAP = {"politics": 1400, "crypto": 700, "nba": 500, "soccer": 500,
               "nfl": 300, "esports": 300, "weather": 200, "other": 700}

TAG_RULES = [
    ("esports", {"esports", "cs2", "counter-strike", "league of legends", "lol",
                 "dota", "dota 2", "valorant", "call of duty", "overwatch"}),
    ("nba", {"nba", "basketball", "ncaa basketball", "ncaab", "wnba"}),
    ("nfl", {"nfl", "football", "ncaa football", "ncaaf"}),
    ("soccer", {"soccer", "epl", "premier league", "la liga", "laliga",
                "serie a", "bundesliga", "champions league", "uefa", "mls"}),
    ("politics", {"politics", "elections", "election", "us politics",
                  "geopolitics", "trump", "congress", "senate"}),
    ("crypto", {"crypto", "crypto prices", "bitcoin", "ethereum", "solana",
                "xrp", "ripple", "dogecoin", "up or down"}),
    ("weather", {"weather", "temperature", "hurricane", "climate"}),
]
SLUG_RULES = [("nba", r"^(nba|ncaab|wnba)-"), ("nfl", r"^(nfl|ncaaf)-"),
              ("soccer", r"^(epl|laliga|seriea|bundesliga|ucl|mls|soccer)-"),
              ("crypto", r"(updown|^(btc|eth|sol|xrp|doge)[-_])"),
              ("politics", r"(election|president|senate|congress|governor)"),
              ("weather", r"(temperature|hurricane|weather)")]
SLUG_RULES = [(c, re.compile(p)) for c, p in SLUG_RULES]


def categorise(tags, slug):
    tl = {str(t).strip().lower() for t in (tags or [])} if isinstance(tags, list) \
        else ({str(tags).lower()} if tags else set())
    for cat, keys in TAG_RULES:
        if tl & keys:
            return cat
    s = (slug or "").lower()
    for cat, pat in SLUG_RULES:
        if pat.search(s):
            return cat
    return "other"


def build_universe():
    """Live, order-book-enabled tokens on markets currently accepting orders."""
    by_cat = defaultdict(list)
    cur = ""
    pages = 0
    while pages < 40:
        try:
            r = S.get(f"{CLOB}/sampling-markets",
                      params={"next_cursor": cur} if cur else {}, timeout=60)
            if not r.ok:
                break
            j = r.json()
        except Exception:  # noqa: BLE001
            break
        data = j.get("data") or []
        if not data:
            break
        for m in data:
            if not (m.get("accepting_orders") and m.get("enable_order_book")):
                continue
            if m.get("closed"):
                continue
            cat = categorise(m.get("tags"), m.get("market_slug"))
            for t in (m.get("tokens") or []):
                tid = t.get("token_id")
                if tid:
                    by_cat[cat].append({
                        "token_id": tid, "cat": cat,
                        "cid": m.get("condition_id"),
                        "slug": (m.get("market_slug") or "")[:80],
                        "outcome": t.get("outcome"),
                        "tick": m.get("minimum_tick_size")})
        cur = j.get("next_cursor") or ""
        pages += 1
        if not cur or cur == "LTE=":
            break
    uni = []
    for cat, cap in PER_CAT_CAP.items():
        uni += by_cat.get(cat, [])[:cap]
    return uni, {k: len(v) for k, v in by_cat.items()}


def top_levels(side_rows, is_bid):
    """Book sides come back ascending by price; best bid is last, best ask last."""
    if not side_rows:
        return []
    try:
        rows = [(float(x["price"]), float(x["size"])) for x in side_rows]
    except Exception:  # noqa: BLE001
        return []
    rows.sort(key=lambda z: z[0], reverse=is_bid)
    return rows[:LEVELS]


print(f"recorder: {RUN_SECONDS/3600:.1f}h, cycle {CYCLE_SECONDS}s, "
      f"batch {BATCH}, top {LEVELS} levels/side", flush=True)

uni, cat_counts = build_universe()
print(f"  universe: {len(uni):,} tokens  {Counter(u['cat'] for u in uni)}",
      flush=True)
print(f"  available by category: {cat_counts}", flush=True)
(OUTDIR / "universe.json").write_text(
    json.dumps({"built": int(time.time()), "n": len(uni),
                "by_cat": dict(Counter(u["cat"] for u in uni)),
                "available": cat_counts, "tokens": uni}, indent=2),
    encoding="utf-8")

meta = {u["token_id"]: u for u in uni}
t_start = time.time()
t_refresh = t_start
cycle = 0
stats = Counter()

while time.time() - t_start < RUN_SECONDS:
    cyc_t0 = time.time()
    hour = time.strftime("%Y-%m-%d_%H", time.gmtime())
    path = OUTDIR / f"books_{hour}.jsonl"
    ids = list(meta.keys())
    n_rows = 0
    with path.open("a", encoding="utf-8") as fh:
        for i in range(0, len(ids), BATCH):
            chunk = ids[i:i + BATCH]
            payload = [{"token_id": t} for t in chunk]
            try:
                r = S.post(f"{CLOB}/books", json=payload, timeout=90)
                if r.status_code == 429:
                    stats["rate_limited"] += 1
                    time.sleep(10)
                    continue
                if not r.ok:
                    stats["http_err"] += 1
                    continue
                books = r.json()
            except Exception:  # noqa: BLE001
                stats["exc"] += 1
                continue
            now = int(time.time())
            if not isinstance(books, list):
                stats["bad_shape"] += 1
                continue
            for b in books:
                tid = b.get("asset_id") or b.get("token_id")
                if not tid:
                    continue
                bids = top_levels(b.get("bids"), True)
                asks = top_levels(b.get("asks"), False)
                if not bids or not asks:
                    stats["one_sided_or_empty"] += 1
                    continue
                m = meta.get(tid, {})
                fh.write(json.dumps({
                    "t": now, "tok": tid, "cat": m.get("cat"),
                    "slug": m.get("slug"), "tick": m.get("tick"),
                    "bids": [[round(p, 6), round(s, 4)] for p, s in bids],
                    "asks": [[round(p, 6), round(s, 4)] for p, s in asks],
                }) + "\n")
                n_rows += 1
            time.sleep(0.4)
    cycle += 1
    stats["cycles"] += 1
    stats["rows"] += n_rows
    el = time.time() - t_start
    if cycle % 5 == 0 or cycle == 1:
        print(f"  cycle {cycle:>5}  rows={stats['rows']:>10,}  "
              f"elapsed {el/3600:>5.2f}h  last cycle {time.time()-cyc_t0:.0f}s  "
              f"{dict(stats)}", flush=True)
        STATE.write_text(json.dumps({
            "started": int(t_start), "cycles": cycle, "rows": stats["rows"],
            "elapsed_h": round(el / 3600, 3), "counters": dict(stats),
            "n_tokens": len(meta)}, indent=2), encoding="utf-8")

    if time.time() - t_refresh > REFRESH_UNIVERSE_S:
        try:
            uni2, cc2 = build_universe()
            if uni2:
                meta = {u["token_id"]: u for u in uni2}
                stats["universe_refreshes"] += 1
                print(f"  universe refreshed: {len(meta):,} tokens", flush=True)
        except Exception:  # noqa: BLE001
            stats["refresh_failed"] += 1
        t_refresh = time.time()

    nap = CYCLE_SECONDS - (time.time() - cyc_t0)
    if nap > 0:
        time.sleep(nap)

STATE.write_text(json.dumps({
    "started": int(t_start), "finished": int(time.time()), "cycles": cycle,
    "rows": stats["rows"], "elapsed_h": round((time.time() - t_start) / 3600, 3),
    "counters": dict(stats), "n_tokens": len(meta)}, indent=2), encoding="utf-8")
print(f"\ndone: {cycle} cycles, {stats['rows']:,} book snapshots")
