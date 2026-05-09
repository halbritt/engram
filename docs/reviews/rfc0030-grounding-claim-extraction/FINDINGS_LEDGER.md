# RFC 0030 Public-Dataset Entity Grounding Findings Ledger

author: ledger-codex-gpt-5.5-001

Status: findings
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

Source reviews (8): claude (privacy/local-first lens), codex (impl
feasibility), gemini (operator workflow), usability_adversary,
privacy_adversary, schema_adversary, eval_adversary, cost_adversary.

Source verdicts at submit time: 6 × accept_with_findings; 2 ×
needs_revision (privacy_adversary, eval_adversary). Both needs_revision
verdicts were operator-overridden to accept_with_findings via
`continue` checkpoint resolution; the substantive findings stand and
are normalized below for synthesis.

## Findings

### L001 - "No live web at extraction time" is policy, not a code-side chokepoint
Severity: blocking
Sources: claude:F001; privacy_adversary:P003
Disposition target: accept
Rationale: Both lenses converge: the RFC's central privacy claim is
defended by the *current shape of `extractor.py`* rather than by a
named, grep-checkable invariant. The fix is the same in both reviews:
add a "Code-side enforcement" subsection that names the modules in
which HTTP clients are forbidden and commits to a unit test that walks
the AST and asserts the prohibition. Excludes the dataset-acquisition
module explicitly.

### L002 - Snapshot integrity hash is required for reproducibility to be a real invariant
Severity: blocking
Sources: claude:F003; privacy_adversary:P002; schema_adversary:S002 (rollback flow)
Disposition target: accept
Rationale: D-E commits to versioned snapshots but not to content-hashed
labels. Three lenses raised the same flag. Without a content hash,
"reproducibility" is a directory-name promise that any local-attacker
or filesystem-corruption event can break. Schema_adversary further
notes that snapshot-rollback semantics depend on this fix landing.
Recommended fix: snapshot id is `<dataset>@<date>@sha256:<hash>`; the
loader verifies and refuses on mismatch.

### L003 - Lock the five non-negotiables in DECISION_LOG to prevent future drift
Severity: blocking
Sources: privacy_adversary:P007
Disposition target: accept
Rationale: The non-negotiables are the RFC's strongest guarantee. They
should be promoted to a new D### entry whose supersession requires a
named replacement. Without this, "grounding" can be redefined later by
a smaller-scope RFC that softens the boundary.

### L004 - D-H eval oracle is fundamentally insufficient as proposed (multiple confounders)
Severity: blocking
Sources: eval_adversary:E001 (prompt confound), E002 (gaming via
coverage drop), E003 (undersized sample), E004 (slice bias),
E005 (contaminated secondary), E006 (no pre-registered threshold);
gemini:F008 (bench journey costs)
Disposition target: accept
Rationale: The most consequential set of findings in the run. As
proposed, D-H cannot distinguish "grounding helps" from "the new
prompt helps" (E001), can be gamed by suppressing low-confidence
candidates (E002), is under-powered by ~6x (E003), is selection-biased
on slice (E004), and uses a downstream-of-grounding signal as
"independent" secondary (E005). Required revisions to D-H:
- Three-arm bench: v8 / v9-grounding-disabled / v9-grounding-enabled.
  Only the v9-disabled vs v9-enabled comparison isolates grounding.
- Paired metric: false-rate AND coverage. Acceptance criterion pairs
  both directions.
- Sample size: 600+ segments for promotion-grade decision (100 only
  for sanity).
- Pre-registered decision rule: e.g., ≥30% relative false-rate
  reduction with ≤5% coverage drop.
- Replace PHASE-0004 merge-rate as secondary; use a held-out
  pre-resolved entity-grounding gold set instead.

### L005 - Hybrid resolver placement biases extraction without a prompt-shape guard
Severity: major
Sources: claude:F004; privacy_adversary:P004 (poisoned dataset
exfil through prompt injection); usability_adversary:U004 (interview
disambiguation cost)
Disposition target: accept
Rationale: The candidate-block-in-prompt approach (D-B option 3) is
recommended but lacks: (a) a prompt-shape guard distinguishing
"candidate hints" from "facts"; (b) sanitization of dataset-supplied
text against prompt-injection payloads; (c) a sane interview-UI
default for full candidate sets that does not double interview time.
Required fixes:
- Pin the candidate-block prompt sentence framing the hint as
  non-authoritative.
- Treat dataset description fields as untrusted; sanitize before
  insertion.
- Default interview UI to top-1-above-threshold-X with "see N more"
  affordance.

