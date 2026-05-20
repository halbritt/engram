from __future__ import annotations

import uuid
from uuid import uuid4

import psycopg
import pytest
from psycopg import errors

from engram.consolidator import CONSOLIDATOR_MODEL_VERSION, CONSOLIDATOR_PROMPT_VERSION
from engram.extractor import EXTRACTION_PROMPT_VERSION, EXTRACTION_REQUEST_PROFILE_VERSION
from engram.interview.storage import insert_session
from engram.migrations import MIGRATIONS_DIR, MigrationDriftError, migrate


def _new_session(conn: psycopg.Connection) -> str:
    return insert_session(
        conn,
        seed=1,
        sampler_id="stratified",
        sampler_version="stratified.v1.d079.initial",
        strata_weights={},
    )


def _claim_target_row(
    session_id: str,
    *,
    idx: int = 0,
    target_id: str | None = None,
) -> tuple[str, ...]:
    return (
        session_id,
        idx,
        "claim",
        target_id or str(uuid.uuid4()),
        str(uuid.uuid4()),  # candidate_pool_snapshot_id
        EXTRACTION_PROMPT_VERSION,
        "model-a",
        None,
        None,
        EXTRACTION_REQUEST_PROFILE_VERSION,
        "identity",
        "0.6-0.8",
        "<30d",
        None,
    )


def _belief_target_row(
    session_id: str,
    *,
    idx: int = 0,
    target_id: str | None = None,
) -> tuple[str, ...]:
    return (
        session_id,
        idx,
        "belief",
        target_id or str(uuid.uuid4()),
        str(uuid.uuid4()),  # candidate_pool_snapshot_id
        None,
        None,
        CONSOLIDATOR_PROMPT_VERSION,
        CONSOLIDATOR_MODEL_VERSION,
        "interview.v1.d079.initial",
        "preference",
        "0.4-0.6",
        "<90d",
        "candidate",
    )


