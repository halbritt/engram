"""Append-only INSERT helpers for the RFC 0021 gold-label tables.

Storage rules per RFC 0021 § Storage:

* ``gold_labels`` is append-only at the schema layer (``fn_gold_labels_append_only``).
* ``target_id`` is validated against the parent table per ``target_kind``.
* ``privacy_tier`` is carried from the parent row by trigger; an
  operator-supplied value that disagrees is rejected.

Trigger ``P0001`` exceptions are translated into ``GoldLabelStorageError`` so
callers in :mod:`engram.interview` see a domain error rather than a raw
``psycopg.errors.RaiseException``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any  # noqa: F401  # used in psycopg signatures below

import psycopg
from psycopg import errors
from psycopg.types.json import Jsonb

from engram.interview.errors import GoldLabelStorageError
from engram.interview.sampler import SampledTarget


VersionTriple = dict[str, str]
"""Mapping with required keys ``request_profile_version`` plus the kind-specific
extraction or consolidation pair. Schema-level CHECKs enforce shape; this
helper does not pre-validate beyond keying into the right columns."""


@dataclass(frozen=True)
class Session:
    session_id: str
    seed: int
    sampler_id: str
    sampler_version: str
    started_at: datetime
    completed_at: datetime | None
    operator_note: str | None


@dataclass(frozen=True)
class SessionTarget:
    """One materialized target in a gold-label interview session."""

    session_id: str
    idx: int
    target_kind: str
    target_id: str
    candidate_pool_snapshot_id: str
    active_learning_signal_version: str | None
    extraction_prompt_version: str | None
    extraction_model_version: str | None
    consolidation_prompt_version: str | None
    consolidation_model_version: str | None
    request_profile_version: str
    stability_class: str
    conf_band: str
    recency_band: str
    belief_status: str | None
    confidence: float | None
    observed_at: datetime | None


def _translate_raise(exc: errors.RaiseException) -> GoldLabelStorageError:
    return GoldLabelStorageError(str(exc).strip() or "gold-label storage trigger raised P0001")


def insert_active_learning_event(
    conn: psycopg.Connection,
    *,
    signal_version: str,
) -> str:
    """Persist an operator opt-in active-learning signal and return its event id."""
    normalized = signal_version.strip()
    if not normalized:
        raise GoldLabelStorageError("signal_version must not be blank")
    try:
        row = conn.execute(
            """
            INSERT INTO gold_label_active_learning_events (signal_version)
            VALUES (%s)
            RETURNING id::text
            """,
            (normalized,),
        ).fetchone()
    except errors.RaiseException as exc:
        raise _translate_raise(exc) from exc
    if row is None:
        raise GoldLabelStorageError("insert_active_learning_event returned no row")
    return row[0]


def get_active_learning_signal_version(conn: psycopg.Connection) -> str | None:
    """Return the latest locally enabled active-learning signal version."""
    row = conn.execute(
        """
        SELECT signal_version
        FROM gold_label_active_learning_events
        ORDER BY enabled_at DESC, id DESC
        LIMIT 1
        """
    ).fetchone()
    if row is None:
        return None
    return row[0]


def insert_session(
    conn: psycopg.Connection,
    *,
    seed: int,
    sampler_id: str,
    sampler_version: str,
    strata_weights: dict[str, float],
    operator_note: str | None = None,
) -> str:
    """Insert a new ``gold_label_sessions`` row and return its UUID as a string."""
    try:
        row = conn.execute(
            """
            INSERT INTO gold_label_sessions (
                seed,
                sampler_id,
                sampler_version,
                strata_weights,
                operator_note
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING session_id::text
            """,
            (seed, sampler_id, sampler_version, Jsonb(strata_weights), operator_note),
        ).fetchone()
    except errors.RaiseException as exc:
        raise _translate_raise(exc) from exc
    if row is None:
        raise GoldLabelStorageError("insert_session returned no row")
    return row[0]


def mark_session_completed(conn: psycopg.Connection, session_id: str) -> None:
    """Mark a session ``completed_at = now()`` if not already completed."""
    try:
        conn.execute(
            """
            UPDATE gold_label_sessions
            SET completed_at = now()
            WHERE session_id = %s
              AND completed_at IS NULL
            """,
            (session_id,),
        )
    except errors.RaiseException as exc:  # session-table updates are not blocked, but be defensive
        raise _translate_raise(exc) from exc


def insert_label(
    conn: psycopg.Connection,
    *,
    session_id: str,
    target_kind: str,
    target_id: str,
    version_triple: VersionTriple,
    prompt_template_version: str,
    prompt_template_path: str,
    prompt_text: str,
    verdict: str,
    rationale: str | None,
    sampler_id: str,
    sampler_version: str,
    candidate_pool_snapshot_id: str,
    active_learning_signal_version: str | None,
    stability_class: str,
    conf_band: str,
    recency_band: str,
    belief_status: str | None = None,
    strata_extra: dict[str, Any] | None = None,
    asked_at: datetime,
    answered_at: datetime,
    evidence_excerpt: str | None = None,
    privacy_tier: int | None = None,
) -> str:
    """Insert a new ``gold_labels`` row and return its UUID as a string.

    The schema-level ``CHECK`` and the three ``BEFORE INSERT`` triggers do the
    work of validating the version triple, refusing dangling ``target_id``
    references, and carrying ``privacy_tier`` from the parent row. This helper
    only routes columns into the right slots and translates any raised
    ``P0001`` into :class:`GoldLabelStorageError`.
    """
    extraction_prompt_version = version_triple.get("extraction_prompt_version")
    extraction_model_version = version_triple.get("extraction_model_version")
    consolidation_prompt_version = version_triple.get("consolidation_prompt_version")
    consolidation_model_version = version_triple.get("consolidation_model_version")
    request_profile_version = version_triple.get("request_profile_version")
    if request_profile_version is None:
        raise GoldLabelStorageError(
            "version_triple missing required key request_profile_version"
        )

    # Schema-level CHECK and the validate-target trigger enforce the shape; we
    # still pre-write a sentinel so the privacy_tier carry trigger can override
    # without a NOT NULL violation when the operator omits the column.
    effective_tier = privacy_tier if privacy_tier is not None else 0

    try:
        row = conn.execute(
            """
            INSERT INTO gold_labels (
                session_id,
                target_kind,
                target_id,
                extraction_prompt_version,
                extraction_model_version,
                consolidation_prompt_version,
                consolidation_model_version,
                request_profile_version,
                prompt_template_version,
                prompt_template_path,
                prompt_text,
                evidence_excerpt,
                verdict,
                rationale,
                sampler_id,
                sampler_version,
                candidate_pool_snapshot_id,
                active_learning_signal_version,
                stability_class,
                conf_band,
                recency_band,
                belief_status,
                strata_extra,
                asked_at,
                answered_at,
                privacy_tier
            )
            VALUES (
                %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s,
                %s, %s,
                %s
            )
            RETURNING id::text
            """,
            (
                session_id,
                target_kind,
                target_id,
                extraction_prompt_version,
                extraction_model_version,
                consolidation_prompt_version,
                consolidation_model_version,
                request_profile_version,
                prompt_template_version,
                prompt_template_path,
                prompt_text,
                evidence_excerpt,
                verdict,
                rationale,
                sampler_id,
                sampler_version,
                candidate_pool_snapshot_id,
                active_learning_signal_version,
                stability_class,
                conf_band,
                recency_band,
                belief_status,
                Jsonb(strata_extra or {}),
                asked_at,
                answered_at,
                effective_tier if privacy_tier is not None else None,
            ),
        ).fetchone()
    except errors.RaiseException as exc:
        raise _translate_raise(exc) from exc
    if row is None:
        raise GoldLabelStorageError("insert_label returned no row")
    return row[0]


def list_sessions(
    conn: psycopg.Connection,
    *,
    state: str | None = None,
) -> list[Session]:
    """List sessions, optionally filtered by ``open`` / ``completed`` / ``all``.

    ``state=None`` is treated as ``all``.
    """
    where = ""
    if state == "open":
        where = "WHERE completed_at IS NULL"
    elif state == "completed":
        where = "WHERE completed_at IS NOT NULL"
    elif state in (None, "all"):
        where = ""
    else:
        raise GoldLabelStorageError(f"unknown session state: {state!r}")

    rows = conn.execute(
        f"""
        SELECT
            session_id::text,
            seed,
            sampler_id,
            sampler_version,
            started_at,
            completed_at,
            operator_note
        FROM gold_label_sessions
        {where}
        ORDER BY started_at DESC
        """,
    ).fetchall()
    return [
        Session(
            session_id=row[0],
            seed=row[1],
            sampler_id=row[2],
            sampler_version=row[3],
            started_at=row[4],
            completed_at=row[5],
            operator_note=row[6],
        )
        for row in rows
    ]


def insert_session_targets(
    conn: psycopg.Connection,
    *,
    session_id: str,
    sampled: list[SampledTarget],
) -> None:
    """Materialize sampled targets in stable session order."""
    if not sampled:
        return
    rows = [
        (
            session_id,
            idx,
            target.target_kind,
            target.target_id,
            target.candidate_pool_snapshot_id,
            target.active_learning_signal_version,
            target.extraction_prompt_version,
            target.extraction_model_version,
            target.consolidation_prompt_version,
            target.consolidation_model_version,
            target.request_profile_version,
            target.stability_class,
            target.conf_band,
            target.recency_band,
            target.belief_status,
            target.confidence,
            target.observed_at,
        )
        for idx, target in enumerate(sampled)
    ]
    try:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO gold_label_session_targets (
                    session_id,
                    idx,
                    target_kind,
                    target_id,
                    candidate_pool_snapshot_id,
                    active_learning_signal_version,
                    extraction_prompt_version,
                    extraction_model_version,
                    consolidation_prompt_version,
                    consolidation_model_version,
                    request_profile_version,
                    stability_class,
                    conf_band,
                    recency_band,
                    belief_status,
                    confidence,
                    observed_at
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s
                )
                """,
                rows,
            )
    except errors.RaiseException as exc:
        raise _translate_raise(exc) from exc


