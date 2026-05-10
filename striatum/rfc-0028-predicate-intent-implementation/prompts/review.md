# Review RFC 0028 Predicate-Intent Implementation

Review the implementation against RFC 0028 and Engram's invariants. Do not edit
implementation files.

Checklist:

1. Schema: migration 012 is additive, nullable, idempotent under the migration
   runner, and does not weaken append-only/raw-evidence constraints.
2. Runtime vocabulary: extractor metadata matches the database vocabulary; the
   schema preflight catches drift including description and subject-kind hint.
3. Prompt versioning: the extraction prompt version is bumped and old rows stay
   versioned under prior prompts.
4. Prompt shape: descriptions and hints are actually visible in
   `build_extraction_prompt`, without changing the JSON output contract.
5. Interview UX: `format_summary_line` puts intent on its own line and warning
   text is clear without being overconfident.
6. Web parity: CLI and web use the same rationale prompt and summary rendering.
7. Tests: focused tests cover prompt rendering, migration/schema preflight,
   rationale label, and warning rendering. No live LLM calls.
8. Docs: changelog, decision log, RFC status/index, and schema docs are updated
   or explicitly called out as unavailable.

Write to the exact path in the packet. Use this structure:

```md
# RFC 0028 Predicate Intent Implementation Review — <lane>
author: <packet author line>

Status: review
Date: 2026-05-09
RFC refs: RFC-0028
Decision refs: D082
Phase refs: PHASE-0003, PHASE-0003-FOLLOWON

## Findings

### F001 — <title>
Severity: <blocking | major | minor | nit>
Source: <path:line or section>
Rationale: <paragraph>

## Open questions

verdict: <accept | accept_with_findings | needs_revision | reject>
```
