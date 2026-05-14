author: operator [self-declared: alignment-findings-ledger]

# Striatum Memory RFC Alignment Findings Ledger

Status: ledger
Date: 2026-05-14
Run ID: run_169531d5568248ff8f0dfc803d955311
Job ID: job_run_169531d5568248ff8f0dfc803d955311_findings_ledger
Session ID: sess_a56973bfbe7e404783d2c0fe5b43c360
Lease ID: lease_da4f88430fef46bb89a569338cea0467

This ledger normalizes the alignment review outputs under
`docs/reviews/striatum-memory-rfc-alignment-2026-05-14/`. It is a review
artifact only. It does not promote RFCs, authorize implementation, change
runtime behavior, enable default-on memory, edit source artifacts, or record a
Striatum verdict.

## Package Posture

- RFC 0045-RFC 0049 remain proposal/default-off material unless a later
  recorded project decision, accepted spec, or promoted successor says
  otherwise.
- No implementation, migration, generated schema doc, runtime behavior, or
  routine/default-on Striatum memory use is authorized by this package.
- Routine Level 3 automatic memory remains blocked until accepted/promoted
  upstream contracts and the applicable RFC 0049 gates exist and pass.
- Personal-memory reads remain outside default Striatum injection.
- Generated memory products remain blocked from Level 2 and Level 3 injection
  until a separate accepted privacy-inheritance, citation, audit, and gate
  contract exists.

## Cross-Check Notes

- Contract review reports five read-only sub-agent checks; four found no
  blockers and one argued two items were blockers. The contract review carried
  those as major nonblocking findings because the package is proposal-only and
  RFC 0049 still blocks implementation/default-on use.
- Privacy review reports three read-only sub-agent lanes covering unauthorized
  metadata redaction, path/dirty privacy mirroring, and generated/personal
  blockade. Its AP-001..AP-006 findings are nonblocking.
- Operator-ergonomics review reports five read-only checks and one blocker
  (B001). The later repair re-review reports no native sub-agent tool in that
  session, but parallelized read-only checks across the relevant artifacts and
  accepted the repair.
- This ledger also ran mechanical read-only ID checks across the listed input
  artifacts to catch duplicate IDs, stale deferrals, and dependency impacts.

## Active Blockers

None.

The original operator-ergonomics B001 blocker is not active. It is recorded
below as repaired and accepted.

## Accepted Repairs And Closed Findings

| Ledger ID | Source finding | Severity before repair | Affected artifact | Disposition | Evidence | Dependency impact |
|---|---|---:|---|---|---|---|
| AL-R001 | B001 | blocker | RFC 0046 | Repaired and accepted. RFC 0046 now chooses direct copied authorization/provenance columns for retrieval-visible rows and uses joins as consistency checks. | `REPAIR_RFC0046_PROVENANCE.md`; `REVIEW_operator_ergonomics_repair.md`; `OPERATOR_DECISION_ERGONOMICS_REPAIR.md`; `OPERATOR_DECISION_ACCEPT_ERGONOMICS_REPAIR_REVIEW.md` | No longer blocks promotion review or implementation handoff on this point. Enforcement mechanism selection remains deferred to implementation design. |
| AL-R002 | F002 | promotion blocker in prior package | RFC 0046 side of dirty-working-tree projection | Addressed at proposal-text level. Dirty evidence projects only after manifest opt-in and row-level dirty provenance; derived rows copy dirty state. | `ALIGN_RFC0046.md`; confirmed nonblocking by `REVIEW_contract_alignment.md` and `REVIEW_privacy_boundary.md` | Does not authorize implementation. Dirty state still has active retrieval/packet follow-up AL-N005. |
| AL-R003 | F003, F004, F013 | promotion blockers in prior package | RFC 0047 | Addressed at proposal-text level. Unauthorized/no-data/pair-mismatch responses redact inventory metadata; identity labels are display-only; bundle ids are opaque and separate from bundle hashes. | `ALIGN_RFC0047.md`; confirmed nonblocking by `REVIEW_privacy_boundary.md` | Does not authorize implementation. |
| AL-R004 | F008, F010, F011, F016, F022, F012 | promotion blockers or major findings in prior package | RFC 0048 | Addressed at proposal-text level. Manual paste-through, audit privacy inheritance, omission codes, default-on blocking, session-disable transience, and generated-product ineligibility are now stated. | `ALIGN_RFC0048.md`; confirmed nonblocking by `REVIEW_privacy_boundary.md` | Does not authorize runtime packet injection. Generated products remain deferred by AL-D004. |
| AL-R005 | F009, F014, F017 in RFC 0049 scope | promotion blockers or cleanup items in prior package | RFC 0049 | Addressed in RFC 0049 proposal text for no-egress wording, gate status naming, exact-reference coverage, and RFC 0049's stale redaction open-decision wording. | `ALIGN_RFC0049.md`; `REVIEW_contract_alignment.md` | Does not promote RFC 0049. Some companion-RFC cleanup remains active as AL-N007/AL-N008. |
| AL-R006 | Roadmap/index stale scaffolding posture | cleanup | `STRIATUM_MEMORY_ROADMAP.md`; `docs/rfcs/README.md` | Cleaned up to say alignment cleanup, RFC 0044 hardening/EG-000 evidence, and a separate decision/spec handoff come before implementation treats the package as binding. | `ROADMAP_INDEX_CLEANUP.md`; `REVIEW_contract_alignment.md` | Reduces operator confusion. Next promotion packet still needs explicit acceptance status for the alignment handoffs. |

