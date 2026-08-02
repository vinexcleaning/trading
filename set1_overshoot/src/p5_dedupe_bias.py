"""The dedupe-selection leak: evidence, magnitude, and the fix.

Phase 0 kept "the higher-volume side" of each mirrored pair. Volume is read from
the API after settlement and the winning side attracts more trading, so that
rule conditions on the outcome. This quantifies it and checks the replacement.
"""
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def main():
    raw = json.loads((DATA / "markets_raw.json").read_text(encoding="utf-8"))
    rows = []
    for _, ms in raw.items():
        for m in ms:
            if m.get("result") in ("yes", "no"):
                rows.append((m["event_ticker"], m["ticker"], m["result"],
                             float(m.get("volume_fp") or 0),
                             float(m.get("open_interest_fp") or 0)))
    d = pd.DataFrame(rows, columns=["ev", "tk", "res", "vol", "oi"])
    d = d.groupby("ev").filter(lambda x: len(x) == 2)

    out = []

    def w(s=""):
        print(s, flush=True)
        out.append(s)

    w("DEDUPE SELECTION LEAK")
    w("=" * 72)
    w(f"paired events: {d['ev'].nunique():,}")
    w("")
    w("If a dedupe rule is outcome-independent, the kept side must win exactly")
    w("half the time. Anything else means the rule is reading the answer.")
    w("")
    w(f"{'rule':<36} {'P(kept wins)':>13} {'95% band':>16} {'z':>8}")
    w("-" * 76)

    def rate(df, label):
        top = df.groupby("ev").head(1)
        p = (top["res"] == "yes").mean()
        se = (p * (1 - p) / len(top)) ** 0.5
        w(f"{label:<36} {p:>13.4f} {'+/-%.4f' % (1.96 * se):>16} "
          f"{(p - 0.5) / se:>+8.2f}")
        return p

    v = rate(d.sort_values(["ev", "vol"], ascending=[True, False]),
             "higher VOLUME  (the Phase 0 rule)")
    rate(d.sort_values(["ev", "oi"], ascending=[True, False]),
         "higher OPEN INTEREST")
    a = rate(d.sort_values(["ev", "tk"]), "first TICKER alphabetically  (FIX)")
    rate(d.sort_values(["ev", "tk"], ascending=[True, False]),
         "last TICKER alphabetically")
    h = d.copy()
    h["hh"] = [hash(t) % 2 for t in h["tk"]]
    rate(h.sort_values(["ev", "hh", "tk"]), "hash-of-ticker parity")

    w("")
    tot = d.groupby("ev")["vol"].sum()
    win = d[d["res"] == "yes"].set_index("ev")["vol"]
    share = (win / tot).dropna()
    w(f"Winning side's share of the event's total volume: "
      f"mean {share.mean():.4f}, median {share.median():.4f}")
    w(f"Winning side has the larger volume in {100 * (share > 0.5).mean():.1f}% "
      f"of events.")
    w("")
    w("MECHANISM. Kalshi runs a separate order book for each side of a match, so")
    w("the two books do not share volume. As a match resolves, trading "
      "concentrates")
    w("in the side that is winning. Reading volume after settlement therefore")
    w("reveals the outcome, and picking the busier book picks the winner "
      f"{100 * v:.1f}% of")
    w("the time.")
    w("")
    w("WHY IT MATTERED SO MUCH. The analysis orients every match to the "
      "favourite, so")
    w("it splits on whether the kept (busier) player IS the favourite. When it "
      "is, the")
    w("winner-biased side is the favourite and the favourite appears to "
      "overperform its")
    w("price. When it is not, the same bias makes the favourite appear to")
    w("underperform. One selection error, entering the two halves with "
      "opposite sign.")
    w("")
    w(f"FIX: lexicographic ticker order, {a:.4f} (z = "
      f"{(a - 0.5) / ((a * (1 - a) / d['ev'].nunique()) ** 0.5):+.2f}). Player-name")
    w("abbreviations cannot know who wins. Measured, not assumed.")

    (ROOT / "reports" / "p5_dedupe_bias.txt").write_text("\n".join(out),
                                                         encoding="utf-8")
    print(f"\n-> {ROOT / 'reports' / 'p5_dedupe_bias.txt'}")


if __name__ == "__main__":
    main()
