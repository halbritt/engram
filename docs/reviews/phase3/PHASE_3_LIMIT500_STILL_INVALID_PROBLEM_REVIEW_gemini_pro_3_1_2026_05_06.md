# Phase 3 Limit-500 Still-Invalid Problem Review - gemini_pro_3_1

Reviewer: gemini_pro_3_1
Date: 2026-05-06
Verdict: human_checkpoint

## Summary

The limit-500 Phase 3 run remains blocked. The previous schema-rejection
repair succeeded in moving model-facing schema rejections to local Python
validation. However, when all extracted claims in a response fail local
validation and validation repair returns a `still_invalid` result, the pipeline
correctly halts as a hard operational failure according to the current policy.

The core question is whether a fully parsed, fully redacted, and fully
diagnosed all-invalid extraction should continue to trigger a hard operational
pipeline stop, or if it should be treated as a zero-claim extraction subjected
to the dropped-claim quality gate.

## Findings

### F1 - major: High Dropped-Claim Rate Risk Exceeds Quality Gate

The partial expanded dropped-claim rate at the time of the stop was about
15.7% (227 / 1448). This exceeds the 10% acceptance gate. Moving from a hard
operational failure to a zero-claim extraction (Option B or C) means this
failure mode will count toward the quality gate, likely resulting in a
downstream quality gate failure anyway.

Proposed fix: the repair spec must address whether to tune the prompt, such as
specific negative constraints for the `has_name` null-object pattern, or adjust
the quality gate threshold to ensure the run can pass the 10% threshold.

### F2 - moderate: Ambiguity in "Fully Diagnosed" for Hybrid Policy

Option C relies on the concept of a "fully diagnosed" failure to allow a
zero-claim fallback. If the definitions are too loose, we risk masking
unobservable parse errors.

Proposed fix: the repair spec must explicitly enumerate the failure classes,
for example `pre-validation failed` and specific missing fields, that qualify
for the zero-claim fallback and mandate hard failures for all unknown or
unredacted conditions.

## Recommended Policy

Option C - hybrid policy.

Rationale: Option C provides the most resilient path forward for full-corpus
execution without compromising strict observability and data loss protection.

By converting fully accounted, locally validated failures into zero-claim
extractions, the pipeline avoids stalling indefinitely on isolated model quirks
like persistently emitting a malformed `has_name` claim despite repair
instructions. Crucially, these drops remain bounded by the 10% dropped-claim
quality gate. Keeping the hard operational failure for unobservable parse
errors, strict schema rejections, or unredacted diagnostics ensures we do not
normalize silent data loss.

## Required Spec Criteria

1. Define eligible failure classes. Explicitly list which local validation
   failure classes, such as `exactly one of object_text or object_json is
   required`, are eligible to transition to an `extracted` status with
   `claim_count = 0`.
2. Require strict accounting. All final drops and validation-repair prior drops
   must be accurately recorded in `raw_payload`.
3. Preserve hard failures. Maintain a hard `failed` status for strict schema
   rejections, JSON parse errors, missing or unredacted diagnostics, unknown
   drop reasons, and quality-gate overflow.
4. Verify zero-claim consolidation. Ensure downstream consolidation correctly
   handles conversations with zero-claim segments.

## Required Tests And Gates

1. Focused Phase 3 tests. Add unit tests verifying the status transition to
   `extracted` with zero claims for fully diagnosed all-invalid outputs. Verify
   that `raw_payload` records dropped-claim diagnostics accurately without
   exposing raw text.
2. Full test suite.
3. No-work live gate:
   `.venv/bin/python -m engram.cli pipeline-3 --limit 0`
4. Targeted extraction rerun. Requeue and extract for conversation
   `06dd9815-2298-488a-b544-39a08311dae3` to prove the new zero-claim
   behavior.
5. Bounded targeted consolidation. Run consolidation for conversation
   `06dd9815-2298-488a-b544-39a08311dae3` to ensure zero-claim handling
   downstream.
6. Same-bound limit-500 gate. It must complete without hard operational
   failures and satisfy the 10% dropped-claim quality gate.

## Redaction Review

The redaction boundary in the problem description is strictly maintained. The
report correctly avoids exposing private raw text, prompt payloads, model
completions, or conversation titles. Aggregate counts, object-shape diagnostics
such as `predicate: has_name` and `object_text type: null`, and diagnostic ids
are properly used without violating RFC 0013.

## Open Questions

1. If Option C allows the pipeline to complete, but the dropped-claim rate
   remains above the 10% threshold, should we prioritize refining the prompt to
   eliminate the `has_name` null-object hallucination, or is the 10% threshold
   too tight for this model?
2. Can we add a specific negative constraint to the repair prompt instructing
   the model to never emit `has_name` with both objects null, regardless of the
   chosen pipeline policy?
