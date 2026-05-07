# RFC 0014 Branch Review

Date: 2026-05-06
author: reviewer-codex-gpt-5.5-001
Reviewed head: `19ca7d0` (`agent-runner/rfc-0014-validation`)
Scope: pull latest branch state, review the promoted RFC 0014 operational
artifact home changes, and record findings.

## Summary

The branch correctly records owner acceptance of RFC 0014, promotes the spec
into Phase 3 implementation scope, updates the runbook, and adds tests around
new operations-root and legacy marker interaction.

The remaining issues are implementation-contract mismatches in the marker gate
script and one unresolved spec wording/detail mismatch from the rerun-4
synthesis. These should be fixed before relying on the script as the accepted
RFC 0014 gate.

## Findings

### P1: Schema-bearing marker validation is incomplete and can allow malformed ready markers to avoid blocking

Files:

- `scripts/phase3_tmux_agents.sh`
- `docs/process/operational-artifact-home-spec.md`
- `tests/test_phase3_tmux_agents.py`

Relevant code:

- `scripts/phase3_tmux_agents.sh:180`
- `scripts/phase3_tmux_agents.sh:192`
- `scripts/phase3_tmux_agents.sh:258`
- `docs/process/operational-artifact-home-spec.md:178`
- `docs/process/operational-artifact-home-spec.md:243`

`marker_schema_error` currently checks only front matter presence,
`created_at` parseability, `corpus_content_included: none`, and a narrow
hardcoded `/home/...` path pattern. The accepted spec says new and migrated
schema-bearing markers must have all required front matter fields and that
malformed, missing, ambiguous, contradictory, or privately contaminated marker
front matter fails closed.

A `ready` marker with missing `issue_id`, missing `family`, missing
`linked_report`, missing `scope`, or an unknown `state`/`gate` value is not
currently treated as malformed. If it is not otherwise blocking, `next` can
ignore it instead of surfacing a human checkpoint. The tests cover missing front
matter but do not cover missing required fields or invalid enum values.

Recommended fix: make marker schema validation explicit for all required
fields and enum values, and add fixtures for malformed ready markers that must
block.

### P1: Marker timestamp validation is not portable and does not enforce timezone-aware timestamps

Files:

- `scripts/phase3_tmux_agents.sh`
- `docs/process/operational-artifact-home-spec.md`
- `tests/test_phase3_tmux_agents.py`

Relevant code:

- `scripts/phase3_tmux_agents.sh:170`
- `scripts/phase3_tmux_agents.sh:196`
- `docs/process/operational-artifact-home-spec.md:225`
- `docs/process/operational-artifact-home-spec.md:328`

The implementation uses GNU `date -u -d` and GNU `stat -c`. On the local macOS
environment, `date -u -d '2026-05-06T01:00:00' +%s` exits with an illegal-option
error. Because the new schema gate calls `date -u -d` directly, valid
schema-bearing markers will fail closed on macOS instead of being evaluated.

The accepted rerun-4 synthesis also required timezone-aware RFC3339/ISO-8601
timestamps with `Z` or a numeric offset. The spec still says only "ISO-8601
timestamp", and the shell implementation delegates acceptance to `date -d`,
which is not a precise contract and can accept non-contract timestamp forms on
platforms where it exists.

Recommended fix: replace the shell date/stat parsing with a portable validator
or a small Python helper that requires `Z` or `+/-HH:MM`, normalizes to epoch
seconds, and has fixtures for naive timestamps, malformed timestamps, and both
Linux and macOS execution.

### P2: Human-checkpoint resolution evidence is weaker than the accepted finding

Files:

- `scripts/phase3_tmux_agents.sh`
- `docs/process/operational-artifact-home-spec.md`
- `tests/test_phase3_tmux_agents.py`

Relevant code:

- `scripts/phase3_tmux_agents.sh:280`
- `scripts/phase3_tmux_agents.sh:330`
- `docs/process/operational-artifact-home-spec.md:236`
- `docs/process/operational-artifact-home-spec.md:326`
- `tests/test_phase3_tmux_agents.py:281`

The rerun-4 synthesis required a machine-checkable owner-decision signal for
ready markers that resolve human checkpoints. The current helper returns true
when `linked_report` or `linked_decision` is merely present. Since
`linked_report` is already part of the general marker defaults, this does not
prove the owner decision was recorded.

Recommended fix: require explicit owner-decision front matter on the resolving
ready marker, for example `owner_decision: recorded` plus
`owner_decision_evidence: <repo-relative path>`, or require a linked report path
whose front matter is validated for the same fields.

### P2: D060 path hygiene enforcement only catches Linux-style home paths

Files:

- `scripts/phase3_tmux_agents.sh`
- `docs/process/operational-artifact-home-spec.md`

Relevant code:

- `scripts/phase3_tmux_agents.sh:199`
- `docs/process/operational-artifact-home-spec.md:146`
- `DECISION_LOG.md:82`

D060 says new documentation, prompts, and generated logs must avoid hardcoded
home-directory absolute paths. The script rejects only `/home/...`, so
macOS-style `/Users/<account>/...` paths and other platform home-directory
forms are not rejected. The spec also says "should use" at one point even though
the acceptance criteria say path hygiene is enforced.

Recommended fix: make the spec wording consistently mandatory, and validate
common home-directory forms, at least `/home/<name>/...`, `/Users/<name>/...`,
and the current `$HOME` path when available.

### P3: The canonical report filename still conflicts with the accepted synthesis

File:

- `docs/process/operational-artifact-home-spec.md`

Relevant lines:

- `docs/process/operational-artifact-home-spec.md:90`
- `docs/process/operational-artifact-home-spec.md:96`

The rerun-4 synthesis accepted a rename from `reports/05_REPAIR_VERIFICATION.md`
to `reports/05_REPAIR_VERIFIED.md`. The accepted spec still lists
`05_REPAIR_VERIFICATION.md` for the report while the marker is
`05_REPAIR_VERIFIED.ready.md`.

Recommended fix: choose the canonical report filename in the accepted spec and
keep the RFC sketch, runbook, scripts, and fixtures aligned with that spelling.

## Verification

- Ran `git pull --ff-only`; branch fast-forwarded to `19ca7d0`.
- Attempted `pytest tests/test_phase3_tmux_agents.py`; local `pytest` command
  was not installed in this environment, so the test suite was not executed.
- Probed local `date -u -d` support; it is unavailable on this macOS
  environment, which confirms the portability risk above.
