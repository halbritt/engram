"""Extraction-adjacent RFC 0053 claim-grounding sidecar emission."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

import psycopg
from psycopg.types.json import Jsonb

from engram.claim_grounding import (
    CLAIM_GROUNDING_REQUEST_SCHEMA_VERSION,
    ClaimGroundingRequest,
)
from engram.claim_grounding_runtime import record_claim_grounding_request

CLAIM_GROUNDING_EXTRACTION_INTEGRATION_VERSION = "claim_grounding.extraction_sidecars.v1"
CLAIM_GROUNDING_CANDIDATE_ENTITY_KINDS = (
    "person",
    "product",
    "place",
    "organization",
    "media_work",
    "tool",
    "concept",
    "unknown",
)
CLAIM_GROUNDING_OBJECT_NAME_KEYS = (
    "name",
    "project",
    "product",
    "tool",
    "place",
    "organization",
    "repo",
    "repository",
    "employer",
)


class ClaimGroundingClaimLike(Protocol):
    """Extractor claim draft shape needed for grounding request emission."""

    @property
    def subject_text(self) -> str: ...

    @property
    def object_text(self) -> str | None: ...

    @property
    def object_json(self) -> object | None: ...

    @property
    def evidence_message_ids(self) -> Sequence[str]: ...


class ClaimGroundingSegmentLike(Protocol):
    """Extractor segment shape needed for grounding request emission."""

    @property
    def id(self) -> str: ...

    @property
    def privacy_tier(self) -> int: ...


@dataclass(frozen=True)
class EmittedClaimGroundingRequest:
    """One persisted extraction-grounding request sidecar."""

    request_id: str
    request_record_id: str
    link_id: str
    surface_form: str
    mention_role: str


def emit_claim_grounding_requests_for_claims(
    conn: psycopg.Connection,
    *,
    extraction_id: str,
    segment: ClaimGroundingSegmentLike,
    claims: Sequence[ClaimGroundingClaimLike],
    prompt_version: str,
    model_version: str,
    tenant_id: str = "personal",
    corpus_id: str = "personal",
    requested_at: str | None = None,
    enabled: bool = False,
) -> tuple[EmittedClaimGroundingRequest, ...]:
    """Persist request/link sidecars for already-accepted extraction claim drafts.

    This helper never performs lookup or network IO. It is intended to run only
    after extraction output has been validated and accepted.
    """
    if not enabled:
        return ()

    active_requested_at = requested_at or _rfc3339_now()
    emitted: list[EmittedClaimGroundingRequest] = []
    for index, mention in enumerate(_groundable_mentions(claims)):
        request = ClaimGroundingRequest.from_json(
            _request_payload(
                extraction_id=extraction_id,
                segment=segment,
                mention=mention,
                mention_index=index,
                prompt_version=prompt_version,
                model_version=model_version,
                tenant_id=tenant_id,
                corpus_id=corpus_id,
                requested_at=active_requested_at,
            )
        )
        request_record = record_claim_grounding_request(conn, request)
        link_id = _record_extraction_sidecar_link(
            conn,
            request_record_id=str(request_record.id),
            extraction_id=extraction_id,
            request=request,
            mention_index=index,
        )
        emitted.append(
            EmittedClaimGroundingRequest(
                request_id=request.request_id,
                request_record_id=str(request_record.id),
                link_id=link_id,
                surface_form=request.surface_form,
                mention_role=request.mention_role,
            )
        )
    return tuple(emitted)


@dataclass(frozen=True)
class _GroundableMention:
    surface_form: str
    mention_role: str
    source_refs: tuple[dict[str, str], ...]


def _groundable_mentions(
    claims: Sequence[ClaimGroundingClaimLike],
) -> Iterable[_GroundableMention]:
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    for claim in claims:
        source_refs = _source_refs(claim.evidence_message_ids)
        for role, surface in _claim_surfaces(claim):
            key = (
                role,
                _normalize_surface(surface),
                tuple(ref["target_id"] for ref in source_refs),
            )
            if key in seen:
                continue
            seen.add(key)
            yield _GroundableMention(
                surface_form=surface,
                mention_role=role,
                source_refs=source_refs,
            )


def _claim_surfaces(claim: ClaimGroundingClaimLike) -> Iterable[tuple[str, str]]:
    subject_text = _clean_surface(claim.subject_text)
    if subject_text is not None:
        yield "subject", subject_text
    object_text = _clean_surface(claim.object_text)
    if object_text is not None:
        yield "object", object_text
    if isinstance(claim.object_json, Mapping):
        for key in CLAIM_GROUNDING_OBJECT_NAME_KEYS:
            surface = _clean_surface(claim.object_json.get(key))
            if surface is not None:
                yield "object", surface


def _request_payload(
    *,
    extraction_id: str,
    segment: ClaimGroundingSegmentLike,
    mention: _GroundableMention,
    mention_index: int,
    prompt_version: str,
    model_version: str,
    tenant_id: str,
    corpus_id: str,
    requested_at: str,
) -> dict[str, object]:
    privacy_tier = _privacy_tier(segment.privacy_tier)
    return {
        "schema_version": CLAIM_GROUNDING_REQUEST_SCHEMA_VERSION,
        "request_id": _request_id(
            extraction_id=extraction_id,
            segment_id=segment.id,
            mention=mention,
            mention_index=mention_index,
            prompt_version=prompt_version,
            model_version=model_version,
        ),
        "tenant_id": tenant_id,
        "corpus_id": corpus_id,
        "extraction_run_id": extraction_id,
        "extraction_prompt_version": prompt_version,
        "extraction_model_version": model_version,
        "surface_form": mention.surface_form,
        "mention_role": mention.mention_role,
        "candidate_entity_kinds": list(CLAIM_GROUNDING_CANDIDATE_ENTITY_KINDS),
        "source_refs": list(mention.source_refs),
        "local_context_capsule": {"mode": "none", "text": None},
        "allowed_modes": ["local_lookup"],
        "network_grant": None,
        "privacy_tier_ceiling": privacy_tier,
        "sensitivity_ceiling": list(_sensitivity_ceiling(privacy_tier)),
        "requested_at": requested_at,
    }


def _record_extraction_sidecar_link(
    conn: psycopg.Connection,
    *,
    request_record_id: str,
    extraction_id: str,
    request: ClaimGroundingRequest,
    mention_index: int,
) -> str:
    row = conn.execute(
        """
        INSERT INTO claim_grounding_links (
            request_id,
            extraction_id,
            tenant_id,
            corpus_id,
            link_kind,
            link_payload,
            created_at
        )
        VALUES (%s::uuid, %s::uuid, %s, %s, 'extraction_grounding_sidecar', %s, now())
        RETURNING id::text
        """,
        (
            request_record_id,
            extraction_id,
            request.tenant_id,
            request.corpus_id,
            Jsonb(
                {
                    "integration_version": CLAIM_GROUNDING_EXTRACTION_INTEGRATION_VERSION,
                    "request_id": request.request_id,
                    "mention_index": mention_index,
                    "surface_form": request.surface_form,
                    "mention_role": request.mention_role,
                }
            ),
        ),
    ).fetchone()
    if row is None:
        raise RuntimeError("claim-grounding extraction sidecar link insert returned no row")
    return str(row[0])


def _request_id(
    *,
    extraction_id: str,
    segment_id: str,
    mention: _GroundableMention,
    mention_index: int,
    prompt_version: str,
    model_version: str,
) -> str:
    payload = {
        "integration_version": CLAIM_GROUNDING_EXTRACTION_INTEGRATION_VERSION,
        "extraction_id": extraction_id,
        "segment_id": segment_id,
        "mention_index": mention_index,
        "mention_role": mention.mention_role,
        "surface_form": mention.surface_form,
        "source_refs": mention.source_refs,
        "prompt_version": prompt_version,
        "model_version": model_version,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"claim-grounding-{digest[:32]}"


def _source_refs(evidence_message_ids: Sequence[str]) -> tuple[dict[str, str], ...]:
    refs: list[dict[str, str]] = []
    for message_id in evidence_message_ids:
        refs.append(
            {
                "target_table": "messages",
                "target_id": message_id,
                "span_hash": hashlib.sha256(message_id.encode("utf-8")).hexdigest(),
            }
        )
    return tuple(refs)


def _clean_surface(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    if len(cleaned) < 2 or not any(character.isalpha() for character in cleaned):
        return None
    return cleaned


def _normalize_surface(surface: str) -> str:
    return " ".join(surface.split()).casefold()


def _privacy_tier(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 1
    return max(0, min(value, 5))


def _sensitivity_ceiling(privacy_tier: int) -> tuple[str, ...]:
    if privacy_tier <= 1:
        return ("routine_project",)
    return ("routine_project", "personal_private")


def _rfc3339_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
