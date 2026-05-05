# Phase 3 Build Prompt Synthesis

Date: 2026-05-05
Synthesizer: codex_gpt5_5
Prompt: P027 - Synthesize Phase 3 Build Prompt Findings
Target artifact: `prompts/P028_build_phase_3_claims_beliefs.md`

This synthesis classifies the Phase 3 build-prompt review findings and records
the accepted deltas applied to P028. It does not implement Phase 3 and does
not authorize starting the Phase 3 pipeline.

## Review Markers

The configured review markers were present before synthesis:

```text
docs/reviews/phase3/markers/06_BUILD_PROMPT_REVIEW_gemini_pro_3_1.ready.md
docs/reviews/phase3/markers/06_BUILD_PROMPT_REVIEW_codex_gpt5_5.ready.md
docs/reviews/phase3/markers/06_BUILD_PROMPT_REVIEW_claude_opus_4_7.ready.md
```

The reviewer set matched the configured set. No alternate reviewer set was
used.

## Inputs Read

- `docs/reviews/phase3/PHASE_3_BUILD_PROMPT_REVIEW_gemini_pro_3_1_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_BUILD_PROMPT_REVIEW_codex_gpt5_5_2026_05_05.md`
- `docs/reviews/phase3/PHASE_3_BUILD_PROMPT_REVIEW_claude_opus_4_7_2026_05_05.md`
- `prompts/P028_build_phase_3_claims_beliefs.md`
- `docs/claims_beliefs.md`
- `docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_SYNTHESIS_2026_05_05.md`
- Canonical project docs required by `AGENTS.md`: `README.md`,
  `HUMAN_REQUIREMENTS.md`, `DECISION_LOG.md`, `BUILD_PHASES.md`,
  `ROADMAP.md`, `SPEC.md`, and `docs/schema/README.md`.
- Process guidance: `docs/process/multi-agent-review-loop.md` and
  `docs/process/project-judgment.md`.

## Verdict

P028 is ready for a fresh implementation context after the edits from this
synthesis.

The original prompt was directionally correct and preserved the major Phase 3
boundaries: no full-corpus run, no cloud dependency, deterministic
consolidation, raw immutability, D048-D058 semantics, and Phase 4/5 deferrals.
The accepted review findings mostly clarified execution mechanics that a fresh
builder could otherwise get wrong.

No binding product-architecture changes were made. The deltas below are
implementation clarifications for the already accepted spec and decisions,
especially D049, D052, D054, D055, D057, and D058.

## Accepted Deltas Applied To P028

