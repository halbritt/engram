<a id="rfc-0051"></a>
# RFC 0051: Generic Evidence And Reference Index

| Field | Value |
|-------|-------|
| RFC | 0051 |
| Title | Generic Evidence And Reference Index |
| Status | accepted_as_design_reference |
| Implementation | partial: migration 022, `src/engram/evidence.py`, generic exact-reference lookup in `MemoryService` |
| Date | 2026-05-17 |
| Context | D087, D088, D089, D093, D094; RFC 0050; `ARCHITECTURE_RECOMMENDATION_EXECUTION_PLAN_2026-05-16.md` Phase 8; `src/engram/memory.py`; migrations 017-022 |

Decision refs:
  - [D088](../../DECISION_LOG.md#d088)
  - [D089](../../DECISION_LOG.md#d089)
  - [D093](../../DECISION_LOG.md#d093)
  - [D094](../../DECISION_LOG.md#d094)

This RFC is the design reference for the narrow generic evidence/reference
index substrate approved by D094. It exists to stop future source families from
adding bespoke retrieval branches without first defining the common evidence
envelope.

## Motivation

Striatum captures, git commits, build artifacts, and Markdown files now serve
exact-reference retrieval through one `MemoryHit` shape. The implementation is
uniform at the result boundary, but source-specific tables still require
source-specific lookup code. That is acceptable for the current narrow serving
path; it will not scale cleanly to broader biography sources.

The D094 slice implemented the narrow generic exact-reference substrate. Further
expansion beyond the implemented slice should be driven by real `context_for`
eval failures, not adapter availability.

## Goals

- Define a common local evidence item envelope.
- Define a generic reference index that can cover existing source families.
- Preserve immutable raw evidence and rebuildable projections.
- Preserve tenant/corpus boundaries and local-only serving.
- Keep generated products out of retrieval until a downstream generated-product
  spec exists.
- Let source-family adapters add references without editing `MemoryService`
  source-kind branches.

## Non-Goals

- No new RFC 0050 Stage 3+ source family is approved by this RFC alone.
- No generated summaries, biographies, OCR text, captions, or daily compilers
  become retrieval-visible through this RFC alone.
- No hosted search service, hosted vector store, or remote reranker is allowed.
- No generated-product, high-risk source-family, or remote-store implementation
  is approved by this RFC.

## Design Surface And Deferred Extensions

D094 introduced the first two logical families and left the broader projection
generalization deferred:

- `evidence_items`: one row per immutable source item or source-specific raw
  row, with tenant/corpus, source family, source-local id, privacy tier,
  sensitivity class, content hash, timestamps, and provenance pointer.
- `evidence_refs`: normalized exact references such as path, commit SHA, run id,
  issue id, external id, title slug, or operator-authored alias.
- `projection_items`: derived retrieval/index rows that point back to evidence
  items and projection generations.
- `projection_generations`: a generalized equivalent of current projection
  generation tables, preserving input manifests and activation state.

The RFC should also decide whether large bodies are represented only by
metadata here and stored later through the blob-vault track.

## Implemented Slice

The 2026-05-17 D094 implementation slice adds:

- `evidence_items`: rebuildable source-item projection rows over supported
  raw/source tables.
- `evidence_refs`: normalized exact-reference rows for the current source
  families.
- `src/engram/evidence.py`: tenant/corpus-scoped rebuild helper covering active
  Striatum references, git commits, build artifacts, and Markdown files.
- `engram evidence refresh-index` and `make evidence-refresh`: operator-facing
  rebuild entrypoints.
- `MemoryService.search(... filters.exact_refs=...)`: generic index lookup
  first, source-specific lookup fallback second, preserving existing
  `MemoryHit` and `fetch_reference()` shapes.

Generated products remain retrieval-invisible until a downstream
generated-product implementation specification from this RFC is accepted per
D089.

## Required Compatibility

- Existing exact-reference tests for Striatum, git, build-artifact, and Markdown
  must continue to pass.
- `MemoryService.search(... filters.exact_refs=...)`,
  `MemoryService.build_packet()`, and `fetch_reference()` must keep their
  current external shapes unless versioned.
- Packet audits must remain body-free.
- Existing source-specific raw/source tables remain canonical evidence.
  `evidence_items` and `evidence_refs` are rebuildable index projections and do
  not replace raw/source tables.

## Generated Product Gate

Per D089, generated products require a downstream implementation specification
from this RFC before they become retrieval-visible. That spec must define:

- privacy inheritance;
- provenance and citation;
- audit and rebuildability;
- source/generated distinction in search and packets;
- eval gates for unsupported generated facts.

## Resolved And Open Questions

- Resolved by D094: `evidence_items` and `evidence_refs` are rebuildable
  projections over existing raw/source tables, not canonical replacements.
- Open: Does the reference index store body excerpts, or only reference
  metadata?
- Open: How are stale/tombstoned references represented across source
  families?
- Open: What is the minimum backfill gate proving current source coverage is
  reproducible?
- Open: Which real context-eval failure class justifies expanding beyond the
  D094 narrow slice?
