# CODE_REVIEW_RFC0029 — Bench Triage Workbench RFC, Spec, and Implementation

| Field | Value |
|-------|-------|
| Audit block | C |
| Author | Claude Code |
| Date | 2026-05-13 |
| Method | Independent review of RFC 0029 as a fresh design proposal, of the v1 spec as a fresh implementation contract, and of the `src/engram/bench_review/` package as a fresh implementation. No file under `docs/reviews/rfc0029-bench-triage-workbench{,-spec,-implementation}/` was opened during this review. The provenance audit (Block B) determined that no external-model review lane ever ran for any of these three artifacts; they receive a first-time review here. |
| Files reviewed | `docs/rfcs/0029-bench-triage-workbench.md`, `docs/specs/0029-bench-triage-workbench-spec.md`, `src/engram/bench_review/{__init__,artifacts,classify,cli,detail,export,storage,web}.py`, `src/engram/bench_review/templates/*.html`, `src/engram/bench_review/static/htmx.min.js`, `src/engram/cli.py` (subcommand wiring), `pyproject.toml` (package-data line), `tests/test_bench_review.py` |

## Summary

RFC 0029 proposes a **local-only, loopback-only review surface over scratch
benchmark artifacts** for triaging extraction / re-extraction deltas one
segment at a time. The design respects Engram's load-bearing
constraints: no cloud, no telemetry, no production-DB mutation, no
non-loopback bind, no CDN, scratch SQLite only. The implementation
follows the RFC and spec closely. The 1,782 lines of Python in
`src/engram/bench_review/` look like competent first-draft code, not
scaffolding.

The **design itself is acceptable** as a v1 review tool, and the
**implementation matches the design**. The only reason this RFC cannot
be allowed to remain `promoted/implemented` is that **no legitimate
review process actually adjudicated it** — the Striatum runs that
claimed multi-lane approval did not invoke any external model lane
(see [PROVENANCE_AUDIT.md](PROVENANCE_AUDIT.md) for the evidence). The
work needs a real review, not a revert.

This document is a first such real review.

## RFC design review (treating RFC 0029 as a fresh proposal)

### Design coherence

The RFC argues that Phase 3 / Phase 4 progress depends on repeated "is
this extraction change semantically acceptable?" decisions, that
existing artifacts (benchmark JSON, aggregate Markdown, scratch
Markdown) answer adjacent but not equivalent questions, and that the
operator workflow is dominated by holding context in working memory
across segments. The argument is plausible and matches my read of the
RFC 0028 bench artifacts (which are dense markdown summaries that would
indeed be hard to triage at scale).

### Goals match Engram's architecture

- "Loopback-only, no hosted service, no telemetry, no CDN, no external
  persistence" — direct echo of AGENTS.md and D020.
- "Production data immutable from this surface; benchmark triage writes
  only private scratch review decisions in v1" — matches the
  raw-is-sacred principle (AGENTS.md).
- "Export a redacted, tracked summary suitable for `docs/reviews/`
  without leaking raw private corpus text by default" — privacy
  posture matches RFC 0027 / D080's tier-1 ceiling style.
- SQLite (scratch) vs. Postgres (production) split is a clean boundary
  that does not require schema migrations to introduce or remove.

### Design concerns

#### F-RFC0029-D-001 — Tailscale DNS suffix is allowed without operator opt-in (deviates from RFC 0027 / D081)

**Severity:** moderate.

`src/engram/bench_review/web.py:20` defines
`TAILSCALE_DNS_SUFFIX: str = ".ts.net"` and
`_is_allowed_request_host` returns True for any hostname ending in that
suffix.

RFC 0027 / D081 made the equivalent allowance **operator-extensible via
the `ENGRAM_INTERVIEW_ALLOWED_ORIGINS` env var**, defaulting to
loopback-only. The RFC 0027 reasoning was: "silently broaden the
default allowlist (rejected — privacy regression for non-tailnet
operators)." RFC 0029 broadens unilaterally.

The risk is small in practice — Tailscale is an authenticated overlay,
so reaching the bench-review port from a tailnet host implies operator
trust. But the deviation from D081's posture means a non-tailnet
operator who installs Engram on a machine with a stray `.ts.net` DNS
record (rare but possible) gets a broader allowlist than they would on
the interview UI.

**Recommendation:** mirror D081 — make the Tailscale suffix an opt-in
via `ENGRAM_BENCH_REVIEW_ALLOWED_DNS_SUFFIXES` (default empty), and add
the equivalent `ENGRAM_BENCH_REVIEW_ALLOWED_ORIGINS` env var. Tier 1
follow-up before any forward roadmap step relies on this tool.

