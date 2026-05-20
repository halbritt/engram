from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

import psycopg
import pytest

from engram.claim_grounding import (
    CLAIM_GROUNDING_NETWORK_DISPATCH_SCHEMA_VERSION,
    CLAIM_GROUNDING_REQUEST_SCHEMA_VERSION,
    CLAIM_GROUNDING_RESPONSE_SCHEMA_VERSION,
    ClaimGroundingModeDenied,
    ClaimGroundingRequest,
    ClaimGroundingResponse,
    ClaimGroundingSchemaError,
    ground_claim_entity_locally,
    network_broker_dispatch_payload,
)


def _request_payload() -> dict[str, object]:
    return {
        "schema_version": CLAIM_GROUNDING_REQUEST_SCHEMA_VERSION,
        "request_id": "req-001",
        "tenant_id": "personal",
        "corpus_id": "personal",
        "extraction_run_id": "run-001",
        "extraction_prompt_version": "extractor.v-test",
        "extraction_model_version": "local-test-model",
        "surface_form": "Project Atlas",
        "mention_role": "subject",
        "candidate_entity_kinds": ["product", "organization"],
        "source_refs": [
            {
                "target_table": "messages",
                "target_id": "message-001",
                "span_hash": "a" * 64,
                "span_start": 12,
                "span_end": 25,
            }
        ],
        "local_context_capsule": {"mode": "none", "text": None},
        "allowed_modes": ["local_lookup"],
        "privacy_tier_ceiling": 1,
        "sensitivity_ceiling": ["routine_project"],
        "requested_at": "2026-05-18T00:00:00Z",
    }


def _network_grant() -> dict[str, object]:
    return {
        "grant_id": "grant-001",
        "granted_by": "operator",
        "granted_at": "2026-05-18T00:00:00Z",
        "expires_at": None,
        "purpose": "entity_grounding",
        "search_query": "Project Atlas",
        "query_text_class": "entity_surface_form",
        "query_privacy_tier": 1,
        "allowed_network_targets": ["internet_search", "public_dataset_api"],
    }


def _resolved_response_payload() -> dict[str, object]:
    return {
        "schema_version": CLAIM_GROUNDING_RESPONSE_SCHEMA_VERSION,
        "request_id": "req-001",
        "status": "resolved",
        "mode": "network_fetch",
        "network_fetch": "performed_by_grounding_broker",
        "candidates": [
            {
                "candidate_id": "grounding-001",
                "entity_kind": "product",
                "canonical_label": "Project Atlas",
                "external_ids": [{"kind": "wikidata_qid", "value": "QTEST"}],
                "grounding_evidence_ids": ["grounding-001"],
                "source_url": "https://example.invalid/project-atlas",
                "source_label": "Fixture public page",
                "content_hash": "b" * 64,
                "content_excerpt": "Project Atlas is a local-first software product.",
                "confidence": 0.91,
                "stability": "stable_public_entity",
                "ambiguity_reasons": [],
            }
        ],
        "omissions": [],
        "broker_version": "claim_grounding.network_broker.test",
        "dataset_snapshots": [],
        "created_at": "2026-05-18T00:00:01Z",
    }


def test_claim_grounding_request_round_trips_local_lookup() -> None:
    request = ClaimGroundingRequest.from_json(_request_payload())

    assert request.schema_version == "claim_grounding.request.v1"
    assert request.allowed_modes == ("local_lookup",)
    assert request.local_context_capsule.text is None
    assert ClaimGroundingRequest.from_json(request.to_json()) == request


def test_claim_grounding_request_accepts_explicit_network_broker_grant() -> None:
    payload = _request_payload()
    payload["allowed_modes"] = ["local_lookup", "network_fetch"]
    payload["network_grant"] = _network_grant()

    request = ClaimGroundingRequest.from_json(payload)

    assert request.network_grant is not None
    assert request.network_grant.search_query == "Project Atlas"
    assert request.network_grant.query_text_class == "entity_surface_form"
    assert request.network_grant.query_privacy_tier == 1
    assert request.network_grant.allowed_network_targets == (
        "internet_search",
        "public_dataset_api",
    )


