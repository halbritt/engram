# RFC 0017: Extraction Prompt Versioning and Cross-Corpus Dry-Run

Status: proposal
Date: 2026-05-05
Context: src/engram/extractor.py:31 (`EXTRACTION_PROMPT_VERSION`); migrations/006_claims_beliefs.sql;
RFC 0011 § Stage A; D040 (Phase 3 substrate scope); README.md § Current Status;
deferred from adversarial review 2026-05-05

This is an idea-capture RFC, not an accepted architecture decision. It proposes
(a) formalizing the extraction-prompt versioning contract that already exists
in code, (b) a re-extraction protocol that rebuilds claims and beliefs from
immutable evidence under a new prompt version, and (c) a cheap cross-corpus
dry-run gate before the claim/belief schema hardens past Phase 3.

## Background

Phase 3 restricts claim extraction to AI-conversation segments only — ChatGPT,
Claude, Gemini — per D040 and `README.md` § Current Status. Notes, Obsidian,
and live captures are excluded from the extraction run, even though the
schema reserves room for them.

Extraction prompts are already versioned at the row level. `extractor.py:31`
holds the live identifier:

```python
EXTRACTION_PROMPT_VERSION = "extractor.v5.d063.validation-repair-audited"
```

The version is persisted on each claim row (`claims.extraction_prompt_version`)
and used to gate re-extraction (`extractor.py:1361`, `extractor.py:1625`).
The mechanism exists; what is missing is the contract — when versions
increment, how re-extraction is invoked, what guarantees are preserved, and
how the prompts themselves are governed as artifacts.

The risk this RFC addresses: extraction prompts trained against analytical,
transactional AI-conversation transcripts may absorb that register's
statistical shape — predicate vocabulary, stability-class taxonomy, claim
granularity. Subjective, fragmentary, or narrative captures from Obsidian
notes have different shapes. If the claim/belief schema hardens around
AI-conversation extraction outputs and ships into downstream lane-compiler
work before any other corpus touches the extractor, ontological misfits
will be discovered late, when remediation is expensive.

This RFC does not claim the schema is wrong. It proposes a cheap test —
running the existing extractor against a small Obsidian sample — to surface
misfits while the schema is still pre-load-bearing for downstream stages.

## Proposal

### Part 1: Formalize the prompt versioning contract

The version string is the join key between an extraction artifact and its
source prompt. The contract:

- **Format.** `extractor.v{N}.{date_or_decision}.{descriptor}`. The current
  `extractor.v5.d063.validation-repair-audited` already follows this shape.
- **Storage.** Every prompt version corresponds to exactly one prompt
  artifact under `prompts/extraction/extractor_v{N}.md` (or a similar
  conventional path). The artifact is immutable once a row is persisted
  under that version.
- **Bump rules.** Increment the major version (`v5` → `v6`) on any change
  that could alter extraction outputs: prompt text, tool list, schema
  fields, or model identifier. Decision-tag and descriptor changes alone
  (without touching outputs) are forbidden — they would silently break the
  artifact join.
- **Concurrency.** Only one prompt version is "live" at a time, defined
  as the value of `EXTRACTION_PROMPT_VERSION` in `extractor.py`. Older
  versions remain queryable via the column but are not extended.

The contract is documentation of existing behavior; no code change is
required for Part 1 beyond the prompt artifact directory and a short
section in `docs/claims_beliefs.md` describing the rule.

### Part 2: Re-extraction protocol

When `EXTRACTION_PROMPT_VERSION` increments, the protocol is:

1. Raw evidence (`messages`, `notes`, `captures`, `segments`) is unchanged.
   This is the raw-is-sacred guarantee already enforced by the immutability
   triggers.
2. New claim rows are inserted with the new version. Old rows are *not*
   deleted; they remain queryable for audit and A/B comparison.
3. Bitemporal beliefs are reconsolidated from the union of claim versions
   selected by the operator (typically the latest version). Belief rows
   from the prior consolidation stay in `belief_audit`.
4. The operator step is a single CLI command — `engram re-extract --version
   <new>` — not a manual SQL ritual. The command reports row counts,
   coverage gaps (segments with no claim under the new version), and
   diff-against-prior on a sample.

