# Review ID Registry

Status: accepted (D068, 2026-05-07)
Source: `docs/process/artifact-id-conventions.md`

This registry maps `REVIEW-####` IDs to review documents under `docs/reviews/`.
Per D068, sequential IDs are assigned to top-level review documents (synthesis,
findings, blocker reports, and the V1/RFC-0014 review corpora). Per-reviewer
individual review files aggregate under their synthesis ID until cross-document
references demand finer granularity.

The initial adoption pass capped issuance at 30 IDs. The dozens of per-reviewer
Phase 3 review documents (e.g. `*_codex_gpt5_5_*.md`, `*_claude_opus_*.md`,
`*_gemini_pro_*.md`) and similar per-reviewer files under
`docs/reviews/rfc-0014-operational-artifact-home/reruns/**` are not separately
numbered in this pass — they aggregate under their synthesis or findings-ledger
ID. Marker files under `docs/reviews/phase3/markers/` and
`docs/reviews/phase3/postbuild/markers/` are also not numbered; markers are
process state, not review content.

Files in `docs/reviews/pre_v1/` capture pre-V1 design critiques referenced from
the V1 corpus (notably REVIEW-0001 Consensus Review). They are aggregated under
that synthesis ID for now.

| ID | Date | Path | Type | Notes |
|----|------|------|------|-------|
| REVIEW-0001 | 2026-04-27 | docs/reviews/v1/CONSENSUS_REVIEW.md | synthesis | Round 1 consensus across pre-V1 reviews; aggregates `pre_v1/CODEX_REVIEW.md`, `pre_v1/DESIGN_REVIEW_GEMINI.md`, `pre_v1/REVIEW_claude-opus-4-7.md`, `pre_v1/claw-review.md` |
| REVIEW-0002 | 2026-04-27 | docs/reviews/v1/V1_REVIEW_qwen3.6-35b-a3b.md | individual | V1 architecture review (Qwen 3.6) |
| REVIEW-0003 | 2026-04-28 | docs/reviews/v1/V1_REVIEW_claude-opus-4-7.md | individual | V1 architecture review (Claude Opus 4.7) |
| REVIEW-0004 | 2026-04-28 | docs/reviews/v1/V1_REVIEW_codex.md | individual | V1 principle review (Codex) |
| REVIEW-0005 | 2026-04-28 | docs/reviews/v1/V1_REVIEW_gemini-cli.md | individual | V1 architecture review (Gemini CLI) |
| REVIEW-0006 | 2026-04-30 | docs/reviews/v1/PRE_PHASE_2_ADVERSARIAL_2026_04_30.md | individual | Pre-Phase-2 adversarial round 0 |
| REVIEW-0007 | 2026-04-30 | docs/reviews/v1/PRE_PHASE_2_ADVERSARIAL_2026_04_30_claude-opus-4-7.md | individual | Pre-Phase-2 adversarial round 2 (Claude) |
| REVIEW-0008 | 2026-04-30 | docs/reviews/v1/PRE_PHASE_2_ADVERSARIAL_SYNTHESIS_2026_04_30.md | synthesis | Pre-Phase-2 adversarial gate; promoted D027–D033 |
| REVIEW-0009 | 2026-05-01 | docs/reviews/v1/PHASE_2_CODE_REVIEW_FINDINGS.md | findings | Phase 2 code review findings |
| REVIEW-0010 | 2026-05-03 | docs/reviews/v1/BENCHMARK_SEGMENTATION_HARNESS_SYNTHESIS_2026_05_03.md | synthesis | Benchmark harness review synthesis; aggregates per-reviewer harness reviews |
| REVIEW-0011 | 2026-05-03 | docs/reviews/v1/BENCHMARK_SEGMENTATION_HARNESS_IMPLEMENTATION_SYNTHESIS_2026_05_03.md | synthesis | Benchmark harness implementation review synthesis |
| REVIEW-0012 | 2026-05-04 | docs/reviews/v1/BENCHMARK_SEGMENTATION_EARLY_SIGNAL_SPEC_SYNTHESIS_2026_05_04.md | synthesis | RFC 0008 early-signal spec review synthesis |
| REVIEW-0013 | 2026-05-04 | docs/reviews/v1/BENCHMARK_SEGMENTATION_EARLY_SIGNAL_IMPLEMENTATION_REVIEW_SYNTHESIS_2026_05_04.md | synthesis | RFC 0008 early-signal implementation review synthesis |
| REVIEW-0014 | 2026-05-04 | docs/reviews/v1/PHASE_2_SPAN_EXPANSION_AUDIT_2026_05_04.md | findings | Phase 2 span expansion audit |
| REVIEW-0015 | 2026-05-05 | docs/reviews/v1/PHASE_2_QWEN27B_UMBRELLA_AB_2026_05_05.md | findings | Phase 2 Qwen 27B umbrella A/B run report |
| REVIEW-0016 | 2026-05-05 | docs/reviews/phase3/PHASE_3_BUILD_PROMPT_SYNTHESIS_2026_05_05.md | synthesis | Phase 3 build prompt synthesis; aggregates per-reviewer build prompt reviews |
| REVIEW-0017 | 2026-05-05 | docs/reviews/phase3/PHASE_3_BUILD_REVIEW_SYNTHESIS_2026_05_05.md | synthesis | Phase 3 build review synthesis; aggregates per-reviewer build reviews |
| REVIEW-0018 | 2026-05-05 | docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_FINDINGS_LEDGER_2026_05_05.md | findings | Phase 3 claims/beliefs spec findings ledger |
| REVIEW-0019 | 2026-05-05 | docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_SYNTHESIS_2026_05_05.md | synthesis | Phase 3 claims/beliefs spec synthesis; aggregates per-reviewer spec reviews |
| REVIEW-0020 | 2026-05-05 | docs/reviews/phase3/PHASE_3_D063_LIMIT10_REPAIR_REVIEW_SYNTHESIS_2026_05_05.md | synthesis | Phase 3 D063 limit-10 repair review synthesis |
| REVIEW-0021 | 2026-05-05 | docs/reviews/phase3/PHASE_3_D063_LIMIT50_VALIDATION_REPAIR_REVIEW_SYNTHESIS_2026_05_05.md | synthesis | Phase 3 D063 limit-50 validation repair synthesis |
| REVIEW-0022 | 2026-05-05 | docs/reviews/phase3/RFC_0013_OPERATIONAL_ISSUE_LOOP_SYNTHESIS_2026_05_05.md | synthesis | RFC 0013 operational issue loop review synthesis |
| REVIEW-0023 | 2026-05-06 | docs/reviews/phase3/PHASE_3_FULL_RUN_EXTRACTOR_PARSE_FAILURE_FINDINGS_2026_05_06.md | findings | Phase 3 full-run extractor parse failure findings |
| REVIEW-0024 | 2026-05-06 | docs/reviews/phase3/PHASE_3_LIMIT500_FAILURE_FINDINGS_2026_05_06.md | findings | Phase 3 limit-500 failure findings |
| REVIEW-0025 | 2026-05-06 | docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_REVIEW_SYNTHESIS_2026_05_06.md | synthesis | Phase 3 limit-500 null-object repair review synthesis |
| REVIEW-0026 | 2026-05-06 | docs/reviews/phase3/PHASE_3_LIMIT500_SCHEMA_REJECTION_FINDINGS_2026_05_06.md | findings | Phase 3 limit-500 schema rejection findings |
| REVIEW-0027 | 2026-05-06 | docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_REPAIR_REVIEW_SYNTHESIS_2026_05_06.md | synthesis | Phase 3 limit-500 still-invalid repair review synthesis |
| REVIEW-0028 | 2026-05-06 | docs/reviews/rfc-0014-operational-artifact-home/RFC_0014_FINDINGS_LEDGER.md | findings | RFC 0014 findings ledger; aggregates root-level per-reviewer reviews (claude/codex/gemini) |
| REVIEW-0029 | 2026-05-06 | docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-2/RFC_0014_SYNTHESIS.md | synthesis | RFC 0014 synthesis (rerun-2); aggregates that rerun's per-reviewer reviews |
| REVIEW-0030 | 2026-05-06 | docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-4/RFC_0014_SYNTHESIS.md | synthesis | RFC 0014 spec handoff synthesis (rerun-4); aggregates that rerun's per-reviewer reviews |
| REVIEW-0031 | 2026-05-07 | docs/reviews/phase3/PHASE_3_EXTRACTION_BACKEND_BENCHMARK_2026_05_07.md | findings | RFC 0019 Phase 3 extraction backend benchmark findings for local vLLM and sglang candidates |
| REVIEW-0032 | 2026-05-08 | docs/reviews/v1/BENCHMARK_SEGMENTATION_IK_LLAMA_CONFIG_2026_05_08.md | findings | Phase 2 segmentation ik_llama server-profile benchmark findings |
| REVIEW-0033 | 2026-05-08 | docs/reviews/v1/LOCAL_INFERENCE_SPEED_FINDINGS_2026_05_08.md | findings | Local extraction and segmentation inference speed benchmark findings |
| REVIEW-0034 | 2026-05-08 | docs/reviews/rfc0025/RFC_0025_COMMAND_NAMES_SYNTHESIS.md | synthesis | RFC 0025 command-names review synthesis; aggregates RFC 0025 per-reviewer reviews and findings ledger |

