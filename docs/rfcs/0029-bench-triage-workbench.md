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
5. Provide a concise recommendation-readiness signal: which segments are
   accepted, which are regressions, which need follow-up, which are excluded or
   blocking out of scope, and whether the run is ready for an explicit
   owner/coordinator gate recommendation.
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
  --review-db .scratch/benchmarks/extraction-review/<artifact-id>/review.sqlite3 \
  --prior-prompt-version extractor.v8.d064.accounted-zero \
  --prior-model-version <model-version> \
  --prior-request-profile-version <request-profile-version> \
  --reviewer-label operator \
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
  `request_profile_version`) or explicit prior-run artifacts for direct
  run-to-run comparison;
- optional private-detail candidate artifacts when the operator explicitly
  wants local claim text in the UI.

Prior-run artifact mode is first-class and persistable. The CLI names it with
`--prior-run PATH` plus `--prior-segments PATH`, or with `--prior-run PATH` and
a resolvable prior segment-record path inside that prior run artifact. Startup
validates that candidate and prior artifacts reference the same slice, use the
same ordered segment ID list, and expose enough per-segment records to compute
all required data-availability states. `serve`, `status`, and `export` must be
able to reconstruct the comparison from scratch SQLite alone plus the referenced
artifacts; a prior artifact path/hash mismatch fails closed instead of replaying
old decisions onto a new comparison.

Normal triage mode requires candidate segment records. If segment records are
missing, malformed, or do not match the slice, the app starts only in
metadata-only status mode: aggregate run metadata and artifact diagnostics are
visible, but segment verdict controls are disabled.

The workbench writes:

- a private review SQLite database, defaulting to
  `.scratch/benchmarks/extraction-review/<candidate-artifact-id>/review.sqlite3`;
- optional JSONL snapshots in the same scratch directory for recovery and diff
  review;
- a redacted tracked summary only when the operator explicitly runs the export
  command.

All production Postgres access is read-only. V1 has one enforcement rule: the
workbench must connect to production Postgres as a dedicated read-only role and
must start every production-table route/loader transaction with `SET
TRANSACTION READ ONLY`. Missing read-only role, unexpected write privilege, or
failure to enter a read-only transaction is a startup/request failure, not a
graceful downgrade. Because PostgreSQL roles are cluster-global rather than
schema-local, provisioning is an idempotent local operator command,
`engram phase3 bench-review provision-readonly-role`, for the stable role name
`engram_bench_review_readonly`; the implementation spec may add a Make wrapper
but must not leave role creation as an undocumented manual SQL step. The web
server must not run against a superuser, owner role, or general application
writer role.

### Review State

Review state is intentionally outside production Postgres in v1. A small
SQLite database is enough and keeps the boundary clear.

Recommended tables:

```sql
CREATE TABLE review_sessions (
  id TEXT PRIMARY KEY,
  workbench_schema_version TEXT NOT NULL,
  classifier_version TEXT NOT NULL,
  data_availability_rules_version TEXT NOT NULL,
  readiness_rules_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  bench_run_id TEXT NOT NULL,
  public_candidate_artifact_id TEXT NOT NULL,
  run_path TEXT NOT NULL,
  run_artifact_sha256 TEXT NOT NULL,
  segment_records_path TEXT,
  segment_records_sha256 TEXT,
  slice_path TEXT NOT NULL,
  slice_artifact_sha256 TEXT NOT NULL,
  prior_comparison_mode TEXT NOT NULL CHECK (
    prior_comparison_mode IN ('database', 'artifact')
  ),
  prior_prompt_version TEXT,
  prior_model_version TEXT,
  prior_request_profile_version TEXT,
  prior_run_path TEXT,
  prior_run_artifact_sha256 TEXT,
  prior_segment_records_path TEXT,
  prior_segment_records_sha256 TEXT,
  public_prior_artifact_id TEXT,
  reviewer_label TEXT NOT NULL DEFAULT 'operator',
  active_queue TEXT NOT NULL DEFAULT 'needs_review',
  queue_fingerprint TEXT NOT NULL,
  high_drop_count_threshold INTEGER NOT NULL,
  current_segment_id TEXT,
  metadata_only INTEGER NOT NULL DEFAULT 0,
  artifact_diagnostics_json TEXT NOT NULL DEFAULT '{}',
  run_recommendation TEXT CHECK (
    run_recommendation IN (
      'undecided',
      'recommend_promote',
      'recommend_do_not_promote'
    )
  ) DEFAULT 'undecided',
  run_recommendation_note TEXT NOT NULL DEFAULT '',
  run_recommended_at TEXT
);

CREATE TABLE segment_queue (
  session_id TEXT NOT NULL REFERENCES review_sessions(id),
  segment_id TEXT NOT NULL,
  review_order INTEGER NOT NULL,
  data_availability TEXT NOT NULL,
  semantic_delta_kind TEXT NOT NULL DEFAULT 'none' CHECK (
    semantic_delta_kind IN ('none', 'count_only', 'predicate_or_object', 'unknown')
  ),
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
  public_candidate_artifact_id TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (
    decision IN (
      'accept_candidate_change',
      'flag_candidate_regression',
      'needs_followup',
      'exclude_unchanged_from_review',
      'mark_blocking_out_of_scope'
    )
  ),
  confidence TEXT NOT NULL CHECK (
    confidence IN ('low', 'medium', 'high')
  ),
  review_basis TEXT NOT NULL CHECK (
    review_basis IN (
      'structured_counts_only',
      'local_source_context',
      'private_detail_artifact',
      'not_reviewable'
    )
  ),
  source_context_available INTEGER NOT NULL DEFAULT 0,
  private_detail_available INTEGER NOT NULL DEFAULT 0,
  semantic_delta_cleared INTEGER NOT NULL DEFAULT 0,
  review_context_json TEXT NOT NULL DEFAULT '{}',
  note TEXT NOT NULL DEFAULT '',
  decided_at TEXT NOT NULL,
  PRIMARY KEY (session_id, segment_id),
  FOREIGN KEY (session_id, segment_id)
    REFERENCES segment_queue(session_id, segment_id)
);

CREATE TABLE review_batches (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES review_sessions(id),
  action TEXT NOT NULL CHECK (
    action IN ('exclude_unchanged_from_review')
  ),
  queue_fingerprint TEXT NOT NULL,
  reason TEXT NOT NULL,
  included_segment_ids_json TEXT NOT NULL,
  excluded_segment_ids_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
```

`segment_id` is text because Engram segment IDs are UUIDs. `segment_queue`
materializes every loaded segment, including undecided rows; `segment_reviews`
contains only decided rows and has a composite foreign key back to the loaded
queue, so scratch storage cannot persist an out-of-slice decision. Status and
readiness are computed by left-joining queue rows to review rows, so undecided
state does not require sentinel decisions. `segment_records_path` is nullable
for metadata-only mode, and `artifact_diagnostics_json` records why segment
controls are disabled.

The schema deliberately omits segment text, claim text, prompts, completions,
and private values. The UI may read private corpus text from Postgres and
scratch artifacts for local display, but review state stores only identifiers,
artifact hashes, derived queue tags, review basis metadata, decisions,
confidence, timestamps, and notes. Notes are private scratch content by default
and are not included in tracked exports in v1.

`review_context_json` is for machine-readable basis flags only; it must not
store source excerpts, claim text, prompts, completions, raw path basenames, or
private values.

`reviewer_label` is not an identity field. It defaults to the literal
`operator`, must never default to the OS username, login name, email address, or
home directory, and is excluded from tracked exports. If a follow-on spec allows
custom labels, the label is scratch-local unless the exporter maps it to a
predefined redacted token.

`queue_fingerprint` is a SHA256 over a canonical JSON object, not an arbitrary
implementation detail. It covers:

- workbench schema version and classifier version;
- slice schema/version, slice artifact hash, and ordered segment IDs;
- candidate run public artifact ID plus `run.json` and segment-record hashes;
- prior comparison mode plus either the full prior extraction version triple or
  the prior run/segment artifact public IDs and hashes;
- classifier tunables, including `high_drop_count_threshold`;
- data-availability and readiness rule versions plus private-detail and source
  context availability flags that affect readiness.

Startup recomputes the fingerprint before opening a session. `serve`, `status`,
and `export` fail closed on mismatch and print the persisted fingerprint, live
fingerprint, and the first differing input category. There is no v1 replay or
automatic migration of segment decisions across a changed queue; a future spec
may add an explicit reload command that writes a new session.

