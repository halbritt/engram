# RFC 0049 Striatum Evaluation Gates SPEC_HANDOFF
author: operator [self-declared: roadmap-rfc-author-f]

Status: author handoff
Date: 2026-05-14
Run id: run_500d0f049ea04038b0e19d6045daf918
Workflow job id: rfc0049_evaluation_gates_handoff
Job id: job_run_500d0f049ea04038b0e19d6045daf918_rfc0049_evaluation_gates_handoff
Session id: sess_0cbf865ffdc34d4e86929f1f61a9b69b
Lease id: lease_1c81b4e932524306a7b30ace56e29f13

## Purpose

Move RFC 0049 from scaffold to a reviewable evaluation, no-egress, and
retrieval-quality gate handoff for Striatum memory.

The handoff preserves Engram's local-first boundary: no cloud dependency, no
telemetry, no hosted persistence, and no user data leaving the machine unless
explicitly requested.

## Changed Files

- `docs/rfcs/0049-striatum-evaluation-gates.md`
- `docs/reviews/rfc0049-striatum-evaluation-gates/SPEC_HANDOFF.md`

## Summary Of RFC Changes

- Replaced the scaffold with a reviewable gate contract.
- Added promotion levels for manual/local operator search, experimental
  automatic injection, and routine default-on automatic injection.
- Defined gate IDs EG-000 through EG-130.
- Added explicit gates for V2 fixtures, validator checks, no-egress evidence,
  tenant/corpus isolation, personal-memory denial, `fetch_reference`
  reauthorization, malformed/uncited/redacted fixtures, stale-index behavior,
  retrieval quality, latency, prompt-injection containment, audit
  reconstruction, disable controls, and Striatum-without-Engram compatibility.
- Named RFC 0045, RFC 0046, RFC 0047, and RFC 0048 as upstream proposal
  dependencies with open decisions rather than treating them as accepted.
- Stated that manual/local search may ship earlier only when explicit, local,
  read-only, cited, scope-limited, and non-injecting.
- Stated that routine default-on automatic injection is blocked until the full
  automatic gate set passes and context-injection policy is accepted.

## Validation Evidence

Passed:

```sh
git diff --check -- docs/rfcs/0049-striatum-evaluation-gates.md docs/reviews/rfc0049-striatum-evaluation-gates/SPEC_HANDOFF.md
```

No code, migration, generated schema doc, test, decision-log, changelog,
operator-report, or `.striatum/` file was intentionally changed by this handoff.

## Deferred Questions

- Which exact V2 fixture bundle becomes the committed review seed after
  RFC 0045 acceptance?
- Which `corpus_id` grammar and instance/repository identity rules are accepted
  upstream?
- Which RFC 0046 projection generation and health-check schema is accepted?
- Whether vector retrieval is required for routine default-on automatic
  injection or remains additive after exact, structured, and lexical gates pass.
- Whether initial retrieval-quality thresholds need separate values for small
  fixtures and large real local corpora.
- Which hardware profile becomes the latency reference profile.
- Exact Striatum CLI/UI names for run, session, packet, purpose, and manual
  disable controls.
- Whether stale memory is default-eligible for `operator_startup` or only for
  `review_prepare` and `blocker_recovery`.
- Whether generated memory products require a separate audit RFC before they
  can enter automatic injection.

## Review Recommendations

- Review RFC 0049 as a package with RFC 0045, RFC 0046, RFC 0047, RFC 0048,
  the RFC 0044 final synthesis, and the RFC 0044 findings ledger.
- Treat as blockers any gap that permits personal memory by default,
  cross-corpus leakage, cross-tenant leakage, uncited injection, stale lower-tier
  retrieval, hidden hosted dependency, network egress from a corpus-reading
  path, workflow dependence on Engram, or default-on automatic injection without
  visible disable controls.
- Add an operator ergonomics review lane. The gate text intentionally separates
  manual search from automatic injection, but the usability and noise threshold
  still needs review pressure.
- Do not implement from RFC 0049 until review has either accepted it or promoted
  a successor spec.
