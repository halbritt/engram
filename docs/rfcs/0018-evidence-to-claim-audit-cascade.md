# RFC 0018: Evidence-to-Claim Audit Cascade

Status: proposal
Date: 2026-05-06
Context: ROADMAP Step 6 (post-Phase-3 adversarial round) and Step 9 (gold
set against consolidated corpus); RFC 0011 §§ Stage A / Stage B;
DECISION_LOG D002, D003, D008, D010, D019, D043, D049, D050, D052, D056,
D058, D064; `HUMAN_REQUIREMENTS.md` § refusal of false precision; prior
art: arXiv:2605.03042 § 3.1 (ARIS evidence-to-claim audit cascade)

This RFC proposes an automated, advisory **audit cascade** that runs over
already-extracted claims and consolidated beliefs to surface integrity
defects the schema-level enforcement cannot reach: claims whose cited
evidence does not establish them, stability-class assignments that
overstate the evidence span, projection-level outputs (Phase 5 answers)
that cite unsupported claims. It is a synthesis-stage check, not a new
extraction pipeline. It is not a hard gate; it produces structured
findings that downstream phases (gold-set authoring, the post-Phase-3
adversarial round, lane-compiler readiness) consume.

This is an idea-capture RFC, not an accepted architecture decision.

## Background

Phase 3 already enforces a strong set of integrity invariants at the
schema layer:

- `claims.evidence_message_ids` is non-empty (`cardinality > 0` CHECK)
  and a subset of the parent segment's `message_ids` (insert trigger).
  This blocks the ARIS "model-derived references" failure at structure
  level: a claim cannot cite a UUID that wasn't in the segment.
- `belief_audit` is append-only and the consolidator's transition API
  (D052) guarantees every belief UPDATE is paired with an audit row in
  the same transaction.
- D058 per-claim salvage rejects schema-invalid claims and records them
  in `claim_extractions.raw_payload.dropped_claims`.
- D049 makes the active claim set deterministic: only the latest active
  `claim_extractions` row per segment feeds the consolidator.
- D056 aggregates belief confidence as `MEAN` over contributing claims
  with full distribution preserved in `belief_audit.score_breakdown` —
  no MAX-collapse that would hide spread.

What schema-level enforcement does **not** cover:

1. **Content fidelity of evidence.** The trigger checks the UUID is
   structurally valid; it does not check whether the message text at
   that UUID actually establishes the claim. A claim of the form
   `(subject="user", predicate="lives_in", object="Boulder")` with
   `evidence_message_ids = [m1, m2]` passes the trigger even if m1 and
   m2 contain only a passing mention of Colorado weather.
2. **Stability-class scope.** A claim with `stability_class='identity'`
   asserts something durable; if the evidence is a single message from
   a single date, the class is over-claiming. The schema accepts any
   class the extractor emits.
3. **Self-referential confidence.** Per-claim `confidence` is whatever
   the LLM emitted. There is no check that high-confidence claims
   correlate with strong evidence.
4. **Projection-level reporting fidelity.** Phase 5 `context_for` and
   any future narrative answer surface synthesizes claims into prose.
   No machinery checks whether each factual statement in that prose
   maps back to a supported claim or directly to raw evidence.

The first three failure modes correspond to what ARIS calls *phantom
results*, *scope inflation*, and *self-normalized scores* respectively.
The fourth corresponds to ARIS's Stage 3 *paper-claim audit* — the
final-output consistency check.

These are exactly the failure modes that
`HUMAN_REQUIREMENTS.md` § "refusal of false precision" forbids: a
biographical projection that *looks* well-grounded but whose grounding
chain has a broken link is the project's namesake failure mode.

## Problem

Step 6 (post-claims/beliefs adversarial round) and Step 9 (gold set
against consolidated corpus) on the roadmap are the two places where
projection quality gets stress-tested. Both currently lack an automated
substrate to feed them.

- The adversarial round needs a structured findings document to react
  to, not a raw claims dump. Without one, reviewers spend the round
  rediscovering integrity defects that should have been pre-flagged.
- Gold-set re-extraction cycles need a per-claim verdict so an
  `expected_fact` failure can be diagnosed: was the claim missing,
  present-but-mis-classified, or present-but-evidence-doesn't-support?
