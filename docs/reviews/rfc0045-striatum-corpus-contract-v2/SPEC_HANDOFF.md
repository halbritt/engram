# RFC 0045 Striatum Corpus Contract V2 Spec Handoff
author: operator [self-declared: roadmap-rfc-author-b]

Status: author handoff
Date: 2026-05-14
Striatum run: `run_500d0f049ea04038b0e19d6045daf918`
Striatum job: `rfc0045_contract_handoff`

## Scope

This is an author/spec handoff only. No implementation, review, migration,
source-code, test, changelog, decision-log, or operator-report changes were
made.

The handoff preserves the local-only/no-cloud/no-telemetry/no-hosted
persistence constraints and keeps Engram as optional Striatum augmentation,
not a Striatum runtime dependency.

## Changed Files

- `docs/rfcs/0045-striatum-corpus-contract-v2.md`
  - Replaced the scaffold with a reviewable V2 corpus-contract proposal.
  - Added manifest shape, item record shape, vocabulary, identity, hashing,
    privacy/redaction, incremental watermark, validation, compatibility, and
    downstream dependency sections.
- `docs/reviews/rfc0045-striatum-corpus-contract-v2/SPEC_HANDOFF.md`
  - Created this handoff artifact for the Striatum packet retry.

No other files were intentionally changed.

## Contract Topics Filled

- V2 remains a disk bundle contract: Striatum exports local JSONL bundles,
  Engram consumes them from local disk, and neither repository imports or calls
  the other at runtime.
- Manifest proposal now includes `schema_version`, `bundle_sha256`,
  generator metadata, `memory_target`, instance/repository identity, full vs
  incremental export metadata, privacy/redaction profile, file metadata,
  row counts, and compatibility metadata.
- Item proposal now includes `source_kind`, `sub_kind`, `item_id`,
  `logical_id`, `version_id`, content hashes, timestamps, provenance,
  privacy, visibility, classification, links, and extension metadata.
- Identity rules now distinguish `tenant_id`, `corpus_id`, Striatum
  `instance_id`, repository identity, immutable `item_id`, and stable
  `logical_id`.
- Source-kind vocabulary is fixed to `source_kind='striatum'`; V2 sub-kinds
  are grouped into required core streams and optional streams.
- Privacy/redaction metadata is explicit and local-only. Redaction must happen
  before export without hosted services or cloud DLP.
- Incremental exports are framed as append-only deltas with prior-bundle
  references, source watermarks, and explicit tombstone/redaction records.
- Validation rules are deterministic and fail closed without live network,
  live model, Striatum daemon RPC, Engram MCP, or hosted service calls.
- Compatibility states that RFC 0044 V1 bundles remain valid for RFC 0044 raw
  retrieval but are not V2 bundles; V2-only projections must not silently run
  on V1-only input.

## Intentionally Deferred

- Exact `corpus_id` grammar for per-instance corpora.
- Exact Striatum source of `identity.instance_id`.
- Exact repository identity derivation for repositories with no remote or
  multiple remotes.
- Whether required streams are zero-row files or may be omitted with manifest
  declarations.
- Default volume of git diff content.
- Whether raw stdout/stderr excerpts are allowed or only summaries.
- Final redaction-state vocabulary and which privacy tiers Striatum can
  guarantee before export.
- Whether V2 permanently uses one file per sub-kind.
- Where V1/V2 compatibility adapters should live.
- Which fixture bundle should seed RFC 0049 evaluation.

## Validation Evidence

- Required read-before-writing inputs were inspected:
  `AGENTS.md`, `STRIATUM_MEMORY_ROADMAP.md`, `SPEC.md`,
  `docs/schema/README.md`, RFC 0045, the Striatum workflow `SOURCES.md`,
  `prompts/rfc_author.md`, `roles/author.md`, RFC 0044 final synthesis, and
  RFC 0044 findings ledger.
- Additional Striatum-side context was inspected:
  `/home/halbritt/git/striatum/ENGRAM_DEVELOPER_REQUEST.md` and
  `/home/halbritt/git/striatum/docs/rfcs/0044-engram-phase-1-implementation-spec.md`.
- Neighboring downstream RFC scaffolds 0046, 0047, 0048, and 0049 were
  inspected for dependency alignment.
- Three read-only native sub-agents inspected disjoint context areas:
  canonical Engram constraints, RFC 0045/authoring packet expectations, and
  RFC 0044 findings/dependency implications.
- Docs-only validation was performed after writing:
  - `git diff --check -- docs/rfcs/0045-striatum-corpus-contract-v2.md docs/reviews/rfc0045-striatum-corpus-contract-v2/SPEC_HANDOFF.md`
  - `git status --short -- docs/rfcs/0045-striatum-corpus-contract-v2.md docs/reviews/rfc0045-striatum-corpus-contract-v2/SPEC_HANDOFF.md`

No unit tests were run because the packet explicitly forbids implementation
and the change is limited to two Markdown artifacts.

## Downstream Dependencies

RFC 0046 depends on RFC 0045 stabilizing:

- `tenant_id`, `corpus_id`, `source_kind`, and `sub_kind`;
- immutable `item_id`, stable `logical_id`, and `version_id`;
- content, content hashes, record hashes, and timestamp semantics;
- provenance pointers to files, commits, runs, processes, artifacts, issues,
  and blockers;
- privacy, visibility, classification, and link fields.

RFC 0047 depends on RFC 0045 preserving the boundary:

- bundle identity and manifest visibility are not authorization grants;
- Striatum must remain able to run without Engram;
- Engram must ingest from disk without importing or invoking Striatum;
- the reciprocal Striatum-side augmentation-not-dependency artifact remains a
  blocker before claiming runtime augmentation safety.

RFC 0049 depends on RFC 0045 for evaluation inputs:

- deterministic manifest and item hashes;
- real or committed fixture V2 bundle validation;
- explicit V1 rejection or compatibility-adapter behavior;
- no-egress validation scope;
- negative tests for inconsistent tenant/corpus/source-kind declarations.

## Residual Risks

- The RFC now proposes concrete contract shapes, but no fixture bundle exists
  yet to prove ergonomics or parser fit.
- The exact per-instance corpus ID and Striatum instance ID rules are still
  open; this is the highest-leverage review topic before implementation.
- V2 required streams may be too broad if Striatum cannot produce some streams
  cheaply; review should decide whether zero-row files or manifest omissions
  are preferable.
- Privacy/redaction vocabulary is still a candidate contract. It needs a
  Striatum-side producer review before any exporter work.
- RFC 0044 hardening follow-ups remain outside this packet and should not be
  treated as resolved by RFC 0045.
- `CHANGELOG.md` and `DECISION_LOG.md` were not updated because the operator
  packet explicitly forbids writing them in this retry.

## Review Packet Recommendation

The next review should treat RFC 0045 plus this handoff as proposal material,
not implementation authority. Review should focus on contract coherence,
local-only safety, identity/corpus isolation, Striatum producer ergonomics,
and whether RFC 0046/RFC 0047/RFC 0049 have enough stable surface to proceed.
