# V1 Principle Review - Codex

Date: 2026-04-28

Note on scope: `HUMAN_REQUIREMENTS.md` contains six `## Why ...` sections, not
seven. I am treating `The distinguishing property: time-indexed biography` as
the seventh foundational principle because the document calls it the spine of
the system. I am not proposing a new principle.

## 1. Per-principle assessment

### 1. Time-indexed biography

**Classification: Honors, with a V1 naming gap.**

V1 honors the temporal spine by making `beliefs` bitemporal:
`valid_from`, `valid_to`, `observed_at`, `recorded_at`, `superseded_by`, and
close-and-insert on contradiction. `context_for` also defaults to current
beliefs while allowing historical beliefs when the user asks for history or
when historical evidence is highly relevant and explicitly labeled.

The naming gap is that V1 is framed almost entirely around AI-conversation
context. That is acceptable for V1, but the architecture draft should say
explicitly that V1 validates the schema for a future biography and is not the
biography itself. Otherwise the narrow source list can be misread as a product
scope decision.

**Smallest delta:** add a short V1 invariant: "V1 ingests a narrow source set,
but every accepted fact must be representable as a temporally valid
biographical belief; later domains add sources and predicates, not a new
memory model."

### 2. Local-first is load-bearing

**Classification: Silent in V1; partially covered by SECURITY.**

V1 does not propose cloud services, but it also does not explicitly require
local-only segmentation, extraction, embeddings, evaluation, or reranking.
Given the principle, this cannot remain implicit. "LLM-driven" and
"embedding cache" must mean locally executed model calls only.

This is not a V1 feature expansion. It is a constraint on every V1 batch job
and serving job.

**Smallest delta:** add a V1 non-negotiable implementation constraint:
segmentation, claim extraction, belief consolidation, embeddings,
`context_for`, eval runs, and any offline experiments use local models only;
no hosted LLM, hosted embedding API, crash telemetry, analytics, or SaaS sync is
allowed.

### 3. Corpus access and network egress are kept separate

**Classification: Honors structurally; enforcement is under-specified in V1.**

V1's `context_for(conversation)` shape is a pure read-side compiler. It emits a
bounded context package rather than giving the action-taking assistant direct
database access. That honors the principle's core separation.

The draft does not say that the read-side process has no network egress, nor
that the network-using process cannot query engram. `SECURITY.md` names this,
but V1 should reference it because it affects process boundaries and test
setup.

**Smallest delta:** add a build-order gate before MCP exposure: run
`context_for` inside the no-egress engram-reading process, expose only bounded
IPC/stdout responses, and verify that the MCP/action process has no direct
database credentials or filesystem access to the corpus.

### 4. Raw data is sacred

**Classification: Violates in the correction path; honors the rest.**

V1 strongly honors immutable raw evidence, rebuildable derivations,
`evidence_ids NOT NULL`, prompt/model versions on beliefs, non-destructive
re-segmentation, and SHA256-keyed embeddings.

The violation is in HITL correction wording:

> Reviewer actions write back to `beliefs` and `belief_audit`.

Accept/reject/promote status changes can write to `beliefs` and
`belief_audit`. A correction cannot. Under the principle, a user correction is
raw evidence. If the user says "that fact is wrong; the truth is X," that must
land as a new `captures` row and only then supersede the bad belief through the
normal evidence-backed path.

**Smallest delta:** define review-queue `correct` as:

1. Insert immutable `captures` row with `capture_type = 'user_correction'`,
   the correction text, timestamp, and `corrects_belief_id`.
2. Create a new candidate/provisional belief whose `evidence_ids` include that
   capture.
3. Supersede or reject the old belief via `belief_audit`.

No accepted belief should ever be created solely from a UI correction payload.

### 5. Eval is the only objective oracle

**Classification: Violates in the eval-gate subset design.**

V1 honors the principle by requiring a hand-written gold set and gating
full-corpus consolidation on eval results. The problem is the proposed gate:

> Eval set runs on a small ChatGPT subset (approximately 100 conversations)
> before full-corpus consolidation.

That is a useful smoke test, but it is not a valid gold-set gate for a corpus of
roughly 5,000 AI conversations across multiple sources. A random 100-300
conversation subset will omit most specific people, projects, years, and
decisions referenced by the gold prompts. The eval can fail because evidence is
absent, not because retrieval or consolidation is bad.

The tiered alternative correctly identifies the gap. The right structure is:

1. **Smoke gate:** about 100 conversations, preferably random plus known edge
   cases. Gates catastrophic failures: parser errors, missing evidence ids,
   obviously broken segmentation, invalid temporal fields, runaway unsupported
   beliefs. It should not be expected to answer broad gold-set prompts unless
   those prompts are authored against this exact subset.
