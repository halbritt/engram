# Review: RFC 0014 Operational Artifact Home Spec Handoff Package

author: reviewer-claude-opus-001

Scope:

- `docs/rfcs/0014-operational-artifact-home.md`
- `docs/process/operational-artifact-home-spec.md`

Treated as: RFC = proposal/history record; spec = implementation contract under
review. The two are read together. The RFC explicitly cedes implementation
detail to the spec. I did not file a finding solely because a choice lives in
the spec rather than the RFC.

## Findings

### F1: Loop-scope vs root-scope precedence is ambiguous for flat legacy markers

Severity: major clarification, not blocking

References: spec Compatibility Semantics, Flat legacy marker rules 2 and 4;
spec Precedence rules rule 5; trailing paragraph "Precedence is computed
within a loop id."

The spec says a front-matterless flat legacy `.blocked.md` under
`docs/reviews/phase3/postbuild/markers/*.md` is a root-scoped Phase 3
post-build blocker. It is also resolved only by a later `ready` marker whose
`supersedes` names the exact flat path. Schema-bearing markers, however, are
grouped and resolved within an `<area>/<loop_id>`, and a ready marker in one
`<area>/<loop_id>` must not resolve a blocked marker from another loop.

The handoff does not say:

- which `<area>/<loop_id>` a superseding ready marker for a flat blocker must
  live in;
- whether such a ready marker's `(issue_id, family)` matters when its job is
  pure exact-path supersession of a non-grouped legacy blocker;
- whether multiple loops can each emit a ready marker pointing at the same flat
  blocker, and how status output reports that.

Suggested resolution: state explicitly that exact-path supersession of a
front-matterless flat legacy marker is loop-id-independent, and that the
superseding ready marker's `linked_report` is the binding redacted evidence
regardless of which loop directory it sits under. Alternatively, define a
synthetic loop bucket such as `phase3-postbuild/_legacy_flat` for these
supersessions.

This is the only finding I would treat as more than a nit. It is not blocking
because the spec already requires `supersedes` to name the exact flat path and
rule 8 fails closed on ambiguity, so safety is preserved; however, an
implementation prompt would otherwise have to invent the policy.

### F2: Report filename inconsistency between RFC sketch and spec

Severity: minor

References: RFC Proposal Sketch report listing and spec Canonical Layout.

The RFC sketch shows reports with state suffixes:
`reports/01_RUN.blocked.md`, `reports/02_REPAIR_PLAN.ready.md`, and
`reports/05_REPAIR_VERIFIED.ready.md`. The spec correctly forbids state
suffixes on reports and uses `reports/01_RUN_REPORT.md`,
`reports/02_REPAIR_PLAN.md`, and `reports/05_REPAIR_VERIFICATION.md`.

The RFC marks the sketch as the original proposal sketch and points readers to
the spec, so this is not a strict contradiction. Still, the sketched filenames
are an active tripping hazard for a later implementer. Consider either
replacing the sketch's report listing with the spec's canonical names, or
adding a one-line note after the sketch's `reports/` block that the spec's
Canonical Layout controls report filename shape.

### F3: Verb inconsistency between report and marker for the verification stage

Severity: minor

References: spec Canonical Layout,
`reports/05_REPAIR_VERIFICATION.md` vs
`markers/05_REPAIR_VERIFIED.ready.md`.

Other report/marker pairs share a stem. The verification pair changes verb
form. Pick one to keep `linked_report` reasoning trivial.
`05_REPAIR_VERIFIED.md` would align with the marker family `repair_verified`
in RFC 0013 marker schema.

### F4: Missing migration audit step for existing flat legacy markers

Severity: minor

References: spec Migration Work steps 1-8; Compatibility Semantics flat legacy
marker rule 5.

Spec rule 5 says a front-matterless flat `.ready.md` does not resolve a
front-matterless flat `.blocked.md`. This is intentional and good because it
prevents silent clearing. It also means that when legacy-root scanning goes
live, any existing flat blocker becomes a hard gate input regardless of whether
an old flat ready marker once "cleared" it.

