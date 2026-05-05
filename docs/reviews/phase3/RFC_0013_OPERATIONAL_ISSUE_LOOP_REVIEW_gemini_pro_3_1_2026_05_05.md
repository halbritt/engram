# RFC 0013 Review - gemini_pro_3_1

Date: 2026-05-05
Reviewer: gemini_pro_3_1
Verdict: accept_with_findings

## Findings

### Medium: Missing Issue Class for Infrastructure and Environment Failures

The proposed issue classes cover data, model, schema, and orchestration failures. However, Engram relies heavily on local infrastructure (PostgreSQL, pgvector, local LLM endpoints, CUDA/Metal). A disk-full event, a CUDA Out-of-Memory error, or an unreachable local inference server is a distinct failure mode from `upstream_runtime_failure` (which implies a logic or model-capability failure inside a selected scope). Relying on `upstream_runtime_failure` for OOMs could lead to unnecessary prompt/model debugging when the fix is infrastructure repair.

Affected sections:
- Section 2 (Classify each issue before fixing it)

Proposed fix: Add an `infrastructure_or_environment_failure` class with the default action "Stop run; verify local dependencies, disk space, and inference server health before rerun."

### Medium: Verification Ladder Must Support Targeted Reruns

Section 5 (Verification ladder) specifies "the smallest bounded rerun that can exercise the repaired behavior". However, if an issue occurs on the 50th conversation of a `--limit 50` run due to specific conversational content, a generic `--limit 1` or `--limit 10` rerun might not encounter the repaired behavior at all. The CLI needs the ability to target the specific failed entity to truly verify the repair before resuming bounded expansion.

Affected sections:
- Section 5 (Verification ladder)

Proposed fix: Update step 5 to read "a targeted rerun of the specific failed entity (e.g., by UUID), or the smallest bounded rerun that guarantees exercising the repaired behavior".

### Low: Ambiguity in Resolving Blocked Markers

Section 3 and Section 8 define that new `.ready.md` and `.blocked.md` markers are added without deleting old ones. Section 8 says "status commands should show the newest blocked marker before older ready markers." It is not explicitly stated how an orchestration script knows that a *newer* `.ready.md` has resolved an *older* `.blocked.md` for the same step. The runbook relies on file timestamps, but this should be explicit in the architecture.

Affected sections:
- Section 8 (Script and runbook responsibilities)

Proposed fix: Explicitly state that a `.ready.md` resolves a prior `.blocked.md` for the same pipeline step if its timestamp is strictly greater, or specify a marker-naming convention that groups them (e.g., sharing the same step prefix).

## Non-Findings

- Local-first constraints and data immutability are strongly preserved. Section 6 accurately dictates that raw evidence remains immutable and explicitly requires that derivations be repaired auditably.
- Review and human checkpoints are appropriately placed in Section 4, avoiding the trap of skipping adversarial reviews for operational policy changes.
- Expansion gates correctly depend on human approval for large and full-corpus runs.

## Checks Run

- Verified alignment with `AGENTS.md` principles (preservation of immutable raw evidence, local-first posture).
- Cross-checked Phase 3 runbook marker definitions and failure processes against the proposed RFC.
- Validated consistency with `DECISION_LOG.md` (specifically D002, D017, and D060).

## Files Read

- `AGENTS.md`
- `docs/rfcs/0013-development-operational-issue-loop.md`
- `docs/process/multi-agent-review-loop.md`
- `docs/process/project-judgment.md`
- `docs/process/phase-3-agent-runbook.md`
- `docs/reviews/phase3/PHASE_3_POSTBUILD_RUN_LIMIT10_2026_05_05.md`
- `DECISION_LOG.md`
