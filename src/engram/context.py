from __future__ import annotations

import json
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from engram.events import insert_memory_event
from engram.policy import PolicyActor, PolicyRequest, decide_policy

CONTEXT_COMPILER_VERSION = "context_for.v1.phase4.minimal"
CONTEXT_SNAPSHOT_PACKAGE_VERSION = "context_snapshot.package.v1"
DEFAULT_CONTEXT_TENANT_ID = "personal"
DEFAULT_CONTEXT_CORPUS_ID = "personal"
DEFAULT_CONTEXT_WORD_BUDGET = 500
DEFAULT_PRIVACY_TIER_CEILING = 1
MAX_CONTEXT_CANDIDATES_PER_LANE = 20

TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_\-:#./]+", re.IGNORECASE)
UUID_PATTERN = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)

# JSONB payloads can contain nested scalar/list/object values from source rows.
JsonObject = dict[str, Any]


class ContextForError(RuntimeError):
    """Base error for context compilation failures."""


@dataclass(frozen=True)
class ContextForRequest:
    """Input contract for the minimal personal context compiler."""

    query_text: str
    conversation_id: str | None = None
    tenant_id: str = DEFAULT_CONTEXT_TENANT_ID
    corpus_id: str = DEFAULT_CONTEXT_CORPUS_ID
    word_budget: int = DEFAULT_CONTEXT_WORD_BUDGET
    privacy_tier_ceiling: int = DEFAULT_PRIVACY_TIER_CEILING


