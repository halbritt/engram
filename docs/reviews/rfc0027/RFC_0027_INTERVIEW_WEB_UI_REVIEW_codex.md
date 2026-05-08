# RFC 0027 Interview Web UI Review — codex
author: reviewer-codex-gpt-5.5-001

Status: review
Date: 2026-05-08
RFC refs: RFC-0027, RFC-0021, RFC-0022
Decision refs: D016, D020, D044, D052, D069, D078, D079
Phase refs: PHASE-0003-FOLLOWON

Lane focus: FastAPI / Uvicorn implementation feasibility, the exact `render.py`
extraction surface, persistent-target-order option A vs B, the `TestClient`
test surface, and v1 vs v1.1 route deferrals. The Codex lane reads the RFC
against the current Python sources (`src/engram/cli.py`, `src/engram/interview/*`,
`pyproject.toml`, `migrations/010_gold_labels.sql`) and the current test
surface (`tests/test_interview_*`, `tests/conftest.py`).

## Findings

### F001 — `render.py` extraction surface is under-specified for the CLI loop's actual call sites
Severity: major
Source: docs/rfcs/0027-interview-web-ui.md:121-128 vs src/engram/cli.py:1658-1862

The RFC promises four exports — `fetch_target_display`, `fetch_evidence_excerpts`,
`pick_question`, `rationale_prompt_for` — but the live CLI loop also depends on
five additional pieces of shared state that the RFC does not name:
`_VERDICT_PROMPT` (cli.py:1658), `_VERDICT_ALIAS` (cli.py:1659), `_VERDICT_VALID`
(cli.py:1660), `_EVIDENCE_EXCERPT_LIMIT` / `_EVIDENCE_ROWS_SHOWN`
(cli.py:1667-1668), and the `_print_evidence_excerpts` formatter (cli.py:1711-1725).
If only the four named helpers move, the CLI keeps `_print_evidence_excerpts`
and the verdict vocabulary copy, while the web UI re-implements both — exactly
the drift the RFC says it is preventing. The spec needs to (a) move the
`{verdict, alias, valid}` triple into `render.py` (or alongside, in a
`vocabulary.py`) and (b) decide whether the evidence-excerpt formatting is
shared (web HTML rendering of `excerpt['content']` and CLI text rendering will
otherwise diverge on truncation rules). Recommendation: enumerate the full
extraction set in the spec, including the constants, before the implementation
phase begins.

### F002 — `pick_question` has a hidden `now`/timezone dependency the signature elides
Severity: major
Source: src/engram/cli.py:1817-1835; docs/rfcs/0027-interview-web-ui.md:124

`_pick_question` uses `display.get("evidence_max")` to format `ev_date`, which
is the parent `_fetch_target_display`'s `MAX(messages.created_at)` (cli.py:1744-
1745, 1786-1787). That value is timezone-aware out of Postgres, but the CLI
formats `.date().isoformat()` in the server's local timezone implicitly. For a
web route that may be called by an htmx swap from any client, the spec needs
to pin the timezone (UTC-by-default, matching `datetime.now(timezone.utc)` used
elsewhere — sampler.py:205, agent.py:99) so a CLI verdict and a web verdict
that both fire on the same belief produce the same `ev_date` rendering.
Otherwise the same target produces different question text in the two surfaces,
breaking the "no behavior change in the CLI" claim (rfc:128). The fix is one
keyword arg, but it has to be in the function signature.

### F003 — `[serve]` extra is missing from `pyproject.toml` and breaks headless installs without it
Severity: major
Source: pyproject.toml:11-20 vs docs/rfcs/0027-interview-web-ui.md:75-83

The current `pyproject.toml` declares only `psycopg[binary]` as a runtime
dep and one `dev` extra. The RFC says "FastAPI + Uvicorn + Jinja2" but does
not commit to a packaging shape. Without an `[project.optional-dependencies]
serve = ["fastapi>=0.110,<1", "uvicorn>=0.30,<1", "jinja2>=3.1,<4"]` block
(plus `[tool.setuptools.package-data] "engram.interview" = ["templates/*",
"static/*"]`), the implementation will either (a) bloat the headless install
on `pip install -e .` or (b) fail to ship the templates inside the wheel. The
spec must commit to the extra name + the package-data declaration so the
headless `make install` path stays unchanged. Pyright/ruff settings do not
require updates, but pyright's `reportMissingImports = "error"` (pyproject.toml:61)
will fail without `fastapi` installed in the dev venv used by `make typecheck`
(Makefile:294-295) — so either `dev` must depend on `serve`, or pyright must
be told to ignore the optional `engram.interview.web` module when the extra
is absent. Pick one in the spec.

