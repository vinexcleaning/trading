"""Read the code of people who have already built first-inning models.

The user's instruction: see what already exists, look at the actual code, test
it if possible. Five repos target exactly our problem. What matters is not that
they exist but (a) what FEATURES they think matter, (b) whether any of them
reports honest out-of-sample validation, and (c) whether any claims an edge
against a real price rather than against nothing.

A repo that predicts NRFI at 70% accuracy has said nothing until you know the
base rate and the price.
"""
import base64
import json
import os
import re
import time

import requests

UA = {"User-Agent": "Mozilla/5.0 (mlb-research/1.0)"}
REP = os.path.join(os.path.dirname(__file__), "..", "reports")
REPOS = [
    "lucasreydman/sharprfi",
    "lucasreydman/nrfi",
    "dbasley/NRFI_Project",
    "phatcobra/nrfi-predictor",
    "austinlmcconnell/mlb-nsfi-model",
    "abudnick8/prop-edge",
]
KEYWORDS = ("first_inning", "first inning", "nrfi", "yrfi", "inning == 1",
            "inning=1", "brier", "log_loss", "roc_auc", "accuracy",
            "backtest", "roi", "kelly", "closing line", "vig", "devig")


def gh(path, tries=3):
    for i in range(tries):
        try:
            r = requests.get(f"https://api.github.com/{path}", headers=UA,
                             timeout=45)
        except requests.RequestException:
            time.sleep(2 * (i + 1))
            continue
        if r.status_code == 403:
            print("    (github rate limit)")
            time.sleep(20)
            continue
        return r
    return None


out = {}
for full in REPOS:
    print("\n" + "=" * 72)
    print(full)
    print("=" * 72)
    info = {}
    r = gh(f"repos/{full}")
    if r is None or r.status_code != 200:
        print(f"  repo http {getattr(r,'status_code','ERR')}")
        continue
    d = r.json()
    info["pushed"] = d["pushed_at"]
    info["stars"] = d["stargazers_count"]
    info["license"] = (d.get("license") or {}).get("spdx_id")
    info["desc"] = d.get("description")
    print(f"  pushed={d['pushed_at'][:10]} stars={d['stargazers_count']} "
          f"licence={info['license']}")
    print(f"  {d.get('description')}")

    # README
    rr = gh(f"repos/{full}/readme")
    if rr is not None and rr.status_code == 200:
        try:
            txt = base64.b64decode(rr.json()["content"]).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            txt = ""
        info["readme_len"] = len(txt)
        # pull the lines that claim performance
        claims = [l.strip() for l in txt.split("\n")
                  if re.search(r"\b(accuracy|brier|auc|log ?loss|roi|profit|"
                               r"win rate|units|record|hit rate)\b", l, re.I)
                  and len(l.strip()) < 200]
        print(f"  README {len(txt)} chars; performance claims found: {len(claims)}")
        for c in claims[:8]:
            print(f"    | {c[:110]}")
        info["claims"] = claims[:12]

    # file tree
    tr = gh(f"repos/{full}/git/trees/HEAD?recursive=1")
    files = []
    if tr is not None and tr.status_code == 200:
        files = [x["path"] for x in tr.json().get("tree", [])
                 if x["type"] == "blob"]
    py = [f for f in files if f.endswith((".py", ".ipynb", ".R", ".js", ".ts"))]
    data = [f for f in files if f.endswith((".csv", ".parquet", ".json"))]
    info["n_files"] = len(files)
    info["n_code"] = len(py)
    info["n_data"] = len(data)
    print(f"  {len(files)} files: {len(py)} code, {len(data)} data")
    print(f"    code: {py[:10]}")
    print(f"    data: {data[:6]}")

    # read the most promising source files
    cand = [f for f in py
            if any(k in f.lower() for k in
                   ("model", "feature", "train", "predict", "backtest",
                    "nrfi", "yrfi", "main"))][:4]
    feats = set()
    for f in cand:
        rf = requests.get(
            f"https://raw.githubusercontent.com/{full}/HEAD/{f}",
            headers=UA, timeout=45)
        if rf.status_code != 200 or len(rf.text) > 400_000:
            continue
        t = rf.text
        hits = [k for k in KEYWORDS if k in t.lower()]
        # crude feature-name extraction
        for m in re.finditer(r"['\"]([a-z0-9_]{4,32})['\"]\s*[:,\]]", t):
            w = m.group(1)
            if any(s in w for s in ("era", "whip", "ops", "woba", "avg", "obp",
                                    "slg", "k_", "bb_", "pitch", "bat", "run",
                                    "inning", "xwoba", "hard", "barrel",
                                    "temp", "wind", "park", "umpire", "rest",
                                    "lineup", "hand", "split")):
                feats.add(w)
        print(f"    {f[:52]:52s} {len(t):7d} chars  signals={hits[:6]}")
    if feats:
        print(f"  FEATURE NAMES seen across their code ({len(feats)}):")
        print(f"    {sorted(feats)[:40]}")
    info["features_seen"] = sorted(feats)[:60]
    out[full] = info
    time.sleep(1.5)

with open(os.path.join(REP, "community_repos.json"), "w",
          encoding="utf-8") as fh:
    json.dump(out, fh, indent=1, default=str)
print("\nwrote reports/community_repos.json")
