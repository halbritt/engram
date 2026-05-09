# RFC 0030 Public-Dataset Entity Grounding Adversarial Eval Review

author: eval-adversary-gemini-3.1-pro-preview-001

Status: review
Date: 2026-05-09
RFC refs: RFC-0030
Decision refs: D020, D044, D068, D076, D080
Phase refs: PHASE-0003, PHASE-0004

Lens: adversarial eval-as-oracle — operator-false-rate on entity-mismatch
as the proposed primary signal. Take the oracle apart.

## Findings

### E001 - Confounder: prompt_version bump masquerades as grounding win
Severity: blocking
Source: § D-G; § D-H; § Promotion path

The RFC says implementing grounding "bumps `EXTRACTION_PROMPT_VERSION`
per RFC 0017." That means the v8 baseline (prior prompt) and the
grounded run (new prompt) differ on TWO dimensions: (a) candidate-block
inclusion, and (b) prompt format/content. Any improvement in the
operator-false-rate could be attributed to either.

If the prompt was tightened or restructured (independent of the
candidate block), that alone could improve extraction. RFC 0028 itself
showed that adding `subject_kind_hint` improved entity classification
without grounding. The proposed bench cannot distinguish "grounding
helps" from "the new prompt is better even without grounding."

Falsification model: the bench should run THREE arms, not two:
- v8 (baseline, no grounding).
- v9 (new prompt, grounding *disabled*) — the negative control.
- v9 (new prompt, grounding *enabled*).

Only the v9-disabled vs v9-enabled comparison isolates the grounding
effect. The v8 vs v9-enabled comparison conflates prompt and
grounding.

Suggested fix: D-H must require a three-arm bench. Without it, the
oracle is fundamentally confounded.

### E002 - Gaming: resolver suppresses risky claims, lowering false-rate without quality gain
Severity: blocking
Source: § D-C output shape; § D-H

The proposed metric is operator-false-rate on the entity-mismatch
class. A trivial way to lower this is for the resolver to refuse to
attach low-confidence candidates, which means borderline claims that
*would* have been "false" no longer carry resolutions to interview.
False-rate drops; recall drops further; oracle says "improved."

This is exactly the failure mode the RFC's "refusal-of-false-precision"
principle is supposed to defend against — but it can be invoked to
*game* the metric here.

Falsification model: the bench must measure both:
- false-rate on grounded claims (lower = better).
- coverage: fraction of entity-shaped surface forms that received any
  resolution at all (higher = more coverage).

A drop in false-rate accompanied by a comparable drop in coverage is
not an improvement; it is a coverage-precision tradeoff. The RFC's
oracle as proposed cannot detect this.

Suggested fix: D-H should commit to a paired metric: false-rate AND
coverage. Acceptance criterion: false-rate drops by ≥ X% with
coverage drop ≤ Y%. Without the paired metric, the resolver wins by
pulling its punches.

### E003 - Sample size: 100 segments is well below detection threshold for entity-mismatch class
Severity: major
Source: § Promotion path step 3; § Open questions Q1

RFC 0028's failure taxonomy showed ~6 false rationales per the
re-extracted 100-segment slice (RFC 0028 § Current state). That means
the entity-mismatch class is sparse: maybe 5-10 events per 100
segments. To detect a 30% reduction in this class (3 events instead of
5), you need way more than 100 segments to clear noise.

Rough power calculation: detecting a 50% reduction in a Poisson rate
of ~5 events per 100 segments at 80% power, alpha 0.05, requires
roughly 600-1000 segments. 100 is enough for sanity, not enough for
decision.

Falsification model: Q1 ("smallest deliverable") asks the right
question; the answer "100 segments" is wrong by an order of magnitude.

Suggested fix: D-H and Q1 should commit to: "100 segments for sanity;
600+ segments for promotion-grade decision; if 100-segment slice shows
the predicted *direction*, expand to 600-segment slice; commit to
600-segment as the actual gate."

### E004 - Slice representativeness not specified
Severity: major
Source: § Promotion path step 3; § D-H

"100-segment slice" — selected how? Random over the corpus? The same
slice as RFC 0028's bench? Stratified by entity density?

A slice with low entity density will under-detect grounding's effect
because there are few entities to ground. A slice with high entity
density will over-detect because grounded resolution helps most where
entities are dense. Either choice biases the oracle.

