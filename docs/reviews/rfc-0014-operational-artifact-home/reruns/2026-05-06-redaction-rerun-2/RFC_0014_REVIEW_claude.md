# RFC 0014 Review: Operational Artifact Home

author: reviewer-claude-opus-001

Scope: review of `docs/rfcs/0014-operational-artifact-home.md` against RFC
0013, the multi-agent review loop, and the redaction posture inherited from
D060/D062/D063. The RFC declares itself a proposal sketch and defers detailed
layout to `docs/process/operational-artifact-home-spec.md`, which is referenced
but not embedded in this review packet.

## Findings

### 1. Open Questions remain visible in the RFC body even though the prose claims the spec handoff resolves them -- medium

The "Open Questions" section still lists four unresolved choices (root name,
marker/report split, README requirement, area scoping). The introduction and the
section header both assert that the spec handoff resolves these "as explicit
choices rather than inferred during implementation." A future reader who reads
RFC 0014 alone (via `git show`, archived view, or as RFC text without the spec)
will see open questions, not decisions. Either inline the resolved choices in
the RFC text or rewrite the Open Questions section as "Resolved In Spec Handoff"
with the chosen answer per question and a pointer to the spec for rationale.
Right now the RFC and the spec disagree about how decided each question is.

### 2. Artifact Rules are shorter than RFC 0013's redaction contract and drop the owner-approval marker requirement -- medium

RFC 0013 §3 requires that a tracked artifact include private content "only with
explicit owner approval and a marker front-matter field
`corpus_content_included: owner_approved`," and that markers themselves never
contain private corpus content. RFC 0014's "Artifact Rules" section reproduces
the allow/forbid lists but does not reaffirm the `corpus_content_included`
front-matter contract or the routing rule that private content goes to
`logs/operational/` and only redacted summaries to tracked docs. The RFC's
Non-Goals do say it does not authorize raw corpus content, and "Markers should
never contain private corpus content" is preserved, but the explicit
owner-approval flag and the link-only-to-redacted-summary rule are lost.
Reinstate both, or state explicitly that RFC 0013 §3 redaction rules apply
unchanged to `docs/operations/`.

### 3. Cross-root marker precedence is asserted but not specified -- medium

RFC 0013 §5 defines marker precedence by `(issue_id, family)` with explicit
`supersedes` filenames and a "newest-wins-but-newer-blocked-blocks" rule. RFC
0014 step 5 says "Preserve marker front matter and cross-root `supersedes`
semantics from RFC 0013," and step 4 says scripts must read both roots as "one
logical marker set." This is too thin for an implementation prompt:

- How is `supersedes` resolved when it points at a path in the legacy root from
  a marker in the new root (and vice versa)? Repository-relative paths work, but
  the RFC should say so.
- How does `scripts/phase3_tmux_agents.sh` enumerate markers across both roots
  without double-counting or losing per-loop scoping?
- Acceptance criteria asks for "the marker precedence rules from RFC 0013 still
  work" but does not require a concrete test (e.g., a fixture where a new-root
  ready marker correctly resolves a legacy-root blocked marker).

This is the part most likely to silently regress, because automation can pass a
smoke test while losing legacy markers under a fresh-loop discovery filter.
Either the RFC or the spec needs an explicit cross-root precedence algorithm and
a verification test.

### 4. Migration plan is partially specific; gaps will surface in the implementation prompt -- medium

Step 1 names a spec file. Step 3 names the runbook. Step 4 names the script.
Step 6 makes a historical index optional. Missing items that an implementation
prompt will need:

- whether existing `docs/reviews/<area>/postbuild/markers/<run>/` directories
  are frozen (implied by step 7 but not stated as a rule);
- a concrete test or fixture covering cross-root precedence (see finding 3);
- updates to RFC 0013 §10 automation contract -- RFC 0013 currently says
  "tmux/status automation must discover operational markers in the post-build
  marker tree" (singular). RFC 0014 needs that contract amended or referenced;
- whether `docs/reviews/phase3/postbuild/markers/` continues to receive new
  markers during the transition or freezes on RFC 0014 acceptance.

### 5. The proposal does cleanly separate operational run state from model review feedback -- non-blocking, supportive

The split -- `docs/operations/<area>/<loop_id>/` for run state, `docs/reviews/`
for model review feedback (including RFC reviews like this one) -- directly
addresses the overload that RFC 0014 calls out in its Problem section. The
non-goal that RFC 0014 "does not make repository markers an `agent_runner`
control plane" keeps the boundary clear and avoids re-creating the prior
coupling under a new path.

### 6. RFC is a defensible bounded target for agent_runner validation -- non-blocking

The RFC is small, has no product behavior, names its sources of truth (RFC 0013,
multi-agent review loop, runbook), preserves local-first/no-egress as a
non-goal, and produces redacted artifacts only. It is reasonable as an
`agent_runner` review target as long as the reviewing agent has access to both
RFC 0014 and RFC 0013; without RFC 0013 the reviewer cannot evaluate marker
precedence preservation.

### 7. Private corpus content risk is contained, with the caveat in finding 2 -- low

The RFC inherits RFC 0013's allow/forbid lists and explicitly states "Markers
should never contain private corpus content." It does not introduce a new
tracked surface where corpus content would land more easily. Finding 2 is the
only privacy-adjacent gap.

### 8. Minor: tighten the "Proposal Sketch" framing -- low

The RFC labels the layout block as "the original proposal sketch, not the final
implementation contract" and points readers to the spec. That phrasing is
honest but it leaves the RFC body without a single canonical layout statement.
After resolving finding 1, this label can be removed and replaced with the
chosen layout, leaving the spec for rationale and edge cases.

## Summary

No blocking findings. The RFC is a sound bounded proposal that preserves RFC
0013's redaction posture in spirit, separates run state from review feedback,
and avoids over-reaching into `agent_runner` mechanics. The medium findings
(1-4) are clarity and contract-completeness gaps that should be closed before
this RFC is treated as the source for an implementation prompt; most can be
addressed by lifting resolutions out of the spec handoff into the RFC body and
tightening the cross-root marker precedence contract. The privacy posture is
intact except for the missing reaffirmation of the owner-approval front-matter
rule.

Verdict: accept_with_findings
