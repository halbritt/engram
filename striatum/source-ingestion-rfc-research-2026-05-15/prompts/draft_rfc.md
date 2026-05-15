# Source-Ingestion RFC Draft Prompt

You are drafting an independent proposal-grade RFC body from the design
document at `docs/design/source-ingestion-expansion-proposal-2026-05-15.md`.
Your draft is one of three parallel drafts (claude, codex, gemini). A
synthesizer will reconcile them later. Do not edit the design document. Do not
edit the final RFC file. Write only the draft artifact named in your write
scope.

Required reading before drafting:

- `docs/design/source-ingestion-expansion-proposal-2026-05-15.md` — the
  primary source.
- `docs/ingestion.md` — current ingestion documentation.
- `HUMAN_REQUIREMENTS.md`, `SPEC.md`, `BUILD_PHASES.md`, `ROADMAP.md`,
  `docs/schema/README.md`, `AGENTS.md` — project canon.
- `docs/rfcs/0033-multimodal-observation-layer.md`,
  `docs/rfcs/0034-photo-library-ingestion.md`,
  `docs/rfcs/0035-location-timeline-place-model.md`,
  `docs/rfcs/0036-daily-biography-compiler.md` — adjacent multimodal stack.
- `docs/rfcs/0045-striatum-corpus-contract-v2.md` through
  `docs/rfcs/0049-striatum-evaluation-gates.md` — adjacent Striatum-memory
  stack.
- `STRIATUM_MEMORY_E2E_BACKLOG.md` — active execution plan.

Use the maximum useful number of read-only native sub-agents for context
gathering before you start writing. They should report which proposed sources
the existing codebase already covers and which are net-new.

Your draft must include, at minimum:

1. **Front matter** — number `0050`, title, status `proposal`, date,
   authors, source design doc reference.
2. **Context** — why this matters now, what the design doc proposes,
   why the current `source_kind` enum is the practical limitation.
3. **Source contract template** — the four required questions per source
   adapter; mandatory contract fields; how the contract is enforced
   (importer tests).
4. **Projection families** — closed vocabulary; how projections inherit
   privacy/provenance from raw evidence.
5. **Privacy defaults** — privacy_tier per source family; explicit
   no-egress and no-derived-product-leak rules.
6. **Rollout order** — sequenced importer adoption (highest-signal,
   lowest-egress-risk first), with explicit success criteria per stage.
7. **Evaluation gates** — minimum gate set borrowed from RFC 0049 style;
   gate per source family; idempotency / re-projection / no-network
   assertions.
8. **Scope kept out** — explicit deferrals to prevent unrequested
   expansion: media bodies, cloud APIs, derived memory products,
   personal-memory paste-through.
9. **Open questions** — at least three named open questions for human
   decision.
10. **Cross-references** — explicit table or list mapping proposed
    sources to existing RFCs (RFC 0033-0036 for multimodal, RFC 0044-0049
    for the Striatum corpus boundary).

Preserve Engram constraints: no cloud dependency, no user data leaving the
machine unless explicitly requested, immutable raw evidence, rebuildable
projections, provenance/confidence/auditability. Do not propose any change
that would violate them.

Do not edit source files. Do not edit code, tests, migrations, generated
schema docs, `DECISION_LOG.md`, or `CHANGELOG.md`. Run `git diff --check`
against the allowed paths before completing.

Your output artifact must include a short header naming yourself (the
authoring lane). Do not impersonate another lane's byline; that fabrication
rule is load-bearing in this project.
