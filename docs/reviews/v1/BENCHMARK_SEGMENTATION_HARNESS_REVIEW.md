# Benchmark Segmentation Harness Review

Date: 2026-05-03T18:40:11Z
Reviewer: claude-opus-4-7 (Claude Code)
Branch: codex/benchmark-segmentation-harness
Commit: 49f09c709d710187bf0ffd4d00f67eff57fa8055
Scope: `benchmarks/segmentation/` skeleton at `git diff master...HEAD`
(8 files, 719 additions; no production code touched)

## Findings

### 1. minor: `--offline` is a permanent no-op flag, not an opt-in toggle
File/line: `benchmarks/segmentation/run_benchmark.py:30`,
`benchmarks/segmentation/SPEC.md:189-196`

The `run` subcommand declares `--offline` as
`action="store_true", default=True`. Because `store_true` only sets the
attribute to True and there is no paired `--no-offline`, the flag is True
whether or not the user passes it; the live runner cannot ever read it as
False. SPEC.md presents `--offline` as a stance the user opts in to ("`--offline`
is the default posture: no downloads, no service discovery, no model calls
unless a later implementation adds an explicit local strategy enable flag.").

The risk is that a future implementer reads the flag and assumes it gates
network access, but the flag has no information content. A reviewer scanning
the CLI also gets a false sense that offline-vs-online is configurable today.

Recommendation:
Either drop the flag entirely from the skeleton (offline is the only mode and
the spec already says so), or replace it with `argparse.BooleanOptionalAction`
plus an explicit positive flag for the future opt-in (e.g.
`--allow-local-models`, default False) so the meaning is unambiguous on day
one. SPEC.md's CLI Shape section should mirror whichever choice lands.

### 2. minor: fixture spec does not distinguish embeddable from provenance-only message ids
File/line: `benchmarks/segmentation/SPEC.md:68-78`,
`benchmarks/segmentation/fixtures/synthetic_parents.example.jsonl:4`

`docs/segmentation.md` and `src/engram/segmenter.py` enforce a sharp split:
tool/file/null messages stay in `segment.message_ids` for provenance but their
bodies must not appear in `content_text` (production substitutes a bounded
`[tool artifact omitted: ...]` placeholder). The fixture for
`tool_placeholder_mixed_privacy_001` correctly puts the tool message UUID in
the expected segment's `message_ids`, but the expected-segment schema has no
field that flags which member ids are placeholder-only. A future scorer that
checks `empty_embeddable_text`, sub-floor fragment counts, or claim-evidence
coverage cannot tell whether the tool message should contribute to embeddable
text without re-running the production placeholder rules itself.

Risk: silent divergence between the benchmark's notion of "embeddable" and
production's, masking regressions where a candidate model copies tool bodies
into `content_text` in violation of D038, or alternatively flagging compliant
models as having "empty" segments because the scorer counted only non-tool
characters.

Recommendation:
Add an `embeddable_message_ids` (or `placeholder_message_ids`) field to the
expected-segment schema, or document that scorers must derive the
distinction from each message's `placeholders`/`role` field and pin that
derivation rule in SPEC.md. Either way, make it explicit that
`message_ids ⊇ embeddable_message_ids` and that placeholder tool/null/image
messages cite for provenance only.

### 3. minor: `match_aliases` normalization is undefined, leaving claim precision/recall non-reproducible
File/line: `benchmarks/segmentation/SPEC.md:245-247`

The spec says claim matching "starts with normalized exact text plus
`match_aliases`" and defers semantic matching as an open question. It does
not define what "normalized" means: case folding, Unicode normalization
(NFKC?), whitespace collapse, punctuation stripping, stop-word handling, or
locale. Two compliant implementations could pick different normalization and
report claim precision/recall numbers that are not comparable across runs or
across reviewers reproducing the harness from this spec.

Risk: claim utility metrics drift silently, undermining the cross-strategy
comparison the benchmark exists to support.

Recommendation:
Pin a concrete normalization rule in SPEC.md (suggest: NFKC, casefold,
collapse runs of whitespace, no punctuation removal so the user's intent in
`match_aliases` is preserved) and bump the scoring implementation version
when the rule changes. If a rule cannot be picked yet, list it under Open
Questions with the explicit candidates.

### 4. minor: model SHA256 reproducibility field has no capture policy
File/line: `benchmarks/segmentation/SPEC.md:274-292`,
`docs/rfcs/0006-segmentation-model-benchmark.md:236-260`

"Model path/id and SHA256" appears in the reproducibility list, but there is
no statement about when it is computed. For a 35B-A3B Q4_XS gguf (~20+ GB on
disk) hashing on every run start adds non-trivial latency, and a careless
implementation may either skip the field or recompute it repeatedly. RFC 0006
inherits the same gap.

Risk: implementations either drop the SHA256 (silent reproducibility loss) or
spend minutes hashing per run, which discourages the "median across N reruns"
guidance in SPEC.md line 290-292.

Recommendation:
State that the SHA256 is computed once per model file via a sidecar manifest
keyed by absolute path + mtime + size, written under the scratch results
directory, and that the manifest is read on subsequent runs. Note that
manifest entries with stale mtime/size invalidate.

### 5. minor: schema_version bump policy is unspecified
File/line: `benchmarks/segmentation/SPEC.md:24-31, 84-87, 119-138`

Three `schema_version` strings are introduced (`segmentation-fixtures.v1`,
`segmentation-expected-claims.v1`, `segmentation-benchmark-result.v1`)
alongside a separate `fixture_version` semver. The spec defines bump rules
for `fixture_version` (minor on additive, major when expected outputs
change) but does not say what triggers a `schema_version` bump (renaming a
field? adding a required field? semantic-only changes?). Without a rule,
later edits will either over-bump (every additive field becomes v2) or
silently mutate v1.

Risk: stale result files cannot be safely diffed against new ones because
the schema label does not carry information about back-compat.

Recommendation:
Add a one-paragraph "Schema Version Discipline" subsection to SPEC.md:
schema_version bumps on any breaking JSON shape change (rename, removal,
required field added, type narrowing). Backwards-compatible additions stay
on the same schema_version. Every result writer records both
schema_version and the scorer's `SCORING_IMPLEMENTATION_VERSION`.

### 6. nit: implicit namespace package may surprise tooling
File/line: `benchmarks/`, `benchmarks/segmentation/` (no `__init__.py`)

`python3 -m benchmarks.segmentation.run_benchmark --help` succeeds today via
PEP 420 implicit namespace packages, but there is no `__init__.py` at either
`benchmarks/` or `benchmarks/segmentation/`. Some downstream tooling
(pytest collection with non-default rootdir, mypy in package mode, sphinx
autodoc, packaging tools) handles namespace packages inconsistently.

Recommendation:
Add empty `benchmarks/__init__.py` and `benchmarks/segmentation/__init__.py`,
or document in README.md that namespace packages are intentional.

### 7. nit: `StrategyKind` literals overlap with deferred P-FRAG enum names
File/line: `benchmarks/segmentation/strategies.py:13`,
`benchmarks/segmentation/strategies.py:90`,
`benchmarks/segmentation/SPEC.md:154`

`StrategyKind = Literal["llm", "fixed_window", "message_group"]` and the
`message_groups` strategy name reuse vocabulary from the deferred P-FRAG
schema proposal that the original prompt mistake conflated with deployed
`segments.window_strategy`. D039 keeps deployed values at `whole`/`windowed`.
The skeleton correctly does not write `message_group` as a `window_strategy`
value, but a reviewer skimming the file could mistake `StrategyKind` for the
P-FRAG enum.

Recommendation:
Add a one-line comment in `strategies.py` and a sentence in SPEC.md stating
that `StrategyKind` is an internal benchmark classifier, distinct from
`segments.window_strategy`, and is not a vehicle for P-FRAG schema
introduction (cross-link D039).

### 8. nit: backend error class taxonomy is left implicit
File/line: `benchmarks/segmentation/SPEC.md:213, 264`

Operational metrics promise "backend errors grouped by class" and failure
modes list `backend_error: local endpoint failure grouped by backend
signature` but the class taxonomy is undefined. RFC 0006 is also vague.
Without a stable taxonomy, two runs on different days will bucket errors
differently.

Recommendation:
Either enumerate the initial classes (e.g., `connect_refused`, `read_timeout`,
`http_5xx`, `grammar_stack_empty`, `cuda_oom`, `backend_wedge_post_smoke`,
`unknown`) in SPEC.md, or list it as an Open Question with the same
candidate set.

## Non-Blocking Notes

- Boundaries verified: skeleton imports nothing from `engram.*`, has no
  network/file/db side effects at import time, and `main()` aborts before
  any subcommand work runs. No production code, migration, or schema is
  touched.
- D034 / D037 / D038 / D039 are correctly preserved: the skeleton anchors
  LLM strategies to D034, references context-budget failure as D037, treats
  tool messages as placeholder-only via the `placeholders` field on the
  fixture message, and does not redefine `whole`/`windowed`.
- Metric coverage is complete versus RFC 0006: all required operational,
  segmentation, and claim-utility metrics from the RFC's Metrics section are
  present in SPEC.md's Scoring Plan, including W-F1 at +/-1 and +/-2, P_k,
  WindowDiff, sub-floor counts at 50/100/200, and privacy-tier leakage.
- Strategy interface covers all five required strategies (`current_qwen_d034`,
  `qwen_candidate_d034`, `gemma_candidate_d034`, `fixed_token_windows`,
  `message_groups`) and the `Protocol`-shaped `SegmenterStrategy` is sound.
- Reproducibility metadata in SPEC.md is the most complete I would expect
  from a skeleton: every field listed in the original prompt and RFC 0006
  is present, plus `SCORING_IMPLEMENTATION_VERSION` and an explicit
  benchmark-only extractor prompt version.
- Public dataset handling rules are appropriately strong: download outside
  the corpus-reading runtime, no redistribution of rows, no mixing into
  production, snapshot/version tracking, SuperDialseg restricted to labeled
  metrics, LMSYS-Chat-1M restricted to operational stress.
- Fixture-set size (3 example fixtures) is consistent with the original
  prompt's "placeholder/example fixture files only" instruction. Fixture
  family coverage is appropriately small but meaningful: short-clean Q&A,
  multi-topic re-entry with UUID-like-text trap, and tool-placeholder with
  mixed privacy. Cross-checked: every `expected_claim_ids` reference in
  parents has a matching `claim_id` in expected_claims, and every cited
  segment `message_ids` element exists in its parent.
- Open Questions list at the end of SPEC.md is appropriately scoped and
  surfaces the right asks for reviewers (claim-text normalization, fixed
  window token estimator, public-dataset choice, scratch-table policy,
  P-FRAG floor threshold).

## Validation

Performed (offline only, no external services):

- `python3 -m py_compile benchmarks/segmentation/{strategies,scoring,run_benchmark}.py`
  — all clean.
- `python3 -m benchmarks.segmentation.run_benchmark --help` — top-level help
  prints; subcommand help (`validate-fixtures`, `list-strategies`, `run`,
  `score`) all parse.
- `python3 -m benchmarks.segmentation.run_benchmark run --fixtures ... --strategy ... --output-dir ...`
  — parser exits 2 with "segmentation benchmark runner is not implemented
  yet", confirming the skeleton refuses to do work.
- Stdlib JSONL parse of both fixture files: header on line 1 of each;
  3 fixtures with 2/5/3 messages and 1/3/1 expected segments; every
  segment-cited UUID present in its parent's messages; every
  `expected_claim_ids` reference has a matching `claim_id`; no orphan claims.
- Side-effect grep across `benchmarks/segmentation/*.py`: no `import engram`,
  no `urllib`/`requests`, no `psycopg`/sqlite, no `os.environ` reads, no
  `open(`, no implicit network or DB connection paths.
- Direct stub probes: `DEFAULT_STRATEGIES["current_qwen_d034"].segment(None, None)`
  raises `NotImplementedError`; `scoring.validate_provenance()` raises
  `NotImplementedError`; `SCORING_IMPLEMENTATION_VERSION ==
  "segmentation-benchmark-scoring.v0"`.

Not performed (out of scope per review prompt): live benchmark runs, model
calls, public-dataset downloads, production-DB connections.

## Verdict

Pass with changes. No blockers; the skeleton respects every D-decision
boundary, isolates itself cleanly from production, and SPEC.md covers the
full set of metrics and reproducibility fields the original prompt and
RFC 0006 require. The findings above are all minor or nit-level
clarifications that strengthen reproducibility (claim normalization, model
SHA256 capture policy, schema_version discipline, fixture
embeddable-vs-provenance distinction) and tighten the CLI surface
(`--offline` semantics, namespace package, P-FRAG enum-name overlap, backend
error taxonomy). They are best resolved before the live runner lands but do
not block review of the skeleton itself.
