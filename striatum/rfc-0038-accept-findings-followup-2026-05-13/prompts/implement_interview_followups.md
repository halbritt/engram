You are the RFC 0038 accept-with-findings interview implementer. Stay inside
your write scope and do not edit bench, shared substrate, migrations, or
canonical docs.

Use the corrected security and ergonomics reviews as the source of truth.
Address the interview-owned findings:

- FU101: make the interview -> bench surface tab usable or visibly disabled.
  Prefer a symmetric `ENGRAM_INTERVIEW_BENCH_URL` configuration with a safe
  default and route tests.
- CS001: adopt shared origin/tier helpers where feasible without changing
  strict same-origin behavior.
- CS002: make the interview audit footer source the bind address from
  configuration or fail loud; do not silently render a hard-coded wrong port.
- FU103: replace interview-local banner sections with the shared status banner.
- FU104: remove duplicate interview copy-command handling while preserving htmx
  busy-state behavior.

Use maximal useful internal sub-agents if available, with disjoint ownership
inside this lane. Publish the required handoff with changed files, commands,
finding disposition, and remaining risk.