| Source | Severity | Disposition | Applied delta |
| --- | --- | --- | --- |
| Gemini 1 | P1 | accepted | Added explicit D054 privacy-reclassification recompute implementation instructions and explicit `single_current` `group_object_key=''` rule. |
| Codex P0-1 | P0 | accepted | Added physical SQL ordering for same-value supersession, contradiction replacement, and rebuild close under the non-deferrable active-belief unique index. |
| Codex P0-2 | P0 | accepted | Clarified extraction-version cutover: old extracted rows remain active while a replacement is `extracting`; old rows supersede only when the replacement successfully commits `status='extracted'`, including successful empty extraction. |
| Codex P1 pipeline | P1 | accepted | Required auditing existing `engram pipeline` / `make pipeline` scaffolding so Phase 3 only runs through `pipeline-3`; added CLI regression coverage. |
| Codex P1 reclassification hook | P1 | accepted | Added a named invalidation hook requirement that transitions invalidated segment extractions, leaves old claims insert-only, and runs before extract/consolidate/pipeline-3. |
| Codex P1 migration | P1 | accepted | Required migration verification and schema-doc generation from a fresh Phase 2 DB state; warned that a DB with draft `006_claims_beliefs.sql` already recorded is invalid for verification. |
| Codex P2 preflight bounds | P2 | accepted | Clarified relaxed-schema fallback is implemented and unit-tested with fake clients; no real tail-corpus preflight or 50-conversation pilot is authorized. |
| Codex P2 reaping | P2 | accepted | Defined stale `extracting` reaping as UPDATE to `status='failed'` with `failure_kind='inflight_timeout'`, no DELETE, no immediate `error_count` increment. |
| Codex P2 vocabulary parity | P2 | accepted | Added tests for exact predicate-vocabulary seed parity and extractor schema/table predicate parity. |
| Claude F1 | P0 | accepted_with_modification | Kept `ik-llama-json-schema.d034.v2.extractor-8192`, but documented it as the full extractor profile identity, not just a token cap. |
| Claude F2 | P0 | accepted | Required `SET LOCAL` or equivalent transaction-scoped GUC behavior and a no-leak test. |
| Claude F3 | P0 | accepted_with_modification | Tightened `beliefs` INSERT policy: direct INSERT without the transition GUC is rejected; transition API handles inserts and audit. |
| Claude F4 | P1 | accepted | Pinned `pipeline-3 --limit N` as conversations processed end-to-end; `extract --limit N` caps selected segments. |
| Claude F5 | P1 | accepted | Added `pipeline-3` warning when active beliefs exist under a different consolidator prompt version. |
| Claude F6 | P1 | accepted_with_modification | Pinned Phase 3 `extract --requeue --conversation-id` semantics: transition in-flight rows to failed/manual-requeue, reset progress error state, and retry through the normal bounded extraction path. |
| Claude F7 | P1 | accepted | Replaced "preflight" ambiguity with reactive relaxed-schema fallback on grammar/schema-construction failure. |
| Claude F8 | P1 | accepted | Required non-empty `subject_text` checks for `claims` and `beliefs`. |
| Claude F9 | P1 | accepted | Pinned `score_breakdown.cause` values and `score_breakdown.cause_capture_id`. |
| Claude F10 | P1 | accepted | Pinned full seven-value `belief_audit.transition_kind` CHECK, including Phase 4-reserved values. |
| Claude F11 | P1 | accepted | Required deterministic two-connection concurrency coverage, avoiding sleep-based timing. |
| Claude F12 | P1 | accepted | Pinned rebuild-close audit fields: `transition_kind='close'`, `previous_status='candidate'`, `new_status='superseded'`. |
| Claude F13 | P2 | accepted | Same as Codex vocabulary parity delta. |
| Claude F14 | P2 | accepted | Added test that claim derivation-version columns match parent `claim_extractions`. |
| Claude F15 | P2 | accepted | Carved spec tests #25/#26 out as operator gates, not unit tests or authorized runs. |
| Claude F16 | P2 | accepted | Pinned stale-reaping/error-count interaction. |
| Claude F17 | P2 | accepted | Required `claims.raw_payload.rationale` preservation. |
| Claude F18 | P3 | accepted | Required `contradictions` self-reference CHECK. |
| Claude F19 | P3 | accepted | Stated Phase 3 migration is forward-only; no down/rollback migration. |

## Deferred Or Rejected Findings

| Source | Disposition | Rationale |
| --- | --- | --- |
| Claude F20 | deferred | Requiring an extra `ENGRAM_PHASE3_CORPUS_RUN=1` guard would be a new operator contract not present in the accepted spec. P028 already forbids running the corpus in the implementation context and now pins bounded CLI semantics plus regression tests. This can be revisited in an operator-run prompt. |

## Notes On Spec Ambiguities

Two accepted findings clarify ambiguous or contradictory execution details in
`docs/claims_beliefs.md` without editing the spec in this pass:

1. Extraction cutover follows the non-destructive interpretation of D049:
   replacement `extracting` rows do not evict the prior extracted row from the
   active claim set. Supersession happens only when the replacement commits as
   `extracted`.
2. Belief transition ordering follows PostgreSQL reality: the active-belief
   unique partial index is not deferrable, so the transition API must update
   the prior row out of the active set before inserting a same-key replacement.

P028 now says that this synthesis / prompt controls these clarified execution
mechanics where the spec wording is ambiguous.

## Files Updated

- `prompts/P028_build_phase_3_claims_beliefs.md`
- `docs/reviews/phase3/PHASE_3_BUILD_PROMPT_SYNTHESIS_2026_05_05.md`
- `docs/reviews/phase3/markers/07_BUILD_PROMPT_SYNTHESIS.ready.md`

No implementation files were changed by this synthesis.

## Fresh Context Readiness

P028 is ready for a fresh implementation context. The implementation agent
should read the synthesis marker, this synthesis, the amended P028, and
`docs/claims_beliefs.md` before editing. The implementation context remains
prohibited from running the full Phase 3 corpus or starting the production
Phase 3 pipeline.

## Next Expected Marker

```text
docs/reviews/phase3/markers/08_BUILD_COMPLETE.ready.md
```