def _session_target_from_row(row: tuple[Any, ...]) -> SessionTarget:
    return SessionTarget(
        session_id=row[0],
        idx=int(row[1]),
        target_kind=row[2],
        target_id=row[3],
        candidate_pool_snapshot_id=row[4],
        active_learning_signal_version=row[5],
        extraction_prompt_version=row[6],
        extraction_model_version=row[7],
        consolidation_prompt_version=row[8],
        consolidation_model_version=row[9],
        request_profile_version=row[10],
        stability_class=row[11],
        conf_band=row[12],
        recency_band=row[13],
        belief_status=row[14],
        confidence=float(row[15]) if row[15] is not None else None,
        observed_at=row[16],
    )


def _session_target_select_sql(where_clause: str) -> str:
    return f"""
        SELECT
            session_id::text,
            idx,
            target_kind,
            target_id::text,
            candidate_pool_snapshot_id::text,
            active_learning_signal_version,
            extraction_prompt_version,
            extraction_model_version,
            consolidation_prompt_version,
            consolidation_model_version,
            request_profile_version,
            stability_class,
            conf_band,
            recency_band,
            belief_status,
            confidence,
            observed_at
        FROM gold_label_session_targets
        {where_clause}
    """


def list_session_targets(conn: psycopg.Connection, *, session_id: str) -> list[SessionTarget]:
    """Return materialized session targets ordered by stored index."""
    rows = conn.execute(
        _session_target_select_sql("WHERE session_id = %s ORDER BY idx"),
        (session_id,),
    ).fetchall()
    return [_session_target_from_row(row) for row in rows]


