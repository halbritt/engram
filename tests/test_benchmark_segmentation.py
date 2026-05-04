from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks.segmentation.datasets import load_public_dataset, load_public_dataset_manifest
from benchmarks.segmentation.early_signal import (
    generate_early_signal_verdicts,
    load_threshold_set,
)
from benchmarks.segmentation.fixtures import (
    BenchmarkValidationError,
    ExpectedClaim,
    load_fixtures,
)
from benchmarks.segmentation.results import relevant_segmenter_environment
from benchmarks.segmentation.sample_plan import (
    create_sample_plan,
    load_sample_plan,
    validate_sample_plan_for_manifest,
    write_sample_plan,
)
from benchmarks.segmentation.run_benchmark import main as benchmark_main
from benchmarks.segmentation.scoring import (
    boundary_precision_recall_f1,
    claim_matches,
    normalize_claim_text,
    pk_score,
    score_strategy_outputs,
    validate_provenance,
    window_tolerant_boundary_f1,
    windowdiff_score,
)
from benchmarks.segmentation.strategies import (
    DEFAULT_STRATEGIES,
    BenchmarkMessage,
    BenchmarkParent,
    LocalModelProfile,
    LocalModelStrategy,
    RunConfig,
    SegmentProposal,
    StrategyOutput,
    StrategyUnavailable,
    TOKEN_ESTIMATOR_VERSION,
    estimate_text_tokens,
)


FIXTURES_DIR = Path("benchmarks/segmentation/fixtures")


