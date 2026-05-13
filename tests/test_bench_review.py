from __future__ import annotations

import json
import sqlite3
from argparse import Namespace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from engram.bench_review import cli as bench_cli
from engram.bench_review import detail as detail_module
from engram.bench_review import web as bench_web
from engram.bench_review.artifacts import (
    BenchReviewArtifactError,
    PriorSegmentResult,
    build_segment_comparisons,
    load_candidate_run,
    load_segment_records,
    load_slice_segment_ids,
    resolve_segment_records_path,
)
from engram.bench_review.cli import run_phase3_bench_review_serve
from engram.bench_review.detail import (
    CandidateClaimDetail,
    PriorClaimDetail,
    SegmentDetail,
)
from engram.bench_review.export import BenchReviewExportError, export_markdown, render_status
from engram.bench_review.storage import (
    BenchReviewStorageError,
    ReviewSessionConfig,
    initialize_review_db,
    record_run_decision,
    record_segment_decision,
    sanitize_rationale,
    summary,
)
from engram.bench_review.web import create_app


def _write_slice(path: Path, segment_ids: list[str]) -> None:
    path.write_text(
        json.dumps({"segments": [{"segment_id": segment_id} for segment_id in segment_ids]}),
        encoding="utf-8",
    )


def _session_config(tmp_path: Path) -> ReviewSessionConfig:
    return ReviewSessionConfig(
        run_id="run-a",
        slice_path=tmp_path / "slice.json",
        run_path=tmp_path / "run.json",
        segments_path=tmp_path / "segments.jsonl",
        candidate_prompt_version="candidate-prompt",
        candidate_model_version="candidate-model",
        candidate_request_profile_version="candidate-profile",
        prior_prompt_version="prior-prompt",
        prior_model_version="prior-model",
        prior_request_profile_version="prior-profile",
    )


def test_artifact_loader_aliases_jsonl_and_duplicate_state(tmp_path: Path) -> None:
    slice_path = tmp_path / "slice.json"
    _write_slice(slice_path, ["seg-a", "seg-b", "seg-c"])
    run_path = tmp_path / "run.json"
    run_path.write_text(
        json.dumps(
            {
                "run_id": "run-a",
                "prompt_version": "candidate-prompt",
                "model": {"model_id": "candidate-model"},
                "request_profile_version": "candidate-profile",
                "segment_records_path": "segments.jsonl",
            }
        ),
        encoding="utf-8",
    )
    segments_path = tmp_path / "segments.jsonl"
    segments_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "seg-a",
                        "claims": [
                            {"predicate": "has_name", "evidence_ids": ["m1"]},
                            {"predicate": "uses_tool", "evidence_ids": ["m2"]},
                        ],
                        "dropped_claim_count": "3",
                    }
                ),
                json.dumps({"id": "seg-b", "claim_count": 1}),
                json.dumps({"id": "seg-b", "claim_count": 2}),
                json.dumps({"id": "seg-c", "claim_count": "not-an-int"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    candidate_run = load_candidate_run(run_path)
    assert candidate_run.model_version == "candidate-model"
    assert resolve_segment_records_path(
        run_path=run_path, candidate_run=candidate_run, explicit_path=None
    ) == segments_path
    loaded = load_segment_records(segments_path)
    rows = build_segment_comparisons(
        segment_ids=load_slice_segment_ids(slice_path),
        candidate_records=loaded,
        prior_summaries={
            "seg-a": PriorSegmentResult("seg-a", 1, 0, ("has_name",), 1),
            "seg-b": PriorSegmentResult("seg-b", 1, 0, ("has_name",), 1),
            "seg-c": PriorSegmentResult("seg-c", 1, 0, ("has_name",), 1),
        },
    )
    by_id = {row.segment_id: row for row in rows}
    assert by_id["seg-a"].candidate_claim_count == 2
    assert by_id["seg-a"].candidate_dropped_count == 3
    assert "predicate_mix_changed" in by_id["seg-a"].tags
    assert by_id["seg-b"].data_state == "candidate_malformed"
    assert by_id["seg-c"].data_state == "candidate_malformed"


def test_data_state_precedence_and_queue_order(tmp_path: Path) -> None:
    _write_slice(tmp_path / "slice.json", ["seg-missing", "seg-zero", "seg-complete"])
    loaded = load_segment_records(None)
    rows = build_segment_comparisons(
        segment_ids=("seg-missing", "seg-zero", "seg-complete"),
        candidate_records=loaded,
        prior_summaries={
            "seg-zero": PriorSegmentResult("seg-zero", 2, 0, ("has_name",), 2),
            "seg-complete": PriorSegmentResult("seg-complete", 1, 0, ("has_name",), 1),
        },
    )
    assert [row.data_state for row in rows] == [
        "candidate_missing",
        "candidate_missing",
        "candidate_missing",
    ]

    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            [
                {"segment_id": "seg-zero", "claim_count": 0},
                {
                    "segment_id": "seg-complete",
                    "claim_count": 1,
                    "predicates": ["has_name"],
                    "provenance_count": 1,
                },
            ]
        ),
        encoding="utf-8",
    )
    rows = build_segment_comparisons(
        segment_ids=("seg-missing", "seg-zero", "seg-complete"),
        candidate_records=load_segment_records(records_path),
        prior_summaries={
            "seg-zero": PriorSegmentResult("seg-zero", 2, 0, ("has_name",), 2),
            "seg-complete": PriorSegmentResult("seg-complete", 1, 0, ("has_name",), 1),
        },
    )
    assert [row.segment_id for row in rows] == ["seg-zero", "seg-complete", "seg-missing"]
    assert [row.data_state for row in rows] == [
        "candidate_zero",
        "complete",
        "candidate_missing",
    ]


