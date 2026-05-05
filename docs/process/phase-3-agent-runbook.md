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
| 4b. Same-model synthesis re-review after any `reject_for_revision` | `04_SPEC_SYNTHESIS_REVIEW_<model_slug>.ready.md` |
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

If any fan-out reviewer returns `reject_for_revision`, the rejecting model must
re-review the post-synthesis artifact before the next artifact is drafted. A
passing re-review writes `04_SPEC_SYNTHESIS_REVIEW_<model_slug>.ready.md`.
A still-rejecting re-review writes `04_SPEC_SYNTHESIS_REVIEW_<model_slug>.blocked.md`
and deliberately leaves the ready marker absent, so downstream tmux jobs remain
blocked.

A blocked same-model re-review is a human checkpoint, not an automatic repair
loop. The owner decides whether to revise the synthesis, accept the residual
risk, or redirect the phase. Do not create the build prompt until the owner has
resolved the block and the same-model re-review writes the ready marker.

## Prompt Chain

Run these in order:

1. `prompts/P021_generate_phase_3_claims_beliefs_spec.md`
2. `prompts/P022_review_phase_3_claims_beliefs_spec.md`
3. `prompts/P023_record_phase_3_spec_findings.md`
4. `prompts/P024_synthesize_phase_3_spec_findings.md`
5. `prompts/P024_review_phase_3_spec_synthesis_codex.md` when Codex rejected
   the P022 spec draft.
6. `prompts/P025_write_phase_3_build_prompt.md`
7. `prompts/P026_review_phase_3_build_prompt.md`
8. `prompts/P027_synthesize_phase_3_build_prompt_findings.md`
9. `prompts/P028_build_phase_3_claims_beliefs.md`
10. `prompts/P029_review_phase_3_build.md`
11. `prompts/P030_synthesize_phase_3_build_review_findings.md`
12. `prompts/P031_begin_phase_3_pipeline.md`

The build prompt (`P028`) starts as a guarded target artifact. It should not be
executed until `P025` drafts it from the accepted spec and `P027` applies build
prompt review findings.

## Tmux Automation

The helper script:

```text
scripts/phase3_tmux_agents.sh
```

can create a tmux session with one window per step. Every window starts
immediately, waits on its required marker files, then either prints the prompt
to run or pipes the prompt into a configured model command.

Print-mode start:

```bash
scripts/phase3_tmux_agents.sh start
tmux attach -t engram-phase3
```

Print mode is safest when model CLIs are interactive. The ready pane shows the
model slug, prompt path, and expected marker.

Pipe-mode start, for CLIs that accept prompts on stdin:

```bash
export PHASE3_RUN_MODE=pipe
export CLAUDE_CMD='claude --model opus --dangerously-skip-permissions'
export CODEX_CMD='codex -a never exec --model gpt-5.5 --sandbox danger-full-access -'
export GEMINI_CMD='gemini --model gemini-3.1-pro-preview --yolo'
scripts/phase3_tmux_agents.sh start
tmux attach -t engram-phase3
```

These are also the script defaults in pipe mode. Claude is pinned to `opus` so
it does not fall back to Sonnet, Codex is pinned to `gpt-5.5`, and Gemini is
pinned to `gemini-3.1-pro-preview`. If a CLI needs different explicit model
selection, set the full command string yourself, for example:

```bash
export CLAUDE_CMD='claude --model <your-opus-id> --dangerously-skip-permissions'
export CODEX_CMD='codex -a never exec --model <your-gpt-5.5-id> --sandbox danger-full-access -'
export GEMINI_CMD='gemini --model <your-gemini-pro-3.1-id> --yolo'
```

Adjust command strings to the actual local launchers if a CLI spells its
permission flag differently. The script appends a small coordinator injection
containing the model slug, expected marker path, and worktree path.

Progress checks:

```bash
scripts/phase3_tmux_agents.sh status
scripts/phase3_tmux_agents.sh next
```

`status` and `next` also surface post-build operational blockers under
`docs/reviews/phase3/postbuild/markers/`. A `.blocked.md` or
`.human_checkpoint.md` marker blocks expansion until a later reviewed repair
creates an accepted ready marker for that operational loop.

## Post-Build Operational Issue Loop

RFC 0013 governs operational issues found after build review, including bounded
runtime failures, schema/preflight drift, marker mismatches, and unsafe
downstream transitions.

When a bounded post-build run hits a stop condition:

- stop expansion immediately;
- write a redacted run report under `docs/reviews/phase3/`;
- write a blocked or human-checkpoint marker under
  `docs/reviews/phase3/postbuild/markers/`;
- classify the issue using RFC 0013 issue classes;
- keep old markers as provenance instead of deleting them;
- use `docs/process/multi-agent-review-loop.md` for any non-trivial repair,
  run-gate change, derived-state policy change, or human-checkpoint change.

Tracked run reports and markers must not contain private corpus content: no raw
message text, segment text, prompt/completion payloads, extracted claim/belief
values, private names, exact conversation titles, or corpus-derived prose
summaries. If private content is needed for diagnosis, store it only in an
untracked local diagnostics path and reference a redacted summary from tracked
docs. Do not introduce machine-specific home-directory paths; use `~/`,
environment variables, or repository-relative paths.

Same-model re-review is required when any reviewer returns
`reject_for_revision`. A still-rejecting re-review is a human checkpoint.

Before moving to a larger bound, the repair must pass the applicable RFC 0013
ladder: focused tests, full tests when code changed, live no-model preflight,
`pipeline-3 --limit 0`, targeted rerun of the failing scope when feasible,
same-bound rerun when the failure was bound-scoped, and a new redacted report
and marker.

Default blockers for expansion include any nonzero command exit, failed
extraction or downstream stage inside the selected scope, prompt/model contract
failure, unrepaired partial downstream state, dropped-claim rate above 10% of
inserted plus dropped claims, unapplied accepted findings, or missing required
same-model re-review.

Progress-ledger state alone is not an enforceable quarantine for active derived
rows. A ready marker requires proof that affected rows cannot feed downstream
consumers or proof that they were repaired through requeue, close, supersede, or
rebuild paths with before/after counts.

## Human Checkpoints

Pause for the owner before:

- accepting a predicate vocabulary if review models disagree materially,
- continuing after a same-model synthesis re-review remains
  `reject_for_revision`,
- changing local-first / no-egress posture,
- allowing any hosted service or external persistence,
- overriding RFC 0013 operational blockers or retaining visible partial derived
  state,
- proceeding after `pipeline-3 --limit 50`,
- starting a full-corpus Phase 3 run,
- authoring gold-set answers.
