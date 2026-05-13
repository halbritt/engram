<a id="rfc-0029"></a>
# RFC 0029: Bench Triage Workbench

| Field | Value |
|-------|-------|
| RFC | 0029 |
| Title | Bench Triage Workbench |
| Status | proposal |
| Implementation | implemented |
| Date | 2026-05-09 |
| Context | RFC 0017 (re-extraction dry runs); RFC 0019 (extraction backend benchmark harness); RFC 0024 (Phase 4 pre-full-corpus benchmark gate); RFC 0027 (localhost-only FastAPI/htmx web UI); RFC 0028 (predicate-intent surfacing); D020 / D074; `benchmarks/extraction/`; RFC 0032 audit of the RFC 0028 bench artifact |

Draft spec refs:
  - [Spec 0029](../specs/0029-bench-triage-workbench-spec.md) (draft; not promoted)

Decision refs:
  - D020
  - D074

Audit refs:
  - [RFC 0032 suspect-work audit](../reviews/rfc0032-suspect-work-audit/FINAL_DECISION.md)

Phase refs:
  - PHASE-0003-FOLLOWON
  - PHASE-0004

This RFC proposes a **local-only benchmark triage workbench** for reviewing
extraction and re-extraction benchmark deltas at human reading speed. The
immediate pressure comes from the RFC 0028 100-segment re-extraction bench:
aggregate metrics were clean, but the operator still had to validate zeroed and
count-changed segments from a dense Markdown artifact. That review surface is
too high-overhead for the decision it supports.

The workbench is not a new source of truth. It is a private, loopback-only
review UI over scratch benchmark artifacts. It records human triage decisions
to scratch-local review state, exports redacted summaries on demand, and never
writes review labels into production claim, belief, audit, or raw-evidence
tables in v1.

## Problem

Phase 3 and Phase 4 progress now depends on repeated "is this extraction
change semantically acceptable?" decisions. Existing artifacts answer different
questions:

- benchmark JSON answers whether a run completed, produced valid schema, and
  preserved provenance;
- aggregate Markdown answers whether counts, drops, and throughput moved in the
  expected direction;
- scratch review Markdown can list suspicious segments, but it forces the
  reviewer to hold prior claims, candidate behavior, source context, and the
  accept/reject decision in working memory.

That is the wrong ergonomics. The operator should be able to sit down, review a
queue of suspicious segments one at a time, make a clear decision, and stop
without losing progress.

The current Markdown workflow also creates avoidable privacy ambiguity. Private
scratch files may contain segment text and prior claim text. Tracked review
docs must remain redacted or aggregate unless the owner explicitly chooses
otherwise. A dedicated tool can make that boundary mechanical instead of
procedural.

## Goals

1. Let the operator triage extraction benchmark deltas with one segment on
   screen at a time.
2. Preserve Engram's local-first constraint: loopback-only, no hosted service,
   no telemetry, no CDN, no external persistence.
3. Keep production data immutable from this surface. Benchmark triage writes
   only private scratch review decisions in v1.
4. Make suspicious-segment queues obvious: zeroed segments, claim-count
   changes, high drop counts, predicate-mix changes, and provenance anomalies.
5. Provide a concise promotion-readiness signal: which segments are accepted,
   which are regressions, which need follow-up, which are excluded from the
   current review, and whether the run is ready for an explicit owner
   promotion decision.
6. Export a redacted, tracked summary suitable for `docs/reviews/` without
   leaking raw private corpus text by default.

## Non-goals

- This RFC does not add a hosted dashboard, multi-user service, login flow, TLS
  configuration, CDN asset, or JS framework.
- This RFC does not mutate `claims`, `claim_extractions`, `beliefs`,
  `claim_audits`, `projection_audits`, or raw evidence tables.
- This RFC does not decide whether RFC 0028 should be promoted to full-corpus
  re-extraction. It provides the UI for making that decision with less
  cognitive overhead.
- This RFC does not replace the command-line benchmark harness. The harness
  remains the source of benchmark artifacts.
- This RFC does not create gold labels for claim correctness. It records
  benchmark-review decisions about candidate runs.

## Proposal

### Shape

Add a local web surface under a new package, tentatively
`src/engram/bench_review/`, with a CLI entry point:

```text
engram phase3 bench-review serve \
  --slice .scratch/benchmarks/extraction-backend/slices/<slice>.json \
  --run .scratch/benchmarks/extraction-backend/<run>/run.json \
  --segments .scratch/benchmarks/extraction-backend/<run>/segments.jsonl \
  --prior-prompt-version extractor.v8... \
  --prior-model-version <model-version> \
  --prior-request-profile-version <request-profile-version> \
  --host 127.0.0.1 \
  --port 8770
```

The server uses the same delivery posture as RFC 0027: FastAPI, server-rendered
Jinja2 templates, vendored htmx, no build step, and loopback-only binding.
Non-loopback hosts are refused at startup with exit 8 and there is no
`--allow-non-loopback` flag. Static assets are package-local and served by the
app; no network asset fetch is allowed.

The workbench reads:

- an extraction benchmark slice manifest;
- a candidate benchmark run artifact;
- candidate segment records, either from `--segments` or by resolving
  `segment_records_path` from `run.json`;
- the local Postgres database for prior extraction rows and source metadata;
- a full prior extraction identity
  (`extraction_prompt_version`, `extraction_model_version`,
  `request_profile_version`) or an explicit prior-run benchmark artifact for
  direct run-to-run comparison;
- optional private-detail candidate artifacts when the operator explicitly
  wants local claim text in the UI.

Normal triage mode requires candidate segment records. If segment records are
missing, malformed, or do not match the slice, the app starts only in
metadata-only status mode: aggregate run metadata and artifact diagnostics are
visible, but segment verdict controls are disabled.

The workbench writes:

- a private review database, defaulting to
  `.scratch/benchmarks/extraction-review/<run-id>/review.sqlite3`;
- optional JSONL snapshots in the same scratch directory for recovery and diff
  review;
- a redacted tracked summary only when the operator explicitly runs an export
  command.

### Review state

The review state is intentionally outside production Postgres in v1. A small
SQLite database is enough and keeps the boundary clear.

Recommended tables:

```sql
CREATE TABLE review_sessions (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  bench_run_id TEXT NOT NULL,
  run_path TEXT NOT NULL,
  segment_records_path TEXT NOT NULL,
  slice_path TEXT NOT NULL,
  prior_prompt_version TEXT,
  prior_model_version TEXT,
  prior_request_profile_version TEXT,
  reviewer TEXT NOT NULL,
  active_queue TEXT NOT NULL DEFAULT 'needs_review',
  queue_fingerprint TEXT NOT NULL,
  current_segment_id INTEGER,
  run_decision TEXT CHECK (
    run_decision IN ('undecided', 'promote', 'do_not_promote')
  ) DEFAULT 'undecided',
  run_decision_note TEXT NOT NULL DEFAULT '',
  run_decided_at TEXT
);

CREATE TABLE segment_reviews (
  session_id TEXT NOT NULL REFERENCES review_sessions(id),
  segment_id INTEGER NOT NULL,
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

This schema deliberately omits segment text and claim text. The UI may read
private corpus text from Postgres and scratch artifacts for display, but review
state stores only identifiers, decisions, and notes. Notes are private scratch
content by default and are not included in tracked exports in v1. Benchmark
review decisions never feed production derivations: extraction, consolidation,
interview, entity review, and serving paths do not consume this scratch state.

### Data availability

Every segment gets a typed data-availability state before classification:

- `complete`: prior and candidate structured comparison data are available;
- `candidate_zero`: the candidate record proves the run emitted zero claims;
- `candidate_redacted`: structured candidate counts/predicates exist, but
  subject/object text is intentionally absent under the benchmark redaction
  policy;
- `candidate_missing`: the candidate segment record is absent;
- `candidate_malformed`: the candidate record exists but failed validation;
- `prior_missing`: no unambiguous prior extraction rows match the requested
  prior extraction identity.

The UI must never collapse `candidate_zero`, `candidate_redacted`,
`candidate_missing`, and `candidate_malformed` into the same visual state.
Semantic acceptance decisions are enabled only when the workbench has enough
structured data to prove the delta being accepted. Missing or malformed data
can be parked as `needs_followup` or excluded from the current review, but it
cannot make the run promotion-ready.

### Classification model

The loader builds a deterministic queue record per segment:

- `zeroed`: prior extraction had at least one claim and the candidate run
  emitted zero claims;
- `newly_nonzero`: prior extraction had zero claims and the candidate emitted
  at least one claim;
- `count_changed`: prior and candidate claim counts differ;
- `high_drop_count`: the candidate dropped claims above a configurable
  threshold;
- `predicate_mix_changed`: the candidate's predicate set differs from the
  prior predicate set;
- `provenance_anomaly`: candidate provenance cleanliness is below the run's
  expected threshold;
- `unchanged`: no review-triggering delta.

Queue tabs are a view over those tags:

- Needs review;
- Zeroed;
- Count changed;
- Predicate mix changed;
- High drops;
- Provenance;
- All.

Zeroed segments, missing-data states, malformed-data states, count changes,
predicate-mix changes, provenance anomalies, and high-drop segments are always
manual-review items. V1 does not provide acceptance-like batch decisions.
If batching ships at all, it is limited to "exclude unchanged items from this
review" and only for records with complete data, no risk tags, no count delta,
no predicate delta, no provenance warning, and no prior review conflict. Batch
actions require a preview listing included segment IDs and excluded IDs by
reason.

### Screen design

The primary screen is one segment at a time. It starts with a plain-language
change-summary block that answers:

- what changed;
- whether data is complete, redacted, missing, or malformed;
- the highest risk reason;
- what action is required next.

The rest of the page shows:

- a progress header: current queue, reviewed count, remaining count, unresolved
  blocker count, and promotion-readiness state;
- a risk-chip row: zeroed, count delta, predicate delta, drop count, provenance
  status, prompt version;
- source metadata and segment identifiers;
- a compact evidence/segment excerpt panel, with explicit "show more" controls
  and a visible privacy note that the text is local-only and not exported by
  default;
- prior claims as structured rows: subject, predicate, object, confidence, and
  stability class when known;
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

`exclude_from_review` counts as an operator action but does not make a risky or
missing-data item disappear from promotion-readiness accounting; the summary
shows excluded items separately from accepted items.

Promotion readiness is derived and deliberately weaker than promotion. States:

- `blocked`: at least one blocking risk remains, or required data is missing;
- `review_incomplete`: reviewable items remain undecided;
- `ready_for_owner_decision`: all configured review obligations are complete;
- `promoted_by_recorded_decision`: the operator recorded a run-level promotion
  decision in scratch state;
- `not_promoted_by_recorded_decision`: the operator recorded a run-level
  rejection in scratch state.

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

The verdict buttons and shortcut overlay use plain language. The interface does
not use internal labels like "zeroed segment" as the only explanation; it shows
the concrete change: "prior v8 had 3 claims; candidate v9 emitted 0."

### Routes

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

Mutating routes (`POST /segments/{segment_id}/decision` and
`POST /run-decision`) use RFC 0027's browser-tab defense: an Origin allowlist
over the current `http://127.0.0.1:<port>` and `http://localhost:<port>`, plus
`Sec-Fetch-Site: same-origin` enforcement when the header is present. Mismatch
returns 403.

Every route that can render text from private source data enforces a hard-coded
Tier 1 ceiling in v1. Higher-tier rendering is reserved for a follow-on RFC;
there is no v1 CLI flag, env var, or existing-scratch-artifact bypass.

### CLI commands

Add:

```text
engram phase3 bench-review serve
engram phase3 bench-review export --review-db PATH --output docs/reviews/<file>.md
engram phase3 bench-review status
```

`serve` starts the workbench. `status` prints counts from the scratch review
database without starting a server. `export` writes a redacted Markdown summary
to a caller-supplied tracked path under `docs/reviews/`. V1 has no
`--allow-outside-reviews` flag and no web export route. The export command
resolves the output path before writing and refuses absolute paths outside the
repository, `..` traversal, symlink escape, home-directory paths, and
overwriting an existing file unless an explicit `--overwrite` flag is provided.

The export contains:

- run ID, slice path basename, benchmark timestamp, prompt versions;
- candidate segment record basename and prior extraction identity;
- aggregate reviewed/unreviewed counts;
- count of decisions by verdict;
- segment IDs grouped by verdict;
- run-level promotion decision, if recorded;
- no notes, segment text, claim text, private values, prompts, or completions.

### Relationship to RFC 0027

RFC 0027 already established the preferred local web pattern for Engram:
FastAPI, Jinja2, htmx, loopback-only, no JS build pipeline, and route-level
privacy checks. RFC 0029 should reuse that pattern rather than introduce a
parallel frontend stack.

The bench-review package should not import interview-specific transition or
gold-label storage code. Shared web helpers may move to a small common module
only for narrowly repeated web substrate:

