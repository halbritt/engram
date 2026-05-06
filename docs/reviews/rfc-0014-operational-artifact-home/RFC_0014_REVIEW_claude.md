# RFC 0014 Review — claude

Reviewer: claude
Date: 2026-05-06
Target: `docs/rfcs/0014-operational-artifact-home.md`
Comparison anchors: `docs/rfcs/0013-development-operational-issue-loop.md`,
`docs/process/multi-agent-review-loop.md`,
`agent-runner/docs/SPEC.md`, `agent-runner/docs/DECISION_LOG.md`.

The RFC is well-scoped and process-aligned. The proposed split between
`docs/operations/` (committed run state) and `docs/reviews/` (model review
feedback) cleanly resolves the overloading called out in the Problem section
and is consistent with the multi-agent review loop's Storage Rule
(`Raw feedback -> docs/reviews/`). Marker provenance protection
(§Migration step 6) and the explicit non-goal of authorizing raw corpus in
committed artifacts are both right. Findings below are the gaps that must close
before an implementation prompt can be written safely.

## Findings (highest severity first)

### F1. Cross-tree marker precedence is underspecified (high)

References: §Migration Plan If Accepted step 4; §Acceptance Criteria bullet 4;
RFC 0013 §5 "Marker schema and precedence".

RFC 0013 §5 requires scripts to compute the newest marker state per
`(issue_id, family)`, with `supersedes` controlling resolution. RFC 0014
promises "compatibility handling for the existing legacy path
`docs/reviews/phase3/postbuild/markers/`" and that scripts must "read both the
new operations path and legacy RFC 0013 markers during transition", but does
not state the algorithm. Concretely it does not say:

- whether `(issue_id, family)` precedence is computed across the union of the
  two trees;
- whether `supersedes` may name a legacy path from a marker in the new tree
  (and vice versa);
- the discovery order when both trees contain the same `issue_id`.

This is not theoretical — `docs/reviews/phase3/postbuild/markers/` currently
holds live loops including `20260506_limit500_run` and several
`20260505_limit*` directories. An implementation prompt that copies the
"compatibility handling" sentence verbatim will not have enough information to
preserve gating semantics.

Suggested resolution: state explicitly that RFC 0013 §5 precedence applies
across the union of `docs/operations/<area>/<loop_id>/markers/` and the
legacy `docs/reviews/<area>/postbuild/markers/` tree, and that `supersedes`
may name a path in either tree.

### F2. Migration step 3 is not specific enough for an implementation prompt (high)

References: §Migration Plan If Accepted step 3.

Step 3 says only: "Update `scripts/phase3_tmux_agents.sh` to read blocked/ready
markers from the new operations root." The review prompt asks whether the
migration plan is specific enough for a later implementation prompt — for the
script change it is not. Missing required behaviors include those already
mandated by RFC 0013 §10:

- `status` must surface the newest blocked or human-checkpoint marker before
  older ready markers, across both trees;
- `next` must refuse expansion when the newest marker for a loop is `blocked`
  or `human_checkpoint`;
- discovery must scan both the new and legacy roots until legacy is empty;
- no script may remove historical markers as a way to resume.

Suggested resolution: enumerate the script behaviors RFC 0014 inherits from
RFC 0013 §10, and the dual-tree scan obligation, in step 3 itself.

### F3. Owner-approved private-content escape hatch is silently narrowed (medium)

References: §Artifact Rules vs. RFC 0013 §3 "Keep committed operational
artifacts redacted".

RFC 0013 §3 allows tracked artifacts to include private content "only with
explicit owner approval and a marker front-matter field
`corpus_content_included: owner_approved`", and separately forbids private
content in markers. RFC 0014's §Artifact Rules drops the
`corpus_content_included` field and the owner-approved escape hatch entirely,
keeping only the marker-level prohibition. This is either an unintended
narrowing or an unstated tightening. Either reading is dangerous: the first
loses an audited path that operators may rely on; the second silently changes
RFC 0013 policy without saying so.

Suggested resolution: cite RFC 0013 §3 directly and either preserve the
owner-approved exception with the same `corpus_content_included` field, or
state explicitly that RFC 0014 tightens RFC 0013 §3 by removing it.

### F4. `reports/` vs `markers/` duplication is unresolved and load-bearing (medium)

References: §Proposal layout block; §Open Questions bullet 2.

