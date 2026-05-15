from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg

CAPABILITY_READ_STRIATUM = "memory.read_striatum"
CAPABILITY_DESCRIBE = "memory.describe"
CAPABILITY_READ_PERSONAL = "memory.read_personal"
CAPABILITY_READ_CROSS_TENANT = "memory.read_cross_tenant"
CAPABILITY_READ_CROSS_CORPUS = "memory.read_cross_corpus"

KNOWN_MEMORY_CAPABILITIES: frozenset[str] = frozenset(
    {
        CAPABILITY_READ_STRIATUM,
        CAPABILITY_DESCRIBE,
        CAPABILITY_READ_PERSONAL,
        CAPABILITY_READ_CROSS_TENANT,
        CAPABILITY_READ_CROSS_CORPUS,
    }
)

DEFAULT_TENANT_ID = "striatum"
DEFAULT_CORPUS_ID = "striatum"

TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_\-:#./]+", re.IGNORECASE)


class MemoryCapabilityError(PermissionError):
    """Raised when a memory request exceeds its local capability boundary."""


class MemoryReferenceError(ValueError):
    """Raised when an opaque memory reference is malformed or unavailable."""


@dataclass(frozen=True, order=True)
class TenantCorpus:
    """Local Engram application-memory and corpus boundary."""

    tenant_id: str
    corpus_id: str


@dataclass(frozen=True)
class MemoryToken:
    """Engram-local read token for memory serving boundaries."""

    capabilities: frozenset[str]
    allowed_pairs: frozenset[TenantCorpus]
    primary_pair: TenantCorpus | None = None

    @classmethod
    def default_striatum_operator(cls) -> MemoryToken:
        """Return the default read-only Striatum operator token."""
        pair = TenantCorpus(DEFAULT_TENANT_ID, DEFAULT_CORPUS_ID)
        return cls(
            capabilities=frozenset({CAPABILITY_READ_STRIATUM, CAPABILITY_DESCRIBE}),
            allowed_pairs=frozenset({pair}),
            primary_pair=pair,
        )

    def authorize_describe(self, pair: TenantCorpus) -> None:
        """Authorize metadata-only access for one visible tenant/corpus pair."""
        if CAPABILITY_DESCRIBE not in self.capabilities:
            raise MemoryCapabilityError('missing capability "memory.describe"')
        if pair not in self.allowed_pairs:
            raise MemoryCapabilityError(
                f'tenant/corpus "{pair.tenant_id}/{pair.corpus_id}" is not visible'
            )

    def authorize_read(self, pair: TenantCorpus) -> None:
        """Authorize read access for one tenant/corpus pair."""
        if pair not in self.allowed_pairs:
            raise MemoryCapabilityError(
                f'tenant/corpus "{pair.tenant_id}/{pair.corpus_id}" is not allowed'
            )
        self._authorize_cross_boundary(pair)
        if pair.tenant_id == "striatum":
            if CAPABILITY_READ_STRIATUM not in self.capabilities:
                raise MemoryCapabilityError('missing capability "memory.read_striatum"')
            return
        if pair.tenant_id == "personal":
            if CAPABILITY_READ_PERSONAL not in self.capabilities:
                raise MemoryCapabilityError('missing capability "memory.read_personal"')
            return
        if CAPABILITY_READ_CROSS_TENANT not in self.capabilities:
            raise MemoryCapabilityError('missing capability "memory.read_cross_tenant"')

    def authorize_read_many(self, pairs: set[TenantCorpus]) -> None:
        """Authorize a request spanning one or more tenant/corpus pairs."""
        if (
            len({pair.tenant_id for pair in pairs}) > 1
            and CAPABILITY_READ_CROSS_TENANT not in self.capabilities
        ):
            raise MemoryCapabilityError('missing capability "memory.read_cross_tenant"')
        for tenant_id in {pair.tenant_id for pair in pairs}:
            corpora = {pair.corpus_id for pair in pairs if pair.tenant_id == tenant_id}
            if len(corpora) > 1 and CAPABILITY_READ_CROSS_CORPUS not in self.capabilities:
                raise MemoryCapabilityError('missing capability "memory.read_cross_corpus"')
        for pair in pairs:
            self.authorize_read(pair)

    def _authorize_cross_boundary(self, pair: TenantCorpus) -> None:
        primary_pair = self._primary_pair()
        if pair.tenant_id != primary_pair.tenant_id:
            if CAPABILITY_READ_CROSS_TENANT not in self.capabilities:
                raise MemoryCapabilityError('missing capability "memory.read_cross_tenant"')
            return
        if (
            pair.corpus_id != primary_pair.corpus_id
            and CAPABILITY_READ_CROSS_CORPUS not in self.capabilities
        ):
            raise MemoryCapabilityError('missing capability "memory.read_cross_corpus"')

    def _primary_pair(self) -> TenantCorpus:
        if self.primary_pair is not None:
            if self.primary_pair not in self.allowed_pairs:
                raise MemoryCapabilityError("primary tenant/corpus is not allowed")
            return self.primary_pair
        if len(self.allowed_pairs) == 1:
            return next(iter(self.allowed_pairs))
        default_pair = TenantCorpus(DEFAULT_TENANT_ID, DEFAULT_CORPUS_ID)
        if default_pair in self.allowed_pairs:
            return default_pair
        raise MemoryCapabilityError("cannot authorize read without fixed tenant/corpus scope")