@dataclass(frozen=True)
class ContextCitation:
    """One cited source row used by a rendered context item."""

    citation_id: str
    target_table: str
    target_id: str
    source_kind: str
    external_id: str | None = None
    observed_at: str | None = None
    confidence: float | None = None
    provenance: JsonObject = field(default_factory=dict)

    def to_json(self) -> JsonObject:
        """Return the JSON-safe citation shape."""
        return {
            "citation_id": self.citation_id,
            "target_table": self.target_table,
            "target_id": self.target_id,
            "source_kind": self.source_kind,
            "external_id": self.external_id,
            "observed_at": self.observed_at,
            "confidence": self.confidence,
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class ContextSection:
    """One rendered section in a context package."""

    title: str
    lane: str
    items: tuple[str, ...]
    truncated: bool = False

    def to_json(self) -> JsonObject:
        """Return the JSON-safe section shape."""
        return {
            "title": self.title,
            "lane": self.lane,
            "items": list(self.items),
            "truncated": self.truncated,
        }


@dataclass(frozen=True)
class ContextOmission:
    """One candidate that was intentionally not rendered."""

    candidate_id: str
    lane: str
    reason: str
    target_table: str
    target_id: str
    privacy_tier: int | None = None
    policy_action: str | None = None
    sensitivity_class: str | None = None

    def to_json(self) -> JsonObject:
        """Return the JSON-safe omission shape."""
        return {
            "candidate_id": self.candidate_id,
            "lane": self.lane,
            "reason": self.reason,
            "target_table": self.target_table,
            "target_id": self.target_id,
            "privacy_tier": self.privacy_tier,
            "policy_action": self.policy_action,
            "sensitivity_class": self.sensitivity_class,
        }


@dataclass(frozen=True)
class ContextForResult:
    """Output contract for a compiled context package."""

    context_id: str
    compiler_version: str
    status: str
    sections: tuple[ContextSection, ...]
    citations: tuple[ContextCitation, ...]
    omissions: tuple[ContextOmission, ...]
    source_belief_ids: tuple[str, ...]
    source_segment_ids: tuple[str, ...]
    source_reference_ids: tuple[str, ...]
    rendered_context: str
    snapshot_id: str | None = None
    memory_epoch: int | None = None
    request_hash: str | None = None

    def to_json(self) -> JsonObject:
        """Return the JSON-safe context package."""
        return {
            "context_id": self.context_id,
            "compiler_version": self.compiler_version,
            "status": self.status,
            "sections": [section.to_json() for section in self.sections],
            "citations": [citation.to_json() for citation in self.citations],
            "omissions": [omission.to_json() for omission in self.omissions],
            "source_belief_ids": list(self.source_belief_ids),
            "source_segment_ids": list(self.source_segment_ids),
            "source_reference_ids": list(self.source_reference_ids),
            "rendered_context": self.rendered_context,
            "snapshot_id": self.snapshot_id,
            "memory_epoch": self.memory_epoch,
            "request_hash": self.request_hash,
        }


@dataclass(frozen=True)
class _ContextCandidate:
    candidate_id: str
    lane: str
    section_title: str
    priority: int
    target_table: str
    target_id: str
    privacy_tier: int
    sensitivity_class: str
    source_kind: str
    tenant_id: str
    corpus_id: str
    text: str
    sort_key: tuple[Any, ...]
    citation: ContextCitation | None = None
    belief_id: str | None = None
    evidence_ids: tuple[str, ...] = ()
    reference_id: str | None = None


class PersonalContextService:
    """Service for compiling and snapshotting minimal personal context packages."""

    def __init__(self, conn: psycopg.Connection) -> None:
        self.conn = conn

    def context_for(self, request: ContextForRequest | str) -> ContextForResult:
        """Compile a deterministic, sectioned personal context package."""
        compiled_request = (
            ContextForRequest(query_text=request) if isinstance(request, str) else request
        )
        self._validate_request(compiled_request)
        cached = self.lookup_context_snapshot(compiled_request)
        if cached is not None:
            return cached
        result = self._compile_context(compiled_request)
        return self.persist_context_snapshot(compiled_request, result)

    def lookup_context_snapshot(self, request: ContextForRequest) -> ContextForResult | None:
        """Return the latest matching clean snapshot for a request, if one exists."""
        request_payload = snapshot_request_payload(request)
        scope_type, scope_key = snapshot_scope(request)
        row = self.conn.execute(
            """
            SELECT id::text, memory_epoch, compiler_version, package_json, rendered_text
            FROM context_snapshots
            WHERE tenant_id = %s
              AND corpus_id = %s
              AND scope_type = %s
              AND scope_key = %s
              AND compiler_version = %s
              AND is_dirty = false
              AND package_json->'snapshot_request'->>'request_hash' = %s
              AND package_json->'snapshot_request'->>'package_version' = %s
            ORDER BY memory_epoch DESC, created_at DESC, id DESC
            LIMIT 1
            """,
            (
                request.tenant_id,
                request.corpus_id,
                scope_type,
                scope_key,
                CONTEXT_COMPILER_VERSION,
                str(request_payload["request_hash"]),
                CONTEXT_SNAPSHOT_PACKAGE_VERSION,
            ),
        ).fetchone()
        if row is None:
            return None
        package_json = row[3]
        if not isinstance(package_json, Mapping):
            raise ContextForError("snapshot package_json must be an object")
        return context_result_from_json(
            package_json,
            snapshot_id=str(row[0]),
            memory_epoch=int(row[1]),
            compiler_version=str(row[2]),
            rendered_text=str(row[4]),
            request_hash=str(request_payload["request_hash"]),
        )

    def persist_context_snapshot(
        self,
        request: ContextForRequest,
        result: ContextForResult,
    ) -> ContextForResult:
        """Insert a refreshed snapshot event and append-only snapshot row."""
        request_payload = snapshot_request_payload(request)
        scope_type, scope_key = snapshot_scope(request)
        snapshot_id = str(uuid.uuid4())
        request_uuid = str(uuid.uuid4())
        with self.conn.transaction():
            event = insert_memory_event(
                self.conn,
                event_type="context_snapshot_refreshed",
                aggregate_type="context_snapshot",
                aggregate_id=snapshot_id,
                tenant_id=request.tenant_id,
                corpus_id=request.corpus_id,
                scope_type=scope_type,
                scope_key=scope_key,
                payload={
                    "compiler_version": CONTEXT_COMPILER_VERSION,
                    "request_hash": request_payload["request_hash"],
                    "request_uuid": request_uuid,
                },
            )
            persisted = with_snapshot_metadata(
                result,
                snapshot_id=snapshot_id,
                memory_epoch=event.memory_epoch,
                request_hash=str(request_payload["request_hash"]),
            )
            package_json = persisted.to_json()
            package_json["snapshot_request"] = request_payload
            self.conn.execute(
                """
                INSERT INTO context_snapshots (
                    id,
                    tenant_id,
                    corpus_id,
                    scope_type,
                    scope_key,
                    memory_epoch,
                    compiler_version,
                    package_json,
                    rendered_text,
                    source_belief_ids,
                    source_segment_ids,
                    source_reference_ids,
                    omissions,
                    request_uuid
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s::uuid[],
                    %s::uuid[],
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    snapshot_id,
                    request.tenant_id,
                    request.corpus_id,
                    scope_type,
                    scope_key,
                    event.memory_epoch,
                    CONTEXT_COMPILER_VERSION,
                    Jsonb(package_json),
                    persisted.rendered_context,
                    list(persisted.source_belief_ids),
                    list(persisted.source_segment_ids),
                    list(persisted.source_reference_ids),
                    Jsonb([item.to_json() for item in persisted.omissions]),
                    request_uuid,
                ),
            )
        return persisted

    def _validate_request(self, request: ContextForRequest) -> None:
        query_text = request.query_text.strip()
        if query_text == "":
            raise ValueError("query_text must not be empty")
        if request.privacy_tier_ceiling < 0:
            raise ValueError("privacy_tier_ceiling must be >= 0")

    def _compile_context(self, compiled_request: ContextForRequest) -> ContextForResult:
        """Compile context from canonical rows without consulting snapshots."""
        query_text = compiled_request.query_text.strip()
        tokens = tokenize(query_text)
        candidates = self._collect_candidates(compiled_request, tokens)
        visible, omissions = self._apply_policy_and_pack(compiled_request, candidates)

        if not visible:
            visible.extend(self._gap_candidates(compiled_request, omissions))

        sections = build_sections(visible)
        citations = tuple(
            candidate.citation for candidate in visible if candidate.citation is not None
        )
        rendered_context = render_sections(sections)
        status = result_status(visible, omissions)
        source_belief_ids = sorted(
            {candidate.belief_id for candidate in visible if candidate.belief_id is not None}
        )
        source_segment_ids = self._source_segment_ids(source_belief_ids)
        source_reference_ids = sorted(
            {candidate.reference_id for candidate in visible if candidate.reference_id is not None}
        )
        return ContextForResult(
            context_id=str(uuid.uuid4()),
            compiler_version=CONTEXT_COMPILER_VERSION,
            status=status,
            sections=tuple(sections),
            citations=citations,
            omissions=tuple(omissions),
            source_belief_ids=tuple(source_belief_ids),
            source_segment_ids=tuple(source_segment_ids),
            source_reference_ids=tuple(source_reference_ids),
            rendered_context=rendered_context,
        )

    def _collect_candidates(
        self,
        request: ContextForRequest,
        tokens: set[str],
    ) -> list[_ContextCandidate]:
        candidates: list[_ContextCandidate] = []
        candidates.extend(self._pinned_belief_candidates(request))
        pinned_ids = {candidate.belief_id for candidate in candidates}
        candidates.extend(self._current_belief_candidates(request, tokens, pinned_ids))
        candidates.extend(self._historical_belief_candidates(request, tokens, pinned_ids))
        candidates.extend(self._recent_signal_candidates(request, tokens))
        candidates.extend(self._exact_reference_candidates(request))
        candidates.sort(key=lambda candidate: (candidate.priority, candidate.sort_key))
        return candidates

    def _pinned_belief_candidates(self, request: ContextForRequest) -> list[_ContextCandidate]:
        rows = self.conn.execute(
            """
            SELECT
                cb.id::text,
                cb.subject_text,
                cb.predicate,
                cb.object_text,
                cb.object_json,
                cb.status,
                cb.stability_class,
                cb.confidence,
                cb.evidence_ids,
                cb.privacy_tier,
                cb.raw_payload,
                pb.pinned_at
            FROM pinned_beliefs pb
            JOIN current_beliefs cb ON cb.id = pb.belief_id
            WHERE cb.tenant_id = %s
              AND cb.corpus_id = %s
            ORDER BY pb.pinned_at DESC, cb.id
            LIMIT %s
            """,
            (request.tenant_id, request.corpus_id, MAX_CONTEXT_CANDIDATES_PER_LANE),
        ).fetchall()
        return [
            self._belief_candidate(
                row,
                lane="pinned_beliefs",
                section_title="Standing Context",
                priority=10,
                prefix="Pinned",
                sort_key=(index,),
                tenant_id=request.tenant_id,
                corpus_id=request.corpus_id,
                privacy_tier_ceiling=request.privacy_tier_ceiling,
            )
            for index, row in enumerate(rows)
        ]

    def _current_belief_candidates(
        self,
        request: ContextForRequest,
        tokens: set[str],
        pinned_ids: set[str | None],
    ) -> list[_ContextCandidate]:
        rows = self.conn.execute(
            """
            SELECT
                id::text,
                subject_text,
                predicate,
                object_text,
                object_json,
                status,
                stability_class,
                confidence,
                evidence_ids,
                privacy_tier,
                raw_payload,
                observed_at
            FROM current_beliefs
            WHERE tenant_id = %s
              AND corpus_id = %s
            ORDER BY confidence DESC, observed_at DESC NULLS LAST, id
            LIMIT 200
            """,
            (request.tenant_id, request.corpus_id),
        ).fetchall()
        candidates: list[_ContextCandidate] = []
        for row in rows:
            belief_id = str(row[0])
            if belief_id in pinned_ids:
                continue
            score = lexical_score(tokens, belief_search_text(row))
            if tokens and score == 0:
                continue
            candidates.append(
                self._belief_candidate(
                    row,
                    lane="current_beliefs",
                    section_title="Relevant Beliefs",
                    priority=20,
                    prefix="Current",
                    sort_key=(-score, -(float(row[7]) if row[7] is not None else 0.0), belief_id),
                    tenant_id=request.tenant_id,
                    corpus_id=request.corpus_id,
                    privacy_tier_ceiling=request.privacy_tier_ceiling,
                )
            )
            if len(candidates) >= MAX_CONTEXT_CANDIDATES_PER_LANE:
                break
        return candidates

    def _historical_belief_candidates(
        self,
        request: ContextForRequest,
        tokens: set[str],
        excluded_ids: set[str | None],
    ) -> list[_ContextCandidate]:
        if not tokens:
            return []
        rows = self.conn.execute(
            """
            SELECT
                id::text,
                subject_text,
                predicate,
                object_text,
                object_json,
                status,
                stability_class,
                confidence,
                evidence_ids,
                privacy_tier,
                raw_payload,
                COALESCE(closed_at, valid_to, recorded_at, extracted_at) AS sort_at
            FROM beliefs
            WHERE tenant_id = %s
              AND corpus_id = %s
              AND (
                  valid_to IS NOT NULL
                  OR closed_at IS NOT NULL
                  OR superseded_by IS NOT NULL
                  OR status IN ('rejected', 'superseded')
              )
            ORDER BY sort_at DESC NULLS LAST, id
            LIMIT 200
            """,
            (request.tenant_id, request.corpus_id),
        ).fetchall()
        candidates: list[_ContextCandidate] = []
        for row in rows:
            belief_id = str(row[0])
            if belief_id in excluded_ids:
                continue
            score = lexical_score(tokens, belief_search_text(row))
            if score == 0:
                continue
            candidates.append(
                self._belief_candidate(
                    row,
                    lane="historical_beliefs",
                    section_title="Uncertain / Conflicting",
                    priority=60,
                    prefix="Historical, not current",
                    sort_key=(-score, belief_id),
                    tenant_id=request.tenant_id,
                    corpus_id=request.corpus_id,
                    privacy_tier_ceiling=request.privacy_tier_ceiling,
                )
            )
            if len(candidates) >= MAX_CONTEXT_CANDIDATES_PER_LANE:
                break
        return candidates

    def _recent_signal_candidates(
        self,
        request: ContextForRequest,
        tokens: set[str],
    ) -> list[_ContextCandidate]:
        rows = self.conn.execute(
            """
            SELECT
                id::text,
                source_kind::text,
                external_id,
                COALESCE(content_text, ''),
                observed_at,
                imported_at,
                privacy_tier,
                raw_payload,
                source_kind::text
            FROM captures
            WHERE tenant_id = %s
              AND corpus_id = %s
            ORDER BY COALESCE(observed_at, imported_at) DESC, id
            LIMIT 200
            """,
            (request.tenant_id, request.corpus_id),
        ).fetchall()
        candidates: list[_ContextCandidate] = []
        for row in rows:
            score = lexical_score(tokens, str(row[3]))
            if tokens and score == 0:
                continue
            capture_id = str(row[0])
            citation = ContextCitation(
                citation_id=reference_id("captures", capture_id),
                target_table="captures",
                target_id=capture_id,
                source_kind=str(row[1]),
                external_id=row[2],
                observed_at=format_datetime(row[4] or row[5]),
                provenance={
                    "target_table": "captures",
                    "capture_id": capture_id,
                    "source_kind": str(row[1]),
                },
            )
            text = f"{row[3]} (src=capture:{short_id(capture_id)})"
            candidates.append(
                _ContextCandidate(
                    candidate_id=f"recent:{capture_id}",
                    lane="recent_signals",
                    section_title="Recent Signals",
                    priority=40,
                    target_table="captures",
                    target_id=capture_id,
                    privacy_tier=int(row[6]),
                    sensitivity_class=sensitivity_class_from_payload(row[7]),
                    source_kind=str(row[8]),
                    tenant_id=request.tenant_id,
                    corpus_id=request.corpus_id,
                    text=text,
                    sort_key=(-score, capture_id),
                    citation=citation,
                    reference_id=reference_id("captures", capture_id),
                )
            )
            if len(candidates) >= MAX_CONTEXT_CANDIDATES_PER_LANE:
                break
        return candidates

    def _exact_reference_candidates(self, request: ContextForRequest) -> list[_ContextCandidate]:
        ref_ids = UUID_PATTERN.findall(request.query_text)
        if not ref_ids:
            return []
        message_rows = self.conn.execute(
            """
            SELECT
                id::text,
                source_kind::text,
                external_id,
                COALESCE(content_text, ''),
                created_at,
                privacy_tier,
                raw_payload,
                source_kind::text
            FROM messages
            WHERE tenant_id = %s
              AND corpus_id = %s
              AND id = ANY(%s::uuid[])
            ORDER BY created_at DESC NULLS LAST, id
            LIMIT %s
            """,
            (
                request.tenant_id,
                request.corpus_id,
                ref_ids,
                MAX_CONTEXT_CANDIDATES_PER_LANE,
            ),
        ).fetchall()
        candidates: list[_ContextCandidate] = []
        for row in message_rows:
            message_id = str(row[0])
            citation = ContextCitation(
                citation_id=reference_id("messages", message_id),
                target_table="messages",
                target_id=message_id,
                source_kind=str(row[1]),
                external_id=row[2],
                observed_at=format_datetime(row[4]),
            )
            candidates.append(
                _ContextCandidate(
                    candidate_id=f"message:{message_id}",
                    lane="exact_references",
                    section_title="Raw Evidence Snippets",
                    priority=30,
                    target_table="messages",
                    target_id=message_id,
                    privacy_tier=int(row[5]),
                    sensitivity_class=sensitivity_class_from_payload(row[6]),
                    source_kind=str(row[7]),
                    tenant_id=request.tenant_id,
                    corpus_id=request.corpus_id,
                    text=f"{row[3]} (src=message:{short_id(message_id)})",
                    sort_key=(message_id,),
                    citation=citation,
                    reference_id=reference_id("messages", message_id),
                )
            )
        return candidates

    def _belief_candidate(
        self,
        row: tuple[Any, ...],
        *,
        lane: str,
        section_title: str,
        priority: int,
        prefix: str,
        sort_key: tuple[Any, ...],
        tenant_id: str,
        corpus_id: str,
        privacy_tier_ceiling: int,
    ) -> _ContextCandidate:
        belief_id = str(row[0])
        confidence = float(row[7]) if row[7] is not None else None
        evidence_ids = tuple(str(item) for item in row[8])
        first_evidence_id = evidence_ids[0] if evidence_ids else None
        citation = self._message_citation(
            first_evidence_id,
            confidence=confidence,
            tenant_id=tenant_id,
            corpus_id=corpus_id,
            privacy_tier_ceiling=privacy_tier_ceiling,
        )
        source_tag = (
            f"message:{short_id(first_evidence_id)}"
            if citation is not None and first_evidence_id is not None
            else f"belief:{short_id(belief_id)}"
        )
        confidence_tag = f"conf={confidence:.2f}" if confidence is not None else "conf=unknown"
        rendered_belief = render_belief(
            prefix=prefix,
            subject=row[1],
            predicate=row[2],
            object_text=row[3],
            object_json=row[4],
            status=row[5],
            stability_class=row[6],
            confidence_tag=confidence_tag,
            source_tag=source_tag,
        )
        return _ContextCandidate(
            candidate_id=f"belief:{belief_id}",
            lane=lane,
            section_title=section_title,
            priority=priority,
            target_table="beliefs",
            target_id=belief_id,
            privacy_tier=int(row[9]),
            sensitivity_class=sensitivity_class_from_payload(row[10]),
            source_kind="belief",
            tenant_id=tenant_id,
            corpus_id=corpus_id,
            text=rendered_belief,
            sort_key=sort_key,
            citation=citation,
            belief_id=belief_id,
            evidence_ids=evidence_ids,
            reference_id=reference_id("beliefs", belief_id),
        )

    def _message_citation(
        self,
        message_id: str | None,
        *,
        confidence: float | None,
        tenant_id: str,
        corpus_id: str,
        privacy_tier_ceiling: int,
    ) -> ContextCitation | None:
        if message_id is None:
            return None
        row = self.conn.execute(
            """
            SELECT id::text, source_kind::text, external_id, created_at
            FROM messages
            WHERE id = %s
              AND tenant_id = %s
              AND corpus_id = %s
              AND privacy_tier <= %s
            """,
            (message_id, tenant_id, corpus_id, privacy_tier_ceiling),
        ).fetchone()
        if row is None:
            return None
        return ContextCitation(
            citation_id=reference_id("messages", str(row[0])),
            target_table="messages",
            target_id=str(row[0]),
            source_kind=str(row[1]),
            external_id=row[2],
            observed_at=format_datetime(row[3]),
            confidence=confidence,
            provenance={
                "target_table": "messages",
                "message_id": str(row[0]),
                "source_kind": str(row[1]),
            },
        )

    def _apply_policy_and_pack(
        self,
        request: ContextForRequest,
        candidates: list[_ContextCandidate],
    ) -> tuple[list[_ContextCandidate], list[ContextOmission]]:
        visible: list[_ContextCandidate] = []
        omissions: list[ContextOmission] = []
        remaining_budget = max(0, int(request.word_budget))
        actor = PolicyActor(
            actor_id=f"context_for:{request.tenant_id}:{request.corpus_id}",
            tenant_id=request.tenant_id,
            corpus_id=request.corpus_id,
            capabilities=frozenset(),
        )
        for candidate in candidates:
            policy_request = PolicyRequest(
                actor=actor,
                tenant_id=candidate.tenant_id,
                corpus_id=candidate.corpus_id,
                purpose="context",
                privacy_tier=candidate.privacy_tier,
                sensitivity_class=candidate.sensitivity_class,
                source_kind=candidate.source_kind,
                target_surface="context_for",
                privacy_tier_ceiling=request.privacy_tier_ceiling,
            )
            decision = decide_policy(policy_request)
            if decision.action in {"deny", "withhold"}:
                omissions.append(omission(candidate, decision.reason_code, decision.action))
                continue
            packed_candidate = candidate
            if decision.action == "cite_only":
                omissions.append(omission(candidate, decision.reason_code, decision.action))
                packed_candidate = cite_only_candidate(candidate)
            elif decision.action == "redact":
                omissions.append(omission(candidate, decision.reason_code, decision.action))
                packed_candidate = redact_candidate(candidate)
            cost = estimate_words(packed_candidate.text)
            if cost > remaining_budget:
                omissions.append(omission(packed_candidate, "over_budget"))
                continue
            visible.append(packed_candidate)
            remaining_budget -= cost
        return visible, omissions

    def _gap_candidates(
        self,
        request: ContextForRequest,
        omissions: list[ContextOmission],
    ) -> list[_ContextCandidate]:
        withheld = any(
            item.reason
            in {
                "privacy_tier_exceeded",
                "sensitivity_withheld",
                "cross_tenant_denied",
                "cross_corpus_denied",
            }
            for item in omissions
        )
        if withheld:
            if any(item.reason == "privacy_tier_exceeded" for item in omissions):
                text = (
                    "Matching personal memory exists but is withheld by the requested "
                    f"privacy tier ceiling ({request.privacy_tier_ceiling})."
                )
            else:
                text = "Matching personal memory exists but is withheld by context policy."
            status = "withheld"
        else:
            text = f'No matching personal memory found for query: "{request.query_text}".'
            status = "no_data"
        return [
            _ContextCandidate(
                candidate_id=f"gap:{status}",
                lane="gaps",
                section_title="Missing Data / Gaps",
                priority=100,
                target_table="none",
                target_id=status,
                privacy_tier=0,
                sensitivity_class="routine_project",
                source_kind="context_gap",
                tenant_id=request.tenant_id,
                corpus_id=request.corpus_id,
                text=text,
                sort_key=(status,),
            )
        ]

    def _source_segment_ids(self, source_belief_ids: list[str]) -> list[str]:
        if not source_belief_ids:
            return []
        rows = self.conn.execute(
            """
            SELECT DISTINCT c.segment_id::text
            FROM beliefs b
            JOIN claims c ON c.id = ANY(b.claim_ids)
            WHERE b.id = ANY(%s::uuid[])
              AND c.segment_id IS NOT NULL
            ORDER BY c.segment_id::text
            """,
            (source_belief_ids,),
        ).fetchall()
        return [str(row[0]) for row in rows]


def context_for(
    conn: psycopg.Connection,
    request: ContextForRequest | str,
) -> ContextForResult:
    """Compile context through the service-layer entry point."""
    return PersonalContextService(conn).context_for(request)


def snapshot_scope(request: ContextForRequest) -> tuple[str, str]:
    """Return the snapshot scope used for warm lookup and event rows."""
    if request.conversation_id:
        return "conversation", request.conversation_id
    return "user", f"{request.tenant_id}:{request.corpus_id}"


def snapshot_request_payload(request: ContextForRequest) -> JsonObject:
    """Return the stable request/policy fingerprint persisted with snapshots."""
    request_inputs: JsonObject = {
        "query_text": request.query_text.strip(),
        "conversation_id": request.conversation_id,
        "tenant_id": request.tenant_id,
        "corpus_id": request.corpus_id,
        "word_budget": int(request.word_budget),
        "privacy_tier_ceiling": int(request.privacy_tier_ceiling),
    }
    policy_inputs: JsonObject = {
        "target_surface": "context_for",
        "privacy_tier_ceiling": int(request.privacy_tier_ceiling),
    }
    fingerprint_payload: JsonObject = {
        "compiler_version": CONTEXT_COMPILER_VERSION,
        "request": request_inputs,
        "policy": policy_inputs,
    }
    request_hash = stable_json_hash(fingerprint_payload)
    return {
        "package_version": CONTEXT_SNAPSHOT_PACKAGE_VERSION,
        "request_hash": request_hash,
        "compiler_version": CONTEXT_COMPILER_VERSION,
        "request": request_inputs,
        "policy": policy_inputs,
    }


def stable_json_hash(payload: Mapping[str, Any]) -> str:
    """Return a deterministic SHA-256 hash for JSON-compatible input."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()


def with_snapshot_metadata(
    result: ContextForResult,
    *,
    snapshot_id: str,
    memory_epoch: int,
    request_hash: str,
) -> ContextForResult:
    """Return a context result carrying persisted snapshot metadata."""
    return ContextForResult(
        context_id=result.context_id,
        compiler_version=result.compiler_version,
        status=result.status,
        sections=result.sections,
        citations=result.citations,
        omissions=result.omissions,
        source_belief_ids=result.source_belief_ids,
        source_segment_ids=result.source_segment_ids,
        source_reference_ids=result.source_reference_ids,
        rendered_context=result.rendered_context,
        snapshot_id=snapshot_id,
        memory_epoch=memory_epoch,
        request_hash=request_hash,
    )


def context_result_from_json(
    payload: Mapping[str, Any],
    *,
    snapshot_id: str,
    memory_epoch: int,
    compiler_version: str,
    rendered_text: str,
    request_hash: str,
) -> ContextForResult:
    """Hydrate a context result from persisted snapshot package JSON."""
    sections = tuple(
        ContextSection(
            title=str(item.get("title", "")),
            lane=str(item.get("lane", "")),
            items=tuple(str(value) for value in item.get("items", ())),
            truncated=bool(item.get("truncated", False)),
        )
        for item in _mapping_sequence(payload.get("sections"))
    )
    citations = tuple(
        ContextCitation(
            citation_id=str(item.get("citation_id", "")),
            target_table=str(item.get("target_table", "")),
            target_id=str(item.get("target_id", "")),
            source_kind=str(item.get("source_kind", "")),
            external_id=_optional_str(item.get("external_id")),
            observed_at=_optional_str(item.get("observed_at")),
            confidence=_optional_float(item.get("confidence")),
            provenance=dict(item.get("provenance", {}))
            if isinstance(item.get("provenance"), Mapping)
            else {},
        )
        for item in _mapping_sequence(payload.get("citations"))
    )
    omissions = tuple(
        ContextOmission(
            candidate_id=str(item.get("candidate_id", "")),
            lane=str(item.get("lane", "")),
            reason=str(item.get("reason", "")),
            target_table=str(item.get("target_table", "")),
            target_id=str(item.get("target_id", "")),
            privacy_tier=_optional_int(item.get("privacy_tier")),
            policy_action=_optional_str(item.get("policy_action")),
            sensitivity_class=_optional_str(item.get("sensitivity_class")),
        )
        for item in _mapping_sequence(payload.get("omissions"))
    )
    return ContextForResult(
        context_id=str(payload.get("context_id") or snapshot_id),
        compiler_version=compiler_version,
        status=str(payload.get("status") or "ok"),
        sections=sections,
        citations=citations,
        omissions=omissions,
        source_belief_ids=tuple(str(value) for value in payload.get("source_belief_ids", ())),
        source_segment_ids=tuple(str(value) for value in payload.get("source_segment_ids", ())),
        source_reference_ids=tuple(
            str(value) for value in payload.get("source_reference_ids", ())
        ),
        rendered_context=str(payload.get("rendered_context") or rendered_text),
        snapshot_id=snapshot_id,
        memory_epoch=memory_epoch,
        request_hash=request_hash,
    )


def _mapping_sequence(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def tokenize(value: str) -> set[str]:
    """Return normalized lexical tokens for deterministic matching."""
    return {match.group(0).casefold() for match in TOKEN_PATTERN.finditer(value)}


def lexical_score(tokens: set[str], text: str) -> int:
    """Count query token hits in candidate text."""
    if not tokens:
        return 0
    candidate_tokens = tokenize(text)
    return len(tokens & candidate_tokens)


def belief_search_text(row: tuple[Any, ...]) -> str:
    """Build searchable text from a belief row tuple."""
    object_json = row[4]
    object_text = row[3]
    if object_text is None and object_json is not None:
        object_text = str(object_json)
    return " ".join(str(part or "") for part in (row[1], row[2], object_text, row[6]))


def render_belief(
    *,
    prefix: str,
    subject: str,
    predicate: str,
    object_text: str | None,
    object_json: Any,
    status: str,
    stability_class: str,
    confidence_tag: str,
    source_tag: str,
) -> str:
    """Render one belief with confidence and provenance tags."""
    object_value = object_text if object_text is not None else str(object_json)
    predicate_text = str(predicate).replace("_", " ")
    return (
        f"{prefix}: {subject} {predicate_text} {object_value}. "
        f"({confidence_tag}, src={source_tag}, status={status}, stability={stability_class})"
    )


def build_sections(candidates: list[_ContextCandidate]) -> list[ContextSection]:
    """Group packed candidates into deterministic output sections."""
    ordered_titles = [
        ("Standing Context", "pinned_beliefs"),
        ("Relevant Beliefs", "current_beliefs"),
        ("Raw Evidence Snippets", "exact_references"),
        ("Recent Signals", "recent_signals"),
        ("Uncertain / Conflicting", "historical_beliefs"),
        ("Missing Data / Gaps", "gaps"),
    ]
    sections: list[ContextSection] = []
    for title, lane in ordered_titles:
        items = tuple(
            candidate.text for candidate in candidates if candidate.section_title == title
        )
        if items:
            sections.append(ContextSection(title=title, lane=lane, items=items))
    return sections


def render_sections(sections: list[ContextSection]) -> str:
    """Render sections as the markdown context block consumed by callers."""
    blocks: list[str] = []
    for section in sections:
        blocks.append(f"## {section.title}")
        blocks.extend(f"- {item}" for item in section.items)
    return "\n".join(blocks)


def estimate_words(text: str) -> int:
    """Estimate budget cost using a stable local word approximation."""
    return max(1, len(text.split()))


def omission(
    candidate: _ContextCandidate,
    reason: str,
    policy_action: str | None = None,
) -> ContextOmission:
    """Build an omission record for a candidate."""
    return ContextOmission(
        candidate_id=candidate.candidate_id,
        lane=candidate.lane,
        reason=reason,
        target_table=candidate.target_table,
        target_id=candidate.target_id,
        privacy_tier=candidate.privacy_tier,
        policy_action=policy_action,
        sensitivity_class=candidate.sensitivity_class,
    )


def result_status(
    visible: list[_ContextCandidate],
    omissions: list[ContextOmission],
) -> str:
    """Classify the context package without conflating no-data and withholding."""
    visible_lanes = {candidate.lane for candidate in visible}
    if visible_lanes == {"gaps"}:
        gap = visible[0]
        return "withheld" if gap.target_id == "withheld" else "no_data"
    if any(item.reason != "sensitivity_cite_only" for item in omissions):
        return "partial"
    return "ok"


def sensitivity_class_from_payload(raw_payload: Any) -> str:
    """Return the candidate sensitivity label, defaulting routine Tier 1 data."""
    if isinstance(raw_payload, dict):
        sensitivity = raw_payload.get("sensitivity_class")
        if isinstance(sensitivity, str) and sensitivity.strip() != "":
            return sensitivity
    return "routine_project"


def cite_only_candidate(candidate: _ContextCandidate) -> _ContextCandidate:
    """Return a body-suppressed candidate that preserves citation visibility."""
    cite_ref = (
        candidate.citation.citation_id if candidate.citation is not None else candidate.reference_id
    )
    text = (
        "Citation only: body withheld by sensitivity policy "
        f"(reason=sensitivity_cite_only, src={cite_ref or candidate.target_table})."
    )
    return replace_candidate_text(candidate, text)


def redact_candidate(candidate: _ContextCandidate) -> _ContextCandidate:
    """Return a candidate with secret-like body content redacted."""
    text = (
        "Redacted: sensitive body removed by policy "
        f"(reason=secret_redacted, src={candidate.reference_id or candidate.target_table})."
    )
    return replace_candidate_text(candidate, text)


def replace_candidate_text(candidate: _ContextCandidate, text: str) -> _ContextCandidate:
    """Copy a context candidate with a replacement rendered body."""
    return _ContextCandidate(
        candidate_id=candidate.candidate_id,
        lane=candidate.lane,
        section_title=candidate.section_title,
        priority=candidate.priority,
        target_table=candidate.target_table,
        target_id=candidate.target_id,
        privacy_tier=candidate.privacy_tier,
        sensitivity_class=candidate.sensitivity_class,
        source_kind=candidate.source_kind,
        tenant_id=candidate.tenant_id,
        corpus_id=candidate.corpus_id,
        text=text,
        sort_key=candidate.sort_key,
        citation=candidate.citation,
        belief_id=candidate.belief_id,
        evidence_ids=candidate.evidence_ids,
        reference_id=candidate.reference_id,
    )


def reference_id(target_table: str, target_id: str) -> str:
    """Return a stable local reference id for context citations."""
    return f"{target_table}:{target_id}"


def short_id(value: str) -> str:
    """Return a compact display id."""
    return value.split("-")[0]


def format_datetime(value: Any) -> str | None:
    """Return an ISO timestamp for database datetime values."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
