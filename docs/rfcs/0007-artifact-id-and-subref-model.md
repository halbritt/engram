# RFC 0007: Artifact ID And Subref Model

Status: proposal
Date: 2026-05-03
Context: Documentation traceability; DECISION_LOG; docs/rfcs; docs/reviews; docs/phases

This RFC replaces the abandoned operational prompt
`prompts/engram-artifact-refactor.md`. The idea is worth considering, but it
is a documentation architecture change and should be reviewed as an RFC before
any repo-wide rewrite.

## Problem

Engram now has several long-lived documentation artifact types:

- RFCs in `docs/rfcs/`,
- accepted and rejected decisions in `DECISION_LOG.md`,
- reviews in `docs/reviews/`,
- phase plans and phase status documents in `BUILD_PHASES.md` and
  `docs/phases/`,
- operational prompts in `prompts/`.

These artifacts refer to each other heavily. The current references are useful
but uneven: `D034` is stable and compact, while RFCs, reviews, and phase docs
are mostly referenced by filename, title, or prose. As the docs grow, broad
references like "the pre-Phase-2 review" become harder to audit.

The failed prompt attempted to jump straight to a mechanical refactor. That is
unsafe for four reasons:

1. The existing `D001` through `D040` decision IDs are already canonical across
   the repo.
2. Subrefs need deterministic anchor rules before they can be trusted.
3. `docs/rfcs/README.md` is an index, not an RFC document.
4. The scope touches canonical architecture docs, so the migration must be
   incremental and reviewable.

## Goals

- Give every long-lived documentation artifact a stable typed identifier.
- Allow precise references to subsections, findings, decisions, or phase
  requirements.
- Preserve existing links and decision references.
- Make future mechanical validation possible.
- Keep RFCs as proposals until promoted through the normal decision process.

## Non-goals

- Do not rewrite the whole repo as part of this RFC.
- Do not replace existing `D###` references unless an accepted decision defines
  a compatibility plan.
- Do not make RFCs binding merely by assigning IDs.
- Do not hand-edit generated schema docs.
- Do not introduce external documentation tooling or hosted services.

## Proposed Model

Artifact ID sequences are independent per artifact family:

| Family | Proposed ID | Primary location |
|--------|-------------|------------------|
| RFC | `RFC-####` | `docs/rfcs/[0-9][0-9][0-9][0-9]-*.md` |
| Decision | `D###` today; possible `DEC-####` alias later | `DECISION_LOG.md` |
| Review | `REVIEW-####` | `docs/reviews/` |
| Phase | `PHASE-####` | `BUILD_PHASES.md` and `docs/phases/` |

Existing decision IDs remain canonical while this RFC is only proposed. If a
future accepted decision introduces `DEC-####`, it must define whether
`DEC-0034` is an alias for `D034` or a new successor namespace. Until then,
new docs should continue to use `D034`-style references for accepted decisions.

## Typed References

References should include the artifact type when stored in metadata. Prose may
continue to use normal Markdown links when that is clearer.

Recommended metadata format:

```md
Decision refs:
  - D034#request-profile
Review refs:
  - REVIEW-0003#context-overflow
Phase refs:
  - PHASE-0002#generation-activation
```

One artifact may reference many others. Shared numbering is not required and
should not be implied. For example, `RFC-0007` may lead to `D041`, several
review findings, and multiple phase edits without any of those artifacts
sharing the number `0007`.

## Subref Anchors

Subrefs use explicit anchors, not generated Markdown heading slugs.

Rules:

- Format: `<artifact-id>#<slug>`.
- Slugs are lowercase ASCII with words separated by hyphens.
- Slugs are unique within one artifact.
- Slugs are stable after publication, even if the visible heading changes.
- Do not rely on GitHub's auto-generated heading IDs.

Preferred Markdown pattern:

```md
<a id="request-profile"></a>
### Request Profile
```

Decision rows in `DECISION_LOG.md` need special care because table rows are not
good anchor targets. If this RFC is accepted, the implementation should either
add an explicit anchor registry for decisions or split decisions into anchored
sections. It should not depend on table-row positioning.

## RFC Header Guidance

Numbered RFC files should keep a small header. The exact format can be
expanded later, but it should remain human-readable Markdown:

```md
# RFC 0007: Artifact ID And Subref Model

Status: proposal
Date: 2026-05-03
Context: Documentation traceability; DECISION_LOG
Decision refs:
  - none
Review refs:
  - none
Phase refs:
  - none
```

This applies to numbered RFC documents only. `docs/rfcs/README.md` remains an
index and should be updated separately.

## Migration Strategy

If accepted, migrate in small additive passes:

1. Record the accepted decision in `DECISION_LOG.md`.
2. Define the decision compatibility rule for `D###` and any `DEC-####` alias.
3. Add explicit anchors only where a precise reference is needed.
4. Update numbered RFC headers, not the RFC index.
5. Introduce review and phase IDs only after their numbering and scope are
   clear.
6. Add a local reference checker before any broad mechanical rewrite.
7. Only then create an operational prompt to apply the accepted policy.

## Validation

A future checker should verify:

- referenced artifact IDs exist,
- referenced subref anchors exist,
- numbered RFC files are indexed in `docs/rfcs/README.md`,
- the RFC index is not treated as an RFC artifact,
- generated docs are not rewritten by hand.

The checker must run locally and must not require network access.

## Open Questions

1. Should decisions keep `D###` forever, with `DEC-####` rejected as churn?
2. If `DEC-####` is adopted, is it a pure alias for existing `D###` numbers?
3. Are phase IDs assigned to phase sections in `BUILD_PHASES.md`, files in
   `docs/phases/`, or both?
4. Are review IDs assigned per review document, per finding, or both?
5. Where should an artifact registry live, if one is needed at all?

## Recommendation

Keep this RFC in proposal state until the current Phase 2 work is stable. The
artifact model is useful, but it should not interrupt the active
AI-conversation segmentation and embedding run.
