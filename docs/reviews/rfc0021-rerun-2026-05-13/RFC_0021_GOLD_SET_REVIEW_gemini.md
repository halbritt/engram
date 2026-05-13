# RFC 0021 Gold-Set Interview Curation Review — gemini

Status: review
Date: 2026-05-13
author: operator [self-declared: debug-rfc0021-gemini]
RFC refs: RFC-0021
Decision refs: D044, D069
Phase refs: PHASE-0003

## Findings

### F001 — Verdict count discrepancy: 6 states in schema vs 8 states expected
Severity: major
Source: docs/rfcs/0021-gold-set-interview-curation.md: "Lookup tables seeded by the migration... v1 seeds:"
Rationale: The job objective requested a review of "whether the eight verdict states fit how a human actually rules on a row." However, the RFC and the `migrations/010_gold_labels.sql` schema both only define six verdict states (`true`, `false`, `stale`, `unsupported`, `unsure`, `skip`). There is a mismatch between the expected eight states and the provided six. The current six states are mutually distinct and clearly differentiate between `false` (world truth) and `unsupported` (evidence quality). If eight states were intended, the missing two need to be identified and added to the RFC.

### F002 — Strong schema alignment avoiding JSONB for version stamps
Severity: nit
Source: docs/rfcs/0021-gold-set-interview-curation.md: "Typed version triple."
Rationale: The review prompt raised a concern about a potential `target_version_stamp` JSONB column, but the RFC avoids JSONB entirely. It instead correctly mirrors the typed columns on `claims` (`extraction_prompt_version`, `extraction_model_version`) and `beliefs` (`consolidation_prompt_version`, `consolidation_model_version`). This ensures equality joins remain indexed and performant.

### F003 — Privacy-tier inheritance is correctly enforced
Severity: nit
Source: docs/rfcs/0021-gold-set-interview-curation.md: "Privacy and provenance"
Rationale: The `gold_labels.privacy_tier` inheritance correctly reflects the target row's tier via the `fn_gold_labels_carry_privacy_tier` trigger. The default fail-closed export (`--privacy-tier-max 1`) ensures no data leakage above the safest tier unless explicitly overridden.

### F004 — Append-only discipline is robust
Severity: nit
Source: docs/rfcs/0021-gold-set-interview-curation.md: "Append-only, schema-enforced"
Rationale: The RFC correctly specifies that re-asks produce new rows, and schema-level enforcement via the `fn_gold_labels_append_only` trigger protects against `UPDATE` or `DELETE` operations. This perfectly matches the raw-evidence immutability rules.

### F005 — Session state tracking is structurally sound
Severity: nit
Source: docs/rfcs/0021-gold-set-interview-curation.md: "Storage"
Rationale: The introduction of `gold_label_sessions` with a dedicated `session_id` to anchor `gold_labels` rows provides a clean, normalized way to track interview loops instead of relying on a free-text metadata field.

## Open questions

- What are the missing two verdict states that the objective expected, or is the six-state vocabulary considered final?
- Will future `active_learning_signal_version` values dictate additional required schemas, or does the text column suffice indefinitely?

verdict: accept_with_findings
