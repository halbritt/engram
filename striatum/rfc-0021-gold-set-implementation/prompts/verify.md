# Verify RFC 0021 Gold-Set Implementation

Verify the implementation against the accepted RFC and implementation
handoff. Do not modify source, tests, Makefile, migrations, prompts, or
docs outside the expected report path.

Run focused local checks. Prefer:

```sh
git diff --check
make check-refs
.venv/bin/python -m pytest tests/test_interview_cli.py tests/test_interview_sampler.py tests/test_interview_storage.py
.venv/bin/engram phase3 interview --help
.venv/bin/engram phase3 interview export --help
.venv/bin/engram --help
```

Specifically confirm:

1. `engram phase3 interview` subcommands dispatch (start, resume,
   history, export, list-sessions, coverage, enable-active-learning).
2. `engram phase3 interview export` defaults to Tier 1 ceiling
   (`--privacy-tier-max 1`).
3. No bare `engram interview` namespace exists at the top level.
4. Migration 010 file exists and parses (run `python3 -c "import
   pathlib; pathlib.Path('migrations/010_gold_labels.sql').read_text()"`
   or attempt `make migrate-docker` if the test DB is available).
5. The append-only trigger is named `fn_gold_labels_append_only` and
   the parent-validation trigger is `fn_gold_labels_validate_target`
   per RFC § Storage.
6. `prompts/interview/claim_v1.md` and `prompts/interview/belief_v1.md`
   exist and match the `prompt_template_version` strings in the code.
7. Tests pass deterministically; no live LLM calls.
8. `make phase3-interview-start --help` (or equivalent inspection)
   shows the target wired.

If a check cannot be run safely (e.g., DB not available locally), record
why.

Write `docs/reviews/rfc0021-gold-set-implementation/VERIFICATION_REPORT.md`
with the exact lowercase `author:` line from the work packet, the
commands run, results, failures, and residual risks. Use `accept`,
`accept_with_findings`, or `needs_revision` according to the Striatum
work packet.
