# Focused Review Ledger

author: operator [self-declared: rfc0028-focused-ledger-recovery]

Status: ledger
Date: 2026-05-14
Workflow: `rerun-backlog-focused-reviews-2026-05-13`
Run: `run_6d6d3c3ce51f4b4286bfefad6d4ed09e`

## Boundary Statement

This ledger normalizes focused review outputs only. Accepting or recording
these reviews is not promotion, does not accept RFC 0021, RFC 0027, RFC 0028,
RFC 0029, or RFC 0024, does not authorize Phase 4 full-corpus execution, and
does not resolve findings by itself.

Findings remain open until resolved by implementation, revised RFC/spec text,
fresh review, or an explicit operator decision. Supplemental re-review evidence
is recorded as evidence only; it is not decision authority.

## Inputs Normalized

| Area | Artifact | Verdict Recorded In Artifact | Ledger Disposition |
|---|---|---:|---|
| RFC 0028 prompt provenance and subject-kind warning | `RFC0028_FOCUSED_REVIEW.md` | `needs_revision` | Initial finding recorded; later narrow re-review evidence accepted the prompt-literal repair, but D082 remains proposed and RFC 0028 is not promoted. |
| RFC 0027 interview web UI focused review | `RFC0027_FOCUSED_REVIEW.md` | `accept_with_findings` | Focused blockers mostly resolved with a minor residual; later recovery/re-review evidence is recorded separately below. |
| RFC 0021 gold-set contract re-review | `RFC0021_CONTRACT_RE_REVIEW.md` | `accept_with_findings` | B007 blockers resolved in RFC text; one medium contract mismatch and several nits remain carried. |
| RFC 0029 bench triage workbench design re-review | `RFC0029_DESIGN_RE_REVIEW.md` | `accept` | Focused design blockers resolved; this is design-review evidence only, not spec or implementation acceptance. |
| Phase 4 evidence-fix scaffold focused review | `FOCUSED_SCAFFOLD_REVIEW.md` | `accept_with_findings` | Scaffold accepted as non-promoting bounded evidence plan; Tier 2 and evidence provenance blockers remain carried. |

Supplemental evidence consulted for reconciliation:

| Area | Artifact | Verdict Recorded In Artifact | Ledger Use |
|---|---|---:|---|
| RFC 0028 prompt literal repair | `RFC0028_PROMPT_LITERAL_RE_REVIEW.md` | `accept` | Confirms the original RFC 0028 F001 line-level prompt-literal finding was repaired. Does not promote RFC 0028 or accept D082. |
| RFC 0027 recovery review | `RFC0027_FOCUSED_REVIEW_RECOVERY.md` | `needs_revision` | Records five additional web/privacy/session-state findings. |
| RFC 0027 web-state re-review | `RFC0027_WEB_STATE_RE_REVIEW.md` | `accepted` | Confirms RFC 0027 recovery findings F001-F005 were resolved. Does not clear unrelated Striatum process-adapter state debt by itself. |

## Normalized Findings

### RFC 0028

Findings:

- `RFC0028-F001`: the governed v9 prompt artifact originally recorded Python
  f-string escaped double braces for the zero-claim JSON literal rather than
  the rendered runtime literal. Severity in source review: major.

Clean checks:

- Prompt artifact/provenance shape exists for
  `extractor.v9.d082.predicate-intent`.
- The subject-kind warning false-positive path for mixed person/non-person
  active entities is resolved and has deterministic test coverage.
- Supplemental prompt-literal re-review confirms the governed artifact now
  records `{"claims":[]}` and focused tests pin both artifact and runtime
  rendering.

Carried blockers and questions:

- D082 remains only a proposed prompt-version reservation. This ledger does
  not accept D082, does not promote RFC 0028, and does not authorize
  non-scratch extraction writes under `extractor.v9.d082.predicate-intent`
  without a separate accepted decision binding or explicit operator decision.

### RFC 0027

Findings from the original focused review:

- The original focused review carried one non-blocking residual: web
  `GET /sessions/{id}` used its own unanswered-target query and silently
  redirected targetless pre-011 sessions instead of surfacing the same explicit
  diagnostic as the CLI.

Supplemental recovery findings:

- `RFC0027-RF001`: `/evidence/all` bypassed the parent-target Tier 1 ceiling.
- `RFC0027-RF002`: completed or abandoned sessions could still be resumed and
  mutated.
- `RFC0027-RF003`: final completion was based on URL position rather than
  remaining frozen targets.
- `RFC0027-RF004`: web progress counts ignored the frozen target/version
  predicate.
- `RFC0027-RF005`: targetless open sessions remained stranded in the web path.

Clean checks:

- The original focused review found the normal question-page Tier 1 ceiling,
  mutating-GET removal, Origin / Sec-Fetch contract, evidence-scoped
  reachability, frozen target version triple handling, migration 011/013
  baseline, and D020 no-egress documentation aligned within scope.
- Supplemental web-state re-review records RFC0027-RF001 through RFC0027-RF005
  as resolved.

Carried blockers and questions:

- No product-contract blocker remains in the focused RFC 0027 evidence set
  reviewed here.
- Striatum issue `#7` remains process-adapter state debt: the accepted
  web-state re-review evidence exists, but the completed-job process blocker
  remains visible until tooling reconciliation. This is not resolved by the
  ledger.

### RFC 0021

Resolved checks:

- Synthetic-audit SQL trigger language was revised to be truthful: v1 does not
  claim a fictional trigger and relies on code-path discipline.
- Candidate-pool replay claims were scoped down to materialized selected-order
  targets; `candidate_pool_snapshot_id` is an opaque session-instance tag.
- Belief version-stamp language now distinguishes claim-side derivation stamps
  from belief-side interview metadata.
- Strata validation is explicitly deferred as a SQL guarantee.
- Status/stale wording and migration baseline text are mostly aligned with the
  current schema and implementation.

Carried findings:

- `RFC0021-F001`: rendered evidence excerpts are not persisted by current CLI
  or web verdict commits even though RFC text still describes storing rendered
  one-line excerpts in `gold_labels.evidence_excerpt`. Severity in source
  review: medium.

Carried nits:

- The sampler module docstring still suggests the candidate-pool UUID anchors
  replay.
- The RFC interval-question wording for closed beliefs is more precise than
  the current renderer behavior under `--include-superseded`.
- Migration 010's file header mentions four named triggers while the executable
  migration implements three trigger families.

Open question:

- Decide whether to revise RFC 0021 to make `evidence_excerpt` optional and
  currently unpopulated by CLI/web paths, or pass a bounded rendered excerpt
  through both commit paths and update tests.

### RFC 0029

Clean checks:

- Prior-run artifact mode is persistable and fail-closed on slice/order
  mismatch.
- `queue_fingerprint` is defined over canonical queue-affecting inputs and
  gates `serve`, `status`, and `export`.
- Export redaction handles operator-provided identifiers as hostile and avoids
  leaking paths, backend names, filenames, reviewer labels, and usernames.
- Read-only DB enforcement includes a dedicated role plus transaction-level
  read-only behavior, with provisioning command shape specified.
- Follow-up, regression, excluded-blocker, and accepted queues are explicit.
- Promotion language has been replaced with scratch-local recommendation
  states.
- Exclusion semantics distinguish unchanged/no-risk rows from blocking
  out-of-scope rows that require rationale and remain visible.

Carried blockers and questions:

- None from the focused design re-review. This does not accept an RFC 0029 spec
  or implementation; those remain downstream of their own review gates.

### Phase 4 Evidence-Fix Scaffold

Clean checks:

- The scaffold is explicitly non-promoting and does not authorize Phase 4
  full-corpus execution.
- Privacy and redaction boundaries are preserved: committed outputs are limited
  to aggregates, command shapes, timing summaries, schema relation names,
  redacted identifiers, and finding ids.
