---
schema_version: "striatum.alignment_handoff.v1"
artifact_kind: "handoff"
---

# RFC 0047 Retrieval Boundary Alignment
author: operator [self-declared: alignment-rfc0047]

Status: handoff
Date: 2026-05-14
Run ID: run_169531d5568248ff8f0dfc803d955311
Job: align_rfc0047_retrieval_boundary
Scope: Proposal-text alignment only. This artifact does not promote RFC 0047,
authorize implementation, alter runtime behavior, commit, publish, close a
workflow, or update Striatum state.

## Findings Addressed

- F003: RFC 0047 now requires unauthorized, `no_data`, and tenant/corpus
  pair-mismatch responses to omit or null corpus inventory metadata, including
  bundle ids, bundle hashes, source time bounds, staleness, hidden labels,
  row counts, and hidden paths. The failure table and freshness rules now
  carry the same redaction posture.
- F004: RFC 0047 now names `identity.instance_label`,
  `identity.repository_label`, and `identity.repository_root_hint` as
  display-only, privacy-inherited metadata. The text forbids using those fields
  as authorization, discovery, join, or collision inputs and requires
  unauthorized/not-visible diagnostics to omit or redact them.
- F013: RFC 0047 examples now use opaque RFC 0045 `bundle_id` values such as
  `striatum.bundle:<stable-local-id>`, with `bundle_sha256` represented as a
  separate integrity hash.
- Source time bounds and staleness: RFC 0047 now scopes these fields to
  authorized visible result sets and forbids stale-rejected `no_data` responses
  from leaking rejected staleness metadata.

## Findings Deferred

- F006: `fetch_reference` reauthorization remains in RFC 0047 text, but
  reference replay/collision proof remains deferred to implementation tests and
  RFC 0049 gate evidence.
- F014: exact-reference vocabulary changes for `workflow_job_id` and `job_id`
  remain deferred to the RFC 0046/RFC 0049 alignment lane. RFC 0047 already
  exposes those identifiers as request filters.
- No code, migration, generated schema, decision-log, changelog, runtime, or
  Striatum-state evidence was produced by this alignment. Routine default-on
  memory remains blocked until accepted/promoted RFC 0045-RFC 0048 successors
  exist and applicable RFC 0049 gates pass.

## Files Changed

- `docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md`
- `docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0047.md`

## Dependency Impact

- RFC promotion: the RFC 0047 proposal text now addresses the F003, F004, and
  F013 alignment blockers identified for promotion review. This handoff does
  not promote the RFC.
- Implementation: implementation remains blocked on an accepted/promoted
  contract, RFC 0044 hardening or equivalent EG-000 evidence, and applicable
  RFC 0049 gates for authorization, redaction, reference replay, no-egress,
  freshness, and latency.
- Routine Striatum use: Level 3/default-on automatic memory remains blocked.
  Any earlier manual/local search remains limited to explicit, cited,
  scope-limited, local read-only use under the RFC 0049 constraints.

## Validation

- Ran:
  `git diff --check -- docs/rfcs/0047-striatum-retrieval-augmentation-boundary.md docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0047.md`
- Result: passed with exit code 0 and no output.
- Because `ALIGN_RFC0047.md` is a new untracked file, also ran:
  `git diff --no-index --check /dev/null docs/reviews/striatum-memory-rfc-alignment-2026-05-14/ALIGN_RFC0047.md`
- Result: no whitespace-check output; command exited 1 as expected for a
  no-index comparison against `/dev/null`.
- `make check-refs` was not run because this alignment did not change
  references or anchors.

## Workflow Friction

- The first native sub-agent spawn attempt was rejected because full-history
  forks cannot override agent type; the agents were retried as read-only
  explorers without forking.
- The user-named synthesis, ledger, and repair review paths under the Striatum
  run directory were absent. The workflow JSON points those inputs to
  `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/`, which was used.
- The expected alignment review directory did not exist and was created for the
  required handoff artifact.