_INSERT_TARGET_SQL = """
INSERT INTO gold_label_session_targets (
    session_id,
    idx,
    target_kind,
    target_id,
    candidate_pool_snapshot_id,
    extraction_prompt_version,
    extraction_model_version,
    consolidation_prompt_version,
    consolidation_model_version,
    request_profile_version,
    stability_class,
    conf_band,
    recency_band,
    belief_status
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def test_rfc0021_migration_010_exists_on_disk() -> None:
    path = MIGRATIONS_DIR / "010_gold_labels.sql"
    assert path.exists(), f"missing migration: {path}"
    text = path.read_text(encoding="utf-8")
    # Sanity checks on the header and core schema landmarks.
    assert "RFC 0021" in text
    assert "gold_label_sessions" in text
    assert "gold_label_strata_vocabulary" in text
    assert "gold_label_verdict_vocabulary" in text
    assert "gold_labels" in text
    assert "fn_gold_labels_append_only" in text
    assert "fn_gold_labels_validate_target" in text
    assert "fn_gold_labels_carry_privacy_tier" in text
    assert "current_gold_label" in text


def test_rfc0028_migration_012_exists_on_disk() -> None:
    path = MIGRATIONS_DIR / "012_predicate_subject_kind_hint.sql"
    assert path.exists(), f"missing migration: {path}"
    text = path.read_text(encoding="utf-8")
    assert "RFC 0028" in text
    assert "subject_kind_hint" in text
    assert "has_name" in text


def test_interview_active_learning_migration_013_exists_on_disk() -> None:
    path = MIGRATIONS_DIR / "013_interview_active_learning_state.sql"
    assert path.exists(), f"missing migration: {path}"
    text = path.read_text(encoding="utf-8")
    assert "gold_label_active_learning_events" in text
    assert "active_learning_signal_version" in text
    assert "fn_gold_label_active_learning_events_append_only" in text


def test_rfc0044_migration_014_exists_on_disk() -> None:
    path = MIGRATIONS_DIR / "014_striatum_tenant_corpus.sql"
    assert path.exists(), f"missing migration: {path}"
    text = path.read_text(encoding="utf-8")
    assert "RFC 0044" in text
    assert "ADD VALUE IF NOT EXISTS 'striatum'" in text
    assert "tenant_id" in text
    assert "corpus_id" in text
    assert "captures_striatum_external_idx" in text


def test_rfc0046_migration_015_exists_on_disk() -> None:
    path = MIGRATIONS_DIR / "015_striatum_projection.sql"
    assert path.exists(), f"missing migration: {path}"
    text = path.read_text(encoding="utf-8")
    assert "RFC 0046" in text
    assert "striatum_projection_generations" in text
    assert "striatum_references" in text
    assert "striatum_projection_generations_active_parent_idx" in text
    assert "striatum_references_exact_lookup_idx" in text
    assert "fn_striatum_references_validate_parent" in text


def test_rfc0048_migration_016_exists_on_disk() -> None:
    path = MIGRATIONS_DIR / "016_striatum_packet_audits.sql"
    assert path.exists(), f"missing migration: {path}"
    text = path.read_text(encoding="utf-8")
    assert "RFC 0048" in text
    assert "striatum_packet_audits" in text
    assert "striatum_packet_audits_packet_id_idx" in text
    assert "striatum_packet_audits_omitted_gin_idx" in text
    assert "fn_striatum_packet_audits_validate" in text
    assert "fn_striatum_packet_audits_append_only" in text


def test_rfc0051_migration_022_exists_on_disk() -> None:
    path = MIGRATIONS_DIR / "022_generic_evidence_reference_index.sql"
    assert path.exists(), f"missing migration: {path}"
    text = path.read_text(encoding="utf-8")
    assert "RFC 0051" in text
    assert "evidence_items" in text
    assert "evidence_refs" in text
    assert "evidence_refs_exact_lookup_idx" in text


def test_rfc0052_migration_023_exists_on_disk() -> None:
    path = MIGRATIONS_DIR / "023_entity_grounding_review.sql"
    assert path.exists(), f"missing migration: {path}"
    text = path.read_text(encoding="utf-8")
    assert "RFC 0052" in text
    assert "entity_grounding_evidence" in text
    assert "entity_identity_review_actions" in text
    assert "fn_entity_grounding_append_only" in text


def test_rfc0053_migration_024_exists_on_disk() -> None:
    path = MIGRATIONS_DIR / "024_claim_grounding_runtime.sql"
    assert path.exists(), f"missing migration: {path}"
    text = path.read_text(encoding="utf-8")
    assert "RFC 0053" in text
    assert "claim_grounding_requests" in text
    assert "claim_grounding_responses" in text
    assert "claim_grounding_network_dispatches" in text
    assert "claim_grounding_grants" in text
    assert "claim_grounding_grant_uses" in text
    assert "claim_grounding_links" in text
    assert "fn_claim_grounding_append_only" in text


def test_rfc0021_migration_010_applies_via_conn_fixture(conn) -> None:
    """The conftest fixture already runs ``migrate(conn)``; presence of the
    new tables/views is the contract."""

    for table in (
        "gold_label_sessions",
        "gold_label_strata_vocabulary",
        "gold_label_verdict_vocabulary",
        "gold_labels",
    ):
        row = conn.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{table}",)).fetchone()
        assert row[0] is True, f"table missing: {table}"
    view_row = conn.execute(
        "SELECT to_regclass('public.current_gold_label') IS NOT NULL"
    ).fetchone()
    assert view_row[0] is True


def test_012_predicate_subject_kind_hint_applies(conn) -> None:
    row = conn.execute(
        """
        SELECT description, subject_kind_hint
        FROM predicate_vocabulary
        WHERE predicate = 'has_name'
        """
    ).fetchone()
    assert row == ("legal or preferred name", "persons only")

    with pytest.raises(errors.CheckViolation):
        conn.execute(
            """
            UPDATE predicate_vocabulary
            SET subject_kind_hint = ''
            WHERE predicate = 'has_name'
            """
        )
    conn.rollback()


def test_013_interview_active_learning_state_applies(conn) -> None:
    table_row = conn.execute(
        "SELECT to_regclass('public.gold_label_active_learning_events') IS NOT NULL"
    ).fetchone()
    assert table_row[0] is True
    columns = {
        row[0]
        for row in conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'gold_label_session_targets'
            """
        ).fetchall()
    }
    assert {
        "active_learning_signal_version",
        "confidence",
        "observed_at",
    } <= columns

    event_id = conn.execute(
        """
        INSERT INTO gold_label_active_learning_events (signal_version)
        VALUES ('rfc0018.reviewer.v1')
        RETURNING id
        """
    ).fetchone()[0]
    with pytest.raises(errors.RaiseException) as update_exc:
        conn.execute(
            "UPDATE gold_label_active_learning_events SET signal_version = 'changed' WHERE id = %s",
            (event_id,),
        )
    assert update_exc.value.diag.sqlstate == "P0001"
    conn.rollback()


