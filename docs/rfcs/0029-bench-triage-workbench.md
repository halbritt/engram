<a id="rfc-0029"></a>
# RFC 0029: Bench Triage Workbench

| Field | Value |
|-------|-------|
| RFC | 0029 |
| Title | Bench Triage Workbench |
| Status | proposal |
| Implementation | none |
| Date | 2026-05-13 |
| Context | RFC 0017 (extraction prompt versioning and re-extraction); RFC 0019 (extraction benchmark harness); RFC 0024 (benchmark gates and artifact redaction); RFC 0027 / Spec 0027 (local FastAPI/Jinja2/htmx web posture); RFC 0028 (predicate-intent re-extraction candidate); `docs/reviews/rfc0028-predicate-intent-implementation/REEXTRACTION_BENCH_100.md`; D020 / D074 |

Decision refs:
  - D020
  - D074

Phase refs:
  - PHASE-0003-FOLLOWON
  - PHASE-0004

This RFC proposes a **local-only benchmark triage workbench** for reviewing
extraction and re-extraction benchmark deltas at human reading speed. It is a
fresh 2026-05-13 proposal; prior RFC 0029 text is treated only as draft input,
not as accepted implementation evidence.

The immediate pressure comes from the RFC 0028 100-segment re-extraction
benchmark. The run completed with zero segment failures, 100% schema-valid
outputs, and 100% provenance-clean outputs, but it also reduced same-slice
claim count from 600 prior claims to 475 candidate claims and produced 11
prior-positive / candidate-zero segments. Those aggregate signals are useful,
but they do not answer the human question: "are the changed or zeroed segments
actually acceptable, or did the new prompt lose useful memories?"

The workbench is not a new source of truth. It is a private, loopback-only
review UI over scratch benchmark artifacts. It records human triage decisions
to scratch-local review state, exports redacted summaries on explicit command,
and never writes review labels into production claim, belief, audit, or raw
evidence tables in v1.

V1 scope is **Phase 3 extraction/re-extraction validation**. PHASE-0004 is
listed because RFC 0024's benchmark-gate and artifact-redaction rules shape
the design and because a future spec may adapt the same workbench pattern to
Phase 4 artifacts. This RFC does not add a Phase 4 command alias or a Phase 4
entity-review surface in v1.

## Problem

Phase 3 progress now depends on repeated "is this extraction change
semantically acceptable?" decisions; later Phase 4 gate work will need the
same artifact-redaction discipline. The existing artifacts answer different
questions:

- benchmark JSON answers whether a run completed, produced valid schema, and
  preserved provenance;
- aggregate Markdown answers whether counts, drops, and throughput moved in
  the expected direction;
- scratch review artifacts can list suspicious segments, but they force the
  reviewer to hold prior behavior, candidate behavior, source context, and the
  accept/reject decision in working memory.

That is the wrong ergonomics for re-extraction validation. The operator should
be able to sit down, review a queue of suspicious segments one at a time, make
a clear decision, stop without losing progress, resume later, and export a
redacted summary without copying private text into tracked docs.

The current Markdown workflow also creates avoidable privacy ambiguity.
Private scratch files may contain segment text, prior claim text, model
outputs, or local source excerpts. Tracked `docs/reviews/` exports are always
redacted in v1. If raw/private export is ever allowed, it must be a separate
ignored local artifact outside tracked docs. A dedicated tool can make that
boundary mechanical instead of procedural.

## Goals

1. Let the operator triage extraction benchmark and re-extraction deltas with
   one segment on screen at a time.
2. Preserve Engram's local-first constraint: loopback-only, no hosted service,
   no telemetry, no CDN, no external persistence, and no network dependency.
3. Keep production data immutable from this surface. Benchmark triage writes
   only private scratch review decisions in v1.
4. Make suspicious-segment queues obvious: zeroed segments, new nonzero
   segments, claim-count changes, predicate-mix changes, high drop counts,
   provenance anomalies, malformed candidate records, and ambiguous prior
   matches.
5. Provide a concise promotion-readiness signal: which segments are accepted,
   which are regressions, which need follow-up, which are excluded from the
   current review, and whether the run is ready for an explicit owner promotion
   decision.
6. Export a redacted tracked summary suitable for `docs/reviews/` without
   leaking raw private corpus text by default.

## Non-Goals

- This RFC does not add a hosted dashboard, multi-user service, login flow,
  TLS configuration, CDN asset, JS framework, or browser build pipeline.
