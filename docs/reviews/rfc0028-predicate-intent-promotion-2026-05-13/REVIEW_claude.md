# RFC 0028 Predicate Intent Implementation Review — claude
author: operator [self-declared: rfc0028-review-claude]

Status: review
Date: 2026-05-13
RFC refs: RFC-0028, RFC-0011, RFC-0017, RFC-0021, RFC-0027
Decision refs: current RFC 0028 proposal and fresh review evidence; D016, D044, D069, D079, D080, D082 (reserved by artifacts, not yet recorded)
Phase refs: PHASE-0003, PHASE-0003-FOLLOWON

Scope: schema safety (migration 012), runtime-vocabulary parity and
schema preflight, prompt-version semantics, prompt shape, interview UX
(CLI + web), test coverage, and doc / changelog discipline. Read-only
review against the worktree at
`/home/halbritt/git/engram-worktrees/rfc0028-promotion` and the IMPLEMENTATION_HANDOFF
authored 2026-05-13.

## Findings

### F001 — Migration 012 is correctly additive, nullable, and constraint-bounded
Severity: nit
Source: `migrations/012_predicate_subject_kind_hint.sql:1-46`
Rationale: The migration adds a single nullable column
(`predicate_vocabulary.subject_kind_hint TEXT NULL`) and a named
non-blank CHECK that explicitly allows NULL
(`chk_predicate_vocabulary_subject_kind_hint_nonblank`). It does not
weaken any append-only / insert-only contracts:
`predicate_vocabulary` has no mutation-guard trigger in
`migrations/006_claims_beliefs.sql:37-62`, so seeding via UPDATE is the
established pattern. Claims (`claims_insert_only`), beliefs
(`fn_beliefs_prepare_validate` + `engram.transition_in_progress`
gate), and `belief_audit` (append-only) are untouched. The migration
file is not authored with `ADD COLUMN IF NOT EXISTS`, but the
project's migration runner (`src/engram/migrations.py:61-112`)
enforces single-application by sha256-keyed `schema_migrations` row,
so re-application is structurally prevented; on-disk idempotency
guards are not required by the runner contract. The constraint name
is unique and descriptive — no clashes detected. This is a clean
schema change.

### F002 — Runtime vocabulary, DB seed, and schema preflight stay in lock-step (description + subject_kind_hint)
Severity: nit
Source: `src/engram/extractor.py:83-393`,
`src/engram/cli.py:1088-1238`,
`tests/test_phase3_claims_beliefs.py:227-292,2286-2343`
Rationale: `PREDICATE_INTENT_METADATA` is merged into the public
`PREDICATE_VOCABULARY` via a comprehension; the DB seed in migration
012 carries the same hints. `phase3_schema_preflight` requires both
`description` and `subject_kind_hint` columns
(`cli.py:1129-1131`) and `_check_phase3_predicate_vocabulary`
compares the runtime dict element-wise against the DB rows
(`cli.py:1196-1238`), including `subject_kind_hint`. Three
parametrized drift cases pin the contract:
`description` rename on `has_name`, `subject_kind_hint`
swap to "places only", and a `DROP COLUMN subject_kind_hint`. All
raise `Phase3SchemaPreflightError`. Drift surface is solid.

### F003 — Prompt version bump matches RFC 0017 discipline and the RFC 0028 promotion path
Severity: nit
Source: `src/engram/extractor.py:37-40`,
`docs/rfcs/0028-predicate-intent-surfacing.md:362-370`,
`tests/test_phase3_claims_beliefs.py:227-232`
Rationale: `EXTRACTION_PROMPT_VERSION = "extractor.v9.d082.predicate-intent"`
matches the regex enforced by `EXTRACTION_PROMPT_VERSION_REGEX` and
the value the RFC pre-committed to in its promotion path (step 2b).
Existing claim rows remain attached to their prior `extraction_prompt_version`
because the `claims_insert_only` trigger
(`migrations/006_claims_beliefs.sql:472-486`) forbids UPDATE/DELETE of
claim rows, so RFC 0017 immutability is mechanically preserved. The
`re-extract` surface guarded by
`extractor.py:2960-2975` rejects "re-extract under same version" so
operators have a fail-closed safety net before they consume the new
slot. Note: D082 is *referenced* by the migration comment and the
prompt version, but no `DECISION_LOG.md` row exists yet — see F008.

### F004 — `build_extraction_prompt` surfaces intent + subject-kind hint without breaking the JSON output contract
Severity: nit
Source: `src/engram/extractor.py:2243-2297`,
`tests/test_phase3_claims_beliefs.py:295-318`
Rationale: The vocabulary block now renders two lines per predicate
(the structural shape line + an `  intent: {description} ({subject_kind_hint})`
line). The JSON instructions, key list, and schema enforcement upstream
of the LLM are unchanged: 'Return one JSON object with key "claims"'
and `extraction_json_schema(...)` is verified by
`test_predicate_vocabulary_and_extractor_schema_parity` to keep the
predicate enum, the `oneOf`-free strict item, and the relaxed item
in sync with the DB. The new test pins both
`"intent: legal or preferred name (persons only)"` and
`"intent: software or hardware tool (persons or projects)"`. Prompt
budget impact (~25 predicates × ~30 tokens) is consistent with the
RFC's open-question recommendation to bench before any full-corpus
re-extraction; the handoff explicitly notes that full-corpus
re-extraction has not been run and remains gated on a bounded bench.

