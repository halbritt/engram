# RFC 0029 Bench Triage Workbench Review - claude
author: operator [self-declared: rfc0029-design-review-claude]

Status: review
Date: 2026-05-13
RFC refs: RFC-0029
Decision refs: D020, D074
Phase refs: PHASE-0003-FOLLOWON, PHASE-0004

## Overall assessment

The RFC sits in a strong place. It picks the right operator problem (one
segment on screen, queued by risk, resumable, exportable without leaking),
defends the local-first posture with concrete mechanisms rather than aspiration
(loopback bind with exit 8, vendored htmx, hard-coded Tier 1 ceiling with
max-carry on multi-message excerpts, Origin allowlist plus
`Sec-Fetch-Site: same-origin`, read-only Postgres role + read-only transactions
fail-closed, scratch SQLite for review state), and explicitly opts out of
inheriting RFC 0027's later `ENGRAM_INTERVIEW_ALLOWED_ORIGINS` extension (D081)
so the workbench cannot drift onto a network without a fresh RFC paired with
auth. The D074 boundary is stated cleanly: scratch review decisions are
evidence only, not Striatum gate state, and not consumed by extraction,
consolidation, interview, entity review, or serving.

Queue classifications map cleanly onto the signals from the RFC 0028
100-segment bench (prior-positive/candidate-zero, count delta, predicate
delta, drop reasons, schema/parse, provenance). The route surface stays
narrow (seven routes, no general dashboard, no web export). The CLI surface
extends the `engram phase3 <verb> ...` precedent set by D080. The export
contract is the tightest in the codebase to date — operator-chosen artifact
filenames are sanitized to slugs/IDs, path resolution refuses absolute / `..` /
symlink-escape / home-dir / overwrite-without-flag, and notes are
permanently scratch-only.

Findings below are polish items, not architectural blockers.

## Findings

### F001 - Reviewer identity may leak into tracked exports
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:187 (`reviewer TEXT NOT NULL`),
        docs/rfcs/0029-bench-triage-workbench.md:512-539 (export contract)
Rationale: The `review_sessions` schema requires a `reviewer TEXT NOT NULL`
column, and the RFC does not say where that value comes from (CLI flag, env
var, OS username default). The export contract enumerates what the redacted
summary *contains* (run identity, version triples, sanitized slugs, counts,
segment IDs by decision) and what it *does not contain* (notes, segment text,
claim text, prompts, completions, private values, home-dir paths, model file
paths). The reviewer field is neither named on the include list nor on the
exclude list. If the implementation defaults `reviewer` to `os.getlogin()` or
`$USER`, an OS username will land in tracked `docs/reviews/` exports without
the operator ever being prompted, and the export-redaction tests as listed
will not catch it. Either the spec should pin `reviewer` to a value
explicitly named by the operator (CLI flag, no default-to-username), and the
export contract should explicitly exclude the reviewer string from tracked
summaries, or the spec should document that the field is sanitized through a
stable token (e.g., `operator`) before export and add an explicit test.

### F002 - `prior_model_version` strings can carry local filesystem paths
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:482-498 (CLI surface),
        docs/rfcs/0029-bench-triage-workbench.md:515-539 (export contract),
        docs/reviews/rfc0028-predicate-intent-implementation/REEXTRACTION_BENCH_100.md:46-55
Rationale: The export contract lists "prompt versions, model versions, and
request profile versions" as included fields, and "home-directory absolute
paths" and "local model filesystem paths" as excluded. The two collide.
REEXTRACTION_BENCH_100.md records the live model identifier as
`/home/halbritt/models/Qwen_Qwen3.6-35B-A3B-IQ4_XS.gguf` — a home-dir
absolute path that doubles as the model_version value. The operator passes
`--prior-model-version <model-version>` as a CLI flag, so if they paste the
value off `run.json` (where the harness writes the path) it lands in the
SQLite session row and then in the redacted export verbatim. The spec should
either (a) require the operator to provide a sanitized model-version slug at
session start and refuse anything that resolves to an existing local file or
contains `$HOME`, or (b) commit the export layer to a normalization step
that replaces filesystem-path-shaped model_version values with a stable
basename or content hash, and add a test that fails when a model_version
contains `/home/` or any absolute path.

### F003 - `do_not_promote` is unreachable when a hard blocker exists
Severity: major
Source: docs/rfcs/0029-bench-triage-workbench.md:380-397 (readiness matrix),
        docs/rfcs/0029-bench-triage-workbench.md:463-465 (`/run-decision` 409)