- This RFC does not mutate `claims`, `claim_extractions`, `beliefs`,
  `belief_audit`, `claim_audits`, `projection_audits`, `messages`,
  `segments`, or raw evidence tables.
- This RFC does not decide whether RFC 0028 should be promoted to full-corpus
  re-extraction. It provides the local review surface for making that decision
  with less cognitive overhead.
- This RFC does not replace the command-line benchmark harness. The harness
  remains the source of benchmark artifacts.
- This RFC does not create gold labels for claim correctness. It records
  benchmark-review decisions about candidate runs.
- This RFC does not define a Phase 4 entity-review UI. The first surface is
  extraction/re-extraction validation; Phase 4 may reuse the pattern later.

## Proposal

### Shape

Add a local web surface under a new package, tentatively
`src/engram/bench_review/`, with a phase-scoped CLI entry point:

```text
engram phase3 bench-review serve \
  --slice .scratch/benchmarks/extraction-backend/slices/<slice>.json \
  --run .scratch/benchmarks/extraction-backend/<run>/run.json \
  --segments .scratch/benchmarks/extraction-backend/<run>/segments.jsonl \
  --prior-prompt-version extractor.v8.d064.accounted-zero \
  --prior-model-version <model-version> \
  --prior-request-profile-version <request-profile-version> \
  --host 127.0.0.1 \
  --port 8770
```

The server follows the RFC 0027 delivery posture: FastAPI, server-rendered
Jinja2 templates, vendored htmx, no build step, and loopback-only binding.
Non-loopback hosts are refused at startup with exit 8 and there is no
`--allow-non-loopback` flag in v1. Static assets are package-local and served
by the app; no network asset fetch is allowed.

The workbench reads:

- an extraction benchmark slice manifest;
- a candidate benchmark run artifact;
- candidate segment records, either from `--segments` or by resolving
  `segment_records_path` from `run.json`;
- the local Postgres database for prior extraction rows and source metadata;
- a full prior extraction identity
  (`extraction_prompt_version`, `extraction_model_version`,
  `request_profile_version`) or an explicit prior-run artifact for direct
  run-to-run comparison;
- optional private-detail candidate artifacts when the operator explicitly
  wants local claim text in the UI.

Normal triage mode requires candidate segment records. If segment records are
missing, malformed, or do not match the slice, the app starts only in
metadata-only status mode: aggregate run metadata and artifact diagnostics are
visible, but segment verdict controls are disabled.

The workbench writes:

- a private review SQLite database, defaulting to
  `.scratch/benchmarks/extraction-review/<run-id>/review.sqlite3`;
- optional JSONL snapshots in the same scratch directory for recovery and diff
  review;
- a redacted tracked summary only when the operator explicitly runs the export
  command.

All production Postgres access is read-only. V1 should enforce this
mechanically by connecting with a read-only role when available and by starting
read-only transactions (`SET TRANSACTION READ ONLY`) for every route/loader
that touches production tables. If either guard cannot be applied, the server
should fail closed rather than silently downgrading to application-level
discipline.

### Review State

Review state is intentionally outside production Postgres in v1. A small
SQLite database is enough and keeps the boundary clear.

Recommended tables:

```sql
CREATE TABLE review_sessions (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  bench_run_id TEXT NOT NULL,
  run_path TEXT NOT NULL,
  segment_records_path TEXT,
  slice_path TEXT NOT NULL,
  prior_prompt_version TEXT,
  prior_model_version TEXT,
  prior_request_profile_version TEXT,
  reviewer TEXT NOT NULL,
  active_queue TEXT NOT NULL DEFAULT 'needs_review',
  queue_fingerprint TEXT NOT NULL,
  current_segment_id TEXT,
  metadata_only INTEGER NOT NULL DEFAULT 0,
  artifact_diagnostics_json TEXT NOT NULL DEFAULT '{}',
  run_decision TEXT CHECK (
    run_decision IN ('undecided', 'promote', 'do_not_promote')
  ) DEFAULT 'undecided',
  run_decision_note TEXT NOT NULL DEFAULT '',
  run_decided_at TEXT
);

CREATE TABLE segment_queue (
  session_id TEXT NOT NULL REFERENCES review_sessions(id),
  segment_id TEXT NOT NULL,
  review_order INTEGER NOT NULL,
  data_availability TEXT NOT NULL,
  risk_tags_json TEXT NOT NULL DEFAULT '[]',
  required_review INTEGER NOT NULL DEFAULT 0,
  hard_blocker INTEGER NOT NULL DEFAULT 0,
  blocker_reason TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (session_id, segment_id)
);

CREATE TABLE segment_reviews (
  session_id TEXT NOT NULL REFERENCES review_sessions(id),
  segment_id TEXT NOT NULL,
  prior_prompt_version TEXT,
  prior_model_version TEXT,
  prior_request_profile_version TEXT,
  candidate_run_id TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (
    decision IN (
      'accept_candidate_change',
      'flag_candidate_regression',
      'needs_followup',
      'exclude_from_review'
    )
  ),
  confidence TEXT NOT NULL CHECK (
    confidence IN ('low', 'medium', 'high')
  ),
  note TEXT NOT NULL DEFAULT '',
  decided_at TEXT NOT NULL,
  PRIMARY KEY (session_id, segment_id)
);
```

