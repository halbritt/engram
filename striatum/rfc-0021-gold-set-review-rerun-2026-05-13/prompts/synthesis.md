# RFC 0021 Synthesis — Task

Read `RFC_0021_GOLD_SET_FINDINGS_LEDGER.md` plus RFC 0021, RFC 0011,
`HUMAN_REQUIREMENTS.md`, and `DECISION_LOG.md`.

Produce a synthesis that recommends one of these outcomes:

1. **accept-rfc** — the RFC is ready for an accepted decision and
   implementation handoff.
2. **revise-rfc** — the RFC should be amended before acceptance.
3. **split-rfc** — the RFC combines separable decisions and should be split.
4. **reject-rfc** — the proposed approach is wrong for Engram.

If the recommendation is `accept-rfc`, the synthesis must also produce:

- a concrete next-migration-number for the gold-labels table (since
  migrations 008 and 009 already exist);
- the exact BUILD_PHASES line(s) to add under Phase 3 follow-on;
- the exact DECISION_LOG entry text to append on acceptance.

## Output

Write to `docs/reviews/rfc0021-rerun-2026-05-13/RFC_0021_GOLD_SET_SYNTHESIS.md`:

```md
# RFC 0021 Gold-Set Interview Curation Synthesis

Status: synthesis
Date: <YYYY-MM-DD>
RFC refs: RFC-0021
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

## Acceptance deltas (only if accept-rfc)

### Migration number
Next available: `XXX_gold_labels.sql` (justify based on `migrations/` listing).

### BUILD_PHASES.md insert
```text
<exact text to add under Phase 3 follow-on / Step 5 substrate>
```

### DECISION_LOG.md insert
```text
<exact text for a new D### entry>
```

## Risks the synthesis carries

- <each place the synthesis chose a resolution the ledger did not
  unambiguously support>
```

Do not modify the ledger or any review file. Do not edit RFC 0021,
`BUILD_PHASES.md`, `DECISION_LOG.md`, `HUMAN_REQUIREMENTS.md`, `Makefile`,
README, or source code.
