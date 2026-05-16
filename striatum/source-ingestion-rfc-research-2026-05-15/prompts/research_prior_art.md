# Prior-Art Research Prompt

You are producing a prior-art dossier that the RFC drafters and reviewers will
cite. You do not write RFC body text. Your output is a single dossier file at
the path named in your write scope.

Required reading:

- `docs/design/source-ingestion-expansion-proposal-2026-05-15.md`.
- `docs/ingestion.md`.
- All `docs/rfcs/0033-*.md` through `docs/rfcs/0036-*.md`.
- All `docs/rfcs/0044-*.md` through `docs/rfcs/0049-*.md`.
- `STRIATUM_MEMORY_E2E_BACKLOG.md`.
- `src/engram/` source ingestion modules (look at importer modules, raw
  evidence tables, the `source_kind` enum, segmentation entry points).
- Migrations under `migrations/` that touch source tables.

Use the maximum useful number of read-only native sub-agents to map:

1. **Existing source kinds in code** — what `source_kind` values are
   currently accepted, where they are enforced (schema + code), where the
   enum is closed today.
2. **Existing importer patterns** — the shape of the currently working
   importers (ChatGPT, Claude, Gemini, Striatum bundle): file layout,
   identity keys, idempotency keys, privacy_tier handling.
3. **Adjacent RFC coverage** — for every proposed source in the design
   document, identify whether RFC 0033-0036 or RFC 0044-0049 already
   covers it, partly covers it, or leaves it net-new.
4. **Privacy and no-egress posture** — where in current code the
   no-network invariant is asserted; where additional invariants would
   be needed for new sources (e.g. git diff bodies, media bodies).
5. **Projection contract precedent** — what the Striatum projection
   layer (Layer 1, migration 015) already does for derived rows; how a
   generalized "source contract" should align with or diverge from it.
6. **Open questions and unresolved tradeoffs** — from the design doc,
   the backlog, and adjacent RFCs.

The dossier must be operator-readable: section anchors, file path
citations, RFC numbers, and a final "questions for the drafters and
reviewers" section.

Do not write RFC text. Do not edit source files. Cite, do not assume.
