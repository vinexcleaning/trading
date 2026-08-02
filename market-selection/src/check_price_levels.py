"""What is Kalshi's tick, authoritatively?

`tick_size` is absent from the market object on all 419,828 open markets -- the
key does not exist. But `price_level_structure` and `price_ranges` do, and the
depth recorder already showed that some series quote to 0.1c while most quote
to 1c. This reads the structural fields so the tick is a fact from the venue
rather than an inference from observed prices.

Why it matters: the tick is the floor on the spread, and the spread is most of
the cost bar. A family quoting on a 0.1c tick can price ten times finer than
one on a 1c tick, so "the book sits at the tightest possible quote" means two
completely different things in the two cases.
"""
import json
import os
from collections import Counter

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
WANT = {"KXPGATOUR", "KXMLB", "KXMLBGAME", "KXPRESNOMD", "KXBTCD", "KXWTAMATCH",
        "KXBTCY", "KXSENATEMID", "KXITFMATCH", "KXATPMATCH", "KXLPGATOUR",
        "KXNBA", "KXMLBTOTAL", "KXBTC15M", "KXMLSGAME"}

structs = Counter()
by_series = {}
n = 0
with open(os.path.join(DATA, "kalshi_markets_open.jsonl"), encoding="utf-8") as fh:
    for line in fh:
        m = json.loads(line)
        n += 1
        s = m["ticker"].split("-")[0]
        pls = m.get("price_level_structure")
        structs[json.dumps(pls, sort_keys=True)] += 1
        if s in WANT and s not in by_series:
            by_series[s] = (pls, m.get("price_ranges"), m.get("market_type"),
                            m.get("strike_type"))

print(f"scanned {n:,} open markets\n")
print("=== distinct price_level_structure values ===")
for k, v in structs.most_common(8):
    print(f"  {v:8,d} markets  {k[:180]}")

print("\n=== per series ===")
for s in sorted(by_series):
    pls, pr, mt, st = by_series[s]
    print(f"\n{s}")
    print(f"  market_type={mt}  strike_type={st}")
    print(f"  price_level_structure = {json.dumps(pls)[:400]}")
    print(f"  price_ranges          = {json.dumps(pr)[:400]}")
