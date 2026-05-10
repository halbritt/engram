"""Scratch SQLite review state for the RFC 0029 bench triage workbench."""

from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from engram.bench_review.artifacts import SegmentComparison
from engram.bench_review.classify import STRONG_DECISION_DISABLED_STATES, queue_sort_key

RATIONALE_MAX_CHARS: int = int(
    os.environ.get("ENGRAM_BENCH_REVIEW_RATIONALE_MAX_CHARS", "500")
)

SEGMENT_DECISIONS: frozenset[str] = frozenset(
    {
        "accept_candidate_change",
        "flag_candidate_regression",
        "needs_followup",
        "exclude_from_review",
    }
)
RUN_DECISIONS: frozenset[str] = frozenset(
    {"safe_to_promote", "blocked_by_regressions", "needs_more_review"}
)

RUN_DECISION_LABELS: dict[str, str] = {
    "safe_to_promote": "Bench review: safe to promote candidate",
    "blocked_by_regressions": "Bench review: blocked by regressions",
    "needs_more_review": "Bench review: needs more review",
}


class BenchReviewStorageError(RuntimeError):
    """Raised when scratch review state cannot be read or written."""


@dataclass(frozen=True)
class ReviewSessionConfig:
    run_id: str
    slice_path: Path
    run_path: Path
    segments_path: Path | None
    candidate_prompt_version: str | None
    candidate_model_version: str | None
    candidate_request_profile_version: str | None
    prior_prompt_version: str
    prior_model_version: str
    prior_request_profile_version: str


def initialize_review_db(
    db_path: Path, *, config: ReviewSessionConfig, rows: tuple[SegmentComparison, ...]
) -> None:
    """Create/update scratch SQLite review state without overwriting decisions."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        _create_schema(conn)
        now = _utc_now()
        conn.execute(
            """
            INSERT INTO review_sessions (
              id, run_id, slice_path, run_path, segments_path,
              candidate_prompt_version, candidate_model_version,
              candidate_request_profile_version,
              prior_prompt_version, prior_model_version,
              prior_request_profile_version, created_at, updated_at
            )
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              run_id=excluded.run_id,
              slice_path=excluded.slice_path,
              run_path=excluded.run_path,
              segments_path=excluded.segments_path,
              candidate_prompt_version=excluded.candidate_prompt_version,
              candidate_model_version=excluded.candidate_model_version,
              candidate_request_profile_version=excluded.candidate_request_profile_version,
              prior_prompt_version=excluded.prior_prompt_version,
              prior_model_version=excluded.prior_model_version,
              prior_request_profile_version=excluded.prior_request_profile_version,
              updated_at=excluded.updated_at
            """,
            (
                config.run_id,
                str(config.slice_path),
                str(config.run_path),
                str(config.segments_path) if config.segments_path is not None else None,
                config.candidate_prompt_version,
                config.candidate_model_version,
                config.candidate_request_profile_version,
                config.prior_prompt_version,
                config.prior_model_version,
                config.prior_request_profile_version,
                now,
                now,
            ),
        )
        for row in rows:
            conn.execute(
                """
                INSERT INTO segment_reviews (
                  segment_id, data_state, tags_json,
                  prior_claim_count, candidate_claim_count,
                  prior_dropped_count, candidate_dropped_count,
                  updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(segment_id) DO UPDATE SET
                  data_state=excluded.data_state,
                  tags_json=excluded.tags_json,
                  prior_claim_count=excluded.prior_claim_count,
                  candidate_claim_count=excluded.candidate_claim_count,
                  prior_dropped_count=excluded.prior_dropped_count,
                  candidate_dropped_count=excluded.candidate_dropped_count,
                  updated_at=excluded.updated_at
                """,
                (
                    row.segment_id,
                    row.data_state,
                    json.dumps(list(row.tags), sort_keys=True),
                    row.prior_claim_count,
                    row.candidate_claim_count,
                    row.prior_dropped_count,
                    row.candidate_dropped_count,
                    now,
                ),
            )
        conn.execute(
            """
            INSERT INTO run_reviews (id, updated_at)
            VALUES (1, ?)
            ON CONFLICT(id) DO NOTHING
            """,
            (now,),
        )


def get_session(db_path: Path) -> sqlite3.Row:
    """Return the singleton review session row."""
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM review_sessions WHERE id = 1").fetchone()
        if row is None:
            raise BenchReviewStorageError("review session not initialized")
        return row


def list_segments(
    db_path: Path,
    *,
    state: str | None = None,
    tag: str | None = None,
    decision: str | None = None,
    remaining: bool = False,
    reviewable: bool = False,
    limit: int | None = None,
) -> list[sqlite3.Row]:
    """List segment review rows with simple filters."""
    clauses: list[str] = []
    params: list[object] = []
    if state:
        clauses.append("data_state = ?")
        params.append(state)
    if decision:
        clauses.append("decision = ?")
        params.append(decision)
    if remaining:
        clauses.append("decision IS NULL")
    if reviewable:
        placeholders = ", ".join("?" for _ in STRONG_DECISION_DISABLED_STATES)
        clauses.append(f"data_state NOT IN ({placeholders})")
        params.extend(sorted(STRONG_DECISION_DISABLED_STATES))
    sql = "SELECT * FROM segment_reviews"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    with _connect(db_path) as conn:
        rows = list(conn.execute(sql, params).fetchall())
    if tag:
        rows = [row for row in rows if tag in json.loads(row["tags_json"])]
    rows.sort(
        key=lambda row: queue_sort_key(
            row["data_state"], tuple(json.loads(row["tags_json"])), row["segment_id"]
        )
    )
    if limit is not None:
        rows = rows[:limit]
    return rows


def get_segment(db_path: Path, segment_id: str) -> sqlite3.Row | None:
    """Return one segment row."""
    with _connect(db_path) as conn:
        return conn.execute(
            "SELECT * FROM segment_reviews WHERE segment_id = ?", (segment_id,)
        ).fetchone()


def record_segment_decision(
    db_path: Path, *, segment_id: str, decision: str, rationale: str | None
) -> None:
    """Persist a segment decision in scratch SQLite."""
    if decision not in SEGMENT_DECISIONS:
        raise BenchReviewStorageError(f"invalid segment decision: {decision}")
    now = _utc_now()
    note = sanitize_rationale(rationale)
    with _connect(db_path) as conn:
        cur = conn.execute(
            """
            UPDATE segment_reviews
            SET decision = ?, rationale = ?, decided_at = ?, updated_at = ?
            WHERE segment_id = ?
            """,
            (decision, note, now, now, segment_id),
        )
        if cur.rowcount == 0:
            raise BenchReviewStorageError(f"unknown segment: {segment_id}")


def record_run_decision(db_path: Path, *, decision: str, rationale: str | None) -> None:
    """Persist the run-level decision in scratch SQLite."""
    if decision not in RUN_DECISIONS:
        raise BenchReviewStorageError(f"invalid run decision: {decision}")
    now = _utc_now()
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO run_reviews (id, decision, rationale, decided_at, updated_at)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              decision=excluded.decision,
              rationale=excluded.rationale,
              decided_at=excluded.decided_at,
              updated_at=excluded.updated_at
            """,
            (decision, sanitize_rationale(rationale), now, now),
        )


