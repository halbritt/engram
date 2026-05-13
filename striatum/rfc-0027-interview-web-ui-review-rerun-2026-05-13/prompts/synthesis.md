# RFC 0027 Synthesis — Task

Read `RFC_0027_INTERVIEW_WEB_UI_FINDINGS_LEDGER.md` plus RFC 0027,
RFC 0021, `HUMAN_REQUIREMENTS.md`, and `DECISION_LOG.md`.

Produce a synthesis recommending one of:

1. **accept-rfc** — RFC is ready to promote to a spec for
   implementation handoff.
2. **revise-rfc** — RFC needs concrete edits before acceptance.
3. **split-rfc** — separable decisions; split into two RFCs.
4. **reject-rfc** — proposed approach is wrong for Engram.

If the recommendation is **accept-rfc**, the synthesis must include a
**Spec deltas** section concrete enough to be the implementation
contract, covering at minimum:

- final route table (verb / path / purpose / htmx swap target);
- final template list (path / purpose);
- `src/engram/interview/render.py` API surface (full function
  signatures);
- migration plan (none, or `011_gold_label_session_targets.sql`
  shape);
- `pyproject.toml` deltas (deps, optional extras);
- test surface (files and what they cover);
- privacy-tier env var name + default;
- verdict keyboard-shortcut letter assignment;
- BUILD_PHASES insert text;
- DECISION_LOG entry text (next available D###).

## Output

Write to `docs/reviews/rfc0027-rerun-2026-05-13/RFC_0027_INTERVIEW_WEB_UI_SYNTHESIS.md`:

```md
# RFC 0027 Interview Web UI Synthesis

Status: synthesis
Date: <YYYY-MM-DD>
RFC refs: RFC-0027
Decision refs: ...
Phase refs: ...

## Findings outcome

| ID  | Outcome  | Reason |
|-----|----------|--------|
| F001 | accepted | <one-line reason> |

## Open decisions

### O001 — <one-line question>
- Option A — <one-line description>
- Option B — <one-line description>
- Recommended: <A | B>
- Rationale: <one paragraph>

## Recommendation

<one of: accept-rfc | revise-rfc | split-rfc | reject-rfc>

<paragraph explaining the choice and what comes next.>

## Spec deltas (only if accept-rfc)

### Routes

| Verb | Path | Purpose | HX-Swap |
|------|------|---------|---------|

### Templates

### `src/engram/interview/render.py` API

### Migration plan

### `pyproject.toml` deltas

### Test surface

### Privacy-tier env var

### Verdict keyboard shortcuts

### BUILD_PHASES.md insert

### DECISION_LOG.md entry

## Risks the synthesis carries

- <each place the synthesis chose a resolution the ledger did not
  unambiguously support>
```

Do not modify the ledger or any review file. Do not edit RFC 0027,
BUILD_PHASES.md, DECISION_LOG.md, HUMAN_REQUIREMENTS.md, Makefile,
README, or source code.
