from __future__ import annotations

import ast
import tomllib
from pathlib import Path

import pytest
from fastapi import HTTPException
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.requests import Request

from engram.web import assets, chrome
from engram.web.origin import require_origin
from engram.web.status import status_definition
from engram.web.tier import privacy_tier_envelope, require_tier_ceiling

REPO_ROOT = Path(__file__).resolve().parents[1]


def _request(headers: dict[str, str]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
        }
    )


def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(assets.template_dir())),
        autoescape=select_autoescape(("html",)),
    )


def test_shared_package_data_registered() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    package_data = data["tool"]["setuptools"]["package-data"]

    assert package_data["engram.web"] == ["templates/*.html", "templates/*", "static/*"]


def test_dev_extra_declares_fastapi_testclient_dependency() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    dev_dependencies = data["project"]["optional-dependencies"]["dev"]

    assert "httpx>=0.27,<0.29" in dev_dependencies


def test_shared_resource_directories_exist() -> None:
    assert assets.template_dir().is_dir()
    assert (assets.template_dir() / "_app_shell.html").is_file()
    assert (assets.static_dir() / "keyboard.js").is_file()


def test_shared_resources_have_no_external_asset_references() -> None:
    for resource_name, text in assets.iter_shared_resource_texts():
        assert assets.find_external_asset_references(text) == (), resource_name


def test_app_shell_renders_audit_footer_and_future_tab() -> None:
    html = (
        _environment()
        .get_template("_app_shell.html")
        .render(
            surface="interview",
            surface_label="Interview",
            bind_address="127.0.0.1:8765",
            build_sha="abc123",
            verdict_help_rows=[("true", "correct", "t")],
            shortcut_rows=[("?", "help")],
            disclosure_lines=["Verdicts are advisory."],
        )
    )

    assert "local-only · loopback bind: 127.0.0.1:8765 · no network egress." in html
    assert 'data-future="true"' in html
    assert 'aria-disabled="true"' in html
    future_idx = html.index("Entities (future)")
    future_slice = html[future_idx - 180 : future_idx + 40]
    assert "href=" not in future_slice


def test_surface_tabs_render_from_template_context() -> None:
    bench_html = (
        _environment()
        .get_template("_surface_tabs.html")
        .render(
            surface="bench",
            interview_url="/interview/",
            bench_url="/bench/segments?remaining=1&reviewable=1",
        )
    )
    interview_html = (
        _environment()
        .get_template("_surface_tabs.html")
        .render(
            surface="interview",
            interview_url="/interview/",
            bench_url="/bench/segments?remaining=1&reviewable=1",
        )
    )

    assert 'href="/interview/">Interview</a>' in bench_html
    assert 'href="/bench/segments?remaining=1&amp;reviewable=1">Bench review</a>' in bench_html
    assert 'class="surface-tab is-active"\n     href="/interview/"' in interview_html
    assert (
        'class="surface-tab is-active"\n     href="/bench/segments?remaining=1&amp;reviewable=1"'
    ) in bench_html
    assert 'role="link"' in bench_html
    assert 'aria-disabled="true"' in bench_html
    assert 'data-future="true"' in bench_html
    future_idx = bench_html.index("Entities (future)")
    future_slice = bench_html[future_idx - 180 : future_idx + 40]
    assert "href=" not in future_slice
    assert 'title="Phase 4: not yet built">Entities (future)</span>' in bench_html


def test_chrome_does_not_define_parallel_surface_tab_defaults() -> None:
    assert not hasattr(chrome, "DEFAULT_SURFACE_TABS")
    assert not hasattr(chrome, "SurfaceTab")


def test_app_shell_declares_tokens_without_external_fonts() -> None:
    shell = (assets.template_dir() / "_app_shell.html").read_text(encoding="utf-8")

    assert "--color-accent: #0f6e69" in shell
    assert "--space-4: 16px" in shell
    assert "@import" not in shell
    assert "font-face" not in shell.lower()


def test_app_shell_uses_shared_partials_and_package_local_keyboard() -> None:
    shell = (assets.template_dir() / "_app_shell.html").read_text(encoding="utf-8")

    assert '{% include "_surface_tabs.html" %}' in shell
    assert '{% include "_audit_footer.html" %}' in shell
    assert '{% include "_help_modal.html" %}' in shell
    assert "keyboard_static_url|default('/static/keyboard.js')" in shell
    assert "https://" not in shell


