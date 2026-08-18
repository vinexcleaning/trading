"""Find claims that appear in more than one LEDGER.md section.

A claim that travels between projects gets a fresh row and a fresh status each
time, and the weakest status is the one a reader happens to find. This matches
on NUMERIC FINGERPRINT - sample size and effect size - rather than on wording,
because wording is exactly what differs when a claim is restated.

Two real errors found on the first two runs (2026-08-03):

  n=98,766   K015 (UNVERIFIED) is the same claim as W011 (RETRACTED).
             wallet-copy-study had already recomputed +7.05pp down to
             +2.09pp gross / -0.29pp net. kalshi-market-scan was still
             calling it the finding that reframed its copy-trading block.

  n=1,083    crypto cited this study twice as "zero violations in 1,083
             scans". kalshi-market-scan actually found 52 net-positive
             violations, none tradeable. Same conclusion, different
             mechanism claim.

Benign matches are expected and are not errors - the same dataset legitimately
supports several rows, and a retraction usually shares its n with the corrected
row that replaced it. Read the output, do not just count it.

    python common/find_duplicate_claims.py
"""
import collections
import re
import sys

# ⚠ Windows console fix, added 2026-08-18 by the `mlb-paper` session.
# This tool CRASHED partway through its own output -- UnicodeEncodeError on
# U+2212, the real minus sign, which several ledgers use in effect sizes
# (`soccer`'s SO037 is "-0.40c" with a real minus). The default Windows console
# codepage is cp1252 and cannot encode it. It died AFTER printing a screen of
# valid findings, which is the dangerous shape: it looks like it ran.
# Verified pre-existing -- it fails the same way with this session's rows
# stashed. `CLAUDE.md` section 6 tells every session to run this, so it is
# fixed here rather than worked around locally.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


LEDGER = "C:/Users/vinig/trading/LEDGER.md"
src = open(LEDGER, encoding="utf-8").read()

# section boundaries
secs = []
for m in re.finditer(r"^# SECTION (\d+) — (.+)$", src, re.M):
    secs.append((m.start(), m.group(1), m.group(2)))
secs.append((len(src), None, None))


def section_of(pos):
    for i in range(len(secs) - 1):
        if secs[i][0] <= pos < secs[i + 1][0]:
            return f"S{secs[i][1]} {secs[i][2][:34]}"
    return "(front matter)"


STATUS = re.compile(r"\*\*(SETTLED|SUGGESTIVE|UNVERIFIED|BROKEN|RETRACTED)\*\*")
# distinctive numbers: n with thousands separators, and pp/% effect sizes
NUM_N = re.compile(r"\b(\d{1,3}(?:,\d{3})+)\b")
NUM_PP = re.compile(r"([+−-]?\d+\.\d{1,4})\s*(?:pp|%|¢|c\b)")

rows = []
for m in re.finditer(r"^\|\s*\*{0,2}([A-Z]{1,2}\d{3})\*{0,2}\s*\|(.+)$",
                     src, re.M):
    rid, body = m.group(1), m.group(2)
    st = STATUS.search(body)
    rows.append({
        "id": rid,
        "section": section_of(m.start()),
        "status": st.group(1) if st else "?",
        "ns": set(NUM_N.findall(body)),
        "pps": set(NUM_PP.findall(body)),
        "text": body,
    })

print(f"parsed {len(rows)} ledger rows across "
      f"{len({r['section'] for r in rows})} sections\n")

# de-duplicate ids (a row can appear in the loud table and its own section)
by_id = collections.defaultdict(list)
for r in rows:
    by_id[r["id"]].append(r)

# --- 1. same id, conflicting statuses across its appearances --------------
print("=" * 88)
print("1. SAME ID, CONFLICTING STATUS between the loud table and its section")
print("=" * 88)
conflicts = 0
for rid, rs in sorted(by_id.items()):
    sts = {r["status"] for r in rs if r["status"] != "?"}
    if len(sts) > 1:
        conflicts += 1
        print(f"  {rid}: {sorted(sts)}")
        for r in rs:
            print(f"      [{r['status']:10s}] {r['section']}")
print(f"  -> {conflicts} conflicts\n")

# --- 2. distinctive n shared by rows in DIFFERENT sections ----------------
print("=" * 88)
print("2. SAME SAMPLE SIZE in different projects — candidate duplicate claims")
print("=" * 88)
n_index = collections.defaultdict(set)
for r in rows:
    for n in r["ns"]:
        if int(n.replace(",", "")) >= 1000:      # ignore small/common numbers
            n_index[n].add((r["id"], r["section"], r["status"]))

hits = 0
for n, who in sorted(n_index.items(),
                     key=lambda kv: -int(kv[0].replace(",", ""))):
    projs = {w[1] for w in who}
    ids = {w[0] for w in who}
    if len(projs) > 1 and len(ids) > 1:
        hits += 1
        sts = {w[2] for w in who}
        flag = "  <-- DIFFERENT STATUSES" if len(sts) > 1 else ""
        print(f"\n  n={n}{flag}")
        for wid, sec, st in sorted(who):
            print(f"      {wid:6s} [{st:10s}] {sec}")
print(f"\n  -> {hits} sample sizes shared across projects\n")

# --- 3. distinctive effect size shared across sections --------------------
print("=" * 88)
print("3. SAME EFFECT SIZE in different projects")
print("=" * 88)
pp_index = collections.defaultdict(set)
for r in rows:
    for v in r["pps"]:
        try:
            f = abs(float(v.replace("−", "-")))
        except ValueError:
            continue
        if f >= 1.0:            # ignore tiny/common values
            pp_index[v].add((r["id"], r["section"], r["status"]))

hits2 = 0
for v, who in sorted(pp_index.items()):
    projs = {w[1] for w in who}
    ids = {w[0] for w in who}
    if len(projs) > 1 and len(ids) > 1:
        sts = {w[2] for w in who}
        if len(sts) > 1:
            hits2 += 1
            print(f"\n  effect={v}  <-- DIFFERENT STATUSES")
            for wid, sec, st in sorted(who):
                print(f"      {wid:6s} [{st:10s}] {sec}")
print(f"\n  -> {hits2} effect sizes shared across projects with differing status")