def test_014_striatum_tenant_corpus_applies(conn) -> None:
    source_kind_row = conn.execute("SELECT 'striatum'::source_kind::text").fetchone()
    assert source_kind_row[0] == "striatum"

    for table in (
        "sources",
        "conversations",
        "messages",
        "notes",
        "captures",
        "segments",
        "claims",
        "beliefs",
    ):
        columns = {
            row[0]
            for row in conn.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s
                """,
                (table,),
            ).fetchall()
        }
        assert {"tenant_id", "corpus_id"} <= columns

    capture_columns = {
        row[0]
        for row in conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'captures'
            """
        ).fetchall()
    }
    assert "bundle_id" in capture_columns

    index_row = conn.execute(
        "SELECT to_regclass('public.captures_striatum_external_idx') IS NOT NULL"
    ).fetchone()
    assert index_row[0] is True


def test_015_striatum_projection_schema_applies(conn) -> None:
    for table in ("striatum_projection_generations", "striatum_references"):
        row = conn.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{table}",)).fetchone()
        assert row[0] is True, f"table missing: {table}"

    for index in (
        "striatum_projection_generations_idempotency_idx",
        "striatum_projection_generations_active_parent_idx",
        "striatum_references_generation_ref_idx",
        "striatum_references_exact_lookup_idx",
        "striatum_references_generation_active_idx",
    ):
        row = conn.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{index}",)).fetchone()
        assert row[0] is True, f"index missing: {index}"


def test_015_striatum_projection_constraints(conn) -> None:
    manifest_hash = "a" * 64
    content_hash = "b" * 64
    generation_id = conn.execute(
        """
        INSERT INTO striatum_projection_generations (
            tenant_id,
            corpus_id,
            parent_kind,
            parent_id,
            bundle_id,
            contract_version,
            projection_schema_version,
            projection_code_version,
            input_manifest_sha256,
            input_item_count,
            status,
            activated_at
        )
        VALUES (
            'striatum',
            'striatum',
            'bundle',
            'bundle-1',
            'bundle-1',
            'striatum.v2',
            'rfc0046.layer1.v1',
            'projection.v1',
            %s,
            1,
            'activated',
            now()
        )
        RETURNING id
        """,
        (manifest_hash,),
    ).fetchone()[0]

    with pytest.raises(errors.UniqueViolation):
        conn.execute(
            """
            INSERT INTO striatum_projection_generations (
                tenant_id,
                corpus_id,
                parent_kind,
                parent_id,
                bundle_id,
                contract_version,
                projection_schema_version,
                projection_code_version,
                input_manifest_sha256,
                input_item_count,
                status,
                activated_at
            )
            VALUES (
                'striatum',
                'striatum',
                'bundle',
                'bundle-1',
                'bundle-2',
                'striatum.v2',
                'rfc0046.layer1.v1',
                'projection.v1',
                %s,
                1,
                'activated',
                now()
            )
            """,
            ("c" * 64,),
        )
    conn.rollback()

    source_id = conn.execute(
        """
        INSERT INTO sources (
            source_kind,
            external_id,
            raw_payload,
            tenant_id,
            corpus_id,
            bundle_id
        )
        VALUES ('striatum', 'source-1', '{}'::jsonb, 'striatum', 'striatum', 'bundle-1')
        RETURNING id
        """
    ).fetchone()[0]
    capture_id = conn.execute(
        """
        INSERT INTO captures (
            source_id,
            source_kind,
            external_id,
            raw_payload,
            capture_type,
            tenant_id,
            corpus_id,
            bundle_id,
            observed_at
        )
        VALUES (
            %s,
            'striatum',
            'capture-1',
            '{}'::jsonb,
            'reference',
            'striatum',
            'striatum',
            'bundle-1',
            now()
        )
        RETURNING id
        """,
        (source_id,),
    ).fetchone()[0]

    conn.execute(
        """
        INSERT INTO striatum_references (
            capture_id,
            tenant_id,
            corpus_id,
            ref_kind,
            ref_value,
            ref_value_normalized,
            content_hash,
            generation_id,
            is_active,
            observed_at
        )
        VALUES (%s, 'striatum', 'striatum', 'rfc_id', 'RFC 0046', 'rfc 0046', %s, %s, true, now())
        """,
        (capture_id, content_hash, generation_id),
    )

    with pytest.raises(errors.UniqueViolation):
        conn.execute(
            """
            INSERT INTO striatum_references (
                capture_id,
                tenant_id,
                corpus_id,
                ref_kind,
                ref_value,
                ref_value_normalized,
                content_hash,
                generation_id,
                is_active,
                observed_at
            )
            VALUES (
                %s,
                'striatum',
                'striatum',
                'rfc_id',
                'RFC 0046',
                'rfc 0046',
                %s,
                %s,
                true,
                now()
            )
            """,
            (capture_id, content_hash, generation_id),
        )
    conn.rollback()

    with pytest.raises(errors.CheckViolation):
        conn.execute(
            """
            INSERT INTO striatum_references (
                capture_id,
                tenant_id,
                corpus_id,
                ref_kind,
                ref_value,
                ref_value_normalized,
                content_hash,
                generation_id,
                is_active,
                observed_at
            )
            VALUES (
                %s,
                'striatum',
                'striatum',
                'unbounded_kind',
                'x',
                'x',
                %s,
                %s,
                false,
                now()
            )
            """,
            (capture_id, content_hash, generation_id),
        )
    conn.rollback()