## Aggregated (not separately numbered)

The following sets of files are aggregated under the synthesis or findings ID
shown above for the same scope. Future passes may promote individual entries to
their own `REVIEW-####` IDs if cross-document references demand it.

- `docs/reviews/pre_v1/*.md` — under REVIEW-0001.
- `docs/reviews/phase3/PHASE_3_BUILD_PROMPT_REVIEW_*_2026_05_05.md` — under REVIEW-0016.
- `docs/reviews/phase3/PHASE_3_BUILD_REVIEW_*_2026_05_05.md` (per-reviewer) — under REVIEW-0017.
- `docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_REVIEW_*_2026_05_05.md` and
  `PHASE_3_CLAIMS_BELIEFS_SPEC_SYNTHESIS_REVIEW_*` — under REVIEW-0019.
- `docs/reviews/phase3/PHASE_3_D063_LIMIT10_REPAIR_REVIEW_*_2026_05_05.md`
  (per-reviewer plus rereview) — under REVIEW-0020.
- `docs/reviews/phase3/PHASE_3_D063_LIMIT50_VALIDATION_REPAIR_*_2026_05_05.md`
  (per-reviewer plus rereview) — under REVIEW-0021.
- `docs/reviews/phase3/RFC_0013_OPERATIONAL_ISSUE_LOOP_REVIEW_*_2026_05_05.md`
  (per-reviewer plus rereview) — under REVIEW-0022.
