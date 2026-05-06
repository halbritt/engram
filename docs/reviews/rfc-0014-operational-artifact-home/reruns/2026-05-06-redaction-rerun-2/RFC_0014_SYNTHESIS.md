# RFC 0014 Synthesis: Operational Artifact Home

author: synthesizer-claude-opus-001

## Review Inputs

- Target RFC: `docs/rfcs/0014-operational-artifact-home.md` (status: proposal,
  dated 2026-05-05).
- Spec handoff referenced by the RFC:
  `docs/process/operational-artifact-home-spec.md` (2026-05-06).
- Findings ledger: `RFC 0014 Findings Ledger`
  (author: ledger-codex-gpt-5.5-001), 12 ledgered findings F001-F012.
- Underlying reviews:
  - `reviewer-claude-opus-001` -- 8 findings, verdict
    `accept_with_findings`;
  - `reviewer-codex-gpt-5.5-001` -- 5 findings, verdict
    `accept_with_findings`;
  - `reviewer-gemini-3.1-pro-preview-001` -- 5 findings, verdict
    `accept_with_findings`.
- Cross-references named by the RFC and reviewers: RFC 0013, D060, D062, D063,
  `docs/process/multi-agent-review-loop.md`,
  `docs/process/phase-3-agent-runbook.md`,
  `scripts/phase3_tmux_agents.sh`.

All three reviewers returned `accept_with_findings` with no blocking findings.
Convergence is highest on cross-root marker precedence (F001), the RFC/spec
delegation gap (F002), and the redaction-contract duplication risk (F003).

## Finding Disposition Table

| Finding | Title (abbreviated) | Priority | Disposition | Rationale |
|---------|---------------------|----------|-------------|-----------|
| RFC0014-F001 | Cross-root marker precedence underspecified | high | accepted with modification | All three reviewers flag this; require an explicit mixed-root precedence algorithm in the RFC body and a verification fixture, rather than only in the spec. |
| RFC0014-F002 | RFC body delegates resolved layout decisions while retaining Open Questions | medium | accepted with modification | Convert "Open Questions" to a "Resolved In Spec Handoff" section with the chosen answers inline; remove the "Proposal Sketch" framing once layout is normative. |
| RFC0014-F003 | Redaction contract partially duplicated, may drift from RFC 0013 | medium | accepted with modification | Replace the partial duplicate list with an authoritative reference to RFC 0013 Section 3 and explicitly reaffirm `corpus_content_included: owner_approved` and the link-only-to-redacted-summary rule. |
| RFC0014-F004 | Script migration testing expectations too implicit | medium | accepted | Add explicit acceptance criteria for legacy-only, operations-only, mixed-root, cross-root `supersedes`, unresolved blocked, and newer `human_checkpoint` cases. |
| RFC0014-F005 | Migration plan leaves transition rules unclear | medium | accepted | Clarify whether legacy marker directories are frozen on acceptance, whether new legacy markers may still be written during transition, and that RFC 0013 Section 10's singular post-build marker-tree contract is amended to plural roots. |
| RFC0014-F006 | `docs/operations/` needs explicit local-diagnostics boundary | low | accepted | Require a `docs/operations/README.md` repeating forbidden-content rules and routing private repair evidence to ignored `logs/operational/`. |
| RFC0014-F007 | Proposal-sketch framing weakens canonical layout | low | accepted with modification | Treat as a duplicate of F002; resolved by the same RFC body change (drop "Proposal Sketch" label after lifting resolved choices inline). |
| RFC0014-F008 | Agent-runner validation success signal should remain narrow | low | accepted | Add a validation note in non-goals that this target exercises redacted artifact generation and policy review only, not live marker orchestration. |
| RFC0014-F009 | Operational state and review feedback cleanly separated | non-blocking | accepted (preserve) | Positive observation; preserve the `docs/operations/` vs `docs/reviews/` split as currently described. |
| RFC0014-F010 | Legacy compatibility intent is present | non-blocking | accepted (preserve, depends on F001) | Intent is correct; sufficiency depends on F001 being addressed. |
| RFC0014-F011 | Privacy posture broadly preserved | low / positive | accepted (preserve, depends on F003) | Privacy stance is intact; the only privacy-adjacent gap is closed by F003. |
| RFC0014-F012 | RFC 0014 is a bounded validation target for `agent_runner` | non-blocking | accepted (preserve, depends on F008) | Confirm the bounded framing while narrowing the validation signal per F008. |

No findings are deferred or rejected. Findings F007 and F002 share a single
edit; F010, F011, and F012 are confirmations rather than asks and are
preserved subject to the related modifications.

## Proposed RFC 0014 Disposition

**Recommendation:** `revise`.

The RFC is a sound bounded proposal; no reviewer recommends rejection, and
the privacy posture, separation of concerns, and migration intent are all
intact. However, four medium findings (F001, F002/F007, F003, F004) and one
medium plan-completeness finding (F005) describe contract gaps that must be
closed in the RFC text, or unambiguously delegated to a normative companion,
before this RFC is treated as the source for an implementation prompt. A
revision pass that lifts spec-handoff decisions inline, tightens the cross-root
marker precedence contract, and aligns the redaction language with RFC 0013
will likely move this RFC to `accept` without further review rounds.

The human owner remains the deciding party; this synthesis does not edit RFC
0014, `DECISION_LOG.md`, or process docs.

## Exact Canonical Doc Changes If The Recommendation Is Accepted

The following changes apply only to `docs/rfcs/0014-operational-artifact-home.md`
unless explicitly noted. They are scoped to address F001-F008 and to preserve
the supportive findings (F009-F012).

### Change set 1: Resolved layout (addresses F002, F007)