### F005 — `format_summary_line` puts intent on its own line; warning text is hedged
Severity: nit
Source: `src/engram/interview/render.py:253-321,392-409`,
`tests/test_interview_render.py:136-189,482-517`
Rationale: `format_summary_line` returns three lines maximum
(summary; `  intent: <doc> (<hint>)`; `  [warning] ...`). The warning
helper `subject_kind_warning` is gated by `_subject_hint_is_person_only`
(only fires on `persons only` / `person only`), then dispatches to a
curated five-entry non-person list and to active-entity-kind lookup
against `entities`. The warning sentence
(`subject "<X>" looks like a <label>; predicate intent is persons. Likely a `false` extraction.`)
uses the hedged "looks like" / "Likely" framing the RFC asked for and
is purely advisory — it does not set any DB state. Tests verify both
the curated-string path and the entity-kind path, and skip cases for
non-`persons only` hints and mixed-allowed hints like
`persons or projects`. Posture matches the RFC's "v1 is small and
advisory" stance.

### F006 — CLI and web share the same render seam; rationale prompt is broadened in both surfaces
Severity: nit
Source: `src/engram/cli.py:1875-1929`,
`src/engram/interview/web.py:41-51,497-573`,
`src/engram/interview/templates/question.html:18-22`,
`tests/test_interview_web.py:493-509`,
`tests/test_interview_render.py:419-470`
Rationale: Both the CLI (`_run_phase3_interview_prompt_loop`) and
the web's `_render_question_template` import
`fetch_target_display`, `format_summary_line`,
`rationale_prompt_for`, and `RATIONALE_PROMPT_BY_VERDICT` from
`engram.interview.render`. The web template renders
`summary_lines = summary_line.splitlines()` inside a
`.summary-line { white-space: pre-wrap; }` container so the intent
and warning lines render on their own row. The web smoke test
`test_question_page_uses_shared_false_rationale_prompt` confirms the
broadened `"what's wrong? ..."` prompt is served and the old
`"correct value > "` label is gone; the rationale-prompt-table
invariant test confirms the table covers exactly the non-terminal
verdicts. Verdict alias/vocabulary invariants are preserved.

### F007 — Tests are focused, deterministic, and avoid live LLM calls
Severity: nit
Source: `tests/test_phase3_claims_beliefs.py:227-318,2286-2343`,
`tests/test_interview_render.py:136-517`,
`tests/test_interview_web.py:493-509`,
`tests/test_migrations.py:111-165`
Rationale: The new tests pin: (1) the predicate-vocabulary parity
including description and subject_kind_hint, (2) the prompt-version
constant, (3) `build_extraction_prompt` content, (4)
`format_summary_line` shape with and without the hint and the
warning, (5) `subject_kind_warning` dispatch on curated terms,
entity-kind lookup, and skip cases, (6) `rationale_prompt_for` for
every verdict, (7) `test_phase3_schema_preflight_detects_semantic_schema_drift`
covers `description`, `subject_kind_hint`, and column-drop drift, (8)
the migration applies and the CHECK fires on blank input, and (9)
the web question page actually serves the broadened rationale prompt
and `pre-wrap` style. `subject_kind_warning` tests use `MagicMock`
for the connection; the prompt test builds a `SegmentPayload`
fixture. No live extractor / LLM call appears in the new test
surface, matching the AGENTS.md "no live LLM calls in unit tests"
rule.

### F008 — D082 is referenced by artifacts but not yet recorded in DECISION_LOG.md
Severity: minor
Source: `migrations/012_predicate_subject_kind_hint.sql:1`,
`src/engram/extractor.py:37`,
`docs/reviews/rfc0028-predicate-intent-promotion-2026-05-13/IMPLEMENTATION_HANDOFF.md:16-20`
Rationale: The migration header (`RFC 0028 / D-082`) and the
extractor prompt version (`extractor.v9.d082.predicate-intent`)
both pre-commit to a `D082` decision number, but `DECISION_LOG.md`
has no D082 row yet — the handoff explicitly defers this to the
promotion pass per project convention. This is consistent with
RFC-0028 promotion-path step 6 ("Record the cycle's outcome in
`DECISION_LOG.md` (next available `D###`)"). It becomes a problem
only if a *different* decision races to `D082` between now and
promotion. Recommendation: when the promotion review accepts and
records the decision, treat the artifact-side `D082` reservations
as already-canonical or, if a collision happened, follow up with a
prompt-version rename per RFC 0017's re-extract semantics. Not
blocking for this review; flagged so the promotion-recorder agent
knows the slot is informally claimed.

### F009 — `format_summary_line` docstring claims a four-space CLI prefix; CLI uses two
Severity: minor
Source: `src/engram/interview/render.py:392-409`,
`src/engram/cli.py:1917-1918`
Rationale: The docstring on `format_summary_line` says: "The
four-space prefix the CLI prepends before printing is the caller's
responsibility; this helper returns just the line content." In
practice the CLI call site is `print(f"  {format_summary_line(display)}")`
(two-space prefix on line 1 only; embedded newlines keep their
internal two-space indent), and the web template renders each line
inside its own `<div>` with no outer indent. Both surfaces end up
with consistent two-space indent on the intent and warning lines,
but the docstring is stale relative to both call sites and the
RFC's worked example (which depicts a four-space indent on the
intent/warning lines, two-space on the summary). Minor cosmetic
drift; either tighten the docstring or align indents to match the
RFC's example. Not blocking.

