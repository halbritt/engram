<a id="rfc-0030"></a>
# RFC 0030: Public-Dataset Entity Grounding for Claim Extraction

| Field | Value |
|-------|-------|
| RFC | 0030 |
| Title | Public-Dataset Entity Grounding for Claim Extraction |
| Status | accepted (revised after design review 2026-05-09) |
| Implementation | none |
| Date | 2026-05-09 |
| Context | RFC 0011 § Schema (claims/beliefs); RFC 0017 (extraction prompt versioning); RFC 0018 (evidence-to-claim audit cascade); RFC 0028 (predicate-intent surfacing — adjacent prompt change); `src/engram/extractor.py:37` (`EXTRACTION_PROMPT_VERSION`); `src/engram/extractor.py:1961` (`build_extraction_prompt`); `migrations/009_phase4_entities_review.sql` (entities table, entity_kind enum); engram principles: local-first, corpus/network separation, raw-is-sacred, eval-as-oracle |

Decision refs:
  - D020 (LLM endpoint is local-only)
  - D044 (gold-set is advisory)
  - D068 (artifact-id model)
  - D076 (32k context budget)
  - D080 (RFC 0027 promotion pattern)

Review refs:
  - [Design review final review](../reviews/rfc0030-grounding-claim-extraction/FINAL_REVIEW.md)
  - [Findings ledger](../reviews/rfc0030-grounding-claim-extraction/FINDINGS_LEDGER.md)
  - [Revision synthesis](../reviews/rfc0030-grounding-claim-extraction/REVISION_SYNTHESIS.md)

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

### Code-side enforcement

The five constraints above are the privacy posture; this subsection
makes them grep-checkable rather than convention-checkable.

- **Forbidden HTTP-client imports** in `src/engram/grounding/resolver.py`,
  `src/engram/grounding/attachment.py`, and `src/engram/extractor.py`.
  The unit test `tests/test_grounding.py::test_no_http_clients` walks
  the AST of these modules and asserts no `urllib`, `requests`,
  `httpx`, `aiohttp`, or socket imports.
- **Sanctioned network module:** `src/engram/grounding/snapshot.py` is
  the *only* module permitted to make outbound network calls. Its
  responsibilities are bounded to (a) downloading a public dataset
  by content-addressed URL, (b) verifying integrity hashes, (c)
  emitting structured progress to stdout/stderr. The module does not
  accept corpus content as a parameter; tests pin this.
- **Single-accessor chokepoint:** every read of an active grant goes
  through `src/engram/grounding/grants.GrantStore.read_active(role,
  dataset)`. Tests assert no other module accesses the grants
  database directly.

### Locked in DECISION_LOG

On RFC acceptance, the five non-negotiables in this section are
promoted to a new `D###` entry in `DECISION_LOG.md` whose body is the
verbatim list above. Any future change to the constraints requires a
new `D###` entry that names the predecessor and explicitly supersedes
it. This protects the boundary against quiet softening.

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

**Position (synthesis 2026-05-09):** v1 ships Wikidata + GeoNames with
filters scoped to the entity classes most-relevant to engram (places,
organizations, products, public figures). OpenStreetMap is deferred
to v1.x; domain-specific datasets (MusicBrainz, OpenLibrary, Open
Food Facts) are deferred until the v1 oracle has produced a measured
result.

Storage budget is enforced, not aspirational: 10GB target, 12GB
hard-fail by default (`ENGRAM_GROUNDING_STORAGE_BUDGET_GB`); warn at
80%. `engram grounding snapshot` refuses to add a new snapshot whose
inclusion would exceed the hard cap.

Operator-facing dataset names ship as aliases to reduce jargon:
`places` → GeoNames + Wikidata-places filter, `companies` →
Wikidata-organizations filter, `public-figures` → Wikidata-people
filter. The CLI accepts either the alias or the explicit dataset id.

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

**Position (synthesis 2026-05-09):** option 3 (hybrid), with three
guards that the original recommended seed lacked.

**Module split.** The hybrid placement decomposes into three testable
units:
- `surface_form_extractor` — scans segment text for entity-shaped
  phrases. Reuses the existing predicate-vocabulary tokenizer.
  Output: `tuple[SurfaceFormSpan, ...]`.