- The lane compiler (RFC 0016) and `context_for` will consume beliefs
  as load-bearing inputs. The schema enforces shape; nothing currently
  enforces *content fidelity* before that consumption begins.

This RFC proposes an automated audit cascade that produces those
findings as structured, versioned artifacts derivable from raw evidence
plus claims plus beliefs.

## Proposal

The cascade has three stages, each independently invocable, each
appending append-only rows to a new `claim_audits` table. None of the
three stages is a gate at the schema level; verdicts propagate as
status fields that downstream consumers (gold-set runner, lane
compiler, Phase 5 ranking) can read.

### Stage 1: Extraction-integrity audit

**Input.** A `claim_extractions.id` (or a sample drawn from a
`(extraction_prompt_version, extraction_model_version)` pair).

**Check.** A reviewer model from a different local family than the
extractor reads the segment's raw messages and the extractor's
`raw_payload`, and verifies that the integrity-failure-mode catalog is
clean:

1. **Evidence-trace integrity.** For each claim, do the messages at
   `evidence_message_ids` actually contain the asserted subject /
   predicate / object? Verdict: `trace_ok` / `trace_partial` /
   `trace_broken`.
2. **Stability-class span fit.** Is the asserted `stability_class`
   consistent with the evidence span? An `identity` claim from a single
   message on a single date should be flagged. Verdict: `class_ok` /
   `class_overclaim` / `class_underclaim`.
3. **Confidence calibration.** Coarse only: was a claim with
   `confidence > 0.8` flagged `trace_broken`? Verdict per-claim:
   `confidence_consistent` / `confidence_inflated`.
4. **Predicate-vocabulary fit.** Did the extractor route a fact through
   a predicate whose `cardinality_class` (D050) is wrong for the fact
   shape? E.g., a multi-current real fact emitted under
   `single_current`. Verdict: `predicate_ok` / `predicate_misrouted`.
5. **Scope inflation.** Did the claim generalize beyond the temporal
   window the segment covers? Verdict: `scope_ok` / `scope_inflated`.

**Output.** A `claim_audits` row per audited claim with stage=`1`,
plus a `claim_extractions_audit` summary row aggregating per-extraction
counts.

**Sampling.** Stage 1 runs on (a) a random sample per
`(extraction_prompt_version, extraction_model_version)` pair, (b) the
full set of claims contributing to any belief that
`/audit-belief <belief_id>` invokes, (c) any claim flagged by Stage 3.

The advisory bit: Stage 1 does not block; the `claim_extractions` row
is not edited. Status propagates downstream (Stage 2 reads Stage 1
findings).

### Stage 2: Claim-to-evidence verdict (claim ledger)

**Input.** A `claim_id` plus its Stage 1 audit row (if any).

**Check.** Independent of the extractor's emitted `confidence`, assign
each claim a verdict drawn from `{supported, partial, invalidated}`:

- `supported` — Stage 1 traces clean; cited evidence contains a clear,
  unambiguous instance of the asserted predicate-object on the asserted
  subject.
- `partial` — Stage 1 finds one or more weak axes (e.g., trace partial,
  class overclaim, scope inflated) but the core fact is grounded.
- `invalidated` — Stage 1 finds `trace_broken` or the cited evidence
  contradicts the claim.

**Status propagation rule.** A Stage 1 finding of `trace_broken`,
`class_overclaim` (when the class is `identity`), or `scope_inflated`
(when it crosses a year boundary) **cannot be marked `supported` in
Stage 2**. The Stage 2 reviewer can downgrade further but cannot
upgrade past Stage 1's hard ceilings. This is the operational form of
ARIS's "Stage 1 fail prevents Stage 2 fully-supported" invariant
adapted to engram's specific failure modes.

**Output.** A `claim_audits` row with stage=`2`, verdict, and
`audit_reasons[]`.

**Belief impact.** Beliefs that have at least one contributing claim
in `invalidated` enter a new soft state — they remain `candidate` per
D044, but `belief_audit.score_breakdown` records the
`audit_invalidated_claim_count` so Phase 4's review queue can
prioritize them. No automatic demotion: per D044, no auto-promotion
**or** auto-demotion in V1; the audit produces a signal, not a
transition.