def test_storage_status_and_export_are_redacted(tmp_path: Path) -> None:
    db_path = tmp_path / "review.sqlite3"
    row = build_segment_comparisons(
        segment_ids=("seg-a",),
        candidate_records=load_segment_records(None),
        prior_summaries={},
    )[0]
    initialize_review_db(db_path, config=_session_config(tmp_path), rows=(row,))
    record_segment_decision(
        db_path,
        segment_id="seg-a",
        decision="needs_followup",
        rationale="  ok\t\nnote  " + "x" * 700,
    )
    record_run_decision(db_path, decision="safe_to_promote", rationale="bench ok")
    assert sanitize_rationale("a\n\nb") == "a b"
    result = summary(db_path)
    assert result["by_decision"]["needs_followup"] == 1
    assert "Bench review: safe to promote candidate" in render_status(db_path)

    outside = tmp_path / "out.md"
    with pytest.raises(BenchReviewExportError):
        export_markdown(db_path=db_path, output_path=outside, repo_root=tmp_path)
    output = tmp_path / "docs" / "reviews" / "bench.md"
    export_markdown(db_path=db_path, output_path=output, repo_root=tmp_path)
    text = output.read_text(encoding="utf-8")
    assert "seg-a" in text
    assert "claim text" in text
    assert "private-subject" not in text

    with sqlite3.connect(db_path) as conn:
        columns = [
            row[1]
            for row in conn.execute("PRAGMA table_info(segment_reviews)").fetchall()
        ]
    assert "claim_text" not in columns
    assert "segment_text" not in columns


def _fake_detail(segment_id: str) -> SegmentDetail:
    return SegmentDetail(
        segment_id=segment_id,
        summary_text="segment summary",
        segment_excerpt="segment private excerpt",
        excerpt_truncated=False,
        privacy_tier=1,
        prior_claims=(
            PriorClaimDetail(
                claim_id="claim-a",
                subject_text="private subject",
                predicate="has_name",
                object_display="private object",
                stability_class="identity",
                confidence=1.0,
                evidence_count=1,
                evidence_message_ids=("message-a",),
                privacy_tier=1,
            ),
        ),
        candidate_claims=(
            CandidateClaimDetail(
                predicate="uses_tool",
                stability_class="preference",
                confidence=0.9,
                evidence_count=2,
                evidence_message_ids=("message-a", "message-b"),
                object_kind="text",
                object_present=True,
                subject_text_present=True,
                rationale_present=True,
            ),
        ),
        candidate_detail_note="candidate metadata only",
        error=None,
    )


