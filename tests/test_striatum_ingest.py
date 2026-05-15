from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import psycopg
import pytest
from psycopg.types.json import Jsonb

from engram.memory import (
    CAPABILITY_DESCRIBE,
    CAPABILITY_READ_CROSS_CORPUS,
    CAPABILITY_READ_CROSS_TENANT,
    CAPABILITY_READ_PERSONAL,
    CAPABILITY_READ_STRIATUM,
    MemoryCapabilityError,
    MemoryService,
    MemoryToken,
    TenantCorpus,
    encode_reference_id,
)
from engram.striatum_ingest import (
    JSONL_FILES,
    SCHEMA_VERSION,
    IngestConflict,
    ManifestValidationError,
    canonical_manifest_sha256,
    ingest_striatum_bundle,
)
from engram.striatum_projection import project_striatum_references


def _row(sub_kind: str, external_id: str, content: str) -> dict[str, Any]:
    return {
        "source_kind": "striatum",
        "external_id": external_id,
        "sub_kind": sub_kind,
        "content": content,
        "provenance": {
            "path": f"docs/{sub_kind}.md",
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "commit": "abc123",
        },
        "observed_at": "2026-05-13T00:00:00Z",
    }


def _write_bundle(
    root: Path,
    rows: list[dict[str, Any]],
    *,
    include_bundle_sha256: bool = False,
) -> dict[str, Any]:
    rows_by_kind = {sub_kind: [] for sub_kind in JSONL_FILES}
    for row in rows:
        rows_by_kind[str(row["sub_kind"])].append(row)

    files: dict[str, dict[str, int | str]] = {}
    row_counts: dict[str, int] = {}
    for sub_kind, filename in JSONL_FILES.items():
        ordered = sorted(rows_by_kind[sub_kind], key=lambda item: str(item["external_id"]))
        lines = [json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in ordered]
        body = ("\n".join(lines) + "\n").encode("utf-8")
        (root / filename).write_bytes(body)
        files[filename] = {
            "sha256": hashlib.sha256(body).hexdigest(),
            "rows": len(ordered),
            "bytes": len(body),
        }
        row_counts[sub_kind] = len(ordered)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "striatum_version": "test",
        "repo_root": "/tmp/striatum",
        "git_head": "abc123",
        "git_dirty": False,
        "since_ref": "v1.30.0",
        "since_commit": "000111",
        "generated_at": "2026-05-13T00:00:00Z",
        "schema": {
            "row_shape_version": "striatum.corpus_row.v1",
            "sub_kinds": list(JSONL_FILES),
        },
        "source_kinds": ["striatum"],
        "row_counts": row_counts,
        "files": files,
        "repo_local_schema_version": 13,
        "missing_optional_sources": [],
        "daemon_audit_included": False,
    }
    if include_bundle_sha256:
        manifest["bundle_sha256"] = canonical_manifest_sha256(manifest)
    (root / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def _write_personal_capture(conn: psycopg.Connection) -> str:
    source_row = conn.execute(
        """
        INSERT INTO sources (source_kind, external_id, raw_payload)
        VALUES ('capture', 'personal-source', '{}')
        RETURNING id
        """
    ).fetchone()
    assert source_row is not None
    source_id = source_row[0]
    capture_row = conn.execute(
        """
        INSERT INTO captures (
            source_id,
            source_kind,
            external_id,
            raw_payload,
            capture_type,
            content_text
        )
        VALUES (%s, 'capture', 'personal-secret', '{}', 'reference', 'Jennifer MBTI')
        RETURNING id
        """,
        (source_id,),
    ).fetchone()
    assert capture_row is not None
    capture_id = capture_row[0]
    return str(capture_id)


def _write_striatum_capture(
    conn: psycopg.Connection,
    *,
    corpus_id: str,
    external_id: str,
    content: str,
) -> str:
    source_row = conn.execute(
        """
        INSERT INTO sources (
            source_kind,
            external_id,
            raw_payload,
            tenant_id,
            corpus_id,
            bundle_id
        )
        VALUES ('striatum', %s, %s, 'striatum', %s, 'test-bundle')
        RETURNING id
        """,
        (
            f"striatum-source-{corpus_id}-{external_id}",
            Jsonb({"fixture": "cross-boundary"}),
            corpus_id,
        ),
    ).fetchone()
    assert source_row is not None
    source_id = source_row[0]
    capture_row = conn.execute(
        """
        INSERT INTO captures (
            source_id,
            source_kind,
            external_id,
            raw_payload,
            capture_type,
            content_text,
            observed_at,
            tenant_id,
            corpus_id,
            bundle_id
        )
        VALUES (
            %s,
            'striatum',
            %s,
            %s,
            'reference',
            %s,
            '2026-05-13T00:00:00Z',
            'striatum',
            %s,
            'test-bundle'
        )
        RETURNING id
        """,
        (
            source_id,
            external_id,
            Jsonb({"sub_kind": "rfc", "provenance": {"path": "docs/rfc.md"}}),
            content,
            corpus_id,
        ),
    ).fetchone()
    assert capture_row is not None
    capture_id = capture_row[0]
    return str(capture_id)


def test_striatum_bundle_ingest_is_idempotent_and_preserves_boundary(conn, tmp_path: Path) -> None:
    _write_bundle(
        tmp_path,
        [
            _row("rfc", "rfc:0043#proposal", "RFC 0043 daemon RPC capability vocabulary"),
            _row("decision_log_row", "decision:D082", "D082 predicate-intent slot reservation"),
        ],
        include_bundle_sha256=True,
    )

    first = ingest_striatum_bundle(conn, tmp_path, repo="striatum")
    second = ingest_striatum_bundle(conn, tmp_path, repo="striatum")

    assert first.records_inserted == 2
    assert first.records_seen == 2
    assert second.records_inserted == 0
    assert second.records_skipped == 2

    row = conn.execute(
        """
        SELECT tenant_id, corpus_id, source_kind::text, count(*)::int
        FROM captures
        WHERE source_kind::text = 'striatum'
        GROUP BY tenant_id, corpus_id, source_kind::text
        """
    ).fetchone()
    assert row == ("striatum", "striatum", "striatum", 2)


def test_striatum_bundle_rejects_tampered_file(conn, tmp_path: Path) -> None:
    _write_bundle(tmp_path, [_row("rfc", "rfc:0044#proposal", "RFC 0044")])
    (tmp_path / "rfcs.jsonl").write_text("tampered\n", encoding="utf-8")

    with pytest.raises(ManifestValidationError, match="hash mismatch"):
        ingest_striatum_bundle(conn, tmp_path, repo="striatum")


def test_striatum_bundle_conflicting_row_content_raises(conn, tmp_path: Path) -> None:
    _write_bundle(tmp_path, [_row("rfc", "rfc:0044#proposal", "original")])
    ingest_striatum_bundle(conn, tmp_path, repo="striatum")

    changed = tmp_path / "changed"
    changed.mkdir()
    _write_bundle(changed, [_row("rfc", "rfc:0044#proposal", "changed")])

    with pytest.raises(IngestConflict, match="content differs"):
        ingest_striatum_bundle(conn, changed, repo="striatum")


def test_default_striatum_token_cannot_read_personal_or_fetch_personal_reference(
    conn,
    tmp_path: Path,
) -> None:
    _write_bundle(tmp_path, [_row("rfc", "rfc:0043#proposal", "RFC 0043 capability")])
    ingest_striatum_bundle(conn, tmp_path, repo="striatum")
    personal_capture_id = _write_personal_capture(conn)
    service = MemoryService(conn)

    assert service.search("RFC 0043")
    with pytest.raises(MemoryCapabilityError, match=r"not allowed|not visible"):
        service.search("Jennifer", tenant_id="personal", corpus_id="personal")
    with pytest.raises(MemoryCapabilityError, match=r"not allowed|memory.read_personal"):
        service.fetch_reference(encode_reference_id("captures", personal_capture_id))

    health = service.health()
    assert health["visible_tenant_corpora"] == [
        {
            "tenant_id": "striatum",
            "corpus_id": "striatum",
            "record_count": 1,
            "latest_ingest_at": health["visible_tenant_corpora"][0]["latest_ingest_at"],
        }
    ]


def test_cross_corpus_capability_does_not_grant_cross_tenant(conn, tmp_path: Path) -> None:
    _write_bundle(tmp_path, [_row("rfc", "rfc:0043#proposal", "RFC 0043 capability")])
    ingest_striatum_bundle(conn, tmp_path, repo="striatum")
    token = MemoryToken(
        capabilities=frozenset(
            {
                CAPABILITY_READ_STRIATUM,
                CAPABILITY_DESCRIBE,
                CAPABILITY_READ_CROSS_CORPUS,
            }
        ),
        allowed_pairs=frozenset(
            {
                TenantCorpus("striatum", "striatum"),
                TenantCorpus("future_app", "future"),
            }
        ),
    )
    service = MemoryService(conn, token=token)

    assert service.search("RFC 0043", tenant_id="striatum", corpus_id="striatum")
    with pytest.raises(MemoryCapabilityError, match=r"memory.read_cross_tenant"):
        service.search("anything", tenant_id="future_app", corpus_id="future")


def test_service_search_and_fetch_require_cross_corpus_for_secondary_striatum_corpus(
    conn: psycopg.Connection,
) -> None:
    secondary_id = _write_striatum_capture(
        conn,
        corpus_id="secondary",
        external_id="rfc:secondary#capability",
        content="secondary corpus capability boundary",
    )
    token = MemoryToken(
        capabilities=frozenset({CAPABILITY_READ_STRIATUM, CAPABILITY_DESCRIBE}),
        allowed_pairs=frozenset(
            {
                TenantCorpus("striatum", "striatum"),
                TenantCorpus("striatum", "secondary"),
            }
        ),
    )
    service = MemoryService(conn, token=token)
    reference_id = encode_reference_id("captures", secondary_id)

    with pytest.raises(MemoryCapabilityError, match=r"memory.read_cross_corpus"):
        service.search("secondary capability", tenant_id="striatum", corpus_id="secondary")
    with pytest.raises(MemoryCapabilityError, match=r"memory.read_cross_corpus"):
        service.fetch_reference(reference_id)

    cross_corpus_token = MemoryToken(
        capabilities=frozenset(
            {
                CAPABILITY_READ_STRIATUM,
                CAPABILITY_DESCRIBE,
                CAPABILITY_READ_CROSS_CORPUS,
            }
        ),
        allowed_pairs=token.allowed_pairs,
    )
    allowed_service = MemoryService(conn, token=cross_corpus_token)

    assert allowed_service.search(
        "secondary capability",
        tenant_id="striatum",
        corpus_id="secondary",
    )
    assert allowed_service.fetch_reference(reference_id)["content"] == (
        "secondary corpus capability boundary"
    )


def test_service_search_and_fetch_require_cross_tenant_for_personal_pair(
    conn: psycopg.Connection,
) -> None:
    personal_id = _write_personal_capture(conn)
    token = MemoryToken(
        capabilities=frozenset(
            {
                CAPABILITY_READ_STRIATUM,
                CAPABILITY_DESCRIBE,
                CAPABILITY_READ_PERSONAL,
            }
        ),
        allowed_pairs=frozenset(
            {
                TenantCorpus("striatum", "striatum"),
                TenantCorpus("personal", "personal"),
            }
        ),
    )
    service = MemoryService(conn, token=token)
    reference_id = encode_reference_id("captures", personal_id)

    with pytest.raises(MemoryCapabilityError, match=r"memory.read_cross_tenant"):
        service.search("Jennifer", tenant_id="personal", corpus_id="personal")
    with pytest.raises(MemoryCapabilityError, match=r"memory.read_cross_tenant"):
        service.fetch_reference(reference_id)

    cross_tenant_token = MemoryToken(
        capabilities=frozenset(
            {
                CAPABILITY_READ_STRIATUM,
                CAPABILITY_DESCRIBE,
                CAPABILITY_READ_PERSONAL,
                CAPABILITY_READ_CROSS_TENANT,
            }
        ),
        allowed_pairs=token.allowed_pairs,
    )
    allowed_service = MemoryService(conn, token=cross_tenant_token)

    assert allowed_service.search("Jennifer", tenant_id="personal", corpus_id="personal") == []
    assert allowed_service.fetch_reference(reference_id)["content"] == "Jennifer MBTI"


EG000_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "striatum_eg000"


def test_eg000_committed_fixture_round_trip_ingest_and_read(
    conn: psycopg.Connection,
) -> None:
    """EG-000 baseline: committed real-shape fixture survives ingest and
    read-only retrieval.

    The bundle at tests/fixtures/striatum_eg000/ is built from Engram's own
    public RFC/decision-log/operator-report/changelog prose (see
    `build_fixture.py`), so it exercises the
    `striatum.corpus_export.v1` schema with non-synthetic content. The
    smoke confirms that ingest+search+fetch+describe all work on this
    real-shape fixture and stay inside the default striatum/striatum
    boundary.
    """
    assert EG000_FIXTURE_DIR.exists(), "EG-000 fixture is missing"

    result = ingest_striatum_bundle(conn, EG000_FIXTURE_DIR, repo="engram-eg000")

    assert result.records_inserted == 5
    assert result.records_seen == 5

    service = MemoryService(conn)

    # search inside the default striatum/striatum boundary. Ingested
    # external_ids are namespaced as `<repo>:<sub_kind>:<original>`, so
    # match by substring rather than equality.
    rfc_hits = service.search("RFC 0044", limit=5)
    assert any("rfc:0044#hardening-baseline" in hit["external_id"] for hit in rfc_hits)
    decision_hits = service.search("subject_kind_hint", limit=5)
    assert any("decision:D082" in hit["external_id"] for hit in decision_hits)

    # fetch_reference re-authorizes the stored row
    reference_id = rfc_hits[0]["reference_id"]
    fetched = service.fetch_reference(reference_id)
    assert fetched["tenant_id"] == "striatum"
    assert fetched["corpus_id"] == "striatum"
    assert fetched["source_kind"] == "striatum"

    # describe_corpus reports the fixture counts
    description = service.describe_corpus()
    assert description["record_count"] == 5
    assert description["projection_active_count"] == 0
    assert description["bundle_count"] == 1
    assert description["sub_kind_counts"]["rfc"] == 2
    assert description["sub_kind_counts"]["decision_log_row"] == 1
    assert description["sub_kind_counts"]["operator_report"] == 1
    assert description["sub_kind_counts"]["changelog_entry"] == 1

    projection = project_striatum_references(conn)
    assert projection.captures_seen == 5
    assert service.describe_corpus()["projection_active_count"] == 5


def test_health_schema_version_uses_applied_ordering_not_lex_max(
    conn: psycopg.Connection,
) -> None:
    """EG-000 baseline: schema_version reflects applied ordering, not lex max.

    Insert a synthetic later-applied migration whose filename loses
    lexicographic comparison against existing migrations. health() must
    report the synthetic one because it is the most recently applied,
    proving the query is not `SELECT max(filename) FROM schema_migrations`.
    """
    conn.execute(
        """
        INSERT INTO schema_migrations (filename, applied_at, checksum)
        VALUES ('0_synthetic_lex_loser.sql', NOW(), 'synthetic')
        """
    )
    service = MemoryService(conn)

    health = service.health()

    assert health["schema_version"] == "0_synthetic_lex_loser.sql"