def _insert_striatum_projection_generation(
    conn: psycopg.Connection,
    *,
    tenant_id: str = "striatum",
    corpus_id: str = "striatum",
) -> uuid.UUID:
    return conn.execute(
        """
        INSERT INTO striatum_projection_generations (
            tenant_id,
            corpus_id,
            parent_kind,
            parent_id,
            bundle_id,
            contract_version,
            projection_schema_version,
            projection_code_version,
            input_manifest_sha256,
            input_item_count,
            status,
            activated_at
        )
        VALUES (
            %s,
            %s,
            'bundle',
            %s,
            %s,
            'striatum.v2',
            'rfc0046.layer1.v1',
            'projection.v1',
            %s,
            1,
            'activated',
            now()
        )
        RETURNING id
        """,
        (
            tenant_id,
            corpus_id,
            f"bundle-{uuid4()}",
            f"bundle-{uuid4()}",
            "d" * 64,
        ),
    ).fetchone()[0]


def test_016_striatum_packet_audits_schema_applies(conn) -> None:
    row = conn.execute("SELECT to_regclass('public.striatum_packet_audits') IS NOT NULL").fetchone()
    assert row[0] is True

    for index in (
        "striatum_packet_audits_packet_id_idx",
        "striatum_packet_audits_tenant_corpus_created_idx",
        "striatum_packet_audits_generation_created_idx",
        "striatum_packet_audits_status_created_idx",
        "striatum_packet_audits_selected_gin_idx",
        "striatum_packet_audits_omitted_gin_idx",
    ):
        row = conn.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{index}",)).fetchone()
        assert row[0] is True, f"index missing: {index}"