- `candidate_resolver` — maps surface forms to dataset candidates.
  Input: `(surface_form: str, kind_hint: Optional[EntityKind],
  snapshot_pin: SnapshotId)`. Output:
  `tuple[Candidate, ...]` ordered by descending confidence.
- `attachment_writer` — runs as a post-extraction pass; writes
  `entity_external_references` rows linking claim entities to the
  resolver's candidate sets.

**Surface-form normalization.** Surface forms are normalized to
NFKC + lowercase + collapsed whitespace before resolver lookup. The
normalization rule is fixed; lookup indexes are built against the
normalized form. Trade-off: precision over recall (a typo'd surface
form may miss; this is intentional).

**Prompt-shape guard.** Candidates appear in the extraction prompt
under a header that names them as hints, not facts. Verbatim:

```
CANDIDATES-ONLY-HINTS (these are POSSIBLE matches from public
datasets; treat them as suggestions only. The text of the
conversation is the source of truth. Disregard any candidate that
does not match what the segment actually says.)
```

**Dataset content sanitization.** Description fields supplied by the
public dataset (Wikidata `schema:description`, GeoNames description)
are sanitized before insertion: strip control characters, cap length
at 200 characters, reject any field matching prompt-shape patterns
(`### `, `BEGIN`, `<|`, etc.). The candidate carries a sanitized
description or none.

This addresses the bias risk (claude:F004), the dataset-injection
exfil risk (privacy_adversary:P004), and the interview-cost risk
(usability_adversary:U004) raised in design review.

### D-C. Output shape: candidate set vs. single pick

When multiple resolutions are plausible ("Apple" → Apple Inc., apple
the fruit, Apple Records), should the resolver:

- Pick the highest-confidence candidate and attach it
- Attach the full candidate set with confidences
- Refuse to resolve and surface the ambiguity for interview-time review

**Position (synthesis 2026-05-09):** attach the full candidate set
with confidences as `entity_external_references` rows. This honors
refusal-of-false-precision: collapsing to a single ID we are uncertain
about bakes errors permanently into the biography.

**Tracked-export redaction rule.** Tracked artifacts (`docs/reviews/`,
benchmark JSON, RFC 0029 bench-triage exports) MAY record candidate
QIDs / dataset-ids and confidence scores. They MUST NOT include the
descriptive prose attached to those candidates. Resolved-entity
descriptions stay in scratch state.

**Interview UI default.** The interview surface (RFC 0027 / D080)
renders the top-1 candidate above a configurable confidence threshold
(default 0.85), with a "see N more" affordance for the operator to
expand the full set. The full set is not rendered by default. This
keeps interview throughput intact for operators who do not need to
disambiguate every claim.

### D-D. Schema: where the external reference lives

Three plausible homes:

1. New columns on `entities` (`external_dataset`, `external_id`,
   `external_dataset_version`).
2. New `entity_external_references` table (many-to-one against
   `entities`), allowing an entity to be linked to multiple datasets
   and accumulate references over time.
3. Sidecar `claim_resolutions` table, scoped to claim-level resolution
   without disturbing the entity model.

**Position (synthesis 2026-05-09):** option 2,
`entity_external_references` table, with append-only / tombstone /
cascade discipline.

**Schema (DDL sketch):**
- `entity_external_references` columns: `eer_id PRIMARY KEY`,
  `entity_id REFERENCES entities`, `dataset TEXT`,
  `external_id TEXT`, `snapshot_id TEXT`, `confidence NUMERIC`,
  `superseded_by REFERENCES entity_external_references (NULLable)`,
  `created_at TIMESTAMP`.
- Unique constraint: `(entity_id, dataset, external_id, snapshot_id)`.
- Index: `(dataset, external_id)` for resolver lookups.
- Trigger: `BEFORE UPDATE OR DELETE` raises; the table is append-only
  by enforcement.

**Tombstone supersession.** Replacing a resolution inserts a new row
and stores its id in the predecessor's `superseded_by`. Current-state
queries filter `WHERE superseded_by IS NULL AND <grant active>`.
Audit queries see all rows including tombstones.

