from __future__ import annotations

from dataclasses import dataclass

import psycopg

SENSITIVITY_CLASSES: tuple[str, ...] = (
    "routine_project",
    "personal_private",
    "third_party_communication",
    "calendar_contact",
    "behavioral_activity",
    "raw_media",
    "exact_location",
    "health",
    "biometric",
    "finance",
    "credential_or_secret_reference",
)


@dataclass(frozen=True)
class EvidenceRefreshResult:
    """Summary of one generic evidence/reference index rebuild."""

    tenant_id: str
    corpus_id: str
    evidence_items: int
    evidence_refs: int


def refresh_evidence_reference_index(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
) -> EvidenceRefreshResult:
    """Rebuild generic evidence/reference projections for one tenant/corpus."""
    if not tenant_id.strip() or not corpus_id.strip():
        raise ValueError("tenant_id and corpus_id must be non-empty")
    _ensure_tables(conn)
    conn.execute(
        """
        DELETE FROM evidence_items
        WHERE tenant_id = %s
          AND corpus_id = %s
        """,
        (tenant_id, corpus_id),
    )
    if _table_exists(conn, "striatum_references"):
        _insert_striatum_items(conn, tenant_id=tenant_id, corpus_id=corpus_id)
        _insert_striatum_refs(conn, tenant_id=tenant_id, corpus_id=corpus_id)
    if _table_exists(conn, "git_commits"):
        _insert_git_items(conn, tenant_id=tenant_id, corpus_id=corpus_id)
        _insert_git_refs(conn, tenant_id=tenant_id, corpus_id=corpus_id)
    if _table_exists(conn, "build_artifacts"):
        _insert_build_artifact_items(conn, tenant_id=tenant_id, corpus_id=corpus_id)
        _insert_build_artifact_refs(conn, tenant_id=tenant_id, corpus_id=corpus_id)
    if _table_exists(conn, "markdown_files"):
        _insert_markdown_items(conn, tenant_id=tenant_id, corpus_id=corpus_id)
        _insert_markdown_refs(conn, tenant_id=tenant_id, corpus_id=corpus_id)

    item_row = conn.execute(
        """
        SELECT count(*)::int
        FROM evidence_items
        WHERE tenant_id = %s
          AND corpus_id = %s
        """,
        (tenant_id, corpus_id),
    ).fetchone()
    ref_row = conn.execute(
        """
        SELECT count(*)::int
        FROM evidence_refs
        WHERE tenant_id = %s
          AND corpus_id = %s
        """,
        (tenant_id, corpus_id),
    ).fetchone()
    return EvidenceRefreshResult(
        tenant_id=tenant_id,
        corpus_id=corpus_id,
        evidence_items=int(item_row[0] if item_row is not None else 0),
        evidence_refs=int(ref_row[0] if ref_row is not None else 0),
    )


def _ensure_tables(conn: psycopg.Connection) -> None:
    for table_name in ("evidence_items", "evidence_refs"):
        if not _table_exists(conn, table_name):
            raise RuntimeError(f"{table_name} table is unavailable")


def _table_exists(conn: psycopg.Connection, table_name: str) -> bool:
    row = conn.execute("SELECT to_regclass(%s)", (f"public.{table_name}",)).fetchone()
    return bool(row is not None and row[0] is not None)


def _insert_striatum_items(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
) -> None:
    conn.execute(
        """
        INSERT INTO evidence_items (
            tenant_id,
            corpus_id,
            source_kind,
            source_table,
            source_id,
            source_external_id,
            source_sub_kind,
            content_hash,
            privacy_tier,
            sensitivity_class,
            observed_at,
            imported_at,
            provenance,
            lifecycle_state
        )
        SELECT
            c.tenant_id,
            c.corpus_id,
            c.source_kind::text,
            'captures',
            c.id,
            c.external_id,
            COALESCE(NULLIF(c.raw_payload ->> 'sub_kind', ''), 'unknown'),
            min(r.content_hash),
            c.privacy_tier,
            CASE
                WHEN c.raw_payload ->> 'sensitivity_class' = ANY(%s::text[])
                    THEN c.raw_payload ->> 'sensitivity_class'
                ELSE 'routine_project'
            END,
            c.observed_at,
            c.imported_at,
            jsonb_build_object(
                'projection_source',
                'striatum_references',
                'capture_id',
                c.id::text
            ),
            'active'
        FROM captures c
        JOIN striatum_references r ON r.capture_id = c.id
        WHERE r.tenant_id = %s
          AND r.corpus_id = %s
          AND r.is_active = true
        GROUP BY c.id
        ON CONFLICT (tenant_id, corpus_id, source_table, source_id) DO NOTHING
        """,
        (list(SENSITIVITY_CLASSES), tenant_id, corpus_id),
    )


