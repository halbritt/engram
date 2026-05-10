<a id="rfc-0028"></a>
# RFC 0028: Predicate-Intent Surfacing Across Extraction and Interview

| Field | Value |
|-------|-------|
| RFC | 0028 |
| Title | Predicate-Intent Surfacing Across Extraction and Interview |
| Status | accepted |
| Implementation | partial |
| Date | 2026-05-09 |
| Context | RFC 0011 § Schema (`predicate_vocabulary`); RFC 0017 (extraction prompt versioning); RFC 0021 / D079 (gold-set interview); RFC 0027 / D080 (interview web UI); D016 (eval gate sequencing); `src/engram/extractor.py:1961` (`build_extraction_prompt`); `src/engram/interview/render.py` (operator UI rendering); `predicate_vocabulary.description` column |

Decision refs:
  - D016
  - D044
  - D069
  - D079
  - D080
  - D082

Review refs:
  - striatum/rfc-0028-predicate-intent-implementation

Phase refs:
  - PHASE-0003 (extraction)
  - PHASE-0003-FOLLOWON (gold-set interview)

This RFC proposes that the **predicate vocabulary's `description` column
become first-class** at three points where it is currently invisible:
the extraction prompt sent to the local LLM, the operator-facing
interview render, and the rationale-prompt taxonomy. The motivation is
empirical: every operator-rule `false` verdict recorded so far reduces
to a predicate-intent mismatch the extractor never had a chance to
recognize because the description never reaches the prompt.

This is a small, surgical RFC. It does not change the claims, beliefs,
or gold-label schemas, does not add new predicates, and does not alter
the gold-label or claim contracts. It adds one nullable metadata column
to `predicate_vocabulary`, bumps the extraction prompt version per RFC
0017 (a routine operation), modifies the shared render helper, and
broadens one rationale prompt label.

## Current state

DB snapshot at 2026-05-09 (the local `engram` database that prompted
this RFC):

| Metric | Value |
|--------|-------|
| total `claims` | 43,812 |
| total `beliefs` | 42,558 |
| total `gold_labels` | 32 (10 sessions, hand-rolled CLI + web mix) |
| `gold_labels` verdict distribution | true=22, false=6, skip=2, stale=2 |

Predicate distribution (top 10 of `claims`):

| Predicate | Count | Stability | Cardinality | Description (DB column) |
|-----------|-------|-----------|-------------|------------------------|
| `uses_tool` | 7,205 | identity | multi_current | tool, library, language, or technology |
| `has_name` | 6,579 | identity | single_current | legal or preferred name |
| `prefers` | 4,155 | preference | multi_current | preference |
| `wants_to` | 3,684 | goal | multi_current | goal or aspiration |
| `is_related_to` | 3,040 | relationship | multi_current | named relationship |
| `feels` | 2,804 | mood | multi_current | emotion or disposition |
| `believes` | 2,705 | preference | multi_current | belief or stance |
| `talked_about` | 2,612 | preference | event | topic discussed as an event |
| `owns_repo` | 2,246 | identity | multi_current | source-code repository |
| `working_on` | 1,522 | project_status | multi_current | active project |

`has_name` + `uses_tool` together account for ~31% of all claims. They
are also the two predicates where every observed mis-application
shares the same shape: the subject does not match the predicate's
intended subject type.

Operator `false` rationales recorded in `gold_labels` so far:

| Subject | Predicate | Object | Rationale |
|---------|-----------|--------|-----------|
| Hobnob | `has_name` | Hobnob | "Hobnob is a restaurant, not a person, has_name doesn't apply" |
| Alameda | `has_name` | Encinal and Nob Hill Foods | "Alameda is a city, Encinal and Nob Hill are a street and a grocery store respectively. None are persons." |
| User | `uses_tool` | spice mix | "a spice mix is not a tool, it's a mixture of seasonings." |
| EVNotify | `is_related_to` | (null) | "EVNotify is an app" (subject was the app, not a relation target) |
| User | `feels` | Experiencing motherboard power cycling fault | "not a feeling, a hardware failure" |
| User | `prefers` | to send text updates after each open house | "no preference was expressed. I was trying to get the llm to make sense of gibberish from the real estate agent." |

Five of six (~83%) reduce to "predicate intent does not match what the
subject or evidence actually was." One (`prefers`) is an
over-extraction pattern (the LLM emitted a preference where none was
asserted) — a related but distinct failure mode this RFC also touches.

