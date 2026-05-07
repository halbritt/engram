# Artifact ID and Subref Conventions

Status: accepted (D068, 2026-05-07)
Source RFC: [RFC-0007](../rfcs/0007-artifact-id-and-subref-model.md)

This document is the executable spec for the artifact ID and subref system
accepted in D068. RFC 0007 is the design rationale; this file is the rule set
that tools and agents apply.

The model is deliberately conservative: existing identifiers stay canonical,
nothing is renamed in one broad pass, and every change is additive. Anyone
extending Engram's documentation should follow these rules; the reference
checker at `scripts/check_artifact_refs.py` enforces them.

## ID families

| Family | ID format | Primary location | Notes |
|--------|-----------|------------------|-------|
| RFC | `RFC-NNNN` (4 digits) | `docs/rfcs/NNNN-*.md` | ID matches the filename ordinal. |
| Decision | `D###` (3 digits) | `DECISION_LOG.md` | Canonical; **no** `DEC-####` alias. |
| Phase | `PHASE-NNNN` (4 digits) | `BUILD_PHASES.md`, `docs/phases/` | Phase 1=`PHASE-0001`, 1.5=`PHASE-0001.5` (literal in slug: `phase-0001-5`), 2=`PHASE-0002`, etc. |
| Review | `REVIEW-NNNN` (4 digits) | `docs/reviews/**/*.md` | Assigned per top-level review document; sub-findings via slug anchors. |
| Prompt | `P###` (existing global ordinal) | `prompts/P###_*.md` | Treated as `PROMPT-###` in references. **Not renamed.** |

Numbering is independent across families. `RFC-0007` does **not** imply any
relationship to `D007`, `PHASE-0007`, or `REVIEW-0007`.

## Subref anchor rules

Subrefs use explicit HTML anchors, **not** GitHub-generated heading slugs.

```md
<a id="request-profile"></a>
### Request Profile
```

- Format: `<artifact-id>#<slug>`. Example: `RFC-0006#synthetic-fixture-set`.
- Slugs are lowercase ASCII; words separated by single hyphens.
- Slugs are unique within one artifact.
- Slugs are stable after publication, even if the visible heading changes.
- Anchors precede the heading on a separate line. The heading text may evolve
  freely; the slug is the contract.
- For decisions, the canonical anchor is `dNNN` lowercase: `D034#request-profile`
  resolves to `<a id="d034"></a>` followed by an optional finer slug anchor.

When a heading is referenced from another document, an explicit anchor must
exist. Adding anchors only where references exist is the preferred pattern;
do not anchor every heading speculatively.

## File-level ID anchors

Every numbered RFC, phase, and review document begins with a file-level anchor
matching its ID. The first line of the file is the anchor, the second is the
H1 title.

```md
<a id="rfc-0007"></a>
# RFC 0007: Artifact ID And Subref Model
```

`DECISION_LOG.md` is one file with many decisions; each `D###` row gets an
inline anchor immediately before the row, on its own line:

```md
<a id="d068"></a>
| D068 | accepted | ... |
```

`BUILD_PHASES.md` is one file with many phases; each phase H2 gets a preceding
anchor:

```md
<a id="phase-0002"></a>
## Phase 2 — Segmentation + embeddings
```

## Header block (numbered RFCs, phases, reviews)

Long-lived numbered artifacts carry a small header block immediately after the
H1 title. The fields are:

```md
Status: <proposal | specified | accepted | promoted | superseded>
Date: YYYY-MM-DD
Context: <one short line>
Decision refs:
  - <list of D### or "none">
Review refs:
  - <list of REVIEW-#### or "none">
Phase refs:
  - <list of PHASE-#### or "none">
RFC refs:
  - <list of RFC-#### or "none">    (only on non-RFC artifacts)
```

Existing fields like `Status` and `Date` are preserved. Missing fields are
filled with `none` when no reference exists. If an RFC predates this
convention and uses a slightly different shape (e.g. only `Status` + `Date`),
extend rather than rewrite — keep the prose body untouched.

For prompts, use a smaller variant (Status, Phase, RFC refs, Decision refs,
Review refs, Safe to execute):

```md
# P018: Run Segmentation Early-Signal Benchmark

Status: ready | superseded | done
Phase: Phase 2
RFC refs:
  - RFC-0008
Decision refs:
  - D042
Review refs:
  - none
Safe to execute: yes
```

Prompt files are **not** renamed. Existing `P###` filenames stay; the header
block is additive.

## Reference syntax

Inside metadata blocks (header `Decision refs:` etc.), use bare IDs:

```md
Decision refs:
  - D034
  - D042#request-profile
```

Inside prose, prefer linked Markdown when the link target is unambiguous:

```md
See [D034](../DECISION_LOG.md#d034) for the request-profile decision.
```

The reference checker accepts both forms.

## What the reference checker enforces

`scripts/check_artifact_refs.py` runs locally with no network access and
verifies:

1. Every `RFC-NNNN` referenced anywhere in the repo corresponds to a file
   `docs/rfcs/NNNN-*.md`.
2. Every `D###` referenced corresponds to a row in `DECISION_LOG.md`.
3. Every `PHASE-NNNN` corresponds to an anchor in `BUILD_PHASES.md` or a file
   under `docs/phases/`.
4. Every `REVIEW-NNNN` corresponds to a header anchor under `docs/reviews/`
   and is listed in `docs/artifacts/review-id-registry.md`.
5. Every `<artifact-id>#<slug>` reference resolves to an `<a id="slug"></a>`
   inside the target artifact.
6. Numbered RFC files have file-level anchors and are listed in
   `docs/rfcs/README.md`.
7. Prompt ordinals are unique within `prompts/` (warned during initial
   adoption, hard error under `--strict`; one historical collision at `P024`
   from the codex-review/synthesize loop is acknowledged and not renamed —
   filename references would break).

The checker exits non-zero on any failure. It is run manually or from CI, not
on every commit, until the convention has settled.

## Migration discipline

- **Additive only.** Add anchors and headers; do not rename files or restructure
  prose.
- **One-shot adoption is safe.** Because the work is additive and ID-stable, all
  artifacts can adopt the convention in one sweep without breaking older
  references.
- **References are best-effort during adoption.** A missing anchor is a checker
  warning, not a build failure, until the bulk pass completes.
- **`docs/rfcs/README.md` is an index, not an RFC.** It does not get an
  `RFC-####` ID. The checker treats it specially.
- **Generated docs are off-limits.** `make schema-docs` regenerates schema
  documentation; the checker skips files declared as generated.

## Open follow-ups

These were left out of the initial adoption to keep scope small. Each is a
candidate for a future, separately-recorded decision:

- Phase-local prompt folders (`prompts/phase_2/...`) instead of the global
  `P###` scheme. RFC 0007 §Prompt Ordinals prefers this shape; D068 keeps the
  global scheme until renaming pays back.
- A standalone artifact registry file mapping IDs to titles. D068 defers this;
  filenames already encode the ID, and the checker derives the registry by
  scan.
- Sub-finding IDs inside review documents (e.g. `REVIEW-0003.F12`). D068
  resolves sub-findings via slug anchors; introduce composite IDs only if
  cross-document references to specific findings become common.