- Rename the "Open Questions" section to "Resolved In Spec Handoff" and, for
  each of the four questions, state the chosen answer inline followed by a
  pointer to `docs/process/operational-artifact-home-spec.md` for rationale:
  - root path (`docs/operations/` vs `docs/ops/` vs `docs/operational/`);
  - reports vs markers as separate files vs one combined marker file;
  - whether each loop has a `README.md`;
  - phase-scoped (`phase3-postbuild`) vs process-scoped
    (`postbuild/phase3`) area naming.
- Remove the trailing paragraph in "Proposal Sketch" that labels the layout
  block as "the original proposal sketch, not the final implementation
  contract." Replace with: "This layout is the normative contract for RFC
  0014. The spec handoff records rationale and edge cases."
- Update the introductory paragraph that calls RFC 0014 "still a proposal
  sketch" to reflect that resolved choices now live in the RFC body.

### Change set 2: Cross-root marker precedence (addresses F001, F010)

Add a new subsection immediately after "Migration Plan If Accepted" titled
"Cross-Root Marker Precedence Contract" stating:

- marker state is computed across `docs/operations/` and legacy RFC 0013
  marker roots before precedence is evaluated; root location must not alter
  gate priority;
- `supersedes` may reference repository-relative paths in either root;
- the RFC 0013 newest-wins-but-newer-blocked-blocks rule applies unchanged;
- unresolved legacy `blocked` or `human_checkpoint` markers continue to block
  expansion until explicitly superseded by name;
- discovery must not double-count markers and must preserve per-loop scoping.

Add a parallel acceptance-criteria bullet: "the cross-root marker precedence
contract is implemented and verified by fixture, not only by smoke test."

### Change set 3: Redaction contract alignment (addresses F003, F011)

- In "Artifact Rules", replace the duplicated allow/forbid lists with a single
  authoritative reference: "Committed operational artifacts under
  `docs/operations/` follow RFC 0013 Section 3 redaction rules unchanged,
  including the allow/forbid lists, the
  `corpus_content_included: owner_approved` front-matter requirement, and
  the rule that private content remains in `logs/operational/` with only
  redacted summaries linked from tracked docs."
- Retain the explicit sentence: "Markers should never contain private corpus
  content."

### Change set 4: Migration plan precision (addresses F004, F005)

- In "Migration Plan If Accepted", add explicit transition rules:
  - existing `docs/reviews/<area>/postbuild/markers/<run>/` directories are
    frozen for new writes on RFC 0014 acceptance, but remain readable as part
    of the logical marker set;
  - new markers are written under `docs/operations/` only after acceptance;
  - RFC 0013 Section 10's singular post-build marker-tree automation contract
    is amended to read across both roots; record this as a deprecation
    cross-reference in RFC 0013 rather than a rewrite of historical text.
- Add concrete acceptance-criteria bullets covering: legacy-only,
  operations-only, mixed-root, cross-root `supersedes`, unresolved legacy
  `blocked`, and newer `human_checkpoint` overriding older `ready` markers.

### Change set 5: Operations-root README (addresses F006)

- Add a migration plan step requiring a `docs/operations/README.md` that:
  - restates the forbidden-content rule by reference to RFC 0013 Section 3;
  - directs private repair evidence to ignored `logs/operational/`;
  - reaffirms that markers may never contain private corpus content.

### Change set 6: Validation framing (addresses F008, F012)

- In "Non-Goals", append: "RFC 0014 validation via `agent_runner` exercises
  redacted artifact generation, stable byline/format handling, source-only
  constraints, and policy review. It does not exercise live marker
  orchestration."

### Out of scope for this synthesis

This synthesis does not propose edits to RFC 0013, `DECISION_LOG.md`,
`docs/process/multi-agent-review-loop.md`,
`docs/process/phase-3-agent-runbook.md`, or
`scripts/phase3_tmux_agents.sh`. The amendments to RFC 0013 Section 10 and to
the script described above would happen on acceptance of revised RFC 0014,
under a separate work scope.

## Runner Validation Observations (Separate From RFC 0014 Findings)

These observations are about the `agent_runner` dogfood workflow itself, not
about RFC 0014 as a target document. They are recorded here to keep them
distinct from RFC 0014 dispositions.

- **Bounded-target framing held.** RFC 0014 was a small, source-bounded
  target with clear dependencies (RFC 0013, the multi-agent review loop, the
  Phase 3 runbook). All three reviewers and the synthesis lane were able to
  produce redacted artifacts without requiring corpus access, which matches
  the intended runner validation signal.
- **Source completeness matters.** The Claude review explicitly notes that an
  RFC 0014 reviewer cannot evaluate marker precedence preservation without
  RFC 0013 in the work packet. For future runner validations of process RFCs,
  the work packet should include the prior RFCs that the target RFC amends or
  supersedes, not only the target.
- **Spec handoff vs RFC body is a real review hazard.** The runner produced
  three independent reviews that all surfaced the RFC/spec delegation gap
  (F002/F007). This suggests the runner is doing useful work surfacing
  contract ambiguity, but it also suggests that future targets should either
  inline normative decisions or clearly mark a companion spec as
  authoritative.
- **Validation signal scope.** Per F008, the runner validation signal should
  remain artifact generation, byline/format stability, source-only
  constraints, and policy review. This synthesis was produced under those
  constraints; the synthesis does not write to canonical docs and does not
  touch repository markers.
- **Redaction posture preserved.** No review or synthesis artifact in this
  packet introduced raw corpus content; all references stayed at the
  process/policy layer. This is the intended privacy outcome for runner
  dogfood targets.
- **Disposition authority.** Per the work packet, this synthesis recommends a
  disposition; the human owner decides. No canonical docs were edited in this
  job.
