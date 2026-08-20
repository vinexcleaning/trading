"""Keep the test suite off his real files and off the network.

⚠ WHY THIS FILE EXISTS, AND IT IS THE SAME REASON TWICE.

**Once:** a green run of 150 tests deleted `data/ledger.json` -- his real record
of his real money -- because `Ledger.__init__` bound the path at definition and
the redirect in a fixture did nothing.

**Twice, on 2026-08-19:** the two-machine guard went into the refresh loop, and
`test_button_never_moves.py` builds a real `Desk` and runs a real refresh. So
the suite started writing his real `data/desk.lock` **and posting a claim to
ntfy under this computer's name.** The next time he opened the desk it would
have refused to start, naming a pytest process that had exited hours earlier.

Neither was visible in the test output. Both were found by running the tool
afterwards and reading what it printed.

**So the protection is here, once, applied to every test automatically**, rather
than remembered file by file. A test that genuinely wants the real path has to
say so out loud.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def _never_his_real_files(tmp_path, monkeypatch):
    """Redirect every real path this project writes, and cut the network.

    Applied to EVERY test, including ones written later by someone who has
    never read this file. That is the point -- the two incidents above were
    both caused by a new caller reaching a default path that an older test had
    no reason to think about.
    """
    import onemachine

    monkeypatch.setattr(onemachine, "LOCK_PATH", tmp_path / "desk.lock")

    # ⚠ AND NO CLAIM GOES OUT. His ntfy topic is set in this shell, so without
    # this the suite publishes this machine's name to a public topic on every
    # run -- and a claim posted by a test is indistinguishable from a claim
    # posted by a real desk, which is precisely what would then block him.
    monkeypatch.setenv("KALSHI_NTFY_TOPIC", "")
    monkeypatch.setenv("KALSHI_HEALTHCHECK_URL", "")

    import alerts
    monkeypatch.setattr(alerts, "STATE_PATH", tmp_path / "alerts_state.json")
