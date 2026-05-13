# Implement RFC 0028 Predicate-Intent Surfacing

Read the work packet, `AGENTS.md`, RFC 0028, `docs/rfcs/0012-python-agentic-coding-standard.md`,
`src/engram/extractor.py`, `src/engram/interview/render.py`,
`src/engram/interview/web.py`, `migrations/006_claims_beliefs.sql`,
`tests/test_phase3_claims_beliefs.py`, and `tests/test_interview_render.py`
before editing.

Implement the owner-directed RFC 0028 slice:

This is a fresh provenance run after RFC 0032. Do not rely on quarantined
review artifacts as authoritative evidence. Treat the existing implementation
as code to audit and repair, not as accepted architecture. If your runtime
supports sub-agents, delegate independent implementation, test, and doc checks
to the maximum useful number of sub-agents, with disjoint file ownership and no
reverts of other agents' work.

1. Add migration `012_predicate_subject_kind_hint.sql` with nullable
   `predicate_vocabulary.subject_kind_hint TEXT`.
2. Seed subject-kind hints for the existing predicate vocabulary. Keep the
   values human-readable free text, not an enum.
3. Add `description` and `subject_kind_hint` metadata to
   `PREDICATE_VOCABULARY`, and update phase-3 schema preflight to catch
   metadata drift between the runtime vocabulary and database vocabulary.
4. Bump `EXTRACTION_PROMPT_VERSION` to the next extractor prompt version for
   predicate intent, and render each predicate's description and hint in
   `build_extraction_prompt`.
5. Update interview rendering so predicate intent is on its own line under the
   triple. Render a warning line when the subject-kind hint and a small local
   heuristic indicate a likely predicate/subject mismatch.
6. Broaden the `false` rationale prompt label for both CLI and web surfaces.
7. Add deterministic tests. Do not call live LLMs.
8. Update `CHANGELOG.md`, RFC 0028 / RFC index status, and generated schema
   docs if schema generation is available. Do not add a `DECISION_LOG.md` row
   unless a later fresh review explicitly accepts promotion.

Do not run full-corpus re-extraction. Bench/re-extract remains a follow-up
operator action after this code lands.

When done, write
`docs/reviews/rfc0028-predicate-intent-promotion-2026-05-13/IMPLEMENTATION_HANDOFF.md`
with the exact lowercase `author:` line from the work packet, changed files,
commands run, and residual risks.
