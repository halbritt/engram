# RFC 0001: Supervisor Controller Loop

Status: proposal
Date: 2026-05-02

This is an idea-capture RFC, not an accepted architecture decision. It records a
possible future shape for Engram's supervisor after the basic ingest,
segmentation, embedding, claim, belief, and serving stack exists.

The motivating analogy is the Kubernetes controller pattern: continuously
observe actual state, compare it with desired state, and reconcile the system
toward that desired state through small, idempotent actions.

## Background

During Phase 2, the word **supervisor** emerged as a useful term for the
component around stage workers such as `segment_pending` and
`embed_pending_segments`. The supervisor selects work, records progress, handles
failures, and controls activation gates so partially processed derivations do
not become retrieval-visible.

The broader idea is to make that supervisor a first-class, long-running Engram
process rather than a set of manually invoked batch commands.

## Shape

Run Engram's supervisor as a local service, likely a `systemd` unit on the
deployment host:

```text
systemd
  -> engram-supervisor.service
       -> reconcile loop
            -> observe database + source state
            -> compute desired work
            -> invoke bounded stage workers
            -> record progress, failures, and activation events
```

The service should be boring at the operating-system layer. `systemd` restarts
the process if it crashes. Engram's own supervisor decides what corpus work is
safe to do.

The reconciliation loop should be explicit:

1. Observe current state.
2. Determine desired state from schema versions, policy, source cursors, and
   queued events.
3. Pick a small unit of work.
4. Execute through a stage worker or constrained LLM worker.
5. Commit progress and emitted events.
6. Sleep, back off, or continue.

All durable state lives in Postgres. The supervisor must be restartable without
hidden conversational state.

## Desired State

Desired state is not "run everything all the time." It is a set of versioned
invariants, for example:

- all configured raw sources have been ingested to their latest observed cursor;
- every eligible conversation has an active segment generation for the current
  segmenter prompt/model/request profile;
- every active segment has required embeddings for configured embedding models;
- privacy reclassification captures have invalidated affected derived rows;
- claim extraction has run for active segments under the current extractor
  version;
- belief consolidation has considered all pending claims;
- accepted beliefs have current embeddings where required;
- context snapshots are fresh for active or recently used consumer scopes;
- eval gates block phases that have not earned full-corpus execution.

Desired state should be declarative enough that the supervisor can explain why
it is doing work.

## Stage Workers

The supervisor should orchestrate workers; it should not bury all logic inside
one large agent loop.

Likely workers:

- source ingest workers: ChatGPT, Claude, Gemini, Obsidian, MCP capture;
- segmenter worker;
- embedder worker;
- claim extractor worker;
- belief consolidator worker;
- entity canonicalizer worker;
- snapshot refresher;
- eval runner;
- maintenance / re-derivation worker.

Workers should own bounded transformations. The supervisor owns ordering,
backpressure, retry policy, and visibility gates.

## Minimal Agentic Core

The supervisor can eventually contain a small agentic component, but the agent
should be constrained by design:

- local-only model;
- narrow context window;
- no network egress;
- typed tools only;
- no direct SQL writes except through approved stage APIs;
- no ability to mutate raw evidence;
- decisions recorded as structured events;
- every LLM-mediated action tied to a prompt/model/request-profile version.

The agent's job is not to "think freely about memory." Its job is to inspect
diagnostics, classify work, choose among approved actions, and propose
operator-visible decisions when policy is ambiguous.

Examples of acceptable agent decisions:

- classify a failed segmenter run as runaway generation vs. service outage;
- choose to requeue a parent after a transient local-model failure;
- recommend shrinking a window budget after repeated timeouts;
- summarize why a context snapshot is stale;
- propose a re-derivation run after a prompt/model version bump.

Examples of unacceptable agent decisions:

- invent beliefs without raw evidence;
- silently relax privacy tiers;
- run arbitrary SQL migrations;
- call external services;
- rewrite canonical architecture decisions.

## Position On LLM In The Loop

The LLM should not be the controller. The deterministic reconcile loop should
remain the controller, and the LLM should be a bounded advisor or worker inside
that loop.

This distinction matters. A controller must be boring: observable, replayable,
restartable, and explainable from database state. An LLM is useful exactly where
Engram encounters ambiguous, language-shaped material, but it is a poor owner of
system invariants. If the LLM owns the loop, the system eventually becomes a
chat transcript with side effects. If the loop owns the LLM, the system remains
a database-backed controller that occasionally asks a model to classify,
extract, summarize, or recommend.

Recommended layering:

```text
deterministic controller
  -> computes eligible work from Postgres state
  -> enforces gates, leases, retries, and backpressure
  -> invokes typed workers
       -> some workers call local LLMs under strict request profiles
       -> LLM outputs become proposed derived rows or recommendations
  -> validates outputs
  -> commits, rejects, retries, or asks for operator approval
```

