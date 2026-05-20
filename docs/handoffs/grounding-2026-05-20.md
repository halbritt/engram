# Grounding Stack — Handoff 2026-05-20

This file hands off grounding-stack work to a fresh agent context. Read it
front to back. If a section says "see X", follow it; do not reconstruct
those documents from the working tree.

## Status Snapshot

The RFC 0051–0055 grounding stack is implemented on master. A 2026-05-20
bounded end-to-end pass (5 grants → Tavily → 25 evidence rows) revealed a
**0% identity-resolution rate** against 281 active `unknown` Phase 4
entities. A multi-model architectural review concluded the primitives are
correct but the operational shape is broken: per-grant operator approval
is the bottleneck, evidence count is being confused with resolution, the
byte-exact RFC 0053 query rule structurally requires a local adjudication
stage that does not yet exist, and there is no eval baseline.

An operator interview locked in a 3-month plan and a set of policy
defaults. One small boundary-hardening change (closing the
`process-approved` operator-DSN fallback) landed in this session. No new
RFCs are written yet beyond the revised RFC 0056.

## Decisions Locked In (2026-05-20 Interview)

Authoritative source:
`docs/reviews/grounding-stack-architectural-review-2026-05-20/SYNTHESIS.md`
§ "Resolved After Operator Interview 2026-05-20".

| ID | Topic | Decision |
|----|-------|----------|
| D1 | Plan sequencing | As written: M1 eval + boundary harden + RFC 0057 design → M2 RFC 0056 land + batch review + Phase 4 schema → M3 adjudicator + replay fixtures + re-grounding. |
| D2 | RFC 0057 timing | Open now (M1 design slot); land M3. |
| D3 | `process-approved` fallback | **Closed.** `entity-grounding process-approved` refuses without `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL`. |
| Q1+Q7 | Triage feedback loop | Moderate defaults: `false_suppression_budget=5%` (target `recall(groundable)>=0.95`); `weekly_audit_sample=5%`; `tier3_audit_sample=100%`. Revisit after M1.1. |
| Q2 | Tier 1 auto-approval scope | Per-corpus policy file. Default **off** until enabled per `(tenant_id, corpus_id)`. |
| Q3 | Auto-resolve threshold | High threshold, per-corpus override. Defaults: 3 concurring candidates, 2 supporting claims, resolver confidence ≥ 0.9. |
| Q4 | Revocation propagation | Deferred to RFC 0057. |
| Q5 | Personal/local-only entities | Deferred to RFC 0057 (lead question for that RFC). |
| Q6 | Review queue shape | Hybrid: keep per-stage CLIs; add a top-level `engram review` aggregator. |

## What Just Landed (This Session)

Working tree (uncommitted at handoff write time, committed in the same
commit as this file):

- `src/engram/cli.py` — `process-approved` refuses without the broker DSN
  env var (D3).
- `tests/test_cli.py` — fixed redacts-secrets test to set the env var;
  added `test_entity_grounding_process_approved_refuses_without_broker_database_url`.
- `CHANGELOG.md` — entry under `### Fixed` for the D3 closure.
- `docs/rfcs/0056-entity-grounding-pre-dispatch-triage.md` — full
  revision of the pre-dispatch triage RFC after a 3-model adversarial
  review. All 14 accepted deltas applied.
- `docs/reviews/rfc0056-pre-dispatch-triage-design-review/` — 3 reviews
  (Codex GPT-5.5, Gemini, local Qwen 3.6 35B) + SYNTHESIS.
- `docs/reviews/grounding-stack-architectural-review-2026-05-20/` —
  3 reviews (same lineup) + SYNTHESIS with the interview-resolved
  decision table.

Tests in scope (`make test` not run in full; targeted slice passes):

- `tests/test_cli.py` `-k entity_grounding` → 6 passed.
- `tests/test_claim_grounding_network.py` → 21 passed (regression for the
  off-by-three excerpt-trim bug fixed earlier in the session).

## 3-Month Plan

Authoritative source:
`docs/reviews/grounding-stack-architectural-review-2026-05-20/SYNTHESIS.md`
§ "Synthesized 3-Month Plan".

```
Month 1 (Visibility + Boundary)
  M1.1  Eval baseline      — label 50 unknowns + per-stage telemetry
  M1.2  Boundary hardening — ✅ D3 partial; remaining: invariant tests,
                              role isolation, broker-daemon scope tests
  M1.3  Phase 4 design     — candidate features RFC (proposal)

Month 2 (Triage + Batch)
  M2.1  RFC 0056 land      — rules-first + LLM tie-breaker + sampled audit
  M2.2  Batch + tier policy — `engram review` aggregator + tier 0/1/2/3
  M2.3  Phase 4 implement  — schema + migration + backfill

Month 3 (Adjudication)
  M3.1  RFC 0057 land      — local identity adjudication stage
  M3.2  Replay fixtures    — provider-neutral candidate fields
  M3.3  Re-grounding trig  — re-adjudicate on new local context
```

