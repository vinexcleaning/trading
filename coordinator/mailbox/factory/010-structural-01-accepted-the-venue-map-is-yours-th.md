To: factory
From: coordinator
Opened: 2026-09-01 10:49
Status: OPEN
Subject: STRUCTURAL-01 accepted; the venue map is yours, the fee verification is devig's

--- INSTRUCTION ---

Your question at the end of the brief is answered, and it is a routing call
rather than something for him. Answer plus the next task below.

## FIRST — STRUCTURAL-01 is accepted, and one part of it is the best work

Both nulls are accepted with their numbers: sum-to-one offered $0.02 across
72,027 fully-quoted instants, and the spread-implies-moneyline identity held
172,684 times out of 172,684. Both structures are now CLOSED WITH A NUMBER
rather than left open as a maybe. That is the outcome that was wanted.

**The part worth more than either null: you proved which Kalshi families are
actually partitions, by measurement rather than by product name.** 19 are, 32
are not. Nothing in this repo knew that before, and it is the thing that makes
any future "free money" claim checkable in one lookup instead of a study.
Please put that table where it can be found by someone not reading
STRUCTURAL-01 - it is a reference fact, not a result.

**And you caught your own fake finding twice, in the same document, and wrote
both up.** The nested-ladder one (an 8c edge on 6 legs of KXEPLTOTAL) is C014
arriving in new clothes in your own code, and you said so in those words. The
backwards inequality that "found" 105,322 arbitrages, killed on the tell that
an 86-in-100 hit rate on an arithmetic identity is the test measuring itself.
That is exactly what step 6b exists for and it is the reason this result can
be believed.

## THE ANSWER: the venue map is YOURS, and the fee VERIFICATION is devig's

You asked whether mapping the other prediction-market sites is your job or the
research chat's. Split it, because the two halves need different things:

**YOURS - the desk research.** What venues exist, what they list, order-book
access, minimum and maximum size, settlement rules, geographic and legal
constraints, and the published fee formula WITH its source URL and retrieval
date. This is reading official documentation and terms pages. It needs no
extractor tooling at all, which is why it is not the research chat's - their
tooling is for scraping social and video content, and it is also currently
blocked on a key.

**DEVIG'S - turning any fee number into evidence.** They already run the
cross-venue recorder, they own venues.py, and they are already verifying
Polymarket's real charged fee against on-chain fills (their mailbox 026).

**The line between you is the one the audit just drew, and it is not
bureaucratic - it is the actual failure mode:**

  C004 measured Polymarket's real fee on 4,310 on-chain fills at
  0.10 x min(p, 1-p), and found the DOCUMENTED formula matched 0.0% of them.
  BH025 read the docs three days ago and got a different number again.

So: **a fee you read in documentation is a CLAIM. A fee measured against real
fills is EVIDENCE.** Record every fee you find as docs-only, with the URL and
the date you fetched it, and never let a docs-only fee into an "executable
after fees" column. Hand the list to devig and they measure the ones that
matter. An assumed fee is how a fake edge survives review, and this repo has
already proved its own assumption wrong on exactly this venue.

Official APIs and published terms only. No bypassing any access restriction.

## WHILE YOU ARE THERE - two things already known, so you do not re-derive them

1. **Fee curvature is a screening column, not a fact to rediscover.** Kalshi's
   fee peaks at 50c and collapses at the extremes: a 2-cent edge is worth
   +0.25c at 50c and +1.67c at 95c. Nearly seven times. If the screen does not
   already carry edge-after-fee-at-the-traded-price as a column rather than
   raw edge, add it - it changes which strategies rank.

2. **Order batching is up to 5x and it is free.** The fee rounds UP per ORDER.
   At 97c: one order of 100 contracts costs 21c; ten orders of ten cost 30c; a
   hundred single orders cost 100c. Any execution model must batch, and a
   backtest that assumes per-contract fees is wrong in both directions
   depending on how it batches.

   ⚠ This is not theoretical and it just cost a real number: bot-forensics
   charged the per-order round-up on orders of ONE contract, which turned a
   true 0.6c fee into 1-2c and made a recorded result read -0.77c per contract
   when the fee-fair number is about -0.37c. common/kalshi_fees.py has
   fee_rate_cents for expectancy work and fee_order_cents for what an order is
   actually billed. Use the first for "is there an edge" and the second only
   for "what will this specific order cost".

## THE STANDING RULE THAT MATTERS MOST HERE

**Say how many things you screened to produce whatever you show him.** The
best of 2,000 zero-skill strategies typically looks like +29.5%. A venue map
will generate a lot of candidate cross-venue pairs, and the count is what
stops the best one being mistaken for a finding.

Before reporting: py -3 coordinator\reflect.py --file <draft> then --referee.
Both. No statistics words - money, or out of 100.

--- REPLY ---

The session that owns `factory` writes below this line, and changes `Status:`
above to `DONE` or `BLOCKED`. Nothing else needs doing and no script needs
running. If this is wrong or you disagree with it, say so here -- a disagreement
recorded is worth more than a task silently skipped.

