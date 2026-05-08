# RFC 0025 Command-Names Review — Task

You are reviewing RFC 0025, the proposed command naming cleanup for Engram's
phase pipelines. Your job is to surface ambiguity, operator-safety gaps,
backwards-compatibility risks, and implementation pitfalls before the owner
decides whether to accept the RFC.

## Inputs

- `docs/rfcs/0025-phase-scoped-command-names.md` — the RFC under review.
- `README.md` — current operator-facing command examples.
- `Makefile` — current Make targets.
- `src/engram/cli.py` — current CLI command surface.
- `BUILD_PHASES.md` — authoritative phase boundaries.
- `DECISION_LOG.md` and `HUMAN_REQUIREMENTS.md` — local-first, phase, and
  operator-safety constraints.

## Review checklist

1. **Naming clarity.** Does the proposed `phaseN` command shape prevent the
   concrete mistake that motivated the RFC?
2. **Fail-closed behavior.** Is making bare `pipeline` non-mutating the right
   default, and is the acceptance test strong enough?
3. **Compatibility.** Does the migration plan protect scripts while still
   removing the dangerous behavior quickly?
4. **Argparse / Make feasibility.** Are nested CLI subcommands and phase-scoped
   Make targets practical in this repo without a broad refactor?
5. **Phase boundary accuracy.** Do the command names match PHASE-0002,
   PHASE-0003, PHASE-0004, PHASE-0005, and PHASE-SMOKE?
6. **Operator ergonomics.** Are the names short and predictable enough for
   repeated local use?
7. **Documentation coverage.** Does the RFC require README and help text
   updates in enough places?
8. **What is missing.** Identify any command, target, or failure mode the RFC
   does not cover.

## Output

Write your review to the path in your job packet:
`docs/reviews/rfc0025/RFC_0025_COMMAND_NAMES_REVIEW_<lane>.md`.

Use this structure:

```md
# RFC 0025 Command-Names Review — <lane>

Status: review
Date: <YYYY-MM-DD>
RFC refs: RFC-0025
Decision refs: ...
Phase refs: ...

## Findings

### F001 — <one-line title>
Severity: <blocking | major | minor | nit>
Source: <path>:<line range or section anchor>
Rationale: <one paragraph>

[... more findings ...]

## Open questions

- <questions to resolve before acceptance or implementation>

verdict: <accept | accept_with_findings | needs_revision | reject>
```

Do not modify any file outside the path your packet specifies. Do not edit the
RFC, `BUILD_PHASES.md`, `DECISION_LOG.md`, `Makefile`, or `src/engram/cli.py`.
