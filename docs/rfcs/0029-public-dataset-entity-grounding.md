<a id="rfc-0029"></a>
# RFC 0029: Public-Dataset Entity Grounding for Claim Extraction

| Field | Value |
|-------|-------|
| RFC | 0029 |
| Title | Public-Dataset Entity Grounding for Claim Extraction |
| Status | proposal |
| Implementation | none |
| Date | 2026-05-09 |
| Context | RFC 0011 § Schema (claims/beliefs); RFC 0017 (extraction prompt versioning); RFC 0028 (predicate-intent surfacing — adjacent prompt change); `src/engram/extractor.py:37` (`EXTRACTION_PROMPT_VERSION`); `src/engram/extractor.py:1961` (`build_extraction_prompt`); `migrations/009_phase4_entities_review.sql` (entities table, entity_kind enum); engram principles: local-first, corpus/network separation, raw-is-sacred, eval-as-oracle |

Decision refs:
  - none yet (proposal)

Review refs:
  - none (proposed for striatum-orchestrated multi-agent review per
    `docs/process/multi-agent-review-loop.md`)

Phase refs:
  - PHASE-0003 (extraction)
  - PHASE-0004 (entity consolidation)

This RFC proposes that claim extraction gain **entity grounding from
locally-held public datasets** (Wikidata, GeoNames, OpenStreetMap, and
similar), with three load-bearing constraints:

1. **Local only.** Datasets are downloaded once, stored on disk,
   queried in-process. No live web calls from the extraction loop.
2. **Explicit grant.** A given agent context only sees a dataset
   when the operator has explicitly granted access; the grant is
   recorded and enumerable.
3. **Snapshot-pinned per extraction run.** The dataset version used
   to ground a claim is recorded alongside the claim, so the same
   raw evidence re-extracted later reproduces (or knowingly
   diverges from) the original output.

The hypothesis is that grounding will materially improve extraction
quality — fewer "Hobnob is a person" mistakes (RFC 0028's failure
class), better entity de-duplication, and richer provenance — without
violating engram's local-first principle. This RFC seeds the design
space; the detailed architecture is intended to be elaborated through
striatum's review loop before any implementation lands.

## Motivation

The current extractor (`src/engram/extractor.py::extract_claims_from_segment`)
sees only the segment text and the predicate vocabulary. The local LLM
has no way to know whether "Tartine" is a bakery, a French word, or a
person; whether "EVNotify" is an app or a product line; whether a city
mentioned in passing is in California or Estonia. Its only knowledge of
the world outside the segment comes from training data, which is:

- Variably accurate for any specific entity
- Often stale (post-cutoff entities are invisible)
- Not introspectable — we cannot tell when it is guessing
- Not reproducible — a model upgrade silently changes what it "knows"

Observed downstream costs already documented in adjacent RFCs:

- **RFC 0028 § Current state** records six operator `false` rationales,
  five of which (~83%) reduce to "the LLM extracted a claim about an
  entity it misidentified." `Hobnob -[has_name]-> Hobnob` is the
  archetype: a restaurant labeled as a person because the model had no
  grounding signal to distinguish.
- **PHASE-0004 entity consolidation** (`migrations/009_phase4_entities_review.sql`)
  exists in part because the extractor cannot reliably co-refer
  entities across segments. Two mentions of "the bakery on Guerrero"
  and "Tartine" become two entity rows that a separate consolidation
  pass must merge — work that grounding could partly avoid.

A meaningful share of the entities flowing through the extractor are
**public, stable, well-described**: products, places, companies, media
works, public figures. These can be resolved against versioned public
datasets without sending personal evidence to a remote service.

## Non-negotiable constraints

These are stated up front so the design loop does not relitigate them:

1. **No live web access from the extraction path.** Datasets are
   pre-downloaded and queried locally (file/SQLite/embedded index).
   This RFC does not propose calling Wikidata's HTTP API at extraction
   time, calling a search engine, or contacting any external service
   during the extraction loop.
2. **Personal evidence does not leave the machine.** Even at dataset-
   acquisition time, the only external traffic is fetching the
   dataset itself (a public, content-addressed download). No part of
   the user's corpus participates in those requests.
3. **Per-agent dataset grants are explicit and recorded.** An agent
   context that has not been granted dataset X cannot read it. The
   grant is operator-driven, enumerable (`engram grants list` or
   similar), and revocable. Default posture is no grants.
