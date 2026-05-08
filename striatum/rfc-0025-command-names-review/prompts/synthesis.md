# RFC 0025 Synthesis — Task

Read `RFC_0025_COMMAND_NAMES_FINDINGS_LEDGER.md` plus RFC 0025 and the current
command surface (`README.md`, `Makefile`, `src/engram/cli.py`).

Produce a synthesis that recommends one of these outcomes:

1. **accept-rfc** — the RFC is ready for an accepted decision.
2. **revise-rfc** — the RFC should be amended before acceptance.
3. **split-rfc** — the RFC combines separable decisions and should be split.
4. **reject-rfc** — the proposed taxonomy is wrong for Engram.

## Output

Write to `docs/reviews/rfc0025/RFC_0025_COMMAND_NAMES_SYNTHESIS.md`:

```md
# RFC 0025 Command-Names Synthesis

Status: synthesis
Date: <YYYY-MM-DD>
RFC refs: RFC-0025
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

<short paragraph explaining the choice and the next implementation step.>

## Risks the synthesis carries

- <each place the synthesis chose a resolution the ledger did not
  unambiguously support>
```

Do not modify the ledger or any review file. Do not edit RFC 0025, Makefile,
README, or source code.