@dataclass(frozen=True)
class SearchHit:
    """One ranked raw-memory search result."""

    reference_id: str
    tenant_id: str
    corpus_id: str
    source_kind: str
    sub_kind: str
    external_id: str
    content: str
    score: float
    privacy_tier: int
    provenance: dict[str, Any]  # Provenance is source JSON and remains schema-flexible.

    def to_json(self) -> dict[str, Any]:
        """Return the JSON shape exposed through CLI and MCP."""
        return {
            "reference_id": self.reference_id,
            "tenant_id": self.tenant_id,
            "corpus_id": self.corpus_id,
            "source_kind": self.source_kind,
            "sub_kind": self.sub_kind,
            "external_id": self.external_id,
            "content": self.content,
            "score": self.score,
            "privacy_tier": self.privacy_tier,
            "provenance": self.provenance,
        }


class MemoryService:
    """Read-only retrieval service over local Engram memory rows."""

    def __init__(self, conn: psycopg.Connection, token: MemoryToken | None = None) -> None:
        self.conn = conn
        self.token = token or MemoryToken.default_striatum_operator()

    def search(
        self,
        query: str,
        *,
        tenant_id: str = DEFAULT_TENANT_ID,
        corpus_id: str = DEFAULT_CORPUS_ID,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search raw Striatum memory rows inside one authorized boundary."""
        pair = TenantCorpus(tenant_id=tenant_id, corpus_id=corpus_id)
        self.token.authorize_read(pair)
        bounded_limit = max(1, min(limit, 50))
        tokens = tokenize(query)
        if not tokens:
            return []

        rows = self.conn.execute(
            """
            SELECT
                id::text,
                tenant_id,
                corpus_id,
                source_kind::text,
                external_id,
                privacy_tier,
                COALESCE(content_text, ''),
                raw_payload,
                observed_at,
                imported_at
            FROM captures
            WHERE tenant_id = %s
              AND corpus_id = %s
              AND source_kind::text = 'striatum'
            ORDER BY imported_at DESC, external_id
            LIMIT 1000
            """,
            (tenant_id, corpus_id),
        ).fetchall()

        hits: list[SearchHit] = []
        for row in rows:
            hit = build_search_hit(row, query=query, tokens=tokens)
            if hit is not None:
                hits.append(hit)
        hits.sort(key=lambda item: (-item.score, item.external_id))
        return [hit.to_json() for hit in hits[:bounded_limit]]

    def fetch_reference(self, reference_id: str) -> dict[str, Any]:
        """Fetch one referenced row after re-authorizing its stored boundary."""
        table, row_id = decode_reference_id(reference_id)
        if table != "captures":
            raise MemoryReferenceError(f'unsupported reference table "{table}"')
        row = self.conn.execute(
            """
            SELECT
                id::text,
                tenant_id,
                corpus_id,
                source_kind::text,
                external_id,
                privacy_tier,
                content_text,
                raw_payload,
                observed_at,
                imported_at
            FROM captures
            WHERE id = %s
            """,
            (row_id,),
        ).fetchone()
        if row is None:
            raise MemoryReferenceError(f'reference not found "{reference_id}"')

        pair = TenantCorpus(tenant_id=str(row[1]), corpus_id=str(row[2]))
        self.token.authorize_read(pair)
        raw_payload = dict(row[7] or {})
        return {
            "reference_id": reference_id,
            "id": row[0],
            "tenant_id": row[1],
            "corpus_id": row[2],
            "source_kind": row[3],
            "sub_kind": raw_payload.get("sub_kind"),
            "external_id": row[4],
            "privacy_tier": row[5],
            "content": row[6],
            "provenance": raw_payload.get("provenance") or {},
            "raw_payload": raw_payload,
            "observed_at": format_datetime(row[8]),
            "imported_at": format_datetime(row[9]),
        }

    def describe_corpus(
        self,
        *,
        tenant_id: str = DEFAULT_TENANT_ID,
        corpus_id: str = DEFAULT_CORPUS_ID,
    ) -> dict[str, Any]:
        """Describe one authorized local tenant/corpus pair."""
        pair = TenantCorpus(tenant_id=tenant_id, corpus_id=corpus_id)
        self.token.authorize_describe(pair)
        row_counts = {
            str(row[0] or "unknown"): int(row[1])
            for row in self.conn.execute(
                """
                SELECT COALESCE(raw_payload ->> 'sub_kind', 'unknown') AS sub_kind,
                       count(*)::int
                FROM captures
                WHERE tenant_id = %s
                  AND corpus_id = %s
                  AND source_kind::text = 'striatum'
                GROUP BY sub_kind
                ORDER BY sub_kind
                """,
                (tenant_id, corpus_id),
            ).fetchall()
        }
        source_counts = {
            str(row[0]): int(row[1])
            for row in self.conn.execute(
                """
                SELECT source_kind::text, count(*)::int
                FROM captures
                WHERE tenant_id = %s
                  AND corpus_id = %s
                GROUP BY source_kind::text
                ORDER BY source_kind::text
                """,
                (tenant_id, corpus_id),
            ).fetchall()
        }
        metadata = self.conn.execute(
            """
            SELECT
                count(*)::int,
                max(imported_at),
                min(observed_at),
                max(observed_at),
                count(DISTINCT bundle_id)::int,
                array_remove(array_agg(DISTINCT raw_payload ->> 'repo'), NULL)
            FROM captures
            WHERE tenant_id = %s
              AND corpus_id = %s
            """,
            (tenant_id, corpus_id),
        ).fetchone()
        if metadata is None:
            raise MemoryReferenceError("could not read corpus metadata")
        return {
            "tenant_id": tenant_id,
            "corpus_id": corpus_id,
            "record_count": int(metadata[0] or 0),
            "source_kind_counts": source_counts,
            "sub_kind_counts": row_counts,
            "latest_ingest_at": format_datetime(metadata[1]),
            "observed_at_min": format_datetime(metadata[2]),
            "observed_at_max": format_datetime(metadata[3]),
            "bundle_count": int(metadata[4] or 0),
            "available_repos": sorted(str(item) for item in (metadata[5] or [])),
        }

    def health(self) -> dict[str, Any]:
        """Return local DB and visible corpus readiness without leaking hidden corpora."""
        if CAPABILITY_DESCRIBE not in self.token.capabilities:
            raise MemoryCapabilityError('missing capability "memory.describe"')
        # Sort by applied ordering (applied_at DESC, filename DESC as tiebreaker)
        # instead of a fragile lexicographic max over filename — EG-000 baseline.
        schema_row = self.conn.execute(
            """
            SELECT filename FROM schema_migrations
            ORDER BY applied_at DESC, filename DESC
            LIMIT 1
            """
        ).fetchone()
        if schema_row is None:
            raise MemoryReferenceError("could not read schema metadata")
        visible_pairs = []
        for pair in sorted(self.token.allowed_pairs):
            self.token.authorize_describe(pair)
            count_row = self.conn.execute(
                """
                SELECT count(*)::int, max(imported_at)
                FROM captures
                WHERE tenant_id = %s
                  AND corpus_id = %s
                """,
                (pair.tenant_id, pair.corpus_id),
            ).fetchone()
            if count_row is None:
                raise MemoryReferenceError("could not read corpus health")
            visible_pairs.append(
                {
                    "tenant_id": pair.tenant_id,
                    "corpus_id": pair.corpus_id,
                    "record_count": int(count_row[0] or 0),
                    "latest_ingest_at": format_datetime(count_row[1]),
                }
            )
        latest = max(
            (item["latest_ingest_at"] for item in visible_pairs if item["latest_ingest_at"]),
            default=None,
        )
        return {
            "db_reachable": True,
            "schema_version": schema_row[0],
            "last_ingest_at": latest,
            "visible_tenant_corpora": visible_pairs,
        }


def build_search_hit(
    row: tuple[Any, ...],
    *,
    query: str,
    tokens: list[str],
) -> SearchHit | None:
    raw_payload = dict(row[7] or {})
    content = str(row[6] or "")
    haystack = " ".join(
        [
            content,
            str(row[4]),
            str(raw_payload.get("sub_kind") or ""),
            json.dumps(raw_payload.get("provenance") or {}, sort_keys=True),
        ]
    ).lower()
    score = score_text(haystack, query=query, tokens=tokens)
    if score <= 0:
        return None
    return SearchHit(
        reference_id=encode_reference_id("captures", str(row[0])),
        tenant_id=str(row[1]),
        corpus_id=str(row[2]),
        source_kind=str(row[3]),
        sub_kind=str(raw_payload.get("sub_kind") or "unknown"),
        external_id=str(row[4]),
        content=content,
        score=score,
        privacy_tier=int(row[5]),
        provenance=dict(raw_payload.get("provenance") or {}),
    )


def score_text(haystack: str, *, query: str, tokens: list[str]) -> float:
    """Return a small deterministic lexical relevance score."""
    score = 0.0
    normalized_query = " ".join(tokens)
    if normalized_query and normalized_query in haystack:
        score += 5.0
    for token in tokens:
        occurrences = haystack.count(token)
        if occurrences:
            score += min(occurrences, 5)
    # Reward rows matching more of the query, not one repeated term.
    score += sum(1 for token in set(tokens) if token in haystack) * 0.25
    return round(score, 4)


def tokenize(value: str) -> list[str]:
    """Tokenize a user query for local lexical search."""
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(value)]


def encode_reference_id(table: str, row_id: str) -> str:
    """Encode a reference id without making it an authorization token."""
    payload = json.dumps(
        {"table": table, "id": row_id},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_reference_id(reference_id: str) -> tuple[str, str]:
    """Decode an opaque reference id."""
    padding = "=" * (-len(reference_id) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(reference_id + padding))
    except (ValueError, json.JSONDecodeError) as exc:
        raise MemoryReferenceError("malformed reference_id") from exc
    if not isinstance(payload, dict):
        raise MemoryReferenceError("malformed reference_id")
    table = payload.get("table")
    row_id = payload.get("id")
    if not isinstance(table, str) or not isinstance(row_id, str):
        raise MemoryReferenceError("malformed reference_id")
    return table, row_id


def format_datetime(value: Any) -> str | None:
    """Return an ISO timestamp for database datetime values."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
