# 02_SPEC_REVIEW_claude_opus_4_7.ready

Prompt: P022 — Review Phase 3 Claims And Beliefs Spec
Model / agent: claude_opus_4_7 (fresh context, secondary architecture review)
Started:   2026-05-05T07:32Z
Completed: 2026-05-05T07:46Z

## Files written

- `docs/reviews/phase3/PHASE_3_CLAIMS_BELIEFS_SPEC_REVIEW_claude_opus_4_7_2026_05_05.md`
  — adversarial architecture review of `docs/claims_beliefs.md`. Verdict:
  `accept_with_findings`. Two P0 findings (bitemporal close rule;
  re-extraction blast radius), six P1 findings, and a set of P2/P3
  cleanup items.

## Files read

- `docs/reviews/phase3/markers/01_SPEC_DRAFT.ready.md`
- `docs/claims_beliefs.md`
- `docs/rfcs/0011-phase-3-claims-beliefs.md`
- `README.md`
- `HUMAN_REQUIREMENTS.md`
- `DECISION_LOG.md`
- `BUILD_PHASES.md`
- `ROADMAP.md`
- `SPEC.md`
- `docs/schema/README.md`
- `docs/segmentation.md`
- `docs/process/multi-agent-review-loop.md`

I did not read peer reviewers' reviews (Gemini, Codex) so the findings
remain independent. I did not edit `docs/claims_beliefs.md`. I did not
write code. I did not call external services.

## Headline findings

- **P0-1.** Contradiction-supersession rule sets prior `valid_to = now()`
  while new belief `valid_from = MIN(messages.created_at)` over new
  evidence. Result: intervals always overlap on historical corpus, the
  spec's own auto-resolution rule is dead code, and biographic queries
  observe wrong supersession dates by years. Acceptance test #22 cannot
  pass as written.
- **P0-2.** Re-extraction creates two co-active vintages of `claims` per
  segment that both feed the consolidator. Old + new vintage with
  different values produces spurious contradictions on every prompt bump.
  Violates D045 ("blast radius bounded"). Spec needs a "consolidator
  reads only the latest extraction-version's claims per segment" rule.

## Verdict

`accept_with_findings`. P024 should resolve P0-1 and P0-2 before the
build prompt; P1 items (subject_normalized computation site, unique
index for active beliefs, partial-reclassification decision tree,
rebuild idempotency, discovery-vs-biographic time documentation) should
land in the same synthesis pass.

## Next expected marker

`03_SPEC_FINDINGS_LEDGER.ready.md` — synthesis of the three reviewer
markers (Gemini Pro 3.1 already filed; Codex GPT-5.5 expected; this
Opus 4.7 review). Per `docs/process/phase-3-agent-runbook.md`, the
synthesis owner can amend `docs/claims_beliefs.md` and add DECISION_LOG
entries as needed.
