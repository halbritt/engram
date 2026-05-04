# Segmentation Benchmark Ready

Date: 2026-05-04

The RFC 0008 / D042 Tier 1 early-signal segmentation benchmark has completed
for:

- `fixed_token_windows`
- `message_groups`
- `qwen_35b_a3b_iq4_xs_d034`
- `qwen_27b_q5_k_m_d034`
- `gemma_26b_a4b_q4_k_m_d034`

Run summary:

- Review artifact:
  `docs/reviews/v1/BENCHMARK_SEGMENTATION_EARLY_SIGNAL_RUN_2026_05_04.md`
- Scratch root:
  `.scratch/benchmarks/segmentation/early-signal-20260504T073337Z`
- Production corpus: not used
- Production database: not written
- Production segmenter behavior: not changed
- Normal Qwen 35B local service: restored after the benchmark

Tier 1 is not decision-grade. The run does not authorize a production
segmenter model switch.
