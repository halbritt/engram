# Phase 3 Agent Runbook

This runbook coordinates the multi-model Phase 3 path from RFC 0011 to the
first claim-extraction / belief-consolidation pipeline run.

It is process guidance, not product architecture. Binding architecture still
lands in `DECISION_LOG.md`, `BUILD_PHASES.md`, `SPEC.md`, and the Phase 3 spec.

## Model Roles

| Role | Preferred model | Responsibility |
| --- | --- | --- |
| Coordinator | Codex GPT-5.5 | Owns sequencing, marker checks, synthesis, repo edits, tests, commits, and pushes. |
| Architecture author | Claude Opus 4.7 | Drafts and revises the Phase 3 spec from RFC 0011 and canonical docs. |
| Broad adversarial reviewer | Gemini Pro 3.1 | Checks consistency across docs, unresolved decisions, privacy/local-first drift, and missing cases. |
| Implementation reviewer | Codex GPT-5.5 | Checks schema feasibility, code/test implications, migration risk, and operator ergonomics. |
| Secondary architecture reviewer | Claude Opus 4.7 fresh context | Reviews the spec or build prompt without preserving draft-context attachment. |
| Builder / operator | Codex GPT-5.5 | Implements code, runs local tests, regenerates schema docs, and starts bounded local pipeline runs. |

Use as many review sessions as useful, but keep write ownership narrow. Review
agents write only under `docs/reviews/phase3/` unless their prompt explicitly
assigns edits elsewhere.

## Same-Branch Rules

All agents may run in tmux on the same branch. To keep this survivable:

- Only one agent edits source/spec/prompt files at a time.
- Review agents may run in parallel if each writes a unique review file.
- Do not commit from worker sessions unless the coordinator explicitly asks.
- Before writing, check `git status --short` and avoid overwriting unrelated
  changes.
- If a marker says a step is complete but required files are missing, stop and
  report the mismatch instead of guessing.

## Marker Contract

Markers live under:

```text
docs/reviews/phase3/markers/
```

The directory is tracked with `.gitkeep`. If an agent runs before the directory
exists in its checkout, it should create it with:

```bash
mkdir -p docs/reviews/phase3/markers
```

Each marker is a small Markdown file, not an empty sentinel. It must include:

- prompt ordinal and title,
- model / agent name,
- started and completed timestamp,
- files written or modified,
- verification performed,
- next expected marker.

Marker names:

| Step | Marker |
| --- | --- |
| 1. Spec draft | `01_SPEC_DRAFT.ready.md` |
| 2. Spec reviews | `02_SPEC_REVIEW_<model_slug>.ready.md` |
| 3. Spec findings ledger | `03_SPEC_FINDINGS_LEDGER.ready.md` |
| 4. Spec synthesis | `04_SPEC_SYNTHESIS.ready.md` |
| 5. Build prompt draft | `05_BUILD_PROMPT_DRAFT.ready.md` |
| 6. Build prompt reviews | `06_BUILD_PROMPT_REVIEW_<model_slug>.ready.md` |
| 7. Build prompt synthesis | `07_BUILD_PROMPT_SYNTHESIS.ready.md` |
| 8. Build complete | `08_BUILD_COMPLETE.ready.md` |
| 9. Build reviews | `09_BUILD_REVIEW_<model_slug>.ready.md` |
| 10. Build review synthesis | `10_BUILD_REVIEW_SYNTHESIS.ready.md` |
| 11. Pipeline started | `11_PIPELINE_STARTED.ready.md` |

Review steps are fan-out / fan-in. The coordinator decides how many review
markers are enough before synthesis, but the default is one each from Gemini,
Codex, and Opus fresh context.

## Prompt Chain

Run these in order:

1. `prompts/P021_generate_phase_3_claims_beliefs_spec.md`
2. `prompts/P022_review_phase_3_claims_beliefs_spec.md`
3. `prompts/P023_record_phase_3_spec_findings.md`
4. `prompts/P024_synthesize_phase_3_spec_findings.md`
5. `prompts/P025_write_phase_3_build_prompt.md`
6. `prompts/P026_review_phase_3_build_prompt.md`
7. `prompts/P027_synthesize_phase_3_build_prompt_findings.md`
8. `prompts/P028_build_phase_3_claims_beliefs.md`
9. `prompts/P029_review_phase_3_build.md`
10. `prompts/P030_synthesize_phase_3_build_review_findings.md`
11. `prompts/P031_begin_phase_3_pipeline.md`

The build prompt (`P028`) starts as a guarded target artifact. It should not be
executed until `P025` drafts it from the accepted spec and `P027` applies build
prompt review findings.

## Human Checkpoints

Pause for the owner before:

- accepting a predicate vocabulary if review models disagree materially,
- changing local-first / no-egress posture,
- allowing any hosted service or external persistence,
- starting a full-corpus Phase 3 run,
- authoring gold-set answers.