## Problem

The predicate vocabulary already encodes the intent in three columns:
`stability_class`, `cardinality_class`, and the human-readable
`description`. Two of those three reach the LLM at extraction time;
the description does not.

`src/engram/extractor.py::build_extraction_prompt` (line 1961+)
renders the vocabulary into the user prompt as:

```text
- has_name: stability=identity, cardinality=single_current, object_kind=text, required_object_keys=none
```

The model is told the predicate's structural shape but never the
sentence "legal or preferred name." Without that guidance, the LLM
shoehorns proper-noun-shaped extracts ("Hobnob", "Alameda") into
`has_name` because they look like names.

At the interview render layer
(`src/engram/interview/render.py::format_summary_line`,
`fetch_target_display`), the description column IS pulled into the
display dict (`predicate_doc`) and rendered parenthetically after the
summary line. In practice (CLI + web operator runs) the parenthetical
form is too easy to miss; operators rule on the surface text and only
notice the mismatch when something obviously wrong (a foodstuff, a
restaurant) catches their attention. Quieter mismatches (a tool that
isn't actually a tool; a relation target that's an app) slip through.

At the verdict capture layer, the `false` rationale prompt label is
"correct value > " (`render.py::RATIONALE_PROMPT_BY_VERDICT`). This
label assumes the predicate is correct and only the object value is
wrong. For predicate-intent mismatches the operator wants to say
"wrong predicate" or "wrong subject" rather than supply a corrected
object, and the prompt label actively misleads them. The rationale
field accepts free text, so this is label-misleading-but-functional;
the operator works around it (as seen in the rationales above), but
that's friction we can remove.

Together: the LLM doesn't know predicate intent, the operator can't
quickly check predicate intent, and the operator can't cleanly express
predicate-intent corrections. The eval-loop signal we want
(`gold_labels` verdicts driving prompt revision per D016) is being
collected, but the loop's input side (the prompt) doesn't yet consume
that signal.

## Proposal

Three coordinated changes, each small enough to land in one commit
each:

### 1. Surface predicate descriptions in the extraction prompt

`src/engram/extractor.py::build_extraction_prompt` renders the vocab
list with the description appended:

```text
- has_name: stability=identity, cardinality=single_current,
  object_kind=text, required_object_keys=none
  intent: legal or preferred name (persons only)
```

The `(persons only)` parenthetical is a per-predicate intent hint that
authors of this RFC propose to add to the `predicate_vocabulary`
table as a second human-readable column,
`subject_kind_hint TEXT` (NULL allowed; defaulted to NULL on the
existing rows; a follow-up migration seeds explicit hints for the top
~15 predicates from the operator-rationale evidence above). The hint
is advisory, not a constraint; the schema stays as-is otherwise.

Bump `EXTRACTION_PROMPT_VERSION` per RFC 0017's discipline. Suggested
new value: `extractor.v6.d082.predicate-intent`. The artifact for the
new prompt lands at the conventional path under the active extractor
naming. Existing claim rows stay attached to the prior version
(RFC 0017 immutability).

This is a routine prompt-version bump in the existing machinery; the
re-extraction surface from RFC 0017 (`engram phase3 re-extract
--version <new>`) already supports landing the new claims alongside
the old.

### 2. Surface predicate descriptions more prominently in the interview render

Two render-layer changes in
`src/engram/interview/render.py`:

- `format_summary_line` renders the description on its own line below
  the triple, not parenthetically inline. Example:

  ```text
  Hobnob -[has_name]-> Hobnob
    intent: legal or preferred name (persons only)
  ```

  This is one extra line per question. The operator's eye lands on
  the predicate intent before the verdict prompt, which materially
  changes the rule-on-mismatch case from "did I notice the mismatch?"
  to "is the mismatch intentional?"

- `fetch_target_display` includes a heuristic
  `subject_kind_hint_match` boolean: if the predicate's
  `subject_kind_hint` says "persons" and the subject text contains a
  string the heuristic recognizes as not-a-person (a foodstuff
  noun, a place name found in `entities` of `entity_kind='place'`,
  etc.), set the flag and render an inline warning under the intent
  line:

  ```text
  Hobnob -[has_name]-> Hobnob
    intent: legal or preferred name (persons only)
    [warning] subject "Hobnob" looks like a place/business; predicate
              intent is persons. Likely a `false` extraction.
  ```

  V1 of the heuristic is small and rule-based (entity_kind lookup +
  a hand-curated foodstuff/business-name list). v1.1 may use a local
  classifier; that's deferred.