def test_claim_grounding_request_requires_complete_local_context_capsule() -> None:
    payload = _request_payload()
    payload["local_context_capsule"] = {"mode": "none"}

    with pytest.raises(ClaimGroundingSchemaError, match="local_context_capsule"):
        ClaimGroundingRequest.from_json(payload)


def test_claim_grounding_request_requires_explicit_query_privacy_tier() -> None:
    payload = _request_payload()
    payload["allowed_modes"] = ["network_fetch"]
    grant = _network_grant()
    del grant["query_privacy_tier"]
    payload["network_grant"] = grant

    with pytest.raises(ClaimGroundingSchemaError, match="query_privacy_tier"):
        ClaimGroundingRequest.from_json(payload)


def test_claim_grounding_request_rejects_network_mode_without_operator_grant() -> None:
    payload = _request_payload()
    payload["allowed_modes"] = ["network_fetch"]

    with pytest.raises(ClaimGroundingModeDenied, match="network_fetch requires"):
        ClaimGroundingRequest.from_json(payload)


def test_claim_grounding_request_rejects_private_context_on_network_mode() -> None:
    payload = _request_payload()
    payload["allowed_modes"] = ["network_fetch"]
    payload["network_grant"] = _network_grant()
    payload["local_context_capsule"] = {
        "mode": "local_only_redacted_hint",
        "text": "Private sentence from the source message.",
    }

    with pytest.raises(ClaimGroundingSchemaError, match=r"local_context_capsule\.text"):
        ClaimGroundingRequest.from_json(payload)


def test_claim_grounding_request_allows_private_entity_name_as_search_query() -> None:
    payload = _request_payload()
    payload["surface_form"] = "Rowan Quill"
    payload["allowed_modes"] = ["network_fetch"]
    grant = _network_grant()
    grant["search_query"] = "Rowan Quill"
    grant["query_privacy_tier"] = 2
    payload["network_grant"] = grant
    payload["privacy_tier_ceiling"] = 2

    request = ClaimGroundingRequest.from_json(payload)

    assert request.surface_form == "Rowan Quill"
    assert request.network_grant is not None
    assert request.network_grant.search_query == "Rowan Quill"
    assert request.network_grant.query_privacy_tier == 2


def test_claim_grounding_request_rejects_surface_grant_query_drift() -> None:
    payload = _request_payload()
    payload["allowed_modes"] = ["network_fetch"]
    grant = _network_grant()
    grant["search_query"] = "Project Atlas private budget context"
    payload["network_grant"] = grant

    with pytest.raises(ClaimGroundingSchemaError, match="surface_form"):
        ClaimGroundingRequest.from_json(payload)


@pytest.mark.parametrize("search_query", ["project atlas", " Project  Atlas "])
def test_claim_grounding_request_rejects_normalized_surface_grant_query_drift(
    search_query: str,
) -> None:
    payload = _request_payload()
    payload["allowed_modes"] = ["network_fetch"]
    grant = _network_grant()
    grant["search_query"] = search_query
    payload["network_grant"] = grant

    with pytest.raises(ClaimGroundingSchemaError, match="surface_form"):
        ClaimGroundingRequest.from_json(payload)


def test_claim_grounding_request_rejects_query_privacy_above_ceiling() -> None:
    payload = _request_payload()
    payload["allowed_modes"] = ["network_fetch"]
    grant = _network_grant()
    grant["query_privacy_tier"] = 3
    payload["network_grant"] = grant

    with pytest.raises(ClaimGroundingSchemaError, match="query_privacy_tier"):
        ClaimGroundingRequest.from_json(payload)


def test_claim_grounding_request_rejects_raw_private_payload_fields() -> None:
    payload = _request_payload()
    payload["source_refs"] = [
        {
            "target_table": "messages",
            "target_id": "message-001",
            "message_text": "The private message must not cross the boundary.",
        }
    ]

    with pytest.raises(ClaimGroundingSchemaError, match="message_text"):
        ClaimGroundingRequest.from_json(payload)


def test_claim_grounding_request_rejects_raw_context_as_source_ref_id() -> None:
    payload = _request_payload()
    payload["source_refs"] = [
        {
            "target_table": "messages",
            "target_id": "Project Atlas private budget context",
        }
    ]

    with pytest.raises(ClaimGroundingSchemaError, match="opaque local id"):
        ClaimGroundingRequest.from_json(payload)