**Cascade integration with RFC 0018.** Cascade walks the join order
raw evidence → `entities` (via segment_id provenance) →
`entity_external_references` (joined on `entity_id`) → `claims`. When
a snapshot is rolled back (D-E), all `entity_external_references`
rows with that `snapshot_id` are tombstoned by inserting "rolled back"
markers. Claim rows are unaffected; `projection_audits` records the
rollback.

**Live vs audit query semantics.** Live consumer queries filter to
grant-active rows. Audit queries (`projection_audits` and similar)
include all rows. Tests pin both behaviors.

**Backfill semantics.** Claims extracted under prior `prompt_version`
have no `entity_external_references` rows; absence of a join row
means "not grounded under any snapshot." Documented in
`docs/schema/README.md`.

### D-E. Snapshot discipline

Open: per-dataset versioning, per-extraction-run versioning, or both.

**Position (synthesis 2026-05-09):** per-dataset content-hashed
snapshots stored under tightened mode bits, indexed at fetch time,
rolled back via tombstone insertion.

**Snapshot id with content hash.** Snapshot identifier is
`<dataset>@<date>@sha256:<hash>` — for example,
`wikidata@2026-04-15@sha256:abcd1234...`. The hash is computed at
registration time over a Merkle-rooted index of the snapshot's files
and stored in a snapshot manifest. The loader recomputes the hash on
every access and refuses to load on mismatch (loud failure, not
silent). This turns "snapshot reproducibility" from a directory-name
promise into a verifiable invariant.

**Storage layout and mode bits.** Snapshots live at
`~/.engram/grounding/<dataset>/<snapshot_id>/`; directories at
mode 0700, manifest files at mode 0600. Engram refuses to use a
snapshot directory whose permissions are looser. This narrows the
shared-machine fingerprint surface.

**Indexing at fetch time.** The resolver's lookup index (e.g.,
SQLite or Lance over the snapshot subset) is built when the snapshot
is fetched, not lazily on first extraction. `engram grounding
snapshot --dataset <name>` blocks until indexing completes;
extraction never indexes lazily.

**Snapshot rollback semantics.** Rolling back a snapshot tombstones
all `entity_external_references` rows recorded under it (per D-D
cascade); claim rows are unaffected. Re-extraction under a new
snapshot is the operator's path to fresh resolutions. The rollback
itself is an operator-initiated CLI action
(`engram grounding rollback --snapshot-id <id>`); the system never
rolls back automatically.

**Provenance shape (RFC 0017 interaction).** Snapshot provenance
does NOT extend the claim row's `(prompt_version, model_version,
request_profile_version)` tuple. Instead it lives on a new sidecar
table `grounding_resolution_set` keyed by `(claim_id, run_id)` and
storing the set of `(dataset, snapshot_id)` pairs consulted for that
extraction. This preserves RFC 0017's immutability while preserving
reproducibility.

### D-F. Grant model

Operator grants are per-dataset, recorded in a new
`grounding_grants` table (or equivalent local config). Open:

- Are grants per agent role, per agent process, or global?
- Are grants time-bounded?
- Is there an audit trail of grant exercises?

**Position (synthesis 2026-05-09):** per agent role, persistent until
revoked, scratch-SQLite-stored, non-syncing, with templates and
forward-only revocation.

**Storage.** Grants live at `~/.engram/grants/grants.sqlite3`. Schema:
- `grants(role, dataset, granted_at, granted_by, revoked_at NULLable)`.
- `grants_audit(audit_id, role, dataset, action, occurred_at,
  process_pid)` — append-only access log.

**Non-sync stance.** A marker file at
`~/.engram/grants/.engram-no-sync` documents that the grants
directory must not replicate via dotfile sync (chezmoi, mackup,
Dropbox-mounted home, etc.). The grant log is per-machine; tooling
that respects the marker honors that boundary.

**Retention.** Grant-exercise audit rows are kept 90 days, then
truncated. Grant-state rows (`grants` table) are append-only via
`revoked_at` rather than DELETE.

**CLI surface.** `engram grants list [--usage]` (with `--usage` showing
last-accessed dates), `engram grants grant <role> <dataset>`,
`engram grants revoke <role> <dataset>`, `engram grants
apply-template <template> <role>`. Default templates ship:
`places-only`, `places-and-companies`, `everything-public`. The
templates reduce the role × dataset matrix to "pick one of N
templates per role."

**Revocation behavior.** Forward-only. Existing
`entity_external_references` rows persist as historical record. Live
consumer queries filter by grant-active. Audit queries see all rows.
The operator's path to *removing* grounded resolutions is
re-extraction under a no-grant configuration (or `engram grounding
detach` per Q4 below for cheap rollback).

**Default for non-role-typed CLI invocations.** Default is
operator-inherits — a CLI invocation outside a striatum lane runs as
the operator and sees the operator's union of role grants. State
explicitly so future operators do not assume default-deny.

**Run-summary surfacing.** Every extraction run summary includes a
machine-readable line:

```json
{"grounding_status": {"active": true|false,
                      "active_grants": ["wikidata", "geonames"],
                      "lock_state": "matches" | "lost_grants" | "fresh"}}
