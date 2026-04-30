# Pre-Phase-2 Adversarial Synthesis

Date: 2026-04-30
Scope: D026 pre-Phase-2 gate
Inputs:
- `PRE_PHASE_2_ADVERSARIAL_2026_04_30.md` (Gemini Round 0)
- `PRE_PHASE_2_ADVERSARIAL_2026_04_30_claude-opus-4-7.md` (Opus Round 2)
- Canonical docs at `6e3eb4e`

## 1. Executive Decision

**Proceed after canonical doc updates and Phase 2 preflight probes.**

Gemini found two structural schema faults, now captured as D027 and D028.
Opus found remaining implementation-contract faults that should be fixed before
Phase 2 coding because they affect schema shape, provenance integrity, privacy
scope, or retrieval visibility. The accepted changes are still Phase-2-local:
they do not reopen graph architecture, belief modeling, Obsidian writeback, or
the serving-path design.

## 2. Synthesis Matrix

| Source | Finding | Title | Disposition | Rationale | Canonical targets | Decision |
|--------|---------|-------|-------------|-----------|-------------------|----------|
| Gemini | 1.1 | KNN pre-filtering collapse over joins | accept | HNSW search must filter active/privacy-visible rows before candidate limit; joining through `embedding_cache` risks silent recall collapse. | `DECISION_LOG`, `BUILD_PHASES`, `V1_ARCHITECTURE_DRAFT`, Phase 2 prompt | D027 |
| Gemini | 1.2 | N-to-M supersession mapping impossible | accept | Segment generations do not map 1:1 across prompt versions. | `DECISION_LOG`, Phase 2 prompt | D027 |
| Gemini | 1.3 | Multiple dimensions in one pgvector column | accept-with-modification | The problem is real, but the fix should be a dimension-flexible column plus per-model/dimension indexes, not table partitioning in V1. | `DECISION_LOG`, Phase 2 prompt, `V1_ARCHITECTURE_DRAFT` | D033 |
| Gemini | 1.4 | Privacy reclassification cascade leak | accept-with-modification | Invalidation is required, but scope must be parent conversation/note/capture, not whole source. | `DECISION_LOG`, `BUILD_PHASES`, Phase 2 prompt | D028, D032 |
| Gemini | 1.5 | Poison-pill infinite loops | accept | Retry tracking is cheap and prevents one bad conversation from pinning the batcher. | Phase 2 prompt | none |
| Gemini | 2.1 | Sub-note/sub-message provenance loss | defer | Coarse provenance is acceptable for V1 unless eval shows token waste or citation imprecision. | Synthesis doc only | none |
| Gemini | 2.2 | Duplicate text vector domination | defer | Ranking/dedup belongs to Phase 5; D027 already prevents cache-join amplification. | Synthesis doc only | none |
| Gemini | 3.1 | Unified vector index | defer | Separate segment and belief indexes are acceptable for V1. | Synthesis doc only | none |
| Gemini | 3.2 | Character-level span tracking | defer | Do not add span schema until eval proves coarse provenance is insufficient. | Synthesis doc only | none |
| Opus | 1.1 | Long-conversation context overflow | accept | Full-conversation prompting will fail on long coding/Gemini sessions. Windowing must be part of Phase 2. | `DECISION_LOG`, `BUILD_PHASES`, Phase 2 prompt | D029 |
| Opus | 1.2 | Active sequence uniqueness | accept | Active segment order must be deterministic per parent. | `DECISION_LOG`, Phase 2 prompt | D030 |
| Opus | 1.3 | Generation cutover gap | accept-with-modification | The gap is real; use generation-state activation so a generation is retrieval-visible only after required embeddings exist. | `DECISION_LOG`, `BUILD_PHASES`, Phase 2 prompt | D031 |
| Opus | 1.4 | `message_ids` integrity | accept | Arrays do not enforce FKs; provenance needs write-side validation. | `DECISION_LOG`, Phase 2 prompt | D030 |
| Opus | 1.5 | D028 cascade scope too broad | accept | Reclassifying one message must not reprocess a whole export source. | `DECISION_LOG`, Phase 2 prompt | D032 |
| Opus | 1.6 | Parent privacy inheritance | accept | Segment tier must include parent conversation/note/capture tier and constituent raw rows. | `DECISION_LOG`, Phase 2 prompt | D032 |
| Opus | 1.7 | Embedding cache race | accept | Parallel embed workers need deterministic `ON CONFLICT DO NOTHING RETURNING` semantics. | Phase 2 prompt | none |
| Opus | 1.8 | Hardcoded `vector(768)` | accept-with-modification | V1 starts with `nomic-embed-text`, but schema must not block future dimensions. | `DECISION_LOG`, Phase 2 prompt, `V1_ARCHITECTURE_DRAFT` | D033 |
| Opus | 2.1 | Exact bytes hashed | accept | The cache key must be implementation-stable. | Phase 2 prompt | none |
| Opus | 2.2 | Multimodal/tool-use canonicalization | accept | Placeholder-heavy messages should not poison embeddings; provenance should still preserve covered message ids. | Phase 2 prompt | none |
| Opus | 2.3 | Segment eval hook | accept-with-modification | A small preflight probe is required; a full labeled eval harness can wait. | Phase 2 prompt, `BUILD_PHASES` | none |
| Opus | 2.4 | `notes.privacy_tier` missing | accept | Raw note rows need the same tier default before note segmentation. | Phase 2 prompt | D032 |
| Opus | 2.5 | Re-embed warning | accept | `pipeline` must run segment then embed; standalone segment runs should warn about non-retrieval-visible rows. | Phase 2 prompt | D031 |
| Opus | 3.1 | Sub-message spans | defer | Same disposition as Gemini 3.2. | Synthesis doc only | none |
| Opus | 3.2 | Unified vector index | defer | Same disposition as Gemini 3.1. | Synthesis doc only | none |
| Opus | 3.3 | Summary-text embedding | defer | Keep `summary_text`; do not add another embedding surface in Phase 2. | Synthesis doc only | none |
| Opus | 3.4 | Cross-conversation segment merging | reject for V1 | Cross-conversation segments conflict with current provenance and scope boundaries. | Synthesis doc only | none |

