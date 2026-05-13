# CODE_REVIEW — Cross-cutting Technical Findings

| Field | Value |
|-------|-------|
| Audit block | C |
| Author | Claude Code |
| Date | 2026-05-13 |
| Scope | Items not specific to RFC 0028 or RFC 0029 implementation: test-suite status, Striatum workflow scaffolds, root-level Striatum guide files, `.codex/agents/` files, Phase 4 tiered-gate operations artifacts, `docs/schema/README.md`, Claude skill SKILL files. |
| Companion docs | [CODE_REVIEW_RFC0028.md](CODE_REVIEW_RFC0028.md), [CODE_REVIEW_RFC0029.md](CODE_REVIEW_RFC0029.md) |

## Test suite status

Command run during this audit:

```
ENGRAM_TEST_DATABASE_URL=postgresql:///engram_test \
  .venv/bin/pytest -q \
  --ignore=tests/test_benchmark_segmentation.py \
  --ignore=tests/test_benchmark_extraction_backend.py
```

Result: **430 passed, 1 failed in 210s**.

The two ignored files fail at import (`ModuleNotFoundError: No module
named 'benchmarks'`) because the `benchmarks/` tree is not on
`sys.path` in this environment. Those failures predate the suspect
commit and are environmental, not code-correctness, signals.

### The one real failure

```
tests/test_phase3_claims_beliefs.py::test_cli_pipeline_is_phase2_only_and_pipeline3_warns
  AssertionError: assert 2 == 0
  +  where 2 = cli.main(['pipeline', '--limit', '1'])

  ambiguous command: pipeline
  Use one of:
    engram phase2 run
    engram phase3 run
    engram phase4 smoke
```

**This failure is not caused by the suspect commit.** The test was
introduced by `2de6123 Implement Phase 3 claims pipeline` (a real,
pre-suspect commit) and pins the behavior of the bare `pipeline`
subcommand. The RFC 0025 command-surface implementation
(`12e2111 Implement RFC 0025 command surface`, also pre-suspect)
deprecated the bare form in favor of `engram phase2 run`,
`engram phase3 run`, etc. The test was not updated when RFC 0025
landed.

This is a **pre-existing regression in the legitimate work** that the
suspect commit happened to surface (because every developer running
the test suite now sees it). Fixing it is out of scope for RFC 0032 —
it belongs in a separate small commit that either updates the test to
assert the new ambiguous-command behavior or adds the missing
backward-compatibility alias.

**Recommendation:** flag for a separate follow-up commit. Not a
disposition decision for this audit.

## Striatum workflow scaffolds (under `striatum/`)

The suspect commit adds four new workflow directories:

- `striatum/rfc-0028-predicate-intent-implementation/`
- `striatum/rfc-0029-bench-triage-workbench-design/`
- `striatum/rfc-0029-bench-triage-workbench-spec/`
- `striatum/rfc-0029-bench-triage-workbench-implementation/`

Each contains `RUNBOOK.md`, `SOURCES.md`, a `prompts/` directory, a
`roles/` directory, and a `workflow.json`. The `workflow.json` files
validate against `striatum.workflow.v1` (sampled `rfc-0028-predicate-intent-implementation/workflow.json` — well-formed JSON with the
expected fields: `name`, `workflow_id`, `schema_version`, `lanes`,
`jobs`, `edges`, `roles`).

Findings:

### F-WF-001 — Scaffolds define real multi-lane workflows that were not actually executed

**Severity:** documentation.

The `lanes` block correctly declares external-model lane commands:

```json
"claude": {"command":["claude","--model","opus","-p"]},
"codex":  {"command":["codex","exec","--model","gpt-5.5","-"]},
"gemini": {"command":["gemini","--model","gemini-3.1-pro-preview"]}
```

The workflows themselves are syntactically correct and would run if
the operator started them properly via `striatum run start`. Block B
established that for three of the four runs, the model lanes never
actually launched (zero `process_executions` rows). The scaffolds are
not broken — they were just not used as intended.

**Recommendation:** keep the scaffolds for the RFC 0028 workflow
(its run did actually launch all three model lanes, even though those
lanes failed to produce output). For the three RFC 0029 workflow
directories, the disposition depends on whether the operator intends
to re-run them properly through Striatum to re-do RFC 0029 review.
Disposition in Block D.

### F-WF-002 — Workflow definitions sit inside the application repo

**Severity:** moderate.

The four `striatum/rfc-*` directories materially mix two concerns:

- **Engram** code, schema, docs, tests.
- **Striatum** workflow definitions for reviewing Engram changes.

The canonical home for Striatum workflow templates is `~/git/striatum`
(see [reference memory entry](../../../../../.claude/projects/-home-halbritt-git-engram/memory/reference_striatum_docs.md)).
Engram-specific workflow definitions can legitimately live in the
Engram repo, but the pattern is worth questioning when those
definitions are 60+ files per RFC.

Compare with how `phase-4-spec-review/` and `phase-4-tiered-gate/`
sit in the Engram repo — they were also added by prior real commits
and exhibit the same mixing. So this is a longstanding pattern, not
new with the suspect commit.

**Recommendation:** keep the pattern (consistent with prior practice)
but consider in the forward roadmap whether
`striatum/rfc-*-implementation/` directories should migrate to the
`docs/striatum/` subtree to make the "workflow-for-this-RFC" boundary
clearer. Not a Block D disposition; tag for FORWARD_PATH.md.

## Root-level Striatum guide files

The suspect commit adds four files **at the Engram repo root**:

- `striatum-STRIATUM_AGENT_GUIDE.md` (128 lines)
- `striatum-STRIATUM_AGENT_GUIDE.manifest.json` (16 lines)
- `striatum-STRIATUM_GEMINI_GUIDE.md` (135 lines)
- `striatum-STRIATUM_GEMINI_GUIDE.manifest.json` (16 lines)

The content is the generic-profile Striatum agent guide, generated by
`striatum 1.14.0`. The same content also exists in canonical form at
`~/git/striatum/docs/`.

### F-GUIDE-001 — Root-level placement is anomalous

**Severity:** moderate / hygiene.

Engram's repo root contains `README.md`, `CHANGELOG.md`,
`DECISION_LOG.md`, `AGENTS.md`, `CLAUDE.md`, `BUILD_PHASES.md`,
`HUMAN_REQUIREMENTS.md`, `ROADMAP.md`, `SPEC.md`, `Makefile`,
`pyproject.toml`, and the four `striatum-STRIATUM_*` files added by
the suspect commit. The root convention is project-level top-of-tree
documents; the Striatum guides are tooling, not Engram project docs.

The naming pattern `striatum-STRIATUM_*` with double-prefixing also
suggests these were the output of `striatum skills install --profile
generic --scope project` writing to the repo root rather than to a
subdirectory.

**Recommendation:** **delete**. These files are stale (striatum 1.14.0;
current is 1.31.0 per the just-regenerated `.claude/skills/`), they
duplicate canonical content in `~/git/striatum/docs/`, and their
placement does not match repo convention. The Block D disposition is
`revert` (remove from the working tree via a new commit). If a
generic-profile Striatum guide is wanted in the Engram repo, the right
home is `docs/striatum/` and the regeneration should be explicit.

## `.codex/agents/` files

Six files added under `.codex/agents/`:

- `striatum-claim-loop.md` (110)
- `striatum-recover.md` (65)
- `striatum-scaffold.md` (59)
- `striatum-supervise.md` (59)
- `striatum-workflow.md` (48)
- `striatum-workflow.manifest.json` (40)

These mirror the equivalent `.claude/skills/striatum-*` files,
configuring the Codex agent to know about Striatum slash commands.

### F-CODEX-001 — Codex agent config legitimately lives in the repo

**Severity:** none / informational.

Multi-agent setups using Codex as one lane benefit from per-repo
`.codex/agents/` configuration. The files mirror the `.claude/skills/`
pattern (which is canonical project-scope skill configuration). The
Codex agent config is therefore appropriate to keep — but should be
regenerated against the current Striatum version if the operator wants
1.31.0 features.

**Recommendation:** `accept` if the operator uses Codex as a lane;
`revert` if not. The operator's call. Tag in
[ARTIFACT_DISPOSITION.md](ARTIFACT_DISPOSITION.md).

## Phase 4 tiered-gate operations artifacts

Five files added under `docs/operations/phase4-build/tiered-gate/`:

- `FINAL_GATE_REVIEW.md` (45 lines)
- `RUN_SUMMARY.md` (43 lines)
- `TIER0_SMOKE_REPORT.md` (89 lines)
- `TIER1_NONHUMAN_REPORT.md` (121 lines)
- `TIER2_PREFLIGHT_SCAFFOLD.md` (131 lines)

