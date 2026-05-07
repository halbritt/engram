<a id="review-0028"></a>
# RFC 0014 Findings Ledger

Review ID: REVIEW-0028
Status: findings
Date: 2026-05-06
RFC refs:
  - RFC-0013
  - RFC-0014
Decision refs:
  - D060
Phase refs:
  - none

Status: recorded; spec handoff created
Date: 2026-05-06
Target: `docs/rfcs/0014-operational-artifact-home.md`
Run ID: `run_2970e12484aa4320a85084cb45e6e880`

This ledger normalizes findings from the independent RFC 0014 review artifacts.
It preserves source severities and affected sections; it does not decide final
disposition.

## Source Artifacts

- `docs/reviews/rfc-0014-operational-artifact-home/RFC_0014_REVIEW_claude.md`
- `docs/reviews/rfc-0014-operational-artifact-home/RFC_0014_REVIEW_codex.md`
- `docs/reviews/rfc-0014-operational-artifact-home/RFC_0014_REVIEW_gemini.md`

## Findings

| ID | Normalized finding | Max severity | Source reviewers | Affected sections | Concise rationale |
| --- | --- | --- | --- | --- | --- |
| RFC0014-F001 | Cross-root marker precedence is underspecified during the transition from `docs/reviews/.../postbuild/markers/` to `docs/operations/.../markers/`. | High | Claude F1; Codex 1; Gemini 1 | RFC 0014 Migration Plan steps 3-4; RFC 0014 Acceptance Criteria; RFC 0013 marker schema and precedence | RFC 0013 depends on newest marker state per `issue_id` and `family`, with explicit `supersedes` semantics. RFC 0014 says scripts must read both roots but does not define whether precedence is computed across the union, whether cross-root `supersedes` is valid, or how blocked and ready markers interact across roots. |
| RFC0014-F002 | Script migration obligations are not specific enough for an implementation prompt. | High | Claude F2; Codex 1, 3, 4; Gemini 1 | RFC 0014 Migration Plan step 3; RFC 0013 script/runbook responsibilities | Updating `scripts/phase3_tmux_agents.sh` requires more than reading a new root. The implementation prompt needs explicit dual-root discovery, status surfacing, `next` refusal behavior, historical marker preservation, and marker-front-matter compatibility. |
| RFC0014-F003 | RFC 0013 marker front matter and owner-approved private-content metadata are only implied, not explicitly preserved. | Medium | Claude F3; Codex 4 | RFC 0014 Artifact Rules; RFC 0013 redaction rules; RFC 0013 marker front matter | RFC 0014 inherits redaction rules but does not restate that marker front matter remains unchanged, including `gate`, `linked_report`, `supersedes`, and `corpus_content_included`. The owner-approved tracked-artifact exception remains mentioned in prose but lacks the RFC 0013 field contract. |
| RFC0014-F004 | `reports/` versus `markers/` remains unresolved even though the proposed tree shows both. | Medium | Claude F4; Gemini 2 | RFC 0014 Proposal layout; RFC 0014 Open Questions | Implementation cannot safely proceed while the RFC still asks whether reports and markers are separate or consolidated. The choice affects write paths, artifact validation, marker redaction surface, and script discovery. |
| RFC0014-F005 | The operation-root naming question leaves `docs/operational/` as a confusing candidate beside `logs/operational/`. | Medium | Claude F5 | RFC 0014 Open Questions | The RFC is meant to clarify committed operational artifacts versus untracked diagnostics. Keeping `docs/operational/` as an option risks confusion with the existing ignored `logs/operational/` diagnostics path. |
| RFC0014-F006 | Phase-scoped versus process-scoped path mapping is unresolved. | Medium | Claude F6; Codex 3 | RFC 0014 Proposal path example; RFC 0014 Open Questions | RFC 0014 proposes `docs/operations/phase3-postbuild/<loop_id>/` but still asks whether the shape should be `postbuild/phase3`. A later script migration needs a deterministic legacy-to-new mapping. |
| RFC0014-F007 | Per-loop `README.md` is shown in the canonical tree but has no required content contract. | Low | Claude F7 | RFC 0014 Proposal layout; RFC 0014 Open Questions | If every operational loop has a `README.md`, the RFC should state whether scripts rely on it and what redacted content it may contain. If not, it should be removed from the canonical layout. |
| RFC0014-F008 | The D060 path-hygiene acceptance criterion is opaque without a local summary. | Low | Claude F8 | RFC 0014 Acceptance Criteria | The RFC gates acceptance on D060 but does not summarize its requirement: use generalized paths and avoid hardcoded home-directory paths or machine-specific PII. |
| RFC0014-F009 | The example review artifact path appears to use `RFC_0013` where `RFC_0014` is intended. | Low | Codex 5 | RFC 0014 Proposal review-artifact example | The target artifact is RFC 0014, but the example path names `RFC_0013_OPERATIONAL_ARTIFACT_HOME_REVIEW...`, which can confuse review artifact naming and runner artifact validation. |
| RFC0014-F010 | The RFC should clarify the `agent_runner` boundary if it is used as a runner validation fixture. | High | Codex 2 | RFC 0014 Goals; agent_runner SPEC Product Boundary | `agent_runner` treats SQLite under `.agent_runner/state.sqlite3` as live control-plane state and repository artifacts as durable provenance. RFC 0014 can remain marker/script-focused for Engram, but should not imply that committed markers are runner queue truth. |

## Source Verdicts

- Claude: `accept_with_findings`
- Codex: `needs_revision`
- Gemini: `accept_with_findings`

## Spec Handoff

Coordinator follow-up on 2026-05-06 converted the unresolved RFC 0014 proposal
choices into `docs/process/operational-artifact-home-spec.md`. The ledger still
does not decide final disposition. The spec handoff gives RFC0014-F001 through
RFC0014-F010 an explicit implementation target for review and owner decision.

## Notes

- RFC0014-F001 is the only finding raised by all three reviewers.
- RFC0014-F001, RFC0014-F002, RFC0014-F003, RFC0014-F004, and RFC0014-F006
  are tightly related and should be handled together in any RFC revision.
- Gemini suggested "global timestamp sort across both roots" as an example
  precedence strategy. The ledger records the underlying ambiguity but does not
  endorse that strategy; RFC 0013's `issue_id` / `family` / `supersedes`
  semantics are the controlling context.