def _insert_striatum_refs(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
) -> None:
    conn.execute(
        """
        INSERT INTO evidence_refs (
            evidence_item_id,
            tenant_id,
            corpus_id,
            ref_kind,
            ref_value,
            ref_value_normalized,
            source_table,
            source_id,
            freshness,
            dirty_working_tree,
            observed_at,
            raw_payload
        )
        SELECT
            ei.id,
            r.tenant_id,
            r.corpus_id,
            r.ref_kind,
            r.ref_value,
            r.ref_value_normalized,
            'captures',
            r.capture_id,
            CASE
                WHEN r.raw_payload ->> 'freshness' IN
                    ('fresh','stale','dirty_working_tree','unknown')
                    THEN r.raw_payload ->> 'freshness'
                ELSE 'fresh'
            END,
            CASE
                WHEN lower(r.raw_payload ->> 'source_dirty_working_tree') IN ('true', 'false')
                    THEN (r.raw_payload ->> 'source_dirty_working_tree')::boolean
                ELSE false
            END,
            r.observed_at,
            jsonb_build_object(
                'projection_source',
                'striatum_references',
                'striatum_reference_id',
                r.id::text
            ) || r.raw_payload
        FROM striatum_references r
        JOIN evidence_items ei
          ON ei.tenant_id = r.tenant_id
         AND ei.corpus_id = r.corpus_id
         AND ei.source_table = 'captures'
         AND ei.source_id = r.capture_id
        WHERE r.tenant_id = %s
          AND r.corpus_id = %s
          AND r.is_active = true
        ON CONFLICT (evidence_item_id, ref_kind, ref_value_normalized) DO NOTHING
        """,
        (tenant_id, corpus_id),
    )


def _insert_git_items(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
) -> None:
    conn.execute(
        """
        INSERT INTO evidence_items (
            tenant_id,
            corpus_id,
            source_kind,
            source_table,
            source_id,
            source_external_id,
            source_sub_kind,
            content_hash,
            privacy_tier,
            sensitivity_class,
            observed_at,
            imported_at,
            provenance,
            lifecycle_state
        )
        SELECT
            tenant_id,
            corpus_id,
            'git',
            'git_commits',
            id,
            repository_id || ':' || commit_sha,
            'commit',
            content_hash,
            privacy_tier,
            'routine_project',
            committer_date,
            imported_at,
            jsonb_build_object(
                'repository_id',
                repository_id,
                'commit_sha',
                commit_sha
            ),
            'active'
        FROM git_commits
        WHERE tenant_id = %s
          AND corpus_id = %s
        ON CONFLICT (tenant_id, corpus_id, source_table, source_id) DO NOTHING
        """,
        (tenant_id, corpus_id),
    )


