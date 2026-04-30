# Architecture Evolution Delta — Hot State + Staged Memory Fabric

Status: accepted direction, implementation staged
Date: 2026-04-29

## Purpose

This note integrates the 2026-04-29 architecture review without rewriting the
V1 plan around later-stage optimizations.

The working posture remains:

```text
1. Get raw data in.
2. Segment, embed, extract, and consolidate enough memory to be useful.
3. Ship a basic serving stack through MCP.
4. Evolve the serving path into a low-latency memory fabric as evidence
   accumulates.
```

Most of the review feedback is V1.5+ / V2 architecture. The one V1 change is
that async precompute of context packages is promoted from deferred option to
serving-path primitive. `context_for(...)` remains the primary product surface,
but it should be treated as a context compiler and cache-miss path, not as the
normal per-turn hot path.

In V1, "hot state" means versioned MCP-ready context snapshots. It does not
assume the consuming chat model is local or that Engram controls that model's
KV cache.

## Decision Delta

### Promote Async Hot State Into V1

The previous position deferred async precompute until live latency exceeded
tolerance. That is too late: the shape of the serving stack changes once the
system assumes each user turn can be preceded by a freshly compiled context
package.

V1 should instead ship a hybrid serving path:

```text
canonical store
  -> context_for compiler
  -> versioned context snapshots / hot state
  -> MCP serving path
  -> context_feedback
```

The live MCP tool may still call the compiler synchronously on a cold miss, but
the preferred path is to serve a current snapshot and refresh asynchronously for
the next turn.

### Consumer Modes

Engram has two distinct serving modes. They share the same canonical store and
snapshot compiler, but have different latency mechanics.

```text
Mode A: External frontier consumer
  - Claude / ChatGPT / Gemini / Cursor / other MCP client calls Engram.
  - Engram returns a compact, policy-filtered context snapshot over MCP.
  - Hot state lives in Postgres or a local cache as rendered text + ids.
  - No assumption of KV-cache residency, prefix caching, or model-server
    control.

Mode B: Local agent consumer
  - Engram and the chat model are co-resident on local hardware.
  - The same snapshot can be promoted into a stable system prefix.
  - Prefix / KV-cache optimization becomes possible through vLLM, SGLang,
    ik-llama, or a later local inference stack.
```

V1 targets Mode A first. Mode B is an optimization layer, not a prerequisite for
MCP utility.

### Keep The Rest Staged

The following review recommendations are valid, but should not block data
ingestion, Phase 2, or the first useful serving stack:

- multi-GPU microservice routing;
- prefix/KV-cache-aware model serving;
- deterministic TMS / ATMS belief environments;
- Hippocampal / spreading-activation graph retrieval;
- MemoryOS / MemOS-style lifecycle scheduler;
- negative-space memory beyond manual pinned facts;
- salience decay functions beyond the initial ranking features;
- Obsidian wiki write-back as a projection layer;
- model-side memory artifacts such as cartridges or latent stores.

Each remains a staged evolution track with explicit promotion criteria.

## Serving Model

`context_for(conversation)` remains the product surface, but the serving stack
should split compilation from delivery.

```text
user turn
  -> lightweight query/entity/task parse
  -> read hot state for session/project/user
  -> deliver rendered context package over MCP
  -> consuming model answers
  -> async refresh compiles next hot state
  -> feedback updates ranking/suppression signals
```

The hot state should initially be simple rendered text plus provenance ids. It
does not need a separate cache database in V1; a Postgres table is sufficient
until measurements prove otherwise.

Minimum V1 hot-state scopes:

```text
standing_user_state      identity, durable preferences, pinned facts
project_state            active project / goal context, when detectable
session_state            entities and topics from the current conversation
recent_signal_state      recent captures / notes / conversations
```

V1 can materialize these as context snapshots rather than adding separate
domain-specific state files. The important property is versioned, inspectable,
rebuildable derived state.

## Minimal Schema Additions For Phase 5

Add only what the basic serving stack needs:

```text
memory_events
  id
  event_type
  aggregate_type
  aggregate_id
  memory_epoch
  payload
  created_at

context_snapshots
  id
  scope_type              user | project | session | eval
  scope_key
  memory_epoch
  compiler_version
  prompt_hash
  rendered_text
  token_count
  source_belief_ids
  source_segment_ids
  source_entity_ids
  expires_at
  created_at
```

