# RFC 0012: Python Agentic Coding Standard

Status: proposal
Date: 2026-05-05

This is an idea-capture RFC, not an accepted decision. It proposes a small,
explicit, pattern-driven coding standard for the Python source under
`src/engram/`, intended to make the codebase legible to both human and agentic
contributors and to give review a fixed surface to compare against.

## Background

Engram is increasingly authored and reviewed by a mix of humans and coding
agents. The existing `AGENTS.md` and `docs/process/project-judgment.md` cover
*what* to work on and *how to coordinate*. There is no document that pins
*how Python in this repo is supposed to look* — type-hint expectations,
exception discipline, environment-variable conventions, worker shape, test
determinism, formatter, type-checker, and so on.

Two empirical observations from 2025–2026 motivate writing this down rather
than leaving it implicit:

1. Agents pattern-match against examples. Guidelines that work for AI agents
   are more explicit, more demonstrative, and lean on do/don't pairs more
   than guidelines aimed only at humans.[^so][^minimaxir] The same artefact
   is also useful to a human reviewer, because it makes "is this normal for
   this repo?" a checkable question.
2. The agent's feedback loop dominates output quality. "The better the
   feedback loop to the machine, the better the results."[^ronacher] A
   pinned linter, type-checker, and test runner — with `make` targets — is
   the cheapest way to give that loop something to react to.

The proposal is a thin standard plus a small toolchain. It does not
introduce new abstractions, new dependencies beyond local dev tooling, or
new process. It is meant to fit on top of what is already here.

## Non-Goals

- Not a rewrite. This RFC does not propose mass-reformatting the codebase,
  changing existing public signatures, or relitigating naming.
- Not an architecture change. RFC 0001 still owns supervisor / controller
  shape; RFC 0007 still owns artifact ID model; this RFC owns *how the
  Python is written*.
- Not a CI mandate. Adoption is local-tool first. A blocking gate is a
  later, separate decision after the baseline is clean.
- Not a process document. Review loop and judgment guidance live in
  `docs/process/`.

## Why A Standard, Not A Style Guide

A style guide tells humans what looks nice. A coding standard for an
agentic codebase has a different job:

- It must be *machine-checkable* where possible, because that is the
  fastest feedback loop available to an agent in a single turn.
- It must be *pattern-driven*, because both LLMs and reviewers extrapolate
  from the nearest existing example.
- It must encode the *project invariants* the system already depends on
  (local-first, no telemetry, idempotent re-derivation, versioned
  prompts/models), so an agent that follows the standard cannot
  accidentally violate them.
- It must be *small enough to read in one pass* before editing, otherwise
  it does not get read.

The standard below tries to satisfy all four.

## Toolchain

Pin the following dev dependencies in `pyproject.toml`'s `[project.optional-dependencies].dev`:

- `ruff` — lint and format (replaces black, isort, flake8, pyupgrade).
- `pyright` — static type-check. Chosen over mypy because it is faster, has
  no plugin requirement for `psycopg`, and is the basis for editor
  integration in VS Code; mypy remains acceptable as an alternative if it
  lands first in CI.
- `pytest` — already pinned.

Add three Makefile targets that wrap them:

```text
make lint        # ruff check . && ruff format --check .
make format      # ruff format .
make typecheck   # pyright src tests
```

