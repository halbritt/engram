<a id="rfc-0034"></a>
# RFC 0034: Photo Library Ingestion And Local Vision Derivations

Status: proposal
Date: 2026-05-07
Context: RFC 0033; `HUMAN_REQUIREMENTS.md` sections photos and media,
locations, genealogy and relationships, sensory / embodied memory;
DECISION_LOG D002, D003, D018, D019, D020, D021, D023, D032

This is an idea-capture RFC, not an accepted architecture decision. It
proposes a post-V1 ingestion pipeline for a local phone photo corpus: preserve
the original media metadata, derive local-only visual observations, cluster and
label faces under human control, and feed photo-derived evidence into later
location, relationship, event, and daily-biography projections.

The goal is not "make photos searchable" in isolation. The goal is to let
Engram answer biographical questions such as "Who was I with that night?",
"Where was this taken?", "What were we doing on that day?", and "What did
summer 2023 look like?" without sending images or embeddings to a hosted
service.

## Background

`HUMAN_REQUIREMENTS.md` currently defers full photo ingestion to V2+ because
the overhead is high: EXIF parsing, on-device facial recognition, scene
recognition, and storage all arrive before immediate V1 value. That deferral
is still correct.

The eventual scope is explicit:

> not just the file. Who is in it. Where. Why we were there. What was
> happening just before and after. The inside joke embedded in it.

That scope is broader than media indexing. A photo is a dense bundle of
time, place, people, objects, text, social context, and emotional memory. The
pipeline should treat the original file as sacred raw evidence and every
classification, caption, OCR span, face cluster, or event grouping as a
rebuildable observation.

## Problem

A phone photo library is large, personally sensitive, and semantically noisy.
Several naive designs would break Engram's core properties:

- Uploading images to a hosted vision API violates the local-first constraint.
- Storing only generated captions throws away the raw evidence and makes future
  model improvements impossible to apply.
- Letting a face-recognition model silently name people turns uncertain visual
  matches into overconfident relationship facts.
- Treating every photo as a claim-bearing memory floods the claim/belief layer
  with low-value or repetitive entries.
- Ignoring screenshots loses one of the most useful non-camera photo classes:
  receipts, conversations, maps, code, tickets, memes, and UI state.

The pipeline needs strong separation:

```text
media asset
  -> metadata observations
  -> visual observations
  -> face clusters / person label candidates
  -> photo event clusters
  -> optional claims / daily summaries / context lanes
```

## Proposal

### Source scope

The first photo corpus backfill should support local files and local exports:

- Apple Photos library export or filesystem export,
- Google Photos Takeout,
- direct camera-roll directory,
- sidecar metadata files where present.

The first version should not call Apple Photos cloud services, Google Photos
APIs, iCloud APIs, or any hosted classifier. Google Photos Takeout is
acceptable because it is a user-requested local export already on disk.

### Raw media asset records

Add a raw media asset family, likely as a new table rather than overloading
`captures`:

- `id`
- `source_id`
- `source_kind`
- `external_id`
- `imported_at`
- `filesystem_path`
- `content_hash`
- `perceptual_hash`
- `media_kind` (`photo`, `video`, `live_photo`, `screenshot`, `burst`,
  `edited_derivative`, `sidecar`)
- `created_at` from source metadata when available
- `source_timezone` or timezone hint
- `width`, `height`, duration for video
- `mime_type`
- `privacy_tier`
- `raw_payload`

The binary file itself should not be stored in ordinary Postgres rows. The
first design should reference local files by path and content hash, with an
open option for a managed content-addressed media store later. Either way, the
database must be able to detect file movement or content drift without
rewriting raw records.

Raw EXIF and export sidecars are preserved in `raw_payload`. Normalized fields
are convenience indexes; the raw metadata remains the source of truth.

### Metadata observations

The deterministic parser stage emits observations such as:

- `media_exif_timestamp`
- `media_exif_coordinate`
- `media_camera_metadata`
- `media_edit_relationship`
- `media_duplicate_candidate`
- `media_screenshot_app_hint`

EXIF timestamps are often timezone-ambiguous. The parser should preserve:

- raw timestamp string,
- timezone offset if present,
- source timezone hint,
- imported filesystem timestamps,
- confidence in the normalized `observed_at`.

The system should prefer an honest uncertain timestamp over a clean but
invented one.

### Local vision observations

The local-only model stage emits rebuildable observations:

- image embedding references for visual similarity,
- scene labels,
- object labels and optional bounding boxes,
- generated captions,
- OCR text spans,
- aesthetic or quality signals where useful for clustering,
- screenshot text and UI hints.

