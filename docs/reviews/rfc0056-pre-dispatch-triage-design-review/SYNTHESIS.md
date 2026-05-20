# RFC 0056 Design Review Synthesis

| Field | Value |
|-------|-------|
| Artifact | `docs/rfcs/0056-entity-grounding-pre-dispatch-triage.md` |
| Reviewers | Codex GPT-5.5 (`REVIEW_codex.md`); Gemini (`REVIEW_gemini.md`); local ik-llama Qwen 3.6 35B-A3B (`REVIEW_ik_llama_qwen.md`) |
| Date | 2026-05-20 |
| Originator | Claude Opus 4.7 (this synthesis) |
| Verdict | reject-revise-major (3 of 3 reviewers concurred) |

## Reviewer Convergence

| Theme | Codex | Gemini | ik-llama | Net Severity |
|---|---|---|---|---|
| Privacy-tier inheritance + audit table missing `privacy_tier` | BLOCKER | BLOCKER | BLOCKER | **BLOCKER** |
| Dedupe correctness (target lifecycle / scope / cycles / hallucinated UUID) | BLOCKER | MAJOR + MINOR | BLOCKER | **BLOCKER** |
| Idempotency / capsule-hash determinism + supersede vs override race | MAJOR | MAJOR | BLOCKER | **BLOCKER** |
| Free-text rationale allows paraphrase exfiltration | MINOR | BLOCKER | (implicit) | **BLOCKER** |
| `no_egress` "smoke test" too weak for hard constraint | BLOCKER | — | — | **MAJOR** |
| JSON schema in RFC is illustrative, not enforceable | MAJOR | (implicit) | (implicit) | **MAJOR** |
| Decisions not mutually exclusive, no precedence rule | MAJOR | — | — | **MAJOR** |
| Model serving contention on shared ik-llama backend | MAJOR | MINOR | MAJOR | **MAJOR** |
| Alternative-model claims overpromise structured-output parity | MAJOR | — | — | **MAJOR** |
| Eval gate insufficient to justify default-on suppression | MAJOR | — | (implicit) | **MAJOR** |
| Operator override CLI under-specified (no `--decision`, `--reason`, `--actor`) | MAJOR | — | MAJOR | **MAJOR** |
| `needs_review` has no specified review UI / dead-end | MINOR | — | MAJOR | **MAJOR** |
| Capsule size cap arbitrary; bounded-list non-determinism | MINOR | — | MAJOR | **MAJOR** |
| Short "public-tier" strings still leak | MINOR | — | — | **MINOR** |
| `--dry-run` hides per-entity debug data | MINOR | — | — | **MINOR** |
| Editorial / naming inconsistencies | NIT | — | — | **NIT** |

## Per-Finding Verdicts

Per `docs/process/multi-agent-review-loop.md`, each finding is classified
**accepted**, **accepted-with-modification**, **deferred**, or **rejected**.

### Accepted (apply to RFC 0056 before any implementation)

