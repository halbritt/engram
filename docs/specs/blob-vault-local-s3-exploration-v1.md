# Blob Vault Local S3-Compatible Exploration

| Field | Value |
|-------|-------|
| Spec | blob-vault-local-s3-exploration-v1 |
| Title | Blob Vault Local S3-Compatible Exploration |
| Status | proposal |
| Date | 2026-05-17 |
| Source decisions | [D092](../../DECISION_LOG.md#d092) |
| Related design | [local-backup-key-tier5-design-v1](local-backup-key-tier5-design-v1.md), [RFC 0051](../rfcs/0051-generic-evidence-reference-index.md) |
| Source plan | `ARCHITECTURE_RECOMMENDATION_EXECUTION_PLAN_2026-05-16.md` Phase 11 |

This document scopes the A11 blob-vault exploration. It is not an accepted
implementation contract and it does not select a storage product. Its purpose
is to make the local S3-compatible endpoint experiment concrete without
weakening Engram's local-first boundary.

## Purpose

Postgres should not become the byte store for full photo libraries, audio,
video, OCR-heavy documents, medical PDFs, large logs, or other high-volume
sensitive bodies. Engram needs a local encrypted blob vault whose metadata can
be cited and governed from Postgres while bytes stay in a dedicated local
storage substrate.

D092 separates this track from backup/key management. The two tracks interact
through encryption and restore, but the blob vault can be explored separately.

## Scope

The first exploration covers:

- a local, containerizable, S3-compatible endpoint;
- client-side encryption before object upload;
- content-addressed immutable object keys;
- Postgres metadata shape for future `evidence_blobs`;
- failure modes for endpoint unavailable, corrupt object, auth failure, and
  unauthorized render.

## Non-Goals

- No AWS S3, hosted object store, cloud backup, or background sync.
- No remote presigned URLs, public buckets, or non-loopback corpus-serving
  endpoint.
- No live source-family ingestion is approved by this spec.
- No migration of existing small text bodies is required.
- No generated products become retrieval-visible through this spec.
- No storage vendor is selected until the exploration is run and reviewed.

## Local Endpoint Requirements

The first endpoint candidate must:

- bind only to loopback or a private container network;
- run without outbound network access during tests;
- support durable local volume mounts;
- support object put/get/head/delete operations needed by Engram;
- support deterministic startup in a developer/test environment;
- expose explicit credentials supplied by local config, not anonymous access;
- survive restart without object loss;
- fail closed when credentials are wrong.

"S3-compatible" means an API shape that can be served locally. It does not
mean AWS, cloud S3, or any third-party persistence.

## Blob Object Contract

The preferred object key shape is content-addressed:

```text
sha256/<first-two-hex>/<full-sha256>
```

Object payloads are encrypted before upload. The S3-compatible endpoint stores
opaque ciphertext and should not be trusted with plaintext policy decisions.

Writes are append-only by convention:

- uploading an existing hash with identical ciphertext is idempotent;
- uploading the same object key with different ciphertext is a corruption
  error;
- body mutation creates a new content hash and new object key.

## Future Metadata Shape

RFC 0051 provides the current `evidence_items` / `evidence_refs` model. This
exploration should report any blob-specific extensions needed rather than
waiting on RFC 0051:

```text
evidence_blobs(
  id,
  tenant_id,
  corpus_id,
  content_hash,
  object_uri,
  byte_size,
  media_type,
  encryption_key_id,
  privacy_tier,
  sensitivity_class,
  source_kind,
  source_item_id,
  created_at,
  lifecycle_state
)
```

Metadata is queryable; bytes are not rendered unless policy permits body
release.

Blob-bearing source adapters will also need source-contract additions before
implementation: metadata-only versus body-import mode, attachment retention,
extraction eligibility, default consumers, protection rules, and reconstruction
tests.

## Policy And Retrieval Rules

- Search and `context_for` may cite blob metadata without reading bytes.
- Packet audits must not store blob body content.
- Unauthorized reads return a policy omission, not a missing-data result.
- Tier 5 blob bytes must be encrypted under Tier 5 key material so key
  destruction is meaningful.
- Blob-derived projections must cite the blob metadata and extraction version.

## Exploration Gates

The exploration should produce a small fixture and prove:

- endpoint starts locally and is reachable only through configured local
  address;
- object upload/download round-trips exact bytes after decryption;
- object hash mismatch is detected;
- restart preserves the object;
- wrong credentials fail closed;
- endpoint unavailable produces a typed local error;
- partial write, duplicate object conflict, disk-full, and metadata-present but
  object-missing cases fail predictably;
- `make no-egress-smoke` or an equivalent wrapper reports the enforcement
  status honestly on the host;
- no test requires outbound network access.

## Relationship To Backup

Blob backups are not "copy the object store directory and hope." A later backup
implementation must export:

- encrypted blob shards or object copies;
- object hash manifest;
- encryption key wrapping records;
- restore procedure that verifies blob hashes;
- Tier 5 key exclusion/destruction behavior.

The backup/key design owns posthumous release and Tier 5 policy. This spec owns
the blob storage substrate exploration.

## Open Questions

1. Which local S3-compatible endpoint should be the first test target?
2. Should Engram talk directly to the endpoint, or should a tiny local adapter
   own retries, encryption, and hash verification?
3. Should small text bodies stay in Postgres while only large/sensitive bytes
   move to blobs?
4. What size threshold first triggers blob storage?
5. How should range reads and partial extraction jobs cite byte ranges?