### F004 — Persistent target order: option B is correct; option A is misframed
Severity: major
Source: docs/rfcs/0027-interview-web-ui.md:175-198 vs src/engram/interview/sampler.py:322-369

The RFC frames option A as "with the same `seed`, the sampler is deterministic.
Each request rebuilds the list and indexes into it." Reading `GoldLabelSampler.sample`,
this is true *only when the cooldown filter result is identical across requests*.
But every successful verdict POST writes a new `gold_labels` row, which
`_last_blocking_label_at` (sampler.py:286-302) folds into the cooldown filter
on the next call (sampler.py:331). So between question 4 and question 5 in a
session, target N answered at q3 disappears from the pool, and `order =
self._rng.shuffle([0..len-1])` (sampler.py:341-342) shuffles a *shorter list*
with the same RNG — the index map at q5 does not match the index map at q1.
Option A is therefore not "deterministic re-sample"; it is "re-sample with
order that drifts as you label." Option B (new migration `011_gold_label_session_targets.sql`)
is the only correct option. Recommendation strengthens accordingly: B is not a
performance win, it is a correctness requirement. The RFC text should be revised
to remove "deterministic" from the option A description and to mark the recommendation
as forced rather than chosen.

### F005 — `011_gold_label_session_targets.sql` shape needs FK + idx pinned in the spec
Severity: major
Source: docs/rfcs/0027-interview-web-ui.md:188-198; migrations/010_gold_labels.sql:9-25

Per F004, option B is required. The RFC says "FK to `gold_label_sessions`,
no triggers needed beyond that" (rfc:198). Migration 010's pattern (sql:74-77,
139-159) suggests the concrete shape:

  - `(session_id UUID NOT NULL REFERENCES gold_label_sessions(session_id), idx INT NOT NULL, target_kind TEXT NOT NULL, target_id UUID NOT NULL, candidate_pool_snapshot_id UUID NOT NULL, ... primary key (session_id, idx))`
  - `CHECK (idx >= 0)` matching the route's `q/{idx}` parameter contract.
  - `INDEX (session_id, idx)` — already covered by the PK if PK is composite.
  - The 0-prefix trigger naming convention from migration 010 (sql:230-232) for
    any future BEFORE INSERT validate guards.

The route at `GET /sessions/{session_id}/q/{idx}` (rfc:140) is pinned 1-indexed
in the worked example ("[1/10]", rfc:262) but the schema sketch suggests a
`(session_id, idx)` PK that the operator never sees; pin in the spec whether
the URL is 0- or 1-indexed and whether the table follows. Equally important:
the persistent-targets table needs to carry the typed version triple **at
session-creation time** (extraction or consolidation pair + `request_profile_version`),
because a re-extraction between q1 and q5 (RFC 0017) would otherwise let the
question render against a freshly re-versioned belief that the operator
already labeled at q1 — drifting away from the immutable
`candidate_pool_snapshot_id` discipline (sampler.py:325, agent.py:113).

### F006 — `record_verdict` payload from the route does not have access to `evidence_excerpt`
Severity: major
Source: src/engram/interview/agent.py:77-122 vs docs/rfcs/0027-interview-web-ui.md:140-141