- Tier 0, Tier 1, and Tier 2 are bounded; forbidden unbounded command shapes
  are named.
- Prior Phase 4 gate findings are carried forward rather than laundered into
  permission.

Carried findings:

- `P4-SCAFFOLD-F001`: Tier 2 eligibility must gate on explicit owner decisions
  or landed implementation changes for P4-GATE-L008 and P4-GATE-L010 before
  any `--limit 500` production entity/edge write. Severity in source review:
  major.
- `P4-SCAFFOLD-F002`: single-lane Tier evidence would reopen P4-GATE-L016 for
  the loop's products; Tier evidence reports need multi-lane production or an
  explicit operator deviation before later reliance. Severity in source review:
  major.
- `P4-SCAFFOLD-F003`: `make install` or Python toolchain failures should be
  classified as `environment_unavailable` and map to `blocked`, not Phase 4
  findings. Severity in source review: medium.
- `P4-SCAFFOLD-F004`: Tier 1 eligibility ordering should be explicit: RFC 0021
  slice and review-action evidence should run only after Tier 0 passes or is
  classified unrelated. Severity in source review: medium.
- `P4-SCAFFOLD-F005`: the RFC 0021 `candidate_pool_snapshot_id` caveat should
  be carried into slice-construction notes; capture seeds, strata weights, and
  session ids rather than relying on snapshot replay. Severity in source
  review: medium.

Open question:

- Before any bounded Tier 2 preflight, decide how P4-GATE-L008 source-belief
  status propagation and P4-GATE-L010 reuse provenance should be handled:
  owner-accepted current behavior, code/spec change, or human checkpoint.

## Backlog Mapping

| Backlog Item | Ledger State |
|---|---|
| B001 - RFC 0028 prompt provenance | Original focused blocker repaired by supplemental accepted re-review; D082/RFC 0028 promotion remains unresolved. |
| B002 - RFC 0028 subject-kind warning | Resolved in focused review evidence. |
| B003 - RFC 0027 question-page Tier ceiling | Resolved in original focused review and supplemental web-state re-review, including `evidence/all` parent-tier coverage. |
| B004 - RFC 0027 mutation and CSRF contract | Resolved in focused/re-review evidence for the reviewed scope. |
| B005 - RFC 0027 evidence-scoped reachability | Resolved in focused review evidence. |
| B006 - RFC 0027 frozen target resume | Resolved in focused/re-review evidence for version predicates, completion, progress, and targetless sessions. |
| B007 - RFC 0021 contract truthfulness | Accepted with findings; evidence excerpt persistence mismatch remains. |
| B008 - RFC 0029 design revision | Accepted in focused design re-review. |
| B009 - Phase 4 evidence-fix scaffold | Accepted with findings; Tier 2/status-provenance and multi-lane evidence constraints remain. |
| B011 - Focused re-review queue | This ledger records the queue outputs; it does not promote any upstream artifact. |

## Promotion And Execution Status

- RFC 0021: not accepted or promoted by this ledger. D079 remains historical
  project context; current focused re-review evidence is `accept_with_findings`
  and carries the evidence-excerpt mismatch.
- RFC 0027: not accepted or promoted by this ledger. Focused web/privacy and
  session-state findings are recorded as resolved by re-review evidence, with
  Striatum state reconciliation still separate.
- RFC 0028: not accepted or promoted by this ledger. D082 remains proposed.
- RFC 0029: not accepted or promoted by this ledger. Design-focused evidence
  is accepted; spec/implementation gates remain separate.
- Phase 4: full-corpus Phase 4 execution remains blocked. The evidence-fix
  scaffold is accepted only as a bounded, privacy-preserving plan with carried
  findings.

## Verification Notes

No source artifacts, migrations, tests, RFCs, specs, CHANGELOG, DECISION_LOG,
OPERATOR_REPORT, or schema docs were edited for this ledger. No network access
was used. This artifact is a curated ledger only; transcripts are not
published.
