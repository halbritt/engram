# Verify RFC 0025 Command Surface

Verify the implementation against the accepted RFC and implementation handoff.
Do not modify source, tests, Makefile, or docs outside the expected report path.

Run focused local checks that are appropriate for the diff. Prefer:

```sh
git diff --check
make check-refs
.venv/bin/python -m pytest tests/test_cli.py
```

Also inspect or dry-run the Make targets enough to confirm that generic
pipeline targets fail closed and phase-scoped targets exist. If a check cannot
be run safely, record why.

Write `docs/reviews/rfc0025-command-surface-implementation/VERIFICATION_REPORT.md`
with the exact lowercase `author:` line from the work packet, the commands run,
results, failures, and residual risks. Use an `accept`, `accept_with_findings`,
or `needs_revision` verdict according to the Striatum work packet.
