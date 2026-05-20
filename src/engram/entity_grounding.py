from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import psycopg

GROUNDING_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_\-:#./]+", re.IGNORECASE)
GROUNDING_SCAN_LIMIT = 1000


@dataclass(frozen=True)
class GroundingEvidenceHit:
    """One local entity-grounding evidence search hit."""

    id: str
    tenant_id: str
    corpus_id: str
    query_text: str
    entity_kind: str
    source_url: str | None
    source_label: str | None
    content_hash: str
    content_excerpt: str
    fetched_at: str | None
    created_at: str | None
    fetch_tool_version: str
    extractor_version: str
    privacy_tier: int
    sensitivity_class: str
    score: float

    def to_json(self) -> dict[str, Any]:
        citation = {
            "grounding_evidence_id": self.id,
            "source_url": self.source_url,
            "source_label": self.source_label,
            "content_hash": self.content_hash,
            "fetched_at": self.fetched_at,
        }
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "corpus_id": self.corpus_id,
            "query_text": self.query_text,
            "entity_kind": self.entity_kind,
            "source_url": self.source_url,
            "source_label": self.source_label,
            "content_hash": self.content_hash,
            "content_excerpt": self.content_excerpt,
            "fetched_at": self.fetched_at,
            "created_at": self.created_at,
            "fetch_tool_version": self.fetch_tool_version,
            "extractor_version": self.extractor_version,
            "privacy_tier": self.privacy_tier,
            "sensitivity_class": self.sensitivity_class,
            "score": self.score,
            "citation": {key: value for key, value in citation.items() if value is not None},
        }


def search_grounding_evidence(
    conn: psycopg.Connection,
    *,
    query_text: str,
    tenant_id: str,
    corpus_id: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Search already-local entity grounding evidence without network fetches."""
    query = query_text.strip()
    if not query:
        raise ValueError("query_text must be non-empty")
    if not _table_exists(conn, "entity_grounding_evidence"):
        return []

    rows = conn.execute(
        """
        SELECT
            id::text,
            tenant_id,
            corpus_id,
            query_text,
            entity_kind,
            source_url,
            source_label,
            content_hash,
            content_excerpt,
            fetched_at,
            created_at,
            fetch_tool_version,
            extractor_version,
            privacy_tier,
            sensitivity_class,
            raw_payload
        FROM entity_grounding_evidence
        WHERE tenant_id = %s
          AND corpus_id = %s
        ORDER BY COALESCE(fetched_at, created_at) DESC, id::text
        LIMIT %s
        """,
        (tenant_id, corpus_id, GROUNDING_SCAN_LIMIT),
    ).fetchall()

    tokens = _tokenize(query)
    hits: list[GroundingEvidenceHit] = []
    for row in rows:
        score = _score_grounding_row(row, query=query, tokens=tokens)
        if score <= 0:
            continue
        hits.append(
            GroundingEvidenceHit(
                id=str(row[0]),
                tenant_id=str(row[1]),
                corpus_id=str(row[2]),
                query_text=str(row[3]),
                entity_kind=str(row[4]),
                source_url=str(row[5]) if row[5] is not None else None,
                source_label=str(row[6]) if row[6] is not None else None,
                content_hash=str(row[7]),
                content_excerpt=str(row[8]),
                fetched_at=str(row[9]) if row[9] is not None else None,
                created_at=str(row[10]) if row[10] is not None else None,
                fetch_tool_version=str(row[11]),
                extractor_version=str(row[12]),
                privacy_tier=int(row[13]),
                sensitivity_class=str(row[14]),
                score=score,
            )
        )
    hits.sort(key=lambda hit: (-hit.score, hit.source_label or "", hit.id))
    return [hit.to_json() for hit in hits[: max(1, min(limit, 50))]]


def _score_grounding_row(
    row: tuple[Any, ...],
    *,
    query: str,
    tokens: list[str],
) -> float:
    raw_payload = row[15] if isinstance(row[15], dict) else {}
    haystack = " ".join(
        [
            str(row[3] or ""),
            str(row[4] or ""),
            str(row[5] or ""),
            str(row[6] or ""),
            str(row[8] or ""),
            json.dumps(raw_payload, sort_keys=True),
        ]
    ).lower()
    score = 0.0
    normalized_query = " ".join(tokens)
    if normalized_query and normalized_query in haystack:
        score += 8.0
    if query.lower() == str(row[3] or "").lower():
        score += 5.0
    for token in tokens:
        if token in haystack:
            score += 1.0
    score += sum(1 for token in set(tokens) if token in haystack) * 0.25
    return round(score, 4)


def _tokenize(value: str) -> list[str]:
    return [match.group(0).lower() for match in GROUNDING_TOKEN_PATTERN.finditer(value)]


def _table_exists(conn: psycopg.Connection, table_name: str) -> bool:
    row = conn.execute("SELECT to_regclass(%s)", (f"public.{table_name}",)).fetchone()
    return bool(row is not None and row[0] is not None)
