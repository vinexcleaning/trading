r"""What is actually capping Task 5 coverage at 16.1%?

Coverage is the share of surviving wallets' period-2 positions for which a
complete token book exists, so a price at +delay can be read. Before pulling
more data, find out which of three things is binding:

  a. tokens never attempted   -- the pull list was truncated
  b. tokens attempted but empty -- the token has no fills in the subgraph
  c. tokens present but too thin -- a book exists, but has no print at t+delay
     inside the lookahead window, so the position is still unusable

These need different fixes, and (c) cannot be fixed by pulling harder.
"""
import json
from bisect import bisect_left
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
TARGETS = D / "spec_task5_targets.json"
DONE = D / "spec_task5_done.json"
PANEL = D / "spec_panel.jsonl"
BOOKS = [D / "spec_task5_fills.jsonl", D / "exit_fills.jsonl", D / "fills.jsonl"]
OUT = ROOT / "reports" / "spec_coverage_diag.json"

CUT = 1767830400
DELAYS = [0, 10, 60, 300, 1800]
MAX_LOOKAHEAD = 3600

t = json.loads(TARGETS.read_text(encoding="utf-8"))
survivors = set(t["survivors"])
print(f"survivors: {len(survivors)}")
print(f"targets: n_distinct_tokens={t['n_distinct_tokens']:,} "
      f"already_have={t['n_already_have']:,} to_pull={t['n_to_pull']:,}")

done = json.loads(DONE.read_text(encoding="utf-8"))
done_set = set(done if isinstance(done, list) else done.get("done", []))
print(f"done file records {len(done_set):,} tokens pulled")

# ---- which tokens actually have a book on disk, and how deep
print("\nscanning books on disk...", flush=True)
depth = Counter()
bts = defaultdict(list)
n = 0
for p in BOOKS:
    if not p.exists():
        continue
    for line in p.open(encoding="utf-8"):
        try:
            f = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        tok = f.get("token")
        if tok is None:
            continue
        depth[tok] += 1
        bts[tok].append(f["ts"])
        n += 1
        if n % 10_000_000 == 0:
            print(f"  {n:,} fills, {len(depth):,} tokens", flush=True)
for k in bts:
    bts[k].sort()
print(f"  {n:,} fills over {len(depth):,} distinct tokens")

# ---- classify every surviving-wallet period-2 position
print("\nclassifying positions...", flush=True)
cls = Counter()
usable_by_delay = Counter()
tok_needed = Counter()
missing_tokens = Counter()
rows = 0
for line in PANEL.open(encoding="utf-8"):
    r = json.loads(line)
    if r["ts"] < CUT or r["w"] not in survivors:
        continue
    rows += 1
    tok = r["tok"]
    tok_needed[tok] += 1
    ts = bts.get(tok)
    if not ts:
        cls["no_book_on_disk"] += 1
        missing_tokens[tok] += 1
        continue
    ok_all = True
    for d in DELAYS:
        i = bisect_left(ts, r["ts"] + d)
        if i < len(ts) and ts[i] - (r["ts"] + d) <= MAX_LOOKAHEAD:
            usable_by_delay[d] += 1
        else:
            ok_all = False
    if ok_all:
        cls["usable_all_delays"] += 1
    else:
        cls["book_too_thin_for_some_delay"] += 1

print(f"\n=== {rows:,} surviving-wallet period-2 positions ===")
for k, v in cls.most_common():
    print(f"  {k:>34}: {v:>8,}  ({v/rows:.1%})")
print("\n  usable at each delay individually:")
for d in DELAYS:
    print(f"    d={d:>5}s: {usable_by_delay[d]:>8,}  ({usable_by_delay[d]/rows:.1%})")

print(f"\n  distinct tokens needed        : {len(tok_needed):,}")
print(f"  distinct tokens WITH a book   : {sum(1 for k in tok_needed if k in depth):,}")
print(f"  distinct tokens MISSING       : {len(missing_tokens):,}")
print(f"  positions blocked by missing  : {sum(missing_tokens.values()):,}")

# how much coverage would pulling every missing token buy, at most?
ceiling = (cls["usable_all_delays"] + sum(missing_tokens.values())) / rows
print(f"\n  CEILING if every missing token were pulled and were dense enough: "
      f"{ceiling:.1%}")
print(f"  (currently {cls['usable_all_delays']/rows:.1%})")

# thin-book tokens: present but not dense enough
thin = [k for k in tok_needed if k in depth and depth[k] < 5]
print(f"  tokens present but with <5 fills: {len(thin):,}")

miss_sorted = [k for k, _ in missing_tokens.most_common()]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({
    "n_positions": rows,
    "classification": dict(cls),
    "usable_by_delay": {str(k): v for k, v in usable_by_delay.items()},
    "coverage_now": round(cls["usable_all_delays"] / rows, 4),
    "coverage_ceiling_if_all_pulled": round(ceiling, 4),
    "n_tokens_needed": len(tok_needed),
    "n_tokens_have": sum(1 for k in tok_needed if k in depth),
    "n_tokens_missing": len(missing_tokens),
    "positions_blocked_by_missing_tokens": sum(missing_tokens.values()),
    "n_tokens_present_but_thin": len(thin),
    "missing_tokens_ranked_by_positions_unlocked": miss_sorted[:60000],
}, indent=2), encoding="utf-8")
print(f"\nwrote {OUT}")
