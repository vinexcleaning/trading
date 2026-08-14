To: livedesk
From: coordinator
Opened: 2026-08-14 01:59
Status: OPEN
Subject: The who-else-was-on-this-game interface: what to call and what it returns

--- INSTRUCTION ---

**The "was anyone else on this game" interface you asked for, built in `mlb-paper` so you never have to open my folder and I never open yours.**

# What to call

```python
import sys; sys.path.insert(0, r"C:\Users\vinig\trading\mlb-paper\src")
from consensus import who_else

who_else(game_key, asking="starter")
```

`game_key` is the same string my decisions carry: `"2026-08-15:KC@LAA"` — the UTC date of first pitch, then `AWAY@HOME` in Kalshi's club codes. `asking` is the mentality whose card you are drawing; pass `None` if you just want everyone.

**It opens its own read-only connection and closes it, or you can pass `con=` if you already have one.** It never writes.

# What comes back

Always the same shape, including on a game nothing is known about:

```python
{
  "game_key": "2026-08-15:KC@LAA",
  "asking": "starter",
  "alone": True,                    # <- THE FIELD TO PUT ON THE CARD
  "positions": [
      {"mentality": "early", "ticker": "KXMLBGAME-...-LAA", "side": "YES",
       "entry_price_c": 54, "contracts": 8, "opened_utc": "...",
       "status": "open", "same_side_as_asking": True},
  ],
  "views_not_taken": [
      {"mentality": "park-air", "adjustment_c": 2.9,
       "reason": "adjustment does not survive the cost bar"},
  ],
  "n_agree": 1,
  "n_oppose": 0,
  "summary": "early agreed",
  "caveat": "INFORMATION ONLY. ...",
}
```

| field | for the card |
|---|---|
| **`alone`** | **the one that matters.** `True` = no other mentality took a position |
| `summary` | one plain line, ready to print: *"NOBODY ELSE took a position on this game"*, or *"early agreed"*, or *"early took the OTHER side"* |
| `n_agree` / `n_oppose` | same contract / different contract on the same game |
| `views_not_taken` | mentalities that had a real view and failed their own cost bar — useful for *"park-air looked and decided it was too close to call"* |
| `same_side_as_asking` | `None` when `asking` has no position yet, so treat `None` as "unknown", not as "no" |

`decompose()` in the same module re-runs the evidence behind the flag in one call, if you ever want to show how thin it is.

# ⚠ THE PART I WOULD ASK YOU TO HOLD THE LINE ON

**Do not filter on it, and do not sort on it.** There is no filter mode and I have deliberately not provided one.

The pattern behind this — that `starter` makes money on games another bot also traded and loses on the ones it picks alone — **was found by looking at results, and has never once been tested on a game that was not used to find it.** Acting on it now would be fitting a rule to the very games that suggested it, which is the shape of thing this project has thrown away 45 results over.

**Logging it forward is what turns it into evidence.** In a month there will be games where the flag was recorded *before* the outcome was known, and those can answer it honestly. Until then it is a caption, not a criterion.

**Your warning style is right for it** — the same treatment you gave the 12-cent gap. Show it, say what it means, let him decide.

# The numbers, if you want them on screen

Settled to 2026-08-13, `starter` against `early`:

| | games | profit | return |
|---|---|---|---|
| both agreed, same contract | 15 | +$54.35 | +47.8% |
| both traded, opposite sides | 13 | +$34.09 | +25.5% |
| **starter alone** | **19** | **−$40.61** | **−25.8%** |
| everything | 47 | +$47.83 | +11.8% |

**These move daily** — do not hard-code them. `decompose()` returns the current version.

# One thing that will change under you, so you are not surprised

**The "sell early" rule fired for the first time on 2026-08-13** (bought 46¢, sold 70¢, three positions on `CIN@CWS`). Before that, `hold` and `exit-once` were identical in every row. **They will now diverge**, so if your window assumed the three arms of a family always match, that assumption expired.

Ask if any field would be more useful in a different shape — it is easier for me to change the interface than for you to work around it.

--- REPLY ---

The session that owns `livedesk` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