## 3. Accepted Decision Deltas

### D029 — Bounded Segmentation

Durable enough for `DECISION_LOG` because it defines what a segmenter is allowed
to do when a parent conversation exceeds model context. Phase 2 must probe the
local model's effective context window and use deterministic windowed
segmentation with overlap for over-budget parents.

### D030 — Segment Integrity

Durable enough for `DECISION_LOG` because segment rows become the first derived
provenance surface. Active sequence order and `message_ids` integrity must be
enforced at the database boundary, not left to LLM JSON discipline.

### D031 — Generation Activation

Durable enough for `DECISION_LOG` because retrieval visibility is a system
invariant. Segment generations should not become retrieval-visible until the
required embedding rows exist; version bumps must not blank retrieval.

### D032 — Privacy Scope And Inheritance

Durable enough for `DECISION_LOG` because it clarifies D019/D023/D028. Segment
privacy tiers inherit the maximum of the parent row and covered raw rows.
Reclassification invalidation scope is the affected parent conversation, note,
or capture, not the entire source export.

### D033 — Embedding Dimension Policy

Durable enough for `DECISION_LOG` because it reconciles D021's model portability
with pgvector's index constraints. Embedding storage must allow multiple model
dimensions through per-model/dimension indexes rather than hardcoding `vector(768)`.

## 4. Prompt And Spec Deltas

Required Phase 2 prompt changes:
- Add `segment_generations` or equivalent generation-state activation.
- Add `window_strategy` and bounded/windowed segmentation contract.
- Add active parent sequence uniqueness.
- Add `message_ids` validation trigger contract.
- Replace parent source invalidation with parent conversation/note/capture
  invalidation.
- Define privacy inheritance as `max(parent tier, constituent raw tiers)`.
- Replace hardcoded `vector(768)` with dimension-flexible storage and
  per-model/dimension indexes.
- Define embedding cache conflict behavior with `ON CONFLICT DO NOTHING
  RETURNING id`, then SELECT fallback.
- Define exact UTF-8 byte string used for `input_sha256`.
- Define message canonicalization for NULL/tool/image placeholder content.
- Add preflight probes before full Phase 2 implementation.

Required `BUILD_PHASES` / `V1_ARCHITECTURE_DRAFT` changes:
- Phase 2 acceptance criteria must include bounded segmentation, segment
  integrity checks, generation activation, scoped privacy invalidation, and
  dimension-flexible embedding indexes.
- The 2026-04-30 delta should list D029-D033 alongside D027-D028.

## 5. Deferred Items

- Character-level spans: revisit when eval attributes token waste or citation
  ambiguity to coarse message/note provenance.
- Unified segment/belief vector index: revisit if Phase 5 retrieval calibration
  suffers from dual-index merging.
- Summary-text embeddings: revisit if content-text retrieval is noisy and
  summary_text proves useful as a second retrieval surface.

## 6. Rejected Items

- Cross-conversation segment merging in V1. It is a plausible later memory
  layer, but it breaks Phase 2's parent-bounded provenance model.

## 7. Phase 2 Gate Checklist

- [x] D029-D033 are recorded in `DECISION_LOG`.
- [x] Phase 2 prompt no longer hardcodes `vector(768)` as the only allowed
  storage shape.
- [x] Phase 2 prompt defines bounded/windowed segmentation and records
  `window_strategy`.
- [x] Phase 2 prompt defines segment generation activation and cutover.
- [x] Phase 2 prompt defines parent-scoped reclassification invalidation.
- [x] Phase 2 prompt defines parent + constituent privacy inheritance.
- [x] Phase 2 prompt defines `message_ids` integrity checks and active sequence
  uniqueness.
- [x] Phase 2 prompt defines embedding cache conflict handling.
- [ ] Phase 2 preflight probes are run or explicitly accepted as part of the
  implementation prompt.
