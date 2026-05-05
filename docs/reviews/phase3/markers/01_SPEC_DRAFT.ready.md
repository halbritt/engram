# 01_SPEC_DRAFT.ready

Prompt: P021 — Generate Phase 3 Claims And Beliefs Spec
Model / agent: claude_opus_4_7 (Architecture author)
Started:   2026-05-05T07:24Z
Completed: 2026-05-05T07:29Z

## Files written or modified

- `docs/claims_beliefs.md` — new Phase 3 spec, drafted from RFC 0011 +
  D043–D047 + Phase 2 audit findings. Pins schema, extractor prompt and
  request profile, predicate vocabulary, deterministic consolidator decision
  rules, time semantics, privacy / reclassification invalidation behavior,
  resumability, CLI surface, and acceptance tests. Section *Open owner
  checkpoints* lists the items P024 may amend.
- `docs/README.md` — added the new spec link under *Current Design*.
- `docs/reviews/phase3/markers/01_SPEC_DRAFT.ready.md` — this marker.

## Verification performed

- Read the required upstream docs: README, HUMAN_REQUIREMENTS, DECISION_LOG
  (through D047), BUILD_PHASES, ROADMAP, SPEC, docs/schema/README,
  docs/segmentation, RFC 0011, phase-3 agent runbook, the Phase 2 span
  expansion audit (2026-05-04), and the Phase 2 Qwen-27B umbrella A/B
  (2026-05-05).
- Confirmed D043–D047 are already accepted in DECISION_LOG; spec treats
  them as binding, not as open questions.
- Confirmed the P021 constraint list: no cloud APIs / hosted services, no
  weakening of raw immutability or local-first, no code, no build prompt,
  no DECISION_LOG edits.
- Ran `git status --short` before writing. Three Phase 3 worktree files
  predate this spec and are unrelated to this prompt:
  `migrations/006_claims_beliefs.sql`, `src/engram/extractor.py`,
  `src/engram/consolidator.py`, `tests/test_phase3_claims_beliefs.py`,
  plus a modified `DECISION_LOG.md`, `src/engram/cli.py`, `tests/conftest.py`,
  and a renamed migration `004_source_kind_gemini.sql ->
  005_source_kind_gemini.sql`. None of those files were edited by this
  prompt; reviewers should treat them as in-flight context, not as the
  spec target.

## Unresolved questions reviewers should focus on

1. **Predicate vocabulary lock-in (RFC 0011 OQ1 / D046).** The spec ships
   a flat 30-predicate enum. Reviewers should weigh: is the list complete
   enough for the AI-conversation corpus, are the predicate ↔
   stability-class assignments correct, and should any predicate be split
   or merged? This is the largest single owner judgment call.
2. **`valid_from` derivation.** Spec uses `MIN(messages.created_at)` over
   `evidence_ids`; the alternative is `MAX(...)`. Reviewers should
   challenge with concrete close-and-insert examples to see whether the
   default produces wrong supersession order anywhere in the corpus.
3. **`observed_at` derivation (RFC 0011 OQ7).** Spec uses
   `MAX(messages.created_at)`. Reviewers should confirm this is what the
   contradiction auto-resolution rule (`temporal_ordering`) actually needs,
   not the median or the most-recent-cited message.
4. **Auto-resolution scope (RFC 0011 OQ5).** Spec restricts auto-resolution
   to non-overlapping intervals. Reviewers should challenge whether
   identity / project_status beliefs need stricter or looser auto-resolve
   gates than mood beliefs in V1, or whether everything except temporal
   ordering should land in the Phase 4 review queue (the spec's default).
5. **Reclassification → belief rejection rule.** Spec says beliefs whose
   `claim_ids` are *fully* drawn from invalidated claims are rejected.
   Beliefs *partially* supported by invalidated claims are recomputed.
   Reviewers should validate this matches D023 / D028 / D032 intent and
   that the partial case is reproducible from the deterministic
   consolidator without LLM input.
6. **Pre-existing Phase 3 worktree files vs the spec.** The repo has an
   in-flight `migrations/006_claims_beliefs.sql` and Python skeletons that
   pre-date this spec. They diverge on at least the migration filename
   slot, the omission of `subject_normalized` and `extraction_id`, and
   privacy reclassification handling. The build prompt (P025) should treat
   the spec as authoritative and direct the implementer to bring those
   files into alignment, not the other way around. Reviewers should flag
   any spec choice that would force the in-flight code to throw away
   substantial work without good reason.
7. **`belief_audit.evidence_episode_ids` column name.** The spec keeps the
   D010-era name but documents it as raw `messages.id`s. If reviewers
   prefer renaming to `evidence_message_ids` for consistency with `claims`,
   flag for P024 — the change is cheap before any rows exist.
8. **`engram consolidate --rebuild` semantics.** Spec proposes that
   rebuild closes the active belief set and reruns deterministic
   consolidation over current active claims. Reviewers should confirm
   this is the right trade-off vs. "only re-run for newly-superseded
   group keys," especially given the no-auto-rebuild rule from D045.

## Next expected marker

`02_SPEC_REVIEW_<model_slug>.ready.md` — fan-out spec reviews from
Gemini Pro 3.1 (broad adversarial), Codex GPT-5.5 (implementation
feasibility), and Opus 4.7 fresh context (secondary architecture review),
per `docs/process/phase-3-agent-runbook.md`. Default is one marker each
before synthesis at marker `03_SPEC_FINDINGS_LEDGER.ready.md`.
