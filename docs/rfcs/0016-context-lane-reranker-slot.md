# RFC 0016: Context Lane Reranker Slot

Status: proposal
Date: 2026-05-05
Context: SPEC.md § Live Ranking; docs/design/V1_ARCHITECTURE_DRAFT.md:207-226;
README.md § Explicitly Not V1; PHASE_3_CLAIMS_BELIEFS spec; deferred from
adversarial review 2026-05-05

This is an idea-capture RFC, not an accepted architecture decision. It proposes
a typed seam in the lane compiler so a cross-encoder reranker can be A/B-tested
later against a gold set, without forcing a redesign of `context_for` when
that experiment becomes possible. It does *not* propose shipping a reranker in
V1 — the existing not-V1 decision stands.

## Background

V1 live serving uses a weighted scorer over the candidate set produced by the
multi-lane retriever (`docs/design/V1_ARCHITECTURE_DRAFT.md:209-222`):

```text
score =
    relevance * currentness * confidence * specificity
  * source_quality * recurrence * task_fit
  - redundancy - stale_penalty
```

An LLM cross-encoder reranker is explicitly deferred to "an offline experiment,
not part of v1 live serving" (`V1_ARCHITECTURE_DRAFT.md:226`) and listed under
`README.md` § Explicitly Not V1 as "LLM cross-encoder reranker in the live
path." The deferral is correct on two grounds: V1 has no gold set against
which to measure recall@k or MRR (gold-set authoring waits on Phase 3), and a
local cross-encoder adds latency that can't be evaluated until claims and
beliefs exist.

Two facts about the bitemporal data shape are worth recording, since they
shape why this experiment will eventually matter:

1. Dense semantic similarity over a long-running personal corpus surfaces
   temporally-disconnected near-duplicates: superseded assumptions, retracted
   facts, and historical states sharing surface similarity with current
   beliefs. The weighted scorer's `currentness` and `stale_penalty` terms
   target this directly via `stability_class`, but the eval lens for whether
   they are sufficient does not yet exist.
2. The eval lens (gold sets, `context_feedback` annotations, belief review
   queue outcomes) accumulates only after Phase 3 ships. Until then any
   reranker decision is unfalsifiable.

## Problem

The lane compiler is not yet implemented — `context_for` lives in the V1
architecture draft and SPEC, not in `src/engram/`. That is the cheap moment to
shape the scorer seam. Once the weighted scorer is wired directly into the
lane code, swapping it for an A/B harness costs more than placing the seam
correctly the first time.

The risk addressed by this RFC: V1 ships the weighted scorer as an inline
function call inside the lane compiler; later, when a gold set exists and a
local cross-encoder is worth evaluating, the experiment requires invasive
edits to `context_for` and its budget logic, discouraging the experiment
itself.

## Proposal

### Typed scorer interface

Define a single typed seam between candidate generation and budgeted lane
output:

```python
class CandidateScorer(Protocol):
    def score(
        self,
        query: ContextQuery,
        candidates: Sequence[Candidate],
    ) -> Sequence[ScoredCandidate]: ...
```

V1 ships exactly one implementation: `WeightedScorer`, encoding the existing
factor list. The lane compiler depends on the protocol, not the concrete
class.

`Candidate` and `ScoredCandidate` should carry enough provenance for an
external scorer to operate without a second DB round-trip: the segment id,
belief ids, evidence snippet, embedding distance, stability class, and the
factor inputs the weighted scorer already needs.

### Pre-budget placement

Scoring happens *before* the lane budgeter, not after. This RFC fixes the
ordering as:

```text
candidate generation (per lane)
  -> CandidateScorer.score (single call, all lanes)
  -> per-lane budgeter (token-aware, deterministic)
  -> sectioned output
```

Rationale: a reranker needs to see all lanes' candidates together to make
relative quality calls; the budgeter then trims by lane budget given the
final scores. Putting the scorer post-budget would force two scoring passes
when an experiment swaps in a cross-encoder.

### A/B harness, not a feature flag

The seam supports a `compare` mode, not a runtime toggle. Given two scorers,
the harness runs both over the same candidate set and emits a diff
(top-k overlap, rank correlation, per-section deltas). Output goes to a
review artifact under `docs/reviews/`, not into the live `context_for`
response. This avoids the trap of shipping a reranker behind a flag with no
falsification record.

### Determinism contract

`WeightedScorer` is deterministic given the same candidate inputs. The scorer
protocol should require ordering stability: ties resolve by `(segment_id,
belief_id)` lexicographically. This is the cheap version of reproducibility
the eval substrate will need.

### Non-goals

- Shipping any cross-encoder in V1.
- Choosing a specific cross-encoder model.
- Running the A/B harness before a gold set exists.
- Introducing a remote rerank API or any scorer that breaks the local-first
  constraint.
- Replacing or restructuring the weighted scorer's factor list.

## Open questions

1. Does `Candidate` carry the raw segment text, or just an id the scorer
   resolves? Carrying text simplifies a future cross-encoder; carrying ids
   keeps `Candidate` cheap and matches the snapshot serialization needs.
2. Should `CandidateScorer.score` be allowed to drop candidates, or only
   re-score? A pure rerank-and-keep contract is simpler to reason about; a
   filtering contract handles the "obviously irrelevant" case in one pass.
3. Where does `context_feedback` plug into the harness output? Likely as a
   labeling source for the eval set rather than a scorer input, but worth
   pinning before the harness is built.

## Acceptance criteria for promotion

This RFC is ready to promote into `BUILD_PHASES.md` once:

- The `CandidateScorer` protocol and `Candidate` / `ScoredCandidate` shapes
  are concrete enough to land in the lane compiler build prompt.
- The pre-budget placement is reflected in the lane compiler's phase row.
- The eval-substrate prerequisites for the A/B harness (gold set,
  `context_feedback` schema) are tracked.

Until then this RFC is design-time guidance for the lane compiler build, not
a binding contract.