```

Downstream tooling (RFC 0029 bench triage, benchmarks, interview
exports) detects grounded vs ungrounded runs from this field.

### D-G. Extraction prompt impact

If the resolver passes candidates into the extraction prompt
(D-B option 1 or 3), the prompt grows. The current prompt is already
~1500–2500 tokens depending on segment size; adding even a
modestly-sized candidate block per entity-shaped phrase could push
toward the 32k-slot context (RFC 0023 / D076) on long segments.

**Position (synthesis 2026-05-09):** per-segment cap with
batch-level fail-fast.

- Per-segment cap: 1000 tokens of candidate block per segment,
  truncated by descending candidate confidence. Soft cap (warn);
  fail at 1500 tokens.
- Batch-level cap: in batched extraction (RFC 0019 / RFC 0023), total
  candidate-block tokens across all segments in one request must not
  exceed `CANDIDATE_BATCH_CAP` (default 8000 tokens,
  `ENGRAM_CANDIDATE_BATCH_CAP_TOKENS`). The batched-prompt assembler
  fails fast on overflow with a loud error rather than silently
  truncating; the extraction worker must produce a smaller batch.
- `EXTRACTION_PROMPT_VERSION` bump rule: any change to the
  candidate-block format, the prompt-shape guard sentence, or the
  per-segment cap triggers a version bump per RFC 0017.

### D-H. Eval oracle

The eval-as-oracle principle bites hard here: "grounding improves
extraction quality" is the hypothesis, and we need a way to measure it
before claiming the win. The first version of this section was
fundamentally insufficient — confounded with prompt-version effects,
gameable by coverage drop, under-powered at 100 segments,
selection-biased on slice, and contaminated at the secondary signal.
The position below addresses each of those.

**Three-arm bench (mandatory).** Promotion-grade evaluation uses three
arms, not two:

1. **Arm A — v8 baseline.** Existing prompt, no grounding, the
   pre-existing extraction behavior at the time of the bench.
2. **Arm B — v9 negative control.** New `EXTRACTION_PROMPT_VERSION`
   with the candidate-block format present but grounding *disabled*.
   This isolates the prompt-format effect from the grounding effect.
3. **Arm C — v9 grounded.** New prompt + grounding enabled with the
   active snapshot pin.

Only the **Arm B vs Arm C** comparison isolates the grounding
contribution. Arm A is reported for context (drift over time) but is
not the gate.

**Paired metric (false-rate AND coverage).**

- Primary: operator-`false`-rate on entity-mismatch claims (lower is
  better). RFC 0028's failure taxonomy is the source of truth for
  what counts as an entity-mismatch claim.
- Required paired: coverage = fraction of entity-shaped surface forms
  in the slice that received any candidate attachment at all.
  Reporting only false-rate would let a resolver "win" by suppressing
  low-confidence candidates (lower false-rate, lower coverage, no
  actual quality gain).

Both metrics are reported for both Arm B and Arm C.

**Pre-registered decision rule.**

Promotion to spec → bench → implementation requires:

- Arm C false-rate ≥ **30% relative reduction** vs Arm B false-rate
  on the entity-mismatch class.
- Arm C coverage drop ≤ **5%** vs Arm B coverage.
- Both conditions hold simultaneously.

The thresholds are pre-registered to remove after-the-fact latitude.

**Sample size and slice spec.**

- 100-segment **sanity slice** (same slice as RFC 0028's failure-class
  slice) for fast-fail. If Arm C does not move the false-rate in the
  predicted direction at 100 segments, abort before scaling.
- 600-segment **promotion slice**: stratified random selection across
  the corpus. The 600 figure derives from a Poisson-rate power
  calculation (~5 entity-mismatch events per 100 segments at
  baseline; detecting a 50% reduction at 80% power, alpha 0.05
  requires ~600).
- Both slices reported. The 100 is precondition; the 600 is the gate.

**Independent secondary signal (replaces PHASE-0004 merge-rate).**

PHASE-0004 entity-consolidation merge-rate is *downstream of
grounding* (resolved external refs feed consolidation), so it is a
correlated signal, not an independent one. Drop it as secondary.

The replacement secondary is a held-out gold set of 100 segments with
operator-curated `(surface_form → external_id)` pairs (Wikidata QIDs,
GeoNames ids), built specifically for grounding evaluation.
Reports: precision, recall, F1 of the resolver's top-1 candidate
versus the gold pairs. The gold set is *not* used as the primary
oracle (D044 stands — gold labels are advisory), but a dramatic
precision/recall regression on this set is a separate-axis signal
that something is wrong with the resolver itself even if Arm C
false-rate is fine.

**Baseline reproducibility.**

Arm A (v8 baseline) artifacts must be content-hash-pinned and
verified at bench preflight. If the cached v8 artifacts are
unavailable or stale, the bench is blocked until the operator either
re-runs v8 under the original `(prompt_version, model_version,
request_profile_version)` or accepts a v9-disabled run as the
new baseline (and loses the historical comparison, which the bench
preflight states explicitly).

**Bench-and-iterate cost (operator-honest).**

A full promotion-grade bench cycle (Arm A regen if needed + Arm B +
Arm C + 600-segment interview pass) is on the order of **6-12
operator-hours** plus **2-6 wall-clock hours** of compute. The
promotion path's "iterate dataset coverage only after v1 produces
measured value" applies; the iterate cost is real.

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
  position) refuses to collapse to a single QID we cannot defend.
  The D-B prompt-shape guard prevents premature collapse to a single
  ID at extraction time, even when a high-confidence candidate is
  available.
- **Adversarial-review.** This RFC was explicitly authored to be
  reviewed through striatum's multi-agent loop before implementation,
  and was so reviewed (8 lanes, including 5 adversarial lenses) on
  2026-05-09. The five non-negotiables are grep-checkable in the
  resulting code (see § Non-negotiable constraints / Code-side
  enforcement), not just stated in this document.

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

## Open questions, resolved

The design loop took explicit positions on each. They are recorded
here for future readers and as inputs to the spec-authoring run.

1. **Smallest deliverable that proves the thesis.** 100-segment
   sanity slice (Wikidata-places-only, post-extraction attachment) for
   fast-fail; **600-segment stratified random slice as the
   promotion gate.** The single-stage 100-segment claim from the prior
   draft was under-powered by ~6x; sample-size revision is the most
   consequential D-H change.
2. **Interaction with RFC 0028 `subject_kind_hint`.** **Deepening with
   type-narrowing.** When RFC 0028 supplies `subject_kind=person`, the
   resolver narrows the candidate-type filter to person-class
   candidates. When the operator's interview verdict disagrees with
   either, the verdict wins and supersedes the candidate set.
3. **Interaction with PHASE-0004 consolidation.** External refs are a
   strong de-dup signal; **consolidation consumes them before
   falling back to text similarity.** Two candidate-merge entities
   sharing an `(dataset, external_id)` pair are presumptively merged;
   conflicting refs require operator intervention. PHASE-0004
   merge-rate is no longer a grounding oracle (D-H removes it from
   the bench); it is a downstream consumer.
4. **Resolver disagrees with the user.** **Per-corpus private alias
   suppression.** The operator's interview verdict on a wrong
   grounding case populates a `private_aliases` table at
   `~/.engram/grounding/private_aliases.sqlite3`:
   `(surface_form, scope, reason, suppressed_dataset,
   suppressed_external_id)`. Scope is per-segment (precise) or
   per-corpus (broad); operator picks. The resolver consults
   `private_aliases` before any dataset; matching aliases yield no
   attachment.
5. **Storage budget.** **10GB target, 12GB hard-fail by default**
   (`ENGRAM_GROUNDING_STORAGE_BUDGET_GB`). Warn at 80%. `engram
   grounding snapshot` refuses to add a new snapshot whose inclusion
   would exceed the hard cap.
6. **Resolution latency.** **≤100ms per segment with fail-fast on
   overflow; ≤2x extraction time per corpus.** A segment whose
   resolution exceeds the per-segment budget skips resolution (one
   warning per run, surfaced in the run summary). The resolver caches
   per-process via an LRU keyed by `(surface_form, snapshot)` capped
   at 100k entries.
7. **Failure mode when grants are missing.** **Silent downgrade in
   the extraction path; loud surfacing in the run summary; lock-file
   detection of prior-grants-now-absent.**
   - Default: extraction proceeds without grounding (conservative
     ergonomics).
   - Run-summary JSON includes `grounding_status` (per § D-F);
     downstream tooling detects ungrounded runs.
   - Lock file at `~/.engram/grounding/active-grants.lock` records
     prior grants. If extraction starts and the difference between
     current grants and the lock is "lost grants", interactive runs
     prompt; non-interactive runs fail unless `--ungrounded-ok` is
     passed.

The design-loop synthesis is recorded at
`docs/reviews/rfc0030-grounding-claim-extraction/REVISION_SYNTHESIS.md`.

## Promotion path

1. **Striatum-orchestrated multi-agent review** per
   `docs/process/multi-agent-review-loop.md`. The loop should resolve
   D-A through D-H, the open questions above, and produce a tightened
   spec ready for promotion.
2. **Promote the tightened spec** to `docs/specs/0030-*` if accepted,
   following the RFC 0027 / D080 pattern. Record the spec acceptance
   in `DECISION_LOG.md` (next available `D###`). Mark this RFC
   `promoted` and link the spec.