`InterviewAgent.record_verdict` accepts `evidence_excerpt: str | None = None`
(agent.py:84), and that excerpt lands in the dedicated column for redaction at
export time (storage.py:120). The CLI loop never passes one (cli.py:1977),
which is fine for v1 (the column stays NULL), but the RFC's question page
*does* render evidence excerpts (rfc:140, "with 'show full message' hyperlink"),
and the obvious operator expectation is "the excerpt I clicked on is the one
attached to my verdict." The RFC needs to explicitly answer one question:
when a web verdict is recorded, is `evidence_excerpt` (a) left NULL like the
CLI today, (b) populated from the first rendered `excerpt['content']`, or
(c) populated from a `<form>` hidden input that carries the excerpt the
operator was actually looking at? The privacy story changes by option:
options (b)/(c) write privacy-tier-N excerpts to `gold_labels.evidence_excerpt`,
and migration 010's `fn_gold_labels_carry_privacy_tier` (sql:235-272) carries
the parent tier but does not redact the excerpt itself. The RFC § Privacy
Posture section (rfc:200-218) does not name this gap. Spec must close it.

### F007 — `--allow-non-loopback` exit code claim does not match the precedent it cites
Severity: minor
Source: docs/rfcs/0027-interview-web-ui.md:117-119, 201-205 vs docs/rfcs/0022-server-binary-api-mcp.md:179-185