Configure ruff in `pyproject.toml`. Suggested baseline:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E", "F", "W",      # pycodestyle / pyflakes
    "I",                # isort
    "B",                # bugbear (mutable defaults, etc.)
    "UP",               # pyupgrade
    "SIM",              # simplify
    "RUF",              # ruff-specific
    "TID",              # tidy imports
]
ignore = []
```

Configure pyright in `pyproject.toml` with `strict = false` initially and
tighten as findings drop. The goal is "no new violations on touched files,"
not a flag day.

These tools are local, do not require network, and do not introduce hosted
services, so they are compatible with the project's local-first
constraint.

## Language Rules

These are written as imperative do/don't pairs. Where the codebase already
follows the rule, the rule is documenting current practice so an agent can
pattern-match against it.

### Type Hints

- All function signatures (parameters and return types) are annotated.
- Public functions, dataclasses, and module-level constants are annotated.
- Use builtin generics (`list[int]`, `dict[str, Any]`) and `X | None`,
  never `Optional[X]` or `List[int]`.
- `from __future__ import annotations` at the top of every module.
- Avoid `Any`. Where it is unavoidable (for example, JSON columns), use
  `Any` and add a one-line comment explaining why a tighter type is
  unsafe.

```python
# do
def upsert_progress(
    conn: psycopg.Connection,
    *,
    stage: str,
    scope: str,
    status: str,
    position: dict[str, Any] | None = None,
) -> None: ...

# don't
def upsert_progress(conn, stage, scope, status, position=None):
    ...
```

### Exceptions

- Define a per-stage exception family that subclasses a domain root
  (`SegmentationError(RuntimeError)` is the existing pattern in
  `segmenter.py`). New stages follow it.
- Catch the narrowest exception that captures the failure. No bare
  `except:`; no `except Exception:` without re-raising or recording.
- Errors carry context (response payload, ids, scope). Do not log and
  swallow — either re-raise, return a sentinel the caller knows about, or
  record an `error_count` row.

```python
# do
class SegmenterRequestTimeout(SegmentationError):
    """Raised when one parent/window exceeds the configured deadline."""

try:
    response = call_segmenter(window)
except urllib.error.URLError as exc:
    raise SegmenterServiceUnavailable(str(exc)) from exc

# don't
try:
    response = call_segmenter(window)
except Exception:        # too broad; loses traceback context
    response = None      # silent swallow
```

### Logging vs `print`

- CLI commands may `print` user-facing status to stdout.
- Library code (`src/engram/segmenter.py`, `embedder.py`, etc.) uses the
  stdlib `logging` module via a module-level `logger = logging.getLogger(__name__)`.
- Do not use `print` to report failure. Failure goes to a log line *and* a
  structured progress / event row.

### Environment Variables

- All tunables live behind environment variables prefixed `ENGRAM_`.
- Read them at module top, not inside functions, so the value is fixed for
  the process and visible at import time. The segmenter module is the
  pattern.
- Document the variable in the module docstring or a nearby comment when
  it changes behavior beyond a numeric tweak.

### Mutable Defaults & Other Footguns

- No mutable default arguments (`def f(x=[])`). Use `None` and assign
  inside.
- Compare with `None`/`True`/`False` using `is`.
- f-strings for string formatting; never `%` or `.format` for new code.
- Use `pathlib.Path` for filesystem paths; do not concatenate with
  `os.path.join` in new code.
- Resource cleanup goes through `with` (file handles, DB cursors,
  subprocess pipes).

### Comments and Docstrings

- Default to no comment. Add one only when *why* is non-obvious: a hidden
  invariant, a workaround, a constraint that would surprise a reader.
- Public functions and dataclasses get a one-line docstring describing
  intent. Multi-paragraph docstrings are not required and not encouraged
  for internal code.
- Do not describe *what* the code does ("this loop iterates segments");
  the code already does that.

### Imports

- Three groups, separated by blank lines: stdlib, third-party, local.
- ruff's `I` rule enforces this.
- Top-level imports only. If you have a circular import, refactor; do not
  paper over it with a local import.
- No wildcard imports.

## Database Rules

- All SQL goes through `psycopg` with parameterized queries. Never
  f-string a user-supplied value into SQL.
- Workers wrap their unit of work in an explicit transaction. Commit on
  success; let exceptions roll back.
- Writes are idempotent on `(input_id, version)` or an analogous natural
  key, so re-running a worker on the same input is safe. This is already
  the project invariant; the standard codifies it.
- Raw evidence tables are append-only. New code must not issue
  `UPDATE`/`DELETE` against them; derived tables get rebuilt instead.

## Worker / Pipeline Rules

These restate the contracts in RFC 0001, expressed at the code level so an
agent can apply them without reading the architecture RFC first.

- A stage worker is a function or small class with the contract
  `(input_id, version) -> idempotent commit`.
- The worker accepts a `dry_run: bool = False` parameter, or the module
  exposes a way to compute the work plan without committing. If the cost
  is high, document the gap explicitly.
- Prompt, model, and request-profile versions are explicit module
  constants (see `SEGMENTER_PROMPT_VERSION`, `SEGMENTER_REQUEST_PROFILE_VERSION`
  in `src/engram/segmenter.py`). They are stored on every derived row.
- No network egress in corpus-reading paths. The local model endpoint
  (`ENGRAM_IK_LLAMA_BASE_URL`) is bound to `127.0.0.1` and is the only
  permitted outbound destination.

## Test Rules

- Tests are deterministic. A flaky test is a bug, not a tolerated cost.
- Unit tests do not call live LLMs, do not hit real external services,
  and do not depend on wall-clock time except via injected fixtures.
- Use fakes (`FakeSegmenterClient`, etc.) for boundary calls; record /
  replay fixtures for end-to-end integration tests.
- One behavior per test. The test name describes the behavior, not the
  function under test.
- New behavior comes with a test that fails before the change and passes
  after.

```python
# do
def test_segmenter_retries_on_timeout(fake_client: FakeSegmenterClient) -> None:
    fake_client.queue_responses([Timeout(), ok_payload()])
    result = run_segmenter(fake_client, parent_id="p1")
    assert result.attempts == 2

