# RFC 0053 Apply Accepted Deltas -- Task

Apply only the accepted deltas from
`docs/reviews/rfc0053-claim-grounding-boundary/SYNTHESIS.md`.

## Scope

Allowed targets are the RFC 0053 proposal, RFC index text, roadmap/changelog
status, schema README text, and RFC 0053 review artifacts. Do not edit Python,
migrations, or tests in this job unless the synthesis explicitly says a
contract test is wrong and the allowed write scope includes it.

## Output

Write `docs/reviews/rfc0053-claim-grounding-boundary/APPLY_HANDOFF.md`:

```md
# RFC 0053 Accepted Delta Handoff

Status: applied
Date: 2026-05-18
Lane: codex_author
Role: author

## Applied

- <file>: <summary>

## Verification

- <command>: <result>

## Remaining

- <remaining blocker or "none">
```
