# RFC 0014 Review

Author: reviewer / codex / Codex GPT-5.5 / review_codex

No blocking findings.

## Findings

### Medium: Dual-root marker precedence is underspecified for migration

References: `RFC 0014 / Migration Plan If Accepted`, `RFC 0014 / Acceptance Criteria`,
`RFC 0013 / Marker schema and precedence`

RFC 0014 requires scripts to read both `docs/operations/.../markers/` and legacy
`docs/reviews/phase3/postbuild/markers/`, while preserving RFC 0013 precedence.
The RFC does not yet specify how automation should merge markers when the same
`issue_id` and `family` exist in both roots.

The risky cases are:

- a new `ready` marker under `docs/operations/` superseding a legacy `blocked`
  marker;
- a newer legacy `blocked` or `human_checkpoint` marker still blocking after
  operations-root markers exist;
- path validation for `supersedes:` when it references a legacy marker path;
- tie-breaking if filenames and front-matter timestamps disagree.

RFC 0013's rule is strict: a `ready` marker resolves a prior `blocked` marker
only when it shares `issue_id` and `family` and explicitly names the older
marker in `supersedes`. RFC 0014 should carry that rule into a concrete
dual-root algorithm so the later `scripts/phase3_tmux_agents.sh` migration is
not left to interpretation.

Proposed fix: add a short "Compatibility Semantics" subsection saying scripts
must treat new and legacy marker roots as one logical marker set, group by
`issue_id` and `family`, honor `supersedes` across both repo-relative roots,
and let any newest unsuperseded `blocked` or `human_checkpoint` block expansion.

### Medium: Migration plan does not define report-path compatibility

References: `RFC 0014 / Proposal`, `RFC 0014 / Migration Plan If Accepted`,
`RFC 0013 / Required artifacts`

RFC 0014 explicitly calls out marker compatibility, but not operational report
compatibility. RFC 0013 requires redacted run reports as part of the loop, and
markers include `linked_report`. If historical reports remain under
`docs/reviews/<area>/` while new reports move under
`docs/operations/<area>/<loop_id>/reports/`, scripts and reviewers may need to
resolve both locations.

This is lower risk than marker precedence because reports do not directly gate
expansion, but it matters for auditability and runner validation. A later
implementation prompt should know whether `linked_report` may point to legacy
`docs/reviews/...` paths indefinitely and whether report discovery should search
both roots.

Proposed fix: add one migration bullet stating that `linked_report` may
reference either legacy review-root reports or new operations-root reports, and
that scripts validating markers should accept both repo-relative forms during
transition.

### Low: Runner validation target is useful but acceptance criteria could be more testable

References: `RFC 0014 / Acceptance Criteria`, task prompt check for bounded
`agent_runner` validation

RFC 0014 is a good bounded target for `agent_runner`: it has a small artifact
surface, clear upstream dependency on RFC 0013, and concrete script/runbook
migration implications. The current acceptance criteria, however, are mostly
review judgments rather than executable checks.

For runner usefulness, the RFC would be stronger if it named validation examples
a later implementation can assert, such as:

- fixture with legacy `blocked` plus new superseding `ready`;
- fixture with new `ready` plus newer legacy `blocked`;
- fixture rejecting a marker that contains forbidden private-content fields or
  absolute home paths;
- status output showing the blocking marker before older ready markers.

Proposed fix: add a "Validation Fixtures" or "Implementation Checks" subsection.
This would make the RFC a cleaner target for validating whether `agent_runner`
can turn reviewed process text into concrete code/test changes.

## Notes

The proposed `docs/operations/` root cleanly separates committed operational run
state from model review feedback while keeping review artifacts under
`docs/reviews/`, which matches the multi-agent review loop storage rule.

RFC 0014 preserves the local-first and redaction posture from RFC 0013. It
explicitly keeps private diagnostics under ignored `logs/operational/` paths and
does not authorize raw corpus content in committed operational artifacts.

Legacy marker provenance is directionally correct: old markers are not deleted
or moved without owner approval. The main remaining risk is implementation
ambiguity while both roots coexist.

Verdict: accept_with_findings
