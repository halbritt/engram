"""Tests for ``scripts/cross_corpus_dryrun.py``.

These tests must run without a real Obsidian vault and without calling a
real LLM. The harness is a scaffolding deliverable for RFC-0017 Part 3;
its value is the wiring + reporting, so the assertions focus on
discovery, sample shape, and the privacy contract (no raw corpus content
in the findings doc).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Make ``scripts/cross_corpus_dryrun.py`` importable as a module.
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import cross_corpus_dryrun as harness  # noqa: E402


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------


def test_walks_input_dir_for_markdown(tmp_path: Path) -> None:
    _write(tmp_path / "note1.md", "# Note 1\n\nbody one")
    _write(tmp_path / "note2.md", "# Note 2\n\nbody two")
    _write(tmp_path / "note3.md", "# Note 3\n\nbody three")
    _write(tmp_path / "skip.txt", "not a markdown file")

    paths = sorted(p.name for p in harness.iter_markdown_files(tmp_path))
    assert paths == ["note1.md", "note2.md", "note3.md"]


def test_skips_hidden_dirs_and_obsidian_config(tmp_path: Path) -> None:
    _write(tmp_path / "note1.md", "# Note 1")
    _write(tmp_path / ".obsidian" / "config.md", "# Should be skipped")
    _write(tmp_path / ".git" / "HEAD.md", "# Should be skipped")
    _write(tmp_path / ".trash" / "old.md", "# Should be skipped")
    _write(tmp_path / "subdir" / "note2.md", "# Note 2")

    found = sorted(p.name for p in harness.iter_markdown_files(tmp_path))
    assert found == ["note1.md", "note2.md"]


# --------------------------------------------------------------------------
# Splitting / sample shape
# --------------------------------------------------------------------------


def test_splits_long_notes_on_h2_headings(tmp_path: Path) -> None:
    md = (
        "# Top\n\n"
        "preamble paragraph.\n\n"
        "## Section A\n\nbody A.\n\n"
        "## Section B\n\nbody B.\n\n"
        "## Section C\n\nbody C.\n"
    )
    note = tmp_path / "long.md"
    note.write_text(md, encoding="utf-8")

    synths = harness.build_synthetic_segments(note, root=tmp_path)
    # Preamble + 3 H2 sections = 4 segments.
    assert len(synths) == 4
    bodies = [s.payload.content_text for s in synths]
    assert "preamble paragraph." in bodies[0]
    assert bodies[1].lstrip().startswith("## Section A")
    assert bodies[2].lstrip().startswith("## Section B")
    assert bodies[3].lstrip().startswith("## Section C")


def test_honors_limit(tmp_path: Path) -> None:
    for i in range(100):
        _write(tmp_path / f"note_{i:03d}.md", f"# Note {i}\n\nbody {i}\n")
    segments = harness.discover_segments(tmp_path, limit=10)
    assert len(segments) == 10


def test_synthetic_segment_has_expected_shape(tmp_path: Path) -> None:
    note = tmp_path / "shape.md"
    note.write_text("# Hi\n\ncontent body\n", encoding="utf-8")

    synths = harness.build_synthetic_segments(note, root=tmp_path)
    assert len(synths) == 1
    payload = synths[0].payload
    assert payload.source_kind == "note"
    assert payload.content_text.strip() != ""
    assert payload.message_ids and payload.messages
    assert payload.messages[0].content_text == payload.content_text
    # Deterministic id: building twice yields the same id.
    again = harness.build_synthetic_segments(note, root=tmp_path)
    assert payload.id == again[0].payload.id


# --------------------------------------------------------------------------
# Extractor wiring
# --------------------------------------------------------------------------


def test_extractor_called_once_per_synthetic_segment(tmp_path: Path) -> None:
    for i in range(5):
        _write(tmp_path / f"note_{i}.md", f"# Note {i}\n\ncontent {i}\n")
    segments = harness.discover_segments(tmp_path, limit=50)
    assert len(segments) == 5

    fake = harness.FakeExtractorClient()
    _, counts = harness.run_extraction(segments, client=fake, model_id="fake-model")
    assert fake.calls == len(segments)
    assert counts.segments_processed == len(segments)
    # Fake returns no claims, so all segments fall in zero-claims bucket.
    assert counts.segments_with_zero_claims == len(segments)
    assert counts.total_claims == 0


# --------------------------------------------------------------------------
# Privacy contract
# --------------------------------------------------------------------------


def test_findings_doc_has_no_raw_corpus_content(tmp_path: Path) -> None:
    marker = "UNIQUEMARKER123"
    _write(
        tmp_path / "secret.md",
        f"# Private Note\n\nthis content includes {marker} which must not leak\n",
    )
    output_dir = tmp_path / "out"

    rc = harness.main([
        "--input-dir", str(tmp_path),
        "--output-dir", str(output_dir),
        "--limit", "10",
        "--self-test",
    ])
    assert rc == 0

    written = list(output_dir.glob("PHASE_3_CROSS_CORPUS_DRYRUN_*.md"))
    assert len(written) == 1, "exactly one dated findings doc should be written"
    body = written[0].read_text(encoding="utf-8")
    assert marker not in body, "raw corpus content leaked into findings doc"
    # Defense-in-depth: the file path itself is also corpus-derived metadata.
    assert "secret.md" not in body
    assert str(tmp_path) not in body


def test_findings_doc_has_all_four_checklist_sections(tmp_path: Path) -> None:
    _write(tmp_path / "note.md", "# Note\n\nbody\n")
    output_dir = tmp_path / "out"
    rc = harness.main([
        "--input-dir", str(tmp_path),
        "--output-dir", str(output_dir),
        "--limit", "1",
        "--self-test",
    ])
    assert rc == 0
    written = next(output_dir.glob("PHASE_3_CROSS_CORPUS_DRYRUN_*.md"))
    body = written.read_text(encoding="utf-8")
    # The four checklist questions from RFC-0017 § Part 3 procedure step 3.
    expected_substrings = [
        "Did the extractor produce 0 claims",
        "Did the extractor force a stability_class",
        "Did the predicate vocabulary look strained",
        "Did consolidation propose contradictions",
    ]
    for needle in expected_substrings:
        assert needle in body, f"findings doc missing checklist item: {needle!r}"


# --------------------------------------------------------------------------
# Endpoint guard
# --------------------------------------------------------------------------


def test_refuses_non_local_llm_endpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(tmp_path / "note.md", "# Note\n\nbody\n")
    output_dir = tmp_path / "out"
    # Non-self-test path forces the guard. Patch the module-level constant
    # *and* the segmenter's view of it so ensure_local_base_url sees the bad URL.
    monkeypatch.setattr(harness, "IK_LLAMA_BASE_URL", "https://api.example.com")

    rc = harness.main([
        "--input-dir", str(tmp_path),
        "--output-dir", str(output_dir),
        "--limit", "1",
    ])
    assert rc == 2
    captured = capsys.readouterr()
    assert "local-only" in captured.err or "local" in captured.err.lower()


# --------------------------------------------------------------------------
# Stdout summary
# --------------------------------------------------------------------------


def test_run_summary_printed_to_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for i in range(3):
        _write(tmp_path / f"n_{i}.md", f"# Note {i}\n\nbody {i}\n")
    output_dir = tmp_path / "out"
    rc = harness.main([
        "--input-dir", str(tmp_path),
        "--output-dir", str(output_dir),
        "--limit", "5",
        "--self-test",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Segments processed:" in out
    assert "Total claims emitted:" in out
    assert "Findings doc:" in out


# --------------------------------------------------------------------------
# Bonus: empty input dir is treated as a hard error
# --------------------------------------------------------------------------


def test_empty_input_dir_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output_dir = tmp_path / "out"
    rc = harness.main([
        "--input-dir", str(tmp_path),
        "--output-dir", str(output_dir),
        "--limit", "1",
        "--self-test",
    ])
    assert rc == 2
    err = capsys.readouterr().err
    assert "no markdown files" in err.lower()
