---
name: github-signal
description: Search GitHub for real trading-bot code and turn it into answers — which repos actually trade Kalshi or Polymarket, what kind of thing each one is (market maker, backtester, arbitrage, copy trader, data collector, scraper), whether it really places orders, whether it is alive, and whether its fee model is correct. Use when the user wants code, repos, libraries or implementations found on GitHub; wants to know how other people built something; wants inspiration or reference code for a trading bot; or asks what already exists before building. Triggers on "/github-signal", "find me repos for X", "search GitHub for X", "has anyone built X", "what does GitHub have on X", "steal/borrow code for X".
---

# github-signal

Turn GitHub into answers about working code. Retrieval, gating, scoring and
classification are **free and cost no model context**. Only the final reading
step costs anything.

**Project root:** `<repo>/signal-github` — on the desktop
`C:\Users\vinig\trading\signal-github`, on the laptop `C:\Users\gianf\trading\signal-github`.
**Python:** the full interpreter path
(`C:\Users\vinig\AppData\Local\Programs\Python\Python314\python.exe`).
`python` on PATH is a Microsoft Store stub and will fail.

---

## THE COST MODEL — read this before running anything

The expensive resource is **your context window**, not API calls. Everything a
repo's source touches stays in context for the rest of the session, so reading
N repos in one context costs roughly N²/2, not N. Reading 10 repos this way
turned a 200k job into 2.7M on the YouTube project.

**Rules, in order of how much they save:**

1. **Never read a repo to find out whether it is worth reading.** That is what
   `classify.py` and the scores are for. They read every file on disk without
   putting a single byte in your context.
2. **One repo per context when reading.** Dump it, extract it, write the
   extraction to disk, and do not carry the source forward. If you must read
   several, do them in separate turns or separate agents — never accumulate.
3. **Query the cache, never recompute.** `classify.py` without `--reclassify`
   loads `reports/classified.json` instantly. Re-classifying takes ~10 minutes
   and re-reads 2,000+ archives. The same rule applies to every stage: all
   HTTP is cached on disk by URL, so a re-run is free.
4. **Ask a narrow question.** `--venue kalshi --kind market_maker --alive`
   returns 10 lines. "Tell me about the corpus" returns 2,000.

---

## What this is, and what it is not

It is an **absorber for code**, not a recommender. Ranking exists only to decide
what to read. The deliverables are `reports/classified.json` (rows) and
`GITHUB_KNOWLEDGE.md` (claims with `path:line` provenance).

**Stars are worthless here — measured, not assumed.** `rho(stars, S_strict) =
−0.008, p = 0.65` at **n = 3,165 (full coverage)**. An earlier n = 105 sample showed +0.241 and the
project wrongly "corrected" itself; 21× the data killed it. Do not rank by stars
and do not let a star count into a recommendation.

---

## Pipeline

Every step is resumable and cached. Run only what you need.

```bash
python src/run_retrieval.py     # 6 axes -> repos table.        free
python src/run_gates.py         # on-topic + not-empty.         free
python src/prescreen.py         # queue order.                  free
python src/fetch_repo.py tree 1400   # whole repos via codeload. ZERO core budget
python src/fetch_repo.py full 900    # commits/contributors.     needs the token
python src/rescore.py           # strict S score.               free
python src/size_adjust.py       # remove the size advantage.    free
python src/classify.py          # venue + kind + liveness.      free
python src/currency.py          # IS IT STILL ALIVE. a GATE.    free
python src/fee_audit.py         # does it model fees right.     free
python src/shortlist.py         # substance AND credibility.    free
python src/build_knowledge.py   # regenerate GITHUB_KNOWLEDGE.md
```

**The token.** `signal-github/.env` holds `GITHUB_TOKEN=...` (gitignored).
It is NOT needed for depth — `gh.archive()` pulls whole repos from
`codeload.github.com` unmetered. It IS needed for code search (which returned
916 repos found by no other axis) and to stop unauthenticated search silently
dropping pages.

---

## Answering a question — the normal path

```bash
python src/classify.py --venue kalshi --kind market_maker --alive --limit 10
python src/classify.py --venue polymarket --kind backtester
python src/classify.py --need "tennis|weather"      # regex over name + description
```

Columns: `s_adj` (substance, size-normalised) · `kind` · `venue` · days since
push · `ord` = places real orders · fee model `ok`/`suspect` · `TRUST-ME-BRO`.

`--venue` is decided by **what the code imports** (`api.elections.kalshi.com`,
`py_clob_client`, `ClobClient`, …), never by the README. 27% of repos that pass
the topic gate import neither venue.

