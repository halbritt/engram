"""Tests for RFC 0017 Part 2 ``engram re-extract`` CLI subcommand and the
``extractor.re_extract`` orchestration function.

Coverage of the dispatch surface (CLI argv → orchestrator kwargs) follows the
pattern in ``tests/test_cli.py``. Coverage of the protocol semantics (new rows
under the new version, old rows preserved, raw evidence unchanged, coverage
gap report, sample diff) uses the live ``conn`` DB fixture and a stubbed
extractor client mirroring ``tests/test_phase3_claims_beliefs.py``.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest
from test_phase3_claims_beliefs import (
    StaticExtractor,
    active_segment,
    insert_extracted_claim,
)

from engram import cli, extractor
from engram.extractor import (
    EXTRACTION_PROMPT_VERSION,
    ClaimDraft,
    ReExtractError,
    re_extract,
)

# Per-test target version, valid format, never equal to the live constant.
TARGET_VERSION = "extractor.v99.test.synthetic"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_connect(monkeypatch: pytest.MonkeyPatch, conn: Any) -> Any:
    """Make ``cli.connect`` yield the live test connection."""

    @contextmanager
    def _fake_connect(*args: Any, **kwargs: Any) -> Iterator[Any]:
        yield conn

    monkeypatch.setattr(cli, "connect", _fake_connect)
    return conn


@pytest.fixture(autouse=True)
def patch_health_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    """Suppress the live health smoke and model-id probe across this module."""

    monkeypatch.setattr(cli, "run_extractor_health_smoke", lambda *a, **k: None)
    monkeypatch.setattr(cli, "default_extractor_model_id", lambda: "model-a")
    monkeypatch.setattr(cli, "IkLlamaExtractorClient", lambda: object())
    monkeypatch.setattr(
        cli, "apply_phase3_reclassification_invalidations", lambda _conn: None
    )
    # extractor.extract_claims_from_segment also calls these via the path
    monkeypatch.setattr(
        extractor,
        "apply_phase3_reclassification_invalidations",
        lambda _conn: None,
    )
    monkeypatch.setattr(extractor, "reap_stale_extractions", lambda _conn: None)
    monkeypatch.setattr(extractor, "default_extractor_model_id", lambda: "model-a")


# ---------------------------------------------------------------------------
# CLI dispatch surface
# ---------------------------------------------------------------------------


def test_re_extract_cli_dispatches_with_kwargs(
    monkeypatch: pytest.MonkeyPatch, fake_connect: Any
) -> None:
    captured: dict[str, Any] = {}

    def fake_orchestrator(connection: Any, target_version: str, **kwargs: Any) -> Any:
        captured["conn"] = connection
        captured["target_version"] = target_version
        captured.update(kwargs)
        return _fake_result(target_version)

    monkeypatch.setattr(cli, "re_extract", fake_orchestrator)

    rc = cli.main(
        [
            "phase3",
            "re-extract",
            "--version",
            "extractor.v9.d999.smoke",
            "--batch-size",
            "7",
            "--limit",
            "11",
            "--source-id",
            "src-abc",
            "--diff-sample",
            "3",
        ]
    )

    assert rc == 0
    assert captured["target_version"] == "extractor.v9.d999.smoke"
    assert captured["batch_size"] == 7
    assert captured["limit"] == 11
    assert captured["source_id"] == "src-abc"
    assert captured["diff_sample"] == 3
    assert captured["dry_run"] is False


def test_re_extract_cli_missing_version_exits_nonzero() -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["phase3", "re-extract"])
    assert excinfo.value.code != 0


def test_re_extract_cli_bad_version_format_exits_nonzero(
    fake_connect: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = cli.main(["phase3", "re-extract", "--version", "not-a-valid-format"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "re-extract" in err.lower()
    assert "format" in err.lower() or "extractor.v" in err


def test_re_extract_cli_rejects_same_version(
    fake_connect: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = cli.main(["phase3", "re-extract", "--version", EXTRACTION_PROMPT_VERSION])
    assert rc == 1
    err = capsys.readouterr().err
    assert "re-extract" in err.lower()
    assert "same" in err.lower() or "wasteful" in err.lower() or "equals" in err.lower()


# ---------------------------------------------------------------------------
# Protocol semantics (DB-backed)
# ---------------------------------------------------------------------------


def test_re_extract_dry_run_writes_no_rows(
    fake_connect: Any, conn: Any
) -> None:
    conv_id, gen_id, seg_id, msg_ids = active_segment(
        conn, [("user", "I use Postgres", 1)]
    )
    insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=[msg_ids[0]],
        predicate="uses_tool",
        object_text="Postgres",
        prompt_version="extractor.v1.test.prior",
    )
    initial_extractions = conn.execute(
        "SELECT count(*) FROM claim_extractions"
    ).fetchone()[0]
    initial_claims = conn.execute("SELECT count(*) FROM claims").fetchone()[0]

    rc = cli.main(
        ["phase3", "re-extract", "--dry-run", "--version", TARGET_VERSION]
    )

    assert rc == 0
    assert (
        conn.execute("SELECT count(*) FROM claim_extractions").fetchone()[0]
        == initial_extractions
    )
    assert conn.execute("SELECT count(*) FROM claims").fetchone()[0] == initial_claims


def test_re_extract_creates_new_rows_under_new_version_and_preserves_old(
    fake_connect: Any,
    conn: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conv_id, gen_id, seg_id, msg_ids = active_segment(
        conn, [("user", "I use Postgres", 1)]
    )
    insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=[msg_ids[0]],
        predicate="uses_tool",
        object_text="Postgres",
        prompt_version="extractor.v1.test.prior",
    )
    prior_extraction_ids = {
        row[0]
        for row in conn.execute(
            "SELECT id::text FROM claim_extractions"
        ).fetchall()
    }
    prior_claim_ids = {
        row[0]
        for row in conn.execute("SELECT id::text FROM claims").fetchall()
    }
    raw_message_count_before = conn.execute(
        "SELECT count(*) FROM messages"
    ).fetchone()[0]
    segment_count_before = conn.execute(
        "SELECT count(*) FROM segments"
    ).fetchone()[0]

    static_client = StaticExtractor(
        [
            ClaimDraft(
                "user",
                "uses_tool",
                "Postgres",
                None,
                "preference",
                0.9,
                msg_ids,
                "post-bump",
            )
        ]
    )
    monkeypatch.setattr(cli, "IkLlamaExtractorClient", lambda: static_client)

    rc = cli.main(["phase3", "re-extract", "--version", TARGET_VERSION])
    assert rc == 0

    # New rows under the new version exist.
    new_versions = {
        row[0]
        for row in conn.execute(
            "SELECT extraction_prompt_version FROM claim_extractions"
        ).fetchall()
    }
    assert TARGET_VERSION in new_versions
    assert "extractor.v1.test.prior" in new_versions

    # Old rows are still present, byte-for-byte.
    surviving_extractions = {
        row[0]
        for row in conn.execute(
            "SELECT id::text FROM claim_extractions"
        ).fetchall()
    }
    assert prior_extraction_ids.issubset(surviving_extractions)
    surviving_claims = {
        row[0] for row in conn.execute("SELECT id::text FROM claims").fetchall()
    }
    assert prior_claim_ids.issubset(surviving_claims)

    # New version produced at least one claim.
    new_claim_count = conn.execute(
        "SELECT count(*) FROM claims WHERE extraction_prompt_version = %s",
        (TARGET_VERSION,),
    ).fetchone()[0]
    assert new_claim_count >= 1

    # Raw evidence is unchanged.
    assert (
        conn.execute("SELECT count(*) FROM messages").fetchone()[0]
        == raw_message_count_before
    )
    assert (
        conn.execute("SELECT count(*) FROM segments").fetchone()[0]
        == segment_count_before
    )


def test_re_extract_preserves_immutable_evidence(
    fake_connect: Any,
    conn: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conv_id, gen_id, seg_id, msg_ids = active_segment(
        conn, [("user", "I use Postgres", 1)]
    )
    insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=[msg_ids[0]],
        predicate="uses_tool",
        object_text="Postgres",
        prompt_version="extractor.v1.test.prior",
    )
    msg_payloads_before = conn.execute(
        "SELECT id::text, content_text, raw_payload FROM messages ORDER BY id"
    ).fetchall()
    seg_payload_before = conn.execute(
        "SELECT id::text, content_text, message_ids FROM segments ORDER BY id"
    ).fetchall()

    static_client = StaticExtractor(
        [
            ClaimDraft(
                "user",
                "uses_tool",
                "Postgres",
                None,
                "preference",
                0.9,
                msg_ids,
                "post-bump",
            )
        ]
    )
    monkeypatch.setattr(cli, "IkLlamaExtractorClient", lambda: static_client)

    rc = cli.main(["phase3", "re-extract", "--version", TARGET_VERSION])
    assert rc == 0

    msg_payloads_after = conn.execute(
        "SELECT id::text, content_text, raw_payload FROM messages ORDER BY id"
    ).fetchall()
    seg_payload_after = conn.execute(
        "SELECT id::text, content_text, message_ids FROM segments ORDER BY id"
    ).fetchall()
    assert msg_payloads_before == msg_payloads_after
    assert seg_payload_before == seg_payload_after


def test_re_extract_reports_coverage_gap_when_new_version_drops_claims(
    fake_connect: Any,
    conn: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    conv_id, gen_id, seg_id, msg_ids = active_segment(
        conn, [("user", "I use Postgres", 1)]
    )
    insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=[msg_ids[0]],
        predicate="uses_tool",
        object_text="Postgres",
        prompt_version="extractor.v1.test.prior",
    )
    # New version produces zero claims.
    static_client = StaticExtractor([])
    monkeypatch.setattr(cli, "IkLlamaExtractorClient", lambda: static_client)

    rc = cli.main(["phase3", "re-extract", "--version", TARGET_VERSION])
    assert rc == 0
    out = capsys.readouterr().out
    assert "coverage gap" in out.lower()
    assert seg_id in out


def test_re_extract_diff_sample_compares_versions(
    fake_connect: Any,
    conn: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    conv_id, gen_id, seg_id, msg_ids = active_segment(
        conn, [("user", "I use Postgres", 1)]
    )
    insert_extracted_claim(
        conn,
        segment_id=seg_id,
        generation_id=gen_id,
        conversation_id=conv_id,
        evidence_ids=[msg_ids[0]],
        predicate="uses_tool",
        object_text="Postgres",
        prompt_version="extractor.v1.test.prior",
    )
    static_client = StaticExtractor(
        [
            ClaimDraft(
                "user",
                "uses_tool",
                "Postgres",
                None,
                "preference",
                0.9,
                msg_ids,
                "post-bump",
            )
        ]
    )
    monkeypatch.setattr(cli, "IkLlamaExtractorClient", lambda: static_client)

    rc = cli.main(
        ["phase3", "re-extract", "--version", TARGET_VERSION, "--diff-sample", "2"]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "diff sample" in out.lower()
    assert "prior_count" in out
    assert "new_count" in out


def test_re_extract_limit_caps_segment_count(
    fake_connect: Any,
    conn: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seg_ids: list[str] = []
    for _ in range(3):
        conv_id, gen_id, seg_id, msg_ids = active_segment(
            conn, [("user", "I use a tool", 1)]
        )
        insert_extracted_claim(
            conn,
            segment_id=seg_id,
            generation_id=gen_id,
            conversation_id=conv_id,
            evidence_ids=[msg_ids[0]],
            predicate="uses_tool",
            object_text="Postgres",
            prompt_version="extractor.v1.test.prior",
        )
        seg_ids.append(seg_id)

    extracted: list[str] = []

    def fake_extract_one(conn_arg, segment_id, **kwargs):
        extracted.append(segment_id)
        return extractor.ExtractionResult(
            extraction_id="x",
            segment_id=segment_id,
            claim_count=1,
            status="extracted",
        )

    monkeypatch.setattr(extractor, "extract_claims_from_segment", fake_extract_one)

    rc = cli.main(
        ["phase3", "re-extract", "--version", TARGET_VERSION, "--limit", "2"]
    )
    assert rc == 0
    assert len(extracted) == 2


def test_re_extract_source_id_filter_restricts_segments(
    fake_connect: Any,
    conn: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Create two segments under different sources.
    conv_a, gen_a, seg_a, msg_a = active_segment(
        conn, [("user", "Source A message", 1)]
    )
    conv_b, gen_b, seg_b, msg_b = active_segment(
        conn, [("user", "Source B message", 1)]
    )
    insert_extracted_claim(
        conn,
        segment_id=seg_a,
        generation_id=gen_a,
        conversation_id=conv_a,
        evidence_ids=[msg_a[0]],
        predicate="uses_tool",
        object_text="Postgres",
        prompt_version="extractor.v1.test.prior",
    )
    insert_extracted_claim(
        conn,
        segment_id=seg_b,
        generation_id=gen_b,
        conversation_id=conv_b,
        evidence_ids=[msg_b[0]],
        predicate="uses_tool",
        object_text="SQLite",
        prompt_version="extractor.v1.test.prior",
    )
    source_a_id = conn.execute(
        "SELECT source_id::text FROM segments WHERE id = %s",
        (seg_a,),
    ).fetchone()[0]

    extracted: list[str] = []

    def fake_extract_one(conn_arg, segment_id, **kwargs):
        extracted.append(segment_id)
        return extractor.ExtractionResult(
            extraction_id="x",
            segment_id=segment_id,
            claim_count=1,
            status="extracted",
        )

    monkeypatch.setattr(extractor, "extract_claims_from_segment", fake_extract_one)

    rc = cli.main(
        [
            "phase3",
            "re-extract",
            "--version",
            TARGET_VERSION,
            "--source-id",
            source_a_id,
        ]
    )
    assert rc == 0
    assert seg_a in extracted
    assert seg_b not in extracted


def test_re_extract_batch_size_is_accepted_and_threads_through(
    fake_connect: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_orchestrator(connection: Any, target_version: str, **kwargs: Any) -> Any:
        captured.update(kwargs)
        return _fake_result(target_version)

    monkeypatch.setattr(cli, "re_extract", fake_orchestrator)

    rc = cli.main(
        [
            "phase3",
            "re-extract",
            "--version",
            "extractor.v9.d111.batch-test",
            "--batch-size",
            "23",
        ]
    )
    assert rc == 0
    assert captured["batch_size"] == 23


def test_re_extract_orchestrator_rejects_bad_format_directly(conn: Any) -> None:
    with pytest.raises(ReExtractError, match="format"):
        re_extract(conn, "totally-wrong-shape")


def test_re_extract_orchestrator_rejects_same_version_directly(
    conn: Any,
) -> None:
    with pytest.raises(ReExtractError, match="same version"):
        re_extract(conn, EXTRACTION_PROMPT_VERSION)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_result(target_version: str) -> Any:
    """Build a minimal ReExtractResult-shaped object for CLI dispatch tests."""

    plan = SimpleNamespace(
        target_version=target_version,
        current_version=EXTRACTION_PROMPT_VERSION,
        segments=[],
        prior_version_counts={},
        source_kind_counts={},
        segment_count=0,
    )
    return SimpleNamespace(
        target_version=target_version,
        plan=plan,
        processed=0,
        created=0,
        skipped=0,
        failed=0,
        coverage_gaps=[],
        diff_samples=[],
        dry_run=False,
    )