### L006 - Grant audit log location and non-sync stance unspecified
Severity: major
Sources: claude:F002; privacy_adversary:P005; schema_adversary:S005
Disposition target: accept
Rationale: D-F mentions an audit log but does not name storage,
retention, or non-sync stance. Three lenses converge on scratch SQLite
under `~/.engram/grants/` with a `.engram-no-sync` marker; the
artifact-id treatment must align with D068. Production PostgreSQL is
explicitly the wrong home (drags grant-exercise volume into a schema
reachable by anyone with DB read access, and replicates if Postgres
itself is replicated).

### L007 - D-D entity_external_references append-only / cascade behavior unspecified
Severity: major
Sources: schema_adversary:S001 (append-only); S004 (RFC 0018 cascade);
S008 (downgrade orphan rows)
Disposition target: accept
Rationale: Choosing option 2 (separate table) is right for the
multi-dataset case, but the RFC does not specify: tombstone-based
supersession (preserves append-only); cascade behavior (raw evidence →
entities → entity_external_references → claims); or how revoked-grant
rows behave for live consumer queries. Required: D-D commits to the
tombstone discipline and cascade order; D-F commits to live-query
filter on grant-active rows with audit queries seeing all rows.

### L008 - Snapshot-versioning interaction with RFC 0017 prompt_version is structurally undecided
Severity: major
Sources: schema_adversary:S003; codex:F002 (batched prompt budget)
Disposition target: accept
Rationale: Where does `dataset@snapshot` provenance live on the claim
row? Three options each have failure modes; the right answer
(per S003) is a separate `grounding_resolution_set` table pinning the
(claim_id, run_id, snapshot_pin_set) tuple. RFC must commit; without
it, RFC 0017 immutability is at risk.

### L009 - Resolver placement (D-B) and module-boundary sketch missing
Severity: major
Sources: codex:F001; codex:F003 (extractor integration);
codex:F006 (surface-form normalization)
Disposition target: accept
Rationale: The hybrid placement requires three distinct testable
units (surface-form extractor, candidate resolver, post-extraction
attachment). The RFC describes data flow but not seams. Required:
spec ships a "Module split" subsection with input/output shapes,
caching/lifecycle pattern, and a canonical normalization rule for
surface forms.

### L010 - First-run operator path is six steps with no story or progress feedback
Severity: major
Sources: gemini:F001; usability_adversary:U008 (download progress);
cost_adversary:C004 (bench cost framing)
Disposition target: accept
Rationale: From `engram install` to first grounded extraction is six
opaque operator decisions (discover, pick datasets, snapshot, index,
grant, re-extract). The RFC names each step but does not coherently
sequence them or surface their costs. Required: spec ships an
`engram grounding onboarding` (or similar) command, progress
indicators on slow steps (multi-GB downloads, indexing), and an
honest cost statement on the bench-and-iterate loop.

### L011 - Storage budget under-stated for realistic v1+ configurations
Severity: major
Sources: cost_adversary:C001
Disposition target: accept
Rationale: The 10GB budget is plausible for a *minimum* v1 (places-
only Wikidata, no embeddings, single snapshot, single role). With
two co-existing snapshots and indexes, the realistic footprint is
~10-12GB; with embeddings, ~16-20GB. Required: enforce the budget
(refuse new snapshots if total exceeds), warn at 80%, and pin a
hard-fail at 12GB by default.

### L012 - Resolution-latency budget undefined; risks halving extraction throughput silently
Severity: major
Sources: cost_adversary:C002; codex:F002 (batching prompt budget
interaction)
Disposition target: accept
Rationale: D-G defers latency to bench but does not name an
acceptable cost. Realistic per-segment add of 50-200ms × 100k
segments = 1.4-5.5h additional re-extraction time. Required: a
per-segment budget (≤100ms recommended) with fail-fast on overflow,
and a per-corpus budget (≤2x current extraction time) as a
re-extraction precondition.

### L013 - "Silent downgrade" default rewards inattention; should be observable
Severity: major
Sources: gemini:F005 (machine-readable warning); usability_adversary:U003
(privacy-by-erosion); privacy_adversary:P009
Disposition target: accept
Rationale: Q7's recommended seed of "silent downgrade with a one-line
warning per run" is too quiet. Required: machine-readable
`grounding_status` field in the run summary JSON; a
`~/.engram/grounding/active-grants.lock` state file detecting prior
grants now absent; loud failure (or one-flag override) when a prior
grounded operator runs ungrounded by accident.

### L014 - Persistent grants rot into invisible state; need usage surfacing
Severity: major
Sources: usability_adversary:U001 (grants-you-forget); cost_adversary:C005
(matrix scaling); usability_adversary:U002 (snapshot freshness)
Disposition target: accept
Rationale: Both UX adversaries flag the saved-passwords failure mode
for persistent grants. Required: `engram grants list --usage`
showing last-accessed dates; daily/weekly run summary line surfacing
active grants; "grant template" surface to manage the role × dataset
matrix (`engram grants apply-template default <role>`).

