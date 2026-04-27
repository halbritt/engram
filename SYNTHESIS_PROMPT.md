# Synthesis Prompt

Use this prompt after collecting the initial design reviews. The goal is to turn
multiple model opinions into a decision surface.

Repository path:

```text
~/git/engram/
```

## Prompt

```text
You are reviewing multiple architecture reviews for a local personal memory
system called Engram.

Work in this repository:

~/git/engram/

Engram vision:
- Fully local personal memory system.
- Ingests AI conversation history, notes, live captures, and later other personal
  signals.
- Builds a structured memory layer with embeddings, temporal beliefs, entity
  relationships, and context assembly.
- The primary product surface is context_for(conversation): a compact context
  package for the next AI interaction.
- A secondary goal is experimentation with graph retrieval, temporal memory,
  context engineering, evals, and LLM-assisted information retrieval.

Important context:
- I will run this on my own hardware.
- Do not optimize primarily for API cost or token cost.
- Offline local inference can run for hours if it improves correctness,
  provenance, temporal cleanup, graph quality, or eval quality.
- Live context must still be concise, high precision, and useful.
- Do not default to "single-user means simple." My personal corpus is complex,
  and I may want this to scale.
- I professionally work on information retrieval and personalization systems for
  a frontier model. Assume I care about retrieval quality, evals, ranking,
  freshness, feature-store-like signals, context packing, and failure analysis.
- I am interested in trying things that may be too slow or too experimental for
  a large company, because this is also a local research lab.

Inputs:
- Original design: BRAINSTORM.md
- Repo docs: README.md, SPEC.md, TODO.md
- Model reviews, as available:
  - CODEX_REVIEW.md
  - DESIGN_REVIEW_GEMINI.md
  - REVIEW_claude-opus-4-7.md
  - claw-review.md
  - self-hosted Qwen3.6:35B-MOE review, if present

Task:
Consolidate these reviews into repo artifacts. Do not summarize each review
separately. Extract the architectural signal and write it back into the design
files listed below.

Files to update:
- `CONSENSUS_REVIEW.md`: replace the template sections with the consolidated
  synthesis.
- `DECISION_LOG.md`: update proposed/accepted/deferred/rejected decisions and
  open questions based on the synthesis.
- `V1_ARCHITECTURE_DRAFT.md`: update only if the synthesis changes the proposed
  v1 architecture, build order, schema primitives, or non-goals.

Do not edit:
- original model review files
- `BRAINSTORM.md`
- `README.md`
- `SPEC.md`
- `TODO.md`
- `ADVERSARIAL_PROMPTS.md`, unless you identify a concrete defect in the prompts
  that would make the next review round weaker.

Output:
Update the files directly. At the end, report:
1. Files changed
2. Decisions accepted
3. Decisions deferred
4. Top unresolved questions for adversarial rounds
5. Any review inputs that were missing or unreadable

`CONSENSUS_REVIEW.md` must contain:
- consensus points across reviews
- important disagreements
- decisions that are hard to reverse later
- decisions that can safely be deferred
- recommended v1 architecture
- recommended research/experimental architecture
- a decision matrix with columns:
  - decision
  - options
  - model positions
  - risk
  - recommendation
  - reversibility
- top 10 questions for the next adversarial review round
- the strongest dissenting argument against your own recommendation

`DECISION_LOG.md` must contain:
- accepted decisions
- deferred decisions
- rejected decisions, if any
- open decisions with the evidence needed to resolve them
- revisit triggers for decisions that should not be permanent yet

`V1_ARCHITECTURE_DRAFT.md`, if updated, must preserve:
- v1 goal
- non-goals
- canonical data flow
- derived projections
- minimal schema primitives
- belief requirements
- context_for shape
- candidate lanes
- first eval harness
- build order

Specific design areas to cover:
- Canonical memory store vs derived projections
- Relational schema vs Apache AGE vs dedicated graph store
- Temporal modeling and belief lifecycle
- Raw evidence, claims, beliefs, provenance, and audit trail
- Hallucination compounding and circuit breakers
- Ingestion granularity for AI conversations and notes
- Entity canonicalization
- Context_for candidate generation, ranking, freshness, and token packing
- Eval harness and feedback signals
- What to cut from v1

Be direct. Prefer decisions over commentary. If something is uncertain, state
what evidence or experiment would resolve it.
```
