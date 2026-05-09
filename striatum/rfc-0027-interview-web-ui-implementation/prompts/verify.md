# Verify RFC 0027 Web UI Implementation

Verify the implementation against `docs/specs/0027-interview-web-ui-spec.md`.
Do not modify source, tests, migrations, Makefile, pyproject, prompts,
or docs outside the expected report path.

## Run these checks

```sh
git diff --stat HEAD~1 HEAD 2>&1 || git status --short
make check-refs 2>&1 | tail -3
.venv/bin/python -m pytest tests/test_interview_render.py tests/test_interview_cli.py tests/test_interview_sampler.py tests/test_interview_storage.py -x
.venv/bin/python -m pytest tests/test_interview_web.py -x
.venv/bin/python -m pytest tests/test_migrations.py -x
.venv/bin/python -c "from engram.interview.web import app; print('app ok')"
.venv/bin/python -c "
import engram.interview.web as w
import sys
mods = [m for m in sys.modules if 'consolidator.transitions' in m]
assert not mods, f'Web imports forbidden module: {mods}'
print('D044/D069 import guard: ok')
"
.venv/bin/engram phase3 interview --help 2>&1 | head -15
.venv/bin/engram phase3 interview serve --help 2>&1 | head -15
ls migrations/011_gold_label_session_targets.sql
ls src/engram/interview/render.py src/engram/interview/web.py
ls src/engram/interview/templates/
ls src/engram/interview/static/htmx.min.js
grep -c "phase3-interview-serve" Makefile
grep -A2 "optional-dependencies" pyproject.toml | head -10
grep "package-data" pyproject.toml
```

## Specifically confirm

1. `migrations/011_gold_label_session_targets.sql` exists, parses, and
   applies. `fn_gold_label_session_targets_append_only` trigger raises
   on UPDATE/DELETE.
2. `src/engram/interview/render.py` exists and exports the full
   extraction surface from spec § render.py API.
3. `src/engram/cli.py` no longer defines underscore-prefixed
   verdict/evidence/render helpers; it imports them from `render.py`.
   Existing `tests/test_interview_cli.py` still passes.
4. `tests/test_interview_render.py` exists; golden-output tests pin
   the rendered text shape.
5. `src/engram/interview/web.py` exists; routes from spec § Routes
   are present (GET `/`, POST `/sessions`, GET
   `/sessions/{id}/q/{idx}`, POST `/sessions/{id}/q/{idx}/verdict`,
   GET `/sessions/{id}/messages/{message_id}`, GET
   `/sessions/{id}/messages/{message_id}/context`, GET
   `/sessions/{id}/q/{idx}/evidence/all`, POST
   `/sessions/{id}/save-and-quit`, POST `/sessions/{id}/complete`,
   POST `/sessions/{id}/abandon`).
6. `src/engram/interview/templates/` contains `base.html`,
   `index.html`, `question.html`, `_evidence_excerpt.html`,
   `_strata_strip.html`.
7. `src/engram/interview/static/htmx.min.js` is present (vendored, no
   CDN reference reachable from any rendered page).
8. `engram phase3 interview serve --help` lists `--host`, `--port` and
   does not list `--allow-non-loopback`.
9. `Makefile` has `phase3-interview-serve` with `HOST` and `PORT`
   variables.
10. `pyproject.toml` has `[project.optional-dependencies] serve` and
    `[tool.setuptools.package-data]` block.
11. Origin allowlist test passes (POST with non-localhost Origin → 403).
12. Tier 1 ceiling tests pass (Tier 2+ on `/messages/{id}` → 403).
13. D044/D069 import guard test passes (web module does not import
    `engram.consolidator.transitions`).
14. `run_phase3_interview_start` writes `gold_label_session_targets`
    rows; CLI-started sessions are web-resumable.

## Output

Write `docs/reviews/rfc0027-interview-web-ui-implementation/VERIFICATION_REPORT.md`
with the work-packet author byline (line 2), a commands-run table with
exit codes and trimmed stdout, ## Findings (V### with Severity / Source
/ Rationale), ## Residual risks, final `verdict:` line.

If a check cannot be run (e.g., DB not available locally), record why.
Use `accept` / `accept_with_findings` / `needs_revision` per the
Striatum work packet.
