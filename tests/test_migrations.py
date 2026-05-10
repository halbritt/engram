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