## Nonblocking Promotion And Implementation Findings

These findings are active but are not current blockers for this proposal-only
ledger. They should be addressed before promoting the affected RFC or
implementing the affected surface.

| Ledger ID | Source review | Source ID(s) | Severity | Affected artifact | Required action | Blocks promotion? | Blocks implementation? | Blocks routine Striatum use? | Future personal/generated only? |
|---|---|---|---:|---|---|---|---|---|---|
| AL-N001 | `REVIEW_contract_alignment.md` | contract #1 | major | RFC 0047 request shape | Add generic `{ref_kind, ref_value}` filtering or explicitly mirror the RFC 0045/RFC 0046 exact-reference vocabulary. | Not this package; required before RFC 0047 promotion or exact-lane promotion successor. | Yes, for exact-reference retrieval implementation. | No. Routine Level 3 is already globally blocked. | No. |
| AL-N002 | `REVIEW_contract_alignment.md`; `REVIEW_operator_ergonomics.md` | contract #2; N004 | major | RFC 0047/RFC 0048/RFC 0049 omission and audit continuity | Define `omitted[]` or an equivalent privacy-safe local audit event shape, including candidate ids, lineage, ranks/scores, and closed omission reason vocabulary or extension rules. | Not this package; required before automatic packet promotion. | Yes, for packet builder and audit implementation. | No. Routine Level 3 is already globally blocked. | No. |
| AL-N003 | `REVIEW_contract_alignment.md` | contract #3 | major | RFC 0046 embedding activation/skips | Persist the required embedding profile or activation manifest and add an XOR health/activation rule: exactly one active embedding or active skip per `(generation_id, chunk_id, model, dimension)`. | Not this package; promotion-level invariant for RFC 0046 or successor. | Yes, for projection activation/embedding workers. | No. Routine Level 3 is already globally blocked. | No. |
| AL-N004 | `REVIEW_privacy_boundary.md` | AP-001 | major | RFC 0046/RFC 0047/RFC 0048/RFC 0049 `raw_payload` handling | State that every projection `raw_payload` inherits parent privacy tier, redaction state, and visibility; forbid retrieval-visible `raw_payload` fields above caller authorization; add an EG-060 fixture. | Not this package; required before affected RFC promotion. | Yes, for projection, retrieval, and gate implementations touching `raw_payload`. | No. Routine Level 3 is already globally blocked. | No. |
| AL-N005 | `REVIEW_privacy_boundary.md` | AP-002 | minor | RFC 0047/RFC 0048/RFC 0049 dirty-working-tree retrieval surface | Surface `dirty_working_tree` in retrieval results/citations, add a packet freshness label or equivalent, and add gate coverage for dirty-state rendering and audit reconstruction. | Not this package; should be fixed before affected RFC promotion. | Yes, for packet builder/retrieval surfaces that can present dirty evidence. | No. Routine Level 3 is already globally blocked. | No. |
| AL-N006 | `REVIEW_privacy_boundary.md`; `REVIEW_contract_alignment.md` | AP-003; contract #6 | minor | RFC 0048 audit policy; RFC 0047/RFC 0049 no-egress wording | Restate local-only/no-egress audit storage in RFC 0048 and align RFC 0047's "no HTTP client" wording with RFC 0049's paired-loopback/local-runtime exception. | Not this package; promotion cleanup. | Yes, for audit storage and retrieval transport implementation. | No. Routine Level 3 is already globally blocked. | No. |
| AL-N007 | `REVIEW_contract_alignment.md`; `REVIEW_privacy_boundary.md`; `ROADMAP_INDEX_CLEANUP.md` | contract #4; AP-004; F017 residual | minor/nit | RFC 0046 and RFC 0048 open-decision lists | Remove or restate stale "final redaction-state vocabulary" open-decision text now that RFC 0045 has a closed redaction vocabulary and RFC 0049 cleanup already landed. | Not this package; promotion cleanup. | No immediate implementation blocker if implementers follow the closed vocabulary elsewhere, but cleanup reduces drift. | No. | No. |
| AL-N008 | `REVIEW_contract_alignment.md`; `REVIEW_privacy_boundary.md` | contract #5; AP-005 | minor/nit | RFC 0049 EG-060 | Remove stale wording that `identity_leak` and `citation_leak` are gate-local until RFC 0048 reconciles them, since RFC 0048 now defines the codes. | Not this package; promotion cleanup. | No, unless implementation treats the stale wording as vocabulary authority. | No. | No. |
| AL-N009 | `REVIEW_operator_ergonomics.md`; `REVIEW_contract_alignment.md` | N002; contract deferred F022 | minor | RFC 0049 EG-120 disable controls | Add restart/transient and promotion-record cases before disable controls are considered fully validated. | Not this package; gate promotion cleanup. | Yes, for disable-control gate implementation. | No. Routine Level 3 is already globally blocked. | No. |
| AL-N010 | `REVIEW_operator_ergonomics.md` | N003 | minor | RFC 0047/RFC 0048 render contract | State the response-status to packet-label mapping, especially `ok` to `memory: available`. | Not this package; promotion polish. | Yes, for rendering implementation consistency. | No. | No. |
| AL-N011 | `REVIEW_operator_ergonomics.md`; `REVIEW_contract_alignment.md` | N005; contract #1 related | minor | RFC 0047/RFC 0048 citation rendering | Require workflow/job identifiers in citation rendering where available, matching the exact-reference vocabulary. | Not this package; promotion cleanup. | Yes, for citation renderer implementation. | No. | No. |
| AL-N012 | `REVIEW_operator_ergonomics.md`; `REVIEW_contract_alignment.md` | N006; contract #7 | minor | Roadmap/index promotion packet posture | Make the next promotion packet explicitly accept or reject the alignment handoffs, then move to RFC 0044 hardening/EG-000 evidence; clarify roadmap Phase 7 as gate-spec/evidence before routine use or make the backlog ordering canonical. | Not this package; process cleanup before promotion packet. | No direct implementation blocker, but prevents scaffolding out of order. | No. Routine Level 3 is already globally blocked. | No. |
| AL-N013 | `REVIEW_operator_ergonomics.md` | N007 | minor | RFC 0049 Level 1 manual/raw-only search | Add a concrete Level 1 quality checklist for minimal cited exact/search coverage. | Not this package; before Level 1 promotion/scaffolding. | Yes, for Level 1 gate/scaffold implementation. | No. | No. |
| AL-N014 | `REVIEW_contract_alignment.md` | contract #8 | minor | RFC 0047 authority wording | Replace wording that implies RFC 0045 is already accepted with "proposes" or "accepted successor wins." | Not this package; promotion cleanup. | No, unless implementers treat proposal text as accepted authority. | No. | No. |
| AL-N015 | `REVIEW_privacy_boundary.md` | AP-006 | nit | RFC 0049 EG-030/EG-110 | Add a manual paste-through fixture proving that personal-memory or non-primary results require explicit per-packet opt-in and audit, and fail without it. | Not this package; before Level 1 manual-search promotion if paste-through is in scope. | Yes, for manual paste-through gate coverage. | No. | Yes, personal/non-primary memory paste-through only. |

