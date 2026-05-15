from __future__ import annotations

import base64
import json
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

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
RFC_ID_PATTERN = re.compile(r"(?:^|[^0-9])(?:rfc[:\-_ ]?)?0*([0-9]{1,5})(?:[^0-9]|$)", re.I)
DECISION_ID_PATTERN = re.compile(r"(D[0-9]{3,})", re.I)
EXACT_REF_KINDS: frozenset[str] = frozenset(
    {
        "item_id",
        "logical_id",
        "version_id",
        "path",
        "logical_path",
        "rfc_id",
        "decision_id",
        "review_id",
        "run_id",
        "workflow_id",
        "workflow_job_id",
        "job_id",
        "agent_process_id",
        "artifact_id",
        "issue_id",
        "blocker_id",
        "commit_sha",
        "branch",
        "tag",
        "source_hash",
        "bundle_id",
    }
)
FRESHNESS_VALUES: frozenset[str] = frozenset(
    {"fresh", "stale", "dirty_working_tree", "unknown"}
)
PACKET_POLICY_VERSION = "striatum.context_injection_policy.v1"
PACKET_RETRIEVAL_LIMIT = 50
OMISSION_REASONS: frozenset[str] = frozenset(
    {
        "disabled",
        "unavailable",
        "unauthorized",
        "privacy_tier_exceeded",
        "redaction_withheld",
        "stale_rejected",
        "over_budget",
        "duplicate",
        "generated_product_blocked",
        "low_score",
        "pair_mismatch",
    }
)


class MemoryCapabilityError(PermissionError):
    """Raised when a memory request exceeds its local capability boundary."""


class MemoryReferenceError(ValueError):
    """Raised when an opaque memory reference is malformed or unavailable."""


@dataclass(frozen=True)
class ExactRefFilter:
    """One normalized exact-reference retrieval filter."""

    ref_kind: str
    ref_value: str


