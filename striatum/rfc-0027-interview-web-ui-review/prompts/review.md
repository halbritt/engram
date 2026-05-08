# RFC 0027 Interview Web UI — Review Task

You are reviewing RFC 0027, the proposal for a localhost-only
FastAPI + htmx web UI over the gold-set interview surface (RFC 0021 /
D079). Your job is to surface privacy, reuse, route, schema, test, and
operator-UX risks before the owner decides whether to accept the RFC.

## Inputs

- `docs/rfcs/0027-interview-web-ui.md` — the RFC under review.
- `docs/rfcs/0021-gold-set-interview-curation.md` — the upstream RFC
  whose web surface this RFC implements.
- `docs/rfcs/0022-server-binary-api-mcp.md` — the server-binary RFC
  whose D020 localhost posture this RFC mirrors.
- `src/engram/cli.py` — current interview CLI loop, including
  `_fetch_target_display`, `_fetch_evidence_excerpts`, `_pick_question`,
  `_RATIONALE_PROMPT_BY_VERDICT`. The render.py extraction is meant
  to unify these.
- `src/engram/interview/{sampler,agent,storage}.py` — modules the
  web layer reuses.
- `migrations/010_gold_labels.sql` — current schema. The persistent
  target order question proposes a new migration.
- `HUMAN_REQUIREMENTS.md`, `DECISION_LOG.md` (esp. D016, D044, D069,
  D074, D079).
- `BUILD_PHASES.md`, `ROADMAP.md`.

## Review checklist

1. **Privacy posture (D020).** Is localhost-only binding sufficient?
   Is the `--allow-non-loopback` escape clause acceptable, or
   excessive? Is htmx vendoring vs CDN sufficiently justified?
2. **D044 / D069 invariants.** Does any web route, button, or
   redirect introduce a path that could auto-flip belief status? Does
   the UI accidentally expose `enable-active-learning` toggles?
3. **CLI/web rendering reuse.** Does the proposed `render.py`
   actually unify the underscore-prefixed CLI helpers, or does it
   leave a duplicated copy that will drift?
4. **Persistent target order.** A (deterministic re-sample) vs B
   (`011_gold_label_session_targets.sql`). Which is right? Does the
   RFC's recommendation have the right reasoning?
5. **Route surface.** Are the v1 routes complete enough? Are the
   v1.1 deferrals (`export`, `history`, `coverage`,
   `enable-active-learning`) defensible or premature?
6. **Template footprint.** Is three templates the right number?
   Are htmx attributes used where appropriate, or over-used?
7. **Process model.** Sync `def` vs `async def` route handlers.
   Single Uvicorn worker vs more.
8. **Error handling.** Trigger errors → banner. 404, 422.
   Server-side rate limiting (none). Are these gaps?
9. **Test surface.** FastAPI `TestClient`, `tests/test_interview_web.py`,
   no live LLM, what coverage is required.
10. **Operator UX.** Keyboard shortcuts (which letters per verdict?),
    rationale auto-hide on `true`/`skip`, save-and-quit equivalence
    with CLI Ctrl-C, "show full message" expansion, evidence-row
    pagination beyond three.
11. **Dependency footprint.** FastAPI, Uvicorn, Jinja2. New `[serve]`
    extra in `pyproject.toml`? Does it pollute headless installs?
12. **Promotion-path coherence.** RFC → spec at
    `docs/specs/0027-interview-web-ui-spec.md`. RFC → `promoted` per
    `docs/process/multi-agent-review-loop.md`. Are the deltas
    concrete enough for the implementation phase?

## Output

Write to the path in your job packet:
`docs/reviews/rfc0027/RFC_0027_INTERVIEW_WEB_UI_REVIEW_<lane>.md`.

Structure:

```md
# RFC 0027 Interview Web UI Review — <lane>

Status: review
Date: <YYYY-MM-DD>
RFC refs: RFC-0027
Decision refs: ...
Phase refs: ...

## Findings

### F001 — <one-line title>
Severity: <blocking | major | minor | nit>
Source: <path>:<line range or section anchor>
Rationale: <one paragraph>

[... more findings ...]

## Open questions

- <questions to resolve before acceptance or implementation>

verdict: <accept | accept_with_findings | needs_revision | reject>
```

Cite findings with file:line references. Aim for 6–12 findings.

Do not modify any file outside the path your packet specifies.