Benchmark review decisions never feed production derivations. Extraction,
consolidation, gold-label interview, entity review, and serving paths do not
consume this scratch state.

Scratch run recommendations are review evidence only. They do not update
Striatum state, do not satisfy a Striatum blocker, and do not make an
operational gate decision authoritative under D074. If a benchmark run should
advance, the owner or coordinator records that through the normal Striatum/docs
gate artifact for the relevant workflow; the scratch SQLite recommendation is
cited as supporting evidence, not treated as the gate.

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
structured data and persisted review basis to prove the delta being accepted.
The POST route computes `review_basis`, `source_context_available`,
`private_detail_available`, and `semantic_delta_cleared` from loaded artifacts
and route state; it must not trust form input for those fields. Missing,
malformed, or ambiguous data can be parked as `needs_followup` or marked
blocking out of scope, but it cannot make the run ready for a promotion
recommendation.
`candidate_zero` is reviewable when the prior identity is unambiguous and the
UI can show local source context or private-detail evidence sufficient for the
operator to decide whether zero claims are acceptable.

Redacted candidate artifacts are allowed for aggregate/count review, but not
for ungrounded semantic acceptance. A `candidate_redacted` item with
`semantic_delta_kind='count_only'` can clear readiness from
`structured_counts_only` if the review is only about counts/provenance. A
`candidate_redacted` item with predicate or object semantic change can clear
readiness only when the stored basis is `local_source_context` or
`private_detail_artifact` and `semantic_delta_cleared=1`; otherwise it remains
a blocker even after the operator records `accept_candidate_change`.

### Classification Model

The loader builds a deterministic queue record per segment:

- `zeroed`: prior extraction had at least one claim and the candidate emitted
  zero claims;
- `newly_nonzero`: prior extraction had zero claims and the candidate emitted
  at least one claim;
- `count_changed`: prior and candidate claim counts differ;
- `high_drop_count`: the candidate dropped at least
  `ENGRAM_BENCH_REVIEW_HIGH_DROP_COUNT_THRESHOLD` prior claims in one segment
  by absolute count; the v1 default is `2`, the value must be an integer `>= 1`,
  and the resolved value is stored in `review_sessions` and included in
  `queue_fingerprint`;
- `predicate_mix_changed`: the candidate predicate multiset differs from the
  prior predicate multiset, so both distinct predicate membership changes and
  per-predicate count distribution changes are review-triggering;
- `provenance_anomaly`: candidate provenance cleanliness is below the run's
  expected threshold;
- `schema_or_parse_anomaly`: candidate validation produced malformed or
  schema-invalid structured output;
- `unchanged`: no review-triggering delta.

Queue tabs are a view over those tags:

- Needs review;
- Follow-up;
- Regressions;
- Excluded blockers;
- Accepted;
- Zeroed;
- Newly nonzero;
- Count changed;
- Predicate mix changed;
- High drops;
- Provenance;
- Schema / parse;
- Unchanged;
- All.

Zeroed segments, newly nonzero segments, missing-data states, malformed-data
states, count changes, predicate-mix changes, provenance anomalies, and
high-drop segments are always manual-review items. Complete unchanged no-risk
segments are loaded with `required_review=0` by default, so they do not block
readiness and do not need one-by-one review. V1 provides one first-class batch
action: `exclude_unchanged_from_review`. It is limited to records with complete
data, `semantic_delta_kind='none'`, no risk tags, no count delta, no predicate
delta, no provenance warning, no prior review conflict, and the exact current
`queue_fingerprint`. The batch preview lists included segment IDs and excluded
IDs by reason, and `review_batches` records the machine-readable reason plus
the fingerprint used for the preview.

## Screen Design

The primary screen is one segment at a time. It starts with a plain-language
change-summary block that answers:

- what changed;
- whether data is complete, redacted, missing, malformed, or ambiguous;
- the highest risk reason;
- what action is required next.

The rest of the page shows:

- a progress header: current queue, reviewed count, remaining count,
  unresolved blocker count, and recommendation-readiness state;
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
- applicable verdict controls with visible consequence labels:
  - Accept candidate change: count this delta as reviewed and acceptable;
  - Flag candidate regression: block recommendation readiness until resolved;
  - Park for follow-up: keep the item unresolved;
  - Exclude unchanged from this review: available only for complete unchanged
    no-risk rows;
  - Mark blocking out of scope: available for risky, missing, malformed,
    ambiguous, zeroed, or changed rows, requires a rationale note, and remains
    visible in blocker queues.

