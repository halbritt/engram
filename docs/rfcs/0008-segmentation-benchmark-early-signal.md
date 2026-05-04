# RFC 0008: Segmentation Benchmark Early-Signal Revision

Status: specified
Date: 2026-05-04
Context: RFC 0006; D034, D039, D041; short public model benchmark on 2026-05-03

Promoted: benchmarks/segmentation/SPEC.md and D042 on 2026-05-04

This RFC refines the public-first segmentation benchmark from RFC 0006 so it
produces a better early signal before spending hours on a longer model run.
It does not replace the need for a longer benchmark. It defines the layer
between a 10-parent smoke test and a decision-grade run.

## Background

The first public model benchmark run used 10 SuperDialseg validation parents to
validate the harness and smoke-test the Qwen 3.6 27B Q5 model. That run was
successful for its purpose:

- the public dataset download and preparation path worked;
- the benchmark-local local-model strategies exercised `ik_llama`;
- Qwen 35B, Qwen 27B, and Gemma 26B all produced schema-valid outputs;
- Qwen 27B was verified as runnable through the local patched server;
- the run produced comparable scratch artifacts and reports.

The run should not be treated as a production model-selection result. Gemma
scored best on strict SuperDialseg boundary F1, but it also produced many more
segments than Qwen 35B. That may reflect better alignment with SuperDialseg's
granular labels, or it may reflect over-fragmentation that is harmful for
Engram memory units. The current benchmark does not separate those cases well
enough.

## Problem

The benchmark needs a better early model-selection signal than "highest
SuperDialseg boundary F1 on a tiny slice."

Boundary F1 is useful, but Engram's segmenter is not only a dialogue-boundary
detector. Its output becomes the unit for embeddings, claims, beliefs,
privacy-tier propagation, and future `context_for` retrieval. A model that
maximizes boundary recall by over-splitting can look good on SuperDialseg while
creating worse memory units:

- too many small fragments;
- duplicate or near-duplicate adjacent segments;
- context-poor segment summaries;
- unnecessary splits in no-boundary or single-topic parents;
- higher downstream embedding and extraction cost;
- lower retrieval coherence.

The current harness reports some of these facts, such as segment counts and
sub-floor fragment counts, but it does not make them first-class in the early
verdict. That makes the result too easy to misread.

## Goals

- Preserve D041: public datasets first, private corpus absent from model
  comparison.
- Keep the 10-parent run as a smoke/validation tier, not a selection tier.
- Add an early-signal tier that is still cheap enough to run before long
  soaks.
- Penalize harmful fragmentation explicitly.
- Keep boundary quality visible without letting boundary F1 dominate every
  verdict.
- Add Engram-shaped public/synthetic proxy checks for memory-unit usefulness.
- Produce an explicit "continue, reject, or longer-run" recommendation.

## Non-goals

- Do not make a model-selection decision from the existing 10-parent run.
- Do not introduce private corpus dependencies.
- Do not write production database tables.
- Do not promote P-FRAG schema values into production `segments.window_strategy`
  values.
- Do not require hosted APIs, telemetry, or external judging services.
- Do not require a local LLM judge as part of the first revision.

## Benchmark Ladder

The benchmark should have three distinct tiers.

### Tier 0: Harness Smoke

Purpose: prove the machinery runs.

Recommended size: 10 labeled SuperDialseg parents.

Use this tier to validate:

- dataset preparation and manifest validation;
- model server launch and smoke completion;
- local-model strategy opt-in;
- schema/provenance parsing;
- result writing, scoring, and report rendering.

Do not use Tier 0 to pick a production model. Its verdict should say only
whether the harness and candidate are ready for a larger run.

### Tier 1: Early Signal

Purpose: cheap but meaningful model triage.

Recommended size:

- 60-100 SuperDialseg validation parents;
- plus the synthetic/Engram-proxy fixture set;
- optional LMSYS-Chat-1M sample for unlabeled operational shape if license
  acceptance has already happened locally.

Tier 1 should be enough to answer:

- Does the candidate avoid obvious over-fragmentation?
- Does it improve boundary quality after fragmentation penalties?
- Does it remain schema/provenance safe?
- Does it preserve throughput and tail latency within an acceptable envelope?
- Is it worth a longer run?

Tier 1 may recommend "continue with the operationally proven model" even when
another model has better raw boundary F1.

### Tier 2: Decision Run

Purpose: support a model/profile change.

Recommended size:

- several hundred SuperDialseg parents or the full validation split;
- all synthetic/Engram-proxy fixtures;
- an LMSYS operational-stress slice if allowed locally;
- repeated runs for nondeterminism if the local backend shows variance.

Tier 2 is where a candidate can displace the current production model. Tier 1
only determines whether Tier 2 is worth the compute.

## Early-Signal Sample Construction

The Tier 1 SuperDialseg slice should be deterministic and stratified instead
of "first N rows":

- no-boundary parents;
- 1-2 boundary parents;
- 3-5 boundary parents;
- high-boundary-count parents;
- short dialogues;
- medium dialogues;
- long dialogues near the benchmark context budget;
- mixed role patterns if present.

Record:

- dataset revision;
- split;
- fixed sample seed;
- selected parent ids;
- expected boundary count distribution;
- message count distribution.