### L015 - Snapshot lifecycle has no operator-facing dial; staleness invisible
Severity: major
Sources: usability_adversary:U002; cost_adversary:C003 (social process);
gemini:F004 (alarm/notification)
Disposition target: accept
Rationale: Operator-curated snapshots will go stale silently.
Required: per-dataset staleness thresholds (default 90 days,
configurable); `engram grounding versions` command (queries upstream
*only at command-invocation time*, never at extraction time, so the
non-negotiable holds); staleness warning header in extraction
summary.

### L016 - Operator interview verdict on wrong grounding does not propagate to private alias suppression
Severity: major
Sources: usability_adversary:U005 ("Tartine" private nickname)
Disposition target: accept
Rationale: The RFC's motivating example ("Tartine" misidentification)
has a sub-class the proposal does not address: a private entity that
shares a surface form with a public one. Required: per-corpus alias
suppression / private entity override surface; interview verdict
populates a private alias table that the resolver consults *first*.

### L017 - Reversibility is "redoable" not "reversible"
Severity: minor
Sources: usability_adversary:U006
Disposition target: accept
Rationale: Re-extraction under no-grant configuration is the only
named rollback path; that's a multi-hour, multi-stage operation.
Required: `engram grounding detach --segment <id>` and
`--all-since <date>` for cheap rollback that leaves claims intact
but un-grounds them.

### L018 - Bench gate operator-decision surface should be automated
Severity: minor
Sources: usability_adversary:U007; cost_adversary:C004
Disposition target: accept
Rationale: Step 3 of promotion path implicitly requires the operator
to manually compare 100 grounded vs 100 v8 claims. Required:
`engram phase3 grounding-bench` automation that surfaces a single
delta number and a recommendation; operator decision is "trust /
inspect" not "compare 100 claims."

### L019 - File-mode discipline for snapshot dirs unspecified
Severity: minor
Sources: privacy_adversary:P006
Disposition target: accept
Rationale: Shared-machine fingerprinting via snapshot directory
listing. Required: D-E names mode bits (0700 dirs, 0600 manifests);
engram refuses to use a snapshot dir with looser permissions.

### L020 - Resolver output redaction policy needed for tracked exports
Severity: minor
Sources: privacy_adversary:P008
Disposition target: accept
Rationale: RFC 0029 (bench triage workbench) redaction policy does
not contemplate grounded-resolution prose. Required: D-C extends
redaction rule — tracked exports may record candidate QIDs /
dataset-ids and confidence scores, but not the descriptive prose
attached to those candidates.

### L021 - Dataset-acquisition network footprint should be explicitly documented
Severity: minor
Sources: privacy_adversary:P001
Disposition target: accept
Rationale: Dataset-fetch is a sanctioned network-boundary crossing
with a footprint of (operator IP, user-agent, dataset id, snapshot
date, download volume). The RFC implicitly extends "local-first" to
exclude this; should explicitly document the footprint and rule
that nothing else crosses.

### L022 - Test coverage matrix and CLI/argparse shape missing
Severity: minor
Sources: codex:F005; codex:F008
Disposition target: accept
Rationale: Spec must ship a test matrix (grant enforcement,
snapshot integrity, resolver placement, prompt-version bump,
downgrade behavior) and exact `argparse` subparser definitions for
the new CLI verbs.

### L023 - Resolver determinism contract not stated
Severity: minor
Sources: codex:F007
Disposition target: accept
Rationale: Resolver invocations must be deterministic under
(surface_form, dataset@snapshot). The RFC implies this but does
not state it. Tests must pin it.

### L024 - Migration shape, table DDL, and locking discipline missing
Severity: minor
Sources: codex:F004; schema_adversary:S007 (index discipline)
Disposition target: accept
Rationale: Step 4a must commit to migration step count, table DDL,
exact index list (with `CONCURRENTLY` annotation where required),
trigger code, and idempotency confirmation. Snapshot-internal
indexes live outside production PG (under
`~/.engram/grounding/<snapshot>/index/`); pin this.

### L025 - RFC 0028 subject_kind_hint × grounding precedence unspecified
Severity: minor
Sources: claude:F007; gemini:F007 (interview verdict precedence)
Disposition target: accept
Rationale: Q2 should pick "deepening with type-narrowing": if RFC 0028
says `subject_kind=person`, resolver narrows candidate-type filter
accordingly; if a verdict from interview disagrees, verdict wins.