`segment_id` is text because Engram segment IDs are UUIDs. `segment_queue`
materializes every loaded segment, including undecided rows; `segment_reviews`
contains only decided rows. Status/readiness is computed by left-joining queue
rows to review rows, so undecided state does not require sentinel decisions.
`segment_records_path` is nullable for metadata-only mode, and
`artifact_diagnostics_json` records why segment controls are disabled.

The schema deliberately omits segment text, claim text, prompts, completions,
and private values. The UI may read private corpus text from Postgres and
scratch artifacts for local display, but review state stores only identifiers,
derived queue tags, decisions, confidence, timestamps, and notes. Notes are
private scratch content by default and are not included in tracked exports in
v1.

Benchmark review decisions never feed production derivations. Extraction,
consolidation, gold-label interview, entity review, and serving paths do not
consume this scratch state.

Scratch run decisions are review evidence only. They do not update Striatum
state, do not satisfy a Striatum blocker, and do not make an operational gate
decision authoritative under D074. If a benchmark decision is promoted, the
owner or coordinator records that promotion through the normal Striatum/docs
gate artifact for the relevant workflow; the scratch SQLite row is cited as
supporting evidence, not treated as the gate.

### Data Availability

Every segment gets a typed data-availability state before classification:

- `complete`: prior and candidate structured comparison data are available;
- `candidate_zero`: the candidate record proves the run emitted zero claims;
- `candidate_redacted`: structured candidate counts, predicates, object-kind
  presence, confidence, stability class, and evidence IDs exist, but
  subject/object text is intentionally absent under the benchmark redaction
  policy;
- `candidate_missing`: the candidate segment record is absent;
- `candidate_malformed`: the candidate record exists but failed validation;
- `prior_missing`: no prior extraction rows match the requested prior
  extraction identity;
- `prior_ambiguous`: multiple prior extraction identities match and the
  operator did not provide enough version fields to disambiguate them.

The UI must never collapse `candidate_zero`, `candidate_redacted`,
`candidate_missing`, `candidate_malformed`, `prior_missing`, and
`prior_ambiguous` into the same visual state.

Semantic acceptance controls are enabled only when the workbench has enough
structured data to prove the delta being accepted. Missing, malformed, or
ambiguous data can be parked as `needs_followup` or excluded from the current
review, but it cannot make the run promotion-ready. `candidate_zero` is
reviewable when the prior identity is unambiguous and the UI can show enough
local source context for the operator to decide whether zero claims are
acceptable.

### Classification Model

The loader builds a deterministic queue record per segment:

- `zeroed`: prior extraction had at least one claim and the candidate emitted
  zero claims;
- `newly_nonzero`: prior extraction had zero claims and the candidate emitted
  at least one claim;
- `count_changed`: prior and candidate claim counts differ;
- `high_drop_count`: the candidate dropped claims above a configurable
  threshold;
- `predicate_mix_changed`: the candidate predicate set differs from the prior
  predicate set;
- `provenance_anomaly`: candidate provenance cleanliness is below the run's
  expected threshold;
- `schema_or_parse_anomaly`: candidate validation produced malformed or
  schema-invalid structured output;
- `unchanged`: no review-triggering delta.

Queue tabs are a view over those tags:

- Needs review;
- Zeroed;
- Newly nonzero;
- Count changed;
- Predicate mix changed;
- High drops;
- Provenance;
- Schema / parse;
- All.

