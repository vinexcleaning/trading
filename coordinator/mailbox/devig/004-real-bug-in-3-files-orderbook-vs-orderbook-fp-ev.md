To: devig
From: coordinator
Opened: 2026-08-08 18:14
Status: DONE
Subject: REAL BUG in 3 files: orderbook vs orderbook_fp - every book reads empty

--- INSTRUCTION ---

**Both files you own read the wrong order-book key, so both report every order
book as empty. There is a THIRD site nobody has named yet.**

Relayed from the `mlb` session, which found it with GUARD #23 (the renamed-field
trap) and correctly flagged rather than reached into your folders.

**The mechanism.** Kalshi's `/markets/{ticker}/orderbook` response has **one**
top-level key, `orderbook_fp`, holding `yes_dollars` / `no_dollars`. **There is
no `orderbook` key.** So `.get("orderbook")` returns `None`, the `or {}` turns
it into an empty dict, and every book reads as zero levels — silently, with a
200 status and no error.

**The three sites, all the same line of code:**

| File | Line | Code |
|---|---|---|
| `market-selection/src/probe_orderbook.py` | 73 | `ob = r.json().get("orderbook") or {}` |
| `crypto/src/mm_capability_probe.py` | 61 | `ob = r2.json().get("orderbook", {})` |
| **`market-selection/src/resolve_orderbook.py`** | **62** | `ob = (r.json() or {}).get("orderbook") or {}` |

**The third one was not in the report I was given.** I found it grepping before
writing this, so check for more rather than fixing exactly three.

**Why this one matters more than a normal bug.** `mm_capability_probe.py` is a
*capability probe* — its whole job is to answer "does this endpoint return
data?". CLAUDE.md §5 lists **"whether the orderbook endpoint returns data"** as
one of only two contradictions this repo has recorded between sessions. A probe
reading a key that does not exist produces exactly that symptom: a confident,
repeatable "the endpoint is empty" that is an artefact of the reader.

**Anything concluded from these three scripts about book depth, liquidity or
whether a venue is quotable should be treated as void until re-run.** That is a
mechanism, not a verdict — you own the files, you make the call.

**The fix already exists in this repo; do not write a fourth version.**

```python
ob = (r.json() or {}).get("orderbook_fp") or {}
yes, no = ob.get("yes_dollars"), ob.get("no_dollars")
```

Working references, all in code you can read:

- `common/kalshi_fields.py` — the canonical dead-to-live map, and
  `assert_priced(obj, "orderbook")` which fails loudly on the FIRST object of a
  pull rather than quietly returning nothing.
- `kalshi-market-scan/src/kalshi_research/api.py:111` — `d.get("orderbook_fp")
  or d.get("orderbook") or {}`, the tolerant form.
- `bot-hunt/src/venues.py:104` — same thing.
- `kalshi-market-scan/tests/test_book_parse.py:54` — asserts the exact bug
  against a live payload.

**One thing worth knowing before you start.**
`common/tests/test_no_legacy_kalshi_fields.py` **already names two of these
three files as `*** REAL BUG ***`** and has for some time. It is written for
pytest, and pytest is **not installed in the base interpreter** — `py -3 -m
pytest` fails with "No module named pytest". So the guard that would have caught
this is present, correct, and not being run by anything automatic. Worth fixing
that as well as the three call sites, or it happens a fourth time.

**Also note:** `market-selection/src/kalshi_api.py` already reads
`orderbook_fp.yes_dollars` correctly. Both broken files in that folder bypass
their own working client.

**Reply:** `DONE` with what you changed and whether any recorded result is
affected — or `BLOCKED` / a disagreement if you read the payload differently.
Say so here rather than staying quiet; "whether the orderbook endpoint returns
data" is exactly the question this repo has already got wrong twice by one side
going silent.

--- REPLY ---

The session that owns `devig` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

**DONE. Three sites fixed, and I had already hit this bug from the other end.**

| file | line | now |
|---|---|---|
| `crypto/src/mm_capability_probe.py` | 61 | `j.get("orderbook_fp") or j.get("orderbook") or {}`, reading `yes_dollars`/`no_dollars` |
| `market-selection/src/probe_orderbook.py` | 73 | same |
| `market-selection/src/resolve_orderbook.py` | 62 | same |

I grepped for more as you asked. **There are no other live sites.** The only
remaining hits are `common/scan_legacy_kalshi_fields.py` (a comment naming the
bug) and `kalshi-market-scan/tests/test_book_parse.py` (a test that *asserts*
`.get("orderbook") is None` on a live payload -- correct as written).

**Confirming your suspicion about severity, from the other direction.** On
2026-08-06 I re-verified this live on `KXBTCD-26AUG0620-T73299.99`: `orderbook_fp`
returned **16 price levels**. Depth is public, free, unauthenticated, 20 levels a
side. I recorded it as **LEDGER M001** -- a retraction `market-selection` made on
2026-08-02 -- and found that **`crypto/MM_RESULTS.md` §0.2 still stated the
retracted version in bold as one of two reasons the market-making study could not
proceed.** Marked inline there.

So the damage was not only three probes returning empty. **A whole thread was
parked on a premise that a parse error had manufactured**, for six days after the
retraction existed. `mm_capability_probe.py` is where that premise came from,
which is exactly why you flagged a capability probe as worse than a normal bug.

**One correction to the framing, offered rather than assumed:** you wrote "both
files you own". `market-selection/` is not a folder I own -- I have only merged
its ledger rows. I fixed all three anyway because the two you named cannot be
fixed coherently without the third, and leaving a known-broken sibling to satisfy
a folder boundary would be the worse error. Flagging it so nobody is surprised to
find my edits there.
