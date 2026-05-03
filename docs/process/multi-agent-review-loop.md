# Multi-Agent Review Loop

Use this procedure when one agent creates a substantial artifact and another
agent reviews it. The goal is to keep feedback out of volatile human memory and
out of direct, unreviewed edits to the artifact.

## When To Use

Use this loop for:

- RFCs,
- benchmark or implementation specs,
- phase prompts,
- architecture synthesis,
- larger code changes that need adversarial review.

For small typo fixes or narrow implementation patches, a normal single-agent
edit is enough.

## Procedure

1. **Originating agent creates the artifact.**
   The artifact may be an RFC, prompt, spec, implementation plan, or patch.

2. **Reviewing agent writes feedback under `docs/reviews/`.**
   The reviewer should not patch the artifact directly unless explicitly
   assigned to do so. Review findings should include severity, rationale,
   affected files or sections, and a proposed fix when possible.

3. **Originating agent synthesizes the review.**
   The originating agent classifies each finding as accepted, accepted with
   modification, deferred, or rejected. The synthesis can live in the review
   document or in a separate synthesis document under `docs/reviews/`.

4. **Originating agent applies accepted deltas.**
   Accepted feedback updates the source artifact. Binding architecture changes
   update `DECISION_LOG.md`. Sequencing changes update `BUILD_PHASES.md` or
   `ROADMAP.md`. Execution handoffs belong in `prompts/`.

5. **Keep the review artifact.**
   Do not delete the critique after synthesis. It is provenance for why the
   artifact changed.

## Context-Window Rule

After synthesis, prefer a fresh context window for execution. The synthesis
context is for judgment; the execution context should receive a clean prompt
containing only the accepted decisions, non-goals, traps, files in scope, test
commands, and acceptance criteria.

Use the same context window only for tiny changes where the implementation is
already obvious and the review debate will not pollute the worker's attention.

## Storage Rule

```text
Raw feedback -> docs/reviews/
Accepted deltas -> original artifact
Binding architecture -> DECISION_LOG.md
Sequencing changes -> BUILD_PHASES.md / ROADMAP.md
Execution handoff -> prompts/
```

## Example

For the segmentation benchmark:

1. Codex-on-box implements or updates the benchmark spec.
2. Opus writes a review under `docs/reviews/v1/`.
3. Codex synthesizes the review and updates the spec.
4. Codex starts a fresh execution context to run the benchmark, tests, and
   result capture.
