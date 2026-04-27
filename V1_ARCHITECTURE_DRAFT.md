# V1 Architecture Draft

Status: draft pending consensus review

This is a working target for the first useful version. It should be revised after
`CONSENSUS_REVIEW.md` is filled and the adversarial rounds are complete.

## V1 Goal

Given a new AI conversation, produce a compact, useful, current personal context
package with evidence-backed memory.

The first version is successful if `context_for(conversation)` improves real AI
interactions without injecting stale, noisy, or unsupported personal facts.

## Non-Goals For V1

- Full life graph completeness
- Full automatic Obsidian wiki generation
- Goal progress inference
- Failure pattern inference
- Hypothesis lifecycle
- Causal-link mining
- Broad graph algorithms in the live path
- Letting synthesized facts become ground truth without raw evidence

## Canonical Data Flow

```text
raw sources
  -> messages / notes / captures
  -> topic segments
  -> claims
  -> beliefs
  -> current_beliefs
  -> context_for(conversation)
```

## Derived Projections

```text
vector index
entity graph
wiki pages
context packages
eval snapshots
```

Derived projections should be rebuildable from canonical evidence-backed state.

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
context_feedback
belief_audit
```

## Belief Requirements

Accepted beliefs should include:

```text
subject
predicate
object or value
valid_from
valid_to
observed_at
confidence
status
stability_class
evidence_ids
prompt_version
model_version
```

## Context_For Shape

```text
Standing Context
Active Projects / Goals
Relevant Beliefs
Recent Signals
Entity Context
Raw Evidence Snippets
Uncertain Or Conflicting Context
```

Each section should have an explicit token budget. Historical facts should be
included only when relevant and clearly dated.

## Candidate Lanes

```text
semantic belief search
semantic segment search
keyword search
recent activity
active projects/goals
mentioned entity neighborhood
pinned profile facts
open contradictions
```

## First Eval Harness

Start with 25 to 50 prompts that cover:

```text
current project continuation
past decision recall
person/entity recall
style preference recall
active goal support
failed approach avoidance
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

## Build Order

```text
1. Ingest ChatGPT into raw conversations/messages.
2. Segment conversations by topic.
3. Embed segments.
4. Extract claims with evidence ids.
5. Consolidate claims into beliefs with temporal validity.
6. Extract and canonicalize entities.
7. Materialize current_beliefs.
8. Implement context_for candidate generation.
9. Implement ranking and token packing.
10. Expose context_for through MCP.
11. Add feedback capture.
12. Run evals before full-corpus consolidation.
```

