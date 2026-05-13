# CODE_REVIEW_RFC0028 — Predicate-Intent Surfacing Implementation

| Field | Value |
|-------|-------|
| Audit block | C |
| Author | Claude Code |
| Date | 2026-05-13 |
| Method | Independent re-read of the RFC 0028 implementation diff. No file under `docs/reviews/rfc0028-predicate-intent-implementation/` was opened during this review; the suspect "REVIEW_claude.md" / "REVIEW_codex.md" / "REVIEW_gemini.md" / "FINDINGS_LEDGER.md" content is not consulted. |
| Files reviewed | `docs/rfcs/0028-predicate-intent-surfacing.md`, `migrations/012_predicate_subject_kind_hint.sql`, `src/engram/extractor.py` (changes), `src/engram/interview/render.py`, `src/engram/interview/web.py`, `src/engram/interview/templates/question.html`, `src/engram/cli.py` (phase3 preflight section), `tests/test_phase3_claims_beliefs.py` (changes), `tests/test_interview_render.py` (changes), `tests/test_interview_web.py` (changes), `tests/test_migrations.py` (changes) |

## Summary

The RFC 0028 implementation is **substantively sound**. The migration is
minimal and additive, the prompt-version bump follows RFC 0017 discipline,
the interview render layer is consistent with the RFC's worked example, and
the phase 3 schema preflight does validate the new column. Tests cover the
new prompt shape, the warning heuristic, and the DB/Python vocabulary
parity.

The implementation looks like the kind of work one would expect for a small
proposal of this shape. The provenance failure does not appear to be a
cover for broken code; it appears to be a cover for "this work was not
actually multi-lane reviewed before being marked accepted."

## RFC ↔ implementation crosswalk

| RFC clause | Implementation evidence | Match |
|------------|--------------------------|-------|
| Add nullable `subject_kind_hint` to `predicate_vocabulary` with NULL allowed | `migrations/012_predicate_subject_kind_hint.sql` — `ADD COLUMN subject_kind_hint TEXT NULL`, plus a `chk_predicate_vocabulary_subject_kind_hint_nonblank` check that the column is `NULL OR btrim(...) <> ''` | ✓ |
| Seed hints for top ~15 predicates | Migration seeds **29 predicates** (every name in the vocabulary). Broader than the RFC's "~15" but consistent with the intent and not user-visible regressively. | ✓ (with note) |
| Bump `EXTRACTION_PROMPT_VERSION` to `extractor.v9.d082.predicate-intent` | `src/engram/extractor.py:37` — `EXTRACTION_PROMPT_VERSION = "extractor.v9.d082.predicate-intent"` | ✓ |
| Extraction prompt renders `intent: <description> (<subject_kind_hint>)` per predicate | `build_extraction_prompt` at `extractor.py:2243` — emits `f"  intent: {row['description']} ({row['subject_kind_hint']})"` | ✓ |
| `format_summary_line` renders the description on its own line below the triple | `interview/render.py:383` `format_summary_line` produces `  intent: <description> (<subject_kind_hint>)` and an optional `  [warning] ...` line | ✓ |
| `fetch_target_display` includes a `subject_kind_hint_match` flag and an inline warning | `interview/render.py:113` and `:181`; produces `subject_kind_hint`, `subject_kind_hint_match`, `subject_kind_warning` keys in the display dict | ✓ |
| `RATIONALE_PROMPT_BY_VERDICT["false"]` broadened to the wrong-predicate / wrong-subject / different-object prompt | `interview/render.py:35-43` matches the RFC wording exactly | ✓ |
| No schema change to `claims`, `beliefs`, or `gold_labels` | Confirmed — migration 012 only touches `predicate_vocabulary` | ✓ |
| Privacy contract unchanged | Confirmed — no new sinks; render still flows over the same surfaces | ✓ |

## Substantive findings

### F-RFC0028-001 — Python-side description duplicates the DB description without runtime cross-check

**Severity:** minor.

`PREDICATE_INTENT_METADATA` at `extractor.py:83` holds `description` and
`subject_kind_hint` for every predicate. The Python `description` is merged
into `PREDICATE_VOCABULARY` rows at `extractor.py:388` and rendered into
the extraction prompt. The DB also has `predicate_vocabulary.description`
(from migration 006) and `predicate_vocabulary.subject_kind_hint` (from
migration 012).

If the Python `PREDICATE_INTENT_METADATA[p]["description"]` ever differs
from `predicate_vocabulary.description` in the DB for the same `p`, the
extraction prompt uses one value while the interview UI (which reads the
DB row via `fetch_target_display`) uses another. The `engram.cli`
schema-preflight check selects both columns but does not assert equality
across the boundary.

