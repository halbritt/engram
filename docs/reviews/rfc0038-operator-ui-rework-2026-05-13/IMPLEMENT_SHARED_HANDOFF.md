# RFC 0038 Shared Web Substrate Handoff
author: operator [self-declared: rfc0038-implement-shared]

Status: implemented
Date: 2026-05-13
RFC refs: RFC-0038

## Summary

Implemented the additive shared Engram web substrate under `src/engram/web/`.
The slice is intentionally local-first and presentation-only: it provides
shared chrome templates, design tokens, status-chip semantics, package-local
static helpers, Origin/Sec-Fetch and tier-ceiling helpers, and no-CDN checks.
It does not modify interview or bench-review route/template behavior.

## Files Changed

- `src/engram/web/__init__.py`
- `src/engram/web/assets.py`
- `src/engram/web/chrome.py`
- `src/engram/web/origin.py`
- `src/engram/web/status.py`
- `src/engram/web/tier.py`
- `src/engram/web/templates/_app_shell.html`
- `src/engram/web/templates/_audit_footer.html`
- `src/engram/web/templates/_cli_command_card.html`
- `src/engram/web/templates/_error_banner.html`
- `src/engram/web/templates/_future_slot.html`
- `src/engram/web/templates/_help_modal.html`
- `src/engram/web/templates/_status_banner.html`
- `src/engram/web/templates/_status_chip.html`
- `src/engram/web/templates/_surface_tabs.html`
- `src/engram/web/static/keyboard.js`
- `tests/test_web_ui_shared.py`
- `pyproject.toml`

## Shared Components

- Shared app shell with RFC 0038 color, spacing, type, banner, chip, footer,
  and responsive tokens.
- Surface tabs with an inert `Entities (future)` tab using
  `data-future="true"` and `aria-disabled="true"`.
- Audit footer copy:
  `local-only · loopback bind: <address> · no network egress.`
- Help modal with the mandated no-cloud/no-telemetry/no-CDN copy.
- CLI command card, future slot, status banner, error banner, and status chip
  partials.
- `keyboard.js` dispatcher for help modal, `data-key` controls, text-entry
  focus safety, htmx live-region updates, and focus movement after swaps.
- `engram.web.origin.require_origin(...)` strict Origin + Sec-Fetch-Site
  guard.
- `engram.web.tier.require_tier_ceiling(...)` standard 403 envelope helper.
- `engram.web.assets` resource path and external-asset-marker checks.

## No-CDN / Local-Only Checks

- Shared templates and static assets are package-local under `engram.web`.
- `pyproject.toml` now ships `engram.web` templates and static assets via
  `[tool.setuptools.package-data]`.
- Static checks found no external asset markers (`http://`, `https://`, CDN
  hostnames, Google asset hostnames, CSS imports, or remote CSS URLs) in the
  new shared resources.
- The shared package AST import check confirms no imports from
  `engram.interview`, `engram.bench_review`, `engram.consolidator`,
  `engram.extractor`, or `engram.segmenter`.

## Tests Run

- `python3 -m compileall src/engram/web tests/test_web_ui_shared.py`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 - <<'PY' ...` static
  shared-resource/no-CDN/status-copy check
- `python3 - <<'PY' ...` shared package AST import-boundary check
- `python3 - <<'PY' ...` `pyproject.toml` package-data check
- `grep -RIn '[[:blank:]]$' src/engram/web tests/test_web_ui_shared.py pyproject.toml || true`

Attempted but blocked:

- `.venv/bin/python -m pytest tests/test_web_ui_shared.py` failed because
  `.venv/bin/python` does not exist in this worktree.
- `python -m pytest tests/test_web_ui_shared.py` failed because `python` is
  not installed on PATH.
- `python3 -m pytest tests/test_web_ui_shared.py` failed because pytest is not
  installed for system Python.

## Residual Risk

- Focused pytest coverage is committed in `tests/test_web_ui_shared.py` but
  was not executable in this worktree without installing dev dependencies.
- Existing interview/bench surfaces are not yet wired to the shared substrate;
  that is intentionally left to their separate RFC 0038 implementation lanes.
- `CHANGELOG.md` was not updated because this work packet's write scope does
  not include it.
