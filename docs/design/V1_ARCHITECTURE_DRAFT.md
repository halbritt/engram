# V1 Architecture Draft

Status: revised after round-1 synthesis (CONSENSUS_REVIEW.md, 2026-04-27)

This is the working target for the first useful version. It will be revised
again after the adversarial rounds.

## V1 Goal

Given a new AI conversation, produce a compact, useful, current personal
context package with evidence-backed memory.

The first version is successful if `context_for(conversation)` improves real
AI interactions without injecting stale, noisy, or unsupported personal
facts.

## Non-Goals For V1

- Full life graph completeness.
- Auto Obsidian wiki generation. (Replaced by a belief review queue.)
- Goal progress inference.
- Failure pattern inference.
- Hypothesis lifecycle.
- Causal-link mining.
- Higher-order pattern extraction.
- Broad graph algorithms in the live path.
- Synthesized facts becoming ground truth without raw evidence.
- Apache AGE / Neo4j / FalkorDB / Kuzu graph backend.
- LLM cross-encoder reranker in the live path.
- Bidirectional Obsidian sync.
- Bulk Evernote → Obsidian migration (per F008).

## Canonical Data Flow

```text
sources
  → conversations / notes / captures        (immutable raw evidence)
  → messages                                (immutable raw evidence)
  → segments                                (topic-segmented, embedded)
  → claims                                  (LLM-extracted, evidence_ids required)
  → beliefs                                 (bitemporal, status-tracked, stability-classed)
  → current_beliefs (view / materialized)
  → context_for(conversation)               (multi-lane compiler, sectioned output)
```

Episodes / messages / notes / captures are immutable. Re-segmentation and
re-extraction are non-destructive: new segment / claim / belief rows
supersede prior rows; nothing is overwritten in place.

## Derived Projections

```text
vector index
entity graph (relational entity_edges)
context packages / context snapshots
eval snapshots
review-queue surface (belief inspection)
```

Derived projections are rebuildable from canonical evidence-backed state.
Wiki pages, full-graph stores, advanced cache services, and
goal/failure/hypothesis tables are deferred. Minimal context snapshots are
part of the Phase 5 serving path per D025.

## Minimal Schema Primitives

```text
sources
conversations
messages
notes
captures
segments
claims
beliefs
entities
entity_edges
embedding_cache
memory_events
context_snapshots
context_feedback
belief_audit
contradictions
settings
```

## Belief Requirements

Accepted beliefs include:

```text
id
subject_entity_id
predicate
object_entity_id | value_text | value_json
valid_from
valid_to             (NULL = currently valid)
observed_at
recorded_at
extracted_at
superseded_by
status               (candidate | provisional | accepted | superseded | rejected)
stability_class      (identity | preference | project_status | goal | task | mood | relationship)
confidence
evidence_ids         (NOT NULL — at least one raw episode/message/note/capture id)
prompt_version
model_version
original_prompt_version
original_model_version
privacy_tier         (integer, default 1)
```

Invariants:

- `evidence_ids` NOT NULL on `accepted` beliefs.
- Beliefs are never UPDATEd on contradiction. The prior belief's `valid_to`
  is closed; a new row is inserted with the new value and a `superseded_by`
  back-pointer.
- `belief_audit` rows are written on every state transition.

## Vector Index Policy

- Embed: topic segments and accepted beliefs (text form).
- Do not embed: raw single turns, full conversations, or unsegmented notes.
- Raw messages remain in Postgres for provenance and rendering only — not
  in the vector index.
- Embedding cache is SHA256-keyed.

## Context_For Shape

```text
Standing Context           (~300-800 tokens — identity, active goals/projects, pinned facts)
Active Projects / Goals    (~700 tokens)
Relevant Beliefs           (~1200 tokens — current_beliefs filtered by query)
Recent Signals             (~600 tokens — last N days of activity)
Entity Context             (~900 tokens — mentioned-entity neighborhood, conditional)
Raw Evidence Snippets      (~1000 tokens — citations supporting Relevant Beliefs)
Uncertain / Conflicting    (only when topic-relevant)
Missing Data / Gaps        (~200 tokens — explicit "no data" when queried entities lack beliefs)
```