This avoids accidentally choosing a slice that rewards one segmentation habit,
such as aggressive short-topic splitting.

## Fragmentation-Aware Scoring

Tier 1 should report raw metrics and a normalized early-signal score. The raw
metrics remain the audit trail; the composite is only a triage aid.

### Raw Boundary Metrics

Keep the current RFC 0006 metrics:

- strict boundary precision/recall/F1;
- window-tolerant F1 at +/-1 and +/-2;
- P_k;
- WindowDiff;
- over-split and under-split counts.

### Fragmentation Metrics

Promote these to first-class verdict inputs:

- average and median segments per parent;
- predicted/expected segment-count ratio for labeled parents;
- absolute segment-count distance from expected;
- no-boundary false split rate;
- sub-50, sub-100, and sub-200 estimated-token fragment rates;
- adjacent tiny-fragment rate;
- duplicate or near-duplicate adjacent summary/content rate;
- parents with more than twice the expected segment count.

The no-boundary false split rate should be a hard warning. A model that splits
a parent with no expected boundaries may be useful in some private-corpus
cases, but on a labeled no-boundary public parent it is direct evidence of
over-fragmentation.

### Engram Proxy Fixture Metrics

Synthetic fixtures should remain small, but they should cover Engram-specific
failure modes public dialogue labels do not capture:

- long coding/debugging threads;
- topic re-entry after interruption;
- repeated facts;
- quiet durable preference inside noisy conversation;
- tool/file artifact placeholders;
- null/image/tool-only messages;
- privacy-tier mixed spans;
- JSON-looking content;
- one-segment conversations;
- near context-guard conversations.

Score fixtures with:

- expected span F1;
- expected segment count distance;
- provenance validity;
- embeddable text validity;
- sub-floor fragment count;
- whether tool/file placeholders stayed provenance-only.

These fixtures should not dominate public metrics, but they should veto a
candidate that is clearly incompatible with Engram's memory-unit requirements.

## Early-Signal Verdict Rules

Tier 1 should produce one of four verdicts:

- `reject`: fails schema/provenance safety, has unacceptable backend failures,
  or severe fragmentation.
- `defer`: valid but not enough improvement to justify more compute.
- `longer_run`: promising, but evidence is insufficient for production change.
- `candidate`: strong enough on Tier 1 to schedule a Tier 2 decision run.

Suggested gates:

- schema-valid rate must be 1.0 or explain every failure;
- provenance-valid rate should be 1.0;
- no backend wedge, CUDA OOM, or runaway on Tier 1;
- no-boundary false split rate must be low and called out if nonzero;
- average segment count should not exceed expected count by more than a
  configured multiplier without improving downstream proxy metrics;
- sub-100 fragment rate should be below a configured threshold or justified by
  fixture expectations;
- boundary metrics should improve over deterministic baselines and the current
  model after fragmentation penalties.

The current production model can remain the operational choice even if another
model wins raw boundary F1. A challenger should win the combined early signal,
not just one public metric.

## Reporting Changes

The summary report should separate:

1. **Smoke status**: did the candidate run?
2. **Boundary quality**: how well did it match public labels?
3. **Fragmentation quality**: did it create useful-sized units?
4. **Engram proxy quality**: did it handle memory-specific traps?
5. **Operational quality**: did it run reliably and fast enough?
6. **Recommendation**: reject, defer, longer_run, or candidate.

Tables should include a "selection caveat" column when a metric is not
decision-grade. For example, a 10-parent run should explicitly display
`smoke_only`.

## Interpretation Of The 2026-05-03 Run

The 2026-05-03 10-parent run should be retained as a harness validation and
Qwen 27B smoke result. It does not justify switching the full segment run away
from Qwen.

The useful conclusions are:

- local-model benchmark execution works;
- SuperDialseg public data preparation works;
- Qwen 27B Q5 can run through the patched local `ik_llama` server;
- Gemma 26B is worth keeping in future evaluations;
- raw boundary F1 alone is not enough because Gemma's win coincided with
  substantially more segments.

The run should motivate a Tier 1 benchmark revision, not a production model
change.

## Implementation Plan

1. Add deterministic Tier 1 sample selection for SuperDialseg.
2. Add fragmentation metrics and make them prominent in `score.json` and
   reports.
3. Add an early-signal verdict object to benchmark results.
4. Expand synthetic/Engram-proxy fixtures for memory-unit traps.
5. Update the short-run prompt to label 10-parent runs as `smoke_only`.
6. Rerun Tier 1 for current Qwen, Qwen 27B Q5, and Gemma 26B before scheduling
   any Tier 2 model-selection run.

## Open Questions

1. What sub-100/sub-200 fragment thresholds are acceptable for Engram?
2. Should the composite score be a weighted number, a rules-based verdict, or
   both?
3. Should LMSYS-Chat-1M become part of Tier 1 despite its license handling
   overhead, or remain Tier 2 operational stress only?
4. How many synthetic proxy fixtures are enough before they become a private
   benchmark by another name?
5. Should a local evaluator model ever judge segment coherence, or should the
   first revision stay fully deterministic?

## Recommendation

Revise the benchmark before using it for production model selection. Continue
the current full segment run with the operationally proven Qwen profile unless
Tier 1 plus Tier 2 evidence says otherwise.