### F010 — Curated non-person subject list uses substring matching with a small seed set
Severity: minor
Source: `src/engram/interview/render.py:56-62,287-294`
Rationale: `_KNOWN_NON_PERSON_SUBJECTS` holds five entries and
matches via `if needle in normalized:` (substring contains), so a
hypothetical person whose subject text *contains* one of the
needles (e.g. "Alameda Smith") would falsely receive a
"place/business" advisory. The RFC anticipates a curated list
under 50 entries growing as operators report misses; the current
implementation is small and may produce occasional false-positives
in the wild. Mitigated by (a) advisory framing ("Likely a `false`
extraction" — not a status change, not validation), (b) operator
reading evidence before ruling, and (c) the verdict-capture text
remaining free-text. Acceptable for v1; worth a comment so a
follow-on contributor doesn't reach for exact-match thinking it's
"safer" without re-checking the entity-kind path. Not blocking.

### F011 — Warning text uses Markdown backticks; CLI and web render them literally
Severity: nit
Source: `src/engram/interview/render.py:317-321`,
`src/engram/interview/templates/question.html:18-22`
Rationale: The warning ends with ``Likely a `false` extraction.``
The CLI prints the backticks as-is, and the web template renders
the line inside a `<div>` (no `|safe`/markdown filter), so users
see literal backticks. Cosmetic; consistent across surfaces because
both share the same string. Either drop the backticks or accept
them as the canonical advisory format. Not blocking.

### F012 — Privacy / local-first posture: unchanged
Severity: nit
Source: `src/engram/extractor.py:2243-2297`,
`src/engram/interview/render.py:253-321`,
`src/engram/interview/web.py:106-135,219-229`
Rationale: The extractor prompt continues to flow only to the local
LLM endpoint; no new fields are exfiltrated. The interview render
warning quotes the subject text already on display, so no new
private data surface is added. Tier 1 ceiling and origin allowlist
on the web routes are untouched. RFC 0028 explicitly stated "no
auth / transport / non-loopback bind" changes and the implementation
honors that. ✓

### F013 — Doc discipline: changelog and RFC index are updated; schema doc regenerated; DECISION_LOG deliberately deferred
Severity: nit
Source: `CHANGELOG.md:10-18`,
`docs/rfcs/README.md:48`,
`docs/schema/README.md:331-334,840-843`,
`docs/reviews/rfc0028-predicate-intent-promotion-2026-05-13/IMPLEMENTATION_HANDOFF.md:35-44`
Rationale: The Unreleased section in CHANGELOG records the
implementation, the prompt version, the migration, the renderer
delta, and that RFC status remains proposal pending fresh review.
The RFC index marks 0028 status `proposal` and Implementation
`implemented`. The generated schema doc reflects
`subject_kind_hint TEXT` as nullable. The handoff explicitly notes
no DECISION_LOG entry on the author pass; that is consistent with
project promotion discipline and the canonical AGENTS.md guidance.
The author pass left CHANGELOG + RFC index + schema docs in a
review-ready state; DECISION_LOG and RFC status promotion are
correctly scoped to this fresh review's outcome.

## Open questions

1. **Indent / shape final form.** The RFC's worked example shows the
   intent and warning lines at four-space indent; the implementation
   ends up at two-space indent (CLI) or zero-space outer + two-space
   inner (web). Is the current shape the intended canonical, or do
   we want to converge on the RFC's worked-example shape before
   promotion?
2. **Substring-match policy on `_KNOWN_NON_PERSON_SUBJECTS`.** Acceptable
   for v1's five-entry list, but should we lock the contract (e.g.,
   require word-boundary or exact `subject_normalized` matching) at
   any expansion threshold (RFC's "under 50 entries"), so a 30-entry
   list does not produce silent false-positives?
3. **D082 reservation.** Confirm at promotion that no other decision
   has taken the `D082` slot, and either accept the pre-committed
   number or re-mint the prompt version per RFC 0017 if a collision
   occurred.

verdict: accept_with_findings
