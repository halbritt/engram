# RFC 0014 Review - Operational Artifact Home

Author: reviewer / claude / Claude Opus / review_claude
Date: 2026-05-06
Subject: docs/rfcs/0014-operational-artifact-home.md
Reviewer: Claude Opus (root reviewer for run run_e1e472612df34abe8f0daef7cf9ffd32)

## Findings

### High

**H1. Migration plan is underspecified for a later implementation prompt.**
RFC 0014 § Migration Plan lists six steps but several lack the precision needed
to drive a later implementation prompt:
- Step 1 ("Update RFC 0013") does not enumerate the sections that must change.
  RFC 0013 § 3 (committed paths), § 4 (artifact ordering), § 5 (the example
  marker tree `docs/reviews/<area>/postbuild/markers/<YYYYMMDD>_<run_slug>/`),
  and § 10 (script responsibilities) all reference `docs/reviews/`. An
  implementation prompt needs that explicit list, not "update RFC 0013."
- Step 3 ("Update `scripts/phase3_tmux_agents.sh` to read blocked/ready markers
  from the new operations root") does not say whether the script should scan
  both roots simultaneously during transition or pivot exclusively to the new
  root with a fallback. Step 4 mentions "compatibility handling" but does not
  specify the mechanism (dual-glob, symlink, migration manifest, etc.).
- The `linked_report` and `supersedes` front-matter fields in RFC 0013 § 5
  currently point at `docs/reviews/...`. The migration plan does not state
  whether existing markers' fields are left alone (preserving historical paths)
  or rewritten (touching audit provenance). The non-goal "do not move existing
  artifacts unless the owner explicitly asks" implies "leave them," but the
  implementation prompt should not have to infer that.

**H2. RFC 0014 does not anchor marker precedence to the new directory shape.**
The acceptance criterion "the marker precedence rules from RFC 0013 still work"
depends on RFC 0013 § 5: newest-state-per-(`issue_id`,`family`), explicit
`supersedes` to retire a `blocked` with a `ready`, and blocking by any newer
`blocked` or `human_checkpoint`. Because RFC 0014 changes the directory shape
from `docs/reviews/<area>/postbuild/markers/<YYYYMMDD>_<run_slug>/` to
`docs/operations/<area>/<loop_id>/markers/`, the implementer must be told that
precedence is computed *within* `<loop_id>` (the new analogue of
`<YYYYMMDD>_<run_slug>`) and not across `<area>`. This should be stated in the
Proposal or Artifact Rules section, not left to an inference from the example
layout.

### Medium

**M1. Reports and markers share `.<state>.md` suffixes and canonical numbering,
blurring the report/marker distinction.**
The example layout shows `reports/01_RUN.blocked.md` and
`markers/01_RUN.blocked.md` as siblings. RFC 0013 § 4 treats redacted run
reports (prose) and machine-readable markers (YAML front matter) as distinct
artifact families with different consumers. Identical filenames in sibling
directories invite confusion about which file scripts read for gate state.
Recommend either prose-only report names (e.g., `01_RUN_REPORT.md`) or an
explicit rule that automation only ever reads the `markers/` subtree.

**M2. The per-loop `README.md` is introduced without redaction guidance.**
The Artifact Rules section governs reports and markers but is silent on the new
per-loop `README.md`. README files are the highest-risk surface for narrative
leakage of corpus content because authors instinctively write "what happened in
this run" prose. Either drop the README (open question 3 already raises this) or
extend the redaction rules to explicitly cover it and forbid corpus-derived
prose summaries.

**M3. Path example references the wrong RFC number.**
The review-artifact example reads
`docs/reviews/phase3/RFC_0013_OPERATIONAL_ARTIFACT_HOME_REVIEW_<model_slug>_2026_05_05.md`.
This document is RFC 0014; the example should read `RFC_0014_...`. Minor, but
confusing in a document whose subject is path discipline.

### Low

**L1. Open Questions are unresolved and not gated by the Acceptance Criteria.**
Four open questions remain (root name `operations` vs `ops` vs `operational`,
marker/report consolidation, README requirement, area scoping `phase3-postbuild`
vs `postbuild/phase3`). The Acceptance Criteria do not require these to be
resolved or explicitly deferred before acceptance, which lets the next
implementer inherit the choice silently. Recommend adding "open questions
resolved or explicitly deferred" to acceptance criteria.

**L2. Phase 3 example path omits the inner `reports/` and `markers/`
directories.**
`docs/operations/phase3-postbuild/<YYYYMMDD>_<run_slug>/` does not show the
`<area>/<loop_id>/{reports,markers}/` shape applied to Phase 3 (i.e.,
`<area> = phase3-postbuild`, `<loop_id> = <YYYYMMDD>_<run_slug>`). One
clarifying line removes the ambiguity.

**L3. No sunset condition for legacy-path compatibility.**
Step 4 adds compatibility for `docs/reviews/phase3/postbuild/markers/` but
offers no retirement criterion. Even a soft condition ("until no `blocked` or
`human_checkpoint` markers remain in the legacy path") prevents indefinite
dual-scanning by automation.

## What This Proposal Does Well

- The three-way split -- `docs/operations/` for committed redacted operational
  state, `docs/reviews/` for model review feedback, `logs/operational/` for
  untracked local diagnostics -- cleanly resolves the overload identified in
  the Problem section, and the non-goals correctly forbid raw corpus content and
  any silent migration.
- The Artifact Rules section reproduces RFC 0013's allow/deny redaction lists
  faithfully; the privacy posture survives the proposed move intact.
- Marker filename conventions (`01_RUN.<state>.md` ... `05_REPAIR_VERIFIED.<state>.md`)
  match RFC 0013 § 5 exactly, so existing marker-parsing logic stays stable
  across the move.
- The local-first constraint is explicitly preserved, and the RFC declines to
  change Phase 3 expansion gates as a side effect.

## Suitability For `agent_runner` Validation

This RFC is a sound bounded target for `agent_runner`. It is process-only,
modifies no code or data, has a small and self-contained source artifact, and
carries clear (if currently underspecified) acceptance criteria. The findings
above are the kind of gaps a multi-agent review loop is designed to surface,
which makes the exercise useful in both directions.

## Blocking Status

H1 and H2 are not blocking for accepting RFC 0014 as a *proposal*, but they
should be resolved before the migration step graduates into an implementation
prompt. The remaining findings are non-blocking polish.

Verdict: accept_with_findings