Each section has an explicit token budget. Defaults to current beliefs
(`valid_to IS NULL`); historical beliefs surface only when the conversation
asks for history or when an old belief scores high enough with explicit
historical labeling.

## Hot State / Context Snapshots

`context_for(conversation)` is the context compiler and cache-miss path, not
a mandatory full recompute before every user turn.

V1 hot state is MCP snapshot-first. For external frontier-model consumers
(Claude, ChatGPT, Gemini, Cursor, or any MCP client), Engram returns a compact
rendered snapshot and makes no assumption about KV-cache residency or system
prompt control. If a future local chat agent is co-resident with Engram, the
same snapshot can later be promoted into a stable prefix / KV-cache artifact.

Phase 5 ships a hybrid serving path:

```text
canonical store
  → context_for candidate generation
  → ranking + sectioned token packing
  → context_snapshots
  → MCP warm read or synchronous cold compile
  → async refresh after capture / review / feedback / belief change
```

Minimum snapshot scopes:

```text
standing_user_state
project_state
session_state
recent_signal_state
```

The first implementation can keep snapshots in Postgres. Separate cache
services, model-side prefix / KV cache management, and multi-GPU memory
workers are later optimizations, not V1 blockers.

## Candidate Lanes

```text
semantic belief search        (pgvector against belief embeddings)
semantic segment search       (pgvector against segment embeddings)
keyword / BM25 search         (Postgres FTS over segments + claims)
recent activity               (segments / claims by recorded_at)
active projects / goals       (manual capture, status=active)
mentioned entity neighborhood (entity_edges, 1-2 hop, conditional)
pinned profile facts          (curated standing context)
open contradictions           (only when subject is topic-adjacent)
missing data detection        (fires when queries yield zero/low-scoring results for known entities)
```

The mentioned-entity lane only fires when entity extraction on the running
conversation produces matches. Its inclusion in live context is gated on
eval results — ship live only if it improves precision.

## Live Ranking (v1)

Simple weighted scorer over candidate set:

```text
score =
    relevance
  * currentness
  * confidence
  * specificity
  * source_quality
  * recurrence
  * task_fit
  - redundancy
  - stale_penalty
```

`currentness` and `stale_penalty` are computed against `stability_class` —
identity beliefs get near-flat decay, transient beliefs decay fast. An LLM
cross-encoder reranker is an offline experiment, not part of v1 live serving.

## HITL Feedback (v1)

Two surfaces, both ship in v1:

1. **Belief review queue.** A CLI (or thin web view) that surfaces newly
   accepted beliefs for the user to accept / reject / correct / promote to
   pinned. This is the v1 substitute for wiki-as-control-plane. `accept` / `reject` / `promote` write back to `beliefs` and `belief_audit`. `correct` inserts a new immutable `captures` row as raw evidence, which then supersedes the bad belief via the standard extraction pipeline.
2. **`context_feedback`.** One-keystroke annotations on `context_for`
   outputs: `useful`, `wrong`, `stale`, `irrelevant`. Each annotation
   records the belief ids and segment ids that produced the offending
   section.

## Sources (v1)

- ChatGPT export (3,437 conversations + 388 project conversations across
  25 projects).
- Claude.ai conversation export (added in Phase 1.5 per D024).
- Gemini Takeout (added in Phase 1.5 per D024).
- Obsidian vault (read-only ingestion).
- MCP `capture` tool for live observations / tasks / ideas / references /
  person notes.

All three AI-conversation sources share the same `raw_evidence` schema;
`source_kind` (chatgpt | claude | gemini | obsidian | capture | future)
discriminates. Adding a source is parser work, not architectural work.

Deferred sources: bulk Evernote → Obsidian migration (per F008 trimmed).

