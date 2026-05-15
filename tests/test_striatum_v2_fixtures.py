from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Protocol, cast

import pytest

from engram.striatum_ingest import (
    JSONL_FILES,
    ManifestValidationError,
    load_striatum_bundle,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "striatum_v2"
SCENARIOS = ("minimal", "multi_corpus_isolation", "redaction", "tombstone")


class FixtureValidationResult(Protocol):
    """Validation evidence returned by the EG-010 helper."""

    scenario: str
    path: Path
    bundle_id: str
    manifest_hash: str
    row_counts: dict[str, int]
    records_seen: int


class FixtureBuilderModule(Protocol):
    """Runtime shape of tests/fixtures/striatum_v2/fixture_builder.py."""

    def validate_fixture(self, bundle_dir: Path) -> FixtureValidationResult:
        """Validate one scenario fixture."""


def _load_fixture_builder() -> FixtureBuilderModule:
    helper_path = FIXTURE_ROOT / "fixture_builder.py"
    spec = importlib.util.spec_from_file_location("striatum_v2_fixture_builder", helper_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["striatum_v2_fixture_builder"] = module
    spec.loader.exec_module(module)
    return cast(FixtureBuilderModule, module)


FIXTURE_BUILDER = _load_fixture_builder()


def test_eg010_v2_scenarios_validate_through_existing_ingest_loader() -> None:
    results = [
        FIXTURE_BUILDER.validate_fixture(FIXTURE_ROOT / scenario) for scenario in SCENARIOS
    ]

    assert [result.scenario for result in results] == list(SCENARIOS)
    assert [result.records_seen for result in results] == [1, 2, 2, 2]
    for result in results:
        assert result.bundle_id == result.manifest_hash
        assert set(result.row_counts) == set(JSONL_FILES)


def test_eg010_v2_scenario_metadata_is_committed_and_non_private() -> None:
    minimal = load_striatum_bundle(FIXTURE_ROOT / "minimal")
    multi_corpus = load_striatum_bundle(FIXTURE_ROOT / "multi_corpus_isolation")
    redaction = load_striatum_bundle(FIXTURE_ROOT / "redaction")
    tombstone = load_striatum_bundle(FIXTURE_ROOT / "tombstone")

    assert minimal.manifest["fixture_contract"] == "eg-010-v2-compatible"
    assert minimal.manifest["fixture_scenario"] == "minimal"
    assert minimal.manifest["corpus_ids"] == ["striatum"]

    multi_corpus_ids = {row.raw_payload["corpus_id"] for row in multi_corpus.rows}
    assert multi_corpus_ids == {"striatum", "striatum:eg010"}

    redaction_rows = {row.external_id: row.raw_payload for row in redaction.rows}
    withheld = redaction_rows["operator_report:eg010-redaction-withheld"]
    assert withheld["redaction_state"] == "withheld"
    assert withheld["privacy_tier"] == 2
    assert "content above caller privacy tier is not present" in withheld["content"]

    lifecycle_states = {row.raw_payload["lifecycle_state"] for row in tombstone.rows}
    assert lifecycle_states == {"active", "tombstone"}

    for bundle in (minimal, multi_corpus, redaction, tombstone):
        assert bundle.manifest["tenant_id"] == "striatum"
        for row in bundle.rows:
            provenance = row.raw_payload["provenance"]
            assert isinstance(provenance, dict)
            assert not str(provenance["path"]).startswith("/")


def test_eg010_v2_fixture_validation_fails_closed_on_file_tamper(tmp_path: Path) -> None:
    tampered = tmp_path / "minimal"
    shutil.copytree(FIXTURE_ROOT / "minimal", tampered)

    row = json.loads((tampered / "rfcs.jsonl").read_text(encoding="utf-8").splitlines()[0])
    row["content"] = "tampered fixture content"
    (tampered / "rfcs.jsonl").write_text(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ManifestValidationError, match="hash mismatch"):
        FIXTURE_BUILDER.validate_fixture(tampered)


def test_eg010_v2_fixture_validation_checks_manifest_bundle_hash(tmp_path: Path) -> None:
    invalid = tmp_path / "minimal"
    shutil.copytree(FIXTURE_ROOT / "minimal", invalid)

    manifest_path = invalid / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["bundle_sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ManifestValidationError, match="bundle_sha256"):
        FIXTURE_BUILDER.validate_fixture(invalid)