def write_manifest(
    tmp_path: Path,
    *,
    dataset_name: str = "superdialseg",
    dataset_source: str = "huggingface:Coldog2333/super_dialseg",
    dataset_version: str = "synthetic-shape-v1",
    local_path: str | None = None,
    local_path_sha256: str | None = "not-computed-for-synthetic-shape-data",
    license_accepted_at: str | None = None,
) -> Path:
    manifest = {
        "schema_version": "segmentation-public-dataset-manifest.v1",
        "dataset_name": dataset_name,
        "dataset_source": dataset_source,
        "dataset_version": dataset_version,
        "local_path": local_path
        or str((FIXTURES_DIR / "superdialseg_shape.synthetic.jsonl").resolve()),
        "local_path_sha256": local_path_sha256,
        "license_name": "synthetic-shape-data",
        "license_accepted_at": license_accepted_at,
        "preprocessing_version": "segmentation-public-preprocess.v1",
        "created_at": "2026-05-03T00:00:00Z",
    }
    path = tmp_path / f"{dataset_name}.manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def write_superdialseg_sample(
    tmp_path: Path,
    *,
    parent_count: int = 80,
    split: str = "validation",
    include_high_boundary: bool = True,
) -> Path:
    path = tmp_path / "superdialseg_many.synthetic.jsonl"
    lines = [
        json.dumps(
            {
                "record_type": "header",
                "synthetic_shape_data": True,
                "description": "not copied from SuperDialseg",
            }
        )
    ]
    for parent_index in range(parent_count):
        message_count = 14 if parent_index % 7 == 0 else 8 if parent_index % 3 == 0 else 4
        mode = parent_index % 4
        if mode == 0:
            boundary_positions: set[int] = set()
        elif mode == 1:
            boundary_positions = {2}
        elif mode == 2:
            boundary_positions = {2, 4}
        elif include_high_boundary:
            boundary_positions = {
                position for position in range(2, message_count, 2)
            }
        else:
            boundary_positions = {2, 4} if message_count > 4 else {2}
        for turn in range(message_count):
            lines.append(
                json.dumps(
                    {
                        "dial_id": f"synthetic_dialog_{parent_index:03d}",
                        "split": split,
                        "turn_id": turn,
                        "role": "user" if turn % 2 == 0 else "assistant",
                        "utterance": f"dialog {parent_index} turn {turn}",
                        "topic_id": f"topic-{sum(1 for p in boundary_positions if p <= turn)}",
                        "segmentation_label": 1
                        if (turn + 1) in boundary_positions and turn < message_count - 1
                        else 0,
                    }
                )
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_public_dataset_manifest_and_superdialseg_adapter(tmp_path):
    manifest_path = write_manifest(tmp_path)

    manifest = load_public_dataset_manifest(manifest_path)
    dataset = load_public_dataset(manifest)

    assert manifest.dataset_name == "superdialseg"
    assert len(dataset.parents) == 2
    assert dataset.parents[0].expected_boundaries == (2,)
    assert dataset.parents[0].messages[0].id != dataset.parents[0].messages[1].id


def test_superdialseg_prefers_segmentation_label_after_labeled_turn(tmp_path):
    sample = tmp_path / "superdialseg_disagreement.synthetic.jsonl"
    sample.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "record_type": "header",
                        "synthetic_shape_data": True,
                        "description": "not copied from SuperDialseg",
                    }
                ),
                json.dumps(
                    {
                        "dial_id": "dialog",
                        "turn_id": 0,
                        "role": "user",
                        "utterance": "Topic A starts.",
                        "topic_id": "A",
                        "segmentation_label": 0,
                    }
                ),
                json.dumps(
                    {
                        "dial_id": "dialog",
                        "turn_id": 1,
                        "role": "assistant",
                        "utterance": "Topic A ends here.",
                        "topic_id": "A",
                        "segmentation_label": 1,
                    }
                ),
                json.dumps(
                    {
                        "dial_id": "dialog",
                        "turn_id": 2,
                        "role": "user",
                        "utterance": "Topic B starts.",
                        "topic_id": "B",
                        "segmentation_label": 0,
                    }
                ),
                json.dumps(
                    {
                        "dial_id": "dialog",
                        "turn_id": 3,
                        "role": "assistant",
                        "utterance": "Topic B continues.",
                        "topic_id": "B",
                        "segmentation_label": 0,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manifest_path = write_manifest(tmp_path, local_path=str(sample))

    dataset = load_public_dataset(manifest_path)

    assert dataset.parents[0].expected_boundaries == (2,)


def test_dataset_source_validation_rejects_substring_forks(tmp_path):
    manifest_path = write_manifest(
        tmp_path,
        dataset_source="local:superdialseg-personal-fork",
    )

    with pytest.raises(BenchmarkValidationError, match="dataset_source"):
        load_public_dataset_manifest(manifest_path)


def test_lmsys_adapter_is_unlabeled_and_gated_license_is_explicit(tmp_path):
    sample = tmp_path / "lmsys.synthetic.jsonl"
    sample.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "record_type": "header",
                        "synthetic_shape_data": True,
                        "description": "not copied from LMSYS",
                    }
                ),
                json.dumps(
                    {
                        "conversation_id": "synthetic-lmsys-1",
                        "messages": [
                            {"role": "user", "content": "Please draft an outline."},
                            {"role": "assistant", "content": "Use three sections."},
                        ],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    missing_acceptance = write_manifest(
        tmp_path,
        dataset_name="lmsys_chat_1m",
        dataset_source="huggingface:lmsys/lmsys-chat-1m",
        local_path=str(sample),
    )
    with pytest.raises(BenchmarkValidationError, match="requires local license acceptance"):
        load_public_dataset_manifest(missing_acceptance)

    accepted = write_manifest(
        tmp_path,
        dataset_name="lmsys_chat_1m",
        dataset_source="huggingface:lmsys/lmsys-chat-1m",
        local_path=str(sample),
        license_accepted_at="2026-05-03T00:00:00Z",
    )
    dataset = load_public_dataset(accepted)
    assert dataset.parents[0].expected_boundaries is None

    strategy = DEFAULT_STRATEGIES["fixed_token_windows"]
    output = strategy.segment(
        dataset.parents[0],
        RunConfig(run_id="test", strategy_config={"target_tokens": 100}),
    )
    metrics = score_strategy_outputs(
        dataset.parents,
        {dataset.parents[0].parent_id: output},
    )
    assert metrics.operational["schema_valid_rate"] == "not_applicable"
    assert metrics.segmentation["strict_boundary"] == "not_applicable"


def test_sample_plan_is_deterministic_stratified_and_records_shortfalls(tmp_path, capsys):
    sample = write_superdialseg_sample(
        tmp_path, parent_count=65, include_high_boundary=False
    )
    manifest_path = write_manifest(tmp_path, local_path=str(sample))
    dataset = load_public_dataset(manifest_path, split="validation")

    plan_a = create_sample_plan(
        dataset,
        benchmark_tier="early_signal",
        split="validation",
        sample_seed=42,
        target_sample_size=80,
    )
    plan_b = create_sample_plan(
        dataset,
        benchmark_tier="early_signal",
        split="validation",
        sample_seed=42,
        target_sample_size=80,
    )
    plan_c = create_sample_plan(
        dataset,
        benchmark_tier="early_signal",
        split="validation",
        sample_seed=99,
        target_sample_size=80,
    )

    first_n = tuple(parent.parent_id for parent in dataset.parents[: len(plan_a.selected_parent_ids)])
    assert plan_a.selected_parent_ids == plan_b.selected_parent_ids
    assert plan_a.selected_parent_ids != first_n
    assert plan_a.selected_parent_ids != plan_c.selected_parent_ids
    assert len(plan_a.selected_parent_ids) == 65
    assert plan_a.stratum_shortfalls["high_boundary_count"] > 0
    assert plan_a.stratum_actual_sizes["high_boundary_count"] == 0

    output = tmp_path / "sample-plan.json"
    assert benchmark_main(
        [
            "sample-plan",
            "--dataset-manifest",
            str(manifest_path),
            "--split",
            "validation",
            "--benchmark-tier",
            "early_signal",
            "--sample-seed",
            "42",
            "--target-size",
            "80",
            "--output",
            str(output),
        ]
    ) == 0
    assert Path(capsys.readouterr().out.strip()) == output
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["schema_version"] == "segmentation-benchmark-sample-plan.v1"


def test_smoke_sample_plan_uses_smoke_stratum_and_cli_path(tmp_path, capsys):
    sample = write_superdialseg_sample(tmp_path, parent_count=8)
    manifest_path = write_manifest(tmp_path, local_path=str(sample))
    dataset = load_public_dataset(manifest_path, split="validation")

    plan = create_sample_plan(
        dataset,
        benchmark_tier="smoke",
        split="validation",
        sample_seed=1,
        target_sample_size=3,
    )

    assert len(plan.selected_parent_ids) == 3
    assert plan.stratum_target_sizes == {"smoke": 3}
    assert plan.stratum_actual_sizes == {"smoke": 3}
    assert plan.stratum_shortfalls == {"smoke": 0}

    output = tmp_path / "smoke-sample-plan.json"
    assert benchmark_main(
        [
            "sample-plan",
            "--dataset-manifest",
            str(manifest_path),
            "--split",
            "validation",
            "--benchmark-tier",
            "smoke",
            "--sample-seed",
            "1",
            "--target-size",
            "3",
            "--output",
            str(output),
        ]
    ) == 0
    assert Path(capsys.readouterr().out.strip()) == output
    assert load_sample_plan(output).stratum_shortfalls == {"smoke": 0}


def test_sample_plan_validation_rejects_dataset_revision_mismatch(tmp_path):
    sample = write_superdialseg_sample(tmp_path, parent_count=65)
    manifest_path = write_manifest(
        tmp_path,
        local_path=str(sample),
        local_path_sha256="revision-a",
    )
    dataset = load_public_dataset(manifest_path, split="validation")
    plan = create_sample_plan(
        dataset,
        benchmark_tier="early_signal",
        split="validation",
        sample_seed=42,
        target_sample_size=60,
    )
    changed_manifest = load_public_dataset_manifest(
        write_manifest(
            tmp_path,
            local_path=str(sample),
            local_path_sha256="revision-b",
        )
    )

    with pytest.raises(BenchmarkValidationError, match="dataset revision"):
        validate_sample_plan_for_manifest(
            plan,
            changed_manifest,
            split="validation",
        )


def test_tier1_sample_plan_validation_fails_below_minimum(tmp_path):
    sample = write_superdialseg_sample(tmp_path, parent_count=12)
    manifest_path = write_manifest(tmp_path, local_path=str(sample))
    dataset = load_public_dataset(manifest_path, split="validation")

    with pytest.raises(BenchmarkValidationError, match="minimum is 60"):
        create_sample_plan(
            dataset,
            benchmark_tier="early_signal",
            split="validation",
            sample_seed=42,
            target_sample_size=80,
        )

    lower_level_plan = create_sample_plan(
        dataset,
        benchmark_tier="early_signal",
        split="validation",
        sample_seed=42,
        target_sample_size=80,
        enforce_tier_minimum=False,
    )
    assert len(lower_level_plan.selected_parent_ids) == 12


def test_run_with_sample_plan_respects_selected_parent_order(tmp_path, capsys):
    sample = write_superdialseg_sample(tmp_path, parent_count=65)
    manifest_path = write_manifest(tmp_path, local_path=str(sample))
    dataset = load_public_dataset(manifest_path, split="validation")
    plan = create_sample_plan(
        dataset,
        benchmark_tier="early_signal",
        split="validation",
        sample_seed=7,
        target_sample_size=60,
    )
    plan_path = write_sample_plan(plan, tmp_path / "sample-plan.json")

    output_dir = tmp_path / "results"
    assert benchmark_main(
        [
            "run",
            "--dataset-manifest",
            str(manifest_path),
            "--benchmark-tier",
            "early_signal",
            "--sample-plan",
            str(plan_path),
            "--early-signal-thresholds",
            str(FIXTURES_DIR / "early_signal_thresholds.example.json"),
            "--strategy",
            "fixed_token_windows",
            "--operational-model-strategy",
            "qwen_27b_q5_k_m_d034",
            "--output-dir",
            str(output_dir),
        ]
    ) == 0
    run_path = Path(capsys.readouterr().out.strip())
    records = [
        json.loads(line)
        for line in (run_path.parent / "parents.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [record["parent"]["parent_id"] for record in records] == list(
        plan.selected_parent_ids
    )
    run_json = json.loads(run_path.read_text(encoding="utf-8"))
    assert run_json["benchmark_tier"] == "early_signal"
    assert run_json["selection_caveat"] == "early_signal_not_decision_grade"
    assert run_json["operational_model_strategy"] == "qwen_27b_q5_k_m_d034"
    assert run_json["sample_plan"]["selected_parent_count"] == 60
    assert (
        run_json["early_signal_thresholds"]["threshold_set_id"]
        == "example-non-normative"
    )
    assert "fixed_token_windows" in run_json["early_signal_verdicts"]

    assert benchmark_main(["score", "--results", str(run_path)]) == 0
    capsys.readouterr()
    score_json = json.loads((run_path.parent / "score.json").read_text(encoding="utf-8"))
    assert score_json["operational_model_strategy"] == "qwen_27b_q5_k_m_d034"
    assert (
        score_json["early_signal_thresholds"]["threshold_set_id"]
        == "example-non-normative"
    )

    assert benchmark_main(
        ["report", "--results", str(run_path), "--format", "markdown"]
    ) == 0
    capsys.readouterr()
    report_text = (run_path.parent / "report.md").read_text(encoding="utf-8")
    assert "Early-Signal Verdicts" in report_text
    assert "Fragmentation" in report_text
    assert "qwen_27b_q5_k_m_d034" in report_text
    assert "early_signal_not_decision_grade" in report_text


def test_early_signal_run_requires_sample_plan(tmp_path, capsys):
    sample = write_superdialseg_sample(tmp_path, parent_count=65)
    manifest_path = write_manifest(tmp_path, local_path=str(sample))

    assert benchmark_main(
        [
            "run",
            "--dataset-manifest",
            str(manifest_path),
            "--benchmark-tier",
            "early_signal",
            "--strategy",
            "fixed_token_windows",
            "--output-dir",
            str(tmp_path / "results"),
        ]
    ) == 2
    assert "requires --sample-plan" in capsys.readouterr().err


def test_fixture_and_expected_claim_validation():
    bundle = load_fixtures(
        FIXTURES_DIR / "synthetic_parents.example.jsonl",
        FIXTURES_DIR / "expected_claims.example.jsonl",
    )

    assert len(bundle.parents) >= 10
    tool_segment = bundle.expected_segments_by_fixture["tool_placeholder_mixed_privacy_001"][0]
    assert set(tool_segment.embeddable_message_ids) < set(tool_segment.message_ids)
    null_tool_segment = bundle.expected_segments_by_fixture[
        "null_image_tool_only_messages_001"
    ][0]
    assert set(null_tool_segment.embeddable_message_ids) < set(
        null_tool_segment.message_ids
    )
    assert sum(len(claims) for claims in bundle.expected_claims_by_fixture.values()) >= 9


def test_fixture_validation_reports_multiple_errors(tmp_path):
    bad = tmp_path / "bad_fixtures.jsonl"
    unknown = "00000000-0000-4000-8000-999999999999"
    bad.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "record_type": "header",
                        "fixture_version": "0.1.0",
                        "schema_version": "segmentation-fixtures.v1",
                    }
                ),
                json.dumps(
                    {
                        "record_type": "fixture",
                        "fixture_id": "bad",
                        "source_kind": "chatgpt",
                        "parent_id": "not-a-uuid",
                        "privacy_tier": 1,
                        "messages": [
                            {
                                "id": "00000000-0000-4000-8000-000000000001",
                                "sequence_index": 0,
                                "role": "user",
                                "content_text": "hello",
                                "privacy_tier": 1,
                            }
                        ],
                        "expected_segments": [
                            {
                                "segment_id": "s1",
                                "message_ids": [unknown],
                                "embeddable_message_ids": [unknown],
                            }
                        ],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkValidationError) as exc_info:
        load_fixtures(bad)

    message = str(exc_info.value)
    assert "invalid UUID" in message
    assert "unknown id" in message


def test_invalid_expected_claim_references_are_reported(tmp_path):
    fixtures = FIXTURES_DIR / "synthetic_parents.example.jsonl"
    claims = tmp_path / "bad_claims.jsonl"
    claims.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "record_type": "header",
                        "fixture_version": "0.1.0",
                        "schema_version": "segmentation-expected-claims.v1",
                    }
                ),
                json.dumps(
                    {
                        "record_type": "expected_claim_set",
                        "fixture_id": "short_clean_single_segment_001",
                        "claims": [
                            {
                                "claim_id": "c-bad",
                                "claim_text": "bad",
                                "evidence_message_ids": [
                                    "00000000-0000-4000-8000-999999999999"
                                ],
                                "expected_segment_ids": ["missing-segment"],
                                "privacy_tier": 1,
                            }
                        ],
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(BenchmarkValidationError) as exc_info:
        load_fixtures(fixtures, claims)

    message = str(exc_info.value)
    assert "evidence_message_ids: unknown id" in message
    assert "expected_segment_ids: unknown id" in message


def test_fixed_windows_excludes_tool_body_and_records_oversize_message():
    parent = BenchmarkParent(
        fixture_id="tool",
        source_kind="synthetic",
        parent_id="parent",
        title=None,
        privacy_tier=1,
        messages=(
            BenchmarkMessage("m1", 0, "user", "summarize", 1),
            BenchmarkMessage("m2", 1, "tool", "TOOL BODY SHOULD NOT EMBED", 2),
            BenchmarkMessage("m3", 2, "assistant", "done", 1),
            BenchmarkMessage("m4", 3, "user", "x" * 60, 1),
        ),
    )
    strategy = DEFAULT_STRATEGIES["fixed_token_windows"]
    output = strategy.segment(
        parent,
        RunConfig(
            run_id="test",
            strategy_config={"target_tokens": 5, "overlap_messages": 0},
        ),
    )

    joined_text = "\n".join(segment.content_text for segment in output.segments)
    assert "TOOL BODY" not in joined_text
    assert output.segments[-1].raw["single_message_over_target"] is True


def test_message_groups_keep_user_assistant_pairs_together():
    parent = BenchmarkParent(
        fixture_id="pairs",
        source_kind="synthetic",
        parent_id="parent",
        title=None,
        privacy_tier=1,
        messages=(
            BenchmarkMessage("m1", 0, "user", "aaaa", 1),
            BenchmarkMessage("m2", 1, "assistant", "bbbb", 1),
            BenchmarkMessage("m3", 2, "user", "cccc", 1),
            BenchmarkMessage("m4", 3, "assistant", "dddd", 1),
        ),
    )
    output = DEFAULT_STRATEGIES["message_groups"].segment(
        parent,
        RunConfig(run_id="test", strategy_config={"target_tokens": 2}),
    )

    assert output.segments[0].message_ids == ("m1", "m2")
    assert output.segments[1].message_ids == ("m3", "m4")


def test_boundary_metrics_known_case():
    strict = boundary_precision_recall_f1({2}, {3})
    tolerant = window_tolerant_boundary_f1((2,), (3,), tolerance=1)
    no_boundary_strict = boundary_precision_recall_f1(set(), set())
    no_boundary_tolerant = window_tolerant_boundary_f1((), (), tolerance=1)
    over_split = boundary_precision_recall_f1(set(), {2})
    under_split = boundary_precision_recall_f1({2}, set())

    assert strict["f1"] == 0.0
    assert tolerant["f1"] == 1.0
    assert no_boundary_strict["precision"] == 1.0
    assert no_boundary_strict["recall"] == 1.0
    assert no_boundary_strict["f1"] == 1.0
    assert no_boundary_tolerant["f1"] == 1.0
    assert over_split["f1"] == 0.0
    assert over_split["false_positives"] == 1
    assert under_split["f1"] == 0.0
    assert under_split["false_negatives"] == 1
    assert pk_score((2,), (3,), 5) == 0.5
    assert windowdiff_score((2,), (3,), 5) == 0.5


def test_provenance_validation_classifies_unknown_cross_parent_and_unordered_ids():
    parent_a = BenchmarkParent(
        fixture_id="a",
        source_kind="synthetic",
        parent_id="a",
        title=None,
        privacy_tier=1,
        messages=(
            BenchmarkMessage("a1", 0, "user", "one", 1),
            BenchmarkMessage("a2", 1, "assistant", "two", 1),
        ),
    )
    parent_b = BenchmarkParent(
        fixture_id="b",
        source_kind="synthetic",
        parent_id="b",
        title=None,
        privacy_tier=1,
        messages=(BenchmarkMessage("b1", 0, "user", "other", 1),),
    )
    failures = validate_provenance(
        parent_a,
        (
            SegmentProposal(("a2", "a1"), None, "text"),
            SegmentProposal(("missing", "b1"), None, ""),
        ),
        {"a1": "a", "a2": "a", "b1": "b"},
    )
    kinds = {failure["kind"] for failure in failures}
    assert {
        "provenance_unordered",
        "provenance_unknown_id",
        "provenance_cross_parent_id",
        "empty_embeddable_text",
    } <= kinds


def test_fragmentation_metrics_detect_false_splits_too_many_segments_and_duplicates():
    parent = BenchmarkParent(
        fixture_id=None,
        source_kind="synthetic",
        parent_id="no-boundary",
        title=None,
        privacy_tier=1,
        messages=(
            BenchmarkMessage("m1", 0, "user", "same topic one", 1),
            BenchmarkMessage("m2", 1, "assistant", "same topic two", 1),
            BenchmarkMessage("m3", 2, "user", "same topic three", 1),
        ),
        expected_boundaries=(),
    )
    output = StrategyOutput(
        strategy_name="manual",
        strategy_kind="fixed_window",
        parent_id=parent.parent_id,
        segments=(
            SegmentProposal(("m1",), None, "duplicate tiny fragment"),
            SegmentProposal(("m2",), None, "duplicate tiny fragment"),
            SegmentProposal(("m3",), None, "duplicate tiny fragment"),
        ),
    )

    metrics = score_strategy_outputs((parent,), {parent.parent_id: output})

    assert metrics.fragmentation["no_boundary_false_split_count"] == 2
    assert metrics.fragmentation["no_boundary_false_split_rate"] == 1.0
    assert metrics.fragmentation["parents_more_than_twice_expected_count"] == 1
    assert metrics.fragmentation["duplicate_adjacent_pair_count"] == 2
    assert metrics.fragmentation["adjacent_tiny_fragment_rate"] == 1.0


def test_fragmentation_label_dependent_metrics_are_not_applicable_for_unlabeled_parent():
    parent = BenchmarkParent(
        fixture_id=None,
        source_kind="synthetic",
        parent_id="unlabeled",
        title=None,
        privacy_tier=1,
        messages=(BenchmarkMessage("m1", 0, "user", "one", 1),),
        expected_boundaries=None,
    )
    output = StrategyOutput(
        strategy_name="manual",
        strategy_kind="fixed_window",
        parent_id=parent.parent_id,
        segments=(SegmentProposal(("m1",), None, "one", embeddable_message_ids=("m1",)),),
    )

    metrics = score_strategy_outputs((parent,), {parent.parent_id: output})

    assert (
        metrics.fragmentation["predicted_expected_segment_count_ratio_average"]
        == "not_applicable"
    )
    assert metrics.fragmentation["sub_100_fragment_rate"] == 1.0


def test_claim_normalization_is_nfkc_casefold_whitespace_without_punctuation_stripping():
    claim = ExpectedClaim(
        claim_id="c1",
        claim_text="Hello, world",
        evidence_message_ids=(),
        expected_segment_ids=(),
        privacy_tier=1,
        match_aliases=("resume notes",),
    )

    assert normalize_claim_text(" Re\u0301sume\u0301\tNOTES ") == "résumé notes"
    assert claim_matches(claim, "hello,   WORLD")
    assert not claim_matches(claim, "hello world")
    assert claim_matches(claim, "RESUME   notes")


def test_token_estimator_matches_production_default_and_empty_env_is_explicit(monkeypatch):
    monkeypatch.delenv("ENGRAM_SEGMENTER_MODEL", raising=False)
    monkeypatch.delenv("ENGRAM_SEGMENTER_TIMEOUT_SECONDS", raising=False)

    assert TOKEN_ESTIMATOR_VERSION == "segmentation-benchmark-token-estimator.v2"
    assert estimate_text_tokens("x" * 5) == 2
    assert relevant_segmenter_environment() == {
        "_note": "no ENGRAM_SEGMENTER_* env vars set"
    }

    monkeypatch.setenv("ENGRAM_SEGMENTER_MODEL", "local-model.gguf")
    assert relevant_segmenter_environment() == {
        "ENGRAM_SEGMENTER_MODEL": "local-model.gguf"
    }


def verdict_metric_payload(
    *,
    schema_valid_rate=1.0,
    provenance_valid_rate=1.0,
    strict_f1=0.5,
    no_boundary_false_split_rate=0.0,
):
    return {
        "operational": {
            "schema_valid_rate": schema_valid_rate,
            "provenance_valid_rate": provenance_valid_rate,
            "backend_error_counts": {
                "backend_wedge_post_smoke": 0,
                "cuda_oom": 0,
            },
            "runaway_count": 0,
        },
        "segmentation": {"strict_boundary": {"f1": strict_f1}},
        "fragmentation": {
            "predicted_expected_segment_count_ratio_average": 1.0,
            "no_boundary_false_split_rate": no_boundary_false_split_rate,
            "sub_100_fragment_rate": 0.1,
            "adjacent_tiny_fragment_rate": 0.0,
            "duplicate_adjacent_rate": 0.0,
        },
    }


def test_threshold_validation_and_structured_verdict_rules(tmp_path):
    invalid = tmp_path / "bad-thresholds.json"
    invalid.write_text(json.dumps({"schema_version": "wrong"}), encoding="utf-8")
    with pytest.raises(BenchmarkValidationError, match="unsupported schema_version"):
        load_threshold_set(invalid)

    threshold_set = load_threshold_set(
        FIXTURES_DIR / "early_signal_thresholds.example.json"
    )
    metrics = {
        "fixed_token_windows": verdict_metric_payload(strict_f1=0.5),
        "qwen_35b_a3b_iq4_xs_d034": verdict_metric_payload(strict_f1=0.6),
        "challenger": verdict_metric_payload(schema_valid_rate=0.5, strict_f1=0.9),
    }
    kinds = {
        "fixed_token_windows": "fixed_window",
        "qwen_35b_a3b_iq4_xs_d034": "llm",
        "challenger": "llm",
    }
    verdicts = generate_early_signal_verdicts(
        benchmark_tier="early_signal",
        selection_caveat="early_signal_not_decision_grade",
        metrics_by_strategy=metrics,
        strategy_kinds=kinds,
        threshold_set=threshold_set,
    )
    challenger = verdicts["challenger"]
    assert challenger["verdict"] == "reject"
    assert challenger["blocking_failures"]
    assert isinstance(challenger["metric_reasons"], dict)
    assert challenger["metric_reasons"]["schema_valid_rate"]["passed"] is False

    metrics["challenger"] = verdict_metric_payload(strict_f1=0.4)
    verdicts = generate_early_signal_verdicts(
        benchmark_tier="early_signal",
        selection_caveat="early_signal_not_decision_grade",
        metrics_by_strategy=metrics,
        strategy_kinds=kinds,
        threshold_set=threshold_set,
    )
    assert verdicts["challenger"]["verdict"] == "defer"

    metrics["challenger"] = verdict_metric_payload(strict_f1=0.9)
    metrics_without_operational = {
        "fixed_token_windows": metrics["fixed_token_windows"],
        "challenger": metrics["challenger"],
    }
    kinds_without_operational = {
        "fixed_token_windows": "fixed_window",
        "challenger": "llm",
    }
    verdicts = generate_early_signal_verdicts(
        benchmark_tier="early_signal",
        selection_caveat="early_signal_not_decision_grade",
        metrics_by_strategy=metrics_without_operational,
        strategy_kinds=kinds_without_operational,
        threshold_set=threshold_set,
    )
    assert verdicts["challenger"]["verdict"] == "longer_run"
    assert "comparison to operational model" in verdicts["challenger"]["hard_warnings"][0]

    metrics_without_baselines = {
        "qwen_35b_a3b_iq4_xs_d034": metrics["qwen_35b_a3b_iq4_xs_d034"],
        "challenger": verdict_metric_payload(strict_f1=0.9),
    }
    kinds_without_baselines = {
        "qwen_35b_a3b_iq4_xs_d034": "llm",
        "challenger": "llm",
    }
    verdicts = generate_early_signal_verdicts(
        benchmark_tier="early_signal",
        selection_caveat="early_signal_not_decision_grade",
        metrics_by_strategy=metrics_without_baselines,
        strategy_kinds=kinds_without_baselines,
        threshold_set=threshold_set,
    )
    assert verdicts["challenger"]["verdict"] == "longer_run"
    assert "deterministic baselines unavailable" in verdicts["challenger"][
        "hard_warnings"
    ][0]

    metrics["challenger"] = verdict_metric_payload(
        strict_f1=0.9,
        no_boundary_false_split_rate=0.9,
    )
    verdicts = generate_early_signal_verdicts(
        benchmark_tier="early_signal",
        selection_caveat="early_signal_not_decision_grade",
        metrics_by_strategy=metrics,
        strategy_kinds=kinds,
        threshold_set=threshold_set,
    )
    assert verdicts["challenger"]["hard_warnings"]
    assert verdicts["challenger"]["metric_reasons"]["no_boundary_false_split_rate"][
        "passed"
    ] is False


def test_absent_thresholds_prevent_candidate_verdict():
    metrics = {
        "fixed_token_windows": verdict_metric_payload(strict_f1=0.5),
        "qwen_35b_a3b_iq4_xs_d034": verdict_metric_payload(strict_f1=0.6),
        "challenger": verdict_metric_payload(strict_f1=0.9),
    }
    kinds = {
        "fixed_token_windows": "fixed_window",
        "qwen_35b_a3b_iq4_xs_d034": "llm",
        "challenger": "llm",
    }

    verdicts = generate_early_signal_verdicts(
        benchmark_tier="early_signal",
        selection_caveat="early_signal_not_decision_grade",
        metrics_by_strategy=metrics,
        strategy_kinds=kinds,
        threshold_set=None,
    )

    assert verdicts["fixed_token_windows"]["verdict"] == "defer"
    assert verdicts["challenger"]["verdict"] == "longer_run"
    assert verdicts["challenger"]["threshold_set"]["status"] == "missing"


def test_cli_validate_list_run_and_score(tmp_path, capsys):
    manifest = write_manifest(tmp_path)

    assert benchmark_main(
        [
            "validate-dataset",
            "--manifest",
            str(manifest),
        ]
    ) == 0
    assert "valid dataset" in capsys.readouterr().out

    assert benchmark_main(
        [
            "validate-fixtures",
            "--fixtures",
            str(FIXTURES_DIR / "synthetic_parents.example.jsonl"),
            "--expected-claims",
            str(FIXTURES_DIR / "expected_claims.example.jsonl"),
        ]
    ) == 0
    assert "valid fixtures" in capsys.readouterr().out

    assert benchmark_main(["list-strategies"]) == 0
    assert "fixed_token_windows" in capsys.readouterr().out

    with pytest.raises(SystemExit) as help_exit:
        benchmark_main(["run", "--help"])
    assert help_exit.value.code == 0
    help_output = capsys.readouterr().out
    assert "--allow-local-models" in help_output
    assert "Non-local URLs" in help_output
    assert "are refused" in help_output

    output_dir = tmp_path / "results"
    assert benchmark_main(
        [
            "run",
            "--dataset-manifest",
            str(manifest),
            "--strategy",
            "fixed_token_windows",
            "--strategy",
            "message_groups",
            "--output-dir",
            str(output_dir),
            "--target-tokens",
            "20",
        ]
    ) == 0
    run_path = Path(capsys.readouterr().out.strip())
    assert run_path.name == "run.json"
    assert (run_path.parent / "parents.jsonl").exists()
    run_json = json.loads(run_path.read_text(encoding="utf-8"))
    assert run_json["benchmark_tier"] == "smoke"
    assert run_json["selection_caveat"] == "smoke_only"

    assert benchmark_main(["score", "--results", str(run_path)]) == 0
    score_output = capsys.readouterr().out
    assert "segmentation-benchmark-score.v1" in score_output
    assert (run_path.parent / "score.json").exists()

    assert benchmark_main(
        [
            "report",
            "--results",
            str(run_path),
            "--format",
            "both",
            "--max-parents",
            "1",
        ]
    ) == 0
    report_output = capsys.readouterr().out
    assert "report.md" in report_output
    assert "report.html" in report_output
    report_md = run_path.parent / "report.md"
    report_html = run_path.parent / "report.html"
    assert report_md.exists()
    assert report_html.exists()
    report_text = report_md.read_text(encoding="utf-8")
    assert "Strategy Comparison" in report_text
    assert "Parent Boundary Diffs" in report_text
    assert "Fragmentation" in report_text
    assert "Benchmark tier" in report_text
    assert "positions:" in report_text
    assert "Showing 1 of 2 parents" in report_text

    old_run = json.loads(run_path.read_text(encoding="utf-8"))
    old_run.pop("benchmark_tier", None)
    old_run.pop("selection_caveat", None)
    old_run.pop("early_signal_verdicts", None)
    old_run.pop("early_signal_thresholds", None)
    for metrics in old_run["metrics"].values():
        metrics.pop("fragmentation", None)
    old_path = run_path.parent / "old-style-run.json"
    old_path.write_text(json.dumps(old_run), encoding="utf-8")
    assert benchmark_main(["score", "--results", str(old_path)]) == 0
    capsys.readouterr()
    assert benchmark_main(
        ["report", "--results", str(old_path), "--format", "markdown"]
    ) == 0
    capsys.readouterr()


class FakeLocalModelClient:
    def __init__(self, response: dict):
        self.response = response
        self.gets: list[str] = []
        self.posts: list[dict] = []

    def get_json(self, path: str, *, timeout_seconds: int) -> dict:
        self.gets.append(path)
        if path == "/v1/models":
            return {"data": [{"id": "fake-model"}]}
        if path == "/props":
            return {"total_slots": 1, "default_generation_settings": {"n_ctx": 49152}}
        raise AssertionError(f"unexpected GET {path}")

    def post_json(
        self,
        path: str,
        *,
        payload: dict,
        timeout_seconds: int,
    ) -> dict:
        self.posts.append({"path": path, "payload": payload, "timeout_seconds": timeout_seconds})
        return self.response


def llm_parent() -> BenchmarkParent:
    return BenchmarkParent(
        fixture_id="llm",
        source_kind="synthetic",
        parent_id="parent",
        title=None,
        privacy_tier=1,
        messages=(
            BenchmarkMessage("m1", 0, "user", "Topic A", 1),
            BenchmarkMessage("m2", 1, "assistant", "Topic B", 1),
        ),
    )


def test_llm_strategy_refuses_without_local_model_opt_in():
    parent = BenchmarkParent(
        fixture_id="llm",
        source_kind="synthetic",
        parent_id="parent",
        title=None,
        privacy_tier=1,
        messages=(BenchmarkMessage("m1", 0, "user", "hello", 1),),
    )
    strategy = DEFAULT_STRATEGIES["qwen_35b_a3b_iq4_xs_d034"]

    with pytest.raises(StrategyUnavailable):
        strategy.segment(parent, RunConfig(run_id="test"))


def test_llm_strategy_refuses_non_loopback_url(tmp_path):
    client = FakeLocalModelClient({"choices": []})
    strategy = LocalModelStrategy(
        LocalModelProfile("test_local_d034", str(tmp_path / "model.gguf")),
        client=client,
    )

    with pytest.raises(StrategyUnavailable):
        strategy.segment(
            llm_parent(),
            RunConfig(
                run_id="test",
                allow_local_models=True,
                strategy_config={"local_model_base_url": "http://example.com:8081"},
            ),
        )
    assert client.posts == []


def test_llm_strategy_uses_d034_schema_and_parses_segments(tmp_path):
    model_path = tmp_path / "model.gguf"
    model_path.write_bytes(b"tiny fake model")
    response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "segments": [
                                {
                                    "message_ids": ["m1"],
                                    "summary": "A",
                                    "content_text": "Topic A",
                                    "raw": {"confidence": "low"},
                                },
                                {
                                    "message_ids": ["m2"],
                                    "summary": None,
                                    "content_text": "Topic B",
                                    "raw": {},
                                },
                            ]
                        }
                    )
                }
            }
        ]
    }
    client = FakeLocalModelClient(response)
    strategy = LocalModelStrategy(
        LocalModelProfile("test_local_d034", str(model_path)),
        client=client,
    )

    output = strategy.segment(
        llm_parent(),
        RunConfig(run_id="test", allow_local_models=True),
    )

    assert output.strategy_kind == "llm"
    assert [segment.message_ids for segment in output.segments] == [("m1",), ("m2",)]
    assert output.metadata["model"]["model_path"] == str(model_path)
    assert output.metadata["model"]["size_bytes"] == len(b"tiny fake model")
    assert output.metadata["model"]["request_profile"] == "ik-llama-json-schema.d034.benchmark.v1"
    assert output.metadata["request"]["status"] == "ok"
    assert output.metadata["request"]["latency_seconds"] >= 0
    assert client.gets == ["/v1/models", "/props"]
    payload = client.posts[0]["payload"]
    assert payload["stream"] is False
    assert payload["temperature"] == 0
    assert payload["top_p"] == 1
    assert payload["chat_template_kwargs"]["enable_thinking"] is False
    assert payload["response_format"]["type"] == "json_schema"
    schema = payload["response_format"]["json_schema"]["schema"]
    enum = schema["properties"]["segments"]["items"]["properties"]["message_ids"][
        "items"
    ]["enum"]
    assert enum == ["m1", "m2"]


def test_llm_strategy_records_failed_schema_response(tmp_path):
    client = FakeLocalModelClient(
        {"choices": [{"message": {"content": "not json"}}]}
    )
    strategy = LocalModelStrategy(
        LocalModelProfile("test_local_d034", str(tmp_path / "model.gguf")),
        client=client,
    )

    output = strategy.segment(
        llm_parent(),
        RunConfig(run_id="test", allow_local_models=True),
    )

    assert output.segments == ()
    assert output.failures[0]["kind"] == "schema_invalid"
    assert output.metadata["request"]["status"] == "failed"
