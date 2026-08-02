"""Diagnose the two Stage 0 gaps: unmapped venues and unmatched player names."""
import pathlib
import sys

import pandas as pd
from rapidfuzz import fuzz, process

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import tennis_data as td  # noqa: E402
import stage0_audit as s0  # noqa: E402

matches = td.load_matches()
long = td.to_long(matches)
ev = td.load_kalshi_events()

smap = s0.build_surface_map(matches)
ev["surface"] = ev["venue"].map(lambda v: s0.surface_for(v, smap))

print("=" * 78)
print("UNMAPPED VENUES -- how many markets do they cost?")
print("=" * 78)
miss = ev[ev["surface"].isna()]
print(f"{len(miss)} markets ({len(miss) / len(ev) * 100:.1f}%) with no surface\n")
for v, g in miss.groupby("venue", observed=True):
    print(f"  {v:<22} {len(g):>5} markets   tier={sorted(set(g['tier']))} "
          f"raw={g['tourney_raw'].iloc[0]!r}")

print("\n  nearest Sackmann venue names (to see if it is a naming mismatch):")
keys = list(smap.keys())
for v in sorted(miss["venue"].dropna().unique()):
    top = process.extract(v, keys, scorer=fuzz.ratio, limit=3)
    print(f"  {v:<22} -> " + ", ".join(f"{k}({s:.0f},{smap[k]})" for k, s, _ in top))

print("\n" + "=" * 78)
print("UNMATCHED PLAYERS -- are they naming misses or genuinely absent?")
print("=" * 78)
names, exact, key, li = s0.build_player_index(long)

# token-subset index: does a Sackmann name contain all the Kalshi tokens?
from collections import defaultdict  # noqa: E402
by_token = defaultdict(set)
for n in names:
    for t in td.norm_name(n).split():
        by_token[t].add(n)

kalshi_players = pd.unique(pd.concat([ev["player_a"], ev["player_b"]]).dropna())
unmatched = [p for p in kalshi_players
             if s0.resolve(p, names, exact, key, li)[0] is None]
print(f"{len(unmatched)} unmatched\n")

for p in unmatched:
    toks = set(td.norm_name(p).split())
    if not toks:
        continue
    # Sackmann names sharing >=2 tokens, or sharing the rarest token
    cand = set()
    for t in toks:
        cand |= by_token.get(t, set())
    scored = []
    for c in cand:
        ct = set(td.norm_name(c).split())
        shared = len(toks & ct)
        if shared >= 2 or (toks <= ct) or (ct <= toks):
            scored.append((shared, len(ct ^ toks), c))
    scored.sort(key=lambda x: (-x[0], x[1]))
    top = scored[:3]
    if top:
        print(f"  {p:<34} -> " + ", ".join(f"{c!r}(shared={s})" for s, _, c in top))
    else:
        print(f"  {p:<34} -> (no plausible candidate)")
