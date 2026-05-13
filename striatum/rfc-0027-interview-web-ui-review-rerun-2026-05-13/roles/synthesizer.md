# Synthesizer Role — RFC 0027 Interview Web UI

Synthesize the RFC 0027 findings ledger into a recommendation: accept-rfc,
revise-rfc, split-rfc, or reject-rfc.

If the recommendation is **accept-rfc**, the synthesis must produce
concrete spec deltas suitable for an implementation handoff:

- final route table (verb + path + purpose), with htmx swap targets
  noted where relevant;
- final template list (path, purpose, htmx attributes);
- exact `render.py` API surface (function signatures, what stays in
  cli.py, what moves out);
- migration call (none, or `011_gold_label_session_targets.sql`);
- dependency additions to `pyproject.toml` (FastAPI, Uvicorn, Jinja2)
  with whether they live under a `[serve]` extra;
- test surface (file paths, what each test exercises);
- privacy-tier env-var resolution (default value, name);
- keyboard shortcut letters per verdict;
- BUILD_PHASES insert text and DECISION_LOG entry text for acceptance.

Write only the expected synthesis artifact.