def test_016_striatum_packet_audits_accept_privacy_safe_entries(conn) -> None:
    generation_id = _insert_striatum_projection_generation(conn)
    audit_id = conn.execute(
        """
        INSERT INTO striatum_packet_audits (
            packet_id,
            generation_id,
            tenant_id,
            corpus_id,
            policy_version,
            purpose,
            status,
            query,
            budget,
            selected,
            omitted
        )
        VALUES (
            gen_random_uuid(),
            %s,
            'striatum',
            'striatum',
            'rfc0048.layer3.v1',
            'packet_prepare',
            'ok',
            'RFC 0048 packet audit',
            '{"max_tokens": 1400}'::jsonb,
            '[{
                "candidate_id": "candidate-1",
                "selected": true,
                "lineage": {
                    "projection_generation_id": "generation-visible",
                    "reference_id": "ref-1",
                    "item_id": "item-1",
                    "logical_id": "logical-1",
                    "version_id": "version-1"
                }
            }]'::jsonb,
            '[{
                "candidate_id": "candidate-2",
                "selected": false,
                "reason": "over_budget",
                "lineage": {
                    "projection_generation_id": "generation-visible",
                    "reference_id": "ref-2"
                },
                "ranking": {
                    "rank": 2,
                    "score": 0.1
                }
            }]'::jsonb
        )
        RETURNING id
        """,
        (generation_id,),
    ).fetchone()[0]

    row = conn.execute(
        """
        SELECT selected -> 0 ->> 'candidate_id', omitted -> 0 ->> 'reason'
        FROM striatum_packet_audits
        WHERE id = %s
        """,
        (audit_id,),
    ).fetchone()
    assert row == ("candidate-1", "over_budget")


def test_016_striatum_packet_audits_reject_invalid_status_reason_and_payload(conn) -> None:
    generation_id = _insert_striatum_projection_generation(conn)

    with pytest.raises(errors.CheckViolation):
        conn.execute(
            """
            INSERT INTO striatum_packet_audits (
                packet_id,
                generation_id,
                tenant_id,
                corpus_id,
                policy_version,
                purpose,
                status,
                query
            )
            VALUES (
                gen_random_uuid(),
                %s,
                'striatum',
                'striatum',
                'rfc0048.layer3.v1',
                'packet_prepare',
                'invented_status',
                'query'
            )
            """,
            (generation_id,),
        )
    conn.rollback()

    with pytest.raises(errors.CheckViolation):
        conn.execute(
            """
            INSERT INTO striatum_packet_audits (
                packet_id,
                generation_id,
                tenant_id,
                corpus_id,
                policy_version,
                purpose,
                status,
                query,
                omitted
            )
            VALUES (
                gen_random_uuid(),
                %s,
                'striatum',
                'striatum',
                'rfc0048.layer3.v1',
                'packet_prepare',
                'ok',
                'query',
                '[{
                    "candidate_id": "candidate-1",
                    "selected": false,
                    "reason": "ad_hoc_reason"
                }]'::jsonb
            )
            """,
            (generation_id,),
        )
    conn.rollback()

    with pytest.raises(errors.CheckViolation):
        conn.execute(
            """
            INSERT INTO striatum_packet_audits (
                packet_id,
                generation_id,
                tenant_id,
                corpus_id,
                policy_version,
                purpose,
                status,
                query,
                selected
            )
            VALUES (
                gen_random_uuid(),
                %s,
                'striatum',
                'striatum',
                'rfc0048.layer3.v1',
                'packet_prepare',
                'ok',
                'query',
                '[{
                    "candidate_id": "candidate-1",
                    "selected": true,
                    "raw_payload": {"content": "must not be copied into audit"}
                }]'::jsonb
            )
            """,
            (generation_id,),
        )
    conn.rollback()


def test_016_striatum_packet_audits_match_generation_pair_and_append_only(conn) -> None:
    generation_id = _insert_striatum_projection_generation(conn)

    with pytest.raises(errors.CheckViolation):
        conn.execute(
            """
            INSERT INTO striatum_packet_audits (
                packet_id,
                generation_id,
                tenant_id,
                corpus_id,
                policy_version,
                purpose,
                status,
                query
            )
            VALUES (
                gen_random_uuid(),
                %s,
                'other',
                'striatum',
                'rfc0048.layer3.v1',
                'packet_prepare',
                'ok',
                'query'
            )
            """,
            (generation_id,),
        )
    conn.rollback()

    audit_id = conn.execute(
        """
        INSERT INTO striatum_packet_audits (
            packet_id,
            generation_id,
            tenant_id,
            corpus_id,
            policy_version,
            purpose,
            status,
            query
        )
        VALUES (
            gen_random_uuid(),
            %s,
            'striatum',
            'striatum',
            'rfc0048.layer3.v1',
            'packet_prepare',
            'ok',
            'query'
        )
        RETURNING id
        """,
        (generation_id,),
    ).fetchone()[0]

    with pytest.raises(errors.RaiseException) as update_exc:
        conn.execute(
            "UPDATE striatum_packet_audits SET status = 'stale' WHERE id = %s",
            (audit_id,),
        )
    assert update_exc.value.diag.sqlstate == "P0001"
    conn.rollback()


