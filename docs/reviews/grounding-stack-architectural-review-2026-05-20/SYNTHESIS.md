# Grounding Stack Architectural Review — Synthesis

| Field | Value |
|-------|-------|
| Date | 2026-05-20 |
| Reviewers | Codex GPT-5.5 (`REVIEW_codex.md`); Gemini (`REVIEW_gemini.md`); local ik-llama Qwen 3.6 35B-A3B (`REVIEW_ik_llama_qwen.md`) |
| Originator | Claude Opus 4.7 (this synthesis) |
| Synthesized Verdict | **restructure within the existing shape** — the primitives (append-only evidence, RFC 0053 byte-exact query, restricted broker DSN) are correct; the operational workflow around them is not. |

## Cross-Reviewer Convergence

| Theme | Codex | Gemini | ik-llama | Synthesized Severity |
|---|---|---|---|---|
| Per-grant operator approval is the bottleneck | R2 (H) | R1 (H) | R1 (H) | **H — UNANIMOUS** |
| Upstream Phase 4 noise is the root cause, not the materializer | R1 (H) | R2 (H) | (implicit) | **H — UNANIMOUS** |
| No labeled eval surface; resolution rate untracked | R5 (H) | R3 (H) | (implicit) | **H — 2/3 explicit, 3/3 directional** |
| Evidence rows ≠ resolution; wrong success metric | R7 (H) | (implicit) | (implicit) | **H — Codex elevation, others agree** |
| Byte-exact `search_query == surface_form` cannot disambiguate alone | R3 (H) | R5 (M) | (implicit) | **H — UNANIMOUS direction** |
| RFC 0056 false-suppression is a real correctness risk | R4 (H) | R4 (M) | R2 (H) | **H — UNANIMOUS** |
| Local LLM prompt drift weakens auditability | R9 (M) | (implicit) | R5 (H) | **M/H** |
| Broker privilege expansion as automation grows | R8 (H) | — | R4 (M) | **M/H** |
| Provider lock-in to Tavily-specific result shape | R10 (M) | — | — | **M — Codex-only** |
| Stale entity identity, no re-grounding trigger | — | — | R3 (M) | **M — ik-llama-only** |

3/3 reviewers concur that the stack is architecturally sound but operationally broken, and that the root cause is upstream signal quality, not the broker or materializer.

## Synthesized Risk Register

| ID | Risk | Likelihood | Impact | Net |
|----|------|------------|--------|-----|
| R1 | Per-grant operator approval does not scale | H | H | **H** |
| R2 | Phase 4 emits ungroundable surfaces as `unknown` entities | H | H | **H** |
| R3 | No eval baseline; cannot measure improvement or regression | H | H | **H** |
| R4 | Resolution-rate-blind: evidence count masks 0% resolution | H | M | **H** |
| R5 | Byte-exact query cannot disambiguate without local adjudication | H | M | **H** |
| R6 | False suppression by triage hides real entities permanently | M | H | **H** |
| R7 | Local LLM in triage introduces prompt-drift audit gap | M | M | **M** |
| R8 | Broker privilege expansion as automation grows | M | H | **M/H** |
| R9 | Tavily-specific result shape leaks into resolver semantics | M | M | **M** |
| R10 | Stale entities never re-grounded as new local context arrives | M | M | **M** |

## Synthesized Recommendations (Ranked)

### 1. Land a labeled eval baseline before scaling automation
**Action:** Label the 281 current `unknown` entities (or a 50-item representative sample to start) into:
broker-eligible-public, duplicate, segmentation-noise, personal-artifact,
local-only-entity, sensitive-private, ambiguous-but-real, ungroundable.
Track per-stage metrics: draft-rate, approval-rate, dispatch-success,
**resolution-rate**, false-suppression-rate, operator-actions-per-resolved-entity.

**Why now:** The 0% resolution rate is undiagnosable without this. Every other
recommendation gets graded against it. Without an eval surface, Phase 4
changes, RFC 0056, and any new tiered approval are flying blind.

**Tradeoff:** Up-front labeling effort. Cheaper than continuing to approve
ungroundable grants.

**Provenance:** Codex R5 + Rec 1; Gemini R3 + Rec 3; ik-llama implicit. **3/3 agreement on order.**

