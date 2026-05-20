from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb
from test_context_for import insert_context_belief

from engram.context_eval import CONTEXT_EVAL_DATASET_GOLD_FILENAME
from engram.phase4 import refresh_current_beliefs

SYNTHETIC_CONTEXT_E2E_DIR = (
    Path(__file__).parent / "fixtures" / "context_eval" / "synthetic_e2e"
)
SYNTHETIC_CONTEXT_CORPUS_FILENAME = "corpus.json"
SYNTHETIC_CONTEXT_CORPUS_SCHEMA_VERSION = "context_eval.synthetic_corpus.v1"


@dataclass(frozen=True)
class SyntheticBelief:
    external_id: str
    message_text: str
    predicate: str
    object_text: str
    confidence: float
    privacy_tier: int
    sensitivity_class: str
    claim_stability_class: str | None = None


@dataclass(frozen=True)
class SyntheticCapture:
    external_id: str
    content_text: str
    privacy_tier: int
    sensitivity_class: str


@dataclass(frozen=True)
class SyntheticGroundingEvidence:
    query_text: str
    entity_kind: str
    source_url: str
    source_label: str
    content_excerpt: str
    fetched_at: str
    fetch_tool_version: str
    extractor_version: str
    privacy_tier: int
    sensitivity_class: str


@dataclass(frozen=True)
class SyntheticContextEvalDataset:
    root: Path
    gold_set_path: Path
    beliefs: tuple[SyntheticBelief, ...]
    captures: tuple[SyntheticCapture, ...]
    grounding_evidence: tuple[SyntheticGroundingEvidence, ...]


@dataclass(frozen=True)
class SyntheticContextSeedResult:
    belief_count: int
    capture_count: int
    grounding_evidence_count: int
    gold_set_path: Path


def load_synthetic_context_eval_dataset(
    dataset_dir: Path = SYNTHETIC_CONTEXT_E2E_DIR,
) -> SyntheticContextEvalDataset:
    """Load the public synthetic context-eval corpus fixture."""
    root = Path(dataset_dir)
    payload = _load_json_object(root / SYNTHETIC_CONTEXT_CORPUS_FILENAME)
    schema_version = _required_str(payload, "schema_version")
    if schema_version != SYNTHETIC_CONTEXT_CORPUS_SCHEMA_VERSION:
        raise ValueError(f"unsupported synthetic corpus schema: {schema_version}")
    beliefs = tuple(
        _belief_from_payload(item, index=index)
        for index, item in enumerate(_required_list(payload, "beliefs"), start=1)
    )
    captures = tuple(
        _capture_from_payload(item, index=index)
        for index, item in enumerate(_required_list(payload, "captures"), start=1)
    )
    grounding_evidence = tuple(
        _grounding_from_payload(item, index=index)
        for index, item in enumerate(
            _required_list(payload, "grounding_evidence"),
            start=1,
        )
    )
    return SyntheticContextEvalDataset(
        root=root,
        gold_set_path=root / CONTEXT_EVAL_DATASET_GOLD_FILENAME,
        beliefs=beliefs,
        captures=captures,
        grounding_evidence=grounding_evidence,
    )


def seed_synthetic_context_eval_dataset(
    conn: psycopg.Connection,
    dataset_dir: Path = SYNTHETIC_CONTEXT_E2E_DIR,
) -> SyntheticContextSeedResult:
    """Seed the synthetic context-eval corpus into an empty test database."""
    dataset = load_synthetic_context_eval_dataset(dataset_dir)
    for belief in dataset.beliefs:
        evidence_message_id = insert_stable_evidence_message(
            conn,
            external_id=belief.external_id,
            content_text=belief.message_text,
        )
        insert_context_belief(
            conn,
            message_text=belief.message_text,
            predicate=belief.predicate,
            object_text=belief.object_text,
            confidence=belief.confidence,
            privacy_tier=belief.privacy_tier,
            sensitivity_class=belief.sensitivity_class,
            claim_stability_class=belief.claim_stability_class,
            evidence_message_id=evidence_message_id,
        )
    for capture in dataset.captures:
        insert_stable_capture(conn, capture)
    for grounding in dataset.grounding_evidence:
        insert_grounding_evidence(conn, grounding)
    refresh_current_beliefs(conn)
    return SyntheticContextSeedResult(
        belief_count=len(dataset.beliefs),
        capture_count=len(dataset.captures),
        grounding_evidence_count=len(dataset.grounding_evidence),
        gold_set_path=dataset.gold_set_path,
    )


