# DECISIONS — extractor-upgrade

Conservative calls taken without asking, per `CLAUDE.md` §2. Each names what
was decided, why, and what would reverse it.

---

**D1 — `reports/` is gitignored; findings go in tracked markdown.**
The generated reports carry per-document honesty judgments about named YouTube
channels, named GitHub authors and pseudonymous Reddit accounts, across 5,567
documents. `signal-github/reports/` and `youtube-signal/reports/` are already
ignored for the same reason. The readable payoff is committed as
`FINDINGS_T1.md`, which names the 24 test cases only — public channels, public
repos and public permalinks, the same set `STATUS.md` already names.
*Reverses if:* the repo goes private.

**D2 — the rubrics are imported from the siblings, never copied.**
`corpora.lexicon()` and `corpora.llm_rubric()` load
`social-signal/src/rubric.py` and `youtube-signal/src/read_video.py` by path
and fail loudly if either moves. GUARDS #6 exists because the Kalshi fee
formula went from 3 copies to 17 while "one implementation" was only a
convention. A rubric under test is exactly the thing that must not have a
private fork living in the harness that grades it.

**D3 — ground-truth labels may be BANDS, and every band is tabled.**
For 17 of 24 cases the outside evidence fixes a bound, not a point: a fully
disclosed negative post-mortem must not be discounted and must not be rejected,
but whether it is also worth a human's own 19 minutes is taste. Encoding taste
as ground truth would make the confusion matrix an opinion poll. The two
metrics that decide anything — false RECOMMEND and false REJECT — are judged
against the band's own edges, so a wider band can never manufacture a pass.

**D4 — the brief's `$23.53` case is recorded as MISSING, not reconstructed.**
It appears in no corpus in this repo (searched: both video databases'
transcripts, and every markdown in youtube-signal, social-signal, signal-github
and bot-hunt). Two verifiable cases were substituted. Writing the case from the
brief's description would have put an unverifiable label in a test set whose
entire premise is that labels are verifiable.

**D5 — no satire detector was built.**
The satire case (C21) is the only one of its kind in the set. Building a
detector from one example is the overfitting `social-signal/src/rubric_audit.py`
explicitly refused to do. It is recorded as a limit and left failing.
*Reverses if:* a labelled satire set of ≥20 exists.

**D6 — the existing corpora are NOT rescored under v2.**
The 38 read videos were scored by a model following the v1 prompt. Applying v2
weights to v1 components produces numbers that are neither. v2 applies from the
next read forward and the boundary should be stamped in the database.

**D7 — `S5` and `H4` scored 0 rather than deleted.**
Both fire on ~90% of the LLM read set, so they are intercepts. Deleting them
would lose evidence a reader wants; scoring them would keep an intercept in a
threshold. They are recorded and weighted 0, and `INFORMATIVE_MIN` drops by the
same amount so ranking is unchanged.

**D8 — the `B` route threshold moved 4 → 3.**
Not a knob. B2 (2.7%), B4 (4.3%) and B5 (0.1%) almost never fire over 4,432
posts, so a threshold of 4 closed the build route the B axis was added to open.
B1 alone — "shows working code or a runnable artifact" — is worth 3.

**D9 — `guest.api.arcadia.pinnacle.com/0.1/sports` returns 401, and this does
NOT contradict `bot-hunt`.**
That session recorded the guest API as free and unauthenticated (commit
`2674c7d`). The index endpoint `/0.1/sports` returns **401 with no header and
403 with the public guest key**; the endpoint that matters,
`/0.1/sports/29/matchups`, returns **200 and 1.7 MB with no header at all**.
Their finding stands and is refined: **the sports index is gated, the matchups
endpoints are not.** Recorded because a future session probing `/sports` first
would wrongly conclude the API is dead — the same "probe sampled the wrong
thing and failed toward a kill" shape `bot-hunt` recorded three times.

**D10 — `oracleselixir.com` returns HTTP 200, against `bot-hunt`'s "404".**
3,919 bytes from the root, which is a shell, not the data path. Not treated as
a contradiction: the two measurements are of different URLs. Recorded so
whoever needs esports data checks the data path rather than trusting either
line.

**D11 — vision runs on the existing read set only, and downloads no video it
does not need.** See `FINDINGS_T2.md`.
