# Claude Design Prompt: Engram UI Rework

You are Claude Design working on `/home/halbritt/git/engram`. Your job is to
produce an implementation-ready UI redesign handoff for Codex implementers. Do
not implement code in this pass.

## Required Context

Read these files first, in order:

- `AGENTS.md`
- `README.md`
- `HUMAN_REQUIREMENTS.md`
- `DECISION_LOG.md`
- `BUILD_PHASES.md`
- `ROADMAP.md`
- `SPEC.md`
- `docs/schema/README.md`
- `docs/howto/gold-set-interview.md`
- `docs/rfcs/0021-gold-set-interview-curation.md`
- `docs/rfcs/0027-interview-web-ui.md`
- `docs/specs/0027-interview-web-ui-spec.md`
- `docs/rfcs/0028-predicate-intent-surfacing.md`
- `docs/rfcs/0029-bench-triage-workbench.md`
- `src/engram/interview/web.py`
- `src/engram/interview/render.py`
- `src/engram/interview/templates/base.html`
- `src/engram/interview/templates/index.html`
- `src/engram/interview/templates/question.html`
- `src/engram/bench_review/web.py`
- `src/engram/bench_review/templates/base.html`
- `src/engram/bench_review/templates/index.html`
- `src/engram/bench_review/templates/segments.html`
- `src/engram/bench_review/templates/segment.html`
- `src/engram/bench_review/templates/summary.html`

Then inspect related tests on demand, especially:

- `tests/test_interview_web.py`
- `tests/test_interview_render.py`
- `tests/test_interview_storage.py`
- `tests/test_bench_review.py`

## Objective

Redesign Engram's local web operator experience around its current product
direction: a local-first personal memory layer where the operator reviews,
corrects, and promotes derived memory artifacts without raw user data leaving
the machine. The design should cover the existing gold-set interview UI and
bench triage workbench, and should leave clear extension points for future
Phase 4 entity/review surfaces without pretending those surfaces are already
built.

The output must be directly usable by Codex as an implementation brief. Prefer
precise interface structure, labels, state tables, route-aware behavior,
component requirements, and acceptance checks over broad visual direction.

## Product And Claim Boundaries

- Engram is local-first. Do not introduce cloud services, telemetry, hosted
  auth, remote assets, or external persistence.
- The UI must never imply that derived claims, beliefs, entities, benchmark
  recommendations, or prompt candidates are canonical without explicit review
  state and provenance.
- Raw evidence is immutable; derived tables and projections are rebuildable.
  The UI must preserve this mental model.
- Gold labels are advisory review artifacts, not automatic corrections to
  production memory.
- Bench triage decisions are scratch-local review evidence, not production
  extraction or consolidation inputs.
- Phase 4 full-corpus execution and promotion remain gated. Do not design a UI
  that presents Phase 4 as authorized or complete.
- RFC 0044 tenant-aware memory work is queued only. Do not assume ingestion or
  tenant isolation exists unless explicitly marked as future/backlog.

## Design Constraints

- Treat this as an operational review and memory-governance tool, not a
  marketing site.
- Do not create a landing-page hero.
- Avoid decorative gradients, orbs, bokeh, illustration-first layouts, and
  card-heavy marketing composition.
- Favor dense but readable information hierarchy, predictable navigation,
  compact controls, and side-by-side evidence comparison where it improves
  review quality.
- Preserve truthful claim boundaries. Confidence, provenance, stability class,
  privacy tier, extraction version, prompt version, and review state should be
  visible where they affect operator decisions.
- Make warnings and unsupported states visible without blocking normal local
  review unless the backend already requires a hard block.
- Respect the existing stack: FastAPI, Jinja2, htmx, server-rendered HTML,
  vendored static assets, no JavaScript build step.
- Do not require new backend capabilities unless you explicitly label them as
  future/backlog or RFC-required.
- Keep CLI parity visible. If an action belongs in CLI only, say so in the UI
  or leave it out.
