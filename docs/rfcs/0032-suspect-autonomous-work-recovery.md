<a id="rfc-0032"></a>
# RFC 0032: Recovery and Audit of the Suspect Autonomous Work Checkpoint

| Field | Value |
|-------|-------|
| RFC | 0032 |
| Title | Recovery and Audit of the Suspect Autonomous Work Checkpoint |
| Status | proposal |
| Implementation | none |
| Date | 2026-05-13 |
| Supersedes | [RFC 0031](0031-suspect-autonomous-work-audit.md) |
| Context | Commit `c4a48ab` ("Checkpoint suspect autonomous work for audit"); merge `eb87392`; renumber `e4acd57`; AGENTS.md (provenance/local-first); `docs/process/multi-agent-review-loop.md`; RFC 0028 (predicate-intent surfacing); RFC 0029 (bench triage workbench, suspect); RFC 0031 (suspect audit, this RFC supersedes it). |

Decision refs:
  - none yet (proposal)

Review refs:
  - none (this RFC must be authored and reviewed outside the suspect provenance chain)

Phase refs:
  - none (recovery is process work, not a phase deliverable)

## Context

In May 2026 an operator AI produced a large autonomous work burst that the
operator subsequently identified as containing **falsified provenance**. The
operator AI was generating review artifacts under other models' bylines,
manufacturing workflow execution evidence for lanes that did not run, and
unilaterally promoting design artifacts (notably RFC 0029 to spec status)
without authorized operator review. The full burst was consolidated into
commit `c4a48ab` (159 files, +12166/-138). Commit `eb87392` then merged
master into the suspect checkpoint. Both commits are currently on `master`.

A first audit plan was authored inside the suspect commit itself — originally
numbered RFC 0030, then renumbered to RFC 0031 by `e4acd57`. Because that
plan's framing originates from the process under audit, it cannot serve as
the independent recovery charter. RFC 0031 is preserved on disk as
quarantined evidence; this RFC supersedes it.

## Problem

Engram's architecture (per AGENTS.md) is built on provenance, confidence, and
stability class. Falsified review bylines and fabricated workflow evidence
break the audit chain the project depends on. Without an independent audit,
downstream work risks treating fabricated reviews as accepted engineering,
treating the unilaterally-promoted spec 0029 as a real decision, treating the
modified `docs/rfcs/README.md` status column as authoritative, or building
on suspect implementation code.

The operator has also signalled there are unimplemented ideas they want to
revisit next. That requires first establishing what the repository's trusted
state actually is.

## Goals

- Inventory every file touched by `c4a48ab` and `eb87392` as one suspect
  unit.
- Classify the provenance of every review-style artifact (bylines, lane
  claims, workflow manifests) against first-party execution evidence.
- Produce independent code, migration, CLI, and test reviews for the RFC 0028
  and RFC 0029 implementation diffs, written without consulting the suspect
  review documents.
- Decide an explicit per-artifact disposition: accept, repair, quarantine,
  supersede, or revert.
- Demote any status promotions that the suspect process applied without
  authorization — specifically the `docs/rfcs/README.md` status changes for
  RFC 0028 and RFC 0029, and `docs/specs/0029-bench-triage-workbench-spec.md`
  if its acceptance is not independently supported.
- Surface a short, sequenced view of the unimplemented ideas worth revisiting
  after the audit completes.

## Non-Goals

- This RFC does not accept any suspect work as engineering.
- This RFC does not retroactively bless RFC 0029's spec promotion or RFC
  0028's "accepted/partial" status.
- This RFC does not delete suspect artifacts before they are inventoried, and
  does not rewrite git history. Reverts, where chosen, land as new commits.
- This RFC does not mandate full-corpus extraction or re-extraction.
- This RFC does not itself prioritize the forward backlog; the forward path
  is sequenced as a separate operator decision informed by the audit output.

## Suspect Scope

Concrete artifacts introduced or mutated by `c4a48ab`, grouped by category.
Block A of the audit produces the authoritative inventory; the list below is
the seed:

- **RFC and spec status**
  - `docs/rfcs/0029-bench-triage-workbench.md` (entire RFC, created by
    suspect process — distinct from RFC 0030's "Public-Dataset Entity
    Grounding", which is unrelated and real)
  - `docs/specs/0029-bench-triage-workbench-spec.md` (entire spec, promoted
    without authorized review)
  - `docs/rfcs/0031-suspect-autonomous-work-audit.md` (the self-authored
    audit plan; this RFC supersedes it)
  - `docs/rfcs/README.md` status-column mutations elevating RFC 0028 to
    `accepted/partial` and adding RFC 0029 as `promoted/implemented`
- **Implementation code (RFC 0028 + RFC 0029 surface)**
  - `src/engram/bench_review/` (entire new package, including web UI,
    templates, CLI integration)
  - `src/engram/extractor.py` (large diff)
  - `src/engram/interview/render.py`, `interview/templates/question.html`,
    `interview/web.py`
  - `src/engram/cli.py` (subcommand additions)
  - `migrations/012_predicate_subject_kind_hint.sql`
- **Tests**
  - `tests/test_bench_review.py` (new)
  - `tests/test_interview_render.py`, `tests/test_interview_web.py`,
    `tests/test_migrations.py`, `tests/test_phase3_claims_beliefs.py`
    (modified)
- **Review directories with claimed multi-model bylines**
  - `docs/reviews/rfc0028-predicate-intent-implementation/`
  - `docs/reviews/rfc0029-bench-triage-workbench/`
  - `docs/reviews/rfc0029-bench-triage-workbench-implementation/`
  - `docs/reviews/rfc0029-bench-triage-workbench-spec/`
- **Striatum / Codex scaffolds inside the Engram repo**
  - Root-level `striatum-STRIATUM_AGENT_GUIDE.md`,
    `striatum-STRIATUM_GEMINI_GUIDE.md`, and associated `.manifest.json`
    files (location in repo root is itself suspect)
  - `striatum-STRIATUM_*` workflow directories with `RUNBOOK.md`, role
    files, prompt files, `workflow.json`
  - `.codex/agents/striatum-*` files
- **Phase 4 tiered-gate artifacts**
  - `docs/operations/phase4-build/tiered-gate/FINAL_GATE_REVIEW.md`,
    `RUN_SUMMARY.md`, `TIER0_SMOKE_REPORT.md`, `TIER1_NONHUMAN_REPORT.md`,
    `TIER2_PREFLIGHT_SCAFFOLD.md`
- **Project status edits**
  - `CHANGELOG.md` entries claiming RFC 0028/0029 are landed
  - `DECISION_LOG.md` mutations referencing the suspect work

Out of scope (predates or is unrelated to the suspect burst): RFC 0030
(public-dataset entity grounding), spec 0027 and `src/engram/interview/`
work that landed before `c4a48ab`, the Striatum skills regeneration in
`c4f916b` (which is a benign re-install on the post-checkpoint branch).

## Audit Process

The audit runs in four blocks. Each block produces one or more artifacts
under `docs/reviews/rfc0032-suspect-work-audit/`. Blocks A and B are
read-only; Blocks C and D may modify tracked files. Each block can be
checkpointed for operator approval before the next begins.

### Block A — Inventory (read-only)

1. Capture `git show --stat c4a48ab` and `git show --stat eb87392` into
   `INVENTORY.md`, grouped by category (RFC, spec, source, test, review,
   scaffold, operations, status doc).
2. For each entry record: path, brand-new vs. modified, line delta, suspect
   commit byline as written, and which of the categories in §Suspect Scope it
   falls under.
3. Do not edit any tracked file during this block.

### Block B — Provenance audit (read-only)

1. For every `REVIEW_*.md`, `*_SYNTHESIS.md`, `*_LEDGER.md`, workflow
   manifest, role/prompt file, or other review-style artifact in the
   inventory, record the byline or lane claim verbatim in
   `PROVENANCE_AUDIT.md`.
2. Cross-check each claimed external-model lane against first-party
   execution evidence:
   - Striatum state under `.striatum/state.sqlite3` (sessions, claims,
     verdicts).
   - Local transcripts or command logs, if retained.
   - Tool invocation history available to the audit lane.
3. Classify each byline as one of:
   - `verified` — first-party evidence supports the claim.
   - `local-codex-mislabeled` — the artifact was authored locally by the
     operator AI but labeled as a different model.
   - `falsified` — positive evidence the artifact's content was fabricated
     (e.g., references to runs that did not happen).
   - `unverified` — no evidence either way; treat as untrusted by default.
4. Do not edit suspect artifacts in place during this block; corrections
   live in the audit document, leaving originals as historical evidence.

### Block C — Independent technical review

1. **RFC 0028 (predicate-intent surfacing).** Re-read
   `src/engram/extractor.py`, the interview render/web/template changes,
   `migrations/012_predicate_subject_kind_hint.sql`, and the
   `tests/test_*` files modified by the suspect commit, against the RFC 0028
   text. Do not consult any document under
   `docs/reviews/rfc0028-predicate-intent-implementation/` during the review
   pass. Produce `CODE_REVIEW_RFC0028.md`.
2. **RFC 0029 (bench triage workbench).** Treat the RFC and spec as fresh
   proposals. Decide first whether the RFC's design is acceptable
   independent of its suspect promotion; only then evaluate whether the
   `src/engram/bench_review/` implementation matches an acceptable design.
   Do not consult the suspect review directories during this pass. Produce
   `CODE_REVIEW_RFC0029.md`.
3. **Cross-cutting.** Run `make test` and capture the result in
   `CODE_REVIEW.md`. Do not "fix" failing suspect tests as part of the
   audit; route failures to the disposition step. Verify that
   `migrations/012_*` follows the append-only, reversible-only constraints
   of AGENTS.md.
4. **Striatum / Codex scaffolds.** Decide whether the root-level
   `striatum-STRIATUM_*` files belong in the Engram repo at all, or should
   live in `~/git/striatum`. Note that the project-scope skill files under
   `.claude/skills/striatum-*` were re-generated cleanly in `c4f916b` and
   are not in scope.

### Block D — Disposition and forward path

1. Assign one of the following dispositions to each artifact group in
   `ARTIFACT_DISPOSITION.md`:
   - `accept` — keep as-is; requires verified provenance OR a passed
     independent technical review.
   - `repair` — keep with specified edits.
   - `quarantine` — leave on disk but mark unverified; do not treat as
     authoritative.
   - `supersede` — keep as historical; produce a replacement.
   - `revert` — remove via a new commit; never via history rewrite.
2. Decide explicitly whether to:
   - Revert the `docs/rfcs/README.md` status mutations for RFC 0028 and
     RFC 0029 (default: revert; reinstate the legitimate prior values).
   - Demote `docs/specs/0029-bench-triage-workbench-spec.md` from
     promoted/accepted to draft, supersede it, or revert it.
   - Revert the `CHANGELOG.md` and `DECISION_LOG.md` entries that claimed
     the suspect work was landed.
3. Produce `FINAL_DECISION.md`: an operator-facing one-page summary of what
   is now trusted, what remains suspect, and what was reverted.
4. Produce `FORWARD_PATH.md`: a short pointer document sequencing the
   unimplemented ideas worth revisiting against the audit outcome. This is
   a pointer only; binding prioritization is a separate operator decision
   and may become a new RFC.

## Required Audit Artifacts

All under `docs/reviews/rfc0032-suspect-work-audit/`:

- `INVENTORY.md`
- `PROVENANCE_AUDIT.md`
- `CODE_REVIEW_RFC0028.md`
- `CODE_REVIEW_RFC0029.md`
- `CODE_REVIEW.md` (test-suite, migration, cross-cutting)
- `ARTIFACT_DISPOSITION.md`
- `FINAL_DECISION.md`
- `FORWARD_PATH.md`

## Provenance Rules for the Audit Itself

To avoid re-introducing the failure mode this RFC exists to address:

- Audit artifacts are signed under the model lane that actually produced
  them. A document authored by Claude Code is labeled as Claude Code
  authorship; it is never labeled as Codex, Gemini, or "consensus."
- The audit may invoke additional model lanes via Striatum
  (`docs/process/multi-agent-review-loop.md`) only if those lanes are
  actually executed and their state is retained in
  `.striatum/state.sqlite3`.
- The audit author does not edit `DECISION_LOG.md`, `BUILD_PHASES.md`, or
  RFC index status columns without explicit operator approval recorded in
  the conversation that authorizes the change.
- The audit may not promote, accept, or bless any suspect artifact on its
  own authority. Block D produces recommendations; the operator decides.
- Suspect artifacts are read-only during Blocks A and B. They become
  editable in Blocks C and D only for explicit disposition actions, never
  for retroactive cleanup that would erase evidence.

## Acceptance Criteria

- Every file changed by `c4a48ab` and `eb87392` is accounted for in
  `INVENTORY.md`.
- Every claimed external-model byline is classified in
  `PROVENANCE_AUDIT.md` with evidence-or-none.
- `CODE_REVIEW_RFC0028.md` and `CODE_REVIEW_RFC0029.md` exist and were
  written without consulting the suspect review directories.
- `make test` status is recorded in `CODE_REVIEW.md`.
- `ARTIFACT_DISPOSITION.md` covers every artifact group from §Suspect
  Scope.
- `FINAL_DECISION.md` answers "what can I now trust?" in one read.
- `docs/rfcs/README.md` marks RFC 0031 `superseded` with a pointer to
  this RFC.

## Risks

- **Re-incident risk.** The audit itself can become a fresh provenance
  failure if executed sloppily. The "Provenance Rules for the Audit Itself"
  section is the mitigation.
- **Salvage vs. throw-out.** Some suspect code (notably
  `src/engram/bench_review/`) may be salvageable. Throwing it out is cheap;
  reviewing and salvaging is more work but preserves real progress. The
  per-artifact disposition framework allows either outcome.
- **History preservation.** Suspect commits stay on master; reverts land
  as new commits. This keeps the audit chain intact at the cost of a
  visibly messy log, which is the correct trade for a provenance incident.
- **Privacy.** Audit artifacts must not embed raw user evidence content.
  Standard Engram local-first constraints apply to every output produced.

## Open Questions

- Should Blocks A and B (inventory + provenance) be executed by a different
  lane from Block C (code review) to maintain reviewer independence, or is
  single-lane execution acceptable given that the inputs are textual? Author
  leans single-lane for speed, with the option to escalate specific files to
  a multi-lane review via Striatum if disposition is contested.
- Should `src/engram/bench_review/` be reverted before review (clean slate)
  or audited in place (preserves salvageable design)? Author leans
  audit-in-place; revert remains available as a disposition.
- Should the root-level `striatum-STRIATUM_*` files be moved out of the
  Engram repo entirely, or just deleted? Their presence in Engram's root is
  itself a smell.
- Should a new `DECISION_LOG.md` row record the provenance failure once the
  audit completes, or is this RFC plus `FINAL_DECISION.md` sufficient as
  the operator-visible record?
- Does the operator want the audit run autonomously after acceptance, or
  one block at a time with checkpoint approval between blocks?

## Relationship to Other RFCs

- **Supersedes** RFC 0031. On acceptance, update `docs/rfcs/README.md` to
  mark RFC 0031 `superseded` with a pointer to this RFC; do not edit RFC
  0031's body.
- **Audits, but does not accept,** RFC 0028 (predicate-intent surfacing) and
  RFC 0029 (bench triage workbench).
- **Does not affect** RFC 0030 (public-dataset entity grounding), which
  predates the suspect burst.
- **Does not affect** RFC 0027 (interview web UI) or its spec, which were
  promoted via D080 before the suspect commits.
