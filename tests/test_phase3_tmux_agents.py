from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "phase3_tmux_agents.sh"
POSTBUILD = Path("docs/reviews/phase3/postbuild/markers")


def copy_script(tmp_path: Path) -> Path:
    script_path = tmp_path / "scripts" / "phase3_tmux_agents.sh"
    script_path.parent.mkdir(parents=True)
    shutil.copy2(SCRIPT, script_path)
    return script_path


def write_marker(root: Path, rel: Path, front_matter: dict[str, str] | None = None) -> str:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if front_matter is None:
        path.write_text("# Legacy blocked marker\n", encoding="utf-8")
        return rel.as_posix()
    lines = ["---"]
    lines.extend(f"{key}: {value}" for key, value in front_matter.items())
    lines.extend(["---", "", "# Marker", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return rel.as_posix()


def run_next(root: Path) -> subprocess.CompletedProcess[str]:
    copy_script(root)
    return subprocess.run(
        ["bash", "scripts/phase3_tmux_agents.sh", "next"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def test_unrelated_ready_marker_cannot_supersede_blocker(tmp_path):
    blocked = write_marker(
        tmp_path,
        POSTBUILD / "issue_a" / "01_RUN.blocked.md",
        {
            "issue_id": "issue_a",
            "family": "run",
            "state": "blocked",
            "gate": "blocked",
            "created_at": "2026-05-05T01:00:00Z",
        },
    )
    write_marker(
        tmp_path,
        POSTBUILD / "issue_b" / "05_REPAIR_VERIFIED.ready.md",
        {
            "issue_id": "issue_b",
            "family": "run",
            "state": "ready",
            "gate": "ready_for_next_bound",
            "created_at": "2026-05-05T02:00:00Z",
            "supersedes": blocked,
        },
    )

    result = run_next(tmp_path)

    assert result.returncode == 1
    assert "issue_a/01_RUN.blocked.md" in result.stdout


def test_same_identity_ready_marker_supersedes_blocker(tmp_path):
    blocked = write_marker(
        tmp_path,
        POSTBUILD / "issue_a" / "01_RUN.blocked.md",
        {
            "issue_id": "issue_a",
            "family": "run",
            "state": "blocked",
            "gate": "blocked",
            "created_at": "2026-05-05T01:00:00Z",
        },
    )
    write_marker(
        tmp_path,
        POSTBUILD / "issue_a" / "05_REPAIR_VERIFIED.ready.md",
        {
            "issue_id": "issue_a",
            "family": "run",
            "state": "ready",
            "gate": "ready_for_next_bound",
            "created_at": "2026-05-05T02:00:00Z",
            "supersedes": blocked,
        },
    )

    result = run_next(tmp_path)

    assert result.returncode == 0
    assert result.stdout == "01_SPEC_DRAFT.ready.md\n"


def test_newer_ready_marker_with_blocked_gate_blocks_expansion(tmp_path):
    blocked = write_marker(
        tmp_path,
        POSTBUILD / "issue_a" / "01_RUN.blocked.md",
        {
            "issue_id": "issue_a",
            "family": "run",
            "state": "blocked",
            "gate": "blocked",
            "created_at": "2026-05-05T01:00:00Z",
        },
    )
    write_marker(
        tmp_path,
        POSTBUILD / "issue_a" / "05_REPAIR_VERIFIED.ready.md",
        {
            "issue_id": "issue_a",
            "family": "run",
            "state": "ready",
            "gate": "ready_for_next_bound",
            "created_at": "2026-05-05T02:00:00Z",
            "supersedes": blocked,
        },
    )
    write_marker(
        tmp_path,
        POSTBUILD / "issue_a" / "06_REPAIR_REVIEW_codex.ready.md",
        {
            "issue_id": "issue_a",
            "family": "review",
            "state": "ready",
            "gate": "blocked",
            "created_at": "2026-05-05T03:00:00Z",
        },
    )

    result = run_next(tmp_path)

    assert result.returncode == 1
    assert "issue_a/06_REPAIR_REVIEW_codex.ready.md" in result.stdout


def test_legacy_blocker_can_be_superseded_by_explicit_path(tmp_path):
    blocked = write_marker(tmp_path, POSTBUILD / "03_LIMIT10_RUN.blocked.md")
    write_marker(
        tmp_path,
        POSTBUILD / "issue_a" / "05_REPAIR_VERIFIED.ready.md",
        {
            "issue_id": "issue_a",
            "family": "repair_verified",
            "state": "ready",
            "gate": "ready_for_next_bound",
            "created_at": "2026-05-05T02:00:00Z",
            "supersedes": blocked,
        },
    )

    result = run_next(tmp_path)

    assert result.returncode == 0
    assert result.stdout == "01_SPEC_DRAFT.ready.md\n"
