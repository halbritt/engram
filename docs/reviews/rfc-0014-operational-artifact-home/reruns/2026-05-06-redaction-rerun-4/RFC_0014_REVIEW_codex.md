# RFC 0014 Handoff Package Review

author: reviewer-codex-gpt-5.5-001

## Findings

No blocking findings.

### F1: Human-checkpoint owner-decision evidence is not fully machine-checkable

Severity: medium

References:

- `docs/process/operational-artifact-home-spec.md`, Compatibility Semantics,
  precedence rule 6
- `docs/process/operational-artifact-home-spec.md`, Implementation Fixtures
- `docs/process/operational-artifact-home-spec.md`, Acceptance Criteria

The spec correctly preserves the stricter rule that a `human_checkpoint`
remains blocking until exact-path supersession plus linked owner-decision
evidence. The unresolved part is how an implementation validates that
evidence.

Right now the contract says the linked redacted report must record the owner
decision, but it does not define whether tooling should check only that
`linked_report` exists, parse report front matter, scan prose, require a
distinct owner-decision path, or surface this as manual verification. That
leaves a later implementation prompt to infer a policy choice in one of the
most sensitive gate paths.

Proposed fix: add a deterministic validation rule. For example, require a
ready marker that supersedes a `human_checkpoint` to include a
repository-relative linked report that exists and carries a small
machine-readable field such as `owner_decision: recorded` or
`owner_decision_evidence: <repo-relative-path>`. If the intent is manual
validation only, say that explicitly and require tooling to keep the gate
blocked until a human marks the checkpoint resolved.

### F2: D060 path hygiene is weaker in prose than in the fixture and acceptance criteria

Severity: medium-low

References:

- `docs/process/operational-artifact-home-spec.md`, Artifact Rules
- `docs/process/operational-artifact-home-spec.md`, Implementation Fixtures
- `docs/process/operational-artifact-home-spec.md`, Acceptance Criteria

The spec says tracked documentation and artifacts "should" use
repository-relative paths, environment variables, or generalized `~/` paths.
Later sections say a hardcoded home-directory path is rejected by validation
and that D060 path hygiene remains enforced.

That is directionally correct, but the implementation contract should use one
enforcement level. As written, an implementer could reasonably treat path
hygiene as advisory for reports but mandatory for markers, or mandatory
everywhere.

Proposed fix: replace the Artifact Rules sentence with a `must` rule and state
the validation boundary explicitly. For markers, hardcoded home-directory
absolute paths should fail closed. For prose reports, either require rejection
as well or define them as review findings that must be corrected before
publication.

### F3: `created_at` ordering should require timezone-aware timestamps

Severity: low

References:

- `docs/process/operational-artifact-home-spec.md`, Marker Schema
- `docs/process/operational-artifact-home-spec.md`, Compatibility Semantics,
  precedence rules 3 and 4

The spec requires valid ISO-8601 timestamps and uses `created_at` for
cross-root marker precedence. ISO-8601 can include naive local timestamps,
which are ambiguous once markers are produced by multiple tools or agents.

Proposed fix: require RFC 3339 / ISO-8601 timestamps with an explicit offset or
`Z`, and make naive timestamps fail closed as malformed marker front matter.

## Non-Blocking Assessment

The package cleanly separates committed operational run state from model review
feedback. `docs/operations/` owns redacted reports and markers, while
`docs/reviews/` remains the home for review, synthesis, and final review
artifacts. That aligns with the multi-agent review loop storage rule.

RFC 0013 marker semantics mostly survive the move. The spec preserves front
matter, exact-path `supersedes`, cross-root compatibility, old-marker
provenance, and fail-closed behavior for malformed schema-bearing markers. The
flat legacy marker handling is explicit enough to prevent old blocked and
human-checkpoint files from being silently cleared.

The private-content posture is materially improved for markers. The absolute
`corpus_content_included: none` requirement avoids letting owner approval turn
machine-readable gate files into private-content carriers. Reports still
inherit RFC 0013's owner-approved exception, but that is a preserved upstream
rule rather than a new contradiction.

The `agent_runner` boundary is good. The spec makes RFC 0014 a validation
fixture for artifact publication, review collection, write-scope discipline,
and blocked-run introspection without making repository markers the runner's
queue truth.

## Verdict Rationale

This is a good bounded target for `agent_runner` validation. The remaining
issues are contract-tightening items, not architectural blockers. The main
revision needed before implementation is to make human-checkpoint resolution
and path-hygiene validation deterministic enough that a worker does not have
to invent policy during coding.

Verdict: accept_with_findings