def load_session_target(
    conn: psycopg.Connection,
    *,
    session_id: str,
    idx: int,
) -> SessionTarget | None:
    """Return one materialized session target by zero-based table index."""
    row = conn.execute(
        _session_target_select_sql("WHERE session_id = %s AND idx = %s"),
        (session_id, idx),
    ).fetchone()
    if row is None:
        return None
    return _session_target_from_row(row)


def unanswered_session_targets(
    conn: psycopg.Connection,
    *,
    session_id: str,
) -> list[SessionTarget]:
    """Return materialized targets without a label in this session."""
    rows = conn.execute(
        _session_target_select_sql(
            """
            WHERE session_id = %s
              AND NOT EXISTS (
                  SELECT 1
                  FROM gold_labels gl
                  WHERE gl.session_id = gold_label_session_targets.session_id
                    AND gl.target_kind = gold_label_session_targets.target_kind
                    AND gl.target_id = gold_label_session_targets.target_id
                    AND gl.request_profile_version =
                        gold_label_session_targets.request_profile_version
                    AND COALESCE(gl.extraction_prompt_version, '') =
                        COALESCE(gold_label_session_targets.extraction_prompt_version, '')
                    AND COALESCE(gl.extraction_model_version, '') =
                        COALESCE(gold_label_session_targets.extraction_model_version, '')
                    AND COALESCE(gl.consolidation_prompt_version, '') =
                        COALESCE(gold_label_session_targets.consolidation_prompt_version, '')
                    AND COALESCE(gl.consolidation_model_version, '') =
                        COALESCE(gold_label_session_targets.consolidation_model_version, '')
              )
            ORDER BY idx
            """
        ),
        (session_id,),
    ).fetchall()
    return [_session_target_from_row(row) for row in rows]


def session_target_to_sampled(target: SessionTarget) -> SampledTarget:
    """Reconstruct a sampled target from a materialized session row."""
    return SampledTarget(
        target_kind=target.target_kind,
        target_id=target.target_id,
        stability_class=target.stability_class,
        confidence=target.confidence if target.confidence is not None else 0.0,
        observed_at=target.observed_at or datetime.now(timezone.utc),
        conf_band=target.conf_band,
        recency_band=target.recency_band,
        belief_status=target.belief_status,
        candidate_pool_snapshot_id=target.candidate_pool_snapshot_id,
        active_learning_signal_version=target.active_learning_signal_version,
        extraction_prompt_version=target.extraction_prompt_version,
        extraction_model_version=target.extraction_model_version,
        consolidation_prompt_version=target.consolidation_prompt_version,
        consolidation_model_version=target.consolidation_model_version,
        request_profile_version=target.request_profile_version,
    )
