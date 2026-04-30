# Roadmap (Owner Actions)

> What I need to do, in order. Update this when status changes.
> Default to working through these in sequence — convergence happens by
> finishing the prior step, not by parallelizing.

## Right now

**Step 4B: Build pipeline + smoke pre-pass.** Run the Phase 2 preflight probes,
then implement V1 build order through the smoke gate (~200 random
conversations) per D016. See V1_ARCHITECTURE_DRAFT and
[prompts/phase_2_segments_embeddings.md](prompts/phase_2_segments_embeddings.md)
for build steps. Done when smoke passes and the corpus inventory is browsable —
that inventory is what Step 5 needs.

## Already done

- Step 1: principle review → HUMAN_REQUIREMENTS.
- Step 2: ingestion-blocking open questions → privacy_tier defaults Tier 1 (D019); posthumous policy in HUMAN_REQUIREMENTS.
- Step 3: V1 re-pass against principles → V1_SYNTHESIS_DELTAS, DECISION_LOG D016–D022.
- Step 4A: D026 pre-Phase-2 adversarial round → Gemini + Opus reviews,
  synthesis, DECISION_LOG D027-D033.

## Up next, in order

**Step 5: Author the gold set.** 25–50 entries via GOLD_SET_TEMPLATE. *Trap to watch:* `expected_facts` come from my real-life answer, not from what the smoke pipeline extracted. Reference evidence by content, not by id. Done after a 24-hour-gap re-read.

**Step 6: Adversarial round** on V1 + principles + gold set + smoke inventory.
This is the post-smoke round and does not replace the narrower D026
pre-Phase-2 round.

**Step 7: Synthesize.** Update DECISION_LOG and V1_ARCHITECTURE_DRAFT as needed.

**Step 8: Full V1-corpus consolidation.** Runs unblocked. Multi-week local compute.

**Step 9: Gold set against consolidated V1 corpus.** Drives prompt/model re-extraction cycles via the non-destructive pipeline. Done when pass-rate stabilizes.

## Standing items I own forever

- **Update this file when status changes.** Attention artifact, not a one-shot.
- **Resist per-decision review.** Multi-model convergence beats my intuition on technical calls; anxiety to weigh in is background noise.
- **Reauthor gold-set entries** as new categories of question come up.
- **Run adversarial sweeps** on the live store after launch (P6).

## Promoted into V1

- Async context precompute / hot state — promoted by D025. Implement only
  as minimal Phase 5 `context_snapshots` + `memory_events`; distributed
  multi-GPU serving remains later-stage.

## Explicitly deferred (so anxiety doesn't pull me back)

### Engram features (v2-or-later)

- Wiki output layer (replaced by belief review queue for v1)
- Goal / failure / hypothesis / pattern inference
- Causal-link mining
- Apache AGE / graph backend
- Bulk Evernote → Obsidian migration (Claude + Gemini brought into V1 per D024)
- LLM cross-encoder reranker in live path
- Bidirectional Obsidian sync

### External tooling

- **Dev-workflow orchestrator** (e.g., [ai-auto-work](https://github.com/chaohong-ai/ai-auto-work)) — skipped. Working pattern is single coding agent + multi-model adversarial review at decision boundaries. Revisit only if that breaks down.

## When in doubt

- **Outcome:** *Biography of one human life, queryable at any point in time, owned by me.*
- **Process:** *Articulate principles. Articulate desired outcome. Articulate the eval. Get out of the way.*
- **My job:** Steps 1, 2, 5. Refuse to do Steps 6, 7, 9 until 5 is done. Steps 3, 4, 8 are engineering / model-driven.