4. **Raw evidence stays sacred.** Grounding affects derived claim
   rows; the raw evidence tables (segments, conversations, messages)
   are not modified.
5. **Reproducibility is preserved.** Each grounded claim records
   which dataset(s) at which snapshot version contributed to its
   resolution. Re-running extraction at a later date with a different
   dataset version is a knowing operation, not silent drift.

If a proposed sub-design violates any of these, the RFC needs to come
back here, not the design loop.

## Scope

In scope:

- A locally-held public-dataset registry and snapshot mechanism.
- A resolver that maps surface forms in segment text to candidate
  entries in granted datasets.
- A way to surface candidate resolutions to the extractor (prompt-time
  context) and/or to the post-extraction validation layer.
- A schema mechanism for recording the resolved external reference(s)
  on a claim or entity row, with snapshot version.
- A grant model that gates which agent contexts may read which
  datasets.

Out of scope (deferred or explicitly rejected):

- Live web search at extraction time.
- Calling external LLM endpoints with corpus content.
- Resolution against private datasets that a user happens to have
  locally but did not intend to expose to extraction (e.g., contact
  list, calendar). Those belong to PHASE-0004 and the local entity
  store.
- Cross-machine dataset sharing or sync.
- Any change to how raw evidence is stored.

## Design space (to be resolved through review)

The following are the consequential choices the design loop should
work through. Each has a recommended default for the seed; the loop
should challenge or confirm each.

### D-A. Starting dataset set

Recommended seed: **Wikidata + GeoNames** as the v1 grounding sources.

- **Wikidata** — broad coverage (places, products, companies, works,
  public figures) under stable QIDs. Full dump is large (~100GB+
  uncompressed), but a subset filtered to entity types relevant to
  engram is feasible. Snapshot frequency is operator-controlled.
- **GeoNames** — focused, small (~350MB compressed), strong for places
  and administrative geography. A useful complement to Wikidata's
  place coverage.

Open: should v1 also include **OpenStreetMap (Nominatim)** for
fine-grained place lookup? Domain-specific datasets (MusicBrainz,
OpenLibrary, Open Food Facts) are clearly v1.x candidates rather than
v1.

### D-B. Resolver placement

Three placement options; the loop should pick one:

1. **Pre-extraction enrichment.** Run a candidate-resolver pass over
   the segment text first; pass a structured "candidates" block into
   the extraction prompt as additional context. The LLM extracts
   claims that may reference resolved entities by ID.
2. **Post-extraction resolution.** The LLM extracts claims as today.
   A separate pass over the extracted claims tries to resolve subject
   and object surface forms against datasets, attaching candidate
   external references to a sidecar table.
3. **Hybrid.** Resolver runs first and emits a small "you might be
   talking about these" hint block; the LLM extraction stays surface-
   form-based; resolution attachment happens post-extraction with the
   resolver's output already cached.

Recommended seed: **(3) hybrid**, on the bet that nudging the LLM
toward known entities helps quality without forcing it to commit to
QIDs it can't reason about, while keeping resolution attachment as a
clean, testable post-pass.

### D-C. Output shape: candidate set vs. single pick

When multiple resolutions are plausible ("Apple" → Apple Inc., apple
the fruit, Apple Records), should the resolver:

- Pick the highest-confidence candidate and attach it
- Attach the full candidate set with confidences
- Refuse to resolve and surface the ambiguity for interview-time review

Recommended seed: **attach the full candidate set with confidences**.
This honors the refusal-of-false-precision principle: collapsing to a
single ID we are uncertain about bakes errors permanently into the
biography. The interview UI (RFC 0027 / D080) is the right place for
the operator to disambiguate.

### D-D. Schema: where the external reference lives

Three plausible homes:

1. New columns on `entities` (`external_dataset`, `external_id`,
   `external_dataset_version`).
2. New `entity_external_references` table (many-to-one against
   `entities`), allowing an entity to be linked to multiple datasets
   and accumulate references over time.
3. Sidecar `claim_resolutions` table, scoped to claim-level resolution
   without disturbing the entity model.

Recommended seed: **(2) `entity_external_references` table**, because
an entity can legitimately have a Wikidata QID *and* a GeoNames ID
*and* a MusicBrainz MBID; multi-row is natural. The
`projection_audits` cascade (RFC 0018) is the model for how to keep
this auditable.

