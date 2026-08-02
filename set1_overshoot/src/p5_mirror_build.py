"""Build state for the 400 sibling markets, so Task 3e can price the same match
from both sides independently."""
import json
import pathlib
import subprocess
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

SERIES_LABEL = {"KXATPMATCH": "ATP", "KXWTAMATCH": "WTA",
                "KXATPCHALLENGERMATCH": "CHALL",
                "KXITFMATCH": "ITF-M", "KXITFWMATCH": "ITF-W"}


def main():
    uni = pd.read_parquet(DATA / "universe.parquet")
    sides = pd.read_parquet(DATA / "sides.parquet")
    import glob
    have = set()
    for p in glob.glob(str(DATA / "candles" / "*.parquet")):
        have |= set(pd.read_parquet(p, columns=["ticker"])["ticker"].unique())

    kept = set(uni["ticker"])
    mir = sides[(~sides["ticker"].isin(kept)) & sides["ticker"].isin(have)
                & sides["event_ticker"].isin(set(uni["event_ticker"]))].copy()
    mir["tour"] = mir["series"].map(SERIES_LABEL)
    mir["volume"] = 1.0
    mir = mir[["event_ticker", "ticker", "series", "tour", "result",
               "open_time", "close_time", "volume"]]
    mir.to_parquet(DATA / "mirror_universe.parquet", index=False)
    print(f"{len(mir):,} sibling markets with candles")

    subprocess.run([sys.executable, str(ROOT / "src" / "p1_state.py"),
                    "--subdir", "candles", "--out", "mirror",
                    "--uni", "mirror_universe.parquet"], check=True)


if __name__ == "__main__":
    main()