@dataclass(frozen=True)
class MemorySearchFilters:
    """Typed search filters for local memory retrieval."""

    exact_refs: Sequence[ExactRefFilter] = ()


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
    dirty_working_tree: bool
    freshness: str

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
            "dirty_working_tree": self.dirty_working_tree,
            "freshness": self.freshness,
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
        filters: MemorySearchFilters | None = None,
    ) -> list[dict[str, Any]]:
        """Search raw Striatum memory rows inside one authorized boundary."""
        pair = TenantCorpus(tenant_id=tenant_id, corpus_id=corpus_id)
        self.token.authorize_read(pair)
        bounded_limit = max(1, min(limit, 50))
        if filters is not None and filters.exact_refs:
            return self._search_exact_refs(
                filters.exact_refs,
                query=query,
                tenant_id=tenant_id,
                corpus_id=corpus_id,
                limit=bounded_limit,
            )

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

    def build_packet(
        self,
        query: str,
        *,
        budget: int,
        tenant_id: str,
        corpus_id: str,
        filters: MemorySearchFilters | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a bounded, cited Striatum memory packet and persist its audit."""
        pair = TenantCorpus(tenant_id=tenant_id, corpus_id=corpus_id)
        self.token.authorize_read(pair)

        packet_id = str(uuid.uuid4())
        bounded_budget = max(0, int(budget))
        search_filters = coerce_memory_search_filters(filters)
        hits = self.search(
            query,
            tenant_id=tenant_id,
            corpus_id=corpus_id,
            limit=PACKET_RETRIEVAL_LIMIT,
            filters=search_filters,
        )

        selected: list[dict[str, Any]] = []
        omitted: list[dict[str, Any]] = []
        audit_selected: list[dict[str, Any]] = []
        audit_omitted: list[dict[str, Any]] = []
        seen_references: set[str] = set()
        remaining_budget = bounded_budget

        for index, hit in enumerate(hits, start=1):
            candidate_id = f"candidate-{index:04d}"
            citation = build_packet_citation(hit)
            generation_id = active_generation_id_for_reference(
                self.conn,
                reference_id=str(hit["reference_id"]),
                tenant_id=tenant_id,
                corpus_id=corpus_id,
            )
            audit_entry = build_packet_audit_entry(
                candidate_id=candidate_id,
                hit=hit,
                generation_id=generation_id,
                rank=index,
                selected=False,
                reason="",
            )
            estimated_cost = estimate_packet_item_cost(hit, citation)
            reason: str | None = None
            if str(hit["reference_id"]) in seen_references:
                reason = "duplicate"
            elif estimated_cost > remaining_budget:
                reason = "over_budget"

            if reason is not None:
                audit_entry["reason"] = reason
                omitted.append(
                    {
                        "candidate_id": candidate_id,
                        "selected": False,
                        "reason": reason,
                        "reference_id": hit["reference_id"],
                        "score": hit["score"],
                        "freshness": hit["freshness"],
                        "privacy_tier": hit["privacy_tier"],
                    }
                )
                audit_omitted.append(audit_entry)
                continue

            seen_references.add(str(hit["reference_id"]))
            remaining_budget -= estimated_cost
            item = {
                "candidate_id": candidate_id,
                "reference_id": hit["reference_id"],
                "content": hit["content"],
                "score": hit["score"],
                "privacy_tier": hit["privacy_tier"],
                "freshness": hit["freshness"],
                "dirty_working_tree": hit["dirty_working_tree"],
                "citation": citation,
            }
            selected.append(item)
            audit_entry["selected"] = True
            audit_selected.append(audit_entry)

        packet_generation_id = first_generation_id(
            [*audit_selected, *audit_omitted]
        ) or active_generation_id_for_pair(
            self.conn,
            tenant_id=tenant_id,
            corpus_id=corpus_id,
        )
        status = "available" if selected else "no_data"
        packet = {
            "packet_id": packet_id,
            "policy": PACKET_POLICY_VERSION,
            "query": query,
            "budget": bounded_budget,
            "tenant_id": tenant_id,
            "corpus_id": corpus_id,
            "status": status,
            "generation_id": packet_generation_id,
            "selected": selected,
            "omitted": omitted,
            "citations": [item["citation"] for item in selected],
            "omission_reason_vocabulary": sorted(OMISSION_REASONS),
        }
        insert_packet_audit(
            self.conn,
            packet_id=packet_id,
            generation_id=packet_generation_id,
            tenant_id=tenant_id,
            corpus_id=corpus_id,
            query=query,
            budget=bounded_budget,
            filters=search_filters,
            status="ok" if selected else "no_data",
            selected=audit_selected,
            omitted=audit_omitted,
        )
        return packet

    def _search_exact_refs(
        self,
        exact_refs: Sequence[ExactRefFilter],
        *,
        query: str,
        tenant_id: str,
        corpus_id: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Search projected Striatum and project-execution references."""
        normalized_refs = normalize_exact_refs(exact_refs)
        if not normalized_refs:
            return []
        striatum_hits = self._search_striatum_exact_refs(
            normalized_refs,
            query=query,
            tenant_id=tenant_id,
            corpus_id=corpus_id,
            limit=limit,
        )
        project_hits = self._search_project_execution_exact_refs(
            normalized_refs,
            tenant_id=tenant_id,
            corpus_id=corpus_id,
            limit=limit,
        )
        combined = list(striatum_hits) + list(project_hits)
        combined.sort(key=lambda hit: (-int(hit.get("score") or 0), hit.get("external_id") or ""))
        return combined[:limit]

    def _search_striatum_exact_refs(
        self,
        normalized_refs: Sequence[ExactRefFilter],
        *,
        query: str,
        tenant_id: str,
        corpus_id: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Search projected Striatum references inside one authorized boundary."""
        if not normalized_refs:
            return []

        projection_columns = table_columns(self.conn, "striatum_references")
        if not projection_columns:
            raise MemoryReferenceError("striatum_references projection table is unavailable")
        capture_column = projection_capture_id_column(projection_columns)
        dirty_expression = (
            "bool_or(r.source_dirty_working_tree)"
            if "source_dirty_working_tree" in projection_columns
            else "NULL::boolean"
        )
        freshness_expression = (
            "array_remove(array_agg(DISTINCT r.freshness), NULL)"
            if "freshness" in projection_columns
            else "ARRAY[]::text[]"
        )
        raw_payload_expression = (
            "array_remove(array_agg(r.raw_payload), NULL)"
            if "raw_payload" in projection_columns
            else "ARRAY[]::jsonb[]"
        )
        active_clause = "AND r.is_active = true" if "is_active" in projection_columns else ""

        ref_kinds = [item.ref_kind for item in normalized_refs]
        ref_values = [item.ref_value for item in normalized_refs]
        rows = self.conn.execute(
            f"""
            WITH requested(ref_kind, ref_value_normalized) AS (
                SELECT * FROM unnest(%s::text[], %s::text[])
            ),
            matched_refs AS (
                SELECT
                    r.{capture_column} AS capture_id,
                    {dirty_expression} AS projection_dirty_working_tree,
                    {freshness_expression} AS projection_freshness_values,
                    {raw_payload_expression} AS projection_payloads
                FROM striatum_references r
                JOIN requested q
                  ON q.ref_kind = r.ref_kind
                 AND q.ref_value_normalized = r.ref_value_normalized
                WHERE r.tenant_id = %s
                  AND r.corpus_id = %s
                  {active_clause}
                GROUP BY r.{capture_column}
            )
            SELECT
                c.id::text,
                c.tenant_id,
                c.corpus_id,
                c.source_kind::text,
                c.external_id,
                c.privacy_tier,
                COALESCE(c.content_text, ''),
                c.raw_payload,
                c.observed_at,
                c.imported_at,
                matched_refs.projection_dirty_working_tree,
                matched_refs.projection_freshness_values,
                matched_refs.projection_payloads
            FROM matched_refs
            JOIN captures c ON c.id = matched_refs.capture_id
            WHERE c.tenant_id = %s
              AND c.corpus_id = %s
              AND c.source_kind::text = 'striatum'
            ORDER BY c.imported_at DESC, c.external_id
            LIMIT 1000
            """,
            (ref_kinds, ref_values, tenant_id, corpus_id, tenant_id, corpus_id),
        ).fetchall()

        tokens = tokenize(query)
        hits = [build_exact_ref_search_hit(row, query=query, tokens=tokens) for row in rows]
        hits.sort(key=lambda item: (-item.score, item.external_id))
        return [hit.to_json() for hit in hits[:limit]]

    def _search_project_execution_exact_refs(
        self,
        normalized_refs: Sequence[ExactRefFilter],
        *,
        tenant_id: str,
        corpus_id: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Search git/build-artifact projections by exact ref kind.

        Returns a list of hits shaped like the Striatum exact-ref path
        (id, tenant_id, corpus_id, source_kind, external_id, content,
        observed_at, imported_at, score, freshness). RFC 0050 Layer 5.
        """
        hits: list[dict[str, Any]] = []
        for ref in normalized_refs:
            if ref.ref_kind == "commit_sha":
                hits.extend(self._lookup_git_commits(ref.ref_value, tenant_id, corpus_id))
            elif ref.ref_kind == "source_hash":
                hits.extend(
                    self._lookup_build_artifacts_by_hash(
                        ref.ref_value, tenant_id, corpus_id
                    )
                )
            elif ref.ref_kind == "run_id":
                hits.extend(
                    self._lookup_build_artifacts_by_run(
                        ref.ref_value, tenant_id, corpus_id
                    )
                )
            elif ref.ref_kind == "path":
                hits.extend(
                    self._lookup_markdown_files_by_path(
                        ref.ref_value, tenant_id, corpus_id
                    )
                )
        return hits[:limit]

    def _lookup_git_commits(
        self, sha: str, tenant_id: str, corpus_id: str
    ) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT id::text, tenant_id, corpus_id, repository_id, commit_sha,
                   subject, committer_date, imported_at, refs, content_hash
            FROM git_commits
            WHERE tenant_id = %s
              AND corpus_id = %s
              AND commit_sha = %s
            ORDER BY committer_date DESC
            """,
            (tenant_id, corpus_id, sha.lower()),
        ).fetchall()
        return [
            {
                "id": row[0],
                "tenant_id": row[1],
                "corpus_id": row[2],
                "source_kind": "git",
                "external_id": f"{row[3]}:{row[4]}",
                "content": row[5] or "",
                "observed_at": format_datetime(row[6]),
                "imported_at": format_datetime(row[7]),
                "score": 100,
                "freshness": "fresh",
                "dirty_working_tree": False,
                "raw_payload": {"refs": list(row[8] or []), "content_hash": row[9]},
            }
            for row in rows
        ]

    def _lookup_build_artifacts_by_hash(
        self, content_hash: str, tenant_id: str, corpus_id: str
    ) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT id::text, tenant_id, corpus_id, artifact_root_id, relative_path,
                   artifact_kind, imported_at, content_hash, sensitivity_class
            FROM build_artifacts
            WHERE tenant_id = %s
              AND corpus_id = %s
              AND content_hash = %s
            ORDER BY imported_at DESC
            """,
            (tenant_id, corpus_id, content_hash.lower()),
        ).fetchall()
        return [
            {
                "id": row[0],
                "tenant_id": row[1],
                "corpus_id": row[2],
                "source_kind": "build_artifact",
                "external_id": f"{row[3]}:{row[4]}",
                "content": "",
                "observed_at": None,
                "imported_at": format_datetime(row[6]),
                "score": 100,
                "freshness": "fresh",
                "dirty_working_tree": False,
                "raw_payload": {
                    "artifact_kind": row[5],
                    "content_hash": row[7],
                    "sensitivity_class": row[8],
                },
            }
            for row in rows
        ]

    def _lookup_build_artifacts_by_run(
        self, run_id: str, tenant_id: str, corpus_id: str
    ) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT id::text, tenant_id, corpus_id, artifact_root_id, relative_path,
                   artifact_kind, imported_at, content_hash, run_id
            FROM build_artifacts
            WHERE tenant_id = %s
              AND corpus_id = %s
              AND run_id = %s
            ORDER BY imported_at DESC
            """,
            (tenant_id, corpus_id, run_id),
        ).fetchall()
        return [
            {
                "id": row[0],
                "tenant_id": row[1],
                "corpus_id": row[2],
                "source_kind": "build_artifact",
                "external_id": f"{row[3]}:{row[4]}",
                "content": "",
                "observed_at": None,
                "imported_at": format_datetime(row[6]),
                "score": 100,
                "freshness": "fresh",
                "dirty_working_tree": False,
                "raw_payload": {
                    "artifact_kind": row[5],
                    "content_hash": row[7],
                    "run_id": row[8],
                },
            }
            for row in rows
        ]

    def _lookup_markdown_files_by_path(
        self, path: str, tenant_id: str, corpus_id: str
    ) -> list[dict[str, Any]]:
        # ``path`` is already normalized (lowercased, forward-slashed) by
        # ``normalize_ref_value``; match case-insensitively against the
        # stored relative_path so authors can cite README.md or readme.md
        # interchangeably.
        rows = self.conn.execute(
            """
            SELECT id::text, tenant_id, corpus_id, markdown_root_id, relative_path,
                   title, content_hash, imported_at
            FROM markdown_files
            WHERE tenant_id = %s
              AND corpus_id = %s
              AND lower(relative_path) = %s
              AND superseded_at IS NULL
            ORDER BY imported_at DESC
            """,
            (tenant_id, corpus_id, path),
        ).fetchall()
        return [
            {
                "id": row[0],
                "tenant_id": row[1],
                "corpus_id": row[2],
                "source_kind": "markdown_tree",
                "external_id": f"{row[3]}:{row[4]}",
                "content": row[5] or "",
                "observed_at": None,
                "imported_at": format_datetime(row[7]),
                "score": 100,
                "freshness": "fresh",
                "dirty_working_tree": False,
                "raw_payload": {"content_hash": row[6]},
            }
            for row in rows
        ]

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
        projection_active_count = active_projection_capture_count(
            self.conn,
            tenant_id=tenant_id,
            corpus_id=corpus_id,
        )
        return {
            "tenant_id": tenant_id,
            "corpus_id": corpus_id,
            "record_count": int(metadata[0] or 0),
            "projection_active_count": projection_active_count,
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
    dirty_working_tree, freshness = freshness_from_payloads([raw_payload])
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
        dirty_working_tree=dirty_working_tree,
        freshness=freshness,
    )


def active_projection_capture_count(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
) -> int:
    """Return active projected capture coverage for one tenant/corpus."""
    table_row = conn.execute("SELECT to_regclass('public.striatum_references')").fetchone()
    if table_row is None or table_row[0] is None:
        return 0
    row = conn.execute(
        """
        SELECT count(DISTINCT capture_id)::int
        FROM striatum_references
        WHERE tenant_id = %s
          AND corpus_id = %s
          AND is_active = true
        """,
        (tenant_id, corpus_id),
    ).fetchone()
    if row is None:
        return 0
    return int(row[0] or 0)


def build_exact_ref_search_hit(
    row: tuple[Any, ...],
    *,
    query: str,
    tokens: list[str],
) -> SearchHit:
    """Build a search hit from a projected exact-reference match."""
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
    lexical_score = score_text(haystack, query=query, tokens=tokens) if tokens else 0.0
    score = round(10.0 + lexical_score, 4)
    projection_payloads = [item for item in (row[12] or []) if isinstance(item, dict)]
    dirty_working_tree, freshness = freshness_from_payloads(
        [raw_payload, *projection_payloads],
        projection_dirty_working_tree=row[10],
        projection_freshness_values=row[11] or [],
    )
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
        dirty_working_tree=dirty_working_tree,
        freshness=freshness,
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


def normalize_exact_refs(exact_refs: Sequence[ExactRefFilter]) -> list[ExactRefFilter]:
    """Validate and normalize exact-reference filters for projection lookup."""
    normalized: list[ExactRefFilter] = []
    for exact_ref in exact_refs:
        ref_kind = exact_ref.ref_kind.strip().lower()
        if ref_kind not in EXACT_REF_KINDS:
            raise MemoryReferenceError(f'unsupported exact ref_kind "{exact_ref.ref_kind}"')
        ref_value = normalize_ref_value(ref_kind, exact_ref.ref_value)
        if not ref_value:
            raise MemoryReferenceError("exact ref_value must be non-empty")
        normalized.append(ExactRefFilter(ref_kind=ref_kind, ref_value=ref_value))
    return normalized


def coerce_memory_search_filters(
    filters: MemorySearchFilters | dict[str, Any] | None,
) -> MemorySearchFilters | None:
    """Return typed search filters from API-shaped JSON input."""
    if filters is None or isinstance(filters, MemorySearchFilters):
        return filters
    exact_refs_value = filters.get("exact_refs")
    if exact_refs_value is None:
        return MemorySearchFilters()
    if not isinstance(exact_refs_value, Sequence) or isinstance(exact_refs_value, (str, bytes)):
        raise MemoryReferenceError("filters.exact_refs must be a list")
    exact_refs: list[ExactRefFilter] = []
    for item in exact_refs_value:
        if not isinstance(item, dict):
            raise MemoryReferenceError("filters.exact_refs entries must be objects")
        ref_kind = item.get("ref_kind")
        ref_value = item.get("ref_value")
        if not isinstance(ref_kind, str) or not isinstance(ref_value, str):
            raise MemoryReferenceError("filters.exact_refs entries require ref_kind and ref_value")
        exact_refs.append(ExactRefFilter(ref_kind=ref_kind, ref_value=ref_value))
    return MemorySearchFilters(exact_refs=tuple(exact_refs))


def memory_search_filters_to_json(filters: MemorySearchFilters | None) -> dict[str, Any]:
    """Return audit-safe JSON for packet search filters."""
    if filters is None:
        return {}
    return {
        "exact_refs": [
            {"ref_kind": exact_ref.ref_kind, "ref_value": exact_ref.ref_value}
            for exact_ref in filters.exact_refs
        ]
    }


def normalize_ref_value(ref_kind: str, value: str) -> str:
    """Normalize a projected exact-reference value for lookup."""
    normalized = " ".join(value.strip().split())
    if ref_kind in {"path", "logical_path"}:
        return normalized.replace("\\", "/").lower()
    if ref_kind == "commit_sha":
        return normalized.lower()
    if ref_kind == "rfc_id":
        match = RFC_ID_PATTERN.search(normalized)
        if match is not None:
            return f"rfc {int(match.group(1)):04d}"
        return normalized.lower()
    if ref_kind == "decision_id":
        match = DECISION_ID_PATTERN.search(normalized)
        if match is not None:
            return match.group(1).upper()
        return normalized.upper()
    return normalized.lower()


def build_packet_citation(hit: dict[str, Any]) -> dict[str, Any]:
    """Build the cited memory item shape for one retrieval hit."""
    provenance = dict(hit.get("provenance") or {})
    return {
        "tenant_id": hit["tenant_id"],
        "corpus_id": hit["corpus_id"],
        "source_kind": hit["source_kind"],
        "sub_kind": hit["sub_kind"],
        "external_id": hit["external_id"],
        "reference_id": hit["reference_id"],
        "path": provenance.get("path") or provenance.get("logical_path"),
        "lines": provenance.get("lines") or provenance.get("line_range"),
        "bundle": provenance.get("bundle_id"),
        "authority": provenance.get("authority_class"),
        "stability": provenance.get("stability_class"),
        "confidence": provenance.get("confidence"),
        "freshness": hit["freshness"],
        "dirty_working_tree": hit["dirty_working_tree"],
    }


def estimate_packet_item_cost(hit: dict[str, Any], citation: dict[str, Any]) -> int:
    """Estimate a packet item's budget cost using a stable local approximation."""
    content_cost = max(1, len(str(hit.get("content") or "").split()))
    citation_cost = max(1, len(json.dumps(citation, sort_keys=True).split()))
    return content_cost + citation_cost


def build_packet_audit_entry(
    *,
    candidate_id: str,
    hit: dict[str, Any],
    generation_id: str | None,
    rank: int,
    selected: bool,
    reason: str,
) -> dict[str, Any]:
    """Build a privacy-safe packet audit entry without raw memory content."""
    if reason and reason not in OMISSION_REASONS:
        raise MemoryReferenceError(f'unsupported omission reason "{reason}"')
    return {
        "candidate_id": candidate_id,
        "selected": selected,
        "reason": reason,
        "lineage": {
            "retrieval_lane": "exact_reference",
            "projection_family": "striatum_references",
            "projection_generation_id": generation_id,
            "reference_id": hit["reference_id"],
            "source_kind": hit["source_kind"],
        },
        "ranking": {
            "rank": rank,
            "score": hit["score"],
            "ranking_profile": "memory_packet.v1",
        },
        "labels": {
            "freshness": hit["freshness"],
            "privacy_tier": hit["privacy_tier"],
            "redaction_state": "none",
        },
    }


def active_generation_id_for_reference(
    conn: psycopg.Connection,
    *,
    reference_id: str,
    tenant_id: str,
    corpus_id: str,
) -> str | None:
    """Return the active projection generation for a packet candidate when present."""
    table, row_id = decode_reference_id(reference_id)
    if table != "captures":
        return None
    if not table_columns(conn, "striatum_references"):
        return None
    row = conn.execute(
        """
        SELECT generation_id::text
        FROM striatum_references
        WHERE capture_id = %s
          AND tenant_id = %s
          AND corpus_id = %s
          AND is_active = true
        ORDER BY observed_at DESC, id::text
        LIMIT 1
        """,
        (row_id, tenant_id, corpus_id),
    ).fetchone()
    if row is None:
        return None
    return str(row[0])


def active_generation_id_for_pair(
    conn: psycopg.Connection,
    *,
    tenant_id: str,
    corpus_id: str,
) -> str | None:
    """Return the active Striatum projection generation for one pair."""
    if not table_columns(conn, "striatum_projection_generations"):
        return None
    row = conn.execute(
        """
        SELECT id::text
        FROM striatum_projection_generations
        WHERE tenant_id = %s
          AND corpus_id = %s
          AND status = 'activated'
          AND superseded_at IS NULL
        ORDER BY activated_at DESC NULLS LAST, started_at DESC
        LIMIT 1
        """,
        (tenant_id, corpus_id),
    ).fetchone()
    if row is None:
        return None
    return str(row[0])


def first_generation_id(entries: Sequence[dict[str, Any]]) -> str | None:
    """Return the first projection generation id present in audit entries."""
    for entry in entries:
        lineage = entry.get("lineage")
        if not isinstance(lineage, dict):
            continue
        generation_id = lineage.get("projection_generation_id")
        if isinstance(generation_id, str) and generation_id:
            return generation_id
    return None


def insert_packet_audit(
    conn: psycopg.Connection,
    *,
    packet_id: str,
    generation_id: str | None,
    tenant_id: str,
    corpus_id: str,
    query: str,
    budget: int,
    filters: MemorySearchFilters | None,
    status: str,
    selected: list[dict[str, Any]],
    omitted: list[dict[str, Any]],
) -> None:
    """Persist the privacy-safe packet audit row."""
    columns = table_columns(conn, "striatum_packet_audits")
    if not columns:
        raise MemoryReferenceError("striatum_packet_audits table is unavailable")
    required = {"packet_id", "generation_id", "query", "budget", "selected", "omitted"}
    missing = required - columns
    if missing:
        raise MemoryReferenceError(
            f"striatum_packet_audits missing columns: {', '.join(sorted(missing))}"
        )
    if {"tenant_id", "corpus_id", "policy_version", "purpose", "status", "filters"} <= columns:
        if generation_id is None:
            raise MemoryReferenceError("packet audit requires a projection generation id")
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
                budget,
                filters,
                selected,
                omitted
            )
            VALUES (%s, %s, %s, %s, %s, 'packet_prepare', %s, %s, %s, %s, %s, %s)
            """,
            (
                packet_id,
                generation_id,
                tenant_id,
                corpus_id,
                PACKET_POLICY_VERSION,
                status,
                query,
                Jsonb({"max_tokens": budget}),
                Jsonb(memory_search_filters_to_json(filters)),
                Jsonb(selected),
                Jsonb(omitted),
            ),
        )
        return
    conn.execute(
        """
        INSERT INTO striatum_packet_audits (
            packet_id,
            generation_id,
            query,
            budget,
            selected,
            omitted
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (packet_id, generation_id, query, budget, Jsonb(selected), Jsonb(omitted)),
    )


