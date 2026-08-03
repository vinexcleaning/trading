# AUDIT PROMPT — reconstruct ground truth

Run this in Claude Code on the machine that has the project files. Read-only. Expect 1–3 hours.

---

You are performing a **read-only audit**. You are reconstructing what has actually been tested and what was actually found across several months of trading research spread over multiple chat sessions, multiple Claude Code sessions, two accounts, and several project folders.

## Hard rules

1. **Read only.** Do not modify, delete, or run any existing project code. Do not start, stop, or touch any bot or recorder. Do not place, cancel, or modify any order. Do not call any authenticated trading endpoint.
2. **Do not do new research.** You are inventorying, not investigating. If you find an open question, record it as open — do not go answer it.
3. **Do not trust summaries, including mine and including the user's.** Where a chat says "we found X," look for the code and the output that produced X. A claim with no artifact behind it is `UNVERIFIED`, no matter how confidently it was stated.
4. **Write as you go**, not at the end. If you run out of context, the partial ledger must still be useful.

## Inputs

- `audit/pro_chats.json` and `audit/max_chats.json` — full Claude conversation exports (JSON array; each conversation has messages with timestamps). Filter to trading-related conversations only; ignore everything else and don't summarise unrelated personal chats.
- Every project folder on this machine. Find them yourself — search for git repos, Python projects, and directories containing Kalshi/Polymarket/tennis/BTC/weather code.
- Any existing `MORNING_REPORT.md`, `PROGRESS.md`, `DECISIONS.md`, `contract_spec.md`, results files, notebooks, parquet outputs, and logs.

## Output 1 — `LEDGER.md`, the main deliverable

One row per distinct **claim**. A claim is any assertion about whether something works, what a number was, or what was concluded. Columns:

| Field | Meaning |
|---|---|
| ID | C001, C002… |
| Claim | The assertion, in one sentence |
| Project | Which thread it belongs to |
| Source | Chat date / file path / script name |
| Artifact | The actual script and output file that produced it — or `NONE` |
| Sample | n, and **the unit of observation** (bets? markets? matches? candles?) |
| Validation | Which of these were done: out-of-sample split, look-ahead test, clustering by market, multiple-testing correction, synthetic control |
| Status | `SETTLED` / `SUGGESTIVE` / `UNVERIFIED` / `BROKEN` / `RETRACTED` |
| Note | Anything that changes how much to trust it |

Status definitions — apply them strictly:

- **SETTLED** — reproducible artifact, adequate n at the correct unit of observation, validated out-of-sample, and either a structural/arithmetic result or a well-powered statistical one. Safe to build on.
- **SUGGESTIVE** — real artifact, but underpowered, unclustered, in-sample, or uncorrected. Directionally interesting, not decision-grade.
- **UNVERIFIED** — asserted in a chat with no artifact you can locate. Most claims will land here and that's the point of the exercise.
- **BROKEN** — the artifact exists but has a defect that invalidates it (look-ahead leak, pseudo-replication, wrong unit of observation, silent data corruption).
- **RETRACTED** — corrected later in the same or a later session. **Flag these loudly.** A retracted conclusion that survived into someone's memory of the project is the single most dangerous artifact you can find, and there are known instances of it here.

## Output 2 — `FAILURE_MODES.md`

Search specifically for these five patterns and list every instance with file and line. They have all occurred at least once already:

1. **Pseudo-replication** — many observations from one underlying event treated as independent (many bets on one match; many candles from one market; many fills from one settlement). Check the unit of observation on every CI in the ledger.
2. **Look-ahead leakage** — any feature whose knowability timestamp is at or after the decision timestamp. One known past instance: a price anchor set at or after settlement.
3. **Silent data corruption** — writers that produce correct row counts with empty or malformed content. One known past instance: an orderbook parser unwrapping a key that doesn't exist.
4. **Floating-point fee dust** — `0.07*100*0.5*0.5*100` evaluates to `175.00000000000003`, so a naive `ceil()` overcharges by a cent. This bug has appeared in at least three separate codebases here. Find every independent implementation of the fee formula and list them.
5. **Benchmark inflation** — beating a weak benchmark (climatology, a coinflip, a near-settlement price) reported as if it were beating the market mid.

## Output 3 — `GAPS.md`

What was never tested. Be specific and include these explicitly, confirming or refuting each:

- Whether the trading-server owner's posted calls have any edge (persistence, shrinkage for sample size, edge decay after the call, adverse selection). Believed never measured.
- Whether any strategy works as a **maker** rather than a taker. Every cost-bar conclusion so far appears to assume crossing the spread, and the maker fee is a quarter of taker.
- Whether any model beats the Kalshi **mid** at adequate n, for weather or anything else.
- Whether the tennis structural-event signal is inverted (does fade-the-drop beat ride-the-rise?).
- Set-score and multi-leg/parlay tennis markets, where correlated legs may be priced as independent.
- Anything else you find that was proposed and never executed.

## Output 4 — `STATUS.md`

The file every future session reads first. Keep it under two pages:

- Which threads are alive, which are closed, and the one-line reason for each
- What is currently running on this machine (recorders, bots, scanners) and where
- What data exists on disk, where, how much, and covering what period
- What must not be touched, and why
- The single next action per live thread

## Output 5 — `INVENTORY.md`

Every project folder, what it is, whether it's live or dormant, its git status, and whether it duplicates another folder. Flag duplicated logic across projects — especially the fee formula.

## Method

Work chat-export first (cheap, gives you the narrative and the claim list), then code (expensive, gives you the artifacts), then reconcile the two. The reconciliation is where the value is: every claim in a chat that has no matching artifact in the code is a finding.

Commit after each output file. Update `PROGRESS.md` as you go so an interrupted run is still useful.

Begin.
