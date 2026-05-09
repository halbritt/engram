# RFC 0030 Findings Ledger

Read the eight independent review artifacts (claude/codex/gemini + 5
adversarial) for RFC 0030 and normalize them into one findings ledger.

Output:

`docs/reviews/rfc0030-grounding-claim-extraction/FINDINGS_LEDGER.md`

## Structure

```md
# RFC 0030 Public-Dataset Entity Grounding Findings Ledger
author: <packet author line>

Status: findings
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

## Findings

### L001 - <normalized title>
Severity: <blocking | major | minor | nit>
Sources: <review ids, e.g. claude:F003, privacy_adversary:P001>
Disposition target: <accept | reject | defer | needs-owner>
Rationale: <paragraph>

## Cross-lane patterns
- Findings independently raised by 2+ lanes (especially across
  generic + adversarial pairs).
- Contradictions between lanes (one says blocker, another says fine).
- RFC sections flagged repeatedly without any single blocker.

## Consensus

## Conflicts

## Recommended next action
```

## Discipline

- Preserve source-lane provenance in every entry. Do not collapse a
  privacy_adversary finding into a generic-review finding without
  noting the lens.
- De-duplicate aggressively: two reviewers naming the same RFC line
  with the same concern is one ledger entry with two sources.
- Prefer "needs-owner" disposition for any finding the synthesizer
  would otherwise have to guess on.
- Do not include private corpus excerpts.

Do not modify files outside `docs/reviews/rfc0030-grounding-claim-extraction/`.