2. **Gold-target gate:** a target-closed, stratified subset large enough to
   contain the evidence and distractors for the gold set. The proposed
   1,000-2,000 conversations is reasonable if the gold set spans many people,
   projects, years, stale facts, and source systems. The subset should be
   stratified by the prompts' actual targets, not merely by source/date.
3. **Full AI-conversation corpus:** run only after tier 2 passes. Re-run the
   same gold set against the full corpus and require no regression in precision,
   stale fact rate, unsupported belief rate, and token waste. Full AI
   conversation coverage is still not full biographical coverage.

The gold set should be authored differently. Each prompt needs metadata:
target entities, target projects, target years, expected evidence ids or source
locators, must-not-include stale facts, and required distractor classes. A
smaller stratified subset can be sufficient only if it is target-closed:
every prompt's required evidence, temporal counter-evidence, and plausible
distractors are included. Random sampling is the wrong tool for the gold gate.

**Smallest delta:** replace V1 steps 14-15 with smoke gate -> target-closed
gold gate -> full AI-corpus consolidation. Keep the 100-conversation gate, but
rename it smoke validation and stop treating it as the gold-set pass/fail gate.

### 6. Adversarial review is a permanent feature

**Classification: Violates by omission of required schema.**

The principle explicitly says adversarial sweeps can be deferred for V1, but
the schema must accommodate them now. It names `contradictions`, `belief_audit`,
and immutable raw store as the required infrastructure.

V1 has `belief_audit` and immutable raw evidence. It also has an "open
contradictions" context lane and an `Uncertain / Conflicting` context section.
But `contradictions` is missing from `Minimal Schema Primitives`, so the lane
has no canonical backing table.

This does not require re-opening the rejected Stash-style schema. A small
contradiction table is not the same as adopting the old 20-table pipeline.

**Smallest delta:** add a minimal `contradictions` table in V1 and create rows
during belief consolidation when two evidence-backed claims/beliefs conflict.
Adversarial sweeps themselves can remain post-V1, but their output shape should
exist from the first migration.

### 7. Refusal of false precision is a contract

**Classification: Silent/incomplete.**

V1 has the main ingredients: `confidence`, `status`, temporal validity,
stale penalties, historical labeling, raw evidence snippets, context feedback,
and an uncertainty/conflict section. That is directionally right.

The incomplete part is the serving contract. The V1 `context_for` shape does
not require confidence and provenance to be emitted alongside each included
belief, and it does not say what happens when the system has no evidence for a
question. Ranking by confidence is not enough; confidence must survive into the
context package so the downstream model can weight it. Missing evidence should
produce an explicit "no data / insufficient evidence" result when the user asks
about something engram cannot support.

**Smallest delta:** define a context item schema with `text`,
`belief_id/segment_id`, `confidence`, `valid_from`, `valid_to`,
`temporal_label`, `evidence_ids`, and `uncertainty_reason`. Add a
`no_data`/`insufficient_evidence` output type for relevant requested topics
where candidate retrieval produces no supported memory.

## 2. Schema or build-order additions

Concrete additions implied by the principles but missing or under-specified in
V1:

- Add `contradictions`:

```text
contradictions
  id
  subject_entity_id
  predicate
  belief_id_a
  belief_id_b
  claim_id_a
  claim_id_b
  evidence_ids
  contradiction_type
  status              -- open | resolved | false_positive | superseded
  detected_by         -- consolidation | user | adversarial_sweep
  model_version
  prompt_version
  created_at
  resolved_at
```

- Add correction-as-raw support to `captures`:

```text
captures
  capture_type        -- observation | task | idea | reference | person_note | user_correction
  corrects_belief_id
  raw_text
  recorded_at
  source = 'user'
```

- Add derivation-version columns below beliefs, not only on beliefs:

```text
segments.segmentation_model_version
segments.segmentation_prompt_version
claims.extraction_model_version
claims.extraction_prompt_version
embedding_cache.embedding_model_version
embedding_cache.embedding_dimension
embedding_cache.input_sha256
```

- Add context run storage for eval and feedback:

```text
context_runs
  id
  conversation_ref
  query_text
  compiler_version
  ranking_version
  created_at

context_items
  context_run_id
  section
  item_type           -- belief | segment | evidence_snippet | contradiction | no_data
  belief_id
  segment_id
  evidence_ids
  confidence
  valid_from
  valid_to
  temporal_label
  uncertainty_reason
  token_count
```

- Add explicit privacy/release fields before live context emission, even if all
  V1 imports default conservatively:

```text
beliefs.privacy_tier        -- default Tier 1 unless promoted
segments.privacy_tier
captures.privacy_tier
beliefs.posthumous_policy   -- inherit | release | posthumous_only | redact_on_death
```

