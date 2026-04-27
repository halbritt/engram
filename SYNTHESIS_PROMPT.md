# Synthesis Prompt

Use this prompt after collecting the initial design reviews. The goal is to turn
multiple model opinions into a decision surface.

## Prompt

```text
You are reviewing multiple architecture reviews for a local personal memory
system called Engram.

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
Consolidate these reviews into an architecture decision brief. Do not summarize
each review separately. Extract the architectural signal.

Output:
1. Consensus points across reviews
2. Important disagreements
3. Decisions that are hard to reverse later
4. Decisions that can safely be deferred
5. Recommended v1 architecture
6. Recommended research/experimental architecture
7. A decision matrix with columns:
   - decision
   - options
   - model positions
   - risk
   - recommendation
   - reversibility
8. Top 10 questions for the next adversarial review round
9. The strongest dissenting argument against your own recommendation

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

