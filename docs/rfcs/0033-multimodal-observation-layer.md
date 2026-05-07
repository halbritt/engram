<a id="rfc-0033"></a>
# RFC 0033: Multimodal Observation Layer

Status: proposal
Date: 2026-05-07
Context: `HUMAN_REQUIREMENTS.md` sections time-indexed biography, domain
coverage, locations, photos and media, gaps as data; `README.md` section
Architecture;
DECISION_LOG D002, D003, D018, D019, D020, D021, D022, D032, D051

This is an idea-capture RFC, not an accepted architecture decision. It
proposes a general observation layer for multimodal and non-conversational
evidence so photos, location history, calendar, health, finance, and future
source families do not each invent their own path from raw data to beliefs.

The core claim: not every derived fact in Engram should become a claim or a
belief. A model saying "this image contains Alice" or "this GPS sample is
near SFO" is an evidence-backed observation. It may later support a claim, an
event, a place visit, a daily summary, or a relationship inference, but it is
not itself the same kind of thing as "Alice was my close friend in 2023" or
"I lived in Oakland from 2018 to 2022."

## Background

The current V1 architecture is intentionally text-shaped:

```text
sources
  -> conversations / messages / notes / captures
  -> segments
  -> claims
  -> beliefs
  -> context_for(conversation)
```

That shape is right for AI-conversation history. Messages are segmented into
topic-coherent text units. A local LLM extracts atomic claims. A deterministic
consolidator turns claims into bitemporal beliefs.

The long-arc human requirements are broader. Photos, videos, EXIF data,
Google or Apple location history, calendar events, receipts, health samples,
and activity traces all produce observations whose natural unit is not a
textual claim:

- A photo's EXIF metadata says it was captured at a timestamp and coordinate.
- A face detector finds a face bounding box in an image.
- A face clustering pass groups that face with other faces.
- A local vision model classifies the scene as a restaurant.
- A location sample records latitude, longitude, accuracy, and source time.
- A visit inference groups samples into "probably at SFO from 08:20 to 09:10."
- A calendar event says "Dinner with Alice" on the same evening.

Forcing these directly into the claim/belief pipeline creates two hazards:

1. **False precision.** "This image contains Alice" at confidence 0.78 is not
   a stable relationship belief. Treating it as one gives downstream consumers
   the wrong certainty signal.
2. **Bespoke pipelines.** If each new source family creates its own hidden
   derived tables, Engram loses the general provenance/versioning discipline
   that makes raw evidence portable across model generations.

## Proposal

Introduce a general **observation layer** between raw evidence and semantic
state:

```text
raw evidence / raw artifacts
  -> observations
  -> events / visits / media annotations / claim candidates
  -> claims / beliefs / daily summaries / context lanes
```

An observation is an atomic, source-backed or model-derived statement about
some artifact, time, place, entity, or measurement. Observations are not
authoritative beliefs. They are versioned, rebuildable, confidence-bearing
evidence records.

### Definitions

**Raw evidence.** Immutable source rows or artifact records. Examples:
`messages`, `captures`, future `media_assets`, imported location history
files, calendar export rows, or health export rows. Raw evidence is never
updated or deleted in place.

**Observation.** A normalized assertion extracted from raw evidence or from a
local derivation over raw evidence. It carries provenance, confidence,
privacy tier, temporal coordinates, and derivation metadata. Examples:
`media_exif_timestamp`, `media_exif_coordinate`, `face_detected`,
`face_cluster_member`, `image_scene_label`, `location_sample`,
`place_visit_candidate`, `calendar_event_time`, `ocr_text_span`.

**Interpretation.** A higher-level derived unit composed from observations.
Examples: a photo event cluster, a place visit interval, a "people present"
candidate, a travel episode candidate, or a daily event candidate. Some
interpretations may eventually emit claims. Others may feed context lanes or
daily summaries directly.

**Belief.** A consolidated, bitemporal semantic memory that survives the
claim/belief rules. Beliefs remain downstream of claims and must cite raw
evidence. Observations can help create claims, but observations do not replace
the raw evidence requirement.

### Observation contract

Every observation should carry:

- `id`
- `observation_type`
- `source_id` and source family
- one or more raw evidence references
- optional parent artifact reference
- optional subject reference, if the observation is about an entity candidate
- `object_json`, typed by `observation_type`
- `observed_at`, when the underlying thing happened if known
- optional `valid_from` / `valid_to` for interval observations
- optional spatial fields or a reference to a place/geometry row
- `confidence`
- `privacy_tier`
- `derivation_kind`, such as `raw_metadata`, `deterministic_parser`,
  `local_model`, `human_label`, or `imported_local_label`
- `derivation_version`
- `model_version` and `prompt_version`, where a model is involved
- `raw_payload` preserving source-specific or model-specific details

The schema should enforce two invariants:

1. An observation must cite raw evidence or a raw artifact. It may also cite
   input observations, but it cannot be grounded only in another observation.
   This preserves D002/D003's anti-synthesis-cascade principle.
