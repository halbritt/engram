# RFC 0038 Bench Review UI Handoff
author: operator [self-declared: rfc0038-implement-bench]

Status: implemented
Date: 2026-05-13
RFC refs: RFC-0038, RFC-0029

## Summary

Implemented the RFC 0038 bench-review UI slice inside the existing
`engram.bench_review` web surface. The pass keeps the workbench server-rendered,
local-only, scratch-state-only, and production-read-only while making run
readiness, queue state, prior/candidate comparison, disabled strong decisions,
and CLI-owned export handoff explicit in the UI.

## Files Changed

- `src/engram/bench_review/web.py`
- `src/engram/bench_review/templates/base.html`
- `src/engram/bench_review/templates/index.html`
- `src/engram/bench_review/templates/segments.html`
- `src/engram/bench_review/templates/segment.html`
- `src/engram/bench_review/templates/excerpt.html`
- `src/engram/bench_review/templates/summary.html`
- `src/engram/bench_review/static/keyboard.js`
- `tests/test_bench_review.py`

## Bench Review Flow Changes

- Added dashboard readiness display, run metadata, computed queue fingerprint,
  blocker-first resume targets, metadata-only banner, queue tabs, and state/tag
  chips.
- Reworked segment detail into a responsive prior/candidate comparison layout
  with counts, state instruction banner, visible saved decision, candidate
  metadata notes, rationale cap copy, and decision buttons with text plus icon.
- Kept strong decisions disabled and now route-rejected for malformed, missing,
  and prior-missing states with a controlled JSON 400 envelope.
- Added route-level 403 for excerpt detail above Tier 1.
- Added summary readiness panel and CLI export command card rather than a web
  export mutation.

## Truthfulness / Scratch-State Preservation

- The literal banner `Bench review decisions do not mutate production data or
  bypass Phase 4 gates.` renders on `/` and `/summary`.
- Readiness and run recommendations use warning/advisory styling, not success
  styling; ready state says `Ready (recommendation, not gate)`.
- Segment review writes still go only through existing scratch SQLite storage.
  No production claim, belief, audit, raw evidence, extraction, consolidation,
  interview, entity-review, or serving path is imported or written.
- Export remains CLI-owned and redacted by default; the web UI only displays
  the command shape.

## Tests Run

- `python3 -m py_compile src/engram/bench_review/web.py tests/test_bench_review.py` — passed.
- `.venv/bin/python -m py_compile src/engram/bench_review/web.py tests/test_bench_review.py` — passed.
- `.venv/bin/python -m ruff check src/engram/bench_review/web.py tests/test_bench_review.py` — passed.
- Jinja template compile smoke for all six bench templates — passed.
- `rg` checks for external URLs/CDNs/font imports in bench templates/static — no matches.
- `rg` check for `engram.consolidator` / `transitions` in bench `web.py` — no matches.
- `make test` — blocked during collection: `starlette.testclient` requires
  `httpx`, which is not installed by the current dev environment.
- `.venv/bin/python -m pytest tests/test_bench_review.py` — same collection
  blocker: missing `httpx`.

## Residual Risk

- Route tests could not execute until the dev dependency set includes `httpx`
  for FastAPI/Starlette `TestClient`.
- Responsive behavior is implemented through CSS media queries and covered by
  template/test assertions, but no Playwright screenshot check was run in this
  lane.
- `CHANGELOG.md` was not updated because this work packet's write scope did
  not include it.
