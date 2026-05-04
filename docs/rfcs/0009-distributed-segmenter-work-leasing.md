# RFC 0009: Distributed Segmenter Work Leasing

Status: proposal
Date: 2026-05-04
Context: Phase 2 segmentation; RFC 0001; RFC 0004; D005, D027, D029, D030, D031, D034, D040

This RFC captures a possible future shape for running Engram's segmenter across
multiple owned local machines while keeping the database on one machine. It is
not an accepted Phase 2 change. It records the subdivision and coordination
model so the idea can be reviewed before it becomes schema or implementation.

## Problem

The current segmenter can run through pending conversations from one process.
That is simple and appropriate for the active Phase 2 path, but the full
AI-conversation corpus is local-model expensive. If several owned machines can
run local segmenters, the obvious data flow is:

1. worker pulls one raw parent and its ordered messages from the database;
2. worker runs the local segmenter on that machine;
3. worker writes an inactive `segment_generation` and its `segments`;
4. embedding and generation activation proceed after the generation is
   complete.

The hard part is not the data flow. The hard part is deciding which worker owns
which parent at any moment without double-processing, losing retries, or
making the generation cutover semantics ambiguous.

Static subdivision by source, UUID range, or equal parent counts is fragile.
The corpus has a long tail: one large coding conversation can cost more than
hundreds of short conversations. Work should therefore be dynamically leased
from the database.

## Goals

- Use the database as the single work allocator.
- Preserve immutable raw evidence and non-destructive derived generations.
- Keep the subdivision unit compatible with existing parent-scoped generation
  activation.
- Avoid duplicate active generations for the same parent and derivation
  version.
- Allow workers to crash without permanently losing work.
- Keep local-first and no-egress constraints explicit when raw evidence moves
  from the database host to worker machines.

## Non-goals

- Do not require this for the current Phase 2 run.
- Do not introduce a hosted queue, cloud coordinator, telemetry service, or
  external persistence layer.
- Do not split ordinary parents across machines.
- Do not change D034's deterministic request profile contract.
- Do not change D031's activation rule: new segment generations become
  retrieval-visible only after required embeddings exist.

## Proposed Work Unit

The natural work identity is:

```text
(parent_kind, parent_id, segmenter_prompt_version, segmenter_model_version)
```

For the current AI-conversation Phase 2 scope, `parent_kind` is `conversation`.
This keeps the unit aligned with existing generation semantics:

- one parent produces one `segment_generation` for a given segmenter prompt and
  model version;
- that generation may contain multiple `segments`;
- the generation stays inactive until embedding and activation are complete;
- an eventual new prompt/model version creates a new generation rather than
  mutating old rows.

The default grain should be one parent per leased job. Window-level
parallelism should be deferred unless the long tail proves dominant, because
splitting one parent across machines complicates:

- topic continuity across windows;
- deterministic segment ordering;
- partial retry semantics;
- provenance expansion;
- generation completion and activation.

## Lease Model

Workers should claim work through a database-backed lease. A lease is a
time-bounded claim that says "worker X is currently responsible for this parent
and derivation version."

The lease record needs at least:

- `stage`, e.g. `segmenter`;
- `parent_kind`;
- `parent_id`;
- `segmenter_prompt_version`;
- `segmenter_model_version`;
- `status`: `pending`, `in_progress`, `completed`, `retryable_failed`,
  `terminal_failed`;
- `lease_owner`;
- `lease_expires_at`;
- `attempt_count`;
- `last_error`;
- optional cost hints such as `message_count`, `content_chars`, or
  `estimated_tokens`.

This could be implemented as a dedicated `segment_jobs` table, or as an
extension of `consolidation_progress`. A dedicated table is cleaner for
multi-worker leasing because `consolidation_progress` currently mixes stage
status, error counters, and human-readable position state.

## Claim Query Shape

The database should claim and return work in one transaction using
`FOR UPDATE SKIP LOCKED`.

Illustrative query:

```sql
WITH candidate AS (
    SELECT id
    FROM segment_jobs
    WHERE stage = 'segmenter'
      AND status IN ('pending', 'retryable_failed')
      AND (lease_expires_at IS NULL OR lease_expires_at < now())
      AND attempt_count < $1
    ORDER BY estimated_tokens DESC NULLS LAST, created_at
    FOR UPDATE SKIP LOCKED
    LIMIT 1
)
UPDATE segment_jobs j
SET status = 'in_progress',
    lease_owner = $2,
    lease_expires_at = now() + interval '15 minutes',
    updated_at = now(),
    attempt_count = attempt_count + 1
FROM candidate
WHERE j.id = candidate.id
RETURNING
    j.parent_kind,
    j.parent_id,
    j.segmenter_prompt_version,
    j.segmenter_model_version;
```

