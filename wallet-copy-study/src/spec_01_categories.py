r"""Task 1: assign every trade a CATEGORY and an EVENT, and report coverage.

Two separate jobs that both come from market metadata.

CATEGORY drives the specialist test. Tags are present on 100% of sampled
markets, but many carry only ['All'], so tags alone are not enough and the
structured slug is used as a fallback (`nba-lac-orl-2023-03-18`,
`ncaab-tenn-duke-2023-03-18`, `btc-updown-5m-1785563700`). Tag first, slug
second, and the split between the two is reported so the reader can see how much
work each is doing.

EVENT is the clustering unit and matters more than it looks. "21 bets on one
match is one observation" -- a prior run produced a "+95pp genius" that was
exactly one coinflip counted 21 times. A sports slug already IS the game, so it
serves as the event key directly. Recurring high-frequency series (5-minute
crypto up/down and similar) get (series, day), because 288 BTC markets in one
day are not 288 independent draws. Anything else falls back to its own market.

Coverage is reported by VOLUME as well as by count, because an unclassified
majority of volume would make everything downstream meaningless.
"""
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNI = ROOT / "data" / "markets_clob.jsonl"
POS = ROOT / "data" / "wallet_positions.jsonl"
OUT_MAP = ROOT / "data" / "spec_cid_category.jsonl"
OUT_STATS = ROOT / "reports" / "spec_task1_categories.json"
OUT_STATS.parent.mkdir(parents=True, exist_ok=True)

# ---- tag vocabulary -> category. Order matters: first hit wins, and the more
# specific leagues are checked before the generic Sports/Games buckets.
TAG_RULES = [
    ("esports", {"esports", "cs2", "counter-strike", "league of legends", "lol",
                 "dota", "dota 2", "valorant", "call of duty", "overwatch",
                 "rocket league", "starcraft"}),
    ("nba", {"nba", "basketball", "ncaa basketball", "ncaab", "wnba"}),
    ("nfl", {"nfl", "football", "ncaa football", "ncaaf"}),
    ("soccer", {"soccer", "epl", "premier league", "la liga", "laliga",
                "serie a", "bundesliga", "champions league", "uefa", "mls",
                "world cup", "ligue 1"}),
    ("politics", {"politics", "elections", "election", "us politics",
                  "geopolitics", "trump", "congress", "senate"}),
    ("crypto", {"crypto", "crypto prices", "bitcoin", "ethereum", "solana",
                "xrp", "ripple", "dogecoin", "up or down"}),
    ("weather", {"weather", "temperature", "hurricane", "climate"}),
]

SLUG_RULES = [
    ("esports", (r"^(cs2|csgo|lol|dota|val|valorant|cod|ow2|rl)-",
                 r"-(cs2|csgo|lol|dota|valorant)-")),
    ("nba", (r"^(nba|ncaab|wnba)-",)),
    ("nfl", (r"^(nfl|ncaaf)-",)),
    ("soccer", (r"^(epl|laliga|seriea|bundesliga|ucl|uel|mls|ligue1|soccer)-",)),
    ("crypto", (r"^(btc|eth|sol|xrp|doge|ada|link|avax|matic|bnb)[-_]",
                r"updown", r"-up-or-down")),
    ("politics", (r"(election|president|senate|congress|governor|parliament|"
                  r"prime-minister|nomination)",)),
    ("weather", (r"(temperature|hurricane|weather|rainfall|snowfall)",)),
    ("nhl_mlb_other_sport", (r"^(nhl|mlb|ufc|atp|wta|tennis|f1|golf|pga)-",)),
]
SLUG_RULES = [(c, tuple(re.compile(p) for p in pats)) for c, pats in SLUG_RULES]

CATEGORIES = ["esports", "nba", "nfl", "soccer", "politics", "crypto",
              "weather", "other"]

_GAME = re.compile(r"^[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-\d{4}-\d{2}-\d{2}")
_LONGNUM = re.compile(r"^\d{4,}$")
_RECUR = re.compile(r"(updown|-5m-|-15m-|-1h-|hourly|-up-down)")


def categorise(tags, slug, question):
    """-> (category, source). Tag first, slug second, else other."""
    tl = set()
    if isinstance(tags, list):
        tl = {str(t).strip().lower() for t in tags}
    elif tags:
        tl = {str(tags).strip().lower()}
    for cat, keys in TAG_RULES:
        if tl & keys:
            return cat, "tag"
    s = (slug or "").lower()
    for cat, pats in SLUG_RULES:
        if any(p.search(s) for p in pats):
            return ("other" if cat == "nhl_mlb_other_sport" else cat), "slug"
    q = (question or "").lower()
    for cat, keys in TAG_RULES:
        if any(k in q for k in keys if len(k) > 4):
            return cat, "question"
    return "other", "unmatched"