- `docs/reviews/phase3/PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_REVIEW_*_2026_05_06.md`
  and supporting spec/spec-review/spec-synthesis docs — under REVIEW-0025.
- `docs/reviews/phase3/PHASE_3_LIMIT500_STILL_INVALID_*_2026_05_06.md`
  (per-reviewer plus problem/policy/spec docs) — under REVIEW-0027.
- `docs/reviews/phase3/PHASE_3_LIMIT500_SCHEMA_REJECTION_REPAIR_*_2026_05_06.md`
  — under REVIEW-0026.
- `docs/reviews/rfc-0014-operational-artifact-home/RFC_0014_REVIEW_*.md` (root) —
  under REVIEW-0028.
- `docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-2/RFC_0014_REVIEW_*.md`
  and `RFC_0014_FINAL_REVIEW.md`, `RFC_0014_FINDINGS_LEDGER.md`,
  `RUN_EVIDENCE.md`, `VALIDATION_NOTES.md` — under REVIEW-0029.
- `docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun-4/RFC_0014_REVIEW_*.md`
  and `RFC_0014_FINAL_REVIEW.md`, `RFC_0014_FINDINGS_LEDGER.md`,
  `RUN_EVIDENCE.md`, `VALIDATION_NOTES.md` — under REVIEW-0030.
- `docs/reviews/rfc-0014-operational-artifact-home/reruns/2026-05-06-redaction-rerun/`
  and `2026-05-06-redaction-rerun-3/` — context-only reruns; aggregated under
  REVIEW-0028.
- `docs/reviews/rfc-0014-operational-artifact-home/AGENT_RUNNER_VALIDATION_NOTES.md`
  and `BRANCH_REVIEW_codex_2026_05_06.md` — RFC 0014 dogfood evidence; under
  REVIEW-0028.
- `docs/reviews/v1/BENCHMARK_SEGMENTATION_HARNESS_REVIEW.md`,
  `BENCHMARK_SEGMENTATION_HARNESS_IMPLEMENTATION_REVIEW.md`,
  `BENCHMARK_SEGMENTATION_HARNESS_IMPLEMENTATION_REREVIEW_2026_05_03.md`,
  `BENCHMARK_SEGMENTATION_SHORT_PUBLIC_MODEL_RUN_2026_05_03.md` — under
  REVIEW-0010 / REVIEW-0011.
- `docs/reviews/v1/BENCHMARK_SEGMENTATION_EARLY_SIGNAL_*_2026_05_04.md`
  (spec-review, run, implementation-review) — under REVIEW-0012 / REVIEW-0013.
- `docs/reviews/rfc0025/RFC_0025_COMMAND_NAMES_REVIEW_*.md`,
  `RFC_0025_COMMAND_NAMES_FINDINGS_LEDGER.md`,
  `RFC_0025_COMMAND_NAMES_FINAL_REVIEW.md`, `EVIDENCE.md`, and
  `RUN_SUMMARY.md` — under REVIEW-0034.
- Phase 3 pipeline run reports (`PHASE_3_PIPELINE_*`,
  `PHASE_3_POSTBUILD_RUN_*`, `PHASE_3_POSTBUILD_*_REPAIR*`,
  `PHASE_3_POST_LIMIT50_EXPANSION_PLAN_2026_05_05.md`,
  `PHASE_3_FULL_RUN_CONSOLIDATOR_NULL_GROUP_KEY_FINDING_2026_05_06.md`,
  `PHASE_3_LIMIT500_NULL_OBJECT_REPAIR_LIVE_RERUN_2026_05_06.md`,
  `PHASE_3_LIMIT500_SCHEMA_REJECTION_REPAIR_RERUN_2026_05_06.md`,
  `PHASE_3_LIMIT500_STILL_INVALID_PROBLEM*`,
  `PHASE_3_LIMIT500_STILL_INVALID_POLICY_DECISION_2026_05_06.md`,
  `PHASE_3_LIMIT500_STILL_INVALID_REPAIR_SPEC_2026_05_06.md`) are run/spec
  evidence rather than review content; they are not separately numbered and
  flow under the nearest synthesis or findings ID for their iteration.
- All marker files under `docs/reviews/phase3/markers/` and
  `docs/reviews/phase3/postbuild/markers/**` — process state markers, not
  numbered.