## Deferred Items

| Ledger ID | Source review | Source ID(s) | Status | Affected area | Required future action | Blocks promotion? | Blocks implementation? | Blocks routine Striatum use? | Future personal/generated only? |
|---|---|---|---|---|---|---|---|---|---|
| AL-D001 | `REVIEW_contract_alignment.md`; `ALIGN_RFC0046.md`; `ROADMAP_INDEX_CLEANUP.md` | F007; EG-000 | deferred prerequisite | RFC 0044 hardening / EG-000 evidence | Produce RFC 0044 Phase 0 hardening or EG-000-equivalent evidence before projection, retrieval, or operator-context implementation depends on the current Striatum substrate. | Yes, before binding promotion/implementation handoff. | Yes, for projection/retrieval/operator-context implementation. | Yes, for routine workflows depending on Striatum memory. | No. |
| AL-D002 | `REVIEW_contract_alignment.md`; `ROADMAP_INDEX_CLEANUP.md` | package posture | deferred decision | RFC 0045-RFC 0048 authority | Record a project decision, accepted spec, or promoted successor before treating proposal RFCs as binding. | Yes, for RFC package promotion. | Yes, for any implementation that treats the contracts as binding. | Yes, for routine/default-on use. | No. |
| AL-D003 | `REVIEW_contract_alignment.md`; `ALIGN_RFC0047.md`; `ALIGN_RFC0048.md`; `ALIGN_RFC0049.md` | Level 3/default-on | deferred gate | Routine automatic memory | Keep Level 3/default-on automatic memory blocked until accepted/promoted upstream contracts and all required RFC 0049 gates pass. | Yes, for routine/default-on promotion. | Yes, for default-on automatic injection implementation. | Yes. | No. |
| AL-D004 | `REVIEW_contract_alignment.md`; `REVIEW_privacy_boundary.md`; `REVIEW_operator_ergonomics.md`; `ALIGN_RFC0048.md`; `ALIGN_RFC0049.md` | F012; D004; EG-140 | deferred contract | Generated memory products | Keep generated products ineligible for Level 2 and Level 3 injection until a separate accepted privacy-inheritance, citation, audit, and gate contract exists. | Yes, for generated-product promotion. | Yes, for generated-product injection implementation. | No for ordinary Striatum raw/source memory; yes for generated-product routine use. | Yes, generated products only. |
| AL-D005 | `REVIEW_contract_alignment.md` | audit storage home | deferred design | Audit storage | Decide whether to extend existing audit storage or add Striatum-specific audit tables with tenant/corpus, generation, selected/omitted candidate, and privacy-tier fields. | No current package blocker. | Yes, before audit implementation. | No. | No. |
| AL-D006 | `REVIEW_operator_ergonomics.md`; `REVIEW_privacy_boundary.md`; `REVIEW_contract_alignment.md` | D001; F019 | deferred UX | Collapsed `no_data` status ergonomics | Revisit packet noise and collapsed no-data status before UX stabilization. | No. | No, unless UX work is in scope. | No. | No. |
| AL-D007 | `REVIEW_operator_ergonomics.md` | D002 | deferred policy | Stale-memory automatic inclusion | Treat stale automatic inclusion as a policy question; mark request examples as illustrative if reused in promotion packets. | No current package blocker. | Yes, before stale automatic inclusion implementation. | Potentially for workflows that include stale evidence automatically. | No. |
| AL-D008 | `REVIEW_operator_ergonomics.md` | D003 | deferred workflow | Gate reports and commands | Define durable gate-report artifact homes and runnable validation command names before workflow scaffolding. | No current package blocker. | Yes, before gate automation implementation. | No. | No. |
| AL-D009 | `REVIEW_operator_ergonomics.md`; `REVIEW_privacy_boundary.md` | D005; F007 dependency | deferred evidence navigation | RFC 0044 hardening references | Add direct links to RFC 0044 findings ledger or hardening packet in roadmap/index follow-up docs. | No current package blocker. | No direct implementation blocker. | No. | No. |
| AL-D010 | `REVIEW_privacy_boundary.md` | F020 | deferred policy | Current-authority conflict warning | Decide whether RFC 0048 must explicitly require both omitted memory and current authority items in conflict warnings; RFC 0049 already carries gate-level coverage. | No current package blocker. | Yes, before conflict-warning packet implementation. | No. | No. |
| AL-D011 | `REVIEW_privacy_boundary.md`; `REVIEW_operator_ergonomics.md` | F022; N002 | deferred gate detail | Session-scope disable persistence | The transient-unless-promoted rule is now stated; add restart/promotion-record gate coverage under AL-N009 before treating disable controls as fully validated. | No current package blocker. | Yes, for disable-control validation. | No. | No. |

