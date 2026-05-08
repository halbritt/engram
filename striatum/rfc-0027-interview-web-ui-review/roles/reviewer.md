# Reviewer Role — RFC 0027 Interview Web UI

Review RFC 0027 adversarially. Write only the expected review artifact.

Prioritize:

- D020 / privacy: localhost-only binding, vendored htmx vs CDN, no
  outbound network, no auth surface that could leak;
- D044 / D069: gold labels stay advisory; the web surface must not
  introduce a path that auto-flips beliefs;
- reuse-vs-duplication of CLI rendering helpers
  (`_fetch_target_display`, `_fetch_evidence_excerpts`, `_pick_question`,
  `_RATIONALE_PROMPT_BY_VERDICT`) — does the proposed `render.py`
  extraction actually unify them, or does it leave the CLI loop with
  copies?
- persistent target order: A (deterministic re-sample) vs B (new
  table at migration 011);
- v1 route surface vs v1.1 deferrals — is `export` / `history` /
  `coverage` / `enable-active-learning` correctly deferred?
- error handling: trigger errors, 404, 422, banner UX;
- htmx attributes vs full-page reload semantics (Refresh button,
  back-button behavior);
- test surface — `TestClient` smoke, no live LLM, what coverage is
  required.

Cite findings with file path + line range. End with exactly one verdict
on the final line:

```text
verdict: accept
verdict: accept_with_findings
verdict: needs_revision
verdict: reject
```