Workers should commit immediately after claiming. The expensive local LLM call
happens outside the claim transaction. The lease timeout is what allows another
worker to recover the job if the first worker dies.

Workers may heartbeat by extending `lease_expires_at` while processing a large
parent. Heartbeats should be small updates to the lease row only; they should
not mutate raw evidence or derived segment content.

## Completion Flow

For a successful job:

1. worker loads the parent and messages;
2. worker creates or resumes the matching `segment_generation`;
3. worker writes inactive `segments`;
4. worker marks the generation `segmented`;
5. worker marks the lease `completed`;
6. embedding workers later embed pending segments and activate completed
   generations under the existing D031 rule.

For a retryable failure, such as temporary segmenter service unavailability:

1. mark the current attempt failed with diagnostics;
2. set the lease status to `retryable_failed`;
3. clear or expire the lease;
4. allow another attempt until the poison cap is reached.

For a terminal failure, such as invalid provenance after retries:

1. mark the `segment_generation` failed with `failure_kind`;
2. set the lease status to `terminal_failed`;
3. keep diagnostics for review.

## Required Database Guards

The lease table prevents most duplicate work, but the segment tables still need
database-level guards. Multi-machine execution should not depend on perfect
worker behavior.

Required or recommended constraints:

- at most one non-terminal generation per
  `(parent_kind, parent_id, segmenter_prompt_version, segmenter_model_version)`;
- at most one active generation per parent, already covered by the current
  `segment_generations_active_parent_idx`;
- active sequence uniqueness per parent, already covered for conversations,
  notes, and captures;
- provenance validation that conversation segments cite ordered message ids
  from the same conversation, already covered by D030's trigger;
- idempotent inserts or conflict handling for segment embeddings.

The first constraint is the main missing guard for distributed segmentation.
Without it, two workers racing outside the lease path could create duplicate
`segmenting` generations for the same parent/version.

## Scheduling Policy

Use dynamic scheduling, not static partitions.

Recommended first policy:

- order by estimated cost descending, then creation/import order;
- lease one parent at a time per worker;
- make lease duration long enough for ordinary parents;
- heartbeat for long parents;
- cap attempts for poison parents;
- expose stuck and terminal-failed jobs for human review.

Largest-first scheduling keeps expensive outliers from becoming end-of-run
stragglers. It also makes better use of heterogeneous machines: a fast worker
will naturally claim more jobs over time.

## Privacy And Local-First Constraints

This proposal moves raw evidence from the database machine to worker machines.
That is still local-first only if those machines are explicitly trusted as part
of the user's owned local compute boundary.

Minimum expectations:

- worker machines are owned or explicitly trusted by the user;
- database access is limited to known worker hosts;
- Postgres traffic uses TLS or an SSH tunnel;
- workers run local model endpoints only;
- workers have no outbound internet while holding corpus access;
- no hosted queue, hosted model, telemetry, or cloud log sink is introduced;
- worker logs do not persist raw message text unless explicitly requested.

If these conditions are not true, distributed segmentation violates the spirit
of the local-first constraint even if no commercial cloud API is involved.

## Relationship To RFC 0001 And RFC 0004

RFC 0001 proposes a future supervisor/controller loop. RFC 0004 narrows the
segmenter into a bounded worker entry point. Distributed work leasing fits that
direction:

- supervisor claims a lease;
- supervisor invokes a segmenter worker for one bounded parent;
- worker returns a structured attempt result;
- supervisor records attempt outcome and decides retry/backoff/escalation.

The current CLI can act as a temporary supervisor, but the lease model should
not be buried inside segmenter domain logic. Leasing is orchestration state.

## Open Questions

1. Should the first implementation extend `consolidation_progress`, or create
   a dedicated `segment_jobs` table?
2. Should embeddings use the same lease mechanism immediately, or remain
   single-machine until segmentation is no longer the bottleneck?
3. What heartbeat interval and lease TTL fit the observed long-tail parent
   durations?
4. Should a worker be allowed to resume a partially written windowed generation,
   or should stale partial generations be terminal-failed and retried with a
   fresh generation?
5. Should cost hints be computed during ingestion, during job seeding, or lazily
   when the scheduler first sees a parent?

## Recommendation

If multi-machine segmentation becomes necessary, implement parent-level dynamic
leasing in the database before adding more worker processes. Do not rely on
multiple workers running the current pending-query loop. Start with one parent
per lease, largest-estimated-cost-first scheduling, stale lease recovery, and a
database uniqueness guard for non-terminal parent/version generations.
