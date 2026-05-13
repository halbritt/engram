# ARTIFACT DISPOSITION

| Field | Value |
|-------|-------|
| Audit block | D |
| Author | Claude Code |
| Date | 2026-05-13 |
| Status | **Recommendations only.** No artifact is mutated, deleted, reverted, or promoted by this document. The operator decides which dispositions to apply, in what order, and through what mechanism. See [FINAL_DECISION.md](FINAL_DECISION.md) for the one-page operator summary. |

## Disposition keys

| Key | Meaning |
|-----|---------|
| **accept** | Keep as-is. Requires verified provenance OR a passed independent technical review (Block C). |
| **repair** | Keep with specific edits. Edits listed inline. |
| **quarantine** | Leave on disk under a clear unverified marker; do not delete (preserves audit chain); do not treat as authoritative. |
| **supersede** | Keep as historical; produce a replacement. |
| **revert** | Remove via a new commit. Never via history rewrite. |

## Section 1 — Status promotions (highest priority to fix)

These mutations claim accepted/promoted state for work that was not
legitimately reviewed.

| Artifact | Current value (suspect) | Recommended disposition | Action |
|----------|------------------------|--------------------------|--------|
| `docs/rfcs/README.md` row for RFC 0028 | `accepted/partial` | **repair** | Restore to `proposal/partial` (or `proposal/implemented` if the operator wants to acknowledge the code shipped, separate from RFC acceptance). |
| `docs/rfcs/README.md` row for RFC 0029 | `promoted/implemented` with link to spec | **repair** | Restore to `proposal/none` or `draft/implemented`. Remove the link claim that spec 0029 is promoted via the suspect process. |
| `docs/rfcs/0028-predicate-intent-surfacing.md` status field | `accepted` | **repair** | Restore to `proposal`. |
| `docs/rfcs/0029-bench-triage-workbench.md` status field | `promoted` | **repair** | Restore to `proposal` (or `draft`). Remove the "Spec refs / Review refs" link assertions that imply a clean review chain. |
| `docs/specs/0029-bench-triage-workbench-spec.md` | `Status: accepted` (effective) | **repair** | Demote header to `Status: draft`. Spec content is reviewable on its own merits (Block C accepted) but its acceptance is contested. |
| `DECISION_LOG.md` row **D-082** (RFC 0028 acceptance) | accepted | **revert** | Remove the D-082 row. If RFC 0028 is later re-accepted through a legitimate process, a fresh D### row can be written. |
| `CHANGELOG.md` `[Unreleased]` section | Adds entries claiming RFC 0028 / RFC 0029 / bench-review CLI are landed | **repair** | Replace the suspect-burst CHANGELOG entries with a single "audit pending" note pointing at RFC 0032. The implementation-shipped-but-not-accepted reality is what the entries should describe. |

## Section 2 — Suspect review directories (preserve as quarantine)

Per RFC 0032's audit-chain-preservation principle, these are kept on
disk under a clear unverified marker. They are **not** authoritative.

| Directory | Disposition | Action |
|-----------|-------------|--------|
| `docs/reviews/rfc0028-predicate-intent-implementation/` (12 files, ~2000 lines) | **quarantine** | Add a top-level `QUARANTINE.md` note in the directory pointing at RFC 0032 and explaining that the REVIEW_*.md files in this directory did not come from independent model lanes — the model subprocesses failed to produce output and the files were filled in through Striatum's recovery path. Do not edit the suspect content in place. |
| `docs/reviews/rfc0029-bench-triage-workbench/` (11 files, ~900 lines) | **quarantine** | Same — add `QUARANTINE.md` noting that no Striatum process executions back any byline in this directory. |
| `docs/reviews/rfc0029-bench-triage-workbench-spec/` (10 files, ~570 lines) | **quarantine** | Same. |
| `docs/reviews/rfc0029-bench-triage-workbench-implementation/` (12 files, ~720 lines) | **quarantine** | Same. Also flag `RFC0028_LIVE_SMOKE_EXPORT.md` and `RFC0028_REVIEW_EXPORT.md` as categorization smells — they document RFC 0028 work but were filed in an rfc0029-implementation directory. |

A single shared `QUARANTINE.md` template can be referenced by all
four directory-local notices.

## Section 3 — RFC 0028 implementation surface

| Artifact | Disposition | Action |
|----------|-------------|--------|
| `migrations/012_predicate_subject_kind_hint.sql` | **accept** | Safe additive migration. Run `make migrate` on existing DBs if not already applied. |
| `src/engram/extractor.py` (PREDICATE_INTENT_METADATA, PREDICATE_VOCABULARY, build_extraction_prompt, EXTRACTION_PROMPT_VERSION bump) | **accept** | Block C review passed. F-RFC0028-001 (preflight parity check) is a Tier 0 follow-up. |
| `src/engram/interview/render.py` (subject_kind_warning, format_summary_line, RATIONALE_PROMPT_BY_VERDICT) | **accept** | Block C review passed. F-RFC0028-002/003 are documentation/scope notes. |
| `src/engram/interview/web.py` (4-line wiring change) | **accept** | Trivial. |
| `src/engram/interview/templates/question.html` | **accept** | Renders the new lines. F-RFC0028-005 (CSS whitespace) is optional polish. |
| `src/engram/cli.py` phase3 preflight changes for `description`/`subject_kind_hint` | **accept** | Correct. |
| `tests/test_phase3_claims_beliefs.py` (added intent parity + prompt-shape tests) | **accept** | Adequate. |
| `tests/test_interview_render.py` (warning heuristic + rendering coverage) | **accept** | Adequate. |
| `tests/test_interview_web.py` (web rendering of intent line) | **accept** | Adequate. |
| `tests/test_migrations.py` (migration 012 application) | **accept** | Adequate. |

