"""Build the committed EG-000 baseline Striatum corpus fixture.

The fixture content is drawn from Engram's own public RFC and decision-log
prose so the resulting bundle is non-private and safe to commit, while
exercising the real RFC 0044 bundle shape and the
`striatum.corpus_export.v1` schema. Run this script in-place after editing
the row payloads to regenerate the JSONL files and `manifest.json` with
fresh sha256 checksums:

    python tests/fixtures/striatum_eg000/build_fixture.py

The smoke test in tests/test_striatum_ingest.py loads the result.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from engram.striatum_ingest import JSONL_FILES, SCHEMA_VERSION, canonical_manifest_sha256


def _row(sub_kind: str, external_id: str, content: str, provenance: dict[str, str]) -> dict[str, object]:
    provenance_with_hash = {
        **provenance,
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "commit": "egbaseline000",
    }
    return {
        "source_kind": "striatum",
        "external_id": external_id,
        "sub_kind": sub_kind,
        "content": content,
        "provenance": provenance_with_hash,
        "observed_at": "2026-05-15T00:00:00Z",
    }


def build_rows() -> list[dict[str, object]]:
    """Return the canonical EG-000 fixture rows."""
    return [
        _row(
            "rfc",
            "rfc:0044#hardening-baseline",
            (
                "RFC 0044 hardens the local Striatum memory boundary. The "
                "primary tenant/corpus is `striatum/striatum`; cross-tenant "
                "and cross-corpus reads require explicit capability tokens. "
                "EG-000 verifies the boundary before any projection or "
                "retrieval surfaces are built on top of it."
            ),
            {"path": "docs/rfcs/0044-striatum-memory-phase1.md"},
        ),
        _row(
            "rfc",
            "rfc:0045#corpus-contract-v2-proposal",
            (
                "RFC 0045 proposes Striatum Corpus Contract V2, defining the "
                "shape of bundles exported from Striatum into Engram for "
                "projection. The contract remains proposal-only until the "
                "AL-D001 RFC 0044 hardening evidence and the AL-D002 "
                "acceptance decision both land."
            ),
            {"path": "docs/rfcs/0045-striatum-corpus-contract-v2.md"},
        ),
        _row(
            "decision_log_row",
            "decision:D082",
            (
                "D082 reserves the `subject_kind_hint` advisory metadata "
                "slot on `predicate_vocabulary`. The hint surfaces predicate "
                "intent to extractor prompts and operator UI without "
                "constraining claims or beliefs."
            ),
            {"path": "DECISION_LOG.md#D082"},
        ),
        _row(
            "operator_report",
            "operator_report:eg-000-baseline-2026-05-15",
            (
                "EG-000 baseline operator note: the RFC 0044 boundary "
                "remains true. MemoryService search and fetch_reference "
                "enforce primary-pair semantics; MCP --capability rejects "
                "unknown memory.* names; engram.health reports the most "
                "recently applied migration rather than the lexicographic "
                "max filename."
            ),
            {"path": "OPERATOR_REPORT.md#eg-000-baseline-2026-05-15"},
        ),
        _row(
            "changelog_entry",
            "changelog:eg-000-baseline-2026-05-15",
            (
                "Engram CHANGELOG: closed EG-000 baseline gate. "
                "MemoryService.health() now sorts schema_migrations by "
                "applied_at DESC, filename DESC instead of max(filename). "
                "engram-mcp-stdio --capability rejects unknown memory.* "
                "names. engram describe-corpus requires --tenant for "
                "non-striatum corpora."
            ),
            {"path": "CHANGELOG.md#eg-000-baseline"},
        ),
    ]


def main() -> None:
    root = Path(__file__).parent
    rows = build_rows()

    rows_by_kind: dict[str, list[dict[str, object]]] = {sub_kind: [] for sub_kind in JSONL_FILES}
    for row in rows:
        rows_by_kind[str(row["sub_kind"])].append(row)

    files: dict[str, dict[str, int | str]] = {}
    row_counts: dict[str, int] = {}
    for sub_kind, filename in JSONL_FILES.items():
        ordered = sorted(rows_by_kind[sub_kind], key=lambda item: str(item["external_id"]))
        lines = [
            json.dumps(item, ensure_ascii=False, separators=(",", ":"))
            for item in ordered
        ]
        body = ("\n".join(lines) + "\n").encode("utf-8")
        (root / filename).write_bytes(body)
        files[filename] = {
            "sha256": hashlib.sha256(body).hexdigest(),
            "rows": len(ordered),
            "bytes": len(body),
        }
        row_counts[sub_kind] = len(ordered)

    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "striatum_version": "eg-000-baseline",
        "repo_root": "/home/halbritt/git/engram",
        "git_head": "egbaseline000",
        "git_dirty": False,
        "since_ref": "v0.0.0",
        "since_commit": "egbaseline000",
        "generated_at": "2026-05-15T00:00:00Z",
        "schema": {
            "row_shape_version": "striatum.corpus_row.v1",
            "sub_kinds": list(JSONL_FILES),
        },
        "source_kinds": ["striatum"],
        "row_counts": row_counts,
        "files": files,
        "repo_local_schema_version": 14,
        "missing_optional_sources": [],
        "daemon_audit_included": False,
    }
    manifest["bundle_sha256"] = canonical_manifest_sha256(manifest)
    (root / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
