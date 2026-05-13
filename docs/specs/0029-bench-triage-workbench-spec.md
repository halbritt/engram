<a id="spec-0029"></a>
# Spec 0029: Bench Triage Workbench Implementation Contract

| Field | Value |
|-------|-------|
| Spec | 0029 |
| Title | Bench Triage Workbench |
| Status | draft |
| Source RFC | [RFC 0029](../rfcs/0029-bench-triage-workbench.md) |
| Review status | Source review chain quarantined by [RFC 0032](../reviews/rfc0032-suspect-work-audit/FINAL_DECISION.md) |
| Date | 2026-05-09 |
| Decision refs | D020, D074 |
| Phase refs | PHASE-0003-FOLLOWON, PHASE-0004 |

## Purpose

This document is the implementation contract for the Engram Bench Triage
Workbench. The workbench exists because benchmark and re-extraction reports
became a human bottleneck: dense Markdown artifacts can show that a change
matters, but they do not give the operator a fast, resumable, low-cognitive-load
way to decide whether each affected segment is acceptable, a regression, or a
follow-up.

The v1 workbench is a local-only FastAPI/Jinja2/htmx surface plus a CLI export.
It reviews benchmark deltas from scratch artifacts, writes only scratch-local
review state, and emits redacted tracked summaries. It never mutates raw
evidence, segment rows, claim rows, or projections.

## Out of scope

The following are explicitly out of v1 scope:

- Hosted service, cloud API, telemetry, external persistence, login system,
  multi-user mode, or any mode where the server binds to a non-loopback address.
- Writing review decisions into production PostgreSQL tables.
- Promoting an extraction prompt, model, or request profile automatically.
- Showing full private segment text in tracked artifacts or web export routes.
- A general benchmark dashboard. The workbench is a narrow triage tool for one
  benchmark/re-extraction run at a time.
- Editing extraction artifacts or re-running extraction from the UI.
- Batch acceptance of risky segments. v1 may offer filters and navigation, but
  every mutating segment decision is per segment.
- A JavaScript build pipeline. htmx is vendored; all pages render server-side.

## Architecture

### Modules

- `src/engram/bench_review/__init__.py` - package marker and public exports.
- `src/engram/bench_review/artifacts.py` - loads slice/run/segment artifacts,
  normalizes candidate/prior comparison rows, and computes data availability.
- `src/engram/bench_review/classify.py` - assigns stable classification tags
  and risk ordering to normalized comparison rows.
- `src/engram/bench_review/storage.py` - owns scratch SQLite schema,
  idempotent initialization, segment decisions, run decision, and summaries.
- `src/engram/bench_review/export.py` - renders redacted Markdown exports from
  scratch review state.
- `src/engram/bench_review/web.py` - FastAPI app, route handlers, template
  context construction, and loopback-origin write protection.
- `src/engram/bench_review/templates/base.html` - shared page frame.
- `src/engram/bench_review/templates/index.html` - run summary and filters.
- `src/engram/bench_review/templates/segments.html` - triage queue.
- `src/engram/bench_review/templates/segment.html` - one-segment review view.
- `src/engram/bench_review/templates/summary.html` - completion and run verdict.
- `src/engram/bench_review/static/htmx.min.js` - vendored htmx, no CDN.
- `src/engram/cli.py` - adds `engram phase3 bench-review ...` commands.
- `pyproject.toml` - includes package data for templates/static assets if not
  already covered by package discovery.

### Boundaries

Production PostgreSQL is read-only for this feature. Candidate benchmark
artifacts and segment-record artifacts are also read-only. All review state is
stored under `.scratch/benchmarks/extraction-review/<run-id>/review.sqlite3`
unless the operator passes an explicit `--review-db` path.

Tracked review exports under `docs/reviews/` may contain aggregate counts,
segment identifiers, classification tags, data-availability states, prompt/model
version labels, artifact paths, and reviewer decisions. They must not contain
raw segment text, raw claim text, private excerpts, or LLM responses.