3. **Bench v1 on a 100-segment slice** before any schema or pipeline
   changes land in the main loop. Measure the `false`-rate signal
   from D-H against the v8 baseline. If the slice shows no
   improvement, return to the design loop.
4. **Land schema and resolver in four commits** if the bench passes.
   The original three-commit framing under-weights the realistic
   1500-3000 LOC implementation footprint. Split:
   a. `migrations/0NN_grounding_grants_and_external_refs.sql` — new
      tables for grants, snapshots, `entity_external_references`, and
      `grounding_resolution_set`; append-only triggers; index list
      with `CONCURRENTLY` annotations where required; idempotent.
      Snapshot-internal indexes live outside production PG (under
      `~/.engram/grounding/<snapshot>/index/`).
   b. `src/engram/grounding/` module with `snapshot.py` (the only
      sanctioned-network module), `resolver.py`, `attachment.py`,
      `grants.py` (single-accessor chokepoint), and `private_aliases.py`.
      CLI surface: `engram grants {list,grant,revoke,apply-template}`
      and `engram grounding {snapshot,rollback,detach,versions}`.
      `tests/test_grounding.py` covers grant enforcement,
      `test_no_http_clients` AST walk, and resolver determinism.
   c. Extractor integration: prompt-version bump per RFC 0017,
      candidate-block assembly with the prompt-shape guard,
      per-segment / per-batch budget enforcement, post-extraction
      attachment writes, run-summary `grounding_status` field.
      Update `tests/test_extractor.py`.
   d. Consolidator integration: PHASE-0004 consolidation consumes
      external refs before text-similarity (Q3 precedence).
      `projection_audits` integration so the cascade sees grounding
      tombstones. Update `tests/test_consolidator.py`.

   **Iteration cost (operator-honest):** each promotion-path bench
   cycle is on the order of **6-12 operator-hours plus 2-6 wall-clock
   compute hours** (per D-H). Plan iterations accordingly.
5. **Run grounded re-extraction on the consolidated corpus** per
   RFC 0017's `re-extract --version` surface. Old claim rows stay
   under the prior version; grounded rows land alongside.
6. **Re-run interview** against the grounded rows; measure the
   D-H signal. Record the cycle's outcome in `DECISION_LOG.md`.
7. **Iterate dataset coverage** (D-A) only after v1 is producing
   measured value: GeoNames-only extension, then domain-specific
   datasets, each as a separate review cycle.