## Workflow Friction

| Ledger ID | Source artifact(s) | Observation | Impact |
|---|---|---|---|
| AL-W001 | `REVIEW_privacy_boundary.md` | Run summary reported `doctor ok=false`; no detailed failure was present in the summary. | Operator should confirm workflow-state consistency before publishing verdicts. |
| AL-W002 | `ALIGN_RFC0046.md`; `ALIGN_RFC0047.md`; `ALIGN_RFC0048.md`; `REVIEW_operator_ergonomics.md`; `REVIEW_privacy_boundary.md` | Native sub-agent spawn attempts failed when combining a full-history fork with an explicit explorer role; retries as non-forked/read-only explorers succeeded. | Update workflow prompt patterns to match runner restrictions. |
| AL-W003 | `ALIGN_RFC0047.md`; `ALIGN_RFC0048.md`; `ALIGN_RFC0049.md`; `REVIEW_privacy_boundary.md`; `ROADMAP_INDEX_CLEANUP.md` | Prompt-named upstream inputs were absent under the prompt-local Striatum run path; agents had to read the committed files from `docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/`. | Future prompts should point directly at committed review artifacts. |
| AL-W004 | Multiple handoffs/reviews | Shared worktree contained out-of-scope edits such as `CHANGELOG.md`, `OPERATOR_REPORT.md`, RFC source files, roadmap/index files, and untracked alignment directories. | Ledger worker must not revert or overwrite them; operator should reconcile before publication. |
| AL-W005 | `ALIGN_RFC0047.md`; `ALIGN_RFC0049.md`; `REVIEW_privacy_boundary.md` | The alignment review directory did not exist when early lanes started and had to be created. | Minor setup friction; current ledger reused the requested directory. |
| AL-W006 | `REVIEW_operator_ergonomics.md` | Gemini ergonomics lane exhausted model capacity and produced no artifact; operator authored a recovery ergonomics review. | Provenance should treat `REVIEW_operator_ergonomics.md` as operator recovery output, not Gemini output. |
| AL-W007 | `REVIEW_operator_ergonomics.md`; `ALIGN_RFC0049.md` | Some per-RFC handoffs are stale in isolation because parallel lanes deferred work later handled by companion lanes. | This ledger should be used as the roll-up status for current finding disposition. |

## Validation

- `git diff --no-index --check /dev/null docs/reviews/striatum-memory-rfc-alignment-2026-05-14/FINDINGS_LEDGER.md`
  produced no whitespace or conflict-marker output. Exit code 1 is expected for
  a no-index comparison between `/dev/null` and a present untracked file.