Zeroed segments, newly nonzero segments, missing-data states, malformed-data
states, count changes, predicate-mix changes, provenance anomalies, and
high-drop segments are always manual-review items. V1 does not provide
acceptance-like batch decisions. If batching ships at all, it is limited to
"exclude unchanged items from this review" and only for records with complete
data, no risk tags, no count delta, no predicate delta, no provenance warning,
and no prior review conflict. Batch actions require a preview listing included
segment IDs and excluded IDs by reason.

## Screen Design

The primary screen is one segment at a time. It starts with a plain-language
change-summary block that answers:

- what changed;
- whether data is complete, redacted, missing, malformed, or ambiguous;
- the highest risk reason;
- what action is required next.

The rest of the page shows:

- a progress header: current queue, reviewed count, remaining count,
  unresolved blocker count, and promotion-readiness state;
- a risk-chip row: zeroed/newly-nonzero, count delta, predicate delta, drop
  count, provenance status, schema/parse status, and prompt/request profile;
- source metadata and stable segment identifiers;
- a compact evidence/segment excerpt panel, with explicit "show more"
  controls and a visible privacy note that the text is local-only and not
  exported by default;
- prior claims as structured rows: subject present/redacted, predicate,
  object present/redacted, confidence, stability class, and evidence count
  when known;
- candidate rows in one of two display modes:
  - redacted mode: count, predicate, object kind/presence, confidence,
    stability class, evidence IDs, and drop/provenance metadata;
  - private-detail mode: local-only subject/object/rationale text when the
    operator explicitly supplies a scratch claim-text artifact;
- dropped-claim reasons from benchmark output where available;
- four large verdict controls with visible consequence labels:
  - Accept candidate change: count this delta as reviewed and acceptable;
  - Flag candidate regression: block promotion readiness until resolved;
  - Park for follow-up: keep the item unresolved;
  - Exclude from this review: mark intentionally out of scope for this run.

`exclude_from_review` counts as an operator action but does not make a risky,
missing, malformed, or ambiguous item disappear from promotion-readiness
accounting. The summary shows excluded items separately from accepted items.

Promotion readiness is derived and deliberately weaker than promotion:

- `blocked`: at least one blocking risk remains, required data is missing or
  malformed, or a regression has been flagged;
- `review_incomplete`: reviewable items remain undecided;
- `ready_for_owner_decision`: all configured review obligations are complete;
- `promoted_by_recorded_decision`: the operator recorded a scratch-local
  promotion recommendation;
- `not_promoted_by_recorded_decision`: the operator recorded a scratch-local
  rejection recommendation.

Readiness is computed from a deterministic matrix:

| Availability / decision | Clears review obligation? | Clears promotion blocker? |
|-------------------------|---------------------------|----------------------------|
| `complete` + `accept_candidate_change` | yes | yes, unless a hard tag remains |
| `candidate_zero` + `accept_candidate_change` | yes | yes, when prior identity is unambiguous and local source context was available |
| `candidate_redacted` + `accept_candidate_change` | limited | only for aggregate/count-only deltas; semantic predicate/object changes remain blocked until private-detail or source context is available |
| any state + `flag_candidate_regression` | yes | no; blocks readiness |
| any state + `needs_followup` | yes | no; blocks readiness |
| risky, missing, malformed, or ambiguous state + `exclude_from_review` | yes | no; remains an excluded blocker |
| `unchanged` + `exclude_from_review` | yes | yes |
| `candidate_missing`, `candidate_malformed`, `prior_missing`, `prior_ambiguous` | no | no; hard blocker until fixed by a new artifact or disambiguated prior identity |
| `schema_or_parse_anomaly` or `provenance_anomaly` | no | no; hard blocker until fixed by a new artifact |

`ready_for_owner_decision` is true only when there are zero hard blockers, zero
flagged regressions, zero `needs_followup` rows, zero undecided review
obligations, and every remaining non-hard required-review row has either
`accept_candidate_change` or an allowed `exclude_from_review` decision.

The UI must support keyboard review without requiring it:

- `a`: accept candidate change;
- `r`: regression;
- `u`: park unresolved / needs follow-up;
- `x`: exclude from this review;
- `j`: next item;
- `k`: previous item;
- `/`: focus filter/search;
- `?`: shortcut overlay.

Decision shortcuts are disabled while an input, textarea, select, or
contenteditable element has focus. A saved decision must render a visible
confirmation and remain visible when the segment is reloaded.