def table_columns(conn: psycopg.Connection, table_name: str) -> set[str]:
    """Return public table columns visible to the current connection."""
    rows = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = ANY(current_schemas(true))
          AND table_name = %s
        """,
        (table_name,),
    ).fetchall()
    return {str(row[0]) for row in rows}


def projection_capture_id_column(projection_columns: set[str]) -> str:
    """Return the supported capture-id column for the projection table."""
    if "source_capture_id" in projection_columns:
        return "source_capture_id"
    if "capture_id" in projection_columns:
        return "capture_id"
    raise MemoryReferenceError("striatum_references has no capture id column")


def freshness_from_payloads(
    payloads: Sequence[dict[str, Any]],
    *,
    projection_dirty_working_tree: bool | None = None,
    projection_freshness_values: Sequence[str] = (),
) -> tuple[bool, str]:
    """Derive conservative dirty/freshness labels from source metadata."""
    dirty_known = projection_dirty_working_tree is not None
    dirty_working_tree = bool(projection_dirty_working_tree)
    freshness: str | None = None
    for value in projection_freshness_values:
        if value in FRESHNESS_VALUES and value != "unknown":
            freshness = value
            break
    for payload in payloads:
        payload_dirty, payload_dirty_known = payload_dirty_working_tree(payload)
        dirty_known = dirty_known or payload_dirty_known
        dirty_working_tree = dirty_working_tree or payload_dirty
        payload_freshness = payload_freshness_value(payload)
        if payload_freshness is not None and payload_freshness != "unknown":
            freshness = payload_freshness
    if dirty_working_tree:
        return True, "dirty_working_tree"
    if freshness is not None:
        return False, freshness
    if dirty_known:
        return False, "fresh"
    return False, "unknown"


def payload_dirty_working_tree(payload: dict[str, Any]) -> tuple[bool, bool]:
    """Return dirty working-tree value plus whether source metadata carried it."""
    provenance = payload.get("provenance")
    payloads = [payload]
    if isinstance(provenance, dict):
        payloads.append(provenance)
    for item in payloads:
        for key in ("dirty_working_tree", "source_dirty_working_tree", "git_dirty"):
            if key in item:
                return bool(item[key]), True
    return False, False


def payload_freshness_value(payload: dict[str, Any]) -> str | None:
    """Return a valid source freshness label when present."""
    for key in ("freshness", "freshness_status"):
        value = payload.get(key)
        if isinstance(value, str) and value in FRESHNESS_VALUES:
            return value
    return None


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