### D-E. Snapshot discipline

Open: per-dataset versioning, per-extraction-run versioning, or both.

Recommended seed: **per-dataset versioned snapshots, recorded per
resolution.** Each dataset is downloaded as `dataset@snapshot_id`
(e.g., `wikidata@2026-04-15`), stored under
`~/.engram/grounding/<dataset>/<snapshot_id>/`. Each `claim_resolution`
or `entity_external_reference` row records the snapshot used. Multiple
snapshots may co-exist; the active snapshot per extraction run is
explicit (CLI flag or config).

This dovetails with RFC 0017's prompt-version immutability: a claim's
provenance becomes (segment_id, prompt_version, model_version,
{dataset@snapshot}\*).

### D-F. Grant model

Operator grants are per-dataset, recorded in a new
`grounding_grants` table (or equivalent local config). Open:

- Are grants per agent role, per agent process, or global?
- Are grants time-bounded?
- Is there an audit trail of grant exercises?

Recommended seed: **per agent role, persistent until revoked, with an
audit log of access.** A simple `engram grants` CLI surface (`grant
<role> <dataset>`, `revoke`, `list`) keeps the model legible. The
extraction agent role is one of several; striatum's claim-loop agents
get separately-named roles.

### D-G. Extraction prompt impact

If the resolver passes candidates into the extraction prompt
(D-B option 1 or 3), the prompt grows. The current prompt is already
~1500–2500 tokens depending on segment size; adding even a
modestly-sized candidate block per entity-shaped phrase could push
toward the 32k-slot context (RFC 0023 / D076) on long segments.

Open: budget cap on candidate-block size per segment? Truncation
strategy when the cap is hit? Recommended seed: cap at ~1000 tokens
per segment, truncate by descending candidate confidence.

This change bumps `EXTRACTION_PROMPT_VERSION` per RFC 0017.

### D-H. Eval oracle

The eval-as-oracle principle bites hard here: "grounding improves
extraction quality" is the hypothesis, and we need a way to measure it
before claiming the win.

Open: which signal is the oracle?

