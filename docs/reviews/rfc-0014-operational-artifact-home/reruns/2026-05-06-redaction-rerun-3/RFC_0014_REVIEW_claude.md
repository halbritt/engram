# Review: RFC 0014 Operational Artifact Home Spec Handoff

author: reviewer-claude-opus-001
date: 2026-05-06
artifact: `docs/rfcs/0014-operational-artifact-home.md` plus
`docs/process/operational-artifact-home-spec.md`
context: RFC 0013, `docs/process/multi-agent-review-loop.md`

## Summary

The RFC 0014 spec handoff package converts the original proposal sketch into
explicit, reviewable choices. The RFC correctly defers layout decisions to the
spec; the spec resolves the four open questions, preserves RFC 0013 marker
front matter and redaction rules, and bounds the `agent_runner` validation
scope. The package is close to implementation-ready. There is one medium
ambiguity around flat legacy markers and a few minor clarifications worth
making before a final implementation prompt.

## Findings

### M1: Flat legacy marker participation in gate state is ambiguous

Priority: medium

`docs/process/operational-artifact-home-spec.md` (Compatibility Semantics)
says the per-loop scan covers:

```text
docs/operations/phase3-postbuild/<loop_id>/markers/
docs/reviews/phase3/postbuild/markers/<loop_id>/
```

and then states that "Existing flat legacy post-build markers under
`docs/reviews/phase3/postbuild/markers/` remain historical provenance.
Tooling may index them for audit, but new expansion gates should be
represented by the per-loop legacy or operations-root marker directories
above."

However, the same spec's Migration Work step 8 makes legacy-root retirement
contingent on "no unresolved `blocked` or `human_checkpoint` marker remains in
the legacy path", which implies flat legacy markers can in fact be load bearing
for blocking.

This is a real gap: if a flat legacy marker, not nested under a `<loop_id>/`
directory, currently records an unresolved blocked or human-checkpoint state,
the spec gives tooling permission to ignore it for gates while still requiring
its resolution for retirement. RFC 0013's precedence rule that the newest
marker per `(issue_id, family)` blocks expansion does not survive cleanly
across that ambiguity.

Recommendation: either state explicitly that flat legacy markers also
participate in gate computation when they carry valid front matter, with
malformed flat markers failing closed per rule 7, or require the migration to
first relocate any unresolved flat legacy markers into a per-loop directory
before tooling switches to the new precedence rules. The first option is the
lower-risk default and matches the "preserve provenance" goal.

### M2: Human-checkpoint resolution rule extends RFC 0013 without flagging the change

Priority: medium

Spec precedence rule 5 says a `human_checkpoint` marker remains blocking until
a later marker explicitly supersedes it and the linked report records the owner
decision that resolved the checkpoint.

RFC 0013 Section 5 only requires that a newer ready marker share `(issue_id,
family)` and name the older marker in `supersedes`. The linked-report owner
decision requirement is new behavior, not a layout choice.

The constraint is sensible because it prevents silent overrides of human
checkpoints, but it is a substantive precedence-rule addition that should
either be stated in RFC 0014's Goals or Artifact Rules so it is part of the
proposal under review, or be moved out of this spec into a follow-on RFC 0013
amendment.

As written, an implementer reading only the RFC could miss this requirement,
and a reviewer reading only the RFC will not see it for explicit acceptance.

### Minor 1: `<loop_id>` format is implied but not specified

The canonical layout shows `<YYYYMMDD>_<run_slug>` for Phase 3 post-build, but
the general `<area>/<loop_id>/` shape never states the loop id grammar. RFC
0013 Section 5 already uses `<YYYYMMDD>_<run_slug>` for the marker directory.
The spec should pin the loop id to that grammar, or explicitly say it is
area-defined, so implementation fixtures and validation can rely on it.

### Minor 2: Optional `docs/operations/README.md` lacks an explicit redaction binding

Spec Migration Work step 7 allows an optional root README as a redacted index.
The Artifact Rules section binds redaction to "Committed operational artifacts
under `docs/operations/`," which covers the README, but a single sentence in
step 7 would make that explicit and prevent a later index from accreting prose
summaries from blocked runs.

### Minor 3: `loop` front matter and `<area>` path are related but distinct concepts

Markers continue to use `loop: postbuild` while the path uses
`phase3-postbuild`. RFC 0013 already had this asymmetry, so it is not new, but
the spec is the right place to either map area to loop or note that the path
string is more specific than the front-matter `loop` enum. This is
documentation hygiene, not a behavior change.

## Items Confirmed Healthy

- Operational vs review separation is clean: `docs/operations/` hosts redacted
  operational artifacts, and `docs/reviews/` continues to host multi-agent
  review feedback.
- RFC 0013 redaction rules survive: the spec restates allowed and forbidden
  categories, preserves `corpus_content_included: none` as default and
  `corpus_content_included: owner_approved` as the explicit exception, and
  applies D060 path hygiene.
- Marker front matter compatibility is preserved: `issue_id`, `family`,
  `gate`, `linked_report`, `supersedes`, and privacy fields are unchanged.
- Apart from M1 and M2, cross-root precedence preserves RFC 0013 Section 5
  semantics. Per-loop scoping is correct and prevents cross-loop
  contamination. Fail-closed behavior on malformed front matter is a strict
  but correct addition.
- RFC supersession discipline is healthy: treating RFC 0013 as a point-in-time
  record and adding only a deprecation cross-reference matches the
  multi-agent review loop's storage rule.
- The `agent_runner` boundary is explicit: SQLite is live workflow state and
  repository markers are durable artifacts.
- RFC 0014 is a good bounded `agent_runner` validation target: small surface
  area, clear write scopes, deterministic fixtures, and an explicit non-goal
  that markers are not the queue.
- No private-corpus commit risk is introduced.
- RFC/spec alignment is adequate: the RFC clearly points to the spec, the spec
  cites the RFC and source reviews, and the RFC's open questions map to
  S001-S004 in the spec.

## Recommendations Before Implementation Prompt

1. Resolve M1 by stating explicitly whether flat legacy markers participate in
   gate state, ideally by including them as a third scan path that still fails
   closed on malformed front matter.
2. Move M2's human-checkpoint resolution requirement into RFC 0014, either in
   Artifact Rules or a new Precedence section, so the constraint is part of
   what gets accepted.
3. Pin `<loop_id>` grammar to `<YYYYMMDD>_<run_slug>` in the spec.
4. Add one sentence binding any optional `docs/operations/README.md` to the
   redaction rules and to the no-script-dependency clause.

None of these are blocking for the spec handoff itself. M1 and M2 should be
resolved before an implementation prompt is cut from the spec.

Verdict: accept_with_findings
