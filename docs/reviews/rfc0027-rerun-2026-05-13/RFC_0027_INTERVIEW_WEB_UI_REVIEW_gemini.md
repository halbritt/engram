# RFC 0027 Interview Web UI Review — gemini

Status: review
Date: 2026-05-13
RFC refs: RFC-0027
Decision refs: D016, D020, D044, D069, D074, D079
Phase refs: PHASE-0003-FOLLOWON

## Findings

### F001 — Privacy: Strict Localhost Binding
Severity: nit
Source: docs/rfcs/0027-interview-web-ui.md:183
Rationale: The RFC specifies loopback-only with no `--allow-non-loopback` flag. While this perfectly aligns with D020, operators using remote headless servers (e.g., via SSH port forwarding) may encounter friction if they expect the service to listen on 0.0.0.0. However, since adding an escape clause without token auth is dangerous on a remote box, deferring this to a follow-on RFC is the safest and most defensible posture.

### F002 — Schema: Persistent Target Order is Mandatory
Severity: minor
Source: docs/rfcs/0027-interview-web-ui.md:248
Rationale: The RFC correctly identifies that deterministic re-sampling (Option A) is fundamentally flawed due to the cooldown filter shifting the index map as verdicts are committed. Materializing the sampled order into `gold_label_session_targets` (Option B) is not just a preference; it is mandatory for correctness. The schema migration 011 properly implements this append-only logic.

### F003 — Architecture: Process Model Correctness for Sync DB
Severity: minor
Source: docs/rfcs/0027-interview-web-ui.md:310
Rationale: The decision to use sync `def` route handlers instead of `async def` is critical and correct. Since the underlying `engram.interview` helpers use synchronous `psycopg` connections, an `async def` handler would block the ASGI event loop. By using `def`, FastAPI correctly dispatches the handlers to a threadpool, preventing blocking. The `uvicorn --workers 1` constraint safely manages connection pooling for a single user.

### F004 — UX: Save-and-Quit Discards Rationale
Severity: nit
Source: docs/rfcs/0027-interview-web-ui.md:158
Rationale: The `/sessions/{session_id}/save-and-quit` route discards in-progress rationales. While this matches the CLI's `Ctrl-C` parity, it might frustrate web users who type a long rationale and click "Save and quit" expecting the text to be preserved as a draft. However, since the database schema does not support draft rationales, this is an acceptable v1 limitation.

### F005 — Code Reuse: Unified Render Logic Confirmed
Severity: minor
Source: src/engram/cli.py:53
Rationale: The RFC proposes moving shared rendering logic out of `cli.py` and into `engram.interview.render.py`. Reviewing `cli.py` confirms that this refactoring is successfully architected; functions like `fetch_target_display`, `format_evidence_excerpts`, and `pick_question` are imported cleanly. This mitigates the risk of presentation drift between the CLI and web interfaces.

### F006 — Security: CSRF Mitigation without Tokens
Severity: minor
Source: docs/rfcs/0027-interview-web-ui.md:275
Rationale: V1 defers per-form CSRF tokens in favor of an `Origin` allowlist and `Sec-Fetch-Site: same-origin` headers. For a localhost-bound, single-user application running in modern browsers, these Fetch Metadata Request Headers provide robust CSRF protection without the state overhead of tokens. This is a pragmatic and secure approach for v1.

### F007 — UX / Scope: Deferral of Admin Routes
Severity: minor
Source: docs/rfcs/0027-interview-web-ui.md:167
Rationale: Deferring `export`, `history`, `coverage`, and `enable-active-learning` to the CLI (or a v1.1 web release) is an excellent scope-control decision. The primary goal of the web UI is to increase the throughput of the core labeling loop. Cluttering the V1 UI with administrative actions would dilute the focus and increase the initial implementation risk.

## Open questions

- Are there any edge cases in browser compatibility with `Sec-Fetch-Site` that might require a fallback CSRF mechanism sooner than v1.1?
- Should the "Save and quit" button include a JavaScript confirmation dialog if the rationale textarea is non-empty to prevent accidental data loss?

verdict: accept