- Add a source/domain marker so future biography domains are extensions rather
  than rewrites:

```text
sources.source_kind       -- chatgpt | obsidian | capture | future source kinds
beliefs.domain_tags       -- health, finance, relationship, project, identity, etc.
captures.domain_tags
```

- Replace the eval build order with:

```text
14. Smoke eval on approximately 100 conversations.
15. Gold-target eval on target-closed stratified corpus slice.
16. Gate: full AI-conversation consolidation only after tier-2 pass.
17. Re-run gold set on full AI-conversation corpus and check no regression.
18. Add Obsidian/capture or additional AI sources only behind the same source-specific gate.
```

If D013 remains settled as ChatGPT + Obsidian + capture for V1, apply the same
structure first to ChatGPT and repeat it when Claude/Gemini are admitted by the
revisit trigger. The eval principle does not require re-opening D013; it does
require that any source entering live memory pass a target-appropriate gate.

- Add a process-isolation build gate before MCP exposure:

```text
before step 12:
  verify engram-reading process has no network egress
  verify action/MCP process has no direct corpus filesystem or DB access
  verify context package is the only bridge
```

## 3. Security implications

Items to add or sharpen in `SECURITY.md` based on this review:

- Local-only model execution applies to every corpus-reading batch job:
  segmentation, extraction, embeddings, consolidation, eval, offline
  reranking experiments, and adversarial sweeps. It is not only a live-serving
  rule.
- No telemetry, crash reporting, analytics, remote tracing, or model-runtime
  phone-home from any process that can see raw corpus, derived beliefs, eval
  snapshots, or context packages.
- Model artifacts and embedding models need supply-chain controls: pinned
  versions, local checksums, reproducible download/import process, and no
  automatic model updates while connected to the corpus.
- Temporary files, prompt logs, model runtime caches, swap, eval snapshots, and
  context package archives must be treated as corpus data: encrypted, tiered,
  and excluded from cloud sync.
- `context_for` output is an explicit export. It must run through privacy-tier
  filtering, emit only Tier-2-eligible material by default, and record an audit
  row for what was released to the action-taking process.
- MCP exposure must bind locally and authenticate the caller. A local network
  service with unauthenticated `context_for` access is corpus access.
- Imported raw conversations and notes are adversarial input for extractors.
  Prompt-injection handling should cover raw corpus text, not only web/email
  tool output.
- User corrections are raw evidence and may themselves be sensitive. They need
  the same encryption, privacy-tier, and posthumous handling as any other
  capture.
- Privacy-tier defaults need to be conservative before ingestion. Health,
  finances, legal, relationships, beliefs, conflicts, and identity facts found
  inside AI conversations should default to Tier 1 unless explicitly promoted.
- Logs must not contain raw prompts, raw evidence snippets, or full context
  packages unless the log row is encrypted and tiered as the underlying data.
- Backups must include vector indexes, derived tables, audit logs, and eval
  artifacts under the same no-SaaS, user-held-key rule as raw data.

## 4. Position changes

- **Eval gate:** Round 1 treated the approximately 100-conversation eval as the
  gate before full consolidation. I now think that is only a smoke gate. The
  principle that eval is the objective oracle makes absent evidence a fatal
  confounder: a perfect pipeline cannot answer gold prompts whose evidence was
  never included in the subset.
- **Adversarial review:** Round 1 put adversarial re-extraction sweeps in the
  research/experimental bucket. I still would not ship the sweeps as a V1
  product surface, but I now think their schema target must exist in V1. The
  missing `contradictions` table is a real V1 gap.
- **Review queue corrections:** Round 1 accepted a belief review queue with
  correct/reject/promote actions. The raw-data principle changes the correction
  semantics: correction is not a privileged belief edit. It is a new raw
  capture that causes belief supersession.
- **Local compute budget:** Round 1 was more conservative about avoiding costly
  offline passes. The principles make that the wrong default. Live context must
  stay concise and fast enough to use, but offline local compute should be spent
  where it improves provenance, temporal cleanup, contradiction detection, and
  eval quality.
- **Security as architecture:** Round 1 focused on schema and retrieval. The
  corpus/network separation principle makes process isolation part of V1
  architecture, not an implementation detail to fill in later.

## 5. Strongest residual concern

The strongest remaining issue is coverage accounting: V1 needs to know the
difference between "the fact is absent from this eval subset," "the fact is
present but retrieval failed," and "engram has no evidence anywhere." Without a
target-closed gold gate, context item provenance, and explicit no-data outputs,
the system can fail evals for the wrong reason and still violate refusal of
false precision after launch. Fixing that does not expand V1; it makes the V1
validation phase capable of telling truth from missing coverage.