- loopback host validation;
- Origin allowlist and `Sec-Fetch-Site` check;
- vendored htmx static serving;
- package-local template/static setup;
- Tier 1 render ceiling helpers.

If extracted, the likely home is `src/engram/web/`. The extraction must be
small, directly tested, and must not import interview or bench-review domain
logic.

## Privacy and Security

The workbench inherits Engram's core local-first requirement. All user data
stays on the machine unless explicitly requested by the user.

Required constraints:

- default bind is `127.0.0.1`;
- non-loopback bind is refused in v1 with exit 8 and no escape flag;
- Origin allowlist and `Sec-Fetch-Site` checks reject unsafe cross-origin POSTs;
- no CDN, telemetry, analytics, remote model call, hosted storage, or browser
  asset fetch;
- htmx is vendored at `src/engram/bench_review/static/htmx.min.js` and shipped
  via package data;
- review SQLite and JSONL files live under `.scratch/` by default;
- tracked exports are CLI-only and redacted by default;
- the export command must not include raw segment text, claim text, note text,
  prompts, completions, private values, or home-directory absolute paths.

The UI may display private text because it is a local operator tool. That does
not make private text eligible for tracked docs.

## Implementation Plan

1. Add artifact loaders and classifiers for benchmark slices, candidate run
   artifacts, required segment records, prior extraction rows, data-availability
   states, and risk tags.
2. Add scratch review-state storage with SQLite and JSONL recovery export.
3. Add the FastAPI/htmx web app and package-local templates/static assets.
4. Add CLI commands under `engram phase3 bench-review`.
5. Add redacted export and status commands.
6. Add focused tests.

Implementation should prefer small modules:

- `src/engram/bench_review/artifacts.py`;
- `src/engram/bench_review/classify.py`;
- `src/engram/bench_review/storage.py`;
- `src/engram/bench_review/web.py`;
- `src/engram/bench_review/cli.py`.

## Tests and Acceptance Criteria

Acceptance requires:

- loader tests for slice/run artifacts, required segment records,
  metadata-only fallback, malformed benchmark data, and ambiguous prior
  extraction identity rejection;
- classifier tests for zeroed, count-changed, predicate-mix, high-drop, and
  unchanged cases;
- storage tests proving decisions are idempotently upserted and review state
  stores no segment or claim text columns, plus tests for run-level decisions
  and resumable UI state;
- FastAPI `TestClient` tests for landing, queue, segment page, decision POST,
  visible saved decisions, origin rejection, `Sec-Fetch-Site` rejection,
  excerpt privacy-tier rejection, and no-CDN rendered pages;
- UI contract tests for data-availability blocking, promotion-readiness
  blockers, batch-preview exclusions if batching ships, deterministic resume,
  shortcut focus safety, and visible post-decision confirmation;
- export tests proving tracked summaries omit raw segment text, claim text,
  note text, prompts, completions, private values, and home-directory absolute
  paths by default;
- export path tests for absolute paths, `..` traversal, symlink escape,
  home-directory paths, and overwrite refusal;
- CLI tests for `serve` argument validation, non-loopback refusal, `status`,
  and `export`;
- package-data tests proving `src/engram/bench_review/static/htmx.min.js`
  ships from the wheel and no rendered page references an external asset URL;
- no live LLM calls and no network calls in unit tests.

Manual acceptance for the first implementation should include reviewing the
RFC 0028 100-segment bench's zeroed-segment set in the UI and producing a
redacted summary under
`docs/reviews/rfc0028-predicate-intent-implementation/`.

## Open Questions

1. Should review state remain SQLite-only after v1, or should accepted
   benchmark-review decisions eventually become an append-only Postgres table?
   V1 chooses SQLite to avoid polluting canonical project data with
   run-specific operator notes.
2. Should candidate claim text be emitted by the benchmark harness for UI
   display? If so, it should remain scratch-only and should not be included in
   tracked reports by default.
3. Should the first implementation create a read-only Postgres role for prior
   extraction lookups, or is application-level read-only discipline enough for
   v1?
4. Should future Phase 4 benchmark artifacts get a `phase4 bench-review` alias,
   or should this command remain extraction-artifact-specific under Phase 3?

## Promotion Path

If accepted, this RFC should be promoted to a concrete spec before code
implementation, mirroring RFC 0027. The spec should freeze the route contract,
review-state schema, privacy/export rules, and CLI surface. Code implementation
can then proceed through the same multi-agent implementation review process
used for RFC 0028.
