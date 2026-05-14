# RFC 0044 Review: Operator Gemini
author: operator [self-declared: rfc0044-review-operator-flash-retry2]

## Review Objective

Review bundle manifest/provenance handling, operator ergonomics, and augmentation-not-dependency contract for RFC 0044.

## Findings

### Bundle Manifest and Provenance Handling

The implementation successfully addresses bundle manifest and provenance handling as detailed in `IMPLEMENTATION_HANDOFF.md` and `CAPABILITY_BOUNDARY_EVIDENCE.md`.

-   **Manifest Validation:** `engram ingest-striatum` processes `manifest.json` and JSONL files, performing rigorous validation including schema verification, file hashes, byte counts, and row counts. It correctly identifies and handles duplicate `(sub_kind, external_id)` rows and raises `IngestConflict` for re-ingestions with differing content. This ensures data integrity and prevents silent overwrites.
-   **Provenance Preservation:** Each ingested Striatum corpus row is stored as an immutable raw capture with `source_kind='striatum'` and `capture_type='reference'`. Crucially, provenance fields such as `path`, `sha256`, `commit`, `rfc`, `decision`, `run_id`, and `audit` metadata are preserved within `raw_payload.provenance`. These provenance fields are exposed through `MemoryService.search` and re-checked during `fetch_reference` authorization, ensuring traceability and security.

### Operator Ergonomics

The operator ergonomics align with the design principles, prioritizing clarity and explicit boundaries.

-   **Explicit Tenant/Corpus Handling:** The system consistently uses `tenant_id` and `corpus_id` as the primary isolation keys, with `source_kind='striatum'` and `tenant_id='striatum', corpus_id='striatum'` for Striatum artifacts. Although shorthand commands like `corpus="striatum"` are available for convenience, the underlying handlers and authorization mechanisms correctly enforce the explicit `(tenant_id, corpus_id)` pair, preventing ambiguity or unintended cross-tenant/corpus access.
-   **Read-Only MCP Interface:** The `engram-mcp-stdio` tool provides a strictly read-only interface, exposing only `engram.search`, `engram.fetch_reference`, `engram.describe_corpus`, and `engram.health`. This narrow surface prevents write operations, claim creation, belief mutations, or administrative functions via the MCP, enhancing security and operational predictability. The console script nature and use of stdio framing further reinforce its local, controlled interaction model.
-   **Clear CLI Commands:** The `README.md` clearly outlines `engram ingest-striatum` for ingestion and `engram describe-corpus striatum` for inspection, demonstrating straightforward command-line interaction for operators.

### Augmentation-Not-Dependency Contract

The implementation fully honors the augmentation-not-dependency contract, as specified and verified.

-   **No Runtime Dependency on Striatum:** Engram does not `import striatum` or depend on `striatum-orchestrator` at runtime. The integration is purely augmentation-based: Engram consumes exported files from Striatum without establishing any direct code-level dependency or invoking Striatum commands.
-   **No Network/Cloud/Telemetry:** Verified by code inspection and focused tests, the RFC 0044 runtime surface (e.g., `src/engram/striatum_ingest.py`, `src/engram/memory.py`, `src/engram/mcp_stdio.py`) contains no HTTP clients, sockets, hosted APIs, telemetry, cloud services, or remote persistence mechanisms. This strictly adheres to the local-first and privacy mandates.
-   **No Writes to `.striatum/`:** Engram explicitly does not write into a target repository's `.striatum/` directory, maintaining Striatum's autonomy as the source of truth for its own state.

## Conclusion

The RFC 0044 implementation successfully delivers on its objective. Bundle manifest and provenance handling are robust, operator ergonomics are clearly defined and enforced, and the augmentation-not-dependency contract is fully satisfied and verified by targeted tests and inspections. The adherence to local-first principles and strict capability boundaries is well-implemented.

## Recommendations

No critical issues found. The implementation appears solid.

---
**Job ID:** `job_run_322110269dfb4ec98fc6f7ea818448c0_review_operator_gemini`
**Lease ID:** `lease_3aaea880272a41178b66472ccbe56cad`