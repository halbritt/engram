# RFC 0027 Interview Web UI Review — codex

author: operator [self-declared: rfc0027-review-codex]
Status: review
Date: 2026-05-13
RFC refs: RFC-0027, RFC-0021, RFC-0022
Decision refs: D016, D020, D044, D069, D074, D079, D080, D081
Phase refs: PHASE-0003-FOLLOWON

## Findings

### F001 — Question page can render Tier 2+ evidence before guarded routes
Severity: blocking
Source: docs/rfcs/0027-interview-web-ui.md:303-310; src/engram/interview/sampler.py:217-229; src/engram/interview/web.py:515-527; src/engram/interview/templates/_evidence_excerpt.html:1-18
Rationale: RFC 0027 hard-codes the Tier 1 ceiling on full-message, context, and evidence-all routes, but the main question page also renders evidence excerpts. The sampler reads claims and beliefs without a Tier 1 filter, `_render_question_template` only checks message tiers when `full_evidence=True`, and `_evidence_excerpt.html` emits `excerpt.content` directly. A Tier 2 target can therefore leak a truncated raw message on `/sessions/{id}/q/{idx}` before the operator clicks any route that has the intended ceiling.

### F002 — Final-question completion requires a mutating GET
Severity: blocking
Source: docs/rfcs/0027-interview-web-ui.md:183-188; src/engram/interview/web.py:847-855; src/engram/interview/web.py:1069-1081; tests/test_interview_web.py:562-592
Rationale: The RFC says the final verdict handler emits `HX-Redirect` to `/sessions/{id}/complete`, while `/complete` is defined as a POST route. The implementation resolves that mismatch by adding `GET /sessions/{id}/complete`, which mutates `gold_label_sessions.completed_at` without Origin enforcement. This violates the stated mutating-route posture and should be fixed by making finalization happen inside the verdict POST transaction or by redirecting to a non-mutating completed page after a guarded POST.

### F003 — Origin enforcement is weaker than the stated CSRF contract
Severity: major
Source: docs/rfcs/0027-interview-web-ui.md:291-302; docs/specs/0027-interview-web-ui-spec.md:480-492; src/engram/interview/web.py:181-216; tests/test_interview_web.py:512-523
Rationale: The RFC requires an Origin allowlist plus `Sec-Fetch-Site: same-origin` on every mutating route, and the spec describes exact loopback origins for the bound port. The implementation accepts requests with no `Origin`, treats `Sec-Fetch-Site` as optional, and allows any port for allowlisted hosts. That may be an intentional curl/TestClient concession, but then the spec needs to say so and tests need to pin the actual threat model; otherwise the per-form CSRF-token deferral is resting on a stricter contract than the code enforces.

### F004 — Message reachability is conversation-wide instead of evidence-scoped
Severity: major
Source: docs/rfcs/0027-interview-web-ui.md:184-186; src/engram/interview/web.py:586-634; src/engram/interview/web.py:940-998; tests/test_interview_web.py:680-688
Rationale: RFC 0027 frames `/messages/{message_id}` as the full body for one evidence row and `/messages/{message_id}/context` as cited-message context. The implementation only checks whether the session can reach the message's conversation, not whether the requested message is one of the target's cited evidence ids or the bounded neighbor window around such an id. Anyone with another message UUID from the same conversation can expand the read surface beyond the sampled target.

### F005 — D020 no-egress is not carried into the serve process contract
Severity: major
Source: HUMAN_REQUIREMENTS.md:153-160; DECISION_LOG.md:42; docs/rfcs/0027-interview-web-ui.md:311-313; src/engram/cli.py:2313-2318
Rationale: D020 requires the corpus-reading process to have no network egress, ideally enforced outside code discipline. RFC 0027's no-outbound-network section is limited to vendored htmx and no CDN, and the serve driver starts Uvicorn normally. Vendoring static assets is necessary, but it is not equivalent to an egress-denied runtime. The accepted contract should either require the same OS-level no-egress wrapper as other corpus-reading processes or explicitly record why this local web surface is exempt.

### F006 — Web resume does not match the frozen target version triple
Severity: major
Source: docs/rfcs/0027-interview-web-ui.md:266-272; src/engram/interview/web.py:737-746; src/engram/interview/storage.py:478-510
Rationale: The materialized-order design is correct because cooldown changes make deterministic re-sampling unsafe, but the web resume query only joins `gold_labels` on `session_id` and `target_id`. The storage helper correctly treats a target as answered only when `target_kind` and the full version triple also match. A label under a different extraction or consolidation version can make the web route skip a still-unanswered frozen target, breaking the core reason migration 011 exists.

