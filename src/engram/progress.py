from __future__ import annotations

from typing import Any

import psycopg
from psycopg.types.json import Jsonb


def upsert_progress(
    conn: psycopg.Connection,
    *,
    stage: str,
    scope: str,
    status: str,
    position: dict[str, Any] | None = None,
    last_error: str | None = None,
    increment_error: bool = False,
) -> None:
    conn.execute(
        """
        INSERT INTO consolidation_progress (
            stage,
            scope,
            status,
            started_at,
            updated_at,
            position,
            error_count,
            last_error
        )
        VALUES (
            %s,
            %s,
            %s,
            CASE WHEN %s = 'in_progress' THEN now() ELSE NULL END,
            now(),
            %s,
            CASE WHEN %s THEN 1 ELSE 0 END,
            %s
        )
        ON CONFLICT (stage, scope) DO UPDATE SET
            status = EXCLUDED.status,
            started_at = COALESCE(consolidation_progress.started_at, EXCLUDED.started_at),
            updated_at = now(),
            position = EXCLUDED.position,
            error_count = consolidation_progress.error_count
                + CASE WHEN %s THEN 1 ELSE 0 END,
            last_error = EXCLUDED.last_error
        """,
        (
            stage,
            scope,
            status,
            status,
            Jsonb(position or {}),
            increment_error,
            last_error,
            increment_error,
        ),
    )
