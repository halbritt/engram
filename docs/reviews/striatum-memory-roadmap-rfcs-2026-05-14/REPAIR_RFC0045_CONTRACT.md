# Repair Handoff: RFC 0045 Contract Coherence

author: Codex RFC repair implementor
date: 2026-05-14
scope: RFC 0045 proposal repair only

## Summary

Repaired `docs/rfcs/0045-striatum-corpus-contract-v2.md` for the contract
coherence review findings routed by
`OPERATOR_DECISION_CONTRACT_REPAIR.md`.

The repair keeps RFC 0045 as proposal text only. It does not implement an
exporter, ingester, projection, migration, test, fixture, or runtime behavior.

## Accepted Findings

- CC-001: accepted. RFC 0045 now requires row-level `tenant_id` and
  `corpus_id` on every V2 item and validates both against
  `manifest.memory_target`.
- CC-002: accepted. RFC 0045 now defines `bundle_id`, separates it from
  `bundle_sha256`, defines `previous_bundle_id` chain semantics, and adds
  lifecycle record shapes for `content`, `tombstone`, `redaction`, and
  `withheld_marker`.
- CC-007: accepted. RFC 0045 now closes downstream-stable provenance,
  reference, lifecycle, classification, authority, stability, and confidence
  vocabularies enough for RFC 0046 and RFC 0049 to target exact fields.
- PB-001: incorporated where it affects the corpus contract. Item path-shaped
  fields are repository-relative by default; absolute paths and user-profile
  prefixes require explicit operator opt-in.
- PB-002: incorporated where it affects the corpus contract. Dirty working
  tree export is invalid by default and requires manifest-level opt-in plus
  row-level `provenance.dirty_working_tree=true`.
- PB-004: incorporated where it affects the corpus contract. Labels and root
  hints are display-only, inherit corpus privacy, and cannot appear in
  unauthorized agent-visible diagnostics.
- PB-005: incorporated where it affects the corpus contract. Withheld bodies
  are represented by deterministic notices; hashes, chunks, and embeddings may
  cover only emitted notice text.
- PB-007: incorporated as an RFC 0044 ledger precondition reference for F004
  and F009.

## Changed Sections

- Dependencies: added RFC 0044 ledger preconditions F004 and F009.
- Manifest Shape and Manifest Requirements: added `bundle_id`,
  path/dirty-tree privacy policy, required row fields, label privacy rules,
  and `previous_bundle_id` semantics.
- Item Record Shape and Item Requirements: added row-level tenant/corpus,
  row-level `bundle_id`, lifecycle object, closed nullable provenance fields,
  repository-relative path rules, and dirty-tree provenance.
- Classification Contract: added closed `evidence_kind`, `authority_class`,
  `stability_class`, and confidence rules.
- Reference And Link Vocabulary: added closed reference and typed-link
  vocabularies for downstream exact lookup and projection.
- Identity Rules: clarified row-level tenant/corpus authority and manifest
  validation role.
- Hashing Rules: defined lifecycle hash rules and clarified `bundle_id` versus
  `bundle_sha256`.
- Privacy, Redaction, And Visibility: tightened withheld-content,
  redaction-notice, and redaction-metadata rules.
- Lifecycle Record Shapes: added content, tombstone, redaction, and withheld
  marker shapes.
- Incremental Export Watermarks: tied incremental exports to
  `export.previous_bundle_id`.
- Validation Rules: added fail-closed checks for row/manifest mismatch,
  lifecycle shape, provenance keys, classification/confidence, path leakage,
  dirty-tree opt-in, and hidden-content leakage.
- Downstream Requirements and Acceptance Criteria: updated the stable field
  handoff for RFC 0046/RFC 0049.
- Open Decisions: narrowed the redaction vocabulary open decision now that the
  RFC defines the lifecycle/redaction vocabularies.

## Validation Evidence

Command:

```sh
git diff --check -- docs/rfcs/0045-striatum-corpus-contract-v2.md
```

Result: passed with exit code 0 and no output.

Required final command:

```sh
git diff --check -- docs/rfcs/0045-striatum-corpus-contract-v2.md docs/reviews/striatum-memory-roadmap-rfcs-2026-05-14/REPAIR_RFC0045_CONTRACT.md
```

Result: passed with exit code 0 and no output.

## Deferred Questions

- Exact accepted grammar for per-instance `corpus_id`.
- Exact source and bootstrap behavior for `identity.instance_id`.
- Exact source of `identity.repository_id` for no-remote or multi-remote
  repositories.
- Whether required streams are always zero-row files or may be manifest-declared
  omissions.
- Default depth for git diff and stdout/stderr exports.
- Exact privacy-tier assignment policy Striatum can guarantee before export.
- Whether V2 keeps one file per sub-kind or later supports sharded item files.
- Compatibility adapter ownership for V1 raw-only bundles.
- Which V2 fixture bundle becomes the RFC 0049 review/evaluation seed.