`exclude_unchanged_from_review` is not available on risky rows.
`mark_blocking_out_of_scope` counts as an operator action but does not make a
risky, missing, malformed, ambiguous, zeroed, or changed item disappear from
recommendation-readiness accounting. The summary shows excluded unchanged rows
separately from blocking out-of-scope rows.

Recommendation readiness is derived and deliberately weaker than a Striatum
gate decision:

- `blocked`: at least one blocking risk remains, required data is missing or
  malformed, or a regression has been flagged;
- `review_incomplete`: reviewable items remain undecided;
- `ready_for_owner_gate_recommendation`: all configured review obligations are
  complete and the operator may record a non-authoritative recommendation for
  the owner/coordinator gate;
- `promotion_recommendation_recorded`: the operator recorded a scratch-local
  recommendation to promote through the external owner gate;
- `rejection_recommendation_recorded`: the operator recorded a scratch-local
  recommendation not to promote.

Readiness is computed from a deterministic matrix:

| Availability / decision / basis | Clears review obligation? | Clears recommendation blocker? |
|---------------------------------|---------------------------|--------------------------------|
| `complete` + `accept_candidate_change` | yes | yes, unless a hard tag remains |
| `candidate_zero` + `accept_candidate_change` + `local_source_context` or `private_detail_artifact` | yes | yes, when prior identity is unambiguous |
| `candidate_zero` + `accept_candidate_change` + `structured_counts_only` | yes | no; zero-claim semantic judgment lacks basis |
| `candidate_redacted` + `accept_candidate_change` + `structured_counts_only` + `semantic_delta_kind='count_only'` | yes | yes |
| `candidate_redacted` + `accept_candidate_change` + `structured_counts_only` + predicate/object semantic delta | yes | no; semantic blocker remains |
| `candidate_redacted` + `accept_candidate_change` + `local_source_context` or `private_detail_artifact` + `semantic_delta_cleared=1` | yes | yes, unless a hard tag remains |
| any state + `flag_candidate_regression` | yes | no; blocks readiness |
| any state + `needs_followup` | yes | no; blocks readiness |
| risky, missing, malformed, ambiguous, zeroed, or changed state + `mark_blocking_out_of_scope` | yes | no; remains an out-of-scope blocker and requires a note |
| complete unchanged no-risk row + `exclude_unchanged_from_review` | yes | yes |
| `candidate_missing`, `candidate_malformed`, `prior_missing`, `prior_ambiguous` with no decision | no | no; hard blocker until fixed by a new artifact or disambiguated prior identity |
| `schema_or_parse_anomaly` or `provenance_anomaly` with no resolved artifact | no | no; hard blocker until fixed by a new artifact |

`ready_for_owner_gate_recommendation` is true only when there are zero hard
blockers, zero flagged regressions, zero `needs_followup` rows, zero
`mark_blocking_out_of_scope` rows, zero undecided review obligations, and every
remaining non-hard required-review row has either `accept_candidate_change` with
sufficient stored review basis or an allowed `exclude_unchanged_from_review`
decision.

The UI must support keyboard review without requiring it:

- `a`: accept candidate change;
- `r`: regression;
- `u`: park unresolved / needs follow-up;
- `x`: exclude unchanged from this review when the row is eligible;
- `o`: mark blocking out of scope when the row is eligible and a note is present;
- `c`: cycle confidence;
- `j`: next item;
- `k`: previous item;
- `/`: focus filter/search;
- `?`: shortcut overlay.

Decision shortcuts are disabled while an input, textarea, select, or
contenteditable element has focus. A saved decision must render a visible
confirmation and remain visible when the segment is reloaded.

The decision panel includes the applicable decision buttons, a confidence
control (`low` / `medium` / `high`, default `medium`), and a note textarea.
Notes remain scratch-local and are excluded from tracked exports. Notes are
optional except for `mark_blocking_out_of_scope`, where a rationale is required.
Segment decisions are idempotent upserts on `(session_id, segment_id)`:
resubmitting a decision updates decision, confidence, review-basis metadata,
note, and `decided_at` for that segment inside the active review session.