The decision panel includes the four decision buttons, a confidence control
(`low` / `medium` / `high`, default `medium`), and an optional note textarea.
Notes remain scratch-local and are excluded from tracked exports. Segment
decisions are idempotent upserts on `(session_id, segment_id)`: resubmitting a
decision updates decision, confidence, note, and `decided_at` for that segment
inside the active review session.

Keyboard details should be frozen in the follow-on spec, but v1 semantics are:
decision keys submit the currently selected confidence and note; `j` / `k`
move within the current filtered queue and stop at boundaries with a visible
status message; `/` focuses the queue filter/search input; `?` opens a shortcut
modal; `Esc` closes the modal and restores focus to the last active control.

## Routes

V1 route contract:

| Verb | Path | Purpose |
|------|------|---------|
| GET | `/` | Review session landing page: run metadata, queue counts, last decision, resume link. |
| GET | `/segments` | Queue list with filters. Defaults to Needs review. |
| GET | `/segments/{segment_id}` | Full segment review page. |
| POST | `/segments/{segment_id}/decision` | Record or update the segment decision in scratch review state. |
| GET | `/segments/{segment_id}/excerpt` | Expand local segment/evidence excerpt. Tier ceiling enforced at route layer. |
| GET | `/summary` | Private local summary: counts by decision and risk tag. |
| POST | `/run-decision` | Record a scratch-local run-level decision after the run is ready for owner decision. |

One `serve` process owns exactly one active review session. The route paths do
not include `session_id` because the session is selected or created at startup
from `--review-db`, `--run`, `--slice`, and `--segments`. The SQLite schema
keeps `session_id` so future multi-session or cross-run review is possible, but
v1 routes always resolve the single active session from process state.

`GET /segments` accepts `queue=<needs_review|zeroed|newly_nonzero|
count_changed|predicate_mix_changed|high_drops|provenance|schema_parse|all>`
and optional `q=<text>` filter parameters. Ordering is deterministic:
hard blockers first, then risk-rank order, then slice order / segment ID. V1
does not paginate; if a future benchmark slice makes this too heavy, pagination
must preserve deterministic `j` / `k` next/previous behavior within the active
filter. Empty tabs render an explicit "no items in this queue" state.

`GET /segments/{segment_id}` and `/segments/{segment_id}/excerpt` return 404
unless `segment_id` belongs to the loaded slice for the active session. Segment
IDs outside the loaded benchmark cannot be rendered by guessing URLs.

`POST /segments/{segment_id}/decision` accepts form fields
`decision`, `confidence`, and optional `note`; invalid values return 422, an
unknown or out-of-slice segment returns 404, and a successful htmx request
returns either the updated decision panel or `HX-Redirect` to the next segment
in the current filtered queue. `POST /run-decision` accepts
`decision=promote|do_not_promote` plus optional `note`; it returns 409 unless
readiness is exactly `ready_for_owner_decision`.

Mutating routes (`POST /segments/{segment_id}/decision` and
`POST /run-decision`) use RFC 0027's browser-tab defense: an Origin allowlist
over the current `http://127.0.0.1:<port>` and
`http://localhost:<port>`, plus `Sec-Fetch-Site: same-origin` enforcement when
the header is present. Mismatch returns 403 and has no side effects.

Every route that can render text from private source data enforces a hard-coded
Tier 1 ceiling in v1. Higher-tier rendering is reserved for a follow-on RFC;
there is no v1 CLI flag, environment variable, or existing-scratch-artifact
bypass.

For multi-message excerpts, the tier ceiling is max-carry: if any message in
the excerpt window is Tier 2+, the whole excerpt response is 403. Candidate
private-detail artifacts do not bypass the Tier 1 route ceiling.

## CLI Commands

Add:

```text
engram phase3 bench-review serve
engram phase3 bench-review status --review-db PATH
engram phase3 bench-review export --review-db PATH --output docs/reviews/<file>.md
```

`serve` starts the workbench. Required inputs are `--run` plus either
`--segments` or a resolvable segment-records path inside the run artifact.
`--slice` is required unless the run artifact contains a verified slice
reference. Prior comparison requires either all three prior identity fields
(`--prior-prompt-version`, `--prior-model-version`,
`--prior-request-profile-version`) or an explicit prior benchmark run artifact.
Ambiguous prior identity is a startup error unless `--metadata-only` is passed.

`status` prints counts from the scratch review database without starting a
server: run ID, queue fingerprint, reviewed count, blocker count, decisions by
verdict, and promotion-readiness state.