def test_claim_grounding_request_rejects_unknown_source_ref_table() -> None:
    payload = _request_payload()
    payload["source_refs"] = [
        {
            "target_table": "raw_chat_history",
            "target_id": "message-001",
        }
    ]

    with pytest.raises(ClaimGroundingSchemaError, match="target_table"):
        ClaimGroundingRequest.from_json(payload)


@pytest.mark.parametrize("query_text_class", ["operator_entered", "broker_minimized"])
def test_claim_grounding_request_rejects_non_surface_network_queries(
    query_text_class: str,
) -> None:
    payload = _request_payload()
    payload["allowed_modes"] = ["network_fetch"]
    grant = _network_grant()
    grant["query_text_class"] = query_text_class
    payload["network_grant"] = grant

    with pytest.raises(ClaimGroundingSchemaError, match="query_text_class"):
        ClaimGroundingRequest.from_json(payload)


@pytest.mark.parametrize("target", ["public_web", "operator_supplied_url"])
def test_claim_grounding_request_rejects_direct_url_network_targets(target: str) -> None:
    payload = _request_payload()
    payload["allowed_modes"] = ["network_fetch"]
    grant = _network_grant()
    grant["allowed_network_targets"] = [target]
    payload["network_grant"] = grant

    with pytest.raises(ClaimGroundingSchemaError, match="allowed_network_targets"):
        ClaimGroundingRequest.from_json(payload)


def test_claim_grounding_request_rejects_duplicate_boundary_enums() -> None:
    duplicate_modes = _request_payload()
    duplicate_modes["allowed_modes"] = ["local_lookup", "local_lookup"]
    with pytest.raises(ClaimGroundingSchemaError, match="allowed_modes"):
        ClaimGroundingRequest.from_json(duplicate_modes)

    duplicate_kinds = _request_payload()
    duplicate_kinds["candidate_entity_kinds"] = ["product", "product"]
    with pytest.raises(ClaimGroundingSchemaError, match="candidate_entity_kinds"):
        ClaimGroundingRequest.from_json(duplicate_kinds)

    duplicate_targets = _request_payload()
    duplicate_targets["allowed_modes"] = ["network_fetch"]
    grant = _network_grant()
    grant["allowed_network_targets"] = ["internet_search", "internet_search"]
    duplicate_targets["network_grant"] = grant
    with pytest.raises(ClaimGroundingSchemaError, match="allowed_network_targets"):
        ClaimGroundingRequest.from_json(duplicate_targets)


def test_network_broker_dispatch_payload_minimizes_private_local_context() -> None:
    payload = _request_payload()
    payload["allowed_modes"] = ["local_lookup", "network_fetch"]
    payload["network_grant"] = _network_grant()

    dispatch_payload = network_broker_dispatch_payload(payload)

    assert dispatch_payload == {
        "schema_version": CLAIM_GROUNDING_NETWORK_DISPATCH_SCHEMA_VERSION,
        "request_id": "req-001",
        "tenant_id": "personal",
        "corpus_id": "personal",
        "surface_form": "Project Atlas",
        "network_grant": _network_grant(),
        "requested_at": "2026-05-18T00:00:00Z",
    }
    assert "source_refs" not in dispatch_payload
    assert "local_context_capsule" not in dispatch_payload
    assert "extraction_prompt_version" not in dispatch_payload


def test_network_broker_dispatch_payload_has_dedicated_schema() -> None:
    schema = _load_schema("claim_grounding_network_dispatch.v1.schema.json")
    payload = _request_payload()
    payload["allowed_modes"] = ["local_lookup", "network_fetch"]
    payload["network_grant"] = _network_grant()

    dispatch_payload = network_broker_dispatch_payload(payload)

    assert _schema_errors(schema, dispatch_payload) == []
    assert _schema_errors(schema, payload)


def test_claim_grounding_response_round_trips_network_fetch_result() -> None:
    response = ClaimGroundingResponse.from_json(_resolved_response_payload())

    assert response.mode == "network_fetch"
    assert response.network_fetch == "performed_by_grounding_broker"
    assert response.candidates[0].grounding_evidence_ids == ("grounding-001",)
    assert ClaimGroundingResponse.from_json(response.to_json()) == response