def insert_stable_evidence_message(
    conn: psycopg.Connection,
    *,
    external_id: str,
    content_text: str,
) -> str:
    """Insert one deterministic message used as cited synthetic evidence."""
    source_id = conn.execute(
        """
        INSERT INTO sources (source_kind, external_id, raw_payload)
        VALUES ('chatgpt', %s, '{}')
        RETURNING id
        """,
        (f"source:{external_id}",),
    ).fetchone()[0]
    conversation_id = conn.execute(
        """
        INSERT INTO conversations (
            source_id,
            source_kind,
            external_id,
            raw_payload,
            title
        )
        VALUES (%s, 'chatgpt', %s, '{}', 'synthetic context eval')
        RETURNING id
        """,
        (source_id, f"conversation:{external_id}"),
    ).fetchone()[0]
    return conn.execute(
        """
        INSERT INTO messages (
            source_id,
            source_kind,
            conversation_id,
            external_id,
            raw_payload,
            role,
            content_text,
            sequence_index
        )
        VALUES (%s, 'chatgpt', %s, %s, '{}', 'user', %s, 0)
        RETURNING id::text
        """,
        (source_id, conversation_id, external_id, content_text),
    ).fetchone()[0]


def insert_stable_capture(conn: psycopg.Connection, capture: SyntheticCapture) -> str:
    """Insert one deterministic synthetic capture used by context eval."""
    source_id = conn.execute(
        """
        INSERT INTO sources (source_kind, external_id, raw_payload)
        VALUES ('capture', %s, '{}')
        RETURNING id
        """,
        (f"source:{capture.external_id}",),
    ).fetchone()[0]
    return conn.execute(
        """
        INSERT INTO captures (
            source_id,
            source_kind,
            external_id,
            raw_payload,
            privacy_tier,
            capture_type,
            content_text,
            observed_at
        )
        VALUES (%s, 'capture', %s, %s, %s, 'observation', %s, now())
        RETURNING id::text
        """,
        (
            source_id,
            capture.external_id,
            Jsonb({"sensitivity_class": capture.sensitivity_class}),
            capture.privacy_tier,
            capture.content_text,
        ),
    ).fetchone()[0]


def insert_grounding_evidence(
    conn: psycopg.Connection,
    grounding: SyntheticGroundingEvidence,
) -> str:
    """Insert one local web-search-style grounding row for entity typing."""
    content_hash = hashlib.sha256(grounding.content_excerpt.encode("utf-8")).hexdigest()
    return conn.execute(
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
            sensitivity_class,
            raw_payload
        )
        VALUES (
            'personal',
            'personal',
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
        RETURNING id::text
        """,
        (
            grounding.query_text,
            grounding.entity_kind,
            grounding.source_url,
            grounding.source_label,
            content_hash,
            grounding.content_excerpt,
            grounding.fetched_at,
            grounding.fetch_tool_version,
            grounding.extractor_version,
            grounding.privacy_tier,
            grounding.sensitivity_class,
            Jsonb(
                {
                    "fixture": "context_eval.synthetic_e2e",
                    "network_fetch": False,
                    "websearch_grounding_synthetic": True,
                }
            ),
        ),
    ).fetchone()[0]


def _load_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return payload


def _belief_from_payload(value: object, *, index: int) -> SyntheticBelief:
    payload = _required_mapping(value, f"beliefs[{index}]")
    return SyntheticBelief(
        external_id=_required_str(payload, "external_id"),
        message_text=_required_str(payload, "message_text"),
        predicate=_required_str(payload, "predicate"),
        object_text=_required_str(payload, "object_text"),
        confidence=_required_float(payload, "confidence"),
        privacy_tier=_required_int(payload, "privacy_tier"),
        sensitivity_class=_required_str(payload, "sensitivity_class"),
        claim_stability_class=_optional_str(payload, "claim_stability_class"),
    )


def _capture_from_payload(value: object, *, index: int) -> SyntheticCapture:
    payload = _required_mapping(value, f"captures[{index}]")
    return SyntheticCapture(
        external_id=_required_str(payload, "external_id"),
        content_text=_required_str(payload, "content_text"),
        privacy_tier=_required_int(payload, "privacy_tier"),
        sensitivity_class=_required_str(payload, "sensitivity_class"),
    )


def _grounding_from_payload(
    value: object,
    *,
    index: int,
) -> SyntheticGroundingEvidence:
    payload = _required_mapping(value, f"grounding_evidence[{index}]")
    return SyntheticGroundingEvidence(
        query_text=_required_str(payload, "query_text"),
        entity_kind=_required_str(payload, "entity_kind"),
        source_url=_required_str(payload, "source_url"),
        source_label=_required_str(payload, "source_label"),
        content_excerpt=_required_str(payload, "content_excerpt"),
        fetched_at=_required_str(payload, "fetched_at"),
        fetch_tool_version=_required_str(payload, "fetch_tool_version"),
        extractor_version=_required_str(payload, "extractor_version"),
        privacy_tier=_required_int(payload, "privacy_tier"),
        sensitivity_class=_required_str(payload, "sensitivity_class"),
    )


def _required_mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _required_list(payload: dict[str, object], key: str) -> list[object]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    return value


def _required_str(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_str(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(f"{key} must be a non-empty string when present")
    return value


def _required_float(payload: dict[str, object], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, int | float):
        raise ValueError(f"{key} must be a number")
    return float(value)


def _required_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value
