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

## RFC-To-Spec Promotion

RFCs are proposal and provenance artifacts. They are useful for framing a
problem, collecting review pressure, and explaining why a concrete contract
exists. They should not remain the implementation target after an accepted spec
or equivalent handoff exists.

When review turns an RFC into a spec handoff:

1. Put the explicit implementation choices in the spec, not in scattered review
   comments or coordinator memory.
2. Review the RFC and spec as a package until the spec is clear enough to be
   accepted or rejected.
3. When the spec is accepted, record the project decision in `DECISION_LOG.md`
   or another canonical decision surface named by the project.
4. Mark the RFC as `promoted` or `superseded` and link to the accepted spec.
   The RFC remains historical context.
5. Future implementation prompts and reviews target the accepted spec. They may
   cite the RFC for provenance, but should not ask whether the historical RFC is
   self-contained unless the task is explicitly to revise that RFC.

If a spec is not accepted yet, the package remains in proposal/revision state.
An agent should not implement from it merely because the RFC exists or because
review artifacts recommended a direction.

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
Accepted RFC-to-spec handoff -> accepted spec + promoted/superseded RFC
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