def test_web_rejects_cross_site_and_disables_missing_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "review.sqlite3"
    row = build_segment_comparisons(
        segment_ids=("seg-a",),
        candidate_records=load_segment_records(None),
        prior_summaries={},
    )[0]
    initialize_review_db(db_path, config=_session_config(tmp_path), rows=(row,))
    monkeypatch.setattr(
        detail_module,
        "fetch_segment_detail",
        lambda _db_path, segment_id: _fake_detail(segment_id),
    )
    client = TestClient(create_app(review_db_path=db_path))

    response = client.get("/segments/seg-a")
    assert response.status_code == 200
    assert "Regenerate the candidate segment records" in response.text
    assert "segment private excerpt" in response.text
    assert "private subject" in response.text
    assert "uses_tool" in response.text
    assert 'value="accept_candidate_change" disabled' in response.text

    response = client.post(
        "/segments/seg-a/decision",
        data={"decision": "needs_followup", "rationale": "ok"},
        headers={"origin": "http://evil.example"},
    )
    assert response.status_code == 403

    response = client.post(
        "/segments/seg-a/decision",
        data={"decision": "needs_followup", "rationale": "ok"},
        headers={"origin": "http://testserver"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_web_rejects_same_origin_tailscale_posts_without_opt_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bench_web, "ALLOWED_DNS_SUFFIXES", ())
    db_path = tmp_path / "review.sqlite3"
    row = build_segment_comparisons(
        segment_ids=("seg-a",),
        candidate_records=load_segment_records(None),
        prior_summaries={},
    )[0]
    initialize_review_db(db_path, config=_session_config(tmp_path), rows=(row,))
    monkeypatch.setattr(
        detail_module,
        "fetch_segment_detail",
        lambda _db_path, segment_id: _fake_detail(segment_id),
    )
    client = TestClient(
        create_app(review_db_path=db_path, port=8766),
        base_url="https://proximal.tail0ecc2e.ts.net:8766",
    )
    response = client.post(
        "/segments/seg-a/decision",
        data={"decision": "needs_followup", "rationale": "ok"},
        headers={"origin": "https://proximal.tail0ecc2e.ts.net:8766"},
        follow_redirects=False,
    )
    assert response.status_code == 403


def test_web_accepts_same_origin_tailscale_posts_with_suffix_opt_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bench_web, "ALLOWED_DNS_SUFFIXES", (".ts.net",))
    db_path = tmp_path / "review.sqlite3"
    row = build_segment_comparisons(
        segment_ids=("seg-a",),
        candidate_records=load_segment_records(None),
        prior_summaries={},
    )[0]
    initialize_review_db(db_path, config=_session_config(tmp_path), rows=(row,))
    monkeypatch.setattr(
        detail_module,
        "fetch_segment_detail",
        lambda _db_path, segment_id: _fake_detail(segment_id),
    )
    client = TestClient(
        create_app(review_db_path=db_path, port=8766),
        base_url="https://proximal.tail0ecc2e.ts.net:8766",
    )
    response = client.post(
        "/segments/seg-a/decision",
        data={"decision": "needs_followup", "rationale": "ok"},
        headers={"origin": "https://proximal.tail0ecc2e.ts.net:8766"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_allowed_dns_suffixes_env_var_is_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENGRAM_BENCH_REVIEW_ALLOWED_DNS_SUFFIXES", raising=False)
    assert bench_web._resolve_allowed_dns_suffixes() == ()

    monkeypatch.setenv(
        "ENGRAM_BENCH_REVIEW_ALLOWED_DNS_SUFFIXES",
        "ts.net, .example.test., ,ts.net",
    )
    assert bench_web._resolve_allowed_dns_suffixes() == (".ts.net", ".example.test")


def test_create_app_refuses_non_loopback_configured_host(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="loopback"):
        create_app(review_db_path=tmp_path / "review.sqlite3", host="0.0.0.0")


def test_segment_decision_advances_within_current_review_queue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "review.sqlite3"
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            [
                {"segment_id": "seg-a", "claim_count": 0},
                {"segment_id": "seg-b", "claim_count": 0},
                {"segment_id": "seg-c", "claim_count": 1, "predicates": ["has_name"]},
                {"segment_id": "seg-no-prior", "claim_count": 0},
            ]
        ),
        encoding="utf-8",
    )
    rows = build_segment_comparisons(
        segment_ids=("seg-a", "seg-b", "seg-c", "seg-no-prior"),
        candidate_records=load_segment_records(records_path),
        prior_summaries={
            "seg-a": PriorSegmentResult("seg-a", 1, 0, ("has_name",), 1),
            "seg-b": PriorSegmentResult("seg-b", 1, 0, ("has_name",), 1),
            "seg-c": PriorSegmentResult("seg-c", 1, 0, ("has_name",), 1),
        },
    )
    initialize_review_db(db_path, config=_session_config(tmp_path), rows=rows)
    monkeypatch.setattr(
        detail_module,
        "fetch_segment_detail",
        lambda _db_path, segment_id: _fake_detail(segment_id),
    )
    client = TestClient(create_app(review_db_path=db_path))

    response = client.get("/segments?remaining=1&reviewable=1")
    assert response.status_code == 200
    assert "seg-a" in response.text
    assert "seg-b" in response.text
    assert "seg-c" in response.text
    assert "seg-no-prior" not in response.text

    response = client.post(
        "/segments/seg-a/decision",
        data={
            "decision": "accept_candidate_change",
            "rationale": "zero is right",
            "next_state": "candidate_zero",
            "next_remaining": "1",
        },
        headers={"origin": "http://testserver"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/segments/seg-b?")
    assert "state=candidate_zero" in response.headers["location"]


def test_cli_serve_refuses_non_loopback_host() -> None:
    args = Namespace(host="0.0.0.0", port=8770)
    with pytest.raises(SystemExit) as exc:
        run_phase3_bench_review_serve(args)
    assert exc.value.code == 8


def test_cli_status_catches_expected_errors(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_status(_path: Path) -> str:
        raise BenchReviewStorageError("missing review db")

    monkeypatch.setattr(bench_cli, "render_status", fail_status)
    rc = bench_cli.run_phase3_bench_review_status(Namespace(review_db="missing.sqlite3"))
    assert rc == 1
    assert "missing review db" in capsys.readouterr().err


def test_cli_status_propagates_unexpected_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_status(_path: Path) -> str:
        raise ValueError("programming bug")

    monkeypatch.setattr(bench_cli, "render_status", fail_status)
    with pytest.raises(ValueError, match="programming bug"):
        bench_cli.run_phase3_bench_review_status(Namespace(review_db="missing.sqlite3"))


def test_cli_export_catches_expected_errors(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_export(**_kwargs: object) -> Path:
        raise BenchReviewExportError("unsafe export path")

    monkeypatch.setattr(bench_cli, "export_markdown", fail_export)
    rc = bench_cli.run_phase3_bench_review_export(
        Namespace(
            review_db="review.sqlite3",
            output="out.md",
            allow_outside_reviews=False,
        )
    )
    assert rc == 1
    assert "unsafe export path" in capsys.readouterr().err


def test_cli_export_propagates_unexpected_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_export(**_kwargs: object) -> Path:
        raise ValueError("programming bug")

    monkeypatch.setattr(bench_cli, "export_markdown", fail_export)
    with pytest.raises(ValueError, match="programming bug"):
        bench_cli.run_phase3_bench_review_export(
            Namespace(
                review_db="review.sqlite3",
                output="out.md",
                allow_outside_reviews=False,
            )
        )


def test_cli_export_catches_artifact_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail_export(**_kwargs: object) -> Path:
        raise BenchReviewArtifactError("bad artifact")

    monkeypatch.setattr(bench_cli, "export_markdown", fail_export)
    rc = bench_cli.run_phase3_bench_review_export(
        Namespace(
            review_db="review.sqlite3",
            output="out.md",
            allow_outside_reviews=False,
        )
    )
    assert rc == 1
    assert "bad artifact" in capsys.readouterr().err