Keyboard details should be frozen in the follow-on spec, but v1 semantics are:
decision keys submit the currently selected confidence and note; `c` cycles
confidence without moving focus; `j` / `k` move within the current filtered
queue and stop at boundaries with a visible status message; `/` focuses the
queue filter/search input; `?` opens a shortcut modal; `Esc` closes the modal
and restores focus to the last active control.

## Routes

V1 route contract:

| Verb | Path | Purpose |
|------|------|---------|
| GET | `/` | Review session landing page: run metadata, queue counts, last decision, and primary resume action. |
| GET | `/segments` | Queue list with filters. Defaults to Needs review. |
| GET | `/segments/{segment_id}` | Full segment review page. |
| POST | `/segments/{segment_id}/decision` | Record or update the segment decision in scratch review state. |
| POST | `/segments/batch-exclude-unchanged` | Record reviewed exclusion for eligible unchanged/no-risk rows after preview. |
| GET | `/segments/{segment_id}/excerpt` | Expand local segment/evidence excerpt. Tier ceiling enforced at route layer. |
| GET | `/summary` | Private local summary: counts by decision and risk tag. |
| POST | `/run-recommendation` | Record a scratch-local non-authoritative run-level recommendation. |

One `serve` process owns exactly one active review session. The route paths do
not include `session_id` because the session is selected or created at startup
from `--review-db`, `--run`, `--slice`, `--segments`, and any prior-artifact
inputs. The SQLite schema keeps `session_id` so future multi-session or
cross-run review is possible, but v1 routes always resolve the single active
session from process state.

The landing page uses blocker-first resume behavior. If follow-up,
regression, or blocking-out-of-scope rows exist, the primary action links to
the unresolved blocker queue. If no blockers exist but required review remains,
it links to Needs review. If the run is
`ready_for_owner_gate_recommendation`, it links to the recommendation panel.

`GET /segments` accepts `queue=<needs_review|zeroed|newly_nonzero|
count_changed|predicate_mix_changed|high_drops|provenance|schema_parse|
followup|regressions|excluded_blockers|accepted|unchanged|all>` and optional
`q=<text>` filter parameters. Ordering is deterministic: hard blockers first,
then risk-rank order, then decision-state rank, then slice order / segment ID.
V1 does not paginate; if a future benchmark slice makes this too heavy,
pagination must preserve deterministic `j` / `k` next/previous behavior within
the active filter. Empty tabs render an explicit "no items in this queue"
state.

`GET /segments/{segment_id}` and `/segments/{segment_id}/excerpt` return 404
unless `segment_id` belongs to the loaded slice for the active session. Segment
IDs outside the loaded benchmark cannot be rendered by guessing URLs.

`POST /segments/{segment_id}/decision` accepts form fields
`decision`, `confidence`, and optional `note`; invalid values return 422, an
unknown or out-of-slice segment returns 404, and a successful htmx request
returns either the updated decision panel or `HX-Redirect` to the next segment
in the current filtered queue. The route computes and persists review-basis
fields from server-side artifact/source availability. `mark_blocking_out_of_scope`
without a non-empty note returns 422.

`POST /segments/batch-exclude-unchanged` accepts the current
`queue_fingerprint` and records `exclude_unchanged_from_review` only for rows
that still match the preview eligibility rule. A fingerprint mismatch returns
409 with no side effects.

`POST /run-recommendation` accepts
`recommendation=recommend_promote|recommend_do_not_promote` plus optional
`note`. `recommend_promote` returns 409 unless readiness is exactly
`ready_for_owner_gate_recommendation`. `recommend_do_not_promote` is reachable
from `blocked`, `review_incomplete`, and `ready_for_owner_gate_recommendation`
when a candidate run artifact is loaded; a note is required unless the
recommendation is recorded from the ready state. Both values are explicitly
non-authoritative D074 support evidence, not gate state.