### L026 - Test-suite fixture footprint and download-on-test strategy missing
Severity: minor
Sources: cost_adversary:C006
Disposition target: accept
Rationale: Tests need a synthetic ~10MB snapshot fixture
(content-hash-pinned, committed); integration tests opt-in via env
var to download a real subset.

### L027 - Index rebuild cost on snapshot upgrade unspecified
Severity: minor
Sources: cost_adversary:C007
Disposition target: accept
Rationale: D-E should commit: indexing happens at fetch time;
extraction never indexes lazily.

### L028 - Decision-log compatibility check incomplete (D068 artifact-id model)
Severity: minor
Sources: claude:F008; schema_adversary:S005 (gnt_* convention)
Disposition target: accept
Rationale: Snapshot manifests, grant entries, grant-exercise log
events, and grounding_resolution_set rows are all artifacts in
D068's sense. Required: explicit artifact-id treatment with
documented prefix conventions (`snap_*`, `gnt_*`, `gres_*` or
similar).

### L029 - Implementation footprint understated; promotion path step 4 should split
Severity: minor
Sources: cost_adversary:C008
Disposition target: accept
Rationale: Realistic implementation is 1500-3000 LOC across
extractor, consolidator, CLI, new module, migrations, tests.
Required: split step 4 into 4a/4b/4c/4d.

### L030 - Grant-revocation behavior on existing grounded claims unspecified
Severity: minor
Sources: gemini:F002
Disposition target: accept
Rationale: Required: D-F commits to forward-only revocation;
existing entity_external_references rows persist (history); live
queries filter by grant-active.

## Cross-lane patterns

- **Snapshot-integrity (L002) is raised by privacy + claude (privacy
  lens) + schema (rollback flow).** Three independent lanes flag the
  same root cause with the same fix. This is consensus-level signal.
- **D-H oracle (L004) is the single largest finding cluster.** Six of
  the eval_adversary's eight findings are blocking; the gemini
  reviewer's F008 corroborates the bench-cost framing.
- **Privacy + UX adversaries converge on grant-management UX (L006,
  L013, L014).** Different lanes, same problem: persistent grants
  with no surfacing rot into invisible state.
- **The "candidate hint biases extraction" theme (L005) lands from
  three independent angles**: claude (privacy/local-first lens —
  refusal-of-false-precision violation), privacy_adversary (poisoned
  dataset exfil), usability_adversary (interview cost).
- **Schema lane and Codex lane converge on D-D + D-E specification
  gaps (L007, L008).** Append-only discipline, cascade order,
  prompt_version interaction.

## Consensus

- The five non-negotiables in § "Non-negotiable constraints" are
  *correctly identified* and central to the privacy posture. Eight
  reviews preserve them. Synthesis must not soften any of them; the
  blocking findings are about *enforcing* them better, not weakening.
- D-D option 2 (separate `entity_external_references` table) is the
  right home for the schema. The schema_adversary endorses it; codex
  endorses it. Synthesis should pick option 2 and address the
  append-only / cascade / prompt-version interactions raised in L007,
  L008.
- D-C "full candidate set with confidences" is the right output shape;
  refusal-of-false-precision honored. The fix landscape is at the
  *interview UI* (top-1 default, "see more" affordance) and at the
  *prompt* (hint framing).
- The promotion path (design → spec → bench → implementation) is
  defensible if the bench is restructured per L004.

## Conflicts

- **Eval_adversary's E003 (sample size 600+) vs. RFC's open-question
  Q1 (smallest deliverable: 100 segments).** The RFC explicitly asks
  the loop to answer Q1; the eval_adversary answers "100 is wrong by
  ~6x." Synthesis must take a position. Recommended: 100 for sanity,
  600+ for promotion gate (the eval_adversary's framing).
- **Gemini's F003 (interview UI candidate disambiguation impacts
  throughput) vs. D-C (full candidate set is the output shape).** The
  shapes are not in conflict; the UI display is. Synthesis must pin
  a default that is conservative on operator interview throughput.
- **Cost_adversary C001 (10GB is the ragged edge) vs. RFC's Q5 (≤10GB
  configurable).** Not a conflict in direction; only in budget
  enforcement strictness. Synthesis should accept the
  fail-at-12GB-default fix.

## Recommended next action

Synthesis should:

1. Accept all 30 findings (every disposition is `accept`). The RFC is
   substantively defensible; the findings are tightening, expanding,
   and locking, not rejecting.
2. Take the prescribed positions on D-A through D-H and Q1 through Q7.
   In particular, D-H requires a substantial rewrite (three-arm bench;
   paired metric; pre-registered decision rule; held-out gold set as
   secondary).
3. Promote the five non-negotiables to a new D### entry locked against
   future drift (L003).
4. Produce a revision instruction set granular enough that
   apply_findings can edit the RFC section-by-section without
   inventing new design.
