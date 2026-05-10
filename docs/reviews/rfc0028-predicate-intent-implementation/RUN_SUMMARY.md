# Striatum Run Summary

Run ID: `run_66ba248f6e4f47e49c130bca866e383f`
Branch: `engram/rfc0028-predicate-intent-implementation`
Run state: `completed`
Verification: `doctor ok=false`

## Timing

- Created at: `2026-05-09T02:10:34Z`
- Started at: `2026-05-09T02:10:48Z`
- Completed at: `2026-05-09T02:48:47Z`
- Duration: `0h 37m 59s`

## Jobs

- `completed`: 8

## Verdicts

- `review_gemini` (1 attempts): `accept`
- `review_codex` (1 attempts): `accept_with_findings`
- `review_claude` (1 attempts): `accept_with_findings`
- `final_review` (1 attempts): `accept`

## Artifacts

- `finding` `final_review`: `docs/reviews/rfc0028-predicate-intent-implementation/FINAL_REVIEW.md` - `author: reviewer-codex-gpt-5.5-003`
- `findings_ledger` `ledger`: `docs/reviews/rfc0028-predicate-intent-implementation/FINDINGS_LEDGER.md` - `author: ledger-codex-gpt-5.5-002`
- `handoff` `implementation_handoff`: `docs/reviews/rfc0028-predicate-intent-implementation/IMPLEMENTATION_HANDOFF.md` - `author: author-codex-gpt-5.5-001`
- `finding` `review`: `docs/reviews/rfc0028-predicate-intent-implementation/REVIEW_claude.md` - `author: reviewer-claude-opus-002`
- `finding` `review`: `docs/reviews/rfc0028-predicate-intent-implementation/REVIEW_codex.md` - `author: reviewer-codex-gpt-5.5-002`
- `finding` `review`: `docs/reviews/rfc0028-predicate-intent-implementation/REVIEW_gemini.md` - `author: reviewer-gemini-3.1-pro-preview-001`
- `finding` `review_recovered`: `docs/reviews/rfc0028-predicate-intent-implementation/REVIEW_gemini.md` - `author: reviewer-gemini-3.1-pro-preview-002`
- `handoff` `revision_handoff`: `docs/reviews/rfc0028-predicate-intent-implementation/REVISION_HANDOFF.md` - `author: author-codex-gpt-5.5-002`
- `synthesis` `revision_synthesis`: `docs/reviews/rfc0028-predicate-intent-implementation/REVISION_SYNTHESIS.md` - `author: synthesizer-codex-gpt-5.5-001`

## Sessions

- `author-codex-1` `closed` (closed_at: `2026-05-09T02:27:03Z`) reason: `implementation job completed and handoff published`
- `reviewer-claude-1` `closed` (closed_at: `2026-05-09T02:44:30Z`) reason: `requeued blocked adapter review for manual artifact submission`
- `reviewer-codex-1` `closed` (closed_at: `2026-05-09T02:40:12Z`) reason: `adapter job was requeued after manual review artifact recovery`
- `reviewer-gemini-1` `closed` (closed_at: `2026-05-09T02:35:39Z`) reason: `adapter job was requeued after manual review artifact recovery`
- `reviewer-gemini-2` `closed` (closed_at: `2026-05-09T02:48:08Z`) reason: `review lane complete`
- `reviewer-codex-2` `closed` (closed_at: `2026-05-09T02:48:08Z`) reason: `review lane complete`
- `reviewer-claude-2` `closed` (closed_at: `2026-05-09T02:48:08Z`) reason: `review lane complete`
- `ledger-codex-1` `closed` (closed_at: `2026-05-09T02:48:08Z`) reason: `unused duplicate ledger session`
- `ledger-codex-2` `closed` (closed_at: `2026-05-09T02:48:08Z`) reason: `ledger job complete`
- `synthesizer-codex-1` `closed` (closed_at: `2026-05-09T02:48:08Z`) reason: `synthesis job complete`
- `author-codex-2` `closed` (closed_at: `2026-05-09T02:48:09Z`) reason: `apply findings job complete`
- `reviewer-codex-3` `closed` (closed_at: `2026-05-09T02:48:47Z`) reason: `run_completed`

## Blockers

- `open` `blocked` `process_review_verdict_missing` (blk_b17b8f9d745845e7871c3c58e627016d)
- `open` `blocked` `process_review_verdict_missing` (blk_21f692125f53493f9c378a3865e51be8)
- `open` `blocked` `process_review_verdict_missing` (blk_857ee9425c734fcd8eeccb4a6b09ebfa)

## Next Actions

- `inspect_blocker`
- `export_run_evidence`