### Stage 3: Projection-claim audit

**Input.** Any projection-level output that synthesizes claims into
prose: a Phase 5 `context_for` response, a future lane-compiler
output, an exported narrative. The output must carry inline claim
references (a `(claim_id, span)` mapping the audit can join on; the
exact format is an open question — see below).

**Check.** A **fresh-context** reviewer (new model session, no prior
conversation history, the engram-local analog of ARIS's "fresh thread")
reads the projection prose plus the cited claims plus, where it
matters, the raw evidence. Per factual statement, it verifies:

1. **Existence** — the cited `claim_id` resolves to a claim whose
   Stage 2 verdict is at least `partial`.
2. **Metadata correctness** — the projection's framing of *who*,
   *when*, and *where* matches the underlying claim's subject, the
   `observed_at` of supporting evidence, and the `privacy_tier` (no
   Tier-0 facts surfacing through a Tier-1 projection path).
3. **Context appropriateness** — the projection uses the claim to
   support the assertion the projection actually makes. This is the
   most diagnostic axis. A real, supported claim used to support a
   wrong assertion is the failure mode metadata-only checks miss.

**Output.** A `projection_audits` row with verdict per cited fact and
an aggregate verdict for the projection. The aggregate gates downstream
publication — e.g., the lane compiler will not commit a
`compiled_lane_output` whose Stage 3 aggregate is `failed`.

### Reviewer-independence protocol

Inherits from ARIS § 2.2 and adapts to local-only operation:

- **Reviewer reads source artifacts directly.** The audit harness
  passes file-paths (or DB row references) to the reviewer; the
  extractor / consolidator / projection-emitter must not pre-summarize
  the artifact. Otherwise the reviewer assesses the executor's
  framing, not the underlying work — and shared-error risk goes up.
- **Cross-family pairing where possible.** The reviewer model must come
  from a different local model family than the extractor. With local-
  only constraint, "family" means a different lineage among locally
  hosted runtimes (e.g., a Llama-derived reviewer auditing a Qwen-
  derived extraction). This is a weaker decoupling than ARIS's
  cross-vendor pattern; see the *Honest limitation* paragraph below.
- **Fresh context for Stage 3.** Stage 3 always opens a new model
  session. Stages 1 and 2 may reuse a session within a batch but must
  not carry context across audit batches.

### Failure-mode taxonomy

The cascade's audit_reason vocabulary is a fixed enum, seeded from the
ARIS catalog and adapted to engram. Stored in a new
`audit_reason_vocabulary` lookup table analogous to
`predicate_vocabulary` (D057), so the schema is a structural backstop:

| reason | stage | description |
|---|---|---|
| `trace_broken` | 1 | Cited evidence does not contain the claim. |
| `trace_partial` | 1 | Cited evidence partially supports the claim. |
| `class_overclaim` | 1 | `stability_class` overstates evidence span. |
| `class_underclaim` | 1 | `stability_class` understates evidence span. |
| `predicate_misrouted` | 1 | Predicate cardinality wrong for the fact. |
| `scope_inflated` | 1 | Claim generalizes beyond evidence's temporal window. |
| `confidence_inflated` | 1 | High-confidence claim with weak trace. |
| `evidence_synthesized` | 1 | Cited evidence appears to be model-generated rather than corpus-derived. |
| `value_mismatch` | 2 | Claim value disagrees with evidence content. |
| `numerical_mismatch` | 3 | Projection's number disagrees with claim. |
| `cite_invalid` | 3 | Projection cites a claim that doesn't exist or is invalidated. |
| `cite_misapplied` | 3 | Cited claim doesn't establish the projection's assertion. |
| `privacy_tier_leak` | 3 | Projection surfaces evidence above the claimed tier. |

The vocabulary is fixed in V1 and grows by new RFCs. Free-text
findings land in `claim_audits.raw_payload.notes` but do not affect
verdicts.

### Effort levels

The cascade exposes three preset run modes, set per invocation:

- **`sample`** — Stage 1 on a 1% random sample per
  `(prompt_version, model_version)` pair; Stage 2 derives verdicts only
  for sampled claims. Used as a continuous-integration-style check.
- **`belief-targeted`** — Stage 1 on the union of claims contributing
  to a named belief or set of beliefs; Stage 2 produces a per-belief
  `belief_audit_summary` row. Used by the gold-set runner when a
  test fails.
- **`full`** — Stage 1 over all claims under a given prompt version;
  Stage 2 over all claims; Stage 3 over a named projection batch.
  Used at the post-Phase-3 adversarial round (Step 6) and at lane-
  compiler readiness.

These mirror ARIS's `lite` / `balanced` / `max` presets but are named
operationally rather than by relative cost — engram operators want to
say what they're auditing, not how much compute they're willing to
spend.

## Schema additions

A new migration `migrations/00X_claim_audits.sql` adds three tables.
None modify existing claim, belief, or audit shapes — the cascade is
strictly additive.

`audit_reason_vocabulary`:

- `reason TEXT PRIMARY KEY` — the enum value (see table above).
- `stage SMALLINT NOT NULL CHECK (stage IN (1, 2, 3))`.
- `description TEXT NOT NULL`.
- `precludes_supported BOOLEAN NOT NULL DEFAULT FALSE` — when TRUE on
  a Stage 1 reason, no Stage 2 verdict can be `supported` while this
  reason is present.

`claim_audits`:

- `id UUID PK DEFAULT gen_random_uuid()`.
- `claim_id UUID NOT NULL REFERENCES claims(id)`.
- `stage SMALLINT NOT NULL CHECK (stage IN (1, 2))`.
- `verdict TEXT NULL` — Stage 2 only; one of `supported` / `partial`
  / `invalidated`. NULL on Stage 1 rows.
- `audit_reasons TEXT[] NOT NULL DEFAULT '{}'` — references
  `audit_reason_vocabulary.reason`. Per-row trigger validates
  membership and stage match.
- `auditor_model_version TEXT NOT NULL`.
- `auditor_prompt_version TEXT NOT NULL`.
- `audited_at TIMESTAMPTZ NOT NULL DEFAULT now()`.
- `raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb`.
- Append-only — no UPDATE, no DELETE. The "latest active audit per
  (claim_id, stage)" is `MAX(audited_at)` at query time.
- Indexes: `(claim_id, stage)`, GIN on `audit_reasons`,
  `(auditor_model_version, auditor_prompt_version)`.

`projection_audits`:

- `id UUID PK`.
- `projection_kind TEXT NOT NULL` — e.g., `context_for`, `lane_output`.
- `projection_ref TEXT NOT NULL` — opaque identifier the projection
  emitter chooses (a query log id, a lane output id).
- `cited_claim_ids UUID[] NOT NULL` — projections that don't cite
  claims cannot be audited; the emitter must produce citations. Phase
  5 design implication: every `context_for` response carries inline
  `claim_id` annotations.
- `verdict TEXT NOT NULL CHECK (verdict IN
  ('clean','warnings','failed'))`.
- `audit_reasons TEXT[] NOT NULL DEFAULT '{}'`.
- `auditor_model_version TEXT NOT NULL`.
- `auditor_prompt_version TEXT NOT NULL`.
- `audited_at TIMESTAMPTZ NOT NULL DEFAULT now()`.
- `raw_payload JSONB NOT NULL` — per-fact verdicts.
- Append-only.
- Indexes: `(projection_kind, projection_ref, audited_at DESC)`,
  GIN on `cited_claim_ids`.

No changes to `claims`, `beliefs`, `belief_audit`, or
`claim_extractions`. Verdicts are read-side joins, not column updates.

## Cross-cutting properties

- **Local-only execution.** All audit reviewer calls go through the
  same local LLM endpoint as the extractor (D020). No cross-vendor
  cloud routing. This is enforced at the harness level — there is no
  cloud bridge in the audit code path.
- **Insert-only audit rows.** `claim_audits` and `projection_audits`
  are append-only. Re-auditing a claim under a new auditor version
  inserts a new row; the prior row remains for diff and replay.
- **Versioning carry.** Every audit row records
  `auditor_model_version` and `auditor_prompt_version`. The auditor
  prompt is governed under the same versioning contract as the
  extractor prompt (RFC 0017 Part 1).
- **Privacy carry.** Audit rows inherit the privacy tier of the
  audited claim (or the highest tier among cited claims for a
  projection audit). The audit itself does not leak: it runs locally,
  writes locally, and surfaces only to local consumers.
- **Idempotency.** `engram audit --rebuild` produces a structurally
  equivalent active audit set under fixed model and prompt versions
  (the D055 analog for audits).

## Honest limitation: cross-family decoupling under local-only

ARIS's strongest evidence for the audit cascade comes from cross-vendor
pairings (Claude executor / GPT reviewer). The argument: same-family
models share inductive biases, so generator and validator miss
correlated errors. Engram's local-only constraint cuts that lever:
locally-hostable models cluster in a smaller phylogenetic tree (Llama,
Qwen, Mistral, Phi, Gemma) and several share base-model lineage.

The cascade still produces value in this setting:

- Schema-level integrity checks (Stage 1 verdicts 1, 4, 5) are
  largely structural and don't rely on the reviewer "thinking
  differently" — they rely on the reviewer reading raw evidence the
  extractor abstracted past.
- Fresh-context isolation (Stage 3) breaks confirmation-bias chains
  even with same-family models.
- Stage 2 verdicts are weaker than ARIS's: a Llama reviewer auditing
  a Llama-finetune extractor will share more biases than a GPT/Claude
  pair.

This RFC proposes the cascade despite the weaker decoupling, because
the alternative is no automated content-fidelity check at all. A
follow-up RFC should evaluate whether multi-runtime quantization,
cross-prompt-context auditing, or temperature-adversarial pairings
recover any of the lost decoupling. This is recorded as an open
question, not a blocker.

## Proposed Decisions (require DECISION_LOG entries before build)

1. **The audit cascade is advisory in V1, not a gate.** No
   `claim_audits` row blocks extraction, consolidation, or `current_
   beliefs` exposure. Verdicts surface as joinable status used by
   gold-set runners, the adversarial round, and Phase 4's review
   queue. Rationale: auto-blocking based on locally-run LLM verdicts
   risks new-failure-mode introduction (reviewer false negatives
   silencing real claims) and contradicts D044's "no auto-promotion
   or auto-demotion" stance.
2. **Stage 1 reasons listed `precludes_supported = TRUE` form a hard
   ceiling on Stage 2 verdicts.** The named list at vocabulary seed
   time is `trace_broken`, `evidence_synthesized`, and
   `predicate_misrouted` — verdicts that admit no "partially OK"
   reading.
3. **Stage 3 requires inline claim citations from projection
   emitters.** Phase 5 `context_for` and any future narrative output
   must carry `(claim_id, span)` annotations. A projection without
   citations cannot be audited and is treated as `failed` at Stage 3.
4. **Audit reviewer is a different local model family from the
   extractor when at all possible.** When only one local family is
   available, the audit still runs and the audit row records a
   `same_family_warning` flag for downstream visibility.
5. **`audit_reason_vocabulary` is FK-enforced and grows only by
   RFC.** Mirrors D057's pattern for `predicate_vocabulary`.

## Open Questions

1. **Inline citation format for projections.** What does a Phase 5
   `context_for` response look like with claim citations? Candidate
   formats: (a) Markdown footnote references; (b) inline JSON
   sidecars; (c) a structured-output schema with `claim_id` per
   asserted span. Affects Phase 5 prompt design.
2. **Sampling rate for `sample` mode.** 1% is a placeholder. What
   sample size gives stable per-extractor-version verdict precision?
   The extractor currently runs ~hundreds of segments per prompt
   bump; 1% of that is ~5 audits, too small to spot rare-failure-mode
   regressions. May need to be absolute count rather than percentage.
3. **Belief-level rollup.** Should `beliefs` carry a derived
   `audit_status` column (computed from contributing-claim verdicts)
   or only expose it through a view? Column = faster read, requires
   transition discipline; view = pure derivation but slower under
   the load Phase 5 will produce.
4. **Confidence-calibration verdict precision.** Stage 1 verdict 3
   (`confidence_inflated`) is currently coarse: high-confidence claim
   plus weak trace. Should it be a continuous score or stay binary?
   Continuous adds value for downstream calibration but loads the
   reviewer with a regression-style task that local LLMs do poorly.
5. **Projection-audit batching.** Each `context_for` call producing a
   per-call audit is expensive. Batch the audit nightly? On every
   call? On any call whose projection_kind is in a sensitive set
   (e.g., `lane_output`)? Cost-model-dependent; defer to first
   measurement.
6. **Cross-runtime auditor pairings.** Beyond cross-family, do
   different quantizations of the same base model count as
   sufficient decoupling? (E.g., Q8 reviewer auditing Q4 extractor.)
   Unclear theoretically; needs a small study.
7. **Promotion path for Stage 3 to gate the lane compiler.** This
   RFC proposes Stage 3 as advisory in V1, but the lane compiler
   (RFC 0016) is the natural place to make it a gate. Should that
   transition happen in this RFC or a follow-up?
8. **Pre-audit smoke check.** Should `engram audit` refuse to run if
   the auditor model is the same family as the extractor model and
   no override flag is set? Strict default is safer; lenient default
   is more usable when only one family is locally available.

## Risks

- **Reviewer false-negative drift.** The local audit reviewer may
  systematically miss a class of failure modes (e.g., subtle
  numerical mismatches). Without a gold set of *audited claims with
  known verdicts*, there's no ground truth to detect this. Step 5's
  gold set is biographical, not audit-quality. A separate audit gold
  set is implied future work.
- **Audit-noise saturation.** A flaky reviewer model emitting
  `trace_partial` on every claim turns the cascade into noise.
  Verdict-distribution monitoring per `auditor_model_version` is
  required from day one to catch this.
- **Same-family blind spot.** Acknowledged in the *Honest limitation*
  section. The cascade may produce false confidence about content
  fidelity it cannot actually verify.
- **Schema-creep into projection emitters.** Stage 3 requires
  projection citations. If Phase 5 design lands without them, Stage
  3 is dead weight until refactored. This RFC proposes citations as
  a non-negotiable Phase 5 design input; if Phase 5 RFC declines,
  Stage 3 must be revisited.
- **Cost.** Stage 1 on a full extractor pass is N × extractor-cost
  (one auditor pass per claim). Local compute, but real wall-clock.
  The `sample` / `belief-targeted` / `full` mode separation exists
  precisely to keep this bounded; abuse is possible.

## Promotion Path

If accepted:

1. Open DECISION_LOG entries for the five Proposed Decisions above
   (numbering assigned at acceptance time).
2. Resolve the Open Questions in those entries or in follow-up RFCs.
   Open Question 1 (citation format) is a Phase 5 design input;
   resolution should land before any Phase 5 build prompt.
3. Add a row to `BUILD_PHASES.md` for the audit cascade. Likely slot:
   between Phase 3 (currently shipped) and Phase 4 (review queue), so
   the cascade can produce findings the review queue consumes. Not
   blocking on Phase 3 close.
4. Schedule the audit cascade build prompt after Step 5 (gold set
   authoring) so the gold set provides a sanity check on Stage 2
   verdicts — gold-set `expected_facts` failures should correlate
   with Stage 2 `invalidated` / `partial` verdicts on the relevant
   claims.
5. Run the audit cascade `full` mode against the consolidated V1
   corpus before Step 6 (post-claims/beliefs adversarial round) so
   the round operates on a structured findings document rather than
   raw claims.

## Non-goals

- Replacing Step 6's adversarial round. The cascade produces input
  for the round; reviewers still read principles, schema, and
  inventory.
- Changing the claim, belief, or claim_extractions schema. The
  cascade is strictly additive — three new tables, no column
  additions to existing tables.
- Auto-blocking, auto-rejecting, or auto-demoting beliefs based on
  audit verdicts. D044's "no auto-promotion / no auto-demotion"
  stance holds; verdicts are read-side joinable signals.
- Cloud-routed cross-vendor reviewer access. ARIS's strongest version
  uses GPT/Claude/Gemini APIs. Engram's local-only constraint forbids
  this; the *Honest limitation* section is explicit about the cost.
- Citation audit for external publications (`\cite` resolution
  against DBLP / arXiv). ARIS includes this; engram has no external
  citation surface in V1.
- Adversarial probing or falsification (F004 — deferred). The
  cascade is a content-fidelity check, not a probe for absent
  claims.
- Building an audit gold set. Implied future work; not in scope for
  this RFC.