- Design for responsive browser layouts. Mobile can be compact and inspectable;
  it does not need to make every expert workflow equally fast.

## Required Deliverable

Create a Markdown design handoff with these sections:

1. **Design Intent**
   - One short paragraph describing the redesigned Engram operator surface.
   - Explicit statement of the claims the UI must not make.

2. **Primary User Flows**
   - Open or resume a gold-label interview session.
   - Review one claim or belief with cited evidence.
   - Triage unsupported, stale, unsure, and false verdicts with rationale.
   - Inspect predicate intent, subject-kind hints, and warning states.
   - Save and resume an unfinished session.
   - Review benchmark segment queues and candidate/prior deltas.
   - Mark benchmark decisions and inspect readiness without promoting.
   - Export or hand off review evidence through CLI-owned paths.

3. **Information Architecture**
   - Proposed top-level navigation or layout regions across interview and
     bench-review surfaces.
   - What appears in the first viewport on desktop.
   - What collapses or moves on narrow screens.
   - How future Phase 4/entity-review surfaces can join the IA without being
     designed as if implemented now.

4. **Screen Specifications**
   - For each major screen or panel, include purpose, visible data, controls,
     empty states, loading states, error states, disabled states, and
     route/htmx behavior.
   - Include exact user-facing labels for important controls, warnings,
     status chips, and unavailable states.
   - Cover at least: interview session list/start, interview question page,
     evidence/message reveal panel, rationale capture, completion/abandon
     states, bench-review summary, bench queue list, bench segment detail, and
     bench readiness/export guidance.

5. **Component Inventory**
   - List reusable components Codex should build or refactor toward.
   - Include props/data requirements, states, and expected interactions.
   - Include components for evidence snippets, provenance rows, status chips,
     verdict controls, rationale editor, queue filters, diff/count tables,
     privacy-tier warnings, and keyboard review help.

6. **Truthfulness And State Rules**
   - Table of statuses and copy for accepted, candidate, proposed, reviewed,
     advisory, blocked, stale, unsupported, unsure, redacted, unavailable,
     failed, and future/backlog states.
   - Include how these statuses should surface in interview UI, bench-review
     UI, and future Phase 4 UI.
   - Include explicit wording for local-only and no-cloud assurances without
     turning them into marketing copy.

7. **Visual System**
   - Layout density, typography scale, spacing, icon usage, table/list style,
     evidence/diff treatment, form control treatment, and color semantics.
   - Keep the palette restrained but not one-note. Avoid dominant purple,
     beige/tan, dark slate/blue, or brown/orange themes.
   - Specify colors as semantic tokens, not just hex values.
   - Use familiar icon names where helpful, but do not require a new icon
     library unless the implementation map marks it as optional.

8. **Implementation Map**
   - Map each proposed UI change to likely files/modules.
   - Identify which changes are safe template/CSS/front-end-only work and
     which require Python route, storage, CLI, schema, or RFC support.
   - Mark any proposed future work that should become an RFC instead of being
     implemented immediately.
   - Preserve import-boundary expectations between `engram.interview` and
     `engram.bench_review`.

9. **Acceptance Checks For Codex**
   - Concrete checklist for automated tests.
   - Include route tests, htmx fragment checks, responsive screenshot checks,
     warning text assertions, keyboard/accessibility checks, no-CDN checks,
     local-only/no-network regression checks, and tests for unsupported or
     overclaiming status text.
   - Identify which checks belong in existing tests and which require new
     tests.

10. **Open Questions**
    - Only list questions that block implementation.
    - If a reasonable assumption is safe, make the assumption and label it.

## Output Rules

- Output only the design handoff Markdown.
- Use file references where relevant.
- Do not include implementation patches.
- Do not include an `author:` line.
- Do not propose cloud, telemetry, hosted auth, CDN assets, or remote storage.
- Do not invent backend capabilities as available. Label speculative work as
  future/backlog or RFC-required.
- Be specific enough that Codex can implement without interpreting visual
  intent from prose alone.