Mutating routes (`POST /segments/{segment_id}/decision`,
`POST /segments/batch-exclude-unchanged`, and `POST /run-recommendation`) use
RFC 0027's browser-tab defense: an Origin allowlist over the current
`http://127.0.0.1:<port>` and `http://localhost:<port>`, plus
`Sec-Fetch-Site: same-origin` enforcement when the header is present. Mismatch
returns 403 and has no side effects.

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
engram phase3 bench-review provision-readonly-role
```

The `provision-readonly-role` command is setup-only and idempotent. It creates
or repairs the local read-only role grants needed by the workbench; it does not
start a review session or write review state.

`serve` starts the workbench. Required inputs are `--run` plus either
`--segments` or a resolvable segment-records path inside the run artifact.
`--slice` is required unless the run artifact contains a verified slice
reference. Prior comparison requires either all three prior identity fields
(`--prior-prompt-version`, `--prior-model-version`,
`--prior-request-profile-version`) for database-prior mode or explicit
prior-artifact inputs (`--prior-run` plus `--prior-segments` or a resolvable
prior segment-record path inside `--prior-run`). Ambiguous prior identity is a
startup error unless `--metadata-only` is passed.

`--review-db PATH` is an optional `serve` override; without it, the path is
derived from the sanitized candidate public artifact ID, not the raw benchmark
run ID. `--reviewer-label` defaults to the literal `operator`; the CLI must not
read `$USER`, `$LOGNAME`, `os.getlogin()`, Git config, or email address for this
field.

At startup, `serve` parses run metadata before creating or resuming the
session. If the loaded candidate artifact is redacted and contains semantic
predicate/object deltas that cannot clear readiness from structured counts
alone, the CLI prints a warning before the URL so the operator can choose to
rerun the scratch benchmark with private-detail artifacts.

`status` prints counts from the scratch review database without starting a
server: public artifact ID, queue fingerprint, reviewed count, blocker count,
decisions by verdict, and recommendation-readiness state.

`export` writes a redacted Markdown summary to a caller-supplied tracked path
under `docs/reviews/`. V1 has no `--allow-outside-reviews` flag and no web
export route. The export command resolves the output path before writing and
refuses absolute paths outside the repository, `..` traversal, symlink escape,
home-directory paths, and overwriting an existing file unless an explicit
`--overwrite` flag is provided.

## Redacted Export Contract

The export contains:

- public candidate artifact ID and prior artifact ID, when present, derived
  from artifact hashes; raw benchmark run IDs are untrusted and are not exported
  verbatim;
- benchmark timestamp, generated-at timestamp, queue fingerprint, and content
  hashes for `run.json` and segment-record artifacts;
- sanitized prompt-version, model-version, and request-profile display tokens;
- public artifact IDs for the slice and candidate/prior segment records; raw
  path basenames are not exported because operator-chosen filenames can contain
  private names;
- prior extraction identity or prior artifact identity, with path-shaped model
  versions normalized before export;
- aggregate reviewed/unreviewed counts;
- counts by data-availability state, risk tag, decision, and
  data-availability-by-decision cross-product;
- segment IDs grouped by decision and blocker reason;
- run-level recommendation, if recorded, labeled as non-authoritative support
  evidence for the external D074 gate;
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
- raw run IDs derived from operator-provided backend names;
- reviewer labels;
- home-directory absolute paths;
- local model filesystem paths;
- unsanitized model-version strings that look like absolute or home-relative
  filesystem paths;
- raw artifact path basenames;
- non-redacted scratch JSON/JSONL payloads.

The UI may display private text because it is a local operator tool. That does
not make private text eligible for tracked docs.

Export sanitization treats every operator-provided identifier as hostile:
benchmark run IDs, backend names, artifact filenames, reviewer labels, and
model-version strings all go through the same allowlist. Values that are empty,
path-shaped, contain home-directory fragments, or fail the public-token grammar
are replaced with stable `sha256:<12-hex>` tokens. The raw values remain in
scratch SQLite only.

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
  prompts, completions, private values, raw run IDs, reviewer labels, raw
  artifact path basenames, home-directory absolute paths, or local model
  filesystem paths;
- scratch review state is not consumed by production extraction,
  consolidation, interview, entity review, or serving paths.
- production Postgres reads require the `engram_bench_review_readonly` role and
  read-only transactions together; no production-table write privilege is
  allowed for the workbench connection.
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
   artifacts, required segment records, prior extraction rows, prior-run
   artifacts, data-availability states, artifact hashes, and risk tags.
2. Add queue-fingerprint computation and fail-closed mismatch handling for
   `serve`, `status`, and `export`.
3. Add deterministic classifier functions for queue tags, review-basis
   eligibility, and recommendation-readiness state.
4. Add the read-only Postgres role provisioning path and startup privilege
   checks.
5. Add scratch review-state storage with SQLite and optional JSONL recovery
   export.
6. Add the FastAPI/Jinja2/htmx web app and package-local templates/static
   assets.
7. Add CLI commands under `engram phase3 bench-review`.
8. Add redacted export and status commands.
9. Add focused tests.

Implementation should prefer small modules:

- `src/engram/bench_review/artifacts.py`;
- `src/engram/bench_review/classify.py`;
- `src/engram/bench_review/storage.py`;
- `src/engram/bench_review/web.py`;
- `src/engram/bench_review/cli.py`.

## Tests And Acceptance Criteria

Acceptance requires:

- loader tests for slice/run artifacts, required segment records,
  metadata-only fallback, malformed benchmark data, slice/run mismatch,
  prior-run artifact same-slice/same-order validation, prior artifact hash
  mismatch, and ambiguous prior extraction identity rejection;
- fingerprint tests proving the queue fingerprint covers ordered segment IDs,
  artifact hashes, prior comparison mode, classifier versions, threshold values,
  data-availability rule versions, and readiness rule versions, and that
  `serve`, `status`, and `export` fail closed on mismatch;
- classifier tests for zeroed, newly nonzero, count-changed, predicate-multiset
  changes, high-drop absolute-count threshold/default/env override,
  provenance-anomaly, schema/parse-anomaly, and unchanged cases;
- storage tests proving decisions are idempotently upserted and review state
  stores no segment text or claim text columns, the note column is never read by
  export, review-basis fields are computed server-side, composite queue/review
  keys reject out-of-slice decisions, plus tests for run-level recommendations
  and resumable UI state;
- queue-state tests proving undecided rows live in `segment_queue`, decided
  rows live in `segment_reviews`, UUID-shaped segment IDs round-trip as text,
  decision-state queues include follow-up/regression/excluded-blocker rows, and
  metadata-only sessions preserve artifact diagnostics without a segment records
  path;
- production-DB access tests proving the server refuses missing read-only role,
  refuses writer/superuser connections, runs loaders in read-only transactions,
  and fails closed when a write is attempted;
- FastAPI `TestClient` tests for landing, queue, segment page, decision POST,
  visible saved decisions, Origin rejection, `Sec-Fetch-Site` rejection,
  excerpt privacy-tier rejection, and no-CDN rendered pages;
- route tests proving one process owns one active review session, out-of-slice
  segment IDs return 404, `recommend_promote` returns 409 until readiness is
  `ready_for_owner_gate_recommendation`, `recommend_do_not_promote` is reachable
  from blocked/review-incomplete states with a required note, batch unchanged
  exclusion checks the queue fingerprint, and multi-message excerpts enforce
  max-tier carry;
- UI contract tests for every data-availability state and every verdict result:
  rendered change-summary consequence text, enabled/disabled controls,
  persisted review basis, resulting queue membership, recommendation-readiness
  label, blocker-first landing-page resume link, shortcut focus safety, and
  visible post-decision confirmation;
- export tests proving tracked summaries omit raw segment text, claim text,
  note text, prompts, completions, private values, raw run IDs, reviewer labels,
  home-directory absolute paths, and local model filesystem paths by default;
- export path tests for absolute paths, `..` traversal, symlink escape,
  home-directory paths, and overwrite refusal;
- export sanitization tests proving operator-chosen artifact filenames do not
  leak into tracked summaries, raw run IDs derived from backend names are
  replaced with public artifact IDs, and filesystem-path-shaped model versions
  are replaced with stable hash tokens;
- CLI tests for `serve` argument validation, prior-run artifact flags,
  `--review-db` default/override behavior, non-loopback refusal, read-only role
  failure, redacted-semantic-delta startup warning, `status`, and `export`;
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
3. Should future Phase 4 benchmark artifacts get a `phase4 bench-review` alias,
   or should this command remain extraction-artifact-specific under Phase 3?

## Promotion Path

If accepted, this RFC should be promoted to a concrete implementation spec
before code implementation, mirroring RFC 0027. The spec should freeze the
route contract, artifact schemas, review-state schema, privacy/export rules,
CLI surface, and acceptance tests. Code implementation can then proceed through
the standard multi-agent implement-review-synthesize loop, with fresh execution
contexts preferred after synthesis.