If the corpus does not contain the answer, say so and run retrieval with new
terms in `src/queries.py`. Do not invent repos.

---

## The four axes, and why no single one works

| axis | what it measures | how it fails alone |
|---|---|---|
| `s_strict` | substance from artifacts | 59% explained by file count before adjustment |
| `s_adj` | substance, size removed | its own #1 pick had **1 commit** and claimed "Guaranteed profit" |
| `trust_me_bro` | results claim, <10 commits, no artifact | fires on **19.1% of 2,717**; **weakly POSITIVELY correlated with substance — rho +0.064, p 0.0009.** The earlier "uncorrelated" reading was n=822 and is WITHDRAWN. Flagged repos score slightly HIGHER, because making a results claim at all requires having built something. It is an HONESTY signal: **discount the claims, not the tooling.** |
| fee audit | is a venue constant correct | only decidable for repos that hardcode one |

`shortlist.py` combines them. The weights are a judgement and are printed so
they can be disputed.

---

## ⛔ CURRENCY IS A GATE, and it was missing until 2026-08-05

**27.0% of the scored corpus is discontinued by its own owner** — 711 repos
import the Polymarket v1 CLOB client that *Polymarket archived*, and 28 are
archived outright. Nothing in `s_adj`, `trust_me_bro` or the fee audit could
see it, and **the share is worse at the top than in the corpus**:

| slice | discontinued by the owner |
|---|---|
| top 25 by `s_adj` | **6 = 24.0%** |
| top 100 | **35 = 35.0%** |
| whole corpus | 739 = 27.0% |

> **The trap that makes it invisible to a reader: `pip install py-clob-client`
> STILL WORKS.** PyPI serves 0.34.6 while the GitHub repo is archived. Nothing
> errors, nothing warns, and you find out at the order endpoint.

`src/currency.py` is a **gate, not a component**. A rigorous, well-tested
implementation of a dead API is not 70% as useful as a live one — it is a thing
you must not build on, however good it is. So it can only LOWER a verdict and it
always names the evidence. It costs **zero API calls** (every input is already
in `repos`); `--live` re-verifies the client libraries themselves so the table
cannot rot silently.

**Gating costs nothing measurable.** Against the external ground truth — repos
that provably model Kalshi's *maker* fee correctly — the top 100 goes **6 → 9**
fee-correct and the top 200 goes **10 → 17**, and **zero fee-correct repos in
the top 200 are lost.** Removing dead weight promotes live repos that were
underneath it.

**The ranking has also never been graded, and now has been** — see
`extractor-upgrade/reports/T6_github_validation.md`. On the five repos this
project read in full, **the ranking agrees with the read on 1 of 5**: it would
RECOMMEND `hcharper/polyBot-Weather` (rank 3, ONE commit, a README claiming
"Guaranteed profit", v1 client) and merely ABSORB `aulekator` (557 stars,
4 commits, `fee_rate_bps=0` live). Five is not a precision estimate. It is five
demonstrations that `s_adj` alone must never be read as a recommendation.

## Traps that already cost real work

- **`codeload.github.com/<repo>/tar.gz/<branch>`** — use the legacy form. The
  documented `/tar.gz/refs/heads/<branch>` times out from this network.
- **Default branch is not always `main`.** A live 1,098-star repo uses
  `v4.1-alpha`; a naive fetch 404s on it.
- **Popular repos get venue constants wrong.** 49 repos model Kalshi's maker fee
  correctly and have **79 stars between them**; 41 get it wrong and have 2,387.
- **The maker rate is per-series.** Kalshi charges makers on exactly 130 of
  12,396 series — and they are the liquid ones. Applying 0.0175 everywhere is
  wrong in the *other* direction, and two of the most rigorous repos in the
  corpus do exactly that. Use `common/kalshi_fees.py`, which refuses to guess.
- **Polymarket's `makerBaseFee` is not the fee.** It reads `1000` on 94% of
  markets; the CLOB API returns 0 for the same markets. `feeSchedule` is
  authoritative.
- **578 repos import the ARCHIVED Polymarket v1 client, 121 the v2.** Importing
  v1 means the code cannot be current.
- **A silent failure that inflates a denominator is worse than a crash.** A bug
  once reported 358 repos scored when 92 had real data.

---

## Privacy

`data/`, `cache/`, `reports/` and `GITHUB_KNOWLEDGE.md` are gitignored: they hold
judgements about named repositories and named people. Code and `CORRECTIONS.md`
are tracked. Keep it that way.