def test_claim_grounding_response_requires_cited_candidate() -> None:
    payload = _resolved_response_payload()
    candidate = dict(payload["candidates"][0])  # type: ignore[index]
    candidate["grounding_evidence_ids"] = []
    payload["candidates"] = [candidate]

    with pytest.raises(ClaimGroundingSchemaError, match="grounding_evidence_ids"):
        ClaimGroundingResponse.from_json(payload)


def test_claim_grounding_response_preserves_ambiguity_shape() -> None:
    payload = _resolved_response_payload()
    first_candidate = dict(payload["candidates"][0])  # type: ignore[index]
    second_candidate = dict(first_candidate)
    second_candidate["candidate_id"] = "grounding-002"
    second_candidate["entity_kind"] = "organization"
    second_candidate["grounding_evidence_ids"] = ["grounding-002"]
    payload["status"] = "ambiguous"
    payload["mode"] = "local_lookup"
    payload["network_fetch"] = "not_requested"
    payload["candidates"] = [first_candidate, second_candidate]

    response = ClaimGroundingResponse.from_json(payload)

    assert response.status == "ambiguous"
    assert len(response.candidates) == 2


def test_claim_grounding_response_requires_schema_arrays_when_parsing() -> None:
    missing_omissions = _resolved_response_payload()
    del missing_omissions["omissions"]
    with pytest.raises(ClaimGroundingSchemaError, match="omissions"):
        ClaimGroundingResponse.from_json(missing_omissions)

    missing_external_ids = _resolved_response_payload()
    candidate = dict(missing_external_ids["candidates"][0])  # type: ignore[index]
    del candidate["external_ids"]
    missing_external_ids["candidates"] = [candidate]
    with pytest.raises(ClaimGroundingSchemaError, match="external_ids"):
        ClaimGroundingResponse.from_json(missing_external_ids)


def test_claim_grounding_response_rejects_invalid_status_cardinality() -> None:
    resolved_without_candidate = _resolved_response_payload()
    resolved_without_candidate["candidates"] = []
    with pytest.raises(ClaimGroundingSchemaError, match="resolved"):
        ClaimGroundingResponse.from_json(resolved_without_candidate)

    terminal_with_candidate = _resolved_response_payload()
    terminal_with_candidate["status"] = "denied"
    with pytest.raises(ClaimGroundingSchemaError, match="denied"):
        ClaimGroundingResponse.from_json(terminal_with_candidate)


def test_claim_grounding_response_rejects_network_fetch_mode_mismatch() -> None:
    payload = _resolved_response_payload()
    payload["mode"] = "local_lookup"

    with pytest.raises(ClaimGroundingSchemaError, match="performed_by_grounding_broker"):
        ClaimGroundingResponse.from_json(payload)


