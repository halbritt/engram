# RFC 0030 Public-Dataset Entity Grounding Review - gemini

author: reviewer-gemini-3.1-pro-preview-001

Status: review
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

Lens: operator workflow, grant-management UX, snapshot lifecycle, alignment
with the RFC 0027 interview surface and RFC 0028 entity-mismatch failure
taxonomy.

## Findings

### F001 - First-run path from `engram install` to first grounded extraction has no story
Severity: major
Source: § Promotion path; § D-A; § D-F

A new operator runs `engram install`, then `engram phase3 extract`.
Without grounding setup, extraction proceeds (silent downgrade per Q7).
But the operator who *wants* grounding has to:
1. Discover that grounding exists (no documented onramp).
2. Pick datasets (D-A is operator-facing).
3. Snapshot them (`engram grounding snapshot --dataset wikidata` —
   ~10 GB download, opaque time estimate).
4. Index them (separate step? same step? RFC ambiguous).
5. Grant them (`engram grants grant <role> <dataset>`).
6. Re-run extraction.

This is a six-step onramp before grounding works. The RFC does not
acknowledge it.

Suggested fix: spec should ship an `engram grounding onboarding` or
equivalent that walks the operator through these six steps in order,
with progress reporting on the slow ones (snapshot, index).

### F002 - Grant-revocation UX implications not addressed
Severity: major
Source: § D-F grant model; § Privacy and provenance (revocability)

The RFC commits to revocability but does not address what happens *to
existing claims* when a grant is revoked. Three behaviors are plausible:
- Existing grounded claims keep their resolutions (revocation is
  forward-only). Reasonable, matches RFC 0017's prompt-version
  immutability discipline.
- Existing grounded claims have their `entity_external_references`
  rows tombstoned. Compatible with append-only via a tombstone row.
- Existing grounded claims become invisible to interview UI. Worst —
  silent data hiding.

The RFC names only "revoking a grant stops future grounding." That's
fine, but the operator-visible behavior on already-grounded data
needs explicit answer.

Suggested fix: D-F (or a new § Revocation behavior) should commit to
the forward-only stance and document that operators wanting to remove
grounded resolutions must run re-extraction under the no-grant
configuration.

### F003 - Interview UI integration with candidate sets (D-C) unspecified
Severity: major
Source: § D-C output shape; references to RFC 0027

D-C recommends attaching the full candidate set with confidences and
deferring disambiguation to the interview UI. The interview UI
(RFC 0027 / D080) is where the operator answers true/false/unsure on
extracted claims. Adding candidate-set disambiguation to that surface
is non-trivial:
- The interview operator now has THREE choices: true/false/unsure on
  the claim, AND which-candidate is right (or "none").
- A claim with subject and object both ambiguous compounds candidate
  cardinality (5 × 5 = 25 candidate combinations).
- The current interview is designed for fast yes/no decisions; adding
  candidate selection slows it.

Suggested fix: spec must specify the interview-UI surface change. Two
acceptable options: (a) interview shows top-1 candidate and "other?"
collapse, surface the full set on demand; (b) candidate selection is a
separate review pass after primary verdict, not blocking it.

### F004 - Snapshot lifecycle alarm/notification behavior unspecified
Severity: major
Source: § D-E snapshot discipline; § D-A

Operator-curated snapshots will go stale. The RFC does not name the
alarm strategy:
- Does the system warn at extraction start that the active snapshot is
  >90 days old?
- Does it warn at interview time?
- Is staleness a property of the snapshot itself or of the operator's
  freshness preference?
- Wikidata changes daily; GeoNames monthly. The "stale" threshold is
  dataset-specific.

Suggested fix: D-E should specify a per-dataset staleness threshold
(default value + override) and the alarm channel (warning header on
every extraction summary; nothing on interview).

### F005 - "Silent downgrade" warning (Q7) is too quiet
Severity: minor
Source: § Open questions Q7

The recommended seed says "silent downgrade with a one-line warning per
run." A one-line warning in stdout is invisible during piped runs,
benchmark runs, and cron-driven extraction. The RFC needs to commit to
where the warning surfaces — extraction summary header, benchmark JSON
field, both.

Suggested fix: pin the warning channel to the run-summary JSON (a new
field like `grounding_status: {"active": false, "reason": "no grants"}`)
so any downstream tool can detect grounded vs. ungrounded results.

### F006 - Dataset names are not aligned with operator mental models
Severity: minor
Source: § D-A starting datasets

"Wikidata" and "GeoNames" are precise but jargon. The CLI should accept
operator-friendly aliases (`engram grants grant extractor places` should
do something sensible, even if just "GeoNames + Wikidata place subset").

Suggested fix: spec should pin a small alias table (`places →
geonames+wikidata-places`, `companies → wikidata-companies`).

### F007 - The interaction with RFC 0028 subject_kind_hint is friction-prone
Severity: minor
Source: § Open questions Q2

Both RFCs add entity-type signal. From the operator's view, an
"organization" hint from RFC 0028 plus a Wikidata candidate of class
`organization` plus an interview verdict of "true person" could
contradict each other. The interview UI's verdict semantics already
have to absorb predicate-intent feedback (RFC 0028); adding grounding
candidate disagreement creates a third axis.

Suggested fix: spec should pin precedence rules: operator interview
verdict overrides everything; subject_kind_hint pre-filters candidates;
candidates are presented in confidence order with the kind-filter
applied.

### F008 - The bench gate's operator journey is not described
Severity: minor
Source: § Promotion path step 5; § D-H

"Run grounded re-extraction on the consolidated corpus per RFC 0017's
re-extract --version surface" — fine, but operationally:
- How long does this take? Hours? Days?
- What does the operator see during? A progress bar? A daily
  Slack-style ping?
- What happens on failure mid-run?
- Where do the grounded claims land — in the same `claims` table under
  a new prompt_version, or a sidecar?

Suggested fix: align with RFC 0017's existing re-extraction surface;
state explicitly that grounded claims land alongside ungrounded under
the bumped prompt_version, not in a sidecar.

## Open questions

- What does `engram grants list` show — datasets, role-x-dataset matrix,
  or per-grant audit log entries?
- Is the silent-downgrade warning machine-readable for downstream
  tooling?
- Is the bench (Step 5 in promotion) fully automated, or does it
  require operator intervention between runs?

verdict: accept_with_findings