### 3. Broaden the `false` rationale prompt label

`render.py::RATIONALE_PROMPT_BY_VERDICT` currently maps:

```python
{
    "false": "correct value > ",
    "stale": "when did it change? > ",
    "unsupported": "what's missing from the evidence? > ",
    "unsure": "note (Enter to skip) > ",
}
```

Change `false` to:

```python
"false": "what's wrong? (e.g., wrong predicate, wrong subject, "
         "different object value, predicate doesn't apply) > ",
```

The rationale field stays plain `TEXT` (no schema change); the label
just stops over-fitting to one failure mode. Optional v1.5: add a
`false_subtype` capture (enum of the four hinted failure modes) as a
nullable column on `gold_labels`; deferred until evidence shows the
operator-rationale free text is too noisy to mine for re-extraction
signal.

## Worked example

Before (current state at 2026-05-09):

```text
[3/10] claim 7f3a…  stability=identity  conf=0.93
  Hobnob -[has_name]-> Hobnob    (legal or preferred name)
  evidence: 1 row(s), evidence dates: 2025-08-04
  Q: Is this an accurate paraphrase of what was said on 2025-08-04?
verdict [t/f/stale/unsupported/unsure/skip] (q to save and quit) > f
correct value > wrong predicate, Hobnob is a restaurant
```

After (post-RFC 0028):

```text
[3/10] claim 7f3a…  stability=identity  conf=0.93
  Hobnob -[has_name]-> Hobnob
    intent: legal or preferred name (persons only)
    [warning] subject "Hobnob" looks like a place/business; predicate
              intent is persons. Likely a `false` extraction.
  evidence: 1 row(s), evidence dates: 2025-08-04
  Q: Is this an accurate paraphrase of what was said on 2025-08-04?
verdict [t/f/stale/unsupported/unsure/skip] (q to save and quit) > f
what's wrong? (e.g., wrong predicate, wrong subject, different object
value, predicate doesn't apply) > predicate doesn't apply (restaurant)
```

The operator's rationale text gets shorter because the prompt label
already prompts for the right shape of correction. The warning line
gives them a one-second confidence boost on the verdict.

The same change at the extraction layer (RFC 0017 prompt-version bump)
should reduce the population of `Hobnob -[has_name]-> Hobnob`-shape
claims that need ruling on at all. The eval-loop closes: bad pattern
identified by gold labels → extractor prompt revised → re-extraction
under new version → fewer bad-pattern rows → bandwidth freed for
quieter failure modes.

## Privacy and provenance

No change. All three changes operate on the same data surfaces with
the same permissions. The extraction prompt continues to flow only to
the local LLM endpoint (D020). The interview render layer continues
to respect the privacy-tier ceiling (D080's hard-coded Tier 1 on
`/messages/{id}` and `/q/{idx}/evidence/all`). The rationale field
continues to be append-only (RFC 0021 § Storage; D079's
`fn_gold_labels_append_only` trigger).

## What this RFC does not propose

- **No schema change to `claims`, `beliefs`, or `gold_labels`.** The
  one new column proposed (`predicate_vocabulary.subject_kind_hint`)
  is on the small vocabulary table only; it is `NULL`-able and does
  not alter the existing UNIQUE / CHECK constraints or trigger
  surfaces.
- **No new predicates, no removed predicates, no renames.** The
  vocabulary itself stays as-is. This RFC is about surfacing what's
  already there.
- **No structured `false_subtype` capture in v1.** Deferred. The
  free-text rationale field is sufficient for v1 eval-loop consumers
  to mine (the rationales above are clearly classifiable by hand);
  if v1.1 finds the noise too high, structured capture follows.
- **No change to D044 / D069 advisory posture.** Gold labels remain
  advisory inputs to Step 9 evals. A `false` verdict still does not
  flip belief status, even when the rationale explicitly identifies
  a wrong predicate.
- **No change to RFC 0027's web-UI route surface.** The render-layer
  changes propagate to both CLI and web automatically because
  `engram.interview.render` is the shared rendering surface (RFC 0027
  D081 spec deltas confirmed this is the unification point).
