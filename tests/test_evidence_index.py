from __future__ import annotations

from pathlib import Path

import psycopg

from engram.build_artifact_import import import_build_artifacts
from engram.evidence import refresh_evidence_reference_index
from engram.markdown_import import import_markdown_tree
from engram.memory import (
    CAPABILITY_READ_PERSONAL,
    ExactRefFilter,
    MemorySearchFilters,
    MemoryService,
    MemoryToken,
    TenantCorpus,
)


def _make_personal_service(conn: psycopg.Connection) -> MemoryService:
    pair = TenantCorpus("personal", "personal")
    return MemoryService(
        conn,
        token=MemoryToken(
            capabilities=frozenset({CAPABILITY_READ_PERSONAL}),
            allowed_pairs=frozenset({pair}),
            primary_pair=pair,
        ),
    )


def test_refresh_evidence_reference_index_backfills_and_rebuilds(
    conn: psycopg.Connection,
    tmp_path: Path,
) -> None:
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()
    (artifacts_root / "junit.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="generic" tests="1" failures="0">
    <testcase classname="generic.case" name="test_generic" time="0.1"/>
  </testsuite>
</testsuites>
""",
        encoding="utf-8",
    )
    commit_sha = "a" * 40
    import_build_artifacts(
        conn,
        artifacts_root,
        run_id="run_generic_123",
        commit_sha=commit_sha,
    )

    markdown_root = tmp_path / "vault"
    markdown_root.mkdir()
    (markdown_root / "README.md").write_text("# Root\n\nGeneric evidence.\n", encoding="utf-8")
    import_markdown_tree(conn, markdown_root)

    first = refresh_evidence_reference_index(
        conn,
        tenant_id="personal",
        corpus_id="personal",
    )
    second = refresh_evidence_reference_index(
        conn,
        tenant_id="personal",
        corpus_id="personal",
    )

    assert first.evidence_items >= 2
    assert first.evidence_refs >= 5
    assert second.evidence_items == first.evidence_items
    assert second.evidence_refs == first.evidence_refs

    refs = {
        (row[0], row[1])
        for row in conn.execute(
            """
            SELECT ref_kind, ref_value_normalized
            FROM evidence_refs
            WHERE tenant_id = 'personal'
              AND corpus_id = 'personal'
            """
        ).fetchall()
    }
    assert ("run_id", "run_generic_123") in refs
    assert ("commit_sha", commit_sha) in refs
    assert ("path", "readme.md") in refs


def test_exact_ref_search_uses_generic_reference_index_when_available(
    conn: psycopg.Connection,
    tmp_path: Path,
) -> None:
    artifacts_root = tmp_path / "artifacts"
    artifacts_root.mkdir()
    (artifacts_root / "junit.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="generic" tests="1" failures="0">
    <testcase classname="generic.case" name="test_generic" time="0.1"/>
  </testsuite>
</testsuites>
""",
        encoding="utf-8",
    )
    import_build_artifacts(conn, artifacts_root, run_id="run_generic_lookup")
    refresh_evidence_reference_index(conn, tenant_id="personal", corpus_id="personal")

    service = _make_personal_service(conn)
    hits = service.search(
        "run_generic_lookup",
        tenant_id="personal",
        corpus_id="personal",
        filters=MemorySearchFilters(
            exact_refs=(
                ExactRefFilter(ref_kind="run_id", ref_value="run_generic_lookup"),
            )
        ),
    )

    assert hits
    assert hits[0]["target_table"] == "build_artifacts"
    assert hits[0]["provenance"]["generic_evidence_item_id"]
    assert hits[0]["provenance"]["generic_evidence_ref_ids"]