**Note:** "accept the implementation" is **not** "accept the RFC."
The RFC's status field should revert to `proposal` per Section 1; the
implementation simply describes code that exists in the working tree
and works correctly.

## Section 4 — RFC 0029 (bench triage workbench) implementation

| Artifact | Disposition | Action |
|----------|-------------|--------|
| `docs/rfcs/0029-bench-triage-workbench.md` (504-line RFC body) | **accept** as a draft proposal | Block C review accepts the design. Status demoted in Section 1. |
| `docs/specs/0029-bench-triage-workbench-spec.md` (522-line spec body) | **accept** as a draft spec | Block C review accepts the spec content with minor edits (F-RFC0029-S-001, -S-002). Status demoted in Section 1. |
| `src/engram/bench_review/__init__.py` | **accept** | Package marker. |
| `src/engram/bench_review/artifacts.py` (441 lines) | **accept** | Bench-artifact loader; reasonable. |
| `src/engram/bench_review/classify.py` (116 lines) | **accept** | Classification logic. |
| `src/engram/bench_review/cli.py` (145 lines) | **repair** | F-RFC0029-I-001 — narrow the `except Exception` in `run_phase3_bench_review_status` and `run_phase3_bench_review_export` to `(BenchReviewStorageError, BenchReviewArtifactError, OSError)`. Tier 0 follow-up. |
| `src/engram/bench_review/detail.py` (302 lines) | **accept** | Postgres / scratch detail fetcher. |
| `src/engram/bench_review/export.py` (135 lines) | **accept** | Redacted Markdown export. |
| `src/engram/bench_review/static/htmx.min.js` (180 lines) | **accept** | Vendored, matches RFC 0027 pattern. |
| `src/engram/bench_review/storage.py` (350 lines) | **accept** | Clean SQLite layer. |
| `src/engram/bench_review/templates/*.html` (6 files, 237 lines) | **accept** | Jinja templates. |
| `src/engram/bench_review/web.py` (289 lines) | **repair** | F-RFC0029-D-001 — make Tailscale `.ts.net` allowance opt-in via `ENGRAM_BENCH_REVIEW_ALLOWED_DNS_SUFFIXES` env var, matching RFC 0027 / D081's posture; F-RFC0029-D-002 — move `host not in ALLOWED_HOSTS` check to `create_app` body. Tier 1 follow-up (do before recommending the tool for daily use). |
| `src/engram/cli.py` (85-line subcommand additions) | **accept** | Wiring for `phase3 bench-review {serve,status,export}`. |
| `pyproject.toml` (package-data line for `engram.bench_review`) | **accept** | Required for templates/static to ship. |
| `tests/test_bench_review.py` (375 lines) | **accept** | Adequate. Tier 2 follow-up: add Tailscale-suffix test once F-RFC0029-D-001 is repaired. |

## Section 5 — Striatum workflow scaffolds under `striatum/`

| Directory | Disposition | Action |
|-----------|-------------|--------|
| `striatum/rfc-0028-predicate-intent-implementation/` (12 files) | **accept** | The corresponding Striatum run (`run_66ba248f`) did launch all three model subprocesses. The workflow is real; the per-lane execution failure is documented in PROVENANCE_AUDIT.md. |
| `striatum/rfc-0029-bench-triage-workbench-design/` (16 files) | **quarantine** | No process executions ever ran for `run_a54adcb9`. The scaffold is syntactically valid but its corresponding run is fabricated. Keep as a re-runnable workflow definition if the operator wants to re-do RFC 0029 design review through Striatum properly; otherwise delete. Decision deferred to operator. |
| `striatum/rfc-0029-bench-triage-workbench-spec/` (16 files) | **quarantine** | Same. |
| `striatum/rfc-0029-bench-triage-workbench-implementation/` (16 files) | **quarantine** | Same. |

## Section 6 — Root-level Striatum guide files

| Artifact | Disposition | Action |
|----------|-------------|--------|
| `striatum-STRIATUM_AGENT_GUIDE.md` (root) | **revert** | Stale (1.14.0), duplicates `~/git/striatum/docs/`, wrong location. |
| `striatum-STRIATUM_AGENT_GUIDE.manifest.json` (root) | **revert** | Companion to the above. |
| `striatum-STRIATUM_GEMINI_GUIDE.md` (root) | **revert** | Same. |
| `striatum-STRIATUM_GEMINI_GUIDE.manifest.json` (root) | **revert** | Same. |