Rationale: `POST /run-decision` returns 409 unless readiness is exactly
`ready_for_owner_decision`, and the readiness rule requires zero hard
blockers, zero flagged regressions, zero `needs_followup` rows, and zero
undecided review obligations. The matrix marks `candidate_missing`,
`candidate_malformed`, `prior_missing`, `prior_ambiguous`,
`schema_or_parse_anomaly`, and `provenance_anomaly` as "hard blocker until
fixed by a new artifact". When a candidate run is clearly broken in those
ways, the operator needs to record `do_not_promote` precisely *because* the
artifact is bad — but the route refuses, because the readiness gate cannot be
satisfied without a re-run that produces a different artifact. The
asymmetry is wrong: promotion should be gated on readiness, but a scratch
rejection should be reachable from any state where a candidate exists at all.
Either allow `decision=do_not_promote` from `blocked` and
`review_incomplete`, or add a `blocked_recommend_reject` terminal state to
the readiness vocabulary and tie 409 to promotion attempts only.

### F004 - `queue_fingerprint` is load-bearing but undefined
Severity: minor
Source: docs/rfcs/0029-bench-triage-workbench.md:189 (`queue_fingerprint TEXT NOT NULL`)
Rationale: The schema requires a non-null `queue_fingerprint` per
`review_sessions`, but the RFC never says what it hashes over (the set of
segment IDs? the segment IDs plus classifier tags? the SHA of `run.json` +
`segments.jsonl`? the slice manifest hash?). Implementations are free to pick
any of those, and two implementations that disagree will produce false-
positive "stale session" responses on resume. The RFC also never describes
what the server does when the live artifact's fingerprint diverges from the
persisted one (refuse to start? prompt the operator? replay decisions onto
the new queue?). The spec should pin the fingerprint inputs and define the
divergence behavior — the natural choice is "fail closed on divergence with
an explicit reload command", since silently replaying decisions onto a new
classifier output would change what `accept_candidate_change` means after
the fact.

### F005 - `predicate_mix_changed` leaves set-vs-multiset ambiguous
Severity: minor
Source: docs/rfcs/0029-bench-triage-workbench.md:301-302
Rationale: "The candidate predicate set differs from the prior predicate set"
defines the classification as set-membership only. A transition from
`{has_name×3, feels×1}` to `{has_name×1, feels×3}` preserves the set while
changing the per-predicate distribution — exactly the kind of semantic shift
a re-extraction prompt change can produce, and exactly what
REEXTRACTION_BENCH_100.md's per-predicate counts capture at the slice level
(`uses_tool` 149, `has_name` 55, `wants_to` 33, ...). The spec should say
whether the comparison is on the distinct set or the multiset / distribution,
and the classifier tests should pin both directions. Default to multiset —
losing distinct-set-membership cases would be a real regression in queue
coverage.

### F006 - `--review-db` is referenced but not in the canonical `serve` example
Severity: minor
Source: docs/rfcs/0029-bench-triage-workbench.md:116-126 (example),
        docs/rfcs/0029-bench-triage-workbench.md:156-158 (default path),
        docs/rfcs/0029-bench-triage-workbench.md:486-491 (`status`/`export` flags)
Rationale: The example `serve` invocation lists `--slice`, `--run`,
`--segments`, the three prior-identity flags, `--host`, and `--port`, with
no mention of `--review-db`. The default review-DB path is
`.scratch/benchmarks/extraction-review/<run-id>/review.sqlite3`, but `status`
and `export` are documented as `--review-db PATH` consumers. Two surfaces
disagree: an operator reading only the example will not learn that the
review-DB path is a tunable, and an operator reading only `status`/`export`
will not see how `serve` derives its default. The spec should either include
`[--review-db PATH]` in the `serve` example as the documented override or
add a one-line note pointing at the default path. Cheap fix; meaningful for
the operator who runs `serve` once and then `status` two days later.

### F007 - `high_drop_count` threshold and units unspecified
Severity: minor
Source: docs/rfcs/0029-bench-triage-workbench.md:297-298 (classifier),
        docs/rfcs/0029-bench-triage-workbench.md:610-612 (impl plan)
Rationale: `high_drop_count` is "the candidate dropped claims above a
configurable threshold", but the RFC names no default, no env-var name, and
no unit (per-segment drop count? per-segment drop *rate*? per-slice
aggregate?). REEXTRACTION_BENCH_100 shows a slice-aggregate dropped rate of
0.1503 (84/559) with all drops from `trigger_violation` — a per-segment
absolute count would behave very differently than a per-segment rate against
that distribution. The spec should pin the metric, commit a sensible default
that produces a usable queue against the RFC 0028 numbers, and name an
`ENGRAM_BENCH_REVIEW_*` env var per the Engram Python coding standard
(RFC 0012 § tunables-at-module-top).