Falsification model: the same slice that motivates grounding
(RFC 0028's failure taxonomy slice) is the right slice for the oracle
because it is the population the system is trying to improve. But
that's also the slice with the highest base-rate, which is the easiest
slice to show improvement on. Reporting "we improved on the slice we
selected for being broken" is not the same as "we improved
extraction."

Suggested fix: bench must specify (a) primary slice = RFC 0028's
failure-class slice for sanity; (b) secondary slice = random
600-segment selection across the corpus for the promotion-grade
result. Both reported.

### E005 - Secondary signal (PHASE-0004 merge-rate) is contaminated
Severity: major
Source: § D-H; § Open questions Q3

The RFC names PHASE-0004 entity-consolidation merge-rate as a secondary
signal. Q3 acknowledges that grounding feeds external refs into
consolidation. That means the secondary signal is *exactly* downstream
of the change under test: grounding produces external refs;
consolidation uses them; merge-rate moves; the bench reports
"consolidation improved." But consolidation improving here only
reflects grounding's success at the consolidation step, not extraction
quality.

Falsification model: PHASE-0004 merge-rate is a *correlated* signal,
not an *independent* one. A primary signal and a correlated secondary
signal both moving is no more evidence than the primary alone.

Suggested fix: drop merge-rate as a secondary signal. Replace with
something independent: e.g., a pre-resolved gold-set of
entity-grounding pairs (a small held-out set of 100 segments where the
operator pre-labels the correct external reference for each entity
mention). The bench reports recall/precision against this gold set.

### E006 - Negative result threshold is undefined
Severity: major
Source: § Promotion path step 3; § D-H

"If the slice shows no improvement, return to the design loop."
"No improvement" is unspecified. Is it:
- False-rate on entity-mismatch class shows no statistically
  significant decrease (p > 0.05)?
- Decrease is < 10% relative?
- Decrease but coverage drops too?

Without a pre-registered threshold, the operator has wide latitude to
declare "moved enough" or "didn't move enough" after the fact. That
removes the oracle's force.

Falsification model: pre-register the threshold. Recommend ≥ 30%
relative decrease in entity-mismatch false-rate AND coverage decrease
≤ 5% for "promote."

Suggested fix: D-H must pre-register the decision rule.

### E007 - Gold-set destabilization risk underweighted
Severity: minor
Source: § Open questions Q implicit; references to RFC 0021

RFC 0021's gold set is operator-curated and advisory. The interview
operator's verdicts inform the gold set. Once grounding is active and
candidate sets appear in interview, the operator's verdict patterns
shift (per the usability adversary's U004): they spend more time on
disambiguation, less on yes/no. This shift could change the gold set's
composition independently of extraction quality.

Falsification model: gold-set as an oracle on grounding is suspect
because grounding changes the interview UX that produces the gold-set.

Suggested fix: the bench should not lean on the gold set's verdicts
on grounded runs as the oracle. Ungrounded gold-set is a fixed
benchmark; grounded gold-set is downstream of the change under test.

### E008 - Re-running v8 baseline in May 2026 may not be reproducible
Severity: minor
Source: § Promotion path step 3; § D-H

The "v8 baseline" was generated under a specific
(prompt_version, model_version, request_profile_version) at some
earlier date. Re-running it now requires the same model checkpoint,
same prompt file, same configuration. RFC 0017's immutability covers
the prompt; the *model checkpoint* is harder. If the local model has
been updated, "v8 baseline" can't be re-run; the cached benchmark
artifacts must be trusted.

Falsification model: if the cached v8 artifacts are unavailable or
stale, the bench has no usable baseline.

Suggested fix: bench preflight should verify the v8 baseline
artifacts are available and content-hash-pinned. If not, the bench
is blocked until the operator either re-runs v8 (under the original
configuration) or accepts a v9-disabled run as the new baseline (and
loses the historical comparison).

## Oracle assessment

The proposed oracle (operator-false-rate on entity-mismatch class)
is *necessary but radically insufficient*. As specified, it is:
- confounded with prompt-version effect (E001),
- gameable via coverage drop (E002),
- under-powered at 100 segments (E003),
- selection-biased on the slice (E004),
- contaminated at the secondary signal (E005),
- under-pre-registered at the decision rule (E006).

Five of these are blocking for promotion. The RFC's promotion path
cannot stand on the proposed oracle.

verdict: needs_revision