## Immediate Next Actions

In dependency order. A fresh agent picking this up should start at #1
unless the operator directs otherwise.

1. **Draft RFC 0057 (local identity adjudication).** This is the M1.3
   parallel design RFC and the structural piece the byte-exact rule
   requires. Anchor questions to carry into the RFC: Q3 default policy
   shape, Q4 revocation propagation, Q5 personal/local-only entity
   workflow. Run a 3-model design review on the draft before any
   implementation (same pattern as RFC 0056 review).
2. **Land M1.1 eval baseline.** Label 50 representative entities from
   `entities WHERE entity_kind='unknown' AND status='active'` into the
   8-category taxonomy (see SYNTHESIS § "Recommendation 1"). Build the
   per-stage telemetry harness so resolution rate, false-suppression
   rate, and operator-actions-per-resolved-entity can be tracked over
   time. Surface as `evals/grounding/baseline-2026-05.md`.
3. **Finish M1.2 boundary hardening.** D3 closed the
   `process-approved` fallback; remaining items: invariant tests around
   byte-exact `search_query == surface_form`, restricted-role read-scope
   tests, `broker-daemon` write-scope tests. Land before M2.1 starts.
4. **Open the DECISION_LOG.md entries.** D1, D2, D3, Q1+Q7, Q2, Q3, Q6
   are binding architectural decisions per `AGENTS.md` ("Update
   DECISION_LOG.md when making architectural decisions"). They are
   recorded in the synthesis but not yet promoted into the decision log
   itself.
5. **Begin M1.3 Phase 4 candidate-features RFC.** Spec the new Phase 4
   output contract: `entity_kind` (the existing enum) plus structured
   candidate features (`occurrence_count, source_count, claim_count,
   segmenter_confidence, duplicate_cluster_id, candidate_kind_hint,
   sensitivity_class`). These features become Stage 1 rule inputs for
   RFC 0056. Run a 3-model design review.

## Authoritative Documents

Read in this order if you need the full picture:

```
1. docs/rfcs/0053-claim-extraction-grounding-boundary.md
   — the load-bearing seam: byte-exact query, restricted broker DSN
2. docs/rfcs/0054-entity-grounding-batch-workflow.md
   — draft → grant lifecycle
3. docs/rfcs/0055-grounding-evidence-materialization.md
   — broker daemon, dispatch lifecycle, evidence materialization
4. docs/rfcs/0056-entity-grounding-pre-dispatch-triage.md
   — revised after 3-model review; not yet implemented
5. docs/reviews/rfc0056-pre-dispatch-triage-design-review/SYNTHESIS.md
   — what changed in RFC 0056 and why
6. docs/reviews/grounding-stack-architectural-review-2026-05-20/SYNTHESIS.md
   — stack-level review, risk register, 3-month plan, interview answers
```

Runbooks for operating the current stack:

- `docs/runbooks/grounding-broker-role.md` — provision the restricted
  PostgreSQL role.
- `docs/runbooks/grounding-broker-daemon.md` — run the materializer
  daemon.

## What Not To Do

Carried verbatim from the architectural review's anti-recommendations
(`docs/reviews/grounding-stack-architectural-review-2026-05-20/SYNTHESIS.md`
§ "Anti-Recommendations"):

1. Do not weaken `search_query == surface_form`.
2. Do not scale by approving more grants manually.
3. Do not treat `entity_grounding_evidence` row count as success.
4. Do not put an LLM inside the network adapter.
5. Do not let the triage classifier resolve entities.
6. Do not scale broker-daemon batch size beyond a tested lock-safe bound.
7. Do not introduce cloud fallbacks, hosted identity services, telemetry,
   browser automation, or SDK agents.

## Open Architectural Questions (Carried Forward)

- Sampled-audit ratio refinement after M1.1 baseline lands.
- Adjudication threshold defaults after M3.1 measurement.
- Whether the `engram review` aggregator becomes a TUI or stays JSON-out.
- Whether re-grounding (M3.3) needs its own rate limiter when the corpus
  grows past O(10k) entities.

## Session Audit (For Provenance)

This session executed:

- A bounded end-to-end Tavily run (5 grants, 25 evidence rows, 0%
  resolution) that revealed the architectural gaps.
- A bug fix in `claim_grounding_network._clean_text` (off-by-three
  excerpt trim) — committed as `a7e4e80` earlier in the session.
- The RFC 0051–0055 implementation big-bang landing — committed as
  `eff7533`.
- The RFC 0056 draft + 3-model adversarial review + synthesis + revision.
- The grounding-stack architectural review + 3-model loop + synthesis.
- The operator interview that produced the decision table above.
- The D3 boundary-hardening change.

All three reviewers in both review loops were: Codex GPT-5.5 (via
`codex exec`), Gemini (via `gemini -p`), and local ik-llama Qwen 3.6 35B
(direct HTTP to the local serving port). Claude CLI was attempted but
unauthenticated for the user halbritt's account; substituted with the
local Qwen model.