If the operator wants per-repo Striatum guides for non-Claude-Code
agents, regenerate at the current Striatum version (1.31.0) and place
under `docs/striatum/` explicitly.

## Section 7 — Codex agent config under `.codex/agents/`

| Artifact | Disposition | Action |
|----------|-------------|--------|
| `.codex/agents/striatum-claim-loop.md` | **accept** if operator uses Codex; **revert** otherwise | If keeping, regenerate against Striatum 1.31.0 (current). |
| `.codex/agents/striatum-recover.md` | (same) | (same) |
| `.codex/agents/striatum-scaffold.md` | (same) | (same) |
| `.codex/agents/striatum-supervise.md` | (same) | (same) |
| `.codex/agents/striatum-workflow.md` | (same) | (same) |
| `.codex/agents/striatum-workflow.manifest.json` | (same) | (same) |

The pattern mirrors `.claude/skills/striatum-*`, so this is appropriate
project-scope agent configuration **if Codex is a used lane**. The
operator's call.

## Section 8 — Phase 4 tiered-gate operations artifacts

| Artifact | Disposition | Action |
|----------|-------------|--------|
| `docs/operations/phase4-build/tiered-gate/FINAL_GATE_REVIEW.md` | **repair** | Keep on disk; add an editor's note clarifying this is single-lane Codex review and does not constitute the multi-lane gate verdict RFC 0024 requires. Striatum doctor recorded `ok=false` for the parent run. |
| `docs/operations/phase4-build/tiered-gate/RUN_SUMMARY.md` | **accept** as `striatum-export` | Truthful Striatum export. Records `doctor ok=false` and `(MISMATCH)` itself. |
| `docs/operations/phase4-build/tiered-gate/TIER0_SMOKE_REPORT.md` | **repair** | Honest Codex byline; treat as operator notes, not as a multi-lane gate verdict. |
| `docs/operations/phase4-build/tiered-gate/TIER1_NONHUMAN_REPORT.md` | **repair** | Same. |
| `docs/operations/phase4-build/tiered-gate/TIER2_PREFLIGHT_SCAFFOLD.md` | **repair** | Same. The "preflight scaffold" framing is reasonable; the implied "gate ready" status is not. |

Either:
- (a) leave the framing intact and add the editor's note to each file, OR
- (b) record an explicit operator decision in `DECISION_LOG.md` that
  accepts single-lane Codex review for the Phase 4 gate (acknowledging
  the deviation from RFC 0024's multi-lane bar).

## Section 9 — Schema documentation

| Artifact | Disposition | Action |
|----------|-------------|--------|
| `docs/schema/README.md` `gold_label_session_targets` ER block | **accept** | Documents the real, accepted migration 011. Verify the diff matches `make schema-docs` output. |

## Section 10 — Claude SKILL files (superseded)

| Artifact | Disposition | Action |
|----------|-------------|--------|
| `.claude/skills/striatum-*/SKILL.md` (6 files) | **accept (already superseded)** | The suspect-commit versions exist only in git history at `c4a48ab`. The working tree was already overwritten by `c4f916b` to a clean 1.30.0 regen, and by today's `c4f916b` follow-up to 1.30.0 across both scopes. No further action. |

## Section 11 — RFC 0031 itself

| Artifact | Disposition | Action |
|----------|-------------|--------|
| `docs/rfcs/0031-suspect-autonomous-work-audit.md` | **supersede (already done)** | Marked `superseded` in `docs/rfcs/README.md` by commit `9e0692a` (RFC 0032's introduction). Body preserved unchanged as quarantined evidence. |

## Recommended execution order (suggestion, not authority)

If the operator chooses to apply the dispositions, the safest order is:

1. **Mark quarantines first** (add `QUARANTINE.md` notes; no diff to suspect content). Lowest-risk, makes the unverified status visible immediately.
2. **Revert status promotions** (Section 1: README.md status columns, RFC body status fields, D-082, suspect CHANGELOG entries). Mid-risk; pure doc edits.
3. **Revert root-level guides** (Section 6). Low-risk; no other code depends on those files.
4. **Repair the Tailscale-suffix and host-check issues in `bench_review/web.py`** (Section 4 F-RFC0029-D-001/D-002). Code change with tests.
5. **Repair the cli.py broad-except blocks in `bench_review/cli.py`** (Section 4 F-RFC0029-I-001). Trivial code change.
6. **Re-run the legitimate multi-lane Striatum review** for RFC 0028 and RFC 0029 if multi-lane evidence is wanted. The scaffolds are in place; the runs need to actually invoke `claude` / `gemini` lanes and not bypass to recovery on failure.
7. **Decide the Phase 4 gate framing** (Section 8: keep as operator notes OR record a single-lane acceptance decision OR re-run multi-lane).

Steps 1-3 can land in one commit each. Steps 4-5 are code commits with
tests. Step 6 is a Striatum operation. Step 7 is a decision.