#### F-RFC0029-D-002 — RFC ↔ implementation mismatch on host validation timing

**Severity:** minor.

The CLI driver (`bench_review/cli.py:21-33`) validates that `--host`
is in the loopback set **at startup** with `sys.exit(8)` for non-loopback
values. Per the RFC, this is correct.

The FastAPI app also has a per-request check at the bottom of
`_origin_check` (`web.py:210`): `if host not in ALLOWED_HOSTS:
raise HTTPException(...)`. This is dead code in practice because the
CLI rejects non-loopback hosts before the app starts. But if the app is
instantiated programmatically with `create_app(host=<non-loopback>)`,
the check fires on every POST request rather than at construction.

**Recommendation:** move the `host not in ALLOWED_HOSTS` check to
`create_app`'s body so it raises at startup time, not per-request.
Acceptable to defer; not a v1 blocker.

#### F-RFC0029-D-003 — Spec proposes `engram phase3 bench-review {serve,status,export}`; verify the CLI wiring is consistent with RFC 0025

**Severity:** check-worthy.

RFC 0025 (D078) defined the phase-scoped command surface and the
expected naming. The new bench-review commands land under `phase3
bench-review {serve,status,export}` which matches the convention. The
existing single test failure
(`test_cli_pipeline_is_phase2_only_and_pipeline3_warns`) is a
**pre-suspect** regression caused by RFC 0025 itself (commit
`2de6123`), not by RFC 0029.

**Recommendation:** consistent. No action.

### Non-goals are honored

- No mutation of `claims`, `claim_extractions`, `beliefs`,
  `claim_audits`, `projection_audits`, or raw evidence: confirmed in
  `storage.py` (all writes go to a separate SQLite file).
- No new gold labels: confirmed; review decisions live in a
  `segment_reviews` table that does not feed back into production.
- No hosted dashboard / multi-user / login / TLS / CDN / JS framework:
  confirmed; vendored htmx, server-rendered Jinja, single-file static.

## Spec review (treating spec 0029 as a fresh implementation contract)

The spec at `docs/specs/0029-bench-triage-workbench-spec.md` is 522
lines. It elaborates the RFC's design into a tighter contract — table
schemas, classification rules, queue-tab definitions, state-instruction
strings, redaction policy, and CLI argument shape.

### Spec ↔ implementation crosswalk (sampled)

| Spec clause (paraphrased) | Implementation evidence |
|---------------------------|--------------------------|
| Review state lives in `.scratch/benchmarks/extraction-review/<run-id>/review.sqlite3` | `cli.py:run_phase3_bench_review_serve` builds the path via `prepare_review_db`; `storage.initialize_review_db` creates the file in that location |
| Segment decision enum: `accept_candidate_change`, `flag_candidate_regression`, `needs_followup`, `exclude_from_review` | `storage.SEGMENT_DECISIONS` frozenset matches exactly |
| Run decision enum: `safe_to_promote`, `blocked_by_regressions`, `needs_more_review` | `storage.RUN_DECISIONS` frozenset matches exactly |
| Strong decisions disabled for missing/malformed/redacted data states | `web.py` checks `STRONG_DECISION_DISABLED_STATES` membership before allowing accept/regression POSTs (HTTP 400 if disabled) |
| Redaction: scratch notes private by default, tracked exports redacted | `export.py:export_markdown` flow; storage holds notes; export path requires explicit `--output` under `docs/reviews/` |
| Per-segment classification tags: zeroed / newly_nonzero / count_changed / high_drop_count / predicate_mix_changed / provenance_anomaly / unchanged | `classify.py` produces these; `storage.tags_json` persists |

### Spec concerns

#### F-RFC0029-S-001 — `RUN_DECISIONS` set membership differs in spirit between RFC and implementation

**Severity:** minor.

