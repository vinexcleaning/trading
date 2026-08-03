"""Write the LLM (Claude) judgments into the G3 validation stub.

Judged against the question the gate actually asks: "is this genuinely on topic
for prediction markets / trading bots / algorithmic trading?"

Two judgment calls worth stating, because they change the score:
  * The four "Backtesting Walk Forward Optimization Global N Futures" uploads have
    on-topic TITLES but music-only transcripts -- no discernible content at all.
    Judged OFF TOPIC, on the reading that "genuinely on topic" means the content
    is about the topic, not that the title claims to be.
  * Black-Scholes (Khan Academy) and a discretionary "when not to trade" commentary
    are finance/trading adjacent but are not about prediction markets, bots, or
    algorithmic method. Judged OFF TOPIC.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUB = ROOT / "reports" / "g3_validation.json"

ON = {2, 3, 4, 5, 6, 7, 9, 12, 13, 14, 16, 17, 18, 23, 25, 26, 27, 28, 29, 30,
      33, 34, 36, 37, 38}

items = json.loads(STUB.read_text(encoding="utf-8"))
assert len(items) == 40, len(items)
for i, it in enumerate(items):
    it["llm_says_on_topic"] = i in ON
    it["llm_judge"] = "claude-opus-5, manual, 2026-08-02"
STUB.write_text(json.dumps(items, indent=2), encoding="utf-8")
print(f"wrote {len(items)} judgments ({len(ON)} on-topic, {len(items)-len(ON)} off-topic)")
