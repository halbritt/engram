You are the RFC 0038 accept-with-findings bench implementer. Stay inside your
write scope and do not edit interview, shared substrate, migrations, or
canonical docs.

Use the corrected security and ergonomics reviews as the source of truth.
Address bench-owned findings:

- FU102: consolidate bench keyboard behavior onto the shared dispatcher where
  feasible; keep only a small bench-specific queue-filter enhancement.
- CS001: adopt the shared tier helper where feasible without changing current
  denial behavior.

Preserve local-only/no-CDN posture, scratch-local review state, and production
read-only behavior. Use maximal useful internal sub-agents if available, with
disjoint ownership inside this lane. Publish the required handoff with changed
files, commands, finding disposition, and remaining risk.
