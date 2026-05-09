# RFC 0030 Public-Dataset Entity Grounding Adversarial Schema Review

author: schema-adversary-codex-gpt-5.5-001

Status: review
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

Lens: adversarial schema and migration — D-D placement, append-only
invariants, RFC 0017/0018 versioning compatibility, downgrade
reversibility.

## Findings

### S001 - D-D option 2 (entity_external_references) wins for the multi-dataset case but its append-only story is incomplete
Severity: major
Source: § D-D; § Why this fits the principles (raw-is-sacred)

Option 2 (separate table) is correct for the case "Tartine entity has
a Wikidata QID and a GeoNames id and a MusicBrainz MBID later." The
RFC stops there, but the schema choice has a derived-side append-only
problem the RFC does not address:

What happens when a snapshot is rolled back (D-E) and the
entity_external_references rows recorded under that snapshot need to
be invalidated? Three options:

1. UPDATE rows to mark invalid — violates append-only.
2. Delete rows — violates append-only.
3. Insert tombstone rows that supersede the prior reference — preserves
   append-only but adds a "current state" view layer.

Option 3 is correct under engram's existing pattern (RFC 0018 audit
cascade does similar). The RFC does not commit to option 3, leaving
the door open to a tempting UPDATE that breaks invariants.

Failure mode: a future implementation rolls back a snapshot, runs an
UPDATE to invalidate rows, and the audit cascade no longer sees the
prior resolutions. RFC 0018's view of "what was true when" is broken
for grounding.

Suggested fix: D-D option 2 must add: "entity_external_references is
append-only; supersession uses tombstone rows (column:
`superseded_by` referencing the new row, NULL for current). A
materialized view or query-time filter resolves to current."

### S002 - Snapshot rollback semantics not specified for already-extracted claims
Severity: major
Source: § D-E; § Promotion path step 5

If an operator pins `wikidata@2026-04-15`, runs grounded extraction on
their corpus, then learns the snapshot was tampered with and rolls back
to `wikidata@2026-03-01`:

- Claim rows under the old prompt_version stay valid (RFC 0017
  immutability).
- entity_external_references rows under the rollback'd snapshot are
  factually wrong but the schema doesn't know it.
- The operator wants those resolutions invalidated without losing the
  underlying claim provenance.

The RFC does not name a mechanism. The implementer can guess (insert
tombstones marked "snapshot rolled back"), but every implementer will
guess differently.

Suggested fix: D-E should commit to a snapshot-rollback procedure:
"Rolling back snapshot X invalidates all entity_external_references
recorded under X via tombstone insertion. The claim row is unaffected.
Re-extraction under a new snapshot is the operator's path to fresh
resolutions."

### S003 - RFC 0017 prompt-version immutability and grounding interaction is too cute
Severity: major
Source: § Why this fits the principles (eval-as-oracle); § Promotion
path 5

RFC 0017 says (prompt_version, model_version, request_profile_version)
is immutable per claim. The grounding RFC says "each grounded claim
records which dataset(s) at which snapshot version contributed to its
resolution."

Question: is `dataset@snapshot` part of the prompt_version tuple, a
parallel tuple on the claim row, or stored separately on
entity_external_references?

If it's part of prompt_version, then the *prompt_version* string itself
encodes the snapshot — meaning a snapshot bump forces a
prompt_version bump even though the prompt didn't change. That violates
the spirit of RFC 0017.

If it's a parallel tuple on the claim row, the claims table grows new
columns for every dataset; brittle.

If it's stored separately on entity_external_references, the claim row
only records "I was grounded" without specifying *against what world*,
and reproducibility is broken.

Suggested fix: the right choice is "stored separately on
entity_external_references, AND a per-extraction-run
`grounding_resolution_set` row that pins the (claim_id, run_id,
snapshot_pin_set) tuple." This costs one extra table but cleanly
separates concerns.

### S004 - RFC 0018 audit cascade integration not specified
Severity: major
Source: § D-D option 2; references to RFC 0018