2. Observation types must be governed by a lookup table, analogous to
   `predicate_vocabulary`, so model outputs cannot invent ad hoc observation
   shapes.

### Observation type vocabulary

The initial vocabulary should be small and source-family-oriented:

| observation type | object shape | likely source |
|---|---|---|
| `media_exif_timestamp` | `{captured_at, timezone_hint}` | photo/video metadata |
| `media_exif_coordinate` | `{latitude, longitude, altitude, accuracy?}` | photo/video metadata |
| `media_camera_metadata` | `{make?, model?, lens?, software?}` | photo/video metadata |
| `image_scene_label` | `{label, taxonomy?, score}` | local vision model |
| `image_object_label` | `{label, box?, score}` | local vision model |
| `image_ocr_text` | `{text, box?, language?, score}` | OCR |
| `face_detected` | `{box, embedding_ref?, quality}` | local face detector |
| `face_cluster_member` | `{cluster_id, distance}` | local clustering |
| `person_label_candidate` | `{person_name?, entity_id?, source}` | human/imported label |
| `location_sample` | `{latitude, longitude, accuracy, source_time}` | location export |
| `place_visit_candidate` | `{place_candidate_id, start, end, evidence_count}` | visit inference |
| `coverage_gap` | `{domain, start, end, reason}` | coverage compiler |

This table should be additive. New source families add observation types, not
unstructured JSON folklore.

### Privacy inheritance

Observation privacy tier is the maximum of:

- all cited raw evidence tiers,
- parent artifact tier,
- observation type default tier,
- any local reclassification capture that applies to the source artifact.

Exact coordinates, face embeddings, face clusters, and raw OCR text should
default to Tier 1 unless a later privacy RFC chooses stricter defaults. Derived
coarse observations can be lower tier only if explicitly designed that way,
for example "city=San Francisco" derived from exact coordinates.

Privacy reclassification must invalidate retrieval-visible observations and
any downstream derived rows, following the same parent-scoped logic as D028
and D032.

### Derivation versioning and rebuilds

Observation rows are derived cache unless they come directly from raw source
metadata. Re-running a face detector, OCR model, EXIF parser, or visit
inference creates a new generation of observations. Prior observations remain
auditable and may be marked inactive, superseded, or generation-scoped without
being deleted.

The observation layer should reuse the Phase 2/3 discipline:

- deterministic parser version strings for metadata stages,
- local model version strings for ML stages,
- prompt/request-profile versions where a local LLM is used,
- resumable progress rows for long backfills,
- no network egress from corpus-reading processes.

### Relationship to claims and beliefs

Observations can support claims in at least three ways:

1. **Direct claim evidence.** A human-reviewed observation may support a
   claim, but the resulting claim must still cite the original raw evidence
   or artifact, not only the observation row.
2. **Candidate generation.** Observation clusters can propose claim candidates
   for human or local-model review: "photos and calendar suggest dinner with
   Alice on 2023-06-14."
3. **Context lanes without beliefs.** Some observations should never become
   beliefs but should still answer queries. For example, "photos exist from
   this day" or "location coverage is sparse" belongs in a context or daily
   lane, not in `beliefs`.

This RFC does not change the V1 claim/belief pipeline. It gives future
non-text ingestion a compatible substrate.

## Non-goals

- Implementing photos, location history, calendar, health, or any specific
  source family. Follow-up RFCs define those.
- Replacing claims and beliefs. The observation layer is below them.
- Allowing remote model APIs. Local-only and no-egress constraints remain.
- Choosing a graph backend, geospatial extension, vector model, OCR model, or
  face-recognition stack.
- Making all observations retrieval-visible by default.

## Open questions

1. Should observations live in one wide table plus type-specific JSON, or in a
   common parent table plus typed child tables for high-volume families such
   as location samples and face detections?
2. Should there be an `observation_generations` table analogous to
   `segment_generations`, or is `(observation_type, derivation_version)`
   enough for the first implementation?
3. How should raw artifact references be represented when source families do
   not map onto existing `conversations`, `messages`, `notes`, or `captures`?
   A future `raw_artifacts`/`media_assets` table is likely, but this RFC does
   not choose the shape.
4. Which observations can be surfaced to ordinary AI-assistant context, and
   which require an explicit query plus a higher privacy grant?
5. Should observations get embeddings, or should embeddings stay at the
   interpretation/event layer where text summaries are more stable?

## Acceptance criteria for promotion

This RFC is ready to promote when a concrete source-family implementation
needs a shared derived-evidence substrate. Promotion should produce:

- an accepted observation vocabulary seed,
- a schema migration or accepted implementation spec for observation storage,
- privacy inheritance and reclassification invalidation rules,
- a derivation-generation contract,
- at least one source-family RFC using the layer without bypassing raw
  provenance.

Until then, this RFC is design guidance for post-V1 multimodal expansion.
