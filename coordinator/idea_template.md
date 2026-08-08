%%REPORT%%

---

## What the chat receiving this should do

1. Start the way every session here starts: bring the repo up to date with
   `git pull`, then read `STATUS.md` and your own `HANDOFF.md`.
2. **Read the related work above before writing any code.** Open each
   `LEDGER.md` line it points at and read the row in full. The check that
   produced that list matches words, not meaning — it is a starting point for
   reading, not a verdict.
3. **Decide, in writing, whether this is the same question as any of it.**
   Put the answer in your `DECISIONS.md` in your own folder, in this shape:

   > This idea IS / IS NOT the same question as `<ID>`, because `<one sentence>`.

   If it is the same question on the same data over the same dates, say so and
   stop — that is a good outcome and costs an hour instead of a week. If it
   differs in the question, the data, the dates, or the unit of observation,
   say which, and carry on.

4. **Pre-register before you run anything.** Write down the hypothesis, the
   unit of observation, the sample, the date range, the holdout split, and what
   result would make you drop the idea. Commit that file *before* the first
   result exists. This repo's rule is in `CLAUDE.md` §6 and it is not optional:
   selecting on past performance is fine, measuring the return over the same
   window you selected on is not.
5. **Report the naive benchmark next to whatever you find**, cluster the
   confidence interval at the unit that actually settles once, and state that
   unit out loud.
6. When you are done, update `STATUS.md`, write your `HANDOFF.md`, write your
   own section of `BRIEF.md` with
   `py -3 coordinator\brief.py write <your-slug> --file <a file>`, and push.

## The standing prior, so it is not a surprise

Every correction ever recorded in this repo made an apparent edge **smaller**.
Not one has revealed a bigger one. Expect this to fail; make it cheap to fail;
report the failure as prominently as you would report a win. A negative result
written up properly is worth more here than a positive one that has not been
through a holdout.

## What this message is not

It is **not** a judgment that the idea is good. The dictator chat does not judge
trading work — it moved the words and it found the overlaps. Whether this is
worth an hour is yours to decide, and if you think it is not, say so in your
reply and close the message `BLOCKED` with the reason. A disagreement recorded
is worth more than a task silently skipped.
