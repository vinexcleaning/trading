"""Static audit: every read of a post-settlement field, in every codebase here.

The volume-dedupe bug was not a one-off. It is an instance of a class: any
selection, filter, sort, dedupe, join or sample that reads a field only knowable
at or after settlement. Feature-level leak tests cannot see it, because the leak
is not in a feature -- it is in which rows exist.

This finds the occurrences. Classification is done by hand afterwards, because
"is this a filter or a label" is not decidable by regex.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]

SCOPES = {
    "set1_overshoot (this phase)": pathlib.Path(r"C:\Users\gianf\kalshi\set1_overshoot\src"),
    "kalshi Stage 0-5 player model": pathlib.Path(r"C:\Users\gianf\kalshi\src"),
    "crypto": pathlib.Path(r"C:\Users\gianf\crypto\src"),
    "kalshi_backup (Desktop copy)": pathlib.Path(r"C:\Users\gianf\Desktop\kalshi_backup\src"),
}

# Fields whose value is only knowable at/after settlement, or which keep moving
# until then. Grouped so the report can explain why each is unsafe.
FIELDS = {
    "volume": r"\bvolume(_fp|_24h_fp)?\b",
    "open_interest": r"\bopen_interest(_fp)?\b",
    "result": r"[\"']result[\"']|\bresult\b\s*==",
    "settlement_value": r"settlement_value(_dollars)?",
    "settlement_ts": r"settlement_ts|settlement_timer",
    "expiration_value": r"expiration_value",
    "last_price": r"last_price(_dollars)?|[\"']last[\"']",
    "previous_price": r"previous_(price|yes_bid|yes_ask)(_dollars)?",
    "close_time": r"\bclose_time\b",
    "status": r"[\"']status[\"']|\bstatus\b\s*(==|\.isin)",
    "liquidity": r"liquidity(_dollars)?",
    "updated_time": r"\bupdated_time\b",
    "duration/endpoint-derived": r"\bdur_min\b|\bplausible\b|\bt1\b\s*=|minutes",
}

# Selection verbs: a post-settlement field inside one of these is the danger.
SELECT = re.compile(
    r"sort_values|groupby|\.head\(|\.tail\(|nlargest|nsmallest|drop_duplicates"
    r"|\bwhere\(|\.loc\[|\.query\(|isin\(|\bfilter\b|sample\(|argsort|argmax"
    r"|argmin|\bif\b.*[<>=]|\[\s*df|\bmask\b|idxmax|idxmin|rank\(", re.I)


def main():
    lines = []

    def w(s=""):
        print(s, flush=True)
        lines.append(s)

    w("POST-SETTLEMENT FIELD OCCURRENCES")
    w("=" * 100)
    total = 0
    for scope, d in SCOPES.items():
        if not d.exists():
            w(f"\n### {scope}: NOT PRESENT ON THIS MACHINE ({d})")
            continue
        w(f"\n### {scope}  --  {d}")
        w("")
        files = sorted(d.glob("*.py"))
        for f in files:
            try:
                src = f.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            hits = []
            for i, line in enumerate(src, 1):
                s = line.strip()
                if s.startswith("#") or not s:
                    continue
                for name, pat in FIELDS.items():
                    if re.search(pat, line):
                        sel = bool(SELECT.search(line))
                        hits.append((i, name, sel, s[:110]))
                        break
            if hits:
                total += len(hits)
                w(f"  {f.name}")
                for i, name, sel, s in hits:
                    flag = "SELECT?" if sel else "       "
                    w(f"    {i:5d} {flag} [{name:24s}] {s}")
    w("")
    w(f"total occurrences: {total}")
    w("")
    w("SELECT? marks a line where a post-settlement field appears alongside a")
    w("filtering/sorting/dedupe construct. It is a prompt to read the line, not")
    w("a verdict -- classification is in SELECTION_AUDIT.md.")

    outp = ROOT / "reports" / "audit_occurrences.txt"
    outp.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n-> {outp}")


if __name__ == "__main__":
    main()
