# Grounding Stack - Implementation Plan (2026-05-20)

| Field | Value |
|-------|-------|
| Date | 2026-05-20 |
| Model ID | Gemini 3.5 Flash |
| Goal | Execute immediate next actions in order for the grounding stack with maximum parallelism. |

---

## checklist / Tasks

- [ ] Action 4: Update [DECISION_LOG.md](file:///home/halbritt/git/engram/DECISION_LOG.md) with Decisions D097-D103.
- [ ] Action 3: Implement M1.2 Boundary Hardening.
  - [ ] Add invariant tests verifying `search_query == surface_form` for all drafted/approved grants.
  - [ ] Add tests verifying restricted role read-scope.
  - [ ] Add tests verifying `broker-daemon` write-scope.
- [ ] Action 1: Draft [docs/rfcs/0057-local-identity-adjudication.md](file:///home/halbritt/git/engram/docs/rfcs/0057-local-identity-adjudication.md).
- [ ] Action 5: Draft [docs/rfcs/0058-phase4-candidate-features.md](file:///home/halbritt/git/engram/docs/rfcs/0058-phase4-candidate-features.md).
- [ ] Action 2: Land M1.1 Eval Baseline.
  - [ ] Select 50 representative `unknown` entities and label them in [evals/grounding/baseline-2026-05.md](file:///home/halbritt/git/engram/evals/grounding/baseline-2026-05.md).
  - [ ] Implement a telemetry report or helper.

---

## Detailed Proposed Changes

### 1. Update Decision Log
We will record the locked-in decisions from the 2026-05-20 interview under `DECISION_LOG.md` as decisions D097-D103.

### 2. M1.2 Boundary Hardening
We will add new tests to [tests/test_claim_grounding_security.py](file:///home/halbritt/git/engram/tests/test_claim_grounding_security.py):
- Assert that creating a grant where `query_text_class == 'entity_surface_form'` and `search_query != surface_form` raises a validation error (already validated in code by `ClaimGroundingSchemaError`, but needs a test).
- Assert that the restricted role cannot read non-grounding tables (e.g. `messages`, `beliefs`, `claims`, `captures`).
- Assert that the restricted role cannot write to any tables other than `entity_grounding_evidence` and `claim_grounding_grants` (for status updates).

### 3. Draft RFC 0057 (Local Identity Adjudication)
Create [docs/rfcs/0057-local-identity-adjudication.md](file:///home/halbritt/git/engram/docs/rfcs/0057-local-identity-adjudication.md). It will specify:
- The local adjudication stage between evidence materialization and downstream consumption.
- Auto-resolve thresholds (Q3 defaults: 3 concurring candidates, 2 supporting claims, 0.9 confidence).
- Revocation propagation (Q4: deferred to consumer).
- Personal/local-only entity workflow (Q5: separate pipeline or local-identity store).
- Provider-neutral fields mapping.

### 4. Draft RFC 0058 (Phase 4 Candidate Features)
Create [docs/rfcs/0058-phase4-candidate-features.md](file:///home/halbritt/git/engram/docs/rfcs/0058-phase4-candidate-features.md). It will spec the updated Phase 4 contract returning structured candidate features instead of a simple binary `unknown`.

### 5. Land M1.1 Eval Baseline
Select 50 representative active `unknown` entities from the database, classify them across the 8 taxonomy categories, and surface them in [evals/grounding/baseline-2026-05.md](file:///home/halbritt/git/engram/evals/grounding/baseline-2026-05.md).

---

## Verification Plan
1. **Automated tests:** Run `make test` and verify that the security tests pass.
2. **Review:** Design reviews of the new RFC drafts.
