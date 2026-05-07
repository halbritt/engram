<a id="docs-operations-readme"></a>
# Operations

Status: accepted (RFC 0014, D066, 2026-05-06)
Source RFC: [RFC-0014](../rfcs/0014-operational-artifact-home.md)
Spec: [operational-artifact-home-spec.md](../process/operational-artifact-home-spec.md)
Decision refs:
  - D066

This directory is the committed home for redacted development operational
artifacts — the things `agent_runner` (Striatum) and the Phase 3 post-build
loop produce as they run. Per RFC 0014 and D066, `docs/operations/` is the
**only** place new operational reports and markers should land going forward.

## What lives here

| Path | Purpose |
|------|---------|
| `docs/operations/<area>/<loop_id>/reports/` | Human-readable redacted prose run reports (RUN, REPAIR_PLAN, REPAIR_VERIFIED). |
| `docs/operations/<area>/<loop_id>/markers/` | Machine-readable gate markers (`blocked`, `ready`, `human_checkpoint`). The script `scripts/phase3_tmux_agents.sh` reads these. |

`<area>` is phase-scoped (S002): Phase 3 post-build work uses
`docs/operations/phase3-postbuild/<YYYYMMDD>_<run_slug>/`. `<loop_id>` is
typically `<YYYYMMDD>_<short-slug>`.

## What does NOT live here

- **Multi-agent reviews** — those stay under `docs/reviews/` (S005). Reviews
  are model feedback and synthesis, not gate state.
- **Untracked local diagnostics** — those stay under `logs/operational/`,
  which is gitignored. Private corpus content goes there, never here (S011).
- **Legacy RFC 0013 markers** — these remain in place under
  `docs/reviews/phase3/postbuild/markers/` until the owner explicitly asks
  for history cleanup (RFC 0014 §Migration Plan). The marker scanner reads
  legacy and new roots as one logical set during transition (S007, S010).

## Marker schema

Markers carry RFC 0013-style front matter with one stricter rule:
`corpus_content_included: none` is mandatory. See the spec at
`docs/process/operational-artifact-home-spec.md` § Marker Schema for the full
contract.

Reports do not have machine-readable state; they are prose. Only marker files
carry `.blocked`, `.ready`, or `.human_checkpoint` suffixes.

## Privacy and redaction

Same rules as RFC 0013 §3 (S006 unchanged). Markers are stricter than
reports; markers may not carry private corpus content even with owner
approval. If private content is needed for repair triage, it goes in ignored
local diagnostics under `logs/operational/`, with only a redacted summary
linked from a tracked report.

## Path hygiene

D060 enforces relative paths in tracked docs. Markers in particular must use
repository-relative POSIX paths in `linked_report` and `supersedes` front
matter — no `/home/<user>/`, no `~/`, no absolute paths.

## Migration status

As of 2026-05-07, this directory exists but has no live loops yet. Phase 3
post-build markers continue to land in the legacy RFC 0013 path
(`docs/reviews/phase3/postbuild/markers/`) until the next post-build run.
The first new loop landing under `docs/operations/phase3-postbuild/` will
also `supersedes:` its corresponding legacy markers per S007.

The marker scanner (`scripts/phase3_tmux_agents.sh`) already reads both
roots, so adding `docs/operations/` does not break existing gates.