`export` writes a redacted Markdown summary to a caller-supplied tracked path
under `docs/reviews/`. V1 has no `--allow-outside-reviews` flag and no web
export route. The export command resolves the output path before writing and
refuses absolute paths outside the repository, `..` traversal, symlink escape,
home-directory paths, and overwriting an existing file unless an explicit
`--overwrite` flag is provided.

## Redacted Export Contract

The export contains:

- run ID, benchmark timestamp, prompt versions, model versions, and request
  profile versions;
- sanitized artifact slugs or artifact IDs for the slice and candidate segment
  record; raw path basenames are not exported because operator-chosen filenames
  can contain private names;
- prior extraction identity;
- aggregate reviewed/unreviewed counts;
- counts by data-availability state, risk tag, and decision;
- segment IDs grouped by decision and blocker reason;
- run-level promotion decision, if recorded;
- reproduction commands with private paths replaced by sanitized placeholders
  or artifact IDs.

The export does not contain:

- notes;
- segment text;
- message text;
- claim subject/object/rationale text;
- note text;
- prompts or completions;
- private values;
- home-directory absolute paths;
- local model filesystem paths;
- non-redacted scratch JSON/JSONL payloads.

The UI may display private text because it is a local operator tool. That does
not make private text eligible for tracked docs.

## Relationship To RFC 0027

RFC 0027 already established the preferred local web pattern for Engram:
FastAPI, Jinja2, htmx, loopback-only bind, no JS build pipeline, route-level
privacy checks, vendored static assets, and Origin checks on mutating routes.
RFC 0029 should reuse that pattern rather than introduce a parallel frontend
stack.

The bench-review package should not import interview-specific gold-label
storage code, interview route handlers, or consolidation transition code. Shared
web helpers may move to a small common module only for narrowly repeated web
substrate:

- loopback host validation;
- Origin allowlist and `Sec-Fetch-Site` check;
- vendored htmx static serving;
- package-local template/static setup;
- Tier 1 render ceiling helpers.

If extracted, the likely home is `src/engram/web/`. The extraction must be
small, directly tested, and must not import interview or bench-review domain
logic.

## Privacy And Security

The workbench inherits Engram's core local-first requirement. All user data
stays on the machine unless explicitly requested by the user.

Required constraints:

- default bind is `127.0.0.1`;
- non-loopback bind is refused in v1 with exit 8 and no escape flag;
- Origin allowlist and `Sec-Fetch-Site` checks reject unsafe cross-origin POSTs;
- no CDN, telemetry, analytics, remote model call, hosted storage, or browser
  asset fetch;
- no non-loopback outbound HTTP, DNS, or socket access from the corpus-reading
  process; the only allowed network surfaces are loopback bind, loopback
  Postgres access, and other explicitly local endpoints already permitted by
  the benchmark harness;
- htmx is vendored at `src/engram/bench_review/static/htmx.min.js` and shipped
  via package data;
- review SQLite and JSONL files live under `.scratch/` by default;
- tracked exports are CLI-only and redacted by default;
- the export command must not include raw segment text, claim text, note text,
  prompts, completions, private values, home-directory absolute paths, or local
  model filesystem paths;
- scratch review state is not consumed by production extraction,
  consolidation, interview, entity review, or serving paths.
- production Postgres reads use a read-only role and/or read-only transactions;
  no production-table write privilege is required for the workbench.
- v1 does not inherit RFC 0027's later `ENGRAM_INTERVIEW_ALLOWED_ORIGINS`
  extension. Origin hosts are loopback-only in this surface until a follow-on
  RFC pairs any remote access story with authentication and a renewed privacy
  review.

Dependency packaging should mirror RFC 0027: FastAPI, Uvicorn, and Jinja2 live
behind the existing `engram[serve]` optional extra or a narrower follow-on extra
if the implementation spec chooses one. The CLI imports the web module lazily;
missing serve dependencies exit 2 with an install hint. The app uses sync route
handlers, `uvicorn --workers 1`, package-local templates/static assets, and a
served `/static/htmx.min.js` with no external asset URLs.

## Implementation Plan

1. Add artifact loaders and validators for benchmark slices, candidate run
   artifacts, required segment records, prior extraction rows,
   data-availability states, and risk tags.
2. Add deterministic classifier functions for queue tags and promotion-readiness
   state.