### F008 - "Limited" entry in the readiness matrix is undefined as an outcome
Severity: minor
Source: docs/rfcs/0029-bench-triage-workbench.md:382-393 (matrix row),
        docs/rfcs/0029-bench-triage-workbench.md:695-696 (Open Q 5)
Rationale: The matrix row for
`candidate_redacted + accept_candidate_change` reads "limited" under "Clears
review obligation?" and "only for aggregate/count-only deltas; semantic
predicate/object changes remain blocked until private-detail or source
context is available" under "Clears promotion blocker?". "Limited" is not
defined elsewhere; the UI cannot render two different post-decision
confirmations from a single decision value, and the SQLite `decision` check
constraint has four allowed values, none of which are "limited". Either the
matrix should resolve to a yes/no per row (probably "yes for the review
obligation, no for the promotion blocker on semantic deltas"), or the
decision vocabulary should grow an `accept_aggregate_only` variant and the
spec should pin which deltas qualify. Open Question 5 acknowledges the
ambiguity; the resolution should land before the implementation spec freezes.

### F009 - Provisioning of the read-only Postgres role is left to "later"
Severity: minor
Source: docs/rfcs/0029-bench-triage-workbench.md:163-167 (fail-closed
        requirement), docs/rfcs/0029-bench-triage-workbench.md:687-691 (Open Q 3)
Rationale: The RFC requires that production Postgres access "should enforce
[read-only] mechanically by connecting with a read-only role when available
and by starting read-only transactions (`SET TRANSACTION READ ONLY`) for
every route/loader that touches production tables. If either guard cannot be
applied, the server should fail closed rather than silently downgrading to
application-level discipline." Open Question 3 then defers role provisioning
to either migrations, setup docs, or a local operator command. That gap is
where the fail-closed semantics will be tested in practice: a fresh install
won't have the read-only role, the server will fail closed on first
`serve`, and the operator will be left to discover the role-creation
recipe. Pick the provisioning path in the implementation spec — preferably a
new migration that creates a stable role name documented in the howto, since
manual setup-doc steps tend to rot out of sync with the code that depends
on them.

### F010 - Notes field is scratch-only, but the storage tests don't pin it
Severity: nit
Source: docs/rfcs/0029-bench-triage-workbench.md:246-248 (notes scope),
        docs/rfcs/0029-bench-triage-workbench.md:639-643 (storage tests),
        docs/rfcs/0029-bench-triage-workbench.md:657-664 (export tests)
Rationale: The RFC commits "Notes are private scratch content by default and
are not included in tracked exports in v1" and the export-exclusion list
names "note text". The export tests include "tracked summaries omit raw
segment text, claim text, note text, prompts, completions, private values,
home-directory absolute paths, and local model filesystem paths by
default" — good. The storage tests list "decisions are idempotently upserted
and review state stores no segment text or claim text columns" but do not
explicitly require the note column to be present *and* the export pathway
to never read from it. Add a test that the export path reads only the
sanctioned columns from `segment_reviews` (i.e., not the note column), so a
later refactor that wires the export to the full row cannot silently
regress the privacy contract.

## Open questions

1. Should the export include a generated-at timestamp and a content hash of
   the underlying `run.json` + `segments.jsonl` so a reviewer reading the
   summary later can verify which run the decisions were rendered against?
   Worth considering — without it, two re-runs that both land at
   `ready_for_owner_decision` produce visually similar tracked summaries.
2. The shared web substrate proposal at `src/engram/web/` (loopback host
   validation, Origin allowlist, vendored htmx, Tier 1 helpers) — should
   that extraction land in the same spec as the workbench, or as a small
   pre-cursor RFC so the bench-review and interview-web surfaces both
   migrate to it on the same cut? The RFC says "if extracted" leaving the
   sequencing implicit; pinning the order would reduce the risk that two
   parallel implementations diverge.
3. `exclude_from_review` rows on risky / missing / malformed / ambiguous
   states "remain an excluded blocker" per the matrix. Should the summary
   report distinguish excluded-with-blocker rows from
   excluded-because-unchanged rows, or are both collapsed into "excluded"?
   The current export contract says "counts by data-availability state, risk
   tag, and decision" which probably suffices, but it would be worth
   confirming the cross-product is preserved (per-availability × per-decision
   counts) so a downstream owner can see "5 excluded-but-still-blocking"
   distinctly from "12 excluded-unchanged".

verdict: accept_with_findings
