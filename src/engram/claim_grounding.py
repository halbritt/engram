"""RFC 0053 claim-grounding boundary contracts."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

import psycopg

from engram.entity_grounding import search_grounding_evidence

CLAIM_GROUNDING_REQUEST_SCHEMA_VERSION = "claim_grounding.request.v1"
CLAIM_GROUNDING_RESPONSE_SCHEMA_VERSION = "claim_grounding.response.v1"
CLAIM_GROUNDING_NETWORK_DISPATCH_SCHEMA_VERSION = "claim_grounding.network_dispatch.v1"
CLAIM_GROUNDING_BROKER_VERSION = "claim_grounding.local_broker.v1"

CLAIM_GROUNDING_SURFACE_FORM_MAX_CHARS = int(
    os.environ.get("ENGRAM_CLAIM_GROUNDING_SURFACE_FORM_MAX_CHARS", "160")
)
CLAIM_GROUNDING_CONTEXT_CAPSULE_MAX_CHARS = int(
    os.environ.get("ENGRAM_CLAIM_GROUNDING_CONTEXT_CAPSULE_MAX_CHARS", "280")
)
CLAIM_GROUNDING_EXCERPT_MAX_CHARS = int(
    os.environ.get("ENGRAM_CLAIM_GROUNDING_EXCERPT_MAX_CHARS", "500")
)
CLAIM_GROUNDING_SEARCH_QUERY_MAX_CHARS = int(
    os.environ.get("ENGRAM_CLAIM_GROUNDING_SEARCH_QUERY_MAX_CHARS", "240")
)

LOCAL_LOOKUP_MODE = "local_lookup"
NETWORK_FETCH_MODE = "network_fetch"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
RFC3339_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
LOCAL_REF_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
REQUEST_ALLOWED_KEYS = frozenset(
    {
        "schema_version",
        "request_id",
        "tenant_id",
        "corpus_id",
        "extraction_run_id",
        "extraction_prompt_version",
        "extraction_model_version",
        "surface_form",
        "mention_role",
        "candidate_entity_kinds",
        "source_refs",
        "local_context_capsule",
        "allowed_modes",
        "network_grant",
        "privacy_tier_ceiling",
        "sensitivity_ceiling",
        "requested_at",
    }
)
SOURCE_REF_ALLOWED_KEYS = frozenset(
    {"target_table", "target_id", "span_hash", "span_start", "span_end"}
)
LOCAL_CONTEXT_ALLOWED_KEYS = frozenset({"mode", "text"})
NETWORK_GRANT_ALLOWED_KEYS = frozenset(
    {
        "grant_id",
        "granted_by",
        "granted_at",
        "expires_at",
        "purpose",
        "search_query",
        "query_text_class",
        "query_privacy_tier",
        "allowed_network_targets",
    }
)
RESPONSE_ALLOWED_KEYS = frozenset(
    {
        "schema_version",
        "request_id",
        "status",
        "mode",
        "network_fetch",
        "candidates",
        "omissions",
        "broker_version",
        "dataset_snapshots",
        "created_at",
    }
)
CANDIDATE_ALLOWED_KEYS = frozenset(
    {
        "candidate_id",
        "entity_kind",
        "canonical_label",
        "external_ids",
        "grounding_evidence_ids",
        "source_url",
        "source_label",
        "content_hash",
        "content_excerpt",
        "confidence",
        "stability",
        "ambiguity_reasons",
    }
)
EXTERNAL_ID_ALLOWED_KEYS = frozenset({"kind", "value"})
OMISSION_ALLOWED_KEYS = frozenset({"reason", "details"})
DATASET_SNAPSHOT_ALLOWED_KEYS = frozenset({"dataset", "snapshot_id"})
MENTION_ROLES = frozenset({"subject", "object", "context"})
SOURCE_REF_TARGET_TABLES = frozenset({"messages", "segments", "captures", "notes", "claims"})
ENTITY_KINDS = frozenset(
    {
        "person",
        "product",
        "place",
        "organization",
        "media_work",
        "tool",
        "concept",
        "unknown",
    }
)
LOCAL_CONTEXT_MODES = frozenset({"none", "local_only_redacted_hint"})
RESPONSE_STATUSES = frozenset({"resolved", "ambiguous", "not_found", "denied", "deferred", "error"})
REQUEST_MODES = frozenset({LOCAL_LOOKUP_MODE, NETWORK_FETCH_MODE})
NETWORK_FETCH_STATUSES = frozenset(
    {"not_requested", "unsupported", "denied", "performed_by_grounding_broker"}
)
NETWORK_TARGETS = frozenset({"internet_search", "public_dataset_api"})
NETWORK_GRANT_PURPOSES = frozenset({"entity_grounding"})
NETWORK_QUERY_TEXT_CLASSES = frozenset({"entity_surface_form"})
FORBIDDEN_PRIVATE_PAYLOAD_KEYS = frozenset(
    {
        "raw_payload",
        "raw_text",
        "message_text",
        "content_text",
        "segment_text",
        "conversation_text",
        "claim_text",
        "messages",
        "segments",
    }
)
SENSITIVITY_ORDER = {
    "routine_project": 0,
    "personal_private": 1,
    "third_party_communication": 2,
    "calendar_contact": 3,
    "behavioral_activity": 4,
    "raw_media": 5,
    "exact_location": 6,
    "health": 7,
    "biometric": 8,
    "finance": 9,
    "credential_or_secret_reference": 10,
}


class ClaimGroundingError(RuntimeError):
    """Base error for claim-grounding boundary failures."""


class ClaimGroundingSchemaError(ClaimGroundingError):
    """Raised when request or response payloads do not match the boundary."""


class ClaimGroundingModeDenied(ClaimGroundingError):
    """Raised when a request tries to use an unapproved grounding mode."""


@dataclass(frozen=True)
class ClaimGroundingSourceRef:
    """Opaque local evidence reference for a groundable mention."""

    target_table: str
    target_id: str
    span_hash: str | None = None
    span_start: int | None = None
    span_end: int | None = None

    @classmethod
    def from_json(
        cls,
        payload: Mapping[str, object],
        *,
        prefix: str,
    ) -> ClaimGroundingSourceRef:
        _reject_unknown_keys(payload, SOURCE_REF_ALLOWED_KEYS, prefix=prefix)
        _reject_forbidden_private_payload_keys(payload, prefix=prefix)
        span_hash = _optional_string_field(payload, "span_hash", prefix=prefix)
        if span_hash is not None and SHA256_PATTERN.fullmatch(span_hash) is None:
            raise ClaimGroundingSchemaError(f'{prefix}."span_hash" must be a sha256 hex string')
        span_start = _optional_int_field(payload, "span_start", prefix=prefix)
        span_end = _optional_int_field(payload, "span_end", prefix=prefix)
        if span_start is not None and span_start < 0:
            raise ClaimGroundingSchemaError(f'{prefix}."span_start" must be >= 0')
        if span_end is not None and span_end < 0:
            raise ClaimGroundingSchemaError(f'{prefix}."span_end" must be >= 0')
        if span_start is not None and span_end is not None and span_end < span_start:
            raise ClaimGroundingSchemaError(
                f'{prefix}."span_end" must be greater than or equal to "span_start"'
            )
        target_table = _enum_field(
            payload,
            "target_table",
            allowed=SOURCE_REF_TARGET_TABLES,
            prefix=prefix,
        )
        target_id = _string_field(payload, "target_id", prefix=prefix)
        if LOCAL_REF_ID_PATTERN.fullmatch(target_id) is None:
            raise ClaimGroundingSchemaError(f'{prefix}."target_id" must be an opaque local id')
        return cls(
            target_table=target_table,
            target_id=target_id,
            span_hash=span_hash,
            span_start=span_start,
            span_end=span_end,
        )

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "target_table": self.target_table,
            "target_id": self.target_id,
        }
        if self.span_hash is not None:
            payload["span_hash"] = self.span_hash
        if self.span_start is not None:
            payload["span_start"] = self.span_start
        if self.span_end is not None:
            payload["span_end"] = self.span_end
        return payload


@dataclass(frozen=True)
class LocalContextCapsule:
    """Optional extractor-side hint that never leaves local no-egress execution."""

    mode: str = "none"
    text: str | None = None

    @classmethod
    def from_json(
        cls,
        payload: Mapping[str, object] | None,
        *,
        prefix: str = "local_context_capsule",
    ) -> LocalContextCapsule:
        if payload is None:
            return cls()
        _require_keys(payload, ("mode", "text"), prefix=prefix)
        _reject_unknown_keys(payload, LOCAL_CONTEXT_ALLOWED_KEYS, prefix=prefix)
        mode = _enum_field(
            payload,
            "mode",
            allowed=LOCAL_CONTEXT_MODES,
            default="none",
            prefix=prefix,
        )
        text = _optional_string_field(payload, "text", prefix=prefix, allow_empty=True)
        if mode == "none" and text is not None:
            raise ClaimGroundingSchemaError(f'{prefix}."text" requires local_only_redacted_hint')
        if text is not None and len(text) > CLAIM_GROUNDING_CONTEXT_CAPSULE_MAX_CHARS:
            raise ClaimGroundingSchemaError(
                f'{prefix}."text" exceeds {CLAIM_GROUNDING_CONTEXT_CAPSULE_MAX_CHARS} chars'
            )
        return cls(mode=mode, text=text)

    def to_json(self) -> dict[str, object | None]:
        return {"mode": self.mode, "text": self.text}


@dataclass(frozen=True)
class NetworkGroundingGrant:
    """Explicit operator grant for a network-capable grounding broker mode."""

    grant_id: str
    granted_by: str
    granted_at: str
    purpose: str
    search_query: str
    query_text_class: str
    query_privacy_tier: int
    allowed_network_targets: tuple[str, ...]
    expires_at: str | None = None

    @classmethod
    def from_json(
        cls,
        payload: Mapping[str, object],
        *,
        prefix: str = "network_grant",
    ) -> NetworkGroundingGrant:
        _reject_unknown_keys(payload, NETWORK_GRANT_ALLOWED_KEYS, prefix=prefix)
        _reject_forbidden_private_payload_keys(payload, prefix=prefix)
        granted_at = _string_field(payload, "granted_at", prefix=prefix)
        _validate_rfc3339(granted_at, prefix=f'{prefix}."granted_at"')
        expires_at = _optional_string_field(payload, "expires_at", prefix=prefix)
        if expires_at is not None:
            _validate_rfc3339(expires_at, prefix=f'{prefix}."expires_at"')
        search_query = _string_field(payload, "search_query", prefix=prefix)
        if len(search_query) > CLAIM_GROUNDING_SEARCH_QUERY_MAX_CHARS:
            raise ClaimGroundingSchemaError(
                f'{prefix}."search_query" exceeds {CLAIM_GROUNDING_SEARCH_QUERY_MAX_CHARS} chars'
            )
        query_privacy_tier = _required_int_field(
            payload,
            "query_privacy_tier",
            prefix=prefix,
        )
        if query_privacy_tier < 0 or query_privacy_tier > 5:
            raise ClaimGroundingSchemaError(
                f'{prefix}."query_privacy_tier" must be between 0 and 5'
            )
        return cls(
            grant_id=_string_field(payload, "grant_id", prefix=prefix),
            granted_by=_string_field(payload, "granted_by", prefix=prefix),
            granted_at=granted_at,
            expires_at=expires_at,
            purpose=_enum_field(
                payload,
                "purpose",
                allowed=NETWORK_GRANT_PURPOSES,
                prefix=prefix,
            ),
            search_query=search_query,
            query_text_class=_enum_field(
                payload,
                "query_text_class",
                allowed=NETWORK_QUERY_TEXT_CLASSES,
                prefix=prefix,
            ),
            query_privacy_tier=query_privacy_tier,
            allowed_network_targets=_enum_tuple(
                payload,
                "allowed_network_targets",
                allowed=NETWORK_TARGETS,
                min_items=1,
                prefix=prefix,
            ),
        )

    def to_json(self) -> dict[str, object | None]:
        return {
            "grant_id": self.grant_id,
            "granted_by": self.granted_by,
            "granted_at": self.granted_at,
            "expires_at": self.expires_at,
            "purpose": self.purpose,
            "search_query": self.search_query,
            "query_text_class": self.query_text_class,
            "query_privacy_tier": self.query_privacy_tier,
            "allowed_network_targets": list(self.allowed_network_targets),
        }


@dataclass(frozen=True)
class ClaimGroundingRequest:
    """Versioned request from a no-egress claim extractor to a grounding broker."""

    request_id: str
    tenant_id: str
    corpus_id: str
    extraction_run_id: str
    extraction_prompt_version: str
    extraction_model_version: str
    surface_form: str
    mention_role: str
    candidate_entity_kinds: tuple[str, ...]
    source_refs: tuple[ClaimGroundingSourceRef, ...]
    local_context_capsule: LocalContextCapsule = field(default_factory=LocalContextCapsule)
    allowed_modes: tuple[str, ...] = (LOCAL_LOOKUP_MODE,)
    network_grant: NetworkGroundingGrant | None = None
    privacy_tier_ceiling: int = 1
    sensitivity_ceiling: tuple[str, ...] = ()
    requested_at: str = ""
    schema_version: str = CLAIM_GROUNDING_REQUEST_SCHEMA_VERSION

    @classmethod
    def from_json(cls, payload: Mapping[str, object]) -> ClaimGroundingRequest:
        """Validate and parse the RFC 0053 extractor-to-broker request shape."""
        _reject_unknown_keys(payload, REQUEST_ALLOWED_KEYS, prefix="request")
        _reject_forbidden_private_payload_keys(payload, prefix="request")
        schema_version = _string_field(payload, "schema_version", prefix="request")
        if schema_version != CLAIM_GROUNDING_REQUEST_SCHEMA_VERSION:
            raise ClaimGroundingSchemaError(f'unsupported schema_version "{schema_version}"')
        surface_form = _string_field(payload, "surface_form", prefix="request")
        if len(surface_form) > CLAIM_GROUNDING_SURFACE_FORM_MAX_CHARS:
            raise ClaimGroundingSchemaError(
                f'"surface_form" exceeds {CLAIM_GROUNDING_SURFACE_FORM_MAX_CHARS} chars'
            )
        allowed_modes = _string_tuple(
            payload,
            "allowed_modes",
            default=(LOCAL_LOOKUP_MODE,),
            prefix="request",
            unique=True,
        )
        local_context_capsule = LocalContextCapsule.from_json(
            _optional_mapping_field(payload, "local_context_capsule", prefix="request")
        )
        network_grant = _network_grant(payload, prefix="request")
        privacy_tier_ceiling = _int_field(
            payload,
            "privacy_tier_ceiling",
            default=1,
            prefix="request",
        )
        if privacy_tier_ceiling < 0 or privacy_tier_ceiling > 5:
            raise ClaimGroundingSchemaError('"privacy_tier_ceiling" must be between 0 and 5')
        _validate_request_modes(
            allowed_modes,
            network_grant=network_grant,
            local_context_capsule=local_context_capsule,
            surface_form=surface_form,
            privacy_tier_ceiling=privacy_tier_ceiling,
        )
        requested_at = _string_field(payload, "requested_at", prefix="request")
        _validate_rfc3339(requested_at, prefix='request."requested_at"')
        return cls(
            request_id=_string_field(payload, "request_id", prefix="request"),
            tenant_id=_string_field(payload, "tenant_id", prefix="request"),
            corpus_id=_string_field(payload, "corpus_id", prefix="request"),
            extraction_run_id=_string_field(payload, "extraction_run_id", prefix="request"),
            extraction_prompt_version=_string_field(
                payload,
                "extraction_prompt_version",
                prefix="request",
            ),
            extraction_model_version=_string_field(
                payload,
                "extraction_model_version",
                prefix="request",
            ),
            surface_form=surface_form,
            mention_role=_enum_field(
                payload,
                "mention_role",
                allowed=MENTION_ROLES,
                prefix="request",
            ),
            candidate_entity_kinds=_enum_tuple(
                payload,
                "candidate_entity_kinds",
                allowed=ENTITY_KINDS,
                min_items=1,
                prefix="request",
            ),
            source_refs=_source_refs(payload, prefix="request"),
            local_context_capsule=local_context_capsule,
            allowed_modes=allowed_modes,
            network_grant=network_grant,
            privacy_tier_ceiling=privacy_tier_ceiling,
            sensitivity_ceiling=_string_tuple(
                payload,
                "sensitivity_ceiling",
                default=(),
                prefix="request",
            ),
            requested_at=requested_at,
            schema_version=schema_version,
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "tenant_id": self.tenant_id,
            "corpus_id": self.corpus_id,
            "extraction_run_id": self.extraction_run_id,
            "extraction_prompt_version": self.extraction_prompt_version,
            "extraction_model_version": self.extraction_model_version,
            "surface_form": self.surface_form,
            "mention_role": self.mention_role,
            "candidate_entity_kinds": list(self.candidate_entity_kinds),
            "source_refs": [source_ref.to_json() for source_ref in self.source_refs],
            "local_context_capsule": self.local_context_capsule.to_json(),
            "allowed_modes": list(self.allowed_modes),
            "network_grant": (
                self.network_grant.to_json() if self.network_grant is not None else None
            ),
            "privacy_tier_ceiling": self.privacy_tier_ceiling,
            "sensitivity_ceiling": list(self.sensitivity_ceiling),
            "requested_at": self.requested_at,
        }


@dataclass(frozen=True)
class GroundingExternalId:
    """External public identifier attached to a grounding candidate."""

    kind: str
    value: str

    @classmethod
    def from_json(cls, payload: Mapping[str, object], *, prefix: str) -> GroundingExternalId:
        _reject_unknown_keys(payload, EXTERNAL_ID_ALLOWED_KEYS, prefix=prefix)
        return cls(
            kind=_string_field(payload, "kind", prefix=prefix),
            value=_string_field(payload, "value", prefix=prefix),
        )

    def to_json(self) -> dict[str, object]:
        return {"kind": self.kind, "value": self.value}


@dataclass(frozen=True)
class ClaimGroundingCandidate:
    """One cited grounding candidate returned by the local broker."""

    candidate_id: str
    entity_kind: str
    canonical_label: str
    grounding_evidence_ids: tuple[str, ...]
    content_hash: str
    content_excerpt: str
    confidence: float
    stability: str
    external_ids: tuple[GroundingExternalId, ...] = ()
    source_url: str | None = None
    source_label: str | None = None
    ambiguity_reasons: tuple[str, ...] = ()

    @classmethod
    def from_json(cls, payload: Mapping[str, object], *, prefix: str) -> ClaimGroundingCandidate:
        _reject_unknown_keys(payload, CANDIDATE_ALLOWED_KEYS, prefix=prefix)
        content_hash = _string_field(payload, "content_hash", prefix=prefix)
        if SHA256_PATTERN.fullmatch(content_hash) is None:
            raise ClaimGroundingSchemaError(f'{prefix}."content_hash" must be a sha256 hex string')
        content_excerpt = _string_field(payload, "content_excerpt", prefix=prefix)
        if len(content_excerpt) > CLAIM_GROUNDING_EXCERPT_MAX_CHARS:
            raise ClaimGroundingSchemaError(
                f'{prefix}."content_excerpt" exceeds {CLAIM_GROUNDING_EXCERPT_MAX_CHARS} chars'
            )
        confidence = _float_field(payload, "confidence", prefix=prefix)
        if confidence < 0.0 or confidence > 1.0:
            raise ClaimGroundingSchemaError(f'{prefix}."confidence" must be between 0 and 1')
        evidence_ids = _string_tuple(
            payload,
            "grounding_evidence_ids",
            default=(),
            prefix=prefix,
        )
        if not evidence_ids:
            raise ClaimGroundingSchemaError(
                f'{prefix}."grounding_evidence_ids" must cite local grounding evidence'
            )
        return cls(
            candidate_id=_string_field(payload, "candidate_id", prefix=prefix),
            entity_kind=_enum_field(
                payload,
                "entity_kind",
                allowed=ENTITY_KINDS,
                prefix=prefix,
            ),
            canonical_label=_string_field(payload, "canonical_label", prefix=prefix),
            external_ids=_external_ids(payload, prefix=prefix),
            grounding_evidence_ids=evidence_ids,
            source_url=_optional_string_field(payload, "source_url", prefix=prefix),
            source_label=_optional_string_field(payload, "source_label", prefix=prefix),
            content_hash=content_hash,
            content_excerpt=content_excerpt,
            confidence=confidence,
            stability=_string_field(payload, "stability", prefix=prefix),
            ambiguity_reasons=_string_tuple(
                payload,
                "ambiguity_reasons",
                default=(),
                prefix=prefix,
            ),
        )

    def to_json(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "entity_kind": self.entity_kind,
            "canonical_label": self.canonical_label,
            "external_ids": [external_id.to_json() for external_id in self.external_ids],
            "grounding_evidence_ids": list(self.grounding_evidence_ids),
            "source_url": self.source_url,
            "source_label": self.source_label,
            "content_hash": self.content_hash,
            "content_excerpt": self.content_excerpt,
            "confidence": self.confidence,
            "stability": self.stability,
            "ambiguity_reasons": list(self.ambiguity_reasons),
        }


@dataclass(frozen=True)
class GroundingOmission:
    """Reason a grounding response omitted data or could not resolve."""

    reason: str
    details: str | None = None

    @classmethod
    def from_json(cls, payload: Mapping[str, object], *, prefix: str) -> GroundingOmission:
        _reject_unknown_keys(payload, OMISSION_ALLOWED_KEYS, prefix=prefix)
        return cls(
            reason=_string_field(payload, "reason", prefix=prefix),
            details=_optional_string_field(payload, "details", prefix=prefix),
        )

    def to_json(self) -> dict[str, object | None]:
        return {"reason": self.reason, "details": self.details}


@dataclass(frozen=True)
class GroundingDatasetSnapshot:
    """Local public dataset snapshot cited by a grounding response."""

    dataset: str
    snapshot_id: str

    @classmethod
    def from_json(
        cls,
        payload: Mapping[str, object],
        *,
        prefix: str,
    ) -> GroundingDatasetSnapshot:
        _reject_unknown_keys(payload, DATASET_SNAPSHOT_ALLOWED_KEYS, prefix=prefix)
        return cls(
            dataset=_string_field(payload, "dataset", prefix=prefix),
            snapshot_id=_string_field(payload, "snapshot_id", prefix=prefix),
        )

    def to_json(self) -> dict[str, object]:
        return {"dataset": self.dataset, "snapshot_id": self.snapshot_id}


@dataclass(frozen=True)
class ClaimGroundingResponse:
    """Versioned grounding response that preserves citations and ambiguity."""

    request_id: str
    status: str
    mode: str
    network_fetch: str
    candidates: tuple[ClaimGroundingCandidate, ...]
    omissions: tuple[GroundingOmission, ...]
    broker_version: str
    dataset_snapshots: tuple[GroundingDatasetSnapshot, ...]
    created_at: str
    schema_version: str = CLAIM_GROUNDING_RESPONSE_SCHEMA_VERSION

    @classmethod
    def from_json(cls, payload: Mapping[str, object]) -> ClaimGroundingResponse:
        """Validate and parse the RFC 0053 local-only response shape."""
        _reject_unknown_keys(payload, RESPONSE_ALLOWED_KEYS, prefix="response")
        schema_version = _string_field(payload, "schema_version", prefix="response")
        if schema_version != CLAIM_GROUNDING_RESPONSE_SCHEMA_VERSION:
            raise ClaimGroundingSchemaError(f'unsupported schema_version "{schema_version}"')
        mode = _enum_field(
            payload,
            "mode",
            allowed=REQUEST_MODES,
            prefix="response",
        )
        network_fetch = _enum_field(
            payload,
            "network_fetch",
            allowed=NETWORK_FETCH_STATUSES,
            prefix="response",
        )
        if network_fetch == "performed_by_grounding_broker" and mode != NETWORK_FETCH_MODE:
            raise ClaimGroundingSchemaError(
                '"performed_by_grounding_broker" requires response mode "network_fetch"'
            )
        status = _enum_field(payload, "status", allowed=RESPONSE_STATUSES, prefix="response")
        candidates = _candidates(payload, prefix="response")
        _validate_status_candidate_shape(status, candidates)
        created_at = _string_field(payload, "created_at", prefix="response")
        _validate_rfc3339(created_at, prefix='response."created_at"')
        return cls(
            request_id=_string_field(payload, "request_id", prefix="response"),
            status=status,
            mode=mode,
            network_fetch=network_fetch,
            candidates=candidates,
            omissions=_omissions(payload, prefix="response"),
            broker_version=_string_field(payload, "broker_version", prefix="response"),
            dataset_snapshots=_dataset_snapshots(payload, prefix="response"),
            created_at=created_at,
            schema_version=schema_version,
        )

    def to_json(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "status": self.status,
            "mode": self.mode,
            "network_fetch": self.network_fetch,
            "candidates": [candidate.to_json() for candidate in self.candidates],
            "omissions": [omission.to_json() for omission in self.omissions],
            "broker_version": self.broker_version,
            "dataset_snapshots": [snapshot.to_json() for snapshot in self.dataset_snapshots],
            "created_at": self.created_at,
        }


def validate_grounding_request(payload: Mapping[str, object]) -> ClaimGroundingRequest:
    """Validate a claim-grounding request payload."""
    return ClaimGroundingRequest.from_json(payload)


def validate_grounding_response(payload: Mapping[str, object]) -> ClaimGroundingResponse:
    """Validate a claim-grounding response payload."""
    return ClaimGroundingResponse.from_json(payload)


def ground_claim_entity_locally(
    conn: psycopg.Connection,
    request: ClaimGroundingRequest | Mapping[str, object],
    *,
    limit: int = 5,
    created_at: str | None = None,
) -> ClaimGroundingResponse:
    """Resolve one RFC 0053 request against already-local grounding evidence."""
    active_request = (
        request
        if isinstance(request, ClaimGroundingRequest)
        else ClaimGroundingRequest.from_json(request)
    )
    if limit < 1 or limit > 50:
        raise ClaimGroundingSchemaError("limit must be between 1 and 50")
    hits = search_grounding_evidence(
        conn,
        query_text=active_request.surface_form,
        tenant_id=active_request.tenant_id,
        corpus_id=active_request.corpus_id,
        limit=limit,
    )
    filtered_hits = tuple(
        hit
        for hit in hits
        if _hit_allowed_by_request_policy(
            hit,
            privacy_tier_ceiling=active_request.privacy_tier_ceiling,
            sensitivity_ceiling=active_request.sensitivity_ceiling,
        )
    )
    policy_filtered_count = len(hits) - len(filtered_hits)
    candidates = tuple(_candidate_from_hit(hit) for hit in filtered_hits)
    if not candidates:
        if NETWORK_FETCH_MODE in active_request.allowed_modes:
            status = "deferred"
            network_fetch = "unsupported"
            omission_rows = [
                GroundingOmission(
                    reason="network_fetch_not_implemented",
                    details=(
                        "The request includes a network grant, but this broker helper "
                        "only performs local lookup."
                    ),
                )
            ]
        else:
            status = "not_found"
            network_fetch = "not_requested"
            omission_rows = [
                GroundingOmission(
                    reason="local_lookup_no_result",
                    details="No matching local grounding evidence was found.",
                )
            ]
    elif len(candidates) == 1:
        status = "resolved"
        network_fetch = "not_requested"
        omission_rows = []
    else:
        status = "ambiguous"
        network_fetch = "not_requested"
        omission_rows = [
            GroundingOmission(
                reason="multiple_local_candidates",
                details="Multiple cited local grounding candidates matched.",
            )
        ]
    if policy_filtered_count:
        omission_rows.append(
            GroundingOmission(
                reason="policy_filtered_grounding_evidence",
                details=(
                    f"{policy_filtered_count} local grounding candidate(s) exceeded "
                    "privacy or sensitivity ceilings."
                ),
            )
        )
    return ClaimGroundingResponse(
        request_id=active_request.request_id,
        status=status,
        mode=LOCAL_LOOKUP_MODE,
        network_fetch=network_fetch,
        candidates=candidates,
        omissions=tuple(omission_rows),
        broker_version=CLAIM_GROUNDING_BROKER_VERSION,
        dataset_snapshots=(),
        created_at=created_at or _utc_now_rfc3339(),
    )


def network_broker_dispatch_payload(
    request: ClaimGroundingRequest | Mapping[str, object],
) -> dict[str, object]:
    """Return the minimized payload allowed to cross to a network broker."""
    active_request = (
        request
        if isinstance(request, ClaimGroundingRequest)
        else ClaimGroundingRequest.from_json(request)
    )
    if NETWORK_FETCH_MODE not in active_request.allowed_modes:
        raise ClaimGroundingModeDenied("network dispatch requires network_fetch mode")
    if active_request.network_grant is None:
        raise ClaimGroundingModeDenied("network dispatch requires network_grant")
    return {
        "schema_version": CLAIM_GROUNDING_NETWORK_DISPATCH_SCHEMA_VERSION,
        "request_id": active_request.request_id,
        "tenant_id": active_request.tenant_id,
        "corpus_id": active_request.corpus_id,
        "surface_form": active_request.surface_form,
        "network_grant": active_request.network_grant.to_json(),
        "requested_at": active_request.requested_at,
    }


def _candidate_from_hit(hit: Mapping[str, object]) -> ClaimGroundingCandidate:
    score = _float_from_object(hit.get("score"), default=1.0)
    confidence = round(min(0.99, max(0.01, 0.45 + (score / 20.0))), 4)
    evidence_id = _hit_string(hit, "id")
    return ClaimGroundingCandidate(
        candidate_id=evidence_id,
        entity_kind=_hit_string(hit, "entity_kind"),
        canonical_label=_hit_string(hit, "query_text"),
        grounding_evidence_ids=(evidence_id,),
        source_url=_hit_optional_string(hit, "source_url"),
        source_label=_hit_optional_string(hit, "source_label"),
        content_hash=_hit_string(hit, "content_hash"),
        content_excerpt=_hit_string(hit, "content_excerpt"),
        confidence=confidence,
        stability="stable_public_entity",
    )


def _hit_allowed_by_request_policy(
    hit: Mapping[str, object],
    *,
    privacy_tier_ceiling: int,
    sensitivity_ceiling: Sequence[str],
) -> bool:
    privacy_tier = _int_from_object(hit.get("privacy_tier"), default=0)
    if privacy_tier > privacy_tier_ceiling:
        return False
    if not sensitivity_ceiling:
        return True
    sensitivity_class = _hit_optional_string(hit, "sensitivity_class")
    if sensitivity_class is None:
        return False
    max_rank = max(SENSITIVITY_ORDER.get(value, -1) for value in sensitivity_ceiling)
    return SENSITIVITY_ORDER.get(sensitivity_class, len(SENSITIVITY_ORDER)) <= max_rank


def _source_refs(
    payload: Mapping[str, object],
    *,
    prefix: str,
) -> tuple[ClaimGroundingSourceRef, ...]:
    rows = _mapping_tuple(payload, "source_refs", prefix=prefix)
    if not rows:
        raise ClaimGroundingSchemaError(f'{prefix}."source_refs" must contain at least one ref')
    return tuple(
        ClaimGroundingSourceRef.from_json(row, prefix=f'{prefix}."source_refs[{index}]"')
        for index, row in enumerate(rows)
    )


def _network_grant(
    payload: Mapping[str, object],
    *,
    prefix: str,
) -> NetworkGroundingGrant | None:
    value = _optional_mapping_field(payload, "network_grant", prefix=prefix)
    if value is None:
        return None
    return NetworkGroundingGrant.from_json(value)


def _external_ids(
    payload: Mapping[str, object],
    *,
    prefix: str,
) -> tuple[GroundingExternalId, ...]:
    return tuple(
        GroundingExternalId.from_json(row, prefix=f'{prefix}."external_ids[{index}]"')
        for index, row in enumerate(
            _mapping_tuple(payload, "external_ids", prefix=prefix, required=True)
        )
    )


def _candidates(
    payload: Mapping[str, object],
    *,
    prefix: str,
) -> tuple[ClaimGroundingCandidate, ...]:
    return tuple(
        ClaimGroundingCandidate.from_json(row, prefix=f'{prefix}."candidates[{index}]"')
        for index, row in enumerate(
            _mapping_tuple(payload, "candidates", prefix=prefix, required=True)
        )
    )


def _omissions(
    payload: Mapping[str, object],
    *,
    prefix: str,
) -> tuple[GroundingOmission, ...]:
    return tuple(
        GroundingOmission.from_json(row, prefix=f'{prefix}."omissions[{index}]"')
        for index, row in enumerate(
            _mapping_tuple(payload, "omissions", prefix=prefix, required=True)
        )
    )


def _dataset_snapshots(
    payload: Mapping[str, object],
    *,
    prefix: str,
) -> tuple[GroundingDatasetSnapshot, ...]:
    return tuple(
        GroundingDatasetSnapshot.from_json(row, prefix=f'{prefix}."dataset_snapshots[{index}]"')
        for index, row in enumerate(
            _mapping_tuple(payload, "dataset_snapshots", prefix=prefix, required=True)
        )
    )


def _validate_status_candidate_shape(
    status: str,
    candidates: tuple[ClaimGroundingCandidate, ...],
) -> None:
    if status == "resolved" and len(candidates) != 1:
        raise ClaimGroundingSchemaError('"resolved" responses require exactly one candidate')
    if status == "ambiguous" and len(candidates) < 2:
        raise ClaimGroundingSchemaError('"ambiguous" responses require at least two candidates')
    if status in {"not_found", "denied", "deferred", "error"} and candidates:
        raise ClaimGroundingSchemaError(f'"{status}" responses must not include candidates')


def _validate_request_modes(
    modes: Sequence[str],
    *,
    network_grant: NetworkGroundingGrant | None,
    local_context_capsule: LocalContextCapsule,
    surface_form: str,
    privacy_tier_ceiling: int,
) -> None:
    unsupported = tuple(mode for mode in modes if mode not in REQUEST_MODES)
    if unsupported:
        raise ClaimGroundingModeDenied(
            "claim grounding only supports local_lookup and explicitly granted "
            f"network_fetch; unsupported mode(s): {', '.join(unsupported)}"
        )
    if not modes:
        raise ClaimGroundingSchemaError('"allowed_modes" must contain at least one mode')
    if NETWORK_FETCH_MODE in modes and network_grant is None:
        raise ClaimGroundingModeDenied(
            "network_fetch requires an explicit network_grant and bounded search_query"
        )
    if NETWORK_FETCH_MODE not in modes and network_grant is not None:
        raise ClaimGroundingSchemaError(
            '"network_grant" requires allowed_modes to include network_fetch'
        )
    if NETWORK_FETCH_MODE in modes and local_context_capsule.text is not None:
        raise ClaimGroundingSchemaError(
            "network-capable requests must not include local_context_capsule.text"
        )
    if network_grant is None:
        return
    if network_grant.query_privacy_tier > privacy_tier_ceiling:
        raise ClaimGroundingSchemaError(
            '"network_grant.query_privacy_tier" exceeds privacy_tier_ceiling'
        )
    if (
        network_grant.query_text_class == "entity_surface_form"
        and network_grant.search_query != surface_form
    ):
        raise ClaimGroundingSchemaError(
            'entity_surface_form network grants must search exactly "surface_form"'
        )


def _reject_unknown_keys(
    payload: Mapping[str, object],
    allowed: frozenset[str],
    *,
    prefix: str,
) -> None:
    unknown = sorted(str(key) for key in payload if str(key) not in allowed)
    if unknown:
        raise ClaimGroundingSchemaError(
            f"{prefix} contains unsupported field(s): {', '.join(unknown)}"
        )


def _require_keys(
    payload: Mapping[str, object],
    keys: Sequence[str],
    *,
    prefix: str,
) -> None:
    missing = tuple(key for key in keys if key not in payload)
    if missing:
        raise ClaimGroundingSchemaError(f"{prefix} missing required field(s): {', '.join(missing)}")


def _reject_forbidden_private_payload_keys(payload: Mapping[str, object], *, prefix: str) -> None:
    for key, value in payload.items():
        key_name = str(key)
        if key_name in FORBIDDEN_PRIVATE_PAYLOAD_KEYS:
            raise ClaimGroundingSchemaError(
                f'{prefix}."{key_name}" is not allowed across the grounding boundary'
            )
        if isinstance(value, Mapping):
            _reject_forbidden_private_payload_keys(value, prefix=f'{prefix}."{key_name}"')
        elif isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
            for index, item in enumerate(value):
                if isinstance(item, Mapping):
                    _reject_forbidden_private_payload_keys(
                        item,
                        prefix=f'{prefix}."{key_name}[{index}]"',
                    )


def _mapping_tuple(
    payload: Mapping[str, object],
    key: str,
    *,
    prefix: str,
    required: bool = False,
) -> tuple[Mapping[str, object], ...]:
    if required and key not in payload:
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" is required')
    value = payload.get(key, ())
    if value is None:
        if required:
            raise ClaimGroundingSchemaError(f'{prefix}."{key}" must be an array of objects')
        return ()
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" must be an array of objects')
    rows: list[Mapping[str, object]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ClaimGroundingSchemaError(f'{prefix}."{key}[{index}]" must be an object')
        rows.append(item)
    return tuple(rows)


def _string_tuple(
    payload: Mapping[str, object],
    key: str,
    *,
    default: Sequence[str],
    prefix: str,
    unique: bool = False,
) -> tuple[str, ...]:
    value = payload.get(key, default)
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" must be an array of strings')
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ClaimGroundingSchemaError(f'{prefix}."{key}[{index}]" must be a non-empty string')
        result.append(item)
    if unique and len(set(result)) != len(result):
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" must contain unique values')
    return tuple(result)


def _enum_tuple(
    payload: Mapping[str, object],
    key: str,
    *,
    allowed: frozenset[str],
    min_items: int,
    prefix: str,
) -> tuple[str, ...]:
    values = _string_tuple(payload, key, default=(), prefix=prefix)
    if len(values) < min_items:
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" must contain at least {min_items} item')
    unsupported = tuple(value for value in values if value not in allowed)
    if unsupported:
        raise ClaimGroundingSchemaError(
            f'{prefix}."{key}" has unsupported value(s): {", ".join(unsupported)}'
        )
    if len(set(values)) != len(values):
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" must contain unique values')
    return values


def _enum_field(
    payload: Mapping[str, object],
    key: str,
    *,
    allowed: frozenset[str],
    prefix: str,
    default: str | None = None,
) -> str:
    value = _string_field(payload, key, prefix=prefix, default=default)
    if value not in allowed:
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" has unsupported value "{value}"')
    return value


def _string_field(
    payload: Mapping[str, object],
    key: str,
    *,
    prefix: str,
    default: str | None = None,
) -> str:
    value = payload.get(key, default)
    if value is None:
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" is required')
    if not isinstance(value, str) or not value.strip():
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" must be a non-empty string')
    return value


def _optional_string_field(
    payload: Mapping[str, object],
    key: str,
    *,
    prefix: str,
    allow_empty: bool = False,
) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" must be a string when present')
    if not allow_empty and not value.strip():
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" must be non-empty when present')
    return value


def _int_field(
    payload: Mapping[str, object],
    key: str,
    *,
    default: int,
    prefix: str,
) -> int:
    value = payload.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" must be an integer')
    return value


def _required_int_field(
    payload: Mapping[str, object],
    key: str,
    *,
    prefix: str,
) -> int:
    if key not in payload:
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" is required')
    value = payload[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" must be an integer')
    return value


def _optional_int_field(
    payload: Mapping[str, object],
    key: str,
    *,
    prefix: str,
) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" must be an integer')
    return value


def _float_field(payload: Mapping[str, object], key: str, *, prefix: str) -> float:
    value = payload.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" must be a number')
    return float(value)


def _optional_mapping_field(
    payload: Mapping[str, object],
    key: str,
    *,
    prefix: str,
) -> Mapping[str, object] | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ClaimGroundingSchemaError(f'{prefix}."{key}" must be an object')
    return value


def _validate_rfc3339(value: str, *, prefix: str) -> None:
    if RFC3339_PATTERN.fullmatch(value) is None:
        raise ClaimGroundingSchemaError(f"{prefix} must be an RFC3339 timestamp")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ClaimGroundingSchemaError(f"{prefix} must be an RFC3339 timestamp") from exc


def _utc_now_rfc3339() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hit_string(hit: Mapping[str, object], key: str) -> str:
    value = hit.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ClaimGroundingSchemaError(f'local grounding hit missing "{key}"')
    return value


def _hit_optional_string(hit: Mapping[str, object], key: str) -> str | None:
    value = hit.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value)
    return value


def _float_from_object(value: object, *, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, int | float):
        return float(value)
    return default


def _int_from_object(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    return default