def event_key(slug, cid, end_ts):
    """Clustering unit. A sports slug IS the game; recurring series get a day."""
    s = (slug or "").strip().lower()
    if not s:
        return f"cid:{cid}"
    if _GAME.match(s):
        return f"game:{_GAME.match(s).group(0)}"
    if _RECUR.search(s):
        parts = [p for p in s.split("-") if not _LONGNUM.fullmatch(p)]
        day = int(end_ts // 86400) if end_ts else 0
        return f"series:{'-'.join(parts)}:{day}"
    parts = [p for p in s.split("-") if not _LONGNUM.fullmatch(p)]
    return f"slug:{'-'.join(parts)}"


# ------------------------------------------- pass 1: cids actually traded
print("pass 1: collecting traded cids...", flush=True)
need = set()
n = 0
for line in POS.open(encoding="utf-8"):
    n += 1
    i = line.find('"cid": "')
    if i >= 0:
        j = line.find('"', i + 8)
        need.add(line[i + 8:j])
    if n % 500_000 == 0:
        print(f"  {n:,} rows  {len(need):,} cids", flush=True)
print(f"  {n:,} positions -> {len(need):,} distinct markets")

# --------------------------------- pass 2: classify only those markets
print("\npass 2: classifying...", flush=True)
cat_of, ev_of = {}, {}
src_ct = Counter()
cat_ct = Counter()
m = 0
t0 = time.time()
with OUT_MAP.open("w", encoding="utf-8") as fh:
    for line in UNI.open(encoding="utf-8"):
        r = json.loads(line)
        cid = r["condition_id"]
        if cid not in need:
            continue
        cat, src = categorise(r.get("tags"), r.get("slug"), r.get("question"))
        ev = event_key(r.get("slug"), cid, r.get("end_ts"))
        cat_of[cid] = cat
        ev_of[cid] = ev
        src_ct[src] += 1
        cat_ct[cat] += 1
        fh.write(json.dumps({"cid": cid, "cat": cat, "src": src, "ev": ev}) + "\n")
        m += 1
        if m % 300_000 == 0:
            print(f"  {m:,} classified  {time.time()-t0:.0f}s", flush=True)
print(f"  classified {m:,} of {len(need):,} traded markets "
      f"({m/max(len(need),1):.2%}) in {time.time()-t0:.0f}s")

# --------------------------------- pass 3: coverage BY VOLUME, and wallets
print("\npass 3: volume coverage and per-wallet shares...", flush=True)
vol_by_cat = Counter()
vol_by_src = Counter()
pos_by_cat = Counter()
wallet_vol = defaultdict(Counter)
unmapped_vol = 0.0
n = 0
for line in POS.open(encoding="utf-8"):
    r = json.loads(line)
    n += 1
    if r["flags"] or r["settle_state"] != "settled":
        continue
    c = r["cost"]
    if c <= 0:
        continue
    cid = r["cid"]
    cat = cat_of.get(cid)
    if cat is None:
        unmapped_vol += c
        continue
    vol_by_cat[cat] += c
    pos_by_cat[cat] += 1
    wallet_vol[r["wallet"]][cat] += c
    if n % 500_000 == 0:
        print(f"  {n:,}", flush=True)

total_vol = sum(vol_by_cat.values()) + unmapped_vol
classified_vol = total_vol - vol_by_cat["other"] - unmapped_vol

# ------------------------------------------------- specialist flags
thresholds = [0.50, 0.70, 0.90]
spec_counts = {f"{int(t*100)}%": Counter() for t in thresholds}
wallet_spec = {}
for w, cc in wallet_vol.items():
    tot = sum(cc.values())
    if tot <= 0:
        continue
    top_cat, top_v = cc.most_common(1)[0]
    share = top_v / tot
    wallet_spec[w] = {"top_cat": top_cat, "share": round(share, 4),
                      "volume": round(tot, 2),
                      "shares": {k: round(v / tot, 4) for k, v in cc.items()}}
    for t in thresholds:
        if share >= t:
            spec_counts[f"{int(t*100)}%"][top_cat] += 1

(ROOT / "data" / "spec_wallet_categories.json").write_text(
    json.dumps(wallet_spec, indent=None), encoding="utf-8")

summary = {
    "n_positions_scanned": n,
    "n_traded_markets": len(need),
    "n_markets_classified": m,
    "market_map_coverage": round(m / max(len(need), 1), 4),
    "classification_source": dict(src_ct),
    "markets_by_category": dict(cat_ct.most_common()),
    "volume": {
        "total_usd": round(total_vol, 2),
        "unmapped_usd": round(unmapped_vol, 2),
        "unmapped_share": round(unmapped_vol / max(total_vol, 1), 4),
        "other_usd": round(vol_by_cat["other"], 2),
        "other_share": round(vol_by_cat["other"] / max(total_vol, 1), 4),
        "classified_into_a_named_category_share":
            round(classified_vol / max(total_vol, 1), 4),
        "by_category_usd": {k: round(v, 2) for k, v in vol_by_cat.most_common()},
        "by_category_share": {k: round(v / max(total_vol, 1), 4)
                              for k, v in vol_by_cat.most_common()},
    },
    "positions_by_category": dict(pos_by_cat.most_common()),
    "n_wallets": len(wallet_spec),
    "specialists_by_threshold": {k: dict(v.most_common())
                                 for k, v in spec_counts.items()},
    "specialist_totals": {k: sum(v.values()) for k, v in spec_counts.items()},
}
OUT_STATS.write_text(json.dumps(summary, indent=2), encoding="utf-8")

print("\n=== TASK 1: CATEGORY COVERAGE ===")
print(f"  markets classified      : {m:,} / {len(need):,} "
      f"({m/max(len(need),1):.2%})")
print(f"  classification source   : {dict(src_ct)}")
print(f"  volume unmapped         : {unmapped_vol/max(total_vol,1):.2%}")
print(f"  volume in 'other'       : {vol_by_cat['other']/max(total_vol,1):.2%}")
print(f"  volume in NAMED category: {classified_vol/max(total_vol,1):.2%}")
print("\n  volume by category:")
for k, v in vol_by_cat.most_common():
    print(f"    {k:>10}: ${v:>14,.0f}  ({v/max(total_vol,1):>6.2%})  "
          f"{pos_by_cat[k]:>9,} positions")
print("\n  specialist wallets by concentration threshold:")
for t in thresholds:
    key = f"{int(t*100)}%"
    tot = sum(spec_counts[key].values())
    print(f"    >={key:>4}: {tot:>5,} wallets  {dict(spec_counts[key].most_common(6))}")
print(f"\nwrote {OUT_MAP}, {OUT_STATS}")