def test_help_modal_contains_local_only_manifest_copy() -> None:
    modal = (
        _environment()
        .get_template("_help_modal.html")
        .render(
            verdict_help_rows=[],
            decision_help_rows=[],
            shortcut_rows=[],
            disclosure_lines=[],
        )
    )

    assert chrome.LOCAL_ONLY_HELP_COPY in modal


def test_future_slot_copy_is_exact() -> None:
    html = (
        _environment()
        .get_template("_future_slot.html")
        .render(
            title="Entities",
            subtitle="Canonical review surface",
            references="RFC 0021 / D044 / D069 / D079",
        )
    )

    assert chrome.PHASE4_FUTURE_COPY in html
    assert 'data-future="true"' in html
    assert "<button" not in html
    assert "href=" not in html


def test_cli_command_card_and_keyboard_support_copy_commands() -> None:
    command = "engram phase3 bench-review export --review-db PATH --output out.json"
    html = (
        _environment()
        .get_template("_cli_command_card.html")
        .render(
            description="Export this review:",
            command=command,
        )
    )
    script = (assets.static_dir() / "keyboard.js").read_text(encoding="utf-8")

    assert 'data-copy-command="' in html
    assert command in html
    assert "[data-copy-command]" in script
    assert "navigator.clipboard.writeText(command)" in script


def test_status_definition_for_unsupported_preserves_copy() -> None:
    definition = status_definition("unsupported")

    assert definition.label == "Unsupported"
    assert (
        definition.long_copy == "Evidence does not establish the claim, regardless of world truth."
    )
    assert definition.color_token == "--color-warn-muted"


def test_keyboard_dispatcher_ignores_text_entry_and_moves_focus() -> None:
    script = (assets.static_dir() / "keyboard.js").read_text(encoding="utf-8")

    assert 'tagName === "INPUT"' in script
    assert 'tagName === "TEXTAREA"' in script
    assert "document.querySelector('h2[tabindex=\"-1\"]')" in script


def test_origin_guard_accepts_loopback_same_origin() -> None:
    request = _request(
        {
            "host": "127.0.0.1:8765",
            "origin": "http://127.0.0.1:8765",
            "sec-fetch-site": "same-origin",
        }
    )

    require_origin(request)


def test_origin_guard_requires_origin_header() -> None:
    request = _request({"host": "127.0.0.1:8765", "sec-fetch-site": "same-origin"})

    with pytest.raises(HTTPException) as exc_info:
        require_origin(request)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error"] == "origin_mismatch"


def test_origin_guard_requires_same_origin_sec_fetch() -> None:
    request = _request(
        {
            "host": "127.0.0.1:8765",
            "origin": "http://127.0.0.1:8765",
            "sec-fetch-site": "cross-site",
        }
    )

    with pytest.raises(HTTPException) as exc_info:
        require_origin(request)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["expected"] == ["sec-fetch-site=same-origin"]


def test_origin_guard_rejects_wrong_port() -> None:
    request = _request(
        {
            "host": "127.0.0.1:8765",
            "origin": "http://127.0.0.1:9999",
            "sec-fetch-site": "same-origin",
        }
    )

    with pytest.raises(HTTPException) as exc_info:
        require_origin(request)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error"] == "origin_mismatch"


def test_tier_guard_allows_tier_at_ceiling() -> None:
    require_tier_ceiling(1)


def test_tier_guard_rejects_tier_above_ceiling_with_envelope() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_tier_ceiling(2, message_id="m-1")

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == {
        "error": "privacy_tier_ceiling",
        "tier": 2,
        "ceiling": 1,
        "message_id": "m-1",
    }
    assert privacy_tier_envelope(2)["error"] == "privacy_tier_ceiling"


def test_shared_package_does_not_import_business_logic() -> None:
    forbidden_prefixes = (
        "engram.interview",
        "engram.bench_review",
        "engram.consolidator",
        "engram.extractor",
        "engram.segmenter",
    )

    for source_path in sorted((REPO_ROOT / "src" / "engram" / "web").glob("*.py")):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imported_modules: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.append(node.module)

        for module in imported_modules:
            assert not module.startswith(forbidden_prefixes), (source_path.name, module)