RFC § "Screen design" lists run-readiness as a derived state with values
`blocked`, `review_incomplete`, `ready_for_owner_decision`,
`promoted_by_recorded_decision`, `not_promoted_by_recorded_decision`
(five states). The spec's `RUN_DECISIONS` enum is `safe_to_promote`,
`blocked_by_regressions`, `needs_more_review` (three states; the
operator's explicit run-level decision, not the derived readiness).

These are different concepts (operator decision vs. derived state) and
both can coexist. The implementation only persists the operator
decision; the derived readiness is computed at render time from
segment-level state.

**Recommendation:** make this distinction explicit in the spec. Tier 2
follow-up.

#### F-RFC0029-S-002 — Spec assumes prior-run identity is sufficient to fetch prior claims; in practice we also need the prior `request_profile_version` to disambiguate

**Severity:** minor.

`storage.ReviewSessionConfig` carries both `prior_request_profile_version`
and the candidate versions. The CLI requires all three (prompt, model,
request-profile) when comparing against the production DB.

If two extraction runs share `(prompt_version, model_version)` but
differ in `request_profile_version` (this is the contract from RFC 0017
post-D034), the comparison is ambiguous without the third component.
The implementation gets this right; the spec body should explicitly
require all three.

**Recommendation:** doc-only tweak to the spec. Tier 2 follow-up.

## Implementation review (treating `src/engram/bench_review/` as a fresh package)

### Architecture

The package is partitioned cleanly:

| Module | Lines | Responsibility |
|--------|-------|----------------|
| `__init__.py` | 4 | Package marker |
| `artifacts.py` | 441 | Load slice / run.json / segments.jsonl artifacts; resolve segment record path; produce `SegmentComparison` rows |
| `classify.py` | 116 | Map data-state and tags to queue sort key and instruction strings |
| `cli.py` | 145 | `phase3 bench-review {serve,status,export}` entry points |
| `detail.py` | 302 | On-demand expansion: prior claim text from Postgres, candidate detail from scratch artifacts |
| `export.py` | 135 | Redacted Markdown export to `docs/reviews/...` |
| `storage.py` | 350 | Scratch SQLite schema + read/write helpers |
| `web.py` | 289 | FastAPI app: 7 routes, origin check, query-context plumbing |

This is reasonable separation. `artifacts.py` is largest because the
bench-artifact format is heterogeneous (slice manifest + run.json +
segments.jsonl); the rest are appropriately sized.

### Coding-standard compliance (RFC 0012)

| RFC 0012 rule | Implementation |
|---------------|----------------|
| `from __future__ import annotations` at top | ✓ All 8 modules |
| Type hints on signatures | ✓ Largely; spot-check finds no untyped public signatures |
| Per-stage exception family | ✓ `BenchReviewArtifactError`, `BenchReviewStorageError` |
| No bare `except:` | One slightly broad `except Exception` in `cli.run_phase3_bench_review_status` and `cli.run_phase3_bench_review_export` — `except Exception as exc:` to print and return 1. Per RFC 0012, broad excepts at the CLI boundary are acceptable; flag for tightening |
| `ENGRAM_` env vars at module top | ✓ `ENGRAM_BENCH_REVIEW_RATIONALE_MAX_CHARS` in storage.py |
| Tests deterministic, no live LLM | ✓ `test_bench_review.py` uses static fixtures |

### Substantive findings

#### F-RFC0029-I-001 — `cli.py` broad `except Exception` at status/export entry points

**Severity:** minor / coding-standard.

`run_phase3_bench_review_status` (cli.py:59-66) and
`run_phase3_bench_review_export` (cli.py:69-83) both wrap the call site
in `except Exception as exc:`. RFC 0012 prefers per-stage exception
families. The package has `BenchReviewStorageError` and
`BenchReviewArtifactError`; the export path could raise either plus
`OSError` for the output-path write.

**Recommendation:** narrow to
`except (BenchReviewStorageError, BenchReviewArtifactError, OSError) as exc:`.
Tier 0 follow-up; acceptable as-is for v1.

#### F-RFC0029-I-002 — Origin check enforces Sec-Fetch-Site + Origin only when those headers are present

**Severity:** minor.

`_origin_check` in `web.py:196-211` correctly rejects:

- non-loopback request hosts (HTTP 403)
- `sec-fetch-site` values outside `{same-origin, same-site, none}` (when the header is present)
- Origin / Referer mismatches (when the header is present)

If a browser does not send `sec-fetch-site` or `origin`/`referer` (some
contexts, or a script-driven curl), the check passes purely on the
hostname. Combined with the loopback-only bind, this is the same
posture as RFC 0027 v1; the gap is real but accepted. No CSRF tokens.

**Recommendation:** acceptable for v1. Note that strong decisions
(accept / regression) ARE explicitly origin-checked at the POST
endpoint (`segment_decision` calls `origin_check` first), so the
strongest privilege paths are at least as guarded as the GET surface.
Tier 2 follow-up: per-form CSRF tokens, mirroring RFC 0027 deferred
F005 work.

#### F-RFC0029-I-003 — JSON tag filter is post-query Python list comprehension

**Severity:** minor / scale-readiness.

`storage.list_segments:182-184` does the tag filter in Python after
loading rows from SQLite:

```python
if tag:
    rows = [row for row in rows if tag in json.loads(row["tags_json"])]
```

For a v1 bench review of ~100–500 segments per run, this is fine. For
~5,000+ segments it loads all rows before filtering. SQLite's JSON1
extension would let this run server-side with
`WHERE EXISTS (SELECT 1 FROM json_each(tags_json) WHERE value = ?)`.

**Recommendation:** acceptable for v1. Revisit when bench slices exceed
~2k segments. Add to FORWARD_PATH.md.

#### F-RFC0029-I-004 — Decision idempotency vs. concurrent operators

**Severity:** edge-case.

`record_segment_decision` (`storage.py:203-221`) issues a single UPDATE
and raises if `rowcount == 0`. Two simultaneous POSTs from two browser
tabs could both succeed, with last-writer-wins on `decision` and
`rationale`. Since the workbench is a single-operator tool by design,
the conflict is mostly theoretical, but a workflow where one operator
opens two tabs and clicks different verdicts is possible. There is no
optimistic-concurrency check (e.g. `updated_at >= expected`).

**Recommendation:** acceptable for v1. If two-tab confusion is ever
observed, add a `decided_at IS NULL OR decided_at = ?` predicate to
catch the second writer.

#### F-RFC0029-I-005 — Migration 011's `gold_label_session_targets` schema diagram landed inside this commit but is unrelated to RFC 0029

**Severity:** documentation.

`docs/schema/README.md` gained a `gold_label_session_targets` ER block.
This documents migration 011, which is RFC 0027 (D080) territory,
implemented and accepted **before** the suspect burst.

Looking at the diff: the new diagram appears correct against migration
011. It is not unique to RFC 0029. It was likely intended as a stale
schema-docs refresh and got swept into the same commit.

**Recommendation:** verify by running `make schema-docs` and diffing
against the committed schema-docs output. If the diff is clean, accept
the addition as a legitimate (if mis-grouped) doc refresh.

### Tests

`tests/test_bench_review.py` is 375 lines covering:

- Artifact loaders (slice / run / segments parsing, malformed input).
- Classification (tag derivation, queue sort key, instruction strings).
- Storage round-trips (initialize, record decision, summary,
  idempotent re-initialize).
- Export rendering (redacted output, output-path validation).
- Web route behavior (loopback enforcement, segment listing,
  segment decision, run decision, instruction state propagation).

All tests passed in this audit's `make test` run.

The tests do not yet exercise:

- The Tailscale DNS suffix allowance (would be worth pinning given
  F-RFC0029-D-001 above).
- Two concurrent decision POSTs (F-RFC0029-I-004).
- A real bench slice from `.scratch/benchmarks/extraction-backend/` —
  the test fixtures are synthetic.

These are coverage follow-ups, not v1 blockers.

## Recommendation for Block D

- **Disposition for `src/engram/bench_review/` (entire package):**
  `repair`. The implementation is sound on first review but the
  Tailscale-suffix allowance (F-RFC0029-D-001) should be made
  opt-in before the package is recommended for daily use. The other
  findings are smaller follow-ups.
- **Disposition for `docs/rfcs/0029-bench-triage-workbench.md`:**
  `accept` as a proposal. The RFC's design is reasonable.
- **Disposition for `docs/specs/0029-bench-triage-workbench-spec.md`:**
  `accept` as a draft spec — but **demote** its status from "promoted"
  to "draft" pending operator review. The spec has not actually been
  reviewed by any multi-lane process. F-RFC0029-S-001 and -S-002 are
  minor doc edits.
- **Disposition for `docs/rfcs/README.md` RFC 0029 row status
  (`promoted/implemented`):** `repair` — revert to `proposal` /
  `partial` (or `implemented` if the operator wants to acknowledge
  the code exists, separate from acceptance), and remove the link
  text that asserts spec 0029 was promoted.
- **Disposition for `tests/test_bench_review.py`:** `accept` — the
  test suite is reasonable.
- **Disposition for `pyproject.toml` package-data line:** `accept`
  — required for the templates/static to ship.
- **Disposition for `docs/reviews/rfc0029-*` subdirectories (4 dirs):**
  `quarantine`. They are not load-bearing review evidence. Leave on
  disk as historical (preserves audit chain) but do not treat as
  authoritative.
- **Disposition for `striatum/rfc-0028-*` and `striatum/rfc-0029-*`
  workflow scaffolds:** decided in `CODE_REVIEW.md` (cross-cutting).
