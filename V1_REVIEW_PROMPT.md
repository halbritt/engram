# V1 Review Prompt (Round 2 — Principle Re-pass)

Use this prompt after the foundational principles have been named in
HUMAN_REQUIREMENTS.md, before the gold-set adversarial round. Each model
that reviewed in round 1 should re-read V1 against the principles and
produce a position paper.

This is **narrower than round 1** — principle-only review, no gold set
yet. Each model's output is a delta against its own prior position, plus a
per-principle assessment of V1.

Repository path:

```text
~/git/engram/
```

## Prompt

```text
You are reviewing the V1 architecture for engram, a local-first personal
memory system. You produced a round-1 review previously; this round
revisits it now that foundational principles have been explicitly named.

Work in this repository:

~/git/engram/

Engram vision:
- Fully local personal memory system.
- Ingests AI conversation history, notes, live captures, and later other
  personal signals.
- Builds a structured memory layer with embeddings, temporal beliefs,
  entity relationships, and context assembly.
- The primary product surface is context_for(conversation): a compact
  context package for the next AI interaction.
- The longer-term ambition is a complete time-indexed biography of one
  human life — V1 is a validation phase, not the end state.

Important context:
- I will run this on my own hardware.
- Do not optimize primarily for API cost or token cost.
- Offline local inference can run for hours if it improves correctness,
  provenance, temporal cleanup, graph quality, or eval quality.
- Live context must still be concise, high precision, and useful.
- Do not default to "single-user means simple." My personal corpus is
  complex.
- Local-first is non-negotiable. Cloud-mediated proposals are out of scope.
- I am interested in trying things that may be too slow or too
  experimental for a large company, because this is also a local research
  lab.

Inputs (read in this order):
1. HUMAN_REQUIREMENTS.md — the foundational principles and domain
   coverage. The seven "Why X is Y" sections are the principles. Treat
   them as load-bearing.
2. V1_ARCHITECTURE_DRAFT.md — the synthesis from round 1. This is what
   you are reviewing.
3. SECURITY.md — security skeleton with open questions; some constrain V1.
4. CONSENSUS_REVIEW.md — round-1 synthesis. Useful context. Do not
   re-litigate decisions resolved here.
5. DECISION_LOG.md — settled decisions. Do not re-open these.
6. ROADMAP.md — owner action sequencing. Useful for understanding scope.
7. <YOUR_PRIOR_REVIEW>.md — your own round-1 review. Read this last so
   the prior context is fresh as you write.

Task:
For each of the seven foundational principles in HUMAN_REQUIREMENTS,
classify how V1 handles it:

- Honors — V1 explicitly satisfies the principle.
- Violates — V1 has a design choice that breaks it. Specify which.
- Silent — V1 doesn't address it either way. Recommend whether and how
  V1 should name it.

Then:
- For each violation, propose the smallest delta that brings V1 into
  compliance.
- For each silence that matters, propose specific schema or build-order
  additions.
- List principle-derived security constraints not yet captured in
  SECURITY.md.
- Where your round-1 position has changed because the principles changed
  the analysis, note the change and the reasoning.

Interim consideration to address — the eval gate's subset size:

CONSENSUS_REVIEW's ~100-conversation gate before full-corpus consolidation
is conservative-for-safety, not realistic-for-gold-set. With ~5,000
conversations across three sources, a 100-300 random subset cannot ground
gold-set prompts about specific people, projects, or years — most
references will be absent from any small random sample, so the eval
cannot pass even with a perfect pipeline.

A tiered alternative is on the table:

1. Smoke test (~100 conversations) — catches catastrophic pipeline
   failures. Same as CONSENSUS's current gate.
2. Gold-set validation (~1,000-2,000 conversations, stratified to the
   gold set's actual targets — the people, projects, years, decisions
   the prompts reference) — tests realistic retrieval. Gates full-corpus.
3. Full corpus of AI conversations (~5,000+ across ChatGPT + Claude +
   Gemini exports) — runs after tier-2 passes. Estimated 2-3 weeks of
   continuous local-LLM compute. NOTE: this is full coverage of the
   AI-conversation corpus only, NOT full biographical coverage. Other
   domains (health, finances, locations, relationships, recipes, etc.)
   require sources and pipelines that don't yet exist; much will be
   manual entry over years. V1 ingests AI conversations only.

Address in your review: does the tiered structure correctly identify the
gap? Should the gold set be authored differently to make a smaller
stratified subset sufficient? What's the right eval-gate structure?

Output:
Write the result to V1_REVIEW_<your-model-name>.md with the following
sections:

1. Per-principle assessment — honors / violates / silent + reasoning +
   delta per principle.
2. Schema or build-order additions — concrete table / column / build-step
   items implied by the principles that V1 doesn't yet have.
3. Security implications — items for SECURITY.md based on the principle
   review.
4. Position changes — where your round-1 stance has shifted, with
   reasoning.
5. Strongest residual concern — the single most important issue you'd
   raise about V1 + principles. One paragraph.

Constraints:
- Do not re-litigate decisions in DECISION_LOG. Those are settled.
- Do not propose new principles. The seven are stable.
- Do not expand V1 scope. V1 is a validation phase; v2-or-later is the
  right home for ambitious additions.
- Local-first is non-negotiable. Cloud-mediated proposals are out of
  scope.
- Do not edit any file other than your own V1_REVIEW_<your-model-name>.md.
  In particular, do not edit V1_ARCHITECTURE_DRAFT.md, HUMAN_REQUIREMENTS.md,
  SECURITY.md, CONSENSUS_REVIEW.md, or DECISION_LOG.md.

Be direct. Prefer decisions over commentary. If something is uncertain,
state what evidence or experiment would resolve it.
```

## Output naming

Each model writes to `V1_REVIEW_<model>.md`:

- `V1_REVIEW_codex.md`
- `V1_REVIEW_gemini.md`
- `V1_REVIEW_opus.md`
- `V1_REVIEW_claw.md`
- (any other models that participated)

Round 1's naming was inconsistent (`CODEX_REVIEW.md`,
`DESIGN_REVIEW_GEMINI.md`, `REVIEW_claude-opus-4-7.md`, `claw-review.md`).
Round 2 fixes that with a consistent prefix.

## Synthesis (optional at this stage)

If running multi-model: a light synthesis is enough at this point — a
short `SYNTHESIS_V1.md` covering the deltas, or an in-place update to
`V1_ARCHITECTURE_DRAFT.md`. Reserve a heavier synthesis for the round-3
adversarial pass when the gold set is also in scope.

If running single-model: skip synthesis; the single review is the output.

## Done condition

Step 3 of ROADMAP is done when:

- One or more `V1_REVIEW_<model>.md` files exist, and
- Either a delta document captures the changes V1 needs, or a "V1
  confirmed as-is" note records that the principles surfaced nothing V1
  hasn't already absorbed.
