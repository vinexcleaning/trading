"""Probe tennisabstract.com per-player match files.

The question that decides the data-supply fix: do these files carry serve
statistics, do they cover Challenger/ITF, and how current are they?
"""
import json
import re

import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch(player, career=False):
    url = (f"https://www.tennisabstract.com/jsmatches/"
           f"{player}{'Career' if career else ''}.js")
    r = requests.get(url, headers=H, timeout=60)
    r.raise_for_status()
    return r.text


def extract_arrays(text):
    """Bracket-match each `var name = [[ ... ]]` block (regex is unreliable here)."""
    out = {}
    for m in re.finditer(r"var\s+(\w+)\s*=\s*\[\[", text):
        name = m.group(1)
        start = text.index("[[", m.end() - 2)
        depth, i = 0, start
        while i < len(text):
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = text[start:i + 1]
        try:
            out[name] = json.loads(body)
        except json.JSONDecodeError as e:
            out[name] = f"UNPARSED ({e}) len={len(body)} head={body[:120]}"
    return out


txt = fetch("NovakDjokovic")
print(f"file length {len(txt)}")
print("var names present:")
print(sorted(set(re.findall(r"var\s+(\w+)\s*=", txt))))

arrs = extract_arrays(txt)
print(f"\narrays found: {[(k, len(v) if isinstance(v, list) else v[:60]) for k, v in arrs.items()]}")

for name, rows in arrs.items():
    if not isinstance(rows, list) or not rows:
        continue
    print(f"\n=== {name}: {len(rows)} rows x {len(rows[0])} cols ===")
    print("  most recent row, by column index:")
    for i, v in enumerate(rows[-1]):
        print(f"    [{i:2d}] {v!r}")
    print("\n  first row (oldest):")
    print(f"    {rows[0]}")
    dates = [r[0] for r in rows if r and r[0]]
    if dates:
        print(f"\n  date range: {min(dates)} .. {max(dates)}")