def summary(db_path: Path) -> dict[str, object]:
    """Return aggregate progress for status, export, and web pages."""
    with _connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM segment_reviews").fetchone()[0]
        decided = conn.execute(
            "SELECT COUNT(*) FROM segment_reviews WHERE decision IS NOT NULL"
        ).fetchone()[0]
        by_state = _count_rows(conn, "data_state")
        by_decision = _count_rows(conn, "decision")
        tag_counts: dict[str, int] = {}
        for row in conn.execute("SELECT tags_json FROM segment_reviews"):
            for tag in json.loads(row["tags_json"]):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        run_row = conn.execute("SELECT * FROM run_reviews WHERE id = 1").fetchone()
    return {
        "total": total,
        "decided": decided,
        "remaining": total - decided,
        "by_state": by_state,
        "by_decision": by_decision,
        "by_tag": dict(sorted(tag_counts.items())),
        "run_decision": run_row["decision"] if run_row is not None else None,
        "run_decision_label": (
            run_decision_label(run_row["decision"])
            if run_row is not None and run_row["decision"]
            else None
        ),
        "run_rationale": run_row["rationale"] if run_row is not None else None,
    }


def run_decision_label(decision: str) -> str:
    """Return bench-scoped display label for a run decision."""
    return RUN_DECISION_LABELS.get(decision, decision.replace("_", " "))


def sanitize_rationale(value: str | None) -> str | None:
    """Sanitize operator rationale before storage/export."""
    if value is None:
        return None
    collapsed = re.sub(r"\s+", " ", "".join(ch if ch >= " " else " " for ch in value))
    trimmed = collapsed.strip()
    if not trimmed:
        return None
    return trimmed[:RATIONALE_MAX_CHARS]


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS review_sessions (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          run_id TEXT NOT NULL,
          slice_path TEXT NOT NULL,
          run_path TEXT NOT NULL,
          segments_path TEXT,
          candidate_prompt_version TEXT,
          candidate_model_version TEXT,
          candidate_request_profile_version TEXT,
          prior_prompt_version TEXT NOT NULL,
          prior_model_version TEXT NOT NULL,
          prior_request_profile_version TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS segment_reviews (
          segment_id TEXT PRIMARY KEY,
          data_state TEXT NOT NULL,
          tags_json TEXT NOT NULL,
          prior_claim_count INTEGER,
          candidate_claim_count INTEGER,
          prior_dropped_count INTEGER,
          candidate_dropped_count INTEGER,
          decision TEXT,
          rationale TEXT,
          decided_at TEXT,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS run_reviews (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          decision TEXT,
          rationale TEXT,
          decided_at TEXT,
          updated_at TEXT NOT NULL
        );
        """
    )


def _count_rows(conn: sqlite3.Connection, column: str) -> dict[str, int]:
    rows = conn.execute(
        f"SELECT COALESCE({column}, 'undecided') AS key, COUNT(*) AS count "
        "FROM segment_reviews GROUP BY key ORDER BY key"
    ).fetchall()
    return {row["key"]: int(row["count"]) for row in rows}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
