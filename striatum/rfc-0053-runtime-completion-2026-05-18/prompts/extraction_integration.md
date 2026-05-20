# Extraction Integration Slice

Scaffold extraction-loop integration without changing extraction semantics by
default.

Required:

1. Identify groundable mention surfaces from extracted claims only behind an
   explicit disabled-by-default flag or helper.
2. Emit RFC 0053 request sidecars without performing live network fetch and
   without mutating claim content.
3. Preserve `(segment_id, version) -> idempotent commit`.
4. Add deterministic tests proving default extraction is unchanged and enabled
   scaffold emits sidecars only.

Write `docs/reviews/rfc0053-runtime-completion/EXTRACTION_INTEGRATION_HANDOFF.md`.