Do not add the full memory-fabric schema in V1. Tables such as
`belief_justifications`, `belief_conflicts`, `retrieval_salience`, and
`hot_entities` are reserved for later promotion when the relevant subsystem is
actually implemented.

## Phase Mapping

### Phase 1 / 1.5 — Raw Ingestion

Unchanged. The first step is still conversation history ingestion across
ChatGPT, Claude, and Gemini, then expansion into Obsidian and captures.

No serving optimization matters until the corpus exists.

### Phase 2 — Segmentation + Embeddings

Unchanged. Topic segments remain the embedding and extraction unit.

The only additional consideration is to make segment ids stable enough for
future snapshots to cite them. Snapshot invalidation can be coarse at first:
any new active segment generation increments the memory epoch for affected
scopes.

### Phase 3 — Claims + Beliefs

Unchanged for V1. Bitemporal beliefs, provenance, and audit logs remain the
core correctness primitive.

Deterministic belief revision via TMS / ATMS is not a V1 requirement. The V1
schema should not prevent it, but it should not absorb it yet.

### Phase 4 — Entities + Review

Mostly unchanged. Entity ids become useful invalidation keys for context
snapshots.

The review queue should emit memory events when beliefs are accepted, rejected,
corrected, or promoted to pinned.

### Phase 5 — Serving

Phase 5 now includes a minimal hot-state layer:

```text
context_for candidate generation
ranking + section packing
context snapshot write
MCP reads snapshot or compiles on cold miss
context_feedback capture
async refresh after feedback / capture / belief change
```

The smoke gate should validate both paths:

- cold compile returns a valid context package;
- warm snapshot returns the same package without recomputing every lane;
- a belief/capture/review event invalidates or refreshes the affected snapshot.

## Multi-GPU Evolution Path

The four-GPU architecture should be introduced after the basic serving loop is
measured, not before.

Initial local deployment can be:

```text
GPU 0: foreground assistant inference
GPU 1: batch segmentation / extraction / async context compile
GPU 2: idle or eval/adversarial worker
GPU 3: idle or second inference replica
```

Later target topology:

```text
GPU 0: foreground inference
GPU 1: context compiler / state maintenance / reranker experiments
GPU 2: segmentation + information extraction
GPU 3: belief revision + graph clustering + adversarial sweeps
```

The stable interface between these stages is not GPU assignment. It is the event
contract: raw/capture/belief/review/feedback events produce derived-state
refresh jobs.

## Promotion Criteria For Later Tracks

| Track | Promotion Trigger | First Artifact |
|-------|-------------------|----------------|
| Prefix / KV cache | Local agent mode shows repeated stable context dominates prefill latency | serving benchmark + model-server note |
| TMS / ATMS belief revision | Supersession chains fail on multi-evidence conflicts | belief-revision ADR |
| Spreading activation / HippoRAG-style retrieval | Fixed 1–2 hop entity expansion is noisy or low-recall | graph retrieval experiment |
| Salience decay | Ranking overuses stale but still-valid facts | retrieval feature migration |
| Negative-space memory | Repeated omissions of important absences | negative-space schema note |
| Obsidian wiki projection | Review queue fails to expose cross-belief incoherence | projection-only wiki ADR |
| Memory scheduler | Background jobs compete or memory lifecycles become implicit | scheduler service design |

## Non-Negotiable Boundaries

- Raw evidence remains immutable.
- Context snapshots are derived projections, never canonical memory.
- Obsidian write-back, when introduced, is also a projection.
- Generated projections are not re-ingested as raw evidence unless a human
  explicitly captures an edit as evidence.
- The engram-reading process remains no-egress.
- `context_for` remains inspectable: every emitted item carries provenance and
  confidence.

## Practical Next Step

Continue the current build order through Phase 2. Do not implement the hot-state
tables before the serving path exists.

When Phase 5 begins, build the simplest possible snapshot layer in Postgres and
measure:

```text
cold context_for latency
warm snapshot latency
snapshot token count
stale / wrong / irrelevant feedback rate
context token waste
consumer context-insertion cost where measurable
```

Only promote the larger distributed-memory architecture after those measurements
show which subsystem is actually hot.