Generated captions are descriptions, not beliefs. They should be versioned by
vision model and prompt/request profile, and they should cite the media asset.

### Face detection, clustering, and naming

Faces need stricter semantics than ordinary object labels.

Pipeline:

```text
face detection
  -> face embedding
  -> face cluster
  -> person label candidate
  -> human-confirmed person/entity link
```

Rules:

- A face detector may create `face_detected` observations.
- A clustering pass may group faces into stable local clusters.
- Imported local labels from Apple Photos or Google Takeout are raw evidence
  from that export, not guaranteed truth.
- A local model may propose label candidates only if the evidence is already
  local.
- A person name becomes a durable entity link only through human confirmation
  or an explicit imported local label policy accepted by a later RFC.

The system should never silently turn a face match into a belief such as
"Alice attended this event" or "Alice is associated with this place." Those
can be candidate interpretations requiring provenance, confidence, and review.

Face embeddings and clusters default to Tier 1. They are biometric data.

### Photo event clustering

A photo event cluster groups assets by time, location, visual similarity, and
people/face clusters:

```text
assets + metadata observations + visual observations
  -> photo_event_candidate
```

Example:

```text
2023-06-14 18:20-21:40
Mission District, San Francisco
12 photos
face clusters: P003, P017
scene labels: restaurant, food, group photo
confidence: 0.82
```

This is not yet a belief. It is an interpretation that can feed the daily
biography compiler, a relationship/co-presence review queue, or an explicit
query result.

### Integration with location

EXIF coordinates should feed the location timeline RFC as one location source.
The same coordinate can have multiple interpretations:

- exact coordinate observation,
- nearest known place candidate,
- coarse city/region for lower-tier context,
- visit interval evidence when adjacent photos cluster in time.

The photo pipeline should not own canonical place resolution. It emits
coordinate and media-context observations; RFC 0035 owns place and visit
semantics.

### Integration with claims and beliefs

Photo-derived evidence can eventually support claims, but with high friction:

- "Photo X contains Alice" is a face/person observation.
- "I was with Alice on 2023-06-14" is an event candidate supported by photos,
  location, calendar, and/or messages.
- "Alice and I were close friends in 2023" is a relationship belief and should
  require repeated interactions or explicit textual evidence, not one photo.

This preserves the distinction between seeing a face, attending an event, and
inferring a relationship.

## Operational shape

The first implementation should be a batch backfill, not live sync:

1. Register source export.
2. Scan media files and sidecars.
3. Insert immutable media asset records.
4. Parse EXIF and sidecar metadata.
5. Generate thumbnails or low-resolution working images locally if needed.
6. Run local vision stages in resumable batches.
7. Run face clustering in resumable batches.
8. Present clusters and ambiguous labels for human review.
9. Emit photo event candidates.
10. Feed accepted/candidate outputs to location and daily biography lanes.

Each long-running stage uses progress checkpoints and generation/version
metadata. Failed files should quarantine individually rather than blocking the
entire library.

## Non-goals

- Shipping this in V1.
- Hosted vision, hosted OCR, hosted face recognition, or remote embeddings.
- Silent person identification.
- Full video transcription or audio analysis in the first photo RFC.
- Replacing a photo manager such as Apple Photos.
- Editing, moving, deduplicating, or deleting the user's original files.
- Treating every photo as retrieval-visible context.

## Open questions

1. Is a content-addressed local media store worth the complexity, or should the
   first implementation reference files in place and detect drift by hash?
2. Should screenshots be a first-class `media_kind` with OCR-first handling,
   or simply photos with extra labels?
3. What local face-recognition stack is acceptable for accuracy, auditability,
   and long-term maintainability?
4. How should imported Apple/Google person labels be trusted: raw evidence
   only, provisional entity links, or human-confirmed links if the user opts
   in?
5. Should generated captions be embedded directly, or should only event
   summaries and selected OCR text become searchable?
6. What is the default retention/retrieval policy for face embeddings if the
   user later reclassifies a person or source to a stricter privacy tier?

## Acceptance criteria for promotion

This RFC is ready to promote when:

- RFC 0033's observation layer has an accepted storage shape or spec handoff,
- a local export format is selected for the first backfill,
- a media asset raw table design is accepted,
- face-cluster privacy and human-labeling rules are accepted,
- a bounded sample run demonstrates idempotent ingest, metadata parsing,
  local derivation versioning, and no network egress.

Until then this RFC records the intended photo-library shape and keeps the
current V1 roadmap undisturbed.