def _insert_git_refs(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
) -> None:
    conn.execute(
        """
        INSERT INTO evidence_refs (
            evidence_item_id,
            tenant_id,
            corpus_id,
            ref_kind,
            ref_value,
            ref_value_normalized,
            source_table,
            source_id,
            freshness,
            observed_at,
            raw_payload
        )
        SELECT
            ei.id,
            g.tenant_id,
            g.corpus_id,
            'commit_sha',
            g.commit_sha,
            lower(g.commit_sha),
            'git_commits',
            g.id,
            'fresh',
            g.committer_date,
            jsonb_build_object('projection_source', 'git_commits')
        FROM git_commits g
        JOIN evidence_items ei
          ON ei.tenant_id = g.tenant_id
         AND ei.corpus_id = g.corpus_id
         AND ei.source_table = 'git_commits'
         AND ei.source_id = g.id
        WHERE g.tenant_id = %s
          AND g.corpus_id = %s
        ON CONFLICT (evidence_item_id, ref_kind, ref_value_normalized) DO NOTHING
        """,
        (tenant_id, corpus_id),
    )
    conn.execute(
        """
        INSERT INTO evidence_refs (
            evidence_item_id,
            tenant_id,
            corpus_id,
            ref_kind,
            ref_value,
            ref_value_normalized,
            source_table,
            source_id,
            freshness,
            observed_at,
            raw_payload
        )
        SELECT
            ei.id,
            g.tenant_id,
            g.corpus_id,
            CASE
                WHEN ref.ref_name LIKE 'refs/tags/%%' THEN 'tag'
                WHEN ref.ref_name LIKE 'refs/heads/%%' THEN 'branch'
                ELSE 'logical_id'
            END,
            CASE
                WHEN ref.ref_name LIKE 'refs/tags/%%' THEN substring(ref.ref_name from 11)
                WHEN ref.ref_name LIKE 'refs/heads/%%' THEN substring(ref.ref_name from 12)
                ELSE ref.ref_name
            END,
            lower(
                CASE
                    WHEN ref.ref_name LIKE 'refs/tags/%%' THEN substring(ref.ref_name from 11)
                    WHEN ref.ref_name LIKE 'refs/heads/%%' THEN substring(ref.ref_name from 12)
                    ELSE ref.ref_name
                END
            ),
            'git_commits',
            g.id,
            'fresh',
            g.committer_date,
            jsonb_build_object(
                'projection_source',
                'git_commits.refs',
                'raw_ref',
                ref.ref_name
            )
        FROM git_commits g
        CROSS JOIN LATERAL unnest(g.refs) AS ref(ref_name)
        JOIN evidence_items ei
          ON ei.tenant_id = g.tenant_id
         AND ei.corpus_id = g.corpus_id
         AND ei.source_table = 'git_commits'
         AND ei.source_id = g.id
        WHERE g.tenant_id = %s
          AND g.corpus_id = %s
          AND btrim(ref.ref_name) <> ''
        ON CONFLICT (evidence_item_id, ref_kind, ref_value_normalized) DO NOTHING
        """,
        (tenant_id, corpus_id),
    )


def _insert_build_artifact_items(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
) -> None:
    conn.execute(
        """
        INSERT INTO evidence_items (
            tenant_id,
            corpus_id,
            source_kind,
            source_table,
            source_id,
            source_external_id,
            source_sub_kind,
            content_hash,
            privacy_tier,
            sensitivity_class,
            observed_at,
            imported_at,
            provenance,
            lifecycle_state
        )
        SELECT
            tenant_id,
            corpus_id,
            'build_artifact',
            'build_artifacts',
            id,
            artifact_root_id || ':' || relative_path,
            artifact_kind,
            content_hash,
            privacy_tier,
            sensitivity_class,
            artifact_mtime,
            imported_at,
            jsonb_build_object(
                'artifact_root_id',
                artifact_root_id,
                'relative_path',
                relative_path,
                'run_id',
                run_id,
                'commit_sha',
                commit_sha
            ),
            'active'
        FROM build_artifacts
        WHERE tenant_id = %s
          AND corpus_id = %s
        ON CONFLICT (tenant_id, corpus_id, source_table, source_id) DO NOTHING
        """,
        (tenant_id, corpus_id),
    )


def _insert_build_artifact_refs(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
) -> None:
    _insert_build_artifact_ref_for_column(
        conn,
        tenant_id=tenant_id,
        corpus_id=corpus_id,
        ref_kind="source_hash",
        value_expression="b.content_hash",
        normalized_expression="lower(b.content_hash)",
        predicate="b.content_hash IS NOT NULL",
    )
    _insert_build_artifact_ref_for_column(
        conn,
        tenant_id=tenant_id,
        corpus_id=corpus_id,
        ref_kind="run_id",
        value_expression="b.run_id",
        normalized_expression="lower(b.run_id)",
        predicate="b.run_id IS NOT NULL",
    )
    _insert_build_artifact_ref_for_column(
        conn,
        tenant_id=tenant_id,
        corpus_id=corpus_id,
        ref_kind="commit_sha",
        value_expression="b.commit_sha",
        normalized_expression="lower(b.commit_sha)",
        predicate="b.commit_sha IS NOT NULL",
    )
    _insert_build_artifact_ref_for_column(
        conn,
        tenant_id=tenant_id,
        corpus_id=corpus_id,
        ref_kind="path",
        value_expression="b.relative_path",
        normalized_expression="lower(replace(b.relative_path, E'\\\\', '/'))",
        predicate="b.relative_path IS NOT NULL",
    )