## Inputs

### Required CLI inputs

`engram phase3 bench-review serve` requires:

- `--slice PATH` pointing at the fixed benchmark slice used for the run.
- `--run PATH` pointing at the candidate benchmark run artifact.
- `--prior-prompt-version VERSION`.
- `--prior-model-version VERSION`.
- `--prior-request-profile-version VERSION`.

The command accepts optional `--segments PATH`. If omitted, the loader attempts
to resolve a segment-record artifact from the run artifact first, then from a
well-known sibling path. Missing segment records are allowed only in
metadata-only mode.

### Candidate run artifact

The loader must tolerate the benchmark artifact shapes already used by
`benchmarks/extraction/`, but normalize to this internal shape:

```python
@dataclass(frozen=True)
class CandidateRun:
    run_id: str
    artifact_path: Path
    generated_at: str | None
    prompt_version: str | None
    model_version: str | None
    request_profile_version: str | None
    segment_count: int | None
    result_rows: tuple[CandidateSegmentResult, ...]
```

`result_rows` may be empty. When candidate segment-level rows are absent, the
workbench still starts in metadata-only mode and disables all verdict controls.

Accepted source aliases are deliberately small and deterministic:

- `run_id`: `run_id`, `id`, `name`, or the run artifact stem as fallback.
- `generated_at`: `generated_at`, `created_at`, or `completed_at`.
- candidate prompt version: `prompt_version`,
  `extraction_prompt_version`, or `candidate_prompt_version`.
- candidate model version: `model_version`, `extraction_model_version`,
  or `candidate_model_version`.
- candidate request profile version: `request_profile_version`,
  `extraction_request_profile_version`, or
  `candidate_request_profile_version`.
- `segment_count`: `segment_count`, `segments_count`, or the length of the
  normalized result rows.
- result row list: `segments`, `segment_results`, `results`, `rows`, or
  `items`.

All integer count fields are coerced from JSON numbers or base-10 numeric
strings. Negative values, non-integer strings, missing segment identifiers, and
duplicate segment identifiers make the affected segment row unusable. Duplicate
rows do not use last-write-wins; the segment is assigned `candidate_malformed`
so the operator can regenerate or inspect the artifact instead of silently
trusting an arbitrary row.

### Segment records

The normalized segment-record contract is:

```python
@dataclass(frozen=True)
class CandidateSegmentResult:
    segment_id: str
    candidate_claim_count: int | None
    candidate_dropped_count: int | None
    candidate_predicates: tuple[str, ...]
    candidate_provenance_count: int | None
    data_state_hint: str | None
    source: str
```

Segment-record files may be JSON arrays, JSON objects with a common list key
(`segments`, `segment_results`, `results`, `rows`, or `items`), or JSONL.
Accepted per-row aliases are:

- segment id: `segment_id`, `source_segment_id`, or `id`.
- candidate claim count: `candidate_claim_count`, `claim_count`,
  `claims_count`, `total_claims`, `valid_claim_count`, or the length of a
  `claims` list.
- candidate dropped count: `candidate_dropped_count`, `dropped_count`,
  `dropped_claim_count`, or `invalid_claim_count`.
- candidate predicates: `candidate_predicates`, `predicates`,
  `predicate_names`, or `claims[*].predicate`.
- candidate provenance count: `candidate_provenance_count`,
  `provenance_count`, `evidence_count`, or the total count of
  `claims[*].evidence_ids`.
- data-state hint: `data_state`, `data_state_hint`, or `availability`.

Only `candidate_redacted` is accepted as a semantic hint in v1. Other hints are
preserved for diagnostics but do not override computed state. Malformed files
do not crash the server; they place every slice target in
`candidate_malformed`.

### Prior claims

Prior data comes from production claim tables filtered by:

- `source_segment_id`.
- `extraction_prompt_version`.
- `extraction_model_version`.
- `request_profile_version`.

The query is read-only. The normalized prior shape is:

```python
@dataclass(frozen=True)
class PriorSegmentResult:
    segment_id: str
    prior_claim_count: int
    prior_dropped_count: int
    prior_predicates: tuple[str, ...]
    prior_provenance_count: int
```

If the production schema or local environment cannot provide prior claims, the
affected segment receives `prior_missing`. The page must show that the segment
cannot support a strong candidate-vs-prior decision.

## Data Availability

Each normalized comparison row has exactly one `data_state`. State precedence is
evaluated in this order:

1. `candidate_malformed` when the segment-record file is malformed, the row is
   unusable, counts cannot be coerced, or duplicate rows exist for the segment.
2. `candidate_missing` when the slice segment has no candidate segment row.
3. `prior_missing` when prior lookup cannot produce a comparable prior summary.
4. `candidate_redacted` when the candidate row intentionally omits claim
   details but exposes counts.
5. `candidate_zero` when candidate and prior summaries both exist and the
   candidate claim count is exactly zero.
6. `complete` when candidate and prior summaries both exist and no earlier
   state applies.

The states mean:

- `complete` - candidate segment record and prior claim summary both exist.
- `candidate_zero` - candidate record and prior summary both exist, and the
  candidate has zero candidate claims.
- `candidate_redacted` - candidate record exists but omits claim details by
  design while still exposing counts.
- `candidate_missing` - no candidate segment record exists for this slice
  segment.
- `candidate_malformed` - candidate artifact could not be parsed or the row
  shape is unusable.
- `prior_missing` - prior lookup did not return a comparable prior summary.

When `data_state` is not `complete`, the UI must show an explicit state banner
above verdict controls. The banner includes one state-specific instruction:

- `candidate_malformed`: regenerate or inspect the candidate artifact; only
  follow-up or exclusion decisions are enabled.
- `candidate_missing`: regenerate the candidate segment records; only follow-up
  or exclusion decisions are enabled.
- `prior_missing`: inspect the prior version filters or prior extraction state;
  only follow-up or exclusion decisions are enabled.
- `candidate_redacted`: review counts-only behavior; all decisions remain
  enabled but the UI marks the review as lower confidence.
- `candidate_zero`: review the zeroed candidate carefully; all decisions remain
  enabled.

## Classification

Each row has one or more stable classification tags:

- `zeroed` - prior claim count is positive and candidate claim count is zero.
- `newly_nonzero` - prior claim count is zero and candidate claim count is
  positive.
- `count_changed` - both sides exist and claim counts differ.
- `high_drop_count` - candidate dropped count is above the configured threshold.
- `predicate_mix_changed` - normalized predicate sets differ.
- `provenance_anomaly` - candidate provenance count is missing, zero for
  nonzero claims, or materially below prior provenance count.
- `unchanged` - complete row with no other change tag.

The default queue order is state rank, first risk rank, then lexicographic
`segment_id`. State rank follows the data-state precedence above. Risk rank is:

1. `zeroed`.
2. `high_drop_count`.
3. `provenance_anomaly`.
4. `count_changed`.
5. `predicate_mix_changed`.
6. `newly_nonzero`.
7. `unchanged`.

Rows may have multiple tags. The first risk rank is the lowest-ranked tag in the
row's tag set. `unchanged` is assigned only when no other tag applies.

The `ENGRAM_BENCH_REVIEW_HIGH_DROP_COUNT` module-level environment variable
controls the high-drop threshold and defaults to `3`.

## Scratch SQLite State

The review database is created idempotently and contains no raw private text.
Schema v1:

```sql
CREATE TABLE review_sessions (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  run_id TEXT NOT NULL,
  slice_path TEXT NOT NULL,
  run_path TEXT NOT NULL,
  segments_path TEXT,
  candidate_prompt_version TEXT,
  candidate_model_version TEXT,
  candidate_request_profile_version TEXT,
  prior_prompt_version TEXT NOT NULL,
  prior_model_version TEXT NOT NULL,
  prior_request_profile_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE segment_reviews (
  segment_id TEXT PRIMARY KEY,
  data_state TEXT NOT NULL,
  tags_json TEXT NOT NULL,
  prior_claim_count INTEGER,
  candidate_claim_count INTEGER,
  prior_dropped_count INTEGER,
  candidate_dropped_count INTEGER,
  decision TEXT,
  rationale TEXT,
  decided_at TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE run_reviews (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  decision TEXT,
  rationale TEXT,
  decided_at TEXT,
  updated_at TEXT NOT NULL
);
```

Allowed segment decisions are:

- `accept_candidate_change`.
- `flag_candidate_regression`.
- `needs_followup`.
- `exclude_from_review`.

Allowed stored run decisions are:

- `safe_to_promote`.
- `blocked_by_regressions`.
- `needs_more_review`.

The UI and export must label `safe_to_promote` as "Bench review: safe to
promote candidate" and show that it does not mutate production data or bypass
Phase 4 gates.

`rationale` is optional review metadata with a maximum length controlled by
`ENGRAM_BENCH_REVIEW_RATIONALE_MAX_CHARS`, defaulting to `500`. The shared
sanitizer strips control characters, collapses whitespace, and truncates before
storage and export. No automatic route, template, storage, or export path may
copy raw segment text, raw claim text, evidence excerpts, or LLM responses into
review state. The UI labels the field as "review note, no excerpts" and the
export repeats that warning. User-pasted private text is outside automatic
detection in v1, so the implementation must avoid pre-filling rationale from
private content.

## CLI

### Serve

```bash
engram phase3 bench-review serve \
  --slice .scratch/benchmarks/extraction-backend/<slice>/slice.json \
  --run .scratch/benchmarks/extraction-backend/<run>/run.json \
  --segments .scratch/benchmarks/extraction-backend/<run>/segments.jsonl \
  --prior-prompt-version v1 \
  --prior-model-version llama-cpp:<model> \
  --prior-request-profile-version default \
  --host 127.0.0.1 \
  --port 8770
```

The server refuses non-loopback hosts and exits with status `8`. There is no
override flag in v1. Missing files, malformed artifacts, invalid review DB
paths, unwritable outputs, and other validation/runtime failures use the
existing CLI framework's standard nonzero error behavior; v1 does not assign a
separate numeric code for those cases.

### Export

```bash
engram phase3 bench-review export \
  --review-db .scratch/benchmarks/extraction-review/<run-id>/review.sqlite3 \
  --output docs/reviews/rfc0029-bench-triage-workbench/<name>.md
```

The export command refuses outputs outside `docs/reviews/` unless
`--allow-outside-reviews` is explicitly passed. The flag is intended for local
scratch use only and must be called out in tests.

### Status

```bash
engram phase3 bench-review status \
  --review-db .scratch/benchmarks/extraction-review/<run-id>/review.sqlite3
```

Status prints aggregate counts by data state, tag, and decision, plus the run
decision if one exists.

## Web Routes

### Read routes

- `GET /` - run summary, progress counts, risk queue entry point, and current
  run decision.
- `GET /segments` - filtered queue. Query params: `state`, `tag`, `decision`,
  `remaining=1`, and `limit`.
- `GET /segments/{segment_id}` - one-segment review screen.
- `GET /segments/{segment_id}/excerpt` - renders the local segment excerpt on
  demand from Postgres when the segment is at the displayable privacy tier.
  This text is never copied into scratch SQLite or tracked Markdown exports.
- `GET /summary` - completion summary and run-level decision form.

### Mutating routes

- `POST /segments/{segment_id}/decision` - records a segment decision and
  optional rationale in scratch SQLite, then redirects to the next remaining
  segment in the active review queue.
- `POST /run-decision` - records the run decision and optional rationale.

Every mutating route validates:

