# Local Backup, Key Management, And Tier 5 Destruction Design

| Field | Value |
|-------|-------|
| Spec | local-backup-key-tier5-design-v1 |
| Title | Local Backup, Key Management, And Tier 5 Destruction |
| Status | proposal |
| Date | 2026-05-17 |
| Source decisions | [D091](../../DECISION_LOG.md#d091) |
| Source requirements | [HUMAN_REQUIREMENTS.md](../../HUMAN_REQUIREMENTS.md), `ARCHITECTURE_RECOMMENDATION_EXECUTION_PLAN_2026-05-16.md` Phase 10 |

This document is the first concrete A10 design draft. It is not an accepted
implementation contract. Its job is to make the backup/key/Tier 5 boundary
specific enough to review before durable high-risk source-family expansion.

## Purpose

Engram's long-term corpus can include health, finance, location, private
relationships, raw media, and posthumous material. That corpus must survive
device loss without turning into a cloud dependency, and it must support
cryptographically meaningful Tier 5 destruction before posthumous release.

D091 does not block the already-authorized low-risk A8/A9 slices or other
low-risk eval-driven work. It still blocks durable high-risk ingestion
approval.

## Scope

This design covers:

- local encrypted backup artifacts;
- restore verification before backup automation;
- a key hierarchy for ordinary recovery and posthumous release;
- Tier 5 cryptographic destruction;
- local/offline dead-man's-switch runbook requirements.

Threats in scope:

- device theft or seizure;
- disk failure or accidental deletion;
- accidental cloud sync of a backup directory;
- lost or stale recovery keys;
- corrupted or incomplete backups;
- premature posthumous release while the user is alive but offline;
- incomplete Tier 5 destruction across database rows, projections, embeddings,
  backups, and future blob bytes.

## Non-Goals

- No SaaS backup, cloud sync, hosted key escrow, or telemetry.
- No background export to iCloud, Google Drive, Dropbox, S3, or similar.
- No new high-risk source family is approved by this spec.
- No production key custody mechanism is selected here.
- No migration or CLI behavior is implied until the design is accepted.

## Invariants

- Backups are encrypted before they leave the live database/blob-vault
  boundary.
- The user holds the effective recovery keys. OS login credentials alone are
  not enough.
- `privacy_tier` remains an audience and lifecycle model. It must not be used
  as a shortcut for sensitivity classification. Health, finance, precise
  location, contacts, biometrics, and third-party communications need explicit
  sensitivity labels in addition to any privacy tier.
- Every backup has a manifest with schema version, migration checksums, content
  hashes, created timestamp, and tool versions.
- Restore is tested before scheduled backup automation is considered done.
- Tier 5 material is encrypted under key material that is excluded from
  posthumous release and can be destroyed independently.
- Posthumous release is a local/offline process, not a hosted service.

## Proposed Key Hierarchy

Logical keys:

- `engram_root_key`: local root used only to unwrap narrower key-encryption
  keys; stored outside the database.
- `backup_kek`: wraps backup data-encryption keys for ordinary user restore.
- `successor_kek`: wraps only the keys permitted for a successor view.
- `tier_dek`: encrypts data or blob keys for one privacy tier or tier family.
- `tier5_dek`: encrypts Tier 5 material and is not wrapped for successor
  release.
- `backup_dek`: encrypts one backup artifact or shard.

The concrete storage mechanism is deliberately unresolved. Acceptable options
to evaluate include local passphrase-derived wrapping, hardware-backed local
keys, threshold secret sharing, or a hybrid. Hosted custody is out of scope.

The accepted design must also define key rotation and revocation. Metadata may
store key ids and wrapping records, but never raw keys.

## Backup Artifact Shape

A backup is a local directory or archive with:

- `manifest.json`: backup id, schema version, Engram version, migration
  checksum set, created timestamp, corpus inventory, privacy-tier inventory,
  blob inventory, and hash manifest.
- `database.dump.enc`: encrypted logical database dump or equivalent restore
  payload.
- `blobs/`: encrypted blob-vault export shards when a blob vault exists.
- `keys/`: encrypted key wrapping records, never plaintext data keys.
- `restore-notes.md`: operator-readable restore procedure for this artifact
  version.

The manifest must not include plaintext sensitive body content.

## Restore Smoke

The first implementation gate should restore a non-private fixture backup into
a temporary database/blob location and verify:

- database migration state matches the manifest;
- row counts and selected hashes match the manifest;
- blob hashes match where blobs are present;
- Tier 5 fixture material is unavailable when `tier5_dek` is withheld;
- ordinary Tier 1 fixture material is available when ordinary recovery keys are
  supplied.

Restore failure is a blocking backup failure. Backup automation without a
restore smoke is not considered implemented.

The smoke should also verify that derived rows, projection rows, embeddings,
and audits either restore consistently or are explicitly rebuildable from the
restored canonical evidence.

## Dead-Man's-Switch Runbook Requirements

The posthumous process must be local/offline and should define:

- heartbeat cadence and grace window;
- confirmation/witness process before release;
- threshold or custody model for successor key release;
- per-successor view mapping;
- Tier 5 key destruction before successor keys are released;
- audit record of what key set was released and which key set was destroyed.

The runbook must explicitly handle false-positive risk: the user may be alive
but offline or incapacitated.

## Tier 5 Destruction Semantics

Tier 5 destruction is key destruction, not ordinary filtering. To qualify:

- Tier 5 data must be encrypted under a key not derivable from released
  successor keys.
- Destroying that key must make Tier 5 ciphertext unrecoverable from backups
  and blob exports.
- Backup manifests must distinguish "not included" from "included but
  cryptographically destroyed."
- The system must not rely on deleting rows from append-only evidence tables as
  the primary destruction mechanism.
- Derived rows, projections, embeddings, packet audits, context snapshots, and
  blob objects that contain or can reconstruct Tier 5 plaintext must either be
  encrypted under the Tier 5 key domain or be rebuildable after that domain is
  destroyed.
- Destruction evidence must prove which key domain was destroyed without
  exposing the destroyed content.

## Acceptance Gates

Before durable health, finance, precise-location, raw-media, or comparable
high-risk ingestion is approved:

- this design or a successor spec is accepted;
- a restore smoke exists against a non-private fixture;
- Tier 5 key-withholding/destruction is tested on fixture material;
- a posthumous handoff runbook exists;
- cloud sync and hosted key custody remain explicitly out of scope.

## Open Questions

1. Which local key custody model should ship first: passphrase, hardware token,
   threshold sharing, or hybrid?
2. What heartbeat cadence and grace window balance false positives against
   useful posthumous release?
3. How are per-successor views represented without duplicating the corpus?
4. Should backup artifacts be single archives, content-addressed shards, or
   both?
5. What is the smallest fixture that proves Tier 5 destruction across database
   rows and blob-vault bytes?
6. Which sensitivity classes require A10 gating before source-family approval?
