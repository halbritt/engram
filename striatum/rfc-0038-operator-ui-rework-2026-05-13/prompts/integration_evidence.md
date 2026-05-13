# Run RFC 0038 UI Integration Evidence

Read the three implementation handoffs, then run focused verification for the
combined UI rework.

Do not edit implementation files. You may add only the required evidence
artifact under `docs/reviews/rfc0038-operator-ui-rework-2026-05-13/`.

Run the strongest practical focused checks, including:

- `git diff --check`
- `make check-refs`
- interview route/render tests
- bench-review tests
- any new shared UI tests
- no-CDN/static reference checks

Required artifact:

`docs/reviews/rfc0038-operator-ui-rework-2026-05-13/INTEGRATION_EVIDENCE.md`

Include commands, results, failures if any, and residual risk.