- Host is loopback.
- `Origin` or `Referer`, when present, is loopback and matches the bound port.
- `Sec-Fetch-Site`, when present, is `same-origin`, `same-site`, or `none`.
- Decision values are in the fixed vocabularies above.

Cross-site failures return HTTP 403. Unknown segment IDs return HTTP 404.

## UX Contract

The primary screen must answer three questions without reading a report:

- What changed? Show counts by data state and tag, with the riskiest queue
  linked first.
- Why should I care? Show prior/candidate counts, changed predicate names, and
  provenance/drop-count warnings as compact badges.
- What do I do next? Show exactly one segment-level decision form and a
  next-segment action after save.

The index and summary screens must show above-the-fold counts and direct filters
for undecided rows, `needs_followup`, `flag_candidate_regression`, and
`exclude_from_review`. Resume should not require re-reading a prior report.

The segment screen must keep the decision labels plain:

- "Accept candidate change" for expected or harmless deltas.
- "Flag candidate regression" for harmful extraction behavior.
- "Needs follow-up" for uncertain or incomplete review.
- "Exclude from review" for slice/artifact cases that should not influence the
  run verdict.

Keyboard shortcuts may be present but cannot be required to complete review.
The page must be usable with forms and links alone.

Run-decision copy must be bench-scoped. The stored value `safe_to_promote`
renders as "Bench review: safe to promote candidate" with a note that it does
not apply a production promotion and does not bypass Phase 4 gates.

## Redacted Export

The Markdown export includes:

- Review session metadata.
- Aggregate counts by data state, tag, and decision.
- Run-level decision and rationale.
- Segment table with segment ID, data state, tags, prior/candidate counts,
  decision, and sanitized reviewer rationale.

The export excludes:

- Segment text.
- Claim text.
- Evidence excerpts.
- Raw LLM requests or responses.
- Any field not explicitly listed above.

## Tests

Required focused tests:

- Artifact loader accepts JSON array, JSON object list keys, and JSONL segment
  records.
- Artifact loader applies the specified field aliases and marks duplicate
  segment rows `candidate_malformed`.
- Malformed or missing segment records produce metadata-only state without a
  server crash.
- Data-state precedence is deterministic for malformed, missing, prior-missing,
  redacted, zero, and complete candidate rows.
- Classification covers `zeroed`, `newly_nonzero`, `count_changed`,
  `high_drop_count`, `predicate_mix_changed`, `provenance_anomaly`, and
  `unchanged`.
- Queue ordering is stable for multi-tag rows and ties by `segment_id`.
- Scratch SQLite initialization is idempotent and stores no raw segment/claim
  text columns.
- Segment detail pages hydrate local segment excerpts and prior claim rows on
  demand without copying private text into scratch SQLite.
- Segment and run decisions persist and are reflected in summaries.
- Rationale sanitization strips control characters, collapses whitespace, and
  truncates before storage/export.
- Export refuses unsafe output paths by default and omits private text fields.
- CLI refuses non-loopback serve hosts with exit status `8`.
- Mutating routes reject cross-site requests.
- Mutating routes accept same-origin Tailscale Serve requests while the app
  remains bound to loopback.
- Missing candidate segment rows disable accept/regression controls in rendered
  HTML.
- Incomplete data states render state-specific instruction text.
- Index/summary screens render resume counts for undecided, follow-up,
  regression-flagged, and excluded rows.
- Bench-review modules do not write production PostgreSQL tables; tests pin the
  storage boundary to scratch SQLite plus read-only prior lookup.

## Acceptance

Implementation is complete when:

1. `engram phase3 bench-review serve` starts a loopback-only local workbench
   from existing benchmark artifacts.
2. The workbench can triage complete and incomplete segment comparison rows.
3. Review progress survives server restart via scratch SQLite.
4. `engram phase3 bench-review status` prints aggregate progress.
5. `engram phase3 bench-review export` writes a redacted Markdown summary.
6. Focused tests above pass.
7. The implementation review workflow for RFC 0029 reaches `accept` or
   `accept_with_findings`.
