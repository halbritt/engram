# TODO

This file is a lightweight pointer to the active work queue. It is not the
architecture source of truth.

Authoritative planning lives in:

- [ROADMAP.md](ROADMAP.md) — owner sequencing and current step.
- [BUILD_PHASES.md](BUILD_PHASES.md) — V1 implementation phases and acceptance
  criteria.
- [DECISION_LOG.md](DECISION_LOG.md) — accepted / deferred / rejected
  architecture decisions.
- [docs/design/V1_ARCHITECTURE_DRAFT.md](docs/design/V1_ARCHITECTURE_DRAFT.md)
  — current V1 target architecture.

## Current Work

Step 4 from the roadmap: build the V1 pipeline through the smoke pre-pass.

Active implementation target:

- Pre-Phase-2 adversarial review (D026), using
  [docs/design/ADVERSARIAL_PROMPTS.md](docs/design/ADVERSARIAL_PROMPTS.md).
- Phase 2 — segmentation + embeddings.
- Operational prompt:
  [prompts/phase_2_segments_embeddings.md](prompts/phase_2_segments_embeddings.md).

## Already Landed

- Phase 1 raw evidence layer.
- ChatGPT export ingestion.
- Claude.ai export ingestion.
- Gemini Takeout ingestion.
- Raw immutability triggers.
- `privacy_tier` defaulting and reclassification vocabulary.
- Phase 2 implementation prompt.

## Next Major Milestones

- D026 synthesis: accept/reject pre-Phase-2 adversarial findings.
- Phase 2: topic segmentation + segment embeddings.
- Phase 3: claims + bitemporal beliefs.
- Phase 4: entity canonicalization + belief review queue.
- Phase 5: `context_for`, context snapshots / hot state, MCP serving, and
  `context_feedback`.
- Smoke gate on a small corpus slice.
- Gold-set authoring and validation.

## Explicit Non-TODOs For V1

Do not revive the old Stash-derived checklist unless a decision reopens it.

- No Stash 20-migration schema port.
- No `episodes` / `facts` schema as the canonical V1 model.
- No causal links, patterns, failure inference, hypotheses, or goal-progress
  inference in V1.
- No naive confidence decay / soft-delete stage.
- No auto wiki writeback or `wiki_refresh` tool in V1.
- No bidirectional Obsidian sync in V1.