# don't
def test_segmenter():               # vague name
    result = run_segmenter(...)     # what is this asserting?
    assert result is not None
```

## Module Shape

- One public stage, worker, or domain concept per file. The existing
  layout (`segmenter.py`, `embedder.py`, `chatgpt_export.py`) is the
  pattern.
- Public surface is whatever the module exports through unprefixed names.
  Add new private helpers with a leading underscore.
- New parameters on public functions are keyword-only (`*, new_param: T = default`)
  so call sites do not break and reviewers can see the change at the call
  point.
- Avoid creating new top-level packages or sub-packages without a clear
  reason; flat is fine for a codebase this size.

## Error Message Style

Borrowed and pruned from Vercel's Python guide.[^vercel] Concrete and
optional today; intended to harmonize messages over time.

- Lower-case first letter; no trailing period.
- State the reason after a colon: `could not open file "foo": permission denied`.
- Quote identifiers and filenames in double quotes.
- Use `could not` for transient failures and `cannot` for permanent ones.
- No "failed to", "unable to", "bad" — they communicate frustration, not
  cause.

## Pattern Library

A short do/don't appendix lives at the top of `src/engram/__init__.py` or
in a new `docs/python-style.md` once this RFC is promoted, restating the
rules above with copy-paste-ready examples. The literature is consistent
on this: agents perform better against an explicit example than against a
prose rule.[^so][^minimaxir]

## Adoption Plan

Adoption is incremental and follows existing change discipline (see
`AGENTS.md` § Change Discipline: "Avoid broad refactors unless needed for
the requested change").

1. **Phase 0 — pin and wire.** Add `ruff` and `pyright` to dev deps.
   Add `make lint`, `make format`, `make typecheck`. Configure ruff and
   pyright in `pyproject.toml` with permissive baselines. No code
   changes. Single PR.
2. **Phase 1 — green-on-touch.** When an agent or human edits a file,
   the file must pass `make lint` and `make typecheck` before merge. No
   bulk reformatting. Existing files without changes are not in scope.
3. **Phase 2 — baseline drive.** Once the touched-file set covers the
   majority of `src/engram`, do one bounded sweep PR per module to fix
   residual findings. Each sweep is its own commit and does not mix with
   behavior changes.
4. **Phase 3 — gate.** Promote `make lint && make typecheck && make test`
   to a pre-commit hook and / or local CI gate. This is a separate
   decision recorded in `DECISION_LOG.md`.

The standard itself can be promoted to `DECISION_LOG.md` after Phase 1
has run for long enough to surface friction.

## What This RFC Does Not Promote

- Importing a large dependency (Pydantic, attrs, structlog) just to
  enforce types or shape data. The stdlib `dataclasses` and `typing`
  modules are sufficient for the current code.
- A monorepo split or `src/engram/_internal/` layout. Premature for
  ~7800 LoC.
- A 88-character or 79-character line cap. 100 is closer to the existing
  long lines and avoids line-break churn during adoption.
- Rules that conflict with existing project values: no "always use
  pandas/polars", no required emoji, no "$100 penalty"-style framing
  drawn from popular templates.

## Disproof Probes

Before promoting this RFC into a decision, test:

- Does `ruff check .` against the current tree return a manageable number
  of findings, or thousands? If thousands, the suggested rule selection
  is too aggressive.
- Does pyright produce useful errors on `psycopg` row dicts, or does it
  mostly complain about `Any`? If the latter, basedpyright or mypy with
  the psycopg plugin may be a better default.
- After Phase 0, does an agent editing a file produce code that already
  conforms to the standard, or does the agent need the standard quoted
  back to it in the prompt? If the latter, the rules should move closer
  to `AGENTS.md` rather than living in a deep RFC.
- Does enforcing typed signatures slow down small bug-fix changes more
  than it speeds up review? Watch for two cycles before deciding.
- Does the standard catch the kinds of errors that have actually shown
  up in this repo (silent swallow, untyped JSON columns, mutable
  defaults), or is it cargo-culted from other Python projects?

## Open Questions

- pyright vs mypy. Both are acceptable; the choice should follow the
  first one that integrates cleanly with the existing test setup.
- Should embedded prompt/model version constants live in a single
  `versions.py`, or stay co-located with their workers? Co-location
  matches current style; centralization helps the supervisor enumerate.
- Should ruff format settings match black exactly (so external tools
  do not fight)? Probably yes, but worth confirming after the first
  pass.
- Where does the do/don't appendix live: a doc, a module docstring, or
  a generated artefact? A doc is simplest for now.

## Adjacent Ideas

- A small `make audit` target that runs ruff + pyright + a custom AST
  check for forbidden patterns (raw `print` in `src/engram`, mutable
  defaults, hardcoded URLs). Cheap to write, agent-friendly to read.
- A `tests/test_pyproject.py` that asserts the configured ruff and
  pyright versions match the lockfile, so an agent updating one but not
  the other gets a fast failing test.
- Versioning the standard itself: when this RFC is promoted, give the
  standard a version string and stamp it into commit messages or PR
  descriptions, so a reviewer can see which version the change was
  written against.
- A short "first-edit checklist" appended to `AGENTS.md` that an agent
  runs before touching `src/engram`: `make install`, `make lint`,
  `make typecheck`, `make test`. This is the feedback loop.

## References

The shape of this RFC follows existing Engram RFCs (0001, 0007, 0011).
The content draws on:

[^so]: Stack Overflow, *Building shared coding guidelines for AI (and people too)*, 2026. https://stackoverflow.blog/2026/03/26/coding-guidelines-for-ai-agents-and-people-too/
[^minimaxir]: Max Woolf, *Python AGENTS.md (2026-02-23)*, gist. https://gist.github.com/minimaxir/10b780671ee5d695b4369b987413b38f
[^ronacher]: Armin Ronacher, *Agentic Coding Recommendations*, 2025. https://lucumr.pocoo.org/2025/6/12/agentic-coding/
[^vercel]: Vercel, `python/AGENTS.md`. https://github.com/vercel/vercel/blob/main/python/AGENTS.md

Other useful prior art consulted but not directly quoted: LangChain
`AGENTS.md` (signature stability, deterministic tests), Mirascope
`python/AGENTS.md` (uv + ruff + pyright command set), and the Eficode
*Modern AI Developer Stack* `AGENTS.md` (rules-for-agents framing).