RFC 0018 cascades supersession from raw evidence (segments) through
claims to projections. The grounding layer adds a sidecar table
(`entity_external_references`); when does the cascade visit it?

Three behaviors the RFC must pick from:
1. external_references rows cascade-supersede when their parent
   `entities` row supersedes. (Likely correct.)
2. external_references rows independently supersede when their snapshot
   is rolled back. (Different cascade root.)
3. Both. (Most correct; most complex.)

The current RFC implies (1) but doesn't say. (2) is needed for
snapshot-rollback semantics from S002. (3) has the right behavior but
the RFC needs to spell out the join order at cascade time.

Suggested fix: D-D should commit to behavior (3) and specify that the
cascade query orders: raw evidence → entities → entity_external_references
(joined on entity_id) → claims (joined on entity_id and any external_id
match).

### S005 - The grant log is itself a schema decision and is unspecified
Severity: minor
Source: § D-F; § Privacy and provenance

The grant log is a sequence of (timestamp, role, dataset, action,
operator) rows. It's append-only. It needs an artifact id (D068). It
may live in scratch SQLite (per the privacy-adversary review's P005),
in which case it is not under the same migration discipline as
production tables.

Suggested fix: D-F must commit to grant-log location (scratch SQLite
preferred), the schema (column types, indexes), and the ID convention
(`gnt_*` per D068).

### S006 - Backfill semantics for old claims missing
Severity: minor
Source: § Promotion path step 5; § D-D

When grounding is enabled, claims extracted under prior prompt_versions
exist in the `claims` table. They have no entity_external_references
rows. Are they:

- Implicitly "ungrounded" — semantically distinguishable by the absence
  of a join row?
- Marked explicitly with a tombstone or "ungrounded" flag?

The first is what the RFC implies. The second is what some downstream
consumers (e.g., the bench-triage workbench from RFC 0029) might want
to query against.

Suggested fix: state explicitly that absence of an
entity_external_references row means "not grounded under any snapshot."
Document this in `docs/schema/README.md` so consumers don't reinvent
it.

### S007 - Index discipline at install scale not specified
Severity: minor
Source: § Promotion path step 4a

The new tables need:
- entity_external_references: probably (entity_id) index, (dataset,
  external_id) unique index.
- snapshots: (dataset, snapshot_id) unique.
- grants: (role, dataset) unique.

Wikidata has tens of millions of entities. An external-references table
indexed by (dataset, external_id) for fast resolver lookups is fine,
but if the operator runs `engram grounding index` to materialize
snapshot indexes inside the production DB, the index size could
balloon.

Suggested fix: clarify whether the snapshot's *internal* index lives
in production PG (probably not — too large) or in a separate
SQLite/Lance index under `~/.engram/grounding/<snapshot>/index/`.
The latter is the right answer; pin it.

### S008 - Downgrade reversibility produces orphan rows
Severity: minor
Source: § Privacy and provenance (revocability)

If grounding is enabled, runs for a while, then is disabled by grant
revocation: existing entity_external_references rows persist (correct
under append-only). But the system now has rows whose live lookup
behavior depends on grants the operator no longer holds.

The right behavior is "rows persist as historical record; live joins
to entity_external_references silently filter to grant-active rows."
That is enforceable but not stated.

Suggested fix: D-F should add: "Live consumer queries
(extraction-time, interview-time) filter
entity_external_references on grant-active. Audit queries
(`projection_audits`) include all rows. Tests pin both behaviors."

## Migration footprint

A reasonable v1 estimate:
- 3 new tables (grants, snapshots, entity_external_references).
- 1 grant-log table OR 1 scratch SQLite database.
- 5-7 indexes.
- 1 trigger to enforce append-only on entity_external_references.
- Snapshot indexes live outside production PG.

`migrations/0NN_grounding_grants_and_external_refs.sql` is achievable
in ~150 lines including triggers, but only if S001-S004 are addressed
in the spec.

verdict: accept_with_findings