The LLM can help with:

- semantic extraction from raw evidence;
- failure classification when deterministic diagnostics are insufficient;
- operator-readable summaries of why work is blocked;
- proposing re-derivation slices after model/prompt changes;
- generating candidate repair plans for repeated local-inference failures;
- prioritizing dream work when multiple safe options exist.

The LLM should not own:

- phase gates;
- privacy policy;
- raw evidence mutation;
- database migrations;
- retrieval visibility;
- schema version selection;
- unconditional requeue / rerun loops;
- eval pass/fail decisions.

The controller may ask an LLM "what do you think this failure means?" It should
not ask "what should Engram do next?" without constraining the answer to a small
enumerated action set.

## Work Allocation Problem

The supervisor is not merely a batch runner. It is an ongoing resource
allocation system.

Engram will accumulate multiple competing queues:

- ingest new source material;
- segment raw evidence;
- create embeddings;
- extract claims;
- consolidate claims into beliefs;
- refresh context snapshots;
- revisit stale, contradicted, or high-salience beliefs;
- run eval probes;
- perform dream / maintenance work.

Those queues compete for scarce resources:

- GPU slots;
- local-model context budget;
- embedding throughput;
- database write load;
- operator attention;
- freshness deadlines;
- usefulness and salience;
- risk tolerance around unvalidated phases.

A deterministic scheduler can handle obvious rules: phase gates, FIFO draining,
retry caps, leases, backpressure, and resource limits. It becomes less natural
when the choice is qualitative, for example:

- spend the night embedding thousands of low-value archival segments;
- reprocess a small set of high-salience beliefs affected by a prompt upgrade;
- refresh snapshots for active projects;
- run a soak that blocks full-corpus progress;
- hold GPU time idle because the current failure rate suggests the backend is
  unhealthy.

This is the place where a small local model may be useful. The model should not
execute arbitrary work; it should help rank bounded, controller-generated
options.

## LLM-Assisted Scheduling

The safer pattern is LLM-assisted scheduling:

```text
deterministic controller
  -> builds a state digest
  -> asks policy model for a bounded work plan
  -> validates the plan against hard rules
  -> executes typed workers with leases and budgets
  -> records outcomes
  -> repeats
```

The policy model should see a curated state summary, not unrestricted database
access:

```text
Backlog:
- 4,320 conversations unsegmented
- 1,100 segments missing embeddings
- 270 active segments missing claim extraction
- 38 beliefs flagged stale by feedback
- 12 high-confidence beliefs with possible contradiction candidates

Resources:
- 2 GPUs idle
- embedder healthy
- segmenter has 3 recent timeout failures
- nightly budget: 6 hours
- current phase gate: Phase 2 full corpus not approved

Policy:
- do not run claim extraction before Phase 2 gate
- do not serve stale lower-tier vectors
- prefer active-project freshness over archival completeness
```

It should return a constrained plan:

```json
{
  "actions": [
    {
      "type": "embed_pending_segments",
      "limit": 2000,
      "reason": "Embedding backlog blocks retrieval visibility and embedder is healthy."
    },
    {
      "type": "run_segment_soak",
      "limit": 300,
      "reason": "Enum-ID soak validation is needed before full-corpus segmentation."
    }
  ]
}
```

The controller then validates:

- action type is allowed;
- phase gate permits it;
- privacy policy is not bypassed;
- resource budget is available;
- worker arguments are within configured bounds;
- model/prompt/request-profile versions are explicit;
- no incompatible embedding spaces are mixed;
- no raw evidence mutation is requested.

If validation fails, the plan is rejected and logged. The model never gets to
turn a recommendation into side effects on its own.

## Salience And Time

Salience is a scheduler input, not a substitute for truth. The model may help
estimate semantic importance, but temporal mechanics should remain explicit.

A belief can be old and still true. A belief can be recent and wrong. Time
should affect revisit priority and ranking features, not silently decay belief
confidence or delete evidence.

Useful salience signals include:

- active project relevance;
- recent consumer queries;
- explicit user feedback;
- belief confidence and stability class;
- contradiction candidates;
- frequency of use in `context_for`;
- recency of supporting evidence;
- age since last revalidation;
- privacy tier and blast radius if wrong.

The supervisor can use these signals to decide what to revisit during idle
compute windows. It should still express the selected work as explicit,
versioned, replayable actions.

## Implementation Bias

Build the deterministic controller first. Add the LLM only after there are
enough real failure logs, eval results, and operator tasks to prove that
language-shaped judgment helps.

The initial service can be non-agentic:

- poll for pending source/derivation state;
- run one bounded worker class at a time;
- emit structured events and progress rows;
- stop cleanly;
- expose pause / drain / resume controls.

