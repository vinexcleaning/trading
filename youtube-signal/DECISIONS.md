# DECISIONS — youtube-signal

Method decisions taken without asking, with the measurement that forced each
one. Conservative reading taken wherever ambiguous.

> **Written 2026-08-08 by the `social-signal` session**, on instruction from the
> coordinator (`coordinator/mailbox/signal/005`), because `CLAUDE.md` §10 lists
> this file as missing and the `signal` slug owns this folder. **It is
> reconstructed from `HANDOFF.md`, the source and the git log, not written by the
> session that took the decisions.** Where reasoning was not recorded at the
> time, that is said rather than invented. A session returning to this folder
> should correct anything misread here.

---

## D1 — The transcript is read in-session, not through an API
**2026-08-03.** The previous handoff recorded a blocker: *"buy $5 of Anthropic
API credit"* before any video could be read. **That was wrong.** The session
model reads the transcript directly. 33 videos were read for **$0.00 and 0
YouTube API quota units**.
`src/read_video.py` is written, type-checked and dry-runnable and **has still
never executed**. It is a draft, not a component; its docstring says so.

## D2 — S and H are never averaged, and never combined into one number
**Throughout.** A video can carry genuinely useful tooling *and* lie about its
returns. Averaging gives it a middling score and destroys both facts. Kept
apart, the answer is *use its tools, discount its results* — which is what
`ABSORB_RESULTS_DISCOUNTED` exists to express.

## D3 — A component with no timestamp and no short verbatim quote is dropped
**2026-08-03.** The schema puts `NOT NULL` on both, and `validate_response()`
discards any component arriving without them rather than trusting the model to
have obeyed the instruction. **A component you cannot quote did not happen.**
Quotes are capped under 15 words.

## D4 — The B axis was added because S structurally could not score a build
**2026-08-03.** S1, S2 and S3 all require a **trading claim**. A pure API
tutorial makes none, so it could score at most S4+S5 = 3 and was auto-SKIP
however good the code was. Part Time Larry's Kalshi build scored **S=3 H=9 →
SKIP** with working code, a public repo and an honest itemised account.
**Conservative reading:** claims still reached `KNOWLEDGE.md` throughout; only
the *verdict* was unreliable, and that is what B fixes.

## D5 — Break-even is per claim, never a 50% default
**2026-08-03.** A 50% break-even is right for a coin flip and wrong for almost
every prediction-market claim, where break-even is the price paid. A contract
bought at 5¢ needs a 5% hit rate; comparing 4.18% against 0.50 produces a
technically-true `REFUTED` for entirely the wrong reason. Claims carry their own
break-even where the price is known.

## D6 — `NO_FOOTPRINT` is stored as a distinct value and never merged with positive
**2026-08-03.** Absence of complaints about a small tool is absence of evidence,
not a clean bill of health. The two are stored separately so no aggregation can
collapse them. Promotional coverage does not count as corroboration — a "review"
site carrying an affiliate code is the vendor talking.

## D7 — A garbled name is evidence about the transcript before it is evidence about the tool
**2026-08-03.** Auto-captions mangle product names. "Creo" is **Kreo**, and the
first guessed URL 404'd — which would have been recorded as DEAD. Searching
variants changed the verdict twice, the second time on `moondevonyt`.
**Always search name variants before recording `NO_FOOTPRINT`.**

## D8 — Narrow venue-specific queries beat broad ones, measured
**2026-08-04.** Two corpora were kept deliberately separate. The targeted
Kalshi/Polymarket set returned **70% PASS against the broad set's 50%**, with
within-family overlap of 0.86–0.92 against 0.69–0.76. Narrow queries are both
more on-topic **and** more reproducible.
*(Replicated independently on a third platform: `social-signal` added 25 broad
Mastodon tags, tripled its corpus and gained **zero** recommend-grade items.)*

## D9 — Reports and the knowledge file are gitignored because they name people
**2026-08-03.** `reports/` and `KNOWLEDGE.md` carry judgements about named
creators and this repo is public. Code and corrections are tracked; judgements
are not. **Phase 0/1 copies remain in public git history** — recorded rather
than quietly rewritten.

---

## Open audit items

- **The broad corpus's retrieval test is NOT DEMONSTRATED** and is secondary to
  the practical hunt.
- **`read_video.py` has never run.** Everything below its API call is
  unvalidated.
- **The rubric bug D4 fixed was recorded before it was patched**, so verdicts
  issued in that window are unreliable while their extracted claims are fine.
- **Reading over-samples honesty:** videos are selected for reading by score,
  and honest videos score well *because* they are honest.
