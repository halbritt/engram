# Review: RFC 0014 Operational Artifact Home Spec Handoff

author: reviewer-codex-gpt-5.5-001

## Findings

### Major: Flat legacy markers are not safely included in transition gate logic

References: `docs/process/operational-artifact-home-spec.md` Compatibility
Semantics; Migration Work item 8; RFC 0013 Section 5; RFC 0014 Acceptance
Criteria.

The spec says Phase 3 migration tooling scans:

```text
docs/operations/phase3-postbuild/<loop_id>/markers/
docs/reviews/phase3/postbuild/markers/<loop_id>/
```

It then says existing flat legacy markers under
`docs/reviews/phase3/postbuild/markers/` remain historical provenance and
tooling may index them for audit. That is not strong enough for a transition
contract.

RFC 0013 explicitly recognizes flat post-build markers as legacy provenance,
and RFC 0014 requires old markers to remain audit provenance while scripts read
the new operations root and legacy RFC 0013 marker roots as one logical marker
set. If any flat legacy `blocked` or `human_checkpoint` marker remains
unresolved, an implementation following this spec could ignore it for gate
computation and allow expansion.

Proposed fix: require tooling to scan flat legacy markers for unresolved
`blocked` and `human_checkpoint` states and fail closed until each is either
explicitly superseded by repository-relative path or classified by owner
decision as historical/non-blocking. Add a fixture covering a flat legacy
blocker.

### Medium: Marker private-content exception weakens the marker-specific redaction rule

References: `docs/process/operational-artifact-home-spec.md` Artifact Rules;
RFC 0013 Section 3; RFC 0014 Artifact Rules.

RFC 0013 and RFC 0014 both allow owner-approved private content in tracked
artifacts only as an exception, but they also say markers should never contain
private corpus content. The spec changes that to "Markers should never contain
private corpus content unless the owner explicitly approves a
tracked-artifact exception."

That creates a higher-risk path because markers are intentionally
machine-scanned, durable, and likely to be copied into status surfaces. Even
with owner approval, the safer contract is that private corpus content belongs
in ignored diagnostics or, if truly approved, in a tightly scoped report
artifact rather than a marker.

Proposed fix: make marker bodies and marker front matter categorically free of
private corpus content. Keep `corpus_content_included: owner_approved`
available for reports, or allow markers only to reference an approved redacted
report decision without carrying the private content themselves.

### Minor: The malformed-front-matter rule conflicts with the missing-`created_at` ordering rule

References: `docs/process/operational-artifact-home-spec.md` Compatibility
Semantics.

The spec says markers are ordered by valid `created_at`, and a marker missing
`created_at` sorts before a marker with a valid timestamp. It later says
malformed, ambiguous, or contradictory marker front matter must fail closed.

Because RFC 0013 marker front matter requires `created_at`, a missing timestamp
could reasonably be treated as malformed. The implementation contract should
say whether missing `created_at` is a tolerated legacy condition or a
validation failure.

Proposed fix: state explicitly that missing `created_at` is either accepted
only for legacy audit indexing with fail-closed gate behavior, or accepted for
all marker precedence with the documented sort order.

## Non-Blocking Assessment

No rejection-level findings. The package otherwise cleanly separates committed
operational state under `docs/operations/` from model review feedback under
`docs/reviews/` and ignored diagnostics under `logs/operational/`.

The spec is a good bounded `agent_runner` validation target. Its SQLite/live
state boundary is explicit, and it correctly frames repository markers as
durable artifacts rather than queue truth.

The handoff is mostly specific enough for implementation: it resolves root
choice, area naming, report/marker separation, README optionality, marker schema
preservation, cross-root `supersedes`, and required fixtures. The main
implementation gap is legacy flat-marker handling.

Verdict: needs_revision