### 2. Reframe RFC 0056 as a tiered triage *policy*, not a classifier
**Action:** Keep the revised RFC 0056 architecture (rules-first pre-filter,
LLM tie-breaker), but **rewrite the rollout as a policy gate**: rules
handle the bulk; the LLM only resolves ambiguous cases; every decision
persists prompt version, model digest, confidence, reason code, and a
sampled-audit flag for the operator-review feedback loop. Auto-suppress
only high-confidence noise/duplicate/personal-artifact; medium confidence
goes to **batch review** (next recommendation).

**Why now:** Operator toil has to move left of `claim_grounding_grants`.
This addresses R1, R2, R6, R7 in one move.

**Tradeoff:** False suppression becomes a real failure mode. The sampled-audit
loop is non-negotiable.

**Provenance:** Codex Rec 2; Gemini Rec 4; ik-llama Rec 1. **3/3 agreement on direction; only the priority order varies.**

### 3. Replace per-grant approval with tiered batch review
**Action:** Preserve `claim_grounding_grants` as the audit substrate (it is
not the problem). Add a policy layer above it that classifies grants into
4 tiers:

- **Tier 0** (auto-suppress): high-confidence noise/dup/personal — triage
  drops; no grant drafted; sampled into audit.
- **Tier 1** (auto-approve under policy): low-risk public exact surfaces
  (e.g. existing approved-grant pattern, very-high-confidence
  proper-noun) — grant auto-flips to `approved`; sampled into audit;
  operator can `revoke` post-hoc.
- **Tier 2** (batch review): a list view of N grants at a time, with the
  exact `search_query` visible, approve-all/deny-all controls, individual
  flagging.
- **Tier 3** (explicit handling): sensitive-private or any surface with
  `privacy_tier >= 2`; must go to manual review with full context.

**Why now:** R1 + R8 + R5. Operator toil moves from per-grant to per-batch
or per-policy-update.

**Tradeoff:** Auto-approval increases the chance of an unintended broker
query. Mitigations: dry-run preview, byte-exact `search_query` display,
batch-size limits, sampled post-hoc audit, instant-revoke surface.

**Provenance:** Codex Rec 4; Gemini Rec 1; ik-llama Rec 2 + Rec 4. **3/3 agreement on direction; differs in tier count and threshold.**

### 4. Push the unknown-entity contract into Phase 4
**Action:** Phase 4 currently emits `entity_kind='unknown'` as a binary
state. Replace with structured candidate features:
`{occurrence_count, source_count, claim_count, segmenter_confidence,
duplicate_cluster_id, candidate_kind_hint, sensitivity_class}`. The
grounding stack reads these features; the triage step uses them as Stage 1
rule inputs.

**Why now:** Root cause of the 0% resolution rate is upstream
signal-to-noise (R2). Fixing the downstream materializer cannot resolve
it. The Phase 4 contract is also where dedupe clustering should happen,
not in the triage row.

**Tradeoff:** Phase 4 schema change, migration, possible re-extract on the
existing corpus.

**Provenance:** Codex Rec 3; Gemini Rec 2; ik-llama implicit. **3/3 directional.**

### 5. Add a local-only identity adjudication stage after evidence materialization
**Action:** New stage between `entity_grounding_evidence` materialization
and the rest of the system. The broker still retrieves with the exact
`surface_form`; a **local resolver** then reads materialized evidence +
local claim context and emits one of `{resolved, ambiguous, denied,
needs_operator_review}` with provenance. This is the architectural piece
the RFC 0053 byte-exact rule structurally requires but doesn't currently
provide.

**Why now:** R4 + R5 + R7. The 0% resolution rate is the symptom; the
absence of this stage is the cause. The byte-exact rule keeps the network
surface honest; **local adjudication is where ambiguity gets resolved
without leaking context outward.**

**Tradeoff:** New stage, new RFC needed (proposal: RFC 0057). Some
adjudication logic becomes local-model dependent — but it never touches
the network surface, so the local-first invariant is preserved.