- Drop in operator `false` verdicts in the entity-mismatch class
  (RFC 0028's failure taxonomy).
- Drop in entity-consolidation merge work (PHASE-0004) per N
  conversations.
- A held-out gold set of pre-resolved entity references that the
  grounded extractor must recover.
- All of the above.

Recommended seed: **operator `false`-rate in the entity-mismatch
class** as the primary signal (cheap to capture, already collected via
RFC 0021 gold-set interview), with PHASE-0004 merge-rate as a
secondary signal once enough corpus has been re-extracted.

The "before/after" measurement protocol should mirror RFC 0017's
re-extraction discipline: run grounded extraction on a bounded slice
first; compare against the v8 baseline; only proceed to full-corpus
re-extraction if the slice shows the predicted improvement.

## Privacy and provenance

The non-negotiable constraints above are the privacy stance. Beyond
those:

- **Provenance.** Each grounded claim records the dataset snapshots
  it consulted. Re-derivation from raw evidence remains possible.
- **Auditability.** The grant model produces a log of which agent
  read which dataset when. Operators can ask "what does the
  extraction agent currently see beyond the corpus?" and get a
  precise answer.
- **Revocability.** Revoking a grant stops future grounding but
  does not retroactively unground existing claims. Re-extraction
  under a no-grant configuration is the operator's tool for
  rolling back grounded provenance, not a silent system action.

## Why this fits the principles

- **Local-first.** Datasets live on disk; queries are in-process; no
  corpus content leaves the machine.
- **Corpus/network separation.** The dataset is a one-way admission
  of (sanitized, public) network content into the local environment;
  the corpus does not flow the other way.
- **Raw-is-sacred.** Raw evidence tables are untouched; grounding is
  applied at the derived-claim layer.
- **Eval-as-oracle.** No grounding wiring lands without a measured
  before/after on the targeted failure class.
- **Refusal-of-false-precision.** The candidate-set output (D-C
  recommended seed) refuses to collapse to a single QID we cannot
  defend.
- **Adversarial-review.** This RFC is explicitly authored to be
  reviewed through striatum's multi-agent loop before implementation.

## What this RFC does not propose

- **No live web calls from the extraction loop.** Stated as a
  non-negotiable constraint, restated here for visibility.
- **No remote LLM calls.** D020's local-only LLM endpoint posture
  remains in force.
- **No grounding for private/personal entities.** PHASE-0004 entity
  consolidation and the local entity store handle "Sarah", "the
  gym", "my parents' house". This RFC is strictly about public
  entities resolvable against public datasets.
- **No change to the gold-set verdict semantics.** RFC 0021 / D044 /
  D069 stand: gold labels remain advisory inputs, even when
  grounding is involved.
- **No change to the raw-evidence tables.** Schema deltas are
  confined to new derived-side tables and a vocabulary table.
- **No silent dataset updates.** Dataset snapshots are
  operator-curated; the system does not auto-refresh datasets in the
  background.

## Open questions for the design loop

The design-space items above (D-A through D-H) each carry open
questions; those are the primary content for the loop. Beyond those:

1. **What is the smallest deliverable that proves the thesis?**
   Recommended: Wikidata-only, places-only resolver, post-extraction
   attachment, on a 100-segment slice. If that does not move the
   `false`-rate needle on the place-mismatch class, the larger design
   needs revision before further build.
2. **How does this interact with RFC 0028's `subject_kind_hint`
   heuristic?** The two efforts share the entity_kind surface. Is
   this RFC a deepening of RFC 0028 (resolution as the high-end of
   the heuristic spectrum) or an orthogonal pass?
3. **How does this interact with PHASE-0004 consolidation?** A
   resolved external reference is strong de-dup signal. Should
   consolidation consume external refs before falling back to text
   similarity? Likely yes; the loop should specify the precedence.
4. **What happens when the resolver disagrees with the user?**
   E.g., user says "Tartine" meaning a friend's nickname; resolver
   wants to attach the bakery. The interview UI is the natural
   correction surface, but the design needs to specify how a
   correction back-propagates: does it suppress future resolution
   for this surface form? In this user's corpus only? Forever?
5. **Cost and storage budget.** A Wikidata subset can land in a few
   GB; a full Wikidata index is ~100GB+. What is the operator-facing
   storage budget the resolver targets? Recommended: ≤10GB total for
   v1, configurable.
6. **Resolution latency.** What latency budget per segment is the
   resolver allowed before it slows the extraction pipeline below
   useful throughput? Bench against the existing pipeline rate.
7. **Failure mode when grants are missing.** If the extraction agent
   has no grants, does extraction proceed without grounding (silent
   downgrade) or refuse to run (loud failure)? Recommended: silent
   downgrade with a one-line warning per run, because grounding is
   an enhancement, not a precondition.

## Promotion path

1. **Striatum-orchestrated multi-agent review** per
   `docs/process/multi-agent-review-loop.md`. The loop should resolve
   D-A through D-H, the open questions above, and produce a tightened
   spec ready for promotion.
2. **Promote the tightened spec** to `docs/specs/0029-*` if accepted,
   following the RFC 0027 / D080 pattern. Record the spec acceptance
   in `DECISION_LOG.md` (next available `D###`). Mark this RFC
   `promoted` and link the spec.
3. **Bench v1 on a 100-segment slice** before any schema or pipeline
   changes land in the main loop. Measure the `false`-rate signal
   from D-H against the v8 baseline. If the slice shows no
   improvement, return to the design loop.
4. **Land schema and resolver in three commits** if the bench passes:
   a. `migrations/0NN_grounding_grants_and_external_refs.sql` —
      new tables for grants, snapshots, and external references;
      append-only triggers consistent with the existing pattern.
   b. Resolver module under `src/engram/grounding/` with explicit
      grant-check at every read; CLI surface `engram grants
      [list|grant|revoke]` and `engram grounding [snapshot|index]`.
   c. Extractor / consolidator integration: extraction prompt bump
      per RFC 0017, post-extraction resolution pass, claim-row
      provenance writes. Update `tests/test_extractor.py` and add
      `tests/test_grounding.py` covering grant enforcement.
5. **Run grounded re-extraction on the consolidated corpus** per
   RFC 0017's `re-extract --version` surface. Old claim rows stay
   under the prior version; grounded rows land alongside.
6. **Re-run interview** against the grounded rows; measure the
   D-H signal. Record the cycle's outcome in `DECISION_LOG.md`.
7. **Iterate dataset coverage** (D-A) only after v1 is producing
   measured value: GeoNames-only extension, then domain-specific
   datasets, each as a separate review cycle.
