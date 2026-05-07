from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from benchmarks.extraction import run_benchmark as benchmark
from engram.extractor import ClaimDraft, ExtractorModelOutput, SegmentMessage, SegmentPayload


def _segment(segment_id: str, message_id: str, content: str) -> SegmentPayload:
    return SegmentPayload(
        id=segment_id,
        generation_id=f"generation-{segment_id}",
        conversation_id=f"conversation-{segment_id}",
        source_kind="chatgpt",
        message_ids=[message_id],
        content_text=content,
        summary_text="synthetic summary",
        privacy_tier=1,
        messages=[
            SegmentMessage(
                id=message_id,
                sequence_index=1,
                role="user",
                content_text=content,
            )
        ],
    )


def _config(tmp_path: Path, *, concurrency: int = 1) -> benchmark.BenchmarkRunConfig:
    return benchmark.BenchmarkRunConfig(
        backend_name="fake",
        base_url="http://127.0.0.1:18081",
        model_id="fake-model",
        request_profile_version=benchmark.BENCHMARK_REQUEST_PROFILE_VERSION,
        output_dir=tmp_path,
        max_tokens=256,
        timeout_seconds=30,
        retries=0,
        concurrency=concurrency,
        context_window=None,
        include_chat_template_kwargs=True,
        include_claim_text=False,
        compute_model_sha256=False,
    )


def test_build_chat_completion_payload_uses_d034_contract() -> None:
    payload = benchmark.build_chat_completion_payload(
        model_id="model-a",
        prompt="extract",
        max_tokens=128,
        allowed_message_ids=["m1", "m2"],
        relaxed_schema=False,
        include_chat_template_kwargs=True,
    )

    assert payload["model"] == "model-a"
    assert payload["stream"] is False
    assert payload["temperature"] == 0
    assert payload["top_p"] == 1
    assert payload["max_tokens"] == 128
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["name"] == "ClaimExtractionResult"
    schema = payload["response_format"]["json_schema"]["schema"]
    claim_schema = schema["properties"]["claims"]["items"]
    evidence_items = claim_schema["properties"]["evidence_message_ids"]["items"]
    assert evidence_items["enum"] == ["m1", "m2"]


@pytest.mark.parametrize(
    "base_url",
    [
        "http://example.com:18081",
        "http://user:pass@127.0.0.1:18081",
        "http://127.0.0.1:18081/v1",
        "http://127.0.0.1:18081?x=1",
    ],
)
def test_local_base_url_rejects_non_loopback_or_non_base_urls(base_url: str) -> None:
    with pytest.raises(Exception):
        benchmark.normalized_local_base_url(base_url)


def test_local_model_opt_in_is_required() -> None:
    with pytest.raises(benchmark.ExtractionBenchmarkError):
        benchmark.require_local_model_opt_in(False)


def test_select_balanced_slice_is_seeded_and_covers_buckets() -> None:
    candidates = [
        benchmark.SliceSegment(
            segment_id=f"{source}-{bucket}-{index}",
            generation_id=f"generation-{index}",
            conversation_id=f"conversation-{index}",
            source_kind=source,
            sequence_index=index,
            message_count=1 if bucket == "short" else 12,
            content_chars=500 if bucket == "short" else 20_000,
            size_bucket=bucket,
        )
        for source in ("chatgpt", "claude")
        for bucket in ("short", "long")
        for index in range(3)
    ]

    first = benchmark.select_balanced_slice(candidates, target_size=4, seed=19)
    second = benchmark.select_balanced_slice(candidates, target_size=4, seed=19)

    assert [row.segment_id for row in first] == [row.segment_id for row in second]
    assert {row.bucket for row in first} == {
        "chatgpt:short",
        "chatgpt:long",
        "claude:short",
        "claude:long",
    }


