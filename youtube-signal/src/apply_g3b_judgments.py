"""Claude's judgments on the G3 HOLDOUT sample (24 videos the fix never saw).

Judging rule applied consistently, and worth stating because it drives most of the
disagreement: the topic is prediction markets / trading bots / ALGORITHMIC trading.
Discretionary, manual, chart-reading trading education is judged OFF TOPIC even
when it is competent and even when it says "backtest" -- it is not about
prediction markets, bots, or systematic method. The brief never draws this line,
and it is where the classifier and I part company most often.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUB = ROOT / "reports" / "g3_validation_holdout.json"

ON = {0, 1, 3, 4, 7, 8, 10, 11, 15, 19, 20, 21, 22}

items = json.loads(STUB.read_text(encoding="utf-8"))
assert len(items) == 24, len(items)
for i, it in enumerate(items):
    it["llm_says_on_topic"] = i in ON
    it["llm_judge"] = "claude-opus-5, manual, 2026-08-02, holdout"
STUB.write_text(json.dumps(items, indent=2), encoding="utf-8")
print(f"wrote {len(items)} holdout judgments "
      f"({len(ON)} on-topic, {len(items)-len(ON)} off-topic)")
