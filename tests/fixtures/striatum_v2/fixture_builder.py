"""Build and validate EG-010 Striatum V2-compatible fixture bundles.

The fixtures in this directory intentionally remain ingest-compatible with
Engram's current `striatum.corpus_export.v1` loader while carrying V2-style
metadata fields needed by future gates. Regenerate committed fixture files with:

    python tests/fixtures/striatum_v2/fixture_builder.py
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engram.striatum_ingest import (
    JSONL_FILES,
    SCHEMA_VERSION,
    StriatumBundle,
    canonical_manifest_sha256,
    load_striatum_bundle,
)

# JSON fixture payloads are intentionally open at the disk-boundary edge.
JsonObject = dict[str, Any]

FIXTURE_CONTRACT = "eg-010-v2-compatible"
FIXTURE_GENERATED_AT = "2026-05-15T00:00:00Z"
FIXTURE_COMMIT = "eg010v2fixture000000000000000000000000000000"
FIXTURE_REPO_ROOT = "/home/halbritt/git/engram"


@dataclass(frozen=True)
class FixtureValidationResult:
    """Validation evidence for one EG-010 scenario fixture."""

    scenario: str
    path: Path
    bundle_id: str
    manifest_hash: str
    row_counts: dict[str, int]
    records_seen: int


def validate_fixture(bundle_dir: Path) -> FixtureValidationResult:
    """Parse a scenario bundle and verify manifest/hash/V2 metadata."""
    bundle = load_striatum_bundle(bundle_dir)
    manifest_hash = canonical_manifest_sha256(bundle.manifest)
    if bundle.manifest.get("bundle_sha256") != manifest_hash:
        raise AssertionError("manifest bundle_sha256 does not match canonical hash")
    if bundle.bundle_id != manifest_hash:
        raise AssertionError("loader bundle_id does not match manifest hash")

    scenario = _required_manifest_string(bundle, "fixture_scenario")
    if bundle.manifest.get("fixture_contract") != FIXTURE_CONTRACT:
        raise AssertionError("manifest fixture_contract is not EG-010 V2-compatible")

    for row in bundle.rows:
        _validate_v2_row(bundle, scenario=scenario, row=row.raw_payload)

    return FixtureValidationResult(
        scenario=scenario,
        path=bundle.root,
        bundle_id=bundle.bundle_id,
        manifest_hash=manifest_hash,
        row_counts=dict(bundle.row_counts),
        records_seen=len(bundle.rows),
    )


def build_all(root: Path | None = None) -> list[FixtureValidationResult]:
    """Write every committed EG-010 scenario fixture and validate it."""
    fixture_root = root if root is not None else Path(__file__).parent
    results: list[FixtureValidationResult] = []
    for scenario, rows in _scenario_rows().items():
        scenario_dir = fixture_root / scenario
        scenario_dir.mkdir(parents=True, exist_ok=True)
        _write_bundle(scenario_dir, scenario=scenario, rows=rows)
        results.append(validate_fixture(scenario_dir))
    return results


def _required_manifest_string(bundle: StriatumBundle, key: str) -> str:
    value = bundle.manifest.get(key)
    if not isinstance(value, str) or value.strip() == "":
        raise AssertionError(f"manifest {key} must be a non-empty string")
    return value


def _validate_v2_row(bundle: StriatumBundle, *, scenario: str, row: JsonObject) -> None:
    # JSON rows are intentionally open at the fixture edge; this helper checks
    # the stable V2-compatible fields the EG-010 scenarios depend on.
    for key in (
        "item_id",
        "logical_id",
        "version_id",
        "tenant_id",
        "corpus_id",
        "privacy_tier",
        "redaction_state",
        "visibility",
        "stability_class",
        "authority_class",
        "confidence",
        "content_sha256",
        "record_sha256",
    ):
        if key not in row:
            raise AssertionError(f"fixture row missing {key}: {scenario}")

    if row["tenant_id"] != "striatum":
        raise AssertionError("fixture rows must stay inside the striatum tenant")
    if not str(row["corpus_id"]).startswith("striatum"):
        raise AssertionError("fixture corpus_id must be striatum or striatum:<name>")
    if not _is_sha256_field(row["content_sha256"]):
        raise AssertionError("row content_sha256 must be sha256:<hex>")
    if not _is_sha256_field(row["record_sha256"]):
        raise AssertionError("row record_sha256 must be sha256:<hex>")

    content = row.get("content")
    if not isinstance(content, str):
        raise AssertionError("fixture content must be text")
    expected_content_hash = f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"
    if row["content_sha256"] != expected_content_hash:
        raise AssertionError("row content_sha256 does not match content")

    record_payload = dict(row)
    expected_record_hash = record_payload.pop("record_sha256")
    actual_record_hash = f"sha256:{_canonical_json_hash(record_payload)}"
    if expected_record_hash != actual_record_hash:
        raise AssertionError("row record_sha256 does not match canonical row")

    if row.get("fixture_scenario") != scenario:
        raise AssertionError("row fixture_scenario does not match manifest")
    provenance = row.get("provenance")
    if not isinstance(provenance, dict) or not isinstance(provenance.get("path"), str):
        raise AssertionError("fixture row provenance.path is required")
    if provenance["path"].startswith("/"):
        raise AssertionError("fixture paths must be repository-relative")


def _is_sha256_field(value: object) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(char in "0123456789abcdef" for char in digest)


def _write_bundle(root: Path, *, scenario: str, rows: list[JsonObject]) -> None:
    rows_by_kind: dict[str, list[JsonObject]] = {sub_kind: [] for sub_kind in JSONL_FILES}
    for row in rows:
        rows_by_kind[str(row["sub_kind"])].append(row)

    files: dict[str, dict[str, int | str]] = {}
    row_counts: dict[str, int] = {}
    for sub_kind, filename in JSONL_FILES.items():
        ordered = sorted(rows_by_kind[sub_kind], key=lambda item: str(item["external_id"]))
        lines = [json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in ordered]
        body = ("\n".join(lines) + "\n").encode("utf-8")
        (root / filename).write_bytes(body)
        files[filename] = {
            "sha256": hashlib.sha256(body).hexdigest(),
            "rows": len(ordered),
            "bytes": len(body),
        }
        row_counts[sub_kind] = len(ordered)

    manifest: JsonObject = {
        "schema_version": SCHEMA_VERSION,
        "fixture_contract": FIXTURE_CONTRACT,
        "fixture_scenario": scenario,
        "striatum_version": "eg-010-v2-fixture",
        "repo_root": FIXTURE_REPO_ROOT,
        "git_head": FIXTURE_COMMIT,
        "git_dirty": False,
        "since_ref": f"eg-010/{scenario}",
        "since_commit": FIXTURE_COMMIT,
        "generated_at": FIXTURE_GENERATED_AT,
        "schema": {
            "row_shape_version": "striatum.corpus_row.v2-compatible",
            "sub_kinds": list(JSONL_FILES),
        },
        "source_kinds": ["striatum"],
        "tenant_id": "striatum",
        "corpus_ids": sorted({str(row["corpus_id"]) for row in rows}),
        "row_counts": row_counts,
        "files": files,
        "repo_local_schema_version": 14,
        "missing_optional_sources": [],
        "daemon_audit_included": False,
    }
    manifest["bundle_sha256"] = canonical_manifest_sha256(manifest)
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _scenario_rows() -> dict[str, list[JsonObject]]:
    return {
        "minimal": [
            _row(
                scenario="minimal",
                sub_kind="rfc",
                external_id="rfc:0045#minimal-v2-bundle",
                logical_id="rfc:0045",
                version_id="rfc:0045@eg010-minimal",
                content=(
                    "EG-010 minimal fixture row: RFC 0045 proposes a local "
                    "Striatum Corpus Contract V2 bundle with manifest-backed "
                    "JSONL streams and deterministic hashes."
                ),
                path="docs/rfcs/0045-striatum-corpus-contract-v2.md",
            ),
        ],
        "multi_corpus_isolation": [
            _row(
                scenario="multi_corpus_isolation",
                sub_kind="rfc",
                external_id="rfc:0044#primary-corpus",
                logical_id="rfc:0044",
                version_id="rfc:0044@primary",
                content="Primary striatum corpus row for EG-010 multi-corpus isolation.",
                path="docs/rfcs/0044-striatum-memory-phase1.md",
                corpus_id="striatum",
            ),
            _row(
                scenario="multi_corpus_isolation",
                sub_kind="operator_report",
                external_id="operator_report:eg010-secondary-corpus",
                logical_id="operator_report:eg010-secondary-corpus",
                version_id="operator_report:eg010-secondary-corpus@v1",
                content="Secondary striatum:eg010 corpus row used only for isolation checks.",
                path="docs/reviews/eg-010/secondary-corpus.md",
                corpus_id="striatum:eg010",
            ),
        ],
        "redaction": [
            _row(
                scenario="redaction",
                sub_kind="operator_report",
                external_id="operator_report:eg010-redaction-withheld",
                logical_id="operator_report:eg010-redaction-withheld",
                version_id="operator_report:eg010-redaction-withheld@withheld",
                content=(
                    "[withheld by EG-010 fixture policy: content above caller "
                    "privacy tier is not present in this committed bundle]"
                ),
                path="docs/reviews/eg-010/redaction-withheld.md",
                redaction_state="withheld",
                privacy_tier=2,
                confidence=1.0,
            ),
            _row(
                scenario="redaction",
                sub_kind="changelog_entry",
                external_id="changelog:eg010-redaction-notice",
                logical_id="changelog:eg010-redaction-notice",
                version_id="changelog:eg010-redaction-notice@v1",
                content=(
                    "EG-010 redaction notice: withheld fixture content is "
                    "represented by deterministic notices only."
                ),
                path="CHANGELOG.md#eg010-redaction-notice",
                redaction_state="synthetic_summary",
            ),
        ],
        "tombstone": [
            _row(
                scenario="tombstone",
                sub_kind="decision_log_row",
                external_id="decision:EG010-TOMBSTONE#v1",
                logical_id="decision:EG010-TOMBSTONE",
                version_id="decision:EG010-TOMBSTONE@v1",
                content="EG-010 tombstone fixture prior active decision row.",
                path="DECISION_LOG.md#EG010-TOMBSTONE",
                lifecycle_state="active",
            ),
            _row(
                scenario="tombstone",
                sub_kind="audit_chain_entry",
                external_id="audit:EG010-TOMBSTONE#tombstone",
                logical_id="decision:EG010-TOMBSTONE",
                version_id="decision:EG010-TOMBSTONE@tombstone",
                content=(
                    "EG-010 tombstone fixture invalidates logical item "
                    "decision:EG010-TOMBSTONE for incremental-bundle tests."
                ),
                path="docs/reviews/eg-010/tombstone.md",
                lifecycle_state="tombstone",
            ),
        ],
    }


def _row(
    *,
    scenario: str,
    sub_kind: str,
    external_id: str,
    logical_id: str,
    version_id: str,
    content: str,
    path: str,
    corpus_id: str = "striatum",
    redaction_state: str = "none",
    privacy_tier: int = 1,
    confidence: float = 0.95,
    lifecycle_state: str = "active",
) -> JsonObject:
    content_sha256 = f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"
    row: JsonObject = {
        "source_kind": "striatum",
        "tenant_id": "striatum",
        "corpus_id": corpus_id,
        "external_id": external_id,
        "item_id": f"{scenario}:{sub_kind}:{external_id}",
        "logical_id": logical_id,
        "version_id": version_id,
        "sub_kind": sub_kind,
        "content": content,
        "content_sha256": content_sha256,
        "record_sha256": "sha256:pending",
        "observed_at": FIXTURE_GENERATED_AT,
        "recorded_at": FIXTURE_GENERATED_AT,
        "emitted_at": FIXTURE_GENERATED_AT,
        "provenance": {
            "path": path,
            "logical_path": path,
            "commit": FIXTURE_COMMIT,
            "sha256": content_sha256.removeprefix("sha256:"),
        },
        "privacy_tier": privacy_tier,
        "redaction_state": redaction_state,
        "visibility": "operator_visible",
        "stability_class": "proposal",
        "authority_class": "fixture",
        "confidence": confidence,
        "lifecycle_state": lifecycle_state,
        "fixture_scenario": scenario,
    }
    record_payload = dict(row)
    record_payload.pop("record_sha256")
    row["record_sha256"] = f"sha256:{_canonical_json_hash(record_payload)}"
    return row


def _canonical_json_hash(payload: JsonObject) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    results = build_all()
    for result in results:
        print(f"{result.scenario}: {result.records_seen} rows {result.manifest_hash}")


if __name__ == "__main__":
    main()