Migration step 8 talks about retiring legacy-root scanning after the owner
confirms no unresolved blockers remain, but there is no step that performs the
inventory at the start of migration. Add a step between current steps 4 and 5:
inventory all existing flat legacy `.blocked.md` and `.human_checkpoint.md`
markers under `docs/reviews/phase3/postbuild/markers/` and either emit a
schema-bearing ready marker with exact-path `supersedes` and a redacted
resolution report, or record them as intentionally still-blocking with owner
acknowledgment.

### F5: `corpus_content_included` value enumeration not stated for markers

Severity: minor

References: spec Marker Schema and Artifact Rules; RFC 0013 Section 3.

The spec correctly says markers must always set
`corpus_content_included: none`. It does not say what the validator must do if
a legacy schema-bearing marker carries `corpus_content_included:
owner_approved`. Precedence rule 8 covers this implicitly via "privately
contaminated" fail-closed behavior, but spelling it out in the marker schema
section would remove ambiguity for an implementation prompt.

### F6: `supersedes` semantics for non-`ready` markers is unspecified

Severity: minor

References: spec Marker Schema example and Precedence rules rule 5.

If an updated `blocked` or `human_checkpoint` marker wants to point at a prior
blocked marker for the same `(issue_id, family)` to record evolution of the
diagnosis, is `supersedes` the right field, or is it reserved for
ready-to-blocked transitions? State whether a chain of `blocked` markers may
use `supersedes` to thread provenance, or whether such chains should rely only
on `created_at` ordering.

### F7: Spec acceptance criteria duplicates RFC criteria with slight drift

Severity: minor

References: RFC Acceptance Criteria vs spec Acceptance Criteria.

The two lists are almost identical but differ in wording. For example, the RFC
says malformed or invalid marker front matter fails closed, while the spec says
malformed or invalid `created_at` front matter fails closed. The spec is
narrower than the RFC despite the spec Marker Schema requiring parseable front
matter for all fields. Tighten the spec acceptance bullet to "malformed or
invalid marker front matter, including invalid `created_at`, fails closed."

## Cross-Cut Answers To The Review Checklist

- Operational vs review separation in `docs/operations/`: clean. S001 picks
  `docs/operations/`, S005 keeps reviews under `docs/reviews/`, and ignored
  diagnostics remain under `logs/operational/`.
- RFC 0013 marker precedence and redaction survival: yes. S006 keeps front
  matter unchanged; S007 and the precedence rules union new and legacy roots
  with `(issue_id, family)` grouping; redaction routes through RFC 0013 Section
  3 unchanged for prose, and the spec adds a strict marker-only tightening.
- Spec specificity for an implementation prompt: largely sufficient. The
  canonical layout, marker schema, three-root scan list, flat legacy marker
  rules, precedence rules, and implementation fixtures give a downstream agent
  a deterministic target. F1 is the only policy gap.
- Legacy marker compatibility: adequate. The three-root scan, flat legacy
  marker rules, and flat ready audit-only rule preserve historical blockers
  without making legacy paths permanent blockers.
- Private corpus content risk: low. Markers are categorically forbidden from
  carrying private content, and prose stays under RFC 0013 Section 3.
- Bounded target for `agent_runner` validation: yes. S009 and the Agent Runner
  Boundary section keep marker precedence outside the runner's job/transition
  model. The runner can exercise artifact publication, review-only
  parallelism, write-scope enforcement, verdict collection, redacted evidence
  export, and blocked-run introspection without learning marker truth.

## Summary

The package is coherent. The RFC stays in its lane as proposal/history; the
spec carries the implementation contract and resolves all four open questions
explicitly. RFC 0013 redaction, marker schema, and supersession semantics are
preserved, and the spec correctly tightens marker private-content handling
rather than relaxing it. The `agent_runner` boundary is drawn cleanly. The only
non-trivial gap is loop-scope interaction with root-scoped flat legacy
blockers; everything else is tightening or naming consistency.

Verdict: accept_with_findings