The RFC says non-loopback hosts are refused with exit 8 "mirrors `striatum
serve` D020 posture". RFC 0022 (the server-binary RFC) explicitly does **not**
do this — it says non-loopback "must be explicit via `--bind` and emits a
startup warning" (rfc0022:179-181). The "exit 8" precedent is asserted twice
in RFC 0027 (rfc:87, rfc:205) but no source in the codebase or docs/rfcs
implements it (`grep "exit 8" src/engram` returns no hits). The spec needs to
either (a) cite the actual `striatum serve` repo line that exits 8, or
(b) drop the claim and own the contract directly: the interview web UI
exits with code N on non-loopback bind. Either way, document the exit code
as an explicit project decision rather than a borrowed posture. Because RFC
0022's bind contract is *warn, not refuse*, the interview UI's `refuse`
posture is actually stricter — which is fine, but worth noting as a delta.

### F008 — `TestClient`-only coverage misses the trigger-rejection banner path the RFC promises
Severity: major
Source: docs/rfcs/0027-interview-web-ui.md:220-231, 334-339 vs tests/test_interview_storage.py:155-296

The RFC's error-handling section says trigger rejections (
`fn_gold_labels_append_only`, `fn_gold_labels_validate_target`,
`fn_gold_labels_carry_privacy_tier`) bubble up as `GoldLabelStorageError` and
the route renders an error banner. But the test surface in O7 (rfc:334-339)
proposes "TestClient + a test `conn` fixture" with an *open* question of
whether storage triggers need to fire in web tests. The triggers in
migration 010 (sql:172-276) are the only thing that produce
`GoldLabelStorageError` in production; without them firing, the banner-rendering
codepath is exercised by mocks, not by the actual error shape. Since
`tests/conftest.py:13-83` already provides a `conn` fixture that runs the full
migration suite, the spec should commit to: (a) `TestClient` + the existing
real-DB `conn` fixture for end-to-end route tests at minimum for the verdict
route; (b) plain `TestClient` + monkeypatch for cosmetic / 404 / 422 / index
routes. The "tests/test_interview_web.py" file is not yet enumerated in the
RFC; the spec needs to enumerate at least: index-renders, sessions-create,
question-renders, verdict-success-redirect, verdict-trigger-error-banner (real
DB), 404-on-unknown-session, 404-on-out-of-range-idx, save-and-quit, complete.

### F009 — Sync-vs-async route handler ambiguity will leak into the implementation if not pinned
Severity: minor
Source: docs/rfcs/0027-interview-web-ui.md:332-333 (Open Question 6); src/engram/interview/storage.py:60, 84, 147

Every helper in `engram.interview.{storage,sampler,agent}` is synchronous and
uses `psycopg.Connection` directly (storage.py:60, sampler.py:211). FastAPI's
`def` (sync) handlers run in the threadpool; `async def` handlers must not
call blocking psycopg synchronously. The RFC's open question 6 asks "should
the route signatures be `def` or `async def`" — for a v1 with a sync DB
driver, the only safe answer is `def` (sync) handlers + a single uvicorn
worker. The spec must commit to this in writing, otherwise an implementor
who reaches for `async def` will deadlock the event loop on the first DB
call. Bonus: `uvicorn --workers 1` should be the documented invocation,
because multiple workers around a single sqlite-style local Postgres add
nothing for a single operator and complicate the connection-pool story.

### F010 — v1 route surface omits `coverage` and `history` rendering — defensible but the rationale needs a sentence
Severity: minor
Source: docs/rfcs/0027-interview-web-ui.md:146-148, 290-302 vs src/engram/cli.py:2030-2155

The RFC defers `export`, `history`, `coverage`, and `enable-active-learning`
from v1 web routes (rfc:146-148). For `export` and `enable-active-learning`,
this is correct: `export` carries the privacy ceiling (D020 / D016) and the
project-level `enable-active-learning` decision is explicitly *not* a
per-session UI toggle (RFC 0021 § Open Questions item 4). For `coverage`,
the RFC's deferral rationale ("CLI-only until v1.1", rfc:148) leaves operator
UX (rfc:64-68: "you just labeled 4 mood targets in a row") in the lurch
without giving v1 a path to surface that feedback at all. The spec should
either (a) add a tiny strata-summary widget to `index.html` that calls the
existing `run_phase3_interview_coverage` data path, or (b) commit in writing
to "no in-session coverage feedback in v1; operators see strata only after
they exit and run `engram phase3 interview coverage`." `history` deferral
is defensible (the CLI surface at cli.py:2030-2054 is sparse and operator-
opaque). The RFC text leans toward (b) implicitly, but it should be loud.

### F011 — htmx vendoring path collides with `[tool.setuptools.packages.find]`
Severity: minor
Source: docs/rfcs/0027-interview-web-ui.md:215-218, 308-313 vs pyproject.toml:25-26

The RFC proposes `src/engram/interview/static/htmx.min.js` and templates at
`src/engram/interview/templates/`. The current packaging declaration
(pyproject.toml:25-26) is `[tool.setuptools.packages.find] where = ["src"]`,
which discovers Python packages but **does not** ship non-Python files
inside them by default. Without a `[tool.setuptools.package-data]` block
listing `engram.interview = ["templates/*.html", "static/*.js"]`, a
`pip install` of the wheel will not include the templates or htmx.min.js,
and `engram phase3 interview serve` will 500 on the first GET. The spec
must enumerate the package-data declaration alongside the `[serve]` extra
(see F003). This is not a blocker for editable installs (`pip install -e
.` resolves to source paths) but is a hard blocker for any wheel-built
operator install.

### F012 — Route surface uses `POST /sessions/{id}/complete` and `save-and-quit` redundantly
Severity: nit
Source: docs/rfcs/0027-interview-web-ui.md:140-145 vs src/engram/cli.py:1995-1996, 1968-1973

`POST /sessions/{session_id}/complete` calls `mark_session_completed`
(rfc:144); `POST /sessions/{session_id}/save-and-quit` is a no-op redirect
to `/` (rfc:143). The CLI loop has only one path: it calls
`mark_session_completed` only after the operator answers all `n` targets
(cli.py:1995-1996); Ctrl-C and `q` produce a no-op early return that leaves
the session open (cli.py:1968-1973). The web route shape preserves both
semantics, which is fine, but the RFC does not name "what fires `complete`":
is it the auto-redirect after the final verdict (option A — implicit), or
a button on the question page after the last verdict (option B — explicit)?
Worked example (rfc:286-287) implies A. Pin it in the spec.

## Open questions

- O1 — `render.py` constants (verdict vocabulary, evidence limits): does the
  spec move them, alongside the four named helpers? See F001.
- O2 — Is `evidence_excerpt` populated on web verdicts? (Empty / first / hidden-
  input / clicked-excerpt.) See F006.
- O3 — Does `[serve]` get folded into `dev` so `make typecheck` keeps passing,
  or do we add a pyright exclusion for `engram.interview.web` when the extra
  is absent? See F003.
- O4 — Is `coverage` surfaced inline as a small strata summary on the index
  page, or fully deferred? See F010.
- O5 — Does the persistent-targets table carry the version triple at
  session-creation time so re-extraction between q1 and qN does not drift the
  rendered question? See F005.
- O6 — Exit code on non-loopback bind: pin a concrete number, do not borrow
  from a precedent that does not exist in the codebase. See F007.

verdict: needs_revision