def test_022_generic_evidence_reference_index_schema_applies(conn) -> None:
    for table in ("evidence_items", "evidence_refs"):
        row = conn.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{table}",)).fetchone()
        assert row[0] is True, f"table missing: {table}"

    source_id = conn.execute("SELECT gen_random_uuid()").fetchone()[0]
    item_id = conn.execute(
        """
        INSERT INTO evidence_items (
            tenant_id,
            corpus_id,
            source_kind,
            source_table,
            source_id,
            content_hash,
            provenance
        )
        VALUES (
            'personal',
            'personal',
            'markdown_tree',
            'markdown_files',
            %s,
            repeat('a', 64),
            '{}'::jsonb
        )
        RETURNING id
        """,
        (source_id,),
    ).fetchone()[0]
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
            source_id
        )
        VALUES (
            %s,
            'personal',
            'personal',
            'path',
            'README.md',
            'readme.md',
            'markdown_files',
            %s
        )
        """,
        (item_id, source_id),
    )

    with pytest.raises(errors.UniqueViolation):
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
                source_id
            )
            VALUES (
                %s,
                'personal',
                'personal',
                'path',
                'README.md',
                'readme.md',
                'markdown_files',
                %s
            )
            """,
            (item_id, source_id),
        )
    conn.rollback()


def test_023_entity_grounding_review_schema_and_append_only(conn) -> None:
    source_kind_row = conn.execute("SELECT 'entity_grounding'::source_kind::text").fetchone()
    assert source_kind_row[0] == "entity_grounding"

    evidence_id = conn.execute(
        """
        INSERT INTO entity_grounding_evidence (
            tenant_id,
            corpus_id,
            query_text,
            entity_kind,
            content_hash,
            content_excerpt
        )
        VALUES (
            'personal',
            'personal',
            'OpenAI Codex',
            'product',
            repeat('b', 64),
            'Local grounding fixture.'
        )
        RETURNING id
        """
    ).fetchone()[0]
    action_id = conn.execute(
        """
        INSERT INTO entity_identity_review_actions (
            tenant_id,
            corpus_id,
            action_kind,
            grounding_evidence_id,
            actor
        )
        VALUES (
            'personal',
            'personal',
            'grounding_evidence_attach',
            %s,
            'test'
        )
        RETURNING id
        """,
        (evidence_id,),
    ).fetchone()[0]

    with pytest.raises(errors.RaiseException) as update_exc:
        conn.execute(
            "UPDATE entity_grounding_evidence SET entity_kind = 'tool' WHERE id = %s",
            (evidence_id,),
        )
    assert update_exc.value.diag.sqlstate == "P0001"
    conn.rollback()

    with pytest.raises(errors.RaiseException) as delete_exc:
        conn.execute(
            "DELETE FROM entity_identity_review_actions WHERE id = %s",
            (action_id,),
        )
    assert delete_exc.value.diag.sqlstate == "P0001"
    conn.rollback()


