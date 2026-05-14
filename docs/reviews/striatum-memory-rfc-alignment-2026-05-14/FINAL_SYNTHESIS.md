---
schema_version: "striatum.synthesis.v1"
artifact_kind: "synthesis"
---

author: operator [self-declared: alignment-final-synthesis]

# Striatum Memory RFC Alignment Final Synthesis

Status: final_synthesis
Date: 2026-05-14
Run ID: run_169531d5568248ff8f0dfc803d955311
Job ID: job_run_169531d5568248ff8f0dfc803d955311_final_synthesis
Session ID: sess_b76ea7c03aae4969a0a3f753160335fe
Lease ID: lease_51ee4d0236db4a2db512746ab706c2f9

## Workflow Outcome

The Striatum memory RFC alignment package is complete as a review and alignment
artifact. Current roll-up status is `accept_with_findings` / proposal-aligned:
no active blockers remain in the alignment package, and the open work is
classified below for a separate promotion or implementation handoff.

The package is ready to feed a separate promotion packet. It is not itself that
promotion packet. The promotion packet still needs to explicitly accept,
reject, or supersede the alignment handoffs and carry the preconditions and
active findings forward.

This synthesis does not promote RFCs, authorize implementation, change runtime
behavior, enable default-on Striatum memory, publish Striatum state, complete a
workflow, or record a Striatum verdict.

## Blockers

None active.

The original operator-ergonomics blocker B001 was repaired in RFC 0046 proposal
text and accepted on fresh re-review. RFC 0046 now chooses direct copied
authorization/provenance columns for retrieval-visible rows and uses joins as
mandatory consistency checks. The original ergonomics `needs_revision` verdict
was superseded by operator override after the accepted repair re-review. The
remaining copied-provenance enforcement mechanism choice is deferred to later
implementation design, not an active alignment blocker.

## Promotion And Implementation Findings

Active promotion/implementation findings remain nonblocking for this
proposal-only alignment package:

- Major contract hardening: RFC 0047 exact-reference request shape (`AL-N001`);
  retrieval-to-packet omitted-candidate/audit continuity (`AL-N002`); RFC 0046
  required embedding profile plus active embedding/skip XOR invariant
  (`AL-N003`); projection `raw_payload` privacy inheritance and EG-060 fixture
  coverage (`AL-N004`).
- Retrieval and packet polish before implementation: dirty-working-tree
  surfacing and gate coverage (`AL-N005`); RFC 0048 local-only/no-egress audit
  storage plus RFC 0047/RFC 0049 transport wording alignment (`AL-N006`);
  response-status to packet-label mapping (`AL-N010`); workflow/job identifiers
  in citations where available (`AL-N011`).
- Cleanup before promotion: stale redaction open-decision text in RFC 0046/RFC
  0048 (`AL-N007`); stale RFC 0049 `identity_leak`/`citation_leak` gate-local
  wording (`AL-N008`); RFC 0047 authority wording that implies RFC 0045 is
  already accepted (`AL-N014`).
- Gate detail before scaffolding: RFC 0049 disable-control restart/promotion
  cases (`AL-N009`); concrete Level 1 manual/raw-only quality checklist
  (`AL-N013`); manual paste-through fixture for personal or non-primary results
  if that path is promoted (`AL-N015`).
- Process posture: the next promotion packet should explicitly accept or reject
  the alignment handoffs, then move to RFC 0044 hardening / EG-000 evidence
  before implementation treats the contracts as binding (`AL-N012`).

## Deferred Items

Deferred items are not blockers for this synthesis, but they gate later
authority or implementation:

- RFC 0044 Phase 0 hardening or EG-000-equivalent evidence remains required
  before projection, retrieval, or operator-context implementation depends on
  the current Striatum substrate (`AL-D001`).
- RFC 0045-RFC 0048 remain proposal material until a recorded decision,
  accepted spec, or promoted successor makes them binding (`AL-D002`).
- Routine Level 3/default-on automatic memory remains blocked until
  accepted/promoted upstream contracts exist and required RFC 0049 gates pass
  (`AL-D003`).
- Generated memory products remain ineligible for Level 2 and Level 3 injection
  until a separate accepted privacy-inheritance, citation, audit, and gate
  contract exists (`AL-D004`).
- Audit storage home, collapsed `no_data` ergonomics, stale-memory automatic
  inclusion, gate-report homes/commands, RFC 0044 hardening links,
  current-authority conflict warnings, and session-disable restart/promotion
  coverage remain deferred design or gate-detail work (`AL-D005`-`AL-D011`).

## Workflow Friction

Workflow friction should be carried as process cleanup, not product policy:

- A run summary reported `doctor ok=false` without detailed failure in the
  summary; workflow-state consistency should be confirmed before publishing
  verdicts (`AL-W001`).
- Some native sub-agent attempts failed when combining a full-history fork with
  an explicit explorer role; non-forked/read-only explorers succeeded
  (`AL-W002`).
- Prompt-named upstream inputs were absent under the prompt-local Striatum run
  path; future prompts should point directly at committed review artifacts
  (`AL-W003`).
- The shared worktree had out-of-scope edits and untracked directories; those
  must be reconciled by the operator, not by this synthesis (`AL-W004`).
- Early lanes had setup/path friction, the Gemini ergonomics lane was replaced
  by operator recovery output, and some per-RFC handoffs are stale in isolation;
  the findings ledger is the current roll-up status (`AL-W005`-`AL-W007`).

## Operator-Ready Next Actions

1. Prepare a separate promotion packet that explicitly accepts, rejects, or
   supersedes the alignment handoffs. Keep the packet clear that proposal text
   alone does not authorize implementation, runtime behavior, or default-on
   memory.
2. Produce RFC 0044 Phase 0 hardening or EG-000-equivalent evidence before any
   projection, retrieval, or operator-context implementation handoff depends on
   the Striatum substrate.
3. Resolve the major contract findings for promotion readiness: exact-reference
   request shape, omitted-candidate/audit continuity, embedding activation/skip
   invariants, and `raw_payload` privacy inheritance.
4. Clean up promotion-polish findings: dirty-state rendering, audit no-egress
   wording, stale redaction and omission-code wording, status-label mapping,
   workflow/job citation rendering, RFC 0047 authority wording, and Level 1
   checklist coverage.
5. Assemble no-egress and gate evidence before routine use: EG-020 no-egress,
   EG-060 privacy/redaction, EG-070 exact/search coverage, EG-110 audit
   reconstruction, EG-120 disable controls, and any Level 3/default-on gates
   applicable to the proposed scope.
6. Keep personal-memory and generated-product work out of the ordinary
   Striatum raw/source-memory path unless a separate accepted contract covers
   privacy inheritance, citation, audit, opt-in, and gates.

## Validation

Validation command used for this untracked artifact:

```sh
git diff --no-index --check /dev/null docs/reviews/striatum-memory-rfc-alignment-2026-05-14/FINAL_SYNTHESIS.md
```

Result: passed with no whitespace or conflict-marker output. Exit code 1 is
expected for a no-index comparison between `/dev/null` and a present untracked
file.