This part is design-time guidance for a CLI subcommand that does not yet
exist. It is in scope for the Phase 3 → Phase 4 seam, not Phase 3 itself.

### Part 3: Cross-corpus dry-run gate

Before the claim/belief schema is treated as load-bearing for the lane
compiler (RFC 0016) or `context_for` work, run the existing extractor
against a small Obsidian sample and produce a findings doc. The intent is
falsification, not adoption.

**Sample shape.** ~50 segments drawn from the operator's actual Obsidian
vault, hand-selected to cover registers the AI-conversation corpus
under-represents: fragmentary daily notes, narrative reflection,
list-of-tasks captures, dated journal entries, and quoted external
material. The sample lives outside the corpus that will be ingested in
Phase 3 proper.

**Procedure.**

1. Manually convert the 50 sample segments to the segment schema the
   extractor consumes (no Phase 3 ingestion path is implied).
2. Run `extract_pending` against the sample with the live
   `EXTRACTION_PROMPT_VERSION`.
3. Inspect outputs against a checklist:
   - Did the extractor produce 0 claims for any segment that a human would
     consider claim-bearing? If so, what shape did it miss?
   - Did the extractor force a stability_class onto narrative content
     that doesn't fit any of the existing classes?
   - Did the predicate vocabulary look strained or AI-conversation-shaped
     when applied to subjective material?
   - Did consolidation propose contradictions between Obsidian-derived
     claims and AI-conversation-derived claims that don't actually
     contradict (different registers, different intent)?

**Output.** A findings doc under
`docs/reviews/phase3/PHASE_3_CROSS_CORPUS_DRYRUN_<date>.md`. Outcomes are
one of:

- **Clean.** Schema absorbs Obsidian shape without issue. Record and
  proceed.
- **Tunable.** Misfits exist but are addressable with prompt edits or
  taxonomy adjustments under the next prompt version. Record the deltas
  and let the normal re-extraction flow handle them later.
- **Blocking.** Misfits are structural — the schema itself can't represent
  the captured content faithfully. This is the case the dry-run exists to
  catch. Pause schema-dependent downstream work and open a follow-up RFC.

This is a one-evening exercise, not a phase. It should run against the
already-shipped Phase 3 build, ideally before the lane compiler's build
prompt is written.

### Non-goals

- Ingesting Obsidian notes in Phase 3. The not-V1 expansion-points list
  stands.
- Changing the claim/belief schema *as a result of this RFC*. The dry-run
  produces evidence; schema changes go through their own review.
- Re-running extraction against the full AI-conversation corpus under a
  new version before the lane compiler exists; that is wasted work without
  a downstream consumer.
- Shipping a `re-extract` CLI command in this RFC. Part 2 is design
  guidance for when that command is built.

## Open questions

1. Does the dry-run sample need to be checked into the repo? Probably not
   — it's the operator's private content, and the findings doc is the
   artifact that travels.
2. Should the cross-corpus check repeat at the Phase 4 / Phase 5 seam, or
   is once-before-lane-compiler enough? Likely the former, but with a
   smaller sample and only on prompt-version bumps that change taxonomy.
3. Is there a useful smaller cousin to this dry-run that runs in CI — for
   example, a fixture-based "shape regression" set of 5 hand-built
   adversarial segments? That would catch some classes of regression
   without operator-private data, but probably belongs in RFC 0015's test
   coverage scope, not here.

## Acceptance criteria for promotion

Promotion paths are split:

- **Part 1 (versioning contract):** ready to land into `docs/claims_beliefs.md`
  immediately; no DECISION_LOG entry needed since it documents existing
  behavior.
- **Part 2 (re-extraction protocol):** promote into `BUILD_PHASES.md` when
  a phase-row exists for the lane compiler or for any downstream stage that
  needs a versioned re-extraction story.
- **Part 3 (dry-run gate):** promote into `BUILD_PHASES.md` as a checklist
  item before the lane compiler build prompt is finalized. This is the
  time-sensitive piece of the RFC.