def test_024_claim_grounding_runtime_schema_and_append_only(conn) -> None:
    for table in (
        "claim_grounding_requests",
        "claim_grounding_responses",
        "claim_grounding_network_dispatches",
        "claim_grounding_grants",
        "claim_grounding_grant_uses",
        "claim_grounding_links",
    ):
        row = conn.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{table}",)).fetchone()
        assert row[0] is True, f"table missing: {table}"

    request_id = conn.execute(
        """
        INSERT INTO claim_grounding_requests (
            tenant_id,
            corpus_id,
            extraction_prompt_version,
            extraction_model_version,
            surface_form,
            mention_role,
            candidate_entity_kinds,
            source_refs,
            network_grant,
            allowed_modes
        )
        VALUES (
            'personal',
            'personal',
            'extractor.v1.test',
            'local-model.test',
            'Tartine',
            'subject',
            ARRAY['product'],
            '[{"target_table":"messages","target_id":"00000000-0000-0000-0000-000000000001"}]'::jsonb,
            '{"grant_id":"00000000-0000-0000-0000-000000000002"}'::jsonb,
            ARRAY['local_lookup','network_fetch']
        )
        RETURNING id
        """
    ).fetchone()[0]
    grant_id = conn.execute(
        """
        INSERT INTO claim_grounding_grants (
            tenant_id,
            corpus_id,
            request_id,
            grant_status,
            grant_purpose,
            target_mode,
            surface_form,
            search_query,
            query_text_class,
            query_privacy_tier,
            allowed_network_targets,
            granted_by,
            granted_at,
            expires_at
        )
        VALUES (
            'personal',
            'personal',
            %s,
            'approved',
            'entity_grounding',
            'network_fetch',
            'Tartine',
            'Tartine',
            'entity_surface_form',
            1,
            ARRAY['internet_search'],
            'operator',
            '2026-05-18T00:00:00Z',
            '2026-05-18T01:00:00Z'
        )
        RETURNING id
        """,
        (request_id,),
    ).fetchone()[0]
    dispatch_id = conn.execute(
        """
        INSERT INTO claim_grounding_network_dispatches (
            request_id,
            grant_id,
            tenant_id,
            corpus_id,
            target_mode,
            target_adapter,
            search_query,
            query_privacy_tier,
            dispatch_status
        )
        VALUES (
            %s,
            %s,
            'personal',
            'personal',
            'network_fetch',
            'internet_search',
            'Tartine',
            1,
            'succeeded'
        )
        RETURNING id
        """,
        (request_id, grant_id),
    ).fetchone()[0]
    conn.execute(
        """
        INSERT INTO claim_grounding_grant_uses (
            grant_id,
            request_id,
            dispatch_id,
            tenant_id,
            corpus_id,
            use_status,
            target_adapter,
            search_query,
            query_privacy_tier
        )
        VALUES (
            %s,
            %s,
            %s,
            'personal',
            'personal',
            'verified',
            'internet_search',
            'Tartine',
            1
        )
        """,
        (grant_id, request_id, dispatch_id),
    )
    evidence_id = conn.execute(
        """
        INSERT INTO entity_grounding_evidence (
            tenant_id,
            corpus_id,
            query_text,
            entity_kind,
            content_hash,
            content_excerpt
        )
        VALUES (
            'personal',
            'personal',
            'Tartine',
            'product',
            repeat('c', 64),
            'Public grounding fixture.'
        )
        RETURNING id
        """
    ).fetchone()[0]
    response_id = conn.execute(
        """
        INSERT INTO claim_grounding_responses (
            request_id,
            tenant_id,
            corpus_id,
            status,
            mode,
            network_fetch,
            candidates,
            broker_version
        )
        VALUES (
            %s,
            'personal',
            'personal',
            'resolved',
            'network_fetch',
            'performed_by_grounding_broker',
            jsonb_build_array(jsonb_build_object(
                'candidate_id', 'candidate-1',
                'grounding_evidence_ids', jsonb_build_array(%s::text)
            )),
            'grounding-broker.test'
        )
        RETURNING id
        """,
        (request_id, evidence_id),
    ).fetchone()[0]
    conn.execute(
        """
        INSERT INTO claim_grounding_links (
            request_id,
            response_id,
            grounding_evidence_id,
            tenant_id,
            corpus_id,
            link_kind,
            response_candidate_id
        )
        VALUES (
            %s,
            %s,
            %s,
            'personal',
            'personal',
            'response_candidate_to_evidence',
            'candidate-1'
        )
        """,
        (request_id, response_id, evidence_id),
    )

    with pytest.raises(errors.CheckViolation):
        conn.execute(
            """
            INSERT INTO claim_grounding_responses (
                request_id,
                status,
                mode,
                network_fetch,
                response_payload,
                broker_version
            )
            VALUES (
                %s,
                'not_found',
                'local_lookup',
                'not_requested',
                '[]'::jsonb,
                'grounding-broker.test'
            )
            """,
            (request_id,),
        )
    conn.rollback()

    with pytest.raises(errors.RaiseException) as update_exc:
        conn.execute(
            """
            UPDATE claim_grounding_requests
            SET surface_form = 'Changed'
            WHERE id = %s
            """,
            (request_id,),
        )
    assert update_exc.value.diag.sqlstate == "P0001"
    conn.rollback()

    with pytest.raises(errors.RaiseException) as delete_exc:
        conn.execute(
            "DELETE FROM claim_grounding_responses WHERE id = %s",
            (response_id,),
        )
    assert delete_exc.value.diag.sqlstate == "P0001"
    conn.rollback()