def _insert_build_artifact_ref_for_column(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
    ref_kind: str,
    value_expression: str,
    normalized_expression: str,
    predicate: str,
) -> None:
    conn.execute(
        f"""
        INSERT INTO evidence_refs (
            evidence_item_id,
            tenant_id,
            corpus_id,
            ref_kind,
            ref_value,
            ref_value_normalized,
            source_table,
            source_id,
            freshness,
            observed_at,
            raw_payload
        )
        SELECT
            ei.id,
            b.tenant_id,
            b.corpus_id,
            %s,
            {value_expression},
            {normalized_expression},
            'build_artifacts',
            b.id,
            'fresh',
            b.artifact_mtime,
            jsonb_build_object('projection_source', 'build_artifacts')
        FROM build_artifacts b
        JOIN evidence_items ei
          ON ei.tenant_id = b.tenant_id
         AND ei.corpus_id = b.corpus_id
         AND ei.source_table = 'build_artifacts'
         AND ei.source_id = b.id
        WHERE b.tenant_id = %s
          AND b.corpus_id = %s
          AND {predicate}
        ON CONFLICT (evidence_item_id, ref_kind, ref_value_normalized) DO NOTHING
        """,
        (ref_kind, tenant_id, corpus_id),
    )


def _insert_markdown_items(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
) -> None:
    conn.execute(
        """
        INSERT INTO evidence_items (
            tenant_id,
            corpus_id,
            source_kind,
            source_table,
            source_id,
            source_external_id,
            source_sub_kind,
            content_hash,
            privacy_tier,
            sensitivity_class,
            observed_at,
            imported_at,
            provenance,
            lifecycle_state
        )
        SELECT
            tenant_id,
            corpus_id,
            'markdown_tree',
            'markdown_files',
            id,
            markdown_root_id || ':' || relative_path,
            'markdown_file',
            content_hash,
            privacy_tier,
            sensitivity_class,
            file_mtime,
            imported_at,
            jsonb_build_object(
                'markdown_root_id',
                markdown_root_id,
                'relative_path',
                relative_path
            ),
            CASE WHEN superseded_at IS NULL THEN 'active' ELSE 'stale' END
        FROM markdown_files
        WHERE tenant_id = %s
          AND corpus_id = %s
        ON CONFLICT (tenant_id, corpus_id, source_table, source_id) DO NOTHING
        """,
        (tenant_id, corpus_id),
    )


def _insert_markdown_refs(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
) -> None:
    conn.execute(
        """
        INSERT INTO evidence_refs (
            evidence_item_id,
            tenant_id,
            corpus_id,
            ref_kind,
            ref_value,
            ref_value_normalized,
            source_table,
            source_id,
            freshness,
            observed_at,
            raw_payload
        )
        SELECT
            ei.id,
            m.tenant_id,
            m.corpus_id,
            ref.ref_kind,
            ref.ref_value,
            ref.ref_value_normalized,
            'markdown_files',
            m.id,
            CASE WHEN m.superseded_at IS NULL THEN 'fresh' ELSE 'stale' END,
            m.file_mtime,
            jsonb_build_object('projection_source', 'markdown_files')
        FROM markdown_files m
        JOIN evidence_items ei
          ON ei.tenant_id = m.tenant_id
         AND ei.corpus_id = m.corpus_id
         AND ei.source_table = 'markdown_files'
         AND ei.source_id = m.id
        CROSS JOIN LATERAL (
            VALUES
                ('path', m.relative_path, lower(replace(m.relative_path, E'\\\\', '/'))),
                ('source_hash', m.content_hash, lower(m.content_hash))
        ) AS ref(ref_kind, ref_value, ref_value_normalized)
        WHERE m.tenant_id = %s
          AND m.corpus_id = %s
        ON CONFLICT (evidence_item_id, ref_kind, ref_value_normalized) DO NOTHING
        """,
        (tenant_id, corpus_id),
    )
