# Tier 2 Bounded Production Preflight Scaffold

Prepare the RFC 0024 Tier 2 bounded production preflight scaffold. Do not ask
for human input. Do not run full corpus. Do not treat this job as promotion.

Use `docs/operations/phase4-build/tiered-gate/TIER1_NONHUMAN_REPORT.md` as
input. If Tier 1 records missing RFC 0021 human-label evidence, preserve that
as a blocker for promotion while still preparing the bounded preflight.

Run dry-run checks for bounded commands:

```sh
make -n phase4-smoke LIMIT=500
make -n phase4-build-entities LIMIT=500
.venv/bin/python -m engram.cli phase4 smoke --help
.venv/bin/python -m engram.cli phase4 build-entities --help
.venv/bin/python -m engram.cli phase4 run
```

The final command should fail because RFC 0025 intentionally keeps
`phase4 run` absent until the RFC 0024 gates are complete.

Write `docs/operations/phase4-build/tiered-gate/TIER2_PREFLIGHT_SCAFFOLD.md`.
Include:

- bounded command plan;
- required production database/model endpoint assumptions;
- required aggregate-only report shape;
- expected no-failed/no-in-flight checks;
- duplicate-active-entity, provenance, current-beliefs, review-queue, and p95
  latency checks;
- explicit statement that this scaffold does not authorize full corpus.
