"""Apply B (Build) scores to the videos read before the axis existed.

Every quote below is VERBATIM from the cached transcript, pulled by
src/b_candidates.py and then judged. Nothing here is paraphrased, because a
paraphrased quote is a fabricated citation and the whole evidence rule exists to
stop exactly that.

Two deliberate withholdings, both of which look like B points and are not:

  MyCjPs0pRy4  says "sadly I remove the GitHub" -- the artifact is GONE, so B5
               must NOT fire. A named repo that no longer exists is the opposite
               of a verifiable artifact.
  rrLnJO5x_Po  titled "Full Code" but says "this one's not on my GitHub". Same
               call. The title is not evidence; the transcript is.

And one where the absence of code language is the point: rDkVmkrzpbI explicitly
says "too much into the actual code, but this" -- he is declining to show code,
so B1 does not fire even though the video is a genuine build guide otherwise.

Most of the corpus scores B=0. That is the correct result, not a gap: these are
explanation videos, and explanation is what the S axis is for.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

B_SCORES = {
    # ---- genuine build tutorials -------------------------------------------
    "yYjo1lzNoGI": [  # Robot Traders - Kalshi API in Python. B=8
        ("B1", 0, "These lines of code displays the real"),
        ("B2", 384, "series endpoint, then we'll do events"),
        ("B3", 129, "terminal, pip install Kalshi Python"),
        ("B5", 11, "free and open source, link below"),
    ],
    "lVqF8oLzVAU": [  # wangr - Polymarket CLOB API, real order placed+cancelled. B=7
        ("B1", 247, "wrapper function for it. We uh add our"),
        ("B2", 339, "is uh the value endpoint."),
        ("B3", 64, "your private key. If you have, um, Metam"),
    ],
    "rDkVmkrzpbI": [  # Emil Nielsen - Polymarket WebSockets. B=6
        ("B2", 187, "markets that you can subscribe to which"),
        ("B3", 300, "authenticate with an API key and and"),
        ("B4", 343, "and uh failed"),
    ],
    # ---- partial: real code, but the artifact is gone -----------------------
    "MyCjPs0pRy4": [  # JunkieAI. B=5 -> lifts SKIP to ABSORB, correctly short of BUILD
        ("B1", 230, "code so we can open it on our um editor"),
        ("B3", 515, "this we going to get some private key"),
    ],
    # ---- incidental build signal, not build tutorials -----------------------
    "rrLnJO5x_Po": [("B4", 383, "open, you have to go get the bid price")],
    "btG5YpvPkwE": [("B5", 672, "Karpathy dropped this GitHub repo called")],
    "vT0qMNgOkxo": [("B5", 58, "open-source repository here, complete")],
}

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "reports" / "extractions"


def main():
    for vid, comps in B_SCORES.items():
        p = EXT / f"{vid}.json"
        if not p.exists():
            print(f"  {vid}: no extraction file, skipped")
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        d["b_components"] = [
            {"component": c, "timestamp_s": t, "quote": q} for c, t, q in comps
        ]
        p.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  {vid}: {len(comps)} B components -> {p.name}")
    print("\nnow run: for f in the files above, python src/load_extraction.py <file>")


if __name__ == "__main__":
    main()