def test_migration_checksums_detect_changed_applied_file(conn, tmp_path):
    probe_suffix = uuid4().hex
    probe_table = f"migration_checksum_probe_{probe_suffix}"
    changed_table = f"migration_checksum_probe_changed_{probe_suffix}"
    migration = tmp_path / f"999_checksum_probe_{probe_suffix}.sql"
    migration.write_text(
        f"CREATE TABLE {probe_table} (id INT PRIMARY KEY);",
        encoding="utf-8",
    )

    assert migrate(conn, migrations_dir=tmp_path) == [migration.name]
    assert (
        conn.execute(
            "SELECT checksum IS NOT NULL FROM schema_migrations WHERE filename = %s",
            (migration.name,),
        ).fetchone()[0]
        is True
    )

    migration.write_text(
        f"CREATE TABLE {changed_table} (id INT PRIMARY KEY);",
        encoding="utf-8",
    )

    with pytest.raises(MigrationDriftError, match=migration.name):
        migrate(conn, migrations_dir=tmp_path)


def test_011_session_targets_append_only(conn) -> None:
    """UPDATE/DELETE on gold_label_session_targets raise P0001 (RFC 0027)."""
    session_id = _new_session(conn)
    conn.execute(_INSERT_TARGET_SQL, _claim_target_row(session_id, idx=0))

    with pytest.raises(errors.RaiseException) as update_exc:
        conn.execute(
            "UPDATE gold_label_session_targets SET stability_class = 'mood' "
            "WHERE session_id = %s AND idx = 0",
            (session_id,),
        )
    assert update_exc.value.diag.sqlstate == "P0001"
    assert "append-only" in str(update_exc.value)
    conn.rollback()

    with pytest.raises(errors.RaiseException) as delete_exc:
        conn.execute(
            "DELETE FROM gold_label_session_targets WHERE session_id = %s",
            (session_id,),
        )
    assert delete_exc.value.diag.sqlstate == "P0001"
    assert "append-only" in str(delete_exc.value)
    conn.rollback()


def test_011_session_targets_version_triple_check(conn) -> None:
    """Mixing extraction + consolidation columns violates the CHECK."""
    session_id = _new_session(conn)
    bad_claim = list(_claim_target_row(session_id, idx=0))
    # ``claim`` row with consolidation columns set must fail the CHECK.
    bad_claim[7] = CONSOLIDATOR_PROMPT_VERSION  # consolidation_prompt_version
    bad_claim[8] = CONSOLIDATOR_MODEL_VERSION  # consolidation_model_version
    with pytest.raises(errors.CheckViolation):
        conn.execute(_INSERT_TARGET_SQL, tuple(bad_claim))
    conn.rollback()

    bad_belief = list(_belief_target_row(session_id, idx=1))
    # ``belief`` row with extraction columns set must fail the CHECK.
    bad_belief[5] = EXTRACTION_PROMPT_VERSION  # extraction_prompt_version
    bad_belief[6] = "model-a"  # extraction_model_version
    with pytest.raises(errors.CheckViolation):
        conn.execute(_INSERT_TARGET_SQL, tuple(bad_belief))
    conn.rollback()


def test_011_session_targets_pk_uniqueness(conn) -> None:
    """Duplicate (session_id, idx) raises a unique-violation."""
    session_id = _new_session(conn)
    conn.execute(_INSERT_TARGET_SQL, _claim_target_row(session_id, idx=0))
    with pytest.raises(errors.UniqueViolation):
        conn.execute(_INSERT_TARGET_SQL, _claim_target_row(session_id, idx=0))
    conn.rollback()
