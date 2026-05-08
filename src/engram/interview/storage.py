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
from datetime import datetime
from typing import Any  # noqa: F401  # used in psycopg signatures below

import psycopg
from psycopg import errors
from psycopg.types.json import Jsonb

from engram.interview.errors import GoldLabelStorageError


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


def _translate_raise(exc: errors.RaiseException) -> GoldLabelStorageError:
    return GoldLabelStorageError(str(exc).strip() or "gold-label storage trigger raised P0001")


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