These came from `run_97962575` (Block B). All bylines are honest
Codex (`reviewer-codex-gpt-5.5-001`, `operator-codex-gpt-5.5-001/002/003`).
Striatum's own `doctor` flagged the run as `ok=false` with a
`(MISMATCH)` warning between recorded branch and working-tree branch.

Content sampling: `FINAL_GATE_REVIEW.md` contains a "no blocking
findings" verdict tempered by an F001 noting that human-label and
review-queue UX evidence remain a promotion blocker. That is a
reasonable position consistent with RFC 0024's gate semantics.

### F-PHASE4-001 — Single-lane Codex review is the entire evidence base

**Severity:** moderate.

The Phase 4 gate is a high-consequence decision per RFC 0024. Single-
lane Codex authorship without multi-lane review is below the bar that
RFC 0024 sets for promotion-grade evidence (RFC 0024 explicitly cites
the need for independent review of pre-full-corpus benchmark results).

The bylines do not lie about who authored the reports; the framing as
a "tiered gate review" is what is suspect.

**Recommendation:** `repair`. Keep the artifacts on disk as historical
operator notes; do not treat them as the gate verdict. The actual
Phase 4 gate decision needs either (a) a multi-lane re-review through
Striatum or (b) an explicit operator decision recorded in
`DECISION_LOG.md` that accepts single-lane Codex review for this gate.

## `docs/schema/README.md` changes

The suspect commit adds a `gold_label_session_targets` ER block (152
lines). Migration 011 (the underlying schema) is **real** and accepted
via D080 before the suspect burst.

### F-SCHEMA-001 — Schema docs addition is documentation of legitimate prior work, not a suspect addition

**Severity:** none.

Running `make schema-docs` (per Makefile target,
`scripts/gen_schema_docs.py` against the live DB) would presumably
regenerate the same content. The block adds the migration-011 table
into the ER diagram cluster where it belongs.

**Recommendation:** `accept`. Independently of the audit, verify the
diff matches `make schema-docs` output by running the script and
diffing; if clean, no action needed.

## Claude SKILL files under `.claude/skills/striatum-*`

The suspect commit modifies 6 SKILL files. These have since been
**overwritten** by the legitimate `c4f916b` skills regeneration to
version 1.30.0 (committed post-suspect, before this RFC 0032 work).
The historical suspect versions exist only in git at `c4a48ab` and are
not part of the working tree.

### F-SKILLS-001 — No action needed

**Severity:** none.

The working-tree SKILL files are clean. Block D should record
"superseded by `c4f916b`" and move on.

## Cross-cutting recommendations

### Privacy

No new privacy regressions identified in the implementation code:

- Bench review storage stores only identifiers, decisions, and notes
  in scratch SQLite — not segment text, not claim text.
- Bench review web UI declares `loopback-only` at startup and 403s on
  non-loopback request hosts.
- Interview render layer still respects RFC 0027's Tier 1 ceiling.
- Extraction prompt does not exfiltrate any new fields — only
  per-predicate description and subject-kind hint, which are already
  in the DB.

### Append-only / raw-evidence integrity

Migration 012 touches `predicate_vocabulary`, which is configuration
data, not raw evidence. Append-only constraints from AGENTS.md apply
to raw evidence tables; configuration tables are mutable. No
violation.

### Striatum-operated provenance integrity

The cross-cutting failure underlying the suspect commit is that
**Striatum's recovery path and the operator's discretion together
allowed multi-lane review artifacts to be published under model
bylines without the corresponding model subprocess actually
producing the content**. This is a Striatum-side concern (or a
Striatum-config concern) more than an Engram-code concern, but it
shaped the entire suspect commit. The forward path should consider:

- A Striatum-side option to refuse `striatum publish-artifact` for a
  lane whose subprocess produced no output.
- An Engram-side `make` target that quickly verifies the
  `(process_executions, artifacts)` cross-product for any tracked
  Striatum run before its outputs are committed to `master`.

Both are FORWARD_PATH.md items, not Block D dispositions.

## Block D handoff

Block D should consume:

- Per-RFC findings from [CODE_REVIEW_RFC0028.md](CODE_REVIEW_RFC0028.md)
  and [CODE_REVIEW_RFC0029.md](CODE_REVIEW_RFC0029.md).
- The cross-cutting recommendations in this document.
- The provenance classifications from
  [PROVENANCE_AUDIT.md](PROVENANCE_AUDIT.md).
- The inventory in [INVENTORY.md](INVENTORY.md).

And produce per-artifact dispositions, an operator-facing FINAL
DECISION, and a forward-path pointer document.