def test_concurrent_runner_bounds_inflight_preserves_order_and_redacts_text(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_client = ConcurrentFakeClient()
    monkeypatch.setattr(benchmark, "client_from_config", lambda config: fake_client)
    segments = [
        _segment("segment-1", "00000000-0000-0000-0000-000000000001", "slow private text"),
        _segment("segment-2", "00000000-0000-0000-0000-000000000002", "fast private text"),
    ]

    results = benchmark.run_segments_concurrently(segments, _config(tmp_path, concurrency=2))

    assert [result.segment_id for result in results] == ["segment-1", "segment-2"]
    assert fake_client.max_inflight <= 2
    assert fake_client.calls == 2
    assert all(result.status == "ok" for result in results)
    assert "object_text" not in results[0].claims[0]
    assert results[0].claims[0]["predicate"] == "prefers"


def test_all_invalid_post_repair_output_is_failed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(benchmark, "client_from_config", lambda config: InvalidClaimFakeClient())
    segment = _segment("segment-1", "00000000-0000-0000-0000-000000000001", "private text")

    result = benchmark.extract_segment_for_benchmark(1, segment, _config(tmp_path))

    assert result.status == "failed"
    assert result.schema_valid is False
    assert result.failure == {
        "kind": "local_validation_failed_post_repair",
        "error": "all extracted claims failed local validation",
    }
    assert result.dropped_claims[0]["error"] == "unknown predicate: not_a_predicate"


def test_comparison_requires_same_fixed_slice_order() -> None:
    with pytest.raises(benchmark.ExtractionBenchmarkError):
        benchmark.build_comparison_payload(
            {"metrics": {}},
            [{"segment_id": "s1", "claims": []}],
            {"metrics": {}},
            [{"segment_id": "s2", "claims": []}],
        )


def test_comparison_payload_reports_speed_and_distribution_drift() -> None:
    control_run = {
        "backend_name": "ik",
        "run_id": "control",
        "created_at": "2026-05-07T00:00:00Z",
        "model": {"model_id": "ik-model"},
        "request_profile_version": "ik-profile",
        "metrics": {
            "wall_clock_seconds": 100.0,
            "schema_valid_rate": 1.0,
            "provenance_clean_segment_rate": 1.0,
            "dropped_claim_rate": 0.0,
            "claim_count": 2,
            "segments_failed": 0,
        },
    }
    candidate_run = {
        "backend_name": "vllm",
        "run_id": "candidate",
        "created_at": "2026-05-07T00:10:00Z",
        "model": {"model_id": "vllm-model"},
        "request_profile_version": "vllm-profile",
        "metrics": {
            "wall_clock_seconds": 20.0,
            "schema_valid_rate": 1.0,
            "provenance_clean_segment_rate": 1.0,
            "dropped_claim_rate": 0.0,
            "claim_count": 2,
            "segments_failed": 0,
        },
    }
    control_records = [
        {"segment_id": "s1", "claims": [{"predicate": "prefers", "stability_class": "preference"}]},
        {
            "segment_id": "s2",
            "claims": [{"predicate": "uses_tool", "stability_class": "preference"}],
        },
    ]
    candidate_records = [
        {"segment_id": "s1", "claims": [{"predicate": "prefers", "stability_class": "preference"}]},
        {"segment_id": "s2", "claims": [{"predicate": "prefers", "stability_class": "preference"}]},
    ]

    comparison = benchmark.build_comparison_payload(
        control_run,
        control_records,
        candidate_run,
        candidate_records,
    )

    assert comparison["metrics"]["speedup"] == 5.0
    assert comparison["metrics"]["predicate_distribution_l1"] == 1.0
    assert comparison["promotion_readiness"]["checks"]["speedup_at_least_target_5x"] is True
    assert comparison["promotion_readiness"]["candidate_for_production_switch"] is False


def test_useless_empty_candidate_cannot_be_marked_production_ready() -> None:
    control_metrics = {
        "schema_valid_rate": 1.0,
        "provenance_clean_segment_rate": 1.0,
        "dropped_claim_rate": 0.0,
        "claim_count": 10,
        "segments_failed": 0,
    }
    candidate_metrics = {
        "schema_valid_rate": 1.0,
        "provenance_clean_segment_rate": 1.0,
        "dropped_claim_rate": 0.0,
        "claim_count": 0,
        "segments_failed": 0,
    }

    readiness = benchmark.promotion_readiness(
        control_metrics,
        candidate_metrics,
        {"speedup": 10.0, "dropped_claim_rate_delta": 0.0},
    )

    assert readiness["checks"]["claim_count_nonzero_if_control_nonzero"] is False
    assert readiness["candidate_for_production_switch"] is False


def test_docs_review_output_requires_review_id(tmp_path: Path) -> None:
    comparison = {
        "created_at": "2026-05-07T00:00:00Z",
        "rfc": "0019",
        "control": {"backend_name": "ik"},
        "candidate": {"backend_name": "vllm"},
        "shared_segment_count": 1,
        "metrics": {
            "speedup": 1.0,
            "schema_valid_rate_delta": 0.0,
            "provenance_clean_segment_rate_delta": 0.0,
            "dropped_claim_rate_delta": 0.0,
            "claim_count_delta": 0,
            "predicate_distribution_l1": 0.0,
            "stability_distribution_l1": 0.0,
        },
        "promotion_readiness": {"checks": {}, "note": "evidence only"},
    }

    with pytest.raises(benchmark.ExtractionBenchmarkError):
        benchmark.write_review_output(
            Path("docs/reviews/phase3/example.md"),
            review_id=None,
            comparison=comparison,
        )

    output = tmp_path / "report.md"
    review_id = "REVIEW-" + "0031"
    benchmark.write_review_output(output, review_id=review_id, comparison=comparison)
    assert output.read_text(encoding="utf-8").startswith('<a id="review-0031"></a>')


def test_endpoint_failure_summary_redacts_response_body() -> None:
    error = benchmark.LocalEndpointError(
        "HTTP 500 from local endpoint; response body redacted",
        kind="http_5xx",
    )

    assert benchmark.safe_failure_error(error) == "local endpoint error: http_5xx"
    assert "private" not in benchmark.safe_failure_error(error)


class ConcurrentFakeClient:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._inflight = 0
        self.max_inflight = 0
        self.calls = 0

    def extract(
        self,
        prompt: str,
        *,
        model_id: str,
        max_tokens: int,
        allowed_message_ids: list[str] | None = None,
        relaxed_schema: bool = False,
    ) -> ExtractorModelOutput:
        del model_id, max_tokens, relaxed_schema
        with self._lock:
            self._inflight += 1
            self.calls += 1
            self.max_inflight = max(self.max_inflight, self._inflight)
        try:
            if "slow private text" in prompt:
                time.sleep(0.05)
            evidence_id = (allowed_message_ids or ["00000000-0000-0000-0000-000000000000"])[0]
            return ExtractorModelOutput(
                claims=[
                    ClaimDraft(
                        subject_text="private subject",
                        predicate="prefers",
                        object_text="private object",
                        object_json=None,
                        stability_class="preference",
                        confidence=0.8,
                        evidence_message_ids=[evidence_id],
                        rationale="private rationale",
                    )
                ],
                model_response='{"claims":[]}',
                parse_metadata={"usage": {"prompt_tokens": 1, "completion_tokens": 1}},
            )
        finally:
            with self._lock:
                self._inflight -= 1


class InvalidClaimFakeClient:
    def extract(
        self,
        prompt: str,
        *,
        model_id: str,
        max_tokens: int,
        allowed_message_ids: list[str] | None = None,
        relaxed_schema: bool = False,
    ) -> ExtractorModelOutput:
        del prompt, model_id, max_tokens, allowed_message_ids, relaxed_schema
        return ExtractorModelOutput(
            claims=[
                ClaimDraft(
                    subject_text="private subject",
                    predicate="not_a_predicate",
                    object_text="private object",
                    object_json=None,
                    stability_class="preference",
                    confidence=0.8,
                    evidence_message_ids=["00000000-0000-0000-0000-000000000001"],
                    rationale="private rationale",
                )
            ],
            model_response='{"claims":[]}',
            parse_metadata={},
        )
