# Engram Prompt Artifacts

This directory contains the LLM prompts and operational handoffs used to build and evaluate Engram. Prompts are assigned stable ordinals (`P###`) based on their first introduction to the repository.

## Prompt Index

| Ordinal | Purpose | Introduced | Source |
|:---|:---|:---|:---|
| **P001** | [Synthesis Prompt](prior/P001_SYNTHESIS_PROMPT.md) (Historical) | 2026-04-27 | `c0aed3d` |
| **P002** | [V1 Review Prompt](prior/P002_V1_REVIEW_PROMPT.md) (Historical) | 2026-04-27 | `a6c1816` |
| **P003** | [Phase 1: Raw Evidence Layer](P003_phase_1_raw_ingest.md) | 2026-04-28 | `dfbd654` |
| **P004** | [Phase 1.5: Cleanup](P004_phase_1_5_cleanup.md) | 2026-04-28 | `1430f77` |
| **P005** | [Phase 1.5: Claude Ingestion](P005_phase_1_5_claude_ingest.md) | 2026-04-28 | `618b5bc` |
| **P006** | [Phase 1.5: Gemini Ingestion](P006_phase_1_5_gemini_ingest.md) | 2026-04-28 | `618b5bc` |
| **P007** | [Phase 2: Segmentation + Embeddings](P007_phase_2_segments_embeddings.md) | 2026-04-28 | `3e5d115` |
| **P008** | [Phase 2: Embed Drain](P008_phase_2_embed_drain.md) | 2026-05-02 | `77051b7` |
| **P009** | [Phase 2: Enum-ID Soak Gate](P009_phase_2_enum_soak_gate_full_corpus.md) | 2026-05-02 | `ef4c080` |
| **P010** | [Phase 2: Soak Test](P010_phase_2_soak_test.md) | 2026-05-02 | `64eb7e3` |
| **P011** | [Segmentation Harness Spec](P011_benchmark_segmentation_harness_spec.md) | 2026-05-03 | `85a1c9b` |
| **P012** | [Review Segmentation Harness Spec](P012_review_benchmark_segmentation_harness.md) | 2026-05-03 | `49f09c7` |
| **P013** | [Build Segmentation Harness](P013_build_benchmark_segmentation_harness.md) | 2026-05-03 | `71efa23` |
| **P014** | [Review Harness Implementation](P014_review_benchmark_segmentation_harness_implementation.md) | 2026-05-03 | `b23d400` |
| **P015** | [Fix Harness Findings](P015_fix_benchmark_segmentation_harness_review_findings.md) | 2026-05-03 | `5aeb589` |
| **P016** | [Run Short Public Benchmark](P016_run_short_segmentation_public_model_benchmark.md) | 2026-05-03 | `c3bd353` |
| **P017** | [Implement Early Signal](P017_implement_benchmark_segmentation_early_signal.md) | 2026-05-04 | `89d58f2` |
| **P018** | [Run Early Signal Benchmark](P018_run_segmentation_early_signal_benchmark.md) | 2026-05-04 | `56c7237` |
| **P019** | [Phase 2 Span Expansion Audit](P019_phase_2_span_expansion_audit.md) | 2026-05-04 | `6f39341` |
| **P020** | [Qwen 27B Umbrella A/B](P020_phase_2_qwen27b_umbrella_ab.md) | 2026-05-05 | `6f24fc9` |
| **P021** | [Generate Phase 3 Claims And Beliefs Spec](P021_generate_phase_3_claims_beliefs_spec.md) | pending | `pending` |
| **P022** | [Review Phase 3 Claims And Beliefs Spec](P022_review_phase_3_claims_beliefs_spec.md) | pending | `pending` |
| **P023** | [Record Phase 3 Spec Findings](P023_record_phase_3_spec_findings.md) | pending | `pending` |
| **P024** | [Synthesize Phase 3 Spec Findings](P024_synthesize_phase_3_spec_findings.md) | pending | `pending` |
| **P025** | [Write Phase 3 Build Prompt](P025_write_phase_3_build_prompt.md) | pending | `pending` |
| **P026** | [Review Phase 3 Build Prompt](P026_review_phase_3_build_prompt.md) | pending | `pending` |
| **P027** | [Synthesize Phase 3 Build Prompt Findings](P027_synthesize_phase_3_build_prompt_findings.md) | pending | `pending` |
| **P028** | [Build Phase 3 Claims And Beliefs](P028_build_phase_3_claims_beliefs.md) | pending | `pending` |
| **P029** | [Review Phase 3 Build](P029_review_phase_3_build.md) | pending | `pending` |
| **P030** | [Synthesize Phase 3 Build Review Findings](P030_synthesize_phase_3_build_review_findings.md) | pending | `pending` |
| **P031** | [Begin Phase 3 Pipeline](P031_begin_phase_3_pipeline.md) | pending | `pending` |
| **P032** | [Review Phase 3 Postbuild Changes](P032_review_phase_3_postbuild_changes.md) | pending | `pending` |
| **P033** | [Review RFC 0013 Operational Issue Loop](P033_review_rfc_0013_operational_issue_loop.md) | pending | `pending` |
| **P034** | [Re-review RFC 0013 Operational Issue Loop](P034_rereview_rfc_0013_operational_issue_loop_codex.md) | pending | `pending` |
| **P035** | [Review Phase 3 Limit-10 Repair](P035_review_phase_3_limit10_repair.md) | pending | `pending` |
| **P036** | [Re-review Phase 3 Limit-10 Repair](P036_rereview_phase_3_limit10_repair_codex.md) | pending | `pending` |
| **P037** | [Review Phase 3 Limit-50 Validation Repair](P037_review_phase_3_limit50_validation_repair.md) | pending | `pending` |
| **P038** | [Re-review Phase 3 Limit-50 Validation Repair](P038_rereview_phase_3_limit50_validation_repair_codex.md) | pending | `pending` |
| **P039** | [Run Phase 3 Limit-500 Gate](P039_run_phase_3_limit500_gate.md) | pending | `pending` |
| **P040** | [Run Phase 3 Full-Corpus Gate](P040_run_phase_3_full_corpus_gate.md) | pending | `pending` |
| **P041** | [Review Phase 3 Limit-500 Null-Object Repair Spec](P041_review_phase_3_limit500_null_object_repair_spec.md) | pending | `pending` |
| **P042** | [Review Phase 3 Limit-500 Null-Object Repair Implementation](P042_review_phase_3_limit500_null_object_repair.md) | pending | `pending` |

## Ordinal Derivation

Prompts follow a global sequence `P###`. The ordinal is derived from the **committer time** of the first commit that introduced the file to the repository. Ties are broken by the file path (alphabetical).

Historical prompts (located in `prior/`) are preserved for provenance but are no longer part of the active development pipeline.