### F007 — Version triples are shape-checked but not parent-checked
Severity: major
Source: docs/rfcs/0021-gold-set-interview-curation.md:149-152; migrations/010_gold_labels.sql:112-127; migrations/010_gold_labels.sql:184-210; migrations/011_gold_label_session_targets.sql:27-39
Rationale: Migration 010 validates that claim-shaped rows have extraction columns and belief-shaped rows have consolidation columns, and it validates target existence. It does not validate that the supplied version columns match the parent claim or belief audit/current row. Migration 011 repeats the same shape-only check for materialized targets. Because both tables are append-only, a bad version stamp is hard to repair and can silently poison equality joins against labels or session targets.

### F008 — Migration 011 is stale relative to the current sampled-target shape
Severity: major
Source: docs/rfcs/0027-interview-web-ui.md:259-280; migrations/011_gold_label_session_targets.sql:6-40; src/engram/interview/storage.py:47-67; src/engram/interview/storage.py:338-403; migrations/013_interview_active_learning_state.sql:27-52
Rationale: RFC 0027 says migration 011 is the v1 table, but the current storage layer needs `active_learning_signal_version`, `confidence`, and `observed_at` to reconstruct `SampledTarget` without substituting defaults. Migration 013 later adds those fields and backfills them, which confirms the original 011 contract was incomplete. The spec should either fold those columns into the migration-011 contract or explicitly state that 013 is part of the required RFC 0027 schema baseline.

### F009 — Pre-011 open sessions can be marked complete without targets
Severity: major
Source: docs/rfcs/0021-gold-set-interview-curation.md:138-140; docs/rfcs/0027-interview-web-ui.md:278-280; migrations/011_gold_label_session_targets.sql:6-40; src/engram/cli.py:2066-2085
Rationale: RFC 0027 updates the CLI to write materialized session targets going forward, but it does not say what happens to sessions created before migration 011. The migration creates an empty table with no backfill, and current CLI resume treats an open session with no unanswered materialized targets as complete. If any RFC 0021 sessions exist in an operator database, applying RFC 0027 can silently strand or close them instead of resuming.

### F010 — The serve extra in the RFC omits the form parser dependency
Severity: minor
Source: docs/rfcs/0027-interview-web-ui.md:351-371; src/engram/interview/web.py:676-683; src/engram/interview/web.py:786-794; pyproject.toml:22-27
Rationale: The RFC dependency snippet lists FastAPI, Uvicorn, and Jinja2, but the route handlers use `Form(...)`, which requires `python-multipart` at app import/runtime. `pyproject.toml` includes the dependency, so the scaffold is healthier than the RFC text; the promoted contract should be updated so a fresh implementation from the RFC/spec does not fail on form parsing.

### F011 — Error handling tests bless JSON where the RFC promises inline banners
Severity: minor
Source: docs/rfcs/0027-interview-web-ui.md:326-340; src/engram/interview/web.py:796-821; src/engram/interview/web.py:1096-1104; tests/test_interview_web.py:386-401; tests/test_interview_web.py:479-490
Rationale: RFC 0027 says 422 paths surface as a banner, but the implementation's global `HTTPException` handler returns JSON for unknown verdict and blank rationale, and tests assert that JSON. This is not a privacy violation, but it is a UX/test-contract drift: htmx will swap JSON into the page unless the client handles it specially.

### F012 — The D044/D069 import-graph guard is too shallow
Severity: minor
Source: docs/rfcs/0027-interview-web-ui.md:315-324; tests/test_interview_web.py:29-31; tests/test_interview_web.py:828-843
Rationale: The invariant is right: the web route layer must not reach `engram.consolidator.transitions`. The current test only inspects symbols directly present on `engram.interview.web`, while the test module itself imports transition helpers for fixtures. That does not prove the web module graph is unreachable from transitions; use an AST/import graph check scoped to production modules, or keep fixture-only transition imports outside the guard's module set.

## Open questions

- Should RFC 0027 be treated as historical only now that Spec 0027 and D080 exist? If so, future reruns should target the spec plus scaffold directly and only cite the RFC for provenance.
- Is D081's tailnet bridge now part of the accepted v1 surface, or should the RFC/spec still say "no remote access" without qualification? The current how-to documents remote browser access through a loopback bridge.
- I did not find a reason to pull export, history, coverage dashboard, active-learning toggle, `--include-superseded`, or `--ignore-cooldown` into web v1. The CLI-only deferral is defensible once the route and privacy issues above are fixed.
- The persistent target-order table is the right choice over deterministic re-sampling; the remaining issue is making the schema and resume queries preserve the exact frozen target identity.

verdict: needs_revision