1. **Privacy-tier inheritance is a normative requirement, not an Open
   Question.** Move it from Open Questions to Boundary and Schema. Add
   `privacy_tier INTEGER NOT NULL` to `entity_grounding_triage_actions`.
   Capsule assembly must compute `max(entity.privacy_tier, source claim
   tiers, sibling entity tiers, evidence row tiers)` and carry it onto the
   action and onto downstream display. The capsule must exclude any data
   derived from source claims whose privacy tier exceeds the entity's tier,
   regardless of any short-string allowance. (Codex BLOCKER #1, Gemini
   BLOCKER #1, ik-llama BLOCKER #1.)

2. **Dedupe attribution must be gated on the target's own triage outcome and
   structural validity.** `dedupe_target_entity_id` must satisfy: same
   tenant/corpus; status=active; non-superseded; non-self; no cycle;
   latest-target-triage decision must equal `groundable`. The LLM-emitted
   UUID must also belong to the capsule's provided sibling IDs; if not,
   downgrade to `needs_review` with reason `agent_hallucinated_uuid`. (Codex
   BLOCKER #2, Gemini MAJOR + MINOR, ik-llama BLOCKER #3.)

3. **Operator override survives capsule-hash drift.** If the latest action
   for an entity is `agent_version='operator'`, the agent must skip the LLM
   call and preserve the operator's decision regardless of new source-claim
   churn, unless an explicit `--ignore-overrides` flag is passed. The
   `superseded_at` semantics need an explicit rule for which row supersedes
   which on capsule change. (Gemini MAJOR, ik-llama BLOCKER #2.)

4. **Drop free-text `rationale` from the LLM output schema.** Replace with a
   fixed `reason_code` enum (initial set:
   `personal_artifact`, `segmentation_noise`, `too_broad_or_generic`,
   `duplicate_surface`, `groundable_public_entity`,
   `model_insufficient_context`, `model_refusal`,
   `agent_quoted_private_text`, `agent_hallucinated_uuid`). A bounded
   operator-facing rationale field, if retained at all, must be tier-aware
   and never round-trip through the LLM output. (Gemini BLOCKER #2, Codex
   MINOR #1.)

5. **No-egress invariant must be enforced by tests that bind, not by a smoke
   sentinel.** Required gates: (a) `socket.socket` and `socket.getaddrinfo`
   patched to refuse non-loopback addresses; (b) import-graph assertion that
   `entity_grounding_triage` does not transitively import
   `claim_grounding_network`, `claim_grounding_broker`, or any module under
   the network-adapter surface; (c) broker DSN refusal happens before DB and
   model client construction; (d) proxy environment variables
   (`http_proxy`, `https_proxy`, `all_proxy`, plus uppercase variants) are
   stripped or refused at startup. (Codex BLOCKER #3.)

6. **Provide a real JSON Schema in the RFC, not an example.** Include
   `additionalProperties: false`, `oneOf` conditional for
   `dedupe_target_entity_id`, `enum` for `decision` and `reason_code`,
   `maxLength` on any string, explicit `schema_version`, and reject vs
   downgrade behavior on each violation class. The schema is part of the RFC
   text, not deferred to implementation. (Codex MAJOR #1.)

7. **Decisions need a precedence rule.** Explicit precedence (high to low):
   already-grounded > already-drafted > existing-approved-grant >
   not_groundable > dedupe_of > needs_review > groundable. Capsule assembly
   evaluates structural cases first and short-circuits before any LLM call;
   the LLM only resolves remaining cases. (Codex MAJOR #2.)

8. **Serving contention is in-scope, not a "serving-layer concern".** RFC
   must specify: a separate model id or a separate ik-llama backend port
   (`ENGRAM_TRIAGE_BASE_URL` already exists for this — make the separation
   normative); bounded per-call timeout and retry policy; load eval at 300
   and 1000 candidates before default-on rollout; pagination/resume
   semantics under `ENGRAM_TRIAGE_REQUIRED=1`. The triage worker must never
   block the extractor. (Codex MAJOR #5, ik-llama MAJOR #1, Gemini MINOR.)

9. **Idempotency strengthened.** (a) Add a partial unique index over active
   rows: `(tenant_id, corpus_id, entity_id, capsule_hash, model_id,
   prompt_version, schema_version) WHERE superseded_at IS NULL`. (b)
   Canonicalize capsule hashing: stable sort order on every bounded list
   (sibling entities ORDER BY id, source claims ORDER BY claim_id, evidence
   ORDER BY id), canonical JSON serialization with sorted keys and
   `separators=(",", ":")`. (c) Include `model_digest` (SHA of GGUF file)
   and generation params in the action row for full replay. (d) Enumerate
   every invalidation event in a dedicated subsection. (Codex MAJOR #3,
   ik-llama BLOCKER #2.)

10. **Operator override CLI.** Add `--decision {groundable,
    not_groundable, dedupe_of, needs_review}`, `--reason CODE`, `--actor
    EMAIL`, `--dedupe-target-entity-id UUID`, `--force-rerun`. Insert under
    a row-level lock; reject the agent's append if a concurrent operator
    action lands first. (Codex MAJOR #4.)

11. **Specify the `needs_review` operator surface.** RFC must describe: a
    list view filtered to `decision='needs_review'`; batch-action controls
    (force-ground, force-not-ground, mark-dedupe-of); per-entity context
    panel showing source-claim refs, privacy tier, prior triage history,
    sibling surfaces, existing grants/evidence. The CLI must support batch
    operations equivalent to the UI controls. (ik-llama MAJOR #2, Codex
    MINOR #3.)

12. **Capsule determinism.** Specify selection rule when bounded lists
    overflow: keep the N items with highest tier, then most-recent
    `created_at`, then lowest UUID lex. Explicitly NOT
    "newest 6" alone — that allows non-deterministic capsules under
    concurrent inserts. (ik-llama MAJOR #4.)

13. **Stronger eval gate.** Per-class precision AND recall thresholds,
    especially `recall(groundable) >= 0.95` (false-suppression ceiling).
    Adversarial privacy cases. Duplicate-target correctness measurement
    (does the dedupe target actually have an approved grant?). Confidence
    calibration. Runtime measurement at 300/1000 candidates. No-egress
    pytest run as a gate, not a smoke. Holdout set isolation rule. (Codex
    MAJOR #6.)

14. **Three-stage rollout: rules-only → LLM shadow → enforce.** Codex's
    alternative-design proposal is the right rollout shape. Stage 1: pure
    rule-based pre-filter (length, canonical-key dedupe, stop-list,
    existing-grant check) with no LLM call. Stage 2: LLM runs in shadow
    mode, writes actions, but the draft worker ignores triage decisions.
    Stage 3: `ENGRAM_TRIAGE_REQUIRED=1` flips after eval thresholds pass.
    Most of the bad surfaces in the 2026-05-20 run ("Noise W",
    "Local Grocery Shopping List X" near-duplicate) get caught at Stage 1
    without invoking the model. (Codex Alternative-Design.)

### Accepted with modification

15. **Short public-tier object values in capsule.** Codex MINOR #2 argues
    drop them entirely; Gemini didn't flag. Modification: keep the rule but
    add a denylist of common-but-sensitive short strings (phone shapes,
    address shapes, SSN shapes, common credential prefixes); refuse object
    values matching the denylist regardless of tier. Tier-bound short
    strings remain conditionally allowed, but the rationale-paraphrase
    scanner (Accept #4) also enforces non-leakage on the output side.

16. **`--dry-run` debug ergonomics.** Codex MINOR #3 wants JSONL with
    per-entity detail. Modification: provide `--dry-run --format jsonl`
    that emits per-entity records with `entity_id, decision, reason_code,
    confidence, capsule_hash, reused, elapsed_ms, privacy_tier`; never emit
    rationale text in JSONL; rationale is operator-UI-only and tier-gated.

### Deferred (track as follow-up, not blocking RFC 0056)

17. **Hermes-vs-Qwen bake-off.** Codex MAJOR #5 calls out alternative-model
    overpromise. RFC 0056 should remove the Hermes/Llama/Qwen-2.5
    recommendations entirely from the body, and add a single sentence:
    "Non-default models are explicitly out of scope for this RFC. Any
    additional model must pass a separate compatibility spec proving strict
    JSON schema adherence, refusal handling, and operator-labeled
    calibration before promotion." Bake-off lives in a follow-up RFC.

18. **Cross-batch dedupe consistency under concurrent triage runs.**
    ik-llama BLOCKER #3 raises the case where A→B and B→C are decided
    in parallel and create an invalid chain. The Accept #2 constraint
    (target must already be `groundable`) prevents the chain from
    materializing into drafts, but the action rows can still record an
    invalid dedupe pointer. RFC 0056 should require the draft worker to
    re-validate dedupe pointers at draft time and emit a contradiction
    action if invalid. A stricter "two-phase triage" (Phase 1 classify, Phase
    2 resolve dedupe pointers with knowledge of all Phase 1 outputs) is
    deferred to a follow-up RFC unless the first eval shows pointer
    invalidity above 5%.

### Rejected

None. All reviewer findings are accepted in some form. This reflects the
quality of the reviews more than the quality of the RFC.

## RFC Delta Plan

The originator (Claude Opus 4.7) will apply the following concrete edits to
`docs/rfcs/0056-entity-grounding-pre-dispatch-triage.md` in a follow-up pass
before any implementation work begins:

1. **Frontmatter:** bump status note to `proposal (revised after design
   review 2026-05-20)`; add review provenance link to this synthesis.
2. **Summary:** unchanged.
3. **Goals / Non-Goals:** unchanged structurally; explicitly add "no
   free-text rationale in LLM output" to Non-Goals.
4. **Boundary:** expand `no_egress` requirement per Accept #5; add
   loopback-only socket binding, import-graph assertion, proxy env
   handling, broker-DSN-refusal-before-construction.
5. **Local Model Choice:** delete Hermes/Llama/Qwen-2.5 paragraphs
   (Deferred #17). Add "Triage backend must run on a separate ik-llama
   port or model id from extraction; default `ENGRAM_TRIAGE_BASE_URL`
   reflects this." Add bounded timeout/retry/concurrency requirements per
   Accept #8.
6. **Local Context Capsule:** add capsule determinism rule per Accept #12;
   add max-tier filtering per Accept #1; tighten short-string rule per
   Accept #15.
7. **Decision Schema:** rewrite as Accept #4 + #6 + #7. Embed the real JSON
   Schema. Add `reason_code` enum. Add precedence rule. Add hallucinated-
   UUID downgrade rule.
8. **Schema (SQL):** add `privacy_tier INTEGER NOT NULL`, `reason_code TEXT
   NOT NULL`, `model_digest TEXT NOT NULL`, generation-params columns;
   replace `rationale TEXT NOT NULL` with optional tier-gated
   `operator_rationale TEXT`; add the partial unique index per Accept #9;
   add a `CHECK` enforcing `decision='dedupe_of' AND
   dedupe_target_entity_id IS NOT NULL AND dedupe_target_entity_id !=
   entity_id`.
9. **Workflow Integration:** add structural pre-filter (Accept #14
   Stage 1); add draft-time dedupe re-validation (Deferred #18); rename
   "Workflow Integration" → "Workflow Integration and Rollout Stages".
10. **CLI:** expand override surface per Accept #10; add JSONL dry-run per
    Accept #16; add batch-action commands per Accept #11.
11. **Idempotency:** rewrite per Accept #9. Enumerate invalidation events
    (model id, model digest, prompt version, schema version, context-builder
    version, source-claim membership change, evidence membership change,
    privacy-tier change). Add operator-override survival rule from Accept
    #3.
12. **Evaluation:** rewrite per Accept #13. Add per-class precision AND
    recall thresholds, holdout isolation, no-egress test gate, runtime
    measurement at 300/1000, default-on promotion criteria.
13. **Observability:** restructure to specify the operator UI for
    `needs_review` per Accept #11.
14. **Open Questions:** delete the "privacy tier inheritance" question
    (moved to Boundary). Delete the "Hermes vs Qwen bake-off" question
    (deferred to follow-up RFC). Keep "pre-existing approved grants" and
    "dedupe scope" with their original proposals.
15. **Acceptance Criteria:** expand per Codex's gap list (REVIEW_codex.md
    lines 100–109). All ten gaps become acceptance bullets.

## Process Gate

- This synthesis is the artifact of record for the design review.
- The RFC will be revised in this same conversation (small, focused
  edits, no fresh context required since the edits are mechanical
  application of accepted deltas).
- Implementation must not begin until the revised RFC is in place. Any
  prompt to implement should reference the revised RFC and explicitly cite
  this synthesis as the gating review.

## File Manifest

```
docs/reviews/rfc0056-pre-dispatch-triage-design-review/
├── REVIEW_codex.md
├── REVIEW_gemini.md
├── REVIEW_ik_llama_qwen.md
└── SYNTHESIS.md   (this file)
```

The three review artifacts are preserved as provenance per the multi-agent
review loop's storage rule. They should not be deleted after synthesis.