**Provenance:** Codex Rec 5; Gemini implicit ("redirects R2 to root
cause"); ik-llama not present. **Codex-led, but the gap is felt across all
three reviews.**

### 6. Harden the RFC 0053 boundary before any auto-approval lands
**Action:** Add invariant tests around `search_query == surface_form`,
keep `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL` mandatory for any
materializer path (close the existing fallback), test that
`broker-daemon` cannot read any non-grounding table from the restricted
role, add an explicit policy on what the broker daemon can and cannot
write.

**Why now:** Recommendations 3 and 5 expand automated paths. Blast radius
grows. The boundary is fine today; it becomes more dangerous as
human-in-the-loop frequency drops.

**Tradeoff:** More migration and role testing. Worth it before Tier 1
auto-approval lands.

**Provenance:** Codex Rec 6; ik-llama R4 (lock contention). **2/3 explicit.**

### 7. Add provider replay fixtures and provider-neutral candidate fields
**Action:** Capture sanitized Tavily responses as deterministic test
fixtures. Make the resolver consume **provider-neutral candidate fields**
(`canonical_label, source_url, source_label, content_excerpt,
content_hash`) rather than Tavily-specific result keys. This keeps the
resolver decoupled from a single provider's response semantics.

**Why now:** R9 + supports R3. Cheap to do early; expensive to do once a
second provider arrives.

**Tradeoff:** Fixture maintenance burden.

**Provenance:** Codex Rec 7. **Codex-only, low-cost, accept.**

### 8. Add a re-grounding trigger when new local context arrives
**Action:** When a new claim references an entity previously marked
`ambiguous` or `needs_operator_review`, schedule a re-adjudication. Do
not re-dispatch to the network unless a new grant is approved — the
adjudication runs against existing materialized evidence with refreshed
local context.

**Why now:** R10. The local-first advantage is that we accumulate
context; the current stack doesn't use it.

**Tradeoff:** Background load on the resolver. Manageable with batching.

**Provenance:** ik-llama Rec 3. **ik-llama-only, but architecturally
correct given the rest of the stack.**

## Anti-Recommendations (Consolidated)

1. **Do not weaken `search_query == surface_form`.** Query refinement
   improves search quality but rewrites the consent and privacy model.
   Any future change needs a new RFC and a visibly different operator
   approval surface. (Codex AR1, ik-llama AR1.)
2. **Do not scale by approving more grants manually.** Convert architecture
   debt into automation, not into operator toil. (Codex AR2.)
3. **Do not treat `entity_grounding_evidence` row count as success.** The
   metric is resolved identities with preserved provenance. (Codex AR3.)
4. **Do not put an LLM inside the network adapter.** LLM interpretation
   belongs in local triage or local adjudication. (Codex AR4.)
5. **Do not let the triage classifier resolve entities.** Triage can only
   suppress or pass. Resolution remains the domain of the (proposed)
   local adjudication stage and the operator. (ik-llama AR3.)
6. **Do not scale broker-daemon batch size beyond a tested lock-safe
   bound.** Start at 10–50, grow only with measurement. (ik-llama AR4.)
7. **Do not introduce cloud fallbacks, hosted identity services, telemetry,
   browser automation, or SDK agents.** Local-first is load-bearing.
   (Codex AR5, ik-llama AR2.)

## Synthesized 3-Month Plan

The plan synthesizes Codex's milestones, adjusted with Gemini's
upstream-Phase-4 emphasis and ik-llama's append-only auditability rule.
Each milestone names a deliverable, an improved metric, and a review
surface.

### Month 1: Visibility and Boundary Hardening

- **M1.1 — Eval baseline.** Label a 50-entity representative sample
  across the 8 categories. Add per-stage telemetry: resolution-rate,
  false-suppression-rate, operator-actions-per-resolved-entity. Land
  `evals/grounding/baseline-2026-05.md`.
  - *Metric:* visibility into where the 0% comes from.
  - *Gate:* operator review of category boundaries.
- **M1.2 — RFC 0053 boundary hardening.** Close the operator-DSN fallback
  in `entity-grounding process-approved`. Add invariant tests for
  byte-exact query, restricted-role isolation, broker-daemon read-scope.
  - *Metric:* boundary safety before automation expands blast radius.
  - *Gate:* migration + test review.
- **M1.3 — Phase 4 candidate features (design).** Spec the new
  Phase 4 output contract (`entity_kind` + structured candidate features).
  Land as RFC 0057 (proposal).
  - *Metric:* unblocks Month 2.
  - *Gate:* RFC 0057 design review (3-model loop again).

### Month 2: Triage Policy and Batch Review

- **M2.1 — RFC 0056 implementation as policy gate.** Land the
  revised RFC 0056 with rules-first prefilter, LLM tie-breaker, sampled
  audit loop, three-stage rollout (rules-only → LLM shadow → enforce).
  - *Metric:* reduction in broker-eligible queue size; false-suppression
    rate measured against the M1.1 baseline.
  - *Gate:* eval thresholds documented in RFC 0056.
- **M2.2 — Batch review + tiered approval.** Add `--batch` mode to
  `engram claim-grounding grants` and implement Tier 0/1/2/3 policy.
  Auto-approval requires sampled audit and operator opt-in per tier.
  - *Metric:* operator-actions-per-resolved-entity drops by ≥ 70%
    relative to the M1.1 baseline.
  - *Gate:* CLI workflow review on the labeled corpus.
- **M2.3 — Phase 4 candidate features (implementation).** Land the schema
  change behind a migration. Backfill on the existing corpus.
  - *Metric:* upstream noise rate per category, measurable against M1.1.
  - *Gate:* migration + re-extract review.

### Month 3: Local Adjudication and Re-Grounding

- **M3.1 — RFC 0057 local identity adjudication (proposal +
  implementation).** New stage after evidence materialization;
  consumes provider-neutral candidate fields + local claim context;
  emits `{resolved, ambiguous, denied, needs_operator_review}`.
  - *Metric:* resolution rate among broker-eligible candidates moves
    from 0% to a target threshold set by M1.1 eval (proposal: ≥ 40%
    Phase-1 target).
  - *Gate:* RFC 0057 design review (3-model loop), pre/post resolution
    eval report.
- **M3.2 — Provider replay fixtures + adapter contract.** Capture
  sanitized Tavily responses as fixtures. Refactor resolver to consume
  provider-neutral fields. Document the adapter contract.
  - *Metric:* deterministic regression coverage on resolver behavior.
  - *Gate:* fixture review (no sensitive local data stored), `make test`.
- **M3.3 — Re-grounding trigger.** Schedule re-adjudication when new
  claim context references a `needs_operator_review` or `ambiguous`
  entity. No re-dispatch unless a new grant is drafted.
  - *Metric:* "knowledge decay" rate — fraction of ambiguous entities
    re-resolved without new network calls.
  - *Gate:* batch-job review, background-load measurement.

## Open Architectural Questions (Operator Decisions Required)

The reviewers raised several questions that need operator input before
the plan above can fully execute:

1. **False-suppression budget for RFC 0056.** What rate is acceptable
   before suppressed candidates must be sampled back into human review?
   Codex Q1.
2. **Tier 1 auto-approval scope.** Opt-in per corpus, per operator
   session, or persistent local policy? Codex Q2.
3. **Local adjudication threshold for auto-resolve.** What minimum
   evidence + local-claim-context signal allows the resolver to mark
   `resolved` without operator review? Codex Q3.
4. **Revocation propagation.** When `claim_grounding_grants` rows are
   revoked or expired, what happens to `entity_grounding_evidence` that
   was materialized under that grant in downstream lookup? Codex Q4.
5. **Personal/local-only entities — separate workflow?** Should they
   exit the grounding pipeline entirely into a separate
   local-identity store? Codex Q5.
6. **Unified vs separated review queues.** One review surface for
   triage, grants, identity, or separate CLIs optimized per stage?
   Codex Q6.
7. **Sampled-audit ratio.** What fraction of auto-suppressed and
   auto-approved decisions must be sampled into human review weekly?
   (Synthesizer addition.)

## Decision Items For The Originator

Three concrete next-step decisions for the operator:

- **D1 — Adopt the 3-month plan as written, or adjust sequencing.** If
  upstream Phase 4 work is preferred before Month 2's triage
  implementation (Gemini's framing), M1.3 and M2.3 swap into earlier
  slots and M2.1 moves to Month 3.
- **D2 — Open RFC 0057 (local identity adjudication) immediately, or
  defer to Month 3.** If opened now, it goes through its own 3-model
  review before any implementation. If deferred, Month 3 slips.
- **D3 — Resolve the operator-DSN fallback today.** Closing the fallback
  in `entity-grounding process-approved` is a small-scope change that
  hardens the boundary before automation grows. Codex flags this as a
  Month 1 deliverable but it could land independently.

## Resolved After Operator Interview 2026-05-20

The synthesis's Decision Items and Open Questions were resolved in a
3-round interview. Concrete settings below; these are starting policy and
revisited after M1.1 baseline lands.

### Decision Items

| ID | Question | Decision |
|----|----------|----------|
| D1 | 3-month plan sequencing | Adopt as written: M1 eval + boundary harden + RFC 0057 design; M2 RFC 0056 land + batch review + Phase 4 schema; M3 adjudicator + replay fixtures + re-grounding. |
| D2 | RFC 0057 timing | Open now (Month 1 design slot); land Month 3. Implied by D1. |
| D3 | Close `process-approved` operator-DSN fallback | Closed today (this session). |

### Open Architectural Questions

| ID | Question | Resolution |
|----|----------|------------|
| Q1+Q7 | Triage feedback loop policy | Moderate defaults. `false_suppression_budget = 5%` (target `recall(groundable) >= 0.95`). `weekly_audit_sample = 5%` of auto-suppressed + auto-approved. `tier3_audit_sample = 100%`. Revisited after M1.1. |
| Q2 | Tier 1 auto-approval scope | Per-corpus policy file. Auto-approval defaults **off** until explicitly enabled per `(tenant_id, corpus_id)`. Conservative on `personal/personal`; can loosen on lower-risk corpora later. |
| Q3 | Local adjudication auto-resolve threshold | High threshold with per-corpus override. Defaults: `min_concurring_candidates = 3`, `min_supporting_claims = 2`, `resolver_confidence_min = 0.9`. Lives in the same policy file as Q2. |
| Q4 | Revocation propagation to materialized evidence | Deferred to RFC 0057. Resolver consumes evidence; revocation semantics belong with the consumer. |
| Q5 | Personal/local-only entities — same vs separate pipeline | Deferred to RFC 0057 design. The lead architectural question for the upcoming adjudication RFC. |
| Q6 | Review queue shape | Hybrid. Keep per-stage CLIs (`claim-grounding grants ...`, `entity-grounding triage ...`, identity-review actions); add a top-level `engram review` aggregator that surfaces all pending operator items in one list. |

### Immediate Follow-Ups

- ✅ **D3 landed.** `entity-grounding process-approved` refuses without
  `ENGRAM_ENTITY_GROUNDING_BROKER_DATABASE_URL`. Test
  `test_entity_grounding_process_approved_refuses_without_broker_database_url`
  pins the new behavior. CHANGELOG updated.
- ⏳ **RFC 0057 design** — open the proposal RFC in Month 1 with three
  question anchors carried from this synthesis: Q4 (revocation
  propagation), Q5 (personal/local-only workflow), and the resolver
  auto-resolve threshold (Q3) — note Q3 has a default but the resolver
  RFC should document the policy file shape.
- ⏳ **M1.1 eval baseline** — first labeled batch of 50 unknowns + per-stage
  telemetry harness. Gates almost everything else.
- ⏳ **DECISION_LOG.md entries** — each of D1, D2, D3, Q1+Q7, Q2, Q3, Q6
  is a binding architectural decision that should land as a numbered
  decision entry. Not yet written.

## Storage Rule Compliance

Per `docs/process/multi-agent-review-loop.md`:

```
docs/reviews/grounding-stack-architectural-review-2026-05-20/
├── REVIEW_codex.md          (Codex GPT-5.5, provenance)
├── REVIEW_gemini.md         (Gemini CLI, provenance)
├── REVIEW_ik_llama_qwen.md  (local Qwen 3.6 35B, provenance)
└── SYNTHESIS.md             (this file — distilled action set)
```

Originating reviews are kept as provenance and must not be deleted. Any
accepted deltas to existing RFCs (0053/0054/0055/0056) will be applied
in follow-up edits with this synthesis cited as the gating review. New
RFCs (0057 candidate, possible Phase 4 candidate-features RFC) start
their own 3-model review loop before implementation.