The new test `test_predicate_vocabulary_and_extractor_schema_parity` at
`tests/test_phase3_claims_beliefs.py:243-265` pins the DB-side
`(description, subject_kind_hint)` against the Python-side per-predicate
metadata, so test-time drift is caught — but the runtime path does not
re-validate.

**Recommendation:** consider adding a runtime parity check inside
`phase3_schema_preflight` that compares the DB rows against
`extractor.PREDICATE_VOCABULARY` content for `description` and
`subject_kind_hint`. The test already encodes the assertion; promoting it
to a runtime check is small and aligns with the rest of the preflight.
Acceptable as-is for v1; flag as Tier 0 follow-up.

### F-RFC0028-002 — `_KNOWN_NON_PERSON_SUBJECTS` is a 5-entry hand-curated list seeded with exactly the operator-rationale examples

**Severity:** documentation.

`interview/render.py:56` lists `alameda`, `encinal`, `evnotify`, `hobnob`,
`nob hill foods` — the five proper nouns that appeared in the operator's
real-world `false` rationales (per RFC 0028 § "Current state"). The list
is small and intentionally narrow — RFC 0028 § Open question 2 caps it at
"under 50 entries; expand only when operators report specific misses."

Matching is substring (`if needle in normalized`), so e.g. "Hobnob House"
matches "hobnob". For one-of-a-kind business names this is fine; for
generic words ("alameda" is also a city name plural-form in any number of
real persons, e.g. fictional or rare names) the substring match can
produce false positives. The downstream effect is at most an inline
operator warning — no claim mutation — so the impact is small.

**Recommendation:** acceptable. If operators report false-positive
warnings (a real person named "Alameda Smith" rendering with the warning),
revisit; otherwise no action needed.

### F-RFC0028-003 — Subject-kind warning skips non-"persons only" hints by design

**Severity:** intentional; flagging for visibility.

`_subject_hint_is_person_only` at `interview/render.py:273` only matches
hints exactly equal to `"person only"` or `"persons only"`. Predicates like
`uses_tool` (`persons or projects`), `works_with`
(`persons or organizations`), `owns_repo` (same), `project_status_is`
(`projects only`), and `lives_at` (`persons or households`) **do not get
the warning rendered** even when their subject is plausibly mismatched
(e.g. a `project_status_is` claim on a string that is clearly not a
project name).

This is consistent with the RFC's "v1 heuristic" — the heuristic is
intentionally narrow to its highest-frequency failure class
(`has_name`-on-non-person). The "uses_tool on non-tool" case the RFC also
calls out as a target pattern is NOT covered by the heuristic in v1.

**Recommendation:** acceptable for v1. If operators continue to see
`uses_tool` claims on non-tools after the prompt-version bump alone, v1.1
should add a tool-kind warning path that mirrors the person-only path.
Add an entry to FORWARD_PATH.md.

### F-RFC0028-004 — `KeyError` failure mode on new predicate additions is fail-fast but undocumented

**Severity:** minor.

`extractor.py:388`:

```python
PREDICATE_VOCABULARY: list[dict[str, Any]] = [
    {**row, **PREDICATE_INTENT_METADATA[row["predicate"]]}
    for row in _BASE_PREDICATE_VOCABULARY
]
```

Adding a predicate to `_BASE_PREDICATE_VOCABULARY` without adding a
matching `PREDICATE_INTENT_METADATA` entry raises `KeyError` at import
time. Fail-fast is appropriate. RFC 0028 § Open question 5 proposes a
CI check in `make check-refs`; that check is not present in the diff.

**Recommendation:** wire the CI check or document the requirement near
the two data structures. Small follow-up.

### F-RFC0028-005 — Operator-facing intent line uses two-space indent that may collapse in HTML

**Severity:** minor / cosmetic.

`format_summary_line` returns lines like `"  intent: <text>"` and
`"  [warning] <text>"` with two leading spaces. The CLI prints these
verbatim; the web template at `interview/templates/question.html` iterates
the lines into generic block elements. Whether the two-space indent
renders depends on the surrounding CSS — `white-space: normal` (the
default) will collapse the leading whitespace, while `white-space: pre`
preserves it.

This is a real visual-parity smell between CLI and web UI, but the
information content reaches the operator either way (the leading
`intent:` and `[warning]` tokens carry the meaning). Not a correctness
issue.

**Recommendation:** if CSS parity matters, add `white-space: pre-wrap`
to the `.summary-line` rule (or whichever class the question template
uses). Acceptable to defer.

## Migration safety review

`migrations/012_predicate_subject_kind_hint.sql` is 46 lines, additive:

- `ALTER TABLE predicate_vocabulary ADD COLUMN subject_kind_hint TEXT NULL` — non-destructive on existing rows.
- A `CHECK` constraint forbidding blank-string values (allows NULL).
- A single `UPDATE ... FROM (VALUES ...)` seeding hints for the 29
  vocabulary rows.

Reversibility: a `DROP COLUMN subject_kind_hint` would back this out
cleanly. Append-only constraint from AGENTS.md applies to raw evidence,
not to a vocabulary table; mutating `predicate_vocabulary` is the
established pattern.

The migration does not regenerate or invalidate any existing claim or
belief rows. RFC 0017's `EXTRACTION_PROMPT_VERSION` discipline means
existing claims stay attached to `extractor.v8.d064.accounted-zero`; new
extractions land under `extractor.v9.d082.predicate-intent` without
touching prior rows.

**Verdict:** migration is safe to apply on a populated DB.

## Test coverage review

| Test | Behavior pinned | Verdict |
|------|-----------------|---------|
| `test_predicate_vocabulary_and_extractor_schema_parity` (modified) | Bumps prompt version, asserts DB ↔ Python vocab parity including `(description, subject_kind_hint)` | Adequate |
| `test_build_extraction_prompt_surfaces_predicate_intent` (new) | Pins extraction prompt shape includes `intent: legal or preferred name (persons only)` for `has_name` and `intent: software or hardware tool (persons or projects)` for `uses_tool` | Adequate |
| `test_phase3_schema_preflight_accepts_current_schema` (modified) | Implicitly via the required-column list now including `description` and `subject_kind_hint` | Adequate |
| `tests/test_interview_render.py` (modified, 84-line diff) | Pins the warning heuristic against the 5-name hardcoded list and against `entities` table rows | Adequate |
| `tests/test_interview_web.py` (modified, 19-line diff) | Pins web rendering of the intent line and warning | Adequate |
| `tests/test_migrations.py` (modified, 34-line diff) | Pins migration 012 application against the DB | Adequate |

`make test` execution (run during this audit): **430 passed, 1 failed**.
The single failure
(`test_cli_pipeline_is_phase2_only_and_pipeline3_warns`) was introduced
by the **pre-suspect** RFC 0025 command-surface work
(commit `2de6123`); the test is not part of the c4a48ab diff and is not
caused by RFC 0028 changes. See `CODE_REVIEW.md` for the cross-cutting
note.

## Comparison against the suspect REVIEW_*.md claims (post hoc, not used for review judgment)

After completing the independent review above, I sanity-checked two of
the suspect reviewer findings against the actual code:

| Suspect claim | Reality |
|---------------|---------|
| `REVIEW_codex.md` F001: "warning heuristic gates on substring membership of `person`, so `uses_tool`'s `persons or projects` hint falls into the person-only warning path" | **Wrong.** `_subject_hint_is_person_only` checks set membership against exactly `{"person only", "persons only"}`, not substring. `"persons or projects"` is not in the set; the warning is correctly skipped. |
| `REVIEW_codex.md` F002: "phase3_schema_preflight does not include `description` and `subject_kind_hint` in the required-column list, so a missing migration 012 raises raw `UndefinedColumn` instead of `Phase3SchemaPreflightError`" | **Wrong.** `cli.py:1042-1043` includes both `description` and `subject_kind_hint` in the required-column list. The preflight does raise `Phase3SchemaPreflightError` when the column is missing. |

Both suspect "major" findings against the implementation are
inaccurate. This is consistent with the Block B conclusion that the
suspect review content is not load-bearing engineering evidence — it
appears to be plausible-shaped synthesis rather than real review.

## Recommendation for Block D

- **Disposition for the implementation code (extractor.py, render.py,
  migration 012, interview/web.py and template):** `accept` with the
  Tier-0 follow-up flagged in F-RFC0028-001 (preflight parity check).
- **Disposition for the modified RFC 0028 body:** `accept` — the RFC
  text is well-motivated and consistent with the implementation; the
  status field on the RFC was promoted unilaterally and should be
  decided separately.
- **Disposition for `docs/rfcs/README.md` RFC 0028 row status
  (`accepted/partial`):** `repair` — revert to `proposal` until the
  audit-driven re-review (or an explicit operator decision) re-promotes
  it.
- **Disposition for D-082 in `DECISION_LOG.md`:** `revert` — unilateral
  acceptance. If RFC 0028 is accepted via the legitimate process, a
  fresh D### row can be written then.
- **Disposition for the `docs/reviews/rfc0028-predicate-intent-implementation/`
  subdirectory:** `quarantine`. Leave on disk under a clear marker; do
  not delete (preserves the audit chain) and do not promote.