The example layout shows both `reports/01_RUN.blocked.md` and
`markers/01_RUN.blocked.md`. Open Questions asks whether reports and markers
should be separate files or whether one marker carries enough front matter to
be the report index. Implementation cannot proceed without picking one — they
imply different write paths, different artifact validators, and different
redaction surfaces. Merging them increases the marker-redaction risk surface
because markers must never contain private corpus content (RFC 0013 §3 and
RFC 0014 §Artifact Rules), so any "marker as report index" model has to be
careful.

Suggested resolution: pick a default before the implementation prompt is
written; if undecided, default to "markers carry minimal front matter +
linked_report", which preserves the smallest blast radius.

### F5. `docs/operational/` as a candidate root collides with `logs/operational/` (medium)

References: §Open Questions bullet 1.

`docs/operational/` differs from the existing untracked diagnostics path
`logs/operational/` only by the parent directory. The whole RFC is motivated
by clearer separation between committed and untracked operational state;
keeping `docs/operational/` as a live option undermines that.

Suggested resolution: drop `docs/operational/` from the open question. Choose
between `docs/operations/` (matches existing prose) and `docs/ops/`
(shorter; harder to confuse with `logs/operational/`).

### F6. Phase-scope vs. process-scope is unresolved (low)

References: §Proposal example
(`docs/operations/phase3-postbuild/<YYYYMMDD>_<run_slug>/`) vs.
§Open Questions bullet 4.

The Proposal models `phase3-postbuild` as a single area path component, while
Open Questions still considers `postbuild/phase3` (process-scoped). Compat
code has to know which it is; otherwise the script change in F2 has to handle
both layouts indefinitely.

Suggested resolution: pick one before merge; phase-scoped (`phase3-postbuild`)
matches the existing prose example and is concrete enough.

### F7. Per-loop `README.md` is listed without content rules (low)

References: §Proposal layout block; §Open Questions bullet 3.

`docs/operations/<area>/<loop_id>/README.md` appears in the canonical layout,
but the open question still asks whether it is required, and no content
contract is given. Either specify what it contains (a one-paragraph loop
summary plus links to reports and markers, no private content), or drop it
from the canonical layout to avoid optional artifacts that scripts cannot
rely on.

### F8. Acceptance criterion gating on D060 is opaque (low)

References: §Acceptance Criteria last bullet ("D060 path hygiene remains
enforced").

Readers cannot evaluate this criterion without fetching DECISION_LOG.md.
Either add a one-line summary of what D060 requires (e.g., specific
path-naming or no-PII-in-paths discipline), or do not gate acceptance on
external context the RFC does not quote.

## Cross-cutting checks the prompt asked about

- `docs/operations/` vs review state separation: clean. The RFC also
  preserves `logs/operational/` as the untracked diagnostics path, and the
  non-goals exclude raw corpus in tracked artifacts. The only blur risk is
  the naming option in F5.
- RFC 0013 marker precedence and redaction: precedence rules survive in
  spirit because filenames and YAML are unchanged, but cross-tree semantics
  need to be made explicit (F1). Redaction is inherited at a high level but
  silently narrowed (F3).
- Migration plan specificity: not yet sufficient for an implementation
  prompt (F2, F4, F6, F7).
- Legacy marker compatibility: §Migration step 6 (don't move existing
  artifacts) protects audit history correctly. The remaining gap is the
  cross-tree precedence algorithm (F1).
- Risk of committing private corpus content: low at RFC level (rules carry
  over from RFC 0013), but watch F3 (owner-approved escape hatch) and F4
  (merging reports into markers expands the marker redaction surface).
- Suitability as `agent_runner` validation target: good. Scope is bounded
  (process RFC, no schema or product-code changes); it produces multi-agent
  review artifacts in disjoint paths under
  `docs/reviews/rfc-0014-operational-artifact-home/`; it exercises parallel
  review + synthesis + final review without requiring live model judgment on
  product code; the role and prompt files
  (`agent-runner/examples/rfc-0014-operational-artifact-home/`) are
  self-contained.

## Non-blocking observations

- The RFC says "It is for later review" but is being reviewed now via the
  agent-runner fixture; that mismatch is harmless and likely just a stale
  framing line.
- The proposed layout repeats canonical filenames from RFC 0013 §5 verbatim,
  which is the right call for diff-friendliness.

Verdict: accept_with_findings