- **No new auth, no new transport, no non-loopback bind.** F005 still
  owns that scope.

## Open questions

1. **Subject-kind hint vocabulary.** Is `subject_kind_hint` a free
   text column or an enum? Free text is simpler and matches how
   `description` is already used; enum is stricter and prevents drift
   between predicates that share an intended subject kind. v1
   recommendation: free text, with a soft convention of values like
   `persons | places | tools | apps | concepts | events`. v1.1 may
   formalize as an enum if the values stabilize.
2. **Heuristic v1 scope.** The proposed heuristic for the
   `[warning]` line is "look up `entities.entity_kind` for the
   subject_text + a small hand-curated foodstuff/business list." How
   broad should the hand-curated list be in v1? Recommendation: keep
   it under 50 entries; expand only when operators report specific
   misses.
3. **Multiple `false` failure modes in one claim.** A claim like
   "EVNotify is_related_to (null)" is wrong on multiple axes:
   subject is an app (not a relation target), predicate is misapplied
   (no relation), object is null. The proposed rationale prompt asks
   for free text; this is fine, but if v1.5 introduces structured
   capture, the column would need to be a `TEXT[]` of subtype tags
   rather than a single enum value.
4. **Extraction prompt size budget.** Adding the description (and
   the new `subject_kind_hint`) to every predicate's vocab line in
   the prompt grows the prompt by ~500–800 tokens for the current
   vocabulary size (~25 predicates × ~30 tokens of new text). This
   is well within `ik_llama`'s 32k-slot context (RFC 0023 / D076)
   but worth measuring on a slice before the full
   re-extraction. Recommendation: bench on the existing 100-segment
   slice first, confirm extraction quality improves before
   re-extracting the whole corpus.
5. **Predicate-vocabulary discipline going forward.** Should new
   predicates require `description` and `subject_kind_hint` at
   merge time? Recommendation: yes, enforced via a small CI check
   in `make check-refs` that scans the seed list in
   `migrations/006_claims_beliefs.sql` and the runtime list in
   `src/engram/extractor.py::PREDICATE_VOCABULARY` for missing
   intent metadata. Cheap and self-documenting.
6. **Where does the warning heuristic actually live?** Render-layer
   (`render.py`, runs at interview time) vs validation-layer (a new
   pass after extraction that flags suspect rows for prioritized
   sampling). v1 lands it render-only; v1.1 may move it to a
   validation pass that influences the sampler's strata weights.

## Promotion path

1. Discuss / amend in review. Multi-agent review optional — this is a
   substantially smaller proposal than RFC 0027; the RFC 0021 review
   process is a reasonable lower bound. Owner judgment.
2. If accepted, land three commits:
   a. `migrations/012_predicate_subject_kind_hint.sql` adds the new
      column and seeds hints for the top ~15 predicates;
      `predicate_vocabulary` table stays append-only via the existing
      pattern.
   b. `src/engram/extractor.py::build_extraction_prompt` includes the
      description and the new hint in the vocab block. Bump
      `EXTRACTION_PROMPT_VERSION` to
      `extractor.v9.d082.predicate-intent`. Add a unit test pinning
      the rendered prompt shape.
   c. `src/engram/interview/render.py::format_summary_line` renders
      intent on its own line; `fetch_target_display` includes the
      heuristic warning flag. Update golden-output tests in
      `tests/test_interview_render.py`. Update
      `RATIONALE_PROMPT_BY_VERDICT["false"]` to the broadened label.
3. Bench the new extractor prompt on a bounded slice (100–500
   segments) before any full-corpus re-extraction. Measure: claim
   count, schema validity, and the population of
   `has_name`-on-non-person and `uses_tool`-on-non-tool patterns.
4. If the bench shows the targeted patterns drop, run
   `engram phase3 re-extract --version
   extractor.v9.d082.predicate-intent` against the consolidated
   corpus per RFC 0017. Old claim rows stay attached to their prior
   version; new rows land under v9 alongside.
5. Re-run interview against the v9 rows. Measure: do `false` verdicts
   drop in the predicate-intent bucket? If yes, the loop closed; the
   D016 convergence story has its first measured cycle. If no, the
   intent hint metadata or the heuristic needs revision.
6. Record the cycle's outcome in `DECISION_LOG.md` (next available
   `D###`). If the bench showed no improvement, revert the prompt
   version bump (RFC 0017 already supports this) and revisit.
