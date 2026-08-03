# Notes for Claude sessions in this repo

## Before searching YouTube for anything, read the knowledge base

`youtube-signal/KNOWLEDGE.md` (local only, gitignored) holds YouTube content that
has **already been read in full and scored**: tools and sites with what they
actually do, numeric claims put through a Wilson-interval check, step-by-step
methods with timestamps, and the short list of videos worth a human's own time.

It is not a summary. Every line traces to a video ID and a timestamp, so a
verified repo and a marketer's assertion stay distinguishable months later.

Rules when using it:

- **Claims carry expiries.** Mechanisms and maths never expire. Procedures 12
  months, tool recommendations 4, prices/fees/API specs 3, performance results 3.
  Check before repeating a number.
- **`REFUTED` beats the creator's framing.** It means the stated win rate cannot
  clear its own break-even at the stated sample size. That is arithmetic.
- **S (substance) and H (honesty) are never averaged.** A high-S low-H video still
  has good tools — discount its *results*, not its tooling.
- If the topic is covered there, use it instead of guessing. If it is not, say so
  rather than inventing sources.

Regenerate after new videos are read:

```bash
C:\Users\gianf\trading\youtube-signal\.venv\Scripts\python.exe C:\Users\gianf\trading\youtube-signal\src\build_knowledge.py
```

## Working in this repo

- Several projects live here as siblings. **Two Claude sessions have already
  cross-contaminated commits by using `git add -A`** — stage explicit paths.
- The repo is **public**. `data/`, `reports/`, `KNOWLEDGE.md` and `.env` are
  gitignored because they hold recorded data or judgments about named people.
- `python` on PATH is a Microsoft Store stub. Use the full interpreter path, or a
  project's `.venv\Scripts\python.exe`.
