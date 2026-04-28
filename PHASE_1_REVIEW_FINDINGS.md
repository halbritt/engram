# Phase 1 Review Findings

The Phase 1 implementation successfully achieves the baseline requirements without overstepping into future phases. The schema cleanly implements the requested raw evidence tables, immutability constraints, and the `consolidation_progress` control table while successfully refraining from adding segmentation, embeddings, beliefs, or MCP functionality.

Here are the review findings, ordered by severity.

### Findings

**1. Missing Test Coverage for Split Export Format (Low Severity)**
- **File:** `tests/test_phase1_raw.py`
- **Issue:** The test suite generates and verifies the "classic" `conversations.json` structure via the `write_export` helper, but it lacks coverage for the newer "split export" format (`conversation-index.json` + `json/*.json`). 
- **Risk:** Regressions in the `load_conversations` logic for the split format might not be caught by CI.

**2. Missing Test Coverage for Internal Deduplication (Low Severity)**
- **File:** `tests/test_phase1_raw.py`
- **Issue:** The `validate_unique_payloads` function in `chatgpt_export.py` properly checks for duplicate conversation or message IDs with different payload hashes within a single export run. However, there are no tests to verify that `IngestConflict` is successfully raised when this occurs.

**3. Potential Race Condition in Source Creation (Minor Risk)**
- **File:** `src/engram/chatgpt_export.py`, Lines 235-265 (`get_or_create_source`)
- **Issue:** The function uses a `SELECT` check followed by an `INSERT`. If the CLI were somehow executed concurrently for the exact same export path, this could result in a unique constraint violation on `sources (source_kind, external_id)`.
- **Risk:** Almost zero for a locally-run CLI tool, but an `INSERT ... ON CONFLICT DO NOTHING RETURNING id` (or handling the unique violation gracefully) would make it bulletproof.

**4. Strict Immutability Implications (Observation)**
- **File:** `migrations/001_raw_evidence.sql`, Line 92 (`prevent_raw_evidence_mutation`)
- **Issue:** The trigger perfectly fulfills the requirement to "block UPDATE/DELETE on raw tables." However, be aware that this is a very strict implementation. It means that later phases or user interventions cannot alter *any* field on a raw row—including `privacy_tier` or redacting `content_text`—without first temporarily disabling the trigger (`ALTER TABLE ... DISABLE TRIGGER`) or executing as a superuser overriding constraints. 

### Conclusion

**There are no blocking issues.** 

The codebase meets all the load-bearing requirements for Phase 1. The choice to use `path.expanduser().resolve()` for stable external paths, the robust DFS mapping traversal for conversation trees, and the clean usage of psycopg 3's `Jsonb` and `transaction()` blocks are all excellent operational choices.
