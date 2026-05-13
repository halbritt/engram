# RFC 0030 Design Review Sources

Authoritative inputs for this run, in priority order:

## Primary
- `docs/rfcs/0030-public-dataset-entity-grounding.md` — the RFC under review.

## Adjacent RFCs
- `docs/rfcs/0011-phase-3-claims-beliefs.md` — schema baseline for claims/beliefs.
- `docs/rfcs/0017-extraction-prompt-versioning.md` — prompt-version immutability,
  re-extraction discipline.
- `docs/rfcs/0018-evidence-to-claim-audit-cascade.md` — audit cascade behavior.
- `docs/rfcs/0028-predicate-intent-surfacing.md` — entity-mismatch failure
  taxonomy that motivates RFC 0030.

## Principles and decisions
- `HUMAN_REQUIREMENTS.md` — local-first, refusal-of-false-precision.
- `DECISION_LOG.md` — D020 (LLM-local-only), D044 (gold-set advisory),
  D068 (artifact-id model), D076 (32k context budget), D080 (RFC 0027
  promotion).
- `BUILD_PHASES.md` — PHASE-0003 (extraction), PHASE-0004 (entity consolidation).

## Code references
- `src/engram/extractor.py` — `extract_claims_from_segment`,
  `EXTRACTION_PROMPT_VERSION`, `build_extraction_prompt`.
- `docs/schema/README.md` — current schema overview.

## Process
- `docs/process/multi-agent-review-loop.md` — review-loop discipline.
- `docs/process/project-judgment.md` — scope/priority guidance.
