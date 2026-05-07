<a id="docs-operations-readme"></a>
# Operations

Status: accepted (RFC 0014, D066, 2026-05-06); amended by D074 (markers retired) on 2026-05-07
Source RFC: [RFC-0014](../rfcs/0014-operational-artifact-home.md)
Spec: [operational-artifact-home-spec.md](../process/operational-artifact-home-spec.md)
Decision refs:
  - D066
  - D074

This directory is the committed home for redacted development operational
**reports** — the prose run / repair / verification artifacts that
Striatum-orchestrated multi-agent loops produce. Per RFC 0014 (D066),
`docs/operations/` is the canonical destination for those committed
artifacts. Per D074, gate state is **not** tracked here: live job state,
blockers, verdicts, and `human_checkpoint` severity all live in Striatum's
SQLite store at `.striatum/state.sqlite3`.

## What lives here

| Path | Purpose |
|------|---------|
| `docs/operations/<area>/<loop_id>/reports/` | Human-readable redacted prose run reports (RUN, REPAIR_PLAN, REPAIR_VERIFIED). |

`<area>` is phase-scoped (S002): Phase 3 post-build work uses
`docs/operations/phase3-postbuild/<YYYYMMDD>_<run_slug>/`; Phase 4 will use
`docs/operations/phase4-build/<...>/`, etc. `<loop_id>` is typically
`<YYYYMMDD>_<short-slug>`.

## What does NOT live here

- **Multi-agent reviews** — those stay under `docs/reviews/` (S005). Reviews
  are model feedback and synthesis, not gate state.
- **Untracked local diagnostics** — those stay under `logs/operational/`,
  which is gitignored. Private corpus content goes there, never here.
- **Marker files for new loops** — D074 retired the marker mechanism. Live
  gate state lives in Striatum (`.striatum/state.sqlite3`); read it with
  `striatum list jobs --run-id <id>`, `striatum status`, or `striatum why`.
- **Legacy RFC 0013 markers** — these remain in place under
  `docs/reviews/phase3/postbuild/markers/` as audit provenance for
  in-flight Phase 3 work. New loops do not produce markers.

## Gate state lives in Striatum

D074 designates Striatum's SQLite as the authoritative state for new
operational loops. Common queries:

```sh
# Is anything blocked in this run?
striatum list jobs --run-id <id> --state blocked

# What checkpoints need human attention?
striatum status --run-id <id>

# Why is this job stuck?
striatum why --job-id <id>
```

Owner decisions that resolve a `human_checkpoint` are recorded as durable
Markdown via `striatum decision record --outcome accepted`. Decision
artifacts land under the workflow's configured `write_scope`.

## Privacy and redaction

Reports follow RFC 0013 §3 (S006 carries forward as report-level rules
post-D074). The privacy carry from RFC 0014:

- Tracked reports are redacted prose. Owner-approved private detail is
  permitted only when the report explicitly records the approval per
  RFC 0013.
- Private repair evidence goes to ignored `logs/operational/`. Tracked
  reports may link only to a redacted summary.
- Striatum enforces a default-deny evidence redaction registry at the
  publish-artifact layer; see `src/striatum/cli/evidence.py` in the
  Striatum repo.

## Path hygiene

D060 enforces relative paths in tracked docs. `linked_report:` and similar
artifact references in committed reports must use repository-relative
POSIX paths — no `/home/<user>/`, no `~/`, no absolute paths.

## Migration status

As of 2026-05-07:

- This directory exists with no live loops yet.
- Phase 3 post-build markers under `docs/reviews/phase3/postbuild/markers/`
  are preserved as audit provenance per D074 — they are not deleted, but no
  new markers join them.
- `scripts/phase3_tmux_agents.sh` continues to scan legacy markers so any
  in-flight Phase 3 gate stays operational. It is not the pattern for new
  phases — Phase 4 and later use Striatum directly.
- The first new loop landing under `docs/operations/<area>/<loop_id>/` writes
  only the `reports/` subtree; no markers.
