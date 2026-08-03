"""STEP 4 — load a hand-read extraction. Validation, not trust.

The YouTube project enforces "no quote, no point" in code rather than relying on
the model to behave. The GitHub equivalent is: **no file path or commit SHA, no
claim.** Anything without evidence is rejected here, loudly, and not stored.

Usage:  python src/load_extraction.py reports/extractions/<owner>__<repo>.json
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402

EVIDENCE_RE = re.compile(
    r"([A-Za-z0-9_./-]+\.(py|ts|tsx|js|rs|go|md|toml|txt|json|yml|yaml|ipynb|sol|cfg|sh|lock|"
    r"csv|parquet|env|example)(:\d+)?|(^|/)(Makefile|Dockerfile)\b|\b[0-9a-f]{7,40}\b|https?://)")


def has_evidence(s):
    return bool(s) and bool(EVIDENCE_RE.search(str(s)))


def main():
    if len(sys.argv) < 2:
        print("usage: load_extraction.py <file.json>")
        sys.exit(2)
    path = sys.argv[1]
    with open(path, encoding="utf-8") as fh:
        x = json.load(fh)

    con = db.connect()
    fn = x["full_name"]
    rejected = []

    row = con.execute("SELECT full_name FROM repos WHERE full_name=?", (fn,)).fetchone()
    if not row:
        con.execute("INSERT INTO repos (full_name, url) VALUES (?,?)",
                    (fn, f"https://github.com/{fn}"))

    # --- claimed results must have an artifact path, or be marked as unbacked ---
    artifact = x.get("artifact_behind_claim") or ""
    if x.get("claimed_results") and not has_evidence(artifact) and artifact.lower() not in (
            "no", "none", "no artifact"):
        rejected.append(f"artifact_behind_claim {artifact!r} has no path/SHA — set to 'no'")
        artifact = "no"

    con.execute(
        """UPDATE repos SET what_it_does=?, strategy_type=?, venue=?, claimed_results=?,
             artifact_behind_claim=?, verdict=?, notes=?, read_at=? WHERE full_name=?""",
        (x.get("what_it_does"), x.get("strategy_type"), x.get("venue"),
         x.get("claimed_results"), artifact, x.get("verdict"), x.get("notes"),
         datetime.date.today().isoformat(), fn))

    for s in x.get("strategies", []):
        ev = s.get("backtest_evidence") or s.get("file_path") or ""
        if not has_evidence(ev):
            rejected.append(f"strategy {s.get('name')!r}: no file path or SHA — NOT STORED")
            continue
        con.execute(
            """INSERT INTO strategies (repo,name,description,entry_logic,exit_logic,parameters,
                 costs_modelled,backtest_evidence,file_path) VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(COALESCE(repo,''),COALESCE(name,'')) DO UPDATE SET
                 description=excluded.description, entry_logic=excluded.entry_logic,
                 exit_logic=excluded.exit_logic, parameters=excluded.parameters,
                 costs_modelled=excluded.costs_modelled,
                 backtest_evidence=excluded.backtest_evidence, file_path=excluded.file_path""",
            (fn, s.get("name"), s.get("description"), s.get("entry_logic"), s.get("exit_logic"),
             s.get("parameters"), int(bool(s.get("costs_modelled"))), ev, s.get("file_path")))

    for d in x.get("dependencies", []):
        if not has_evidence(d.get("seen_in")):
            rejected.append(f"dependency {d.get('name')!r}: seen_in has no file path — NOT STORED")
            continue
        con.execute(
            """INSERT INTO dependencies (name,kind,what_it_is,repo_count,seen_in,url,note)
               VALUES (?,?,?,1,?,?,?)
               ON CONFLICT(COALESCE(name,'')) DO UPDATE SET
                 repo_count=dependencies.repo_count+1,
                 seen_in=dependencies.seen_in || ' | ' || excluded.seen_in,
                 what_it_is=COALESCE(NULLIF(excluded.what_it_is,''), dependencies.what_it_is)""",
            (d.get("name"), d.get("kind"), d.get("what_it_is"),
             f"{fn}:{d.get('seen_in')}", d.get("url"), d.get("note")))

    for s in x.get("data_sources", []):
        if not has_evidence(s.get("seen_in")) and not has_evidence(s.get("url")):
            rejected.append(f"data_source {s.get('name')!r}: no path or URL — NOT STORED")
            continue
        con.execute(
            """INSERT INTO data_sources (name,url,free,covers,venue,seen_in,note)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(COALESCE(name,''),COALESCE(url,'')) DO UPDATE SET
                 seen_in=data_sources.seen_in || ' | ' || excluded.seen_in,
                 covers=COALESCE(NULLIF(excluded.covers,''), data_sources.covers)""",
            (s.get("name"), s.get("url"), s.get("free"), s.get("covers"), s.get("venue"),
             f"{fn}:{s.get('seen_in')}", s.get("note")))

    con.commit()
    db.log(con, "extract", f"{fn} rejected={len(rejected)}")
    print(f"loaded {fn}: {len(x.get('strategies',[]))} strategies, "
          f"{len(x.get('dependencies',[]))} deps, {len(x.get('data_sources',[]))} sources")
    for r in rejected:
        print("  REJECTED:", r)


if __name__ == "__main__":
    main()
