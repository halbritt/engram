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

Step 5 from the roadmap: author the gold set against the now-extant
claims and beliefs.

Residual cleanup that does not block step 5:

- Close 149 active segments without an extraction (Phase 3 gap).
- Revisit 22 failed claim extractions.

## Already Landed

- Phase 1 raw evidence layer.
- ChatGPT export ingestion.
- Claude.ai export ingestion.
- Gemini Takeout ingestion.
- Raw immutability triggers.
- `privacy_tier` defaulting and reclassification vocabulary.
- Phase 2 implementation prompt.
- D026 pre-Phase-2 adversarial review and synthesis.
- Phase 2 segmentation + embeddings over the full AI-conversation corpus
  (7916/7916 conversations, 11266 active segments embedded; last activation
  2026-05-08).
- Phase 3 claim extraction + belief consolidation primary run (43812
  claims, 42558 beliefs; last extraction 2026-05-07).

## Next Major Milestones

- Gold set authoring (Step 5, in progress).
- Adversarial round on V1 + principles + gold set + claim/belief inventory
  (Step 6).
- Phase 3 cleanup: 149 unextracted segments + 22 failed extractions.
- Phase 4: entity canonicalization + belief review queue.
- Phase 5: `context_for`, context snapshots / hot state, MCP serving, and
  `context_feedback`.
- Smoke gate on a small corpus slice.
- Gold-set validation cycle.

## Explicit Non-TODOs For V1

Do not revive the old Stash-derived checklist unless a decision reopens it.

- No Stash 20-migration schema port.
- No `episodes` / `facts` schema as the canonical V1 model.
- No causal links, patterns, failure inference, hypotheses, or goal-progress
  inference in V1.
- No naive confidence decay / soft-delete stage.
- No auto wiki writeback or `wiki_refresh` tool in V1.
- No bidirectional Obsidian sync in V1.
