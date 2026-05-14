from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_engram_has_no_runtime_striatum_imports() -> None:
    import_pattern = re.compile(r"^\s*(?:from|import)\s+striatum\b", re.MULTILINE)
    offenders: list[str] = []
    for path in sorted((REPO_ROOT / "src" / "engram").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if import_pattern.search(text):
            offenders.append(str(path.relative_to(REPO_ROOT)))

    assert offenders == []


def test_pyproject_does_not_depend_on_striatum_orchestrator() -> None:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "striatum-orchestrator" not in text
