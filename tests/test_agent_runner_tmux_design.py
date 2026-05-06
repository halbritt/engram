from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "agent-runner" / "scripts" / "agent_runner_tmux_design.sh"
PROMPT = REPO_ROOT / "agent-runner" / "prompts" / "P001_design_review_build_v1_mvp.md"


def copy_bootstrap(tmp_path: Path) -> None:
    agent_root = tmp_path / "agent-runner"
    script_path = agent_root / "scripts" / "agent_runner_tmux_design.sh"
    prompt_path = agent_root / "prompts" / "P001_design_review_build_v1_mvp.md"
    script_path.parent.mkdir(parents=True)
    prompt_path.parent.mkdir(parents=True)
    shutil.copy2(SCRIPT, script_path)
    shutil.copy2(PROMPT, prompt_path)


def run_script(
    tmp_path: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    copy_bootstrap(tmp_path)
    bash = shutil.which("bash") or "/bin/bash"
    return subprocess.run(
        [bash, "agent-runner/scripts/agent_runner_tmux_design.sh", *args],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_next_reports_first_missing_design_input(tmp_path: Path) -> None:
    result = run_script(tmp_path, "next")

    assert result.returncode == 0
    assert result.stdout == (
        "design_claude -> docs/design/V1_MVP_DESIGN_INPUT_claude.md\n"
    )


def test_next_advances_to_synthesis_after_design_inputs(tmp_path: Path) -> None:
    design_dir = tmp_path / "agent-runner" / "docs" / "design"
    design_dir.mkdir(parents=True)
    for lane in ("claude", "codex", "gemini"):
        (design_dir / f"V1_MVP_DESIGN_INPUT_{lane}.md").write_text(
            f"# {lane}\n", encoding="utf-8"
        )

    result = run_script(tmp_path, "next")

    assert result.returncode == 0
    assert result.stdout == "synthesis_ready -> docs/design/V1_MVP_DESIGN.md\n"


def test_print_prompt_scopes_lane_to_single_output(tmp_path: Path) -> None:
    result = run_script(tmp_path, "print-prompt", "design_gemini")

    assert result.returncode == 0
    assert "Model slug: gemini_3_1_pro" in result.stdout
    assert "Required output artifact: docs/design/V1_MVP_DESIGN_INPUT_gemini.md" in result.stdout
    assert "Do not create or switch branches." in result.stdout
    assert "Do not implement source code." in result.stdout


def test_print_mode_run_job_prints_full_lane_prompt(tmp_path: Path) -> None:
    result = run_script(tmp_path, "run-job", "design_codex")

    assert result.returncode == 0
    assert "=== BEGIN LANE PROMPT ===" in result.stdout
    assert "Model slug: codex_gpt5_5" in result.stdout
    assert "Required output artifact: docs/design/V1_MVP_DESIGN_INPUT_codex.md" in result.stdout
    assert "=== END LANE PROMPT ===" in result.stdout


def test_start_without_tmux_reports_clear_fallback(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("dirname", "mkdir"):
        target = shutil.which(name)
        assert target is not None
        os.symlink(target, bin_dir / name)

    env = os.environ.copy()
    env["PATH"] = str(bin_dir)

    result = run_script(tmp_path, "start", env=env)

    assert result.returncode == 127
    assert "tmux is required for start/start-pipe" in result.stderr
    assert "run-job design_claude" in result.stderr
