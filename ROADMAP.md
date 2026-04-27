# Roadmap (Owner Actions)

> What I need to do, in order. Update this when status changes.
> Default to working through these in sequence — convergence happens by
> finishing the prior step, not by parallelizing.

## Right now

**Step 1: Principle review.** Read the foundational-principle sections of
[HUMAN_REQUIREMENTS.md](HUMAN_REQUIREMENTS.md) (everything from "The
distinguishing property" through "Why refusal of false precision is a
contract"). For each principle, decide *keep / cut / amend*.

Done when every principle has been individually grit-tested against my own
intuition and the call has been made.

## Up next, in order

**Step 2: Resolve the two ingestion-blocking open questions.**
- Privacy tier model — which categories default to which tier.
- Posthumous handoff policy — even one line is better than silence.

These don't have to be perfect. They have to *exist* before any health,
financial, or sensitive-relationship data lands.

Done when both have a written answer in HUMAN_REQUIREMENTS.

**Step 3: V1 re-pass against the principles.** V1_ARCHITECTURE_DRAFT was
synthesized before the principles were explicitly named. Read
[V1_ARCHITECTURE_DRAFT.md](V1_ARCHITECTURE_DRAFT.md) against the foundational
principles. For each principle, ask: does V1 honor it, violate it, or stay
silent? Where it stays silent, decide whether it should be named in V1.

Done when there is either a delta document or a "V1 confirmed as-is" note
capturing the result.

**Step 4: Author the gold set.** 25–50 entries using
[GOLD_SET_TEMPLATE.md](GOLD_SET_TEMPLATE.md). The highest-leverage thing only
I can do, and it must land before migrations. The gold set is the actual
specification.

Done when the set has been written and re-read once after at least a
24-hour gap.

**Step 5: Adversarial round on V1 + principles + gold set.** Multi-model
adversarial review with all three artifacts in hand. The methodology has its
best shot here, because the inputs are richer than they were for round 1.

Done when adversarial responses are collected and a synthesis prompt has
been run.

**Step 6: Synthesize the adversarial round.** Decide what to act on, what to
defer. Update DECISION_LOG. Update V1_ARCHITECTURE_DRAFT if needed.

Done when synthesis lands as a commit.

**Step 7: Start migrations.** Stop designing, start building. V1 build order
step 1: Postgres + pgvector baseline. From here on, the work is engineering,
not design.

## Standing items I own forever

- **Update this file when status changes.** This is an attention-management
  artifact, not a one-shot.
- **Resist per-decision review.** Decisions in DECISION_LOG and
  CONSENSUS_REVIEW are technical decisions where multi-model convergence
  beats my intuition. Anxiety telling me to weigh in on each one is a
  background process, not a signal.
- **Reauthor gold-set entries** as new categories of question come up.
- **Run adversarial sweeps** on the live store after launch (per the
  principle that adversarial review is permanent).

## Explicitly deferred (so anxiety doesn't pull me back)

- Wiki output layer (replaced by belief review queue for v1)
- Goal / failure / hypothesis / pattern inference
- Causal-link mining
- Apache AGE / graph backend
- Multi-source ingestion beyond ChatGPT + Obsidian + capture
- LLM cross-encoder reranker in live path
- Bidirectional Obsidian sync
- Async precompute of context packages

These are not lost. They are explicitly v2-or-later. Returning to them now is
scope creep.

## When in doubt

- **The desired outcome:** *Biography of one human life, queryable at any
  point in time, owned by me.*
- **The desired process:** *Articulate principles. Articulate desired
  outcome. Articulate the eval. Get out of the way.*
- **My job:** *Steps 1, 2, 4. And to refuse to do steps 3, 5, 6, 7 until
  1, 2, 4 are done.*
