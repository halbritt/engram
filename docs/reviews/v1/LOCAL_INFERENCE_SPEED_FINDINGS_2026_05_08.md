<a id="review-0033"></a>
# Local Inference Speed Findings

Review ID: REVIEW-0033
Status: findings
Date: 2026-05-08
RFC refs:
  - RFC-0010
  - RFC-0019
  - RFC-0020
Decision refs:
  - D034
  - D042
Phase refs:
  - PHASE-0002
  - PHASE-0003

## Redaction Boundary

This report records only commands, aggregate metrics, server flags, error
classes, and scratch artifact paths. It does not include private corpus text,
public benchmark dialogue text, prompt payloads, model completions,
conversation titles, claim values, belief values, or user-derived prose
summaries.

Extraction probes used a fixed 24-segment local active-segment slice from the
production database. Scratch segment records remain under `.scratch/` and were
not committed. Segmentation probes used the local public SuperDialseg
validation snapshot. All model endpoints were bound to `127.0.0.1`.

## Context

The GPU was otherwise idle for this run. The goal was to look for practical
speed gains for Phase 2 segmentation and Phase 3 extraction without changing
production code or production defaults.

The current user systemd `ik-llama-server.service` profile uses:

```text
--ctx-size 49152
--parallel 1
--batch-size 2048
--ubatch-size 512
--cache-type-k q8_0
--cache-type-v q8_0
--flash-attn on
--threads 8
--gpu-layers 99
--jinja
```

## Extraction Results

The extraction benchmark used the production Phase 3 extractor prompt, schema,
parser, chunking, and validation salvage code, but wrote only scratch
artifacts. The fixed slice was:

```text
.scratch/benchmarks/extraction-backend/slices/speed-seed29-24.json
```

It contained 24 active segments stratified across source-kind and size buckets.

| Profile | Segments ok | Failed | Claims | Dropped rate | Schema valid | Provenance clean | Wall sec | Segment/s | Claim/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `parallel=1 ubatch=512 max_tokens=8192` | 24 | 0 | 103 | 0.055 | 1.000 | 1.000 | 476.1 | 0.0504 | 0.216 |
| `parallel=1 ubatch=2048 max_tokens=8192` | 23 | 1 | 99 | 0.010 | 0.958 | 0.958 | 513.6 | 0.0467 | 0.193 |
| `parallel=2 ubatch=512 concurrency=2 max_tokens=8192` | 24 | 0 | 79 | 0.092 | 1.000 | 1.000 | 481.1 | 0.0499 | 0.164 |
| `parallel=2 ubatch=512 concurrency=4 max_tokens=8192` | 24 | 0 | 89 | 0.063 | 1.000 | 1.000 | 548.0 | 0.0438 | 0.162 |
| `chunk=6/3000 max_tokens=6144` | 24 | 0 | 104 | 0.055 | 1.000 | 1.000 | 400.1 | 0.0600 | 0.260 |
| `chunk=6/3000 max_tokens=8192` | 24 | 0 | 104 | 0.055 | 1.000 | 1.000 | 479.6 | 0.0500 | 0.217 |
| `default chunks max_tokens=6144` | 24 | 0 | 103 | 0.055 | 1.000 | 1.000 | 392.2 | 0.0612 | 0.263 |
| `default chunks max_tokens=6144` repeat | 24 | 0 | 103 | 0.055 | 1.000 | 1.000 | 395.0 | 0.0609 | 0.261 |

### Extraction Findings

`ubatch=2048` is not a useful extraction profile from this run. It was slower
than `ubatch=512` and introduced one failed segment.

Two-slot serving is also not a useful extraction speed profile from this run.
`parallel=2` with two concurrent clients was effectively tied on wall time and
had materially lower claim throughput. Overloading two slots with four clients
was slower.

The useful candidate is `max_tokens=6144` with the current single-slot
`ubatch=512` server profile. It repeated cleanly on the same 24-segment slice:
`392.2s` and `395.0s` versus the `476.1s` control, with the same claim count,
dropped-claim rate, schema validity, provenance validity, prompt token count,
and completion token count. That is about a `17%` wall-clock improvement on
this slice.

Smaller initial chunks did not appear to be the primary win. `chunk=6/3000`
with `max_tokens=8192` was essentially tied with the control. `chunk=6/3000`
with `max_tokens=6144` was fast, but slightly slower than default chunks with
`max_tokens=6144`.

This should not be promoted from a 24-segment slice alone. It is strong enough
to justify a larger fixed-slice validation run.

## Segmentation Results

The prior segmentation server-profile benchmark already showed:

- raw `ubatch=2048` improves prefill throughput;
- `ubatch=2048` did not improve Tier 1 end-to-end segmentation throughput;
- `ubatch=2048` failed Tier 1 hard gates;
- `parallel=2` and `parallel=4` were slower than single-slot serving.

This run added a quick 10-parent SuperDialseg smoke for lower segmentation
`max_tokens` values using the current `ubatch=512` single-slot server profile.

| `max_tokens` | Wall sec | Schema valid | Provenance valid | Strict F1 | Pk | WindowDiff | Unordered ids |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4096 | 61 | 1.000 | 0.900 | 0.283 | 0.364 | 0.364 | 1 |
| 2048 | 60 | 1.000 | 0.900 | 0.283 | 0.364 | 0.364 | 1 |
| 1024 | 58 | 0.900 | 0.900 | 0.226 | 0.377 | 0.377 | 1 |

### Segmentation Findings

The `max_tokens=2048` smoke matched the 4096-token smoke on aggregate quality
and wall time, but this was only a 10-parent slice and is not enough to change
segmentation defaults.

The `max_tokens=1024` smoke should be rejected for this request shape because
schema validity dropped to `0.900`.

No server-side segmentation speed gain was found in this GPU window. The likely
next segmentation gains are operational/profile discipline rather than
backend-slot concurrency:

- pin `ENGRAM_SEGMENTER_MODEL` during long production runs so the segmenter can
  skip repeated model probing;
- test a lower `ENGRAM_SEGMENTER_RETRY_MAX_TOKENS` to reduce runaway retry
  cost and context-shift risk;
- test smaller `ENGRAM_SEGMENTER_WINDOW_CHAR_BUDGET` values against Tier 1 /
  bounded production preflights;
- do not run multiple production segmenter workers until parent-level leasing
  and timeout behavior are concurrency-safe.

## Recommended Next Step

For extraction, run a larger fixed-slice benchmark comparing only:

1. control: current `max_tokens=8192`, `ubatch=512`, `parallel=1`;
2. candidate: `max_tokens=6144`, `ubatch=512`, `parallel=1`.

Use at least the existing 100-segment RFC 0019 slice before changing any
production default. Promotion gates should require:

- 100% segment completion;
- schema-valid and provenance-clean rates at least equal to control;
- same-slice claim count materially close to control;
- dropped-claim rate at or below control;
- no obvious predicate or stability distribution drift;
- no new backend error class.

For segmentation, run Tier 1 before considering a lower `max_tokens` profile.
The 2048-token smoke is only a cheap signal, not decision-grade evidence.

## Evidence Artifacts

Scratch artifacts retained locally:

- `.scratch/benchmarks/extraction-backend/slices/speed-seed29-24.json`
- `.scratch/benchmarks/extraction-backend/speed-20260508/`
- `.scratch/benchmarks/segmentation/speed-20260508/`