Constraint: Engram makes no outbound network requests under any code path. Freshness via web search is explicitly out of scope.

## First Eval Harness

Land 25–50 hand-written prompts covering:

```text
current project continuation
past decision recall
person/entity recall
style preference recall
active goal support
failed-approach avoidance
historical self-state
stale fact suppression
```

Track:

```text
precision
recall of known-important memories
stale fact rate
unsupported belief rate
contradiction rate
token waste
human usefulness rating
```

The eval uses a Tiered Structure:
1.  **Smoke Test:** Runs on ~100 conversations to catch catastrophic pipeline failures.
2.  **Gold-Set Validation:** Runs on a 1,000-2,000 stratified, target-closed subset containing the actual entities, projects, and years referenced by the gold prompts. This is the true eval gate.
3.  **Full Corpus:** (3,400+ conversations) Proceeds only after Tier 2 passes without regressions.

## Build Order

```text
0.  Configure network-disconnected runtime (OS namespace/sandbox) for the engram-reading process. MCP server binds to 127.0.0.1.
1.  PostgreSQL + pgvector baseline.
2.  ChatGPT ingestion into immutable raw conversations / messages.
2.5 Run D026 pre-Phase-2 adversarial review and synthesize accepted deltas before
    segmentation + embeddings implementation.
3.  Topic segmentation (LLM-driven, batch, non-destructive).
4.  Segment embeddings.
5.  Claim extraction with evidence_ids.
6.  Belief consolidation: bitemporal validity + stability_class + status.
7.  Entity canonicalization + entity_edges.
8.  current_beliefs (materialized view).
9.  Belief review queue: accept / reject / correct / promote-to-pinned.
10. context_for candidate generation (multi-lane).
11. Ranking + sectioned token packing.
12. context_snapshots + memory_events for warm serving.
13. MCP exposure of context_for (warm read, cold compile fallback).
14. context_feedback capture (useful / wrong / stale / irrelevant).
15. Smoke eval harness on ~100 conversations.
16. Gold-set eval harness on target-closed stratified corpus slice (~1000-2000 conversations).
17. Gate: full-corpus consolidation only after tier-2 pass.
18. Add Obsidian as a source after evals stabilize.
```

Stages 3–8 are non-destructive: re-running them produces new rows that
supersede prior rows via `valid_to` and `superseded_by`. The pipeline is
fully resumable per `consolidation_progress` checkpoints.

## What Round 1 Cut From This Draft

Compared to the prior draft, the synthesis added:

- Belief review queue as a v1 build-order item (steps 9, 13).
- Explicit eval gate before full-corpus consolidation (step 15).
- `stability_class` and `prompt_version` / `model_version` as required
  belief fields.
- Vector index policy (segments + beliefs only; no raw turns).
- Live ranking formula.
- Explicit non-goals: AGE / Neo4j / FalkorDB / Kuzu, LLM reranker in the
  live path, multi-source ingestion, bidirectional Obsidian sync.
- Replacement of "consolidate claims into beliefs with temporal validity"
  with the bitemporal close-and-insert invariant.

## 2026-04-29 Delta

- D025 promotes async context snapshots / hot state into Phase 5.
- D026 adds a pre-Phase-2 adversarial gate before topic segmentation and
  embeddings implementation.
- `context_for(...)` remains the primary product surface, but the normal
  warm path should serve a versioned snapshot and refresh asynchronously.
- Larger memory-fabric optimizations remain staged. See
  [ARCHITECTURE_EVOLUTION_DELTA_2026_04_29.md](ARCHITECTURE_EVOLUTION_DELTA_2026_04_29.md).

Compared to the prior draft, the synthesis removed:

- Auto wiki writeback as a v1 product surface.
- Causal links, patterns, hypotheses, failures, goal progress inference
  from any v1 stage.
- Claude export and Gemini Takeout from the initial v1 source set. They were
  later restored by D024 after Phase 1 ingestion proved the parser shape and
  raw schema.
