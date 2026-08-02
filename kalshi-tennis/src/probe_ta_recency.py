"""Is tennisabstract.com current, or is it frozen like the GitHub repos?"""
import json
import re

import requests

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def get(url):
    r = requests.get(url, headers=H, timeout=60)
    r.raise_for_status()
    return r.text


def extract_arrays(text):
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
        try:
            out[name] = json.loads(text[start:i + 1])
        except json.JSONDecodeError:
            pass
    return out


def scalars(text):
    out = {}
    for m in re.finditer(r"var\s+(\w+)\s*=\s*'([^']*)'\s*;", text):
        out[m.group(1)] = m.group(2)
    for m in re.finditer(r"var\s+(\w+)\s*=\s*(-?\d+)\s*;", text):
        out.setdefault(m.group(1), m.group(2))
    return out


for player in ["NovakDjokovic", "JannikSinner", "ArynaSabalenka", "IgaSwiatek"]:
    for career in (False, True):
        url = (f"https://www.tennisabstract.com/jsmatches/"
               f"{player}{'Career' if career else ''}.js")
        try:
            txt = get(url)
        except Exception as e:  # noqa: BLE001
            print(f"{player:18s} career={career!s:5s} ERR {e}")
            continue
        arrs = extract_arrays(txt)
        sc = scalars(txt)
        for name, rows in arrs.items():
            dates = [r[0] for r in rows if r and r[0]]
            if dates:
                print(f"{player:18s} career={career!s:5s} {name:12s} "
                      f"n={len(rows):5d} {min(dates)}..{max(dates)}  "
                      f"rank={sc.get('currentrank')} lastdate={sc.get('lastdate')}")

print("\n--- site-level: current rankings file ---")
for u in ["https://www.tennisabstract.com/jsplayers/curr_rank_atp.js",
          "https://www.tennisabstract.com/jsplayers/atp_recent.js",
          "https://www.tennisabstract.com/reports/atp_elo_ratings.html"]:
    try:
        t = get(u)
        print(f"OK  {u}  len={len(t)}")
        print("    " + t[:300].replace("\n", " "))
    except Exception as e:  # noqa: BLE001
        print(f"ERR {u} :: {e}")