def test_claim_grounding_schemas_are_valid_json_objects() -> None:
    for schema_path in (
        Path("docs/schemas/claim_grounding_request.v1.schema.json"),
        Path("docs/schemas/claim_grounding_network_dispatch.v1.schema.json"),
        Path("docs/schemas/claim_grounding_response.v1.schema.json"),
    ):
        payload = json.loads(schema_path.read_text(encoding="utf-8"))
        assert payload["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert payload["additionalProperties"] is False


def test_claim_grounding_request_schema_validates_network_grant_cases() -> None:
    schema = _load_schema("claim_grounding_request.v1.schema.json")
    local_payload = _request_payload()
    network_payload = _request_payload()
    network_payload["allowed_modes"] = ["local_lookup", "network_fetch"]
    network_payload["network_grant"] = _network_grant()
    null_grant_payload = _request_payload()
    null_grant_payload["allowed_modes"] = ["network_fetch"]
    null_grant_payload["network_grant"] = None
    private_context_payload = _request_payload()
    private_context_payload["allowed_modes"] = ["network_fetch"]
    private_context_payload["network_grant"] = _network_grant()
    private_context_payload["local_context_capsule"] = {
        "mode": "local_only_redacted_hint",
        "text": "private context",
    }
    grant_without_mode_payload = _request_payload()
    grant_without_mode_payload["network_grant"] = _network_grant()
    raw_ref_payload = _request_payload()
    raw_ref_payload["source_refs"] = [
        {
            "target_table": "messages",
            "target_id": "Project Atlas private budget context",
        }
    ]
    unknown_ref_payload = _request_payload()
    unknown_ref_payload["source_refs"] = [
        {
            "target_table": "raw_chat_history",
            "target_id": "message-001",
        }
    ]
    operator_query_payload = _request_payload()
    operator_query_payload["allowed_modes"] = ["network_fetch"]
    operator_query_grant = _network_grant()
    operator_query_grant["query_text_class"] = "operator_entered"
    operator_query_payload["network_grant"] = operator_query_grant
    direct_url_payload = _request_payload()
    direct_url_payload["allowed_modes"] = ["network_fetch"]
    direct_url_grant = _network_grant()
    direct_url_grant["allowed_network_targets"] = ["public_web"]
    direct_url_payload["network_grant"] = direct_url_grant
    duplicate_modes_payload = _request_payload()
    duplicate_modes_payload["allowed_modes"] = ["local_lookup", "local_lookup"]
    duplicate_kind_payload = _request_payload()
    duplicate_kind_payload["candidate_entity_kinds"] = ["product", "product"]

    assert _schema_errors(schema, local_payload) == []
    assert _schema_errors(schema, network_payload) == []
    assert _schema_errors(schema, null_grant_payload)
    assert _schema_errors(schema, private_context_payload)
    assert _schema_errors(schema, grant_without_mode_payload)
    assert _schema_errors(schema, raw_ref_payload)
    assert _schema_errors(schema, unknown_ref_payload)
    assert _schema_errors(schema, operator_query_payload)
    assert _schema_errors(schema, direct_url_payload)
    assert _schema_errors(schema, duplicate_modes_payload)
    assert _schema_errors(schema, duplicate_kind_payload)


def test_claim_grounding_response_schema_validates_network_result() -> None:
    schema = _load_schema("claim_grounding_response.v1.schema.json")
    valid_payload = _resolved_response_payload()
    uncited_payload = _resolved_response_payload()
    candidate = dict(uncited_payload["candidates"][0])  # type: ignore[index]
    candidate["grounding_evidence_ids"] = []
    uncited_payload["candidates"] = [candidate]
    resolved_without_candidate = _resolved_response_payload()
    resolved_without_candidate["candidates"] = []
    denied_with_candidate = _resolved_response_payload()
    denied_with_candidate["status"] = "denied"
    mismatched_network_fetch = _resolved_response_payload()
    mismatched_network_fetch["mode"] = "local_lookup"

    assert _schema_errors(schema, valid_payload) == []
    assert _schema_errors(schema, uncited_payload)
    assert _schema_errors(schema, resolved_without_candidate)
    assert _schema_errors(schema, denied_with_candidate)
    assert _schema_errors(schema, mismatched_network_fetch)


def test_ground_claim_entity_locally_maps_local_evidence_to_response(
    conn: psycopg.Connection,
) -> None:
    body = "Project Atlas is a product that uses local Postgres."
    conn.execute(
        """
        INSERT INTO entity_grounding_evidence (
            tenant_id,
            corpus_id,
            query_text,
            entity_kind,
            source_url,
            source_label,
            content_hash,
            content_excerpt,
            fetched_at,
            fetch_tool_version,
            extractor_version
        )
        VALUES (
            'personal',
            'personal',
            'Project Atlas',
            'product',
            'https://example.invalid/project-atlas',
            'Local fixture',
            %s,
            %s,
            '2026-05-18T00:00:00Z',
            'manual.local.test',
            'none'
        )
        """,
        (hashlib.sha256(body.encode("utf-8")).hexdigest(), body),
    )
    request = ClaimGroundingRequest.from_json(_request_payload())

    response = ground_claim_entity_locally(conn, request, created_at="2026-05-18T00:00:01Z")

    assert response.status == "resolved"
    assert response.mode == "local_lookup"
    assert response.network_fetch == "not_requested"
    assert response.candidates[0].entity_kind == "product"
    assert response.candidates[0].source_label == "Local fixture"
    ClaimGroundingResponse.from_json(response.to_json())


def test_ground_claim_entity_locally_filters_policy_disallowed_evidence(
    conn: psycopg.Connection,
) -> None:
    body = "Project Atlas has a private finance reference."
    conn.execute(
        """
        INSERT INTO entity_grounding_evidence (
            tenant_id,
            corpus_id,
            query_text,
            entity_kind,
            source_url,
            source_label,
            content_hash,
            content_excerpt,
            fetched_at,
            fetch_tool_version,
            extractor_version,
            privacy_tier,
            sensitivity_class
        )
        VALUES (
            'personal',
            'personal',
            'Project Atlas',
            'product',
            'https://example.invalid/private-atlas',
            'Private fixture',
            %s,
            %s,
            '2026-05-18T00:00:00Z',
            'manual.local.test',
            'none',
            3,
            'finance'
        )
        """,
        (hashlib.sha256(body.encode("utf-8")).hexdigest(), body),
    )
    request = ClaimGroundingRequest.from_json(_request_payload())

    response = ground_claim_entity_locally(conn, request, created_at="2026-05-18T00:00:01Z")

    assert response.status == "not_found"
    assert response.candidates == ()
    assert {omission.reason for omission in response.omissions} == {
        "local_lookup_no_result",
        "policy_filtered_grounding_evidence",
    }


def test_ground_claim_entity_locally_defers_network_granted_miss_without_fetch(
    conn: psycopg.Connection,
) -> None:
    payload = _request_payload()
    payload["surface_form"] = "Missing Product"
    payload["allowed_modes"] = ["local_lookup", "network_fetch"]
    grant = _network_grant()
    grant["search_query"] = "Missing Product"
    payload["network_grant"] = grant
    request = ClaimGroundingRequest.from_json(payload)

    response = ground_claim_entity_locally(conn, request, created_at="2026-05-18T00:00:01Z")

    assert response.status == "deferred"
    assert response.network_fetch == "unsupported"
    assert response.omissions[0].reason == "network_fetch_not_implemented"
    assert response.candidates == ()


def _load_schema(filename: str) -> dict[str, object]:
    path = Path("docs/schemas") / filename
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _schema_errors(schema: Mapping[str, object], payload: object) -> list[str]:
    return _validate_schema_node(schema, payload, root=schema, path="$")


def _validate_schema_node(
    schema: Mapping[str, object],
    payload: object,
    *,
    root: Mapping[str, object],
    path: str,
) -> list[str]:
    ref = schema.get("$ref")
    if isinstance(ref, str):
        return _validate_schema_node(_resolve_schema_ref(root, ref), payload, root=root, path=path)

    errors: list[str] = []
    const = schema.get("const")
    if "const" in schema and payload != const:
        errors.append(f"{path} must equal {const!r}")
    enum = schema.get("enum")
    if isinstance(enum, Sequence) and not isinstance(enum, str | bytes | bytearray):
        if payload not in enum:
            errors.append(f"{path} must be one of {list(enum)!r}")

    schema_type = schema.get("type")
    if schema_type is not None and not _matches_schema_type(payload, schema_type):
        errors.append(f"{path} has wrong type")
        return errors

    if isinstance(payload, str):
        errors.extend(_validate_string_constraints(schema, payload, path=path))
    if isinstance(payload, int | float) and not isinstance(payload, bool):
        errors.extend(_validate_number_constraints(schema, payload, path=path))
    if isinstance(payload, Mapping):
        errors.extend(_validate_object_schema(schema, payload, root=root, path=path))
    if isinstance(payload, Sequence) and not isinstance(payload, str | bytes | bytearray):
        errors.extend(_validate_array_schema(schema, payload, root=root, path=path))

    for option in _mapping_sequence(schema.get("allOf")):
        if_schema = option.get("if")
        then_schema = option.get("then")
        if isinstance(if_schema, Mapping) and isinstance(then_schema, Mapping):
            if not _validate_schema_node(if_schema, payload, root=root, path=path):
                errors.extend(_validate_schema_node(then_schema, payload, root=root, path=path))
        else:
            errors.extend(_validate_schema_node(option, payload, root=root, path=path))

    one_of = _mapping_sequence(schema.get("oneOf"))
    if one_of:
        match_count = sum(
            1
            for option in one_of
            if not _validate_schema_node(option, payload, root=root, path=path)
        )
        if match_count != 1:
            errors.append(f"{path} must match exactly one oneOf branch")
    return errors


def _validate_object_schema(
    schema: Mapping[str, object],
    payload: Mapping[object, object],
    *,
    root: Mapping[str, object],
    path: str,
) -> list[str]:
    errors: list[str] = []
    required = schema.get("required")
    if isinstance(required, Sequence) and not isinstance(required, str | bytes | bytearray):
        for key in required:
            if isinstance(key, str) and key not in payload:
                errors.append(f"{path}.{key} is required")
    properties = schema.get("properties")
    if isinstance(properties, Mapping):
        if schema.get("additionalProperties") is False:
            unknown = sorted(str(key) for key in payload if key not in properties)
            if unknown:
                errors.append(f"{path} has unknown keys: {unknown!r}")
        for key, nested_schema in properties.items():
            if key in payload and isinstance(key, str) and isinstance(nested_schema, Mapping):
                errors.extend(
                    _validate_schema_node(
                        nested_schema,
                        payload[key],
                        root=root,
                        path=f"{path}.{key}",
                    )
                )
    return errors


def _validate_array_schema(
    schema: Mapping[str, object],
    payload: Sequence[object],
    *,
    root: Mapping[str, object],
    path: str,
) -> list[str]:
    errors: list[str] = []
    min_items = schema.get("minItems")
    if isinstance(min_items, int) and len(payload) < min_items:
        errors.append(f"{path} needs at least {min_items} items")
    max_items = schema.get("maxItems")
    if isinstance(max_items, int) and len(payload) > max_items:
        errors.append(f"{path} allows at most {max_items} items")
    if schema.get("uniqueItems") is True and len(set(map(json.dumps, payload))) != len(payload):
        errors.append(f"{path} items must be unique")
    items_schema = schema.get("items")
    if isinstance(items_schema, Mapping):
        for index, item in enumerate(payload):
            errors.extend(
                _validate_schema_node(
                    items_schema,
                    item,
                    root=root,
                    path=f"{path}[{index}]",
                )
            )
    contains_schema = schema.get("contains")
    if isinstance(contains_schema, Mapping) and not any(
        not _validate_schema_node(contains_schema, item, root=root, path=f"{path}[]")
        for item in payload
    ):
        errors.append(f"{path} does not contain required item")
    return errors


def _validate_string_constraints(
    schema: Mapping[str, object],
    payload: str,
    *,
    path: str,
) -> list[str]:
    errors: list[str] = []
    min_length = schema.get("minLength")
    max_length = schema.get("maxLength")
    pattern = schema.get("pattern")
    if isinstance(min_length, int) and len(payload) < min_length:
        errors.append(f"{path} is shorter than {min_length}")
    if isinstance(max_length, int) and len(payload) > max_length:
        errors.append(f"{path} is longer than {max_length}")
    if isinstance(pattern, str) and re.fullmatch(pattern, payload) is None:
        errors.append(f"{path} does not match pattern")
    return errors


def _validate_number_constraints(
    schema: Mapping[str, object],
    payload: int | float,
    *,
    path: str,
) -> list[str]:
    errors: list[str] = []
    minimum = schema.get("minimum")
    maximum = schema.get("maximum")
    if isinstance(minimum, int | float) and payload < minimum:
        errors.append(f"{path} is below minimum")
    if isinstance(maximum, int | float) and payload > maximum:
        errors.append(f"{path} is above maximum")
    return errors


def _matches_schema_type(payload: object, schema_type: object) -> bool:
    if isinstance(schema_type, Sequence) and not isinstance(schema_type, str | bytes | bytearray):
        return any(_matches_schema_type(payload, nested_type) for nested_type in schema_type)
    if schema_type == "null":
        return payload is None
    if schema_type == "string":
        return isinstance(payload, str)
    if schema_type == "integer":
        return isinstance(payload, int) and not isinstance(payload, bool)
    if schema_type == "number":
        return isinstance(payload, int | float) and not isinstance(payload, bool)
    if schema_type == "object":
        return isinstance(payload, Mapping)
    if schema_type == "array":
        return isinstance(payload, Sequence) and not isinstance(payload, str | bytes | bytearray)
    return True


def _mapping_sequence(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _resolve_schema_ref(root: Mapping[str, object], ref: str) -> Mapping[str, object]:
    if not ref.startswith("#/"):
        raise AssertionError(f"unsupported schema ref: {ref}")
    current: object = root
    for part in ref[2:].split("/"):
        assert isinstance(current, Mapping)
        current = current[part]
    assert isinstance(current, Mapping)
    return current