3. Add scratch review-state storage with SQLite and optional JSONL recovery
   export.
4. Add the FastAPI/Jinja2/htmx web app and package-local templates/static
   assets.
5. Add CLI commands under `engram phase3 bench-review`.
6. Add redacted export and status commands.
7. Add focused tests.

Implementation should prefer small modules:

- `src/engram/bench_review/artifacts.py`;
- `src/engram/bench_review/classify.py`;
- `src/engram/bench_review/storage.py`;
- `src/engram/bench_review/web.py`;
- `src/engram/bench_review/cli.py`.

## Tests And Acceptance Criteria

Acceptance requires:

- loader tests for slice/run artifacts, required segment records,
  metadata-only fallback, malformed benchmark data, slice/run mismatch, and
  ambiguous prior extraction identity rejection;
- classifier tests for zeroed, newly nonzero, count-changed, predicate-mix,
  high-drop, provenance-anomaly, schema/parse-anomaly, and unchanged cases;
- storage tests proving decisions are idempotently upserted and review state
  stores no segment text or claim text columns, plus tests for run-level
  decisions and resumable UI state;
- queue-state tests proving undecided rows live in `segment_queue`, decided
  rows live in `segment_reviews`, UUID-shaped segment IDs round-trip as text,
  and metadata-only sessions preserve artifact diagnostics without a segment
  records path;
- production-DB access tests proving loaders run in read-only transactions and
  fail closed when a write is attempted;
- FastAPI `TestClient` tests for landing, queue, segment page, decision POST,
  visible saved decisions, Origin rejection, `Sec-Fetch-Site` rejection,
  excerpt privacy-tier rejection, and no-CDN rendered pages;
- route tests proving one process owns one active review session, out-of-slice
  segment IDs return 404, run-level decisions return 409 until readiness is
  `ready_for_owner_decision`, and multi-message excerpts enforce max-tier
  carry;
- UI contract tests for data-availability blocking, promotion-readiness
  blockers, deterministic resume, shortcut focus safety, and visible
  post-decision confirmation;
- export tests proving tracked summaries omit raw segment text, claim text,
  note text, prompts, completions, private values, home-directory absolute
  paths, and local model filesystem paths by default;
- export path tests for absolute paths, `..` traversal, symlink escape,
  home-directory paths, and overwrite refusal;
- export sanitization tests proving operator-chosen artifact filenames do not
  leak into tracked summaries;
- CLI tests for `serve` argument validation, non-loopback refusal, `status`,
  and `export`;
- package-data tests proving `src/engram/bench_review/static/htmx.min.js` ships
  from the wheel and no rendered page references an external asset URL;
- network-safety tests or smoke checks proving no non-loopback outbound network
  calls are made by loaders, routes, or export commands;
- import-graph tests proving `engram.bench_review.web` does not import
  `engram.consolidator.transitions` or write-side production pipeline modules;
- no live LLM calls and no network calls in unit tests.

Manual acceptance for the first implementation should include reviewing the
RFC 0028 100-segment bench's prior-positive / candidate-zero set in the UI and
producing a redacted summary under
`docs/reviews/rfc0028-predicate-intent-implementation/`.

## Open Questions

1. Should review state remain SQLite-only after v1, or should accepted
   benchmark-review decisions eventually become an append-only Postgres table?
   V1 chooses SQLite to avoid polluting canonical project data with
   run-specific operator notes.
2. Should candidate claim text be emitted by the benchmark harness for UI
   display? If so, it should remain scratch-only and should not be included in
   tracked reports by default.
3. What is the exact migration/operator path for provisioning the read-only
   Postgres role used by the workbench? The RFC requires mechanical read-only
   access, but implementation should decide whether role creation is part of
   migrations, setup docs, or a local operator command.
4. Should future Phase 4 benchmark artifacts get a `phase4 bench-review` alias,
   or should this command remain extraction-artifact-specific under Phase 3?
5. Should `candidate_redacted` items be eligible for acceptance when only
   aggregate/predicate data is visible, or should semantic acceptance always
   require a local source excerpt?

## Promotion Path

If accepted, this RFC should be promoted to a concrete implementation spec
before code implementation, mirroring RFC 0027. The spec should freeze the
route contract, artifact schemas, review-state schema, privacy/export rules,
CLI surface, and acceptance tests. Code implementation can then proceed through
the standard multi-agent implement-review-synthesize loop, with fresh execution
contexts preferred after synthesis.