The first useful LLM integration is likely not autonomous planning. It is
failure triage: classify Phase 2/3 attempt diagnostics into a small taxonomy
and recommend one of a few approved remediations. That gives Engram a bounded,
measurable reason to put an LLM inside the supervisor without making it the
owner of the system.

After failure triage, the next candidate is shadow-mode scheduling:

1. Deterministic heuristics choose actual work.
2. The LLM policy model recommends a work plan from the same state digest.
3. Engram logs both choices and outcomes.
4. Operator review compares usefulness, wasted work, and surprise.
5. Only after the LLM earns trust does the controller execute approved action
   types from the LLM plan.

## Controller Resources

Engram may benefit from explicit controller-facing tables or views later. These
could be added only after current simpler progress tables become insufficient.

Possible primitives:

- `memory_events`: append-only events emitted by ingest, review, feedback,
  reclassification, prompt/model upgrades, and eval outcomes;
- `work_items`: optional materialized queue when deriving work from tables gets
  too expensive or too opaque;
- `supervisor_runs`: one row per service loop or bounded reconcile pass;
- `stage_attempts`: detailed attempt log for LLM-derived stages;
- `desired_versions`: current accepted prompt/model/request-profile versions
  per stage;
- `source_cursors`: current ingest cursor per source.

The bias should remain: derive work from canonical tables until an explicit
queue is justified.

## Sleep / Dream Work

The useful part of "dream" language is asynchronous maintenance. Avoid mystical
or unconstrained consolidation. Treat dreams as scheduled reconcile classes:

- re-embed stale rows for a new embedding model;
- refresh context snapshots after captures, review actions, or belief changes;
- rerun claim extraction on a target slice after prompt upgrades;
- scan high-confidence beliefs for contradictory raw evidence;
- normalize relative temporal expressions into absolute dates during claim
  extraction or review;
- rebuild derived summaries for Obsidian sections or long conversations;
- run eval probes against known failure slices;
- compact or archive diagnostic rows after they are summarized.

Dream work is allowed to consume idle GPU time. It is not allowed to bypass
provenance, privacy, eval gates, or non-destructive re-derivation.

## Things This RFC Does Not Promote

- Unbounded autonomous "dream replay." Maintenance remains scheduled,
  inspectable, and policy-bound.
- A single monolithic agent that owns the entire memory lifecycle.
- A self-modifying controller. Prompt/model changes are explicit versioned
  events, not improvised loop behavior.
- A replacement for phase prompts, eval gates, or human-authored gold sets.

## Safety And Boundaries

The supervisor is powerful because it can touch every derived stage. Its
boundaries should be stricter than ordinary CLI commands:

- no network egress in any corpus-reading process;
- local bindings only;
- explicit phase gates;
- no destructive updates to raw evidence;
- non-destructive re-derivation for derived data;
- activation gates before retrieval visibility;
- privacy-tier invalidation before serving;
- bounded batch sizes and backpressure;
- structured logs for every LLM-mediated action;
- operator-visible pause / drain / resume controls.

The supervisor should be able to stop cleanly at any time without corrupting
the corpus or hiding partially completed work.

## Possible V1.5 / V2 Path

Near-term, keep using CLI batchers until the core pipeline and smoke gate are
working.

After Phase 5 exists, introduce a minimal supervisor service:

1. Poll `memory_events` and source cursors.
2. Refresh stale context snapshots.
3. Drain pending embeddings and reclassification invalidations.
4. Run only one bounded worker class at a time.
5. Emit `supervisor_runs` / attempt diagnostics.

Later, add the constrained local agent:

1. Inspect failures and classify them.
2. Recommend or execute approved remediation.
3. Schedule dream work from policy.
4. Produce operator-readable reports.

Do not put the LLM agent in charge before the deterministic controller exists.

## Disproof Probes

Before promoting this RFC into decisions, test:

- Can current CLI batchers plus cron/systemd timers cover the need without an
  agentic supervisor?
- Does a materialized work queue reduce operational confusion, or does it add a
  second state system?
- Do snapshot freshness failures actually occur often enough to require a
  long-running reconciler?
- Does LLM-assisted failure classification outperform deterministic rules on
  existing Phase 2 soak failures?
- Can the supervisor explain every action from database state alone?
- Does an LLM sidecar reduce operator work without increasing surprise actions?
- Can every LLM-mediated supervisor action be replayed or audited from stored
  inputs, prompt version, model version, and chosen action?

## Open Questions

- What is the smallest table set needed for a controller loop?
- Should `memory_events` be append-only infrastructure in Phase 5 or wait until
  after `context_for` proves useful?
- Is there one supervisor for all stages, or separate controllers per bounded
  context?
- How does the supervisor coordinate GPU-heavy workers on a multi-GPU host?
- What is the operator UX for pause, drain, force requeue, and version bump?
- Which actions are automatic, which require approval, and which only produce a
  recommendation?
